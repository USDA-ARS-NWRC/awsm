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

    return  not np.any(result>0)


class TestStandardRME(unittest.TestCase):
    """
    Integration test for AWSM using reynolds mountain east
    """

    def setUp(self):
        """
        Runs the short simulation over reynolds mountain east
        """
        run_dir = os.path.abspath(os.path.join(os.path.dirname(awsm.__file__),
                                                '..', 'tests', 'RME'))

        # Gold paths
        self.gold = os.path.abspath(os.path.join(os.path.dirname(awsm.__file__),
                                                '..', 'tests', 'RME', 'gold'))
        self.gold_em = os.path.join(self.gold, 'normal_em.nc')
        self.gold_snow = os.path.join(self.gold, 'normal_snow.nc')

        # Output
        self.output = os.path.join(run_dir, 'output/rme/devel/wy1986/rme_test/runs/run3337_3344')
        self.output_em = os.path.join(self.output, 'em.nc')
        self.output_snow = os.path.join(self.output, 'snow.nc')

        # Remove any potential files to ensure fresh run
        if os.path.isdir(self.output):
            os.remove(self.output_snow)
            os.remove(self.output_em)

        config = os.path.join(run_dir, 'config.ini')

        # Run simulation
        with AWSM(config) as a:
            a.runSmrf()
            a.nc2ipw('smrf')
            a.run_isnobal()
            a.ipw2nc('smrf')

    def test_snow_thickness(self):
        """
        Compare that the simulated snow depth is the same as the gold file
        provided.
        """
        a = compare_image('thickness', self.gold_snow, self.output_snow)
        assert(a)

if __name__ == '__main__':
    unittest.main()
