# Automated Water Supply Model

[![Stable version](https://img.shields.io/badge/stable%20version-v0.10-blue)](https://img.shields.io/badge/stable%20version-v0.10-blue)
[![Pypi version](https://img.shields.io/pypi/v/awsm)](https://img.shields.io/pypi/v/awsm)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.898158.svg)](https://doi.org/10.5281/zenodo.898158)
[![Build Status](https://travis-ci.org/USDA-ARS-NWRC/awsm.svg?branch=main)](https://travis-ci.org/USDA-ARS-NWRC/awsm)
[![Coverage Status](https://coveralls.io/repos/github/USDA-ARS-NWRC/awsm/badge.svg?branch=main)](https://coveralls.io/github/USDA-ARS-NWRC/awsm?branch=main)
[![Maintainability](https://api.codeclimate.com/v1/badges/be953173a19947044e96/maintainability)](https://codeclimate.com/github/USDA-ARS-NWRC/awsm/maintainability)


Automated Water Supply Model (AWSM) was developed at the USDA Agricultural Research Service (ARS) in Boise, ID. AWSM was designed to streamline the work flow used by the ARS to forecast the water supply of multiple water basins. AWSM standardizes the steps needed to distribute weather station data with SMRF, run an energy and mass balance with iSnobal, and process the results, while maintaining the flexibility of each program.

![image](https://raw.githubusercontent.com/USDA-ARS-NWRC/awsm/master/docs/_static/ModelSystemOverview_new.png)

## Which version to use?

### Stable

The stable version of AWSM is currently `v0.10`. The code can be downloaded from the [releases](https://github.com/USDA-ARS-NWRC/awsm/releases) or can be found on the `release-0.10` [branch](https://github.com/USDA-ARS-NWRC/awsm/tree/release-0.10).

Best for:

- Applying the model in near real time
- Researchers wanting a ready to use model
- Those wanting the most stable and tested code

### Experimental

> :warning: **Use at your own risk!** While this contains the latest code, it is not guaranteed to work with the whole modeling framework.

The latest code on `main` contains all the latest development to AWSM. However, this must be used with caution as it can be under active development, may change at any time and is not guaranteed to work with the rest of the modeling framework at that moment. Once the code has been fully tested within the modeling framework, a new release will be created to signal a move to a stable version.

Best for:

- Those planning on developing with AWSM
- Model simulations require features only found in the latest code
- Okay with the possibility that AWSM doesn't work with the rest of the modeling system
