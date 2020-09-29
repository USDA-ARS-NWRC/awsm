
from pysnobal.c_snobal import snobal
from datetime import datetime
import sys
import pytz
import logging
import numpy as np
from smrf.utils import utils
from smrf.framework.model_framework import SMRF
from topocalc.shade import shade
from smrf.envphys import sunang
from smrf.utils import queue

import threading
from awsm.interface import initialize_model as initmodel
from awsm.interface import pysnobal_io as io_mod
from awsm.interface.ingest_data import StateUpdater
from awsm.interface.interface import SMRFConnector

C_TO_K = 273.16
FREEZE = C_TO_K

# Kelvin to Celsius


def K_TO_C(x): return x - FREEZE


class PySnobal():

    # map function from these values to the ones required by snobal
    MAP_INPUTS = {
        'air_temp': 'T_a',
        'net_solar': 'S_n',
        'thermal': 'I_lw',
        'vapor_pressure': 'e_a',
        'wind_speed': 'u',
        'soil_temp': 'T_g',
        'precip': 'm_pp',
        'percent_snow': 'percent_snow',
        'snow_density': 'rho_snow',
        'precip_temp': 'T_pp'
    }

    FORCING_VARIABLES = [
        'thermal',
        'air_temp',
        'vapor_pressure',
        'wind_speed',
        'net_solar',
        'soil_temp',
        'precip',
        'percent_snow',
        'snow_density',
        'precip_temp'
    ]

    # def __init__(self, date_time, variable_list, awsm_output_vars,
    #              options, params, tstep_info, init,
    #              output_rec, nx, ny, soil_temp, logger, tzi):
    def __init__(self, myawsm):
        """
        Args:
            date_time:  array of date_time
            variable_list: list of forcing variables to recieve from smrf
            output_vars:    list of variables to output
            options:    dictionary of Snobal options
            params:     dictionary of Snobal params
            tstep_info: dictionary of info for Snobal time steps
            init:       dictionary of init info for Snobal
            output_rec: dictionary to store Snobal variables between time steps
            nx:         number of points in X direction
            ny:         number of points in y direction
            soil_temp:  uniform soil temperature (float)
            logger:     initialized AWSM logger
            tzi:        time zone information
        """
        self._logger = logging.getLogger(__name__)
        self.awsm = myawsm
        self.smrf = None
        self.force = None
        self.smrf_queue = None
        self._logger.debug('Initialized PySnobal')

    @property
    def data_tstep(self):
        return self.tstep_info[0]['time_step']

    @property
    def init_zeros(self):
        return np.zeros_like(self.awsm.topo.dem)

    @property
    def init_ones(self):
        return np.ones_like(self.awsm.topo.dem)

    def _only_for_testing(self, data):
        """Only apply this in testing. This is to ensure that run_ipysnobal
        and run_smrf_ipysnobal are producing the same results. The issues
        stems from netcdf files storing 32-bit floats but smrf_ipysnobal
        uses 64-bit floats from SMRF.

        Not intendend for use outside testing!

        Args:
            data (dict): data dictionary

        Returns:
            dict: data dictionary that has be "written and extracted" from
                a netcdf file
        """

        if self.awsm.testing:
            for key, value in data.items():
                value = value.astype(np.float32)
                value = value.astype(np.float64)
                data[key] = value

        return data

    def initialize_updater(self):
        if self.awsm.update_depth:
            self.updater = StateUpdater(self.awsm)
        else:
            self.updater = None

    def initialize_ipysnobal(self):

        # parse the input arguments
        self.options, point_run = initmodel.get_args(self.awsm)
        self.date_time = self.options['time']['date_time']

        # get the time step info
        self.params, self.tstep_info = initmodel.get_tstep_info(
            self.options['constants'],
            self.options,
            self.awsm.mass_thresh
        )

        # get init params
        self.init = self.awsm.myinit.init

        self.output_rec = initmodel.initialize(
            self.params,
            self.tstep_info,
            self.init
        )

        # create the output files
        io_mod.output_files(
            self.options,
            self.init,
            self.awsm.start_date,
            self.awsm
        )

        self.time_since_out = 0.0
        self.start_step = 0  # if restart then it would be higher if this were iSnobal
        step_time = self.start_step * self.data_tstep

        self.set_current_time(step_time, self.time_since_out)

    def do_update(self, first_step, tstep):

        if self.updater is not None:
            if tstep in self.updater.update_dates:
                self.output_rec = \
                    self.updater.do_update_pysnobal(self.output_rec, tstep)
                first_step = 1

        return first_step

    def get_smrf_data(self, variable, time_step):
        if not self.smrf.threading:
            data = getattr(self.smrf.distribute[variable['info']['module']],
                           variable['variable'])
        else:
            if variable['variable'] == 'soil_temp':
                data = float(self.awsm.soil_temp) * \
                    np.ones_like(self.awsm.topo.dem)
            else:
                data = self.smrf_queue[variable['variable']].get(time_step)
        return data

    def get_timestep_inputs(self, time_step):

        if self.force is not None:
            data = initmodel.get_timestep_netcdf(self.force, time_step)

        else:
            data = {}
            for var, v in self.variable_list.items():
                # get the data desired
                smrf_data = self.get_smrf_data(v, time_step)

                if smrf_data is None:
                    smrf_data = self.init_zeros
                    self._logger.debug(
                        'No data from smrf to iSnobal for {} in {}'.format(
                            v['variable'], time_step))

                data[self.MAP_INPUTS[var]] = smrf_data

            data = self._only_for_testing(data)

        data['T_a'] = data['T_a'] + FREEZE
        data['T_pp'] = data['T_pp'] + FREEZE
        data['T_g'] = data['T_g'] + FREEZE

        return data

    def set_current_time(self, step_time, time_since_out):

        self.output_rec['current_time'] = step_time * self.init_ones
        self.output_rec['time_since_out'] = time_since_out * self.init_ones

    def do_data_tstep(self, tstep, first_step):

        rt = snobal.do_tstep_grid(
            self.input1,
            self.input2,
            self.output_rec,
            self.tstep_info,
            self.options['constants'],
            self.params,
            first_step=first_step,
            nthreads=self.awsm.ipy_threads
        )

        if rt != -1:
            raise ValueError(
                'ipysnobal error on time step {}, pixel {}'.format(tstep, rt))

    def run_full_timestep(self, tstep, step_index):

        self._logger.info('running iPysnobal for timestep: {}'.format(tstep))

        self.input2 = self.get_timestep_inputs(tstep)

        first_step = step_index
        first_step = self.do_update(first_step, tstep)

        self.do_data_tstep(tstep, first_step)

        self.input1 = self.input2.copy()

        self.output_timestep(tstep, step_index)

        self._logger.info('Finished iPysnobal timestep: {}'.format(tstep))

    def run_full_timestep_threaded(self, smrf_queue, data_queue):

        self._logger.info('Running iPysnobal thread')
        self.smrf_queue = smrf_queue

        for step_index, tstep in enumerate(self.date_time, 0):
            startTime = datetime.now()

            # run ipysnobal
            if step_index == 0:
                self.input1 = self.get_timestep_inputs(tstep)
            elif step_index > 0:
                self.run_full_timestep(tstep, step_index)
            else:
                raise ValueError('Problem with times in run ipysnobal single')

            smrf_queue['ipysnobal'].put([tstep, True])
            telapsed = datetime.now() - startTime
            self._logger.debug('iPysnobal {0:.2f} seconds for time step'
                               .format(telapsed.total_seconds()))

    def output_timestep(self, tstep, step_index):

        out_freq = (step_index * self.data_tstep /
                    3600.0) % self.options['output']['frequency'] == 0
        last_tstep = step_index == len(self.options['time']['date_time']) - 1

        if out_freq or last_tstep:

            self._logger.info('iPysnobal outputting {}'.format(tstep))
            io_mod.output_timestep(
                self.output_rec,
                tstep,
                self.options,
                self.awsm.pysnobal_output_vars
            )

            self.output_rec['time_since_out'] = self.init_zeros

    def run_ipysnobal(self):
        """
        Function to run PySnobal from netcdf forcing data,
        not from SMRF instance.

        Args:
            self.awsm:  awsm class

        """

        self._logger.info('Initializing PySnobal from netcdf files')
        self.initialize_ipysnobal()

        self._logger.info('getting inputs for first timestep')

        self.force = io_mod.open_files_nc(self.awsm)
        self.input1 = self.get_timestep_inputs(
            self.options['time']['date_time'][0],
        )

        self.initialize_updater()

        self._logger.info('starting PySnobal time series loop')

        for step_index, tstep in enumerate(self.date_time[1:], 1):  # noqa
            self.run_full_timestep(tstep, step_index)

            # if input has run_for_nsteps, make sure not to go past it
            if self.awsm.run_for_nsteps is not None:
                if step_index > self.awsm.run_for_nsteps:
                    break

        # close input files
        if self.awsm.forcing_data_type == 'netcdf':
            io_mod.close_files(self.force)

    def run_smrf_ipysnobal(self):
        """
        Function to run SMRF and pass outputs in memory to python wrapped
        iSnobal.

        Args:
            myawsm: AWSM instance
        """
        # first create config to run smrf
        smrf_connector = SMRFConnector(self.awsm)

        with SMRF(smrf_connector.smrf_config, self._logger) as self.smrf:
            # # if input has run_for_nsteps, make sure not to go past it
            # if self.awsm.run_for_nsteps is not None:
            #     change_in_hours = int(self.awsm.run_for_nsteps *
            #                           s.config['time']['time_step']/60)
            #     # recalculate end_date before initializing run
            #     s.end_date = s.start_date + pd.to_timedelta(change_in_hours - 1,
            #                                                 unit='h')
            #     self.awsm.end_date = s.end_date
            #     s.date_time = s.date_time[:self.awsm.run_for_nsteps]
            #     s.time_steps = self.awsm.run_for_nsteps

            # load topo data
            self.smrf.loadTopo()

            # 3. initialize the distribution
            self.smrf.create_distribution()

            # load weather data  and station metadata
            self.smrf.loadData()

            # run threaded or not
            if self.smrf.threading:
                self.run_smrf_ipysnobal_threaded()
            else:
                self.run_smrf_ipysnobal_serial()

        self.options['output']['snow'].close()
        self.options['output']['em'].close()
        self._logger.debug('DONE!!!!')

    def run_smrf_ipysnobal_serial(self):
        """
        Running smrf and PySnobal in non-threaded application.

        Args:
            myawsm:  awsm class
            s:       smrf class

        """

        self._logger.info('Running SMRF and iPysnobal in serial')

        self.initialize_ipysnobal()

        self.smrf.initialize_distribution()

        self.variable_list = self.smrf.create_output_variable_dict(
            self.FORCING_VARIABLES, '.')

        self.initialize_updater()

        # for step_index, t in enumerate(s.date_time, 1):
        for step_index, tstep in enumerate(self.date_time, 0):
            startTime = datetime.now()

            self.smrf.distribute_single_timestep(tstep)
            # perhaps put s.output() here to get SMRF output?

            # run ipysnobal
            if step_index == 0:
                self.input1 = self.get_timestep_inputs(tstep)
            elif step_index > 0:
                self.run_full_timestep(tstep, step_index)
            else:
                raise ValueError('Problem with times in run ipysnobal single')

            telapsed = datetime.now() - startTime
            self.smrf._logger.debug('{0:.2f} seconds for time step'
                                    .format(telapsed.total_seconds()))

    def run_smrf_ipysnobal_threaded(self):
        """
        Function to run SMRF (threaded) and pass outputs in memory to python
        wrapped iSnobal. iPySnobal has replaced the output queue in this
        implimentation.

        Args:
            s:       SMRF instance

        """
        self._logger.info('Running SMRF and iPysnobal threaded')

        # initialize ipysnobal state
        self.initialize_ipysnobal()

        self.variable_list = self.smrf.create_output_variable_dict(
            self.FORCING_VARIABLES, '.')

        self.smrf.create_data_queue()
        self.smrf.set_queue_variables()
        self.smrf.create_distributed_threads()
        self.smrf.smrf_queue['ipysnobal'] = queue.DateQueueThreading(
            self.smrf.queue_max_values,
            self.smrf.time_out,
            name='ipysnobal')

        del self.smrf.smrf_queue['output']

        self.initialize_updater()

        self.smrf.threads.append(
            threading.Thread(
                target=self.run_full_timestep_threaded,
                name='ipysnobal',
                args=(self.smrf.smrf_queue, self.smrf.data_queue))
        )

        # the cleaner
        self.smrf.threads.append(queue.QueueCleaner(
            self.smrf.date_time, self.smrf.smrf_queue))

        # start all the threads
        for i in range(len(self.smrf.threads)):
            self.smrf.threads[i].start()

        for i in range(len(self.smrf.threads)):
            self.smrf.threads[i].join()
