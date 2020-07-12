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

from connect import CompositeAction, get_current, await_user_input

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
    ## R: Suggestion: Consider extending the SeriesDescription search for JC/East
    ##      These are the UW standard I believe. Are they the same for East and JC?
    if "CHEST_MIBH" in series_dict.keys():
        text_DIBH.set("CHEST_MIBH")
    if "CHEST_FREE_BREATHING" in series_dict.keys():
        text_FB.set("CHEST_FREE_BREATHING")

    # Add buttons
    frm_buttons = Frame()
    frm_buttons.pack(fill=X, ipadx=5, ipady=5)

    # Create the "Continue" button and pack it to the
    # right side of `frm_buttons`
    btn_continue = Button(master=frm_buttons, text="Continue", command=continue_func)
    btn_continue.pack(side=RIGHT, padx=10, ipadx=10)

    # Create the "Cancel" button and pack it to the
    # right side of `frm_buttons`
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
    ## R: ChangeRequest:
    ##      len(case.Examinations) is undefined as it is an unsized object, in the past I have
    ## relied on for loops to determine
    ##      the size of RayStation ScriptObjects. I note that both exam names are stores as private
    ## variables _CT 1, and _CT 2
    ##      for example. But I do not know how to make use of this property
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
    ## R: Suggestion:
    ##      An alternative function is available in StructureOperations, and would
    ## consolidate lines 215 to 229
    ##      external_roi = StructureOperations.find_types(case, "External")
    ##      if not external_roi:
    roi_type_list = [roi.Type for roi in case.PatientModel.RegionsOfInterest]
    if "External" not in roi_type_list:
        logging.error("No ROI of type 'External' found.")
        messagebox.showerror(
            "External Structure Error",
            "The script requires that a structure (usually External or ExternalClean) be set as "
            "external in RayStation.",
        )
        exit()
    ## R: Discussion:
    ##      I have been using roi_external to indicate object_attribute, but I am fine with
    ##  attribute_object too.
    # The name of the ROI of type External should have "External" in the name
    external_roi = None
    for roi in case.PatientModel.RegionsOfInterest:
        if roi.Type == "External":
            external_roi = roi
            break
    if "External" not in external_roi.Name:
        logging.warning(
            "ROI of type 'External' is called {}, which deviates from standard naming "
            "conventions.".format(external_roi.Name)
        )
        messagebox.showwarning(
            "External Structure Warning",
            "The ROI of type 'External' is called {}. Typically, it is called 'External' or "
            "'ExternalClean'.".format(external_roi.Name),
        )

    with CompositeAction("Rename DIBH and free-breathing examinations"):
        (DIBH_exam, FB_exam) = get_DIBH_and_FB_exams(case)

        logging.info("Renaming exam {} to DIBH".format(DIBH_exam.Name))
        DIBH_exam.Name = "DIBH"
        logging.info("Renaming exam {} to Free-breathing".format(FB_exam.Name))
        FB_exam.Name = "Free-breathing"
    ## R: ChangeRequest:
    ##      The following statement ensures that any object of type External,
    ##      regardless of the exam on which is belongs (DIBH or FB) will be renamed
    ##      is that the correct behavior? If a user has incorrectly drawn the external
    ##      on the free-breathing, or on both scans, the resulting label will be incorrect.
    ##
    ##      I confirmed the result by defining an External Contour geometry on the
    ##      FB scan. The script changes the name of the External ROI for both
    ##      ROI geometries to "External_DIBH"
    ##
    ##      You may wish to add the following:
    ##      case.PatientModel.StructureSets['Free-breathing']\
    ##          .RoiGeometries['External_DIBH'].DeleteGeometry()
    with CompositeAction("Rename External on DIBH scan to 'External_DIBH'"):
        logging.info("Renaming the ROI of type 'External' to 'DIBH'.")
        external_roi.Name = "External_DIBH"

    """
    ui = get_current("ui")
    menu_item = ui.TitleBar.MenuItem
    menu_item["Patient Modeling"].Click()
    menu_item["Patient Modeling"].Popup.MenuItem["Image Registration"].Click()
    tab_item = ui.TabControl_ToolBar.TabItem
    tab_item["Fusion"].Select()

    messagebox.showinfo(
        title="Please review fusion",
        message="Please review fusion.",
    )
    """

    with CompositeAction("Create External_FB on Free-breathing Image Set"):

        roi_names = [roi.Name for roi in case.PatientModel.RegionsOfInterest]
        ## R: Suggestion:
        ##      I have been trying to think of the "info" debugging channel as something a reviewer
        ##      might want to see, and crafted my message accordingly. As such, it may help to
        ##      change the note to something like: External_FB existed, it was deleted
        if "External_FB" in roi_names:
            logging.info(
                "A region of interest called External_FB already exists. It will be deleted"
            )
            messagebox.showinfo(
                title="External_FB already exists ",
                message="A region of interest called External_FB already exists. It will be deleted",
            )
            case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

        logging.info("Creating an ROI called 'External_FB")
        ## R: Comment and potential Revision Request:
        ##      I note that the attempt is made to specify the ROI type as "External" for the ROI External_FB
        ##      This will not work as the "External" type can only belong to one ROI in the plan. I am unsure
        ##      of how this affects workflow, but if the "Body" type is required in Eclipse, or the AlignRT system
        ##      no structure of type "External" will be delineated on the Free-Breathing scan.
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
        external_roi.SetAsExternal()

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
        clean(case)
    else:
        logging.info("User accepted contours. Script completed.")


def clean(case):
    """Undo all of the actions done by create_external_fb()

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    # Delete External_FB
    with CompositeAction("Delete External_FB"):
        logging.info("Deleting External_FB")
        case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

    # Undo renaming of external DIBH
    ## R: Suggestion
    ##      Consider storing the original external name and passing it in as a parameter
    ##      This will rename the original external "External" regardless of its original name
    ##      say "ExternalClean." This could have implications for later scripts that assume
    ##      "External" is system drawn, and "ExternalClean" is modified, cleaned system-drawn or
    ##      user-drawn (to touch up algorithmic error, like lopping of the patient's ears).
    with CompositeAction("Reverse rename of External_DIBH"):
        logging.info("Renaming 'External_DIBH' to 'External'")
        case.PatientModel.RegionsOfInterest["External_DIBH"].Name = "External"

    # Undo renaming of examinations
    ## R: Suggestion
    ##      Same as above, sending original examination names in will be helpful
    ## or making the clean function
    ##      internal to main? to access the global variable names?
    with CompositeAction("Reverse rename of DIBH and free-breathing examinations"):
        logging.info("Renaming examinations to 'CT_1' and 'CT_2'")
        case.Examinations["DIBH"].Name = "CT 1"
        case.Examinations["Free-breathing"].Name = "CT 2"


def main():
    """The main function for this file"""

    logging.debug("Beginning execution of CreateExternalDIBHandFB.py in main()")
    case = get_current("Case")
    create_external_fb(case)


if __name__ == "__main__":
    main()
