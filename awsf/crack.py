'''
Created on Apr 7, 2017

@author: pkormos
'''

import smrf
from smrf import ipw
from PBR_tools import premodel as pm
import ConfigParser as cfp
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
import faulthandler
import progressbar


class pour(object):
    '''
    Args:
        configFile (str):  path to configuration file.

    Returns:
        PBR class instance.

    Attributes:
        start_date: start_date read from configFile
        end_date: end_date read from configFile
        date_time: Numpy array of date_time objects between start_date and end_date
        config: Configuration file read in as dictionary
        distribute: Dictionary the contains all the desired variables to distribute and is initialized in :func:`~smrf.framework.model_framework.initializeDistirbution`

    '''


    def __init__(self, config_file):
        '''
        Read PBR config file, make variables available to all funtions 
        '''
#         config_file = '/Users/pkormos/src/PBR_tools/config_PBR.txt'
        
        # read the config file and store
        if not os.path.isfile(config_file):
            raise Exception('Configuration file does not exist --> %s' % config_file)
        
        tt = cfp.ConfigParser() 
        tt.read(config_file)
        cfg = dict(tt._sections)
        self.path00 = cfg['PATHS']['path00']
        self.pathws = cfg['PATHS']['pathws']
        self.pathtp = cfg['PATHS']['pathtp']
        self.tmpdir = cfg['PATHS']['tmpdir']
        self.anyini = cfg['PATHS']['anyini']
        self.st = pd.to_datetime(cfg['TIMES']['stime'])
        self.et = pd.to_datetime(cfg['TIMES']['etime'])
        self.tmz = cfg['TIMES']['time_zone']
        self.u  = int(cfg['GRID']['u'])
        self.v  = int(cfg['GRID']['v'])
        self.du  = int(cfg['GRID']['du'])
        self.dv  = int(cfg['GRID']['dv'])
        self.units = cfg['GRID']['units']
        self.csys = cfg['GRID']['csys']
        self.nx = int(cfg['GRID']['nx'])
        self.ny = int(cfg['GRID']['ny'])
        if tt.has_option('FILES','ppt_desc_file'):
            self.ppt_desc_file = cfg['FILES']['ppt_desc_file']
        else:
            self.ppt_desc = '%sdata/data/ppt_desc%s.txt'%(self.path00,self.et.strftime("%Y%m%d"))
        self.anyini = cfg['PATHS']['anyini']
        self.forecast_flag = 0
        if tt.has_option('TIMES', 'fetime'):
            self.forecast_flag = 1
            self.ft = pd.to_datetime(cfg['TIMES']['fetime'])
        if tt.has_option('FILES', 'prev_mod_file'):
            self.prev_mod_file = cfg['FILES']['prev_mod_file']
            
        
        # rigid directory work
        if not os.path.exists(self.path00):  # if the working path specified in the config file does not exist
            y_n = 'a'                        # set a funny value to y_n
            while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.path00)
            if y_n == 'n':
                print('Please fix the base directory (path00) in your config file.')
            elif y_n =='y':
                os.makedirs('%sdata/data/smrfOutputs/'%self.path00)
                os.makedirs('%sdata/data/input/'%self.path00)
                os.makedirs('%sdata/data/ppt_4b/'%self.path00)
                os.makedirs('%sdata/forecast/'%self.path00)
                os.makedirs('%sruns/'%self.path00)
        
        self.paths = '%sdata/data/smrfOutputs/'%self.path00
            
    def smrfMEAS(self):
        '''
        script to automate smrf tasks for multiple runs for real time forecasting
        '''
        
        
        
        # ###################################################################################################
        # ### read in base and write out the specific config file for smrf ##################################
        # ###################################################################################################
        print "writing the config file for smrf (meas)"
        meas_ini_file = "%sbrb%ssmrf.ini"%(self.pathws, self.et.strftime("%Y%m%d"))
        
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
    
    def nc2ipw_mea(self):
        ###################################################################################################
        ### make .ipw input files from netCDF files #######################################################
        ###################################################################################################
        '''
        might split this function into one for precip and one for other forcings later
        '''
        print "making the ipw files from NetCDF files (meas)"
                
        wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.et))
        tt = self.st-wyh
        offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
        nbits = 16
        
        # File paths
        th = '%sthermal.nc'%self.paths
        th_var = 'thermal'
        ta = '%sair_temp.nc'%self.paths
        ta_var = 'air_temp'
        ea = '%svapor_pressure.nc'%self.paths
        ea_var = 'vapor_pressure'
        wind = '%swind_speed.nc'%self.paths
        wind_var = 'wind_speed'
        tg_step = -2.5*np.ones((self.ny,self.nx))
        sn = '%snet_solar.nc'%self.paths
        sn_var = 'net_solar'
        in_path = '%sdata/data/input/'%self.path00
        mp = '%sprecip.nc'%self.paths
        mp_var = 'precip'
        ps = '%spercent_snow.nc'%self.paths
        ps_var = 'percent_snow'
        rho = '%ssnow_density.nc'%self.paths
        rho_var = 'snow_density'
        tp = '%sdew_point.nc'%self.paths
        tp_var = 'dew_point'
        in_pathp = '%sdata/data/ppt_4b/'%self.path00
        self.ppt_desc = '%sdata/data/ppt_desc%s.txt'%(self.path00,self.et.strftime("%Y%m%d"))
        f = open(ppt_desc,'w')
    
    
        th_file = nc.Dataset(th, 'r')
        ta_file = nc.Dataset(ta, 'r')
        ea_file = nc.Dataset(ea, 'r')
        wind_file = nc.Dataset(wind, 'r')
        sn_file = nc.Dataset(sn, 'r')
        mp_file = nc.Dataset(mp, 'r')
        ps_file = nc.Dataset(ps, 'r')
        rho_file = nc.Dataset(rho, 'r')
        tp_file = nc.Dataset(tp, 'r')
    
        N = th_file.variables[th_var].shape[0]
        timeStep = np.arange(offset,N)        # timesteps loop through
        pbar = progressbar.ProgressBar(max_value=len(timeStep)).start()
        j = 0
        for t in timeStep:
            
            trad_step = th_file.variables[th_var][t,:]
            ta_step = ta_file.variables[ta_var][t,:]
            ea_step = ea_file.variables[ea_var][t,:]
            wind_step = wind_file.variables[wind_var][t,:]
            sn_step = sn_file.variables[sn_var][t,:]
            mp_step = mp_file.variables[mp_var][t,:]
        
            in_step = '%s/in.%04i' % (in_path, t)
            
            i = smrf.ipw.IPW()
            i.new_band(trad_step)
            i.new_band(ta_step)
            i.new_band(ea_step)
            i.new_band(wind_step)
            i.new_band(tg_step)
                    
            # add solar if the sun is up
            if np.sum(sn_step) > 0:
                i.new_band(sn_step)
                
            i.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)        
            i.write(in_step, nbits)
            
            # only output if precip
            if np.sum(mp_step) > 0:
                ps_step = ps_file.variables[ps_var][t,:]
                rho_step = rho_file.variables[rho_var][t,:]
                tp_step = tp_file.variables[tp_var][t,:]
                in_stepp = os.path.join('%s/ppt.4b_%04i' % (in_pathp, t))
                i = smrf.ipw.IPW()
                i.new_band(mp_step)
                i.new_band(ps_step)
                i.new_band(rho_step)
                i.new_band(tp_step)
                i.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)        
                i.write(in_stepp, nbits)
                f.write('%i %s\n' % (t, in_stepp))
    
            j += 1
            pbar.update(j)
        th_file.close()
        ta_file.close()
        ea_file.close()
        wind_file.close()
        sn_file.close()
        mp_file.close()
        ps_file.close()
        rho_file.close()
        tp_file.close()
        f.close()
        pbar.finish()
    
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
        

        
    