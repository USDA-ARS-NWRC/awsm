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
with awsf.framework.framework.AWSF(configFile) as a:
    # 2. make directory structure if not made
    s.mk_directories()

    # 2. distribute data by running smrf
    if a.do_smrf:
        a.runSmrf()

    # 3. convert smrf output to ipw for iSnobal
    if a.do_isnobal:
        a.nc2ipw()

        # 4. run iSnobal
        if not a.config['isnobal restart']['restart_crash']:
            a.run_isnobal()
        else:
            # 5. restart iSnobal from crash
            a.restart_crash_image()

        # 6. convert ipw back to netcdf for processing
        a.ipw2nc()

    if a.do_smrf_ipysnobal:
        a.run_smrf_ipysnobal()

    a._logger.info(datetime.now() - start)
