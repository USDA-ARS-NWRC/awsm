import copy
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import numpy as np
import netCDF4 as nc
import pytz
from inicheck.config import MasterConfig, UserConfig
from inicheck.output import print_config_report, generate_config
from inicheck.tools import get_user_config, check_config, cast_all_variables
from smrf.utils import utils
import smrf


import smrf.framework.logger as logger

from awsm.framework import ascii_art
from awsm.models.smrf_connector import SMRFConnector
from awsm.models.pysnobal import PySnobal, ModelInit


class AWSM():
    """
    Args:
        configFile (str):  path to configuration file.

    Returns:
        AWSM class instance.

    Attributes:
    """

    def __init__(self, config):
        """
        Initialize the model, read config file, start and end date, and logging
        Args:
            config: string path to the config file or inicheck UserConfig
                instance
        """

        self.read_config(config)

        # create blank log and error log because logger is not initialized yet
        self.tmp_log = []
        self.tmp_err = []
        self.tmp_warn = []

        self.parse_time()
        self.parse_folder_structure()
        self.mk_directories()
        self.create_log()

        # ################## Decide which modules to run #####################
        self.do_smrf = self.config['awsm master']['run_smrf']
        self.model_type = self.config['awsm master']['model_type']
        # self.do_smrf_ipysnobal = \
        #     self.config['awsm master']['run_smrf_ipysnobal']
        # self.do_ipysnobal = self.config['awsm master']['run_ipysnobal']
        self.do_forecast = False
        if 'gridded' in self.config and self.do_smrf:
            self.do_forecast = self.config['gridded']['hrrr_forecast_flag']

            # WARNING: The value here is inferred in SMRF.data.loadGrid. A
            # change here requires a change there
            self.n_forecast_hours = 18

        # store smrf version if running smrf
        self.smrf_version = smrf.__version__

        if self.do_forecast:
            self.tmp_log.append('Forecasting set to True')

            # self.fp_forecastdata = self.config['gridded']['wrf_file']
            # if self.fp_forecastdata is None:
            #     self.tmp_err.append('Forecast set to true, '
            #                         'but no grid file given')
            #     print("Errors in the config file. See configuration "
            #           "status report above.")
            #     print(self.tmp_err)
            #     sys.exit()

            if self.config['system']['threading']:
                # Can't run threaded smrf if running forecast_data
                self.tmp_err.append('Cannot run SMRF threaded with'
                                    ' gridded input data')
                print(self.tmp_err)
                sys.exit()

        # how often to output form iSnobal
        self.output_freq = self.config['awsm system']['output_frequency']
        # number of timesteps to run if ou don't want to run the whole thing
        self.run_for_nsteps = self.config['awsm system']['run_for_nsteps']
        # pysnobal output variables
        self.pysnobal_output_vars = self.config['ipysnobal']['variables']
        self.pysnobal_output_vars = [wrd.lower()
                                     for wrd in self.pysnobal_output_vars]

        # options for restarting iSnobal
        # TODO move to own function. Raise error if storm days file is not there
        if self.config['ipysnobal']['restart_date_time'] is not None:
            self.start_date = self.config['ipysnobal']['restart_date_time']
            self.start_date = self.start_date - \
                pd.Timedelta(minutes=self.config['time']['time_step'])

            # has to have the storm day file, else the albedo will be
            # set to fresh snow

        # read in update depth parameters
        self.update_depth = False
        if 'update depth' in self.config:
            self.update_depth = self.config['update depth']['update']
            self.update_file = self.config['update depth']['update_file']
            self.update_buffer = self.config['update depth']['buffer']
            self.flight_numbers = self.config['update depth']['flight_numbers']
            # if flights to use is not list, make it a list
            if self.flight_numbers is not None:
                if not isinstance(self.flight_numbers, list):
                    self.flight_numbers = [self.flight_numbers]

        # ################ Topo data for iSnobal ##################
        self.soil_temp = self.config['soil_temp']['temp']
        self.load_topo()

        # ################ Generate config backup ##################
        # if self.config['output']['input_backup']:
        # set location for backup and output backup of awsm sections
        config_backup_location = \
            os.path.join(self.path_output, 'awsm_config_backup.ini')
        generate_config(self.ucfg, config_backup_location)

        # create log now that directory structure is done
        # self.create_log()

        self.smrf_connector = SMRFConnector(self)

        # if we have a model, initialize it
        if self.model_type is not None:
            self.model_init = ModelInit(
                self.config,
                self.topo,
                self.path_output,
                self.start_date)

    @property
    def awsm_config_sections(self):
        return MasterConfig(modules='awsm').cfg.keys()

    @property
    def smrf_config_sections(self):
        return MasterConfig(modules='smrf').cfg.keys()

    def read_config(self, config):

        if isinstance(config, str):
            if not os.path.isfile(config):
                raise Exception('Configuration file does not exist --> {}'
                                .format(config))
            configFile = config

            try:
                combined_mcfg = MasterConfig(modules=['smrf', 'awsm'])

                # Read in the original users config
                self.ucfg = get_user_config(configFile, mcfg=combined_mcfg)
                self.configFile = configFile

            except UnicodeDecodeError as e:
                print(e)
                raise Exception(('The configuration file is not encoded in '
                                 'UTF-8, please change and retry'))

        elif isinstance(config, UserConfig):
            self.ucfg = config
            configFile = ''

        else:
            raise Exception("""Config passed to AWSM is neither file """
                            """name nor UserConfig instance""")

        # Check the user config file for errors and report issues if any
        warnings, errors = check_config(self.ucfg)
        print_config_report(warnings, errors)

        self.config = self.ucfg.cfg

        if len(errors) > 0:
            print("Errors in the config file. "
                  "See configuration status report above.")
            sys.exit()

    def load_topo(self):

        self.topo = smrf.data.load_topo.Topo(self.config['topo'])

        if not self.config['ipysnobal']['mask_isnobal']:
            self.topo.mask = np.ones_like(self.topo.dem)

        # see if roughness is in the topo
        f = nc.Dataset(self.config['topo']['filename'], 'r')
        f.set_always_mask(False)
        if 'roughness' not in f.variables.keys():
            self.tmp_warn.append(
                'No surface roughness given in topo, setting to 5mm')
            self.topo.roughness = 0.005 * np.ones_like(self.topo.dem)
        else:
            self.topo.roughness = f.variables['roughness'][:].astype(
                np.float64)

        f.close()

    def parse_time(self):
        """Parse the time configuration
        """

        self.start_date = pd.to_datetime(self.config['time']['start_date'])
        self.end_date = pd.to_datetime(self.config['time']['end_date'])
        self.time_step = self.config['time']['time_step']
        self.tzinfo = pytz.timezone(self.config['time']['time_zone'])

        # date to use for finding wy
        self.start_date = self.start_date.replace(tzinfo=self.tzinfo)
        self.end_date = self.end_date.replace(tzinfo=self.tzinfo)

        # find water year hour of start and end date
        self.start_wyhr = int(utils.water_day(self.start_date)[0]*24)
        self.end_wyhr = int(utils.water_day(self.end_date)[0]*24)

        # if there is a restart time
        if self.config['ipysnobal']['restart_date_time'] is not None:
            rs_dt = self.config['ipysnobal']['restart_date_time']
            rs_dt = pd.to_datetime(rs_dt).tz_localize(tz=self.tzinfo)
            self.config['ipysnobal']['restart_date_time'] = rs_dt

    def parse_folder_structure(self):
        """Parse the config to get the folder structure

        Raises:
            ValueError: daily_folders can only be ran with smrf_ipysnobal
        """

        if self.config['paths']['path_dr'] is not None:
            self.path_dr = os.path.abspath(self.config['paths']['path_dr'])
        else:
            print('No base path to drive given. Exiting now!')
            sys.exit()

        self.basin = self.config['paths']['basin']
        self.water_year = utils.water_day(self.start_date)[1]
        self.project_name = self.config['paths']['project_name']
        self.project_description = self.config['paths']['project_description']
        self.folder_date_style = self.config['paths']['folder_date_style']

        # setting to output in seperate daily folders
        self.daily_folders = self.config['awsm system']['daily_folders']
        if self.daily_folders and not self.run_smrf_ipysnobal:
            raise ValueError('Cannot run daily_folders with anything other'
                             ' than run_smrf_ipysnobal')

    def create_log(self):
        '''
        Now that the directory structure is done, create log file and print out
        saved logging statements.
        '''

        # clear the logger
        # for handler in logging.root.handlers:
        #     logging.root.removeHandler(handler)

        # setup the logging
        logfile = None
        if self.config['awsm system']['log_to_file']:
            # if self.config['isnobal restart']['restart_crash']:
            #     logfile = \
            #         os.path.join(self.path_log,
            #                      'log_restart_{}.out'.format(self.restart_hr))
            # elif self.do_forecast:
            #     logfile = \
            #         os.path.join(self.path_log,
            #                      'log_forecast_'
            #                      '{}.out'.format(self.folder_date_stamp))
            # else:
            logfile = \
                os.path.join(self.path_log,
                             'log_{}.out'.format(self.folder_date_stamp))
            # let user know
            print('Logging to file: {}'.format(logfile))

        self.config['awsm system']['log_file'] = logfile
        logger.SMRFLogger(self.config['awsm system'])

        self._logger = logging.getLogger(__name__)

        self._logger.info(ascii_art.MOUNTAIN)
        self._logger.info(ascii_art.TITLE)

        # dump saved logs
        for line in self.tmp_log:
            self._logger.info(line)
        for line in self.tmp_warn:
            self._logger.warning(line)
        for line in self.tmp_err:
            self._logger.error(line)

    def run_smrf(self):
        """
        Run smrf through the :mod: `awsm.smrf_connector.SMRFConnector`
        """

        self.smrf_connector.run_smrf()

    def run_smrf_ipysnobal(self):
        """
        Run smrf and pass inputs to ipysnobal in memory.
        """

        PySnobal(self).run_smrf_ipysnobal()
        # smrf_ipy.run_smrf_ipysnobal(self)

    # def run_awsm_daily(self):
    #     """
    #     This function runs
    #     :mod:`awsm.interface.smrf_ipysnobal.run_smrf_ipysnobal` on an
    #     hourly output from Pysnobal, outputting to daily folders, similar
    #     to the HRRR froecast.
    #     """

    #     smin.run_awsm_daily(self)

    def run_ipysnobal(self):
        """
        Run PySnobal from previously run smrf forcing data
        """
        PySnobal(self).run_ipysnobal()

    def mk_directories(self):
        """
        Create all needed directories starting from the working drive
        """
        # rigid directory work
        self.tmp_log.append('AWSM creating directories')

        # string to append to folders indicatiing run start and end
        if self.folder_date_style == 'day':
            self.folder_date_stamp = \
                '{}'.format(self.start_date.strftime("%Y%m%d"))

        elif self.folder_date_style == 'start_end':
            self.folder_date_stamp = \
                '{}_{}'.format(self.start_date.strftime("%Y%m%d"),
                               self.end_date.strftime("%Y%m%d"))

        # make basin path
        self.path_wy = os.path.join(
            self.path_dr,
            self.basin,
            'wy{}'.format(self.water_year),
            self.project_name
        )

        # all files will now be under one single folder
        self.path_output = os.path.join(
            self.path_wy,
            'run{}'.format(self.folder_date_stamp))
        self.path_log = os.path.join(self.path_output, 'logs')

        # name of temporary smrf file to write out
        self.smrfini = os.path.join(self.path_wy, 'tmp_smrf_config.ini')
        self.forecastini = os.path.join(self.path_wy,
                                        'tmp_smrf_forecast_config.ini')

        # assign path names for isnobal, path_names_att will be used
        # to create necessary directories
        path_names_att = ['path_output', 'path_log']

        # Only start if your drive exists
        if os.path.exists(self.path_dr):
            self.make_rigid_directories(path_names_att)
            self.create_project_description()

        else:
            self.tmp_err.append('Base directory did not exist, '
                                'not safe to continue. Make sure base '
                                'directory exists before running.')
            print(self.tmp_err)
            sys.exit()

    def create_project_description(self):
        """Create a project description in the base water year directory
        """

        # find where to write file
        fp_desc = os.path.join(self.path_wy, 'projectDescription.txt')

        if not os.path.isfile(fp_desc):
            with open(fp_desc, 'w') as f:
                f.write(self.project_description)

        else:
            self.tmp_log.append('Description file already exists')

    def make_rigid_directories(self, path_name):
        """
        Creates rigid directory structure from list of relative bases and
        extensions from the base
        """
        # loop through lists
        for idp, pn in enumerate(path_name):
            # get attribute of path
            path = getattr(self, pn)

            if not os.path.exists(path):
                os.makedirs(path)
            else:
                self.tmp_log.append(
                    'Directory --{}-- exists, not creating.'.format(path))

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Provide some logging info about when AWSM was closed
        """

        self._logger.info(
            'AWSM finished in: {}'.format(datetime.now() - self.start_time)
        )
        self._logger.info('AWSM closed --> %s' % datetime.now())
        logging.shutdown()


def run_awsm_daily_ops(config_file):
    """
    Run each day seperately. Calls run_awsm
    """
    # define some formats
    fmt_day = '%Y%m%d'
    fmt_cfg = '%Y-%m-%d %H:%M'
    add_day = pd.to_timedelta(24, unit='h')

    # get config instance
    config = get_user_config(config_file,
                             modules=['smrf', 'awsm'])

    # copy the config and get total start and end
    # config = deepcopy(base_config)
    # set naming style
    config.raw_cfg['paths']['folder_date_style'] = 'day'
    config.apply_recipes()
    config = cast_all_variables(config, config.mcfg)

    # get the water year
    cfg_start_date = pd.to_datetime(config.cfg['time']['start_date'])
    tzinfo = pytz.timezone(config.cfg['time']['time_zone'])
    wy = utils.water_day(cfg_start_date.replace(tzinfo=tzinfo))[1]

    # find the model start depending on restart
    if config.cfg['isnobal restart']['restart_crash']:
        offset_wyhr = int(config.cfg['isnobal restart']['wyh_restart_output'])
        wy_start = pd.to_datetime('{:d}-10-01'.format(wy - 1))
        model_start = wy_start + pd.to_timedelta(offset_wyhr, unit='h')
    else:
        model_start = config.cfg['time']['start_date']

    model_end = config.cfg['time']['end_date']

    # find output location for previous output
    paths = config.cfg['paths']

    prev_out_base = os.path.join(paths['path_dr'],
                                 paths['basin'],
                                 'wy{}'.format(wy),
                                 paths['project_name'],
                                 'runs')

    prev_data_base = os.path.join(paths['path_dr'],
                                  paths['basin'],
                                  'wy{}'.format(wy),
                                  paths['project_name'],
                                  'data')

    # find day of start and end
    start_day = pd.to_datetime(model_start.strftime(fmt_day))
    end_day = pd.to_datetime(model_end.strftime(fmt_day))

    # find total range of run
    ndays = int((end_day-start_day).days) + 1
    date_list = [start_day +
                 pd.to_timedelta(x, unit='D') for x in range(0, ndays)]

    # loop through daily runs and run awsm
    for idd, sd in enumerate(date_list):
        new_config = copy.deepcopy(config)
        if idd > 0:
            new_config.raw_cfg['isnobal restart']['restart_crash'] = False
            new_config.raw_cfg['ipysnobal']['thresh_normal'] = 60
            new_config.raw_cfg['ipysnobal']['thresh_medium'] = 10
            new_config.raw_cfg['ipysnobal']['thresh_small'] = 1
        # get the end of the day
        ed = sd + add_day

        # make sure we're in the model date range
        if sd < model_start:
            sd = model_start
        if ed > model_end:
            ed = model_end

        # set the start and end dates
        new_config.raw_cfg['time']['start_date'] = sd.strftime(fmt_cfg)
        new_config.raw_cfg['time']['end_date'] = ed.strftime(fmt_cfg)

        # reset the initialization
        if idd > 0:
            # find previous output file
            prev_day = sd - pd.to_timedelta(1, unit='D')
            prev_out = os.path.join(prev_out_base,
                                    'run{}'.format(prev_day.strftime(fmt_day)),
                                    'ipysnobal.nc')
            # reset if running the model
            if new_config.cfg['awsm master']['model_type'] is not None:
                new_config.raw_cfg['ipysnobal']['init_type'] = 'netcdf_out'
                new_config.raw_cfg['ipysnobal']['init_file'] = prev_out

            # if we have a previous storm day file, use it
            prev_storm = os.path.join(prev_data_base,
                                      'data{}'.format(
                                          prev_day.strftime(fmt_day)),
                                      'smrfOutputs', 'storm_days.nc')
            if os.path.isfile(prev_storm):
                new_config.raw_cfg['precip']['storm_days_restart'] = prev_storm

        # apply recipes with new settings
        new_config.apply_recipes()
        new_config = cast_all_variables(new_config, new_config.mcfg)

        # run awsm for the day
        run_awsm(new_config)


def run_awsm(config):
    """
    Function that runs awsm how it should be operate for full runs.

    Args:
        config: string path to the config file or inicheck UserConfig instance
    """

    with AWSM(config) as a:
        if a.do_forecast:
            runtype = 'forecast'
        else:
            runtype = 'smrf'

        if not a.config['isnobal restart']['restart_crash']:
            if a.do_smrf:
                a.run_smrf()

            if a.model_type == 'ipysnobal':
                a.run_ipysnobal()

        # if restart
        else:
            if a.model_type == 'ipysnobal':
                a.run_ipysnobal()

        # Run iPySnobal from SMRF in memory
        if a.model_type == 'smrf_ipysnobal':
            if a.daily_folders:
                a.run_awsm_daily()
            else:
                a.run_smrf_ipysnobal()
