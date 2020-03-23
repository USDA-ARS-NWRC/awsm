#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_awsm
----------------------------------

Tests for an entire awsm run. The AWSM integration run!
"""

import os
import shutil
import unittest

import numpy.testing as npt
from netCDF4 import Dataset

from tests.awsm_test_case import AWSMTestCase
from awsm.framework.framework import run_awsm


def compare_image(variable, test_image, gold_image):
    """
    Compares variables between the two netCDF images and determines
    if they are the same.

    Args:
        variable: Compared variable name
        test_image: Absolute path to tested image
        gold_image: Absolute path to gold image
    """

    d1 = Dataset(gold_image, 'r')
    gold_data = d1.variables[variable][:]
    d1.close()

    d2 = Dataset(test_image, 'r')
    test_data = d2.variables[variable][:]
    d2.close()

    npt.assert_array_equal(
        test_data,
        gold_data,
        err_msg=f"Variable ${variable} did not match with gold image"
    )


class TestStandardRME(AWSMTestCase):
    """
    Integration test for AWSM using reynolds mountain east
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        run_dir = os.path.abspath(os.path.join(cls.test_dir, 'RME'))

        cls.gold_path = os.path.join(run_dir, 'gold')
        cls.gold_em = os.path.join(cls.gold_path, 'em.nc')
        cls.gold_snow = os.path.join(cls.gold_path, 'snow.nc')

        cls.output = os.path.join(
            run_dir,
            'output/rme/devel/wy1986/rme_test/runs/run3337_3344'
        )
        cls.output_em = os.path.join(cls.output, 'em.nc')
        cls.output_snow = os.path.join(cls.output, 'snow.nc')

        # Remove any potential files to ensure fresh run
        if os.path.isdir(cls.output):
            shutil.rmtree(cls.output)

        config = os.path.join(run_dir, 'config.ini')

        cls.cache_run = True
        run_awsm(config)

    def test_thickness(self):
        """
        Check the simulated thickness is the same as the gold file
        """
        compare_image("thickness", self.output_snow, self.gold_snow)

    def test_snow_density(self):
        """
        Check the simulated snow density is the same as the gold file
        """
        compare_image("snow_density", self.output_snow, self.gold_snow)

    def test_specific_mass(self):
        """
        Check the simulated specific mass is the same as the gold file
        """
        compare_image("specific_mass", self.output_snow, self.gold_snow)

    def test_liquid_water(self):
        """
        Check the simulated liquid water is the same as the gold file
        """
        compare_image("liquid_water", self.output_snow, self.gold_snow)

    def test_temp_surf(self):
        """
        Check the simulated temp surf is the same as the gold file
        """
        compare_image("temp_surf", self.output_snow, self.gold_snow)

    def test_temp_lower(self):
        """
        Check the simulated temp lower is the same as the gold file
        """
        compare_image("temp_lower", self.output_snow, self.gold_snow)

    def test_temp_snowcover(self):
        """
        Check the simulated temp snowcover is the same as the gold file
        """
        compare_image("temp_snowcover", self.output_snow, self.gold_snow)

    def test_thickness_lower(self):
        """
        Check the simulated thickness lower is the same as the gold file
        """
        compare_image("thickness_lower", self.output_snow, self.gold_snow)

    def test_water_saturation(self):
        """
        Check the simulated water saturation is the same as the gold file
        """
        compare_image("water_saturation", self.output_snow, self.gold_snow)

    def test_net_rad(self):
        """
        Check the simulated net rad is the same as the gold file
        """
        compare_image("net_rad", self.output_em, self.gold_em)

    def test_sensible_heat(self):
        """
        Check the simulated sensible heat is the same as the gold file
        """
        compare_image("sensible_heat", self.output_em, self.gold_em)

    def test_latent_heat(self):
        """
        Check the simulated latent heat is the same as the gold file
        """
        compare_image("latent_heat", self.output_em, self.gold_em)

    def test_snow_soil(self):
        """
        Check the simulated snow soil is the same as the gold file
        """
        compare_image("snow_soil", self.output_em, self.gold_em)

    def test_precip_advected(self):
        """
        Check the simulated precip advected is the same as the gold file
        """
        compare_image("precip_advected", self.output_em, self.gold_em)

    def test_sum_EB(self):
        """
        Check the simulated sum EB is the same as the gold file
        """
        compare_image("sum_EB", self.output_em, self.gold_em)

    def test_evaporation(self):
        """
        Check the simulated evaporation is the same as the gold file
        """
        compare_image("evaporation", self.output_em, self.gold_em)

    def test_snowmelt(self):
        """
        Check the simulated snowmelt is the same as the gold file
        """
        compare_image("snowmelt", self.output_em, self.gold_em)

    def test_SWI(self):
        """
        Check the simulated SWI is the same as the gold file
        """
        compare_image("SWI", self.output_em, self.gold_em)

    def test_cold_content(self):
        """
        Check the simulated cold content is the same as the gold file
        """
        compare_image("cold_content", self.output_em, self.gold_em)


if __name__ == '__main__':
    unittest.main()
