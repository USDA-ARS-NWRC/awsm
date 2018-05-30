Automated Water Supply Model
============================

|GitHub version| |docs| |docker build| |docker automated|

Automated Water Supply Model (AWSM) was developed at the USDA
Agricultural Research Service (ARS) in Boise, ID. AWSM was designed to
streamline the work flow used by the ARS to forecast the water supply of
multiple water basins. AWSM standardizes the steps needed to distribute
weather station data with SMRF, run an energy and mass balance with
iSnobal, and process the results, while maintaining the flexibility of
each program.

.. |GitHub version| image:: https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm.svg
    :alt: AWSM Version
    :target: https://badge.fury.io/gh/USDA-ARS-NWRC%2Fawsm

.. |docs| image:: https://readthedocs.org/projects/awsm/badge/
    :alt: Documentation Status
    :target: https://awsm.readthedocs.io

.. |docker build| image:: https://img.shields.io/docker/build/usdaarsnwrc/awsm.svg
    :alt: Docker Build Status
    :target: https://hub.docker.com/r/usdaarsnwrc/awsm/

.. |docker automated| image:: https://img.shields.io/docker/automated/usdaarsnwrc/awsm.svg
    :alt: Automated Docker Build Status
    :target: https://hub.docker.com/r/usdaarsnwrc/awsm/

.. image::https://raw.githubusercontent.com/USDA-ARS-NWRC/awsm/master/docs/_static/ModelSystemOverview_new.png

Quick Start
-----------

The fastest way to get up and running with AWSM is to use the docker
images that are pre-built and can deployed cross platform.

To build AWSM natively from source checkout the install instructions
`here`_.

.. _here: https://awsm.readthedocs.io/en/latest/installation.html

Docker
~~~~~~

Docker images are containers that allow us to ship the software to our
users seamlessly and without a headache. It is by far the easiest way to
use AWSM. If you are curious to read more about them, visit `Whats a
container`_ on docker’s website.

.. _Whats a container: https://www.docker.com/what-container

Using docker images comes with very minor quirks though, such as
requiring you to mount a volume to access the data when you are done
with your run. To mount a data volume, so that you can share data
between the local file system and the docker, the ``-v`` option must be
used. For a more in depth discussion and tutorial, read about `docker
volumes`_. The container has a shared data volume at ``/data`` where the
container can access the local file system.

.. _docker volumes: https://docs.docker.com/storage/volumes/

**NOTE: On the host paths to the volume to mount, you must use full
absolute paths!**

Running the Demo
~~~~~~~~~~~~~~~~

To simply run the AWSM demo; mount the desired directory as a volume and
run the image, using the following command:

**For Linux:**

.. code-block:: console

     docker run -v <path>:/data -it usdaarsnwrc/awsm:develop

**For MacOSX:**

.. code-block:: console

     docker run -v /Users/<path>:/data -it usdaarsnwrc/awsm:develop

**For Windows:**

.. code-block:: console

     docker run -v /c/Users/<path>:/data -it usdaarsnwrc/awsm:develop

The output netCDF files will be placed in the location you mounted
(using the -v option). We like to use `ncview`_ to view our netcdf files
quickly.

.. _ncview: http://meteora.ucsd.edu/~pierce/ncview_home_page.html

Setting Up Your Run
~~~~~~~~~~~~~~~~~~~

To use the AWSM docker image to create your own runs, you need to setup
a project folder containing all the files necessary to run the model.
Then using the same command above, mount your project folder and provide
a path to the configuration file. An example of a project folder might
like:

.. code-block:: console

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

Then the command would be:

.. code-block:: console

  docker run -v <path>/My_Basin:/data -it usdaarsnwrc/awsm:develop <path>/My_Basin/config.ini
