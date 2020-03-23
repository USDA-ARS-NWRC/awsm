import os
import shutil
import unittest

import awsm


class AWSMTestCase(unittest.TestCase):
    """
    Base AWSM test case class.

    Has an attribute set for with the location of the root test folder.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = os.path.abspath(os.path.join(
            os.path.dirname(awsm.__file__), '..', 'tests'
        ))

    def tearDown(self):
        """
        Clean up the output directory if set via `cls.run_dir`.

        To skip this automated clean up, set the `cls.cache_run` on the
        test class.
        """
        if hasattr(self, 'cache_run') and self.cache_run:
            return
        elif hasattr(self, 'run_dir') and self.run_dir:
            folder = os.path.join(self.run_dir, 'output')
            no_delete = os.path.join(folder, '.keep')
            for the_file in os.listdir(folder):
                file_path = os.path.join(folder, the_file)
                if file_path != no_delete:
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(e)
