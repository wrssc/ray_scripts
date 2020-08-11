""" Create External DIBH and FB Contours
This script accomplishes the following tasks:
1. Renames CT datasets to "DIBH" and "Free-breathing".
2. Renames "External" to "External_DIBH" on the DIBH planning scan.
3. Creates an external contour on the free-breathing scan called "External_FB"
4. Copies "External_FB" to the DIBH planning scan.

This script was tested with:
* Patient: Example, OSMS
* MRN: 20170327DJJ
* RayStation: Launcher 8B SP2 - Test (Development Server)

* Patient: Example, OSMS
* MRN: 20170327DJJ
* RayStation: Launcher
* Title: Validation

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
__date__ = "2020-05-21"
__version__ = "1.0.0"
__status__ = "Development"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"
__reviewed__ = "Commit:2eb335d, 28May2020"
__raystation__ = "8.0 SP B"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2020, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current
import StructureOperations

try:  # for Python 3
    from tkinter import Tk, Frame, Label, StringVar, SUNKEN, X, Button, RIGHT
    from tkinter import messagebox
    from tkinter.ttk import Combobox
except ImportError:  # for Python 2
    from Tkinter import Tk, Frame, Label, StringVar, SUNKEN, X, Button, RIGHT
    import tkMessageBox as messagebox
    from ttk import Combobox
from sys import exit
import logging


def get_DIBH_and_FB_exams(case):
    """ Gets the names of the DIBH and Free-breathing exams from the user

    This scripts launches a tkinter window that allows the user to select
    a DIBH and Free-breathing scan, which are then returned.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    tuple of str, str
        A tuple containing the DIBH and free-breathing exam names, respectively

    """

    def continue_func():
        """ A function that determines if the user-selected values in the
        GUI are valid, which will allow the script to continue.
        """

        logging.debug("User pressed 'Continue'")
        if text_DIBH.get() == text_FB.get():
            logging.warning(
                "The DIBH image set and the free-breathing image set are the same: {}".format(
                    text_DIBH.get()
                )
            )
            messagebox.showerror(
                "Image Set Selection Error",
                "The DIBH image set and the free-breathing image set are the same. "
                "Please select a unique image set for each.",
            )
        else:
            # Destroy window and continue
            window.destroy()

    # Create a window to allow user to choose correct image set
    window = Tk()
    window.title("Select DIBH and Free-breathing Image Sets")
    select_form = Frame(relief=SUNKEN, borderwidth=3)
    select_form.pack()

    # Get dictionary of exams by Series Description:
    series_dict = {
        exam.GetAcquisitionDataFromDicom()["SeriesModule"]["SeriesDescription"]: exam
        for exam in case.Examinations
    }

    # Add DIBH selector
    text_DIBH = StringVar()
    lbl_DIBH = Label(master=select_form, text="DIBH Image Set:")
    cmb_DIBH = Combobox(
        master=select_form,
        width=50,
        values=list(series_dict.keys()),
        state="readonly",
        textvariable=text_DIBH,
    )
    lbl_DIBH.grid(row=0, column=0)
    cmb_DIBH.grid(row=0, column=1)

    # Add Free-breathing selector
    text_FB = StringVar()
    lbl_FB = Label(master=select_form, text="Free-breathing Image Set:")
    cmb_FB = Combobox(
        master=select_form,
        width=50,
        values=list(series_dict.keys()),
        state="readonly",
        textvariable=text_FB,
    )
    lbl_FB.grid(row=1, column=0)
    cmb_FB.grid(row=1, column=1)

    # Try to pre-populate correct image sets
    # These should work for patients scanned at UWHealth
    if "CHEST_MIBH" in series_dict.keys():
        text_DIBH.set("CHEST_MIBH")
    if "CHEST_FREE_BREATHING" in series_dict.keys():
        text_FB.set("CHEST_FREE_BREATHING")

    # These should work for patients scanned at Johnson Creek
    if "BREATH HOLD" in series_dict.keys():
        text_DIBH.set("BREATH HOLD")
    if "FREE BREATHE" in series_dict.keys():
        text_FB.set("FREE BREATHE")

    # Add buttons
    frm_buttons = Frame()
    frm_buttons.pack(fill=X, ipadx=5, ipady=5)

    # Create the "Continue" button and pack it to the
    # right side of `frm_buttons`
    btn_continue = Button(master=frm_buttons, text="Continue", command=continue_func)
    btn_continue.pack(side=RIGHT, padx=10, ipadx=10)

    # Create the "Cancel" button and pack it to the right side of "frm_buttons"
    btn_cancel = Button(master=frm_buttons, text="Cancel", command=exit)
    btn_cancel.pack(side=RIGHT, ipadx=10)
    window.mainloop()

    # Now that two examinations have been identified, we will verify that
    # the structure sets for these series are not approved:
    selected_exams = (series_dict[text_DIBH.get()], series_dict[text_FB.get()])
    selected_exam_names = [exam.Name for exam in selected_exams]
    for structure_set in case.PatientModel.StructureSets:
        for _ in structure_set.ApprovedStructureSets:
            # If you get to this point, there are approved structures in
            # this structure set.
            if structure_set.OnExamination.Name in selected_exam_names:
                logging.error(
                    "The structure set associated with {} is approved, which will prevent "
                    "successful execution of the script.".format(
                        structure_set.OnExamination.Name
                    )
                )
                messagebox.showerror(
                    "Approved Structure Set Error",
                    "The structure set associated with {} is approved, which will prevent "
                    "successful execution of the script.".format(
                        structure_set.OnExamination.Name,
                    ),
                )
                exit()

    return selected_exams


def create_external_fb(case):
    """ Creates External_FB and External_DIBH contours.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    # First, verify that the pre-requisites for the script are present

    # The case must have two or more image sets.
    # Note: case.Examination has type "connect.connect_cpython.PyScriptObjectCollection", and
    # len() is defined for this object.
    if len(case.Examinations) < 2:
        logging.error(
            "Number of examinations = {}. This script requires two more or image sets "
            "(one DIBH and one free-breathing).".format(case.Examinations)
        )
        messagebox.showerror(
            "Image Set Error",
            "This script requires two more or image sets (one DIBH and one free-breathing). "
            "Please import DIBH and free-breathing scans.",
        )
        exit()

    # The case must have a region of interest set to the "External" type
    roi_external = StructureOperations.find_types(case, "External")
    if not roi_external:
        logging.error("No ROI of type 'External' found.")
        messagebox.showerror(
            "External Structure Error",
            "The script requires that a structure (usually External or ExternalClean) be set as "
            "external in RayStation.",
        )
        exit()

    assert len(roi_external) == 1, "Found more than one structure of type External"
    roi_external = roi_external[0]

    # The name of the ROI of type External should have "External" in the name
    original_roi_external_name = roi_external.Name
    if "External" not in roi_external.Name:
        logging.warning(
            "ROI of type 'External' is called {}, which deviates from standard naming "
            "conventions.".format(roi_external.Name)
        )
        messagebox.showwarning(
            "External Structure Warning",
            "The ROI of type 'External' is called {}. Typically, it is called 'External' or "
            "'ExternalClean'.".format(roi_external.Name),
        )

    with CompositeAction("Rename DIBH and free-breathing examinations"):
        (DIBH_exam, FB_exam) = get_DIBH_and_FB_exams(case)

        original_DIBH_exam_name = DIBH_exam.Name
        logging.info("Renaming exam {} to DIBH".format(DIBH_exam.Name))
        DIBH_exam.Name = "DIBH"

        original_FB_exam_name = FB_exam.Name
        logging.info("Renaming exam {} to Free-breathing".format(FB_exam.Name))
        FB_exam.Name = "Free-breathing"

    with CompositeAction("Rename External on DIBH scan to 'External_DIBH'"):
        logging.info("Renaming the ROI of type 'External' to 'DIBH'.")
        roi_external.Name = "External_DIBH"
        # This action renames the External to External_DIBH on all examinations.
        # For clarity, let's delete the geometries that may exist on other examinations.
        # If the user wishes to have an external on another geometry for planning, they will
        # need to create it manually.
        for ss in case.PatientModel.StructureSets:
            if ss.OnExamination.Name != "DIBH":
                log_str = "Deleting geometry for External_DIBH on {}".format(
                    ss.OnExamination.Name
                )
                logging.info(log_str)
                ss.RoiGeometries["External_DIBH"].DeleteGeometry()

    with CompositeAction("Create External_FB on Free-breathing Image Set"):

        roi_names = [roi.Name for roi in case.PatientModel.RegionsOfInterest]
        if "External_FB" in roi_names:
            logging.info(
                "A region of interest called External_FB already existed. It was deleted"
            )
            messagebox.showinfo(
                title="External_FB already exists ",
                message="A region of interest called External_FB existed. It was deleted",
            )
            case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

        logging.info("Creating an ROI called 'External_FB")
        # We will temporarily designate this contour as the External type. Later, we will
        # explicitly set External_DIBH back to the External type.
        external_fb_roi = case.PatientModel.CreateRoi(
            Name="External_FB",
            Color="Green",
            Type="External",
            TissueName="",
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        logging.info(
            "Using CreateExternalGeometry on exam 'Free-breathing' to populate External_FB"
        )
        external_fb_roi.CreateExternalGeometry(
            Examination=case.Examinations["Free-breathing"], ThresholdLevel=-250
        )
        logging.info("Setting External_DIBH as the 'External' ROI.")
        roi_external.SetAsExternal()

    with CompositeAction("Copy External_FB to DIBH Image Set"):
        logging.info("Copying External_FB to the DIBH examination.")
        case.PatientModel.CopyRoiGeometries(
            SourceExamination=case.Examinations["Free-breathing"],
            TargetExaminationNames=["DIBH"],
            RoiNames=["External_FB"],
        )

    message_text = "The script has finished, please review the results\n"
    message_text += "If the External_FB and External_DIBH are acceptable, click OK.\n"
    message_text += (
        "If the contours don't look right, click Cancel and contact the POD.\n"
    )

    script_result_accepted = messagebox.askokcancel("Script has finished", message_text)

    if not script_result_accepted:
        logging.info("User rejected contours. Running clean() to undo changes.")
        clean(
            case,
            original_roi_external_name,
            original_DIBH_exam_name,
            original_FB_exam_name,
        )
    else:
        logging.info("User accepted contours. Script completed.")


def clean(
    case, original_roi_external_name, original_DIBH_exam_name, original_FB_exam_name
):
    """Undo all of the actions done by create_external_fb()

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    original_roi_external_name : str
        The original name for the external ROI.
    original_DIBH_exam_name : str
        The original name for the DIBH examination.
    original_FB_exam_name : str
        The original name for the FB examination.

    RETURNS
    -------
    None

    """

    # Delete External_FB
    with CompositeAction("Delete External_FB"):
        logging.info("Deleting External_FB")
        case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

    # Undo renaming of external DIBH
    with CompositeAction("Reverse rename of External_DIBH"):
        logging.info("Renaming 'External_DIBH' to 'External'")
        case.PatientModel.RegionsOfInterest[
            "External_DIBH"
        ].Name = original_roi_external_name

    # Undo renaming of examinations
    with CompositeAction("Reverse rename of DIBH and free-breathing examinations"):
        logging.info("Renaming examinations to original names")
        case.Examinations["DIBH"].Name = original_DIBH_exam_name
        case.Examinations["Free-breathing"].Name = original_FB_exam_name


def main():
    """The main function for this file"""

    print("Hi")
    logging.debug("Beginning execution of CreateExternalDIBHandFB.py in main()")
    case = get_current("Case")
    create_external_fb(case)


if __name__ == "__main__":
    main()
