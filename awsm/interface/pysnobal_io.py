import glob
import os
from copy import copy
from datetime import datetime

import netCDF4 as nc
import numpy as np
import pandas as pd
from spatialnc.proj import add_proj

C_TO_K = 273.16
FREEZE = C_TO_K
# Kelvin to Celsius
def K_TO_C(x): return x - FREEZE


def open_files_nc(myawsm):
    """
    Open the netCDF files for initial conditions and inputs
    - Reads in the initial_conditions file
    - Required variables are x,y,z,z_0
    - The others z_s, rho, T_s_0, T_s, h2o_sat, mask can be specified
    but will be set to default of 0's or 1's for mask
    - Open the files for the inputs and store the file identifier

    Args:
        myawsm: awsm class
    Returns:
        force:  dictionary of opened netCDF forcing data files

    """
    # -------------------------------------------------------------------------
    # get the forcing data and open the file
    force = {}
    force['thermal'] = nc.Dataset(
        os.path.join(myawsm.paths, 'thermal.nc'), 'r')
    force['air_temp'] = nc.Dataset(
        os.path.join(myawsm.paths, 'air_temp.nc'), 'r')
    force['vapor_pressure'] = nc.Dataset(
        os.path.join(myawsm.paths, 'vapor_pressure.nc'), 'r')
    force['wind_speed'] = nc.Dataset(
        os.path.join(myawsm.paths, 'wind_speed.nc'), 'r')
    force['net_solar'] = nc.Dataset(
        os.path.join(myawsm.paths, 'net_solar.nc'), 'r')

    # soil temp can either be distributed for set to a constant
    try:
        force['soil_temp'] = nc.Dataset(options['inputs']['soil_temp'], 'r')
    except:
        force['soil_temp'] = float(myawsm.soil_temp) * np.ones((myawsm.topo.ny,
                                                                myawsm.topo.nx))

    force['precip_mass'] = nc.Dataset(
        os.path.join(myawsm.paths, 'precip.nc'), 'r')
    force['percent_snow'] = nc.Dataset(
        os.path.join(myawsm.paths, 'percent_snow.nc'), 'r')
    force['snow_density'] = nc.Dataset(
        os.path.join(myawsm.paths, 'snow_density.nc'), 'r')
    force['precip_temp'] = nc.Dataset(
        os.path.join(myawsm.paths, 'precip_temp.nc'), 'r')

    return force


def close_files(force):
    """
    Close input netCDF forcing files
    """

    for f in force.keys():
        if not isinstance(force[f], np.ndarray):
            force[f].close()


def output_files(options, init, start_date, myawsm):
    """
    Create the snow and em output netCDF file

    Args:
        options:     dictionary of Snobal options
        init:        dictionary of Snobal initialization images
        start_date:  date for time units in files
        myawsm:      awsm class

    """
    fmt = '%Y-%m-%d %H:%M:%S'
    # chunk size
    cs = (6, 10, 10)
    if myawsm.topo.nx < 10:
        cs = (3, 3, 3)

    # ------------------------------------------------------------------------
    # EM netCDF
    m = {}
    m['name'] = ['net_rad', 'sensible_heat', 'latent_heat', 'snow_soil',
                 'precip_advected', 'sum_EB', 'evaporation', 'snowmelt',
                 'SWI', 'cold_content']
    m['units'] = ['W m-2', 'W m-2', 'W m-2', 'W m-2', 'W m-2', 'W m-2',
                  'kg m-2', 'kg m-2', 'kg or mm m-2', 'J m-2']
    m['description'] = ['Average net all-wave radiation',
                        'Average sensible heat transfer',
                        'Average latent heat exchange',
                        'Average snow/soil heat exchange',
                        'Average advected heat from precipitation',
                        'Average sum of EB terms for snowcover',
                        'Total evaporation',
                        'Total snowmelt',
                        'Total runoff',
                        'Snowcover cold content']

    emname = myawsm.em_name+'.nc'
    # if myawsm.restart_run:
    #     emname = 'em_restart_{}.nc'.format(myawsm.restart_hr)
    #     start_date = myawsm.restart_date

    netcdfFile = os.path.join(options['output']['location'], emname)

    if os.path.isfile(netcdfFile):
        myawsm._logger.warning(
            'Opening {}, data may be overwritten!'.format(netcdfFile))
        em = nc.Dataset(netcdfFile, 'a')
        h = '[{}] Data added or updated'.format(
            datetime.now().strftime(fmt))
        setattr(em, 'last_modified', h)

        if 'projection' not in em.variables.keys():
            em = add_proj(em, None, myawsm.topo.topoConfig['filename'])

    else:
        em = nc.Dataset(netcdfFile, 'w')

        dimensions = ('time', 'y', 'x')

        # create the dimensions
        em.createDimension('time', None)
        em.createDimension('y', len(init['y']))
        em.createDimension('x', len(init['x']))

        # create some variables
        em.createVariable('time', 'f', dimensions[0])
        em.createVariable('y', 'f', dimensions[1])
        em.createVariable('x', 'f', dimensions[2])

        # setattr(em.variables['time'], 'units', 'hours since %s' % options['time']['start_date'])
        setattr(em.variables['time'], 'units', 'hours since %s' % start_date)
        setattr(em.variables['time'], 'time_zone', myawsm.tmz)
        setattr(em.variables['time'], 'calendar', 'standard')
        #     setattr(em.variables['time'], 'time_zone', time_zone)
        em.variables['x'][:] = init['x']
        em.variables['y'][:] = init['y']

        # em image
        for i, v in enumerate(m['name']):
            # check to see if in output variables
            if v.lower() in myawsm.pysnobal_output_vars:
                # em.createVariable(v, 'f', dimensions[:3], chunksizes=(6,10,10))
                em.createVariable(v, 'f', dimensions[:3], chunksizes=cs)
                setattr(em.variables[v], 'units', m['units'][i])
                setattr(em.variables[v], 'description', m['description'][i])

        # add projection info
        em = add_proj(em, None, myawsm.topo.topoConfig['filename'])

    options['output']['em'] = em

    # ------------------------------------------------------------------------
    # SNOW netCDF

    s = {}
    s['name'] = ['thickness', 'snow_density', 'specific_mass', 'liquid_water',
                 'temp_surf', 'temp_lower', 'temp_snowcover',
                 'thickness_lower', 'water_saturation']
    s['units'] = ['m', 'kg m-3', 'kg m-2', 'kg m-2', 'C',
                  'C', 'C', 'm', 'percent']
    s['description'] = ['Predicted thickness of the snowcover',
                        'Predicted average snow density',
                        'Predicted specific mass of the snowcover',
                        'Predicted mass of liquid water in the snowcover',
                        'Predicted temperature of the surface layer',
                        'Predicted temperature of the lower layer',
                        'Predicted temperature of the snowcover',
                        'Predicted thickness of the lower layer',
                        'Predicted percentage of liquid water saturation of the snowcover']

    snowname = myawsm.snow_name + '.nc'
    # if myawsm.restart_run:
    #     snowname = 'snow_restart_{}.nc'.format(myawsm.restart_hr)

    netcdfFile = os.path.join(options['output']['location'], snowname)

    if os.path.isfile(netcdfFile):
        myawsm._logger.warning(
            'Opening {}, data may be overwritten!'.format(netcdfFile))
        snow = nc.Dataset(netcdfFile, 'a')
        h = '[{}] Data added or updated'.format(
            datetime.now().strftime(fmt))
        setattr(snow, 'last_modified', h)

        if 'projection' not in snow.variables.keys():
            snow = add_proj(snow, None, myawsm.topo.topoConfig['filename'])

    else:
        dimensions = ('time', 'y', 'x')

        snow = nc.Dataset(netcdfFile, 'w')

        # create the dimensions
        snow.createDimension('time', None)
        snow.createDimension('y', len(init['y']))
        snow.createDimension('x', len(init['x']))

        # create some variables
        snow.createVariable('time', 'f', dimensions[0])
        snow.createVariable('y', 'f', dimensions[1])
        snow.createVariable('x', 'f', dimensions[2])

        setattr(snow.variables['time'], 'units', 'hours since %s' % start_date)
        setattr(snow.variables['time'], 'time_zone', myawsm.tmz)
        setattr(snow.variables['time'], 'calendar', 'standard')
        #     setattr(snow.variables['time'], 'time_zone', time_zone)
        snow.variables['x'][:] = init['x']
        snow.variables['y'][:] = init['y']

        # snow image
        for i, v in enumerate(s['name']):
            # check to see if in output variables
            if v.lower() in myawsm.pysnobal_output_vars:
                snow.createVariable(v, 'f', dimensions[:3], chunksizes=cs)
                # snow.createVariable(v, 'f', dimensions[:3])
                setattr(snow.variables[v], 'units', s['units'][i])
                setattr(snow.variables[v], 'description', s['description'][i])

        # add projection info
        snow = add_proj(snow, None, myawsm.topo.topoConfig['filename'])

    options['output']['snow'] = snow


def output_timestep(s, tstep, options, output_vars):
    """
    Output the model results for the current time step

    Args:
        s:       dictionary of output variable numpy arrays
        tstep:   datetime time step
        options: dictionary of Snobal options

    """

    em_out = {'net_rad': 'R_n_bar', 'sensible_heat': 'H_bar',
              'latent_heat': 'L_v_E_bar',
              'snow_soil': 'G_bar', 'precip_advected': 'M_bar',
              'sum_EB': 'delta_Q_bar', 'evaporation': 'E_s_sum',
              'snowmelt': 'melt_sum', 'SWI': 'ro_pred_sum',
              'cold_content': 'cc_s'}
    snow_out = {'thickness': 'z_s', 'snow_density': 'rho',
                'specific_mass': 'm_s', 'liquid_water': 'h2o',
                'temp_surf': 'T_s_0', 'temp_lower': 'T_s_l',
                'temp_snowcover': 'T_s', 'thickness_lower': 'z_s_l',
                'water_saturation': 'h2o_sat'}

    # preallocate
    em = {}
    snow = {}

    # gather all the data together
    for key, value in em_out.items():
        em[key] = copy(s[value])

    for key, value in snow_out.items():
        snow[key] = copy(s[value])

    # convert from K to C
    snow['temp_snowcover'] -= FREEZE
    snow['temp_surf'] -= FREEZE
    snow['temp_lower'] -= FREEZE

    # now find the correct index
    # the current time integer
    times = options['output']['snow'].variables['time']
    # offset to match same convention as iSnobal
    tstep -= pd.to_timedelta(1, unit='h')
    t = nc.date2num(tstep.replace(tzinfo=None), times.units, times.calendar)

    if len(times) != 0:
        index = np.where(times[:] == t)[0]
        if index.size == 0:
            index = len(times)
        else:
            index = index[0]
    else:
        index = len(times)

    # insert the time
    options['output']['snow'].variables['time'][index] = t
    options['output']['em'].variables['time'][index] = t

    # insert the data
    for key in em_out:
        if key.lower() in output_vars:
            options['output']['em'].variables[key][index, :] = em[key]
    for key in snow_out:
        if key.lower() in output_vars:
            options['output']['snow'].variables[key][index, :] = snow[key]

    # sync to disk
    options['output']['snow'].sync()
    options['output']['em'].sync()
