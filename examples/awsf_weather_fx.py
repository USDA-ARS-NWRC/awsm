#!/usr/bin/env python
# -*- coding: utf-8 -*-

import awsf
from datetime import datetime
import sys
import os

start = datetime.now()

configFile = '../test_data/AWSF_tuol_weather.ini'

#===============================================================================
# Initialize and run basin
#===============================================================================
#

scen_start = 0
scen_end = 2
scen_run = range(scen_start, scen_end)
# 1. initialize
# try:
with awsf.framework.framework.AWSF(configFile) as a:

    for sn in scen_run:
        start_temp = datetime.now()
        # replace directory names
        a.proj = 'scenario{}'.format(sn)
        a.desc = 'AWSF run for scenario {}'.format(sn)

        # replace station data paths
        csv_p = '/home/micahsandusky/Documents/Code/awsfTesting/weatherGenerator/scenario_{}/'.format(sn)
        #a.config['csv']['metadata'] = os.path.join(csv_p, 'metadata.csv')
        a.config['csv']['air_temp'] = os.path.join(csv_p, 'air_temp.csv')
        a.config['csv']['vapor_pressure'] = os.path.join(csv_p, 'vapor_pressure.csv')
        a.config['csv']['precip'] = os.path.join(csv_p, 'precip_accum.csv')
        a.config['csv']['solar'] = os.path.join(csv_p, 'solar_radiation.csv')
        a.config['csv']['wind_speed'] = os.path.join(csv_p, 'wind_speed.csv')
        a.config['csv']['wind_direction'] = os.path.join(csv_p, 'wind_direction.csv')
        a.config['csv']['cloud_factor'] = os.path.join(csv_p, 'cloud_factor.csv')

        # make directories
        a.mk_directories()

        if not a.config['isnobal restart']['restart_crash']:
        # distribute data by running smrf
          if a.do_smrf:
              a.runSmrf()

          # convert smrf output to ipw for iSnobal
          if a.do_isnobal:
              if a.do_make_in:
                  a.nc2ipw('smrf')
              # run iSnobal
              a.run_isnobal()

              # convert ipw back to netcdf for processing
          if a.do_make_nc:
              a.ipw2nc('smrf')
        # if restart
        else:
          if a.do_isnobal:
              # restart iSnobal from crash
              a.restart_crash_image()
              # convert ipw back to netcdf for processing
              if a.do_make_nc:
                  a.ipw2nc('smrf')

        # Run iPySnobal from SMRF in memory
        if a.do_smrf_ipysnobal:
          a.run_smrf_ipysnobal()

        a._logger.info('Scenario {} ran in {}'.format( sn, datetime.now() - start_temp ) )

    a._logger.info(datetime.now() - start)
