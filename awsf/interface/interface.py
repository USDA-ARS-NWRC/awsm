import smrf
from smrf import ipw
from smrf.utils import io
from smrf.utils import utils
import ConfigParser as cfp
from awsf import premodel as pm
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
import faulthandler
import progressbar
from datetime import datetime
import sys
from smrf.utils import io

def smrfMEAS(self):
    '''
    script to automate smrf tasks for multiple runs for real time forecasting
    '''

    # ###################################################################################################
    # ### read in base and write out the specific config file for smrf ##################################
    # ###################################################################################################

    # Write out config file to run smrf
    # make copy and delete only awsf sections
    smrf_cfg = self.config.copy()
    for key in smrf_cfg:
        if key in self.sec_awsf:
            del smrf_cfg[key]
    # set ouput location in smrf config
    smrf_cfg['output']['out_location'] = os.path.join(self.pathd,'smrfOutputs/')
    fp_smrfini = os.path.join(os.path.dirname(self.configFile), self.smrfini)

    self._logger.info('Writing the config file for SMRF')
    io.generate_config(smrf_cfg, fp_smrfini, inicheck=False)

    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    self._logger.info('Running SMRF')
    faulthandler.enable()
    start = datetime.now()

    # with smrf.framework.SMRF(meas_ini_file) as s:
    with smrf.framework.SMRF(fp_smrfini) as s:
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

def smrf_go_wrf(config_file):

    # get wrf config
    wrf_cfg = self.config.copy()
    # replace start time with end time
    wrf_cfg['time']['start_date'] = wrf_cfg['time']['end_date']
    # replace end time with forecast time
    wrf_cfg['time']['end_date'] = wrf_cfg['time']['forecast_date']

    # edit config file to use gridded wrf data
    if 'stations' in wrf_cfg:
        del wrf_cfg['stations']
    if 'csv' in wrf_cfg:
        del wrf_cfg['csv']
    if 'mysql' in wrf_cfg:
        del wrf_cfg['mysql']

    wrf_cfg['gridded']['file'] = self.fp_wrfdata
    wrf_cfg['gridded']['data_type'] = 'wrf'
    wrf_cfg['gridded']['zone_number'] = self.zone_number
    wrf_cfg['gridded']['zone_number'] = self.zone_letter

    # delete AWSF sections
    for key in wrf_cfg:
        if key in self.sec_awsf:
            del smrf_cfg[key]

    ###################################################################################################
    ### serious config edits to run wrf  ##############################################################
    ###################################################################################################
    del wrf_cfg['air_temp']
    wrf_cfg['air_temp']['distribution'] = 'grid'
    wrf_cfg['air_temp']['method'] = 'linear'
    wrf_cfg['air_temp']['detrend'] = True
    wrf_cfg['air_temp']['slope'] = -1
    wrf_cfg['air_temp']['mask'] = True

    del wrf_cfg['vapor_pressure']
    wrf_cfg['vapor_pressure']['distribution'] = 'grid'
    wrf_cfg['vapor_pressure']['method'] = 'linear'
    wrf_cfg['vapor_pressure']['detrend'] = True
    wrf_cfg['vapor_pressure']['slope'] = -1
    wrf_cfg['vapor_pressure']['mask'] = True
    wrf_cfg['vapor_pressure']['tolerance'] = self.cfg['vapor_pressure']['tolerance']
    wrf_cfg['vapor_pressure']['nthreads'] = self.cfg['vapor_pressure']['nthreads']

    del wrf_cfg['wind']
    wrf_cfg['wind']['distribution'] = 'grid'
    wrf_cfg['wind']['method'] = 'linear'
    wrf_cfg['wind']['detrend'] = False

    del wrf_cfg['precip']
    wrf_cfg['precip']['distribution'] = 'grid'
    wrf_cfg['precip']['method'] = 'cubic'
    wrf_cfg['precip']['detrend'] = True
    wrf_cfg['precip']['slope'] = 1
    wrf_cfg['precip']['mask'] = True
    wrf_cfg['precip']['storm_mass_threshold'] = self.config['precip']['storm_mass_threshold']
    wrf_cfg['precip']['time_steps_to_end_storms'] = self.config['precip']['time_steps_to_end_storms']
    wrf_cfg['precip']['nasde_model'] = self.config['precip']['nasde_model']

    # leave albedo

    del wrf_cfg['solar']
    wrf_cfg['solar']['distribution'] = 'grid'
    wrf_cfg['solar']['method'] = 'linear'
    wrf_cfg['solar']['detrend'] = False
    wrf_cfg['solar']['clear_opt_depth'] = self.config['solar']['clear_opt_depth']
    wrf_cfg['solar']['clear_tau'] = self.config['solar']['clear_tau']
    wrf_cfg['solar']['clear_omega'] = self.config['solar']['clear_omega']
    wrf_cfg['solar']['clear_gamma'] = self.config['solar']['clear_gamma']

    del wrf_cfg['thermal']
    wrf_cfg['thermal']['distribution'] = 'grid'
    wrf_cfg['thermal']['method'] = 'linear'
    wrf_cfg['thermal']['detrend'] = False

    # replace output directory with forecast data
    wrf_cfg['output']['out_location'] = os.path.join(self.pathd,'forecast/')
    wrf_cfg['output']['log_file'] = os.path.join(self.pathd,'forecast','wrf_log.txt')
    fp_wrfini = os.path.join(os.path.dirname(self.configFile), self.wrfini)

    # output this config and use to run smrf
    self._logger.info('Writing the config file for SMRF forecast')
    io.generate_config(wrf_cfg, fp_wrfini, inicheck=False)

    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    self._logger.info('Running SMRF forecast with gridded WRF data')
    faulthandler.enable()
    start = datetime.now()

    # with smrf.framework.SMRF(meas_ini_file) as s:
    with smrf.framework.SMRF(fp_wrfini) as s:
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

def run_isnobal(self):

    print("calculating time vars")
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.end_date))
    tt = self.start_date-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = self.nbits

    # create the run directory
    if not os.path.exists(self.pathro):
        os.makedirs(self.pathro)
    if not os.path.exists(self.pathinit):
        os.makedirs(self.pathinit)

    # making initial conditions file
    print("making initial conds img")
    i_out = ipw.IPW()

    # making dem band
    if self.topotype == 'ipw':
        i_dem = ipw.IPW(self.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif self.topotype == 'netcdf':
        dem_file = nc.Dataset(self.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)

    if offset > 0:
        i_in = ipw.IPW(self.prev_mod_file)
        # use given rougness from old init file if given
        if self.roughness_init is not None:
            i.out.new_band(ipw.IPW(self.roughness_init).bands[1].data)
        else:
            self._logger.warning('No roughness given from old init, using value of 0.005 m')
            i_out.new_band(0.005*np.ones((self.ny,self.nx)))
        i_out.new_band(i_in.bands[0].data) # snow depth
        i_out.new_band(i_in.bands[1].data) # snow density
        i_out.new_band(i_in.bands[4].data) # active layer temp
        i_out.new_band(i_in.bands[5].data) # lower layer temp
        i_out.new_band(i_in.bands[6].data) # avgerage snow temp
        i_out.new_band(i_in.bands[8].data) # percent saturation
        i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
        i_out.write(os.path.join(self.pathinit,'init%04d.ipw'%(offset)), nbits)
    else:
        zs0 = np.zeros((self.ny,self.nx))
        if self.roughness_init is not None:
            i_out.new_band(ipw.IPW(self.roughness_init).bands[1].data)
        else:
            self._logger.warning('No roughness given from old init, using value of 0.005 m')
            i_out.new_band(0.005*np.ones((self.ny,self.nx)))
        #             i_out.new_band(i_rl0.bands[0].data)
        i_out.new_band(zs0) # zeros snow cover depth
        i_out.new_band(zs0) # 0density
        i_out.new_band(zs0) # 0ts active
        i_out.new_band(zs0) # 0ts avg
        i_out.new_band(zs0) # 0liquid
        i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
        i_out.write(os.path.join(self.pathinit,'init%04d.ipw'%(offset)), nbits)

    # develop the command to run the model
    print("developing command and running")
    nthreads = int(self.ithreads)

    tt = self.end_date-self.start_date
    tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_output = os.path.join(self.pathr,'sout{}.txt'.format(self.end_date.strftime("%Y%m%d")))
    fp_ppt_desc = self.ppt_desc

    # run iSnobal
    if offset>0:
        if (offset + tmstps) < 1000:
            run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,self.pathinit,offset,fp_ppt_desc,self.fp_mask,self.pathi,fp_output)
            # run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(nthreads,offset,pathinit,offset,self.ppt_desc,pathi,pathr,self.end_date.strftime("%Y%m%d"))
        else:
            run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,tmstps,self.pathinit,offset,fp_ppt_desc,self.fp_mask,self.pathi,fp_output)
    else:
      if tmstps<1000:
          run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,self.pathinit,offset,fp_ppt_desc,self.fp_mask,self.pathi,fp_output)
      else:
          run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,tmstps,self.pathinit,offset,fp_ppt_desc,self.fp_mask,self.pathi,fp_output)

    # change directories, run, and move back
    print run_cmd
    os.chdir(self.pathro)
    os.system(run_cmd)
    os.chdir(cwd)

def run_isnobal_forecast(self):

    print("calculating time vars")
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.forecast_date))
    tt = self.end_date-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = self.nbits

    # create the run directory
    if not os.path.exists(self.path_wrf_ro):
        os.makedirs(self.path_wrf_ro)
    if not os.path.exists(self.path_wrf_init):
        os.makedirs(self.path_wrf_init)

    # making initial conditions file
    print("making initial conds img")
    i_out = ipw.IPW()

    # making dem band
    if self.topotype == 'ipw':
        i_dem = ipw.IPW(self.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif self.topotype == 'netcdf':
        dem_file = nc.Dataset(self.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)

    # find last snow file from smrf run
    d = sorted(glob.glob("%s/snow*"%self.path_wrf_ro), key=os.path.getmtime)
    d.sort(key=lambda f: os.path.splitext(f))
    prev_mod_file = d[-1]

    i_in = ipw.IPW(prev_mod_file)
    # use given rougness from old init file if given
    if self.roughness_init is not None:
        i.out.new_band(ipw.IPW(self.roughness_init).bands[1].data)
    else:
        self._logger.warning('No roughness given from old init, using value of 0.005 m')
        i_out.new_band(0.005*np.ones((self.ny,self.nx)))

    i_out.new_band(i_in.bands[0].data) # snow depth
    i_out.new_band(i_in.bands[1].data) # snow density
    i_out.new_band(i_in.bands[4].data) # active layer temp
    i_out.new_band(i_in.bands[5].data) # lower layer temp
    i_out.new_band(i_in.bands[6].data) # avgerage snow temp
    i_out.new_band(i_in.bands[8].data) # percent saturation
    i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
    i_out.write(os.path.join(self.path_wrf_init,'init%04d.ipw'%(offset)), nbits)

    # develop the command to run the model
    print("developing command and running")
    nthreads = int(self.ithreads)

    tt = self.forecast_date - self.end_date                              # get a time delta to get hours from water year start
    tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()

    fp_output = os.path.join(self.path_wrf_runr,'sout{}.txt'.format(self.forecast_date.strftime("%Y%m%d")))
    fp_ppt_desc = self.wrf_ppt_desc

    # run iSnobal
    if (offset + tmstps) < 1000:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,self.path_wrf_init,offset,fp_ppt_desc,self.fp_mask,self.path_wrf_i,fp_output)
        # run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(nthreads,offset,pathinit,offset,self.ppt_desc,pathi,pathr,self.end_date.strftime("%Y%m%d"))
    else:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -m %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,tmstps,self.path_wrf_init,offset,fp_ppt_desc,self.fp_mask,self.path_wrf_i,fp_output)

    # change directories, run, and move back
    print run_cmd
    os.chdir(self.path_wrf_ro)
    os.system(run_cmd)
    os.chdir(cwd)


def restart_crash_image(self):

    nbits = self.nbits
    nthreads = self.ithreads

    # find water year hour and file paths
    name_crash = 'snow.%04d'%self.restart_hr
    fp_crash = os.path.join(self.pathro,name_crash)
    fp_new_init = os.path.join(self.pathinit,'init%04d.ipw'%self.restart_hr)

    # new ipw image for initializing restart
    print("making new init image")
    i_out = ipw.IPW()

    # read in crash image and old init image
    i_crash = ipw.IPW(fp_crash)
#########################################################

    # making dem band
    if self.topotype == 'ipw':
        i_dem = ipw.IPW(self.fp_dem)
        i_out.new_band(i_dem.bands[0].data)
    elif self.topotype == 'netcdf':
        dem_file = nc.Dataset(self.fp_dem, 'r')
        i_dem = dem_file['dem'][:]
        i_out.new_band(i_dem)

    if self.roughness_init is not None:
        i_out.new_band(ipw.IPW(self.roughness_init).bands[1].data)
    else:
        self._logger.warning('No roughness given from old init, using value of 0.005 m')
        i_out.new_band(0.005*np.ones((self.ny,self.nx)))

    # pull apart crash image and zero out values at index with depths < thresh
    z_s = i_crash.bands[0].data # snow depth
    rho = i_crash.bands[1].data # snow density
    T_s_0 = i_crash.bands[4].data # active layer temp
    T_s_l = i_crash.bands[5].data # lower layer temp
    T_s = i_crash.bands[6].data # avgerage snow temp
    h20_sat = i_crash.bands[8].data # percent saturation

    print ("correcting crash image")

    idz = z_s < self.depth_thresh

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
    i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)

    print('Writing to {}'.format(fp_new_init))
    i_out.write(fp_new_init, nbits)

    print('Running isnobal from restart')
    offset = self.restart_hr
    start_date = self.start_date.replace(tzinfo=self.tzinfo)
    end_date = self.end_date.replace(tzinfo=self.tzinfo)
    # calculate timesteps based on water_day function and offset
    tmstps, tmpwy = utils.water_day(end_date)
    tmstps = int(tmstps*24 - offset)

    # make paths absolute if they are not
    cwd = os.getcwd()
    if os.path.isabs(self.pathr):
        fp_output = os.path.join(self.pathr,'sout{}.txt'.format(self.end_date.strftime("%Y%m%d")))
    else:
        fp_output = os.path.join(os.path.abspath(self.pathr),'sout_restart{}.txt'.format(self.restart_hr))
    if os.path.isabs(self.ppt_desc):
        fp_ppt_desc = self.ppt_desc
    else:
        #self.fp_ppt_desc =  os.path.join(cwd, self.ppt_desc)
        fp_ppt_desc =  os.path.abspath(self.ppt_desc)
    if os.path.isabs(self.pathi):
        pass
    else:
        #self.pathi = os.path.join(cwd,self.pathi)
        self.pathi = os.path.abspath(self.pathi)
    if os.path.isabs(fp_new_init):
        pass
    else:
        #self.pathinit = os.path.join(cwd,self.pathinit)
        fp_new_init = os.path.abspath(fp_new_init)

    if (offset + tmstps) < 1000:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,fp_new_init,fp_ppt_desc,self.pathi,fp_output)
        # run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(nthreads,offset,pathinit,offset,self.ppt_desc,pathi,pathr,self.end_date.strftime("%Y%m%d"))
    else:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,tmstps,fp_new_init,fp_ppt_desc,self.pathi,fp_output)

    print run_cmd
    os.chdir(self.pathro)
    os.system(run_cmd)
    os.chdir(cwd)
