from .gitinfo import __gitVersion__, __gitPath__
import os
from smrf import ipw
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

def get_topo_stats(fp, filetype='netcdf'):
    """
    Get stats about topo from the topo file
    Returns:
        ts - dictionary of topo header data
    """

    fp = os.path.abspath(fp)

    ts = {}

    if filetype == 'netcdf':
        ds = Dataset(fp, 'r')
        ts['units'] = ds.variables['y'].units
        y = ds.variables['y'][:]
        x = ds.variables['x'][:]
        ts['nx'] = len(x)
        ts['ny'] = len(y)
        ts['du'] = y[1] - y[0]
        ts['dv'] = x[1] - x[0]
        ts['v'] = x[0]
        ts['u'] = y[0]
        ds.close()

    if filetype == 'ipw':
        i = ipw.IPW(fp)
        ts['nx'] = i.nsamps
        ts['ny'] = i.nlines
        ts['units'] = i.bands[0].units
        ts['du'] = i.bands[0].dline
        ts['dv'] = i.bands[0].dsamp
        ts['v'] = float(i.bands[0].bsamp)
        ts['u'] = float(i.bands[0].bline)
        ts['csys'] = i.bands[0].coord_sys_ID

    return ts
