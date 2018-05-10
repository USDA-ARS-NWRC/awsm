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

print("This utility will gather all netcdf files from listed directories "
      "and combine them into one file")

fmt = '%Y-%m-%d %H:%M:%S'
# chunk size
cs = (6, 10, 10)

# =========================================================================
# Input section
# =========================================================================
fp_list = ['/home/micahsandusky/Code/AWSM/test_data/RME_run/output/rme/devel/wy1998/rme_test/runs/run1464_1680/output',
           '/home/micahsandusky/Code/AWSM/test_data/RME_run/output/rme/devel/wy1998/rme_test/runs/run1560_1800/output',
           '/home/micahsandusky/Code/AWSM/test_data/RME_run/output/rme/devel/wy1998/rme_test/runs/run1800_1920/output'
           ]

# names of files to combine
em_name = 'em.nc'
snow_name = 'snow.nc'

# where to save the files
out_snow_fp = '/home/micahsandusky/Code/AWSM/test_data/RME_run/output/rme/snow.nc'
out_em_fp = '/home/micahsandusky/Code/AWSM/test_data/RME_run/output/rme/em.nc'

# whether or not to delete duplicates
delete_duplicates = True


def avoid_duplicate(dates, var):
    """
    dates: np array of dates
    var: 3d np array for variabbles

    Get rid of duplicate dates for this var,
    but keep the first one.
    """
    # list of deleted indices
    deleted = []
    # loop through and compare
    for idt, d in enumerate(dates):
        deld = np.where(dates == d)
        # print(deld)
        # go delete all but first entry
        for dd in deld[0][1:]:
            if dd not in deleted:
                print('deleting duplicate {}'.format(d))
                var = np.delete(var, (dd), axis=0)
                deleted.append(dd)

    return var


def combine_nc(tot, old):
    """
    Combine netcdfs
    Args:
        tot: total netcdf for all stuff
        old: dictionary of netcdf to combine
    Returns:
        total netcdf
    """
    dont_do = ['time', 'x', 'y']
    # set global parameters
    dimensions = ('time', 'y', 'x')

    # create the dimensions
    tot.createDimension('time', None)
    tot.createDimension('y', old[0].dimensions['y'].size)
    tot.createDimension('x', old[0].dimensions['x'].size)

    # create some variables
    tot.createVariable('time', 'f', dimensions[0])
    tot.createVariable('y', 'f', dimensions[1])
    tot.createVariable('x', 'f', dimensions[2])

    setattr(tot.variables['time'], 'units', old[0].variables['time'].units)
    setattr(tot.variables['time'], 'calendar', old[0].variables['time'].calendar)
    tot.variables['x'][:] = old[0].variables['x'][:]
    tot.variables['y'][:] = old[0].variables['y'][:]

    # set units and description
    var_lst = [f for f in old[0].variables if f not in dont_do]
    for i, v in enumerate(var_lst):

        tot.createVariable(v, 'f', dimensions[:3], chunksizes=cs)
        setattr(tot.variables[v], 'units', old[0].variables[v].units)
        setattr(tot.variables[v], 'description', old[0].variables[v].description)

    # =======================================================================
    # Start reading in and combining data
    # =======================================================================
    # combine time array
    for idnc in range(len(old.keys())):
        onc = old[idnc]
        t_units = onc.variables['time'].units
        nc_calendar = onc.variables['time'].calendar
        if idnc == 0:
            time = onc.variables['time'][:]
            nc_dates = nc.num2date(time, t_units, nc_calendar)
        else:
            time = onc.variables['time'][:]
            nc_dates = np.concatenate((nc_dates, nc.num2date(time, t_units, nc_calendar)),
                                      axis=0)

    t_units = old[0].variables['time'].units
    nc_calendar = old[0].variables['time'].calendar

    # loop through variables not equal to time
    for i, v in enumerate(var_lst):
        print('Combining {}'.format(v))
        # loop through netcdfs and concatenate
        for idnc in range(len(old.keys())):
            onc = old[idnc]
            # set up and concatenate variables
            if idnc == 0:
                var = onc.variables[v][:]
            else:
                varnew = onc.variables[v][:]
                var = np.concatenate((var, varnew), axis=0)

        # avoid having duplicates
        if delete_duplicates:
            var = avoid_duplicate(nc_dates, var)
        # save in total netcdf
        tot.variables[v][:] = var[:]

        # clean up
        del(var)
        del(varnew)

    # save dates
    if delete_duplicates:
        nc_dates = avoid_duplicate(nc_dates, nc_dates)
    tot.variables['time'][:] = nc.date2num(nc_dates, t_units, calendar=nc_calendar)
    # sync and close files
    tot.sync()
    return tot


def run():

    # =========================================================================
    # Read in files
    # =========================================================================
    snow_files = [os.path.join(f, snow_name) for f in fp_list]
    em_files = [os.path.join(f, em_name) for f in fp_list]
    snow_ds = {}
    em_ds = {}
    print('Opening netcdf files')
    for idf, (fs, fe) in enumerate(zip(snow_files, em_files)):
        snow_ds[idf] = nc.Dataset(fs, 'r')
        em_ds[idf] = nc.Dataset(fe, 'r')

    # =========================================================================
    # Set up total file based on first file
    # =========================================================================

    em_tot = nc.Dataset(out_em_fp, 'w')
    snow_tot = nc.Dataset(out_snow_fp, 'w')

    print('Setting attributes of new files based on first old file')

    em_tot = combine_nc(em_tot, em_ds)
    snow_tot = combine_nc(snow_tot, snow_ds)

    # add last modified and which files combined to make it
    h = '[{}] Data added or updated'.format(
        datetime.now().strftime(fmt))
    h1 = 'Data created from {}'.format(snow_files)
    h2 = 'Data created from {}'.format(em_files)
    setattr(snow_tot, 'last_modified', h)
    setattr(em_tot, 'last_modified', h)
    setattr(snow_tot, 'created_from', h1)
    setattr(em_tot, 'created_from', h2)

    # close all netcdf files
    for key, value in snow_ds.items():
        value.close()
    for key, value in em_ds.items():
        value.close()

    em_tot.sync()
    snow_tot.sync()
    em_tot.close()
    snow_tot.close()


if __name__ =='__main__':
    run()
