'''
Created on Mar 28, 2017

@author: pkormos
'''

from PBR_tools import premodel as pm
import pandas as pd
import ConfigParser as cfp
import os
import mysql.connector
import numpy as np
import netCDF4 as nc
import utm
# from matplotlib import pyplot as plt
# from mpl_toolkits.axes_grid1 import Grid
# import matplotlib.dates as dates

def smrf_unmerge(config_file):
    # enter an end date for the run in the format 'yyyy-mm-dd HH:MM:SS', for example: '2017-03-20 06:00:00'
    # this script cleans the forecast model data from the data directories.
    # this script undoes the smrf_merge function in smrfing
    #     etime = '2017-02-15 06:00:00'
    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    et = pd.to_datetime(cfg['TIMES']['etime'])


    pathi = '%sdata/data/input/'%path00
    pathif = '%sdata/forecast/input%s/'%(path00,et.strftime("%Y%m%d"))
    pathp = '%sdata/data/ppt_4b'%path00
    pathpf = '%sdata/forecast/ppt_4b%s'%(path00,et.strftime("%Y%m%d"))

    files = os.listdir(pathif) # get list of files in forecast input dir
    print("cleaning data dir")
    for f in files:
        os.remove("%s%s"%(pathi,f))
    print("cleaning precip files in data dir")
    files = os.listdir(pathpf)
    for f in files:
        os.remove("%s/%s"%(pathp,f))

def validate_snow_brb(config_file):
    #     config_file = '/Users/pkormos/src/PBR_tools/config_PBR.txt'
    #     config_file = '/Volumes/data/snowdrift/BRB/pkormos_workspace/scripts/config_PBR2017.txt'

    cfg = cfp.ConfigParser()
    cfg.read(config_file)
    path00 = cfg.get('PATHS','path00')
    client = cfg.get('DB','client')
    if cfg.has_option('TIMES','fetime'):
        ft = pd.to_datetime(cfg.get('TIMES','fetime'))
    et = pd.to_datetime(cfg.get('TIMES','etime'))
    stns_swe = str.split(cfg.get('VALIDATE','stns'),',')
    #     client = 'BRB_2017';
    #     etime = '2017-03-31 06:00:00'
    #     fetime = '2017-04-03 06:00:00'
    #     et = pd.to_datetime(etime)
    #     ft = pd.to_datetime(fetime)
    #     path00 =  '/Volumes/data/snowdrift/BRB/BRB-wy17/'

    # set paths
    pathr = '%sruns/'%path00

    # get metadata from the data base from snotel sites
    qry = ('SELECT tbl_metadata.* FROM tbl_metadata INNER JOIN tbl_stations ON tbl_metadata.primary_id=tbl_stations.station_id'
           ' WHERE tbl_stations.client="'"%s"'" HAVING network_name = "'"SNOTEL"'";'%client)
    cnx = mysql.connector.connect(user='pkormos', password='outing',host='10.200.28.137',database='weather_db')
    meta_sno = pd.read_sql(qry, cnx)
    meta_sno = meta_sno.loc[meta_sno['source'] == 'NRCS']
    meta_sno.index = meta_sno['secondary_id']

    # get most recent model output file coordinates
    rundirs = os.listdir(pathr)                     # list subdirectories
    rundirs = [s for s in rundirs if "run" in s]    # keep only the run directories
    rtime =  [i.split('run', 1)[1] for i in rundirs]# split into dates
    rtime = pd.to_datetime(rtime, format='%Y%m%d')  # format as dates
    dir_order = sorted(range(len(rtime)), key=lambda k: rtime[k])
    #     latest = rundirs[int(np.where(rtime == max(rtime))[0])] # get most recent run directory

    if cfg.has_option('TIMES','fetime'):
        st_time = '%s-10-01 00:00:00'%pm.wyb(ft)
        end_time = ft.strftime('%Y-%m-%d %H:%M:%S')
        swe_meas = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(ft)), ft, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
        swe_mod = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(ft)), ft, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
    else:
        st_time = '%s-10-01 00:00:00'%pm.wyb(et)
        end_time = et.strftime('%Y-%m-%d %H:%M:%S')
        swe_meas = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
        swe_mod = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt


    # loop through stations to get measured results
    for stn in stns_swe: # for each station
        # get measured data from the database
        swe_meas[stn] = pm.var_get('snow_water_equiv',stn,st_time,end_time,'tbl_level1')
    swe_meas = swe_meas/25.4 # convert mm to inches
    # loop through stations to get modeled results

    for m in dir_order:
        nc_mod_sno = nc.Dataset('%s%s/snow.nc'%(pathr,rundirs[m]), 'r') # open netcdf file

        # get x,y, and time vectors from netcdf file
        ncxvec = nc_mod_sno.variables['x'][:]   # get x vec
        ncyvec = nc_mod_sno.variables['y'][:]   # get y vec
        if cfg.has_option('TIMES','fetime'):
            nctvec = pm.wyh2date(nc_mod_sno.variables['time'][:],pm.date2wy(ft))                            # pull out time vec
        else:
            nctvec = pm.wyh2date(nc_mod_sno.variables['time'][:],pm.date2wy(et))                            # pull out time vec
        t1 = nctvec[0].round('d')
        t2 = nctvec[-1].round('d')
        vswe = nc_mod_sno.variables['specific_mass'] # get variable

        for stn in stns_swe:
            ll = utm.from_latlon(meta_sno.ix[stn,'latitude'],meta_sno.ix[stn,'longitude']) # get utm coords from metadata
            xind = np.where(abs(ncxvec-ll[0]) == min(abs(ncxvec-ll[0])))[0]  # get closest pixel index to the station
            yind = np.where(abs(ncyvec-ll[1]) == min(abs(ncyvec-ll[1])))[0]  # get closest pixel index to the station

            swe = pd.Series(vswe[:,yind,xind].flatten(),index=nctvec)  # pull out closest model pixel data
            swe_mod.ix[t1:t2,stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind-1].flatten(),index=nctvec) # repeat for adjacent cells
            swe_mod.ix[t1:t2,'%s_sw'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_s'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_se'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_e'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_ne'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_n'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind-1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_nw'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind,xind-1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_w'%stn] = swe.resample('D').mean()
        nc_mod_sno.close() #close netcdf file
    swe_mod = swe_mod / 25.4 # convert mm to in

    # plotter uppper
    # get subplots stuff ########################################################################
    numsplots = np.size(stns_swe)
    if numsplots > 8:
        nrows = 3
    elif numsplots > 4:
        nrows = 2
    else:
        nrows = 1
    ncols = int(np.ceil(numsplots/nrows))
    #     le,bo,wi,he = subplot_spacing(nrows,ncols,bot_brd,top_brd,rit_brd,lef_brd,v_space,h_space)
    le,bo,wi,he = pm.subplot_spacing(nrows,ncols,.05,.05,.01,.05,.006,.006)

    # get y axis limits ########################################################################
    yup = np.ceil(swe_mod.max().max())+1
    if yup>30:
        ytic = np.arange(10,yup,10)
    else:
        ytic = np.arange(0,yup,1)
    xtic = pd.date_range(swe_mod.index[0], swe_mod.index[-1], freq='MS')
    xticlabs = xtic.strftime('%b1')
    #     xmintic = pd.date_range(swe_mod.index[0], swe_mod.index[-1], freq='SM')

    fig1 = plt.figure(num=1, figsize=(16,8.5), dpi=100, facecolor='w')
    for sp,stn in enumerate(stns_swe):

        matching = [s for s in swe_mod.columns if stn in s]
        ax = fig1.add_axes([le[sp],bo[sp],wi,he])
        l1 = ax.plot(swe_mod.index,swe_mod[matching],color='b',alpha = .3)
        l2 = ax.plot(swe_meas.index,swe_meas[stn],color='k')
        ax.text(xtic[0], ytic[-1], stn, bbox={'facecolor':'white', 'pad':7})

        ax.set_ylim((0,yup+5))
        ax.grid(b='on', which='major', axis='both')

        if le[sp]== np.min(le) and bo[sp] == np.min(bo): # if left edge and bottom
            ax.set_yticks(ytic)
            ax.set_xticks(xtic)
            ax.set_xticklabels(xticlabs)
        elif le[sp]== np.min(le):                       # if on the left edge
            ax.set_xticks(xtic)
            ax.set_xticklabels([])
            ax.set_yticks(ytic)
            #             ax.set_ylabel('SWE (in)')
            if bo[sp]==np.max(bo):
                ax.legend((l1[0],l2[0]),('Modeled','Measured'),loc=6,framealpha=1)
        elif bo[sp] == np.min(bo):                      # if on the bo
            ax.set_yticks(ytic)
            ax.set_yticklabels([])
            ax.set_xticks(xtic)
            ax.set_xticklabels(xticlabs)
        else:
            ax.set_xticks(xtic)
            ax.set_xticklabels([])
            ax.set_yticks(ytic)
            ax.set_yticklabels([])
    fig1.suptitle('SWE Validation at SNOTEL locations',size='xx-large')
    plt.figtext(.015,.5,'SWE (in)',rotation=90,size='x-large')

    if not os.path.exists('%svalidation/'%path00):
        os.makedirs('%svalidation/'%path00)
    plt.show()

    if cfg.has_option('VALIDATE','file'):# if the config file has a file name
        print('saving file to %svalidation/validation%s.png'%(path00,et.strftime("%Y%m%d")))
        plt.savefig('%svalidation/validation%s.png'%(path00,et.strftime("%Y%m%d")))
    else:
        print('not saving shit')

def validate_snow_sj(config_file):
    #     config_file = '/Users/pkormos/src/PBR_tools/config_PBR.txt'
    #     config_file = '/Volumes/data/blizzard/SanJoaquin/pkormos_workspace/scripts2017/config_PBR2017.txt'

    cfg = cfp.ConfigParser()
    cfg.read(config_file)
    path00 = cfg.get('PATHS','path00')
    client = cfg.get('DB','client')
    if cfg.has_option('TIMES','fetime'):
        ft = pd.to_datetime(cfg.get('TIMES','fetime'))
    et = pd.to_datetime(cfg.get('TIMES','etime'))
    stns_swe = str.split(cfg.get('VALIDATE','stns'),',')

    #     client = 'BRB_2017';
    #     etime = '2017-03-31 06:00:00'
    #     fetime = '2017-04-03 06:00:00'
    #     et = pd.to_datetime(etime)
    #     ft = pd.to_datetime(fetime)
    #     path00 =  '/Volumes/data/snowdrift/BRB/BRB-wy17/'

    # set paths
    pathr = '%sruns/'%path00

    # get metadata from the data base from snotel sites
    qry = ('SELECT tbl_metadata.* FROM tbl_metadata INNER JOIN tbl_stations ON tbl_metadata.primary_id=tbl_stations.station_id'
           ' WHERE tbl_stations.client="'"%s"'";'%client)
    cnx = mysql.connector.connect(user='pkormos', password='outing',host='10.200.28.137',database='weather_db')
    meta_sno = pd.read_sql(qry, cnx)
    meta_sno.index = meta_sno['primary_id']

    # get most recent model output file coordinates
    rundirs = os.listdir(pathr)                     # list subdirectories
    rundirs = [s for s in rundirs if "run" in s]    # keep only the run directories
    rtime =  [i.split('run', 1)[1] for i in rundirs]# split into dates
    rtime = pd.to_datetime(rtime, format='%Y%m%d')  # format as dates
    dir_order = sorted(range(len(rtime)), key=lambda k: rtime[k])

    if cfg.has_option('TIMES','fetime'):
        st_time = '%s-10-01 00:00:00'%pm.wyb(ft)
        end_time = ft.strftime('%Y-%m-%d %H:%M:%S')
        swe_meas = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(ft)), ft, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
        swe_mod = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(ft)), ft, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
    else:
        st_time = '%s-10-01 00:00:00'%pm.wyb(et)
        end_time = et.strftime('%Y-%m-%d %H:%M:%S')
        swe_meas = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt
        swe_mod = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='D'),columns=stns_swe)  # make dataframe for level 1 ppt

    # loop through stations to get measured results
    for stn in stns_swe: # for each station
        # get measured data from the database
        swe_meas[stn] = pm.var_get('snow_water_equiv',stn,st_time,end_time,'tbl_level1')
    swe_meas = swe_meas/25.4 # convert mm to inches
    # loop through stations to get modeled results

    for m in dir_order:
        nc_mod_sno = nc.Dataset('%s%s/snow.nc'%(pathr,rundirs[m]), 'r') # open netcdf file

        # get x,y, and time vectors from netcdf file
        ncxvec = nc_mod_sno.variables['x'][:]   # get x vec
        ncyvec = nc_mod_sno.variables['y'][:]   # get y vec
        if cfg.has_option('TIMES','fetime'):
            nctvec = pm.wyh2date(nc_mod_sno.variables['time'][:],pm.date2wy(ft))                            # pull out time vec
        else:
            nctvec = pm.wyh2date(nc_mod_sno.variables['time'][:],pm.date2wy(et))                            # pull out time vec
        t1 = nctvec[0].round('d')
        t2 = nctvec[-1].round('d')
        vswe = nc_mod_sno.variables['specific_mass'] # get variable

        for stn in stns_swe:
            ll = utm.from_latlon(meta_sno.ix[stn,'latitude'],meta_sno.ix[stn,'longitude']) # get utm coords from metadata
            xind = np.where(abs(ncxvec-ll[0]) == min(abs(ncxvec-ll[0])))[0]  # get closest pixel index to the station
            yind = np.where(abs(ncyvec-ll[1]) == min(abs(ncyvec-ll[1])))[0]  # get closest pixel index to the station

            swe = pd.Series(vswe[:,yind,xind].flatten(),index=nctvec)  # pull out closest model pixel data
            swe_mod.ix[t1:t2,stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind-1].flatten(),index=nctvec) # repeat for adjacent cells
            swe_mod.ix[t1:t2,'%s_sw'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_s'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind-1,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_se'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_e'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind+1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_ne'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_n'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind+1,xind-1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_nw'%stn] = swe.resample('D').mean()
            swe = pd.Series(vswe[:,yind,xind-1].flatten(),index=nctvec)
            swe_mod.ix[t1:t2,'%s_w'%stn] = swe.resample('D').mean()
        nc_mod_sno.close() #close netcdf file
    swe_mod = swe_mod / 25.4 # convert mm to in

    # plotter uppper
    # get subplots stuff ########################################################################
    numsplots = np.size(stns_swe)
    if numsplots > 8:
        nrows = 3
    elif numsplots > 4:
        nrows = 2
    else:
        nrows = 1
    ncols = int(np.ceil(numsplots/nrows))
    #     le,bo,wi,he = subplot_spacing(nrows,ncols,bot_brd,top_brd,rit_brd,lef_brd,v_space,h_space)
    le,bo,wi,he = pm.subplot_spacing(nrows,ncols,.05,.05,.01,.05,.006,.006)

    # get y axis limits ########################################################################
    yup = np.ceil(swe_mod.max().max())+1
    if yup>30:
        ytic = np.arange(10,yup,10)
    else:
        ytic = np.arange(0,yup,1)
    xtic = pd.date_range(swe_mod.index[0], swe_mod.index[-1], freq='MS')
    xticlabs = xtic.strftime('%b1')
    #     xmintic = pd.date_range(swe_mod.index[0], swe_mod.index[-1], freq='SM')

    fig1 = plt.figure(num=1, figsize=(16,8.5), dpi=100, facecolor='w')
    for sp,stn in enumerate(stns_swe):

        matching = [s for s in swe_mod.columns if stn in s]
        ax = fig1.add_axes([le[sp],bo[sp],wi,he])
        l1 = ax.plot(swe_mod.index,swe_mod[matching],color='b',alpha = .3)
        l2 = ax.plot(swe_meas.index,swe_meas[stn],color='k')
        ax.text(xtic[0], ytic[-1], stn, bbox={'facecolor':'white', 'pad':7})

        ax.set_ylim((0,yup+5))
        ax.grid(b='on', which='major', axis='both')

        if le[sp]== np.min(le) and bo[sp] == np.min(bo): # if left edge and bottom
            ax.set_yticks(ytic)
            ax.set_xticks(xtic)
            ax.set_xticklabels(xticlabs)
        elif le[sp]== np.min(le):                       # if on the left edge
            ax.set_xticks(xtic)
            ax.set_xticklabels([])
            ax.set_yticks(ytic)
            #             ax.set_ylabel('SWE (in)')
            if bo[sp]==np.max(bo):
                ax.legend((l1[0],l2[0]),('Modeled','Measured'),loc=6,framealpha=1)
        elif bo[sp] == np.min(bo):                      # if on the bo
            ax.set_yticks(ytic)
            ax.set_yticklabels([])
            ax.set_xticks(xtic)
            ax.set_xticklabels(xticlabs)
        else:
            ax.set_xticks(xtic)
            ax.set_xticklabels([])
            ax.set_yticks(ytic)
            ax.set_yticklabels([])
    fig1.suptitle('SWE Validation at SNOTEL locations',size='xx-large')
    #     fig1.legend((l1[0],l2[0]),('Modeled','Measured'), 'lower center', ncol=2)
    plt.figtext(.015,.5,'SWE (in)',rotation=90,size='x-large')
    if not os.path.exists('%svalidation/'%path00):
        os.makedirs('%svalidation/'%path00)
    plt.show()
    if cfg.has_option('VALIDATE','file'):# if the config file has a file name
        print('saving file to %svalidation/validation%s.png'%(path00,et.strftime("%Y%m%d")))
        plt.savefig('%svalidation/validation%s.png'%(path00,et.strftime("%Y%m%d")))
    else:
        print('not saving shit')

def swi_ts(config_file):
    '''
    function to get a daily timeseries of SWI throughout a basin
    '''
    #     config_file = '/Volumes/data/snowdrift/BRB/pkormos_workspace/scripts/config_PBR2017.txt'
    from isnobal import ipw
#     IPW = "/Users/pkormos/ipw/bin" # this needs changed
#     PATH = os.environ.copy()["PATH"] + ':/usr/local/bin:' + IPW # this also needs changed

    # read data from config file
    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    et = pd.to_datetime(cfg['TIMES']['etime'])
    msk_pa = cfg['PATHS']['pathtp']
    baseini = cfg['PATHS']['anyini']

    tt = cfp.ConfigParser()
    tt.read(baseini)
    cfg0 = dict(tt._sections)
    msk_fn = cfg0['TOPO']['mask']

    # create directories
    pathr = '%sruns/'%path00

    # get modeled data from run directory
    rundirs = os.listdir(pathr)                     # list subdirectories
    rundirs = [s for s in rundirs if "run" in s]    # keep only the run directories
    rtime =  [i.split('run', 1)[1] for i in rundirs]# split into dates
    rtime = pd.to_datetime(rtime, format='%Y%m%d')  # format as dates
    dir_order = sorted(range(len(rtime)), key=lambda k: rtime[k]) # get order of run dirs based on date stamp

    # bring in the mask data to get sub_basin number later
    msk_file = msk_pa + msk_fn
    i = ipw.IPW(msk_file) #  image
    msk = i.bands[0].data # find h20sat
    msk = msk.nonzero() # make an mask array
    #     msk =  msk.astype(int)
    swi_mod = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='D'),columns=['brb_total_mm'])  # make dataframe for basin swi
    swi_mod['brb_total_mm'][0]=0
    for m in dir_order:
        nc_mod_swi = nc.Dataset('%s%s/em.nc'%(pathr,rundirs[m]), 'r') # open netcdf file
        nctvec = pm.wyh2date(nc_mod_swi.variables['time'][:],pm.date2wy(et))                            # pull out time vec
        vswi = nc_mod_swi.variables['snowmelt'] # get variable

        for t in range(np.size(nctvec)):
            tt = vswi[t,:,:]
            t1 = nctvec[t].round('d')
            swi_mod.ix[t1,'brb_total_mm'] = tt[msk].mean()
        nc_mod_swi.close()
    swi_mod.to_csv('%s/daily_swi_mm4gus.csv'%path00)



def ppt_ts(config_file):
    '''
    function to get a daily timeseries of SWI throughout a basin
    '''
    #     config_file = '/Volumes/data/snowdrift/BRB/pkormos_workspace/scripts/config_PBR2017.txt'
    from isnobal import ipw
#     IPW = "/Users/pkormos/ipw/bin" # this needs changed
#     PATH = os.environ.copy()["PATH"] + ':/usr/local/bin:' + IPW # this also needs changed

    # read data from config file
    tt = cfp.ConfigParser()
    tt.read(config_file)
    cfg = dict(tt._sections)
    path00 = cfg['PATHS']['path00']
    et = pd.to_datetime(cfg['TIMES']['etime'])
    msk_pa = cfg['PATHS']['pathtp']
    baseini = cfg['PATHS']['anyini']

    tt = cfp.ConfigParser()
    tt.read(baseini)
    cfg0 = dict(tt._sections)
    msk_fn = cfg0['TOPO']['mask']

    ppt_nc = nc.Dataset('%sdata/data/smrfOutputs/precip.nc'%path00, 'r') # open netcdf file

    # bring in the mask data to get sub_basin number later
    msk_file = msk_pa + msk_fn
    i = ipw.IPW(msk_file) #  image
    msk = i.bands[0].data # find h20sat
    msk = msk.nonzero() # make an mask array
    ppt_tot = pd.DataFrame(index=pd.date_range(pd.to_datetime('%s-10-01'%pm.wyb(et)), et, freq='h'),columns=['ppt_mm'])  # make dataframe for basin swi
    nctvec = pm.wyh2date(ppt_nc.variables['time'][:],pm.date2wy(et))                            # pull out time vec
    vppt = ppt_nc.variables['precip'] # get variable
    for t in range(np.size(nctvec)):
        tt = vppt[t,:,:]
        ppt_tot.ix[nctvec[t],'ppt_mm'] = tt[msk].mean()
    ppt_nc.close()
    ppt_tot.to_csv('%s/hourly_ppt_mm.csv'%path00)
