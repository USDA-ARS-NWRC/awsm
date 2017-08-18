'''
Created on Apr 7, 2017
script to run (test) crack pour class
@author: pkormos
'''
import PBR_tools.crack as crack

# config_file = '/Users/pkormos/src/PBR_tools/config_PBR.txt'
config_file = '/Volumes/data/blizzard/SanJoaquin/pkormos_workspace/scripts2017/config_PBR2017.txt'
pbr = crack.pour(config_file)
pbr.run_isnobal()