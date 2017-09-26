import smrf
from smrf import ipw
from smrf.utils import io
from smrf.utils import water_day
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

    print("writing the config file for smrf (meas)\n")
    io.generate_config(smrf_cfg, fp_smrfini, inicheck=False)

    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    print("running smrf (meas)\n")
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
      #             i_out.new_band(i_rl0.bands[0].data)
    #   i_out.new_band(0.005*np.ones((self.ny,self.nx)))
      i_out.new_band(0.005*np.ones_like(i_dem))
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
      i_out.new_band(0.005*np.ones((self.ny,self.nx)))
      #             i_out.new_band(i_rl0.bands[0].data)
      i_out.new_band(zs0) # zeros snow cover depth
      i_out.new_band(zs0) # 0density
      i_out.new_band(zs0) # 0ts active
      i_out.new_band(zs0) # 0ts avg
      i_out.new_band(zs0) # 0liquid
      i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
      #i_out.write('%sinit%04d.ipw'%(self.pathinit,offset), nbits)
      i_out.write(os.path.join(self.pathinit,'init%04d.ipw'%(offset)), nbits)

    # develop the command to run the model
    print("developing command and running")
    nthreads = int(self.ithreads)
    if self.forecast_flag == 1:
      tt = self.ft-self.start_date                              # get a time delta to get hours from water year start
      tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file
    else:
      tt = self.end_date-self.start_date
      tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file

    # make paths absolute if they are not
    cwd = os.getcwd()
    if os.path.isabs(self.pathr):
        self.fp_output = os.path.join(self.pathr,'sout{}.txt'.format(self.end_date.strftime("%Y%m%d")))
    else:
        self.fp_output = os.path.join(os.path.abspath(self.pathr),'sout{}.txt'.format(self.end_date.strftime("%Y%m%d")))
    if os.path.isabs(self.ppt_desc):
        self.fp_ppt_desc = self.ppt_desc
    else:
        #self.fp_ppt_desc =  os.path.join(cwd, self.ppt_desc)
        self.fp_ppt_desc =  os.path.abspath(self.ppt_desc)
    if os.path.isabs(self.pathi):
        pass
    else:
        #self.pathi = os.path.join(cwd,self.pathi)
        self.pathi = os.path.abspath(self.pathi)
    if os.path.isabs(self.pathinit):
        pass
    else:
        #self.pathinit = os.path.join(cwd,self.pathinit)
        self.pathinit = os.path.abspath(self.pathinit)

    # run iSnobal
    if offset>0:
        if (offset + tmstps) < 1000:
            run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,self.pathinit,offset,self.fp_ppt_desc,self.pathi,self.fp_output)
            # run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(nthreads,offset,pathinit,offset,self.ppt_desc,pathi,pathr,self.end_date.strftime("%Y%m%d"))
        else:
            run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,tmstps,self.pathinit,offset,self.fp_ppt_desc,self.pathi,self.fp_output)
    else:
      if tmstps<1000:
          run_cmd = "time isnobal -v -P %d -t 60 -n 1001 -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,self.pathinit,offset,self.fp_ppt_desc,self.pathi,self.fp_output)
      else:
          run_cmd = "time isnobal -v -P %d -t 60 -n %s -I %s/init%04d.ipw -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,tmstps,self.pathinit,offset,self.fp_ppt_desc,self.pathi,self.fp_output)

    # change directories, run, and move back
    print run_cmd
    os.chdir(self.pathro)
    os.system(run_cmd)
    os.chdir(cwd)


def restart_crash_image(self):

    nbits = self.nbits

    # find water year hour and file paths
    name_crash = 'snow.%04d'%self.restart_hr
    fp_crash = os.path.join(self.pathro,name_crash)
    fp_new_init = os.path.join(self.pathinit,'init%04d.ipw'.%self.restart_hr)

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

    i_out.new_band(0.005*np.ones_like(i_dem))

    # pull apart crash image and zero out values at index with depths < thresh
    z_s = i_crash.bands[0].data # snow depth
    rho = i_crash.bands[1].data # snow density
    m_s = i_crash.bands[2].data
    h20 = i_crash.bands[3].data
    T_s_0 = i_crash.bands[4].data # active layer temp
    T_s_l = i_crash.bands[5].data # lower layer temp
    T_s = i_crash.bands[6].data # avgerage snow temp
    z_s_l = i_crash.bands[7].data
    h20_sat = i_crash.bands[8].data # percent saturation

    print ("correcting crash image")

    idz = z_s < self.depth_thresh

    z_s[idz] = 0.0
    rho[idz] = 0.0
    m_s[idz] = 0.0
    h20[idz] = 0.0
    T_s_0[idz] = -75.0
    T_s_l[idz] = -75.0
    T_s[idz] = -75.0
    z_s_l[idz] = 0.0
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
    tmsteps = water_day(self.start_date) - offset

    if (offset + tmstps) < 1000:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,fp_new_init,self.fp_ppt_desc,self.pathi,self.fp_output)
        # run_cmd = "time isnobal -v -P %d -r %s -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(nthreads,offset,pathinit,offset,self.ppt_desc,pathi,pathr,self.end_date.strftime("%Y%m%d"))
    else:
        run_cmd = "time isnobal -v -P %d -r %s -t 60 -n %s -I %s -p %s -d 0.15 -i %s/in -O 24 -e em -s snow > %s 2>&1"%(nthreads,offset,tmstps,fp_new_init,self.fp_ppt_desc,self.pathi,self.fp_output)
