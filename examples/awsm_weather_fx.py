#!/usr/bin/env python
# -*- coding: utf-8 -*-

import awsm
from datetime import datetime
import sys
import os
import copy

start = datetime.now()

configFile = '/home/micahsandusky/Tuolumne/devel/awsfTesting/AWSF_tuol_weather.ini'

#===============================================================================
# Initialize and run basin
#===============================================================================
#

scen_start = 8
scen_end = 9
scen_run = range(scen_start, scen_end)
#tp = 'regular'
#tps = ['regular', 'warmwet', 'warmdry', 'coldwet', 'colddry']
# tps = ['warmwet', 'warmdry', 'coldwet', 'colddry']
tps = ['regular_hourly2']
# 1. initialize
# try:
with awsm.framework.framework.AWSM(configFile) as a:

    for tp in tps:
        for sn in scen_run:
            start_temp = datetime.now()
            # replace directory names
            a.proj = '{}_scenario{}'.format(tp, sn)
            a.desc = 'AWSM run for {} scenario {}'.format(tp, sn)

            # replace station data paths
            #csv_p = '/data/blizzard/awsftest/weatherGenerator/scenario_{}/'.format(sn)
            #csv_p = '/data/blizzard/awsftest/weatherGenerator_warmwet/scenario_{}/'.format(sn)
            csv_p = '/data/blizzard/awsftest/febWeather/{}/scenario_{}/'.format(tp, sn)

            a.config['csv']['metadata'] = os.path.join(csv_p, 'metadata.csv')
            a.config['csv']['air_temp'] = os.path.join(csv_p, 'air_temp.csv')
            a.config['csv']['vapor_pressure'] = os.path.join(csv_p, 'vapor_pressure.csv')
            a.config['csv']['precip'] = os.path.join(csv_p, 'precip_intensity.csv')
            a.config['csv']['solar'] = os.path.join(csv_p, 'solar_radiation.csv')
            a.config['csv']['wind_speed'] = os.path.join(csv_p, 'wind_speed.csv')
            a.config['csv']['wind_direction'] = os.path.join(csv_p, 'wind_direction.csv')
            a.config['csv']['cloud_factor'] = os.path.join(csv_p, 'cloud_factor.csv')

            # make directories
            a.mk_directories()

            # Run iPySnobal from SMRF in memory
            if a.do_smrf_ipysnobal:
                a.run_smrf_ipysnobal()

            a._logger.info('Scenario {} ran in {}'.format( sn, datetime.now() - start_temp ) )

        a._logger.info(datetime.now() - start)
