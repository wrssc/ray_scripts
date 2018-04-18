# Python scripts for RayStation treatment planning system

by Mark Geurts <mark.w.geurts@gmail.com> and Adam Bayliss <bayliss@humonc.wisc.edu>
<br>Copyright &copy; 2018, University of Wisconsin Board of Regents

## Description

This repository contains a collection of python scripts that were developed 
for use with the [RayStation treatment planning system](https://www.raysearchlabs.com/raystation/). The application of these scripts varies from efficient creation of QA plans to automated planning and plan checks. This repository is actively being developed, so please see our [Projects](../../projects) page for more information on what is coming soon!

## Installation and Use

A full guide to installation is avaiable on the the [Installation](../../wiki/dependencies) wiki page. This repository is set up so that only one "selector" script, [ScriptSelector.py](../../blob/master/ScriptSelector.py), actually needs to be imported into RayStation. Once imported, you can change how scripts are loaded through two variables specified at the top of the script: `local` and `module`. 

If `local` is left empty, each time the selector is called from RayStation it will use the [requests](http://docs.python-requests.org/en/master/) library to connect to this repository and prompt the user to select a branch to run scripts from (the [master](../../) branch contains all validated Production versions, but other feature development branches can be selected to test new features). After selecting a branch, the selector will download all scripts and prompt the user with a list to select one to execute. Alternatively, users can enter a local directory into the `local` variable that contains a local copy of this repository. Instead of downloading a fresh copy each time from GitHub, the local scripts will be displayed to the user for execution.

The `module` variable is used to only show scripts from a particular directory in this repository. For example, setting `module = 'general'` will only show the [general scripts](general) to the user. In this way, multiple copies of [ScriptSelector.py](../../blob/master/ScriptSelector.py) can be loaded into RayStation with each pointing to a single focus of scripts.

Packages not included as part of the standard library have been included as submodules in this repository, and should be installed from these references or [pip](https://packaging.python.org/tutorials/installing-packages/) during RayStation setup. A description of each package and how it is used is available on the [Dependencies](../../wiki/dependencies) wiki page.

## Documentation and Help

With the exception of the library folder, each python script in this repository performs a standalone function in RayStation.  See the [wiki](../../wiki) for information on what each script does, how it is used, and to see troubleshooting tips. If you experience issues with a script or have improvements to suggest please submit an [Issue](../../issues), otherwise contact the script author for questions or feedback.

## License

Released under the GNU GPL v3.0 License. See the [LICENSE](LICENSE) file for further details.
