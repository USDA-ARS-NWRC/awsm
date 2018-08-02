from copy import deepcopy
from inicheck.tools import cast_all_variables
from inicheck.utilities import pcfg
import unittest

from awsm.framework.framework import run_awsm

from .test_configurations import AWSMTestCase


class TestModel(AWSMTestCase):

    def test_isnobal(self):
        """ Test standard iSnobal """

        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['run_isnobal'] = True
        config.raw_cfg['awsm master']['make_nc'] = True
        config.raw_cfg['awsm master']['run_ipysnobal'] = False
        #config.raw_cfg['awsm master']['mask_isnobal'] = True

        config.apply_recipes()

        config = cast_all_variables(config, config.mcfg)


        # ensure that the recipes are used
        self.assertTrue(config.raw_cfg['awsm master']['run_isnobal'] == True)

        result = run_awsm(config)
        self.assertTrue(result)

    def test_isnobal_restart(self):
        """ Test standard iSnobal with crash restart """

        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['run_isnobal'] = True
        config.raw_cfg['awsm master']['make_nc'] = False
        config.raw_cfg['awsm master']['run_ipysnobal'] = False

        config.apply_recipes()

        config = cast_all_variables(config, config.mcfg)

        result = run_awsm(config)

        # run again with restart
        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['run_isnobal'] = True
        config.raw_cfg['awsm master']['make_nc'] = False
        config.raw_cfg['awsm master']['run_ipysnobal'] = False
        config.raw_cfg['isnobal restart']['restart_crash'] = True
        config.raw_cfg['isnobal restart']['wyh_restart_output'] = 1464

        config.apply_recipes()

        config = cast_all_variables(config, config.mcfg)

        self.assertTrue(result)

    def test_pysnobal(self):
        """ Test standard Pysnobal """

        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['run_ipysnobal'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)


        # ensure that the recipes are used
        self.assertTrue(config.raw_cfg['awsm master']['run_ipysnobal'] == True)

        result = run_awsm(config)
        self.assertTrue(result)

    def test_pysnobal_netcdf(self):
        """ Test PySnobal with netCDF Forcing """

        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['run_ipysnobal'] = True
        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['ipysnobal']['forcing_data_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        result = run_awsm(config)
        self.assertTrue(result)

    def test_smrf_pysnobal_single(self):
        """ Test smrf passing variables to PySnobal """

        config = deepcopy(self.base_config)
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['awsm master']['run_smrf_ipysnobal'] = True
        config.raw_cfg['awsm master']['run_ipysnobal'] = False
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertTrue(config.raw_cfg['awsm master']['run_smrf_ipysnobal'])
        self.assertTrue(config.raw_cfg['awsm master']['run_ipysnobal'] == False)

        result = run_awsm(config)
        self.assertTrue(result)

    def test_smrf_pysnobal_thread(self):
        """  Test smrf passing variables to PySnobal threaded """

        config = deepcopy(self.base_config)
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['awsm master']['run_smrf_ipysnobal'] = True
        config.raw_cfg['awsm master']['run_ipysnobal'] = False
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        result = run_awsm(config)
        self.assertTrue(result)
