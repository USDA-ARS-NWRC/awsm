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


OUTPUT_VARIABLES = {
    'net_rad': {
        'units': 'W m-2',
        'description': 'Average net all-wave radiation',
        'ipysnobal_var': 'R_n_bar'
    },
    'sensible_heat': {
        'units': 'W m-2',
        'description': 'Average sensible heat transfer',
        'ipysnobal_var': 'H_bar'
    },
    'latent_heat': {
        'units': 'W m-2',
        'description': 'Average latent heat exchange',
        'ipysnobal_var': 'L_v_E_bar'
    },
    'snow_soil': {
        'units': 'W m-2',
        'description': 'Average snow/soil heat exchange',
        'ipysnobal_var': 'G_bar'
    },
    'precip_advected': {
        'units': 'W m-2',
        'description': 'Average advected heat from precipitation',
        'ipysnobal_var': 'M_bar'
    },
    'sum_EB': {
        'units': 'W m-2',
        'description': 'Average sum of EB terms for snowcover',
        'ipysnobal_var': 'delta_Q_bar'
    },
    'evaporation': {
        'units': 'kg m-2',
        'description': 'Total evaporation',
        'ipysnobal_var': 'E_s_sum'
    },
    'snowmelt': {
        'units': 'kg m-2',
        'description': 'Total snowmelt',
        'ipysnobal_var': 'melt_sum'
    },
    'SWI': {
        'units': 'kg or mm m-2',
        'description': 'Total runoff',
        'ipysnobal_var': 'ro_pred_sum'
    },
    'cold_content': {
        'units': 'J m-2',
        'description': 'Snowcover cold content',
        'ipysnobal_var': 'cc_s'
    },
    'thickness': {
        'units': 'm',
        'description': 'Predicted thickness of the snowcover',
        'ipysnobal_var': 'z_s'
    },
    'snow_density': {
        'units': 'kg m-3',
        'description': 'Predicted average snow density',
        'ipysnobal_var': 'rho'
    },
    'specific_mass': {
        'units': 'kg m-2',
        'description': 'Predicted specific mass of the snowcover',
        'ipysnobal_var': 'm_s'
    },
    'liquid_water': {
        'units': 'kg m-2',
        'description': 'Predicted mass of liquid water in the snowcover',
        'ipysnobal_var': 'h2o'
    },
    'temp_surf': {
        'units': 'C',
        'description': 'Predicted temperature of the surface layer',
        'ipysnobal_var': 'T_s_0'
    },
    'temp_lower': {
        'units': 'C',
        'description': 'Predicted temperature of the lower layer',
        'ipysnobal_var': 'T_s_l'
    },
    'temp_snowcover': {
        'units': 'C',
        'description': 'Predicted temperature of the snowcover',
        'ipysnobal_var': 'T_s'
    },
    'thickness_lower': {
        'units': 'm',
        'description': 'Predicted thickness of the lower layer',
        'ipysnobal_var': 'z_s_l'
    },
    'water_saturation': {
        'units': 'percent',
        'description': 'Predicted percentage of liquid water saturation of the snowcover',
        'ipysnobal_var': 'h2o_sat'
    }
}


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

    filename = myawsm.config['ipysnobal']['output_file_name'] + '.nc'

    netcdfFile = os.path.join(options['output']['location'], filename)

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
        setattr(em.variables['time'], 'units',
                'hours since %s' % start_date.tz_localize(None))
        setattr(em.variables['time'], 'time_zone', str(myawsm.tzinfo).lower())
        setattr(em.variables['time'], 'calendar', 'standard')
        #     setattr(em.variables['time'], 'time_zone', time_zone)
        em.variables['x'][:] = init['x']
        em.variables['y'][:] = init['y']

        for var_name, att in OUTPUT_VARIABLES.items():
            # check to see if in output variables
            if var_name.lower() in myawsm.pysnobal_output_vars:
                # em.createVariable(v, 'f', dimensions[:3], chunksizes=(6,10,10))
                em.createVariable(var_name, 'f', dimensions[:3], chunksizes=cs)
                setattr(em.variables[var_name], 'units', att['units'])
                setattr(em.variables[var_name],
                        'description', att['description'])

        # add projection info
        em = add_proj(em, None, myawsm.topo.topoConfig['filename'])

    options['output']['ipysnobal'] = em


def output_timestep(s, tstep, options, output_vars):
    """
    Output the model results for the current time step

    Args:
        s:       dictionary of output variable numpy arrays
        tstep:   datetime time step
        options: dictionary of Snobal options

    """

    # preallocate
    output = {}

    # gather all the data together
    for key, att in OUTPUT_VARIABLES.items():
        output[key] = copy(s[att['ipysnobal_var']])

    # convert from K to C
    output['temp_snowcover'] -= FREEZE
    output['temp_surf'] -= FREEZE
    output['temp_lower'] -= FREEZE

    # now find the correct index
    # the current time integer
    times = options['output']['ipysnobal'].variables['time']
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
    options['output']['ipysnobal'].variables['time'][index] = t

    # insert the data
    for key in OUTPUT_VARIABLES.keys():
        if key.lower() in output_vars:
            options['output']['ipysnobal'].variables[key][index, :] = output[key]

    # sync to disk
    options['output']['ipysnobal'].sync()
