"""
Distribute thermal long wave using only 1 method

20170731 Micah Sandusky
"""

import smrf
from smrf.utils import queue, io
from smrf import ipw
from threading import Thread
from smrf.envphys import radiation
import sys
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from awsm.interface import ipysnobal
from awsm.interface import interface
from awsm.interface import initialize_model as initmodel
from awsm.interface import pysnobal_io as io_mod
import netCDF4 as nc
try:
    from pysnobal import snobal
except:
    print('pysnobal not installed, ignoring')


def run_ipysnobal(myawsm):
    """
    Function to run PySnobal from netcdf of ipw forcing data
    """
    # initialize ipysnobal state
    # read dem if ipw file
    if myawsm.config['topo']['type'] == 'ipw':
        dem = ipw.IPW(myawsm.config['topo']['dem']).bands[0].data
    # read dem if netcdf file
    if myawsm.config['topo']['type'] == 'netcdf':
        demf = nc.Dataset(myawsm.config['topo']['filename'], 'r')
        dem = demf.variables['dem'][:]
        demf.close()

    myawsm._logger.info('Initializing from files')
    options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsm, dem = dem)


    data_tstep = tstep_info[0]['time_step']
    timeSinceOut = 0.0
    start_step = 0 # if restart then it would be higher if this were iSnobal
    step_time = start_step * data_tstep

    output_rec['current_time'] = step_time * np.ones(output_rec['elevation'].shape)
    output_rec['time_since_out'] = timeSinceOut * np.ones(output_rec['elevation'].shape)

    myawsm._logger.info('getting inputs for first timestep')
    if myawsm.forcing_data_type == 'netcdf':
        force = io_mod.open_files_nc(myawsm)
        input1 = initmodel.get_timestep_netcdf(force, options['time']['date_time'][0])
    else:
        input_list, ppt_list = io_mod.open_files_ipw(myawsm)
        input1 = initmodel.get_timestep_ipw(options['time']['date_time'][0], input_list, ppt_list, myawsm)

    myawsm._logger.info('starting PySnobal time series loop')
    j = 1
    first_step = 1;
    for tstep in options['time']['date_time'][1:]:
    #for tstep in options['time']['date_time'][953:958]:
        myawsm._logger.info('running PySnobal for timestep: {}'.format(tstep))
        if myawsm.forcing_data_type == 'netcdf':
            input2 = initmodel.get_timestep_netcdf(force, tstep)
        else:
            input2 = initmodel.get_timestep_ipw(tstep, input_list, ppt_list, myawsm)
        #print output_rec

        rt = snobal.do_tstep_grid(input1, input2, output_rec, tstep_info, options['constants'], params, j, nthreads=myawsm.ipy_threads)

        if rt != -1:
            print('ipysnobal error on time step %s, pixel %i' % (tstep, rt))
            break

        input1 = input2.copy()

        # output at the frequency and the last time step
        # if (j % options['output']['frequency'] == 0) or (j == len(options['time']['date_time'])):
        if ((j)*(data_tstep/3600.0) % options['output']['frequency'] == 0) or (j == len(options['time']['date_time'])):
            myawsm._logger.info('Outputting {}'.format(tstep))
            io_mod.output_timestep(output_rec, tstep, options)
            output_rec['time_since_out'] = np.zeros(output_rec['elevation'].shape)

        myawsm._logger.info('Finished timestep: {}'.format(tstep))

        j += 1

    # close input files
    if myawsm.forcing_data_type == 'netcdf':
        io_mod.close_files(force)

def run_smrf_ipysnobal(myawsm):
    """
    Function to run SMRF and pass outputs in memory to python wrapped
    iSnobal.

    Args:
        myawsm: AWSM instance
    """
    # first create config file to run smrf
    fp_smrfini = interface.create_smrf_config(myawsm)

    start = datetime.now()

    if len(sys.argv) > 1:
        configFile = sys.argv[1]

    # initialize
    with smrf.framework.SMRF(fp_smrfini, myawsm._logger) as s:
        # load topo data
        s.loadTopo()

        # 3. initialize the distribution
        s.initializeDistribution()

        # load weather data  and station metadata
        s.loadData()

        # run threaded or not
        if s.threading:
            run_smrf_ipysnobal_threaded(myawsm, s)
        else:
            run_smrf_ipysnobal_single(myawsm, s)
            print('Not threading')

        s._logger.debug('DONE!!!!')

def run_smrf_ipysnobal_single(myawsm, s):
    """
    Distribute the measurement point data for all variables in serial. Each
    variable is initialized first using the :func:`smrf.data.loadTopo.topo`
    instance and the metadata loaded from
    :func:`~smrf.framework.model_framework.SMRF.loadData`.
    The function distributes over each time step, all the variables below.

    """

    # tzinfo = pytz.timezone(s.config['time']['time_zone'])
    # # start date that is tz aware for comparing with datetime array
    # compare_start = s.start_date.replace(tzinfo=tzinfo)
    # -------------------------------------
    # Initialize the distibution
    for v in s.distribute:
        s.distribute[v].initialize(s.topo, s.data)

    # -------------------------------------
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsm, s)

    # -------------------------------------
    # create variable list
    force_variables = ['thermal', 'air_temp', 'vapor_pressure', 'wind_speed',
                       'net_solar', 'soil_temp', 'precip', 'percent_snow',
                       'snow_density', 'dew_point']
    variable_list = {}
    for v in force_variables:
        for m in s.modules:

            if m in s.distribute.keys():

                if v in s.distribute[m].output_variables.keys():

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
    my_pysnobal = ipysnobal.PySnobal(s.date_time,
                                    variable_list,
                                    options,
                                    params,
                                    tstep_info,
                                    init,
                                    output_rec,
                                    s.topo.nx,
                                    s.topo.ny,
                                    myawsm.soil_temp,
                                    myawsm._logger,
                                    myawsm.tzinfo)

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
        if output_count == 0:
            my_pysnobal.run_single_fist_step(s)
        elif output_count > 0:
            my_pysnobal.run_single(t, s)
        else:
            raise ValueError('Problem with times in run ipysnobal single')

        telapsed = datetime.now() - startTime
        s._logger.debug('{0:.2f} seconds for time step'
                           .format(telapsed.total_seconds()))

    s.forcing_data = 1

def run_smrf_ipysnobal_threaded(myawsm, s):
    """
    Function to run SMRF (threaded) and pass outputs in memory to python wrapped
    iSnobal. iPySnobal has replaced the output queue in this implimentation.

    Args:
        myawsm: AWSM instance
        s:      SMRF instance
    """
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = ipysnobal.init_from_smrf(myawsm, s)

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
                               myawsm.soil_temp,
                               myawsm._logger,
                               myawsm.tzinfo))

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
