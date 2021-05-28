Create a config file
====================

After the topo file has been created, build the AWSM configuration file. For in depth documentation
see how to :doc:`use a configuration file <../user_guide/configuration>` and the
:doc:`core configuration <../user_guide/core_config>` for all AWSM options.

.. note::

    Configuration file paths are relative to the configuration file location.

At a minimum to get started, the following configuration file will apply all the defaults.
The required changes are specifying the path to the ``topo.nc`` file, dates to run the model
and the location of the csv input data.

Stable vs. Experimental
-----------------------

The configuration file is not compatible between the stable and experimental model versions. SMRF ``v0.10``
made a large overhaul to the configuration file to become more verbose and clean up options. If using
the stable version, the configuration file will be based on the previous `core config`_.

.. _core config: https://github.com/USDA-ARS-NWRC/smrf/blob/release-0.9/smrf/framework/CoreConfig.ini

.. note::

    Migrating from the stable SMRF can be achieved through ``inicheck`` `changelog`_.

.. _changelog: https://inicheck.readthedocs.io/en/latest/changelogs.html

Station Data Example
--------------------

The example below shows the minimum needed for using weather stations data with AWSM.

.. code::

    ################################################################################
    # Files for DEM and vegetation
    ################################################################################
    [topo]
    filename:                      ./topo/topo.nc

    ################################################################################
    # Dates to run model
    ################################################################################
    [time]
    time_step:                     60
    start_date:                    1998-01-14 15:00:00
    end_date:                      1998-01-14 19:00:00
    time_zone:                     utc

    ################################################################################
    # CSV section configurations
    ################################################################################
    [csv]
    wind_speed:                    ./station_data/wind_speed.csv
    air_temp:                      ./station_data/air_temp.csv
    cloud_factor:                  ./station_data/cloud_factor.csv
    wind_direction:                ./station_data/wind_direction.csv
    precip:                        ./station_data/precip.csv
    vapor_pressure:                ./station_data/vapor_pressure.csv
    metadata:                      ./station_data/metadata.csv

    ################################################################################
    # Air temperature distribution
    ################################################################################
    [air_temp]

    ################################################################################
    # Vapor pressure distribution
    ################################################################################
    [vapor_pressure]

    ################################################################################
    # Wind speed and wind direction distribution
    ################################################################################
    [wind]
    maxus_netcdf:                  ./topo/maxus.nc

    ################################################################################
    # Precipitation distribution
    ################################################################################
    [precip]

    ################################################################################
    # Albedo distribution
    ################################################################################
    [albedo]

    ################################################################################
    # Cloud Factor - Fraction used to limit solar radiation Cloudy (0) - Sunny (1)
    ################################################################################
    [cloud_factor]

    ################################################################################
    # Solar radiation
    ################################################################################
    [solar]

    ################################################################################
    # Incoming thermal radiation
    ################################################################################
    [thermal]

    ################################################################################
    # Soil temperature
    ################################################################################
    [soil_temp]

    ################################################################################
    # Output variables
    ################################################################################
    [output]
    out_location:                  ./output

    ################################################################################
    # System variables and Logging
    ################################################################################
    [system]

    ################################################################################
    # Configurations for AWSM Master section
    ################################################################################
    [awsm master]
    run_smrf:                      True
    model_type:                    ipysnobal

    ################################################################################
    # Configurations for PATHS section for rigid directory work
    ################################################################################
    [paths]
    path_dr:                       ./output
    basin:                         rme
    project_name:                  rme_test
    project_description:           fast rme test run

    ################################################################################
    # System parameters
    ################################################################################
    [awsm system]

    ################################################################################
    # Parameters for restarting from crash
    ################################################################################
    [isnobal restart]

    ################################################################################
    # Running Python wrapped iSnobal
    ################################################################################
    [ipysnobal]


Atmospheric Model Example
-------------------------

Atmospheric models require a few changes to the config file to tell SMRF that the input
data is gridded model output and how to interpolate to the AWSM model domain. For another
example, see the Lakes test within AWSM.


.. code::

    ################################################################################
    # Files for DEM and vegetation
    ################################################################################
    [topo]
    filename:                      ./topo/topo.nc

    ################################################################################
    # Dates to run model
    ################################################################################
    [time]
    time_step:                     60
    start_date:                    2019-10-01 15:00
    end_date:                      2019-10-01 17:00

    ################################################################################
    # Gridded dataset i.e. wrf_out
    ################################################################################
    [gridded]
    hrrr_directory:                ./input
    data_type:                     hrrr_grib

    ################################################################################
    # Air temperature distribution
    ################################################################################
    [air_temp]
    distribution:                  grid
    grid_local:                    True

    ################################################################################
    # Vapor pressure distribution
    ################################################################################
    [vapor_pressure]
    distribution:                  grid
    grid_local:                    True

    ################################################################################
    # Wind speed and wind direction distribution
    ################################################################################
    [wind]
    wind_model:                    wind_ninja
    distribution:                  grid
    wind_ninja_dir:                ./input
    wind_ninja_dxdy:               200
    wind_ninja_pref:               topo_windninja_topo
    wind_ninja_tz:                 UTC

    ################################################################################
    # Precipitation distribution
    ################################################################################
    [precip]
    distribution:                  grid
    grid_local:		               True

    ################################################################################
    # Albedo distribution
    ################################################################################
    [albedo]

    ################################################################################
    # Solar radiation distribution
    ################################################################################
    [solar]

    ################################################################################
    # Cloud Factor - Fraction used to limit solar radiation Cloudy (0) - Sunny (1)
    ################################################################################
    [cloud_factor]

    ################################################################################
    # Thermal radiation distribution
    ################################################################################
    [thermal]

    ################################################################################
    #  Soil temperature
    ################################################################################
    [soil_temp]

    ################################################################################
    # Output variables
    ################################################################################
    [output]
    out_location:                  ./output

    ################################################################################
    # System variables
    ################################################################################
    [system]

    ################################################################################
    # Configurations for AWSM Master section
    ################################################################################
    [awsm master]
    run_smrf:                      True
    model_type:                    ipysnobal

    ################################################################################
    # Configurations for PATHS section for rigid directory work
    ################################################################################
    [paths]
    path_dr:                       ./output
    basin:                         lakes
    project_name:                  lakes_gold
    project_description:           Lakes gold HRRR simulation
    
    ################################################################################
    # System parameters
    ################################################################################
    [awsm system]
    log_to_file:                   True
    
    ################################################################################
    # Parameters for restarting from crash
    ################################################################################
    [isnobal restart]

    ################################################################################
    # Running Python wrapped iSnobal
    ################################################################################
    [ipysnobal]

