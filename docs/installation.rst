.. highlight:: shell

============
Installation
============

Installing Dependencies
-----------------------

AWSM was designed to run simulations with SMRF_ and PySnobal_. These are
the two main dependencies for AWSM. To install the dependencies:

.. code:: bash
  python3 -m pip install -r requirements.txt

.. _SMRF: https://github.com/USDA-ARS-NWRC/smrf
.. _PySnobal: https://github.com/USDA-ARS-NWRC/pysnobal

Installing AWSM
---------------

Once the dependencies have been installed for your respective system, the
following will install AWSM. It is preferable to use a Python
`virtual environment`_  to reduce the possibility of a dependency issue. You should
use the same virtual environment in which you installed SMRF. You can just
source your smrfenv instead of step number 1.

.. _virtual environment: https://virtualenv.pypa.io

1. Create a virtualenv and activate it.

  .. code:: bash

    virtualenv awsmenv
    source awsmenv/bin/activate

**Tip:** The developers recommend using an alias to quickly turn on
and off your virtual environment.


2. Clone AWSM source code from the ARS-NWRC github.

  .. code:: console

    git clone https://github.com/USDA-ARS-NWRC/AWSM.git

3. Change directories into the AWSM directory. Install the python requirements.
   After the requirements are done, install AWSM.

  .. code:: console

    cd AWSM
    pip install -r requirements.txt
    python setup.py install

4. (Optional) Generate a local copy of the documentation.

  .. code:: console

    cd docs
    make html

  To view the documentation use the preferred browser to open up the files.
  This can be done from the browser by opening the index.rst file directly or
  by the commandline like the following:

  .. code:: console

    google-chrome _build/html/index.html

Testing AWSM
---------------

Once everything is installed, you can run a quick test case over a small
catchment in Idaho called Reynolds Mountain East (RME).

1. Move to config file and run case. Start in your AWSM directory

  .. code:: console

    cd test_data/RME_run/
    awsm config.ini

2. Wait for the test run to finish and then view the results.

  .. code:: console

    cd output/rme/devel/wy1998/rme_test/

The iSnobal model outputs will be in the "runs" folder and the distributed
SMRF data will be in the "data" folder. Navigate around and see what the
outputs look like. You can visualize the .nc (netCDF) files with
the `ncview`_ utility.

.. _ncview: http://meteora.ucsd.edu/~pierce/ncview_home_page.html
