# Python scripts for RayStation treatment planning system

by Mark Geurts <mark.w.geurts@gmail.com>
<br>Copyright &copy; 2018, University of Wisconsin Board of Regents

## Description

This repository contains a collection of independent python scripts that were developed 
for use with the RayStation treatment planning system. While most scripts are intended to
be loaded into RayStation, others provide ancillary functions such as CreateReferenceCT.py,
which creates a homogeneous phantom.

## Installation

All RayStation scripts can be imported into RayStation without any additional installation.
To use CreateReferenceCT, you will need to install the 
[pydicom](http://pydicom.readthedocs.io/en/stable/getting_started.html) and 
[numpy](https://scipy.org/install.html) packages. Copies of both packages are included as
submodules within this repository. 

## Usage and Documentation

The following list summarizes each script within this repository. Refer to the preamble 
comments within each script for script-specific documentation.

| Script | Description |
|--------|-------------|
| [CreateMobius3DDLGPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/CreateMobius3DDLGPlans.py) | Creates and exports a series of DLG test plans to send to Mobius3D for DLG offset optimization. |
| [CreateMobius3DValidationPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/CreateMobius3DValidationPlans.py) | Creates and exports a series of simple validation plans for Mobius3D following [AAPM MPPG 5.a](https://doi.org/10.1120/jacmp.v16i5.5768) guidelines. |
| [CreateReferenceCT.py](https://github.com/mwgeurts/ray_scripts/blob/master/CreateReferenceCT.py) | Creates a homogeneous phantom CT, for use by other scripts in this repository. |
| [CreateWaterTankPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/CreateWaterTankPlans.py) | Creates and exports a series of reference dose distributions for use with the [Water Tank TPS Comparison Tool](https://github.com/mwgeurts/water_tank). |

## License

Released under the GNU GPL v3.0 License. See the [LICENSE](LICENSE) file for further 
details.
