""" CreateExternalDIBHandFB.py
This script accomplishes the following tasks:
1. Renames CT datasets to "DIBH" and "Free-breathing".
1. Renames "External" to "External_DIBH" on the DIBH planning scan.
2. Creates an external contour on the free-breathing scan called "External_FB"
3. Copies "External_FB" to the DIBH planning scan.

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
__reviewer__ = None
__reviewed__ = None
__raystation__ = "8.0 SP B"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2020, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current, await_user_input

try:  # for Python 3
    from tkinter import *
    from tkinter import messagebox
    from tkinter.ttk import *
except:  # for Python 2
    from Tkinter import *
    import tkMessageBox as messagebox
    from ttk import *
from sys import exit
import logging


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


def rename_examinations(case):
    """ Renames CT data sets to DIBH and Free-breathing

    This scripts launches a tkinter window that allows the user to select
    a DIBH and Free-breathing scan, which are then renamed, respectively,
    to "DIBH" and "Free-breathing".

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    def continue_func():
        """ A function that determines if the user-selected values in the
        GUI are valid, which will allow the script to continue.
        """

        if text_DIBH.get() == text_FB.get():
            messagebox.showerror(
                "Image Set Selection Error",
                "The DIBH image set and the free-breathing image set are the same. Please select a unique image set for each.",
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

    # Rename examinations
    series_dict[text_DIBH.get()].Name = "DIBH"
    series_dict[text_FB.get()].Name = "Free-breathing"


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
    if len(case.Examinations) < 2:
        messagebox.showerror(
            "Image Set Error",
            "This script requires two more or image sets (one DIBH and one free-breathing). Please import DIBH and free-breathing scans.",
        )
        exit()

    # The case must have a region of interest set to the "External" type
    roi_type_list = [roi.Type for roi in case.PatientModel.RegionsOfInterest]
    if "External" not in roi_type_list:
        messagebox.showerror(
            "External Structure Error",
            "The script requires that a structure (usually External or ExternalClean) be set as external in RayStation.",
        )
        exit()

    # The name of the ROI of type External should have "External" in the name
    external_roi = None
    for roi in case.PatientModel.RegionsOfInterest:
        if roi.Type == "External":
            external_roi = roi
            break
    if "External" not in external_roi.Name:
        messagebox.showwarning(
            "External Structure Warning",
            "The ROI of type 'External' is called {}. Typically, it is called 'External' or 'ExternalClean'.".format(
                external_roi.Name
            ),
        )
    

    with CompositeAction("Rename DIBH and free-breathing examinations"):
        rename_examinations(case)

    with CompositeAction("Rename External on DIBH scan to 'External_DIBH'"):
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
        if "External_FB" in roi_names:
            messagebox.showinfo(
                title="External_FB already exists ",
                message="A region of interest called External_FB already exists. It will be deleted",
            )
            case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

        external_fb_roi = case.PatientModel.CreateRoi(
            Name="External_FB",
            Color="Green",
            Type="External",
            TissueName="",
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        external_fb_roi.CreateExternalGeometry(
            Examination=case.Examinations["Free-breathing"], ThresholdLevel=-250
        )
        external_roi.SetAsExternal()

    with CompositeAction("Copy External_FB to DIBH Image Set"):
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
        clean(case)


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
        case.PatientModel.RegionsOfInterest["External_FB"].DeleteRoi()

    # Undo renaming of external DIBH
    with CompositeAction("Reverse rename of External_DIBH"):
        case.PatientModel.RegionsOfInterest["External_DIBH"].Name = "External"

    # Undo renaming of examinations
    with CompositeAction("Reverse rename of DIBH and free-breathing examinations"):
        case.Examinations["DIBH"].Name = "CT 1"
        case.Examinations["Free-breathing"].Name = "CT 2"


if __name__ == "__main__":

    case = get_current("Case")

    create_external_fb(case)
