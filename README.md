# Automated Water Supply Model

[![GitHub version](https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm.svg)](https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.898158.svg)](https://doi.org/10.5281/zenodo.898158)
[![DOI](https://readthedocs.org/projects/awsm/badge/)](https://awsm.readthedocs.io)
[![Docker Build Status](https://img.shields.io/docker/build/usdaarsnwrc/awsm.svg)](https://hub.docker.com/r/usdaarsnwrc/awsm/)
[![Docker Automated build](https://img.shields.io/docker/automated/usdaarsnwrc/awsm.svg)](https://hub.docker.com/r/usdaarsnwrc/awsm/)
[![Coverage Status](https://coveralls.io/repos/github/USDA-ARS-NWRC/awsm/badge.svg?branch=HEAD)](https://coveralls.io/github/USDA-ARS-NWRC/awsm?branch=HEAD)
[![Build Status](https://travis-ci.org/USDA-ARS-NWRC/awsm.svg?branch=devel)](https://travis-ci.org/USDA-ARS-NWRC/awsm)


Automated Water Supply Model (AWSM) was developed at the USDA Agricultural
Research Service (ARS) in Boise, ID. AWSM was designed to streamline the work
flow used by the ARS to forecast the water supply of multiple water basins.
AWSM standardizes the steps needed to distribute weather station data with SMRF,
run an energy and mass balance with iSnobal, and process the results, while
maintaining the flexibility of each program.

![image](https://raw.githubusercontent.com/USDA-ARS-NWRC/awsm/master/docs/_static/ModelSystemOverview_new.png)

## Quick Start

The fastest way to get up and running with AWSM is to use the docker images that
are pre-built and can deployed cross platform.

To build AWSM natively from source checkout the install instructions [here].

[here]: https://awsm.readthedocs.io/en/latest/installation.html

### Docker

Docker images are containers that allow us to ship the software to our users
seamlessly and without a headache. It is by far the easiest way to use AWSM. If
you are curious to read more about them, visit [Whats a container] on docker's
website.

[Whats a container]: https://www.docker.com/what-container

Using docker images comes with very minor quirks though, such as requiring you to
mount a volume to access the data when you are done with your run. To mount a
data volume, so that you can share data between the local file system and the
docker, the `-v` option must be used. For a more in depth discussion and
tutorial, read about [docker volumes]. The container has a shared data volume
at `/data` where the container can access the local file system.

[docker volumes]: https://docs.docker.com/storage/volumes/


**NOTE: On the host paths to the volume to mount, you must use full absolute paths!**

### Running the Demo

To simply run the AWSM demo; mount the desired directory as a volume and run
the image, using the following command:

**For Linux:**

```
  docker run -v <path>:/data -it usdaarsnwrc/awsm:develop
```

**For MacOSX:**

```
  docker run -v /Users/<path>:/data -it usdaarsnwrc/awsm:develop
```

**For Windows:**

```
  docker run -v /c/Users/<path>:/data -it usdaarsnwrc/awsm:develop
```

The output netCDF files will be placed in the location you mounted (using the
-v option). We like to use [ncview] to view our netcdf files quickly.

[ncview]: http://meteora.ucsd.edu/~pierce/ncview_home_page.html

### Setting Up Your Run

To use the AWSM docker image to create your own runs, you need to setup a
project folder containing all the files necessary to run the model. Then using
the same command above, mount your project folder and provide a path to the
configuration file. An example of a project folder might like:

```
My_Basin
      ├── air_temp.csv
      ├── cloud_factor.csv
      ├── config.ini
      ├── maxus.nc
      ├── metadata.csv
      ├── output
      ├── precip.csv
      ├── solar.csv
      ├── topo.nc
      ├── vapor_pressure.csv
      ├── wind_direction.csv
      └── wind_speed.csv
```

Then the command would be:

```
docker run -v <path>/My_Basin:/data -it usdaarsnwrc/awsm:develop <path>/My_Basin/config.ini
```
