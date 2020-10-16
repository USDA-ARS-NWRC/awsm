import copy
import os
import logging
import pytz
from types import MappingProxyType

import numpy as np
import netCDF4 as nc
from smrf.framework.model_framework import run_smrf


class SMRFConnector():

    # map function from these values to the ones required by snobal
    MAP_INPUTS = MappingProxyType({
        'air_temp': 'T_a',
        'net_solar': 'S_n',
        'thermal': 'I_lw',
        'vapor_pressure': 'e_a',
        'wind_speed': 'u',
        'soil_temp': 'T_g',
        'precip': 'm_pp',
        'percent_snow': 'percent_snow',
        'snow_density': 'rho_snow',
        'precip_temp': 'T_pp'
    })

    def __init__(self, myawsm):

        self._logger = logging.getLogger(__name__)
        self.myawsm = myawsm
        self.force = None

        self.create_smrf_config()

        self._logger.info('SMRFConnector initialized')

    def create_smrf_config(self):
        """
        Create a smrf config for running standard :mod: `smr` run. Use the
        :mod: `AWSM` config and remove the sections specific to :mod: `AWSM`.
        We do this because these sections will break the config checker utility
        """
        self.myawsm._logger.info('Making SMRF config')

        delete_keys = self.myawsm.awsm_config_sections

        # Write out config file to run smrf
        # make copy and delete only awsm sections
        smrf_config = copy.deepcopy(self.myawsm.ucfg)
        smrf_config.cfg = {
            key: item for key, item in self.myawsm.ucfg.cfg.items() if key not in delete_keys  # noqa
        }

        # make sure start and end date are correcting
        smrf_config.cfg['time']['start_date'] = self.myawsm.start_date
        smrf_config.cfg['time']['end_date'] = self.myawsm.end_date

        # set output location in smrf config
        smrf_config.cfg['output']['out_location'] = self.myawsm.path_output
        self.output_path = self.myawsm.path_output

        self.smrf_config = smrf_config

    def run_smrf(self):
        """Run SMRF using the `run_smrf` from the SMRF API
        """

        self._logger.info('Running SMRF')
        run_smrf(self.smrf_config, self._logger)

    def open_netcdf_files(self):
        """
        Open the netCDF files for initial conditions and inputs
        - Reads in the initial_conditions file
        - Required variables are x,y,z,z_0
        - The others z_s, rho, T_s_0, T_s, h2o_sat, mask can be specified
        but will be set to default of 0's or 1's for mask
        - Open the files for the inputs and store the file identifier

        """

        self.force = {}
        for variable in self.MAP_INPUTS.keys():
            try:
                self.force[variable] = nc.Dataset(
                    os.path.join(self.output_path, '{}.nc'.format(variable)),
                    'r')
                self.force[variable].set_always_mask(False)

            except FileNotFoundError:
                self.force['soil_temp'] = float(self.myawsm.soil_temp) * \
                    np.ones_like(self.myawsm.topo.dem)

    def close_netcdf_files(self):
        """
        Close input netCDF forcing files
        """

        for f in self.force.keys():
            if not isinstance(self.force[f], np.ndarray):
                self.force[f].close()

    def get_timestep_netcdf(self, tstep):
        """
        Pull out a time step from the forcing files and
        place that time step into a dict

        Args:
            force:   input array of forcing variables
            tstep:   datetime time step

        Returns:
            inpt:    dictionary of forcing variable images
        """

        inpt = {}

        for f in self.force.keys():

            if isinstance(self.force[f], np.ndarray):
                # If it's a constant value then just read in the numpy array
                # pull out the value
                # ensures not a reference (especially if T_g)
                inpt[self.MAP_INPUTS[f]] = self.force[f].copy()

            else:
                # determine the index in the netCDF file

                # compare the dimensions and variables to get the variable name
                v = list(set(self.force[f].variables.keys()) -
                         set(self.force[f].dimensions.keys()))
                v = [fv for fv in v if fv != 'projection'][0]

                # make sure you're in the same timezone
                if hasattr(self.force[f].variables['time'], 'time_zone'):
                    tstep_zone = tstep.astimezone(pytz.timezone(
                        self.force[f].variables['time'].time_zone))
                    tstep_zone = tstep.tz_localize(None)
                else:
                    tstep_zone = tstep.tz_localize(None)

                # find the index based on the time step
                t = nc.date2index(
                    tstep_zone,
                    self.force[f].variables['time'],
                    calendar=self.force[f].variables['time'].calendar,
                    select='exact')

                # pull out the value
                inpt[self.MAP_INPUTS[f]] = \
                    self.force[f].variables[v][t, :].astype(np.float64)

        return inpt
