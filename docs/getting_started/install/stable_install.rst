Installation with Docker
========================

Both the stable and experimental version of AWSM are built into Docker images. While
the code and config files may be different, the way to run AWSM with Docker is the same
between versions.

Stable
------

The AWSM docker version for ``release-0.10`` is built on an Ubuntu 18.04 image and
has all the necessary dependencies installed. To get the stable version of AWSM:

.. code:: console

    docker pull usdaarsnwrc/awsm:0.10

Experimental
------------

The experimental AWSM docker is built on a Python 3.6 image and
has all the necessary dependencies installed. To get the latest version of AWSM
or specify a specific release with the release version:

.. code:: console

    docker pull usdaarsnwrc/awsm:latest
    docker pull usdaarsnwrc/awsm:0.11.3


Basic Project Folder Structure
------------------------------

We recommend the following or similar folder structure for the AWSM simulations. By keeping
to this folder structure, all the inputs and model configuration are in one place and can
be easily backed up, shared with others or packaged for a reproducible journal submission.

::

    awsm_project
    ├── config          
    │   ├── wy2021_awsm_config.ini
    |   |── wy2021_awsm_config_v2.ini
    ├── topo
    |   |── topo.nc
    |   |── lidar
    |       |── wy2020_lidar_snow_depths.nc
    ├── station_data
    |   |── air_temp.csv


- The ``config`` folder contains all the configuration files for the model simulations.
- The ``topo`` folder contains the ``topo.nc`` file and lidar snow depths if available
- The ``station_data`` folder contains csv files if using weather stations for input data
- If using atmospheric model for AWSM inputs, these do not have to be located in the ``awsm_project`` folder.
- The AWSM outputs can be large and also do not have to be located in the ``awsm_project`` folder.

Docker Examples
---------------

The AWSM docker image has a folder meant to mount data inside the docker image at ``/data``. We
recommend having a separate folder for the config, topo, inputs and outputs to make the file paths
verbose. The following docker examples could also be put into a ``docker-compose.yml`` to simplify
the command line.

.. note::

    The paths in the configuration file must be adjusted for being inside the docker image. For example,
    in the command below, the path to the config will be inside the docker image. This would be
    ``/data/config/config.ini`` and not the path on the host machine.


Station Data
~~~~~~~~~~~~

.. code:: console

    docker run \
        -v ./awsm_project/station_data:/data/input \
        -v ./awsm_project/config:/data/config \
        -v ./awsm_project/topo:/data/topo \
        -v /path/to/output:/data/output \ 
        usdaarsnwrc/awsm:0.10 /data/config/<config_name>.ini


Atmospheric Data
~~~~~~~~~~~~

.. code:: console

    docker run \
        -v /path/to/atmospheric/data:/data/input \
        -v ./awsm_project/config:/data/config \
        -v ./awsm_project/topo:/data/topo \
        -v /path/to/output:/data/output \ 
        usdaarsnwrc/awsm:0.10 /data/config/<config_name>.ini

