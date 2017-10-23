"""
Distribute thermal long wave using only 1 method

20170731 Micah Sandusky
"""

import smrf
from smrf.utils import queue, io
from threading import Thread
from smrf.envphys import radiation
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from awsf.interface import ipysnobal
from awsf.interface import interface


def run_smrf_ipysnobal(self):

    # first create config file to run smrf
    fp_smrfini = interface.create_smrf_config(self)

    start = datetime.now()

    if len(sys.argv) > 1:
        configFile = sys.argv[1]

    # initialize
    with smrf.framework.SMRF(fp_smrfini) as s:
        # load topo data
        s.loadTopo()

        # 3. initialize the distribution
        s.initializeDistribution()

        # load weather data  and station metadata
        s.loadData()

        # initialize ipysnobal state
        options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(self)

        #s.initializeOutput()

        # 7. Distribute the data
        # -------------------------------------
        for v in s.distribute:
            s.distribute[v].initialize(s.topo, s.data)

        # Create Queues for all the variables
        q = {}
        t = []

        if s.distribute['precip'].nasde_model == 'marks2017':
            s.thread_variables += ['storm_total', 'storm_id']


        # replace output with isnobal in threaded variables
        s.thread_variables.remove('output')
        s.thread_variables.append('isnobal')

        for v in s.thread_variables:
            q[v] = queue.DateQueue_Threading(s.max_values, s.time_out)

        # -------------------------------------
        # Distribute the data

        # 0.1 sun angle for time step
        t.append(Thread(target=radiation.sunang_thread,
                        name='sun_angle',
                        args=(q, s.date_time,
                              s.topo.topoConfig['basin_lat'],
                              s.topo.topoConfig['basin_lon'],
                              0, 0, 0)))

        # 0.2 illumination angle
        t.append(Thread(target=radiation.shade_thread,
                        name='illum_angle',
                        args=(q, s.date_time,
                              s.topo.slope, s.topo.aspect)))

        # 1. Air temperature
        t.append(Thread(target=s.distribute['air_temp'].distribute_thread,
                        name='air_temp',
                        args=(q, s.data.air_temp)))

        # 2. Vapor pressure
        t.append(Thread(target=s.distribute['vapor_pressure'].distribute_thread,
                        name='vapor_pressure',
                        args=(q, s.data.vapor_pressure)))

        # 3. Wind_speed and wind_direction
        t.append(Thread(target=s.distribute['wind'].distribute_thread,
                        name='wind',
                        args=(q, s.data.wind_speed,
                              s.data.wind_direction)))

        # 4. Precipitation
        t.append(Thread(target=s.distribute['precip'].distribute_thread,
                        name='precipitation',
                        args=(q, s.data.precip, s.date_time,
                              s.topo.mask)))

        # 5. Albedo
        t.append(Thread(target=s.distribute['albedo'].distribute_thread,
                        name='albedo',
                        args=(q, s.date_time)))

        # 6.1 Clear sky visible
        t.append(Thread(target=s.distribute['solar'].distribute_thread_clear,
                        name='clear_vis',
                        args=(q, s.data.cloud_factor, 'clear_vis')))

        # 6.2 Clear sky ir
        t.append(Thread(target=s.distribute['solar'].distribute_thread_clear,
                        name='clear_ir',
                        args=(q, s.data.cloud_factor, 'clear_ir')))

        # 6.3 Net radiation
        t.append(Thread(target=s.distribute['solar'].distribute_thread,
                        name='solar',
                        args=(q, s.data.cloud_factor)))

        # 7. thermal radiation
        if s.distribute['thermal'].gridded:
            t.append(Thread(target=s.distribute['thermal'].distribute_thermal_thread,
                            name='thermal',
                            args=(q, s.data.thermal)))
        else:
            t.append(Thread(target=s.distribute['thermal'].distribute_thread,
                            name='thermal',
                            args=(q, s.date_time)))

        # isnobal thread
        t.append(ipysnobal.QueueIsnobal(q, s.date_time,
                                   s.config['output']['frequency'],
                                   s.thread_variables,
                                   options,
                                   params,
                                   tstep_info,
                                   init,
                                   output_rec,
                                   s.topo.nx,
                                   s.topo.ny,
                                   self.soil_temp))

        # the cleaner
        t.append(queue.QueueCleaner(s.date_time, q))

        # start all the threads
        for i in range(len(t)):
            t[i].start()

        # wait for all the threads to stop
    #         for v in q:
    #             q[v].join()

        for i in range(len(t)):
            t[i].join()

        s._logger.debug('DONE!!!!')
