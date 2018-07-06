import smrf
from smrf import ipw, data
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

    # append snowav keys if we're doing reporting
    if myawsm.do_report:
        delete_keys = myawsm.sec_awsm.append(myawsm.sec_snowav)
    else:
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

    myawsm._logger.info('Writing the config file for SMRF')
    generate_config(smrf_cfg, fp_smrfini)

    return fp_smrfini


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
        # first create config file to run smrf
        fp_smrfini = create_smrf_config(myawsm)

        start = datetime.now()

        # with smrf.framework.SMRF(meas_ini_file) as s:
        with smrf.framework.SMRF(fp_smrfini, myawsm._logger) as s:
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

def make_init_file(myawsm, offset):
    i_out = ipw.IPW()

    # making dem band
    if myawsm.topotype == 'ipw':
        i_dem = ipw.IPW(myawsm.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif myawsm.topotype == 'netcdf':
        dem_file = nc.Dataset(myawsm.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)
        dem_file.close()

    if myawsm.mask_isnobal:
        i_mask = ipw.IPW(myawsm.fp_mask).bands[0].data
        myawsm._logger.info('Masking init file')
    else:
        i_mask = np.ones((myawsm.ny, myawsm.nx))

    if offset > 0:
        # use given rougness from old init file if given
        if myawsm.roughness_init is not None:
            i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
        else:
            myawsm._logger.warning('No roughness given from old init,'
                                   ' using value of 0.005 m')
            i_out.new_band(0.005*np.ones((myawsm.ny, myawsm.nx)))

        # if we have a previous mod file
        if myawsm.prev_mod_file is not None:
            i_in = ipw.IPW(myawsm.prev_mod_file)

            i_out.new_band(i_in.bands[0].data*i_mask)  # snow depth
            i_out.new_band(i_in.bands[1].data*i_mask)  # snow density

            i_out.new_band(i_in.bands[4].data*i_mask)  # active layer temp
            i_out.new_band(i_in.bands[5].data*i_mask)  # lower layer temp
            i_out.new_band(i_in.bands[6].data*i_mask)  # avgerage snow temp

            i_out.new_band(i_in.bands[8].data*i_mask)  # percent saturatio

        else:
            myawsm._logger.warning('Offset is greater than zero, but no prev_mod_file given!')
            i_out.new_band(0.0*i_mask)  # snow depth
            i_out.new_band(0.0*i_mask)  # snow density

            i_out.new_band(-75.0*i_mask)  # active layer temp
            i_out.new_band(-75.0*i_mask)  # lower layer temp
            i_out.new_band(-75.0*i_mask)  # avgerage snow temp

            i_out.new_band(0.0*i_mask)  # percent saturation

        i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv],
                          myawsm.units, myawsm.csys)
        i_out.write(os.path.join(myawsm.pathinit,
                                 'init%04d.ipw' % (offset)), myawsm.nbits)

    else:
        zs0 = np.zeros((myawsm.ny, myawsm.nx))
        if myawsm.roughness_init is not None:
            i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
        else:
            myawsm._logger.warning('No roughness given from old init,'
                                   ' using value of 0.005 m')
            i_out.new_band(0.005*np.ones((myawsm.ny, myawsm.nx)))
        #             i_out.new_band(i_rl0.bands[0].data)
        i_out.new_band(zs0)  # zeros snow cover depth
        i_out.new_band(zs0)  # 0density
        i_out.new_band(zs0)  # 0ts active
        i_out.new_band(zs0)  # 0ts avg
        i_out.new_band(zs0)  # 0liquid
        i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv],
                          myawsm.units, myawsm.csys)

    init_file = os.path.join(myawsm.pathinit,
                             'init%04d.ipw' % (offset))
    i_out.write(init_file, myawsm.nbits)

    myawsm._logger.debug('Wrote init file {}'.format(init_file))

    return init_file

def make_init_restart(myawsm):
    # find water year hour and file paths
    name_crash = 'snow.%04d' % myawsm.restart_hr
    fp_crash = os.path.join(myawsm.pathro, name_crash)
    fp_new_init = os.path.join(myawsm.pathinit,
                               'init%04d.ipw' % myawsm.restart_hr)

    # new ipw image for initializing restart
    myawsm._logger.info("making new init image")
    i_out = ipw.IPW()

    # read in crash image and old init image
    i_crash = ipw.IPW(fp_crash)
    # ########################################################

    # making dem band
    if myawsm.topotype == 'ipw':
        i_dem = ipw.IPW(myawsm.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif myawsm.topotype == 'netcdf':
        dem_file = nc.Dataset(myawsm.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)
        dem_file.close()

    if myawsm.roughness_init is not None:
        i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
    else:
        myawsm._logger.warning('No roughness given from old init, '
                               'using value of 0.005 m')
        i_out.new_band(0.005*np.ones((myawsm.ny, myawsm.nx)))

    # pull apart crash image and zero out values at index with depths < thresh
    z_s = i_crash.bands[0].data  # snow depth
    rho = i_crash.bands[1].data  # snow density
    T_s_0 = i_crash.bands[4].data  # active layer temp
    T_s_l = i_crash.bands[5].data  # lower layer temp
    T_s = i_crash.bands[6].data  # avgerage snow temp
    h20_sat = i_crash.bands[8].data  # percent saturation

    myawsm._logger.info("correcting crash image, deleting "
                        "depths under {} [m]".format(myawsm.depth_thresh))

    # find pixels that need reset
    idz = z_s < myawsm.depth_thresh

    # find number of pixels reset
    num_pix = len(np.where(idz)[0])
    num_pix_tot = z_s.size

    myawsm._logger.warning('Zeroing depth in '
                           '{} out of {} total pixels'.format(num_pix,
                                                              num_pix_tot))

    z_s[idz] = 0.0
    rho[idz] = 0.0
    T_s_0[idz] = -75.0
    T_s_l[idz] = -75.0
    T_s[idz] = -75.0
    h20_sat[idz] = 0.0

    # fill in init image
    i_out.new_band(z_s)
    i_out.new_band(rho)
    i_out.new_band(T_s_0)
    i_out.new_band(T_s_l)
    i_out.new_band(T_s)
    i_out.new_band(h20_sat)
    i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv],
                      myawsm.units, myawsm.csys)

    myawsm._logger.info('Writing to {}'.format(fp_new_init))
    i_out.write(fp_new_init, myawsm.nbits)

    return fp_new_init

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

    # making initial conditions file
    myawsm._logger.debug("Making initial conds img for iSnobal")
    # if we were not given an init file, make one
    if myawsm.init_file is None:
        if myawsm.restart_crash:
            init_file = make_init_restart(myawsm)
            offset = myawsm.restart_hr+1
        else:
            init_file = make_init_file(myawsm, offset)
            print('init', init_file)
    else:
        myawsm._logger.info('Initializing iSnobal with given init file')
        init_file = myawsm.init_file

    # develop the command to run the model
    myawsm._logger.debug("Developing command and running iSnobal")
    nthreads = int(myawsm.ithreads)

    tt = myawsm.end_date-myawsm.start_date

    # if we have input for timesteps, use it
    if myawsm.run_for_nsteps is not None:
        tmstps = myawsm.run_for_nsteps
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
        run_cmd += ' -m %s' % (myawsm.fp_mask)

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


def restart_crash_image(myawsm):
    '''
    Restart iSnobal from crash. Read in last output, zero depths smaller than
    a threshold, write new initialization image, and call iSnobal.

    Args:
        myawsm: AWSM instance
    '''
    nbits = myawsm.nbits
    nthreads = myawsm.ithreads



    myawsm._logger.info('Running isnobal from restart')
    offset = myawsm.restart_hr+1

    # use start date water year
    tt = myawsm.end_date - myawsm.wy_start

    tmstps = tt.days*24 + tt.seconds//3600  # start index for the input file
    tmstps = int(tmstps - offset)
    # if we have input for tmstps, use it
    if myawsm.run_for_nsteps is not None:
        tmstps = myawsm.run_for_nsteps

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_ppt_desc = myawsm.ppt_desc

    # check if there was precip
    is_ppt = os.stat(fp_ppt_desc).st_size
    if is_ppt == 0:
        myawsm._logger.warning('Running iSnobal with no precip')

    # check length of time steps (bug in the way iSnobal reads in input files)
    if (offset + tmstps) < 1000:
        tmstps = 1001

    # thresholds for iSnobal
    mass_thresh = '{},{},{}'.format(myawsm.mass_thresh[0],
                                    myawsm.mass_thresh[1],
                                    myawsm.mass_thresh[2])

    run_cmd = "isnobal -v -P %d -r %s -T %s -t 60 -n %s \
               -I %s -d %f -i %s/in" % (nthreads, offset, mass_thresh,
                                        tmstps, fp_new_init,
                                        myawsm.active_layer, myawsm.pathi)

    if is_ppt > 0:
        run_cmd += ' -p %s' % (fp_ppt_desc)
    else:
        myawsm._logger.warning('Time frame has no precip!')

    if myawsm.mask_isnobal:
        run_cmd += ' -m %s' % (myawsm.fp_mask)

    # add output frequency in hours
    run_cmd += ' -O {}'.format(int(myawsm.output_freq))

    # add end to string
    run_cmd += ' -e em -s snow  2>&1'

    # change directories, run, and move back
    myawsm._logger.debug("Running {}".format(run_cmd))

    os.chdir(myawsm.pathro)
    p = subprocess.Popen(run_cmd, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
        myawsm.config['gridded']['forecast_flag'] = False

        # ################# run_model for day ###############################
        myawsm.run_smrf_ipysnobal()

        # reset restart to be last output for next time step
        myawsm.ipy_init_type = 'netcdf_out'
        myawsm.config['ipysnobal initial conditions']['init_file'] = \
            os.path.join(myawsm.pathro, myawsm.snow_name + '.nc')

        # do the 18hr forecast on each hour if forecast is true
        if myawsm.do_forecast:
            # turn forecast back on in smrf config
            myawsm.config['gridded']['forecast_flag'] = True

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
