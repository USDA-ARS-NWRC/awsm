==========
User guide
==========

The User Guide covers different topic areas in AWSM and will show
how to run specific types of simulations using different inputs, outputs
and/or models.

- Docker volume mounting and what needs to be set
  - permission problems
- Using WindNinja and Katana
  - making sure the data is in the right directory
- Input data and removing config sections
  - What does ``time_step`` mean
  - checking for grid cells in the model domain
- Custom vegetation in the ``topo.nc``
- References
- Debugging errors with ``debug`` log level
- Lidar assimilation
- restarting

.. toctree::
    :maxdepth: 2
    
    configuration
    config/index
    debugging
    tk_lt_zero