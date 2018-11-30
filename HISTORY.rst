=======
History
=======

0.1.0 (2017-08-18)
------------------

* Create package

0.2.0 (2018-01-04)
------------------

* Incorporation scripts used to run SMRF and iSnobal
* Creation of rigid directory structure
* Creation of entire framework
* Incorporation of PySnobal package
* Automated run procedure

0.3.0 (2018-01-10)
------------------

* General cleanup
* Documentation

0.4.0 (2018-05-03)
------------------

* Put into docker package, continuous integration
* Conforming to Pep8 standards
* Improved restart procedure for iSnobal
* Improved gridded forecast ability
* Improved user configuration
* Fast user test cases and unit test capability
* Repeatable runs from station data with git version tracking


0.5.0 (2018-07-02)
------------------

* Inicheck integration
* SNOWAV interface established
* API Documentation


0.6.0 (2018-07-13)
------------------

* Added model state updating using lidar images
* Added a feature to enable the use of wet bulb for precip temp (mirroring SMRF)
* Automatically detecting domain parameters from topo file


0.7.0 (2018-08-13)
------------------

* Added unit tests that run on Travis CI and Coveralls
* Added LiDAR depth updating functionality to iPySnobal runs
* Merged iSnobal and PySnobal init file options in config


0.8.0 (2018-11-28)
------------------

* Daily run script with crash manual crash restart ability
* SNOWAV and dependencies added to Docker
* Automatic depth update difference file writing
* Daily run script for use with Airflow
