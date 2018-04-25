'''
Created on Mar 28, 2017
test script for smrfing module
@author: pkormos
'''
from PBR_tools import smrfing as sm

sm.smrf_go_meas('2017-2-14 0:00','2017-2-15-6:00')
sm.smrf_go_wrf('2017-2-15-6:00')
sm.smrf_merge('2017-2-15-6:00')