Full Development Installation
=============================

The full stack installation will allow a user to run AWSM from source with the following enabled:

* High Resolution Rapid Refresh (HRRR) as inputs
* WindNinja to downscale HRRR to the iSnobal domain

To install AWSM, we recommend using the docker image. If that is not feasible, then
install all the necessary dependencies from source. This will install the following packages:

* Weather Forecast Retrieval
* SMRF
* PySnobal
* Katana (WindNinja)
* AWSM

.. note::

    **Use at your own risk!** While this contains the latest code, it is not guaranteed
    to work with the whole modeling framework. 

    The latest code on contains all the latest developments. However, this must be used with caution
    as it can be under active development, may change at any time and is not guaranteed to work with
    the rest of the modeling framework at that moment. Once the code has been fully tested within the
    modeling framework, a new release will be created to signal a move to a stable version.

Basic Folder Structure
----------------------

The basic folder structure for the full stack will be as follows. Everything
under `windninja` will build the dependencies and windninja code.

- awsm_project
    - .venv
    - windninja (can be removed after install)
        - windninja
        - build
        - <other dependencies>
    - grib2 (can be removed after install)
    - awsm
    - smrf
    - pysnobal
    - katana
    - weather_forecast_retrieval (if needed)


System Dependencies
-------------------

Ubuntu / Debain
~~~~~~~~~~~~~~~

Python dependencies

.. code:: bash

    sudo apt-get install -y python3 \
        python3-dev \
        python3-pip \

System dependencies

.. code:: bash

    sudo apt-get install -y git \
        gcc \
        g++ \
        cmake \
        make \
        ca-certificates \
        libblas-dev \
        liblapack-dev \
        libatlas-base-dev \
        libffi-dev \
        libssl-dev \
        gfortran \
        libyaml-dev \
        libfreetype6-dev \
        netcdf-bin \
        libpng-dev \
        m4 \
        curl \
        libeccodes-dev \
        libeccodes-tools \
        wget

Environment Setup
-----------------

Setup a virtual environment and activate.

.. code:: bash

    python3 -m virtualenv .venv
    source .venv/bin/activate


WindNinja
~~~~~~~~~

WindNinja has many build dependencies and is well documented on their github `wiki`_. WindNinja relies
on `poppler`, `gdal` and `proj` before it can be installed. WindNinja provides a handy `build_deps.sh`
script that aids in the building of the dependencies.

.. _wiki: https://github.com/firelab/windninja/wiki/Building-WindNinja-on-Linux

Download WindNinja and move to the correct location.

.. code:: bash

    cd awsm_project
    mkdir -p windninja/build
    curl -L https://github.com/firelab/windninja/archive/3.5.0.tar.gz | tar xz
    mv windninja-3.5.0 windninja/windninja

Now build the dependencies for WindNinja with their `build_deps.sh` script. This
will take a long time.

.. code:: bash

    cd awsm_project/windninja
    sh windninja/scripts/build_deps.sh

Build WindNinja

.. code:: bash

    cd awsm_project/windninja
    cmake -DNINJA_CLI=ON -DNINJAFOAM=OFF -DNINJA_QTGUI=OFF windninja
    make
    sudo make install
    sudo ldconfig

Clean up the WindNinja build folder.

.. code:: bash

    rm -rf awsm_project/windninja/

wgrib2
~~~~~~

`wgrib2` allows for working with grib2 files and is maintained by NOAA_. The install
will take time as `wgrib2` will perform tests during installation.

.. _NOAA: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/compile_questions.html

.. code:: bash

    cd awsm_project
    export CC=gcc
    export FC=gfortran
    curl -L ftp://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/wgrib2.tgz | tar xz

    cd awsm_project/grib2
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-c-4.7.3.tar.gz
    wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.4/src/hdf5-1.10.4.tar.gz
    sed -i "s/USE_NETCDF4=0/USE_NETCDF4=1/" makefile
    sed -i "s/USE_NETCDF3=1/USE_NETCDF3=0/" makefile
    make
    make lib
    sudo cp wgrib2/wgrib2 /usr/local/bin/wgrib2
    make deep-clean

    rm -rf awsm_project/grib2

Model Code
----------

Weather Forecast Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~

Weather Forecast Retrieval (WFR) loads gridded datasets like HRRR and formats the data into a
format that SMRF can utilize.

.. note::
    
    Weather forecast retrieval is a dependency of SMRF and should not to be installed from source 
    unless modifying the weather forecast retrieval code.

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/weather_forecast_retrieval.git
    cd weather_forecast_retrieval
    python3 -m pip install -r requirements.txt
    python3 -m pip install -e .

PySnobal
~~~~~~~~

PySnobal

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/pysnobal.git
    cd pysnobal
    python3 -m pip install -e .

AWSM
~~~~

Automated Water Supply Model (AWSM)

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/awsm.git
    cd awsm
    python3 -m pip install -r requirements.txt
    python3 -m pip install -e .

SMRF
~~~~

Spatial Modeling for Resources Framework (SMRF)

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/smrf.git
    cd smrf
    python3 -m pip install -r requirements.txt
    python3 -m pip install -e .[test]

katana
~~~~~~

Katana

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/katana.git
    cd awsm
    python3 -m pip install -r requirements.txt
    python3 -m pip install -e .

Testing
-------

After all the dependencies and model code are installed, we recommend testing to
ensure that the code will work as expected during the model simulations.

The unittest framework is used to run the tests with `python3 -m unittest -v` within
the following repositories:

- `weather_forecast_retrieval`
- `smrf`
- `awsm`
- `katana`

If many of the tests provide information that the tests were within a tolerance or
failed because the results were not the same, try to set the following environment variable
to increase the tolerance criteria for passing a test.

.. code:: bash

    export NOT_ON_GOLD_HOST=YOU_BETCHA