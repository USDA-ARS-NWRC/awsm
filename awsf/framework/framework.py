import logging
import os
import coloredlogs
from datetime import datetime
import pandas as pd
import pytz

from smrf import data, distribute, output
from smrf.envphys import radiation
from smrf.utils import queue, io
from awsf.convertFiles import convertFiles as cvf
from awsf.interface import interface as smin
from awsf.interface import smrf_ipysnobal as smrf_ipy


class AWSF():
    """

    Args:
        configFile (str):  path to configuration file.

    Returns:
        AWSF class instance.

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
            self.config = io.read_config(configFile)
            self.configFile = configFile
        except UnicodeDecodeError:
            raise UnicodeDecodeError('''The configuration file is not encoded in
                                    UTF-8, please change and retry''')

        # start logging
        if 'log_level' in self.config['awsf system']:
            loglevel = self.config['awsf system']['log_level'].upper()
        else:
            loglevel = 'INFO'

        numeric_level = getattr(logging, loglevel, None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        # setup the logging
        logfile = None
        if 'log_file' in self.config['awsf system']:
            logfile = self.config['awsf system']['log_file']

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

        ################### Decide which modules to run ######################
        self.do_smrf = self.config['awsf master']['run_smrf']
        self.do_isnobal = self.config['awsf master']['run_isnobal']
        self.do_wrf = self.config['awsf master']['use_wrf']
        self.do_smrf_ipysnobal = self.config['awsf master']['run_smrf_ipysnobal']

        ################# Store some paths from config file ##################
        # path to the base drive (i.e. /data/blizzard)
        self.path_dr = os.path.abspath(self.config['paths']['path_dr'])
        # name of your basin (i.e. Tuolumne)
        self.basin = self.config['paths']['basin']
        # water year of run
        if 'wy' in self.config['paths']:
            self.wy = self.config['paths']['wy']
        # if the run is operational or not
        self.isops = self.config['paths']['isops']
        # name of project if not an operational run
        if 'proj' in self.config['paths']:
            self.proj = self.config['paths']['proj']
        # check for project description
        if 'desc' in self.config['paths']:
            self.desc = self.config['paths']['desc']
        else:
            self.desc = ''

        # path with scripts
        if 'pathws' in self.config['paths']:
            self.pathws = os.path.abspath(self.config['paths']['pathws'])
        # path to topo files
        if 'pathtp' in self.config['paths']:
            self.pathtp = os.path.abspath(self.config['paths']['pathtp'])

        # name of smrf file to write out (not path)
        self.smrfini = self.config['paths']['smrfini']

        ################# Time information ##################
        self.start_date = pd.to_datetime(self.config['time']['start_date'])
        self.end_date = pd.to_datetime(self.config['time']['end_date'])

        if self.do_wrf:
            if 'forecast' in self.config:
                self._logger.info('Forecasting set to True')

                if 'forecast_date' in self.config['forecast']:
                    self.forecast_date = pd.to_datetime(self.config['forecast']['forecast_date'])
                else:
                    self._logger.error('Forecast set to true, but no forecast_date given')
                if ['wrf_data'] in self.config['forecast']:
                    self.fp_wrfdata = self.config['forecast']['wrf_data']
                else:
                    self._logger.error('Forecast set to true, but no wrf_data given')
                self.zone_number = self.config['forecast']['zone_number']
                self.zone_letter = self.config['forecast']['zone_letter']
            else:
                self._logger.error('use_wrf set to True, but no forecast section.')

        self.time_step = self.config['time']['time_step']
        self.tmz = self.config['time']['time_zone']
        self.tzinfo = pytz.timezone(self.config['time']['time_zone'])

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

        ################# Topo information ##################
        self.topotype = self.config['topo']['type']
        if self.topotype == 'ipw':
            self.fp_dem = os.path.abspath(self.config['topo']['dem'])  # pull in location of the dem
        elif self.topotype == 'netcdf':
            self.fp_dem = os.path.abspath(self.config['topo']['filename'])

        # mask file
        self.fp_mask = os.path.abspath(self.config['topo']['mask'])
        # init file just for surface roughness
        if 'roughness_init' in self.config['files']:
            self.roughness_init = os.path.abspath(self.config['files']['roughness_init'])
        else:
            self.roughness_init = None

        if 'prev_mod_file' in self.config['files']:
            self.prev_mod_file = os.path.abspath(self.config['files']['prev_mod_file'])

        # threads for running iSnobal
        if 'ithreads' in self.config['awsf system']:
            self.ithreads = self.config['awsf system']['ithreads']
        else:
            self.ithreads = 1

        # options for restarting iSnobal
        if 'isnobal restart' in self.config:
            if 'restart_crash' in self.config['isnobal restart']:
                if self.config['isnobal restart']['restart_crash'] == True:
                    #self.new_init = self.config['isnobal restart']['new_init']
                    self.depth_thresh = self.config['isnobal restart']['depth_thresh']
                    self.restart_hr = int(self.config['isnobal restart']['wyh_restart_output'])

        # name of smrf file to write out
        self.smrfini = self.config['paths']['smrfini']
        self.wrfini = self.config['paths']['wrfini']
        # if we are going to run ipysnobal with smrf
        if 'ipysnobal' in self.config:
            if self.config['ipysnobal']['smrf_ipysnobal_flag'] == True:
                #print('Stuff happening here \n\n\n')
                self.ipy_threads = self.config['ipysnobal']['nthreads']
                self.ipy_init_type = self.config['ipysnobal initial conditions']['input_type']

        # list of sections releated to AWSF (These will be removed for smrf config)
        self.sec_awsf = ['awsf master', 'paths', 'grid', 'files', 'awsf logging', 'isystem',
                        'isnobal restart', 'ipysnobal', 'ipysnobal initial conditions',
                        'ipysnobal output', 'ipysnobal constants', 'forecast']

    def runSmrf(self):
        """
        Run smrf. Calls :mod: `awsf.interface.interface.smrfMEAS`
        """
        # modify config and run smrf
        smin.smrfMEAS(self)

    def runSmrf_wrf(self):
        """
        Convert ipw smrf output to isnobal inputs. Calls
        :mod: `awsf.convertFiles.convertFiles.nc2ipw_mea`
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
        :mod: `awsf.convertFiles.convertFiles.ipw2nc_mea`
        """
        cvf.ipw2nc_mea(self, runtype)

    def run_isnobal(self):
        """
        Run isnobal. Calls :mod: `awsf.interface.interface.run_isnobal`
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
        Calls :mod: `awsf.interface.smrf_ipysnobal.run_smrf_ipysnobal`
        """

        smrf_ipy.run_smrf_ipysnobal(self)

    def restart_crash_image(self):
        """
        Restart isnobal. Calls :mod: `awsf.interface.interface.restart_crash_image`
        """
        # modify config and run smrf
        smin.restart_crash_image(self)

    def mk_directories(self):
        """
        Create all needed directories starting from the working drive
        """
        # rigid directory work
        self._logger.info('AWSF creating directories')
        # make basin path
        self.path_ba = os.path.join(self.path_dr,self.basin)

        # check if ops or dev
        if self.isops:
            self.path_od = os.path.join(self.path_ba,'ops')
            # check if specified water year
            if len(str(self.wy)) > 1:
                self.path_wy = os.path.join(self.path_od,'wy{}'.format(self.wy))
            else:
                self.path_wy = self.path_od

        else:
            self.path_od = os.path.join(self.path_ba,'devel')
            self.path_proj = os.path.join(self.path_od, self.proj)

            if len(str(self.wy)) > 1:
                self.path_wy = os.path.join(self.path_proj,'wy{}'.format(self.wy))
            else:
                self.path_wy = self.path_proj

        # specific data folder conatining
        self.pathd = os.path.join(self.path_wy, 'data/data{}_{}'.format(self.start_date.strftime("%Y%m%d"), self.end_date.strftime("%Y%m%d")))

        if os.path.exists(self.path_dr):
            if not os.path.exists(self.path_wy):  # if the working path specified in the config file does not exist
                y_n = 'a'                        # set a funny value to y_n
                while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                    y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.path_wy)
                if y_n == 'n':
                    print('Please fix the base directory (path_wy) in your config file.')
                elif y_n =='y':
                    os.makedirs(os.path.join(self.pathd, 'smrfOutputs/'))
                    os.makedirs(os.path.join(self.pathd, 'input/'))
                    os.makedirs(os.path.join(self.pathd, 'init/'))
                    os.makedirs(os.path.join(self.pathd, 'ppt_4b/'))
                    os.makedirs(os.path.join(self.pathd, 'forecast/'))
                    os.makedirs(os.path.join(self.path_wy, 'runs/'))

            elif not os.path.exists(self.pathd):  # if the working path specified in the config file does not exist
                y_n = 'a'                        # set a funny value to y_n
                while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                    y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.pathd)
                if y_n == 'n':
                    print('Please fix the base directory (path_wy) in your config file.')
                elif y_n =='y':
                    os.makedirs(os.path.join(self.pathd, 'smrfOutputs/'))
                    os.makedirs(os.path.join(self.pathd, 'input/'))
                    os.makedirs(os.path.join(self.pathd, 'init/'))
                    os.makedirs(os.path.join(self.pathd, 'ppt_4b/'))

                if not os.path.exists(os.path.join(self.path_wy, 'runs/')):
                    os.makedirs(os.path.join(self.path_wy, 'runs/'))
            else:
                self._logger.warning('This has the potential to overwrite results in {}!!!'.format(self.pathd))

            # find where to write file
            if self.isops:
                fp_desc = os.path.join(self.path_od, 'projectDescription.txt')
            else:
                fp_desc = os.path.join(self.path_proj, 'projectDescription.txt')

            if not os.path.isfile(fp_desc):
                # look for description or prompt for one
                if len(self.desc) > 1:
                    pass
                else:
                    self.desc = raw_input('\nNo description for project. Enter one now:\n')
                f = open(fp_desc, 'w')
                f.write(self.desc)
                f.close()
            else:
                self._logger.info('Description file aleardy exists')

            # assign path names for isnobal
            self.pathi =    os.path.join(self.pathd, 'input/')
            self.pathinit = os.path.join(self.pathd, 'init/')
            self.pathr =    os.path.join(self.path_wy, 'runs/run{}_{}'.format(self.start_date.strftime("%Y%m%d"), self.end_date.strftime("%Y%m%d")))
            self.pathro =   os.path.join(self.pathr, 'output/')
            if not os.path.exists(self.pathro):
                os.makedirs(self.pathro)

            # make directories for wrf
            if self.do_wrf:
                self.path_wrf_data = os.path.join(self.path_wy, 'data/', 'forecast{}_{}'.format(self.end_date.strftime("%Y%m%d"), self.forecast_date.strftime("%Y%m%d")))
                self.path_wrf_run = os.path.join(self.path_wy, 'run/', 'forecast{}_{}'.format(self.end_date.strftime("%Y%m%d"), self.forecast_date.strftime("%Y%m%d")))
                self.path_wrf_i =    os.path.join(self.path_wrf_data, 'input/')
                self.path_wrf_init = os.path.join(self.path_wrf_data, 'init/')
                self.path_wrf_ro =   os.path.join(self.path_wrf_run, 'output/')
                self.path_wrf_s = os.path.join(self.path_wrf_i,'smrfOutputs')
                self.wrf_ppt_desc = os.path.join(self.path_wrf_data, 'ppt_desc{}.txt'.format(self.forecast_date.strftime("%Y%m%d")))

                if not os.path.exists(self.path_wrf_data):
                    os.makedirs(self.path_wrf_data)
                    os.makedirs(self.path_wrf_init)
                    os.makedirs(self.path_wrf_i)
                    os.makedirs(os.path.join(self.path_wrf_i,'ppt_4b/'))
                    os.makedirs(self.path_wrf_s)
                if not os.path.exists(self.path_wrf_run):
                    os.makedirs(self.path_wrf_run)
                    os.makedirs(self.path_wrf_ro)

        else:
            self._logger.error('Base directory did not exist, not safe to conitnue.\
                                Make sure base directory exists before running.')

        self.paths = os.path.join(self.pathd,'smrfOutputs')
        self.ppt_desc = os.path.join(self.pathd, 'ppt_desc{}.txt'.format(self.end_date.strftime("%Y%m%d")))


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Provide some logging info about when AWSF was closed
        """

        self._logger.info('AWSF closed --> %s' % datetime.now())
