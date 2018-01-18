# -*- coding: utf-8 -*-
"""
Functions for initlilizing iSnobal and PySnobal models

Authors: Scott Havens, Micah Sandusky
"""

import os
import numpy as np
from datetime import timedelta
import netCDF4 as nc
from smrf import ipw
from smrf.utils import utils


DEFAULT_MAX_H2O_VOL = 0.01

DATA_TSTEP = 0
NORMAL_TSTEP = 1
MEDIUM_TSTEP = 2
SMALL_TSTEP = 3

DEFAULT_MEDIUM_TSTEP = 15.0
DEFAULT_SMALL_TSTEP = 1.0

WHOLE_TSTEP = 0x1  # output when tstep is not divided
DIVIDED_TSTEP = 0x2  # output when timestep is divided

hrs2min = lambda x: x * 60
min2sec = lambda x: x * 60
SEC_TO_HR = lambda x: x / 3600.0

C_TO_K = 273.16
FREEZE = C_TO_K
# Kelvin to Celcius
K_TO_C = lambda x: x - FREEZE


def check_range(value, min_val, max_val, descrip):
    """
    Check the range of the value
    Args:
        value:  value to check
        min_val: minimum value
        max_val: maximum value
        descrip: short description of input
    Returns:
        True if within range
    """
    if (value < min_val) or (value > max_val):
        raise ValueError("%s (%f) out of range: %f to %f",
                         descrip, value, min_val, max_val)
    pass


def date_range(start_date, end_date, increment):
    '''
    Calculate a list between start and end date with
    an increment
    '''
    result = []
    nxt = start_date
    while nxt <= end_date:
        result.append(nxt)
        nxt += increment
    return np.array(result)


def open_init_files(myawsm, options, dem):
    """
    Reads in the initial_conditions file
        Required variables are x,y,z,z_0
        The others z_s, rho, T_s_0, T_s, h2o_sat, mask can be specified
        but will be set to default of 0's or 1's for mask

    Args:
        myawsm:  awsm Class
        options: dictionary of settings for pysnobal runs
        dem:     digital elevation model image

    Returns:
        init:   dictionary of initialized variables

    """
    # -------------------------------------------------------------------------
    # read the required variables in
    init = {}
    # get the initial conditions
    # if init file is a netcdf init
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
            # if i.variables.has_key(f):
            if f in i.variables:
                init[f] = i.variables[f][:]         # read in the variables
            elif f == 'mask':
                init[f] = np.ones_like(init['elevation'])   # if no mask set all to ones so all will be ran
            else:
                init[f] = all_zeros                 # default is set to zeros

        i.close()

    # if init file is a netcdf output
    elif options['initial_conditions']['input_type'] == 'netcdf_out':
        i = nc.Dataset(os.path.join(options['initial_conditions']['file']))

        init['x'] = i.variables['x'][:]         # get the x coordinates
        init['y'] = i.variables['y'][:]         # get the y coordinates

        # find timestep indices to grab
        time = i.variables['time'][:]
        t_units = i.variables['time'].units
        nc_calendar = i.variables['time'].calendar
        nc_dates = nc.num2date(time, t_units, nc_calendar)
        # find offset of netcdf start
        offset = (nc_dates[0] - myawsm.wy_start).total_seconds()//3600.0

        # add offset to get in wy hours
        time = time + offset

        if myawsm.restart_run:
            tmpwyhr = myawsm.restart_hr
        else:
            # start date water year hour
            tmpwyhr = myawsm.start_wyhr

        # find closest location that the water year hours equal the restart hr
        idt = np.argmin(np.absolute(time - tmpwyhr))  # returns index
        if np.min(np.absolute(time - tmpwyhr)) > 24.0:
            raise ValueError('No time in resatrt file that is within a day of restart time')

        # myawsm._logger.warning('Initialzing PySnobal with state from water year hour {}'.format(myawsm.restart_hr))
        myawsm._logger.warning('Initialzing PySnobal with state from water year hour {}'.format(time[idt]))

        # sample bands
        init['elevation'] = dem        # get the elevation
        if myawsm.roughness_init is not None:
            init['z_0'] = ipw.IPW(myawsm.roughness_init).bands[1].data[:]  # get the roughness length
        else:
            init['z_0'] = 0.005*np.ones((myawsm.ny, myawsm.nx))
            myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')

        init['z_s'] = i.variables['thickness'][idt, :]
        init['rho'] = i.variables['snow_density'][idt, :]
        init['T_s_0'] = i.variables['temp_surf'][idt, :]
        init['T_s'] = i.variables['temp_snowcover'][idt, :]
        init['T_s_l'] = i.variables['temp_lower'][idt, :]
        init['h2o_sat'] = i.variables['water_saturation'][idt, :]

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

    # if init type is an ipw init image
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

    # if initializing from output ipw image
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
            init['z_0'] = ipw.IPW(myawsm.roughness_init).bands[1].data[:]  # get the roughness length
        else:
            init['z_0'] = 0.005*np.ones((myawsm.ny, myawsm.nx))
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
    # init['T_s'][init['T_s'] <= -75.0] = 0.0
    # init['T_s_0'][init['T_s_0'] <= -75.0] = 0.0
    # init['T_s_l'][init['T_s_l'] <= -75.0] = 0.0
    init['T_s'] += FREEZE
    init['T_s_0'] += FREEZE
    if 'T_s_l' in init:
        init['T_s_l'] += FREEZE

    return init


def open_restart_files(myawsm, options, dem):
    """
    Initializes simulation variables for special case when restarting a crashed
    run. Zeros depth under specified threshold and zeros other snow parameters
    that must be dealt with when depth is set to zero.

    Args:
        myawsm:  awsm Class
        options: dictionary of settings for pysnobal runs
        dem:     digital elevation model image

    Returns:
        init:    dictionary of initialized variables
    """
    # restart procedure from failed run
    options['initial_conditions']['input_type'] = 'netcdf_out'
    options['initial_conditions']['file'] = os.path.join(myawsm.pathro, 'snow.nc')
    # initialize with parameters
    init = open_init_files(myawsm, options, dem)
    # zero depths under specified threshold
    restart_var = zero_crash_depths(myawsm,
                                    init['z_s'],
                                    init['rho'],
                                    init['T_s_0'],
                                    init['T_s_l'],
                                    init['T_s'],
                                    init['h2o_sat'])
    # put variables back in init dictionary
    for k, v in restart_var.items():
        init[k] = v

    return init


def zero_crash_depths(myawsm, z_s, rho, T_s_0, T_s_l, T_s, h2o_sat):
    """
    Zero snow depth under certain threshold and deal with associated variables.

    Args:
        myawsm: awsm class
        z_s:    snow depth (Numpy array)
        rho:    snow density (Numpy array)
        T_s_0:  surface layer temperature (Numpy array)
        T_s_l:  lower layer temperature (Numpy array)
        T_s:    average snow cover temperature (Numpy array)
        h2o_sat: percent liquid h2o saturation (Numpy array)

    Returns:
        restart_var: dictionary of input variables after correction
    """

    # find pixels that need reset
    idz = z_s < myawsm.depth_thresh

    # find number of pixels reset
    num_pix = len(np.where(idz)[0])
    num_pix_tot = z_s.size

    myawsm._logger.warning('Zeroing depth in pixels lower than {} [m]'.format(myawsm.depth_thresh))
    myawsm._logger.warning('Zeroing depth in {} out of {} total pixels'.format(num_pix, num_pix_tot))

    z_s[idz] = 0.0
    rho[idz] = 0.0
    T_s_0[idz] = -75.0
    T_s_l[idz] = -75.0
    T_s[idz] = -75.0
    h2o_sat[idz] = 0.0

    restrat_var = {}
    restrat_var['z_s'] = z_s
    restrat_var['rho'] = rho
    restrat_var['T_s_0'] = T_s_0
    restrat_var['T_s_l'] = T_s_l
    restrat_var['T_s'] = T_s
    restrat_var['h2o_sat'] = h2o_sat

    return restrat_var


def get_timestep_netcdf(force, tstep, point=None):
    """
    Pull out a time step from the forcing files and
    place that time step into a dict

    Args:
        force:   input array of forcing variables
        tstep:   datetime timestep

    Returns:
        inpt:    dictionary of forcing variable images
    """

    inpt = {}

    # map function from these values to the ones requried by snobal
    map_val = {'air_temp': 'T_a', 'net_solar': 'S_n', 'thermal': 'I_lw',
               'vapor_pressure': 'e_a', 'wind_speed': 'u',
               'soil_temp': 'T_g', 'precip_mass': 'm_pp',
               'percent_snow': 'percent_snow', 'snow_density': 'rho_snow',
               'precip_temp': 'T_pp'}

    for f in force.keys():

        if isinstance(force[f], np.ndarray):
            # If it's a constant value then just read in the numpy array
            # pull out the value
            if point is None:
                inpt[map_val[f]] = force[f].copy()  # ensures not a reference (especially if T_g)
            else:
                inpt[map_val[f]] = np.atleast_2d(force[f][point[0], point[1]])

        else:
            # determine the index in the netCDF file

            # compare the dimensions and variables to get the variable name
            v = list(set(force[f].variables.keys())-set(force[f].dimensions.keys()))[0]

            # find the index based on the time step
            t = nc.date2index(tstep, force[f].variables['time'],
                              calendar=force[f].variables['time'].calendar,
                              select='exact')

            # pull out the value
            if point is None:
                inpt[map_val[f]] = force[f].variables[v][t, :].astype(np.float64)
            else:
                inpt[map_val[f]] = np.atleast_2d(force[f].variables[v][t, point[0], point[1]].astype(np.float64))

    # convert from C to K
    inpt['T_a'] += FREEZE
    inpt['T_pp'] += FREEZE
    inpt['T_g'] += FREEZE

    return inpt


def get_timestep_ipw(tstep, input_list, ppt_list, myawsm):
    """
    Pull out a time step from the forcing files (IPW) and
    place that time step into a dict

    Args:
        tstep:      datetime of timestep
        input_list: numpy array (1D) of integer timesteps given
        ppt_list:   numpy array(1D) of integer timesteps for ppt_list
        myawsm:     AWSM instance for current run

    Returns:
        inpt:       dictionary of forcing variable images

    """

    inpt = {}

    # map function from these values to the ones requried by snobal
    map_val = {1: 'T_a', 5: 'S_n', 0: 'I_lw',
               2: 'e_a', 3: 'u'}
    map_val_prec = {0: 'm_pp', 1: 'percent_snow',
                    2: 'rho_snow',
                    3: 'T_pp'}

    # get wy hour
    tmp_date = tstep.replace(tzinfo=myawsm.tzinfo)
    wyhr = int(utils.water_day(tmp_date)[0]*24)
    # if we have inputs matching this water year hour
    if np.any(input_list == wyhr):
        i_in = ipw.IPW(os.path.join(myawsm.pathi, 'in.%04i' % (wyhr)))
        # assign soil temp
        inpt['T_g'] = myawsm.soil_temp*np.ones((myawsm.ny, myawsm.nx))
        # myawsm._logger.info('T_g: {}'.format(myawsm.soil_temp))
        # inpt['T_g'] = -2.5*np.ones((myawsm.ny, myawsm.nx))
        for f, v in map_val.items():
            # if no solar data, give it zero
            if f == 5 and len(i_in.bands) < 6:
                # myawsm._logger.info('No solar data for {}'.format(tstep))
                inpt[v] = np.zeros((myawsm.ny, myawsm.nx))
            else:
                inpt[v] = i_in.bands[f].data
    # assign ppt data if there
    else:
        raise ValueError('No input timesteps for {}'.format(tstep))

    if np.any(ppt_list == wyhr):
        i_ppt = ipw.IPW(os.path.join(myawsm.path_ppt, 'ppt.4b_%04i' % (wyhr)))
        for f, v in map_val_prec.items():
            inpt[v] = i_ppt.bands[f].data
    else:
        for f, v in map_val_prec.items():
            inpt[v] = np.zeros((myawsm.ny, myawsm.nx))

    # convert from C to K
    inpt['T_a'] += FREEZE
    inpt['T_pp'] += FREEZE
    inpt['T_g'] += FREEZE

    return inpt


def get_tstep_info(options, config, thresh):
    """
    Parse the options dict, set the default values if not specified
    May need to divide tstep_info and params up into different
    functions

    Args:
        options:    dictionary of input settings for running program
        config:     Snobal config
        thresh:     list of mass thresholds for Snobal

    Returns:
        params:     Snobal parameters
        tstep_info: setting for Snobal timesteps

    """

    # intialize the time step info
    # 0 : data timestep
    # 1 : normal run timestep
    # 2 : medium  "     "
    # 3 : small   "     "

    tstep_info = []
    for i in range(4):
        t = {'level': i, 'output': False, 'threshold': None, 'time_step': None, 'intervals': None}
        tstep_info.append(t)

    # The input data's time step must be between 1 minute and 6 hours.
    # If it is greater than 1 hour, it must be a multiple of 1 hour, e.g.
    # 2 hours, 3 hours, etc.

    data_tstep_min = float(options['time_step'])
    tstep_info[DATA_TSTEP]['time_step'] = min2sec(data_tstep_min)

    norm_tstep_min = 60.0
    tstep_info[NORMAL_TSTEP]['time_step'] = min2sec(norm_tstep_min)
    tstep_info[NORMAL_TSTEP]['intervals'] = int(data_tstep_min / norm_tstep_min)

    med_tstep_min = DEFAULT_MEDIUM_TSTEP
    tstep_info[MEDIUM_TSTEP]['time_step'] = min2sec(med_tstep_min)
    tstep_info[MEDIUM_TSTEP]['intervals'] = int(norm_tstep_min / med_tstep_min)

    small_tstep_min = DEFAULT_SMALL_TSTEP
    tstep_info[SMALL_TSTEP]['time_step'] = min2sec(small_tstep_min)
    tstep_info[SMALL_TSTEP]['intervals'] = int(med_tstep_min / small_tstep_min)

    # output
    if config['output']['output_mode'] == 'data':
        tstep_info[DATA_TSTEP]['output'] = DIVIDED_TSTEP
    elif config['output']['output_mode'] == 'normal':
        tstep_info[NORMAL_TSTEP]['output'] = WHOLE_TSTEP | DIVIDED_TSTEP
    elif config['output']['output_mode'] == 'all':
        tstep_info[NORMAL_TSTEP]['output'] = WHOLE_TSTEP
        tstep_info[MEDIUM_TSTEP]['output'] = WHOLE_TSTEP
        tstep_info[SMALL_TSTEP]['output'] = WHOLE_TSTEP
    else:
        tstep_info[DATA_TSTEP]['output'] = DIVIDED_TSTEP
#     tstep_info[DATA_TSTEP]['output'] = DIVIDED_TSTEP

    # mass thresholds for run timesteps
    tstep_info[NORMAL_TSTEP]['threshold'] = thresh[0]
    tstep_info[MEDIUM_TSTEP]['threshold'] = thresh[1]
    tstep_info[SMALL_TSTEP]['threshold'] = thresh[2]

    # get the rest of the parameters
    params = {}

#     params['elevation'] = options['z']
    params['data_tstep'] = data_tstep_min
    params['max_h2o_vol'] = options['max-h2o']
    params['max_z_s_0'] = options['max_z_s_0']
#     params['sn_filename'] = options['s']
#     params['mh_filename'] = options['h']
#     params['in_filename'] = options['i']
#     params['pr_filename'] = options['p']
    params['out_filename'] = config['output']['out_filename']
    if params['out_filename'] is not None:
        params['out_file'] = open(params['out_filename'], 'w')
    params['stop_no_snow'] = options['c']
    params['temps_in_C'] = options['K']
    params['relative_heights'] = options['relative_heights']

    return params, tstep_info


def get_args(myawsm):
    """
    Parse the configuration file

    Args:
        myawsm: AWSM instance

    Returns:
        options: options structure with defaults if not set

        options = {
            z: site elevation (m),
            t: time steps: data [normal, [,medium [,small]]] (minutes),
            m: snowcover's maximum h2o content as volume ratio,
            d: maximum depth for active layer (m),

            s: snow properties input data file,
            h: measurement heights input data file,
            p: precipitation input data file,
            i: input data file,
            I: initial conditions
            o: optional output data file,
            O: how often output records written (data, normal, all),
            c: continue run even when no snowcover,
            K: accept temperatures in degrees K,
            T: run timesteps' thresholds for a layer's mass (kg/m^2),
        }

    To-do: take all the rest of the defualt and check ranges for the
    input arguements, i.e. rewrite the rest of getargs.c
    """
    # -------------------------------------------------------------------------
    # these are the default options
    options = {
        'time_step': 60,
        'max-h2o': 0.01,
        # 'max_z0': DEFAULT_MAX_Z_S_0,
        'c': True,
        'K': True,
        'mass_threshold': myawsm.mass_thresh[0],
        'time_z': 0,
        'max_z_s_0': myawsm.active_layer,
        'z_u': 5.0,
        'z_t': 5.0,
        'z_g': 0.5,
        'relative_heights': True,
    }

    # make blank config and fill with corresponding sections
    config = {}
    config['time'] = {}
    config['output'] = {}
    config['time']['time_step'] = myawsm.time_step
    if myawsm.restart_run:
        config['time']['start_date'] = myawsm.restart_date
    else:
        config['time']['start_date'] = myawsm.start_date

    config['time']['end_date'] = myawsm.end_date
    config['output']['frequency'] = myawsm.output_freq
    # config['output'] = myawsm.config['ipysnobal output']
    config['output']['location'] = myawsm.pathro
    config['output']['nthreads'] = int(myawsm.ipy_threads)
    config['constants'] = myawsm.config['ipysnobal constants']
    # read in the constants
    c = {}
    for v in myawsm.config['ipysnobal constants']:
        c[v] = float(myawsm.config['ipysnobal constants'][v])
    options.update(c)  # update the defult with any user values

    config['constants'] = options

    # ------------------------------------------------------------------------
    # read in the time and ensure a few things
    # nsteps will only be used if end_date is not specified
    data_tstep_min = int(config['time']['time_step'])
    check_range(data_tstep_min, 1.0, hrs2min(60), "input data's timestep")
    if ((data_tstep_min > 60) and (data_tstep_min % 60 != 0)):
        raise ValueError("Data timestep > 60 min must be multiple of 60 min (whole hrs)")
    config['time']['time_step'] = data_tstep_min

    # add to constant sections for tstep_info calculation
    config['constants']['time_step'] = config['time']['time_step']

    # read in the start date and end date
    start_date = config['time']['start_date']

    end_date = config['time']['end_date']
    if end_date < start_date:
        raise ValueError('end_date is before start_date')
    nsteps = (end_date-start_date).total_seconds()/60  # elapsed time in minutes
    nsteps = int(nsteps / config['time']['time_step'])

    # create a date time vector
    dv = date_range(start_date, end_date,
                    timedelta(minutes=config['constants']['time_step']))

    if len(dv) != nsteps + 1:
        raise Exception('nsteps does not work with selected start and end dates')

    config['time']['start_date'] = start_date
    config['time']['end_date'] = end_date
    config['time']['nsteps'] = nsteps
    config['time']['date_time'] = dv

    # check the output section
    config['output']['frequency'] = int(config['output']['frequency'])

    # user has requested a point run from spatial data
    point_run = False

    config['output']['output_mode'] = 'data'
    config['output']['out_filename'] = None
    config['inputs'] = {}
    config['inputs']['point'] = None
    config['inputs']['input_type'] = myawsm.ipy_init_type
    config['inputs']['soil_temp'] = myawsm.soil_temp

    config['initial_conditions'] = {}
    config['initial_conditions']['file'] = os.path.abspath(myawsm.config['ipysnobal initial conditions']['init_file'])
    config['initial_conditions']['input_type'] = myawsm.config['ipysnobal initial conditions']['input_type'].lower()
    if 'restart' in myawsm.config['ipysnobal initial conditions']:
        config['initial_conditions']['restart'] = myawsm.config['ipysnobal initial conditions']['restart']
    else:
        config['initial_conditions']['restart'] = False

    # if 'mask_file' in myawsm.config['ipysnobal initial conditions']:
    #     if config['initial_conditions']['input_type'] == 'ipw' or config['initial_conditions']['input_type'] == 'ipw_out':
    #         config['initial_conditions']['mask_file'] = myawsm.config['ipysnobal initial conditions']['mask_file']
    #     elif config['initial_conditions']['input_type'] == 'netcdf':
    #         myawsm._logger.error('Mask should be in netcdf, not external file')
    if myawsm.mask_isnobal:
        if myawsm.topotype == 'ipw':
            config['initial_conditions']['mask_file'] = myawsm.fp_mask
        else:
            myawsm._logger.error('Mask should be ipw to run iPySnobal')

    return config, point_run


def initialize(params, tstep_info, init):
    """
    Create the OUTPUT_REC with additional fields and fill
    There are a lot of additional terms that the original output_rec does not
    have due to the output function being outside the C code which doesn't
    have access to those variables.

    Args:
        params:      Snobal parameters
        tstep_info:  setting for Snobal timesteps
        init:        initialization dictionary

    Returns:
        s:           OUTPUT_REC dictionary

    """

    sz = init['elevation'].shape
    flds = ['mask', 'elevation', 'z_0', 'rho', 'T_s_0', 'T_s_l', 'T_s',
            'cc_s_0', 'cc_s_l', 'cc_s', 'm_s', 'm_s_0', 'm_s_l', 'z_s', 'z_s_0', 'z_s_l',
            'h2o_sat', 'layer_count', 'h2o', 'h2o_max', 'h2o_vol', 'h2o_total',
            'R_n_bar', 'H_bar', 'L_v_E_bar', 'G_bar', 'G_0_bar',
            'M_bar', 'delta_Q_bar', 'delta_Q_0_bar', 'E_s_sum', 'melt_sum', 'ro_pred_sum',
            'current_time', 'time_since_out']
    s = {key: np.zeros(sz) for key in flds}  # the structure fields

    # go through each sn value and fill
    for key, val in init.items():
        if key in flds:
            s[key] = val

#     for key, val in mh.items():
#         if key in flds:
#             s[key] = val

    return s
