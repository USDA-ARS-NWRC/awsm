import os
from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case_lakes import AWSMTestCaseLakes


class TestLakesInit(AWSMTestCaseLakes):
    """
    Testing using Lakes:
        - ipysnobal
        - initialize from init.nc file
        - loading from netcdf
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

        config = cls.base_config_copy()

        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config)

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


class TestLakesInitSMRFiPysnobal(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - loading from netcdf
    """

    @classmethod
    def setUpClass(cls):
        cls.load_base_config()
        cls.create_output_dir()

        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config, testing=True)


class TestLakesInitSMRFiPysnobalThreaded(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - threaded SMRF/iPysnobal
    """

    @classmethod
    def setUpClass(cls):
        cls.load_base_config()
        cls.create_output_dir()

        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config, testing=True)


class TestLakesInitSMRFiPysnobalThreadedHRRR(TestLakesInit):
    """
    Testing using Lakes:
        - smrf_ipysnobal
        - initialize from init.nc file
        - threaded SMRF/iPysnobal
        - loading HRRR in timestep mode
    """

    @classmethod
    def setUpClass(cls):
        cls.load_base_config()
        cls.create_output_dir()

        cls.gold_dir = cls.basin_dir.joinpath('gold_hrrr')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/lakes/wy2020/lakes_gold/run20191001_20191001'
        )

        config = cls.base_config_copy()
        config.raw_cfg['gridded']['hrrr_load_method'] = 'timestep'
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True
        config.raw_cfg['ipysnobal']['init_file'] = './topo/init.nc'
        config.raw_cfg['ipysnobal']['init_type'] = 'netcdf'

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config, testing=True)
