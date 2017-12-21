# -*- coding: utf-8 -*-
"""
ipysnobal: the Python implementation of iSnobal

This is not a replica of iSnobal but my interpretation and
porting to Python.  See pysnobal.exact for more direct
interpretation

Authors: Scott Havens, Micah Sandusky
"""

try:
    from pysnobal import snobal
except:
    print('pysnobal not installed, ignoring')

import sys, os
import numpy as np
import pandas as pd
from datetime import timedelta
import netCDF4 as nc
# import matplotlib.pyplot as plt
import progressbar
from copy import copy
from smrf import ipw
from smrf.utils import utils
import sys

try:
    from Queue import Queue, Empty, Full
except:
    from queue import Queue, Empty, Full
import threading
from time import time as _time
import logging
from awsm.interface import initialize_model as initmodel
from awsm.interface import pysnobal_io as io_mod


C_TO_K = 273.16
FREEZE = C_TO_K

# Kelvin to Celcius
K_TO_C = lambda x: x - FREEZE



################################################################
########### Functions for interfacing with smrf run ############
################################################################

def init_from_smrf(myawsm, mysmrf = None, dem = None):
    """
    mimic the main.c from the Snobal model

    Args:
        myawsm: AWSM instance
        mysmrf: SMRF isntance
    """

    # parse the input arguments
    options, point_run = initmodel.get_args(myawsm)

    # get the timestep info
    params, tstep_info = initmodel.get_tstep_info(options['constants'], options)

    if dem is None:
        dem = mysmrf.topo.dem

    # open the files and read in data
    if myawsm.config['isnobal restart']['restart_crash'] == False:
        init = initmodel.open_init_files(myawsm, options, dem)
    # open restart files and zero small depths
    else:
        init = initmodel.open_restart_files(myawsm, options, dem)
        # zero depths at correct location
        restart_var = initmodel.zero_crash_depths(myawsm,
                                                init['z_s'],
                                                init['rho'],
                                                init['T_s_0'],
                                                init['T_s_l'],
                                                init['T_s'],
                                                init['h2o_sat'])
        # put variables back in init dictionary
        for k, v in restart_var.items():
            init[k] = v

    output_rec = initmodel.initialize(params, tstep_info, init)

    # create the output files
    io_mod.output_files(options, init)

    return options, params, tstep_info, init, output_rec

class QueueIsnobal(threading.Thread):
    """
    Takes values from the queue and uses them to run iPySnobal
    """

    def __init__(self, queue, date_time, thread_variables,
                 options, params, tstep_info, init,
                 output_rec, nx, ny, soil_temp, logger, tzi):
        """
        Args:
            date_time: array of date_time
            queue: dict of the queue
        """

        threading.Thread.__init__(self, name='isnobal')
        self.queue = queue
        self.date_time = date_time
        self.thread_variables = thread_variables
        self.options = options
        self.params = params
        self.tstep_info = tstep_info
        self.init = init
        self.output_rec = output_rec
        self.nx = nx
        self.ny = ny
        self.soil_temp = soil_temp
        self.nthreads = self.options['output']['nthreads']
        self.tzinfo = tzi

        # get AWSM logger
        self._logger = logger
        self._logger.debug('Initialized iPySnobal thread')

    def run(self):
        """
        mimic the main.c from the Snobal model

        Args:
            configFile: path to configuration file
        """
        force_variables = ['thermal', 'air_temp', 'vapor_pressure', 'wind_speed',
                           'net_solar', 'soil_temp', 'precip', 'percent_snow',
                           'snow_density', 'dew_point']

        # loop through the input
        # do_data_tstep needs two input records so only go
        # to the last record-1

        data_tstep = self.tstep_info[0]['time_step']
        timeSinceOut = 0.0
        tmp_date = self.date_time[0].replace(tzinfo=self.tzinfo)
        wyhr = utils.water_day(tmp_date)[0] * 24.0
        start_step = wyhr # if restart then it would be higher if this were iSnobal
        # start_step = 0 # if restart then it would be higher if this were iSnobal
        step_time = start_step * data_tstep
        # step_time = start_step * 60.0

        self.output_rec['current_time'] = step_time * np.ones(self.output_rec['elevation'].shape)
        self.output_rec['time_since_out'] = timeSinceOut * np.ones(self.output_rec['elevation'].shape)

        # map function from these values to the ones requried by snobal
        map_val = {'air_temp': 'T_a', 'net_solar': 'S_n', 'thermal': 'I_lw',
                   'vapor_pressure': 'e_a', 'wind_speed': 'u',
                   'soil_temp': 'T_g', 'precip': 'm_pp',
                   'percent_snow': 'percent_snow', 'snow_density': 'rho_snow',
                   'dew_point': 'T_pp'}

        # get first timestep
        input1 = {}
        for v in force_variables:
            if v in self.queue.keys():

                data = self.queue[v].get(self.date_time[0], block=True, timeout=None)
                if data is None:
                    data = np.zeros((self.ny, self.nx))
                    self._logger.info('No data from smrf to iSnobal for {} in {}'.format(v, self.date_time[0]))
                    input1[map_val[v]] = data
                else:
                    input1[map_val[v]] = data
            elif v != 'soil_temp':
                self._logger.error('Value not in keys: {}'.format(v))

        # set ground temp
        input1['T_g'] = self.soil_temp*np.ones((self.ny, self.nx))

        input1['T_a'] += FREEZE
        input1['T_pp'] += FREEZE
        input1['T_g'] += FREEZE

        # tell queue we assigned all the variables
        self.queue['isnobal'].put([self.date_time[0], True])
        self._logger.info('Finished initializing first timestep for iPySnobal')

        #pbar = progressbar.ProgressBar(max_value=len(options['time']['date_time']))
        j = 1
        for tstep in self.date_time[1:]:
        #for tstep in options['time']['date_time'][953:958]:
        # get the output variables then pass to the function
            # this avoids zeroing of the energetics every timestep
            first_step = j
            input2 = {}
            for v in force_variables:
                if v in self.queue.keys():
                    # get variable from smrf queue
                    data = self.queue[v].get(tstep, block=True, timeout=None)
                    if data is None:

                        data = np.zeros((self.ny, self.nx))
                        self._logger.info('No data from smrf to iSnobal for {} in {}'.format(v, tstep))
                        input2[map_val[v]] = data
                    else:
                        input2[map_val[v]] = data
            # set ground temp
            input2['T_g'] = self.soil_temp*np.ones((self.ny, self.nx))
            # convert variables to Kelvin
            input2['T_a'] += FREEZE
            input2['T_pp'] += FREEZE
            input2['T_g'] += FREEZE

            self._logger.info('running PySnobal for timestep: {}'.format(tstep))
            rt = snobal.do_tstep_grid(input1, input2, self.output_rec,
                                      self.tstep_info, self.options['constants'],
                                      self.params, first_step, nthreads=self.nthreads)

            if rt != -1:
                self.logger.error('ipysnobal error on time step {}, pixel {}'.format(tstep, rt))
                break

            self._logger.info('Finished timestep: {}'.format(tstep))
            input1 = input2.copy()

            # output at the frequency and the last time step
            if ((j)*(data_tstep/3600.0) % self.options['output']['frequency'] == 0) or (j == len(self.options['time']['date_time'])):
                io_mod.output_timestep(self.output_rec, tstep, self.options)
                self.output_rec['time_since_out'] = np.zeros(self.output_rec['elevation'].shape)

            j += 1
            #pbar.update(j)

            # put the value into the output queue so clean knows it's done
            self.queue['isnobal'].put([tstep, True])

            #self._logger.debug('%s iSnobal run from queues' % tstep)

        #pbar.finish()

class PySnobal():
    """
    Takes values from the SMRF and uses them to run iPySnobal
    """

    def __init__(self, date_time, variable_list,
                 options, params, tstep_info, init,
                 output_rec, nx, ny, soil_temp, logger, tzi):
        """
        Args:
            date_time: array of date_time
        """

        self.date_time = date_time
        self.variable_list = variable_list
        self.options = options
        self.params = params
        self.tstep_info = tstep_info
        self.init = init
        self.output_rec = output_rec
        self.nx = nx
        self.ny = ny
        self.soil_temp = soil_temp
        self.nthreads = self.options['output']['nthreads']
        self.tzinfo = tzi

        # map function from these values to the ones requried by snobal
        self.map_val = {'air_temp': 'T_a', 'net_solar': 'S_n', 'thermal': 'I_lw',
                   'vapor_pressure': 'e_a', 'wind_speed': 'u',
                   'soil_temp': 'T_g', 'precip': 'm_pp',
                   'percent_snow': 'percent_snow', 'snow_density': 'rho_snow',
                   'dew_point': 'T_pp'}


        # get AWSM logger
        self._logger = logger
        self._logger.debug('Initialized iPySnobal thread')

    def run_single_fist_step(self, s):
        """
        mimic the main.c from the Snobal model

        Args:
            configFile: path to configuration file
        """

        # loop through the input
        # do_data_tstep needs two input records so only go
        # to the last record-1

        self.data_tstep = self.tstep_info[0]['time_step']
        self.timeSinceOut = 0.0
        tmp_date = self.date_time[0].replace(tzinfo=self.tzinfo)
        wyhr = utils.water_day(tmp_date)[0] * 24.0
        start_step = wyhr # if restart then it would be higher if this were iSnobal
        # start_step = 0 # if restart then it would be higher if this were iSnobal
        step_time = start_step * self.data_tstep
        # step_time = start_step * 60.0

        self.output_rec['current_time'] = step_time * np.ones(self.output_rec['elevation'].shape)
        self.output_rec['time_since_out'] = self.timeSinceOut * np.ones(self.output_rec['elevation'].shape)

        # get first timestep
        self.input1 = {}
        for var, v in self.variable_list.items():
                # get the data desired
                data = getattr(s.distribute[v['module']], v['variable'])

                if data is None:
                    data = np.zeros((self.ny, self.nx))
                    self._logger.info('No data from smrf to iSnobal for {} in {}'.format(v, self.date_time[0]))
                    self.input1[self.map_val[var]] = data
                else:
                    self.input1[self.map_val[var]] = data

        # set ground temp
        self.input1['T_g'] = self.soil_temp*np.ones((self.ny, self.nx))

        self.input1['T_a'] += FREEZE
        self.input1['T_pp'] += FREEZE
        self.input1['T_g'] += FREEZE

        # for counting how many steps since the start of the run
        self.j = 1

        self._logger.info('Finished initializing first timestep for iPySnobal')

    def run_single(self, tstep, s):
        #pbar = progressbar.ProgressBar(max_value=len(options['time']['date_time']))

        self.input2 = {}
        for var, v in self.variable_list.items():
            # get the data desired
            data = getattr(s.distribute[v['module']], v['variable'])
            if data is None:

                data = np.zeros((self.ny, self.nx))
                self._logger.info('No data from smrf to iSnobal for {} in {}'.format(v, tstep))
                self.input2[self.map_val[var]] = data
            else:
                self.input2[self.map_val[var]] = data
        # set ground temp
        self.input2['T_g'] = self.soil_temp*np.ones((self.ny, self.nx))
        # convert variables to Kelvin
        self.input2['T_a'] += FREEZE
        self.input2['T_pp'] += FREEZE
        self.input2['T_g'] += FREEZE

        first_step = self.j

        self._logger.info('running PySnobal for timestep: {}'.format(tstep))
        rt = snobal.do_tstep_grid(self.input1, self.input2, self.output_rec,
                                  self.tstep_info, self.options['constants'],
                                  self.params,first_step, nthreads=self.nthreads)

        if rt != -1:
            self.logger.error('ipysnobal error on time step {}, pixel {}'.format(tstep, rt))
            sys.exit()

        self._logger.info('Finished timestep: {}'.format(tstep))
        self.input1 = self.input2.copy()

        # output at the frequency and the last time step
        #if (self.j*(self.data_tstep/3600.0) % self.options['output']['frequency'] == 0) or (self.j == len(self.options['time']['date_time'])):
        if ((self.j)*(self.data_tstep/3600.0) % self.options['output']['frequency'] == 0) or (self.j == len(self.options['time']['date_time'])):
            io_mod.output_timestep(self.output_rec, tstep, self.options)
            self.output_rec['time_since_out'] = np.zeros(self.output_rec['elevation'].shape)

        self.j += 1
