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

configFile = '../tests/AWSF_test_config.ini'
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
    # s.runSmrf()

    # 3. convert smrf output to ipw for iSnobal
    #s.nc2ipw()

    # 4. run iSnobal
    # s.run_isnobal()

    # 5. convert ipw back to netcdf for processing
    # s.ipw2nc()
