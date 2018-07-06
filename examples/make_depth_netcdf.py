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
from awsm.utils.utilities import get_topo_stats

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
        ds = nc.Dataset(netcdfFile, 'a')
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
    basin = 'SJ'
    fpdir = '/home/micahsandusky/Code/awsfTesting/newupdatetest'
    # date_lst = ['2016-03-26', '2016-04-01', '2016-04-07', '2016-04-16',
    #             '2016-04-26', '2016-05-09', '2016-05-27', '2016-06-07',
    #             '2016-06-13', '2016-06-20', '2016-06-25', '2016-07-01',
    #             '2016-07-08']
    date_lst = ['2018-04-23']


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

    # dem_fp = '/data/blizzard/tuolumne/common_data/topo/tuolx_dem_50m.ipw'
    # gisPath = '/home/micahsandusky/Code/awsfTesting/initUpdate/'
    # maskPath = os.path.join(gisPath, 'tuolx_mask_50m.ipw')
    dem_fp = '/data/blizzard/sanjoaquin/common_data/topo/SJ_dem_50m.ipw'
    gisPath = '/data/blizzard/sanjoaquin/common_data/topo/'
    maskPath = os.path.join(gisPath, 'SJ_Millerton_mask_50m.ipw')
    mask = ipw.IPW(maskPath).bands[0].data[:]
    #date_lst = ['2015-06-08']

    output_path = os.path.join(fpdir, 'wy{}'.format(wy))
    fname = 'flight_depths_{}'.format(basin)
    nanval = -9999.0
    nanup = 1000.0


    # #### Now actually do the stuff ####
    # date to use for finding wy
    fname = fname+'_{}'.format(tmpwy)

    # get topo stats from dem
    ts = get_topo_stats(dem_fp, filetype = 'ipw')
    x = ts['v'] + ts['dv']*np.arange(ts['nx'])
    y = ts['u'] + ts['du']*np.arange(ts['ny'])

    # get depth array
    depth_arr = read_flight(fp_lst, ts, nanval = nanval, nanup = nanup)
    #print(depth_arr)
    # create netcdfs
    ds = output_files(output_path, fname, start_date, x,  y)

    # write to file
    for idt, dt in enumerate(date_lst):
        data = depth_arr[idt,:]*mask
        output_timestep(ds, data, dt, idt, start_date)

    # close file
    ds.close()


if __name__ =='__main__':
    run()
