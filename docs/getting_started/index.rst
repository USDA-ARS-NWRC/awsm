===============
Getting started
===============

Which version to use?
---------------------

Stable
~~~~~~

The stable version of AWSM is currently :code:`v0.10`. The code can be downloaded from the `releases`_,
can be found on the :code:`release-0.10` `branch`_ or the stable :doc:`docker image <./stable_install>`.

.. _releases: https://github.com/USDA-ARS-NWRC/awsm/releases
.. _branch: https://github.com/USDA-ARS-NWRC/awsm/tree/release-0.10


Best for:

- Applying the model in near real time
- Researchers wanting a ready to use model
- Those wanting the most stable and tested code

Experimental
~~~~~~~~~~~~

.. note::
    ⚠️ Use at your own risk! While this contains the latest code, it is not guaranteed to work with the whole modeling framework.

The latest code on :code:`main` contains all the latest development to AWSM. However, this must be used with caution as it
can be under active development, may change at any time and is not guaranteed to work with the rest of the modeling framework
at that moment. Once the code has been fully tested within the modeling framework, a new release will be created to signal
a move to a stable version.

Best for:

- Those planning on developing with AWSM
- Model simulations require features only found in the latest code
- Okay with the possibility that AWSM doesn't work with the rest of the modeling system

Content
~~~~~~~

The following will guide the installation and setup of AWSM.

.. toctree::
    :maxdepth: 2

    stable_install
    full_stack_install
    basin_setup
    create_config
    run_awsm
    