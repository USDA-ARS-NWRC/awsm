Run AWSM
========

After installing AWSM, generating a topo and creating a configuration file, AWSM can be ran. There are
two ways to run AWSM, first is through the ``awsm`` command or through the AWSM API.

``awsm`` command
--------------------

To run a full simulation simply run (barring any errors):

.. code:: bash

    awsm <config_file_path>


AWSM API
--------

The ``awsm`` package can also be used as an API, but is not common practice. The main class
:mod:`AWSM <awsm.framework.AWSM>` has many methods that can be used to tailor a simulation
that deviates from the standard workflow in AWSM.