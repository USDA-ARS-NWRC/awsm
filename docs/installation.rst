.. highlight:: shell

============
Installation
============

Installing Dependencies
-----------------------

AWSM utilizes many of the utilities within SMRF. The first step is to read and
follow the install instructions for SMRF, found here_. Make sure to follow all
instructions, including installing IPW.

.. _here: https://smrf.readthedocs.io/en/develop/install.html

The source code for SMRF is stored on on GitHub_.

.. _GitHub: https://github.com/USDA-ARS-NWRC/smrf

If you would like to use the PySnobal within AWSM, you can download
and install the package following the guidelines on the `PySnobal repo`_ .
**This is optional**.

.. _PySnobal repo: https://github.com/USDA-ARS-NWRC/pysnobal

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
