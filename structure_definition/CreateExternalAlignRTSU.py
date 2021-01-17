""" Create Ext_AlignRT_SU for Prone AlignRT Setup

This script accomplishes the following tasks:
1. Creates a copy of the external contour called Ext_AlignRT_SU
2. Shifts Ext_AlignRT_SU anteriorly 10 cm

This script was tested with:
* Patient: ZZ_OSMS, Practice
* MRN: 20180717DJJ
* RayStation: Launcher
* Title: Validation

Version History:
0.1.0 Validation and Review
1.1.0 Update to RS 10A and Python 3

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

__author__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__date__ = "2021-01-14"
__version__ = "1.1.0"
__status__ = "Production"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"
__reviewed__ = None
__raystation__ = "10A SP1"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2020, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current
import StructureOperations

try:  # for Python 3
    from tkinter import messagebox
except ImportError:  # for Python 2
    import tkMessageBox as messagebox
from sys import exit
import logging


def create_external_alignrt_su(case, shift_size=10):
    """ Creates Ext_AlignRT_SU.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    shift_size: float
        The shift size, in cm, in the anterior direction (default is 10)

    RETURNS
    -------
    None

    """

    # This script is designed to be used for prone breast patients:
    exam = get_current("Examination")

    if exam.PatientPosition != "HFP":
        logging.error("Current exam in not in prone position. Exiting script.")
        message = (
            "The script requires a patient in the head-first prone position. "
            "The currently selected exam is not HFP. Exiting script."
        )
        messagebox.showerror("Patient Orientation Error", message)
        exit()

    with CompositeAction("Create Ext_AlignRT_SU"):

        # The case must have a region of interest set to the "External" type
        roi_external = StructureOperations.find_types(case, "External")
        if not roi_external:
            logging.error("No ROI of type 'External' found.")
            message = (
                "The script requires that a structure (usually External or ExternalClean)"
                "be set as External in RayStation."
            )
            messagebox.showerror("External Structure Error", message)
            exit()

        assert len(roi_external) == 1, "Found more than one structure of type External"
        roi_external_name = roi_external[0]

        logging.info("{} identified as external ROI".format(roi_external_name))

        # Create roi for shifted external
        ext_alignrt_su = case.PatientModel.CreateRoi(
            Name="Ext_AlignRT_SU",
            Color="Green",
            Type="Organ",
            TissueName="",
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        logging.info("Created Ext_AlignRT_SU")

        # Copy the external ROI into the shifted external:

        MarginSettings = {
            "Type": "Expand",
            "Superior": 0,
            "Inferior": 0,
            "Anterior": 0,
            "Posterior": 0,
            "Right": 0,
            "Left": 0,
        }
        ext_alignrt_su.SetMarginExpression(
            SourceRoiName=roi_external_name, MarginSettings=MarginSettings
        )
        ext_alignrt_su.UpdateDerivedGeometry(Examination=exam, Algorithm="Auto")

        logging.info("Copied {} into {}".format(roi_external_name, ext_alignrt_su.Name))

        # Finally, shift the contour. This shift direction will only work for HFP
        TransformationMatrix = {
            "M11": 1,
            "M12": 0,
            "M13": 0,
            "M14": 0,  # end row
            "M21": 0,
            "M22": 1,
            "M23": 0,
            "M24": -shift_size,  # end row
            "M31": 0,
            "M32": 0,
            "M33": 1,
            "M34": 0,  # end row
            "M41": 0,
            "M42": 0,
            "M43": 0,
            "M44": 1,  # end row
        }

        ext_alignrt_su.TransformROI3D(
            Examination=exam, TransformationMatrix=TransformationMatrix
        )
        logging.info(
            "Shifted {} anteriorly by {} cm".format(
                ext_alignrt_su.Name, str(shift_size)
            )
        )


def clean(case):
    """Undo all of the actions done by create_external_alignrt_su()

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    # Clean not developed at this time. If there is a problem with Ext_AlignRT_SU, it may be
    # manually deleted.
    pass


def main():
    """The main function for this file"""

    logging.debug("Beginning execution of CreateExternalAlignRTSetup.py in main()")
    case = get_current("Case")
    create_external_alignrt_su(case)


if __name__ == "__main__":
    main()
