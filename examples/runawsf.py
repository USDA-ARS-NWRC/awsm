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

configFile = '../test_data/AWSF_test_config.ini'
if len(sys.argv) > 1:
    configFile = sys.argv[1]


#===============================================================================
# Initialize and run basin
#===============================================================================
#

# 1. initialize
# try:
with awsf.framework.framework.AWSF(configFile) as s:
    # 2. make directory structure if not made
    s.mk_directories()

    # 2. distribute data by running smrf
    tmp_in = raw_input('Do you want to run smrf? (y/n):')
    if tmp_in.lower() == 'y':
        s.runSmrf()

    # 3. convert smrf output to ipw for iSnobal
    tmp_in = raw_input('Convert to ipw? (y/n):')
    if tmp_in.lower() == 'y':
        s.nc2ipw()

    # 4. run iSnobal
    tmp_in = raw_input('Run iSnobal? (y/n):')
    if tmp_in.lower() == 'y':
        s.run_isnobal()

    # 5. convert ipw back to netcdf for processing
    # s.ipw2nc()
