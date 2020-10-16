from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case_lakes import AWSMTestCaseLakes
from awsm.tests.check_mixin import CheckPysnobalOutputs


class TestRestart(CheckPysnobalOutputs, AWSMTestCaseLakes):
    """
    Testing using Lakes:
        - ipysnobal
        - initialize from snow.nc file
        - SMRF from netcdf
        - restart simulation
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        # reoutput the last timestep
        config.raw_cfg['ipysnobal']['restart_date_time'] = '2019-10-01 17:00'  # noqa
        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')
        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )
        run_awsm(cls.run_config)

        # restart the run from a different point
        cls.restart_configure()
        run_awsm(cls.run_config)


class TestSMRFiPysnobalRestart(TestRestart):
    """
    Testing using RME:
        - smrf_ipysnobal
        - initialize from snow.nc file
        - load HRRR first
        - restart simulation
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['output']['variables'] = ['storm_days']
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        # reoutput the last timestep
        config.raw_cfg['ipysnobal']['restart_date_time'] = '2019-10-01 17:00'  # noqa

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
        config.raw_cfg['output']['variables'] = ['storm_days']
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def restart_configure(cls):
        config = cls.run_config_copy()
        # reoutput the last timestep
        config.raw_cfg['ipysnobal']['restart_date_time'] = '2019-10-01 17:00'  # noqa

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestSMRFiPysnobalRestartFailure(AWSMTestCaseLakes):
    """
    Testing using RME:
        - smrf_ipysnobal
        - restart simulation
        - don't provide a storm days file
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['output']['variables'] = []
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['awsm system']['netcdf_output_precision'] = 'double'
        config.raw_cfg['ipysnobal']['restart_date_time'] = '2019-10-01 17:00'  # noqa

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')
        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

    def test_failure(self):
        self.assertRaises(FileNotFoundError, run_awsm, self.run_config)
