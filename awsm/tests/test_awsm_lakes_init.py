from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case_lakes import AWSMTestCaseLakes
from awsm.tests.check_mixin import CheckPysnobalOutputs


class TestLakesInit(CheckPysnobalOutputs, AWSMTestCaseLakes):
    """
    Testing using Lakes:
        - ipysnobal
        - initialize from init.nc file
        - loading from netcdf
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()

        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

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


class TestLakesInitSMRFiPysnobal(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - loading from netcdf
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestLakesInitSMRFiPysnobalThreaded(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - threaded SMRF/iPysnobal
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestLakesInitSMRFiPysnobalThreadedHRRR(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - threaded SMRF/iPysnobal
        - loading HRRR in timestep mode
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()
        config.raw_cfg['gridded']['hrrr_load_method'] = 'timestep'
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)
