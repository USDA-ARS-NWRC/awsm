import os
import unittest

from inicheck.tools import get_user_config

from awsm.framework.framework import run_awsm
from .awsm_test_case import AWSMTestCase


class TestConfigurations(AWSMTestCase):
    """
    Runs the short simulation over reynolds mountain east
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config_file = os.path.join(cls.test_dir, 'test_base_config.ini')

        # Base configuration
        cls.base_config = get_user_config(
            cls.config_file, modules=['smrf', 'awsm']
        )

        cls.run_dir = os.path.join(cls.test_dir, 'RME')

    def test_base_config_file(self):
        self.assertIsNone(run_awsm(self.config_file))

    def test_custom_config_file(self):
        self.assertIsNone(run_awsm(self.base_config))


if __name__ == '__main__':
    unittest.main()
