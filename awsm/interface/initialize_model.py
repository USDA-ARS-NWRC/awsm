# -*- coding: utf-8 -*-
"""
Functions for initlilizing iSnobal and PySnobal models

Authors: Scott Havens, Micah Sandusky
"""

from datetime import timedelta

import numpy as np

DEFAULT_MAX_H2O_VOL = 0.01

DATA_TSTEP = 0
NORMAL_TSTEP = 1
MEDIUM_TSTEP = 2
SMALL_TSTEP = 3

DEFAULT_MEDIUM_TSTEP = 15.0
DEFAULT_SMALL_TSTEP = 1.0

WHOLE_TSTEP = 0x1  # output when tstep is not divided
DIVIDED_TSTEP = 0x2  # output when time step is divided


def hrs2min(x): return x * 60
def min2sec(x): return x * 60
def SEC_TO_HR(x): return x / 3600.0


C_TO_K = 273.16
FREEZE = C_TO_K
# Kelvin to Celsius
def K_TO_C(x): return x - FREEZE


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


def get_args(myawsm):
    """
    Parse the configuration file and returns a dictionary called options.
    Options contains the following keys:

    * z - site elevation (m)
    * t - time steps: data [normal, [,medium [,small]]] (minutes)
    * m - snowcover's maximum h2o content as volume ratio,
    * d - maximum depth for active layer (m),
    * s - snow properties input data file,
    * h - measurement heights input data file,
    * p - precipitation input data file,
    * i - input data file,
    * I - initial conditions
    * o - optional output data file,
    * O - how often output records written (data, normal, all),
    * c - continue run even when no snowcover,
    * K - accept temperatures in degrees K,
    * T - run time steps' thresholds for a layer's mass (kg/m^2)

    To-do: take all the rest of the default and check ranges for the
    input arguments, i.e. rewrite the rest of getargs.c

    Args:
        myawsm: AWSM instance

    Returns:
        dict: dictionary of options structure with defaults if not set

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
    config['output']['location'] = myawsm.path_output
    config['output']['nthreads'] = int(myawsm.ipy_threads)
    config['constants'] = myawsm.config['ipysnobal constants']
    # read in the constants
    c = {}
    for v in myawsm.config['ipysnobal constants']:
        c[v] = float(myawsm.config['ipysnobal constants'][v])
    options.update(c)  # update the default with any user values

    config['constants'] = options

    # ------------------------------------------------------------------------
    # read in the time and ensure a few things
    # nsteps will only be used if end_date is not specified
    data_tstep_min = int(config['time']['time_step'])
    check_range(data_tstep_min, 1.0, hrs2min(60), "input data's time step")
    if ((data_tstep_min > 60) and (data_tstep_min % 60 != 0)):
        raise ValueError(
            "Data time step > 60 min must be multiple of 60 min (whole hrs)")
    config['time']['time_step'] = data_tstep_min

    # add to constant sections for tstep_info calculation
    config['constants']['time_step'] = config['time']['time_step']

    # read in the start date and end date
    start_date = config['time']['start_date']

    end_date = config['time']['end_date']
    if end_date < start_date:
        raise ValueError('end_date is before start_date')
    nsteps = (end_date-start_date).total_seconds() / \
        60  # elapsed time in minutes
    nsteps = int(nsteps / config['time']['time_step'])

    # create a date time vector
    tmp_dv = date_range(start_date, end_date,
                        timedelta(minutes=config['constants']['time_step']))
    dv = [di.replace(tzinfo=myawsm.tzinfo) for di in tmp_dv]

    if len(dv) != nsteps + 1:
        raise Exception(
            'nsteps does not work with selected start and end dates')

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

    # config['initial_conditions'] = {}
    # if myawsm.config['ipysnobal initial conditions']['init_file'] is not None:
    #     config['initial_conditions']['file'] = os.path.abspath(myawsm.config['ipysnobal initial conditions']['init_file'])
    # else:
    #     config['initial_conditions']['file'] = None
    #
    # config['initial_conditions']['input_type'] = myawsm.ipy_init_type.lower()
    # if 'restart' in myawsm.config['ipysnobal initial conditions']:
    #     config['initial_conditions']['restart'] = myawsm.config['ipysnobal initial conditions']['restart']
    # else:
    #     config['initial_conditions']['restart'] = False
    #
    # if myawsm.mask_isnobal:
    #     config['initial_conditions']['mask'] = myawsm.topo.mask

    return config, point_run


def initialize(params, tstep_info, init):
    """
    Create the OUTPUT_REC with additional fields and fill
    There are a lot of additional terms that the original output_rec does not
    have due to the output function being outside the C code which doesn't
    have access to those variables.

    Args:
        params:      Snobal parameters
        tstep_info:  setting for Snobal time steps
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

    return s
