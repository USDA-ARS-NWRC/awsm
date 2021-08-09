AWSM Basin Setup
================

All components will be described using docker containers such that the generation
of the necessary files is reproducible. Note that exact docker versions will be
specified throughout the document but can be updated to different versions.

The initial set up is performed using the package `basin_setup`_. `basin_setup`_ requires a DEM and it
the `LANDFIRE`_ dataset (version 1.4.0) to fill in the vegetation layers and parameters required to run iSnobal.

.. _basin_setup: https://github.com/USDA-ARS-NWRC/basin_setup
.. _LANDFIRE: https://www.landfire.gov


``topo.nc`` file
----------------

The basin setup procdure creates a `topo.nc` that contains the following static layers:

1. Digital elevation model
2. Vegetation type
3. Vegetation height
4. Vegetation extinction coefficient
5. Vegetation optical transmissivity
6. Basin mask (optional)

All these layers are stored in a netCDF file, typically referred to the ``topo.nc`` file. More
information about the ``topo.nc`` file are in the SMRF documentation_ with advanced setup in 
:doc:`../user_guide/topo_veg`.

.. note::

    The ``topo.nc`` **must** have projection information. It's just good practice. Using
    ``basin_setup`` will ensure the projection is in the ``topo.nc`` which will come from
    the basin outline shapefile.


.. _documentation: https://smrf.readthedocs.io/en/latest/getting_started/create_topo.html


Creating the DEM
----------------

The DEM was obtained from the USGS National Elevation `dataset`_ at ~10-m (9.26-m) resolution.
The original tiles are provided in EPSG:4269 - NAD83 – Geographic projection. Download the necessary
tiles to cover the modeling domain. Merge the tiles in the native projection and resolution (EPSG 4269, 10m). 

.. _dataset: https://catalog.data.gov/dataset/usgs-national-elevation-dataset-ned

Optionally, crop the joined DEM
and resample to 50-m resolution and reproject to UTM coordinates (for example EPSG 32613, UTM 13N - WGS 84),
all of which is accomplished using a single ``gdalwarp`` instruction (also available in QGIS or similar ArcGIS
command). This will also be performed within the ``generate_topo`` command.

.. note::
    Beware of using Nearest Neighbor interpolation as it can create artifacts in the resulting DEM. Use average,
    bilinear or cubic interpolation.

A sample ``gdalwarp`` command for the Gunnison in Colorado. This will resample to 50-m grid resolution and
reproject from EPSG:4269 to EPSG:32613:

.. code:: bash

    gdalwarp \
        -s_srs EPSG:4269 \
        -t_srs EPSG:32613 \
        -tr 50.0 50.0 \
        -r bilinear \
        -te 302500.0 4263100.0 388350.0 4328700.0 \
        -te_srs EPSG:32613 \
        -of GTiff \
        in_dem_10_meters.tif out_dem_50_meters.tif


Pour Point File
---------------

Once the final DEM is generated, the basin is delineated using one or multiple pour points to define the
basin and any sub-basins. The pour points are contained within a ``.bna`` file that indicates the pour
point locations.

The format for the ``.bna`` file:

.. code:: sh

    "Point code", "Another point code", 1
    <UTM X>, <UTM Y>

An example for the Gunnison that will delineate multiple sub-basins with the basin outlet at "TRAC2":

.. code:: sh

    "TRAC2","TRAC2H_F",1
    364060.6510282378,4302483.0984167568
    "TPIC2","TPIC2L_F",1
    360137.0765313815,4297634.3167137895
    "ALTC2","ALTC2L_F",1
    339502.3149144283,4281186.4048871947
    "ALEC2","ALEC2H_F",1
    339065.7024648183,4281297.3988735778
    "OHOC2","OHOC2H_F",1
    331764.4055900126,4272796.4096229207
    "GUSC2","GUSC2L_F",1
    330122.1191776489,4267747.993258521
    

Delineate Basin, Generate Topo
------------------------------

The basin delineation and creation of the ``topo.nc`` file is done with the docker version
of ``basin_setup``. A ``docker-compose.yml`` file aids the composition of the docker commands
and simplifies mounting data volumes to the docker image. The following ``docker-compose.yml``
file contains two services, ``delineate`` runs the delineation routine and ``generate_topo`` creates
the ``topo.nc``.

.. code:: yml

    version: '3'

    services:
        delineate:
            image: usdaarsnwrc/basin_setup:0.15
            volumes:
                - ./topo:/data
            entrypoint: delineate

        generate_topo:
            image: usdaarsnwrc/basin_setup:0.15
            volumes:
               - ./topo:/data/topo
               - ./veg_data:/data/veg_data
            entrypoint: generate_topo


With the DEM tiff file ``out_dem_50_meters.tif`` and the ``.bna`` file, run ``delineate``
with the ``basin_setup`` docker image. This will delineate the basin with `TauDEM`_ and
create sub-basins for each pour point.

.. _TauDEM: https://hydrology.usu.edu/taudem/taudem5/index.html

.. code:: bash

    docker-compose run delineate \
        -p pour_points.bna \
        -d out_dem_50_meters.tif \
        -t 100000 \
        -n 2 \
        --debug \
        --streamflow

The ``delineate`` command will create a file in ``./topo/delineation/basin_outline.shp`` which
will contain the delineated basin. Open the shape file and ensure that the basin
delineation performed as expected.

Next, create the topo with ``generate_topo``. The LANDFIRE version 1.4.0
dataset is quite large (~3GB) and must be downloaded prior. Ensure that the
LANDFIRE dataset is in the ``./veg_data`` folder and unzipped. ``generate_topo`` uses a
configuration file to specify all the required parameters to run. See the
`CoreConfig`_ for options and the `sample configuration files`_.

.. _CoreConfig: https://github.com/USDA-ARS-NWRC/basin_setup/blob/main/basin_setup/CoreConfig.ini
.. _sample configuration files: https://github.com/USDA-ARS-NWRC/basin_setup/blob/main/tests/Lakes/config.ini

.. code:: bash

    docker-compose run generate_topo /data/topo/config.ini

    
View ``topo.nc``
----------------

Open the ``topo.nc`` in your favorite netcdf viewer or GIS program. Ensure all the layers
have been generated. The example below shows the Lakes basin in the AWSM tests.

.. note::

    The global attributes for the ``topo.nc`` include the version of ``basin_setup``
    and the command used to create the file for reproducibility.


.. code:: bash

    $ ncdump -h awsm/tests/basins/Lakes/topo/topo.nc 

    $ netcdf topo {
        dimensions:
                y = 168 ;
                x = 156 ;
        variables:
                float y(y) ;
                        y:least_significant_digit = 3LL ;
                        y:description = "UTM, north south" ;
                        y:long_name = "y coordinate" ;
                        y:units = "meters" ;
                        y:standard_name = "projection_y_coordinate" ;
                float x(x) ;
                        x:least_significant_digit = 3LL ;
                        x:description = "UTM, east west" ;
                        x:long_name = "x coordinate" ;
                        x:units = "meters" ;
                        x:standard_name = "projection_x_coordinate" ;
                float dem(y, x) ;
                        dem:least_significant_digit = 3LL ;
                        dem:long_name = "dem" ;
                        dem:grid_mapping = "projection" ;
                ubyte mask(y, x) ;
                        mask:least_significant_digit = 3LL ;
                        mask:long_name = "Lakes Basin" ;
                        mask:grid_mapping = "projection" ;
                ushort veg_type(y, x) ;
                        veg_type:least_significant_digit = 3LL ;
                        veg_type:long_name = "vegetation type" ;
                        veg_type:grid_mapping = "projection" ;
                float veg_height(y, x) ;
                        veg_height:least_significant_digit = 3LL ;
                        veg_height:long_name = "vegetation height" ;
                        veg_height:grid_mapping = "projection" ;
                float veg_k(y, x) ;
                        veg_k:least_significant_digit = 4LL ;
                        veg_k:long_name = "vegetation k" ;
                        veg_k:grid_mapping = "projection" ;
                float veg_tau(y, x) ;
                        veg_tau:least_significant_digit = 4LL ;
                        veg_tau:long_name = "vegetation tau" ;
                        veg_tau:grid_mapping = "projection" ;
                char projection ;
                        projection:grid_mapping_name = "universal_transverse_mercator" ;
                        projection:utm_zone_number = 11. ;
                        projection:semi_major_axis = 6378137. ;
                        projection:inverse_flattening = 298.257223563 ;
                        projection:spatial_ref = "PROJCS[\"WGS84/UTMzone11N\",\nGEOGCS[\"WGS84\",\nDATUM[\"WGS_1984\",\nSPHEROID[\"WGS84\",6378137,298.257223563,\nAUTHORITY[\"EPSG\",\"7030\"]],\nAUTHORITY[\"EPSG\",\"6326\"]],\nPRIMEM[\"Greenwich\",0,\nAUTHORITY[\"EPSG\",\"8901\"]],\nUNIT[\"degree\",0.01745329251994328,\nAUTHORITY[\"EPSG\",\"9122\"]],\nAUTHORITY[\"EPSG\",\"4326\"]],\nUNIT[\"metre\",1,\nAUTHORITY[\"EPSG\",\"9001\"]],\nPROJECTION[\"Transverse_Mercator\"],\nPARAMETER[\"latitude_of_origin\",0],\nPARAMETER[\"central_meridian\",-117],\nPARAMETER[\"scale_factor\",0.9996],\nPARAMETER[\"false_easting\",500000],\nPARAMETER[\"false_northing\",0],\nAUTHORITY[\"EPSG\",\"32611\"],\nAXIS[\"Easting\",EAST],\nAXIS[\"Northing\",NORTH]]" ;
                        projection:_CoordinateTransformType = "Projection" ;
                        projection:_CoordinateAxisTypes = "GeoX GeoY" ;

        // global attributes:
                        :last_modified = "[2019-12-31 21:33:38] Data added or updated" ;
                        string :Conventions = "CF-1.6" ;
                        string :dateCreated = "2019-12-31 21:33:38" ;
                        string :Title = "Topographic Images for SMRF/AWSM" ;
                        string :history = "[2019-12-31 21:33:38] Create netCDF4 file using Basin Setup v0.13.0" ;
                        string :institution = "USDA Agricultural Research Service, Northwest Watershed Research Center" ;
                        string :generation_command = "/usr/local/bin/basin_setup -f delineation/basin_outline.shp -bn Lakes Basin -dm lakes_dem_UTM11_WGS84.tif -d /Downloads -ex 319975 4158253 327755 4166675" ;
        }
