# -*- coding: utf-8 -*-

"""Top-level package for awsf."""

__author__ = """Micah Sandusky"""
__email__ = 'micah.sandusky@ars.usda.gov'
__version__ = '0.1.0'

import os

__core_config__ = os.path.abspath(os.path.dirname(__file__)+'/framework/CoreConfig.ini')
from . import convertFiles
from . import interface
from . import framework
from . import knn
from . import premodel
