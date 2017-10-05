# -*- coding: utf-8 -*-

"""Main module."""

import awsf
from datetime import datetime
import sys
#import faulthandler

#faulthandler.enable()

start = datetime.now()

# read config file
# create a new model instance
# initialize the model
# run the model

configFile = '../test_data/AWSF_test_config_tuol.ini'
if len(sys.argv) > 1:
    configFile = sys.argv[1]


#===============================================================================
# Initialize and run basin
#===============================================================================
#

# 1. initialize
# try:
with awsf.framework.framework.AWSF(configFile) as s:
    # 2. make directory structure (always run this to assign paths)
    s.mk_directories()

    # 3. distribute data by running smrf
    tmp_in = raw_input('Do you want to run smrf? (y/n):  ')
    if tmp_in.lower() == 'y':
        s.runSmrf()

    # 4. convert smrf output to ipw for iSnobal
    tmp_in = raw_input('Convert smrf output to ipw? (y/n):  ')
    if tmp_in.lower() == 'y':
        s.nc2ipw('smrf')

    # 5. run iSnobal
    tmp_in = raw_input('Run iSnobal? (y/n):  ')
    if tmp_in.lower() == 'y':
        s.run_isnobal()

    # 6. restart iSnobal from crash
    if 'isnobal restart' in s.config:
        if 'restart_crash' in s.config['isnobal restart']:
            if s.config['isnobal restart']['restart_crash'] == True:
                tmp_in = raw_input('Restart from crash? (y/n):  ')
                if tmp_in.lower() == 'y':
                    s.restart_crash_image()

    # 7. convert ipw back to netcdf for processing
    tmp_in = raw_input('Convert iSnobal forecast ouput to netcdf? (y/n):  ')
    if tmp_in.lower() == 'y':
        s.ipw2nc('smrf')

    # 8. repeat with gridded wrf data
    if 'forecast' in s.config:
        if s.config['forecast']['forecast_flag']:
            tmp_in = raw_input('Do you want to run smrf forecast with wrf data? (y/n):  ')
            if tmp_in.lower() == 'y':
                s.runSmrf_wrff()
            tmp_in = raw_input('Convert smrf forecast output top ipw? (y/n) ')
            if tmp_in.lower() == 'y':
                s.nc2ipw('wrf')
            tmp_in = raw_input('Run iSnobal forecast? (y/n):  ')
            if tmp_in.lower() == 'y':
                s.run_isnobal_forecast()
            # tmp_in = raw_input('Convert iSnobal forecast ouput to netcdf? (y/n): ')
            # if tmp_in.lower() == 'y':
            #     s.ipw2nc('wrf')
