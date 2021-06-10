AWSM Debugging
==============

While many errors can be handled with AWSM, sometimes not everything is caught. The
following are a few suggestions on debugging an AWSM simulation.

Configuration file issues
-------------------------

A common issue are problems with the configuration file. There are many options that
can be changed/set and various combinations changing what is required. At the beginning of each
simulation, AWSM will check the configuration file for any issues. If there are any, it will
display the warnings or errors in the console.

An example for a warning, the AWSM simulation will continue but ensure that the warnings
are not impacting the simulation. The below warning is a great example where AWSM is warning
that the log file doesn't exist, which is okay because AWSM will create the log file automatically.

.. code:: bash

    Configuration File Status Report:
    ==========================================================================================
    WARNINGS:
    
    Section             Item                      Message                                                     
    ------------------------------------------------------------------------------------------
    system              log_file                 File does not exist.      


When an error in the configuration file occurs, ``inicheck`` will not let the simulation continue.
Look at the error message and consult the documentation for either the :doc:`config/smrf_core_config` or
:doc:`config/awsm_core_config` configuration.

In the example below, the topo file name does not exist and the simulation will exit. Fix by
providing the correct file path.

.. code:: bash

    Configuration File Status Report:
    ==========================================================================================
    ERRORS:
    
    Section             Item                      Message                                                     
    ------------------------------------------------------------------------------------------
    topo                filename                  File does not exist.    
    


Logfile verbosity
-----------------

AWSM and SMRF provide a log of information about what each are doing. The logging capabilties
allow for AWSM to output various levels of information based on Python's ``logging`` module 
(`list of levels`_). If issues occur with AWSM, a good first step is to turn up the logging.
This can be accomplished in the configuration file by setting ``log_level`` to ``DEBUG``.

.. _`list of levels`: https://docs.python.org/3/library/logging.html#levels

.. code:: bash

    [awsm system]
    log_level:      debug