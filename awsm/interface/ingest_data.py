from smrf import ipw
import numpy as np
import os
import copy
import pandas as pd
from netCDF4 import Dataset
import netCDF4 as nc
from collections import OrderedDict
import glob

from smrf.utils import utils

C_TO_K = 273.16
FREEZE = C_TO_K

class StateUpdater():
    """
    Class to initialize the updates, perform the updates, and store the needed
    updating info
    """

    def __init__(self, myawsm):
        self.update_fp = myawsm.update_file
        # read in updates and store both dates and images
        update_info, x, y = self.initialize_aso_updates(myawsm, self.update_fp)

        # callculate offset for each section of the run and filter updates
        # update_info, runsteps, offsets, firststeps = self.calc_offsets_nsteps(myawsm, update_info)

        self.x = x
        self.y = y
        self.update_info = update_info
        # self.runsteps = runsteps
        # self.offsets = offsets
        # self.firststeps = firststeps

        # save the dates of each update if there are any updates in the time frame
        self.update_dates = []
        if len(self.update_info > 0):
            self.update_dates = [self.update_info[k]['date_time'] for k in self.update_info.keys()]

        # get necessary variables from awsm class
        self.active_layer = myawsm.active_layer
        # Buffer size (in cells) for the interpolation to search overself.
        self.update_buffer = myawsm.update_buffer

        self._logger = myawsm._logger

        self.ny = myawsm.topo.ny
        self.nx = myawsm.topo.nx
        self.topo = myawsm.topo
        self.pathinit = myawsm.pathinit

    def do_update_pysnobal(self, output_rec, dt):
        """
        Function to update a time step of a pysnobal run by updating the
        output_rec

        Args:
            output_rec:     iPySnobal state variables
            dt:             iPySnobal datetime of timestep
        """
        self._logger.debug('Preparing to update pysnobal')
        # find the correct update number
        ks = self.update_info.keys()
        update_num = [k for k in ks if self.update_info[k]['date_time'] == dt]
        if len(update_num) > 1:
            raise ValueError('Something wrong in pysnobal updating date compare')

        un = update_num[0]

        # get parameters from PySnobal
        m_s = output_rec['m_s']
        T_s_0 = output_rec['T_s_0'] - FREEZE
        T_s_l = output_rec['T_s_l'] - FREEZE
        T_s = output_rec['T_s'] - FREEZE
        h2o_sat = output_rec['h2o_sat']
        z_s = output_rec['z_s']
        density = output_rec['rho']

        # do the updating
        updated_fields = self.hedrick_updating_procedure(m_s, T_s_0, T_s_l, T_s,
                                                         h2o_sat, density, z_s,
                                                         self.x, self.y,
                                                         self.update_info[un])

        # save the fields
        output_rec['m_s'] = updated_fields['D'] * updated_fields['rho']
        output_rec['T_s_0'] = updated_fields['T_s_0'] + FREEZE
        output_rec['T_s_l'] = updated_fields['T_s_l'] + FREEZE
        output_rec['T_s'] = updated_fields['T_s'] + FREEZE
        output_rec['h2o_sat'] = updated_fields['h2o_sat']
        output_rec['z_s'] = updated_fields['D']
        output_rec['rho'] = updated_fields['rho']

        return output_rec

    def run_update_procedure_isnobal(self, myawsm):
        """
        Function to run iSnobal with direct insertion of lidar depths. This function
        incorporates each available lidar image within the time frame and runs
        each section of isnobal
        """

        # run iSnobal up to first update if needed
        if self.firststeps > 0:
            if myawsm.run_for_nsteps is None:
                myawsm.run_for_nsteps = self.firststeps
            # run isnobal Once
            myawsm.run_isnobal(offset=None)

        # do each update and run again
        for idu, k in enumerate(self.update_info.keys()):
            off = self.offsets[idu]
            # find update output file
            # if we're starting with an update
            if self.firststeps == 0 and idu == 0:
                if myawsm.restart_crash:
                    name_crash = 'snow.%04d' % myawsm.restart_hr
                    update_snow = os.path.join(myawsm.pathro, name_crash)
                else:
                    update_snow = myawsm.prev_mod_file

            else:
                update_snow = self.find_update_snow(myawsm, off)

            # perform the update and set the init file for iSnobal
            myawsm.init_file = self.do_update_isnobal(myawsm, self.update_info[k],
                                         update_snow, self.x, self.y)

            # set nsteps
            myawsm.run_for_nsteps = self.runsteps[idu]

            # run isnobal again
            myawsm.run_isnobal(offset=off)

    def initialize_aso_updates(self, myawsm, update_fp):
        """
        Read in the ASO update file and parse images by date
        Argument:
                myawsm: instantiated awsm class
                update_fp: file pointer to netCDF with all flights in it
        Return:
                update_info: dictionary of updates
        """

        # last_snow_image = ipw.IPW('/home/micahsandusky/Code/awsfTesting/newupdatetest/snow.2879')

        ##  Update the snow depths in the initialization file using ASO lidar:
        fp = update_fp
        # read in update files
        ds = Dataset(fp, 'r')
        # get all depths, x, y, time
        D_all = ds.variables['depth'][:]
        if np.any(D_all) > 100:
            print('Check D_all')
        x = ds.variables['x'][:]
        y = ds.variables['y'][:]
        times = ds.variables['time']
        ts = times[:]
        # convert time index to dates
        t = nc.num2date(ts, times.units, times.calendar)
        # find wyhr of dates

        t_wyhr = []
        for t1 in t:
            #tmp_date = t1.replace(tzinfo=myawsm.tzinfo)
            # this maybe?
            # .astimezone(self.)
            tmp_date = t1.astimezone(tzinfo=myawsm.tzinfo)
            # get wyhr
            tmpwyhr = int(utils.water_day(tmp_date)[0]*24)
            t_wyhr.append(tmpwyhr)

        t_wyhr = np.array(t_wyhr)

        # make dictionary of updates
        update_info = OrderedDict()
        keys = range(1,len(t_wyhr)+1)
        for idk, k in enumerate(keys):
            # make dictionary for each update
            update_info[k] = {}
            # set update number
            update_info[k]['number'] = k
            update_info[k]['date_time'] = t[idk]
            update_info[k]['wyhr'] = t_wyhr[idk]
            # set depth
            update_info[k]['depth'] = D_all[idk,:]

        return update_info, x, y


    def calc_offsets_nsteps(self, myawsm, update_info):
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

        #t_wyhr = update_info['wyhr'].values
        update_number = update_info.keys()
        # filter to desired flights if user input
        if myawsm.flight_numbers is not None:
            filter_number = myawsm.flight_numbers
        else:
            filter_number = update_number
            # # make list if not list
            # if not isinstance(filter_number, list):
            #     filter_number = [filter_number]
            #     update_number = [update_number]

        myawsm._logger.debug('Will update with flights {}'.format(filter_number))
        # filter to correct hourse
        for un in update_number:
            if un not in filter_number:
                # delete update if not in desired update inputs
                update_info.pop(un)

        # check if a first run with no update is needed to get us up to the first update
        if myawsm.restart_crash:
            test_start_wyhr = myawsm.restart_hr+1
        else:
            test_start_wyhr = myawsm.start_wyhr

        # filter so we are in the dates
        update_info_copy = copy.deepcopy(update_info)
        for un in update_info_copy.keys():
            tw = update_info[un]['wyhr']
            # get rid of updates more than a day before start date
            if tw < test_start_wyhr - 24:
                update_info.pop(un)
            # get rid of updates past the end of the run
            elif tw > myawsm.end_wyhr:
                update_info.pop(un)

        # now we are down to the correct wyhrs and update numbers
        update_number = update_info.keys()
        t_wyhr = [update_info[k]['wyhr'] for k in update_number]

        # this is where each run will start from
        offsets = t_wyhr

        if len(offsets) == 0:
            raise IOError('No update dates in this run')

        # do we need to do that run?
        if offsets[0] - test_start_wyhr <= 0:
            firststeps = 0
        else:
            firststeps = offsets[0] - test_start_wyhr

        runsteps = np.zeros_like(offsets)
        for ido, offs in enumerate(offsets):
            if ido == len(offsets) - 1:
                runsteps[ido] = myawsm.end_wyhr - offs
            else:
                runsteps[ido] = offsets[ido+1] - offs

        myawsm._logger.debug('Filtered to updates on: {}'.format(t_wyhr))

        return update_info, runsteps, offsets, firststeps

    def find_update_snow(self, myawsm, offset):
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
        hr = hr[hr < offset]
        #hr = [h for h in hr if h < offset]
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


    def do_update_isnobal(self, myawsm, update_info, update_snow, x, y):
        """
        Function to read in an output file and update it with the lidar depth field

        Argument:
            myawsm: instantiated awsm class
            update_info: update info pandas at correct index
            update_snow: file pointer to snow update image
            x: x vector
            y: y vector
        Returns:
            init_file: file pointer to init image
        """
        # get some info
        update_number = update_info['number']
        date = update_info['date_time']
        wyhr = update_info['wyhr']

        last_snow_image = ipw.IPW(update_snow)
        z_s = last_snow_image.bands[0].data # Get modeled depth image.
        # z_s(mask==0) = NaN;

        ##  Continue as before:
        density = last_snow_image.bands[1].data.copy() # Get density image.
        ## ## ## ## ## ## ## ## ## %
        # SPECIAL CASE... insert adjusted densities here:
        # density = arcgridread_v2(['/Volumes/data/blizzard/Tuolumne/lidar/snowon/2017' ...
        #                 '/adjusted_rho/TB2017' date_mmdd '_operational_rho_ARSgrid_50m.asc']);
        ## ## ## ## ## ## ## ## ## %
        m_s = last_snow_image.bands[2].data.copy() # Get SWE image.
        T_s_0 = last_snow_image.bands[4].data.copy() # Get active snow layer temperature image
        T_s_l = last_snow_image.bands[5].data.copy() # Get lower snow layer temperature image
        T_s = last_snow_image.bands[6].data.copy() # Get average snowpack temperature image
        h2o_sat = last_snow_image.bands[8].data.copy() # Get liquid water saturation image

        updated_fields = self.hedrick_updating_procedure(m_s, T_s_0, T_s_l, T_s,
                                                    h2o_sat, density, z_s,
                                                    x, y, update_info)

        # write init file
        out_file = 'init_update_{}_wyhr{:04d}.ipw'.format(update_number, wyhr)
        init_file = os.path.join(self.pathinit,out_file)
        i_out = ipw.IPW()
        i_out.new_band(updated_fields['dem'])
        i_out.new_band(updated_fields['z0'])
        i_out.new_band(updated_fields['D'])
        i_out.new_band(updated_fields['rho'])
        i_out.new_band(updated_fields['T_s_0'])
        i_out.new_band(updated_fields['T_s_l'])
        i_out.new_band(updated_fields['T_s'])
        i_out.new_band(updated_fields['h2o_sat'])
        #i_out.add_geo_hdr([u, v], [du, dv], units, csys)
        i_out.add_geo_hdr([self.topo.u, self.topo.v],
                          [self.topo.du, self.topo.dv],
                          self.topo.units, self.csys)
        i_out.write(init_file, self.nbits)

        ##  Import newly-created init file and look at images to make sure they line up:
        self._logger.info('Wrote ipw image for update {}'.format(wyhr))

        return init_file


    def hedrick_updating_procedure(self, m_s, T_s_0, T_s_l, T_s, h2o_sat, density, z_s,
                                   x, y, update_info):
        """
        This function performs the direct insertion procedure and returns the
        updated fields.

        Argument:
            m_s:    swe array to be updated
            T_s_0:  surface layer temperature array to be updated
            T_s_l:  lower layer temperature array to be updated
            T_s:    bulk temperature array to be updated
            h2o_sat: h2o_sat array to be updated
            density: density array to be updated
            z_s:     snow height array to be updated
            x:       x vector
            y:       y vector
            logger:  awsm logger
            update_info: necessary update info
        Returns:
            updated_fields:  dictionary of updated fields including dem, z0, D,
                             rho, T_s_0, T_s_l, T_s, h2o_sat
        """

        # keep a copy of the original inputs
        original_fields = {}
        original_fields['m_s'] = m_s.copy()
        original_fields['T_s_0'] = T_s_0.copy()
        original_fields['T_s_l'] = T_s_l.copy()
        original_fields['T_s'] = T_s.copy()
        original_fields['h2o_sat'] = h2o_sat.copy()
        original_fields['density'] = density.copy()
        original_fields['z_s'] = z_s.copy()

        activeLayer = self.active_layer
        Buf = self.update_buffer  # Buffer size (in cells) for the interpolation to search over.
        # get dem and roughness
        dem = self.topo.dem
        z0 = self.topo.roughness

        # New depth field
        D = update_info['depth']

        # make mask
        D[self.topo.mask == 0.0] = np.nan
        mask = np.ones_like(D)
        mask[np.isnan(D)] = 0.0

        XX,YY = np.meshgrid(x,y)

        nrows = len(y)
        ncols = len(x)

        ##  Special case - 20160607
        # I am trying an update with only Tuolumne Basin data where I will mask in
        # Cherry and Eleanor to create a hybrid iSnobal/ASO depth image.
        tempASO = D.copy()
        tempASO[np.isnan(D)] = 0.0
        tempiSnobal = z_s.copy()
        tuolx_mask = mask
        tempASO[tuolx_mask == 1.0] = 0.0
        #tempiSnobal[tuolx_mask == 1] = 0.0
        I_ASO = (tempASO == 0.0)
        tempASO[I_ASO] = tempiSnobal[I_ASO]
        tempASO[tuolx_mask == 1.0] = D[tuolx_mask == 1.0]
        D = tempASO.copy()

        # Address problem of bit resolution where cells have mass and density,
        # but no depth is reported (less than minimum depth above zero).
        u_depth = np.unique(z_s)

        id_m_s = m_s == 0.0
        z_s[id_m_s] = 0.0
        density[id_m_s] = 0.0
        T_s[id_m_s] = -75.0
        T_s_l[id_m_s] = -75.0
        T_s_0[id_m_s] = -75.0
        h2o_sat[id_m_s] = 0.0

        z_s[ (density > 0.0) & (z_s == 0.0) ] = u_depth[1]

        rho = density.copy()
        D[D < 0.05] = 0.0 # Set shallow snow (less than 5cm) to 0.
        D[mask == 0.0] = np.nan # Set out of watershed cells to NaN
        rho[mask == 0.0] = np.nan # Set out of watershed cells to NaN
        tot_pix = ncols * nrows # Get number of pixels in domain.

        I_model = np.where(z_s == 0) # Snow-free pixels in the model.
        modelDepth = tot_pix - len(I_model[0]) # # of pixels with snow (model).
        I_lidar = np.where( (D == 0) | (np.isnan(D) ) ) # Snow-free pixels from lidar.
        lidarDepth = tot_pix - len(I_lidar[0]) # # of pixels with snow (lidar).
        I_rho = np.where( density == 0 ) # Snow-free pixels upon importing.
        modelDensity = tot_pix - len(I_rho[0]) # # of pixels with density (model).


        self._logger.debug('\nJust After Importing.\n \
                              Number of modeled cells with snow depth: {}\n \
                              Number of modeled cells with density: {}\n \
                              Number of lidar cells measuring snow: {}'.format(modelDepth, modelDensity, lidarDepth ) )
        id0 = D == 0.0

        rho[id0] = 0.0 # Find cells without lidar snow and set the modeled density to zero.
        rho[rho == 0.0] = np.nan # Set all cells with no density to NaN.

        T_s_0[id0] = np.nan # Find cells without lidar snow and set the active layer temp to NaN.
        T_s_0[T_s_0 <= -75.0] = np.nan # Change isnobal no-values to NaN.

        T_s_l[id0] = np.nan # Find cells without lidar snow and set the lower layer temp to NaN.
        T_s_l[T_s_l <= -75.0] = np.nan # Change isnobal no-values to NaN.

        T_s[id0] = np.nan # Find cells without lidar snow and set the snow temp to np.nan.
        T_s[T_s <= -75.0] = np.nan # Change isnobal no-values to NaN.

        h2o_sat[id0] = np.nan # Find cells without lidar snow and set the h2o saturation to NaN.
        h2o_sat[mask == 0.0] = np.nan
        # h2o_sat[h2o_sat == -75.0] = np.nan # Change isnobal no-values to NaN.

        I_rho = np.where( np.isnan(rho) ) # Snow-free pixels before interpolation
        #modelDensity = tot_pix - size(I_rho, 1)
        modelDensity = tot_pix - len(I_rho[0])

        self._logger.debug('\nBefore Interpolation.\n \
                              Number of modeled cells with snow depth: {0}\n \
                              Number of modeled cells with density: {1}\n \
                              Number of lidar cells measuring snow: {2}'.format(modelDepth, modelDensity, lidarDepth ) )

        ##  Now find cells where lidar measured snow, but Isnobal simulated no snow:
        I = np.where( (np.isnan(rho)) & (D > 0.0) )
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
                xl = xt - int((n1 - 1) / 2)
                xh = xt + int((n1 - 1) / 2)
                yl = yt - int((n1 - 1) / 2)
                yh = yt + int((n1 - 1) / 2)
                window = rho_buf[yl:yh,xl:xh]
                qq = np.where(np.isfinite(window)) # find number of pixels with a value.
                if (len(qq[0]) > 10):
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

                # check to see if you found a value
                if n1 == n[-1] and np.isnan(rho[ix,iy]):
                    self._logger.error('Failed to find desnity wihtin buffer')
                # if we found a value, move on
                if np.isfinite( rho[ix,iy] ):
                    break

        # ##################### hopefully fixed for loop logic below
        self._logger.debug('Done with loop 1')
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
                xl = xt - int((jj-1)/2)
                xh = xt + int((jj-1)/2)
                yl = yt - int((jj-1)/2)
                yh = yt + int((jj-1)/2)
                window = T_s_l_buf[yl:yh,xl:xh]
                val = np.nanmean(window[:])
                T_s_l[ix,iy] = val # Interpolate for lower layer temp
                ################ fix this to be pyton logic
                #if np.isnan(T_s_l[ii]) == False:
                if not np.any(np.isnan(T_s_l[ix,iy])):
                    break

        self._logger.debug('Done with loop 2')

        iq = (np.isnan(D)) & (np.isfinite(rho))
        rho[iq] = np.nan # Once more, change cells with no lidar snow to have np.nan density.

        # Find occurance where cell has depth and density but no temperature.
        # Delete snowpack from this cell.
        iq2 = (np.isnan(T_s)) & (np.isfinite(rho))
        D[iq2] = 0.0
        rho[iq2] = np.nan

        I_lidar = np.where( (D == 0.0) | (np.isnan(D) ) ) # Snow-free pixels from lidar.
        lidarDepth = tot_pix - len(I_lidar[0]) # # of pixels with snow (lidar).
        I_rho = np.where( np.isnan(rho) ) # Snow-free pixels upon importing.
        modelDensity = tot_pix - len(I_rho[0]) # # of pixels with density (model).

        I_lidaridx = (D == 0.0) | (np.isnan(D) )  # Snow-free pixels from lidar.
        I_rhoidx = np.isnan(rho)  # Snow-free pixels upon importing.

        self._logger.debug('\nAfter Interpolation.\n \
                              Number of modeled cells with snow depth: {}\n \
                              Number of modeled cells with density: {}\n \
                              Number of lidar cells measuring snow: {}'.format(modelDepth,modelDensity,lidarDepth ) )

        ##  Reset NaN's to the proper values for Isnobal:
        #if size(I_lidar, 1) ~= size(I_rho, 1)
        if len(I_lidar[0]) != len(I_rho[0]):
            raise ValueError('Lidar depths do not match interpolated model densities.  Try changing buffer parameters.')

        rho[I_rhoidx] = 0.0 # rho is the updated density map.
        D[rho == 0.0] = 0.0 # D is lidar snow depths, I_rho is where no snow exists.
        I_25_new = D <= activeLayer # find cells with lidar depth less than 25 cm
            # These cells will have the corresponding lower layer temp changed to
            # -75 (no value) and the upper layer temp will be set to equal the
            # average snowpack temp in that cell.
        T_s[rho == 0.0] = -75.0 # T_s is the average snow temperature in a cell. Is NaN (-75) for all rho = 0.
        T_s_0[rho == 0.0] = -75.0 # T_s_0 is the updated active (upper) layer.  Is >0 for everywhere rho is >0.
        T_s_0[I_25_new] = T_s[I_25_new] # If lidar depth <= 25cm, set active layer temp to average temp of cell
        T_s_l[I_25_new] = -75.0
        T_s_l[np.isnan(T_s_l)] = -75.0
        h2o_sat[rho == 0.0] = 0.0

        # grab unmasked cells again
        nmask = mask == 0
        # Make sure non-updated cells stay the same as original
        m_s[nmask] = original_fields['m_s'][nmask] # Get SWE image.
        T_s_0[nmask] = original_fields['T_s_0'][nmask] # Get active snow layer temperature image
        T_s_l[nmask] = original_fields['T_s_l'][nmask] # Get lower snow layer temperature image
        T_s[nmask] = original_fields['T_s'][nmask] # Get average snowpack temperature image
        h2o_sat[nmask] = original_fields['h2o_sat'][nmask] # Get liquid water saturation image
        D[nmask] = original_fields['z_s'][nmask]
        rho[nmask] = original_fields['density'][nmask]

        # create dictionary to return with updated arrays
        updated_fields = {}
        updated_fields['dem'] = dem
        updated_fields['z0'] = z0
        updated_fields['D'] = D
        updated_fields['rho'] = rho
        updated_fields['T_s_0'] = T_s_0
        updated_fields['T_s_l'] = T_s_l
        updated_fields['T_s'] = T_s
        updated_fields['h2o_sat'] = h2o_sat

        return updated_fields
