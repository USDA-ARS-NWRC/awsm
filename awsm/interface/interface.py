import smrf
from smrf import data
from spatialnc import ipw
from smrf.utils import io, utils
import os
import numpy as np
import netCDF4 as nc
from datetime import datetime
import pandas as pd
import subprocess
import copy
from inicheck.output import generate_config

def create_smrf_config(myawsm):
    """
    Create a smrf config for running standard :mod: `smr` run. Use the
    :mod: `AWSM` config and remove the sections specific to :mod: `AWSM`.
    We do this because these sections will break the config checker utility
    """
    # ########################################################################
    # ### read in base and write out the specific config file for smrf #######
    # ########################################################################

    delete_keys = myawsm.sec_awsm

    # Write out config file to run smrf
    # make copy and delete only awsm sections
    smrf_cfg = copy.deepcopy(myawsm.ucfg)
    for key in myawsm.ucfg.cfg.keys():
        if key in delete_keys:
            del smrf_cfg.cfg[key]

    # make sure start and end date are correcting
    smrf_cfg.cfg['time']['start_date'] = myawsm.start_date
    smrf_cfg.cfg['time']['end_date'] = myawsm.end_date

    # change start date if using smrf_ipysnobal and restarting
    if myawsm.restart_run and myawsm.run_smrf_ipysnobal:
        smrf_cfg.cfg['time']['start_date'] = myawsm.restart_date

    # set ouput location in smrf config
    smrf_cfg.cfg['output']['out_location'] = os.path.join(myawsm.paths)
    #smrf_cfg.cfg['system']['temp_dir'] = os.path.join(myawsm.paths, 'tmp')
    if myawsm.do_forecast:
        fp_smrfini = myawsm.forecastini
    else:
        fp_smrfini = myawsm.smrfini

    myawsm._logger.info('Making SMRF config!')

    return smrf_cfg


def smrfMEAS(myawsm):
    '''
    Run standard SMRF run. Calls
    :mod: `awsm.interface.interface.creae_smrf_config`
    to make :mod: `smrf` config file and runs
    :mod: `smrf.framework.SMRF` similar to standard run_smrf script

    Args:
        myawsm: AWSM instance
    '''

    # #####################################################################
    # ### run smrf with the config file we just made ######################
    # #####################################################################
    if myawsm.end_date > myawsm.start_date:
        myawsm._logger.info('Running SMRF')
        # first create config to run smrf
        smrf_cfg = create_smrf_config(myawsm)

        start = datetime.now()

        with smrf.framework.SMRF(smrf_cfg, myawsm._logger) as s:
            # 2. load topo data
            s.loadTopo()

            # 3. initialize the distribution
            s.initializeDistribution()

            # initialize the outputs if desired
            s.initializeOutput()

            # ==============================================================
            # Distribute data
            # ==============================================================

            # 5. load weather data  and station metadata
            s.loadData()

            # 6. distribute
            s.distributeData()

            s._logger.info(datetime.now() - start)


def run_isnobal(myawsm, offset=None):
    '''
    Run iSnobal from command line. Checks necessary directories, creates
    initialization image and calls iSnobal.

    Args:
        myawsm: AWSM instance
    '''

    myawsm._logger.info('Setting up to run iSnobal')
    # find water year for calculating offset
    tt = myawsm.start_date - myawsm.wy_start

    # allow offset to be passed in for depth updating procedure
    if offset is None:
        offset = tt.days*24 + tt.seconds//3600  # start index for the input file

    # set number of bits
    nbits = myawsm.nbits

    # set offset for restart
    if myawsm.restart_crash:
        offset = myawsm.restart_hr+1

    # init file
    init_file = myawsm.myinit.fp_init

    # develop the command to run the model
    myawsm._logger.debug("Developing command and running iSnobal")
    nthreads = int(myawsm.ithreads)

    tt = myawsm.end_date-myawsm.start_date

    # if we have input for timesteps, use it
    if myawsm.run_for_nsteps is not None:
        tmstps = myawsm.run_for_nsteps
    elif myawsm.restart_crash:
        tmstps = myawsm.end_wyhr-offset
    else:
        tmstps = tt.days*24 + tt.seconds//3600  # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_ppt_desc = myawsm.ppt_desc

    # check length of ppt_desc file to see if there has been precip
    is_ppt = os.stat(fp_ppt_desc).st_size
    if is_ppt == 0:
        myawsm._logger.warning('Running iSnobal with no precip')

    # thresholds for iSnobal
    mass_thresh = '{},{},{}'.format(myawsm.mass_thresh[0],
                                    myawsm.mass_thresh[1],
                                    myawsm.mass_thresh[2])

    # check length of time steps (bug in the way iSnobal reads in input files)
    if (offset + tmstps) < 1000:
        tmstps = 1001

    run_cmd = 'isnobal -v -P %d -b %d -t 60 -T %s -n %d \
    -I %s -d %f -i %s/in' % (nthreads, myawsm.nbits,
                                          mass_thresh, tmstps,
                                          init_file,
                                          myawsm.active_layer,
                                          myawsm.pathi)
    if offset > 0:
        run_cmd += ' -r %s' % (offset)
    if is_ppt > 0:
        run_cmd += ' -p %s' % (fp_ppt_desc)
    else:
        myawsm._logger.warning('Time frame has no precip!')

    if myawsm.mask_isnobal:
        run_cmd += ' -m %s' % (myawsm.topo.fp_mask)

    # add output frequency in hours
    run_cmd += ' -O {}'.format(int(myawsm.output_freq))

    # add end to string
    run_cmd += ' -e em -s snow  2>&1'

    # change directories, run, and move back
    myawsm._logger.debug("Running {}".format(run_cmd))
    os.chdir(myawsm.pathro)
    # call iSnobal
    p = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    while True:
        line = p.stdout.readline()
        myawsm._logger.info(line)
        if not line:
            break

    os.chdir(cwd)


def run_awsm_daily(myawsm):
    """
    This function is used to run smrf and pysnobal on an hourly scale with
    outputs seperated into daily folders. This will run hourly and allow for
    forecasts like the 18 hour HRRR forecast.
    """
    # get the array of time steps over which to simulate
    d = data.mysql_data.date_range(myawsm.start_date, myawsm.end_date,
                                   pd.to_timedelta(myawsm.time_step,
                                                   unit='m'))

    if myawsm.do_forecast:
        myawsm._logger.warning('Changing PySnobal output to hourly to allow'
                               ' for forecast on each hour')
        myawsm.output_freq = 1

    # set variables for adding a day or hour
    add_day = pd.to_timedelta(23, unit='h')
    add_hour = pd.to_timedelta(1, unit='h')

    start_day = pd.to_datetime(d[0].strftime("%Y%m%d"))
    end_day = pd.to_datetime(d[-1].strftime("%Y%m%d"))
    # if we're starting on an intermediate hour, find timesteps
    # up to first full day
    if d[0] != start_day:
        start_diff = start_day + add_day - d[0]
    else:
        start_diff = add_day
    # find timesteps to end run on last, incomplete day
    if d[-1] != end_day:
        end_diff = d[-1] - end_day
    else:
        end_diff = add_day

    # find total days to run model
    total_days = int(len(d) * myawsm.time_step / (60*24))

    # loop through timesteps and initialize runs for each day
    for day in range(total_days):
        # set variable output names
        myawsm.snow_name = 'snow_00'
        myawsm.em_name = 'em_00'
        # set start and end appropriately
        if day == 0:
            myawsm.start_date = d[0]
            myawsm.end_date = d[0] + start_diff
        elif day == total_days - 1:
            myawsm.start_date = start_day + pd.to_timedelta(24*day, unit='h')
            myawsm.end_date = myawsm.start_date + end_diff
        else:
            myawsm.start_date = start_day + pd.to_timedelta(24*day, unit='h')
            myawsm.end_date = myawsm.start_date + pd.to_timedelta(23, unit='h')

        # recalculate start and end water year hour
        tmp_date = myawsm.start_date.replace(tzinfo=myawsm.tzinfo)
        tmp_end_date = myawsm.end_date.replace(tzinfo=myawsm.tzinfo)
        myawsm.start_wyhr = int(utils.water_day(tmp_date)[0]*24)
        myawsm.end_wyhr = int(utils.water_day(tmp_end_date)[0]*24)

        # find day for labelling the output folder nested one more level in
        daily_append = '{}'.format(myawsm.start_date.strftime("%Y%m%d"))
        myawsm.pathro = os.path.join(myawsm.pathrr, 'output'+daily_append)
        if not os.path.exists(myawsm.pathro):
            os.makedirs(myawsm.pathro)

        # turn off forecast for daily run (will be turned on later if it was true)
        myawsm.config['gridded']['hrrr_forecast_flag'] = False

        # ################# run_model for day ###############################
        myawsm.run_smrf_ipysnobal()

        # reset restart to be last output for next time step
        myawsm.ipy_init_type = 'netcdf_out'
        myawsm.config['ipysnobal initial conditions']['init_file'] = \
            os.path.join(myawsm.pathro, myawsm.snow_name + '.nc')

        # do the 18hr forecast on each hour if forecast is true
        if myawsm.do_forecast:
            # turn forecast back on in smrf config
            myawsm.config['gridded']['hrrr_forecast_flag'] = True

            # now loop through the forecast hours for 18hr forecasts
            d_inner = data.mysql_data.date_range(myawsm.start_date,
                                                  myawsm.end_date,
                                                  pd.to_timedelta(myawsm.time_step,
                                                  unit='m'))
            for t in d_inner:
                # find hour from start of day
                day_hour = t - pd.to_datetime(d_inner[0].strftime("%Y%m%d"))
                day_hour = int(day_hour / np.timedelta64(1, 'h'))

                # reset output names
                myawsm.snow_name = 'snow_{:02d}'.format(day_hour)
                myawsm.em_name = 'em_{:02d}'.format(day_hour)

                # reset start and end days
                myawsm.start_date = t
                myawsm.end_date = t + pd.to_timedelta(myawsm.n_forecast_hours,
                                                      unit='h')

                # recalculate start and end water year hour
                tmp_date = myawsm.start_date.replace(tzinfo=myawsm.tzinfo)
                tmp_end_date = myawsm.end_date.replace(tzinfo=myawsm.tzinfo)
                myawsm.start_wyhr = int(utils.water_day(tmp_date)[0]*24)
                myawsm.end_wyhr = int(utils.water_day(tmp_end_date)[0]*24)

                # run the model for the forecast times
                myawsm.run_smrf_ipysnobal()
