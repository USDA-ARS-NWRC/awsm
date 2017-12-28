import logging
import os
import sys
import coloredlogs
from datetime import datetime
import pandas as pd
import pytz
import copy
import numpy as np
# make input the same as raw input if python 2
try:
   input = raw_input
except NameError:
   pass

from smrf.utils import utils, io
from awsm.convertFiles import convertFiles as cvf
from awsm.interface import interface as smin
from awsm.interface import smrf_ipysnobal as smrf_ipy

from smrf import __core_config__ as __smrf_core_config__
from awsm import __core_config__ as __awsm_core_config__


class AWSM():
    """

    Args:
        configFile (str):  path to configuration file.

    Returns:
        AWSM class instance.

    Attributes:
    """


    def __init__(self, configFile):
        """
        Initialize the model, read config file, start and end date, and logging
        """
        # read the config file and store
        if not os.path.isfile(configFile):
            raise Exception('Configuration file does not exist --> {}'
                            .format(configFile))
        try:
            # get both master configs
            smrf_mcfg = io.get_master_config()
            awsm_mcfg = io.MasterConfig(__awsm_core_config__).cfg
            # combine master configs
            combined_mcfg = copy.deepcopy(smrf_mcfg)
            combined_mcfg.update(awsm_mcfg)
            #Read in the original users config
            self.config = io.get_user_config(configFile, mcfg = combined_mcfg)
            self.configFile = configFile
        except UnicodeDecodeError:
            raise Exception(('The configuration file is not encoded in '
                                    'UTF-8, please change and retry'))

        # create blank log and error log because logger is not initialized yet
        self.tmp_log = []
        self.tmp_err = []
        self.tmp_warn = []

        #Add defaults.
        self.tmp_log.append("Adding defaults to config...")
        self.config = io.add_defaults(self.config, combined_mcfg)

        #Check the user config file for errors and report issues if any
        self.tmp_log.append("Checking config file for issues...")
        warnings, errors = io.check_config_file(self.config,combined_mcfg,user_cfg_path=configFile)
        io.print_config_report(warnings, errors)

        #Exit AWSM if config file has errors
        if len(errors) > 0:
            print("Errors in the config file. See configuration status report above.")
            sys.exit()

        # update config paths to be absolute
        self.config = io.update_config_paths(self.config, configFile, combined_mcfg)

        ################### Decide which modules to run ######################
        self.do_smrf = self.config['awsm master']['run_smrf']
        self.do_isnobal = self.config['awsm master']['run_isnobal']
        self.do_wrf = self.config['awsm master']['use_wrf']
        self.do_smrf_ipysnobal = self.config['awsm master']['run_smrf_ipysnobal']
        self.do_ipysnobal = self.config['awsm master']['run_ipysnobal']

        # options for converting files
        self.do_make_in = self.config['awsm master']['make_in']
        self.do_make_nc = self.config['awsm master']['make_nc']

        # options for masking isnobal
        self.mask_isnobal = self.config['awsm master']['mask_isnobal']
        if self.mask_isnobal:
            # mask file
            self.fp_mask = os.path.abspath(self.config['topo']['mask'])

        ################# Time information ##################
        self.start_date = pd.to_datetime(self.config['time']['start_date'])
        self.end_date = pd.to_datetime(self.config['time']['end_date'])
        self.time_step = self.config['time']['time_step']
        self.tmz = self.config['time']['time_zone']
        self.tzinfo = pytz.timezone(self.config['time']['time_zone'])
        # date to use for finding wy
        tmp_date = self.start_date.replace(tzinfo=self.tzinfo)
        tmp_end_date = self.end_date.replace(tzinfo=self.tzinfo)

        # find water year hour of start and end date
        self.start_wyhr = int(utils.water_day(tmp_date)[0]*24)
        self.end_wyhr = int(utils.water_day(tmp_end_date)[0]*24)

        # find start of water year
        tmpwy = utils.water_day(tmp_start_date)[1] - 1
        self.wy_start = pd.to_datetime('%d-10-01'%tmpwy)

        # parameters needed for restart procedure
        if self.config['isnobal restart']['restart_crash'] == True:
            self.restart_run = True
            # find restart hour datetime
            reset_offset = pd.to_timedelta(self.restart_hr, unit='h')
            # set a new start date for this run
            self.restart_date = self.start_date + reset_offset
            self._logger.info('Restart date is {}'.format(self.start_date))

        ################# Store some paths from config file ##################
        # path to the base drive (i.e. /data/blizzard)
        if self.config['paths']['path_dr'] != None:
            self.path_dr = os.path.abspath(self.config['paths']['path_dr'])
        else:
            print('No base path to drive given. Exiting now!')
            sys.exit()

        # name of your basin (i.e. Tuolumne)
        self.basin = self.config['paths']['basin']
        # water year of run
        self.wy = utils.water_day(tmp_date)[1]
        # if the run is operational or not
        self.isops = self.config['paths']['isops']
        # name of project if not an operational run
        self.proj = self.config['paths']['proj']
        # check for project description
        self.desc = self.config['paths']['desc']

        if self.do_wrf:
            self.tmp_log.append('Forecasting set to True')


            self.fp_wrfdata = self.config['forecast']['wrf_data']
            if self.fp_wrfdata == None:
                self.tmp_err.append('Forecast set to true, but no wrf_data given')
                print("Errors in the config file. See configuration status report above.")
                print(self.tmp_err)
                sys.exit()

            self.zone_number = self.config['forecast']['zone_number']
            self.zone_letter = self.config['forecast']['zone_letter']

            if self.config['system']['threading'] == True:
                # Can't run threaded smrf if running wrf_data
                self.tmp_err.append('Cannot run SMRF threaded with gridded input data')
                print(self.tmp_err)
                sys.exit()

        ################# Grid data for iSnobal ##################
        self.u  = int(self.config['grid']['u'])
        self.v  = int(self.config['grid']['v'])
        self.du  = int(self.config['grid']['du'])
        self.dv  = int(self.config['grid']['dv'])
        self.units = self.config['grid']['units']
        self.csys = self.config['grid']['csys']
        self.nx = int(self.config['grid']['nx'])
        self.ny = int(self.config['grid']['ny'])
        self.nbits = int(self.config['grid']['nbits'])
        self.soil_temp = self.config['soil_temp']['temp']

        # Time step mass thresholds for iSnobal
        self.mass_thresh = []
        self.mass_thresh.append(self.config['grid']['thresh_normal'])
        self.mass_thresh.append(self.config['grid']['thresh_medium'])
        self.mass_thresh.append(self.config['grid']['thresh_small'])

        ################# Topo information ##################
        self.topotype = self.config['topo']['type']
        if self.topotype == 'ipw':
            self.fp_dem = os.path.abspath(self.config['topo']['dem'])  # pull in location of the dem
        elif self.topotype == 'netcdf':
            self.fp_dem = os.path.abspath(self.config['topo']['filename'])

        # init file just for surface roughness
        if self.config['files']['roughness_init'] != None:
            self.roughness_init = os.path.abspath(self.config['files']['roughness_init'])
        else:
            self.roughness_init = self.config['files']['roughness_init']

        # point to snow ipw image for restart of run
        if self.config['files']['prev_mod_file'] != None:
            self.prev_mod_file = os.path.abspath(self.config['files']['prev_mod_file'])

        # threads for running iSnobal
        self.ithreads = self.config['awsm system']['ithreads']
        # how often to output form iSnobal
        self.output_freq = self.config['awsm system']['output_frequency']

        # options for restarting iSnobal
        if self.config['isnobal restart']['restart_crash'] == True:
            #self.new_init = self.config['isnobal restart']['new_init']
            self.depth_thresh = self.config['isnobal restart']['depth_thresh']
            self.restart_hr = int(self.config['isnobal restart']['wyh_restart_output'])

        # iSnobal active layer
        self.active_layer = self.config['grid']['active_layer']

        # if we are going to run ipysnobal with smrf
        if self.do_smrf_ipysnobal or self.do_ipysnobal:
            #print('Stuff happening here \n\n\n')
            self.ipy_threads = self.ithreads
            self.ipy_init_type = self.config['ipysnobal initial conditions']['input_type']
            # change this
            self.forcing_data_type = self.config['ipysnobal']['forcing_data_type']

        # list of sections releated to AWSM (These will be removed for smrf config)
        # self.sec_awsm = ['awsm master', 'awsm system', 'paths', 'grid', 'files', 'awsm logging',
        #                 'isnobal restart', 'ipysnobal', 'ipysnobal initial conditions',
        #                 'ipysnobal output', 'ipysnobal constants', 'forecast']
        self.sec_awsm = awsm_mcfg.keys()

        # Make rigid directory structure
        self.mk_directories()

        ################# Generate config backup ##################
        order_lst= ['awsm master', 'paths', 'forecast', 'grid', 'files',
                     'awsm system', 'isnobal restart', 'ipysnobal',
                     'ipysnobal initial conditions', 'ipysnobal constants']

        titles = {'awsm master' : 'Configurations for AWSM Master section',
                  'paths' : 'Configurations for PATHS section for rigid directory work',
                  'forecast' : 'Configurations for FORECAST section for running with WRF forecast',
                  'grid' : 'Configurations for GRID data to run iSnobal',
                  'files' : 'Input files to run AWSM',
                  'awsm system' : 'System parameters',
                  'isnobal restart' : 'Parameters for restarting from crash',
                  'ipysnobal' : 'Running Pythonm wrapped iSnobal',
                  'ipysnobal initial conditions' : 'Initial condition parameters for iPySnobal',
                  'ipysnobal constants' : 'Input constants for iPySnobal'
                }
        config_backup_location = os.path.join(self.pathdd, 'awsm_config_backup.ini')
        io.generate_config(self.config,config_backup_location, order_lst=order_lst, titles=titles)


        # create log now that directory structure is done
        self.createLog()


    def createLog(self):
        '''
        Now that the directory structure is done, create log file and print out
        saved logging statements.
        '''
        # start logging
        loglevel = self.config['awsm system']['log_level'].upper()

        numeric_level = getattr(logging, loglevel, None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        # setup the logging
        folder_date_stamp = '{:04d}_{:04d}'.format(self.start_wyhr, self.end_wyhr)
        logfile = None
        if self.config['awsm system']['log_to_file'] == True:
            if self.config['isnobal restart']['restart_crash'] == True:
                logfile = os.path.join(self.pathll, 'log_restart_{}.out'.format(self.restart_hr))
            elif self.do_wrf:
                logfile = os.path.join(self.pathll, 'log_forecast_{}.out'.format(folder_date_stamp))
            else:
                logfile = os.path.join(self.pathll, 'log_{}.out'.format(folder_date_stamp))
            # let user know
            print('Logging to file: {}'.format(logfile))

        fmt = '%(levelname)s:%(name)s:%(message)s'
        if logfile is not None:
            logging.basicConfig(filename=logfile,
                                filemode='w',
                                level=numeric_level,
                                format=fmt)
        else:
            logging.basicConfig(level=numeric_level)
            coloredlogs.install(level=numeric_level, fmt=fmt)

        self._loglevel = numeric_level

        self._logger = logging.getLogger(__name__)

        # dump saved logs
        if len(self.tmp_log) > 0:
            for l in self.tmp_log:
                self._logger.info(l)
        if len(self.tmp_warn) > 0:
            for l in self.tmp_warn:
                self._logger.warning(l)
        if len(self.tmp_err) > 0:
            for l in self.tmp_err:
                self._logger.error(l)

    def runSmrf(self):
        """
        Run smrf. Calls :mod: `awsm.interface.interface.smrfMEAS`
        """
        # modify config and run smrf
        smin.smrfMEAS(self)

    def runSmrf_wrf(self):
        """
        Convert ipw smrf output to isnobal inputs. Calls
        :mod: `awsm.convertFiles.convertFiles.nc2ipw_mea`
        """
        # modify config and run smrf
        smin.smrf_go_wrf(self)

    def nc2ipw(self, runtype):
        """
        Convert ipw smrf output to isnobal inputs
        """
        cvf.nc2ipw_mea(self, runtype)

    def ipw2nc(self, runtype):
        """
        Convert ipw output to netcdf files. Calls
        :mod: `awsm.convertFiles.convertFiles.ipw2nc_mea`
        """
        cvf.ipw2nc_mea(self, runtype)

    def run_isnobal(self):
        """
        Run isnobal. Calls :mod: `awsm.interface.interface.run_isnobal`
        """

        smin.run_isnobal(self)

    def run_isnobal_forecast(self):
        """
        Run isnobal with smrf forecast data
        """
        # modify config and run smrf
        smin.run_isnobal_forecast(self)

    def run_smrf_ipysnobal(self):
        """
        Run smrf and pass inputs to ipysnobal in memory.
        Calls :mod: `awsm.interface.smrf_ipysnobal.run_smrf_ipysnobal`
        """

        smrf_ipy.run_smrf_ipysnobal(self)

    def run_ipysnobal(self):
        """
        Run PySnobal from previously run smrf forcing data
        Calls :mod: `awsm.interface.smrf_ipysnobal.run_ipysnobal`
        """
        smrf_ipy.run_ipysnobal(self)

    def restart_crash_image(self):
        """
        Restart isnobal. Calls :mod: `awsm.interface.interface.restart_crash_image`
        """
        # modify config and run smrf
        smin.restart_crash_image(self)

    def mk_directories(self):
        """
        Create all needed directories starting from the working drive
        """
        # rigid directory work
        self.tmp_log.append('AWSM creating directories')

        # string to append to folders indicatiing run start and end
        folder_date_stamp = '{:04d}_{:04d}'.format(self.start_wyhr, self.end_wyhr)

        # make basin path
        self.path_ba = os.path.join(self.path_dr,self.basin)

        # check if ops or dev
        if self.isops:
            opsdev = 'ops'
        else:
            opsdev = 'devel'
        # assign paths accordinly
        self.path_od = os.path.join(self.path_ba, opsdev)
        self.path_wy = os.path.join(self.path_od,'wy{}'.format(self.wy))
        self.path_wy = os.path.join(self.path_wy, self.proj)

        # specific data folder conatining
        self.pathd = os.path.join(self.path_wy, 'data')
        self.pathr = os.path.join(self.path_wy, 'runs')
        # log folders
        self.pathlog = os.path.join(self.path_wy, 'logs')
        self.pathll = os.path.join(self.pathlog, 'log{}'.format(folder_date_stamp))

        # name of temporary smrf file to write out
        self.smrfini = os.path.join(self.path_wy, 'tmp_smrf_config.ini')
        self.wrfini = os.path.join(self.path_wy, 'tmp_smrf_wrf_config.ini')


        if not self.do_wrf:
            # assign path names for isnobal, path_names_att will be used
            # to create necessary directories
            path_names_att = ['pathdd', 'pathrr', 'pathi', 'pathinit', 'pathro', 'paths', 'path_ppt']
            self.pathdd = os.path.join(self.pathd, 'data{}'.format(folder_date_stamp))
            self.pathrr =    os.path.join(self.pathr, 'run{}'.format(folder_date_stamp))
            self.pathi =    os.path.join(self.pathdd, 'input/')
            self.pathinit = os.path.join(self.pathdd, 'init/')
            self.pathro =   os.path.join(self.pathrr, 'output/')
            self.paths = os.path.join(self.pathdd,'smrfOutputs')
            self.ppt_desc = os.path.join(self.pathdd, 'ppt_desc{}.txt'.format(folder_date_stamp))
            self.path_ppt = os.path.join(self.pathdd, 'ppt_4b')
            # used to check if data direcotry exists
            check_if_data = self.pathdd
        else:
            path_names_att = ['path_wrf_data', 'path_wrf_run', 'path_wrf_i', 'path_wrf_init', 'path_wrf_ro', 'path_wrf_s', 'path_wrf_ppt']
            self.path_wrf_data = os.path.join(self.pathd, 'forecast{}'.format(folder_date_stamp))
            self.path_wrf_run = os.path.join(self.pathr, 'forecast{}'.format(folder_date_stamp))
            self.path_wrf_i =    os.path.join(self.path_wrf_data, 'input/')
            self.path_wrf_init = os.path.join(self.path_wrf_data, 'init/')
            self.path_wrf_ro =   os.path.join(self.path_wrf_run, 'output/')
            self.path_wrf_s = os.path.join(self.path_wrf_data,'smrfOutputs')
            self.wrf_ppt_desc = os.path.join(self.path_wrf_data, 'ppt_desc{}.txt'.format(folder_date_stamp))
            self.path_wrf_ppt = os.path.join(self.path_wrf_data, 'ppt_4b')
            # used to check if data direcotry exists
            check_if_data = self.path_wrf_data

        # add log path to create directory
        path_names_att.append('pathll')

        # Only start if your drive exists
        if os.path.exists(self.path_dr):
            # If the specific path to your WY does not exist, create it and following directories
            if not os.path.exists(self.path_wy):  # if the working path specified in the config file does not exist
                y_n = 'a'                        # set a funny value to y_n
                while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                    y_n = input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.path_wy)
                if y_n == 'n':
                    self.tmp_err.append('Please fix the base directory (path_wy) in your config file.')
                    print(self.tmp_err)
                    sys.exit()
                elif y_n =='y':
                    self.make_rigid_directories(path_names_att)

            # If WY exists, but not this exact run for the dates, create it
            elif not os.path.exists(check_if_data):  # if the working path specified in the config file does not exist
                y_n = 'a'                        # set a funny value to y_n
                while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                    y_n = input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%check_if_data)
                if y_n == 'n':
                    self.tmp_err.append('Please fix the base directory (path_wy) in your config file.')
                    print(self.tmp_err)
                    sys.exit()
                elif y_n =='y':
                    self.make_rigid_directories(path_names_att)

            else:
                self.tmp_warn.append('This has the potential to overwrite results in {}!!!'.format(check_if_data))

            # make sure runs exists
            if not os.path.exists(os.path.join(self.path_wy, 'runs/')):
                os.makedirs(os.path.join(self.path_wy, 'runs/'))

            # if we're not running wrf data, make sure path to outputs exists
            if not self.do_wrf:
                if not os.path.exists(self.pathro):
                    os.makedirs(self.pathro)

            # find where to write file
            fp_desc = os.path.join(self.path_wy, 'projectDescription.txt')

            if not os.path.isfile(fp_desc):
                # look for description or prompt for one
                if self.desc != None:
                    pass
                else:
                    self.desc = input('\nNo description for project. Enter one now:\n')
                f = open(fp_desc, 'w')
                f.write(self.desc)
                f.close()
            else:
                self.tmp_log.append('Description file aleardy exists\n')

        else:
            self.tmp_err.append('Base directory did not exist, not safe to conitnue.\
                                Make sure base directory exists before running.')
            print(self.tmp_err)
            sys.exit()

    def make_rigid_directories(self, path_name):
        """
        Creates rigid directory structure from list of relative bases and
        extensions from the base
        """
        # loop through lists
        for idp, pn in enumerate(path_name):
            # get attribute of path
            path = getattr(self,pn)

            if not os.path.exists(path):
                os.makedirs(path)
            else:
                self.tmp_log.append('Directory ---{}--- exists, not creating.\n')


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Provide some logging info about when AWSM was closed
        """

        self._logger.info('AWSM closed --> %s' % datetime.now())
