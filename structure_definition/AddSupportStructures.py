""" Automatically create and place support structures

Currently supported
* TrueBeam Couch
* TomoTherapy Couch
* Civco Breast Board (w/ and w/o Wingboard)

This script accomplishes the following tasks:
1. Asks used for desired support structures

Couches
1. Create and automatically drop a couch

Civco Incline Board
1. Create and automatically place Civco incline board base
2. Create and automatically place Civco incline board body
    (with user-supplied angle)
3. Create and automatically place Civco wingboard (with user-supplied index)

This script was tested with:
* Patient: INCLINE BOARD
* MRN: 20210713
* Case: 5
* RayStation: Launcher
* Title: Sandbox

Version History:
v0.1.0: First working edition

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
__date__ = "2021-09-14"
__version__ = "0.1.0"
__status__ = "Development"
__deprecated__ = False
__reviewer__ = None
__reviewed__ = None
__raystation__ = "10A SP1"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2021, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current
# from StructureOperations import exists_roi

import PySimpleGUI as sg
from sys import exit
import logging
import re

# GUI Settings
DISPLAY_DURATION_IN_MS = 3000

# Structure template defaults
COUCH_SUPPORT_STRUCTURE_TEMPLATE = "UW Support Structures"
COUCH_SUPPORT_STRUCTURE_EXAMINATION = "CT 1"
COUCH_SOURCE_ROI_NAMES = {
    "TrueBeam": "Couch",
}



# Magic numbers for shifts
COUCH_SHIFT = [0, 6.8, 0]
INCLINE_BASE_SHIFT = [0, 6.9, 0]

CIVCO_INCLINE_BOARD_ANGLES = {
    'Flat': 0,
    '5 deg': 5,
    '7.5 deg': 7.5,
    '10 deg': 10,
    '12.5 deg': 12.5,
    '15 deg': 15,
    '17.5 deg': 17.5,
    '20 deg': 20,
    '22.5 deg': 22.5,
    '25 deg': 25,
}


def get_support_structures_GUI(
    examination,
):

    support_structure_values = None

    sg.ChangeLookAndFeel('DarkAmber')

    layout = [
        [
            sg.Text(
                'Support Structure Selection',
                size=(30, 1),
                justification='center',
                font=("Helvetica", 25),
                relief=sg.RELIEF_RIDGE
            ),
        ],
        [
            sg.Text(
                f'Please select support structures for examination "{examination.Name}"'
            )
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Radio(
                            'TrueBeam',
                            "RADIOCOUCH",
                            default=True,
                            size=(10,1),
                            key="-COUCH TRUEBEAM-"
                        )
                    ],
                    [
                        sg.Radio(
                            'TomoTherapy',
                            "RADIOCOUCH",
                            size=(10,1),
                            key="-COUCH TOMO-"
                        )
                    ],
                                        [
                        sg.Radio(
                            'None',
                            "RADIOCOUCH",
                            size=(10,1),
                            key="-COUCH NONE-"
                        )
                    ],
                ],
                title='Treatment Table',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a treatment table',
            ),
        ],
        [
            sg.Checkbox(
                'Use Civco Incline Breast Board',
                enable_events=True,
                key="-USE CIVCO-"
            )
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Text('Incline Angle'),
                        sg.Combo(
                            list(CIVCO_INCLINE_BOARD_ANGLES.keys()),
                            readonly=True,
                            default_value="7.5 deg",
                            key='-INCLINE ANGLE-'
                        )
                    ],
                    [
                        sg.Checkbox(
                            'Use Wingboard',
                            enable_events=True,
                            key="-USE WINGBOARD-"
                        )
                    ],
                    [
                        sg.Frame(
                            layout=[
                                [
                                    sg.Text('Wingboard Index'),
                                    sg.Slider(
                                        range=(0, 75),
                                        orientation='h',
                                        size=(34, 20),
                                        default_value=50,
                                        key="-WINGBOARD INDEX-",
                                    )
                                ]
                            ],
                            title='Wingboard Options',
                            relief=sg.RELIEF_SUNKEN,
                            tooltip='Select a wingboard position',
                            visible=False,
                            key="-FRAME WINGBOARD-",
                        )
                    ],
                ],
                title='Civco Incline Breast Board Options',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a breast board options',
                visible=False,
                key="-FRAME CIVCO-",
            ),
        ],
        [
            sg.Submit(tooltip='Click to submit this window'),
            sg.Cancel()
        ]
    ]

    civco_visible, wingboard_visible = False, False

    window = sg.Window(
        'Support Structure Selection',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Submit":
            support_structure_values = values
            break
        elif event.startswith('-USE CIVCO-'):
            civco_visible = not civco_visible
            window['-FRAME CIVCO-'].update(visible=civco_visible)

        elif event.startswith('-USE WINGBOARD-'):
            wingboard_visible = not wingboard_visible
            window['-FRAME WINGBOARD-'].update(visible=wingboard_visible)

    window.close()

    return support_structure_values


def exists_roi(case, rois, return_exists=False):
    """See if rois is in the list
    If return_exists is True return the names of the existing rois,
    If it is False, return a boolean list of each structure's existence
    """
    if type(rois) is not list:
        rois = [rois]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    roi_exists = []

    for r in rois:
        pattern = r"^" + r + "$"
        if any(
                re.match(pattern, current_roi, re.IGNORECASE)
                for current_roi in defined_rois
        ):
            if return_exists:
                roi_exists.append(r)
            else:
                roi_exists.append(True)
        else:
            if not return_exists:
                roi_exists.append(False)

    return roi_exists


def deploy_couch_model(
        case,
        support_structure_template="UW Support Structures",
        support_structures_examination="CT 1",
        source_roi_name='Couch'):
    """ Deploys the TrueBeam couch

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    support_structure_template: str
        The name of the support structure template in RayStation
        (default is "UW Support Structures")
    support_structures_examination: str
        The name of the examination associated with support_structure_template
        from which you will load the source ROIs (default is "CT 1")
    source_roi_names : list of str
        The names of the ROIs from support_structures_examination that you wish
        to load (default is ["Couch"]

    RETURNS
    -------
    None

    """

    # This script is designed to be used for HFS patients:
    examination = get_current("Examination")

    if examination.PatientPosition != "HFS":
        logging.error("Current exam in not in HFS position. Exiting script.")
        message = (
            "The script requires a patient in the head-first supine position. "
            "The currently selected exam is not HFS. Exiting script."
        )
        sg.popup_error(message, title="Patient Orientation Error")
        exit()

    with CompositeAction("Drop TrueBeam Couch"):

        # Load the source template for the couch structure:
        patient_db = get_current("PatientDB")
        try:
            support_template = patient_db.LoadTemplatePatientModel(
                templateName=support_structure_template,
                lockMode='Read'
            )
        except:

            message = (
                "The script attempted to load a support_structure_template "
                f"called {support_structure_template}. This was not successful. "
                "Verify that a structure template with this name exists. "
                "Exiting script."
            )
            logging.error(message)
            sg.popup_error(message, title="Structure Template Error")
            exit()

        # Check for Couch already in plan
        if exists_roi(case, source_roi_name):
            message = (
                f"A structure called {source_roi_name} already exists. "
                f"Its geometry will be cleared on examination {examination.Name}"
            )
            logging.info(message)
            sg.popup_notify(
                message,
                title="Table structure will be cleared",
                display_duration_in_ms=DISPLAY_DURATION_IN_MS
            )

            case.PatientModel.StructureSets[examination.Name] \
                .RoiGeometries[source_roi_name].DeleteGeometry()

        # Add the TrueBeam Couch
        case.PatientModel.CreateStructuresFromTemplate(
            SourceTemplate=support_template,
            SourceExaminationName=support_structures_examination,
            SourceRoiNames=[source_roi_name],
            SourcePoiNames=[],
            AssociateStructuresByName=True,
            TargetExamination=examination,
            InitializationOption='AlignImageCenters'
        )
        logging.info("Successfully dropped the TrueBeam Couch")

    with CompositeAction("Shift TrueBeam Couch"):

        couch = case.PatientModel.StructureSets[examination.Name].RoiGeometries[source_roi_name]

        top_of_couch = couch.GetBoundingBox()[0]["y"]
        TransformationMatrix = {
            'M11': 1, 'M12': 0, 'M13': 0, 'M14': -COUCH_SHIFT[0],
            'M21': 0, 'M22': 1, 'M23': 0, 'M24': -(top_of_couch+COUCH_SHIFT[1]),
            'M31': 0, 'M32': 0, 'M33': 1, 'M34': -COUCH_SHIFT[2],
            'M41': 0, 'M42': 0, 'M43': 0, 'M44': 1
            }
        couch.OfRoi.TransformROI3D(
            Examination=examination,
            TransformationMatrix=TransformationMatrix
        )
        logging.info("Successfully translated the TrueBeam Couch")

    with CompositeAction("Extend Table Longitudinally"):

        image_bb = examination.Series[0].ImageStack.GetBoundingBox()
        extent_inf = image_bb[0]["z"]
        extent_sub = image_bb[1]["z"]

        while couch.GetBoundingBox()[0]["z"] > extent_inf:
            MarginSettings = {
                'Type': "Expand",
                'Superior': 0,
                'Inferior': 15,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
                }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=source_roi_name,
                MarginSettings=MarginSettings)

        logging.info("Successfully extended the TrueBeam Couch inferiorly")

        while couch.GetBoundingBox()[1]["z"] < extent_sub:
            MarginSettings = {
                'Type': "Expand",
                'Superior': 15,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
                }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=source_roi_name,
                MarginSettings=MarginSettings
            )
        logging.info("Successfully extended the TrueBeam Couch superiorly")

        # Perform one final contraction to match image boundaries
        contract_inf =  extent_inf - couch.GetBoundingBox()[0]["z"]
        contract_sup =  couch.GetBoundingBox()[1]["z"] - extent_sub

        MarginSettings = {
            'Type': "Contract",
            'Superior': contract_sup,
            'Inferior': contract_inf,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
            }
        couch.OfRoi.CreateMarginGeometry(
            Examination=examination,
            SourceRoiName=source_roi_name,
            MarginSettings=MarginSettings
        )
        logging.info(
            "Successfully matched the treatment couch to image extent."
        )
        sg.popup_notify(
            f"The table structure called {source_roi_name} was added successfully.",
            title="Table structure successfully added",
            display_duration_in_ms=DISPLAY_DURATION_IN_MS
        )


def clean(case):
    """Undo all actions

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    # Clean not developed at this time.
    pass


def main():
    """The main function for this file"""

    logging.debug("Beginning execution of AddSupportStructures.py in main()")
    case = get_current("Case")
    examination = get_current("Examination")
    values = get_support_structures_GUI(examination)

    if values is None:
        message = (
            "The user closed the structure selection window "
            "or pressed Cancel. Exiting script without adding "
            "support structures."
        )
        logging.info(message)

        sg.popup_notify(
            message,
            title="Structure selection window closed",
            display_duration_in_ms=DISPLAY_DURATION_IN_MS
        )
        exit()

    if values['-COUCH TRUEBEAM-']:

        # Deploy the TrueBeam couch
        deploy_couch_model(
            case,
            support_structure_template=COUCH_SUPPORT_STRUCTURE_TEMPLATE,
            support_structures_examination=COUCH_SUPPORT_STRUCTURE_EXAMINATION,
            source_roi_name=COUCH_SOURCE_ROI_NAMES['TrueBeam']
        )
    elif values['-COUCH TOMO-']:
        pass

    if values["-USE CIVCO-"]:
        print("Use civco board")


if __name__ == "__main__":
    main()
