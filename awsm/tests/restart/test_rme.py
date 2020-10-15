from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case import AWSMTestCase
from awsm.tests.check_mixin import CheckPysnobalOutputs


class TestRestart(CheckPysnobalOutputs, AWSMTestCase):
    """
    Testing using RME:
        - ipysnobal
        - initialize with all zeros
        - loading from netcdf
        - restart simulation
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['ipysnobal']['restart_date_time'] = '1986-02-17 05:00:00'  # noqa
        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gold_dir = cls.basin_dir.joinpath('gold')
        cls.output_path = cls.basin_dir.joinpath(
            'output/rme/wy1986/rme_test/run19860217_19860217'
        )
        run_awsm(cls.run_config)

        # restart the run from a different point
        cls.restart_configure()
        run_awsm(cls.run_config)


class TestSMRFiPysnobalRestart(TestRestart):
    """
    Testing using RME:
        - smrf_ipysnobal
        - initialize with all zeros
        - loading from netcdf
        - restart simulation
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        config.raw_cfg['ipysnobal']['restart_date_time'] = '1986-02-17 05:00:00'  # noqa

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestSMRFiPysnobalThreadRestart(TestRestart):
    """
    Testing using RME:
        - smrf_ipysnobal
        - SMRF threading
        - initialize with all zeros
        - loading from netcdf
        - restart simulation
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        config.raw_cfg['ipysnobal']['restart_date_time'] = '1986-02-17 05:00:00'  # noqa

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)
