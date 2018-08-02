from smrf import ipw
import numpy as np
import os
import logging


class topo():
    """
    Class for topo images and processing those images. Images are:
    - DEM
    - Mask

    Inputs to topo are the topo section of the config file

    Attributes:
        topoConfig: configuration for topo
        dem: numpy array for the DEM
        mask: numpy array for the mask
        ny: number of columns in DEM
        nx: number of rows in DEM
        u,v: location of upper left corner
        du, dv: step size of grid
        unit: geo header units of grid
        coord_sys_ID: coordinate syste,
        x,y: position vectors
        X,Y: position grid

    """

    images = ['dem', 'mask']

    def __init__(self, topoConfig, logger):
        self.topoConfig = topoConfig

        logger.debug('Reading in topo info for AWSM')
        # read images
        img_type = self.topoConfig['type']
        if img_type == 'ipw':
            self.readImages()
        elif img_type == 'netcdf':
            self.readNetCDF()

        logger.debug('Done reading in topo info for AWSM')

    def readImages(self):
        """
        Read in the images from the config file
        """
        if 'dem' not in self.topoConfig:
            raise ValueError('DEM file not specified')

        # read in the images
        for v in self.images:
            if v in self.topoConfig:
                i = ipw.IPW(self.topoConfig[v])

                setattr(self, v, i.bands[0].data.astype(np.float64))

                if v == 'dem':
                    # get some general information about the model
                    # domain from the dem
                    self.ny = i.nlines
                    self.nx = i.nsamps
                    self.u = i.bands[0].bline
                    self.v = i.bands[0].bsamp
                    self.du = i.bands[0].dline
                    self.dv = i.bands[0].dsamp
                    self.units = i.bands[0].geounits
                    self.coord_sys_ID = i.bands[0].coord_sys_ID

            else:
                setattr(self, v, None)

        # create the x,y vectors
        self.x = self.v + self.dv*np.arange(self.nx)
        self.y = self.u + self.du*np.arange(self.ny)
        [self.X, self.Y] = np.meshgrid(self.x, self.y)

    def readNetCDF(self):
        """
        Read in the images from the config file where the file
        listed is in netcdf format
        """

        if 'filename' not in self.topoConfig:
            raise ValueError('''Filename was not specified in topo.
                            Please provide a netcdf filename in config file.''')

        # read in the images
        f = Dataset(self.topoConfig['filename'], 'r')

        # read in the images
        # netCDF files are stored typically as 32-bit float, so convert
        # to double or int
        for v_smrf in self.images:

            # check to see if the user defined any variables e.g. veg_height = veg_length
            if v_smrf in self.topoConfig.keys():
                v_file = self.topoConfig[v_smrf]
            else:
                v_file = v_smrf

            if v_file in f.variables.keys():
                result = f.variables[v_file][:].astype(np.float64)

            setattr(self, v_smrf, result)

        # get some general information about the model domain from the dem
        self.nx = f.dimensions['x'].size
        self.ny = f.dimensions['y'].size

        # create the x,y vectors
        self.x = f.variables['x'][:]
        self.y = f.variables['y'][:]
        [self.X, self.Y] = np.meshgrid(self.x, self.y)

        self.du = self.y[1] - self.y[0]
        self.dv = self.x[1] - self.x[0]
        self.v = self.x[0]
        self.u = self.y[0]
        self.units = f.variables['y'].units

        f.close()


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
        ts['x'] = x
        ts['y'] = y
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
        ts['x'] = ts['v'] + ts['dv']*np.arange(ts['nx'])
        ts['y'] = ts['u'] + ts['du']*np.arange(ts['ny'])

    return ts
