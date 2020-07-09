from .gitinfo import __gitVersion__, __gitPath__
import os
import numpy as np
import awsm
from awsm import __version__
import smrf
from spatialnc import ipw
from netCDF4 import Dataset

def getgitinfo():
    """gitignored file that contains specific AWSM version and path

    Input:
        - none
    Output:
        - path to base AWSM directory
        - git version from 'git describe'
    """
    # return git describe if in git tracked SMRF
    if len(__gitVersion__) > 1:
        return __gitVersion__

    # return overarching version if not in git tracked SMRF
    else:
        version = 'v'+__version__
        return version


def get_config_header():
    """
    Produces the string for the main header for the config file.
    """
    hdr = ("Configuration File for AWSM {0}\n"
           "Using SMRF {1}\n"
           "\n"
           "For AWSM related help see:\n"
           "http://awsm.readthedocs.io/en/latest/\n"
           "\nFor SMRF related help see:\n"
           "http://smrf.readthedocs.io/en/latest/\n").format(getgitinfo(),
                                                           smrf.__version__)

    return hdr
