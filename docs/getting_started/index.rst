===============
Getting started
===============

Installation
------------

To install AWSM locally on Linux of MacOSX, first clone the repository and build into a
virtual environment. The general steps are as follows and will
test the AWSM installation by running the tests.

Clone from the repository

.. code:: bash

    git clone https://github.com/USDA-ARS-NWRC/awsm.git


And install the requirements and run the tests.

.. code:: bash

    python3 -m pip install -r requirements_dev.txt
    python3 -m pip install .
    python3 -m unittest -v


For in-depth instructions to installing all the development packages and specific requirements
for AWSM, check out the the :doc:`installation page <full_stack_install>` 

For Windows, the install method is using Docker.

.. toctree::
    :maxdepth: 2

    installation
    full_stack_install