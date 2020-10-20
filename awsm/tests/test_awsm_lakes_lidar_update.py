import os
from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case_lakes import AWSMTestCaseLakes
from awsm.tests.check_mixin import CheckPysnobalOutputs, CheckModelChange


class TestLakesLidarUpdate(CheckPysnobalOutputs,
                           CheckModelChange,
                           AWSMTestCaseLakes):
    """
    Testing using Lakes:
        - ipysnobal
        - initialize from snow.nc
        - loading from netcdf
        - lidar updates
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()

        adj_config = {
            'update depth': {
                'update': True,
                'update_file': './topo/lidar_depths.nc',
                'buffer': 400,
                'flight_numbers': 1,
                'update_change_file': 'output/lakes/wy2020/lakes_gold/run20191001_20191001/model_lidar_change.nc'  # noqa
            }
        }
        config.raw_cfg.update(adj_config)

        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr_update')

        cls.gold_em = os.path.join(cls.gold_dir, 'em.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'snow.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

        run_awsm(cls.run_config)


class TestLakesLidarUpdateSMRFiPysnobal(TestLakesLidarUpdate):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from snow.nc
        - lidar updates
    """

    @classmethod
    def configure(cls):
        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        adj_config = {
            'update depth': {
                'update': True,
                'update_file': './topo/lidar_depths.nc',
                'buffer': 400,
                'flight_numbers': 1,
                'update_change_file': 'output/lakes/wy2020/lakes_gold/run20191001_20191001/model_lidar_change.nc'  # noqa
            },
        }
        config.raw_cfg.update(adj_config)
        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestLakesLidarUpdateSMRFiPysnobalThreaded(TestLakesLidarUpdate):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - threaded SMRF/iPysnobal
        - initialize from snow.nc
        - lidar updates
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        adj_config = {
                'update depth': {
                    'update': True,
                    'update_file': './topo/lidar_depths.nc',
                    'buffer': 400,
                    'flight_numbers': 1,
                    'update_change_file': 'output/lakes/wy2020/lakes_gold/run20191001_20191001/model_lidar_change.nc'  # noqa
                },
            }
        config.raw_cfg.update(adj_config)
        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)


class TestLakesLidarUpdateSMRFiPysnobalThreadedHRRR(TestLakesLidarUpdate):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - threaded SMRF/iPysnobal
        - initialize from snow.nc
        - lidar updates
        - loading HRRR in timestep mode
    """

    @classmethod
    def configure(cls):

        config = cls.base_config_copy()
        config.raw_cfg['gridded']['hrrr_load_method'] = 'timestep'
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        adj_config = {
            'update depth': {
                'update': True,
                'update_file': './topo/lidar_depths.nc',
                'buffer': 400,
                'flight_numbers': 1,
                'update_change_file': 'output/lakes/wy2020/lakes_gold/run20191001_20191001/model_lidar_change.nc'  # noqa
            },
        }
        config.raw_cfg.update(adj_config)
        config.apply_recipes()
        cls.run_config = cast_all_variables(config, config.mcfg)
