import os
from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case_lakes import AWSMTestCaseLakes


class TestLakesLidarUpdate(AWSMTestCaseLakes):
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

    def test_thickness(self):
        self.compare_netcdf_files('ipysnobal.nc', 'thickness')

    def test_snow_density(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snow_density')

    def test_specific_mass(self):
        self.compare_netcdf_files('ipysnobal.nc', 'specific_mass')

    def test_liquid_water(self):
        self.compare_netcdf_files('ipysnobal.nc', 'liquid_water')

    def test_temp_surf(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temp_surf')

    def test_temp_lower(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temp_lower')

    def test_temp_snowcover(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temp_snowcover')

    def test_thickness_lower(self):
        self.compare_netcdf_files('ipysnobal.nc', 'thickness_lower')

    def test_water_saturation(self):
        self.compare_netcdf_files('ipysnobal.nc', 'water_saturation')

    def test_net_rad(self):
        self.compare_netcdf_files('ipysnobal.nc', 'net_rad')

    def test_sensible_heat(self):
        self.compare_netcdf_files('ipysnobal.nc', 'sensible_heat')

    def test_latent_heat(self):
        self.compare_netcdf_files('ipysnobal.nc', 'latent_heat')

    def test_snow_soil(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snow_soil')

    def test_precip_advected(self):
        self.compare_netcdf_files('ipysnobal.nc', 'precip_advected')

    def test_sum_EB(self):
        self.compare_netcdf_files('ipysnobal.nc', 'sum_EB')

    def test_evaporation(self):
        self.compare_netcdf_files('ipysnobal.nc', 'evaporation')

    def test_snowmelt(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snowmelt')

    def test_SWI(self):
        self.compare_netcdf_files('ipysnobal.nc', 'SWI')

    def test_cold_content(self):
        self.compare_netcdf_files('ipysnobal.nc', 'cold_content')

    def test_model_change_depth(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'depth_change')

    def test_model_change_density(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'rho_change')

    def test_model_change_swe(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'swe_change')


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
