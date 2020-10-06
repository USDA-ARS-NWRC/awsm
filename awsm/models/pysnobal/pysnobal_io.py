import os
from copy import copy
import logging
from datetime import datetime

import netCDF4 as nc
import numpy as np
import pandas as pd
from spatialnc.proj import add_proj

FREEZE = 273.16


class PysnobalIO():

    OUTPUT_VARIABLES = {
        'net_radiation': {
            'units': 'W m-2',
            'description': 'Average net all-wave radiation',
            'ipysnobal_var': 'R_n_bar'
        },
        'sensible_heat': {
            'units': 'W m-2',
            'description': 'Average sensible heat transfer',
            'ipysnobal_var': 'H_bar'
        },
        'latent_heat': {
            'units': 'W m-2',
            'description': 'Average latent heat exchange',
            'ipysnobal_var': 'L_v_E_bar'
        },
        'snow_soil': {
            'units': 'W m-2',
            'description': 'Average snow/soil heat exchange',
            'ipysnobal_var': 'G_bar'
        },
        'precip_advected': {
            'units': 'W m-2',
            'description': 'Average advected heat from precipitation',
            'ipysnobal_var': 'M_bar'
        },
        'sum_energy_balance': {
            'units': 'W m-2',
            'description': 'Average sum of energy balance terms for snowcover',
            'ipysnobal_var': 'delta_Q_bar'
        },
        'evaporation': {
            'units': 'kg m-2 (equivalent to mm of water)',
            'description': 'Total evaporation and sublimation per unit area from surface of snowpack',
            'ipysnobal_var': 'E_s_sum'
        },
        'snowmelt': {
            'units': 'kg m-2 (equivalent to mm of water )',
            'description': 'Total snowmelt per unit area occurring within the snowpack',
            'ipysnobal_var': 'melt_sum'
        },
        'surface_water_input': {
            'units': 'kg m-2 (equivalent to mm of water)',
            'description': 'Surface water input is liquid water output from bottom of snowpack or rain on bare ground per unit area',
            'ipysnobal_var': 'ro_pred_sum'
        },
        'cold_content': {
            'units': 'J m-2',
            'description': 'Snowcover cold content',
            'ipysnobal_var': 'cc_s'
        },
        'thickness': {
            'units': 'm',
            'description': 'Thickness of the snowcover',
            'ipysnobal_var': 'z_s'
        },
        'snow_density': {
            'units': 'kg m-3',
            'description': 'Average snow density of the snowcover',
            'ipysnobal_var': 'rho'
        },
        'specific_mass': {
            'units': 'kg m-2 (equivalent to mm of water)',
            'description': 'Specific mass per unit area of the snowcover or snow water equivalent',
            'ipysnobal_var': 'm_s'
        },
        'liquid_water': {
            'units': 'kg m-2 (equivalent to mm of water)',
            'description': 'Mass per unit area of liquid water in the snowcover',
            'ipysnobal_var': 'h2o'
        },
        'temperature_surface': {
            'units': 'C',
            'description': 'Temperature of the surface layer',
            'ipysnobal_var': 'T_s_0'
        },
        'temperature_lower': {
            'units': 'C',
            'description': 'Temperature of the lower layer',
            'ipysnobal_var': 'T_s_l'
        },
        'temperature_snowcover': {
            'units': 'C',
            'description': 'Temperature of the snowcover',
            'ipysnobal_var': 'T_s'
        },
        'thickness_lower': {
            'units': 'm',
            'description': 'Thickness of the lower layer',
            'ipysnobal_var': 'z_s_l'
        },
        'water_saturation': {
            'units': 'percent',
            'description': 'Percentage of liquid water saturation of the snowcover',
            'ipysnobal_var': 'h2o_sat'
        }
    }

    def __init__(self, output_file_name, output_path, myawsm):

        self._logger = logging.getLogger(__name__)

        self.output_file_name = output_file_name + '.nc'
        self.output_path = output_path
        self.output_filename = os.path.join(
            self.output_path, self.output_file_name)

        self.start_date = myawsm.start_date
        self.awsm = myawsm

        self.output_variables = self.awsm.pysnobal_output_vars

        self._logger.info('PysnobalIO initialized')

    def create_output_files(self):
        """
        Create the ipysnobal output netCDF file
        """

        self._logger.info('Creating output iPysnobal file at {}'.format(
            self.output_file_name))

        fmt = '%Y-%m-%d %H:%M:%S'
        # chunk size
        cs = (6, 10, 10)
        if self.awsm.topo.nx < 10:
            cs = (3, 3, 3)

        if os.path.isfile(self.output_file_name):
            self._logger.warning(
                'Opening {}, data may be overwritten!'.format(
                    self.output_filename))
            em = nc.Dataset(self.output_filename, 'a')
            h = '[{}] Data added or updated'.format(
                datetime.now().strftime(fmt))
            setattr(em, 'last_modified', h)

            if 'projection' not in em.variables.keys():
                em = add_proj(em, None, self.awsm.topo.topoConfig['filename'])

        else:
            em = nc.Dataset(self.output_filename, 'w')

            dimensions = ('time', 'y', 'x')

            # create the dimensions
            em.createDimension('time', None)
            em.createDimension('y', len(self.awsm.topo.y))
            em.createDimension('x', len(self.awsm.topo.x))

            # create some variables
            # TODO what is the cell references, LL or center? #41
            em.createVariable('time', 'f', dimensions[0])
            em.createVariable('y', 'f', dimensions[1])
            em.createVariable('x', 'f', dimensions[2])

            setattr(em.variables['time'], 'units',
                    'hours since %s' % self.start_date.tz_localize(None))
            setattr(em.variables['time'], 'time_zone',
                    str(self.awsm.tzinfo).lower())
            setattr(em.variables['time'], 'calendar', 'standard')

            em.variables['x'][:] = self.awsm.topo.x
            em.variables['y'][:] = self.awsm.topo.y

            for var_name, att in self.OUTPUT_VARIABLES.items():
                # check to see if in output variables
                if var_name.lower() in self.awsm.pysnobal_output_vars:

                    em.createVariable(
                        var_name, 'f', dimensions[:3], chunksizes=cs)
                    setattr(em.variables[var_name], 'units', att['units'])
                    setattr(em.variables[var_name],
                            'description', att['description'])

            # add projection info
            em = add_proj(em, None, self.awsm.topo.topoConfig['filename'])

        self.output_file = em

    def output_timestep(self, smrf_data, tstep):
        """
        Output the model results for the current time step

        Args:
            s:       dictionary of output variable numpy arrays
            tstep:   datetime time step

        """

        # preallocate
        output = {}

        # gather all the data together
        for key, att in self.OUTPUT_VARIABLES.items():
            output[key] = copy(smrf_data[att['ipysnobal_var']])

        # convert from K to C
        output['temperature_snowcover'] -= FREEZE
        output['temperature_surface'] -= FREEZE
        output['temperature_lower'] -= FREEZE

        # now find the correct index
        # the current time integer
        times = self.output_file.variables['time']
        # offset to match same convention as iSnobal
        tstep -= pd.to_timedelta(1, unit='h')
        t = nc.date2num(tstep.replace(tzinfo=None),
                        times.units, times.calendar)

        if len(times) != 0:
            index = np.where(times[:] == t)[0]
            if index.size == 0:
                index = len(times)
            else:
                index = index[0]
        else:
            index = len(times)

        # insert the time
        self.output_file.variables['time'][index] = t

        # insert the data
        for key in self.OUTPUT_VARIABLES.keys():
            if key.lower() in self.output_variables:
                self.output_file.variables[key][index, :] = output[key]

        # sync to disk
        self.output_file.sync()
