from glob import glob

from inicheck.tools import cast_all_variables

from awsm.framework.framework import run_awsm
from awsm.tests.awsm_test_case import AWSMTestCase


class TestOutput(AWSMTestCase):
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

    def setUp(self):
        super().setUp()
        self.create_output_dir()

    def tearDown(self):
        super().tearDown()
        self.remove_output_dir()

    def assert_file_number(self, number):
        files = glob(str(self.output_path.joinpath('*.nc')))
        self.assertTrue(len(files) == number)

    def test_output_11_files(self):
        run_awsm(self.run_config)
        self.assert_file_number(11)

    def test_ouput_smrf_ipysnobal_11_files(self):
        config = self.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config)
        self.assert_file_number(11)

    def test_ouput_smrf_ipysnobal_2_files(self):
        config = self.base_config_copy()
        config.raw_cfg['output']['variables'] = 'air_temp'
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = False

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config)
        self.assert_file_number(2)

    def test_ouput_smrf_ipysnobal_threaded_11_files(self):
        config = self.base_config_copy()
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config)
        self.assert_file_number(11)

    def test_ouput_smrf_ipysnobal_threaded_3_files(self):
        config = self.base_config_copy()
        config.raw_cfg['output']['variables'] = ['air_temp', 'vapor_pressure']
        config.raw_cfg['awsm master']['run_smrf'] = False
        config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
        config.raw_cfg['system']['threading'] = True

        config.apply_recipes()
        config = cast_all_variables(config, config.mcfg)

        run_awsm(config)
        self.assert_file_number(3)
