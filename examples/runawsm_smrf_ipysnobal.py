# -*- coding: utf-8 -*-

"""Main module."""

import awsm
from datetime import datetime
import sys
#import faulthandler

#faulthandler.enable()

start = datetime.now()

# read config file
# create a new model instance
# initialize the model
# run the model

configFile = '../test_data/AWSM_test_config_ipysnobal.ini'
if len(sys.argv) > 1:
    configFile = sys.argv[1]


#===============================================================================
# Initialize and run basin
#===============================================================================
#

# 1. initialize
# try:
with awsm.framework.framework.AWSM(configFile) as a:

    # 2. do everything else
    a.run_smrf_ipysnobal()

    a._logger.info(datetime.now() - start)
