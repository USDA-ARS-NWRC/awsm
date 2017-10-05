import smrf
from smrf import ipw
from smrf.utils import utils
import ConfigParser as cfp
from awsf import premodel as pm
import os
import pandas as pd
import numpy as np
import netCDF4 as nc
#import faulthandler
import progressbar
import glob

def nc2ipw_mea(self, runtype):
    '''
    Function to create iSnobal forcing and precip images from smrf ouputs
    '''
    ###################################################################################################
    ### make .ipw input files from netCDF files #######################################################
    ###################################################################################################
    print("making the ipw files from NetCDF files for {}".format(runtype))

    # check if this is forecast or not
    if runtype == 'smrf':
        start_date = self.start_date.replace(tzinfo=self.tzinfo)
    elif runtype == 'wrf':
        start_date = self.end_date.replace(tzinfo=self.tzinfo)
    else:
        self._logger.error('Wrong run type given to nc2ipw. \
                            not smrf or wrf')

    tmpday, tmpwy = utils.water_day(start_date)
    # find start of wy
    wyh = pd.to_datetime('{}-10-01'.format(tmpwy-1))

    if runtype == 'smrf':
        tt = self.start_date - wyh
        smrfpath = self.paths
        datapath = self.pathd
        f = open(self.ppt_desc,'w')
    elif runtype == 'wrf':
        tt = self.end_date - wyh
        smrfpath = self.path_wrf_s
        datapath = self.path_wrf_data
        f = open(self.wrf_ppt_desc,'w')

    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file


    # File paths
    th = os.path.join(smrfpath,'thermal.nc')
    th_var = 'thermal'
    ta = os.path.join(smrfpath,'air_temp.nc')
    ta_var = 'air_temp'
    ea = os.path.join(smrfpath,'vapor_pressure.nc')
    ea_var = 'vapor_pressure'
    wind = os.path.join(smrfpath,'wind_speed.nc')
    wind_var = 'wind_speed'
    #tg_step = -2.5*np.ones((self.ny,self.nx))
    sn = os.path.join(smrfpath,'net_solar.nc')
    sn_var = 'net_solar'

    in_path = os.path.join(datapath,'input/')

    mp = os.path.join(smrfpath,'precip.nc')
    mp_var = 'precip'
    ps = os.path.join(smrfpath,'percent_snow.nc')
    ps_var = 'percent_snow'
    rho = os.path.join(smrfpath,'snow_density.nc')
    rho_var = 'snow_density'
    tp = os.path.join(smrfpath,'dew_point.nc')
    tp_var = 'dew_point'

    in_pathp = os.path.join(datapath,'ppt_4b')

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

        # print('idxt: {} t: {}'.format(idxt, t))
        trad_step = th_file.variables[th_var][idxt,:]
        ta_step = ta_file.variables[ta_var][idxt,:]
        ea_step = ea_file.variables[ea_var][idxt,:]
        wind_step = wind_file.variables[wind_var][idxt,:]
        sn_step = sn_file.variables[sn_var][idxt,:]
        mp_step = mp_file.variables[mp_var][idxt,:]
        tg_step = np.ones_like(mp_step)*(-2.5) # ground temp

        in_step = os.path.join(in_path,'in.%04i'%(t) )

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
        i.write(in_step, self.nbits)

        # only output if precip
        if np.sum(mp_step) > 0:
            ps_step = ps_file.variables[ps_var][idxt,:]
            rho_step = rho_file.variables[rho_var][idxt,:]
            tp_step = tp_file.variables[tp_var][idxt,:]
            in_stepp = os.path.join(os.path.abspath(in_pathp), 'ppt.4b_%04i'%(t) )
            i = smrf.ipw.IPW()
            i.new_band(mp_step)
            i.new_band(ps_step)
            i.new_band(rho_step)
            i.new_band(tp_step)
            i.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
            i.write(in_stepp, self.nbits)
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

def ipw2nc_mea(self, runtype):
    '''
    Function to create netcdf files from iSnobal output
    '''

    if runtype == 'smrf':
        wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.end_date))
    elif runtype == 'wrf':
        wyh = pd.to_datetime('%s-10-01'%pm.wyb(self.forecast_date))
    else:
        self._logger.error('Wrong run type given to ipw2nc. \
                            not smrf or wrf')

    print("convert all .ipw output files to netcdf files")
    ###################################################################################################
    ### convert all .ipw output files to netcdf files #################################################
    ###################################################################################################
    time_zone = self.tmz
    # create the x,y vectors
    x = self.v + self.dv*np.arange(self.nx)
    y = self.u + self.du*np.arange(self.ny)

    #===============================================================================
    # NetCDF EM image
    #===============================================================================
    m = {}
    m['name'] = ['net_rad','sensible_heat','latent_heat','snow_soil','precip_advected','sum_EB','evaporation','snowmelt','runoff','cold_content']
    m['units'] = ['W m-2','W m-2','W m-2','W m-2','W m-2','W m-2','kg m-2','kg m-2','kg or mm m-2','J m-2']
    m['description'] =['Average net all-wave radiation','Average sensible heat transfer','Average latent heat exchange','Average snow/soil heat exchange',
                     'Average advected heat from precipitation','Average sum of EB terms for snowcover','Total evaporation',
                     'Total snowmelt','Total runoff','Snowcover cold content']

    if runtype == 'smrf':
        netcdfFile = os.path.join(self.path_r, 'em.nc')
    elif runtype == 'wrf':
        netcdfFile = os.path.join(self.path_wrf_run, 'em.nc')

    dimensions = ('time','y','x')
    em = nc.Dataset(netcdfFile, 'w')

    # create the dimensions
    em.createDimension('time',None)
    em.createDimension('y',self.ny)
    em.createDimension('x',self.nx)

    # create some variables
    em.createVariable('time', 'f', dimensions[0])
    em.createVariable('y', 'f', dimensions[1])
    em.createVariable('x', 'f', dimensions[2])

    setattr(em.variables['time'], 'units', 'days since %s' % wyh)
    setattr(em.variables['time'], 'calendar', 'standard')
    setattr(em.variables['time'], 'time_zone', time_zone)
    em.variables['x'][:] = x
    em.variables['y'][:] = y

    # em image
    for i,v in enumerate(m['name']):
        em.createVariable(v, 'f', dimensions[:3], chunksizes=(24,10,10))
        setattr(em.variables[v], 'units', m['units'][i])
        setattr(em.variables[v], 'description', m['description'][i])

    #===============================================================================
    # NetCDF SNOW image
    #===============================================================================

    s = {}
    s['name'] = ['thickness','snow_density','specific_mass','liquid_water','temp_surf','temp_lower','temp_snowcover','thickness_lower','water_saturation']
    s['units'] = ['m','kg m-3','kg m-2','kg m-2','C','C','C','m','percent']
    s['description'] =['Predicted thickness of the snowcover','Predicted average snow density','Predicted specific mass of the snowcover',
                       'Predicted mass of liquid water in the snowcover','Predicted temperature of the surface layer',
                       'Predicted temperature of the lower layer','Predicted temperature of the snowcover',
                       'Predicted thickness of the lower layer', 'Predicted percentage of liquid water saturation of the snowcover']

    if runtype == 'smrf':
        netcdfFile = os.path.join(self.path_r, 'snow.nc')
    elif runtype == 'wrf':
        netcdfFile = os.path.join(self.path_wrf_run, 'snow.nc')

    dimensions = ('time','y','x')
    snow = nc.Dataset(netcdfFile, 'w')

    # create the dimensions
    snow.createDimension('time',None)
    snow.createDimension('y',self.ny)
    snow.createDimension('x',self.nx)

    # create some variables
    snow.createVariable('time', 'f', dimensions[0])
    snow.createVariable('y', 'f', dimensions[1])
    snow.createVariable('x', 'f', dimensions[2])

    setattr(snow.variables['time'], 'units', 'hours since %s' % wyh)
    setattr(snow.variables['time'], 'calendar', 'standard')
    setattr(snow.variables['time'], 'time_zone', time_zone)
    snow.variables['x'][:] = x
    snow.variables['y'][:] = y

    # snow image
    for i,v in enumerate(s['name']):

        snow.createVariable(v, 'f', dimensions[:3], chunksizes=(6,10,10))
        setattr(snow.variables[v], 'units', s['units'][i])
        setattr(snow.variables[v], 'description', s['description'][i])

    #===============================================================================
    # Get all files in the directory, open ipw file, and add to netCDF
    #===============================================================================

    # get all the files in the directory
    if runtype == 'smrf':
        d = sorted(glob.glob("%s/snow*"%self.pathro), key=os.path.getmtime)
    elif runtype == 'wrf':
        d = sorted(glob.glob("%s/snow*"%self.path_wrf_ro), key=os.path.getmtime)

    d.sort(key=lambda f: os.path.splitext(f))
    pbar = progressbar.ProgressBar(max_value=len(d)).start()
    j = 0

    for f in d:
        # get the hr
        head, nm = os.path.split(f)
        hr = nm.split('.')[1]
        hr = int(hr)
        snow.variables['time'][j] = hr+1
        em.variables['time'][j] = hr+1

        # Read the IPW file
        i = ipw.IPW(f)

        # output to the snow netcdf file
        for b,var in enumerate(s['name']):
            snow.variables[var][j,:] = i.bands[b].data

        # output to the em netcdf file
        emFile = "%s/%s.%04i" % (head, 'em', hr)
        i = ipw.IPW(emFile)
        for b,var in enumerate(m['name']):
            em.variables[var][j,:] = i.bands[b].data

        em.sync()
        snow.sync()
        j += 1
        pbar.update(j)
    pbar.finish()
    snow.close()
    em.close()
