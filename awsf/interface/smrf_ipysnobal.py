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


def run_smrf_ipysnobal(myawsf):
    """
    Function to run SMRF and pass outputs in memory to python wrapped
    iSnobal.

    Args:
        myawsf: AWSF instance
    """

    # first create config file to run smrf
    fp_smrfini = interface.create_smrf_config(myawsf)

    start = datetime.now()

    if len(sys.argv) > 1:
        configFile = sys.argv[1]

    # initialize
    with smrf.framework.SMRF(fp_smrfini, myawsf._logger) as s:
        # load topo data
        s.loadTopo()

        # 3. initialize the distribution
        s.initializeDistribution()

        # load weather data  and station metadata
        s.loadData()

        # run threaded or not
        if s.threading:
            run_smrf_ipysnobal_threaded(myawsf, s)
        else:
            run_smrf_ipysnobal_single(myawsf, s)

        s._logger.debug('DONE!!!!')

def run_smrf_ipysnobal_single(myawsf, s):
    """
    Distribute the measurement point data for all variables in serial. Each
    variable is initialized first using the :func:`smrf.data.loadTopo.topo`
    instance and the metadata loaded from
    :func:`~smrf.framework.model_framework.SMRF.loadData`.
    The function distributes over each time step, all the variables below.

    """

    # -------------------------------------
    # Initialize the distibution
    for v in s.distribute:
        s.distribute[v].initialize(s.topo, s.data)

    # -------------------------------------
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsf, s)

    # -------------------------------------
    # create variable list
    force_variables = ['thermal', 'air_temp', 'vapor_pressure', 'wind_speed',
                       'net_solar', 'soil_temp', 'precip', 'percent_snow',
                       'snow_density', 'dew_point']
    variable_list = {}
    for v in force_variables:
        for m in s.modules:

            if m in s.distribute.keys():

                d = {'variable': v,
                     'module': m
                     }
                variable_list[v] = d

            elif v == 'soil_temp':
                pass
            else:
                raise ValueError('Not distributing necessary variables to run PySnobal!')

    # -------------------------------------
    # initialize pysnobal run class
    my_pysnobal = ipysnobal.pysnobal(s.date_time,
                                    variable_list,
                                    options,
                                    params,
                                    tstep_info,
                                    init,
                                    output_rec,
                                    s.topo.nx,
                                    s.topo.ny,
                                    myawsf.soil_temp,
                                    myawsf._logger,
                                    myawsf.tzinfo)

    # -------------------------------------
    # Distribute the data
    for output_count, t in enumerate(s.date_time):
        # wait here for the model to catch up if needed

        startTime = datetime.now()

        s._logger.info('Distributing time step %s' % t)
        # 0.1 sun angle for time step
        cosz, azimuth = radiation.sunang(t.astimezone(pytz.utc),
                                         s.topo.topoConfig['basin_lat'],
                                         s.topo.topoConfig['basin_lon'],
                                         zone=0,
                                         slope=0,
                                         aspect=0)

        # 0.2 illumination angle
        illum_ang = None
        if cosz > 0:
            illum_ang = radiation.shade(s.topo.slope,
                                        s.topo.aspect,
                                        azimuth,
                                        cosz)

        # 1. Air temperature
        s.distribute['air_temp'].distribute(s.data.air_temp.ix[t])

        # 2. Vapor pressure
        s.distribute['vapor_pressure'].distribute(s.data.vapor_pressure.ix[t],
                                                    s.distribute['air_temp'].air_temp)

        # 3. Wind_speed and wind_direction
        s.distribute['wind'].distribute(s.data.wind_speed.ix[t],
                                           s.data.wind_direction.ix[t])
#self, data, dpt, time, wind, temp, mask=None
        # 4. Precipitation
        s.distribute['precip'].distribute(s.data.precip.ix[t],
                                            s.distribute['vapor_pressure'].dew_point,
                                            t,
                                            s.data.wind_speed.ix[t],
                                            s.data.air_temp.ix[t],
                                            s.topo.mask)

        # 5. Albedo
        s.distribute['albedo'].distribute(t,
                                             illum_ang,
                                             s.distribute['precip'].storm_days)

        # 6. Solar
        s.distribute['solar'].distribute(s.data.cloud_factor.ix[t],
                                            illum_ang,
                                            cosz,
                                            azimuth,
                                            s.distribute['precip'].last_storm_day_basin,
                                            s.distribute['albedo'].albedo_vis,
                                            s.distribute['albedo'].albedo_ir)

        # 7. thermal radiation
        if s.distribute['thermal'].gridded:
            s.distribute['thermal'].distribute_thermal(s.data.thermal.ix[t],
                                                          s.distribute['air_temp'].air_temp)
        else:
            s.distribute['thermal'].distribute(t,
                                                  s.distribute['air_temp'].air_temp,
                                                  s.distribute['vapor_pressure'].vapor_pressure,
                                                  s.distribute['vapor_pressure'].dew_point,
                                                  s.distribute['solar'].cloud_factor)

        # 8. Soil temperature
        s.distribute['soil_temp'].distribute()

        # 9. pass info to PySnobal
        if t == s.start_date:
            my_pysnobal.run_single_fist_step()
        elif t > s.start_date:
            my_pysnobal.run_single(t)
        else:
            raise ValueError('Problem with times in run ipysnobal single')

        telapsed = datetime.now() - startTime
        s._logger.debug('{0:.2f} seconds for time step'
                           .format(telapsed.total_seconds()))

    s.forcing_data = 1

def run_smrf_ipysnobal_threaded(myawsf, s):
    """
    Function to run SMRF (threaded) and pass outputs in memory to python wrapped
    iSnobal. iPySnobal has replaced the output queue in this implimentation.

    Args:
        myawsf: AWSF instance
        s:      SMRF instance
    """
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsf, s)

    #s.initializeOutput()
    if 'output' in s.thread_variables:
        s.thread_variables.remove('output')
    if not 'isnobal' in s.thread_variables:
        s.thread_variables.append('isnobal')

    # 7. Distribute the data
    # -------------------------------------
    t, q = s.create_distributed_threads()

    # isnobal thread
    t.append(ipysnobal.QueueIsnobal(q, s.date_time,
                               s.thread_variables,
                               options,
                               params,
                               tstep_info,
                               init,
                               output_rec,
                               s.topo.nx,
                               s.topo.ny,
                               myawsf.soil_temp,
                               myawsf._logger,
                               myawsf.tzinfo))

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
