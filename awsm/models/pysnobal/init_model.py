import os
import logging

import netCDF4 as nc
import numpy as np
import pandas as pd
import xarray as xr


C_TO_K = 273.16
FREEZE = C_TO_K

"""
Outline

-get_init_file:
    --reads in the specific init file and stores init fields in dictionary
    --checks if restarting from a crash, in which case init file is not used
    --if no file then make the necessary 0 start file

-write_init:
    --make the needed file or datatype to init the runs
    --if isnobal then write the file or just pass the fp if input was pw init
    --make init dictionary to pass to any pysnobal

-make_backup:
    -- backup init state in netcdf file

"""


class ModelInit():
    """
    Class for initializing snow model. Only runs if a model is specified
    in the AWSM config.

    Attributes:
        init:       Dictionary of init fields
        fp_init:    File pointer if iSnobal init file


    """

    def __init__(self, cfg, topo, path_output, start_date):
        """
        Args:
            cfg:            AWSM config dictionary
            topo:           AWSM topo class
            path_output:         run<date> directory
            start_date:     AWSM start date

        """

        self._logger = logging.getLogger(__name__)
        self.topo = topo
        self.start_date = start_date
        self.config = cfg

        # get parameters from awsm
        self.init_file = cfg['ipysnobal']['init_file']
        self.init_type = cfg['ipysnobal']['init_type']

        if self.init_file is not None:
            self._logger.info(
                'Using {} to build model init state.'.format(self.init_file))

        self.model_type = cfg['awsm master']['model_type']
        self.path_output = path_output

        # when restarting, just reset the start date to grab the
        # right init time step
        if self.config['ipysnobal']['restart_date_time'] is not None:
            self.start_date = self.start_date - \
                pd.Timedelta(minutes=self.config['time']['time_step'])
            self.init_type = 'netcdf_out'
            self.init_file = os.path.join(self.path_output, 'ipysnobal.nc')
            self._logger.info("""Initializing ipysnobal at time {} from """
                              """previous output file""".format(
                                  self.start_date))

        # dictionary to store init data
        self.init = {}
        self.init['x'] = self.topo.x
        self.init['y'] = self.topo.y
        self.init['mask'] = self.topo.mask
        self.init['z_0'] = self.topo.roughness
        self.init['elevation'] = self.topo.dem

        # read in the init file
        self.get_init_file()

        for key in self.init.keys():
            self.init[key] = self.init[key].astype(np.float64)

        if self.model_type in ['ipysnobal', 'smrf_ipysnobal']:
            # convert temperatures to K
            self.init['T_s'] += FREEZE
            self.init['T_s_0'] += FREEZE
            if 'T_s_l' in self.init:
                self.init['T_s_l'] += FREEZE

    def get_init_file(self):
        """
        Get the necessary data from the init.
        This will check the model type and the init file and act accordingly.
        """

        # if we have no init info, make zero init
        if self.init_file is None:
            self.get_zero_init()
        # get init depending on file type
        elif self.init_type == 'netcdf':
            self.get_netcdf()
        elif self.init_type == 'netcdf_out':
            self.get_netcdf_out()

    def get_crash_init(self):
        """
        Initializes simulation variables for special case when restarting a
        crashed run. Zeros depth under specified threshold and zeros other
        snow parameters that must be dealt with when depth is set to zero.

        Modifies:
            init:    dictionary of initialized variables
        """

        self.init_type = 'netcdf_out'
        # find the correct output folder from which to restart
        if self.restart_folder == 'standard':
            self.init_file = os.path.join(self.path_output, 'ipysnobal.nc')

        elif self.restart_folder == 'daily':
            fmt = '%Y%m%d'
            # get the date string
            day_str = self.path_output[-8:]
            day_dt = pd.to_datetime(day_str) - \
                pd.to_timedelta(1, unit='days')
            day_dt_str = day_dt.strftime(fmt)
            # get the previous day
            path_prev_day = os.path.join(self.path_output,
                                         '..', 'run'+day_dt_str)
            self.init_file = os.path.join(path_prev_day, 'ipysnobal.nc')

        self.get_netcdf_out()

        # zero depths under specified threshold
        restart_var = self.zero_crash_depths(self.depth_thresh,
                                             self.init['z_s'],
                                             self.init['rho'],
                                             self.init['T_s_0'],
                                             self.init['T_s_l'],
                                             self.init['T_s'],
                                             self.init['h2o_sat'])
        # put variables back in init dictionary
        for k, v in restart_var.items():
            self.init[k] = v

    def get_zero_init(self):
        """
        Set init fields for zero init
        """
        self._logger.info('No init file given, using zero fields')
        self.init['z_s'] = 0.0*self.topo.mask  # snow depth
        self.init['rho'] = 0.0*self.topo.mask  # snow density

        self.init['T_s_0'] = -75.0*self.topo.mask  # active layer temp
        self.init['T_s_l'] = -75.0*self.topo.mask  # lower layer temp
        self.init['T_s'] = -75.0*self.topo.mask  # average snow temp

        self.init['h2o_sat'] = 0.0*self.topo.mask  # percent saturation

    def get_netcdf(self):
        """
        Get init fields from netcdf init file
        """
        i = nc.Dataset(self.init_file, 'r')
        i.set_always_mask(False)

        # All other variables will be assumed zero if not present
        all_zeros = np.zeros_like(self.init['elevation'])
        flds = ['z_s', 'rho', 'T_s_0', 'T_s', 'h2o_sat', 'T_s_l']

        if len(i.variables['time'][:]) > 1:
            self._logger.warning(
                """More than one time step found in the init """
                """file, using first index""")

        for f in flds:
            # if i.variables.has_key(f):
            if f in i.variables:
                # read in the variables
                self.init[f] = i.variables[f][0, :]
            else:
                # default is set to zeros
                self.init[f] = all_zeros

        i.close()

    def get_netcdf_out(self):
        """
        Get init fields from output netcdf for the closest date within
        24 hours of the start date
        """

        ds = xr.open_dataset(self.init_file)

        init_data = ds.sel(time=self.start_date, method='nearest')
        time_diff = self.start_date.tz_localize(None) - init_data.time.values

        if time_diff.total_seconds() < 0 or \
                time_diff.total_seconds() > 24*3600:
            self._logger.error(
                'No time in restart file that is within a day of restart time')

        self._logger.warning(
            'Initializing PySnobal with state from {}'.format(init_data.time))

        self.init['z_s'] = init_data.thickness.values
        self.init['rho'] = init_data.snow_density.values
        self.init['T_s_0'] = init_data.temperature_surface.values
        self.init['T_s'] = init_data.temperature_snowcover.values
        self.init['T_s_l'] = init_data.temperature_lower.values
        self.init['h2o_sat'] = init_data.water_saturation.values

        ds.close()
