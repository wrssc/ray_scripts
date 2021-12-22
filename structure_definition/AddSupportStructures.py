""" Automatically create and place support structures

Currently supported
* TrueBeam Couch
* TomoTherapy Couch
* Civco Breast Board (w/ and w/o Monarch board)

This script accomplishes the following tasks:
1. Asks used for desired support structures

Couches
1. Create and automatically drop a couch

Civco Incline Board
1. Create and automatically place Civco incline board base
2. Create and automatically place Civco incline board body
    (with user-supplied angle)
3. Create and automatically place Civco Monarch board (with user-supplied index)

This script was tested with:
* Patient: INCLINE BOARD
* MRN: 20210713
* Case: 1
* RayStation: Launcher
* Title: Clinical

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
__status__ = "Released"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"
__reviewed__ = "11/2/2021"
__raystation__ = "10A SP1"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2021, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current, await_user_input
from StructureOperations import exists_roi, find_types

import PySimpleGUI as sg
import numpy as np
from sys import exit
import logging

# GUI Settings
NOTIFY = False
DISPLAY_DURATION_IN_MS = 3000

# Structure template defaults
COUCH_SUPPORT_STRUCTURE_TEMPLATE = "UW Support"
COUCH_SUPPORT_STRUCTURE_EXAMINATION = "Supine Patient"
COUCH_SOURCE_ROI_NAMES = {
    "TrueBeam": "TrueBeamCouch",
    "TomoTherapy": "TomoCouch"
}

BREASTBOARD_SUPPORT_STRUCTURE_TEMPLATE = "UW Civco C-Qual Breastboard"
BREASTBOARD_SUPPORT_STRUCTURE_EXAMINATION = "InclineBoard"
BREASTBOARD_SOURCE_ROI_NAMES = [
    "CivcoBaseBody",
    "NFZ_Base",
    "CivcoInclineBody",
    "NFZ_Incline",
    "CivcoBaseShell",
    "CivcoInclineShell",
]
BREASTBOARD_DERIVED_ROI_NAMES = [
    "NoFlyZone_PRV",
]

MONARCH_SUPPORT_STRUCTURE_TEMPLATE = "UW Civco C-Qual Breastboard"
MONARCH_SUPPORT_STRUCTURE_EXAMINATION = "Wingboard"
MONARCH_SOURCE_ROI_NAMES = ["CivcoWingBoard", "NFZ_WB_Basis"]
MONARCH_DERIVED_ROI_NAMES = []

# Magic numbers for shifts
COUCH_SHIFT = [0, 6.8, 0]

INCLINE_BASE_SHIFT = [-0.05, -6.65, -14.95]  # Lat, Long, Vrt in cm
INCLINE_BASE_PITCH = -0.188  # deg 0]

WINGBOARD_SHIFT = [-0.2, -22.8, 7.35]  # cm
WINGBOARD_ROLL = 0.3  # deg
WINGBOARD_PITCH = 0.4  # deg

INCLINE_CENTER_TO_HINGE = [0.0, -2.18, 45.09]  # cm

INCLINE_ZERO_PITCH = 0.884  # deg, the pitch at flat position
INCLINE_PITCH_BIAS = -0.25  # deg, the difference between measured and actual pitch

WINGBOARD_INDEX_DIST = 225.5/75/10  # cm, 75 markings over 225.5 mm

CIVCO_INCLINE_BOARD_ANGLES = {
    'Flat': INCLINE_ZERO_PITCH-INCLINE_PITCH_BIAS,
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

# Constants for ROIs
BASE_CONTRACTION = 0.2  # cm
INCLINE_CONTRACTION = 0.3  # cm
NOFLYZONE_EXPANSION = 1.5  # cm
SMALL_EXPANSION_SIZE = 0.5  # cm

CIVCOBOARD_MATERIAL_NAME = "CivcoBoard"
CIVCOBOARD_MATERIAL_DENS = 0.73


def verify_localization_point(case, exam):
    """ Checks for a localization point called SimFiducials

    This function searchs for two conditions:
    (1) Is there already a localization point?
    (2) Is there already a point called "SimFiducials"

    Different combinations of True and False can occur, and we handle each case
    as well as possible.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    exam : ScriptObject
        A RayStation ScriptObject corresponding to the current exam.

    RETURNS
    -------
    None

    """

    pois = case.PatientModel.PointsOfInterest

    # First, check for a point called "SimFiducials"
    sim_fiducials_exists = any(poi.Name == 'SimFiducials' for poi in pois)
    loc_point_exists = any(poi.Type == 'LocalizationPoint' for poi in pois)

    # Case 1: True and True
    if sim_fiducials_exists and loc_point_exists:
        # Check to make sure the localization point is "SimFiducials"
        loc_poi = [poi for poi in pois if poi.Type == 'LocalizationPoint']
        assert len(loc_poi) == 1
        loc_poi = loc_poi[0]

        if loc_poi.Name == 'SimFiducials':
            logging.info("POI SimFiducials exists and is the localization point.")
            return None
        else:
            message = (
                f"A localization point called {loc_poi.Name} exists, as does another "
                "POI called 'SimFiducials'. Normally, 'SimFiducials' is the "
                "localization point. Please correct this to ensure the correct point "
                "is used for localization."
            )
            await_user_input(message)
            return None

    # Case 2: True and False
    if sim_fiducials_exists and not loc_point_exists:

        sim_poi = [poi for poi in pois if poi.Name == 'SimFiducials']
        assert len(sim_poi) == 1
        sim_poi = sim_poi[0]

        sim_poi.Type = "LocalizationPoint"

        message = (
            "A POI called 'SimFiducials' exists, but it is not the "
            "localization point. A localization point does not exists, so "
            "the script has changed the 'Type' of 'SimFiducials' to a "
            "localization point."
        )
        logging.info(message)
        sg.popup_quick_message(message)
        return None

    # Case 3: False and True
    if not sim_fiducials_exists and loc_point_exists:

        loc_poi = [poi for poi in pois if poi.Type == 'LocalizationPoint']
        assert len(loc_poi) == 1
        loc_poi = loc_poi[0]

        loc_poi.Type = "SimFiducials"

        message = (
            "A localization point exists, but it is not called 'SimFiducials'. "
            "The script has changed the 'Name' of the localization point to "
            "'SimFiducials'."
        )
        logging.info(message)
        sg.popup_quick_message(message)
        return None

    # Case 4: False and False
    if not sim_fiducials_exists and not loc_point_exists:

        case.PatientModel.CreatePoi(
            Examination=exam,
            Point={'x': 0, 'y': 0, 'z': 0},
            Name="SimFiducials",
            Color="Green",
            Type="LocalizationPoint"
        )
        await_user_input(
            'Ensure correct placement of the SimFiducials point and continue script.')
        message = (
            "Created a localization point called 'SimFiducials'."
        )
        logging.info(message)
        return None


def get_support_structures_GUI(examination):

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
                            size=(10, 1),
                            key="-COUCH TRUEBEAM-"
                        )
                    ],
                    [
                        sg.Radio(
                            'TomoTherapy',
                            "RADIOCOUCH",
                            size=(10, 1),
                            key="-COUCH TOMO-"
                        )
                    ],
                    [
                        sg.Radio(
                            'None',
                            "RADIOCOUCH",
                            size=(10, 1),
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
                            'Use Monarch Wingboard',
                            enable_events=True,
                            key="-USE WINGBOARD-"
                        )
                    ],
                    [
                        sg.Frame(
                            layout=[
                                [
                                    sg.Text('Monarch Wingboard Index'),
                                    sg.Slider(
                                        range=(0, 75),
                                        orientation='h',
                                        size=(34, 20),
                                        default_value=50,
                                        key="-WINGBOARD INDEX-",
                                    )
                                ]
                            ],
                            title='Monarch Wingboard Options',
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


def add_structures_from_template(
    case,
    support_structure_template,
    support_structures_examination,
    source_roi_names,
    derived_roi_names=[],
):
    """Loads template and deploys structures on the current examination

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    support_structure_template: str
        The name of the support structure template in RayStation
    support_structures_examination: str
        The name of the examination associated with support_structure_template
        from which you will load the source ROIs
    source_roi_names : list of str
        The names of the ROIs from support_structures_examination that you wish
        to load
    derived_roi_names : list of str
        The names of the ROIs that are created from source_roi_names which you
        also want to clear
    """
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

    # Check to see if structures already exist. If so, warn the user that they
    # will be cleared.
    examination = get_current("Examination")
    rois_that_exist = exists_roi(
        case=case,
        rois=source_roi_names+derived_roi_names,
        return_exists=True
    )

    roi_list = '\n'.join(rois_that_exist)
    message = (
            f"The following structures already exist:\n{roi_list}. "
            f"\n\nThe geometries will be cleared on examination {examination.Name}"
        )
    if NOTIFY:
        sg.popup_notify(
            message,
            title="Structures will be cleared",
            display_duration_in_ms=DISPLAY_DURATION_IN_MS
        )

    for roi in rois_that_exist:
        message = (
            f"A structure called {roi} already exists. "
            f"Its geometry will be cleared on examination {examination.Name}"
        )
        logging.info(message)

        case.PatientModel.StructureSets[examination.Name] \
            .RoiGeometries[roi].DeleteGeometry()

    # Add structure from template
    # Notes: The use of AlignToImageCenter drops structures in center of image.
    # This is usually not the correct location, so your script must either
    # prompt the user to correct the location, or automate the correct location.
    case.PatientModel.CreateStructuresFromTemplate(
        SourceTemplate=support_template,
        SourceExaminationName=support_structures_examination,
        SourceRoiNames=source_roi_names,
        SourcePoiNames=[],
        AssociateStructuresByName=True,
        TargetExamination=examination,
        InitializationOption='AlignImageCenters'
    )
    roi_list = '\n'.join(source_roi_names)
    message = f"Successfully added the following ROIs:\n{roi_list}"
    logging.info(message)
    if NOTIFY:
        sg.popup_notify(
            message,
            title="Structures added successfully",
            display_duration_in_ms=DISPLAY_DURATION_IN_MS
        )


def transform_structure(
    examination,
    geometry,
    translations=[0.0, 0.0, 0.0],
    pitch=0.0,
    yaw=0.0,
    roll=0.0,
):
    """Transform an ROI with translation and rotations.

    All rotations happen about DICOM (0,0,0).

    PARAMETERS
    ----------
    examination : ScriptObject
        A RayStation ScriptObject corresponding to the current examination.
    geometry: ScriptObject
        A RayStation ScriptObject corresponding to the geometry which you would
        like to transform
    translations : list of float
        A 3x1 array listing the [x, y, z] translations (default is [0.0,0.0,0.0])
    pitch : float
        The pitch (x-axis) rotation, in degrees (default is 0.0)
    yaw : float
        The yaw (y-axis) rotation, in degrees (default is 0.0)
    roll : float
        The roll (z-axis) rotation, in degrees (default is 0.0)
    """

    # Convert to radians
    pitch_r, yaw_r, roll_r = np.pi/180.0*np.array([pitch, yaw, roll])

    # Generate rotation matrices
    M_pitch = np.array([
        [1, 0, 0],
        [0, np.cos(pitch_r), -np.sin(pitch_r)],
        [0, np.sin(pitch_r), np.cos(pitch_r)],
    ])

    M_yaw = np.array([
        [np.cos(yaw_r), 0, np.sin(yaw_r)],
        [0, 1, 0],
        [-np.sin(yaw_r), 0, np.cos(yaw_r)],

    ])

    M_roll = np.array([
        [np.cos(roll_r), -np.sin(roll_r), 0],
        [np.sin(roll_r), np.cos(roll_r), 0],
        [0, 0, 1],

    ])

    # Compute composite rotation matrix (and relabel translations)
    T = translations
    M = np.matmul(M_roll, np.matmul(M_yaw, M_pitch))

    TransformationMatrix = {
        'M11': M[0, 0],
        'M12': M[0, 1],
        'M13': M[0, 2],
        'M14': T[0],  # x left-right
        'M21': M[1, 0],
        'M22': M[1, 1],
        'M23': M[1, 2],
        'M24': T[1],  # y = anterior-posterior
        'M31': M[2, 0],
        'M32': M[2, 1],
        'M33': M[2, 2],
        'M34': T[2],  # z superior-inferior
        'M41': 0, 'M42': 0, 'M43': 0, 'M44': 1
    }

    geometry.OfRoi.TransformROI3D(
        Examination=examination,
        TransformationMatrix=TransformationMatrix
    )


def deploy_couch_model(
        case,
        support_structure_template,
        support_structures_examination,
        source_roi_names):
    """ Deploys the TrueBeam couch

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    support_structure_template: str
        The name of the support structure template in RayStation
    support_structures_examination: str
        The name of the examination associated with support_structure_template
        from which you will load the source ROIs
    source_roi_names : list of str
        The names of the ROIs from support_structures_examination that you wish
        to load)

    RETURNS
    -------
    The RayStation Geometry object corresponding to the couch 

    NOTES
    -----
    This function assumes that the top of the treatment couch is 7 cm above
    the DICOM y=0 plane. This is true of scans acquired on our UWHC Siemens scanner.
    This is likely to be true for the Johnson Creek scanner, but has not been tested.
    This assumption will not work for the East Clinic GE scanner.
    This function has not been tested with padded images. This function will prompt
    the user to evaluate and correct couch placement if necessary.

    """

    # There should only be one source ROI:
    if len(source_roi_names) != 1:
        message = (
            "The list 'source_roi_names' does not have length 1 "
            f"(length is {len(source_roi_names)}. Exiting script."
        )
        logging.error(message)
        sg.popup_error(message, title="Incorrect source ROIs")
        exit()

    # This script is designed to be used for HFS patients:
    examination = get_current("Examination")
    patient = get_current("Patient")

    if examination.PatientPosition != "HFS":
        logging.error("Current exam in not in HFS position. Exiting script.")
        message = (
            "The script requires a patient in the head-first supine position. "
            "The currently selected exam is not HFS. Exiting script."
        )
        sg.popup_error(message, title="Patient Orientation Error")
        exit()

    with CompositeAction("Add Couch Model"):

        add_structures_from_template(
            case=case,
            support_structure_template=support_structure_template,
            support_structures_examination=support_structures_examination,
            source_roi_names=source_roi_names
        )

    with CompositeAction("Shift Couch Model"):

        couch = case.PatientModel.StructureSets[examination.Name].RoiGeometries[source_roi_names[0]]
        couch_roi_name = source_roi_names[0]
        patient.SetRoiVisibility(RoiName=couch_roi_name, IsVisible=False)

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
        logging.info("Successfully translated the couch model")

    with CompositeAction("Fill Couch Model Longitudinally"):

        image_bb = examination.Series[0].ImageStack.GetBoundingBox()
        extent_inf = image_bb[0]["z"]
        extent_sub = image_bb[1]["z"]

        # If inferior edge of couch is inside image boundary
        if couch.GetBoundingBox()[0]["z"] > extent_inf:
            # Extend couch until it exceeds image boundary
            # Note: A while loop is necessary because the maximum expansion is
            # 15 cm. This expansion may need to be repeated, hence the loop.
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
                    SourceRoiName=couch_roi_name,
                    MarginSettings=MarginSettings)

            # Perform a single contraction to match image boundaries
            contract_inf = extent_inf - couch.GetBoundingBox()[0]["z"]

            MarginSettings = {
                'Type': "Contract",
                'Superior': 0,
                'Inferior': contract_inf,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=couch_roi_name,
                MarginSettings=MarginSettings
            )
        # If inferior edge of couch is outside image boundary
        elif couch.GetBoundingBox()[0]["z"] < extent_inf:
            # Contract couch until it is within image boundary
            while couch.GetBoundingBox()[0]["z"] < extent_inf:
                MarginSettings = {
                    'Type': "Contract",
                    'Superior': 0,
                    'Inferior': 15,
                    'Anterior': 0,
                    'Posterior': 0,
                    'Right': 0,
                    'Left': 0
                }
                couch.OfRoi.CreateMarginGeometry(
                    Examination=examination,
                    SourceRoiName=couch_roi_name,
                    MarginSettings=MarginSettings)

            # Perform a single expansion to match image boundaries
            expand_inf = couch.GetBoundingBox()[0]["z"] - extent_inf

            MarginSettings = {
                'Type': "Expand",
                'Superior': 0,
                'Inferior': expand_inf,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=couch_roi_name,
                MarginSettings=MarginSettings
            )
            logging.info(
                "Successfully matched the TrueBeam Couch to the inferior image boundary"
            )

        # If superior edge of couch is inside image boundary
        if couch.GetBoundingBox()[1]["z"] < extent_sub:
            # Extend couch until it exceeds image boundary
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
                    SourceRoiName=couch_roi_name,
                    MarginSettings=MarginSettings
                )

            # Perform a single contraction to match image boundaries
            contract_sup = couch.GetBoundingBox()[1]["z"] - extent_sub

            MarginSettings = {
                'Type': "Contract",
                'Superior': contract_sup,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
                }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=couch_roi_name,
                MarginSettings=MarginSettings
            )
        # If superior edge of couch is outside image boundary
        elif couch.GetBoundingBox()[1]["z"] > extent_sub:
            # Contract couch until it is within image boundary
            while couch.GetBoundingBox()[1]["z"] > extent_sub:
                MarginSettings = {
                    'Type': "Contract",
                    'Superior': 15,
                    'Inferior': 0,
                    'Anterior': 0,
                    'Posterior': 0,
                    'Right': 0,
                    'Left': 0
                    }
                couch.OfRoi.CreateMarginGeometry(
                    Examination=examination,
                    SourceRoiName=couch_roi_name,
                    MarginSettings=MarginSettings
                )

            # Perform a single expansion to match image boundaries
            expand_sup = extent_sub - couch.GetBoundingBox()[1]["z"]

            MarginSettings = {
                'Type': "Expand",
                'Superior': expand_sup,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
                }
            couch.OfRoi.CreateMarginGeometry(
                Examination=examination,
                SourceRoiName=couch_roi_name,
                MarginSettings=MarginSettings
            )

            logging.info(
                "Successfully matched the treatment couch to image extent."
            )

        if NOTIFY:
            sg.popup_notify(
                f"The table structure called {couch_roi_name} was added successfully.",
                title="Table structure successfully added",
                display_duration_in_ms=DISPLAY_DURATION_IN_MS
            )

    patient.SetRoiVisibility(RoiName=couch.OfRoi.Name, IsVisible=True)

    message = (
        "Please use the Translate and Rotate tools to adjust the "
        f"{couch_roi_name}, as needed."
    )
    await_user_input(message)

    patient.SetRoiVisibility(RoiName=couch.OfRoi.Name, IsVisible=False)

    get_current("Patient").Save()
    return couch


def deploy_civco_breastboard_model(
    case,
    incline_angle,
    use_wingboard,
    wingboard_index,
    couch=None
):
    """ Deploys the Civco C-Qual Breastboard

    The function is hard-coded with the current parameters for loading the required structures.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    incline_angle: str
        A key from CIVCO_INCLINE_BOARD_ANGLES corresponding to an incline angle.
    use_wingboard: bool
        True if user wants to add the Civco Monarch board to the image, else False.
    wingboard_index: int or float or None
        The index of the wingboard position (0-75), or None.
    couch: ScriptObject
        A RayStation ScriptObject corresponding to the treatment couch.

    RETURNS
    -------
    None

    """
    # This script is designed to be used for HFS patients:
    examination = get_current("Examination")
    patient = get_current("Patient")

    if examination.PatientPosition != "HFS":
        message = (
            "The script requires a patient in the head-first supine position. "
            "The currently selected exam is not HFS. Exiting script."
        )
        logging.error(message)
        sg.popup_error(message, title="Patient Orientation Error")
        exit()

    # The case must have a region of interest set to the "External" type
    roi_external_list = find_types(case, "External")
    if not roi_external_list:
        message = (
            "The script requires that a structure (usually External or ExternalClean) be set as "
            "external in RayStation."
        )
        logging.error(message)
        sg.popup_error(message, title="Patient Orientation Error")
        exit()

    assert len(roi_external_list) == 1, "Found more than one structure of type External"
    roi_external = case.PatientModel.RegionsOfInterest[roi_external_list[0]]

    with CompositeAction("Add Breastboard components"):

        add_structures_from_template(
            case=case,
            support_structure_template=BREASTBOARD_SUPPORT_STRUCTURE_TEMPLATE,
            support_structures_examination=BREASTBOARD_SUPPORT_STRUCTURE_EXAMINATION,
            source_roi_names=BREASTBOARD_SOURCE_ROI_NAMES,
            derived_roi_names=BREASTBOARD_DERIVED_ROI_NAMES
        )

        if use_wingboard:
            add_structures_from_template(
                case=case,
                support_structure_template=MONARCH_SUPPORT_STRUCTURE_TEMPLATE,
                support_structures_examination=MONARCH_SUPPORT_STRUCTURE_EXAMINATION,
                source_roi_names=MONARCH_SOURCE_ROI_NAMES,
                derived_roi_names=MONARCH_DERIVED_ROI_NAMES
            )

        message = (
            "Civco Breastboard structures added to examination."
        )
        logging.info(message)

    get_current("Patient").Save()

    with CompositeAction("Move ROIs to Initial Position"):

        # Grab ROIs and create groups
        ss = case.PatientModel.StructureSets[examination.Name]
        base_body = ss.RoiGeometries["CivcoBaseBody"]
        base_nfz = ss.RoiGeometries["NFZ_Base"]
        incline_body = ss.RoiGeometries["CivcoInclineBody"]
        incline_nfz = ss.RoiGeometries["NFZ_Incline"]

        # This group of ROIs has the same shifts from initial postion to "Flat" position
        initial_shifts_rois = [base_body, base_nfz, incline_body, incline_nfz]

        # Make invisible
        for roi in initial_shifts_rois:
            patient.SetRoiVisibility(RoiName=roi.OfRoi.Name, IsVisible=False)

        # Compute translations to move from image center to "Flat" position
        base_bb = base_body.GetBoundingBox()
        bottom_of_base = base_bb[1]["y"]
        z_position = (base_bb[1]["z"] + base_bb[0]["z"])/2

        T = [
            INCLINE_BASE_SHIFT[0],
            INCLINE_BASE_SHIFT[1]-bottom_of_base,
            INCLINE_BASE_SHIFT[2]-z_position,
        ]

        # Translate ROIs to correct position for a "Flat" incline
        for roi in initial_shifts_rois:
            transform_structure(
                examination=examination,
                geometry=roi,
                translations=T,
                pitch=INCLINE_BASE_PITCH
            )

        message = (
            "Civco Breastboard structures translated to Flat incline postion."
        )
        logging.info(message)

        if use_wingboard:

            # The wingboard ROI comes from a different exam than the rest of
            # the board, so it has unique translations to get to a
            # "Flat incline at index 50" location.

            # Grab ROIs and create groups
            wingboard_body = ss.RoiGeometries["CivcoWingBoard"]
            wingboard_nfz = ss.RoiGeometries["NFZ_WB_Basis"]

            # This group of ROIs participates in rotation during incline and
            # translations due to wingboard movements
            wingboard_shifts_rois = [wingboard_body, wingboard_nfz]

            # Make invisible
            for roi in wingboard_shifts_rois:
                patient.SetRoiVisibility(RoiName=roi.OfRoi.Name, IsVisible=False)

            T = [
                WINGBOARD_SHIFT[0],
                WINGBOARD_SHIFT[1]-bottom_of_base,
                WINGBOARD_SHIFT[2]-z_position,
            ]

            # Translate ROIs to correct position for a "Flat incline, WB 50"
            for roi in wingboard_shifts_rois:
                transform_structure(
                    examination=examination,
                    geometry=roi,
                    translations=T,
                    pitch=WINGBOARD_PITCH,
                    roll=WINGBOARD_ROLL,
                )

            message = (
                "Civco Monarch wingboard structures have been translated to "
                " a 'Flat' incline postion with the wingboard at index 50."
            )
            logging.info(message)

    # Next, we will let the user correct the location of the base. This
    # will be used to create a shift vector that can be used to correct the
    # position of other items.

    incline_body_center_initial = base_body.GetCenterOfRoi()

    patient.SetRoiVisibility(RoiName=base_body.OfRoi.Name, IsVisible=True)

    message = (
        "Please use the Translate and Rotate tools to adjust the "
        f"{base_body.OfRoi.Name}, as needed."
    )
    await_user_input(message)

    patient.SetRoiVisibility(RoiName=base_body.OfRoi.Name, IsVisible=False)
    get_current("Patient").Save()

    incline_body_center_final = base_body.GetCenterOfRoi()

    manual_translation = np.array([
        incline_body_center_final["x"] - incline_body_center_initial["x"],
        incline_body_center_final["y"] - incline_body_center_initial["y"],
        incline_body_center_final["z"] - incline_body_center_initial["z"],
    ])

    with CompositeAction("Apply Manual Corrections"):

        # First, reset the base_body position
        transform_structure(
            examination=examination,
            geometry=base_body,
            translations=-1*manual_translation,  # minus sign
        )

        # Finally, translate all structures in bulk.
        for roi in initial_shifts_rois:
            transform_structure(
                examination=examination,
                geometry=roi,
                translations=manual_translation
            )

        if use_wingboard:
            for roi in wingboard_shifts_rois:
                transform_structure(
                    examination=examination,
                    geometry=roi,
                    translations=manual_translation,
                )

        message = (
            f"User-defined manual shift, {manual_translation}, "
            "was applied to all structures."
        )
        logging.info(message)

    with CompositeAction("Incline and Shift Wingboard"):

        # This group of ROIs participates in rotation during incline
        incline_shifts_rois = [incline_body, incline_nfz]
        if use_wingboard:
            incline_shifts_rois += wingboard_shifts_rois

        # Shift the incline board hinge to the origin
        incline_body_center = incline_body.GetCenterOfRoi()

        T_hinge = np.array([
            INCLINE_CENTER_TO_HINGE[0],
            INCLINE_CENTER_TO_HINGE[1]-incline_body_center["y"],
            INCLINE_CENTER_TO_HINGE[2]-incline_body_center["z"],
        ])

        for roi in incline_shifts_rois:
            transform_structure(
                examination=examination,
                geometry=roi,
                translations=T_hinge,
            )

        if use_wingboard:

            # Translate the Monarch wingboard

            # The "Flat" position of the board leaves the incline portion at
            # INCLINE_ZERO_PITCH degrees. The wingboard is at the same pitch.
            # We're going to rotate it to a true zero pitch, translate the
            # wingboard longitudinally to the correct indexed location, then
            # Rotate it back up to the "Flat" angle.

            # Rotate wingboard to true 0 degree orientation
            for roi in wingboard_shifts_rois:
                transform_structure(
                    examination=examination,
                    geometry=roi,
                    pitch=-INCLINE_ZERO_PITCH,
                )

            # Shift wingboard to indexed position
            translation_dist = (wingboard_index-50)*WINGBOARD_INDEX_DIST
            T = [0, 0, -translation_dist]

            for roi in wingboard_shifts_rois:
                transform_structure(
                    examination=examination,
                    geometry=roi,
                    translations=T,
                )

            # Rotate back to "Flat" incline
            for roi in wingboard_shifts_rois:
                transform_structure(
                    examination=examination,
                    geometry=roi,
                    pitch=INCLINE_ZERO_PITCH,
                )

            message = (
                f"Civco Monarch wingboard moved to index {wingboard_index}."
            )
            logging.info(message)

        # Rotate to incline board (and wingboard) to correct angle
        incline_board_angle = CIVCO_INCLINE_BOARD_ANGLES[incline_angle]
        incline_rotation = incline_board_angle - INCLINE_ZERO_PITCH + INCLINE_PITCH_BIAS
        for roi in incline_shifts_rois:
            transform_structure(
                examination=examination,
                geometry=roi,
                pitch=incline_rotation,
            )

        # Reverse the translations
        for roi in incline_shifts_rois:
            transform_structure(
                examination=examination,
                geometry=roi,
                translations=-T_hinge,
            )

        message = (
                f"The board was inclined to {incline_angle}."
            )
        logging.info(message)

    get_current("Patient").Save()

    # Make shiftable ROIs visible
    patient.SetRoiVisibility(RoiName=incline_body.OfRoi.Name, IsVisible=True)
    # patient.SetRoiVisibility(RoiName=base_body.OfRoi.Name, IsVisible=True)

    if use_wingboard:
        patient.SetRoiVisibility(RoiName=wingboard_body.OfRoi.Name, IsVisible=True)

    message = (
        "Please use the Translate and Rotate tools to adjust the "
        "CivcoWingBoard, CivcoBaseBody and CivcoInclineBody, as needed."
    )
    await_user_input(message)

    # Make invisible again
    patient.SetRoiVisibility(RoiName=incline_body.OfRoi.Name, IsVisible=False)
    # patient.SetRoiVisibility(RoiName=base_body.OfRoi.Name, IsVisible=False)
    if use_wingboard:
        patient.SetRoiVisibility(RoiName=wingboard_body.OfRoi.Name, IsVisible=False)

    with CompositeAction("Address overlaps"):

        """
        There will inevitably be overlap between the External, wingboard,
        incline board and, perhaps, the couch too. RayStation does not permit
        support structures with density overrides to overlap one another, nor
        the External. We will manage this with subtractions to ensure no
        overlaps. The subtractions will occur before preparation of the final
        shelled structures to ensure they maintain the same attenuation.

        Order of priority
        1. CivcoWingBoard (if in use)
        2. CivcoInclineBody
        3. External
        4. Treatment Table
        5. CivcoBaseBody
        """
        NoExpansion = {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
        }

        SmallExpansion = {
            'Type': "Expand",
            'Superior': SMALL_EXPANSION_SIZE,
            'Inferior': SMALL_EXPANSION_SIZE,
            'Anterior': SMALL_EXPANSION_SIZE,
            'Posterior': SMALL_EXPANSION_SIZE,
            'Right': SMALL_EXPANSION_SIZE,
            'Left': SMALL_EXPANSION_SIZE
        }

        PostExpansion = {
            'Type': "Expand",
            'Superior': SMALL_EXPANSION_SIZE,
            'Inferior': SMALL_EXPANSION_SIZE,
            'Anterior': SMALL_EXPANSION_SIZE,
            'Posterior': 15,  # Capture tissue under the structure.
            'Right': SMALL_EXPANSION_SIZE,
            'Left': SMALL_EXPANSION_SIZE
        }

        # First, address overlap with the wingboard.
        if use_wingboard:
            # Subtract CivcoWingBoard from CivcoInclineBody

            incline_body.OfRoi.CreateAlgebraGeometry(
                Examination=examination,
                ExpressionA={
                    'Operation': "Union",
                    'SourceRoiNames': [incline_body.OfRoi.Name],
                    'MarginSettings': NoExpansion
                },
                ExpressionB={
                    'Operation': "Union",
                    'SourceRoiNames': [wingboard_body.OfRoi.Name],
                    'MarginSettings': NoExpansion
                },
                ResultOperation="Subtraction"
            )

            # Subtract CivcoWingBoard from External
            roi_external.CreateAlgebraGeometry(
                Examination=examination,
                ExpressionA={
                    'Operation': "Union",
                    'SourceRoiNames': [roi_external.Name],
                    'MarginSettings': NoExpansion
                },
                ExpressionB={
                    'Operation': "Union",
                    'SourceRoiNames': [wingboard_body.OfRoi.Name],
                    'MarginSettings': PostExpansion
                },
                ResultOperation="Subtraction"
            )

        # Second, address overlap with the incline board.
        # Subtract CivcoInclineBody from External
        roi_external.CreateAlgebraGeometry(
            Examination=examination,
            ExpressionA={
                'Operation': "Union",
                'SourceRoiNames': [roi_external.Name],
                'MarginSettings': NoExpansion
            },
            ExpressionB={
                'Operation': "Union",
                'SourceRoiNames': [incline_body.OfRoi.Name],
                'MarginSettings': PostExpansion
            },
            ResultOperation="Subtraction"
        )

        # Subtract CivcoInclineBody from CivcoBaseBody
        base_body.OfRoi.CreateAlgebraGeometry(
                Examination=examination,
                ExpressionA={
                    'Operation': "Union",
                    'SourceRoiNames': [base_body.OfRoi.Name],
                    'MarginSettings': NoExpansion
                },
                ExpressionB={
                    'Operation': "Union",
                    'SourceRoiNames': [incline_body.OfRoi.Name],
                    'MarginSettings': SmallExpansion
                },
                ResultOperation="Subtraction"
            )

        # Check for table-base overlap:
        top_of_couch = couch.GetBoundingBox()[0]["y"]
        bottom_of_base = base_body.GetBoundingBox()[1]["y"]

        if top_of_couch > bottom_of_base:
            shift_couch_y = -(top_of_couch-bottom_of_base+0.05)

            # Shift the couch to below the base
            transform_structure(
                examination=examination,
                geometry=couch,
                translations=[0, shift_couch_y, 0],
            )
            message = (f"The couch structure had been lowered {shift_couch_y} cm.")
            logging.info(message)

    with CompositeAction("Clean External"):
        ss.SimplifyContours(
            RoiNames=[roi_external.Name],
            RemoveHoles3D=True,
            RemoveSmallContours=True,
            AreaThreshold=1.0,
        )

    with CompositeAction("Create Final ROIS (if needed)"):

        # Create final ROIs
        if not exists_roi(case, "NoFlyZone_PRV")[0]:
            case.PatientModel.CreateRoi(
                Name='NoFlyZone_PRV',
                Color="Green",
                Type="Avoidance"
            )

        base_shell = ss.RoiGeometries["CivcoBaseShell"]
        incline_shell = ss.RoiGeometries["CivcoInclineShell"]
        nfz_expanded = ss.RoiGeometries["NoFlyZone_PRV"]

        patient.SetRoiVisibility(RoiName=base_shell.OfRoi.Name, IsVisible=False)
        patient.SetRoiVisibility(RoiName=incline_shell.OfRoi.Name, IsVisible=False)
        patient.SetRoiVisibility(RoiName=nfz_expanded.OfRoi.Name, IsVisible=False)

    with CompositeAction("Expand No-fly Zone"):
        # Expand NoFlyZone
        MarginSettings = {
            'Type': "Expand",
            'Superior': NOFLYZONE_EXPANSION,
            'Inferior': NOFLYZONE_EXPANSION,
            'Anterior': NOFLYZONE_EXPANSION,
            'Posterior': NOFLYZONE_EXPANSION,
            'Right': NOFLYZONE_EXPANSION,
            'Left': NOFLYZONE_EXPANSION
        }

        source_roi_names = ["NFZ_Base", "NFZ_Incline"]
        if use_wingboard:
            source_roi_names += ["NFZ_WB_Basis"]

        nfz_expanded.OfRoi.CreateAlgebraGeometry(
            Examination=examination,
            ExpressionA={
                'Operation': "Union",
                'SourceRoiNames': source_roi_names,
                'MarginSettings': MarginSettings
            }
        )

    with CompositeAction("Create Derived Geometries"):

        zipped_parameters = zip(
            [base_shell, incline_shell],
            ["CivcoBaseBody", "CivcoInclineBody"],
            [BASE_CONTRACTION, INCLINE_CONTRACTION]
        )

        for shell, body_name, contraction in zipped_parameters:

            # Create Shell
            MarginSettingsA = {
                'Type': "Expand",
                'Superior': 0,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }

            MarginSettingsB = {
                'Type': "Contract",
                'Superior': contraction,
                'Inferior': contraction,
                'Anterior': contraction,
                'Posterior': contraction,
                'Right': contraction,
                'Left': contraction
            }

            shell.OfRoi.CreateAlgebraGeometry(
                Examination=examination,
                ExpressionA={
                    'Operation': "Union",
                    'SourceRoiNames': [body_name],
                    'MarginSettings': MarginSettingsA
                },
                ExpressionB={
                    'Operation': "Union",
                    'SourceRoiNames': [body_name],
                    'MarginSettings': MarginSettingsB
                },
                ResultOperation="Subtraction"
            )

    with CompositeAction("Apply Special Density Override"):

        # Check if CIVCOBOARD_MATERIAL_NAME already exists
        material_names = [x.Name for x in case.PatientModel.Materials]

        if CIVCOBOARD_MATERIAL_NAME not in material_names:

            # Find the Water material
            material_water = None
            for material in case.PatientModel.Materials:

                if material.Name == "Water":
                    material_water = material
                    break

## RAB_Comment: We should test that this material Creation is still compatible with electron calculation
## otherwise we may find that we can't generate electron plans. If it does, then awesome! RaySearch told me
## there was no work around to the material missing issue.
            # Create a new material
            material_CB = case.PatientModel.CreateMaterial(
                BaseOnMaterial=material_water,
                Name=CIVCOBOARD_MATERIAL_NAME,
                MassDensityOverride=CIVCOBOARD_MATERIAL_DENS,
            )

            message = (
                f"A material called {CIVCOBOARD_MATERIAL_NAME} was created."
            )
            logging.info(message)

        # Find the CIVCOBOARD_MATERIAL_NAME material
        material_CB = None
        for material in case.PatientModel.Materials:

            if material.Name == CIVCOBOARD_MATERIAL_NAME:
                material_CB = material
                break

        # Set the material for the shells
        base_shell.OfRoi.SetRoiMaterial(Material=material_CB)
        incline_shell.OfRoi.SetRoiMaterial(Material=material_CB)

        message = ("The base shell and incline shell have been overridden.")
        logging.info(message)

    with CompositeAction("Delete Extra Structures"):

        base_body.OfRoi.DeleteRoi()
        base_nfz.OfRoi.DeleteRoi()
        incline_body.OfRoi.DeleteRoi()
        incline_nfz.OfRoi.DeleteRoi()
        if use_wingboard:
            wingboard_nfz.OfRoi.DeleteRoi()

        message = ("Deleted extra ROIs.")
        logging.error(message)

    patient.SetRoiVisibility(RoiName=base_shell.OfRoi.Name, IsVisible=True)
    patient.SetRoiVisibility(RoiName=incline_shell.OfRoi.Name, IsVisible=True)
    patient.SetRoiVisibility(RoiName=nfz_expanded.OfRoi.Name, IsVisible=True)
    patient.SetRoiVisibility(RoiName=roi_external.Name, IsVisible=True)
    if use_wingboard:
        patient.SetRoiVisibility(RoiName=wingboard_body.OfRoi.Name, IsVisible=True)

    message = ("The Civco C-Qual Breastboard was added successfully.")
    logging.info(message)
    if NOTIFY:
        sg.popup_notify(message, title="Added Breastboard Successfully")


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
        if NOTIFY:
            sg.popup_notify(
                message,
                title="Structure selection window closed",
                display_duration_in_ms=DISPLAY_DURATION_IN_MS
            )
        exit()

    """ Structure of "values" dictionary (example)
    {
        '-COUCH TRUEBEAM-': True,
        '-COUCH TOMO-': False,
        '-COUCH NONE-': False,
        '-USE CIVCO-': True,
        '-INCLINE ANGLE-': '7.5 deg',
        '-USE WINGBOARD-': True,
        '-WINGBOARD INDEX-': 5.0
        }
    """

    # Add the localization point, if missing:
    verify_localization_point(case=case, exam=examination)

    couch = None
    if values['-COUCH TRUEBEAM-']:

        # Deploy the TrueBeam couch
        couch = deploy_couch_model(
            case,
            support_structure_template=COUCH_SUPPORT_STRUCTURE_TEMPLATE,
            support_structures_examination=COUCH_SUPPORT_STRUCTURE_EXAMINATION,
            source_roi_names=[COUCH_SOURCE_ROI_NAMES['TrueBeam']]
        )
    elif values['-COUCH TOMO-']:
        couch = deploy_couch_model(
            case,
            support_structure_template=COUCH_SUPPORT_STRUCTURE_TEMPLATE,
            support_structures_examination=COUCH_SUPPORT_STRUCTURE_EXAMINATION,
            source_roi_names=[COUCH_SOURCE_ROI_NAMES['TomoTherapy']]
        )

    if values["-USE CIVCO-"]:
        deploy_civco_breastboard_model(
            case,
            incline_angle=values["-INCLINE ANGLE-"],
            use_wingboard=values["-USE WINGBOARD-"],
            wingboard_index=values["-WINGBOARD INDEX-"],
            couch=couch
        )


if __name__ == "__main__":
    main()
