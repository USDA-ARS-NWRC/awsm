"""
Functions for running PySnobal as well as SMRF and Pysnobal
threaded together

20170731 Micah Sandusky
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytz
import smrf.framework
from topocalc.shade import shade
from smrf.envphys import sunang
from smrf.utils import queue

from awsm.interface import ipysnobal, interface, initialize_model as initmodel, \
    pysnobal_io as io_mod
from awsm.interface.ingest_data import StateUpdater

from pysnobal.c_snobal import snobal


def run_ipysnobal(myawsm):
    """
    Function to run PySnobal from netcdf forcing data,
    not from SMRF instance.

    Args:
        myawsm:  awsm class

    """
    # initialize ipysnobal state
    # get dem
    dem = myawsm.topo.dem

    myawsm._logger.info('Initializing from files')
    options, params, tstep_info, init, output_rec = \
        ipysnobal.init_from_smrf(myawsm, dem=dem)

    data_tstep = tstep_info[0]['time_step']
    timeSinceOut = 0.0
    start_step = 0  # if restart then it would be higher if this were iSnobal
    step_time = start_step * data_tstep

    output_rec['current_time'] = step_time * \
        np.ones(output_rec['elevation'].shape)
    output_rec['time_since_out'] = timeSinceOut * \
        np.ones(output_rec['elevation'].shape)

    myawsm._logger.info('getting inputs for first timestep')
    if myawsm.forcing_data_type == 'netcdf':
        force = io_mod.open_files_nc(myawsm)
        input1 = initmodel.get_timestep_netcdf(
            force, options['time']['date_time'][0])

    # initialize updater if required
    if myawsm.update_depth:
        updater = StateUpdater(myawsm)
    else:
        updater = None

    myawsm._logger.info('starting PySnobal time series loop')
    j = 1
    # run PySnobal
    # TODO this will need to change, it should be the other way around
    # where it goes one less
    for tstep in options['time']['date_time'][1:]:
        # for tstep in options['time']['date_time'][953:958]:
        myawsm._logger.info('running PySnobal for timestep: {}'.format(tstep))
        if myawsm.forcing_data_type == 'netcdf':
            input2 = initmodel.get_timestep_netcdf(force, tstep)

        first_step = j
        # update depth if necessary
        if updater is not None:
            if tstep in updater.update_dates:
                start_z = output_rec['z_s'].copy()
                output_rec = \
                    updater.do_update_pysnobal(output_rec, tstep)
                first_step = 1

        rt = snobal.do_tstep_grid(input1, input2, output_rec, tstep_info,
                                  options['constants'], params, first_step=first_step,
                                  nthreads=myawsm.ipy_threads)

        if rt != -1:
            raise ValueError(
                'ipysnobal error on time step %s, pixel %i' % (tstep, rt))
            # break

        input1 = input2.copy()

        # output at the frequency and the last time step
        if ((j)*(data_tstep/3600.0) % options['output']['frequency'] == 0) \
                or (j == len(options['time']['date_time']) - 1):
            myawsm._logger.info('Outputting {}'.format(tstep))
            io_mod.output_timestep(output_rec, tstep, options,
                                   myawsm.pysnobal_output_vars)
            output_rec['time_since_out'] = np.zeros(
                output_rec['elevation'].shape)

        myawsm._logger.info('Finished timestep: {}'.format(tstep))

        j += 1

        # if input has run_for_nsteps, make sure not to go past it
        if myawsm.run_for_nsteps is not None:
            if j > myawsm.run_for_nsteps:
                break

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
    # first create config to run smrf
    smrf_cfg = interface.create_smrf_config(myawsm)

    # start = datetime.now()

    # initialize
    with smrf.framework.SMRF(smrf_cfg, myawsm._logger) as s:
        # if input has run_for_nsteps, make sure not to go past it
        if myawsm.run_for_nsteps is not None:
            change_in_hours = int(myawsm.run_for_nsteps *
                                  s.config['time']['time_step']/60)
            # recalculate end_date before initializing run
            s.end_date = s.start_date + pd.to_timedelta(change_in_hours - 1,
                                                        unit='h')
            myawsm.end_date = s.end_date
            s.date_time = s.date_time[:myawsm.run_for_nsteps]
            s.time_steps = myawsm.run_for_nsteps

        # load topo data
        s.loadTopo()

        # 3. initialize the distribution
        s.create_distribution()

        # load weather data  and station metadata
        s.loadData()

        # run threaded or not
        if s.threading:
            run_smrf_ipysnobal_threaded(myawsm, s)
        else:
            run_smrf_ipysnobal_single(myawsm, s)

        s._logger.debug('DONE!!!!')


def run_smrf_ipysnobal_single(myawsm, s):
    """
    Running smrf and PySnobal in non-threaded application.

    Args:
        myawsm:  awsm class
        s:       smrf class

    """

    # -------------------------------------
    # Initialize the distibution
    s.initialize_distribution()

    # -------------------------------------
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = \
        ipysnobal.init_from_smrf(myawsm, s)

    # -------------------------------------
    # create variable list
    force_variables = ['thermal', 'air_temp', 'vapor_pressure', 'wind_speed',
                       'net_solar', 'soil_temp', 'precip', 'percent_snow',
                       'snow_density', 'precip_temp']

    # Collect the potential output variables
    possible_output_variables = {}
    for variable, module in s.distribute.items():
        possible_output_variables.update(module.output_variables)

    variable_list = {}
    for force_variable in force_variables:

        if force_variable in possible_output_variables.keys():
            module = possible_output_variables[force_variable]['module']

            variable_list[force_variable] = {
                'variable': force_variable,
                'module': module
            }

        else:
            raise ValueError('Not distributing necessary '
                             'variables to run PySnobal!')

    # -------------------------------------
    # initialize updater if required
    if myawsm.update_depth:
        updater = StateUpdater(myawsm)
    else:
        updater = None
    # initialize pysnobal run class
    my_pysnobal = ipysnobal.PySnobal(s.date_time,
                                     variable_list,
                                     myawsm.pysnobal_output_vars,
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
        cosz, azimuth, rad_vec = sunang.sunang(
            t.astimezone(pytz.utc),
            s.topo.basin_lat,
            s.topo.basin_long,
        )

        # 0.2 illumination angle
        illum_ang = None
        if cosz > 0:
            illum_ang = shade(
                s.topo.sin_slope,
                s.topo.aspect,
                azimuth,
                cosz)

        # 1. Air temperature
        s.distribute['air_temp'].distribute(s.data.air_temp.loc[t])

        # 2. Vapor pressure
        s.distribute['vapor_pressure'].distribute(
            s.data.vapor_pressure.loc[t],
            s.distribute['air_temp'].air_temp)

        # 3. Wind_speed and wind_direction
        s.distribute['wind'].distribute(
            s.data.wind_speed.loc[t],
            s.data.wind_direction.loc[t],
            t)

        # 4. Precipitation
        s.distribute['precipitation'].distribute(
            s.data.precip.loc[t],
            s.distribute['vapor_pressure'].dew_point,
            s.distribute['vapor_pressure'].precip_temp,
            s.distribute['air_temp'].air_temp,
            t,
            s.data.wind_speed.loc[t],
            s.data.air_temp.loc[t],
            s.distribute['wind'].wind_direction,
            s.distribute['wind'].wind_model.dir_round_cell,
            s.distribute['wind'].wind_speed,
            s.distribute['wind'].wind_model.cellmaxus
        )

        # 5. Albedo
        s.distribute['albedo'].distribute(
            t,
            illum_ang,
            s.distribute['precipitation'].storm_days
        )

        # 6. cloud factor
        s.distribute['cloud_factor'].distribute(s.data.cloud_factor.loc[t])

        # 7. solar
        s.distribute['solar'].distribute(
            t,
            s.distribute["cloud_factor"].cloud_factor,
            illum_ang,
            cosz,
            azimuth,
            s.distribute['albedo'].albedo_vis,
            s.distribute['albedo'].albedo_ir)

        # 7. thermal radiation
        if s.distribute['thermal'].gridded and \
           s.config['gridded']['data_type'] != 'hrrr_grib':
            s.distribute['thermal'].distribute_thermal(
                s.data.thermal.loc[t],
                s.distribute['air_temp'].air_temp)
        else:
            s.distribute['thermal'].distribute(
                t,
                s.distribute['air_temp'].air_temp,
                s.distribute['vapor_pressure'].vapor_pressure,
                s.distribute['vapor_pressure'].dew_point,
                s.distribute['cloud_factor'].cloud_factor)

        # 8. Soil temperature
        s.distribute['soil_temp'].distribute()

        # 9. pass info to PySnobal
        if output_count == 0:
            my_pysnobal.run_single_fist_step(s)
        elif output_count > 0:
            my_pysnobal.run_single(t, s, updater)
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
        myawsm:  AWSM instance
        s:       SMRF instance

    """
    # initialize ipysnobal state
    options, params, tstep_info, init, output_rec = \
        ipysnobal.init_from_smrf(myawsm, s)

    s.create_data_queue()
    s.set_queue_variables()
    s.create_distributed_threads(['isnobal'])
    s.smrf_queue['isnobal'] = queue.DateQueueThreading(
        s.queue_max_values,
        s.time_out,
        name='isnobal')

    del s.smrf_queue['output']

    # initialize updater if required
    if myawsm.update_depth:
        updater = StateUpdater(myawsm)
    else:
        updater = None

    # isnobal thread
    s.threads.append(ipysnobal.QueueIsnobal(
        s.smrf_queue,
        s.date_time,
        s.thread_queue_variables,
        myawsm.pysnobal_output_vars,
        options,
        params,
        tstep_info,
        init,
        output_rec,
        s.topo.nx,
        s.topo.ny,
        myawsm.soil_temp,
        myawsm._logger,
        myawsm.tzinfo,
        updater))

    # the cleaner
    s.threads.append(queue.QueueCleaner(s.date_time, s.smrf_queue))

    # start all the threads
    for i in range(len(s.threads)):
        s.threads[i].start()

    for i in range(len(s.threads)):
        s.threads[i].join()
