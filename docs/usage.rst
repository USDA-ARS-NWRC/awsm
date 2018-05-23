=====
Usage
=====

To run AWSM, a configuration is require and it's simply passed as the first
argument to the awsm command. If the configuration file was named config.ini
it could be used like the following.

.. code-block:: bash

  awsm config.ini

For configuring AWSM simulations refer to :ref:`using-configs`. If you are
interested in using AWSM in a project, getting started looks like this:

.. code-block:: python

  import awsm

  with awsm.framework.framework.AWSM(configFile) as a:
    # Specify functions to run

Review the script for running AWSM in "./scripts/awsm"  to get a better sense of
the methods used to run AWSM and use the :ref:`api-documentation`
