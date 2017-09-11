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
        print('initializing AWSF')
        # read the config file and store
        if not os.path.isfile(configFile):
            raise Exception('Configuration file does not exist --> {}'
                            .format(configFile))

#         f = MyParser()
#         f.read(configFile)
#         self.config = f.as_dict()
        try:
            self.config = io.read_config(configFile)
        except UnicodeDecodeError:
            raise UnicodeDecodeError('''The configuration file is not encoded in
                                    UTF-8, please change and retry''')

        # start logging

        if 'log_level' in self.config['logging']:
            loglevel = self.config['logging']['log_level'].upper()
        else:
            loglevel = 'INFO'

        numeric_level = getattr(logging, loglevel, None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        # setup the logging
        logfile = None
        if 'log_file' in self.config['logging']:
            logfile = self.config['logging']['log_file']

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

        self.path00 = self.config['paths']['path00']
        self.pathws = self.config['paths']['pathws']
        self.pathtp = self.config['paths']['pathtp']
        self.tmpdir = self.config['paths']['tmpdir']
        self.anyini = self.config['paths']['smrfini']

        self.st = pd.to_datetime(self.config['times']['stime'])
        self.et = pd.to_datetime(self.config['times']['etime'])
        self.tmz = self.config['times']['time_zone']

        self.u  = int(self.config['grid']['u'])
        self.v  = int(self.config['grid']['v'])
        self.du  = int(self.config['grid']['du'])
        self.dv  = int(self.config['grid']['dv'])
        self.units = self.config['grid']['units']
        self.csys = self.config['grid']['csys']
        self.nx = int(self.config['grid']['nx'])
        self.ny = int(self.config['grid']['ny'])

        if 'ppt_desc_file' in self.config['files']:
            self.ppt_desc_file = self.config['files']['ppt_desc_file']
        else:
            self.ppt_desc_file = '%sdata/data/ppt_desc%s.txt'%(self.path00,self.et.strftime("%Y%m%d"))

        self.anyini = self.config['paths']['smrfini']
        self.forecast_flag = 0
        if 'fetime' in self.config['times']:
            self.forecast_flag = 1
            self.ft = pd.to_datetime(self.config['times']['fetime'])
        if 'prev_mod_file' in self.config['files']:
            self.prev_mod_file = self.config['files']['prev_mod_file']

        if 'threads' in self.config['system']:
            self.ithreads = self.config['system']['threads']
        else:
            self.ithreads = 4

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

        if not os.path.exists(self.path00):  # if the working path specified in the config file does not exist
            y_n = 'a'                        # set a funny value to y_n
            while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
                y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%self.path00)
            if y_n == 'n':
                print('Please fix the base directory (path00) in your config file.')
            elif y_n =='y':
                os.makedirs('%sdata/data/smrfOutputs/'%self.path00)
                os.makedirs('%sdata/data/input/'%self.path00)
                os.makedirs('%sdata/data/ppt_4b/'%self.path00)
                os.makedirs('%sdata/forecast/'%self.path00)
                os.makedirs('%sruns/'%self.path00)

        self.paths = '%sdata/data/smrfOutputs/'%self.path00

    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        """
        Provide some logging info about when AWSF was closed
        """

        self._logger.info('AWSF closed --> %s' % datetime.now())
