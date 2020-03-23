import unittest

from awsm.framework.framework import run_awsm
from .awsm_test_case import AWSMTestCase


class TestConfigurations(AWSMTestCase):
    """
    Runs the short simulation over reynolds mountain east
    """
    def test_base_config_file(self):
        self.assertIsNone(run_awsm(self.config_file))

    def test_custom_config_file(self):
        self.assertIsNone(run_awsm(self.base_config))


if __name__ == '__main__':
    unittest.main()
