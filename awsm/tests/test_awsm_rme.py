from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case import AWSMTestCase
from awsm.tests.check_mixin import CheckPysnobalOutputs


class TestStandardRME(CheckPysnobalOutputs, AWSMTestCase):
    """
    Testing using RME:
        - ipysnobal
        - initialize with all zeros
        - loading from netcdf
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gold_dir = cls.basin_dir.joinpath('gold')
        cls.output_path = cls.basin_dir.joinpath(
            'output/rme/wy1986/rme_test/run19860217_19860217'
        )

        run_awsm(cls.run_config)


class TestRMESMRFiPysnobal(TestStandardRME):
    """
    Testing using RME:
        - smrf_ipysnobal
        - initialize with all zeros
        - loading from netcdf
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestRMESMRFiPysnobalThread(TestStandardRME):
    """
    Testing using RME:
        - smrf_ipysnobal
        - SMRF threading
        - initialize with all zeros
        - loading from netcdf
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)
