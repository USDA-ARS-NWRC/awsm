from smrf import ipw
import numpy as np
import os
import pandas as pd

# User inputs:
date_mmdd = '0608' # date in MMDD format for lidar file.
wy = '2015'    # Water year working in 'YYYY'.
wy2 = '2015'   # Water year of lidar survey.
wyhr = '5999'  # Hour number of last daily isnobal image (day before lidar @ 23:00)
update_num = '10' # Span of updates.  1 is first update, 2 is second, etc.
                    # Has to do with directory naming convention I have
                    # used. "4.5" means we are creating a lidar-updated
                    # init file for the day of the fourth flight.
basePath = os.path.join('/Volumes/data/blizzard/Tuolumne/aso-wy', str(wy[-2:-1]))
runDir = 'runs'
dataDir = 'data'
initDir = 'init'

out_file = 'init{}_update'.format(wyhr)
filetype = 'ascii' # Either 'ipw' or 'ascii' at this point.

activeLayer = 0.25 # Set the active layer depth to be used for iSnobal model run.
Buf = 400  # Buffer size (in cells) for the interpolation to search over.

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
    q = rawinput('What is the previous update? (Currently making init_{})'.format(update_num))
    previous_update_dir = 'run.{}'.format(q)
    output_dir = 'output_update'
    add_in = '_update'
else:
    previous_update_dir = 'run.'.format(previous_update_dir)
    output_dir = 'output_update'


gisPath = '/Volumes/data/blizzard/Tuolumne/common_data/topo/'
chdir(os.path.join(basePath,dataDir))
runPath = os.path.join(basePath,runDir,previous_update_dir,output_dir)
# last_snow_image = loadIPW_v3([runPath 'snow.' wyhr])
last_snow_image = ipw.IPW(os.path.join(runPath, 'snow.{}'.format(wyhr)))

demPath = os.path.join(gisPath,'tuolx_dem_50m_int.'.format(filetype[0:2]) )
if int(wy) <= 2015: # Model domain was only above Hetchy before 2016.
    maskPath = os.path.join(gisPath,'tuolx_hetchy_mask_50m.'.format(filetype[0:2]))
else:
    maskPath = os.path.join(gisPath, 'tuolx_mask_50m.'.format(filetype[0:2]) )

z0Path = os.path.join(gisPath, 'tuolx_z0_50m.'.format(filetype[0:2]))
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
    # [dem, R] = arcgridread_v2(demPath)
    # mask = arcgridread_v2(maskPath)
    # z0 = arcgridread_v2(z0Path)
    dem = np.genfromtxt(demPath, dtype='float', skipheader=6)
    mask = np.genfromtxt(maskPath, dtype='int', skipheader=6)
    z0 = np.genfromtxt(z0Path, dtype = 'float', skipheader=6)
    # [x, y] = arcticks(dem, R)

x = self.v + self.dv*np.arange(self.nx)
y = self.u + self.du*np.arange(self.ny)
[XX,YY]=meshgrid(x,y)

# nrows = length(y)
# ncols = length(x)
nrows = self.ny
ncols = self.nx


##  Update the snow depths in the initialization file using ASO lidar:
Path='/Volumes/data/blizzard/Tuolumne/lidar/snowon/{}/gridded_asc/'.format(wy2)
filename = 'TB{}{}_SUPERsnow_depth'.format(wy2, date_mmdd)
# [D, R] = arcgridread_v2([Path filename '.asc'])
# [xs, ys] = arcticks(D, R)
D = np.genfromtxt(Path filename+'.asc', dtype = 'float', skipheader=6)
# [xs, ys] = arcticks(D, R)


## For 2016 only, add NaN columns and rows to match dem and iSnobal
## results...
# D = cat(2, NaN(size(D,1), 312), D);
# D = cat(1, NaN(331, size(D,2)), D, NaN(1, size(D,2)));
## Then mask the image to the Hetchy basin to not update Cherry/Eleanor.
# maskHetchy = arcgridread_v2(['/Volumes/data/blizzard/Tuolumne/common_data' ...
#     '/topo/tuolx_hetchy_mask_50m.asc']);
# D(maskHetchy == 0) = NaN;

# Just for experimentation, change the last_snow_image to the image before
# the previous flight (troubleshooting update 5.6 in 2014:
# previous_update_dir = num2str(str2double(previous_update_dir) - 1.1);

z_s = last_snow_image.bands[0].data # Get modeled depth image.
# z_s(mask==0) = NaN;

##  Special case - 20160607
# I am trying an update with only Tuolumne Basin data where I will mask in
# Cherry and Eleanor to create a hybrid iSnobal/ASO depth image.
tempASO = D
tempASO[np.isnan(D)] = 0
tempiSnobal = z_s
tuolx_mask = mask
tempASO[tuolx_mask == 1] = 0
tempiSnobal[tuolx_mask == 1] = 0
I_ASO = tempASO == 0
tempASO[I_ASO] = tempiSnobal[I_ASO]
tempASO[tuolx_mask == 1] = D[tuolx_mask ==1]
D = tempASO

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
z_s[m_s == 0] = 0
density[m_s == 0] = 0
T_s[m_s == 0] = -75
T_s_l[m_s == 0] = -75
T_s_0[m_s == 0] = -75
h2o_sat[m_s == 0] = 0
z_s[density > 0 && z_s == 0] = u_depth[2]

rho = density
D[D < 0.05] = 0 # Set shallow snow (less than 5cm) to 0.
D[mask == 0] = np.nan # Set out of watershed cells to NaN
rho[mask == 0] = np.nan # Set out of watershed cells to NaN
tot_pix = ncols * nrows # Get number of pixels in domain.

I_model = z_s == 0 # Snow-free pixels in the model.
modelDepth = tot_pix - size(I_model, 1) # # of pixels with snow (model).
I_lidar = find(D == 0 | np.isnan(D)) # Snow-free pixels from lidar.
lidarDepth = tot_pix - size(I_lidar, 1) # # of pixels with snow (lidar).
I_rho = density == 0 # Snow-free pixels upon importing.
modelDensity = tot_pix - size(I_rho, 1) # # of pixels with density (model).

# display(sprintf(['\nJust After Importing.\n' ...
#                   'Number of modeled cells with snow depth: ' ...
#                   num2str(modelDepth) '\n' ...
#                   'Number of modeled cells with density: ' ...
#                   num2str(modelDensity) '\n' ...
#                   'Number of lidar cells measuring snow: ' ...
#                   num2str(lidarDepth) '\n']))

print('\nJust After Importing.\n \
        Number of modeled cells with snow depth: {}\n \
        Number of modeled cells with density: {}\n \
        Number of lidar cells measuring snow: {}'.format(float(modelDepth),
        float(modelDensity),float(lidarDepth) ) )

rho[D == 0] = 0 # Find cells without lidar snow and set the modeled density to zero.
rho[rho == 0] = np.nan # Set all cells with no density to NaN.

T_s_0[D == 0] = np.nan # Find cells without lidar snow and set the active layer temp to NaN.
T_s_0[T_s_0 <= -75] = np.nan # Change isnobal no-values to NaN.

T_s_l[D == 0] = np.nan # Find cells without lidar snow and set the lower layer temp to NaN.
T_s_l[T_s_l <= -75] = np.nan # Change isnobal no-values to NaN.

T_s[D == 0] = np.nan # Find cells without lidar snow and set the snow temp to np.nan.
T_s[T_s <= -75] = np.nan # Change isnobal no-values to NaN.

h2o_sat[D == 0] = np.nan # Find cells without lidar snow and set the h2o saturation to NaN.
h2o_sat[h2o_sat == -75] = np.nan # Change isnobal no-values to NaN.

I_rho = np.isnan(rho) # Snow-free pixels before interpolation
#modelDensity = tot_pix - size(I_rho, 1)
modelDensity = tot_pix - I_rho.shape[0]
# display(sprintf(['\nBefore Interpolation.\n' ...
#                   'Number of modeled cells with snow depth: ' ...
#                   num2str(modelDepth) '\n' ...
#                   'Number of modeled cells with density: ' ...
#                   num2str(modelDensity) '\n' ...
#                   'Number of lidar cells measuring snow: ' ...
#                   num2str(lidarDepth) '\n']))

print('\nBefore Interpolation.\n \
        Number of modeled cells with snow depth: {}\n \
        Number of modeled cells with density: {}\n \
        Number of lidar cells measuring snow: {}'.format(float(modelDepth),
        float(modelDensity),float(lidarDepth) ) )

##  Now find cells where lidar measured snow, but Isnobal simulated no snow:
I = np.isnan(rho) && D>0
I_25 = z_s <= (activeLayer * 1.20) && D >= activeLayer # find cells with lidar
    # depth greater than, and iSnobal depths less than, the active layer
    # depth. Lower layer temperatures of these cells will need to be
    # interpolated from surrounding cells with lower layer temperatures.
    # This happens AFTER the interpolation of all the other variables
    # below.  If cell has snow depth 120# of set active layer depth, then
    # the lower layer temp will be replaced by an areal interpolated value
    # from surrounding cells with lower layer temps and depths greater than
    # 120% of active layer.

# Interpolate over these cells to come up with values for them.
#[X,Y] = meshgrid(1:ncols,1:nrows)
X , Y = np.meshgrid(range(ncols),range(nrows))
# Bufferize the arrays:
rho_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),rho,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))
T_s_0_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),T_s_0,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))
T_s_l_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),T_s_l,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))
T_s_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),T_s,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))
h2o_buf = cat(2,NaN(nrows+2*Buf,Buf),cat(1,NaN(Buf,ncols),h2o_sat,NaN(Buf,ncols)),NaN(nrows+2*Buf,Buf))


###################### hopefully fixed for loop logic below

for i in range(len(I)): # Loop through cells with D > 0 and no iSnobal density,
                  # active layer temp, snow temp, and h2o saturation.
    xt = X[I[i]]+Buf # Add the buffer to the x coords.
    yt = Y[I[i]]+Buf # Add the buffer to the y coords.
    # n=11:10:(Buf+1): # Number of cells in averaging window
    n = range(10,Buff+1,10): # Number of cells in averaging window
    for j in range(len(n)): # Loop through changing buffer windows until enough
                      # cells are found to calculate an average.
        xl = xt-(n[j]-1)/2
        xh = xt+(n[j]-1)/2
        yl = yt-(n[j]-1)/2
        yh = yt+(n[j]-1)/2
        window = rho_buf[yl:yh,xl:xh]
        qq = np.isnan(window) # find number of pixels with a value.
        if len(qq) > 10:
            val = np.nanmean(window[:])
            rho[I[i]] = val  # Interpolate for density (just a windowed mean)
            window = T_s_0_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:])
            T_s_0[I[i]] = val # Interpolate for active snow layer temp
            # Handle the lower layer temp in the following for-loop.
            window=T_s_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:])
            T_s[I[i]] = val # Interpolate for avg snow temp
            window = h2o_buf[yl:yh,xl:xh]
            val = np.nanmean(window[:]
            h2o_sat[I[i]] = val # Interpolate for liquid water saturation
        elif np.sum(qq) <= 10:
            break

        if np.isnan( rho[I[i]] ) == 0:
            break

###################### hopefully fixed for loop logic below

# Now loop over cells with D > activelayer > z_s.  These cells were being
# assigned no temperature in their lower layer (-75) when they needed to
# have a real temperature.  Solution is to interpolate from nearby cells
# using an expanding moving window search.
for ii in range(len(I_25)):
    xt = X[I_25[ii]] + Buf # Add the buffer to the x coords.
    yt = Y[I_25[ii]] + Buf # Add the buffer to the y coords.
    n = 11:10:(Buf+1) # Number of cells in averaging window
    for jj in range(len(n)): # Loop through changing buffer windows until enough
                      # cells are found to calculate an average.
        xl = xt - (n[jj]-1)/2
        xh = xt + (n[jj]-1)/2
        yl = yt - (n[jj]-1)/2
        yh = yt + (n[jj]-1)/2
        window = T_s_l_buf[yl:yh,xl:xh]
        val = nanmean(window[:])
        T_s_l[I_25[ii]] = val # Interpolate for lower layer temp
        ################ fix this to be pyton logic
        if np.isnan(T_s_l[I_25[ii]]) == False:
            break

iq = np.isnan(D) & np.isfinite(rho)
rho[iq] = np.nan # Once more, change cells with no lidar snow to have np.nan density.

# Find occurance where cell has depth and density but no temperature.
# Delete snowpack from this cell.
iq2 = np.isnan(T_s) & np.isfinite(rho)
D[iq2] = 0
rho[iq2] = np.nan

I_lidar = D == 0 | np.isnan(D) # Snow-free pixels from lidar.
lidarDepth = tot_pix - size(I_lidar, 1) # # of pixels with snow (lidar).
I_rho = np.isnan(rho)  # Snow-free pixels after interpolation
modelDensity = tot_pix - size(I_rho, 1)

print('\nAfter Interpolation.\n \
        Number of modeled cells with snow depth: {}\n \
        Number of modeled cells with density: {}\n \
        Number of lidar cells measuring snow: {}'.format(float(modelDepth),
        float(modelDensity),float(lidarDepth) ) )

##  Reset NaN's to the proper values for Isnobal:
#if size(I_lidar, 1) ~= size(I_rho, 1)
if I_lidar.shape[0] ~= I_rho.shape[0]:
    raise ValueError('/nLidar depths do not match interpolated model densities.  Try changing buffer parameters./n')

rho[I_rho] = 0 # rho is the updated density map.
D[rho == 0] = 0 # D is lidar snow depths, I_rho is where no snow exists.
I_25_new = D <= activeLayer # find cells with lidar depth less than 25 cm
    # These cells will have the corresponding lower layer temp changed to
    # -75 (no value) and the upper layer temp will be set to equal the
    # average snowpack temp in that cell.
T_s[rho == 0] = -75 # T_s is the average snow temperature in a cell. Is NaN (-75) for all rho = 0.
T_s_0[rho == 0] = -75 # T_s_0 is the updated active (upper) layer.  Is >0 for everywhere rho is >0.
T_s_0[I_25_new] = T_s(I_25_new) # If lidar depth <= 25cm, set active layer temp to average temp of cell
T_s_l[I_25_new] = -75
T_s_l[np.isnan(T_s_l)] = -75
h2o_sat[rho == 0] = 0

##
# Test for missing sim cells where snow was measured by lidar:
snow_mask = D
snow_mask[D > 0] = 1
#figure(1);clf;imagesc(snow_mask);colorbar

rho_mask = rho;
rho_mask[rho>0] = 1
#figure(2);clf;imagesc(snow_mask - rho_mask);colorbar

T_s_0_mask = T_s_0
T_s_0_mask[T_s_0 > -75] = 1
T_s_0_mask[T_s_0 == -75] = 0
#figure(3);clf;imagesc(snow_mask - T_s_0_mask);colorbar

T_s_l_mask = T_s_l
T_s_l_mask[T_s_l > -75] = 1
T_s_l_mask[T_s_l == -75] = 0
#figure(4);clf;imagesc(snow_mask - T_s_l_mask);colorbar

T_s_mask = T_s
T_s_mask[T_s_l <= -75] = 0
T_s_mask[T_s > -75] = 1;
#figure(5);clf;imagesc(snow_mask - T_s_mask);colorbar

h2o_mask = h2o_sat
h2o_mask[rho == 0] = 0
h2o_mask[h2o_sat > 0] = 1
#figure(6);clf;imagesc(snow_mask - h2o_mask);colorbar

# Test - Look for locations where lidar depths are much different from model.
Diff = D - z_s
Diff[mask == 0] = np.nan
# q = D(882:1049,698:869);
# qx = x(698:869);
# qy = y(882:1049);

#figure(100);clf;imagesc(Diff);colorbar;

# set(gca,'YDir','normal');

# pbaspect([ncols nrows 1])
# save(['/Volumes/BigRAID/ASO/ASO-tuolumne/gis/Distribution_files/' wy ...
#       '/Delta_Lidar_iSnobal_' wy date_mmdd '.mat'], 'Diff')


chdir(initDir)

i_out = ipw.IPW()
i_out.new_band(dem)
i_out.new_band(z0)
i_out.new_band(D)
i_out.new_band(T_s_0)
i_out.new_band(T_s_l)
i_out.new_band(T_s)
i_out.new_band(h2o_sat)
i_out.add_geo_hdr([self.u, self.v], [self.du, self.dv], self.units, self.csys)
i_out.write(os.path.join(self.pathinit,out_file+'.ipw'), nbits)

##  Write the file:
# arcgridwrite('band0.asc',XX, YY,dem,'precision',0)
# arcgridwrite('band1.asc',XX, YY,z0,'precision',3)
# arcgridwrite('band2.asc',XX, YY,D,'precision',3)
# arcgridwrite('band3.asc',XX, YY,rho,'precision',0)
# arcgridwrite('band4.asc',XX, YY,T_s_0,'precision',4)
# arcgridwrite('band5.asc',XX, YY,T_s_l,'precision',3)
# arcgridwrite('band6.asc',XX, YY,T_s,'precision',4)
# arcgridwrite('band7.asc',XX, YY,h2o_sat,'precision',4)
#
# nr = num2str(nrows)
# nc = num2str(ncols)
# string0=['tail -' nr ' band0.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band0.ipw']
# string1=['tail -' nr ' band1.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band1.ipw']
# string2=['tail -' nr ' band2.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band2.ipw']
# string3=['tail -' nr ' band3.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band3.ipw']
# string4=['tail -' nr ' band4.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band4.ipw']
# string5=['tail -' nr ' band5.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band5.ipw']
# string6=['tail -' nr ' band6.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band6.ipw']
# string7=['tail -' nr ' band7.asc | text2ipw -l ' nr ' -s ' nc ' -n 16 > band7.ipw']
# string8=['mux band0.ipw band1.ipw band2.ipw band3.ipw band4.ipw band5.ipw band6.ipw band7.ipw > ' out_file '.ip']
# string9=['mkgeoh -o ' num2str(y(1)) ',' num2str(x(1)) ' -d -50,50 -u ' ...
#          'meters -c UTM ' out_file '.ip > ' out_file '.ipw; rm ' out_file '.ip'];
# string10='rm band*'

# system(string0)
# system(string1)
# system(string2)
# system(string3)
# system(string4)
# system(string5)
# system(string6)
# system(string7)
# system(string8)
# system(string9)
# system(string10)


##  Import newly-created init file and look at images to make sure they line up:


d=ipw.IPW(out_file+'.ipw')
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
snow_mask(z_s == 0) = 0
snow_mask(z_s > 0) = 1

rho_mask = rho
rho_mask(rho > 0) = 1

T_s_0_mask = T_s_0
T_s_0_mask(T_s_0 > -75) = 1
T_s_0_mask(T_s_0 == -75) = 0

T_s_l_mask = T_s_l
T_s_l_mask(T_s_l > -75) = 1
T_s_l_mask(T_s_l == -75) = 0

T_s_mask = T_s
T_s_mask(T_s == -75) = 0
T_s_mask(T_s > -75) = 1

h2o_mask = h2o_sat
h2o_mask(h2o_sat>0)=1

# figure(11);clf;imagesc(snow_mask - rho_mask);colorbar;pbaspect([ncols nrows 1])
# figure(12);clf;imagesc(snow_mask - T_s_0_mask);colorbar;pbaspect([ncols nrows 1])
# figure(13);clf;imagesc(snow_mask - T_s_l_mask);colorbar;pbaspect([ncols nrows 1])
# figure(14);clf;imagesc(snow_mask - T_s_mask);colorbar;pbaspect([ncols nrows 1])
# figure(15);clf;imagesc(snow_mask - h2o_mask);colorbar;pbaspect([ncols nrows 1])
