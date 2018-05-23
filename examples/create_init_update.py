from smrf import ipw
import numpy as np
import os
import pandas as pd
from matplotlib import pyplot as plt
from netCDF4 import Dataset
import netCDF4 as nc

# User inputs:
date_mmdd = '0608' # date in MMDD format for lidar file.
wy = '2015'    # Water year working in 'YYYY'.
wy2 = '2015'   # Water year of lidar survey.
wyhr = '5999'  # Hour number of last daily isnobal image (day before lidar @ 23:00)
update_num = '10' # Span of updates.  1 is first update, 2 is second, etc.
                    # Has to do with directory naming convention I have
                    # used. "4.5" means we are creating a lidar-updated
                    # init file for the day of the fourth flight.
# basePath = os.path.join('/data/blizzard/Tuolumne/aso-wy', str(wy[-2:-1]))
runDir = 'runs'
dataDir = 'data'
initDir = 'init'

out_file = 'init{}_update_new'.format(wyhr)
filetype = 'ipw' # Either 'ipw' or 'ascii' at this point.

activeLayer = 0.25 # Set the active layer depth to be used for iSnobal model run.
Buf = 400  # Buffer size (in cells) for the interpolation to search over.

u = 4246192
v =  238672
du = -50
dv = 50
nx = 1374
ny = 1339
nbits =  16
units = 'm'
csys = 'UTM'
# pathinit = '/home/micahsandusky/Code/awsfTesting/initUpdate/'
pathinit = '/home/micahsandusky/Code/awsfTesting/newupdatetest'

# End User input.**************************
##  Begin opening files and assigning names.
# Lookup last daily isnobal image:
previous_update_dir = int(round(int(update_num)*10)/10 - 1.1)
add_in = '_update'
if float(previous_update_dir) < 1 :
    previous_update_dir = 'All_Runs'
    output_dir = 'output'
    add_in = ''
elif float(previous_update_dir) >= 8 :
    q = raw_input('What is the previous update? (Currently making init_{})'.format(update_num))
    previous_update_dir = 'run.{}'.format(q)
    output_dir = 'output_update'
    add_in = '_update'
else:
    previous_update_dir = 'run.'.format(previous_update_dir)
    output_dir = 'output_update'


#gisPath = '/data/blizzard/Tuolumne/common_data/topo/'
gisPath = '/home/micahsandusky/Code/awsfTesting/initUpdate/'
###chdir(os.path.join(basePath,dataDir))
###runPath = os.path.join(basePath,runDir,previous_update_dir,output_dir)
#last_snow_image = ipw.IPW(os.path.join(runPath, 'snow.{}'.format(wyhr)))
#last_snow_image = ipw.IPW('/home/micahsandusky/Code/awsfTesting/initUpdate/snow.5999')
#last_snow_image = ipw.IPW('/home/micahsandusky/Code/awsfTesting/newupdatetest/snow.5999')
last_snow_image = ipw.IPW('/home/micahsandusky/Code/awsfTesting/newupdatetest/snow.2879')

demPath = os.path.join(gisPath,'tuolx_dem_50m.{}'.format(filetype[0:3]) )
if int(wy) <= 2015: # Model domain was only above Hetchy before 2016.
    maskPath = os.path.join(gisPath,'tuolx_hetchy_mask_50m.{}'.format(filetype[0:3]))
else:
    maskPath = os.path.join(gisPath, 'tuolx_mask_50m.{}'.format(filetype[0:3]) )

z0Path = os.path.join(gisPath, 'tuolx_z0_50m.{}'.format(filetype[0:3]))
if filetype == 'ipw':
    demstruct = ipw.IPW(demPath)
    dem=demstruct.bands[0].data
    mask = ipw.IPW(maskPath)
    mask=mask.bands[0].data
    z0 = ipw.IPW(z0Path)
    z0 = z0.bands[0].data
    # x = demstruct.x # get x & y coords
    # y=demstruct.y
elif strcmp(filetype, 'ascii'):
    dem = np.genfromtxt(demPath, dtype='float', skip_header=6)
    mask = np.genfromtxt(maskPath, dtype='int', skip_header=6)
    z0 = np.genfromtxt(z0Path, dtype = 'float', skip_header=6)
    # [x, y] = arcticks(dem, R)

##  Update the snow depths in the initialization file using ASO lidar:
fp = './flight_depths_2017.nc'
ds = Dataset(fp, 'r')
D_all = ds.variables['depth'][:]
x = ds.variables['x'][:]
y = ds.variables['y'][:]
times = ds.variables['time']
ts = times[:]
t = nc.num2date(ts, times.units, times.calendar)
time1 = t[0]
D = D_all[0,:]

XX,YY = np.meshgrid(x,y)

nrows = len(y)
ncols = len(x)

# Path='/data/blizzard/Tuolumne/lidar/snowon/{}/gridded_asc/'.format(wy2)
# Path = '/home/micahsandusky/Code/awsfTesting/initUpdate/'
# filename = 'TB{}{}_SUPERsnow_depth'.format(wy2, date_mmdd)
# D = np.genfromtxt(os.path.join(Path,'{}.asc'.format(filename) ), dtype = 'float', skip_header=6)

# Just for experimentation, change the last_snow_image to the image before
# the previous flight (troubleshooting update 5.6 in 2014:
# previous_update_dir = num2str(str2double(previous_update_dir) - 1.1);

z_s = last_snow_image.bands[0].data # Get modeled depth image.
# z_s(mask==0) = NaN;

##  Special case - 20160607
# I am trying an update with only Tuolumne Basin data where I will mask in
# Cherry and Eleanor to create a hybrid iSnobal/ASO depth image.
tempASO = D.copy()
tempASO[np.isnan(D)] = 0.0
tempiSnobal = z_s.copy()
tuolx_mask = mask.copy()
tempASO[tuolx_mask == 1] = 0.0
tempiSnobal[tuolx_mask == 1] = 0.0
I_ASO = (tempASO == 0.0)
tempASO[I_ASO] = tempiSnobal[I_ASO]
tempASO[tuolx_mask == 1] = D[tuolx_mask == 1]
D = tempASO.copy()

##  Continue as before:
density = last_snow_image.bands[1].data # Get density image.
## ## ## ## ## ## ## ## ## %
# SPECIAL CASE... insert adjusted densities here:
# density = arcgridread_v2(['/Volumes/data/blizzard/Tuolumne/lidar/snowon/2017' ...
#                 '/adjusted_rho/TB2017' date_mmdd '_operational_rho_ARSgrid_50m.asc']);
## ## ## ## ## ## ## ## ## %
m_s = last_snow_image.bands[2].data # Get SWE image.
T_s_0=last_snow_image.bands[4].data # Get active snow layer temperature image
T_s_l=last_snow_image.bands[5].data # Get lower snow layer temperature image
T_s = last_snow_image.bands[6].data # Get average snowpack temperature image
h2o_sat=last_snow_image.bands[8].data # Get liquid water saturation image

# Address problem of bit resolution where cells have mass and density,
# but no depth is reported (less than minimum depth above zero).
u_depth = np.unique(z_s)

z_s[m_s == 0] = 0.0
density[m_s == 0] = 0.0
T_s[m_s == 0] = -75.0
T_s_l[m_s == 0] = -75.0
T_s_0[m_s == 0] = -75.0
h2o_sat[m_s == 0] = 0.0

z_s[ (density > 0) & (z_s == 0) ] = u_depth[1]

rho = density.copy()
D[D < 0.05] = 0.0 # Set shallow snow (less than 5cm) to 0.
D[mask == 0] = np.nan # Set out of watershed cells to NaN
rho[mask == 0] = np.nan # Set out of watershed cells to NaN
tot_pix = ncols * nrows # Get number of pixels in domain.

I_model = np.where(z_s == 0) # Snow-free pixels in the model.
modelDepth = tot_pix - len(I_model[0]) # # of pixels with snow (model).
I_lidar = np.where( (D == 0) | (np.isnan(D) ) ) # Snow-free pixels from lidar.
lidarDepth = tot_pix - len(I_lidar[0]) # # of pixels with snow (lidar).
I_rho = np.where( density == 0 ) # Snow-free pixels upon importing.
modelDensity = tot_pix - len(I_rho[0]) # # of pixels with density (model).


print('\nJust After Importing.\n \
        Number of modeled cells with snow depth: {}\n \
        Number of modeled cells with density: {}\n \
        Number of lidar cells measuring snow: {}'.format(modelDepth, modelDensity, lidarDepth ) )

rho[D == 0.0] = 0.0 # Find cells without lidar snow and set the modeled density to zero.
rho[rho == 0.0] = np.nan # Set all cells with no density to NaN.

T_s_0[D == 0.0] = np.nan # Find cells without lidar snow and set the active layer temp to NaN.
T_s_0[T_s_0 <= -75.0] = np.nan # Change isnobal no-values to NaN.

T_s_l[D == 0.0] = np.nan # Find cells without lidar snow and set the lower layer temp to NaN.
T_s_l[T_s_l <= -75.0] = np.nan # Change isnobal no-values to NaN.

T_s[D == 0.0] = np.nan # Find cells without lidar snow and set the snow temp to np.nan.
T_s[T_s <= -75.0] = np.nan # Change isnobal no-values to NaN.

h2o_sat[D == 0.0] = np.nan # Find cells without lidar snow and set the h2o saturation to NaN.
h2o_sat[mask == 0] = np.nan
#h2o_sat[h2o_sat == -75.0] = np.nan # Change isnobal no-values to NaN.

I_rho = np.where( np.isnan(rho) ) # Snow-free pixels before interpolation
#modelDensity = tot_pix - size(I_rho, 1)
modelDensity = tot_pix - len(I_rho[0])

print('\nBefore Interpolation.\n \
        Number of modeled cells with snow depth: {0}\n \
        Number of modeled cells with density: {1}\n \
        Number of lidar cells measuring snow: {2}'.format(modelDepth, modelDensity, lidarDepth ) )

##  Now find cells where lidar measured snow, but Isnobal simulated no snow:
I = np.where( (np.isnan(rho)) & (D > 0) )
I_25 = np.where( (z_s <= (activeLayer * 1.20)) & (D >= activeLayer) ) # find cells with lidar
    # depth greater than, and iSnobal depths less than, the active layer
    # depth. Lower layer temperatures of these cells will need to be
    # interpolated from surrounding cells with lower layer temperatures.
    # This happens AFTER the interpolation of all the other variables
    # below.  If cell has snow depth 120% of set active layer depth, then
    # the lower layer temp will be replaced by an areal interpolated value
    # from surrounding cells with lower layer temps and depths greater than
    # 120% of active layer.

# Interpolate over these cells to come up with values for them.
#[X,Y] = meshgrid(1:ncols,1:nrows)
X , Y = np.meshgrid(range(ncols),range(nrows))
# Bufferize the arrays:
# rho_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),rho,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))

# make matrices to use in following commands
tmp1 = np.ones((nrows+2*Buf, Buf))
tmp1[:] = np.nan
tmp2 = np.ones((Buf, ncols))
tmp2[:] = np.nan

rho_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,rho,tmp2) ,axis=0),tmp1 ),axis=1)
T_s_0_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s_0,tmp2) ,axis=0),tmp1 ),axis=1)
T_s_l_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s_l,tmp2) ,axis=0),tmp1 ),axis=1)
T_s_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s,tmp2) ,axis=0),tmp1 ),axis=1)
h2o_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,h2o_sat,tmp2) ,axis=0),tmp1 ),axis=1)
plt.imshow(h2o_buf)
plt.colorbar()
plt.show()
plt.imshow(h2o_sat)
plt.colorbar()
plt.show()
plt.imshow(T_s_buf)
plt.colorbar()
plt.show()

print(h2o_buf.shape)
###################### hopefully fixed for loop logic below

for idx, (ix, iy) in enumerate(zip(I[0], I[1])): # Loop through cells with D > 0 and no iSnobal density,
                  # active layer temp, snow temp, and h2o saturation.
    xt = X[ix,iy]+Buf # Add the buffer to the x coords.
    yt = Y[ix,iy]+Buf # Add the buffer to the y coords.
    # n=11:10:(Buf+1): # Number of cells in averaging window
    #n = range(10,Buf+1,10) # Number of cells in averaging window
    n = range(11,Buf+2,10) # Number of cells in averaging window
    for n1 in n: # Loop through changing buffer windows until enough
                      # cells are found to calculate an average.
        xl = xt - (n1 - 1) / 2
        xh = xt + (n1 - 1) / 2
        yl = yt - (n1 - 1) / 2
        yh = yt + (n1 - 1) / 2
        window = rho_buf[yl:yh,xl:xh]
        qq = np.where(np.isnan(window)) # find number of pixels with a value.
        if len(qq[0]) > 10:
            val = np.nanmean(window[:])
            rho[ix,iy] = val  # Interpolate for density (just a windowed mean)
            window = T_s_0_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:])
            T_s_0[ix,iy] = val # Interpolate for active snow layer temp
            # Handle the lower layer temp in the following for-loop.
            window = T_s_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:])
            T_s[ix,iy] = val # Interpolate for avg snow temp
            window = h2o_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:])
            h2o_sat[ix,iy] = val # Interpolate for liquid water saturation
        # what is this doing?
        elif (np.sum(qq[0])*ncols + np.sum( qq[1])*nrows ) <= 10:
        #else:
            break

        # if np.isnan( rho[ix,iy] ) == 0:
        #     break
        if not np.isnan( rho[ix,iy] ):
            break
plt.imshow(h2o_sat)
plt.colorbar()
plt.show()
###################### hopefully fixed for loop logic below

# Now loop over cells with D > activelayer > z_s.  These cells were being
# assigned no temperature in their lower layer (-75) when they needed to
# have a real temperature.  Solution is to interpolate from nearby cells
# using an expanding moving window search.
for ix, iy in zip(I_25[0], I_25[1]):
    xt = X[ix,iy] + Buf # Add the buffer to the x coords.
    yt = Y[ix,iy] + Buf # Add the buffer to the y coords.
    n = range(11,Buf+2,10)
    for jj in n: # Loop through changing buffer windows until enough
                      # cells are found to calculate an average.
        xl = xt - (jj-1)/2
        xh = xt + (jj-1)/2
        yl = yt - (jj-1)/2
        yh = yt + (jj-1)/2
        window = T_s_l_buf[yl:yh,xl:xh]
        val = np.nanmean(window[:])
        T_s_l[ix,iy] = val # Interpolate for lower layer temp
        ################ fix this to be pyton logic
        #if np.isnan(T_s_l[ii]) == False:
        if not np.any(np.isnan(T_s_l[ix,iy])):
            break

iq = (np.isnan(D)) & (np.isfinite(rho))
rho[iq] = np.nan # Once more, change cells with no lidar snow to have np.nan density.

# Find occurance where cell has depth and density but no temperature.
# Delete snowpack from this cell.
iq2 = (np.isnan(T_s)) & (np.isfinite(rho))
D[iq2] = 0
rho[iq2] = np.nan


I_lidar = np.where( (D == 0) | (np.isnan(D) ) ) # Snow-free pixels from lidar.
lidarDepth = tot_pix - len(I_lidar[0]) # # of pixels with snow (lidar).
I_rho = np.where( np.isnan(rho) ) # Snow-free pixels upon importing.
modelDensity = tot_pix - len(I_rho[0]) # # of pixels with density (model).

I_lidaridx = (D == 0) | (np.isnan(D) )  # Snow-free pixels from lidar.
I_rhoidx = np.isnan(rho)  # Snow-free pixels upon importing.

print('\nAfter Interpolation.\n \
        Number of modeled cells with snow depth: {}\n \
        Number of modeled cells with density: {}\n \
        Number of lidar cells measuring snow: {}'.format(modelDepth,modelDensity,lidarDepth ) )

##  Reset NaN's to the proper values for Isnobal:
#if size(I_lidar, 1) ~= size(I_rho, 1)
if len(I_lidar[0]) != len(I_rho[0]):
    raise ValueError('Lidar depths do not match interpolated model densities.  Try changing buffer parameters.')

rho[I_rhoidx] = 0 # rho is the updated density map.
D[rho == 0] = 0 # D is lidar snow depths, I_rho is where no snow exists.
I_25_new = D <= activeLayer # find cells with lidar depth less than 25 cm
    # These cells will have the corresponding lower layer temp changed to
    # -75 (no value) and the upper layer temp will be set to equal the
    # average snowpack temp in that cell.
T_s[rho == 0] = -75 # T_s is the average snow temperature in a cell. Is NaN (-75) for all rho = 0.
T_s_0[rho == 0] = -75 # T_s_0 is the updated active (upper) layer.  Is >0 for everywhere rho is >0.
T_s_0[I_25_new] = T_s[I_25_new] # If lidar depth <= 25cm, set active layer temp to average temp of cell
T_s_l[I_25_new] = -75
T_s_l[np.isnan(T_s_l)] = -75
h2o_sat[rho == 0] = 0

##
# Test for missing sim cells where snow was measured by lidar:
snow_mask = D.copy()
snow_mask[D > 0] = 1
plt.figure(1)
plt.imshow(snow_mask)
plt.title('ASO snow mask')
plt.colorbar()
plt.show()

rho_mask = rho.copy()
rho_mask[rho>0] = 1
plt.figure(2)
plt.imshow(snow_mask - rho_mask)
plt.title('ASO_snowmask - density mask')
plt.colorbar()
plt.show()

T_s_0_mask = T_s_0.copy()
T_s_0_mask[T_s_0 > -75] = 1
T_s_0_mask[T_s_0 == -75] = 0
plt.figure(3)
plt.imshow(snow_mask - T_s_0_mask)
plt.title('snow_mask - T_s_0 mask')
plt.colorbar()
plt.show()

# seems like a lot
T_s_l_mask = T_s_l.copy()
T_s_l_mask[T_s_l > -75] = 1
T_s_l_mask[T_s_l == -75] = 0
plt.figure(4)
plt.imshow(snow_mask - T_s_l_mask)
plt.title('snow_mask - T_s_l mask')
plt.colorbar()
plt.show()

T_s_mask = T_s.copy()
T_s_mask[T_s_l <= -75] = 0
T_s_mask[T_s > -75] = 1;
plt.figure(5)
plt.imshow(snow_mask - T_s_mask)
plt.title('snow_mask - T_s mask')
plt.colorbar()
plt.show()

h2o_mask = h2o_sat.copy()
h2o_mask[rho == 0] = 0
h2o_mask[h2o_sat > 0] = 1
plt.imshow(h2o_sat)
plt.colorbar()
plt.show()
plt.figure(6)
plt.imshow(snow_mask - h2o_mask)
plt.title('snow_mask - h2o mask')
plt.colorbar()
plt.show()

# Test - Look for locations where lidar depths are much different from model.
Diff = D - z_s
Diff[mask == 0] = np.nan

#chdir(initDir)

i_out = ipw.IPW()
i_out.new_band(dem)
i_out.new_band(z0)
i_out.new_band(D)
i_out.new_band(rho)
i_out.new_band(T_s_0)
i_out.new_band(T_s_l)
i_out.new_band(T_s)
i_out.new_band(h2o_sat)
i_out.add_geo_hdr([u, v], [du, dv], units, csys)
i_out.write(os.path.join(pathinit,out_file+'.ipw'), nbits)

##  Import newly-created init file and look at images to make sure they line up:

d=ipw.IPW(os.path.join(pathinit,out_file+'.ipw'))
print('wrote ipw image')

z = d.bands[0].data
z_0 = d.bands[1].data
z_s = d.bands[2].data
rho = d.bands[3].data
T_s_0 = d.bands[4].data
T_s_l = d.bands[5].data
T_s = d.bands[6].data
h2o_sat = d.bands[7].data

##
snow_mask = z_s
snow_mask[z_s == 0] = 0
snow_mask[z_s > 0] = 1

rho_mask = rho
rho_mask[rho > 0] = 1

T_s_0_mask = T_s_0
T_s_0_mask[T_s_0 > -75] = 1
T_s_0_mask[T_s_0 == -75] = 0

T_s_l_mask = T_s_l
T_s_l_mask[T_s_l > -75] = 1
T_s_l_mask[T_s_l == -75] = 0

T_s_mask = T_s
T_s_mask[T_s == -75] = 0
T_s_mask[T_s > -75] = 1

h2o_mask = h2o_sat
h2o_mask[h2o_sat>0]=1

plt.figure(7)
plt.imshow(snow_mask)
plt.colorbar()
plt.show()
plt.figure(8)
plt.imshow(snow_mask - rho_mask)
plt.colorbar()
plt.show()
plt.figure(9)
plt.imshow(snow_mask - T_s_0_mask)
plt.colorbar()
plt.show()
plt.figure(10)
plt.imshow(snow_mask - T_s_l_mask)
plt.colorbar()
plt.show()
plt.figure(11)
plt.imshow(snow_mask - T_s_mask)
plt.colorbar()
plt.show()
plt.figure(12)
plt.imshow(snow_mask - h2o_mask)
plt.colorbar()
plt.show()
