import smrf
from smrf import ipw
from smrf.utils import io
from smrf.utils import utils
import ConfigParser as cfp
from awsm import premodel as pm
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
import faulthandler
import progressbar
from datetime import datetime
import sys
import glob
from smrf.utils import io
import subprocess
import copy

def create_smrf_config(myawsm):
    """
    Create a smrf config for running standard :mod: `smr` run. Use the
    :mod: `awsm` config and remove the sections specific to :mod: `awsm`.
    We do this because these sections will break the config checker utility
    """
    # ########################################################################
    # ### read in base and write out the specific config file for smrf #######
    # ########################################################################

    # Write out config file to run smrf
    # make copy and delete only awsm sections
    # smrf_cfg = copy.deepcopy(myawsm.config)
    smrf_cfg = myawsm.config.copy()
    for key in smrf_cfg:
        if key in myawsm.sec_awsm:
            del smrf_cfg[key]
    # set ouput location in smrf config
    smrf_cfg['output']['out_location'] = os.path.join(myawsm.paths)
    smrf_cfg['system']['temp_dir'] = os.path.join(myawsm.paths,'tmp')
    fp_smrfini = myawsm.smrfini

    myawsm._logger.info('Writing the config file for SMRF')
    io.generate_config(smrf_cfg, fp_smrfini, inicheck=False)

    return fp_smrfini

def smrfMEAS(myawsm):
    '''
    Run standard SMRF run. Calls :mod: `awsm.interface.interface.creae_smrf_config`
    to make :mod: `smrf` config file and runs :mod: `smrf.framework.SMRF` similar
    to standard run_smrf.py script
    '''

    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    if myawsm.end_date > myawsm.start_date:
        myawsm._logger.info('Running SMRF')
        # first create config file to run smrf
        fp_smrfini = create_smrf_config(myawsm)

        faulthandler.enable()
        start = datetime.now()

        # with smrf.framework.SMRF(meas_ini_file) as s:
        with smrf.framework.SMRF(fp_smrfini, myawsm._logger) as s:
            #try:
                # 2. load topo data
                s.loadTopo()

                # 3. initialize the distribution
                s.initializeDistribution()

                # initialize the outputs if desired
                s.initializeOutput()

                #===============================================================================
                # Distribute data
                #===============================================================================

                # 5. load weather data  and station metadata
                s.loadData()

                # 6. distribute
                s.distributeData()

                s._logger.info(datetime.now() - start)

            # except Exception as e:
            #     print 'Error: %s' % e
            #     s._logger.error(e)

def smrf_go_wrf(myawsm):

    # get wrf config
    wrf_cfg = copy.deepcopy(myawsm.config)

    # edit config file to use gridded wrf data
    if 'stations' in wrf_cfg.keys():
        del wrf_cfg['stations']
    if 'csv' in wrf_cfg.keys():
        del wrf_cfg['csv']
    if 'mysql' in wrf_cfg.keys():
        del wrf_cfg['mysql']

    if 'gridded' not in wrf_cfg:
        wrf_cfg['gridded'] = copy.deepcopy(wrf_cfg['time'])
        wrf_cfg['gridded'].clear()
    wrf_cfg['gridded']['file'] = myawsm.fp_wrfdata
    wrf_cfg['gridded']['data_type'] = 'wrf'
    wrf_cfg['gridded']['zone_number'] = int(myawsm.zone_number)
    wrf_cfg['gridded']['zone_letter'] = str(myawsm.zone_letter)

    # delete awsm sections
    for key in wrf_cfg:
        if key in myawsm.sec_awsm:
            del wrf_cfg[key]

    ###################################################################################################
    ### serious config edits to run wrf  ##############################################################
    ###################################################################################################
    # del wrf_cfg['air_temp'][:]
    wrf_cfg['air_temp'].clear()
    wrf_cfg['air_temp']['distribution'] = 'grid'
    wrf_cfg['air_temp']['method'] = 'linear'
    wrf_cfg['air_temp']['detrend'] = True
    wrf_cfg['air_temp']['slope'] = -1
    wrf_cfg['air_temp']['mask'] = True

    # del wrf_cfg['vapor_pressure'][:]
    wrf_cfg['vapor_pressure'].clear()
    wrf_cfg['vapor_pressure']['distribution'] = 'grid'
    wrf_cfg['vapor_pressure']['method'] = 'linear'
    wrf_cfg['vapor_pressure']['detrend'] = True
    wrf_cfg['vapor_pressure']['slope'] = -1
    wrf_cfg['vapor_pressure']['mask'] = True
    wrf_cfg['vapor_pressure']['tolerance'] = myawsm.config['vapor_pressure']['tolerance']
    wrf_cfg['vapor_pressure']['nthreads'] = myawsm.config['vapor_pressure']['nthreads']

    # del wrf_cfg['wind'][:]
    wrf_cfg['wind'].clear()
    wrf_cfg['wind']['distribution'] = 'grid'
    wrf_cfg['wind']['method'] = 'linear'
    wrf_cfg['wind']['detrend'] = False

    # del wrf_cfg['precip'][:]
    wrf_cfg['precip'].clear()
    wrf_cfg['precip']['distribution'] = 'grid'
    wrf_cfg['precip']['method'] = 'cubic_2-D'
    wrf_cfg['precip']['detrend'] = True
    wrf_cfg['precip']['slope'] = 1
    wrf_cfg['precip']['mask'] = True
    wrf_cfg['precip']['storm_mass_threshold'] = myawsm.config['precip']['storm_mass_threshold']
    wrf_cfg['precip']['time_steps_to_end_storms'] = myawsm.config['precip']['time_steps_to_end_storms']
    wrf_cfg['precip']['nasde_model'] = myawsm.config['precip']['nasde_model']

    # leave albedo
    wrf_cfg['albedo'] = myawsm.config['albedo']

    # del wrf_cfg['solar'][:]
    wrf_cfg['solar'].clear()
    wrf_cfg['solar']['distribution'] = 'grid'
    wrf_cfg['solar']['method'] = 'linear'
    wrf_cfg['solar']['detrend'] = False
    wrf_cfg['solar']['clear_opt_depth'] = myawsm.config['solar']['clear_opt_depth']
    wrf_cfg['solar']['clear_tau'] = myawsm.config['solar']['clear_tau']
    wrf_cfg['solar']['clear_omega'] = myawsm.config['solar']['clear_omega']
    wrf_cfg['solar']['clear_gamma'] = myawsm.config['solar']['clear_gamma']

    # del wrf_cfg['thermal']
    # use default settings for thermal
    wrf_cfg['thermal'].clear()
    # wrf_cfg['thermal']['distribution'] = 'grid'
    # wrf_cfg['thermal']['method'] = 'linear'
    # wrf_cfg['thermal']['detrend'] = False

    # replace output directory with forecast data
    wrf_cfg['output']['out_location'] = myawsm.path_wrf_s
    # wrf_cfg['logging']['log_file'] = os.path.join(myawsm.pathd,'forecast','wrf_log.txt')
    wrf_cfg['system']['temp_dir'] = os.path.join(myawsm.path_wrf_s,'tmp/')
    fp_wrfini = myawsm.wrfini

    # output this config and use to run smrf
    myawsm._logger.info('Writing the config file for SMRF forecast')
    io.generate_config(wrf_cfg, fp_wrfini, inicheck=False)

    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    myawsm._logger.info('Running SMRF forecast with gridded WRF data')
    faulthandler.enable()
    start = datetime.now()

    # with smrf.framework.SMRF(meas_ini_file) as s:
    with smrf.framework.SMRF(fp_wrfini, myawsm._logger) as s:
        #try:
            # 2. load topo data
            s.loadTopo()

            # 3. initialize the distribution
            s.initializeDistribution()

            # initialize the outputs if desired
            s.initializeOutput()

            #===============================================================================
            # Distribute data
            #===============================================================================

            # 5. load weather data  and station metadata
            s.loadData()

            # 6. distribute
            s.distributeData()

            s._logger.info(datetime.now() - start)

        # except Exception as e:
        #     print 'Error: %s' % e
        #     s._logger.error(e)

def run_isnobal(myawsm):
    '''
    Run iSnobal from command line. Checks necessary directories, creates
    initialization image and calls iSnobal.
    '''

    myawsm._logger.info('Setting up to run iSnobal')
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(myawsm.end_date))
    tt = myawsm.start_date-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = myawsm.nbits

    # create the run directory
    # if not os.path.exists(myawsm.pathro):
    #     os.makedirs(myawsm.pathro)
    # if not os.path.exists(myawsm.pathinit):
    #     os.makedirs(myawsm.pathinit)

    # making initial conditions file
    myawsm._logger.debug("making initial conds img for iSnobal")
    i_out = ipw.IPW()

    # making dem band
    if myawsm.topotype == 'ipw':
        i_dem = ipw.IPW(myawsm.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif myawsm.topotype == 'netcdf':
        dem_file = nc.Dataset(myawsm.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)

    if myawsm.mask_isnobal:
        i_mask = ipw.IPW(myawsm.fp_mask).bands[0].data
        myawsm._logger.info('Masking init file')
    else:
        i_mask = np.ones((myawsm.ny,myawsm.nx))

    if offset > 0:
        i_in = ipw.IPW(myawsm.prev_mod_file)
        # use given rougness from old init file if given
        if myawsm.roughness_init is not None:
            i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
        else:
            myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')
            i_out.new_band(0.005*np.ones((myawsm.ny,myawsm.nx)))

        i_out.new_band(i_in.bands[0].data*i_mask) # snow depth
        i_out.new_band(i_in.bands[1].data*i_mask) # snow density

        i_out.new_band(i_in.bands[4].data*i_mask) # active layer temp
        i_out.new_band(i_in.bands[5].data*i_mask) # lower layer temp
        i_out.new_band(i_in.bands[6].data*i_mask) # avgerage snow temp

        i_out.new_band(i_in.bands[8].data*i_mask) # percent saturation
        i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv], myawsm.units, myawsm.csys)
        i_out.write(os.path.join(myawsm.pathinit,'init%04d.ipw'%(offset)), nbits)
    else:
        zs0 = np.zeros((myawsm.ny,myawsm.nx))
        if myawsm.roughness_init is not None:
            i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
        else:
            myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')
            i_out.new_band(0.005*np.ones((myawsm.ny,myawsm.nx)))
        #             i_out.new_band(i_rl0.bands[0].data)
        i_out.new_band(zs0) # zeros snow cover depth
        i_out.new_band(zs0) # 0density
        i_out.new_band(zs0) # 0ts active
        i_out.new_band(zs0) # 0ts avg
        i_out.new_band(zs0) # 0liquid
        i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv], myawsm.units, myawsm.csys)
        i_out.write(os.path.join(myawsm.pathinit,'init%04d.ipw'%(offset)), nbits)

    # develop the command to run the model
    myawsm._logger.debug("Developing command and running iSnobal")
    nthreads = int(myawsm.ithreads)

    tt = myawsm.end_date-myawsm.start_date
    tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_output = os.path.join(myawsm.pathrr,'sout{}.txt'.format(myawsm.end_date.strftime("%Y%m%d")))
    fp_ppt_desc = myawsm.ppt_desc

    # check length of ppt_desc file to see if there has been precip
    is_ppt = os.stat(fp_ppt_desc).st_size
    if is_ppt == 0:
        myawsm._logger.warning('Running iSnobal with no precip')

    # run iSnobal
    if myawsm.mask_isnobal == True:
        if offset>0:
            if is_ppt > 0:
                if (offset + tmstps) < 1000:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,myawsm.pathinit,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,tmstps,myawsm.pathinit,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
            else:
                if (offset + tmstps) < 1000:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,myawsm.pathinit,offset,myawsm.fp_mask,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,tmstps,myawsm.pathinit,offset,myawsm.fp_mask,myawsm.pathi)
        else:
            if is_ppt > 0:
                if tmstps < 1000:
                    run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,myawsm.pathinit,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,tmstps,myawsm.pathinit,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
            else:
                if tmstps < 1000:
                    run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,myawsm.pathinit,offset,myawsm.fp_mask,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,tmstps,myawsm.pathinit,offset,myawsm.fp_mask,myawsm.pathi)
    else:
        if offset>0:
            if is_ppt > 0:
                if (offset + tmstps) < 1000:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,myawsm.pathinit,offset,fp_ppt_desc,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,tmstps,myawsm.pathinit,offset,fp_ppt_desc,myawsm.pathi)
            else:
                if (offset + tmstps) < 1000:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,myawsm.pathinit,offset,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,offset,tmstps,myawsm.pathinit,offset,myawsm.pathi)
        else:
            if is_ppt > 0:
                if tmstps < 1000:
                    run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,myawsm.pathinit,offset,fp_ppt_desc,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,tmstps,myawsm.pathinit,offset,fp_ppt_desc,myawsm.pathi)
            else:
                if tmstps < 1000:
                    run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,myawsm.pathinit,offset,myawsm.pathi)
                else:
                    run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow"%(nthreads,tmstps,myawsm.pathinit,offset,myawsm.pathi)


    # change directories, run, and move back
    myawsm._logger.debug("Running {}".format(run_cmd))
    os.chdir(myawsm.pathro)
    # call iSnobal
    p = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        line = p.stdout.readline()
        myawsm._logger.info(line)
        if not line:
            break

    os.chdir(cwd)

def run_isnobal_forecast(myawsm):

    myawsm._logger.info("Getting ready to run iSnobal for WRF forecast!")
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(myawsm.start_date))
    tt = myawsm.end_date-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = myawsm.nbits

    # create the run directory
    if not os.path.exists(myawsm.path_wrf_ro):
        os.makedirs(myawsm.path_wrf_ro)
    if not os.path.exists(myawsm.path_wrf_init):
        os.makedirs(myawsm.path_wrf_init)

    # making initial conditions file
    myawsm._logger.info("Making initial conds image")
    i_out = ipw.IPW()

    # making dem band
    if myawsm.topotype == 'ipw':
        i_dem = ipw.IPW(myawsm.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif myawsm.topotype == 'netcdf':
        dem_file = nc.Dataset(myawsm.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)


    i_in = ipw.IPW(myawsm.prev_mod_file)
    # use given rougness from old init file if given
    if myawsm.roughness_init is not None:
        i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
    else:
        myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')
        i_out.new_band(0.005*np.ones((myawsm.ny,myawsm.nx)))

    i_out.new_band(i_in.bands[0].data) # snow depth
    i_out.new_band(i_in.bands[1].data) # snow density
    i_out.new_band(i_in.bands[4].data) # active layer temp
    i_out.new_band(i_in.bands[5].data) # lower layer temp
    i_out.new_band(i_in.bands[6].data) # avgerage snow temp
    i_out.new_band(i_in.bands[8].data) # percent saturation
    i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv], myawsm.units, myawsm.csys)
    i_out.write(os.path.join(myawsm.path_wrf_init,'init%04d.ipw'%(offset)), nbits)

    # develop the command to run the model
    myawsm._logger.info("Developing command and running")
    nthreads = int(myawsm.ithreads)

    tt = myawsm.end_date - myawsm.start_date                              # get a time delta to get hours from water year start
    tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_output = os.path.join(myawsm.path_wrf_run,'sout{}.txt'.format(myawsm.end_date.strftime("%Y%m%d")))
    fp_ppt_desc = myawsm.wrf_ppt_desc

    # check length of ppt_desc file to see if there has been precip
    is_ppt = os.stat(fp_ppt_desc).st_size
    if is_ppt == 0:
        myawsm._logger.warning('Running iSnobal with no precip')

    # run iSnobal
    if myawsm.mask_isnobal == True:
        if is_ppt > 0:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,myawsm.path_wrf_init,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.path_wrf_i)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,tmstps,myawsm.path_wrf_init,offset,fp_ppt_desc,myawsm.fp_mask,myawsm.path_wrf_i)
        else:
            myawsm._logger.warning('Time frame has no precip!')
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,myawsm.path_wrf_init,offset,myawsm.fp_mask,myawsm.path_wrf_i)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -m %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,tmstps,myawsm.path_wrf_init,offset,myawsm.fp_mask,myawsm.path_wrf_i)
    else:
        if is_ppt > 0:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,myawsm.path_wrf_init,offset,fp_ppt_desc,myawsm.path_wrf_i)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,tmstps,myawsm.path_wrf_init,offset,fp_ppt_desc,myawsm.path_wrf_i)
        else:
            myawsm._logger.warning('Time frame has no precip!')
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,myawsm.path_wrf_init,offset,myawsm.path_wrf_i)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -d 0.15 -i %s/in -O 24 -e em -s snow  2>&1"%(nthreads,offset,tmstps,myawsm.path_wrf_init,offset,myawsm.path_wrf_i)


    # change directories, run, and move back
    myawsm._logger.debug("Running {}".format(run_cmd))

    os.chdir(myawsm.path_wrf_ro)
    p = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

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
    '''
    nbits = myawsm.nbits
    nthreads = myawsm.ithreads

    # find water year hour and file paths
    name_crash = 'snow.%04d'%myawsm.restart_hr
    fp_crash = os.path.join(myawsm.pathro,name_crash)
    fp_new_init = os.path.join(myawsm.pathinit,'init%04d.ipw'%myawsm.restart_hr)

    # new ipw image for initializing restart
    myawsm._logger.info("making new init image")
    i_out = ipw.IPW()

    # read in crash image and old init image
    i_crash = ipw.IPW(fp_crash)
    #########################################################

    # making dem band
    if myawsm.topotype == 'ipw':
        i_dem = ipw.IPW(myawsm.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif myawsm.topotype == 'netcdf':
        dem_file = nc.Dataset(myawsm.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)

    if myawsm.roughness_init is not None:
        i_out.new_band(ipw.IPW(myawsm.roughness_init).bands[1].data)
    else:
        myawsm._logger.warning('No roughness given from old init, using value of 0.005 m')
        i_out.new_band(0.005*np.ones((myawsm.ny,myawsm.nx)))

    # pull apart crash image and zero out values at index with depths < thresh
    z_s = i_crash.bands[0].data # snow depth
    rho = i_crash.bands[1].data # snow density
    T_s_0 = i_crash.bands[4].data # active layer temp
    T_s_l = i_crash.bands[5].data # lower layer temp
    T_s = i_crash.bands[6].data # avgerage snow temp
    h20_sat = i_crash.bands[8].data # percent saturation

    myawsm._logger.info("correcting crash image, deleting depths under {} [m]".format())

    # find pixels that need reset
    idz = z_s < myawsm.depth_thresh

    # find number of pixels reset
    num_pix = len(np.where(idz == True))

    myawsm._logger.warning('Zeroing depth in {} pixels!'.format(num_pix))

    z_s[idz] = 0.0
    rho[idz] = 0.0
    #m_s[idz] = 0.0
    #h20[idz] = 0.0
    T_s_0[idz] = -75.0
    T_s_l[idz] = -75.0
    T_s[idz] = -75.0
    #z_s_l[idz] = 0.0
    h20_sat[idz] = 0.0

    # fill in init image
    i_out.new_band(z_s)
    i_out.new_band(rho)
    i_out.new_band(T_s_0)
    i_out.new_band(T_s_l)
    i_out.new_band(T_s)
    i_out.new_band(h20_sat)
    i_out.add_geo_hdr([myawsm.u, myawsm.v], [myawsm.du, myawsm.dv], myawsm.units, myawsm.csys)

    myawsm._logger.info('Writing to {}'.format(fp_new_init))
    i_out.write(fp_new_init, nbits)

    myawsm._logger.info('Running isnobal from restart')
    offset = myawsm.restart_hr+1
    start_date = myawsm.start_date.replace(tzinfo=myawsm.tzinfo)
    end_date = myawsm.end_date.replace(tzinfo=myawsm.tzinfo)
    # calculate timesteps based on water_day function and offset
    tmstps, tmpwy = utils.water_day(end_date)
    tmstps = int(tmstps*24 - offset)

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_output = os.path.join(myawsm.pathrr,'sout_restart{}.txt'.format(myawsm.restart_hr))

    fp_ppt_desc = myawsm.ppt_desc

    # check if there was precip
    is_ppt = os.stat(fp_ppt_desc).st_size
    if is_ppt == 0:
        myawsm._logger.warning('Running iSnobal with no precip')

    # give mask if masking set to treu
    if myawsm.mask_isnobal == True:
        if is_ppt > 0:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,fp_new_init,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,tmstps,fp_new_init,fp_ppt_desc,myawsm.fp_mask,myawsm.pathi)
        else:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,fp_new_init,myawsm.fp_mask,myawsm.pathi)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,tmstps,fp_new_init,myawsm.fp_mask,myawsm.pathi)
    else:
        if is_ppt > 0:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,fp_new_init,fp_ppt_desc,myawsm.pathi)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,tmstps,fp_new_init,fp_ppt_desc,myawsm.pathi)
        else:
            if (offset + tmstps) < 1000:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,fp_new_init,myawsm.pathi)
            else:
                run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -d 0.15 -i %s/in -O 24 -e em -s snow 2>&1"%(nthreads,offset,tmstps,fp_new_init,myawsm.pathi)

    # change directories, run, and move back
    myawsm._logger.debug("Running {}".format(run_cmd))

    os.chdir(myawsm.pathro)
    p = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        line = p.stdout.readline()
        myawsm._logger.info(line)
        if not line:
            break

    os.chdir(cwd)
