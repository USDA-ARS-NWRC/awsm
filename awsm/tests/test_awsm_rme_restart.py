# from inicheck.tools import cast_all_variables
# import logging

# from awsm.framework.framework import run_awsm
# from awsm.tests.test_awsm_rme import TestStandardRME, TestRMESMRFiPysnobal


# class TestRestart(TestStandardRME):
#     """
#     Testing using RME:
#         - ipysnobal
#         - initialize with all zeros
#         - loading from netcdf
#         - restart simulation
#     """

#     @classmethod
#     def restart_configure(cls):
#         config = cls.run_config_copy()
#         config.raw_cfg['awsm master']['run_smrf'] = False
#         config.raw_cfg['ipysnobal']['restart_date_time'] = '1986-02-17 05:00:00'  # noqa
#         config.apply_recipes()
#         cls.run_config = cast_all_variables(config, config.mcfg)

#     @classmethod
#     def setUpClass(cls):
#         # run the model as normal
#         super().setUpClass()

#         # restart the run from a different point
#         cls.restart_configure()
#         run_awsm(cls.run_config)


# class TestSMRFiPysnobalRestart(TestRMESMRFiPysnobal):
#     """
#     Testing using RME:
#         - smrf_ipysnobal
#         - initialize with all zeros
#         - loading from netcdf
#         - restart simulation
#     """

#     @classmethod
#     def restart_configure(cls):
#         config = cls.base_config_copy()
#         config.raw_cfg['awsm master']['run_smrf'] = False
#         config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
#         config.raw_cfg['ipysnobal']['restart_date_time'] = '1986-02-17 05:00:00'  # noqa
#         config.raw_cfg['system']['threading'] = False

#         config.apply_recipes()
#         cls.run_config = cast_all_variables(config, config.mcfg)

#     @classmethod
#     def setUpClass(cls):
#         # run the model as normal
#         super().setUpClass()

#         # restart the run from a different point
#         cls.restart_configure()
#         run_awsm(cls.run_config)


# # class TestRMESMRFiPysnobalThread(TestStandardRME):
# #     """
# #     Testing using RME:
# #         - smrf_ipysnobal
# #         - SMRF threading
# #         - initialize with all zeros
# #         - loading from netcdf
# #     """

# #     @classmethod
# #     def configure(cls):
# #         config = cls.base_config_copy()
# #         config.raw_cfg['awsm master']['run_smrf'] = False
# #         config.raw_cfg['awsm master']['model_type'] = 'smrf_ipysnobal'
# #         config.raw_cfg['system']['threading'] = True

# #         config.apply_recipes()
# #         cls.run_config = cast_all_variables(config, config.mcfg)
