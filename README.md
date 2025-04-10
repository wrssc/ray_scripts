# Python scripts for RayStation treatment planning system
DHO_RayScripts

Python tools for the RayStation treatment planning system

Authors:Mark Geurts – mark.w.geurts@gmail.com Adam Bayliss – bayliss@humonc.wisc.eduCopyright © 2018–2025, University of Wisconsin Board of Regents

## 🧭 Overview

DHO_RayScripts is a modular collection of Python scripts designed to enhance and automate workflows in the RayStation treatment planning system.

Enables autoplan generation, structure-based optimization, goal scripting, QA automation, and DICOM integrity checking

Organized by clinical task and RayStation window context (e.g., General, Structure Definition, QA Preparation)

Supports centralized launch via a ScriptSelector GUI

Includes internal tools used in production at the University of Wisconsin Cancer Center
The application of these scripts varies from efficient creation of QA plans to automated planning and plan checks. This repository is actively being developed, so please see our [Projects](../../projects) page for more information on what is coming soon!

## 🚀 Highlighted Capabilities

Feature

Description

AutoPlan

Protocol-driven end-to-end plan creation using XML-based templates

Goal/Objective Automation

Relative goal scaling (e.g., V95% Rx > 95%) not supported natively in RayStation

BeaVIS

Automated beamset-level QA system with physics and dosimetry review integration

DITTO

Cross-platform DICOM integrity checking (e.g., RayStation ↔ Aria) with UID, grid, and structural validation

Electron QA Planning

Monte Carlo vs Mobius QA phantom plan generator for e- QA

Structure Generation

Helper tool for building derived planning rings, standoffs, uniform dose zones

Export Tools

GUI menu for sending DICOM data to preconfigured systems (iDMS, Mobius, MIM)

Plan Review PDFs

Auto-generates structured checklists and physics review documents

## 📁 Repository Structure

DHO_RayScripts/
├── general/                # Core user-facing scripts callable from any RayStation window
├── helper_scripts/        # GUI tools and support scripts for clinicians and physicists
├── structure_definition/  # Scripts for Structure Definition module context
├── development/           # Scripts undergoing clinical testing
├── library/               # Shared utility modules (optimization, goals, export, etc.)
├── protocols/             # XML templates for automated planning workflows
├── PlanReview/            # Automated QA engine and PDF/report tools (BeaVIS)
├── DITTO/                 # Placeholder – full toolset for DICOM integrity checking
├── legacy/                # Deprecated or historical scripts
├── testing/               # Unstable or prototype code
├── ScriptSelector.py      # Entry-point script used to load and execute modules
└── README.md              # You're here

## 🧑‍💻 Usage

Preferred: Use the Script Selector Interface

The ScriptSelector.py script should be loaded into RayStation (via Script Import Tool) as either a:

General script (available in all modules)

Module-specific script (e.g., only available in Structure Definition)

You configure:

local – path to local script repository (or leave blank to use GitHub)

module – name of subdirectory to list scripts from (e.g., "general")

library – shared code directory to append to path (typically "library")

This is the recommended mode as it sets up logging, UI context, and syncs the latest scripts from GitHub.
Full guide to installation is avaiable on the the [Installation](../../wiki/dependencies) wiki page. This repository is set up so that only one "selector" script, [ScriptSelector.py](../../blob/master/ScriptSelector.py), actually needs to be imported into RayStation. Once imported, you can change how scripts are loaded through two variables specified at the top of the script: `local` and `module`. 

If `local` is left empty, each time the selector is called from RayStation it will use the [requests](http://docs.python-requests.org/en/master/) library to connect to this repository and prompt the user to select a branch to run scripts from (the [master](../../) branch contains all validated Production versions, but other feature development branches can be selected to test new features). After selecting a branch, the selector will download all scripts and prompt the user with a list to select one to execute. Alternatively, users can enter a local directory into the `local` variable that contains a local copy of this repository. Instead of downloading a fresh copy each time from GitHub, the local scripts will be displayed to the user for execution.

The `module` variable is used to only show scripts from a particular directory in this repository. For example, setting `module = 'general'` will only show the [general scripts](general) to the user. In this way, multiple copies of [ScriptSelector.py](../../blob/master/ScriptSelector.py) can be loaded into RayStation with each pointing to a single focus of scripts.

Packages not included as part of the standard library have been included as submodules in this repository, and should be installed from these references or [pip](https://packaging.python.org/tutorials/installing-packages/) during RayStation setup. A description of each package and how it is used is available on the [Dependencies](../../wiki/dependencies) wiki page.

Optional: Run a Script Directly

Scripts may also be executed individually by loading them in RayStation:

# Inside RayStation script console
exec(open("create_goals.py").read())

Limitations:

Logging and environment setup may not be initialized

Requires correct manual setup of script paths and RayStation API context

Recommended only for testing or development

## 🧩 A La Carte Usage (Experimental Support)

Scripts like create_goals.py, AutoPlan.py, and physics_review.py can be run as standalone tools if:

The corresponding dependencies from library/ are also downloaded

Scripts are executed inside the RayStation scripting environment

A future tool will allow fetching just a script + its dependencies automatically.

❗ Note: RayStation scripts cannot be run from a regular Python shell. They require execution from within the RayStation UI.

## 📚 Documentation and Support

Detailed documentation and clinical workflow examples are available in the Wiki:

Installation Guide

AutoPlan XML Protocols

Goal/Objectives System

Plan Review (BeaVIS)

DITTO Usage (placeholder)

Script Selector Setup

Please submit issues, suggestions, or questions via GitHub Issues.

## 🤝 Contributing

Pull requests are welcome. For new scripts, please:

Follow the clinical naming conventions

Include a docstring header with author, version, license, and description

Minimize external dependencies unless essential

Add tests or validation notes where appropriate

See the Contributing Guidelines (placeholder) for more details.

📄 License

This project is licensed under the GNU GPL v3.0. See the LICENSE file for details.

DHO_RayScripts is actively maintained and used clinically at the University of Wisconsin. We believe in sharing practical, production-ready scripting workflows to improve safety, efficiency, and reproducibility in radiation oncology planning.

#
## Documentation and Help

With the exception of the library folder, each python script in this repository performs a standalone function in RayStation.  See the [wiki](../../wiki) for information on what each script does, how it is used, and to see troubleshooting tips. If you experience issues with a script or have improvements to suggest please submit an [Issue](../../issues), otherwise contact the script author for questions or feedback.

## License

Released under the GNU GPL v3.0 License. See the [LICENSE](LICENSE) file for further details.
