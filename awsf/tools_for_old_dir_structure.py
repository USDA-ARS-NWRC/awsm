'''
Created on May 2, 2017

@author: pkormos
'''
import os
import netCDF4 as nc
from netCDF4 import netcdftime
import ConfigParser as cfp
import pandas as pd
from isnobal import ipw
from PBR_tools import premodel as pm
import numpy as np

def var_total(var,dir,config_file,wy):
    '''
    function to get a water year total for a variable
    '''
        #     config_file = '/Volumes/data/snowdrift/BRB/pkormos_workspace/scripts/config_PBR2017.txt'
#     IPW = "/Users/pkormos/ipw/bin" # this needs changed
#     PATH = os.environ.copy()["PATH"] + ':/usr/local/bin:' + IPW # this also needs changed

    dir = '/Volumes/data/snowdrift/BRB/BRB-wy16/data/'
    var = 'precip'
    wy=2016
    
    # read data from config file
    tt = cfp.ConfigParser() 
    tt.read(config_file)
    cfg = dict(tt._sections)
    et = pd.to_datetime(cfg['TIMES']['etime'])
    msk_pa = cfg['PATHS']['pathtp']
    baseini = cfg['PATHS']['anyini']
    
    tt = cfp.ConfigParser()
    tt.read(baseini)
    cfg0 = dict(tt._sections)
    msk_fn = cfg0['TOPO']['mask'] 

    # bring in the mask data to get sub_basin number later
    msk_file = msk_pa + msk_fn
    i = ipw.IPW(msk_file) #  image
    msk = i.bands[0].data # find h20sat
    msk = msk.nonzero() # make an mask array
    ppt_tot = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%(wy-1),'%s-9-30 23:00'%wy), freq='h'),columns=['ppt_mm'])  # make dataframe for basin swi

    rundirs = os.listdir(dir)                               # list subdirectories
    rundirs = [s for s in rundirs if "data" in s]           # keep only the data directories
    rundirs = [s for s in rundirs if "forecast" not in s]   # keep only the data directories
    rundirs = [s for s in rundirs if "base" not in s]   # keep only the data directories
    
    rtime =  [i.split('data.', 1)[1] for i in rundirs]# split into dates
    rtime = map(int,rtime)
    dir_order = sorted(range(len(rtime)), key=lambda k: rtime[k]) # get order of run dirs based on date stamp
    for n,m in enumerate(dir_order):
        print('%s of %s files'%(n+1,np.size(dir_order)))
        
        nc_var = nc.Dataset('%s%s/smrf_outputs/%s.nc'%(dir,rundirs[m],var), 'r') # open netcdf file 
        tvar = nc_var.variables['time']
        nctvec = []
        nctvec.append(nc.num2date(tvar[:],units = tvar.units,calendar = tvar.calendar))
        nctvec = nctvec[0]
        var0 = nc_var.variables[var]
        for t in range(np.size(nctvec)):
            tt = var0[t,:,:]
            ppt_tot.ix[nctvec[t],'ppt_mm'] = tt[msk].mean()
        nc_var.close()
    ppt_tot.plot()
    ppt_tot.to_csv('~/boise_ppt_wy16.csv')
        
        