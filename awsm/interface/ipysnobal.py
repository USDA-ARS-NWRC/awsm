
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

    def get_timestep_inputs(self, time_step, force=None, s=None):

        if force is not None:
            data = initmodel.get_timestep_netcdf(force, time_step)

        else:
            data = {}
            for var, v in self.variable_list.items():
                # get the data desired
                smrf_data = getattr(s.distribute[v['info']['module']],
                                    v['variable'])

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

    def run_full_timestep(self, tstep, step_index, force=None, s=None):

        self._logger.info('running PySnobal for timestep: {}'.format(tstep))

        self.input2 = self.get_timestep_inputs(tstep, force=force, s=s)

        first_step = step_index
        first_step = self.do_update(first_step, tstep)

        self.do_data_tstep(tstep, first_step)

        self.input1 = self.input2.copy()

        self.output_timestep(tstep, step_index)

        self._logger.info('Finished PySnobal timestep: {}'.format(tstep))

    def output_timestep(self, tstep, step_index):

        out_freq = (step_index * self.data_tstep /
                    3600.0) % self.options['output']['frequency'] == 0
        last_tstep = step_index == len(self.options['time']['date_time']) - 1

        if out_freq or last_tstep:

            self._logger.info('Outputting {}'.format(tstep))
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

        force = io_mod.open_files_nc(self.awsm)
        self.input1 = self.get_timestep_inputs(
            self.options['time']['date_time'][0],
            force=force
        )

        self.initialize_updater()

        self._logger.info('starting PySnobal time series loop')

        for step_index, tstep in enumerate(self.date_time[1:], 1):  # noqa
            self.run_full_timestep(tstep, step_index, force=force)

            # if input has run_for_nsteps, make sure not to go past it
            if self.awsm.run_for_nsteps is not None:
                if step_index > self.awsm.run_for_nsteps:
                    break

        # close input files
        if self.awsm.forcing_data_type == 'netcdf':
            io_mod.close_files(force)

    def run_smrf_ipysnobal(self):
        """
        Function to run SMRF and pass outputs in memory to python wrapped
        iSnobal.

        Args:
            myawsm: AWSM instance
        """
        # first create config to run smrf
        smrf_connector = SMRFConnector(self.awsm)

        with SMRF(smrf_connector.smrf_config, self._logger) as s:
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
            s.loadTopo()

            # 3. initialize the distribution
            s.create_distribution()

            # load weather data  and station metadata
            s.loadData()

            # run threaded or not
            if s.threading:
                self.run_smrf_ipysnobal_threaded(s)
            else:
                self.run_smrf_ipysnobal_serial(s)

        self._logger.debug('DONE!!!!')

    def run_smrf_ipysnobal_serial(self, s):
        """
        Running smrf and PySnobal in non-threaded application.

        Args:
            myawsm:  awsm class
            s:       smrf class

        """

        self._logger.info('Running SMRF and iPysnobal in serial')

        self.initialize_ipysnobal()

        s.initialize_distribution()

        self.variable_list = s.create_output_variable_dict(
            self.FORCING_VARIABLES, '.')

        self.initialize_updater()

        # for step_index, t in enumerate(s.date_time, 1):
        for step_index, tstep in enumerate(self.date_time, 0):
            startTime = datetime.now()

            s.distribute_single_timestep(tstep)
            # perhaps put s.output() here to get SMRF output?

            # run ipysnobal
            if step_index == 0:
                self.input1 = self.get_timestep_inputs(tstep, s=s)
            elif step_index > 0:
                self.run_full_timestep(tstep, step_index, s=s)
            else:
                raise ValueError('Problem with times in run ipysnobal single')

            telapsed = datetime.now() - startTime
            s._logger.debug('{0:.2f} seconds for time step'
                            .format(telapsed.total_seconds()))

    # def run_smrf_ipysnobal_threaded(self, s):
    #     """
    #     Function to run SMRF (threaded) and pass outputs in memory to python
    #     wrapped iSnobal. iPySnobal has replaced the output queue in this
    #     implimentation.

    #     Args:
    #         s:       SMRF instance

    #     """
    #     # initialize ipysnobal state
    #     options, params, tstep_info, init, output_rec = \
    #         initialize_ipysnobal(self.awsm, s)

    #     s.create_data_queue()
    #     s.set_queue_variables()
    #     s.create_distributed_threads(['isnobal'])
    #     s.smrf_queue['isnobal'] = queue.DateQueueThreading(
    #         s.queue_max_values,
    #         s.time_out,
    #         name='isnobal')

    #     del s.smrf_queue['output']

    #     self.initialize_updater()

    #     # isnobal thread
    #     s.threads.append(QueueIsnobal(
    #         s.smrf_queue,
    #         s.date_time,
    #         s.thread_queue_variables,
    #         self.awsm.pysnobal_output_vars,
    #         options,
    #         params,
    #         tstep_info,
    #         init,
    #         output_rec,
    #         s.topo.nx,
    #         s.topo.ny,
    #         self.awsm.soil_temp,
    #         self._logger,
    #         self.awsm.tzinfo,
    #         self.updater))

    #     # the cleaner
    #     s.threads.append(queue.QueueCleaner(s.date_time, s.smrf_queue))

    #     # start all the threads
    #     for i in range(len(s.threads)):
    #         s.threads[i].start()

    #     for i in range(len(s.threads)):
    #         s.threads[i].join()

# ###############################################################
# ########## Functions for interfacing with smrf run ############
# ###############################################################


# def init_from_smrf(myawsm, mysmrf=None, dem=None):
#     """
#     mimic the main.c from the Snobal model

#     Args:
#         self.awsm: AWSM instance
#         mysmrf: SMRF isntance
#         dem:    digital elevation data
#     """

#     # parse the input arguments
#     options, point_run = initmodel.get_args(myawsm)

#     # get the time step info
#     params, tstep_info = initmodel.get_tstep_info(options['constants'],
#                                                   options,
#                                                   myawsm.mass_thresh)

#     if dem is None:
#         dem = myawsm.topo.dem

#     # get init params
#     init = myawsm.myinit.init

#     output_rec = initmodel.initialize(params, tstep_info, init)

#     # create the output files
#     io_mod.output_files(options, init, myawsm.start_date, myawsm)

#     return options, params, tstep_info, init, output_rec


# class QueueIsnobal(threading.Thread):
#     """
#     Takes values from the queue and uses them to run iPySnobal
#     """

#     def __init__(self, queue, date_time, thread_variables, awsm_output_vars,
#                  options, params, tstep_info, init,
#                  output_rec, nx, ny, soil_temp, logger, tzi,
#                  updater=None):
#         """
#         Args:
#             queue:      dictionary of the queue
#             date_time:  array of date_time
#             thread_variables: list of threaded variables
#             awsm_output_vars: list of variables to output
#             options:    dictionary of Snobal options
#             params:     dictionary of Snobal params
#             tstep_info: dictionary of info for Snobal time steps
#             init:       dictionary of init info for Snobal
#             output_rec: dictionary to store Snobal variables between time steps
#             nx:         number of points in X direction
#             ny:         number of points in y direction
#             soil_temp:  uniform soil temperature (float)
#             logger:     initialized AWSM logger
#             tzi:        time zone information
#             updater:    depth updater
#         """

#         threading.Thread.__init__(self, name='isnobal')
#         self.queue = queue
#         self.date_time = date_time
#         self.thread_variables = thread_variables
#         self.awsm_output_vars = awsm_output_vars
#         self.options = options
#         self.params = params
#         self.tstep_info = tstep_info
#         self.init = init
#         self.output_rec = output_rec
#         self.nx = nx
#         self.ny = ny
#         self.soil_temp = soil_temp
#         self.nthreads = self.options['output']['nthreads']
#         self.tzinfo = tzi
#         self.updater = updater

#         # get AWSM logger
#         self._logger = logger
#         self._logger.debug('Initialized iPySnobal thread')

#     def run(self):
#         """
#         mimic the main.c from the Snobal model. Runs Pysnobal while recieving
#         forcing data from SMRF queue.

#         """
#         force_variables = ['thermal', 'air_temp', 'vapor_pressure', 'wind_speed',
#                            'net_solar', 'soil_temp', 'precip', 'percent_snow',
#                            'snow_density', 'precip_temp']

#         # loop through the input
#         # do_data_tstep needs two input records so only go
#         # to the last record-1

#         data_tstep = self.tstep_info[0]['time_step']
#         time_since_out = 0.0
#         tmp_date = self.date_time[0].replace(tzinfo=self.tzinfo)
#         wyhr = utils.water_day(tmp_date)[0] * 24.0
#         start_step = wyhr  # if restart then it would be higher if this were iSnobal
#         # start_step = 0 # if restart then it would be higher if this were iSnobal
#         step_time = start_step * data_tstep
#         # step_time = start_step * 60.0

#         self.output_rec['current_time'] = step_time * \
#             np.ones(self.output_rec['elevation'].shape)
#         self.output_rec['time_since_out'] = time_since_out * \
#             np.ones(self.output_rec['elevation'].shape)

#         # map function from these values to the ones required by snobal
#         MAP_INPUTS = {'air_temp': 'T_a', 'net_solar': 'S_n', 'thermal': 'I_lw',
#                       'vapor_pressure': 'e_a', 'wind_speed': 'u',
#                       'soil_temp': 'T_g', 'precip': 'm_pp',
#                       'percent_snow': 'percent_snow', 'snow_density': 'rho_snow',
#                       'precip_temp': 'T_pp'}

#         # get first time step
#         input1 = {}
#         for v in force_variables:
#             if v in self.queue.keys():

#                 data = self.queue[v].get(
#                     self.date_time[0], block=True, timeout=None)
#                 if data is None:
#                     data = np.zeros((self.ny, self.nx))
#                     self._logger.info('No data from smrf to iSnobal for {} in {}'
#                                       .format(v, self.date_time[0]))
#                     input1[MAP_INPUTS[v]] = data
#                 else:
#                     input1[MAP_INPUTS[v]] = data
#             elif v != 'soil_temp':
#                 self._logger.error('Value not in keys: {}'.format(v))

#         # set ground temp
#         input1['T_g'] = self.soil_temp * np.ones((self.ny, self.nx))

#         input1['T_a'] += FREEZE
#         input1['T_pp'] += FREEZE
#         input1['T_g'] += FREEZE

#         # tell queue we assigned all the variables
#         self.queue['isnobal'].put([self.date_time[0], True])
#         self._logger.info(
#             'Finished initializing first time step for iPySnobal')

#         j = 1
#         # for tstep in options['time']['date_time'][953:958]:
#         for tstep in self.date_time[1:]:
#             # get the output variables then pass to the function
#             # this avoids zeroing of the energetics every time step
#             first_step = j
#             input2 = {}
#             for v in force_variables:
#                 if v in self.queue.keys():
#                     # get variable from smrf queue
#                     data = self.queue[v].get(tstep, block=True, timeout=None)
#                     if data is None:

#                         data = np.zeros((self.ny, self.nx))
#                         self._logger.info(
#                             'No data from smrf to iSnobal for {} in {}'.format(v, tstep))
#                         input2[MAP_INPUTS[v]] = data
#                     else:
#                         input2[MAP_INPUTS[v]] = data
#             # set ground temp
#             input2['T_g'] = self.soil_temp * np.ones((self.ny, self.nx))

#             # convert variables to Kelvin
#             input2['T_a'] += FREEZE
#             input2['T_pp'] += FREEZE
#             input2['T_g'] += FREEZE

#             first_step = j
#             if self.updater is not None:

#                 if tstep in self.updater.update_dates:
#                     self.output_rec = \
#                         self.updater.do_update_pysnobal(self.output_rec,
#                                                         tstep)
#                     first_step = 1

#             self._logger.info(
#                 'running PySnobal for time step: {}'.format(tstep))
#             rt = snobal.do_tstep_grid(input1, input2,
#                                       self.output_rec,
#                                       self.tstep_info,
#                                       self.options['constants'],
#                                       self.params,
#                                       first_step=first_step,
#                                       nthreads=self.nthreads)

#             if rt != -1:
#                 self.logger.error('ipysnobal error on time step {}, pixel {}'
#                                   .format(tstep, rt))
#                 break

#             self._logger.info('Finished time step: {}'.format(tstep))
#             input1 = input2.copy()

#             # output at the frequency and the last time step
#             if ((j)*(data_tstep/3600.0) % self.options['output']['frequency'] == 0)\
#                     or (j == len(self.options['time']['date_time']) - 1):
#                 io_mod.output_timestep(self.output_rec, tstep, self.options,
#                                        self.awsm_output_vars)
#                 self.output_rec['time_since_out'] = \
#                     np.zeros(self.output_rec['elevation'].shape)

#             j += 1

#             # put the value into the output queue so clean knows it's done
#             self.queue['isnobal'].put([tstep, True])

    # self._logger.debug('%s iSnobal run from queues' % tstep)
