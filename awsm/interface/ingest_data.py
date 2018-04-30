from smrf import ipw
import numpy as np
import os
import pandas as pd
from matplotlib import pyplot as plt
from netCDF4 import Dataset
import netCDF4 as nc


# ###outline
"""
Initialize the updates, stick them in a dictionary or list with the key as the
update date. Only keep ones that are in the daterange.
In this step, make a list of nsteps to run isnobal (between each update and at the end)

Make function to take in last update depths and all necessary bands and do the update
and return necessary bands

Make function to write the update to init file.

Make outer function to loop through each function, output and reassign init file, kick off isnobal runs, call
updates, and so on
"""

def run_update_procedure(myawsm):
    """
    Function to run iSnobal with direct insertion of lidar depths. This function
    incorporates each available lidar image within the time frame and runs
    each section of isnobal
    """

    update_fp = myawsm.update_file
    # read in updates and store both dates and images
    update_info, x, y = initialize_aso_updates(myawsm, update_fp)

    # callculate offset for each section of the run
    update_info, runsteps, offsets, firststeps = calc_offsets_nsteps(myawsm, update_info)

    # run iSnobal up to first update if needed
    if firststeps > 0:
        myawsm.run_for_nsteps = firststeps
        # run isnobal Once
        myawsm.run_isnobal(offset=None)

    # do each update and run again
    for ido, off in enumerate(offsets):
        # find update output file
        # if we're starting with an update
        if firststeps == 0 and ido == 0:
            if mywasm.restart_crash:
                name_crash = 'snow.%04d' % myawsm.restart_hr
                update_snow = os.path.join(myawsm.pathro, name_crash)
            else:
                update_snow = myawsm.prev_mod_file

        else:
            update_snow = find_update_snow(myawsm, off)

        # perform the update and set the init file for iSnobal
        myawsm.init_file = do_update(myawsm, update_info.index[ido],
                                     update_snow, x, y)

        # set nsteps
        mywasm.run_for_nsteps = runsteps[ido]

        # run isnobal again
        myawsm.run_isnobal(offset=off)

def initialize_aso_updates(myawsm, update_fp):
    """
    Read in the ASO update file and parse images by date
    Argument:
            myawsm: instantiated awsm class
            update_fp: file pointer to netCDF with all flights in it
    Return:
            update_info: dictionary of updates
    """

    Buf = myawsm.update_buffer  # Buffer size (in cells) for the interpolation to search over.

    last_snow_image = ipw.IPW('/home/micahsandusky/Code/awsfTesting/newupdatetest/snow.2879')

    ##  Update the snow depths in the initialization file using ASO lidar:
    fp = update_fp
    # read in update files
    ds = Dataset(fp, 'r')
    # get all depths, x, y, time
    D_all = ds.variables['depth'][:]
    x = ds.variables['x'][:]
    y = ds.variables['y'][:]
    times = ds.variables['time']
    ts = times[:]
    # convert time index to dates
    t = nc.num2date(ts, times.units, times.calendar)

    # find wyhr of dates
    t_wyhr = []
    for t1 in t:
        tmp_date = t1.replace(tzinfo=myawsm.tzinfo)
        # get wyhr
        tmpwyhr = int(utils.water_day(tmp_date)[0]*24)
        t_wyhr.append(tmpwyhr)

    t_wyhr = np.array(t_wyhr)

    # make dictionary of updates
    update_info = pd.DataFrame()
    keys = range(1,len(t_wyhr)+1)
    # for idk, k in keys:
    #     update_info[k]
    # set update number
    update_info['number'] = keys
    update_info['date_time'] = t
    update_info['wyhr'] = t_wyhr
    update_info['depth'] = D_all

    return update_info, x, y


def calc_offsets_nsteps(myawsm, update_info):
    """
    Function to calculate the offset for each update run and the number of steps
    the iSnobal run needs to run
    Args:
        myawsm: awsm class
        update_info: pandas dataframe of the update netCDF info
    Returns:
        update_info: update info dataframe filtered to desired updates
        runsteps:    numpy array of runsteps for each section
        offsets:     offset wyhr for each update
        firststeps:  number of steps to run before first update, if any
    """

    t_wyhr = update_info['wyhr'].values
    update_number = update_info['number'].values
    filter_number = update_number
    # filter to correct hourse
    for un in update_number:
        if un not in filter_number:
            update_info = update_info[update_info['number'] != un]

    # filter so we are in the dates
    for tw in t_wyhr:
        if tw < myawsm.start_wyhr - 24:
            update_info = update_info[update_info['wyhr'] != tw]
        if tw > mywasm.end_wyhr:
            update_info = update_info[update_info['wyhr'] != tw]

    # now we are down to the correct wyhrs and update numbers
    t_wyhr = update_info['wyhr'].values
    update_number = update_info['number'].values

    # this is where each run will start from
    offsets = t_wyhr
    # check if a first run with no update is needed to get us up to the first update
    if mywasm.restart_crash:
        test_start_wyhr = myawsm.restart_hr
    # do we need to do that run?
    if offsets[0] - test_start_wyhr <= 0:
        firststeps = 0
    else:
        firststeps = offsets[0] - test_start_wyhr

    runstesps = np.zeros_like(offsets)
    for ido, offs in enumerate(offsets):
        if ido == len(offsets) - 1
            runsteps[ido] = myawsm.end_wyhr - offs
        else:
            runsteps[ido] = offsets[ido+1] - offsets

    return update_info, runsteps, offsets, firststeps

def find_update_snow(myawsm, offset):
    """
    Function to find the nearest, lower ouptut file to perform the update_info
    """
    # get output files so far
    d = sorted(glob.glob("%s/snow*" % myawsm.pathro),
               key=os.path.getmtime)

    d.sort(key=lambda f: os.path.splitext(f))

    hr = []
    for idf, f in enumerate(d):
        # get the hr
        nm = os.path.basename(f)
        head = os.path.dirname(f)
        hr.append(int(nm.split('.')[1]))

    hr = np.array(hr)
    # filter to outputs less than offset
    hr = [h for h in hr if h < offset]
    # find closest
    idx = (np.abs(hr - offset)).argmin()
    offset_hr = int(hr[idx])

    # make sure we are within a day of the update
    if np.abs(offset_hr - offset) > 24:
        raise ValueError('No output in output directory within'
                         ' a day of {} update'.format(offset))

    # set the file to update
    update_snow = os.path.join(myawsm.pathro, 'snow.%04d' % (offset_hr))
    if not os.path.exists(update_snow):
        raise ValueError('Update snow file {} does not exist'.format(update_snow))

    return update_snow


def do_update(myawsm, update_info, update_snow, x, y):
    """
    Function to read in an output file and update it with the lidar depth field
    Argument:
        mywasm: instantiated awsm class
        update_info: update info pandas at correct index
        update_snow: file pointer to snow update image
        x: x vector
        y: y vector
    Returns:
        init_file: file pointer to init image
    """
    D = update_info['depth'].values[0,:]
    print('Shape', D.shape)
    date = update_info['date_time'].values[0]
    wyhr = update_info['wyhr'].values[0]
    update_number = update_info['number'].values[0]

    # mask = myawsm.mask

    XX,YY = np.meshgrid(x,y)

    nrows = len(y)
    ncols = len(x)

    last_snow_image = ipw.IPW(update_snow)

    z_s = last_snow_image.bands[0].data # Get modeled depth image.
    # z_s(mask==0) = NaN;

    ##  Special case - 20160607
    # I am trying an update with only Tuolumne Basin data where I will mask in
    # Cherry and Eleanor to create a hybrid iSnobal/ASO depth image.
    # tempASO = D.copy()
    # tempASO[np.isnan(D)] = 0.0
    # tempiSnobal = z_s.copy()
    # tuolx_mask = myawsm.mask
    # tempASO[tuolx_mask == 1] = 0.0
    # #tempiSnobal[tuolx_mask == 1] = 0.0
    # I_ASO = (tempASO == 0.0)
    # tempASO[I_ASO] = tempiSnobal[I_ASO]
    # tempASO[tuolx_mask == 1] = D[tuolx_mask == 1]
    # D = tempASO.copy()


    ##  Continue as before:
    density = last_snow_image.bands[1].data # Get density image.
    ## ## ## ## ## ## ## ## ## %
    # SPECIAL CASE... insert adjusted densities here:
    # density = arcgridread_v2(['/Volumes/data/blizzard/Tuolumne/lidar/snowon/2017' ...
    #                 '/adjusted_rho/TB2017' date_mmdd '_operational_rho_ARSgrid_50m.asc']);
    ## ## ## ## ## ## ## ## ## %
    m_s = last_snow_image.bands[2].data # Get SWE image.
    T_s_0 = last_snow_image.bands[4].data # Get active snow layer temperature image
    T_s_l = last_snow_image.bands[5].data # Get lower snow layer temperature image
    T_s = last_snow_image.bands[6].data # Get average snowpack temperature image
    h2o_sat = last_snow_image.bands[8].data # Get liquid water saturation image

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
    # D[mask == 0] = np.nan # Set out of watershed cells to NaN
    # rho[mask == 0] = np.nan # Set out of watershed cells to NaN
    tot_pix = ncols * nrows # Get number of pixels in domain.

    I_model = np.where(z_s == 0) # Snow-free pixels in the model.
    modelDepth = tot_pix - len(I_model[0]) # # of pixels with snow (model).
    I_lidar = np.where( (D == 0) | (np.isnan(D) ) ) # Snow-free pixels from lidar.
    lidarDepth = tot_pix - len(I_lidar[0]) # # of pixels with snow (lidar).
    I_rho = np.where( density == 0 ) # Snow-free pixels upon importing.
    modelDensity = tot_pix - len(I_rho[0]) # # of pixels with density (model).


    myawsm._logger.debug('\nJust After Importing.\n \
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
    # h2o_sat[mask == 0] = np.nan
    # h2o_sat[h2o_sat == -75.0] = np.nan # Change isnobal no-values to NaN.

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
    X , Y = np.meshgrid(range(ncols),range(nrows))

    # make matrices to use in following commands
    tmp1 = np.ones((nrows+2*Buf, Buf))
    tmp1[:] = np.nan
    tmp2 = np.ones((Buf, ncols))
    tmp2[:] = np.nan
    # create buffer
    rho_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,rho,tmp2) ,axis=0),tmp1 ),axis=1)
    T_s_0_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s_0,tmp2) ,axis=0),tmp1 ),axis=1)
    T_s_l_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s_l,tmp2) ,axis=0),tmp1 ),axis=1)
    T_s_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,T_s,tmp2) ,axis=0),tmp1 ),axis=1)
    h2o_buf = np.concatenate( (tmp1,np.concatenate( (tmp2,h2o_sat,tmp2) ,axis=0),tmp1 ),axis=1)

    ###################### hopefully fixed for loop logic below

    for idx, (ix, iy) in enumerate(zip(I[0], I[1])): # Loop through cells with D > 0 and no iSnobal density,
                      # active layer temp, snow temp, and h2o saturation.
        xt = X[ix,iy]+Buf # Add the buffer to the x coords.
        yt = Y[ix,iy]+Buf # Add the buffer to the y coords.
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

    # ##################### hopefully fixed for loop logic below

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

    #
    # #chdir(initDir)
    #
    outfile = 'init_{}_wyhr{:04d}.ipw'.format(update_number, wyhr)
    init_file = os.path.join(myawsm.pathinit,out_file)
    i_out = ipw.IPW(init_file)
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
    os.path.info('Wrote ipw image for update {}'.format(wyhr))

    return initfile
