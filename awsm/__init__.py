
__version__ = '0.10.0'

from . import framework
from . import interface
from . import convertFiles
from . import utils
import os
import matplotlib
matplotlib.use('Agg')

__core_config__ = os.path.abspath(
    os.path.dirname(__file__) + '/framework/CoreConfig.ini')
__recipes__ = os.path.abspath(os.path.dirname(
    __file__) + '/framework/recipes.ini')

__config_titles__ = {
    'awsm master': 'Configurations for AWSM Master section',
    'paths': 'Configurations for PATHS section'
    ' for rigid directory work',
    'grid': 'Configurations for GRID data to run iSnobal',
    'files': 'Input files to run AWSM',
    'awsm system': 'System parameters',
    'isnobal restart': 'Parameters for restarting'
    ' from crash',
    'ipysnobal': 'Running Python wrapped iSnobal',
    'ipysnobal initial conditions': 'Initial condition'
    ' parameters for'
    ' PySnobal',
    'ipysnobal constants': 'Input constants for PySnobal'
}


__config_header__ = utils.utilities.get_config_header()
