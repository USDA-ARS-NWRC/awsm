'''
Created on Jan 23, 2018
Gather all netcdf files and
write one netcdf
@author: Micah prime
'''

import pandas as pd
import numpy as np
import netCDF4 as nc
import os
from datetime import datetime
import pytz
import matplotlib.pyplot as plt
from smrf.utils import utils
from smrf import ipw
from awsm.data.topo import get_topo_stats

print("This utility takes geoTiff files for depth updates in AWSM and sticks"
      "them into one netCDF for easier use. ")

fmt = '%Y-%m-%d %H:%M:%S'
# chunk size
cs = (6, 10, 10)


def read_flight(fp_lst, topo_stats, nanval = None, nanup = None):
    """
    args:
        fp_lst - list of paths to flight ascii
        topo_stats - from dem
        nanval - optional nanvalue
    returns: flight_arrays - numpy array of time and images from flight
    """

    # create numpy array to store values
    ny = topo_stats['ny']
    nx = topo_stats['nx']
    data_array = np.zeros((len(fp_lst), ny, nx))

    for idf, fp in enumerate(fp_lst):
        print(fp)
        D = np.genfromtxt(fp, dtype = float, skip_header=6, filling_values=np.nan)
        if nanval is not None:
            D[D==nanval] = np.nan
        if nanup is not None:
            D[D>nanup] = np.nan
        D[D > 100] = np.nan
        # Make sure we assigned nans
        print('There are Nans?: ',np.any(np.isnan(D)))
        # pad values if necessary
        if D.shape != (ny, nx):
            print('Padding array {} to fit domain {}'.format(D.shape, (ny,nx)))

            # pad left side
            #dleft = 1 + ny - D.shape[0]
            dleft = ny - D.shape[0]
            padleft = np.ones((dleft, D.shape[1]))
            padleft[:] = np.nan
            padagain = np.ones((1, D.shape[1]))
            padagain[:] = np.nan
            D = np.concatenate((padleft, D), axis=0)
            D = np.concatenate((D, padagain), axis=0)

            # pad the top
            dtop = 1 + nx - D.shape[1]
            padtop = np.ones((D.shape[0], dtop))
            padtop[:] = np.nan
            D = np.concatenate((padtop, D), axis=1)

            # get rid of last row and column to fit domain correctly
            #D = np.delete(D, ny, 0)
            #D = np.delete(D, nx, 1)

            D = np.delete(D, 0, 0)
            # correct
            D = np.delete(D, 0, 1)

        # store value
        data_array[idf,:] = D

    # plt.imshow(D)
    # plt.show()

    return data_array


def output_files(output_path, fname, start_date, x, y):
    """
    Create the depth netcdf file, don't write yet

    Args:
        output_path: path to directory for output
        fname:       name of file to ouptut
        start_dateL: date for reference index
        x:           vector of x coords
        y:           vector of y coords

    Returns:
        ds: dataset
    """
    fmt = '%Y-%m-%d %H:%M:%S'
    # chunk size
    cs = (6, 10, 10)

    # ------------------------------------------------------------------------
    # Depth netcdf
    m = {}
    m['name'] = ['depth']
    m['units'] = ['m']
    m['description'] = ['ASO depth in meters']

    fname = fname +'.nc'

    netcdfFile = os.path.join(output_path, fname)

    if os.path.isfile(netcdfFile):
        print('Opening {}, data may be overwritten!'.format(netcdfFile))
        ds = nc.Dataset(netcdfFile, 'w', clobber=True)
        h = '[{}] Data added or updated'.format(
            datetime.now().strftime(fmt))
        setattr(ds, 'last_modified', h)

    else:
        ds = nc.Dataset(netcdfFile, 'w')

        dimensions = ('time', 'y', 'x')

        # create the dimensions
        ds.createDimension('time', None)
        ds.createDimension('y', len(y))
        ds.createDimension('x', len(x))

        # create some variables
        ds.createVariable('time', 'f', dimensions[0])
        ds.createVariable('y', 'f', dimensions[1])
        ds.createVariable('x', 'f', dimensions[2])

        # setattr(ds.variables['time'], 'units', 'hours since %s' % options['time']['start_date'])
        setattr(ds.variables['time'], 'units', 'hours since %s' % start_date)
        setattr(ds.variables['time'], 'calendar', 'standard')
        #     setattr(ds.variables['time'], 'time_zone', time_zone)
        ds.variables['x'][:] = x
        ds.variables['y'][:] = y

        # create image
        for i, v in enumerate(m['name']):
            # ds.createVariable(v, 'f', dimensions[:3], chunksizes=(6,10,10))
            ds.createVariable(v, 'f', dimensions[:3], chunksizes=cs)
            setattr(ds.variables[v], 'units', m['units'][i])
            setattr(ds.variables[v], 'description', m['description'][i])

    return ds

def output_timestep(ds, data, tstep, idt, start_date):
    """
    Output the ASO depths at each time

    Args:
        ds:      netcdf dataset
        data:    image to write
        tstep:   datetime time step
        idt:     time index
        start_date: start date datetime
    """

    # offset to match same convention as iSnobal
    tunits = 'hours since %s' % start_date
    calendar = 'standard'

    t = nc.date2num(tstep.replace(tzinfo=None), tunits, calendar)

    # insert the time
    ds.variables['time'][idt] = t

    # insert the data
    ds.variables['depth'][idt, :] = data

    ds.sync()


def run():

    fmt_file = fmt = '%Y%m%d'
    #basin = 'SJ'
    basin = 'TB'
    wy = 2016
    fpdir = '/home/micahsandusky/Code/awsfTesting/newupdatetest'

    sj_updates = {}
    sj_updates[2018] = ['2018-04-23', '2018-05-28']
    sj_updates[2017] = []
    # date_lst = ['2018-04-23', '2018-05-28']

    tuol_updates = {}
    tuol_updates[2013] = ['2013-04-03', '2013-04-29', '2013-05-03', '2013-05-25',
                          '2013-06-01', '2013-06-08']
    tuol_updates[2014] = ['2014-03-23', '2014-04-07', '2014-04-13', '2014-04-20',
                          '2014-04-28', '2014-05-02', '2014-05-11', '2014-05-17',
                          '2014-05-27', '2014-05-31', '2014-06-05']
    tuol_updates[2015] = ['2015-02-18', '2015-03-06', '2015-03-25', '2015-04-03',
                          '2015-04-09', '2015-04-15', '2015-04-27', '2015-05-01',
                          '2015-05-28', '2015-06-08']
    tuol_updates[2016] = ['2016-03-26', '2016-04-07', '2016-04-16',
                          '2016-04-26', '2016-05-09', '2016-05-27', '2016-06-07',
                          '2016-06-13', '2016-06-20', '2016-06-25', '2016-07-01',
                          '2016-07-08']
    #tuol_updates[2016] = ['2016-04-16', '2016-04-26']

    if basin == 'TB':
        date_lst = tuol_updates[wy]

    # put into datetime
    date_lst = [pd.to_datetime(dt) for dt in date_lst]
    tzinfo = pytz.timezone('UTC')
    tmp_date = date_lst[0]
    tmp_date = tmp_date.replace(tzinfo=tzinfo)
    # find start of water year
    tmpwy = utils.water_day(tmp_date)[1]
    wy = tmpwy
    start_date = pd.to_datetime('{:d}-10-01'.format(tmpwy-1))

    # get the paths
    fp_lst = ['wy{}/{}{}_SUPERsnow_depth.asc'.format(wy, basin, dt.strftime(fmt_file))
              for dt in date_lst]
    fp_lst = [os.path.join(fpdir,fpu) for fpu in fp_lst]

    if basin == 'TB':
        dem_fp = '/data/blizzard/tuolumne/common_data/topo/tuolx_dem_50m.ipw'
        gisPath = '/home/micahsandusky/Code/awsfTesting/initUpdate/'
        maskPath = os.path.join(gisPath, 'tuolx_mask_50m.ipw')
        if wy < 2017:
            maskPath = os.path.join(gisPath, 'tuolx_hetchy_mask_50m.ipw')
    elif basin == 'SJ':
        dem_fp = '/data/blizzard/sanjoaquin/common_data/topo/SJ_dem_50m.ipw'
        gisPath = '/data/blizzard/sanjoaquin/common_data/topo/'
        maskPath = os.path.join(gisPath, 'SJ_Millerton_mask_50m.ipw')
    else:
        raise ValueError('Wrong basin name')

    mask = ipw.IPW(maskPath).bands[0].data[:]

    output_path = os.path.join(fpdir, 'wy{}'.format(wy))
    fname = 'flight_depths_{}'.format(basin)
    nanval = -9999.0
    nanup = 1000.0


    # #### Now actually do the stuff ####
    # date to use for finding wy
    fname = fname+'_{}'.format(tmpwy)

    # get topo stats from dem
    ts = get_topo_stats(dem_fp, filetype = 'ipw')
    x = ts['x'] # + ts['dv']*np.arange(ts['nx'])
    y = ts['y'] # + ts['du']*np.arange(ts['ny'])

    # get depth array
    depth_arr = read_flight(fp_lst, ts, nanval = nanval, nanup = nanup)

    print(depth_arr)
    # create netcdfs
    ds = output_files(output_path, fname, start_date, x,  y)

    # write to file
    for idt, dt in enumerate(date_lst):
        data = depth_arr[idt,:]#*mask'
        data[mask == 0.0] = np.nan
        output_timestep(ds, data, dt, idt, start_date)

    # close file
    ds.close()


if __name__ =='__main__':
    run()
