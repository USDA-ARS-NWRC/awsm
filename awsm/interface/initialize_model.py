# -*- coding: utf-8 -*-
"""
Functions for initlilizing iSnobal and PySnobal models

Authors: Scott Havens, Micah Sandusky
"""

try:
    from pysnobal import snobal
except:
    print('pysnobal not installed, ignoring')

import ConfigParser
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

try:
    from Queue import Queue, Empty, Full
except:
    from queue import Queue, Empty, Full
import threading
from time import time as _time
import logging

C_TO_K = 273.16
FREEZE = C_TO_K




def open_init_files(myawsm, options, dem):
    """
    Open the netCDF files for initial conditions and inputs
    - Reads in the initial_conditions file
        Required variables are x,y,z,z_0
        The others z_s, rho, T_s_0, T_s, h2o_sat, mask can be specified
        but will be set to default of 0's or 1's for mask

    - Open the files for the inputs and store the file identifier

    """

    #------------------------------------------------------------------------------
    # read the required variables in
    init = {}
    # get the initial conditions
    if options['initial_conditions']['input_type'] == 'netcdf':
        i = nc.Dataset(options['initial_conditions']['file'])

        init['x'] = i.variables['x'][:]         # get the x coordinates
        init['y'] = i.variables['y'][:]         # get the y coordinates
        init['elevation'] = i.variables['z'][:]         # get the elevation
        init['z_0'] = i.variables['z_0'][:]     # get the roughness length

        # All other variables will be assumed zero if not present
        all_zeros = np.zeros_like(init['elevation'])
        flds = ['z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat', 'mask']

        for f in flds:
            if i.variables.has_key(f):
                init[f] = i.variables[f][:]         # read in the variables
            elif f == 'mask':
                init[f] = np.ones_like(init['elevation'])   # if no mask set all to ones so all will be ran
            else:
                init[f] = all_zeros                 # default is set to zeros

        i.close()

    elif options['initial_conditions']['input_type'] == 'netcdf_out':
        i = nc.Dataset(os.paht.join(options['initial_conditions']['file']))

        init['x'] = i.variables['x'][:]         # get the x coordinates
        init['y'] = i.variables['y'][:]         # get the y coordinates

        # find timestep indices to grab
        t_units = i.variables['time'].units
        t_start = t_units.split('since ')[1]
        t_start = pd.to_datetime(t_start)
        start_wy = pd.to_datetime('{}-10-01'.format(myawsm.wy))
        offset = (t_start - start_wy).astype('timedelta64[h]')

        time = i.variables['time'][:]
        time = time + offset

        idt = np.where(time == myawsm.restart_hr)[0]

        myawsm._logger.warning('Initialzing PySnobal with state from water year hour {}'.format(myawsm.restart_hr))

        # sample bands
        init['elevation'] = dem        # get the elevation
        if myawsm.roughness_init is not None:
            init['z_0'] = ipw.IPW(myawsm.roughness_init).bands[1].data[:] # get the roughness length
        else:
            init['z_0'] = 0.005*np.ones((myawsm.ny,myawsm.nx))
            myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')

        init['z_s'] = i.variables['thickness'][idt,:]
        init['rho'] = i.variables['snow_density'][idt,:]
        init['T_s_0'] = i.variables['temp_surf'][idt,:]
        init['T_s'] = i.variables['temp_snowcover'][idt,:]
        init['T_s_l'] =  i.variables['temp_lower'][idt,:]
        init['h2o_sat'] = i.variables['water_saturation'][idt,:]

        if 'mask_file' in options['initial_conditions']:
            imask = ipw.IPW(options['initial_conditions']['mask_file'])
            msk = imask.bands[0].data
            init['mask'] = msk
        else:
            init['mask'] = np.ones_like(init['elevation'])

        # All other variables will be assumed zero if not present
        all_zeros = np.zeros_like(init['elevation'])
        # flds = ['z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat', 'mask']


        i.close()


    elif options['initial_conditions']['input_type'] == 'ipw':

        i = ipw.IPW(options['initial_conditions']['file'])
        if 'mask_file' in options['initial_conditions']:
            imask = ipw.IPW(options['initial_conditions']['mask_file'])
            msk = imask.bands[0].data

        x = myawsm.v + myawsm.dv*np.arange(myawsm.nx)
        y = myawsm.u + myawsm.du*np.arange(myawsm.ny)

        # read the required variables in
        init = {}
        init['x'] = x         # get the x coordinates
        init['y'] = y         # get the y coordinates
        init['elevation'] = i.bands[0].data[:]        # get the elevation
        init['z_0'] = i.bands[1].data[:]     # get the roughness length

        # All other variables will be assumed zero if not present
        all_zeros = np.zeros_like(init['elevation'])

        init['z_s'] = i.bands[2].data[:]
        init['rho'] = i.bands[3].data[:]
        init['T_s_0'] = i.bands[4].data[:]
        init['T_s'] = i.bands[5].data[:]
        init['h2o_sat'] = i.bands[6].data[:]
        if len(i.bands) > 7:
            init['T_s_l'] = i.bands[6].data[:]

        # Add mask if input
        if 'mask_file' in options['initial_conditions']:
            init['mask'] = msk
        else:
            init['mask'] = np.ones_like(init['elevation'])

    elif options['initial_conditions']['input_type'] == 'ipw_out':
        # initialize from output file and roughness init
        i = ipw.IPW(options['initial_conditions']['file'])
        if 'mask_file' in options['initial_conditions']:
            imask = ipw.IPW(options['initial_conditions']['mask_file'])
            msk = imask.bands[0].data

        x = myawsm.v + myawsm.dv*np.arange(myawsm.nx)
        y = myawsm.u + myawsm.du*np.arange(myawsm.ny)

        # read the required variables in
        init = {}
        init['x'] = x         # get the x coordinates
        init['y'] = y         # get the y coordinates
        init['elevation'] = dem        # get the elevation
        if myawsm.roughness_init is not None:
            init['z_0'] = ipw.IPW(myawsm.roughness_init).bands[1].data[:] # get the roughness length
        else:
            init['z_0'] = 0.005*np.ones((myawsm.ny,myawsm.nx))
            myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')

        # All other variables will be assumed zero if not present
        all_zeros = np.zeros_like(init['elevation'])

        init['z_s'] = i.bands[0].data[:]
        init['rho'] = i.bands[1].data[:]
        init['T_s_0'] = i.bands[4].data[:]
        init['T_s_l'] = i.bands[5].data[:]
        init['T_s'] = i.bands[6].data[:]
        init['h2o_sat'] = i.bands[8].data[:]

        # Add mask if input
        if 'mask_file' in options['initial_conditions']:
            init['mask'] = msk
        else:
            init['mask'] = np.ones_like(init['elevation'])

    else:
        myawsm._logger.error('Wrong input type for iPySnobal init file')


    for key in init.keys():
        init[key] = init[key].astype(np.float64)

    # convert temperatures to K
    # init['T_s'][init['T_s'] <= 75.0] = 0.0
    # init['T_s_0'][init['T_s_0'] <= 75.0] = 0.0
    # init['T_s_l'][init['T_s_l'] <= 75.0] = 0.0
    init['T_s'] += FREEZE
    init['T_s_0'] += FREEZE
    if 'T_s_l' in init:
        init['T_s_l'] += FREEZE

    return init

def open_restart_files(myawsm, options, mysmrf.topo.dem):
    # read in correct variables
    init = {}

    i = nc.Dataset(os.paht.join(myawsm.pathro,'snow.nc'))

    init['x'] = i.variables['x'][:]         # get the x coordinates
    init['y'] = i.variables['y'][:]         # get the y coordinates

    # find timestep indices to grab
    t_units = i.variables['time'].units
    t_start = t_units.split('since ')[1]
    t_start = pd.to_datetime(t_start)
    start_wy = pd.to_datetime('{}-10-01'.format(myawsm.wy))
    offset = (t_start - start_wy).astype('timedelta64[h]')

    time = i.variables['time'][:]
    time = time + offset

    idt = np.where(time == myawsm.restart_hr)[0]

    # sample bands
    init['elevation'] = dem        # get the elevation
    if myawsm.roughness_init is not None:
        init['z_0'] = ipw.IPW(myawsm.roughness_init).bands[1].data[:] # get the roughness length
    else:
        init['z_0'] = 0.005*np.ones((myawsm.ny,myawsm.nx))
        myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')

    init['z_s'] = i.variables['thickness'][idt,:]
    init['rho'] = i.variables['snow_density'][idt,:]
    init['T_s_0'] = i.variables['temp_surf'][idt,:]
    init['T_s'] = i.variables['temp_snowcover'][idt,:]
    init['T_s_l'] =  i.variables['temp_lower'][idt,:]
    init['h2o_sat'] = i.variables['water_saturation'][idt,:]

    if 'mask_file' in options['initial_conditions']:
        imask = ipw.IPW(options['initial_conditions']['mask_file'])
        msk = imask.bands[0].data
        init['mask'] = msk
    else:
        init['mask'] = np.ones_like(init['elevation'])

    # All other variables will be assumed zero if not present
    all_zeros = np.zeros_like(init['elevation'])
    # flds = ['z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat', 'mask']

    i.close()

    for key in init.keys():
        init[key] = init[key].astype(np.float64)

    init['T_s'] += FREEZE
    init['T_s_0'] += FREEZE
    if 'T_s_l' in init:
        init['T_s_l'] += FREEZE

    return init

def zero_crash_depths(myawsm, z_s, rho, T_s_0, T_s_l, T_s, h20_sat):

    # find pixels that need reset
    idz = z_s < myawsm.depth_thresh

    # find number of pixels reset
    num_pix = len(np.where(idz == True)[0])
    num_pix_tot = z_s.size

    myawsm._logger.warning('Zeroing depth in pixels lower than {} [m]'.format(myawsm.depth_thresh))
    myawsm._logger.warning('Zeroing depth in {} out of {} total pixels'.format(num_pix, num_pix_tot))

    z_s[idz] = 0.0
    rho[idz] = 0.0
    T_s_0[idz] = -75.0
    T_s_l[idz] = -75.0
    T_s[idz] = -75.0
    h20_sat[idz] = 0.0

    restrat_var = {}
    restrat_var['z_s'] = z_s
    restrat_var['rho'] = rho
    restrat_var['T_s_0'] = T_s_0
    restrat_var['T_s_l'] = T_s_l
    restrat_var['T_s'] = T_s
    restrat_var['h2o_sat'] = h2o_sat

    return restrat_var
