import smrf
from smrf import ipw
import ConfigParser as cfp
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
import faulthandler
import progressbar

def smrfMEAS(self):
    '''
    script to automate smrf tasks for multiple runs for real time forecasting
    '''



    # ###################################################################################################
    # ### read in base and write out the specific config file for smrf ##################################
    # ###################################################################################################
    print "writing the config file for smrf (meas)"
    meas_ini_file = "%s_%ssmrf.ini"%(self.pathws, self.et.strftime("%Y%m%d"))

    cfg0 = cfp.RawConfigParser()
    cfg0.read(self.anyini)
    tt = cfg0.get('TOPO','dem')
    cfg0.set('TOPO','dem','%s%s'%(self.pathtp,tt))
    tt = cfg0.get('TOPO','veg_type')
    cfg0.set('TOPO','veg_type','%s%s'%(self.pathtp,tt))
    tt = cfg0.get('TOPO','veg_height')
    cfg0.set('TOPO','veg_height','%s%s'%(self.pathtp,tt))
    tt = cfg0.get('TOPO','veg_k')
    cfg0.set('TOPO','veg_k','%s%s'%(self.pathtp,tt))
    tt = cfg0.get('TOPO','veg_tau')
    cfg0.set('TOPO','veg_tau','%s%s'%(self.pathtp,tt))
    cfg0.set('TiMe','start_date',self.st.strftime('%Y-%m-%d %H:%M:%S'))
    cfg0.set('TiMe','end_date',self.et.strftime('%Y-%m-%d %H:%M:%S'))
    cfg0.set('TiMe','tmz',self.tmz)
    cfg0.set('wind','maxus_netcdf','%smaxus.nc'%self.pathtp)
    cfg0.set('output','out_location',self.paths)
    cfg0.set('logging','log_file','%s/out%s.log'%(self.paths,self.et.strftime("%Y%m%d")))
    cfg0.set('system','tmp_dir',self.tmpdir)

    with open(meas_ini_file, 'wb') as configfile:
      cfg0.write(configfile)


    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    print "running smrf (meas)"
    faulthandler.enable()
    # 1. initialize
    s = smrf.framework.SMRF(meas_ini_file)
    # 2. load topo data
    s.loadTopo()
    # 3. initialize the distribution
    s.initializeDistribution()
    # initialize the outputs if desired
    s.initializeOutput()
    # 5. load weather data  and station metadata
    s.loadData()
    # 6. distribute
    s.distributeData()

def run_isnobal(self):

    cfg0 = cfp.RawConfigParser()        # initiate config parser
    cfg0.read(self.anyini)              # read in config file
    dem0 = cfg0.get('TOPO','dem')  # pull in location of the dem

    print "calculating time vars"
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.et))
    tt = self.st-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = 16

    pathi =    '%sdata/data/input/'%self.path00
    pathinit = '%sdata/data/init/'%self.path00
    pathr =    '%sruns/run%s'%(self.path00,self.et.strftime("%Y%m%d"))
    pathro =   '%s/output'%pathr
    print(pathr)
    print(pathro)

    # create the run directory
    if not os.path.exists(pathro):
      print "making dirs"
      os.makedirs(pathro)
      os.makedirs(pathinit)

    # make the initial conditions file (init)
    print "making initial conds img"
    #         rl0 = '%sz0.ipw'%self.pathtp
    i_dem = ipw.IPW('%s%s'%(self.pathtp,dem0))
    #         i_rl0 = ipw.IPW(rl0)
    if offset > 0:
      i_in = ipw.IPW(self.prev_mod_file)
      i_out = ipw.IPW()
      i_out.new_band(i_dem.bands[0].data)
      #             i_out.new_band(i_rl0.bands[0].data)
      i_out.new_band(0.005*np.ones((self.ny,self.nx)))
      i_out.new_band(i_in.bands[0].data) # snow depth
      i_out.new_band(i_in.bands[1].data) # snow density
      i_out.new_band(i_in.bands[4].data) # active layer temp
      i_out.new_band(i_in.bands[5].data) # lower layer temp
      i_out.new_band(i_in.bands[6].data) # avgerage snow temp
      i_out.new_band(i_in.bands[8].data) # percent saturation
      i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
      i_out.write('%sinit%04d.ipw'%(pathinit,offset), nbits)
    else:
      zs0 = np.zeros((self.ny,self.nx))
      i_out = ipw.IPW()
      i_out.new_band(i_dem.bands[0].data)
      i_out.new_band(0.005*np.ones((self.ny,self.nx)))
      #             i_out.new_band(i_rl0.bands[0].data)
      i_out.new_band(zs0) # zeros snow cover depth
      i_out.new_band(zs0) # 0density
      i_out.new_band(zs0) # 0ts active
      i_out.new_band(zs0) # 0ts avg
      i_out.new_band(zs0) # 0liquid
      i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
      i_out.write('%sinit%04d.ipw'%(pathinit,offset), nbits)

    # develop the command to run the model
    print("developing command and running")
    if self.forecast_flag == 1:
      tt = self.ft-self.st                              # get a time delta to get hours from water year start
      tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file
    else:
      tt = self.et-self.st
      tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file
    if offset>0:
      run_cmd = "time isnobal -v -P 20 -r %s -t 60 -n %s -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(offset,tmstps,pathinit,offset,self.ppt_desc_file,pathi,pathr,self.et.strftime("%Y%m%d"))
    else:
      if tmstps<1000:
          run_cmd = "time isnobal -v -P 20 -t 60 -n 1001 -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(pathinit,offset,self.ppt_desc_file,pathi,pathr,self.et.strftime("%Y%m%d"))
      else:
          run_cmd = "time isnobal -v -P 20 -t 60 -n %s -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(tmstps,pathinit,offset,self.ppt_desc_file,pathi,pathr,self.et.strftime("%Y%m%d"))

    os.chdir(pathro)
    os.system(run_cmd)
