import os
import shutil
import unittest

from inicheck.tools import get_user_config

import awsm
from awsm.framework.framework import run_awsm


class AWSMTestCase(unittest.TestCase):
    """
    Runs the short simulation over reynolds mountain east

    The base test case for SMRF that will load in the configuration file and
    store as the base config. Also will remove the output directory upon
    tear down.
    """

    @classmethod
    def setUp(cls):
        cls.test_dir = os.path.abspath(os.path.join(
            os.path.dirname(awsm.__file__), '..', 'tests'
        ))
        cls.config_file = os.path.join(cls.test_dir, 'test_base_config.ini')

        # Base configuration
        cls.base_config = get_user_config(
            cls.config_file, modules=['smrf','awsm']
        )

    def tearDown(self):
        """
        Clean up the output directory
        """

        folder = os.path.join(self.test_dir, 'RME', 'output')
        nodelete = os.path.join(folder, '.keep')
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            if file_path != nodelete:
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path): shutil.rmtree(file_path)
                except Exception as e:
                    print(e)


class TestConfigurations(AWSMTestCase):
    def test_base_config_file(self):
        self.assertIsNone(run_awsm(self.config_file))

    def test_custom_config_file(self):
        self.assertIsNone(run_awsm(self.base_config))


if __name__ == '__main__':
    unittest.main()