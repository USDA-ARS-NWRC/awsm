import os
from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case import AWSMTestCase


class TestStandardRME(AWSMTestCase):
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

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/rme/wy1986/rme_test/run19860217_19860217'
        )

        run_awsm(cls.config_file)

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


class TestRMESMRFiPysnobal(TestStandardRME):
    """
    Testing using RME:
        - smrf_ipysnobal
        - initialize with all zeros
        - loading from netcdf
    """

    @classmethod
    def setUpClass(cls):
        cls.load_base_config()
        cls.create_output_dir()

        cls.gold_dir = cls.basin_dir.joinpath('gold')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/rme/wy1986/rme_test/run19860217_19860217'
        )

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config, testing=True)


class TestRMESMRFiPysnobalThread(TestStandardRME):
    """
    Testing using RME:
        - smrf_ipysnobal
        - SMRF threading
        - initialize with all zeros
        - loading from netcdf
    """

    @classmethod
    def setUpClass(cls):
        cls.load_base_config()
        cls.create_output_dir()

        cls.gold_dir = cls.basin_dir.joinpath('gold')

        cls.gold_em = os.path.join(cls.gold_dir, 'ipysnobal.nc')
        cls.gold_snow = os.path.join(cls.gold_dir, 'ipysnobal.nc')

        cls.output_path = cls.basin_dir.joinpath(
            'output/rme/wy1986/rme_test/run19860217_19860217'
        )

        config = cls.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config, testing=True)
