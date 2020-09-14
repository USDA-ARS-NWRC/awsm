import unittest
from copy import deepcopy

from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from tests.test_configurations import TestConfigurations


class TestModel(TestConfigurations):

    def test_pysnobal(self):
        """ Test standard Pysnobal """

        config = deepcopy(self.base_config)

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        # ensure that the recipes are used
        self.assertTrue(config.cfg['awsm master']['model_type'] == 'ipysnobal')

        self.assertIsNone(run_awsm(config))

    def test_pysnobal_netcdf(self):
        """ Test PySnobal with netCDF Forcing """

        config = deepcopy(self.base_config)

        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['awsm master']['mask_isnobal'] = True
        config.raw_cfg['ipysnobal']['forcing_data_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertIsNone(run_awsm(config))

    def test_smrf_pysnobal_single(self):
        """ Test smrf passing variables to PySnobal """

        config = deepcopy(self.base_config)
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertTrue(
            config.cfg['awsm master']['model_type'] == 'smrf_ipysnobal'
        )

        self.assertIsNone(run_awsm(config))

    def test_smrf_pysnobal_thread(self):
        """  Test smrf passing variables to PySnobal threaded """

        config = deepcopy(self.base_config)
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['make_in'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertIsNone(run_awsm(config))


if __name__ == '__main__':
    unittest.main()
