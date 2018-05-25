# Automated Water Supply Model

[![GitHub version](https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm.svg)](https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.898158.svg)](https://doi.org/10.5281/zenodo.898158)
[![DOI](https://readthedocs.org/projects/awsm/badge/)](https://awsm.readthedocs.io)
[![Docker Build Status](https://img.shields.io/docker/build/usdaarsnwrc/awsm.svg)](https://hub.docker.com/r/usdaarsnwrc/awsm/)
[![Docker Automated build](https://img.shields.io/docker/automated/usdaarsnwrc/awsm.svg)](https://hub.docker.com/r/usdaarsnwrc/awsm/)

Automated Water Supply Model (AWSM) was developed at
the USDA Agricultural Research Service (ARS) in Boise, ID. AWSM was designed to
streamline the work flow used by the ARS to forecast the water supply of multiple
water basins. AWSM standardizes the steps needed to distribute met. data with
SMRF, run an energy and mass balance with iSnobal, and process the results,
while maintaining the flexibility of each program.

![image](https://raw.githubusercontent.com/USDA-ARS-NWRC/awsm/master/docs/_static/ModelSystemOverview_new.png)


## Quick Start

The fastest way to get up and running with AWSM is to use the docker images that
are pre-built and can deployed cross platform.

To build AWSM natively from source checkout the install instructions [here].

[here]: https://awsm.readthedocs.io/en/latest/installation.html

### Docker

To mount a data volume, so that you can share data between the local file system
and the docker, the `-v` option must be used. For a more in depth discussion and
tutorial, read about [docker volumes]. The container has a shared data volume
at `/data` where the container can access
the local file system.

[docker volumes]: https://docs.docker.com/storage/volumes/

When the image is run, it will go into the Python terminal within the image.
Within this terminal, AWSM can be imported. The command `/bin/bash` can be
appended to the end of docker run to enter into the docker terminal for full
control. It will start in the `/data` location with AWSM code in `/code/awsm`.

**NOTE**: On the host paths to the volume to mount, you must use full absolute paths!


For Linux:

```

  docker run -v <path>:/data -it usdaarsnwrc/awsm
```

For MacOSX:

```
  docker run -v /Users/<path>:/code/awsm/test_data/RME_run/output/rme/devel/wy1998/rme_test/runs/run1464_1670/output -it usdaarsnwrc/awsm
```

For Windows:

```

  docker run -v /c/Users/<path>:/code/awsm/test_data/RME_run/output/rme/devel/wy1998/rme_test/runs/run1464_1670/output -it usdaarsnwrc/awsm

```

The output netCDF files will be placed in the location specified.


## Running the test

To simply see if AWSM will run do the following run our test case:

```
  docker run -it usdaarsnwrc/awsm /bin/bash

```
