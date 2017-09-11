'''
Created on Mar 27, 2017
script to automate the many tasks of distributing data
running the model.
@author: pkormos
'''

import pandas as pd
import smrf
from datetime import timedelta
import faulthandler
from PBR_tools import premodel as pm
import numpy as np
import progressbar
from smrf import ipw
import os
import netCDF4 as nc
import shutil
import glob
import ConfigParser as cfp

def smrf_go_meas(config_file):

    #    enter a start date in the format 'yyyy-mm-dd HH:MM:SS', for example: '2017-03-20 06:00:00'
    #    and an end date for the run. directories will be named with the etime timestamp

    # parse config file
    # config_file = '/Users/pkormos/src/PBR_tools/config_PBR.txt'
    # config_file = '/Volumes/data/blizzard/SanJoaquin/pkormos_workspace/scripts2017/config_PBR2017.txt'

    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    pathws = cfg['PATHS']['pathws']
    pathtp = cfg['PATHS']['pathtp']
    tmpdir = cfg['PATHS']['tmpdir']
    anyini = cfg['PATHS']['anyini']
    st = pd.to_datetime(cfg['TIMES']['stime'])
    et = pd.to_datetime(cfg['TIMES']['etime'])
    tmz = cfg['TIMES']['time_zone']
    u  = int(cfg['GRID']['u'])
    v  = int(cfg['GRID']['v'])
    du  = int(cfg['GRID']['du'])
    dv  = int(cfg['GRID']['dv'])
    units = cfg['GRID']['units']
    csys = cfg['GRID']['csys']
    nx = int(cfg['GRID']['nx'])
    ny = int(cfg['GRID']['ny'])

    ### define paths ###
    paths = '%sdata/data/smrfOutputs/'%path00
    pathi = '%sdata/data/input/'%path00
    pathp = '%sdata/data/ppt_4b/'%path00

    # ###################################################################################################
    # ### read in base and write out the specific config file for smrf ##################################
    # ###################################################################################################
    print("writing the config file for smrf (meas)")
    meas_ini_file = "%ssmrf%s.ini"%(pathws, et.strftime("%Y%m%d"))

    cfg0 = cfp.RawConfigParser()
    cfg0.read(anyini)
    tt = cfg0.get('TOPO','dem')
    cfg0.set('TOPO','dem','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','mask')
    cfg0.set('TOPO','mask','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_type')
    cfg0.set('TOPO','veg_type','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_height')
    cfg0.set('TOPO','veg_height','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_k')
    cfg0.set('TOPO','veg_k','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_tau')
    cfg0.set('TOPO','veg_tau','%s%s'%(pathtp,tt))
    cfg0.set('TiMe','start_date',st.strftime('%Y-%m-%d %H:%M:%S'))
    cfg0.set('TiMe','end_date',et.strftime('%Y-%m-%d %H:%M:%S'))
    cfg0.set('TiMe','tmz',tmz)
    tt = cfg0.get('wind','maxus_netcdf')
    cfg0.set('wind','maxus_netcdf','%s%s'%(pathtp,tt))
    cfg0.set('output','out_location',paths)
    cfg0.set('logging','log_file','%sout%s.log'%(paths,et.strftime("%Y%m%d")))
    cfg0.set('system','temp_dir',tmpdir)

    with open(meas_ini_file, 'wb') as configfile:
        cfg0.write(configfile)


    ###################################################################################################
    ### run smrf with the config file we just made ####################################################
    ###################################################################################################
    print("running smrf (meas)")
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

    ###################################################################################################
    ### make .ipw input files from netCDF files #######################################################
    ###################################################################################################
    print("making the ipw files from NetCDF files (meas)")
    #     execfile('/Volumes/data/snowdrift/BRB/common_data/grid_info.py')
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(et))
    tt = st-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = 16

    # File paths
    th = '%sthermal.nc'%paths
    th_var = 'thermal'
    ta = '%sair_temp.nc'%paths
    ta_var = 'air_temp'
    ea = '%svapor_pressure.nc'%paths
    ea_var = 'vapor_pressure'
    wind = '%swind_speed.nc'%paths
    wind_var = 'wind_speed'
    tg_step = -2.5*np.ones((ny,nx))
    sn = '%snet_solar.nc'%paths
    sn_var = 'net_solar'
    in_path = pathi
    mp = '%sprecip.nc'%paths
    mp_var = 'precip'
    ps = '%spercent_snow.nc'%paths
    ps_var = 'percent_snow'
    rho = '%ssnow_density.nc'%paths
    rho_var = 'snow_density'
    tp = '%sdew_point.nc'%paths
    tp_var = 'dew_point'
    in_pathp = pathp
    in_path_w = pathp
    ppt_desc = '%sdata/data/ppt_desc%s.txt'%(path00,et.strftime("%Y%m%d"))
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

    if not os.path.exists(in_path):
        os.makedirs(in_path)
        os.makedirs(in_pathp)

    pbar = progressbar.ProgressBar(max_value=len(timeStep)).start()
    j = 0
    for t in timeStep:

        trad_step = th_file.variables[th_var][t,:]
        ta_step = ta_file.variables[ta_var][t,:]
        ea_step = ea_file.variables[ea_var][t,:]
        wind_step = wind_file.variables[wind_var][t,:]
        sn_step = sn_file.variables[sn_var][t,:]
        mp_step = mp_file.variables[mp_var][t,:]

        in_step = '%sin.%04i' % (in_path, t)

        i = ipw.IPW()
        i.new_band(trad_step)
        i.new_band(ta_step)
        i.new_band(ea_step)
        i.new_band(wind_step)
        i.new_band(tg_step)

        # add solar if the sun is up
        if np.sum(sn_step) > 0:
            i.new_band(sn_step)

        i.add_geo_hdr([u, v], [du, dv], units, csys)
        i.write(in_step, nbits)

        # only output if precip
        if np.sum(mp_step) > 0:
            ps_step = ps_file.variables[ps_var][t,:]
            rho_step = rho_file.variables[rho_var][t,:]
            tp_step = tp_file.variables[tp_var][t,:]
            in_stepp = os.path.join('%sppt.4b_%04i' % (in_pathp, t))
            in_step_w = os.path.join('%sppt.4b_%04i' % (in_path_w,t))
            i = ipw.IPW()
            i.new_band(mp_step)
            i.new_band(ps_step)
            i.new_band(rho_step)
            i.new_band(tp_step)
            i.add_geo_hdr([u, v], [du, dv], units, csys)
            i.write(in_stepp, nbits)
            f.write('%i %s\n' % (t, in_step_w))

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

def smrf_go_wrf(config_file):
    #    enter a download date in the format 'yyyy-mm-dd hh:mm:ss', for example: '2017-03-20 06:00:00'
    #    should be the same time as e time afrom smrf_go function abover
    #     etime = '2017-03-27 06:00:00'
    #     path00,tmpdir,st,et,ft,tmz,u,v,du,dv,units,csys,nx,ny,ppt_desc_file,prev_mod_file = pm.pbr_parse(config_file)
    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    pathws = cfg['PATHS']['pathws']
    pathtp = cfg['PATHS']['pathtp']
    wrfini = cfg['PATHS']['wrfini']
    tmpdir = cfg['PATHS']['tmpdir']
    et = pd.to_datetime(cfg['TIMES']['etime'])
    tmz = cfg['TIMES']['time_zone']
    u  = int(cfg['GRID']['u'])
    v  = int(cfg['GRID']['v'])
    du  = int(cfg['GRID']['du'])
    dv  = int(cfg['GRID']['dv'])
    units = cfg['GRID']['units']
    csys = cfg['GRID']['csys']
    nx = int(cfg['GRID']['nx'])
    ny = int(cfg['GRID']['ny'])

    pathf =  '%sdata/forecast/'%path00
    pathif = '%sdata/forecast/input%s/'%(path00,et.strftime("%Y%m%d"))
    pathp =  '%sdata/data/ppt_4b/'%path00
    pathpf = '%sdata/forecast/ppt_4b%s'%(path00,et.strftime("%Y%m%d"))
    pathsf = '%sdata/forecast/smrfOutputs%s'%(path00,et.strftime("%Y%m%d"))

    # ###################################################################################################
    # ### write out the wrf config file for smrf ########################################################
    # ###################################################################################################
    print("making wrf smrf config file.")
    wrf_ini_file = "%sbrb%ssmrf_forecast.ini"%(pathws, et.strftime("%Y%m%d"))
    tt0 = et+timedelta(hours=1)
    tt1 = et+timedelta(days=3)

    cfg0 = cfp.RawConfigParser()
    cfg0.read(wrfini)
    tt = cfg0.get('TOPO','dem')
    cfg0.set('TOPO','dem','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','mask')
    cfg0.set('TOPO','mask','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_type')
    cfg0.set('TOPO','veg_type','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_height')
    cfg0.set('TOPO','veg_height','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_k')
    cfg0.set('TOPO','veg_k','%s%s'%(pathtp,tt))
    tt = cfg0.get('TOPO','veg_tau')
    cfg0.set('TOPO','veg_tau','%s%s'%(pathtp,tt))
    cfg0.set('TiMe','start_date',tt0.strftime("%Y-%m-%d %H:%M:%S"))
    cfg0.set('TiMe','end_date',tt1.strftime("%Y-%m-%d %H:%M:%S"))
    cfg0.set('TiMe','tmz',tmz)
    cfg0.set('gridded','file','%swrfout_d02_%s.nc'%(pathf,tt0.strftime('%Y-%m-%d')))
    cfg0.set('output','out_location',pathsf)
    cfg0.set('logging','log_file','%s/out%s.txt'%(pathsf,et.strftime("%Y%m%d")))
    cfg0.set('system','tmp_dir',tmpdir)
    cfg0.set('system','threading','false')
    cfg0.set('system','max_values',1)

    with open(wrf_ini_file, 'wb') as configfile:
        cfg0.write(configfile)

    ###################################################################################################
    ### make directories for forecast data ############################################################
    ###################################################################################################
    print("making directories.")
    # for smrf forecast  data
    if not os.path.exists(pathsf):
        os.makedirs(pathsf)
    # for smrf model ipw  data
    if not os.path.exists(pathif):
        os.makedirs(pathif)
    # for smrf model precip data
    if not os.path.exists(pathpf):
        os.makedirs(pathpf)

    ###################################################################################################
    ### run smrf with the forecast config file we just made ###########################################
    ###################################################################################################
    print("running wrf smrf.")
    faulthandler.enable()
    s = smrf.framework.SMRF(wrf_ini_file)
    print("loadTopo")
    s.loadTopo()
    print("init dist")
    s.initializeDistribution()
    print("init output")
    s.initializeOutput()
    print("load data")
    s.loadData()
    print("distribute data")
    s.distributeData()

    ###################################################################################################
    ### make .ipw input files from netCDF forecast files ##############################################
    ###################################################################################################
    print("converting netcdf files to input files (ipw)")
    #     execfile('/Volumes/data/snowdrift/BRB/common_data/grid_info.py')

    wyh = pd.to_datetime('%s-10-01'%pm.wyb(et))
    tt = tt0-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = 16

    # File paths
    th = '%s/thermal.nc'%pathsf
    th_var = 'thermal'
    ta = '%s/air_temp.nc'%pathsf
    ta_var = 'air_temp'
    ea = '%s/vapor_pressure.nc'%pathsf
    ea_var = 'vapor_pressure'
    wind = '%s/wind_speed.nc'%pathsf
    wind_var = 'wind_speed'
    tg_step = -2.5*np.ones((ny,nx))
    sn = '%s/net_solar.nc'%pathsf
    sn_var = 'net_solar'
    in_path = pathif
    mp = '%s/precip.nc'%pathsf
    mp_var = 'precip'
    ps = '%s/percent_snow.nc'%pathsf
    ps_var = 'percent_snow'
    rho = '%s/snow_density.nc'%pathsf
    rho_var = 'snow_density'
    tp = '%s/dew_point.nc'%pathsf
    tp_var = 'dew_point'
    in_pathp = pathpf
    in_path_w = pathp
    ppt_desc = '%sdata/forecast/ppt_desc%s.txt'%(path00,et.strftime("%Y%m%d"))
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
    timeStep = range(N)        # timesteps loop through
    pbar = progressbar.ProgressBar(max_value=len(timeStep)).start()
    j = 0
    for t in timeStep:

        trad_step = th_file.variables[th_var][t,:]
        ta_step = ta_file.variables[ta_var][t,:]
        ea_step = ea_file.variables[ea_var][t,:]
        wind_step = wind_file.variables[wind_var][t,:]
        sn_step = sn_file.variables[sn_var][t,:]
        mp_step = mp_file.variables[mp_var][t,:]

        in_step = '%s/in.%04i' % (in_path, t+offset)

        i = ipw.IPW()
        i.new_band(trad_step)
        i.new_band(ta_step)
        i.new_band(ea_step)
        i.new_band(wind_step)
        i.new_band(tg_step)

        # add solar if the sun is up
        if np.sum(sn_step) > 0:
            i.new_band(sn_step)

        i.add_geo_hdr([u, v], [du, dv], units, csys)
        i.write(in_step, nbits)

        # only output if precip
        if np.sum(mp_step) > 0:
            ps_step = ps_file.variables[ps_var][t,:]
            rho_step = rho_file.variables[rho_var][t,:]
            tp_step = tp_file.variables[tp_var][t,:]
            in_stepp = os.path.join('%s/ppt.4b_%04i' % (in_pathp, t+offset))
            in_step_w = os.path.join('%s/ppt.4b_%04i' % (in_path_w,t+offset))
            i = ipw.IPW()
            i.new_band(mp_step)
            i.new_band(ps_step)
            i.new_band(rho_step)
            i.new_band(tp_step)
            i.add_geo_hdr([u, v], [du, dv], units, csys)
            i.write(in_stepp, nbits)
            f.write('%i %s\n' % (t+offset, in_step_w))

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

def smrf_merge(config_file):
    #    enter a datetime for the run in the format 'yyyy-mm-dd hh:mm:ss', for example: '2017-03-20 06:00:00'
    #    this assumes that you cleaned station data up to 6:00, downloaded a 3 day wrf forecast on that morning
    #         etime = '2017-02-15 06:00:00'

    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    et = pd.to_datetime(cfg['TIMES']['etime'])

    pathi =  '%sdata/data/input/'%path00
    pathif = '%sdata/forecast/input%s/'%(path00,et.strftime("%Y%m%d"))
    pathpf = '%sdata/forecast/ppt_4b%s/'%(path00,et.strftime("%Y%m%d"))
    pathp =  '%sdata/data/ppt_4b/'%path00
    print("copying wrf data files to data dir")
    files = os.listdir(pathif)
    for f in files:
        shutil.copy("%s%s"%(pathif,f), pathi)
    print("copying wrf precip files to data dir")
    files = os.listdir(pathpf)
    for f in files:
        shutil.copy("%s%s"%(pathpf,f), pathp)

    # make the ppt_desc.txt file from meas and forecast
    print("creating joint ppt_desc file")
    ppt_desc_meas = '%sdata/data/ppt_desc%s.txt'%(path00,et.strftime("%Y%m%d"))
    ppt_desc_forecast = '%sdata/forecast/ppt_desc%s.txt'%(path00,et.strftime("%Y%m%d"))
    ppt_desc_comb = '%sdata/data/ppt_desc.txt'%path00
    cmd = "cat %s %s > %s"%(ppt_desc_meas,ppt_desc_forecast,ppt_desc_comb)
    os.system(cmd)

def run_snobal(config_file):

    # creates run directory if it doesn't exist, builds the model init file, runs the model, and converts
    # the .ipw model output files to NetCDF format for reports and analysis
    # the config_file would need the following sections and variables defined to use this function
    #    [TIMES]
    #     stime: enter a start datetime for the run in the format 'yyyy-mm-dd hh:mm:ss', for example: '2017-03-20 06:00:00'
    #     etime: enter an end (end of measured data) datetime for the run in the format 'yyyy-mm-dd hh:mm:ss'
    #     fetime: enter a forecast end datetime for the run in the format 'yyyy-mm-dd hh:mm:ss'
    #    [PATHS]
    #     path00: the base path for scripts, data, and runs
    #    [GRID]
    #     u:    The coordinates of image line 0 in csys
    #     v:    The coordinates of image sample 0 in csys
    #     du:   The distances between adjacent image lines in csys
    #     dv:   The distances between adjacent image samples in csys
    #     units: 'm' for meters or 'km' for kilometers
    #     csys: coordinate system 'UTM', See the ipw manual for  mkproj for a list of standard names for coordinate systems.
    #     nx:    number of lines
    #     ny:    number of samples

    #     stime = '2017-03-01 00:00:00'
    #     etime = '2017-03-27 06:00:00'
    #     fetime = '2017-03-30 06:00:00'
    #     ppt_desc_file = '%sdata/data/ppt_desc.txt'%path00
    #     prev_mod_file = "%sruns/run20170320/output/snow.4085"%path00
    print("pulling in data from config file")
    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    pathtp = cfg['PATHS']['pathtp']
    st = pd.to_datetime(cfg['TIMES']['stime'])
    et = pd.to_datetime(cfg['TIMES']['etime'])

    ft = pd.to_datetime(cfg['TIMES']['fetime'])
    prev_mod_file = cfg['FILES']['prev_mod_file']

    ppt_desc_file = cfg['FILES']['ppt_desc_file']
    u  = int(cfg['GRID']['u'])
    v  = int(cfg['GRID']['v'])
    du  = int(cfg['GRID']['du'])
    dv  = int(cfg['GRID']['dv'])
    units = cfg['GRID']['units']
    csys = cfg['GRID']['csys']
    nx = int(cfg['GRID']['nx'])
    ny = int(cfg['GRID']['ny'])
    anyini = cfg['PATHS']['anyini']

    cfg0 = cfp.RawConfigParser()
    cfg0.read(anyini)
    dem0 = cfg0.get('TOPO','dem')


    print("calculating time vars")
    wyh = pd.to_datetime('%s-10-01'%pm.wyb(et))
    tt = st-wyh
    offset = tt.days*24 +  tt.seconds//3600 # start index for the input file
    nbits = 16

    pathi =    '%sdata/data/input/'%path00
    pathinit = '%sdata/data/init/'%path00
    pathr =    '%sruns/run%s'%(path00,et.strftime("%Y%m%d"))
    pathro =   '%s/output'%pathr

    print("making dirs")
    # create the run directory
    if not os.path.exists(pathro):
        os.makedirs(pathro)
        os.makedirs(pathinit)

        # make the initial conditions file (init)
    print("making initial conds img")
    rl0 = '%sz0.ipw'%pathtp
    i_dem = ipw.IPW('%s%s'%(pathtp,dem0))
    i_rl0 = ipw.IPW(rl0)
    if offset > 0:
        i_in = ipw.IPW(prev_mod_file)
        i_out = ipw.IPW()
        i_out.new_band(i_dem.bands[0].data)
        i_out.new_band(i_rl0.bands[0].data)
        i_out.new_band(i_in.bands[0].data) # snow depth
        i_out.new_band(i_in.bands[1].data) # snow density
        i_out.new_band(i_in.bands[4].data) # active layer temp
        i_out.new_band(i_in.bands[5].data) # lower layer temp
        i_out.new_band(i_in.bands[6].data) # avgerage snow temp
        i_out.new_band(i_in.bands[8].data) # percent saturation
        i_out.add_geo_hdr([u, v], [du, dv], units, csys)
        i_out.write('%sinit%04d.ipw'%(pathinit,offset), nbits)
    else:
        zs0 = np.zeros((ny,nx))
        i_out = ipw.IPW()
        i_out.new_band(i_dem.bands[0].data)
        i_out.new_band(i_rl0.bands[0].data)
        i_out.new_band(zs0) # zeros snow cover depth
        i_out.new_band(zs0) # 0density
        i_out.new_band(zs0) # 0ts active
        i_out.new_band(zs0) # 0ts avg
        i_out.new_band(zs0) # 0liquid
        i_out.add_geo_hdr([u, v], [du, dv], units, csys)
        i_out.write('%sinit%04d.ipw'%(pathinit,offset), nbits)

    # develop the command to run the model
    print("developing command and running")
    tt = ft-st                              # get a time delta to get hours from water year start
    # tt = et-st
    tmstps = tt.days*24 +  tt.seconds//3600 # start index for the input file
    run_cmd = "time isnobal -v -P 20 -r %s -t 60 -n %s -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(offset,tmstps,pathinit,offset,ppt_desc_file,pathi,pathr,et.strftime("%Y%m%d"))
#     run_cmd = "time isnobal -v -P 20 -t 60 -n %s -I %sinit%04d.ipw -p %s -d 0.15 -i %sin -O 24 -e em -s snow > %s/sout%s.txt 2>&1"%(tmstps,pathinit,offset,ppt_desc_file,pathi,pathr,et.strftime("%Y%m%d"))

    os.chdir(pathro)
    os.system(run_cmd)

    print("convert all .ipw output files to netcdf files")
    ###################################################################################################
    ### convert all .ipw output files to netcdf files #################################################
    ###################################################################################################
    time_zone = 'UTC'
    # create the x,y vectors
    x = v + dv*np.arange(nx)
    y = u + du*np.arange(ny)

    #===============================================================================
    # NetCDF EM image
    #===============================================================================
    m = {}
    m['name'] = ['net_rad','sensible_heat','latent_heat','snow_soil','precip_advected','sum_EB','evaporation','snowmelt','runoff','cold_content']
    m['units'] = ['W m-2','W m-2','W m-2','W m-2','W m-2','W m-2','kg m-2','kg m-2','kg or mm m-2','J m-2']
    m['description'] =['Average net all-wave radiation','Average sensible heat transfer','Average latent heat exchange','Average snow/soil heat exchange',
                     'Average advected heat from precipitation','Average sum of EB terms for snowcover','Total evaporation',
                     'Total snowmelt','Total runoff','Snowcover cold content']

    netcdfFile = os.path.join(pathr, 'em.nc')
    dimensions = ('time','y','x')
    em = nc.Dataset(netcdfFile, 'w')

    # create the dimensions
    em.createDimension('time',None)
    em.createDimension('y',ny)
    em.createDimension('x',nx)

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

    netcdfFile = os.path.join(pathr, 'snow.nc')
    dimensions = ('time','y','x')
    snow = nc.Dataset(netcdfFile, 'w')

    # create the dimensions
    snow.createDimension('time',None)
    snow.createDimension('y',ny)
    snow.createDimension('x',nx)

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
    d = sorted(glob.glob("%s/snow*"%pathro), key=os.path.getmtime)
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
