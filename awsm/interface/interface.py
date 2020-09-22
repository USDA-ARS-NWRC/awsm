import copy
import os
import logging

import numpy as np
import pandas as pd
from smrf.framework.model_framework import run_smrf
from smrf.utils import utils


class SMRFConnector():

    def __init__(self, myawsm):

        self._logger = logging.getLogger(__name__)
        self.myawsm = myawsm

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
        for key in self.myawsm.ucfg.cfg.keys():
            if key in delete_keys:
                del smrf_config.cfg[key]

        # make sure start and end date are correcting
        smrf_config.cfg['time']['start_date'] = self.myawsm.start_date
        smrf_config.cfg['time']['end_date'] = self.myawsm.end_date

        # change start date if using smrf_ipysnobal and restarting
        if self.myawsm.restart_run and self.myawsm.run_smrf_ipysnobal:
            smrf_config.cfg['time']['start_date'] = self.myawsm.restart_date

        # set output location in smrf config
        smrf_config.cfg['output']['out_location'] = self.myawsm.path_output

        self.smrf_config = smrf_config

    def run_smrf(self):
        """Run SMRF using the `run_smrf` from the SMRF API
        """

        self._logger.info('Running SMRF')
        run_smrf(self.smrf_config)


def run_awsm_daily(myawsm):
    """
    This function is used to run smrf and pysnobal on an hourly scale with
    outputs seperated into daily folders. This will run hourly and allow for
    forecasts like the 18 hour HRRR forecast.
    """
    # get the array of time steps over which to simulate
    d = utils.date_range(
        myawsm.start_date,
        myawsm.end_date,
        pd.to_timedelta(myawsm.time_step, unit='m'),
        myawsm.tzinfo)

    if myawsm.do_forecast:
        myawsm._logger.warning('Changing PySnobal output to hourly to allow'
                               ' for forecast on each hour')
        myawsm.output_freq = 1

    # set variables for adding a day or hour
    add_day = pd.to_timedelta(23, unit='h')
    # add_hour = pd.to_timedelta(1, unit='h')

    start_day = pd.to_datetime(d[0].strftime("%Y%m%d"))
    end_day = pd.to_datetime(d[-1].strftime("%Y%m%d"))
    # if we're starting on an intermediate hour, find timesteps
    # up to first full day
    if d[0] != start_day:
        start_diff = start_day + add_day - d[0]
    else:
        start_diff = add_day
    # find timesteps to end run on last, incomplete day
    if d[-1] != end_day:
        end_diff = d[-1] - end_day
    else:
        end_diff = add_day

    # find total days to run model
    total_days = int(len(d) * myawsm.time_step / (60*24))

    # loop through timesteps and initialize runs for each day
    for day in range(total_days):
        # set variable output names
        myawsm.snow_name = 'snow_00'
        myawsm.em_name = 'em_00'
        # set start and end appropriately
        if day == 0:
            myawsm.start_date = d[0]
            myawsm.end_date = d[0] + start_diff
        elif day == total_days - 1:
            myawsm.start_date = start_day + \
                pd.to_timedelta(24*day, unit='h')
            myawsm.end_date = myawsm.start_date + end_diff
        else:
            myawsm.start_date = start_day + \
                pd.to_timedelta(24*day, unit='h')
            myawsm.end_date = myawsm.start_date + \
                pd.to_timedelta(23, unit='h')

        # recalculate start and end water year hour
        tmp_date = myawsm.start_date.replace(tzinfo=myawsm.tzinfo)
        tmp_end_date = myawsm.end_date.replace(tzinfo=myawsm.tzinfo)
        myawsm.start_wyhr = int(utils.water_day(tmp_date)[0]*24)
        myawsm.end_wyhr = int(utils.water_day(tmp_end_date)[0]*24)

        # find day for labelling the output folder nested one more level in
        daily_append = '{}'.format(myawsm.start_date.strftime("%Y%m%d"))
        myawsm.pathro = os.path.join(
            myawsm.path_output, 'output'+daily_append)
        if not os.path.exists(myawsm.pathro):
            os.makedirs(myawsm.pathro)

        # turn off forecast for daily run (will be turned on later if it
        # was true)
        myawsm.config['gridded']['hrrr_forecast_flag'] = False

        # ################# run_model for day ###############################
        myawsm.run_smrf_ipysnobal()

        # reset restart to be last output for next time step
        myawsm.ipy_init_type = 'netcdf_out'
        myawsm.config['ipysnobal initial conditions']['init_file'] = \
            os.path.join(myawsm.pathro, myawsm.snow_name + '.nc')

        # do the 18hr forecast on each hour if forecast is true
        if myawsm.do_forecast:
            # turn forecast back on in smrf config
            myawsm.config['gridded']['hrrr_forecast_flag'] = True

            # now loop through the forecast hours for 18hr forecasts
            d_inner = utils.date_range(
                myawsm.start_date,
                myawsm.end_date,
                pd.to_timedelta(myawsm.time_step, unit='m'),
                myawsm.tzinfo)
            for t in d_inner:
                # find hour from start of day
                day_hour = t - pd.to_datetime(d_inner[0].strftime("%Y%m%d"))
                day_hour = int(day_hour / np.timedelta64(1, 'h'))

                # reset output names
                myawsm.snow_name = 'snow_{:02d}'.format(day_hour)
                myawsm.em_name = 'em_{:02d}'.format(day_hour)

                # reset start and end days
                myawsm.start_date = t
                myawsm.end_date = t + pd.to_timedelta(myawsm.n_forecast_hours,
                                                      unit='h')

                # recalculate start and end water year hour
                tmp_date = myawsm.start_date.replace(
                    tzinfo=myawsm.tzinfo)
                tmp_end_date = myawsm.end_date.replace(
                    tzinfo=myawsm.tzinfo)
                myawsm.start_wyhr = int(utils.water_day(tmp_date)[0]*24)
                myawsm.end_wyhr = int(utils.water_day(tmp_end_date)[0]*24)

                # run the model for the forecast times
                myawsm.run_smrf_ipysnobal()
