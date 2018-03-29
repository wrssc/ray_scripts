# Python scripts for RayStation treatment planning system

by Mark Geurts <mark.w.geurts@gmail.com>
<br>Copyright &copy; 2018, University of Wisconsin Board of Regents

## Description

This repository contains a collection of independent python scripts that were developed 
for use with the [RayStation treatment planning system](https://www.raysearchlabs.com/raystation/). While most scripts are intended to
be loaded into RayStation, others provide ancillary functions such as [CreateReferenceCT.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateReferenceCT.py),
which creates a homogeneous phantom.

## Installation

This repository is set up so that only one script, [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py), actually needs to be imported into RayStation. After downloading a copy of this repository to a location accessible by the RayStation servers, import [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) and change the variable `repo` to point to the path of the repository. You can then either leave the `module` variable empty, in which case all scripts will be loaded, or set `module` to be a single subfolder within the repository. Finally, set the script name and module accordingly in RayStation and validate the script. Then, when executed, [ScriptSelector.py](https://github.com/mwgeurts/ray_scripts/blob/master/ScriptSelector.py) will search the provided path for all available Python files, and display a list of all scripts to the user. Clicking on a script will execute it.

To use [CreateReferenceCT.py](https://github.com/mwgeurts/ray_scripts/blob/master/general/CreateReferenceCT.py), you will need to install the 
[pydicom](http://pydicom.readthedocs.io/en/stable/getting_started.html) and 
[numpy](https://scipy.org/install.html) packages. Copies of both packages are included as
submodules within this repository. 

## Usage and Documentation

The following list summarizes each script within this repository. Refer to the preamble 
comments within each script for script-specific documentation.

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
