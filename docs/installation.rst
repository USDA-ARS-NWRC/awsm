.. highlight:: shell

============
Installation
============


Installing AWSM
---------------

Once the dependencies have been installed for your respective system, the
following will install awsm. It is preferable to use a Python
`virtual environment`_  to reduce the possibility of a dependency issue.

.. _virtual environment: https://virtualenv.pypa.io

1. Create a virtualenv and activate it.

  .. code:: bash

    virtualenv awsmenv
    source awsmenv/bin/activate

**Tip:** The developers recommend using an alias to quickly turn on
and off your virtual environment.


2. Clone AWSM source code from the ARS-NWRC github.

  .. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/AWSM.git

3. Change directories into the AWSM directory. Install the python requirements.
   After the requirements are done, install AWSM.

  .. code:: bash

    cd AWSM
    pip install -r requirements-dev.txt
    python setup.py install

4. (Optional) Generate a local copy of the documentation.

  .. code:: bash

    cd docs
    make html

  To view the documentation use the preferred browser to open up the files.
  This can be done from the browser by opening the index.rst file directly or
  by the commandline like the following:

  .. code:: bash

    google-chrome _build/html/index.html
