Choosing Input Data
===================

To generate all the input forcing data required to run iSnobal, the following
measured or derived variables are needed with a full description of the input
data found in the `SMRF documentation`_.

.. _`SMRF documentation`: https://smrf.readthedocs.io/en/latest/user_guide/input_data.html

Variable Descriptions
---------------------

Air temperature [Celcius]
   Measured or modeled air temperature at the surface

Vapor pressure [Pascals]
   Derived from the air temperature and measured relative humidity. Can be calculated
   using the IPW utility ``sat2vp`` or the SMRF function ``rh2vp``.

Precipitation [mm]
   Instantaneous precipitation with no negative values. If using a weighing precipitation
   gauge that outputs accumulated precipitation, the value must be converted.

Wind speed [meters per second]
   The measured wind speed at the surface. Typically an average value over the measurement
   interval.

Wind direction [degrees]
   The measured wind direction at the surface. Typically an average value over the measurement
   interval.

Cloud factor [None]
    The percentage between 0 and 1 of the incoming solar radiation that is obstructed by clouds.
    0 equates to no light and 1 equates to no clouds.  The cloud factor is derived from the
    measured solar radiation and the modeled clear sky solar radiation.  The modeled clear sky
    solar radiation can be calculated using the IPW utility ``twostream`` or the SMRF
    function ``model_solar``.


Input data in the configuration file
------------------------------------

There are two main sections in the configuration file that dictate which dataset is loaded. The
``[csv]`` section contains file paths to csv data and the ``[gridded]`` section contains
the information for gridded datasets like HRRR and WRF.

.. note::

    Only one section can be used at a time. If the simulation is using HRRR, then add the ``[gridded]``
    section and remove the ``[csv]`` section.

The data sections are closely tied to the ``[time]`` section as the ``start_date`` amd ``end_date`` must be
within the files provided. The ``time_step`` represents the time step to distribute the data (typically every hour)
and should match the input data time step.
