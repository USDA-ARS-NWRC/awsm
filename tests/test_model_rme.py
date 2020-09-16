from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from tests.awsm_test_case import AWSMTestCase


class TestModel(AWSMTestCase):

    def test_pysnobal(self):
        """ Test standard Pysnobal """

        config = self.base_config_copy()

        # ensure that the recipes are used
        self.assertTrue(config.cfg['awsm master']['model_type'] == 'ipysnobal')

        self.assertIsNone(run_awsm(config))

    def test_pysnobal_netcdf(self):
        """ Test PySnobal with netCDF Forcing """

        config = self.base_config_copy()

        config.raw_cfg['awsm master']['mask_isnobal'] = True
        config.raw_cfg['ipysnobal']['forcing_data_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertIsNone(run_awsm(config))

    def test_smrf_pysnobal_single(self):
        """ Test smrf passing variables to PySnobal """

        config = self.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
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

        config = self.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        self.assertIsNone(run_awsm(config))
