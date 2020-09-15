
import os

from tests.awsm_test_case import AWSMTestCase


class AWSMTestCaseLakes(AWSMTestCase):
    """
    Runs the short simulation over Lakes.
    """

    basin_dir = AWSMTestCase.test_dir.joinpath('basins', 'Lakes')
    config_file = os.path.join(basin_dir, AWSMTestCase.BASE_INI_FILE_NAME)
    gold_dir = basin_dir.joinpath('gold_hrrr')
