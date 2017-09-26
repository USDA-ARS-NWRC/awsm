'''
Created on Sept 22, 2017
Convert IPW TOPO files to netCDF
@author: Micah prime
'''

import pandas as pd
import numpy as np
from smrf import ipw
import netCDF4 as nc
from datetime import datetime
from matplotlib import pyplot as plt

fp_output = '/home/micahsandusky/Code/workdir/test_ipw_convert/tuol_topo.nc'

dem =         '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_dem_50m.ipw'
mask =        '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_hetchy_mask_50m.ipw'
veg_type =    '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_vegnlcd_50m.ipw'
veg_height =  '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_vegheight_50m.ipw'
veg_k =       '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_vegk_50m.ipw'
veg_tau =     '/data/blizzard/Tuolumne/aso-wy13/data/smrf_outputs/input_backup/tuolx_vegtau_50m.ipw'

u  = 4246192
v  = 238672
du  = -50
dv  = 50
units = 'm'
csys = 'UTM'
nx = 1374
ny = 1339

nbits = 16

print "convert all .ipw output files to netcdf topo files"
# create the x,y vectors
x = v + dv*np.arange(nx)
y = u + du*np.arange(ny)

# create nc file
nc_topo = nc.Dataset(fp_output, 'w',
               format='NETCDF4', clobber=False)
#===============================================================================
# NetCDF TOPO image
#===============================================================================

s = {}
s['name'] = ['veg_height','veg_type','mask','dem','veg_tau','veg_k']
s['file'] = [veg_height, veg_type, mask, dem, veg_tau, veg_k]
s['units'] = ['m','-','-','m','-','-']
s['description'] =['Roughness height of vegetation','NLCD 2011 Classification','Basin mask',
                    'Basin DEM','Vegetation optical transmissivity coefficient',
                    'Vegetation solar extinction coefficient']
s['long_name'] =['Vegetation height','Vegetation type','Mask',
                    'Digital Elevation Map','Optical transmissivity',
                    'Solar extinction']

# create the dimensions
nc_topo.createDimension('y',ny)
nc_topo.createDimension('x',nx)

# create some variables
nc_topo.createVariable('y', 'f', 'y')
nc_topo.createVariable('x', 'f', 'x')

nc_topo.variables['x'][:] = x
nc_topo.variables['y'][:] = y

# snow image
for i,v in enumerate(s['name']):
    nc_topo.createVariable(v, 'f', ['y','x'], chunksizes=(10,10))
    setattr(nc_topo.variables[v], 'units', s['units'][i])
    setattr(nc_topo.variables[v], 'description', s['description'][i])
    setattr(nc_topo.variables[v], 'long_name', s['long_name'][i])

#===============================================================================
# open ipw file, and add to netCDF
#===============================================================================
for f, var in zip(s['file'], s['name']):
    # Read the IPW file
    i = ipw.IPW(f)
    # assign to netcdf
    tmp = i.bands[0].data
    plt.imshow(tmp)
    plt.colorbar()
    plt.show()
    nc_topo.variables[var][:] = i.bands[0].data
    nc_topo.sync()

#===============================================================================
# set attributes
#===============================================================================
# the y variable attributes
nc_topo.variables['y'].setncattr(
        'units',
        'meters')
nc_topo.variables['y'].setncattr(
        'description',
        'UTM, north south')
nc_topo.variables['y'].setncattr(
        'long_name',
        'y coordinate')

# the x variable attributes
nc_topo.variables['x'].setncattr(
        'units',
        'meters')
nc_topo.variables['x'].setncattr(
        'description',
        'UTM, east west')
nc_topo.variables['x'].setncattr(
        'long_name',
        'x coordinate')

# define some global attributes
nc_topo.setncattr_string('Conventions', 'CF-1.6')
nc_topo.setncattr_string('dateCreated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
nc_topo.setncattr_string('history', '[{}] Create netCDF4 file'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
nc_topo.setncattr_string('institution',
        'USDA Agricultural Research Service, Northwest Watershed Research Center')

# close file
nc_topo.close()
