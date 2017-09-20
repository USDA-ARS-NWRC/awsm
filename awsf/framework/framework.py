import logging
import os
import coloredlogs
from datetime import datetime, timedelta
import pandas as pd
# import itertools
import numpy as np
import pytz
# import matplotlib.pyplot as plt

from smrf import data, distribute, output
from smrf.envphys import radiation
from smrf.utils import queue, io
from threading import Thread
from awsf.convertFiles import convertFiles as cvf
from awsf.interface import interface as smin


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

#         f = MyParser()
#         f.read(configFile)
#         self.config = f.as_dict()
        try:
            self.config = io.read_config(configFile)
            self.configFile = configFile
        except UnicodeDecodeError:
            raise UnicodeDecodeError('''The configuration file is not encoded in
                                    UTF-8, please change and retry''')

        # start logging

        if 'log_level' in self.config['awsf logging']:
            loglevel = self.config['awsf logging']['log_level'].upper()
        else:
            loglevel = 'INFO'

        numeric_level = getattr(logging, loglevel, None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        # setup the logging
        logfile = None
        if 'log_file' in self.config['awsf logging']:
            logfile = self.config['awsf logging']['log_file']

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

        self.path_dr = self.config['paths']['path_dr']
        self.basin = self.config['paths']['basin']
        if 'wy' in self.config['paths']:
            self.wy = self.config['paths']['wy']
        self.isops = self.config['paths']['isops']
        self.basin = self.config['paths']['basin']
        if 'proj' in self.config['paths']:
            self.proj = self.config['paths']['proj']
        self.isops = self.config['paths']['isops']
        if 'desc' in self.config['paths']:
            self.desc = self.config['paths']['desc']
        else:
            self.desc = ''

        if 'pathws' in self.config['paths']:
            self.pathws = self.config['paths']['pathws']
        if 'pathtp' in self.config['paths']:
            self.pathtp = self.config['paths']['pathtp']

        #self.anyini = self.config['paths']['smrfini']

        self.start_date = pd.to_datetime(self.config['time']['start_date'])
        self.end_date = pd.to_datetime(self.config['time']['end_date'])
        self.tmz = self.config['time']['time_zone']

        self.u  = int(self.config['grid']['u'])
        self.v  = int(self.config['grid']['v'])
        self.du  = int(self.config['grid']['du'])
        self.dv  = int(self.config['grid']['dv'])
        self.units = self.config['grid']['units']
        self.csys = self.config['grid']['csys']
        self.nx = int(self.config['grid']['nx'])
        self.ny = int(self.config['grid']['ny'])

        if self.config['topo']['type'] == 'ipw':
            self.fp_dem = self.config['topo']['dem']  # pull in location of the dem
        elif self.config['topo']['type'] == 'netcdf':
            self.fp_dem = self.config['topo']['filename']

        self.topotype = self.config['topo']['type']

        if 'ppt_desc_file' in self.config['files']:
            self.ppt_desc = self.config['files']['ppt_desc_file']
        else:
            # self.ppt_desc = '%sdata/ppt_desc%s.txt'%(self.path_wy,self.et.strftime("%Y%m%d"))
            self.ppt_desc = ''

        #self.anyini = self.config['paths']['smrfini']
        self.forecast_flag = 0
        # if 'fetime' in self.config['times']:
        #     self.forecast_flag = 1
        #     self.ft = pd.to_datetime(self.config['times']['fetime'])
        if 'prev_mod_file' in self.config['files']:
            self.prev_mod_file = self.config['files']['prev_mod_file']

        if 'ithreads' in self.config['isystem']:
            self.ithreads = self.config['isystem']['ithreads']
        else:
            self.ithreads = 4

        # list of sections releated to AWSF
        self.sec_awsf = ['paths', 'grid', 'files', 'awsf logging', 'isystem']
        # name of smrf file to write out
        self.smrfini = self.config['paths']['smrfini']

        # self._logger.info('Started SMRF --> %s' % datetime.now())
        # self._logger.info('Model start --> %s' % self.start_date)
        # self._logger.info('Model end --> %s' % self.end_date)
        # self._logger.info('Number of time steps --> %i' % self.time_steps)


    def runSmrf(self):
        """
        This initializes the distirbution classes based on the configFile
        sections for each variable.
        :func:`~smrf.framework.model_framework.SMRF.initializeDistribution`
        """

        # modify config and run smrf
        smin.smrfMEAS(self)

    def nc2ipw(self):
        """
        This initializes the distirbution classes based on the configFile
        sections for each variable.
        :func:`~smrf.framework.model_framework.SMRF.initializeDistribution`
        """

        cvf.nc2ipw_mea(self)

    def run_isnobal(self):
        """
        This initializes the distirbution classes based on the configFile
        sections for each variable.
        :func:`~smrf.framework.model_framework.SMRF.initializeDistribution`

        """

        # modify config and run smrf
        smin.run_isnobal(self)

    def mk_directories(self):
        # rigid directory work
        self._logger.info('AWSF creating directories')
        # make basin path
        self.path_ba = os.path.join(self.path_dr,self.basin)

        # check if ops or dev
        if self.isops:
            self.path_od = os.path.join(self.path_ba,'ops')
            # check if specified water year
            if len(str(self.wy)) > 1:
                self.path_wy = os.path.join(self.path_od,str(self.wy))
            else:
                self.path_wy = self.path_od

        else:
            self.path_od = os.path.join(self.path_ba,'devel')
            self.path_proj = os.path.join(self.path_od, self.proj)

            if len(str(wy)) > 1:
                self.path_wy = os.path.join(self.path_proj,str(self.wy))
            else:
                self.path_wy = self.path_proj

        if os.path.exists(self.path_dr):
            if not os.path.exists(self.path_wy):  # if the working path specified in the config file does not exist
                y_n = 'a'                        # set a funny value to y_n
                while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                    y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.path_wy)
                if y_n == 'n':
                    print('Please fix the base directory (path_wy) in your config file.')
                elif y_n =='y':
                    os.makedirs(os.path.join(self.path_wy, 'data/smrfOutputs/'))
                    os.makedirs(os.path.join(self.path_wy, 'data/input/'))
                    #os.makedirs(os.path.join(self.path_wy, 'data/init/'))
                    os.makedirs(os.path.join(self.path_wy, 'data/ppt_4b/'))
                    os.makedirs(os.path.join(self.path_wy, 'data/forecast/'))
                    os.makedirs(os.path.join(self.path_wy, 'runs/'))

                # look for description or prompt for one
                if len(self.desc) > 1:
                    pass
                else:
                    self.desc = raw_input('\nNo description for project. Enter one now:\n')
                # find where to write file
                if self.isops:
                    fp_desc = os.path.join(self.path_od, 'projectDescription.txt')
                else:
                    fp_desc = os.path.join(self.path_proj, 'projectDescription.txt')

                if not os.path.isfile(fp_desc):
                    f = open(fp_desc, 'w')
                    f.write(self.desc)
                    f.close()
                else:
                    self._logger.warning('Description file aleardy exists')


        else:
            self._logger.error('Base directory did not exist, not safe to conitnue')

        self.paths = os.path.join(self.path_wy,'data/smrfOutputs')
        self.ppt_desc = os.path.join(self.path_wy, 'data/ppt_desc{}.txt'.format(self.end_date.strftime("%Y%m%d")))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Provide some logging info about when AWSF was closed
        """

        self._logger.info('AWSF closed --> %s' % datetime.now())
