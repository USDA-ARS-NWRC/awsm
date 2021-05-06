=============================
Full Development Installation
=============================

The full stack installation will allow a user to run AWSM with the following enabled:

* High Resolution Rapid Refresh (HRRR) as inputs
* WindNinja to downscale HRRR to the iSnobal domain

To install AWSM, we recommend using the docker image. If that is not feasible, then
install all the necessary dependencies from source. This will install the following packages:

* Weather Forecast Retrieval
* SMRF
* PySnobal
* Katana (WindNinja)
* AWSM

Environment Setup
-----------------

Setup a virtual environment and activate.

.. code:: bash

    python3 -m virtualenv .venv
    source .venv/bin/activate

Build Folder Structure
----------------------

The basic folder structure for the full stack will be as follows. Everything
under `windninja` will build the dependencies and windninja code.

- awsm_project
    - windninja (can be removed after install)
        - grib2
        - poppler-0.23.4
        - proj-4.8.0
        - gdal-2.2.2
        - windninja
        - build
    - awsm
    - smrf
    - pysnobal
    - katana
    - weather_forecast_retrieval (if needed)


System Dependencies
-------------------

Ubuntu / Debain
~~~~~~~~~~~~~~~

.. code:: bash

    sudo apt-get install -y python3-dev \
        python3-pip \
        git \
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
        libcurl4-gnutls-dev \
        netcdf-bin \
        libnetcdf-dev \
        libpng-dev \
        python3 \
        python3-pip \
        curl \
        libeccodes-dev \
        libeccodes-tools \
        wget

wgrib2
~~~~~~

`wgrib2` allows for working with grib2 files and is maintained by NOAA_.

.. _NOAA: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/compile_questions.html

.. code:: bash

    export CC=gcc
    export FC=gfortran
    curl -L ftp://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/wgrib2.tgz | tar xz

    cd grib2
    wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-c-4.7.3.tar.gz
    wget https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.10/hdf5-1.10.4/src/hdf5-1.10.4.tar.gz
    sed -i "s/USE_NETCDF4=0/USE_NETCDF4=1/" makefile
    sed -i "s/USE_NETCDF3=1/USE_NETCDF3=0/" makefile
    make
    make lib
    sudo cp wgrib2/wgrib2 /usr/local/bin/wgrib2
    make deep-clean

WindNinja
~~~~~~~~~

WindNinja has many build dependencies and is well documented on their github wiki. WindNinja relies
on `poppler`, `gdal` and `proj` before it can be installed.

.. code:: bash

    PREFIX=/usr/local
    POPPLER="poppler-0.23.4"
    PROJ="proj-4.8.0"
    GDAL="gdal-2.2.2"

    # Get and build poppler for PDF support in GDAL
    wget http://poppler.freedesktop.org/$POPPLER.tar.xz
    tar -xvf $POPPLER.tar.xz 
    cd $POPPLER/
    ./configure --prefix=$PREFIX --enable-xpdf-headers
    make
    sudo make install
    cd ..

    # Get and build proj
    wget http://download.osgeo.org/proj/$PROJ.tar.gz
    tar xvfz $PROJ.tar.gz
    cd $PROJ
    ./configure --prefix=$PREFIX
    make clean
    make
    sudo make install
    sudo cp $PREFIX/include/proj_api.h $PREFIX/lib
    cd ..

    # Get and build GDAL with poppler support
    wget http://download.osgeo.org/gdal/2.2.2/$GDAL.tar.gz
    tar -xvf $GDAL.tar.gz 
    cd $GDAL/
    ./configure --prefix=$PREFIX --with-poppler=$PREFIX
    make -j 8
    sudo make install
    cd ..

With the 3 dependencies installed, WindNinja can be installed.

.. code:: bash

    mkdir -p windninja/build
    curl -L https://github.com/firelab/windninja/archive/3.5.0.tar.gz | tar xz
    mv windninja-3.5.0 windninja/windninja
    cmake -DNINJA_CLI=ON -DNINJAFOAM=OFF -DNINJA_QTGUI=OFF windninja/windninja
    make
    sudo make install
    sudo ldconfig
    rm -rf windninja/

Model Code
----------

Weather Forecast Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~

Weather Forecast Retrieval (WFR) loads gridded datasets like HRRR and formats the data into a
format that SMRF can utilize.

NOTE: Weather forecast retrieval is a dependency of SMRF and should not to be installed from source
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