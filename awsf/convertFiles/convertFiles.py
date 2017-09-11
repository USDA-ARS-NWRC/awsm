import smrf
from smrf import ipw
import ConfigParser as cfp
from awsf import premodel as pm
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
import faulthandler
import progressbar

def nc2ipw_mea(self):
    ###################################################################################################
    ### make .ipw input files from netCDF files #######################################################
    ###################################################################################################
    '''
    might split this function into one for precip and one for other forcings later
    '''
    print("making the ipw files from NetCDF files (meas)")

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
    in_pathp = '%sdata/data/ppt_4b'%self.path00
    self.ppt_desc = '%sdata/data/ppt_desc%s.txt'%(self.path00,self.et.strftime("%Y%m%d"))
    f = open(self.ppt_desc,'w')


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
    #timeStep = np.arange(0,N)        # timesteps loop through
    timeStep = np.arange(offset,N+offset)        # timesteps loop through
    pbar = progressbar.ProgressBar(max_value=len(timeStep)).start()
    j = 0
    for idxt,t in enumerate(timeStep):

      trad_step = th_file.variables[th_var][idxt,:]
      ta_step = ta_file.variables[ta_var][idxt,:]
      ea_step = ea_file.variables[ea_var][idxt,:]
      wind_step = wind_file.variables[wind_var][idxt,:]
      sn_step = sn_file.variables[sn_var][idxt,:]
      mp_step = mp_file.variables[mp_var][idxt,:]
      # tg_step = np.ones_like(mp_step)*(-2.5) # ground temp

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
          ps_step = ps_file.variables[ps_var][idxt,:]
          rho_step = rho_file.variables[rho_var][idxt,:]
          tp_step = tp_file.variables[tp_var][idxt,:]
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
