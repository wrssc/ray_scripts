# Python scripts for RayStation treatment planning system

by Mark Geurts <mark.w.geurts@gmail.com> and Adam Bayliss <bayliss@humonc.wisc.edu>
<br>Copyright &copy; 2018, University of Wisconsin Board of Regents

## Description

This repository contains a collection of python scripts that were developed 
for use with the [RayStation treatment planning system](https://www.raysearchlabs.com/raystation/). The application of these scripts varies from efficient creation of QA plans to automated planning and plan checks. This repository is actively being developed, so please see our [Projects](../../projects) page for more information on what is coming soon!

## Installation

A full guide to installation is avaiable on the the [Installation](../../wiki/dependencies) wiki page. This repository is set up so that only one script, [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py), actually needs to be imported into RayStation. Once imported, you can change how scripts are loaded through two variables specified at the top of the script: `local` and `module`. If `local` is left empty, each time [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) is called from RayStation it will use the [requests](http://docs.python-requests.org/en/master/) library to connect to this repository and prompt the user to select a branch to run scripts from (the [master](../../) branch contains all validated Production versions, but other feature development branches can be selected to test new features). After selecting a branch, [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) will download all scripts and prompt the user with a list to select one to execute.

Alternatively, users can enter a local directory into the `local` variable in [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) that contains a local copy of this repository. Instead of downloading a fresh copy each time from GitHub, the local scripts will be displayed to the user for execution.

The `module` variable is used to only show scripts from a particular directory in this repository. For example, setting `module = 'general'` will only show the [general scripts](general) to the user. In this way, multiple copies of [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) can be loaded into RayStation with each pointing to a single focus of scripts.

Scripts in this repository make use of one or more of the following python packages:
[requests](http://docs.python-requests.org/en/master/), [pydicom](http://pydicom.readthedocs.io/en/stable/getting_started.html), and 
[numpy](https://scipy.org/install.html) packages. Copies of all are included as submodules within this repository. Refer to the [Dependencies](../../wiki/dependencies) wiki page for more details.

## Usage and Documentation

The following list summarizes each script within this repository as well as the RayStation module it is intended for. Refer to the docscring within each script and [wiki](../../wiki) for script-specific documentation.

| Module | Script | Description |
|--------|--------|-------------|
| General | [CreateMobius3DDLGPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateMobius3DDLGPlans.py) | Creates and exports a series of DLG test plans to send to Mobius3D for DLG offset optimization. |
| General | [CreateMobius3DValidationPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateMobius3DValidationPlans.py) | Creates and exports a series of simple validation plans for Mobius3D following [AAPM MPPG 5.a](https://doi.org/10.1120/jacmp.v16i5.5768) guidelines. |
| General | [CreateReferenceCT.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateReferenceCT.py) | Creates a homogeneous phantom CT, for use by other scripts in this repository. |
| General | [CreateWaterTankPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateWaterTankPlans.py) | Creates and exports a series of reference dose distributions for use with the [Water Tank TPS Comparison Tool](https://github.com/mwgeurts/water_tank). |
| General | [ImportRecalcDICOMPlans.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/ImportRecalcDICOMPlans.py) | Imports and re-calculates DICOM RT plans |

## License

Released under the GNU GPL v3.0 License. See the [LICENSE](LICENSE) file for further 
details.
