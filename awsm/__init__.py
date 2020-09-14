from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    __version__ = 'unknown'

from . import framework
from . import interface
import os
import smrf

__core_config__ = os.path.abspath(
    os.path.dirname(__file__) + '/framework/CoreConfig.ini')
__recipes__ = os.path.abspath(os.path.dirname(
    __file__) + '/framework/recipes.ini')

__config_titles__ = {
    'awsm master': 'Configurations for AWSM Master section',
    'paths': 'Configurations for PATHS section for rigid directory work',
    'grid': 'Configurations for GRID data to run iSnobal',
    'files': 'Input files to run AWSM',
    'awsm system': 'System parameters',
    'isnobal restart': 'Parameters for restarting from crash',
    'ipysnobal': 'Running Python wrapped iSnobal',
    'ipysnobal initial conditions': 'Initial condition parameters for PySnobal',
    'ipysnobal constants': 'Input constants for PySnobal'
}


__config_header__ = "Configuration File for AWSM {0}\n" \
    "Using SMRF {1}\n\n" \
    "For AWSM related help see:\n" \
    "http://awsm.readthedocs.io/en/latest/\n" \
    "\nFor SMRF related help see:\n" \
    "http://smrf.readthedocs.io/en/latest/\n".format(
        __version__,
        smrf.__version__)
