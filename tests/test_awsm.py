#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_full_smrf
----------------------------------

Tests for an entire smrf run. The SMRF integration run!
"""

import unittest
import shutil
import os
import awsm
from awsm.framework.framework import AWSM
import numpy as np
from netCDF4 import Dataset


def compare_image(v_name,gold_image,test_image):
    """
    Compares two netcdfs images to and determines if they are the same.

    Args:
        v_name: Name with in the file contains
        gold_dir: Directory containing gold standard results
        test_dir: Directory containing test results to be compared
    Returns:
        Boolean: Whether the two images were the same
    """

    d1 = Dataset(gold_image)
    gold = d1.variables[v_name][:]

    d2 = Dataset(test_image)
    rough = d2.variables[v_name][:]
    result = np.abs(gold-rough)
    return  not np.any(result>0.0)


class TestStandardRME(unittest.TestCase):
    """
    Integration test for AWSM using reynolds mountain east
    """

    @classmethod
    def setUpClass(self):
        """
        Runs the short simulation over reynolds mountain east
        """
        run_dir = os.path.abspath(os.path.join(os.path.dirname(awsm.__file__),
                                                '..', 'tests', 'RME'))

        # Gold paths
        self.gold = os.path.abspath(os.path.join(os.path.dirname(awsm.__file__),
                                                '..', 'tests', 'RME', 'gold'))
        self.gold_em = os.path.join(self.gold, 'em.nc')
        self.gold_snow = os.path.join(self.gold, 'snow.nc')

        # Output
        self.output = os.path.join(run_dir,
                        'output/rme/devel/wy1986/rme_test/runs/run3337_3344')
        self.output_em = os.path.join(self.output, 'em.nc')
        self.output_snow = os.path.join(self.output, 'snow.nc')

        # Remove any potential files to ensure fresh run
        if os.path.isdir(self.output):
            for f in [self.output_snow,self.output_em]:
                if os.path.isfile(f):
                    os.remove(f)

        config = os.path.join(run_dir, 'config.ini')

        # Run simulation
        with AWSM(config) as a:
            a.runSmrf()
            a.nc2ipw('smrf')
            a.run_isnobal()
            a.ipw2nc('smrf')

    def test_thickness(self):
    	"""
    	Check the simulated thickness is the same as the gold file
    	"""
    	a = compare_image("thickness", self.output_snow,self.gold_snow)
    	assert(a)

    def test_snow_density(self):
    	"""
    	Check the simulated snow density is the same as the gold file
    	"""
    	a = compare_image("snow_density", self.output_snow,self.gold_snow)
    	assert(a)

    def test_specific_mass(self):
    	"""
    	Check the simulated specific mass is the same as the gold file
    	"""
    	a = compare_image("specific_mass", self.output_snow,self.gold_snow)
    	assert(a)

    def test_liquid_water(self):
    	"""
    	Check the simulated liquid water is the same as the gold file
    	"""
    	a = compare_image("liquid_water", self.output_snow,self.gold_snow)
    	assert(a)

    def test_temp_surf(self):
    	"""
    	Check the simulated temp surf is the same as the gold file
    	"""
    	a = compare_image("temp_surf", self.output_snow,self.gold_snow)
    	assert(a)

    def test_temp_lower(self):
    	"""
    	Check the simulated temp lower is the same as the gold file
    	"""
    	a = compare_image("temp_lower", self.output_snow,self.gold_snow)
    	assert(a)

    def test_temp_snowcover(self):
    	"""
    	Check the simulated temp snowcover is the same as the gold file
    	"""
    	a = compare_image("temp_snowcover", self.output_snow,self.gold_snow)
    	assert(a)

    def test_thickness_lower(self):
    	"""
    	Check the simulated thickness lower is the same as the gold file
    	"""
    	a = compare_image("thickness_lower", self.output_snow,self.gold_snow)
    	assert(a)

    def test_water_saturation(self):
    	"""
    	Check the simulated water saturation is the same as the gold file
    	"""
    	a = compare_image("water_saturation", self.output_snow,self.gold_snow)
    	assert(a)

    def test_net_rad(self):
    	"""
    	Check the simulated net rad is the same as the gold file
    	"""
    	a = compare_image("net_rad", self.output_em,self.gold_em)
    	assert(a)

    def test_sensible_heat(self):
    	"""
    	Check the simulated sensible heat is the same as the gold file
    	"""
    	a = compare_image("sensible_heat", self.output_em,self.gold_em)
    	assert(a)

    def test_latent_heat(self):
    	"""
    	Check the simulated latent heat is the same as the gold file
    	"""
    	a = compare_image("latent_heat", self.output_em,self.gold_em)
    	assert(a)

    def test_snow_soil(self):
    	"""
    	Check the simulated snow soil is the same as the gold file
    	"""
    	a = compare_image("snow_soil", self.output_em,self.gold_em)
    	assert(a)

    def test_precip_advected(self):
    	"""
    	Check the simulated precip advected is the same as the gold file
    	"""
    	a = compare_image("precip_advected", self.output_em,self.gold_em)
    	assert(a)

    def test_sum_EB(self):
    	"""
    	Check the simulated sum EB is the same as the gold file
    	"""
    	a = compare_image("sum_EB", self.output_em,self.gold_em)
    	assert(a)

    def test_evaporation(self):
    	"""
    	Check the simulated evaporation is the same as the gold file
    	"""
    	a = compare_image("evaporation", self.output_em,self.gold_em)
    	assert(a)

    def test_snowmelt(self):
    	"""
    	Check the simulated snowmelt is the same as the gold file
    	"""
    	a = compare_image("snowmelt", self.output_em,self.gold_em)
    	assert(a)

    def test_SWI(self):
    	"""
    	Check the simulated SWI is the same as the gold file
    	"""
    	a = compare_image("SWI", self.output_em,self.gold_em)
    	assert(a)

    def test_cold_content(self):
    	"""
    	Check the simulated cold content is the same as the gold file
    	"""
    	a = compare_image("cold_content", self.output_em,self.gold_em)
    	assert(a)


if __name__ == '__main__':
    unittest.main()
