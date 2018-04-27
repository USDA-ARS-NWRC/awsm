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
from awsm.utils.utilities import get_topo_stats

print("This utility takes geoTiff files for depth updates in AWSM and sticks"
      "them into one netCDF for easier use. ")

fmt = '%Y-%m-%d %H:%M:%S'
# chunk size
cs = (6, 10, 10)

# =========================================================================
# Read in tif
# =========================================================================

def arcticks(Z, R):
    '''
    ARCTICKS   return vectors of x- and y-directions from arcgridread
      referencing matrix
    [x,y] = ARCTICKS(Z,R) reads the referencing matrix created by reading
    in an Arc ASCII grid using ARCGRIDREAD or ARCGRIDREAD_V2.  x and y
    correspond to the easting and northing coordinates, respectively, of
    each grid cell CENTER that was read. Remember that ESRI ARC/INFO ASCII
    GRID files store the lower left corner of the lower left pixel!!
    Dimensionally:
    [length(y),length(x)]=size(Z)
    but
    (len(x), len(y)) = Z.shape
    '''
    (n,m) = Z.shape
    x = np.arange(R[2] + (R[1] / 2), R[2] + (R[1] * n) + 1, R[1])  # Counts from W to E.
    y = np.arange(R[5] + (R[3] / 2), R[5] + (R[3] * m) + 1, R[3])  # If R[3] is negative, northing will count from N to S.

    return x,y


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

    for fp in fp_lst:
        D = np.genfromtxt(fp, dtype = float, skip_header=6, filling_values=np.nan)
        if nanval is not None:
            D[D==nanval] = np.nan
        if nanup is not None:
            D[D>nanup] = np.nan
        D[D > 100] = np.nan
        # store value
        data_array[0,:] = D

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

    # user inputs
    #fp_lst = ['/home/micahsandusky/Code/awsfTesting/initUpdate/TB20150608_SUPERsnow_depth.asc']
    fp_lst = ['/home/micahsandusky/Code/awsfTesting/newupdatetest/TB20170129_SUPERsnow_depth.asc']
    dem_fp = '/data/blizzard/tuolumne/common_data/topo/tuolx_dem_50m.ipw'
    #date_lst = ['2015-06-08']
    date_lst = ['2017-01-29']
    output_path = './'
    fname = 'flight_depths'
    nanval = -9999.0
    nanup = 10000.0

    date_lst = [pd.to_datetime(dd) for dd in date_lst]
    print(date_lst)

    # get wy start based on first date in list
    # start_date = pd.to_datetime('2014-10-01 00:00:00')
    tzinfo = pytz.timezone('UTC')
    # date to use for finding wy
    tmp_date = date_lst[0]
    tmp_date = tmp_date.replace(tzinfo=tzinfo)
    # find start of water year
    tmpwy = utils.water_day(tmp_date)[1]
    start_date = pd.to_datetime('{:d}-10-01'.format(tmpwy-1))
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
        data = depth_arr[idt,:]
        output_timestep(ds, data, dt, idt, start_date)

    # close file
    ds.close()


if __name__ =='__main__':
    run()
