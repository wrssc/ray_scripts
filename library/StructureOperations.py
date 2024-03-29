""" Perform structure operations on Raystation plans

exclude_from_export
toggles the rois export status

check_roi
checks if an ROI has contours

exists_roi
checks if ROI is present in the contour list

max_roi
checks for maximum extent of an roi

visualize_none
turns all contour visualization off

Versions:
01.00.00 Original submission

Known Issues:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2020-03-20"

__version__ = "1.0.0"
__status__ = "Production"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"

__reviewed__ = ""
__raystation__ = "8.0.SPB"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__help__ = ""
__copyright__ = "Copyright (C) 2018, University of Wisconsin Board of Regents"

import logging
import connect
import re
import numpy as np
import pandas as pd
import xml.etree.ElementTree as Et
import clr
import System.Drawing
import sys
from os import path, listdir

rab_git = "U:\\UWHealth\\RadOnc\\ShareAll\\Users\\Bayliss\\GitSync\\DHO_RayScripts"
sys.path.append(
    "U:\\UWHealth\\RadOnc\\ShareAll\\Users\\Bayliss\\GitSync\\DHO_RayScripts\\protocols\\UW")
sys.path.append(
    "U:\\UWHealth\\RadOnc\\ShareAll\\Users\\Bayliss\\GitSync\\DHO_RayScripts\\protocols\\UW"
    "\\AutoPlans")
sys.path.append(
    "U:\\UWHealth\\RadOnc\\ShareAll\\Users\\Bayliss\\GitSync\\DHO_RayScripts\\protocols\\UW"
    "\\beamset_templates")

PROTOCOL_FOLDER = path.join(rab_git, 'protocols')
INSTITUTION_FOLDER = r'UW'
BEAMSET_FOLDER = r'beamset_templates'
PATH_BEAMSETS = path.join(PROTOCOL_FOLDER, INSTITUTION_FOLDER, BEAMSET_FOLDER)

clr.AddReference("System.Drawing")

from GeneralOperations import logcrit as logcrit
import UserInterface

# Commonly underdoses structures
# Plan structures matched in this list will be selected for checkbox elements below
UNDERDOSE_STRUCTURES = [
    "GreatVes",
    "A_Aorta",
    "Bag_Bowel",
    "Bowel_Small",
    "Bowel_Large",
    "BrachialPlex_L_PRV05",
    "BrachialPlex_L",
    "BrachialPlex_R",
    "BrachialPlex_R_PRV05",
    "Brainstem",
    "Bronchus",
    "Bronchus_L",
    "Bronchus_R",
    "CaudaEquina",
    "Cochlea_L",
    "Cochlea_R",
    "Duodenum",
    "Esophagus",
    "Genitalia",
    "Heart",
    "Eye_L",
    "Eye_R",
    "Hippocampus_L",
    "Hippocampus_L_PRV05",
    "Hippocampus_R",
    "Hippocampus_R_PRV05",
    "Larynx",
    "Lens_R",
    "Lens_L",
    "Bone_Mandible",
    "OpticChiasm",
    "OpticNrv_L",
    "OpticNrv_R",
    "Rectum",
    "Retina_L",
    "Retina_R",
    "SpinalCord",
    "SpinalCord_PRV02",
    "Trachea",
    "V_Pulmonary",
]

# Common uniformly dosed areas
# Plan structures matched in this list will be selected for checkbox elements below
UNIFORM_STRUCTURES = [
    "A_Aorta_PRV05",
    "Bag_Bowel",
    "Bladder",
    "Bowel_Small",
    "Bowel_Large",
    "Brainstem",
    "Brainstem_PRV03",
    "Bronchus_PRV05",
    "Bronchus_L_PRV05",
    "Bronchus_R_PRV05",
    "CaudaEquina_PRV05",
    "Cavity_Oral",
    "Cochlea_L_PRV05",
    "Cochlea_R_PRV05",
    "Esophagus",
    "Esophagus_PRV05",
    "Duodenum_PRV05",
    "Heart",
    "Larynx",
    "Lens_L_PRV05",
    "Lens_R_PRV05",
    "Lips",
    "Mandible",
    "Musc_Constrict",
    "OpticChiasm_PRV03",
    "OpticNerv_L_PRV03",
    "OpticNerv_R_PRV03",
    "Rectum",
    "SpinalCord",
    "SpinalCord_PRV05",
    "Stomach",
    "Trachea",
    "V_Pulmonary_PRV05",
    "Vulva",
]

# Regex expressions for target
TARGET_EXPRESSIONS = ["^PTV", "^ITV", "^GTV", "^CTV"]
# Regex expressions for planning structs
PLANNING_EXPRESSIONS = [
    "^OTV",
    "^sOTV",
    "^opt",
    "^sPTV",
    "_EZ_",
    "^ring",
    "_PTV[0-9]",
    "^Ring",
    "^Normal",
    "^OAR_PTV",
    "^IGRT",
    "^AllPTV",
    "^InnerAir",
    "z_derived",
    "Uniform",
    "^UnderDose",
    "Air",
    "FieldOfView",
    "All_PTVs"
]


def any_regex_match(regex_list, text):
    for pattern in regex_list:
        if re.search(pattern, text):
            return True
    return False


def exclude_from_export(case, rois):
    """Toggle export
    :param case: current case
    :param rois: name of structure to exclude"""

    if type(rois) is not list:
        rois = [rois]

    for r in rois:
        if not case.PatientModel.RegionsOfInterest[r].ExcludeFromExport:
            try:
                case.PatientModel.ToggleExcludeFromExport(
                    ExcludeFromExport=True, RegionOfInterests=[r],
                    PointsOfInterests=[]
                )
            except Exception as e:
                logging.warning(f"Unable to exclude {rois} from export: {e}")


def include_in_export(case, rois):
    """Toggle export to true
    :param case: current case
    :param rois: name of structure to exclude"""

    if type(rois) is not list:
        rois = [rois]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    for r in defined_rois:
        if r in rois and case.PatientModel.RegionsOfInterest[r].ExcludeFromExport:
            try:
                case.PatientModel.ToggleExcludeFromExport(
                    ExcludeFromExport=False, RegionOfInterests=[r], PointsOfInterests=[]
                )

            except Exception as e:
                logging.warning(f"Unable to include {r} in export: {e}")


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


def exists_poi(case, pois):
    """See if rois is in the list"""
    if type(pois) is not list:
        pois = [pois]

    defined_pois = []
    for p in case.PatientModel.PointsOfInterest:
        defined_pois.append(p.Name)

    poi_exists = []

    for p in pois:
        i = 0
        exact_match = False
        if p in defined_pois:
            while i < len(defined_pois):
                if p == defined_pois[i]:
                    logging.debug(
                        f"{p} is an exact match to {defined_pois[i]}"
                    )
                    exact_match = True
                i += 1
            if exact_match:
                poi_exists.append(True)
            else:
                poi_exists.append(False)
        else:
            poi_exists.append(False)

    return poi_exists


def has_coordinates_poi(case, exam, poi):
    """See if pois have locations
    Currently this script will simply look to see if the coordinates are
    finite.

    :param case: desired RS case object from connect
    :param exam: desired RS exam object from connect
    :param poi: type(str) of an existing point of interest name

    TODO Accept an optional ROI as an input, if we have one, then
        Add a bounding box check using:
            case.PatientModel.StructureSets[exam.Name].RoiGeometries['External'].GetBoundingBox
    Usage:
        import StructureOperations
        test = StructureOperations.has_coordinates_poi(
            case=case, exam=exam, poi='SimFiducials')
    """

    poi_position = case.PatientModel.StructureSets[exam.Name].PoiGeometries[poi]
    try:
        coords = [poi_position.Point.x, poi_position.Point.y, poi_position.Point.z]
        if all(abs(c) < 1.e5 for c in coords):
            return True
        else:
            return False
    except AttributeError as e:
        e_message = "'NoneType' object has no attribute 'x'"
        if e_message in str(e):
            return False
        else:
            logging.debug(f'Unhandled exception: {e}')
            sys.exit("Script cancelled")


def find_localization_poi(case):
    # Find the localization point if it exists
    # return poi object or none
    pois = case.PatientModel.PointsOfInterest
    for p in pois:
        if p.Type == 'LocalizationPoint':
            return p
    return None


def create_poi(case, exam, coords=None, name=None, color='Green', diameter=1, rs_type='Undefined'):
    """
    Add a point of interest to the patient model in raystation
    :param case: req: <RS Case>: current case from RS
    :param exam: req: <RS Exam>: current examination
    :param coords: opt: <list>: of DICOM coordinates [x, y, z]
    :param name: opt: <str>: name of point
    :param color: opt: <Color>: color name or hex
    :param diameter: opt: <float>: diameter of point visualization in cm
    :param rs_type: opt: <str>: ROI Type Possible values;
      * Marker: Patient marker or marker on a localizer.
      * Isocenter: Treatment isocenter to be used for external beam therapy.
      * Registration.
      * Control: To be used in control of dose optimization and calculation.
      * DoseRegion: To be used as a dose reference.
      * LocalizationPoint: Laser coordinate system origin.
      * AcquisitionIsocenter: Acquisition isocenter, the position during acquisition.
      * InitialLaserIsocenter: Initial laser isocenter, the position before acquisition.
      * InitialMatchIsocenter: Initial match isocenter, the position after acquisition.
      * Undefined.

    :return: error_message: list or None
    """
    if coords:
        coordinate_dict = {"x": coords[0],
                           "y": coords[1],
                           "z": coords[2]}
    else:
        coordinate_dict = {}
        exam = None

    if not name:
        indx = 0
        while exists_poi(case=case, pois=['POI' + str(indx)]):
            indx += 1
        point_name = 'POI' + str(indx)
    else:
        point_name = name

    try:
        case.PatientModel.CreatePoi(
            Examination=exam,
            Point=coordinate_dict,
            Name=point_name,
            Color=color,
            VisualizationDiameter=diameter,
            Type=rs_type,
        )
        return None
    except Exception as e:
        logging.debug(f'Error creating point {e}')
        error_message = [str(e)]
        return error_message


def visualize_none(patient, case):
    roi_names = find_types(case=case, roi_type=None)
    for r in roi_names:
        patient.SetRoiVisibility(RoiName=r, IsVisible=False)


def check_roi(case, exam, rois):
    """ See if the provided rois has contours, later check for contiguous"""
    if type(rois) is not list:
        rois = [rois]

    roi_passes = []

    if all(exists_roi(case=case, rois=rois)):

        for r in rois:
            if (
                    case.PatientModel.StructureSets[exam.Name]
                        .RoiGeometries[r].HasContours()
            ):
                roi_passes.append(True)
            else:
                roi_passes.append(False)

        return roi_passes

    else:

        return [False]


def check_roi_imported(case, exam, rois=None):
    # Check the provided list of rois to determine which were imported
    # and which were built in Raystation
    # TODO: Figure out how mim assigns uid's and look for different import
    # histories
    # Return: Dictionary of {'Imported': [List of imported rois],
    #                        'RayStation': [List of Raystation rois]}
    if rois:
        if type(rois) is not list:
            rois = [rois]
    else:
        rois = []
        for r in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
            rois.append(r.OfRoi.Name)
    import_status = {'Imported': [], 'RayStation': []}
    for r in rois:
        if case.PatientModel.StructureSets[exam.Name] \
                .RoiGeometries[r].DicomImportHistory is None:
            import_status['RayStation'].append(r)
        else:
            import_status['Imported'].append(r)
    return import_status


def max_coordinates(case, exam, rois):
    """
    Returns the maximum coordinates of the rois as a nested dictionary, e.g.
    rois = PTV1
    a = max_coordinates(case=case, exam=exam, rois=rois)
    a['PTV1']['min_x'] = ...

    TODO: Give max Patient L/R/A/P/S/I, and consider creating a type with
    defined methods
    """
    if type(rois) is not list:
        rois = [rois]

    if any(exists_roi(case, rois)):
        logging.warning(
            f"Maximum Coordinates of ROI: {rois}"
            + "could NOT be determined. ROI does not exist"
        )
        return None

    logging.debug(f"Determining maximum coordinates of ROI: {rois}")

    ret = (
        case.PatientModel.StructureSets[exam.Name]
        .RoiGeometries[rois]
        .SetRepresentation(Representation="Contours")
    )
    logging.debug(f"ret of operation is {ret}")

    max_roi = {}

    for r in rois:
        x = []
        y = []
        z = []

        contours = (
            case.PatientModel.StructureSets[exam]
            .RoiGeometries[rois]
            .PrimaryShape.Contours
        )

        for contour in contours:
            for point in contour:
                x.append(point.x)
                y.append(point.y)
                z.append(point.z)

        max_roi[r] = {
            "min_x": min(x),
            "max_x": max(x),
            "max_y": min(y),
            "min_y": max(y),
            "min_z": min(z),
            "max_z": max(z),
        }
        return max_roi


def get_color_from_roi(case, roi_name):
    """get a system color and return rgb list """
    sys_col = case.PatientModel.RegionsOfInterest[roi_name].Color
    return [int(sys_col.R), int(sys_col.G), int(sys_col.B)]


def define_sys_color(rgb):
    """ Takes an rgb list and converts to a Color object useable by RS
    :param rgb: an rgb color list, e.g. [128, 132, 256]
    :return Color object"""
    return System.Drawing.Color.FromArgb(255, rgb[0], rgb[1], rgb[2])


def change_to_263_color(case, roi_name, df_rois=None):
    """
    case: rs case
    roi_name: str: Name of ROI
    df_rois: Pandas dataframe defined with elements from the
    iter_standard_roi function
    """
    if df_rois is None:
        files = [
            [r"../protocols", r"", r"TG-263.xml"]
        ]  # , [r"../protocols", r"UW", r""]]
        paths = []
        for i, f in enumerate(files):
            secondary_protocol_folder = f[0]
            institution_folder = f[1]
            paths.append(
                os.path.join(
                    os.path.dirname(__file__),
                    secondary_protocol_folder,
                    institution_folder,
                )
            )
        tree = Et.parse(os.path.join(paths[0], files[0][2]))
        rois_dict = iter_standard_rois(tree)
        df_rois = pd.DataFrame(rois_dict["rois"])

    df_e = df_rois[df_rois.name == roi_name]
    if df_e.RGBColor.values[0] is not None:
        e_rgb = [int(x) for x in df_e.RGBColor.values[0]]
        msg = change_roi_color(case=case, roi_name=roi_name, rgb=e_rgb)
        return msg
    else:
        msg = f"Could not find {roi_name} in TG-263 list"


def change_roi_color(case, roi_name, rgb):
    """
    Change the color of an roi to a system color
    :param case: RS case object
    :param roi_name: string containing name of roi to be checked
    :param rgb: an rgb color object, e.g. [r, g, b] = [128, 132,256]
    :return error_message: None for success, or error message for error
    """
    if structure_approved(case=case, roi_name=roi_name):
        error_message = f"Structure {roi_name} is approved, cannot change color"
        return error_message
    if not all(exists_roi(case=case, rois=roi_name)):
        error_message = f"Structure {roi_name} could not be changed to " \
                        f"{rgb} because it was not found in {case}"
        return error_message
    # Convert rgb list to system color
    sys_rgb = define_sys_color(rgb)
    try:
        rs_roi = case.PatientModel.RegionsOfInterest[roi_name]
        if rs_roi.Color != sys_rgb:
            rs_roi.Color = sys_rgb
            error_message = None
        else:
            error_message = f'Color for {rs_roi.Name} was already {rgb}'
    except:
        error_message = f'Unable to change color on roi {roi_name}'
    return error_message


def change_roi_type(case, roi_name, roi_type):
    """
    :param case: RS Case object
    :param roi_name: string containing roi name to be changed
    :param roi_type: type of roi to be changed to. Available types include:
    Avoidance -> OrganAtRisk
    Bolus -> Other
    BrachyAccessory -> Unknown
    BrachyChannel -> Unknown
    BrachyChannelShield -> Unknown
    BrachySourceApplicator -> Unknown
    Cavity -> Unknown
    ContrastAgent -> Unknown
    Control -> Unknown
    CTV -> Target
    DoseRegion -> Unknown
    External -> OrganAtRisk
    FieldOfView -> Unknown
    Fixation -> Other
    GTV -> Target
    IrradiatedVolume -> Unknown
    Marker -> Unknown
    Organ -> OrganAtRisk
    PTV -> Target
    Registration -> Unknown
    Support -> Other
    TreatedVolume -> Unknown
    Undefined -> Unknown
    :return error_message: None for success and error message for error
    """
    error_message = []
    type_dict = {"Other": ["Fixation", "Support"], "OrganAtRisk": ["Avoidance", "Organ"],
                 "Target": ["Ctv", "Gtv", "Ptv"], "Unknown": [
            "BrachyAccessory",
            "BrachyChannel",
            "BrachyChannelShield",
            "BrachySourceApplicator",
            "Cavity",
            "ContrastAgent",
            "Control",
            "DoseRegion",
            "FieldOfView",
            "IrradiatedVolume",
            "Marker",
            "Registration",
            "TreatedVolume",
            "Undefined",
        ]}
    # without a specified type the structure will be set to "Unknown"
    if roi_type == 'None':
        roi_type = 'Undefined'

    if structure_approved(case=case, roi_name=roi_name):
        error_message.append(
            f'Structure {roi_name} is approved, cannot change type {roi_type}'
        )
        return error_message
    if not all(exists_roi(case=case, rois=roi_name)):
        error_message.append(f'Structure {roi_name} not found on case {case}')
        return error_message
    rs_roi = case.PatientModel.RegionsOfInterest[roi_name]
    current_dicom_type = rs_roi.Type
    current_organ_type = rs_roi.OrganData.OrganType
    if roi_type == "External":
        if current_dicom_type == "External":
            error_message.append(
                f'Structure {roi_name} is already type {roi_type}'
            )
        else:
            try:
                rs_roi.SetAsExternal()
            except:
                error_message.append(
                    f'External error. Could not change {roi_name} ' +
                    f'to type {roi_type}'
                )
        return error_message
    # Set the dicom type if necessary
    if current_dicom_type == roi_type:
        error_message.append(
            f'Structure {roi_name} is already type {roi_type}'
        )
    else:
        try:
            rs_roi.Type = roi_type
        except:
            error_message.append(
                f'Unable to change type on roi {roi_name} from'
                f' Dicom type {current_dicom_type} to '
                f'type {roi_type}'
            )
    # Set the organ type if necessary
    for k, v in type_dict.items():
        if not roi_type:
            error_message.append(
                f'Could not change organ type of {roi_name} to {roi_type}')
        elif any(roi_type in types for types in v):
            if current_organ_type == k:
                error_message.append(
                    f"Structure {roi_name} is already "
                    f"organ type {current_organ_type}"
                )
            else:
                try:
                    rs_roi.OrganData.OrganType = k
                except:
                    error_message.append(
                        f"Type error. Could not change {roi_name}"
                        f" to type {roi_type}"
                    )
    return error_message


def find_organs_at_risk(case):
    """
    Find all structures with OrganType "OrganAtRisk"
    and return a list
    :param: case: RS Case object
    :return: plan_oars: a list of organs at risk
    """
    # Declare return list
    plan_oars = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.OrganData.OrganType == "OrganAtRisk":
            plan_oars.append(r.Name)
    return plan_oars


def find_targets(case):
    """
    Find all structures with type 'Target' within the current case.
    Return the matches as a list
    :param case: Current RS Case
    :return: plan_targets # A List of targets
    """

    # Find RS targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.OrganData.OrganType == "Target":
            plan_targets.append(r.Name)
    # Add user threat: empty PTV list.
    if not plan_targets:
        connect.await_user_input(
            'The target list is empty.'
            + ' Please apply type PTV to the targets and continue.'
        )
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == "Target":
                plan_targets.append(r.Name)
    if plan_targets:
        return plan_targets
    else:
        sys.exit("Script cancelled")


def case_insensitive_structure_search(case, structure_name, roi_list=None):
    """
    Check if a case insensitive match to the structure_name exists and
    return the name or None
    :param case: raystation case
    :param structure_name:structure name to be tested
    :param roi_list: list of rois to look in, if not specified, use all rois
    :return: list of names defined in RayStation, if only one structure is found return a string
             or [] if no match was found.
    """
    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r.OfRoi.Name not in roi_list:
                    roi_list.append(r.OfRoi.Name)

    matched_rois = []
    for current_roi in roi_list:
        if re.search(r"^" + structure_name + "$", current_roi, re.IGNORECASE):
            if not re.search(r"^" + structure_name + "$", current_roi):
                matched_rois.append(current_roi)
    if len(matched_rois) == 1:
        matched_rois = matched_rois[0]
    return matched_rois


def exams_containing_roi(case, structure_name, roi_list=None, exam=None):
    """
        See if structure has contours on this exam, if no exam is supplied
        search all examinations in the case
        Verify if a structure with the exact name specified exists or not
        :param case: Current RS case
        :param structure_name: the name of the structure to be confirmed
        :param roi_list: a list of available ROI's as RS RoiGeometries to
                         check against
        :param exam: An RS Script Object for the examination
        :return: roi_found list of exam names (keys) in which roi has contours
    """
    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r not in roi_list:
                    roi_list.append(r)
    # If no exam is supplied build a list of all examination names
    exam_list = []
    if exam == None:
        for e in case.Examinations:
            exam_list.append(e.Name)
    else:
        exam_list = [exam.Name]

    roi_found = []

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        for e in exam_list:
            logging.debug(
                f'Exam is {e} with type {type(e)} '
                f'for structure {structure_name} with '
                f'type {type(structure_name)}'
            )
            ss = case.PatientModel.StructureSets[e]
            rg = ss.RoiGeometries[structure_name]
            logging.debug(f"type ss {ss} and rg {rg}")
            e_has_contours = (
                case.PatientModel.StructureSets[e]
                .RoiGeometries[structure_name]
                .HasContours()
            )
            if e_has_contours:
                roi_found.append(e)
    return roi_found


def check_structure_exists(
        case, structure_name, roi_list=None,
        option="Check", exam=None):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: a list of available ROIs as RS RoiGeometries to check
                     against
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
        Wait - prompt user to create structure if not found
    :param exam: Current RS exam, if supplied the script deletes geometry only,
                 otherwise contour is deleted
    :return: Logical - True if structure is present in ROI List,
                       False otherwise
    """

    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r not in roi_list:
                    roi_list.append(r)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if exam is not None:
            structure_has_contours_on_exam = (
                case.PatientModel.StructureSets[exam.Name]
                .RoiGeometries[structure_name]
                .HasContours()
            )
        else:
            structure_has_contours_on_exam = False

        if option == "Delete":
            if structure_has_contours_on_exam:
                case.PatientModel.StructureSets[exam.Name].RoiGeometries[
                    structure_name
                ].DeleteGeometry()
                logging.warning(f"{structure_name} found - deleting geometry")
                return False
            else:
                case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
                logging.warning(f"{structure_name} found - "
                                f"deleting and creating")
                return True
        elif option == "Check":
            if exam is not None and structure_has_contours_on_exam:
                return True
            elif exam is not None:
                return False
            else:
                return True
        elif option == "Wait":
            if structure_has_contours_on_exam:
                return True
            else:
                logging.info(
                    f"Structure {structure_name} not found on "
                    f"exam {exam.Name}, prompted user to create")
                connect.await_user_input(
                    f"Create the structure {structure_name} "
                    f"and continue script.")
    else:
        return False


def convert_poi(poi1):
    """
    Return a poi as a numpy array
    :param poi1:
    :return: poi_arr
    """

    poi_arr = np.array([poi1.Point.x, poi1.Point.y, poi1.Point.z])
    return poi_arr


def check_overlap(patient, case, exam, structure, rois):
    """
    Checks the overlap of structure with the roi list defined in rois.
    Returns the volume of overlap
    :param: patient: RS patient object
    :param exam: RS exam object
    :param case: RS Case object
    :param structure: List of target structures for overlap
    :param rois: List of structures which will be checked for overlap with structure
    :return: vol
    """
    exist_list = exists_roi(case, rois)
    roi_index = 0
    rois_verified = []
    # Check all incoming rois to see if they exist in the list
    for r in exist_list:
        if r:
            rois_verified.append(rois[roi_index])
        roi_index += 1
    logging.debug(
        f"Found the following in evaluation of overlap with {structure}: "
    )

    overlap_name = "z_overlap"
    for r in structure:
        overlap_name += "_" + r

    overlap_defs = {
        "StructureName": overlap_name,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": [192, 192, 192],
        "OperationA": "Union",
        "SourcesA": structure,
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": rois_verified,
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "Intersection",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    make_boolean_structure(patient=patient, case=case, examination=exam, **overlap_defs)
    vol = None
    try:
        t = case.PatientModel.StructureSets[exam.Name].RoiGeometries[overlap_name]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.info(f"{overlap_name} has no contours, index undefined")
    except:
        logging.warning(
            f"Error getting volume for {overlap_name}, volume => 0.0"
        )

    logging.debug(f"Calculated volume of overlap of {overlap_name} is {vol}")
    case.PatientModel.RegionsOfInterest[overlap_name].DeleteRoi()
    return vol


def compute_comparison_statistics(
        patient, case, exam,
        rois_a, rois_b, compute_distances=False):
    """
    Compute the statistics of the overlap with a structure and the input rois
    Returns the volume of overlap
    :param: patient: RS patient object
    :param exam: RS exam object
    :param case: RS Case object
    :param rois_a: List of target structures for overlap
    :param rois_b: List of structures which will be checked for overlap with structure
    :return: stats: dictionary containing:
        {
         'DiceSimilarityCoefficient': float: 2 | ROIA intersect ROIB | / | ROIA | + | ROIB |
         'Precision': float: ROIA intersect ROIB | / | ROIA union ROIB |
         'Sensitivity': float: 1 - | ROIB not ROIA | / | ROIA |
         'Specificity': float: | ROIA intersect ROIB | / | ROIA |
         'MeanDistanceToAgreement': float: Mean distance to agreement computed from average of
         minimum voxel distances
         'MaxDistanceToAgreement': float: Maximum of minimum distances between voxels (Hausdorff)
         }
    """
    exist_list_a = exists_roi(case, rois_a)
    exist_list_b = exists_roi(case, rois_b)
    roi_index = 0
    rois_verified_a = []
    rois_verified_b = []
    # Check all incoming rois to see if they exist in the list
    for r in exist_list_a:
        if r:
            rois_verified_a.append(rois_a[roi_index])
            roi_index += 1

    # Check all incoming rois to see if they exist in the list
    roi_index = 0
    for r in exist_list_b:
        if r:
            rois_verified_b.append(rois_b[roi_index])
            roi_index += 1
    logging.debug(
        f"Found the following in evaluation of overlap with "
        f"{rois_verified_a} and {rois_verified_b} "
    )

    a_union_name = "z_a_union"
    b_union_name = "z_b_union"
    if len(rois_verified_a) > 1:
        a_union_defs = {
            "StructureName": a_union_name,
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Union",
            "SourcesA": rois_verified_a,
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=exam, **a_union_defs
        )
    else:
        a_union_name = rois_verified_a[0]
    if len(rois_verified_b) > 1:
        b_union_defs = {
            "StructureName": b_union_name,
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Union",
            "SourcesA": rois_verified_b,
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=exam, **b_union_defs
        )
    else:
        b_union_name = rois_verified_b[0]
    # Compute the stats
    stats = case.PatientModel.StructureSets[exam.Name].ComparisonOfRoiGeometries(
        RoiA=a_union_name,
        RoiB=b_union_name,
        ComputeDistanceToAgreementMeasures=compute_distances,
    )
    if len(rois_verified_a) > 1:
        case.PatientModel.RegionsOfInterest[a_union_name].DeleteRoi()
    if len(rois_verified_b) > 1:
        case.PatientModel.RegionsOfInterest[b_union_name].DeleteRoi()

    return stats


def find_types(case, roi_type=None):
    """
    Return a list of all structures that in exist in the roi list with type roi_type
    :param patient:
    :param case: RS case
    :param type: string from any of the following choices:
                 Avoidance, Bolus, BrachyAccessory, BrachyChannel, BrachyChannelShield,
                 BrachySourceApplicator, Cavity, ContrastAgent, Control, Ctv,
                 DoseRegion, External, FieldOfView, Fixation, Gtv,
                 IrradiatedVolume, Marker, Organ, Ptv, Registration, Support,
                 TreatedVolume, Undefined,
    :return: found_roi
    """
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_type is None:
            found_roi.append(r.Name)
        elif r.Type == roi_type:
            found_roi.append(r.Name)
    return found_roi


def translate_roi(case, exam, roi, shifts):
    """
    Translate (only) an roi according to the shifts
    :param case:
    :param exam:
    :param roi:
    :param shifts: a dictionary containing shifts, e.g.
        shifts = {'x': 1.0, 'y':1.0, 'z':1.0} would shift in each direction 1 cm
    :return: centroid of shifted roi
    """
    x = shifts["x"]
    y = shifts["y"]
    z = shifts["z"]
    transform_matrix = {
        "M11": 1, "M12": 0, "M13": 0, "M14": x,
        "M21": 0, "M22": 1, "M23": 0, "M24": y,
        "M31": 0, "M32": 0, "M33": 1, "M34": z,
        "M41": 0, "M42": 0, "M43": 0, "M44": 1,
    }
    case.PatientModel.RegionsOfInterest["TomoCouch"].TransformROI3D(
        Examination=exam, TransformationMatrix=transform_matrix
    )


def levenshtein_match(item, arr, num_matches=None):
    """[match,dist]=__levenshtein_match(item,arr)"""

    # Initialize return args
    if num_matches is None:
        num_matches = 1

    dist = [max(len(item), min(map(len, arr)))] * num_matches
    match = [None] * num_matches

    # Loop through array of options
    for a in arr:
        v0 = list(range(len(a) + 1)) + [0]
        v1 = [0] * len(v0)
        for b in range(len(item)):
            v1[0] = b + 1
            for c in range(len(a)):
                if item[b].lower() == a[c].lower():
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c])

                else:
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c] + 1)

            v0, v1 = v1, v0

        for i, d in enumerate(dist):
            if v0[len(a)] < d:
                dist.insert(i, v0[len(a)])
                dist.pop()
                match.insert(i, a)
                match.pop()
                break

    return match, dist


def find_normal_structures_match(rois, standard_rois, num_matches=None):
    """
    Return a unique structure dictionary from supplied element tree
    :param rois: a list of rois to be matched
    :param standard_rois: a dict keyed by the rois standard name with an unsorted list of aliases
    :param num_matches: the number of matches to return
    :return: matched_rois : a dict of form { Roi1: [Exact match, Close match, ...], where
                            exact match and close match are determined by Levenshtein distance or
                            aliases (previously determined synonyms) for this structure
    """
    match_threshold = 0.6  # Levenshtein match distance
    # If the number of matches to return is not specified, then return the best match
    if num_matches is None:
        num_matches = 1

    standard_names = []
    aliases = {}
    for n, a in standard_rois.items():
        standard_names.append(n)
        if a is not None:
            aliases[n] = a
    matched_rois = {}  # return variable described above
    # alias_distance
    #   An arbitrary number < 1 meant to indicate a distance match that is better
    #   than the levenshtein because it is an alias
    alias_distance = 0.001
    for r in rois:
        [match, dist] = levenshtein_match(r, standard_names, num_matches)
        matched_rois[r] = []
        # unsorted_matches
        #   Dict object: {Key: [(Match distance, Match name),
        #                       (Match distance, MatchName2),
        #                       ... num_matches}
        unsorted_matches = []
        # Create an ordered list. If there is an exact match,
        # make the first element in the ordered list that.
        for a_key, a_val in aliases.items():
            [alias_match, alias_dist] = levenshtein_match(r, a_val, num_matches)
            if any(ad < len(r) * 0.5 * match_threshold for ad in alias_dist):
                lr_mismatch = False
                # If the structure has a laterality indication,
                # don't return results that contain the opposite laterality
                # Look for _L_, $_L, ^L_
                re_r = re.compile(r'.*_R$|^R_.*|.*_R_.*')
                re_l = re.compile(r'.*_L$|^L_.*|.*_L_.*')
                if re_l.match(a_key) and re_r.match(r):
                    lr_mismatch = True
                if re_r.match(a_key) and re_l.match(r):
                    lr_mismatch = True
                if not lr_mismatch:
                    unsorted_matches.append((alias_distance, a_key))
        for i, d in enumerate(dist):
            if d < len(r) * match_threshold:
                # Return Criteria
                lr_mismatch = False
                # Continue checking the current elements in the match list if there is not already
                # an entry for this organ in our output
                if match[i] not in matched_rois[r]:
                    # If the structure has a laterality indication,
                    # don't return results that contain the opposite laterality
                    # Look for _L_, $_L, ^L_
                    re_r = re.compile(r'.*_R$|^R_.*|.*_R_.*')
                    re_l = re.compile(r'.*_L$|^L_.*|.*_L_.*')
                    if re_l.match(a_key) and re_r.match(r):
                        lr_mismatch = True
                    if re_r.match(a_key) and re_l.match(r):
                        lr_mismatch = True
                    if not lr_mismatch:
                        unsorted_matches.append((d, match[i]))
        sorted_matches = sorted(unsorted_matches, key=lambda m: m[0])
        # If the aliasing and matching produced nothing, then
        # add a blank element to the beginning of the sorted list
        if not sorted_matches:
            sorted_matches.append((0, ""))
        elif sorted_matches[0][0] > alias_distance:
            sorted_matches.insert(0, (0, ""))
        matched_rois[r] = sorted_matches

    return matched_rois


def filter_rois(plan_rois, skip_targets=True, skip_planning=True):
    """
    Filters the plan rois for structures that may not need matching and eliminates duplicates
    :param plan_rois:
    :param skip_targets:
    :param skip_planning:
    :return: filtered_rois
    """

    regex_list = []
    if skip_targets:
        regex_list.extend(TARGET_EXPRESSIONS)
    if skip_planning:
        regex_list.extend(PLANNING_EXPRESSIONS)
    # Given the above arguments, filter the list using the regex and return the result
    filtered_rois = []
    for r in plan_rois:
        filter_roi = False
        for exp in regex_list:
            if re.match(exp, r):
                filter_roi = True
        if r not in filtered_rois and not filter_roi:
            filtered_rois.append(r)
    return filtered_rois


def find_gui_match(name, elements, df_rois=None):
    """
    Parse the roi dataframe for the name match
    :param elements: raw values read in from xml
    :param name: name of roi
    :param df_rois: dataframe read in from TG-263.xml
    :return: None if no value was submitted in name [Unmatched]

    """
    if not name:
        return None
    found_index = None
    # First try to match to a dataframe element
    if df_rois is not None:
        df_e = df_rois[df_rois.name == name]
        # If more than one result is returned by the dataframe search report an error
        if len(df_e) > 1:
            logging.warning(f"Too many matching {name}. That makes me a sad panda. :(")
        elif df_e.empty:
            logging.debug(f"{name} was not found in the protocol list")
        else:
            return df_e
    # Try matching to the xml elements directly
    if found_index is None:
        for e_index, standard_rois in enumerate(elements):
            if standard_rois.find("name").text == name:
                return elements[found_index]
    return name


def match_gui(matches, elements, df_rois=None):
    dialog_name = 'Structure Matching and Derived ROI Generation'
    frames = ['-FRAME SUFFIX-', '-FRAME ALT SCHEME-', '-FRAME MATCHING-']
    color_schemes = ['CLINICAL', 'SRS MultiTarget']
    match_row = []
    for k, v in matches.items():
        attr = {'values': [x[1] for x in v],
                'size': (30, 1),
                'default_value': v[0][1],
                'key': k}
        match_row.append([sg.Text(k), sg.Combo(**attr)])
    sg.ChangeLookAndFeel('DarkBlue1')
    top = [
        [sg.Text(
            dialog_name,
            size=(60, 1),
            justification='center',
            font=("Helvetica", 16),
            relief=sg.RELIEF_RIDGE
        )],

        [
            sg.Text(f'Match structures to TG-263 Formalism')
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Combo(
                            color_schemes,
                            default_value=color_schemes[0],
                            size=(30, 1),
                            key="-COLOR SCHEME-"
                        )
                    ],
                ],
                title='Color Selection',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a color template',
                key=frames[1]
            ),
        ],
        [sg.Frame(
            layout=[
                [sg.Text(
                    'Suffix to be used for any structure that cannot be renamed, e.g. _A for '
                    'adaptive')],
                [sg.InputText('_A', key='-SUFFIX-')]
            ],
            title='Existing Structures',
            relief=sg.RELIEF_SUNKEN,
            visible=True,
            key=frames[0]
        )],
        [sg.Frame(
            layout=match_row,
            title='Unmatched Structures',
            relief=sg.RELIEF_SUNKEN,
            tooltip='Match each structure or type in correct name',
            visible=True,
            key=frames[2]
        )],
    ]
    bottom = [
        [
            sg.Submit(tooltip='Click to submit this window'),
            sg.Cancel()
        ]
    ]
    layout = [[sg.Column(top)], [sg.Column(bottom)]]

    window = sg.Window(
        'Matchy Matchy',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    submitted = False  # Flag to track if the Submit button was clicked

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            logging.info("Matching dialog cancelled by user")
            sys.exit("Matching Dialog Cancelled")
        elif event == "Submit":
            submitted = True
            suffix = values['-SUFFIX-']
            values.pop('-SUFFIX-')
            color_scheme = values['-COLOR SCHEME-']
            values.pop('-COLOR SCHEME-')
            responses = {k: values[k] for k in matches.keys()}
            break
    window.close()

    # Check if the Submit button was clicked and if any changes were made
    if not submitted and not any(responses.values()):
        logging.info("Matching dialog cancelled by user")
        raise RuntimeError("Matching Dialog Cancelled")
    dialog_result = {}
    for r, m in responses.items():
        dialog_result[r] = find_gui_match(m, elements, df_rois)
    return suffix, color_scheme, dialog_result


def iter_standard_rois(etree):
    """
    Load the contents of a roi object from xml into a pandas dataframe
    :param etree:
    :return: rois
    """
    rois = {"rois": []}
    for r in etree.iter("roi"):
        roi = {}
        try:
            roi["name"] = r.find("name").text
        except AttributeError:
            roi["name"] = None
        try:
            roi["TG263PrimaryName"] = r.find("TG263PrimaryName").text
        except AttributeError:
            roi["TG263PrimaryName"] = None
        try:
            roi["Description"] = r.find("Description").text
        except AttributeError:
            roi["Description"] = None
        try:
            roi["TargetType"] = r.find("TargetType").text
        except AttributeError:
            roi["TargetType"] = None
        try:
            roi["RTROIInterpretedType"] = str(
                r.find("RTROIInterpretedType").text
            ).capitalize()
        except AttributeError:
            roi["RTROIInterpretedType"] = None
        try:
            roi["MajorCategory"] = r.find("MajorCategory").text
        except AttributeError:
            roi["MajorCategory"] = None
        try:
            roi["MinorCategory"] = r.find("MinorCategory").text
        except AttributeError:
            roi["MinorCategory"] = None
        try:
            roi["AnatomicGroup"] = r.find("AnatomicGroup").text
        except AttributeError:
            roi["AnatomicGroup"] = None
        try:
            roi["NCharacters"] = r.find("NCharacters").text
        except AttributeError:
            roi["NCharacters"] = None
        try:
            roi["TG263ReverseOrderName"] = r.find("TG263ReverseOrderName").text
        except AttributeError:
            roi["TG263ReverseOrderName"] = None
        try:
            dependencies = r.find("Dependencies").text.replace(" ", "")
            dependencies = dependencies.strip()
            roi["Dependencies"] = dependencies.split(",")
        except AttributeError:
            roi["Dependencies"] = None

        derived = ["A", "B", "Result"]
        for d in derived:
            if d == "Result":
                source_key = d
                exp_key = "ExpR"
                margin_key = "MarginTypeR"
            else:
                source_key = "Sources" + d
                exp_key = "Exp" + d
                margin_key = "MarginType" + d
            operation_key = "Operation" + d
            try:
                if r.find(source_key).text:
                    strip_source_key = r.find(source_key).text.replace(" ", "")
                    strip_source_key = strip_source_key.strip()
                    roi[source_key] = strip_source_key.split(",")
                else:
                    roi[source_key] = []
                    # roi[source_key] = ['Hi my name is WHO my name is WHAT']
            except AttributeError:
                roi[source_key] = []
            try:
                roi[operation_key] = r.find(source_key).attrib["operation"]
            except AttributeError:
                roi[operation_key] = None
            # Set the Margin Type
            try:
                roi[margin_key] = r.find(source_key).attrib["margin_type"]
            except AttributeError:
                roi[margin_key] = None
            # Set the expansion
            try:
                roi[exp_key] = [
                    float(r.find(source_key).attrib["margin_sup"]),
                    float(r.find(source_key).attrib["margin_inf"]),
                    float(r.find(source_key).attrib["margin_ant"]),
                    float(r.find(source_key).attrib["margin_pos"]),
                    float(r.find(source_key).attrib["margin_r"]),
                    float(r.find(source_key).attrib["margin_l"]),
                ]
            except AttributeError:
                roi[exp_key] = []

        try:
            if r.find("Export").text == "False":
                roi["ExcludeExport"] = True
            else:
                roi["ExcludeExport"] = False
        except AttributeError:
            roi["ExcludeExport"] = False
        except TypeError:
            roi["ExcludeExport"] = False

        try:
            roi["FMAID"] = r.find("FMAID").text
        except AttributeError:
            roi["FMAID"] = None
        try:
            roi["Color"] = r.find("Color").text
            # RGBColor will be a list of [r, g, b], it gets converted using
            # [r, g, b] : [int(x) for x in df_e.RGBColor.values[0]]
            if roi["Color"] is not None:
                roi["RGBColor"] = [
                    r.find("Color").attrib["red"],
                    r.find("Color").attrib["green"],
                    r.find("Color").attrib["blue"],
                ]
            else:
                roi["RGBColor"] = None
        except AttributeError:
            roi["Color"] = None
            roi["RGBColor"] = None
        try:
            strip_alias = r.find("Alias").text.replace(" ", "")
            strip_alias = strip_alias.strip()
            roi["Alias"] = strip_alias.split(",")
        except AttributeError:
            roi["Alias"] = None
        rois["rois"].append(roi)
    return rois


# noinspection PyPep8Naming
def check_derivation(case, **kwargs):
    """
    Will need an existing structure where StructureName is
    TODO: Write a check_derivation for "Wall types"
    """
    StructureName = kwargs.get("StructureName")
    SourcesA = kwargs.get("SourcesA")
    MarginTypeA = kwargs.get("MarginTypeA")
    ExpA = kwargs.get("ExpA")
    OperationA = kwargs.get("OperationA")
    SourcesB = kwargs.get("SourcesB")
    MarginTypeB = kwargs.get("MarginTypeB")
    ExpB = kwargs.get("ExpB")
    OperationB = kwargs.get("OperationB")
    MarginTypeR = kwargs.get("MarginTypeR")
    ExpR = kwargs.get("ExpR")
    OperationResult = kwargs.get("OperationResult")
    logging.debug(f"Checking {StructureName} derived status")
    # Build a map to the structures used in the RS algebra
    test_structure = case.PatientModel.RegionsOfInterest[StructureName]
    result_operations = test_structure.DerivedRoiExpression
    # If the current expression is None, the structure has no derived status
    if result_operations is None:
        logging.debug("current_margins is None")
        return False
    try:
        if result_operations.ExpandContractType != MarginTypeR:
            logging.debug("Result expand contract type mismatch")
            return False
        if result_operations.SuperiorDistance != ExpR[0]:
            logging.debug("Result superior distance")
            return False
        if result_operations.InferiorDistance != ExpR[1]:
            logging.debug("Result inferior distance")
            return False
        if result_operations.AnteriorDistance != ExpR[2]:
            logging.debug("Result anterior distance")
            return False
        if result_operations.PosteriorDistance != ExpR[3]:
            logging.debug("Result posterior distance")
            return False
        if result_operations.RightDistance != ExpR[4]:
            logging.debug("Result right distance")
            return False
        if result_operations.LeftDistance != ExpR[5]:
            logging.debug("Result left distance")
            return False
    except AttributeError:
        logging.debug(
            f'Structure {StructureName} does not have a/b/result '
            f'attributes, no check performed')
        return False  # remake struct
    # Check A/B operation
    try:
        if result_operations.Children[0].Operation != OperationResult:
            logging.debug("A/B operation")
            return False
    except AttributeError:
        if OperationResult != "None":
            logging.debug("A/B operation should have been something")
            return False
    # Check the expansion type and distances for A
    current_a_margins = result_operations.Children[0]
    # Load the children of A into an expression
    current_a_expression = current_a_margins.Children[0]
    # Expansions have margins and ExpandContractTypes
    try:
        if current_a_margins.ExpandContractType != MarginTypeA:
            logging.debug("A expand contract type")
            return False
    except AttributeError:
        if (
                MarginTypeA is not None
                and current_a_expression.ExpandContractType != MarginTypeA
        ):
            logging.debug("A expand/contract type expected to be something")
            return False
    try:
        if current_a_margins.SuperiorDistance != ExpA[0]:
            logging.debug("A superior distance")
            return False
        if current_a_margins.InferiorDistance != ExpA[1]:
            logging.debug("A I distance")
            return False
        if current_a_margins.AnteriorDistance != ExpA[2]:
            logging.debug("A Anterior distance")
            return False
        if current_a_margins.PosteriorDistance != ExpA[3]:
            logging.debug("A Posterior distance")
            return False
        if current_a_margins.RightDistance != ExpA[4]:
            logging.debug("A Right distance")
            return False
        if current_a_margins.LeftDistance != ExpA[5]:
            logging.debug("A left distance")
            return False
    except AttributeError:
        if ExpA:
            logging.debug("A expansion was expected to be defined")
            return False
            # Check the A structures and combinations
    if current_a_expression.Operation != OperationA:
        logging.debug("A operation")
        return False
    # Create a for loop over the children in A which should have the
    # A Sources in somewhere in their children
    a_rois = []
    for a in current_a_expression.Children:
        a_rois.append(a.RegionOfInterest.Name)
    if set(a_rois) != set(SourcesA):
        logging.debug(f"ASource ROIS {SourcesA} differ from RS {a_rois}")
        return False
    # Check the expansion type and distances for B
    try:
        current_b_margins = result_operations.Children[0].Children[1]
        current_b_expression = current_b_margins.Children[0]
        if current_b_margins.ExpandContractType != MarginTypeB:
            logging.debug("B expand contract type")
            return False
        if current_b_margins.SuperiorDistance != ExpB[0]:
            logging.debug("B Sup distance")
            return False
        if current_b_margins.InferiorDistance != ExpB[1]:
            logging.debug("B Inf distance")
            return False
        if current_b_margins.AnteriorDistance != ExpB[2]:
            logging.debug("B Ant distance")
            return False
        if current_b_margins.PosteriorDistance != ExpB[3]:
            logging.debug("B Post distance")
            return False
        if current_b_margins.RightDistance != ExpB[4]:
            logging.debug("B right distance")
            return False
        if current_b_margins.LeftDistance != ExpB[5]:
            logging.debug("B left distance")
            return False
        # Check the A structures and combinations
        if current_b_expression.Operation != OperationB:
            logging.debug("B operation")
            return False
        b_rois = []
        for b in current_b_expression:
            b_rois.append(b.RegionOfInterest.Name)
        if set(b_rois) != set(SourcesB):
            logging.debug(f"BSource ROIS {SourcesB} differ from RS {b_rois}")
            return False
    except:
        if SourcesB:
            logging.debug("B source list is empty in RS")
            return False
    # If after all that, we haven't returned, then it must be true
    return True


def create_prv(patient, case, examination, source_roi, df_TG263):
    """
    :param case: RS Case Object
    :param examination: RS Examination
    :param source_roi: name of the structure to find a match to
    :param df_TG263: dataframe for the TG-263 database (loaded with iter_standard_rois)
    """
    # df_source_roi = df_TG263[df_TG263.name == source_roi]
    regex_prv = r"^" + source_roi + r"_PRV\d{2}$"
    df_prv = df_TG263[df_TG263.name.str.match(regex_prv) == True]
    msg = []
    # If one or more PRVxx structure is found, loop over all rows in the matching
    # DataFrame
    if not df_prv.empty:
        for i, r in df_prv.iterrows():
            parsed_name = df_prv.loc[[i]].name.str.extract(
                r"([a-zA-z_]+)([0-9]+)", re.IGNORECASE, expand=True
            )
            expansion_mm = int(parsed_name[1])
            expansion_cm = expansion_mm / 10.0
            prv_name = df_prv.loc[[i]].name.values[0]
            if df_prv.loc[[i]].RGBColor.values[0] is not None:
                prv_rgb = [int(x) for x in df_prv.loc[[i]].RGBColor.values[0]]
            else:
                prv_rgb = None
            if df_prv.loc[[i]].RTROIInterpretedType.values[0] is not None:
                prv_type = df_prv.loc[[i]].RTROIInterpretedType.values[0]
            else:
                prv_type = None
            if df_prv.loc[[i]].ExcludeExport.values[0] is not None:
                logging.debug(f"Export has a value {df_prv.loc[[i]].ExcludeExport.values[0]}, " +
                              f"type {type(df_prv.loc[[i]].ExcludeExport.values[0])}")
                export = df_prv.loc[[i]].ExcludeExport.values[0]
            else:
                logging.debug('No export value')
                export = False

            prv_exp_defs = {
                "StructureName": prv_name,
                "ExcludeFromExport": export,
                "VisualizeStructure": False,
                "StructColor": prv_rgb,
                "OperationA": "Union",
                "SourcesA": [source_roi],
                "MarginTypeA": "Expand",
                "ExpA": [expansion_cm] * 6,
                "OperationB": "Union",
                "SourcesB": [],
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "None",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": prv_type,
            }
            if any(exists_roi(case=case, rois=prv_name)):
                roi_geom = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                    prv_name
                ]
            else:
                roi_geom = create_roi(
                    case=case,
                    examination=examination,
                    roi_name=prv_name,
                    delete_existing=True,
                )

            if roi_geom is not None:
                make_boolean_structure(
                    patient=patient, case=case, examination=examination, **prv_exp_defs
                )
            else:
                msg.append(f"Unable to create {prv_name}")
    else:
        msg.append(f"{source_roi} does not need a planning risk volume")
    return msg


def create_derived(patient, case, examination, roi, df_rois, roi_list=None):
    """
    Function to search the df_TG263 pandas dataframe for each element in the source rois list.
    Follow the directions of the derived tags
    """
    msg = []
    if roi_list is None:
        roi_list = find_types(case=case, roi_type=None)
    # Filter the dataframe for the dependencies that are not empty
    df_ne = df_rois[df_rois.Dependencies.notnull()]
    logging.debug(f"{df_ne.to_string()}")
    # Find the dataframe rows for which the dependency element is a subset of the roi_list
    df_needs_derived = df_ne[
        df_ne["Dependencies"].apply(lambda x: set(x).issubset(set(roi_list)))
    ]
    if not df_needs_derived.empty:
        for index, row in df_needs_derived.iterrows():
            derived_roi_name = row["name"]
            logging.debug(
                f"{derived_roi_name} has all dependencies. Checking derived status"
            )
            # If the operation is a subtraction, then check to see if the result will have a volume
            if (
                    row.OperationResult == "Subtraction"
                    and all(r == 0 for r in row.ExpR)
                    and all(a == 0 for a in row.ExpA)
                    and all(b == 0 for b in row.ExpB)
            ):
                specificity = []
                for a in row.SourcesB:
                    for b in row.SourcesA:
                        stats = case.PatientModel.StructureSets[
                            examination.Name
                        ].ComparisonOfRoiGeometries(
                            RoiA=a, RoiB=b, ComputeDistanceToAgreementMeasures=False
                        )
                        specificity.append(stats["Specificity"])
                if any(s != 0 for s in specificity):
                    make_derived = True
                else:
                    make_derived = False
            else:
                make_derived = True
            if row.RGBColor is not None:
                derived_roi_color = [int(x) for x in row.RGBColor]
            else:
                derived_roi_color = None
            if row.RTROIInterpretedType is not None:
                derived_roi_type = row.RTROIInterpretedType
            else:
                derived_roi_type = None
            if make_derived:
                derived_defs = {
                    "StructureName": derived_roi_name,
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    "StructColor": derived_roi_color,
                    "OperationA": row.OperationA,
                    "SourcesA": row.SourcesA,
                    "MarginTypeA": row.MarginTypeA,
                    "ExpA": row.ExpA,
                    "OperationB": row.OperationB,
                    "SourcesB": row.SourcesB,
                    "MarginTypeB": row.MarginTypeB,
                    "ExpB": row.ExpB,
                    "OperationResult": row.OperationResult,
                    "MarginTypeR": row.MarginTypeR,
                    "ExpR": row.ExpR,
                    "StructType": derived_roi_type,
                }
                if any(exists_roi(case=case, rois=derived_roi_name)):
                    roi_geom = case.PatientModel.StructureSets[
                        examination.Name
                    ].RoiGeometries[derived_roi_name]
                else:
                    roi_geom = create_roi(
                        case=case,
                        examination=examination,
                        roi_name=derived_roi_name,
                        delete_existing=True,
                    )

                if roi_geom is not None:
                    make_boolean_structure(
                        patient=patient,
                        case=case,
                        examination=examination,
                        **derived_defs
                    )
                    # TODO check if its empty and then delete it if has no contours on any exam
                    # If subtraction and If A/B are both zero just check the Dice coefficient of
                    # each contour in Source A with source B.
                    msg.append(f"{derived_roi_name} created.")
                else:
                    msg.append(f"Unable to create {derived_roi_name}")
            else:
                logging.debug(f"No Derived necessary for {derived_roi_name}")
        return msg
    else:
        msg.append(f"{roi} does not need any derived structures")
        return msg


def match_roi(patient, case, examination, plan_rois, df_rois=None):
    """
    Matches a input list of plan_rois (user-defined) to protocol,
    if a structure set is approved or a structure already has an existing geometry
    with the potential matched structure then this will create a copy and copy the geometry
    if the geometry is copied, then the specificity and dice coefficients are checked
    outputs data to a log
    :param patient: RS Patient Object
    :param case: RS Case Object
    :param examination: RS Examination object
    :param plan_rois:
    :return: a dictionary with matched elements
    """
    epsilon = (
        1e-6  # tolerance of variation in specificity and precision (Jaccard index)
    )
    oar_list = filter_rois(plan_rois)
    if df_rois is None:
        files = [[r"../protocols", r"", r"TG-263.xml"], [r"../protocols", r"UW", r""]]
        paths = []
        for i, f in enumerate(files):
            secondary_protocol_folder = f[0]
            institution_folder = f[1]
            paths.append(
                os.path.join(
                    os.path.dirname(__file__),
                    secondary_protocol_folder,
                    institution_folder,
                )
            )
        # Generate a list of all standard names used in both protocols and TG-263
        standard_names = []
        for f in os.listdir(paths[1]):
            if f.endswith(".xml"):
                tree = Et.parse(os.path.join(paths[1], f))
                prot_rois = tree.findall(".//roi")
                for r in prot_rois:
                    if not any(i in r.find("name").text for i in standard_names):
                        standard_names.append(r.find("name").text)

        tree = Et.parse(os.path.join(paths[0], files[0][2]))
        roi263 = tree.findall("./" + "roi")
        rois_dict = iter_standard_rois(tree)
        df_rois = pd.DataFrame(rois_dict["rois"])
    # (see results using df_rois.to_string())
    # Remove the exact matches from the structure list
    del_indices = []
    return_rois = {}
    for index, e in enumerate(oar_list):
        df_e = df_rois[df_rois.name == e]
        # If more than one result is returned by the dataframe search report an error
        if len(df_e) > 1:
            logging.warning(
                f"Too many matching {e}. That makes me a sad panda. :("
                + "It is likely the protocol file contains multiple references to the same "
                  "structure"
            )
        elif df_e.empty:
            logging.debug(f"{e} was not found in the protocol list")
        else:
            e_name = df_e.name.values[0]
            return_rois[e] = e_name
            logging.debug(f"{e} matched to  {e_name} in protocol list")
            del_indices.append(index)
    # Eliminate the structures with exact matches from the search.
    for indx in sorted(del_indices, reverse=True):
        del oar_list[indx]

    # Check aliases first (look in TG-263 to see if an alias is there).
    # Currently building a list of all aliases at this point (at little inefficient)
    standard_names = {}
    aliases = {}
    # Search through the dataframe for all available aliases.
    standard_names = df_rois.set_index("name")["Alias"].to_dict()

    # Comes up with a list of up to 5 matches
    potential_matches = find_normal_structures_match(
        rois=oar_list, num_matches=5, standard_rois=standard_names
    )
    potential_matches_exacts_removed = potential_matches.copy()
    exact_match = []
    # Search the match list and if an exact match is found, pop the key
    for roi, match in potential_matches.items():
        if re.match(r"^" + roi + r"$", match[0][1]):
            potential_matches_exacts_removed.pop(roi)
            exact_match.append(match[0][1])

    # Launch the dialog to get the list of matched elements
    suffix, color_scheme, matched_rois = match_gui(matches=potential_matches_exacts_removed,
                                                   elements=roi263,
                                                   df_rois=df_rois)
    # matched_rois now contains:
    # the keys as the planning structures, and the elementtree element found to match (or None)
    for k, v in matched_rois.items():
        # If no match was made, v will be None otherwise,
        # if there is no match in the protocols, a user-supplied
        # value can be used for the name. If it was matched then
        # it is an elementree element for roi
        if v is None:
            return_rois[k] = None
            logging.debug(f"Structure {k} not matched {v}")
        else:
            # If the value is a string, then it was manually entered by the user
            if isinstance(v, str):
                # We can only set name properties as the user has given a structure name
                # with no protocol correlate
                return_rois[k] = v
                k_user_defined = True
            # If this is pandas, then grab its name
            elif type(v) is pd.core.frame.DataFrame:
                return_rois[k] = v.name.to_string(header=False, index=False).strip()
                k_user_defined = False
            # If the value is not a string, then it is an elementtree. Retrieve its name
            else:
                return_rois[k] = v.find("name").text
                k_user_defined = False
            # Does the input structure match the protocol name entirely
            logging.debug(
                f"Post match for {k}, the value is {return_rois[k]}"
            )
            if k == return_rois[k]:
                logging.debug(
                    f"{k} was matched to {return_rois[k]}. No changes necessary"
                )
            else:
                # Move the contents of k to return_rois[k]
                # Check if k is already approved on this examination
                k_is_approved = structure_approved(
                    case=case, roi_name=k, examination=examination
                )
                # Check if there is a misnamed (case insensitive match) in this patient's case
                case_insensitive_match = case_insensitive_structure_search(
                    case=case, structure_name=k
                )
                if not case_insensitive_match:
                    k_case_insensitive_match = False
                else:
                    k_case_insensitive_match = True
                    logging.debug(
                        f"Match to {k} found as {case_insensitive_match}"
                    )
                # See if the destination contour exists
                return_k_exists = check_structure_exists(
                    case=case, structure_name=return_rois[k], option="Check"
                )
                # Find all the exams which contain k
                exams_with_k = exams_containing_roi(case=case, structure_name=k)
                # If exams_with_k is empty, then no examination has contours for k
                if not exams_with_k:
                    k_contours_multiple_exams = False
                    k_empty = True
                    k_contours_this_exam = False
                else:
                    k_empty = False
                    if len(exams_with_k) > 1:
                        k_contours_multiple_exams = True
                    else:
                        k_contours_multiple_exams = False
                    # Go through the list of exams which have contours for k
                    # and see if any are exact matches
                    for e in exams_with_k:
                        k_contours_this_exam = False
                        if e == examination.Name:
                            # k has contours on this examination
                            k_contours_this_exam = True
                            break
                logging.debug(
                    f"Renaming required for matching {k} to {return_rois[k]}"
                )
                # Try to just change the name of the existing contour, but if it is locked or if the
                # desired contour already exists, we'll have to replace the geometry
                # Check to see if return_rois[k] is approved or evaluate whether
                # the correct structure already exists
                if not k_contours_this_exam:
                    #  there are no contours on this structure. So don't do anything with it
                    logging.debug(
                        f"{k} was matched to {return_rois[k]},"
                        f" but is empty on exam "
                        f"{examination.Name}"
                    )
                # if k_is_approved or k_case_insensitive_match or k_contours_multiple_exams:
                if k_is_approved or k_case_insensitive_match or return_k_exists:
                    logging.debug(
                        f"Unable to rename {k} to {return_rois[k]},"
                        f" attempting a geometry copy"
                    )
                    # Try to create the correct return roi or retrieve its existing geometry
                    roi_geom = create_roi(
                        case=case,
                        examination=examination,
                        roi_name=return_rois[k],
                        delete_existing=False,
                        suffix=suffix,
                    )
                    if roi_geom is not None:
                        # Make the geometry and validate the result
                        # TODO move this to a separate function
                        if k_contours_this_exam:
                            roi_geom.OfRoi.CreateMarginGeometry(
                                Examination=examination,
                                SourceRoiName=k,
                                MarginSettings={
                                    "Type": "Expand",
                                    "Superior": 0.0,
                                    "Inferior": 0.0,
                                    "Anterior": 0.0,
                                    "Posterior": 0.0,
                                    "Right": 0.0,
                                    "Left": 0.0,
                                },
                            )
                            # Ensure copy did not result in loss of fidelity
                            geometry_validation = case.PatientModel.StructureSets[
                                examination.Name
                            ].ComparisonOfRoiGeometries(
                                RoiA=k, RoiB=roi_geom.OfRoi.Name
                            )
                            validation_message = []
                            for metric, value in geometry_validation.items():
                                validation_message.append(
                                    str(metric) + ":" + str(value)
                                )
                            logging.debug(
                                f"Roi Geometry copied from {k} to"
                                f" {roi_geom.OfRoi.Name}. "
                                f"Resulting overlap metrics {validation_message}"
                            )
                            # k exists only on this exam, so we've copied its geometry and since its
                            if not k_contours_multiple_exams and k_contours_this_exam:
                                if (
                                        (geometry_validation["Precision"] - 1) <= epsilon
                                        and (geometry_validation["Sensitivity"] - 1)
                                        <= epsilon
                                ):
                                    case.PatientModel.RegionsOfInterest[k].DeleteRoi()
                        else:
                            if k_empty:
                                case.PatientModel.RegionsOfInterest[k].DeleteRoi()
                            logging.debug(
                                f"Roi Geometry not copied from {k} "
                                f"to {roi_geom.OfRoi.Name}. "
                                + f"since {k} does not have contours in "
                                  f"exam {examination.Name}"
                            )
                else:
                    logging.debug(f"Direct rename {k} to {return_rois[k]}")
                    case.PatientModel.RegionsOfInterest[k].Name = return_rois[k]
    return return_rois, color_scheme


def structure_approved(case, roi_name, examination=None):
    """
    Check if structure is approved anywhere in this patient, if an exam is supplied
    only the exam supplied is checked for the approved contour
    :param case: RS case
    :param roi_name: string containing name of roi
    :param examination: RS examination object
    :return: True if structure is approved somewhere
    """
    struct_exists = exists_roi(case=case, rois=roi_name)
    # If the structure is undefined, then is is not approved
    if not struct_exists:
        return False
    else:
        for s in case.PatientModel.StructureSets:
            if examination is not None and s.OnExamination.Name != examination.Name:
                continue
            else:
                for a in s.SubStructureSets:
                    try:
                        if a.Review.ApprovalStatus == 'Approved':
                            for r in a.RoiStuctures:
                                if r.OfRoi.Name == roi_name:
                                    return True
                    except AttributeError:
                        logging.debug(f"A is none {a}")
                        continue
        return False


def renumber_roi(case):
    """
    Sort the ROI list and renumber alphabetically
    """
    rois = find_types(case=case, roi_type=None)
    logging.debug(f"Unsorted list is {rois}")
    sorted_rois = sorted(rois, reverse=True)
    num_rois = len(rois)
    i = num_rois
    logging.debug(f"Sorted array is {sorted_rois}")
    for s in sorted_rois:
        case.PatientModel.RegionsOfInterest[s].RoiNumber = i
        i -= 1


def dialog_create_roi():
    """
    Dialog to ascertain the user preference of overwrite or append on a new roi with existing
    geometry

    :return: overwrite or append
    """
    dialog1 = UserInterface.InputDialog(
        inputs={
            "1": "Delete existing geometry or append a suffix",
            "2": "Suffix if needed, e.g. _R1",
        },
        title="Delete geometry or create a new structure?",
        datatype={"1": "combo", "2": "text", },
        initial={"1": "Delete Geometry", "2": "_R1"},
        options={
            "1": ["Delete Geometry", "Append Suffix"],
            #       'Primary+Boost',
            #       'Multiple Separate Targets'],
        },
        required=["1"],
    )
    dialog1_response = dialog1.show()
    if dialog1_response == {}:
        sys.exit("Unable to proceed due to existing geometry conflict")
    # Determine user responses
    if dialog1_response["1"] == "Delete Geometry":
        return None
    else:
        return dialog1_response["2"]


def create_roi(case, examination, roi_name, delete_existing=None, suffix=None):
    """
    The function create_roi performs a series of checks to determine the status of a
    structure's ROI before creating the structure or making changes. It provides an
    extensive flow of conditions to handle different scenarios of the ROI status.
    It handles the cases of when the structure or geometry doesn't exist, if it exists
    but is not approved, or if it is approved, and takes actions accordingly.

    Workflow:
    -Create it with a suffix if the geometry exists and is locked on the current examination
    Is the structure name already in use?
        *<No>  -> Make it and return the RoiGeometry on this examination
        *<Yes> Are there contours defined for roi_name in this case?
            **<No> -> return the RoiGeometry on this examination
            **<Yes> Is the geometry approved somewhere in the case?
                ***<No> Either delete it (delete_existing), or prompt the user to decide to
                delete or supply a suffix
                ***<Yes> Is the geometry approved on this exam?
                    ****<No> -> Either delete it (delete_existing),
                                or append a supplied or default suffix
                    ****<Yes> -> Return None (delete_existing),
                                 or append a supplied or default suffix
    :param case:
    :param examination:
    :param roi_name: string containing name of roi to be created
    :param delete_existing: delete any existing roi with name roi_name so long as it isn't approved
    :param suffix: append the suffix string to the name of a contour
    :return: new_structure_name: the RoiGeometries object of roi_name or its suffix-modified name
    """
    # First we want to work with the case insensitive match to the structure name supplied
    roi_name_ci = case_insensitive_structure_search(case=case, structure_name=roi_name)
    # Convert this from a list to an individual structure
    roi_name_exists = check_structure_exists(
        case=case, option="Check", structure_name=roi_name
    )
    # struct_exists is true if the roi_name is already defined
    if roi_name_ci:
        struct_exists = True
    elif roi_name_exists:
        roi_name_ci = roi_name
        struct_exists = True
    else:
        roi_name_ci = roi_name
        struct_exists = False

    # geometry_exists_in_case is True if any examination
    # in this case has contours for this roi_name_ci
    geometry_exists_in_case = check_structure_exists(
        case=case, structure_name=roi_name_ci, option="Check"
    )
    # geometry_exists is True if this examination has contours
    geometry_exists = check_structure_exists(
        case=case, structure_name=roi_name_ci, option="Check", exam=examination
    )
    # Look through all structure sets in the patient to see if
    # roi name is approved on an exam in this patient
    geometry_approved = structure_approved(
        case=case, roi_name=roi_name_ci, examination=examination
    )
    logging.debug(
        f"{roi_name_ci} defined in case: {struct_exists}, geometry exists in case: "
        f"{geometry_exists_in_case}, "
        f"geometry exists in current exam {examination.Name}: {geometry_exists}, "
        f"with approved geometry: {geometry_approved}.")

    # If the call has been made without a suffix or deletion instructions, prompt user.
    if delete_existing is None and suffix is None:
        if geometry_exists and not geometry_approved:
            # Prompt the user to make a decision between deleting existing geometry and a suffix
            suffix = dialog_create_roi()
            if suffix is None:
                delete_existing = True
            else:
                delete_existing = False

    if struct_exists:
        # Does the existing structure have any contours defined
        if geometry_exists_in_case:
            # Are the existing contours on this exam?
            if geometry_exists:
                # Is the existing geometry approved?
                if geometry_approved:
                    # TODO if delete_existing is selected, prompt the user to unapprove or quit
                    if delete_existing:
                        # Delete the existing geometry and return
                        # the empty geometry on the current exam
                        logging.debug(
                            f"Exam {examination.Name} has an "
                            f"approved geometry for {roi_name_ci}, "
                            f"cannot create new roi"
                        )
                        return None
                    else:
                        # We can't delete the existing approved geometry, so we'll need to append
                        i = 0
                        if suffix is None:
                            suffix = "_R"
                        updated_roi_name = roi_name + suffix + str(i)
                        while any(exists_roi(case=case, rois=updated_roi_name)):
                            i += 1
                            updated_roi_name = roi_name + suffix + str(i)
                        # Make a new roi using the updated name
                        case.PatientModel.CreateRoi(Name=updated_roi_name)
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[updated_roi_name]
                else:
                    # The geometry is not approved on this examination
                    if delete_existing:
                        # Delete the existing geometry and return
                        # the empty geometry on the current exam
                        _ = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                            roi_name_ci
                        ].DeleteGeometry
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[roi_name_ci]
                    else:
                        # We don't want to delete the existing geometry, so we'll need to append
                        if suffix is None:
                            suffix = "_R"
                        i = 1
                        updated_roi_name = roi_name + suffix + str(i)
                        while any(exists_roi(case=case, rois=updated_roi_name)):
                            logging.debug(
                                f"Roi {updated_roi_name} found in list."
                                f" Checking next available."
                            )
                            i += 1
                            updated_roi_name = roi_name + suffix + str(i)
                        # Make a new roi using the updated name
                        case.PatientModel.CreateRoi(Name=updated_roi_name)
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[updated_roi_name]
            else:
                # Geometry exists but not on the current exam,
                # return the empty geometry on the current exam
                return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                    roi_name_ci
                ]
        else:
            # The existing structure is empty on all exams,
            # return the empty geometry on the current exam
            return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                roi_name_ci
            ]
    else:
        # The roi does not exist, so make it and return the empty geometry for this exam
        case.PatientModel.CreateRoi(Name=roi_name_ci)
        logging.debug(
            f"{roi_name_ci} is not in the list. Creating "
            + "{}".format(
                case.PatientModel.StructureSets[examination.Name]. \
                    RoiGeometries[roi_name_ci].OfRoi.Name)
        )
        return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
            roi_name_ci
        ]


def make_boolean_structure(patient, case, examination, **kwargs):
    StructureName = kwargs.get("StructureName")
    ExcludeFromExport = kwargs.get("ExcludeFromExport")
    VisualizeStructure = kwargs.get("VisualizeStructure")
    StructColor = kwargs.get("StructColor")
    SourcesA = kwargs.get("SourcesA")
    MarginTypeA = kwargs.get("MarginTypeA")
    ExpA = kwargs.get("ExpA")
    OperationA = kwargs.get("OperationA")
    SourcesB = kwargs.get("SourcesB")
    MarginTypeB = kwargs.get("MarginTypeB")
    ExpB = kwargs.get("ExpB")
    OperationB = kwargs.get("OperationB")
    MarginTypeR = kwargs.get("MarginTypeR")
    ExpR = kwargs.get("ExpR")
    OperationResult = kwargs.get("OperationResult")
    StructType = kwargs.get("StructType")
    if "VisualizationType" in kwargs:
        VisualizationType = kwargs.get("VisualizationType")
    else:
        VisualizationType = "contour"

    try:
        case.PatientModel.RegionsOfInterest[StructureName]
        logging.warning(
            f"make_boolean_structure: Structure {StructureName}"
            f" exists.  This will be overwritten in this examination"
        )
    except:
        create_roi(case, examination, StructureName, delete_existing=True, suffix=None)
    already_derived = check_derivation(case=case, **kwargs)
    if already_derived:
        logging.debug(f"{StructureName} is already derived.")
    else:
        logging.debug(f"Deriving {StructureName}")
        case.PatientModel.RegionsOfInterest[StructureName].SetAlgebraExpression(
            ExpressionA={
                "Operation": OperationA,
                "SourceRoiNames": SourcesA,
                "MarginSettings": {
                    "Type": MarginTypeA,
                    "Superior": ExpA[0],
                    "Inferior": ExpA[1],
                    "Anterior": ExpA[2],
                    "Posterior": ExpA[3],
                    "Right": ExpA[4],
                    "Left": ExpA[5],
                },
            },
            ExpressionB={
                "Operation": OperationB,
                "SourceRoiNames": SourcesB,
                "MarginSettings": {
                    "Type": MarginTypeB,
                    "Superior": ExpB[0],
                    "Inferior": ExpB[1],
                    "Anterior": ExpB[2],
                    "Posterior": ExpB[3],
                    "Right": ExpB[4],
                    "Left": ExpB[5],
                },
            },
            ResultOperation=OperationResult,
            ResultMarginSettings={
                "Type": MarginTypeR,
                "Superior": ExpR[0],
                "Inferior": ExpR[1],
                "Anterior": ExpR[2],
                "Posterior": ExpR[3],
                "Right": ExpR[4],
                "Left": ExpR[5],
            },
        )

    if StructureName == "InnerAir":
        logging.debug(f"Excluding {StructureName} from export")
    if ExcludeFromExport:
        exclude_from_export(case=case, rois=StructureName)

    msg = change_roi_color(case=case, roi_name=StructureName, rgb=StructColor)
    if msg is not None:
        logging.debug(msg)
    type_msg = change_roi_type(case=case, roi_name=StructureName, roi_type=StructType)
    if type_msg is not None:
        logging.debug(type_msg)
    case.PatientModel.RegionsOfInterest[StructureName].UpdateDerivedGeometry(
        Examination=examination, Algorithm="Auto"
    )
    # MAYBE Broken in RS 11B
    # patient.Set2DvisualizationForRoi(RoiName=StructureName, Mode=VisualizationType)
    patient.SetRoiVisibility(RoiName=StructureName, IsVisible=VisualizeStructure)


def make_wall(wall, sources, delta, patient, case, examination,
              inner=True, struct_type="Undefined"):
    """
    Args:
    :param wall: Name of wall contour
    :param sources: List of source structures
    :param delta: contraction
    :param patient: current patient
    :param case: current case
    :param inner: logical create an inner wall (true) or ring
    :param examination: current exam
    :param struct_type: (str) Defines the RS structure type for this wall
    :return:
    """

    if inner:
        a = [0] * 6
        b = [delta] * 6
    else:
        a = [delta] * 6
        b = [0] * 6

    wall_defs = {
        "StructureName": wall,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": [46, 122, 177],
        "OperationA": "Union",
        "SourcesA": sources,
        "MarginTypeA": "Expand",
        "ExpA": a,
        "OperationB": "Union",
        "SourcesB": sources,
        "MarginTypeB": "Contract",
        "ExpB": b,
        "OperationResult": "Subtraction",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": struct_type,
    }
    make_boolean_structure(
        patient=patient, case=case, examination=examination, **wall_defs
    )


def make_inner_air(PTVlist, external, patient, case, examination, inner_air_HU=-900):
    """

    :param PTVlist: list of target structures to search near for air pockets
    :param external: string name of external to use in the definition
    :param patient: current patient
    :param case: current case
    :param examination: current examination
    :param inner_air_HU: optional parameter to define upper threshold of air volumes
    :return: new_structs: a list of newly created structures
    """
    new_structs = []
    # Automated build of the Air contour
    air_name = "Air"
    air_color = [55, 221, 159]  # DarkShamrock
    air_exists = exams_containing_roi(
        case=case, structure_name=air_name, exam=examination
    )
    if air_exists:
        retval_air = case.PatientModel.RegionsOfInterest[air_name]
    else:
        msg = create_roi(
            case=case,
            examination=examination,
            roi_name=air_name,
            delete_existing=True,
            suffix=None,
        )
        retval_air = case.PatientModel.RegionsOfInterest[air_name]
        change_roi_color(case=case, roi_name=air_name, rgb=air_color)
        new_structs.append(air_name)
    air_examination = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
        air_name
    ]
    patient.SetRoiVisibility(RoiName=air_name, IsVisible=False)
    exclude_from_export(case=case, rois=air_name)

    ## retval_air.GrayLevelThreshold(
    ##     Examination=examination,
    ##     LowThreshold=-1024,
    ##     HighThreshold=inner_air_HU,
    ##     PetUnit="",
    ##     CbctUnit=None,
    ##     BoundingBox=None,
    ## )
    # A volume reduction without further steps seems to result in a crash.
    # Eliminate the air voxels outside the patient
    # Make a temporary external that we can use to get rid of supports
    i = 0
    temp_air_name = air_name + str(i)
    while check_structure_exists(
            case=case, structure_name=temp_air_name, exam=examination, option="Check"
    ):
        i += 1
        temp_air_name = air_name + str(i)
    temp_air_geom = create_roi(
        case=case,
        examination=examination,
        roi_name=temp_air_name,
        delete_existing=True,
        suffix=None,
    )
    temp_air_roi = case.PatientModel.RegionsOfInterest[temp_air_name]
    # TODO: This is taking too long. Suggest making a bounding box on all targets to speed this up
    # Function would get a bounding box for each target
    #    b = []
    #    a = None
    # funct absolute_max(a,b):
    #    if abs(a) < abs(b)
    #       return b
    #    else:
    #       return a

    # for p in PTV_List:
    #    target_geom = case.PatientModel.StructureSets[exam.Name].RoiGeometries[p]
    #    b = target_geom.GetBoundingBox()
    #    if not a:
    #       a = b
    #    a[0].x = absolute_max(a[0].x,b[0].x)
    #    a[1].x = absolute_max(a[1].x,b[1].x)
    #    a[0].y = absolute_max(a[0].y,b[0].y)
    #    a[1].y = absolute_max(a[1].y,b[1].y)
    #    a[0].z = absolute_max(a[0].z,b[0].z)
    #    a[1].z = absolute_max(a[1].z,b[1].z)
    # box_geom.OfRoi.CreateBoxGeometry(Size={'x': abs(b[0].x - b[1].x)+1.,
    #                                            'y': abs(b[0].y - b[1].y)+1.,
    #                                           'z': abs(z1-z0)},
    #                                     Examination=exam,
    #                                     Center=c,
    #                                     Representation='Voxels',
    #                                     VoxelSize=None)
    # Find the maximum in each direction
    # Add/Subtract a fixed value away from the targets
    # This bounding box would be fed into the GrayLevel thresholding below
    # Build the temporary air volume
    temp_air_roi.GrayLevelThreshold(
        Examination=examination,
        LowThreshold=-1024,
        HighThreshold=inner_air_HU,
        PetUnit="",
        CbctUnit=None,
        BoundingBox=None,
    )
    # Build the arguments for the Boolean Air construction
    air_defs = {
        "StructureName": air_name,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": air_color,
        "OperationA": "Union",
        "SourcesA": [temp_air_name],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": [external],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "Intersection",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    make_boolean_structure(
        patient=patient, case=case, examination=examination, **air_defs
    )
    retval_air.DeleteExpression()
    temp_air_roi.DeleteRoi()

    retval_air.VolumeThreshold(
        InputRoi=retval_air, Examination=examination, MinVolume=0.1, MaxVolume=500
    )
    inner_air_sources = [air_name, external]
    inner_air_defs = {
        "StructureName": "InnerAir",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": air_color,
        "OperationA": "Intersection",
        "SourcesA": inner_air_sources,
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": PTVlist,
        "MarginTypeB": "Expand",
        "ExpB": [1] * 6,
        "OperationResult": "Intersection",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    make_boolean_structure(
        patient=patient, case=case, examination=examination, **inner_air_defs
    )

    # Define the inner_air structure at the Patient Model level
    # inner_air_pm = case.PatientModel.RegionsOfInterest["InnerAir"]
    # Define the inner_air structure at the examination level
    inner_air_ex = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
        "InnerAir"
    ]

    # If the InnerAir structure has contours clean them
    if not inner_air_ex.HasContours():
        # inner_air_pm.VolumeThreshold(
        #    InputRoi=inner_air_pm, Examination=examination, MinVolume=0.1, MaxVolume=500
        # )
        # Check for emptied contours
        # if not inner_air_ex.HasContours():
        #     logging.debug("Volume Thresholding has eliminated InnerAir contours")
        # else:
        logging.debug("No air contours were found near the targets")

    return new_structs


def make_externalclean(
        patient,
        case,
        examination,
        structure_name="ExternalClean",
        suffix=None,
        delete=False):
    """
    Makes a cleaned version of the external (body) contour and sets its type appropriately
    :param case: RS Case object
    :param examination: RS Examination object
    :param structure_name: a supplied external structure name
    :param suffix: optional suffix in the event of locked structures
    :param delete: deletes existing External if present
    :return: the RoiGeometries object of the cleaned external
    """
    if delete:
        externals = find_types(case=case, roi_type="External")
        if externals:
            current_external = externals[0]
            if current_external != structure_name:
                try:
                    roi_geom = case.PatientModel.RegionsOfInterest[
                        current_external
                    ].DeleteRoi()
                except:
                    logging.warning(
                        f"Structure {current_external} could not be deleted"
                    )
    # Make a temporary external that we can use to get rid of supports
    i = 0
    temp_ext = "temp_ext" + str(i)
    while check_structure_exists(
            case=case, structure_name=temp_ext, exam=examination, option="Check"
    ):
        i += 1
        temp_ext = "temp_ext" + str(i)
    temp_ext_geom = create_roi(
        case=case,
        examination=examination,
        roi_name=temp_ext,
        delete_existing=False,
        suffix=suffix,
    )
    temp_ext_geom.OfRoi.CreateExternalGeometry(
        Examination=examination, ThresholdLevel=None
    )
    temp_ext_geom.OfRoi.VolumeThreshold(
        InputRoi=temp_ext_geom.OfRoi,
        Examination=examination,
        MinVolume=1,
        MaxVolume=200000,
    )
    # Redraw the ExternalClean structure if necessary
    if check_structure_exists(
            case=case, structure_name=structure_name, exam=examination, option="Check"
    ):
        roi_geom = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
            structure_name
        ]
    else:
        roi_geom = create_roi(
            case=case,
            examination=examination,
            roi_name=structure_name,
            delete_existing=False,
            suffix=suffix,
        )
    if not roi_geom.HasContours():
        supports = find_types(case=case, roi_type="Support")
        if supports:
            ext_defs = {
                "StructureName": structure_name,
                "ExcludeFromExport": False,
                "VisualizeStructure": False,
                "StructColor": [192, 192, 192],
                "OperationA": "Union",
                "SourcesA": [temp_ext],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": supports,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **ext_defs
            )
            roi_geom.OfRoi.DeleteExpression()
        else:
            roi_geom.OfRoi.CreateExternalGeometry(
                Examination=examination, ThresholdLevel=None
            )
            roi_geom.OfRoi.VolumeThreshold(
                InputRoi=roi_geom.OfRoi,
                Examination=examination,
                MinVolume=1,
                MaxVolume=200000,
            )
    else:
        logging.warning(
            f"Structure {structure_name} exists. "
            + "Using predefined structure after removing holes and changing color."
        )
    case.PatientModel.RegionsOfInterest[temp_ext].DeleteRoi()
    type_msg = change_roi_type(case=case, roi_name=structure_name, roi_type="External")
    if type_msg is not None:
        logging.debug(type_msg)
    rgb = [86, 68, 254]
    color_msg = change_roi_color(case=case, roi_name=structure_name, rgb=rgb)
    if color_msg is not None:
        logging.debug(color_msg)
    case.PatientModel.StructureSets[examination.Name].SimplifyContours(
        RoiNames=[structure_name],
        RemoveHoles3D=True,
        RemoveSmallContours=True,
        AreaThreshold=0.1,
        ReduceMaxNumberOfPointsInContours=True,
        MaxNumberOfPoints=3000,
        CreateCopyOfRoi=False,
        ResolveOverlappingContours=False,
    )
    return roi_geom


def make_high_z(case, exam, desired_name):
    threshold = 3025  # Highest HU value on the scanner
    # Redraw the ExternalClean structure if necessary
    if check_structure_exists(
            case=case,
            structure_name=desired_name,
            exam=exam,
            option="Check"):
        roi_geom = case.PatientModel.StructureSets[exam.Name].RoiGeometries[
            desired_name]
    else:
        roi_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=desired_name,
            delete_existing=False,
            suffix="",
        )
    if not roi_geom.HasContours():
        roi_geom.GrayLevelThreshold(Examination=exam,
                                    LowThreshold=int(0.9 * threshold),
                                    HighThreshold=threshold,
                                    PetUnit="",
                                    CbctUnit=None,
                                    BoundingBox=None)


def make_all_ptvs(patient, case, exam, sources):
    # Generate the All_PTVs combined PTV from
    # sources: a list of source roi names
    all_ptv_defs = {
        "StructureName": "All_PTVs",
        "ExcludeFromExport": False,
        "VisualizeStructure": False,
        "StructColor": [222, 47, 80],
        "OperationA": "Union",
        "SourcesA": sources,
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Ptv",
    }
    make_boolean_structure(patient=patient, case=case, examination=exam, **all_ptv_defs)


def trim_supports(patient, case, exam):
    # Trim all structures of type Support to match the S/I extent of the
    # External type contour
    # Inputs: RS Objects: patient, case, exam
    # returns: error: None if successful
    supports = find_types(case=case, roi_type='Support')
    allowed = ['TrueBeamCouch', 'TomoCouch']
    support_name = [s for s in supports if s in allowed]
    #
    # Find extents of external
    si = case.PatientModel.StructureSets[exam.Name] \
        .GetSuperiorInferiorRangeForExternalGeometry()
    z1 = si['y']
    z0 = si['x']
    #
    # For each support set the bounding box inf/sup to the max
    # dimensions of the external[S/I] and the support structure
    for s in support_name:
        trim_s_name = 'Temp' + s
        s_g = case.PatientModel.StructureSets[exam.Name].RoiGeometries[s]
        b = s_g.GetBoundingBox()
        c = {'x': b[0].x + (b[1].x - b[0].x) / 2,
             'y': b[0].y + (b[1].y - b[0].y) / 2,
             'z': z0 + (z1 - z0) / 2.}
        box_name = 'Box_' + s
        box_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=box_name,
            delete_existing=True,
            suffix='R')
        logging.debug(f'Type of box geom is {type(box_geom)}')
        box_geom.OfRoi.CreateBoxGeometry(Size={'x': abs(b[0].x - b[1].x) + 1.,
                                               'y': abs(b[0].y - b[1].y) + 1.,
                                               'z': abs(z1 - z0)},
                                         Examination=exam,
                                         Center=c,
                                         Representation='Voxels',
                                         VoxelSize=None)
        box_roi = case.PatientModel.RegionsOfInterest[box_name]
        # Make temp_name geometry
        trim_s_geom = case.PatientModel.CreateRoi(Name=trim_s_name,
                                                  Color=s_g.OfRoi.Color,
                                                  Type=s_g.OfRoi.Type,
                                                  TissueName=None,
                                                  RbeCellTypeName=None,
                                                  RoiMaterial=s_g.OfRoi.RoiMaterial)
        trim_s_roi = case.PatientModel.RegionsOfInterest[trim_s_name]
        temp_defs = {
            "StructureName": trim_s_name,
            "ExcludeFromExport": False,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Intersection",
            "SourcesA": [s, box_name],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=exam, **temp_defs)
        # Delete existing s - geometry
        s_g.DeleteGeometry()
        # Copy the geometry of the trimmed s using a margin struct
        s_g.OfRoi.CreateMarginGeometry(
            Examination=exam,
            SourceRoiName=trim_s_name,
            MarginSettings={
                "Type": "Expand",
                "Superior": 0.0,
                "Inferior": 0.0,
                "Anterior": 0.0,
                "Posterior": 0.0,
                "Right": 0.0,
                "Left": 0.0,
            }
        )
        # Delete the temp structure
        trim_s_roi.DeleteRoi()
        box_roi.DeleteRoi()


def iter_planning_structure_etree(etree):
    """Load the elements of a planning structure tag into a dictionary

    Arguments:
        etree {[elementree]} --  planning_structure_set tag

    Returns:
       ps_preferences -- a dictionary for reading into a dataframe
    """
    ps_config = {"planning_structure_config": []}
    for p in etree.iter("planning_structure_set"):
        ps_preference = {}
        #
        # Planning structure set name
        try:
            ps_preference["name"] = p.find("name").text
        except AttributeError:
            ps_preference["name"] = ""
        #
        # Planning structure description
        try:
            ps_preference["description"] = p.find("description").text
        except AttributeError:
            ps_preference["description"] = ""
        #
        # Number of targets
        try:
            ps_preference["number_of_targets"] = p.find("number_of_targets").text
        except AttributeError:
            ps_preference["number_of_targets"] = ""
        #
        # Start target numbering at index
        try:
            ps_preference["first_target_number"] = int(
                p.find("first_target_number").text
            )
        except AttributeError:
            ps_preference["first_target_number"] = None
        # Uniform structure handling
        try:
            uniform_structures = p.find("uniform_dose_structs").text.replace(" ", "")
            uniform_structures = uniform_structures.strip()
            if uniform_structures:
                ps_preference["uniform_structures"] = uniform_structures.split(",")
                ps_preference["uniform_standoff"] = float(
                    p.find("uniform_dose_structs").attrib["standoff"]
                )
            else:
                ps_preference["uniform_structures"] = []
        except AttributeError:
            ps_preference["uniform_structures"] = []
        #
        # Underdose elements
        try:
            underdose_structures = p.find("underdose_structs").text.replace(" ", "")
            underdose_structures = underdose_structures.strip()
            if underdose_structures:
                ps_preference["underdose_structures"] = underdose_structures.split(",")
                ps_preference["underdose_standoff"] = float(
                    p.find("underdose_structs").attrib["standoff"]
                )
            else:
                ps_preference["underdose_structures"] = []
        except AttributeError:
            ps_preference["underdose_structures"] = []
        #
        # Evaluate any skin structure generation
        try:
            skin_structure = p.find("skin_structure").text.replace(" ", "")
            skin_structure = skin_structure.strip()
            if skin_structure:
                ps_preference["skin_name"] = skin_structure
                ps_preference["skin_operation"] = p.find("skin_structure").attrib[
                    "margin_type"
                ]
                ps_preference["skin_ExpA"] = [
                    float(p.find("skin_structure").attrib["margin_sup"]),
                    float(p.find("skin_structure").attrib["margin_inf"]),
                    float(p.find("skin_structure").attrib["margin_ant"]),
                    float(p.find("skin_structure").attrib["margin_pos"]),
                    float(p.find("skin_structure").attrib["margin_r"]),
                    float(p.find("skin_structure").attrib["margin_l"]),
                ]
            else:
                ps_preference["skin_name"] = ""
                ps_preference["skin_operation"] = ""
                ps_preference["skin_ExpA"] = []
        except AttributeError:
            ps_preference["skin_name"] = ""
            ps_preference["skin_ExpA"] = []
        #
        # High Dose Ring
        try:
            ring_hd_elem = p.find("ring_hd")
            ring_hd_structure = ring_hd_elem.text.replace(" ", "")
            ring_hd_structure = ring_hd_structure.strip()
            if ring_hd_structure:
                ps_preference["ring_hd_name"] = ring_hd_structure
                ps_preference["ring_hd_operation"] = ring_hd_elem.attrib[
                    "margin_type"
                ]
                ps_preference["ring_hd_standoff"] = float(
                    ring_hd_elem.attrib["standoff"]
                )
                ps_preference["ring_hd_ExpA"] = [
                    float(ring_hd_elem.attrib["margin_sup"]),
                    float(ring_hd_elem.attrib["margin_inf"]),
                    float(ring_hd_elem.attrib["margin_ant"]),
                    float(ring_hd_elem.attrib["margin_pos"]),
                    float(ring_hd_elem.attrib["margin_r"]),
                    float(ring_hd_elem.attrib["margin_l"]),
                ]
            else:
                ps_preference["ring_hd_name"] = ""
                ps_preference["ring_hd_operation"] = ""
                ps_preference["ring_hd_standoff"] = ""
                ps_preference["ring_hd_ExpA"] = []
        except AttributeError:
            ps_preference["ring_hd_name"] = ""
            ps_preference["ring_hd_operation"] = ""
            ps_preference["ring_hd_standoff"] = ""
            ps_preference["ring_hd_ExpA"] = []
        #
        # Low Dose Ring
        try:
            ring_ld_structure = p.find("ring_ld").text.replace(" ", "")
            ring_ld_structure = ring_ld_structure.strip()
            if ring_ld_structure:
                ps_preference["ring_ld_name"] = ring_ld_structure
                ps_preference["ring_ld_operation"] = p.find("ring_ld").attrib[
                    "margin_type"
                ]
                ps_preference["ring_ld_standoff"] = float(
                    p.find("ring_ld").attrib["standoff"]
                )
                ps_preference["ring_ld_ExpA"] = [
                    float(p.find("ring_ld").attrib["margin_sup"]),
                    float(p.find("ring_ld").attrib["margin_inf"]),
                    float(p.find("ring_ld").attrib["margin_ant"]),
                    float(p.find("ring_ld").attrib["margin_pos"]),
                    float(p.find("ring_ld").attrib["margin_r"]),
                    float(p.find("ring_ld").attrib["margin_l"]),
                ]
            else:
                ps_preference["ring_ld_name"] = ""
                ps_preference["ring_ld_operation"] = ""
                ps_preference["ring_ld_standoff"] = ""
                ps_preference["ring_ld_ExpA"] = []
        except AttributeError:
            ps_preference["ring_ld_name"] = ""
            ps_preference["ring_ld_operation"] = ""
            ps_preference["ring_ld_standoff"] = ""
            ps_preference["ring_ld_ExpA"] = []
        #
        # Target Specific (ts) rings
        try:
            ring_ts_structure = p.find("ring_targets").text.replace(" ", "")
            ring_ts_structure = ring_ts_structure.strip()
            if ring_ts_structure:
                ps_preference["ring_ts_name"] = ring_ts_structure
                ps_preference["ring_ts_operation"] = p.find("ring_targets").attrib[
                    "margin_type"
                ]
                ps_preference["ring_ts_standoff"] = float(
                    p.find("ring_targets").attrib["standoff"]
                )
                ps_preference["ring_ts_ExpA"] = [
                    float(p.find("ring_targets").attrib["margin_sup"]),
                    float(p.find("ring_targets").attrib["margin_inf"]),
                    float(p.find("ring_targets").attrib["margin_ant"]),
                    float(p.find("ring_targets").attrib["margin_pos"]),
                    float(p.find("ring_targets").attrib["margin_r"]),
                    float(p.find("ring_targets").attrib["margin_l"]),
                ]
            else:
                ps_preference["ring_ts_name"] = ""
                ps_preference["ring_ts_operation"] = ""
                ps_preference["ring_ts_standoff"] = ""
                ps_preference["ring_ts_ExpA"] = []
        except AttributeError:
            ps_preference["ring_ts_name"] = ""
            ps_preference["ring_ts_operation"] = ""
            ps_preference["ring_ts_standoff"] = ""
            ps_preference["ring_ts_ExpA"] = []
        #
        # Normal: if the normal tag is present
        try:
            normal_element = p.find("normal")
            if normal_element.text:
                normal_structure = normal_element.text.replace(" ", "")
                normal_structure = normal_structure.strip()
                ps_preference["normal"] = normal_structure
            else:
                ps_preference["normal"] = ""
        except AttributeError:
            ps_preference["normal"] = ""
        #
        # Inner Air
        try:
            inner_air_structure = p.find("inner_air").text.replace(" ", "")
            inner_air_structure = inner_air_structure.strip()
            if inner_air_structure:
                ps_preference["inner_air_name"] = inner_air_structure
            else:
                ps_preference["inner_air_name"] = ""
        except AttributeError:
            ps_config["inner_air_name"] = ""
        #
        # Preserve skin dose
        try:
            superficial_target_structure = p.find("superficial_target").text.replace(
                " ", ""
            )
            superficial_target_structure = superficial_target_structure.strip()
            if superficial_target_structure:
                ps_preference["superficial_target_name"] = superficial_target_structure
                ps_preference["superficial_target_operation"] = p.find(
                    "superficial_target"
                ).attrib["margin_type"]
                ps_preference["superficial_target_standoff"] = float(
                    p.find("superficial_target").attrib["standoff"]
                )
                ps_preference["superficial_target_ExpA"] = [
                    float(p.find("superficial_target").attrib["margin_sup"]),
                    float(p.find("superficial_target").attrib["margin_inf"]),
                    float(p.find("superficial_target").attrib["margin_ant"]),
                    float(p.find("superficial_target").attrib["margin_pos"]),
                    float(p.find("superficial_target").attrib["margin_r"]),
                    float(p.find("superficial_target").attrib["margin_l"]),
                ]
            else:
                ps_preference["superficial_target_name"] = ""
                ps_preference["superficial_target_operation"] = ""
                ps_preference["superficial_target_standoff"] = ""
                ps_preference["superficial_target_ExpA"] = []
        except AttributeError:
            ps_preference["superficial_target_name"] = ""
            ps_preference["superficial_target_operation"] = ""
            ps_preference["superficial_target_standoff"] = ""
            ps_preference["superficial_target_ExpA"] = []
        #
        # OTV preferences
        try:
            otv_structure = p.find("otv").text.replace(" ", "")
            otv_structure = otv_structure.strip()
            if otv_structure:
                ps_preference["otv_name"] = otv_structure
                ps_preference["otv_operation"] = p.find("otv").attrib["margin_type"]
                ps_preference["otv_standoff"] = float(p.find("otv").attrib["standoff"])
                ps_preference["otv_ExpA"] = [
                    float(p.find("otv").attrib["margin_sup"]),
                    float(p.find("otv").attrib["margin_inf"]),
                    float(p.find("otv").attrib["margin_ant"]),
                    float(p.find("otv").attrib["margin_pos"]),
                    float(p.find("otv").attrib["margin_r"]),
                    float(p.find("otv").attrib["margin_l"]),
                ]
            else:
                ps_preference["otv_name"] = ""
                ps_preference["otv_operation"] = ""
                ps_preference["otv_standoff"] = ""
                ps_preference["otv_ExpA"] = []
        except AttributeError:
            ps_preference["otv_name"] = ""
            ps_preference["otv_operation"] = ""
            ps_preference["otv_standoff"] = ""
            ps_preference["otv_ExpA"] = []
        # Append the resulting preferences to the dictionary
        ps_config["planning_structure_config"].append(ps_preference)
    return ps_config


class PlanningStructurePreferences:
    """
    Class for getting all relevant data for creating planning structures.
    """

    def __init__(self):
        self.protocol_name = None
        self.origin_file = None
        self.origin_path = None
        self.number_of_targets = None
        self.first_target_number = None
        self.targets = {}
        self.use_inner_air = None
        self.use_uniform_dose = None
        self.uniform_properties = {'structures': [], 'standoff': None}
        self.uniform_dose_oar = {}
        self.generate_otv = None
        self.generate_ptv = None
        self.generate_eval = None
        self.use_under_dose = None
        self.under_dose_properties = {'structures': [], 'standoff': None}
        self.under_dose_oar = {}
        self.use_target_shells = None
        self.target_shell_properties = {'standoff': None}
        self.plan_type = None


def load_beamsets(beamset_type, beamset_modality):
    """
    params: folder: the file folder containing xml files of autoplanning protocols
    return: protocols: a dictionary containing
                       <protocol_name>: [protocol_ElementTree,
                                         path+file_name]
    """
    beamsets = {}
    # Search file list for xml files containing templates
    for f in listdir(PATH_BEAMSETS):
        if f.endswith('.xml'):
            tree = Et.parse(path.join(PATH_BEAMSETS, f))
            if tree.getroot().tag == 'templates':
                if beamset_type in [t.text for t in tree.findall('type')] \
                        and beamset_modality in tree.find('modality').text:
                    for bs in tree.findall('beamset'):
                        n = str(bs.find('name').text)
                        beamsets[n] = [None, None]
                        beamsets[n][0] = bs
                        beamsets[n][1] = f
    return beamsets


def find_beamset_element(beamsets, beamset_name):
    beamset_et = beamsets[beamset_name][0]
    file_name = beamsets[beamset_name][1]
    return beamset_et, file_name


# TODO: add a check for existing isocenters
def get_pois(pd):
    found_poi = [p.Name for p in pd.case.PatientModel.PointsOfInterest]
    return found_poi


def get_qualities(pd):
    # Get photon beam qualities
    machine = get_machine(pd.beamset.MachineReference.MachineName)
    qualities = []
    try:
        pbb = machine.PhotonBeamQualities
    except AttributeError:
        logging.debug(
            f'No nominal energy attribute for beamset '
            f'{pd.beamset.DicomPlanLabel}')
        return qualities
    for q in pbb:
        q_str = f"{q.NominalEnergy:.0f}"
        if q.FluenceMode:
            q_str += r' ' + q.FluenceMode
        qualities.append(q_str)
    return qualities


def get_isos(pd):
    isos = {}
    beamsets = [bs for tp in pd.case.TreatmentPlans for bs in tp.BeamSets]
    for bs in beamsets:
        for b in bs.Beams:
            if bs.DicomPlanLabel not in isos.keys():
                iso_name = bs.DicomPlanLabel + ':' + b.Isocenter.Annotation.Name
                isos[iso_name] = {'-Beamset Name-': bs.DicomPlanLabel,
                                  '-Iso Name-': b.Isocenter.Annotation.Name}
    return isos


def load_protocols(folder):
    """
    params: folder: the file folder containing xml files of autoplanning protocols
    return: protocols: a dictionary containing
                       <protocol_name>: [protocol_ElementTree,
                                         path+file_name]
    """
    protocols = {}
    # Search protocol list, parsing each XML file for protocols and goalsets
    for f in os.listdir(folder):
        if f.endswith('.xml'):
            tree = Et.parse(os.path.join(folder, f))
            if tree.getroot().tag == 'protocol':
                n = tree.find('name').text
                protocols[n] = [None, None]
                protocols[n][0] = tree.getroot()
                protocols[n][1] = f
    return protocols


def site_list(protocols):
    sites = []
    for n, p in protocols.items():
        raw_sites = p[0].find('AnatomicGroup').text.replace(", ", "")
        sites += raw_sites.split(",")
    return list(set(sites))


def site_protocol_list(protocols, site_name):
    matching_protocols = {}
    for n, p in protocols.items():
        if site_name in p[0].find('AnatomicGroup').text:
            matching_protocols[n] = p[0]
    return matching_protocols


def order_dict(protocol):
    # Return a dictionary of {'order name': order_element}
    orders = {}
    for o in protocol[0].findall('order'):
        orders[o.find('name').text] = o
    return orders


def all_orders(protocols):
    orders = {}
    for n, p in protocols.items():
        for o in p[0].findall('order'):
            orders[o.find('name').text] = o
    return orders


def find_order(protocol, order_name):
    # Look in a protocol elementtree and return an order name match
    # If more than one instance of the same order name is found,
    # or if no match is found, return none
    orders = order_dict(protocol)
    matched_orders = []
    for k, o in orders.items():
        if k == order_name:
            matched_orders.append(o)
    if len(matched_orders) == 1:
        return matched_orders[0]
    else:
        return None


import PySimpleGUI as sg
import os


def build_planning_strategy_frame(site_event, sites,
                                  protocol_event, protocols,
                                  order_event, orders,
                                  target_event,
                                  max_targets, strategy_event,
                                  planning_strategies):
    # Initialization
    target_numbers = list(range(1, max_targets + 1))  # Target number choices
    #
    # Site Selection
    site_combo = [sg.Combo(sites,
                           default_value='Select Site',
                           key=site_event,
                           size=(30, 1),
                           tooltip='Select Site',
                           enable_events=True)]
    #
    # Protocol Selection
    protocol_combo = [sg.Combo(protocols,
                               key=protocol_event,
                               default_value='',
                               size=(30, 1),
                               tooltip='Select Protocol',
                               enable_events=True)]
    #
    # Order Selection
    order_combo = [sg.Combo(orders,
                            default_value='',
                            key=order_event,
                            size=(30, 1),
                            tooltip='Select Treatment Planning Order',
                            enable_events=True)]
    #
    # Planning Strategy
    planning_combo = [sg.Combo(planning_strategies,
                               default_value='',
                               key=strategy_event,
                               size=(30, 1),
                               tooltip='Select Treatment Planning Order',
                               enable_events=True)]
    #
    # Number of targets prompt
    target_combo = [sg.Combo(target_numbers,
                             default_value='',
                             key=target_event,
                             size=(30, 1),
                             enable_events=True)
                    ]
    #
    # Build the return frame
    general_frame = sg.Frame(layout=[site_combo, protocol_combo, order_combo, target_combo],
                             visible=True,
                             title='General Options',
                             key='General Options')
    return [general_frame]


def build_target_frame(targets, plan_targets):
    # Takes in
    # target indices,
    # targets in the plan,
    # poi list,
    # target lists
    # isocenter lists
    # beamset lists (TODO Build from planning strategy frame)
    # and builds a three column set of targets
    # each selection component should be tied to the key of a target type
    # Target name, Dose, Beamset assignment
    target_rows = 5
    target_col1 = []
    target_col2 = []
    target_col3 = []
    target_indicies = [t.Index for t in targets]
    for i in target_indicies:
        target_frame = sg.Frame(layout=[[sg.Combo(plan_targets,
                                                  size=(20, 1)),
                                         sg.Text('Dose',
                                                 justification='right'),
                                         sg.Input(key='TARGET' + str(i) + 'DOSE', size=(6, 1)),
                                         sg.Text('cGy')]],
                                visible=False,
                                title='Target ' + str(i),
                                key='Target' + str(i))
        if i <= target_rows:
            target_col1.append([target_frame])
        elif target_rows < i <= 2 * target_rows:
            target_col2.append([target_frame])
        else:
            target_col3.append([target_frame])
    return [sg.Column(target_col1), sg.Column(target_col2), sg.Column(target_col3)]


from dataclasses import dataclass
from typing import Any


@dataclass
class Isocenter:
    Poi: str
    Roi: str
    Iso_0: str


@dataclass
class Target:
    Index: int
    Key: str
    OrderTarget: str
    PlanTarget: str
    Dose: float
    BeamsetName: str
    Iso: Isocenter


def init_target_assignments(max_targets):
    target_assignments = []
    for i in range(max_targets):
        target_assignments.append(
            Target(i + 1, 'Target' + str(i + 1), "", "", 0.0, None, Isocenter("", "", "")))
    return target_assignments


def find_index(target_assignments, index):
    for t in target_assignments:
        if t.Index == index:
            return t
    return None


def update_target_assignments(target_assignments,
                              plan_names={},
                              order_names={},
                              dose_levels={},
                              beamset_assignments={},
                              isocenter_assignments={}
                              ):
    # Consider a class for this dictionary
    for k, v in plan_names.items():
        t = find_index(target_assignments, k)
        t.PlanTarget = v
    for k, v in order_names.items():
        t = find_index(target_assignments, k)
        t.OrderTarget = v
    for k, v in dose_levels.items():
        t = find_index(target_assignments, k)
        t.Dose = v
    for k, v in beamset_assignments.items():
        t = find_index(target_assignments, k)
        t.BeamsetName = v
    for k, v in isocenter_assignments.items():
        t = find_index(target_assignments, k)
        if v['Type'] == 'Poi':
            t.Iso.Poi = str(v['Name'])
        elif v['Type'] == 'Roi':
            t.Iso.Roi = str(v['Name'])
        elif v['Type'] == 'Iso_0':
            t.Iso.Iso_0 = str(v['Name'])
    return target_assignments


def dialog_planning_structures(protocol_dir, planning_strategies, plan_targets):
    # Initialize inputs by loading files
    beamsets = load_beamsets(beamset_type, modality)
    protocols = load_protocols(protocol_dir)
    sites = site_list(protocols)
    orders = all_orders(protocols)
    dialog_name = 'Planning Generation'
    max_targets = 15
    targets = init_target_assignments(max_targets)
    # Data for the General Strategy Frame
    target_event = '-TARGETS SELECTED-'
    site_event = '-SITE SELECTED-'
    protocol_event = '-PROTOCOL SELECTED-'
    order_event = '-ORDER SELECTED-'
    target_data = {'EVENT': target_event}
    frames = {'-GENERAL STRATEGY-': {'-EVENT N TARGETS-': target_event,
                                     '-FRAME-': None,
                                     },
              '-TARGET SETTINGS-': {'-EVENT-': None,
                                    '-FRAME-': build_target_frame(targets, plan_targets), },

              '-UNIF & UNDER-': {},
              '-OPTIONS-': {}}
    frames['-GENERAL STRATEGY-']['-FRAME-'] = build_planning_strategy_frame(
        site_event=site_event,
        sites=sites,
        protocol_event=protocol_event,
        protocols=protocols.keys(),
        order_event=order_event,
        orders=orders.keys(),
        target_event=target_event,
        max_targets=max_targets,
        planning_strategies=planning_strategies)
    combos = {'-STRATEGY-': planning_strategies}
    check_boxes = ['-INNER AIR-', '-UNIFORM DOSE-', '-UNDER DOSE-', ]
    uniform_visible = False
    underdose_visible = False
    targets_visible = False
    frame_width = 60
    frame_n_targets = {'KEY': '-TARGET SETTINGS-',
                       'TITLE': 'Target selections',
                       # 'SIZE': (frame_width,100),
                       'JUST': 'center',
                       'layout': [frames['-GENERAL STRATEGY-']['-FRAME-'],
                                  frames['-TARGET SETTINGS-']['-FRAME-']]
                       }
    first_column = [
        [sg.Text(
            dialog_name,
            size=(frame_width, 1),
            justification='center',
            font=("Helvetica", 16),
            relief=sg.RELIEF_RIDGE
        )],
        [
            sg.Frame(
                layout=frame_n_targets['layout'],
                title=frame_n_targets['TITLE'],
                relief=sg.RELIEF_SUNKEN,
                tooltip='FRAME STUFF',
                key=frame_n_targets['KEY'])
        ], ]
    bottom = [
        [
            sg.Submit(tooltip='Click to submit this window'),
            sg.Cancel()
        ]
    ]
    layout = [[sg.Column(first_column)], [sg.Column(bottom)]]
    window = sg.Window(
        'Planning Structure Generation',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            responses = {}
            break
        elif event == "Submit":
            responses = values
            break
        elif event == target_event:
            num_targets = int(values[target_event])
            update_target_visibility(window, targets, num_targets)
        elif event == site_event:
            site_name = values[site_event]
            update_protocols(window, site_name, protocol_event, protocols)
            # Update the potential protocol choices based on those for this site
        elif event == protocol_event:
            protocol = protocols[values[protocol_event]]
            update_orders(window, protocol, order_event)
        elif event == order_event:
            update_num_targets(window, target_event)

    window.close()
    #
    return values


def update_target_visibility(window, targets, num_targets):
    # Update the number of targets in the target frame
    for t in targets:
        if t.Index <= num_targets:
            window[t.Key].update(visible=True)
        else:
            window[t.Key].update(visible=False)


def update_protocols(window, site_name, protocol_event, protocols):
    options = list(site_protocol_list(protocols, site_name).keys())
    window[protocol_event].update(value='Select Protocol', values=options)


def update_orders(window, protocol, order_event):
    options = list(order_dict(protocol).keys())
    window[order_event].update(value='Select Treatment Planning Order', values=options)


def update_num_targets(window, target_event):
    window[target_event].update(value='Select Number of Targets')


def dialog_number_of_targets():
    """
    Dialog to ascertain the number of target dose levels to be used in defining
    the planning structures

    :return: planning_structures: an instance of the planning_structure_preferences class
                                  with the attributes:
                                  use_under_dose,
                                  use_uniform_dose,
                                  use_inner_air,
                                  number_of_targets chosen.
    """
    # Create an instance of the planning structure class
    planning_structures = PlanningStructurePreferences()

    dialog1 = UserInterface.InputDialog(
        inputs={
            "1": "Enter Number of Targets",
            "2": "Enter the beginning target number, e.g. start numbering at 2 for PTV2, PTV3, "
                 "PTV4 ...",
            "3": "Priority 1 goals present: Use Underdosing",
            "4": "Targets overlap sensitive structures: Use UniformDoses",
            "5": "Use InnerAir to avoid high-fluence due to cavities",
            # '6': "Select plan type"
        },
        title="Planning Structures and Goal Selection",
        datatype={
            "2": "text",
            "3": "check",
            "4": "check",
            "5": "check",
            # '6': "combo"},
        },
        initial={
            "1": "0",
            "2": "0",
            "5": ["yes"],
            # '6': ["Concurrent"]
        },
        options={
            "3": ["yes"],
            "4": ["yes"],
            "5": ["yes"],
            # '6': ["Concurrent",
            #       "Sequential Primary+Boost(s)",
            #       "Multiple Separate Targets"],
        },
        required=["1", "2"]  # , "6"],
    )
    dialog1_response = dialog1.show()
    if dialog1_response == {}:
        sys.exit("Planning Structures and Goal Selection was cancelled")
    # Parse number of targets
    planning_structures.number_of_targets = int(dialog1_response["1"])
    planning_structures.first_target_number = int(dialog1_response["2"])
    # if dialog1_response['6'] == "Concurrent":
    #     planning_structures.plan_type = "Concurrent"
    # elif dialog1_response['6'] == "Sequential Primary+Boost(s)":
    #     planning_structures.plan_type = "Sequential"
    # else:
    #     planning_structures.plan_type = "Multi"
    # User selected that Underdose is required
    if "yes" in dialog1_response["3"]:
        planning_structures.use_under_dose = True
    else:
        planning_structures.use_under_dose = False
    # User selected that Uniformdose is required
    if "yes" in dialog1_response["4"]:
        planning_structures.use_uniform_dose = True
    else:
        planning_structures.use_uniform_dose = False
    # User selected that InnerAir is required
    if "yes" in dialog1_response["5"]:
        planning_structures.use_inner_air = True
    else:
        planning_structures.use_inner_air = False
    return planning_structures


def planning_structures(
        generate_ptvs=True,
        generate_ptv_evals=True,
        generate_otvs=True,
        generate_skin=True,
        generate_inner_air=True,
        generate_field_of_view=True,
        generate_ring_hd=True,
        generate_ring_ld=True,
        generate_normal_1cm=True,
        generate_normal_2cm=True,
        generate_combined_ptv=True,
        skin_contraction=0.3,
        run_status=True,
        planning_structure_selections=None,
        dialog2_response=None,
        dialog3_response=None,
        dialog4_response=None,
        dialog5_response=None,
):
    """
    Generate Planning Structures

    This script is designed to help you make planning structures.
    Prior to starting you should determine:
    All structures to be treated, and their doses
    All structures with priority 1 goals
        (they are going to be selected for UnderDose)
    All structures where hot-spots are undesirable but underdosing is not desired.
        They will be placed in the UniformDose ROI.


    Raystation script to make structures used for planning.

    Note:
    Using the Standard InputDialog
    We have several calls
    The first will determine the target doses and whether we are uniform or underdosing
    Based on those responses:
    Select and Approve underdose selections
    Select and Approve uniform dose selections
    The second non-optional call prompts the user to use:
    -Target-specific rings
    -Specify desired standoffs in the rings closest to the target

    Inputs:
    None, though eventually the common uniform and underdose should be dumped into xml files
    and stored in protocols

    Usage:

    Version History:
    1.0.1: Hot fix to repair inconsistency when underdose is not used but uniform dose is.
    1.0.2: Adding "inner air" as an optional feature
    1.0.3 Hot fix to repair error in definition of sOTVu: Currently taking union of PTV and
    not_OTV - should be intersection.
    1.0.4 Bug fix for upgrade to RS 8 - replaced the toggling of the exclude from export with
    the required method.
    1.0.4b Save the user mapping for this structure set as an xml file to be loaded by create_goals
    1.0.5 Exclude InnerAir and FOV from Export, add IGRT Alignment Structure
    1.0.6 Added the Normal_1cm structure to the list
    1.0.7 Added E-PTV to list, added ability to skip time consuming contour generation


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.

    :param generate_ptvs:
    :param generate_ptv_evals:
    :param generate_otvs:
    :param generate_skin:
    :param generate_inner_air:
    :param generate_field_of_view:
    :param generate_ring_hd:
    :param generate_ring_ld:
    :param generate_normal_2cm:
    :param generate_combined_ptv:
    :param skin_contraction: Contraction in cm to be used in the definition of the skin contour
    :return:
    """
    # The following list allows different elements of the code to be toggled
    # No guarantee can be made that things will work if elements are turned off
    # all dependencies are not really resolved
    # TODO: Move this down to where the translation map gets declared
    # Xml_Out.save_structure_map()

    # InnerAir Parameters
    # Upper Bound on the air volume to be removed from target coverage considerations
    InnerAirHU = -900

    try:
        patient = connect.get_current("Patient")
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
    except:
        logging.warning("patient, case and examination must be loaded")

    if run_status:
        status = UserInterface.ScriptStatus(
            steps=[
                "User Input",
                "Support elements Generation",
                "Target Generation",
                "Ring Generation",
            ],
            docstring=__doc__,
            help=__help__,
        )

    # Keep track of all rois that are created
    newly_generated_rois = []

    # Redraw the clean external volume if necessary
    StructureName = "ExternalClean"
    try:
        case.PatientModel.StructureSets[examination.Name].ApprovedStructureSets[0]
        UserInterface.WarningBox(
            f"Examination {examination.Name} is approved."
            + " Select an examination without approved structures"
            + " as primary and run this script"
        )
        sys.exit("This script cannot be run on image sets with approved plans.")
    # Interestingly, RS is throwing a ValueError in the console, but system error when executed
    # in CPython
    except Exception:
        logging.debug(
            f"Exam {examination.Name} does not have approved structures. "
            f"Proceeding"
        )

    roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))

    external_name = "ExternalClean"
    ext_clean = make_externalclean(
        patient=patient,
        case=case,
        examination=examination,
        structure_name=external_name,
        suffix=None,
        delete=False,
    )

    if run_status:
        status.next_step(text="Please fill out the following input dialogs")

    # Prompt the user for the number of targets, uniform dose needed, sbrt flag, underdose needed
    if planning_structure_selections is None:
        planning_structure_selections = dialog_number_of_targets()
    number_of_targets = planning_structure_selections.number_of_targets
    initial_target_offset = planning_structure_selections.first_target_number - 1
    generate_underdose = planning_structure_selections.use_under_dose
    generate_uniformdose = planning_structure_selections.use_uniform_dose
    generate_inner_air = planning_structure_selections.use_inner_air
    logging.debug(
        f"Planning structures will use "
        f"{planning_structure_selections.number_of_targets} targets, "
        f"UnderDose (Priority 1 Goals) "
        f"{planning_structure_selections.use_under_dose}, "
        f"UniformDose {planning_structure_selections.use_uniform_dose},"
        f" Inner volumes of air {planning_structure_selections.use_inner_air}"
    )

    # Determine if targets using the skin are in place

    # Find all the target names and generate the potential dropdown list for the cases
    # Use the above list for Uniform Structure Choices and Underdose choices, then
    # autoassign to the potential dropdowns
    TargetMatches = []
    UniformMatches = []
    UnderMatches = []
    AllOars = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == "Ptv":
            TargetMatches.append(r.Name)
        if r.Name in UNIFORM_STRUCTURES:
            UniformMatches.append(r.Name)
        if r.Name in UNDERDOSE_STRUCTURES:
            UnderMatches.append(r.Name)
        if r.OrganData.OrganType == "OrganAtRisk":
            AllOars.append(r.Name)

    translation_mapping = {}
    if dialog2_response is not None:
        logging.debug(f'Number of targets: {number_of_targets}')
        logging.debug(f'Source list {dialog2_response.items()}')
        input_source_list = [None] * number_of_targets
        source_doses = [None] * number_of_targets
        indx = 0
        for k, v in dialog2_response.items():
            input_source_list[indx] = k
            source_doses[indx] = str(int(v))
            indx += 1

    else:
        t_i = {}
        t_o = {}
        t_d = {}
        t_r = []
        for i in range(1, number_of_targets + 1):
            j = str(i + initial_target_offset)
            k_name = j.zfill(2) + "_Aname"
            k_dose = j.zfill(2) + "_Bdose"
            t_name = "PTV" + j
            t_i[k_name] = "Match an existing plan target to " + t_name + ":"
            t_o[k_name] = TargetMatches
            t_d[k_name] = "combo"
            t_r.append(k_name)
            t_i[k_dose] = "Provide dose for plan target " + t_name + " in cGy:"
            t_r.append(k_dose)

        dialog2 = UserInterface.InputDialog(
            inputs=t_i,
            title="Input Target Dose Levels",
            datatype=t_d,
            initial={},
            options=t_o,
            required=t_r,
        )

        dialog2_response = dialog2.show()

        if dialog2_response == {}:
            sys.exit("Planning Structures and Goal Selection was cancelled")
        # Parse the output from initial_dialog
        # We are going to take a user input input_source_list and
        # convert them into PTV's used for planning
        # input_source_list consists of the user-specified targets
        # to be massaged into PTV1, PTV2, .... below

        # TODO: Replace the separate input_source_list and source_doses
        #       lists with a dictionary or a tuple
        # Process inputs
        input_source_list = [None] * number_of_targets
        source_doses = [None] * number_of_targets
        for k, v in dialog2_response.items():
            # Grab the first two characters in the key and convert to an index
            i_char = k[:2]
            indx = int(i_char) - 1 - initial_target_offset
            if len(v) > 0:
                if "name" in k:
                    input_source_list[indx] = v
                if "dose" in k:
                    source_doses[indx] = v
            else:
                logging.warning("No dialog elements returned. Script unsuccessful")
        filtered_list = []
        for i in input_source_list:
            derived_sources = [re.search(r, i) for r in PLANNING_EXPRESSIONS]
            if not any(derived_sources):
                filtered_list.append(i)
            else:
                logging.debug(f'{i} is a derived source')
        input_source_list = filtered_list

    # Generate Scan Lengths
    if generate_combined_ptv:
        logging.debug(
            f"Creating All_PTVs ROI using Sources: {input_source_list}"
        )
        make_all_ptvs(patient=patient, case=case, exam=examination, sources=input_source_list)
        newly_generated_rois.append("All_PTVs")

    logcrit("Target List: [%s]" % ", ".join(map(str, input_source_list)))
    logcrit(
        "Proceeding with target list: [%s]" % ", ".join(map(str, input_source_list))
    )
    logcrit("Proceeding with target doses: [%s]" % ", ".join(map(str, source_doses)))

    # Get a list of underdose objects from the user consisting of up to 3 inputs
    if dialog3_response is not None:
        underdose_structures = dialog3_response["structures"]
        underdose_standoff = dialog3_response["standoff"]
        logging.debug(f"Underdose list selected: {underdose_structures}")
    else:
        # Underdose dialog call
        if generate_underdose:
            under_dose_dialog = UserInterface.InputDialog(
                title="UnderDose",
                inputs={
                    "input1_underdose": "Select UnderDose Structures",
                    "input2_underdose": "Select UnderDose OAR",
                    "input3_underdose": "Select UnderDose OAR",
                    "input4_under_standoff": "UnderDose Standoff: x cm gap between targets and "
                                             "UnderDose volume",
                },
                datatype={
                    "input1_underdose": "check",
                    "input2_underdose": "combo",
                    "input3_underdose": "combo",
                },
                initial={"input4_under_standoff": "0.4"},
                options={
                    "input1_underdose": UnderMatches,
                    "input2_underdose": AllOars,
                    "input3_underdose": AllOars,
                },
                required=[],
            )
            under_dose_dialog.show()
            underdose_structures = []
            try:
                underdose_structures.extend(
                    under_dose_dialog.values["input1_underdose"]
                )
            except KeyError:
                pass
            try:
                underdose_structures.extend(
                    [under_dose_dialog.values["input2_underdose"]]
                )
            except KeyError:
                pass
            try:
                underdose_structures.extend(
                    [under_dose_dialog.values["input3_underdose"]]
                )
            except KeyError:
                pass
            underdose_standoff = float(
                under_dose_dialog.values["input4_under_standoff"]
            )
            logging.debug(f"Underdose list selected: {underdose_structures}")

    # UniformDose dialog call
    if dialog4_response is not None:

        uniformdose_structures = dialog4_response["structures"]
        uniformdose_standoff = dialog4_response["standoff"]
        logging.debug(f"Uniform Dose list selected: {uniformdose_structures}")
    else:
        if generate_uniformdose:
            uniformdose_dialog = UserInterface.InputDialog(
                title="UniformDose Selection",
                inputs={
                    "input1_uniform": "Select UniformDose Structures",
                    "input2_uniform": "Select UniformDose OAR",
                    "input3_uniform": "Select UniformDose OAR",
                    "input4_uniform_standoff": "UniformDose Standoff: x cm gap between targets "
                                               "and UniformDose volume",
                },
                datatype={
                    "input1_uniform": "check",
                    "input2_uniform": "combo",
                    "input3_uniform": "combo",
                },
                initial={"input4_uniform_standoff": "0.4"},
                options={
                    "input1_uniform": UniformMatches,
                    "input2_uniform": AllOars,
                    "input3_uniform": AllOars,
                },
                required=[],
            )
            uniformdose_dialog.show()
            uniformdose_structures = []
            try:
                uniformdose_structures.extend(
                    uniformdose_dialog.values["input1_uniform"]
                )
            except KeyError:
                pass
            try:
                uniformdose_structures.extend(
                    [uniformdose_dialog.values["input2_uniform"]]
                )
            except KeyError:
                pass
            try:
                uniformdose_structures.extend(
                    [uniformdose_dialog.values["input3_uniform"]]
                )
            except KeyError:
                pass
            uniformdose_standoff = float(
                uniformdose_dialog.values["input4_uniform_standoff"]
            )
            logging.debug(
                f"Uniform Dose list selected: {uniformdose_structures}"
            )

    if dialog5_response is not None:
        generate_target_skin = dialog5_response["target_skin"]
        generate_ring_hd = dialog5_response["ring_hd"]
        generate_target_rings = dialog5_response["target_rings"]
        thickness_hd_ring = dialog5_response["thick_hd_ring"]
        thickness_ld_ring = dialog5_response["thick_ld_ring"]
        ring_standoff = dialog5_response["ring_standoff"]
        otv_standoff = dialog5_response["otv_standoff"]
    else:
        # OPTIONS DIALOG
        options_dialog = UserInterface.InputDialog(
            title="Options",
            inputs={
                "input1_otv_standoff": "OTV Standoff: x cm gap between higher dose targets",
                "input2_ring_standoff": "Ring Standoff: x cm gap between targets and rings",
                "input3_skintarget": "Preserve skin dose using skin-specific targets",
                "input4_targetrings": "Make target-specific High Dose (HD) rings",
                "input5_thick_hd_ring": "Thickness of the High Dose (HD) ring",
                "input6_thick_ld_ring": "Thickness of the Low Dose (LD) ring",
            },
            datatype={"input3_skintarget": "check", "input4_targetrings": "check"},
            initial={
                "input1_otv_standoff": "0.3",
                "input2_ring_standoff": "0.2",
                "input5_thick_hd_ring": "2",
                "input6_thick_ld_ring": "7",
            },
            options={
                "input3_skintarget": ["Preserve Skin Dose"],
                "input4_targetrings": ["Use target-specific rings"],
            },
            required=[],
        )

        options_response = options_dialog.show()
        if options_response == {}:
            sys.exit("Selection of planning structure options was cancelled")
        # Determine if targets using the skin are in place
        try:
            if "Preserve Skin Dose" in options_response["input3_skintarget"]:
                generate_target_skin = True
            else:
                generate_target_skin = False
        except KeyError:
            generate_target_skin = False

        # User wants target specific rings or no
        try:
            if "Use target-specific rings" in options_response["input4_targetrings"]:
                generate_target_rings = True
                generate_ring_hd = False
            else:
                generate_target_rings = False
        except KeyError:
            generate_target_rings = False

        logging.debug(
            f"User Selected Preserve Skin Dose: {generate_target_skin}"
        )

        logging.debug(f"User Selected target Rings: {generate_target_rings}")

        # DATA PARSING FOR THE OPTIONS MENU
        # Stand - Off Values - Gaps between structures
        # cm gap between higher dose targets (used for OTV volumes)
        otv_standoff = float(options_response["input1_otv_standoff"])

        # ring_standoff: cm Expansion between targets and rings
        ring_standoff = float(options_response["input2_ring_standoff"])

        # Ring thicknesses
        thickness_hd_ring = float(options_response["input5_thick_hd_ring"])
        thickness_ld_ring = float(options_response["input6_thick_ld_ring"])

    if run_status:
        status.next_step(
            text="Support structures used for removing air, skin, and overlap being generated"
        )

    if generate_ptvs:
        # Build the name list for the targets
        PTVPrefix = "PTV"
        OTVPrefix = "OTV"
        sotvu_prefix = "sOTVu"
        # Generate a list of names for the PTV's, Evals, OTV's and EZ (exclusion zones)
        PTVList = []
        PTVEvalList = []
        OTVList = []
        PTVEZList = []
        sotvu_list = []
        high_med_low_targets = False
        numbered_targets = True
        for index, target in enumerate(input_source_list):
            if high_med_low_targets:
                NumMids = len(input_source_list) - 2
                if index == 0:
                    PTVName = PTVPrefix + "_High"
                    PTVEvalName = PTVPrefix + "_Eval_High"
                    PTVEZName = PTVPrefix + "_EZ_High"
                    OTVName = OTVPrefix + "_High"
                    sotvu_name = sotvu_prefix + "_High"
                elif index == len(input_source_list) - 1:
                    PTVName = PTVPrefix + "_Low"
                    PTVEvalName = PTVPrefix + "_Eval_Low"
                    PTVEZName = PTVPrefix + "_EZ_Low"
                    OTVName = OTVPrefix + "_Low"
                    sotvu_name = sotvu_prefix + "_Low"
                else:
                    MidTargetNumber = index - 1
                    PTVName = PTVPrefix + "_Mid" + str(MidTargetNumber)
                    PTVEvalName = PTVPrefix + "_Eval_Mid" + str(MidTargetNumber)
                    PTVEZName = PTVPrefix + "_EZ_Mid" + str(MidTargetNumber)
                    OTVName = OTVPrefix + "_Mid" + str(MidTargetNumber)
                    sotvu_name = sotvu_prefix + "_Mid" + str(MidTargetNumber)
            elif numbered_targets:
                PTVName = (
                        PTVPrefix
                        + str(index + initial_target_offset + 1)
                        + "_"
                        + source_doses[index]
                )
                PTVEvalName = (
                        PTVPrefix
                        + str(index + initial_target_offset + 1)
                        + "_Eval_"
                        + source_doses[index]
                )
                PTVEZName = (
                        PTVPrefix
                        + str(index + initial_target_offset + 1)
                        + "_EZ_"
                        + source_doses[index]
                )
                OTVName = (
                        OTVPrefix
                        + str(index + initial_target_offset + 1)
                        + "_"
                        + source_doses[index]
                )
                sotvu_name = (
                        sotvu_prefix
                        + str(index + initial_target_offset + 1)
                        + "_"
                        + source_doses[index]
                )
            PTVList.append(PTVName)
            translation_mapping[PTVName] = [
                input_source_list[index],
                str(source_doses[index]),
            ]
            PTVEvalList.append(PTVEvalName)
            PTVEZList.append(PTVEZName)
            translation_mapping[OTVName] = [
                input_source_list[index],
                str(source_doses[index]),
            ]
            OTVList.append(OTVName)
            sotvu_list.append(sotvu_name)
    else:
        logging.warning("Generate PTV's off - a nonsupported operation")

    TargetColors = [
        [227, 26, 28],  # BrewerRed
        [51, 160, 44],  # BrewerDarkGreen
        [31, 120, 180],  # BrewerDarkBlue
        [255, 127, 0],  # BrewerOrange
        [106, 61, 154],  # BrewerPurple
        [177, 89, 40],  # BrewerBrown
        [255, 255, 51],  # BrewerEsqueYellow
    ]
    derived_target_colors = [
        [251, 154, 153],  # BrewerRose
        [178, 223, 138],  # BrewerLightGreen
        [166, 206, 227],  # BrewerLightBlue
        [253, 191, 111],  # BrewerLightOrange
        [202, 178, 214],  # BrewerLightPurple
        [227, 164, 130],  # BreweresqueLightBrown
        [255, 255, 153],  # BrewerLightYellow
    ]
    derived_ring_colors = [
        [159, 96, 97],  # BrewerUnsatRed
        [80, 128, 77],  # BrewerUnsatGreen
        [78, 110, 131],  # BrewerUnsatBlue
        [159, 128, 96],  # BrewerUnsatOrange
        [106, 80, 134],  # BrewerUnsatPurple
        [137, 101, 82],  # BrewerUnsatBrown
        [179, 179, 128],  # BrewerUnsatYellow
    ]

    for k, v in translation_mapping.items():
        logging.debug(f"The translation map k is {k} and v {v}")

    if generate_skin:
        make_wall(
            wall="Skin_PRV03",
            sources=["ExternalClean"],
            delta=skin_contraction,
            patient=patient,
            case=case,
            examination=examination,
            inner=True,
            struct_type="Organ",
        )
        newly_generated_rois.append("Skin_PRV03")

    # Generate the UnderDose structure and the UnderDose_Exp structure
    if generate_underdose:
        logging.debug(
            f"Creating UnderDose ROI using Sources: {underdose_structures}"
        )
        # Generate the UnderDose structure
        underdose_defs = {
            "StructureName": "UnderDose",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [67, 65, 225],
            "OperationA": "Union",
            "SourcesA": underdose_structures,
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **underdose_defs
        )
        newly_generated_rois.append("UnderDose")
        UnderDoseExp_defs = {
            "StructureName": "UnderDose_Exp",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Union",
            "SourcesA": underdose_structures,
            "MarginTypeA": "Expand",
            "ExpA": [underdose_standoff] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **UnderDoseExp_defs
        )
        newly_generated_rois.append("UnderDose_Exp")

    # Generate the UniformDose structure
    if generate_uniformdose:
        logging.debug(
            f"Creating UniformDose ROI using Sources: {uniformdose_structures}"
        )
        if generate_underdose:
            logging.debug(
                "UnderDose structures required, excluding overlap from UniformDose"
            )
            uniformdose_defs = {
                "StructureName": "UniformDose",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": [46, 122, 177],
                "OperationA": "Union",
                "SourcesA": uniformdose_structures,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": underdose_structures,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined",
            }
        else:
            uniformdose_defs = {
                "StructureName": "UniformDose",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": [46, 122, 177],
                "OperationA": "Union",
                "SourcesA": uniformdose_structures,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": [],
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "None",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined",
            }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **uniformdose_defs
        )
        newly_generated_rois.append("UniformDose")

    if run_status:
        status.next_step(text="Targets being generated")
    # Make the primary targets, PTV1... these are limited by external and overlapping targets
    if generate_ptvs:
        # Limit each target to the ExternalClean surface
        ptv_sources = ["ExternalClean"]
        # Initially, there are no targets to use in the subtraction
        subtract_targets = []
        for i, t in enumerate(input_source_list):
            logging.debug(f"Creating target {PTVList[i]} using {t}")
            ptv_sources.append(t)
            if i == 0:
                ptv_definitions = {
                    "StructureName": PTVList[i],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    "VisualizationType": "Filled",
                    "StructColor": TargetColors[i],
                    "OperationA": "Intersection",
                    "SourcesA": [t, "ExternalClean"],
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": [],
                    "MarginTypeB": "Expand",
                    "ExpB": [0] * 6,
                    "OperationResult": "None",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv",
                }
            else:
                ptv_definitions = {
                    "StructureName": PTVList[i],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    "VisualizationType": "Filled",
                    "StructColor": TargetColors[i],
                    "OperationA": "Intersection",
                    "SourcesA": [t, "ExternalClean"],
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": subtract_targets,
                    "MarginTypeB": "Expand",
                    "ExpB": [0] * 6,
                    "OperationResult": "Subtraction",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv",
                }
            logging.debug(f"Creating main target {i}: {PTVList[i]}")
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **ptv_definitions
            )
            newly_generated_rois.append(ptv_definitions.get("StructureName"))
            subtract_targets.append(PTVList[i])

    # Make the InnerAir structure
    if generate_inner_air:
        air_list = make_inner_air(
            PTVlist=PTVList,
            external="ExternalClean",
            patient=patient,
            case=case,
            examination=examination,
            inner_air_HU=InnerAirHU,
        )
        newly_generated_rois.append(air_list)
        logging.debug("Built Air and InnerAir structures.")
    else:
        try:
            # If InnerAir is found, it's geometry should be blanked out.
            StructureName = "InnerAir"
            retval_innerair = case.PatientModel.RegionsOfInterest[StructureName]
            logging.warning(
                "Structure " + StructureName + " exists. Geometry will be redefined"
            )
            case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                "InnerAir"
            ].DeleteGeometry()
            # TODO Move to an internal create call
            case.PatientModel.CreateRoi(
                Name="InnerAir",
                Color="SaddleBrown",
                Type="Undefined",
                TissueName=None,
                RbeCellTypeName=None,
                RoiMaterial=None,
            )
        except:
            # TODO Move to an internal create call
            roi_geom = create_roi(
                case=case,
                examination=examination,
                roi_name="InnerAir",
                delete_existing=True,
            )
            change_roi_color(case=case, roi_name="InnerAir", rgb=[139, 69, 19])

    # Make the PTVEZ objects now
    if generate_underdose:
        # Loop over the PTV_EZs
        for index, target in enumerate(PTVList):
            ptv_ez_name = "PTV" + str(index + 1) + "_EZ"
            logging.debug(
                f"Creating exclusion zone target {str(index + 1)}:"
                f" {ptv_ez_name}"
            )
            # Generate the PTV_EZ
            PTVEZ_defs = {
                "StructureName": PTVEZList[index],
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": derived_target_colors[index],
                "OperationA": "Union",
                "SourcesA": [target],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": ["UnderDose"],
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Intersection",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **PTVEZ_defs
            )
            newly_generated_rois.append(PTVEZ_defs.get("StructureName"))

    # We will subtract the adjoining air, skin, or Priority 1 ROI that overlaps the target
    if generate_ptv_evals:
        if generate_underdose:
            eval_subtract = ["Skin_PRV03", "InnerAir", "UnderDose"]
            logging.debug(
                f"Removing the following from eval structures"
            )
            if not any(exists_roi(case=case, rois=eval_subtract)):
                logging.error(
                    f"Missing structure needed for UnderDose: {eval_subtract}"
                    f" needed"
                )
                sys.exit(
                    f"Missing structure needed for UnderDose: "
                    f"{eval_subtract} needed"
                )

        else:
            eval_subtract = ["Skin_PRV03", "InnerAir"]
            logging.debug(
                f"Removing the following from eval structures"
            )
            if not any(exists_roi(case=case, rois=eval_subtract)):
                logging.error(
                    f"Missing structure needed for UnderDose:"
                    f" {eval_subtract} needed"
                )
                sys.exit(
                    f"Missing structure needed for UnderDose: "
                    f"{eval_subtract} needed"
                )
        """
        Make Evals for MD targets on the principle that we don't want planning structures
        mixing with actual MD targets. Only underdose, skin, and targets outside the external
        are subtracted.
        """
        md_eval_subtract = [e for e in eval_subtract]
        for i, t in enumerate(input_source_list):
            logging.debug(f"Creating Eval from {t}")
            # Set the Sources Structure for Evals
            PTVEval_defs = {
                "StructureName": t + '_Eval',
                "ExcludeFromExport": False,
                "VisualizeStructure": False,
                "StructColor": TargetColors[i],
                "OperationA": "Intersection",
                "SourcesA": [t, "ExternalClean"],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": md_eval_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **PTVEval_defs
            )
            md_eval_subtract.append(t)
            newly_generated_rois.append(PTVEval_defs.get("StructureName"))

        for index, target in enumerate(PTVList):
            logging.debug(
                f"Creating evaluation target {str(index + 1)}: "
                f"{PTVEvalList[index]}"
            )
            # Set the Sources Structure for Evals
            PTVEval_defs = {
                "StructureName": PTVEvalList[index],
                "ExcludeFromExport": False,
                "VisualizeStructure": False,
                "StructColor": TargetColors[index],
                "OperationA": "Intersection",
                "SourcesA": [target, "ExternalClean"],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": eval_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **PTVEval_defs
            )
            newly_generated_rois.append(PTVEval_defs.get("StructureName"))
            # Append the current target to the list of targets to subtract in the next iteration
            eval_subtract.append(target)

    # Generate the OTV's
    # Build a region called z_derived_not_exp_underdose that
    # does not include the underdose expansion
    if generate_otvs:
        otv_intersect = []
        if generate_underdose:
            otv_subtract = ["Skin_PRV03", "InnerAir", "UnderDose_Exp"]
        else:
            otv_subtract = ["Skin_PRV03", "InnerAir"]
        logging.debug(f"otvs will not include {otv_subtract}")

        not_otv_definitions = {
            "StructureName": "z_derived_not_otv",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Union",
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": otv_subtract,
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "Subtraction",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **not_otv_definitions
        )
        newly_generated_rois.append(not_otv_definitions.get("StructureName"))
        otv_intersect.append(not_otv_definitions.get("StructureName"))

        # otv_subtract will store the expanded higher dose targets
        otv_subtract = []
        for index, target in enumerate(PTVList):
            OTV_defs = {
                "StructureName": OTVList[index],
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": derived_target_colors[index],
                "OperationA": "Intersection",
                "SourcesA": [target] + otv_intersect,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "MarginTypeB": "Expand",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv",
            }
            if index == 0:
                OTV_defs["SourcesB"] = []
                OTV_defs["OperationResult"] = "None"
                OTV_defs["ExpB"] = [0] * 6
            else:
                OTV_defs["SourcesB"] = otv_subtract
                OTV_defs["OperationResult"] = "Subtraction"
                OTV_defs["ExpB"] = [otv_standoff] * 6

            make_boolean_structure(
                patient=patient, case=case, examination=examination, **OTV_defs
            )
            otv_subtract.append(PTVList[index])
            newly_generated_rois.append(OTV_defs.get("StructureName"))

        # make the sOTVu structures now
        if generate_uniformdose:
            # Loop over the sOTVu's
            for index, target in enumerate(PTVList):
                logging.debug(
                    f"Creating uniform zone target {str(index + 1)}: "
                    f"{sotvu_name}"
                )
                # Generate the sOTVu
                sotvu_defs = {
                    "StructureName": sotvu_list[index],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    "StructColor": derived_target_colors[index],
                    "OperationA": "Intersection",
                    "SourcesA": [target] + otv_intersect,
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": ["UniformDose"],
                    "MarginTypeB": "Expand",
                    "ExpB": [uniformdose_standoff] * 6,
                    "OperationResult": "Intersection",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv",
                }
                make_boolean_structure(
                    patient=patient, case=case, examination=examination, **sotvu_defs
                )
                newly_generated_rois.append(sotvu_defs.get("StructureName"))

    # Target creation complete moving on to rings
    if run_status:
        status.next_step(text="Rings being generated")

    # Generate a rough field of view contour.
    # It should really be put in with the dependent structures
    # This may be the ticket for cutting support structures off.
    if generate_field_of_view:
        # Automated build of the Air contour
        fov_name = "FieldOfView"
        try:
            patient.SetRoiVisibility(RoiName=fov_name, IsVisible=False)
        except:
            # TODO Move to an internal create call
            case.PatientModel.CreateRoi(
                Name=fov_name,
                Color="192, 192, 192",
                Type="FieldOfView",
                TissueName=None,
                RbeCellTypeName=None,
                RoiMaterial=None,
            )
            case.PatientModel.RegionsOfInterest[fov_name].CreateFieldOfViewROI(
                ExaminationName=examination.Name
            )
            case.PatientModel.StructureSets[examination.Name].SimplifyContours(
                RoiNames=[fov_name],
                MaxNumberOfPoints=20,
                ReduceMaxNumberOfPointsInContours=True,
            )
            patient.SetRoiVisibility(RoiName=fov_name, IsVisible=False)
            exclude_from_export(case=case, rois=fov_name)
            newly_generated_rois.append(fov_name)
    # RINGS
    if generate_ring_hd or generate_ring_ld or generate_target_rings:
        # First make an ExternalClean-limited expansion volume
        # This will be the outer boundary for any expansion: a
        z_derived_exp_ext_defs = {
            "StructureName": "z_derived_exp_ext",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "SourcesA": [fov_name],
            "MarginTypeA": "Expand",
            "ExpA": [8] * 6,
            "OperationA": "Union",
            "SourcesB": ["ExternalClean"],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **z_derived_exp_ext_defs
        )
        newly_generated_rois.append(z_derived_exp_ext_defs.get("StructureName"))

        # This structure will be all targets plus the standoff:
        z_derived_targets_plus_standoff_ring_defs = {
            "StructureName": "z_derived_targets_plus_standoff_ring_defs",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "SourcesA": PTVList,
            "MarginTypeA": "Expand",
            "ExpA": [ring_standoff] * 6,
            "OperationA": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "None",
            "StructType": "Undefined",
        }
        make_boolean_structure(
            patient=patient,
            case=case,
            examination=examination,
            **z_derived_targets_plus_standoff_ring_defs
        )
        newly_generated_rois.append(
            z_derived_targets_plus_standoff_ring_defs.get("StructureName")
        )
        # Now generate a ring for each target
        # Each iteration will add the higher dose targets and
        # rings to the subtract list for subsequent rings
        # ring(i) = [PTV(i) + thickness] - [a + b + PTV(i-1)]
        # where ring_avoid_subtract = [a + b + PTV(i-1)]
        ring_avoid_subtract = [
            z_derived_exp_ext_defs.get("StructureName"),
            z_derived_targets_plus_standoff_ring_defs.get("StructureName"),
        ]

    if generate_target_rings:
        logging.debug("Target specific rings being constructed")
        for index, target in enumerate(PTVList):
            ring_name = (
                    "ring"
                    + str(index + initial_target_offset + 1)
                    + "_"
                    + source_doses[index]
            )
            target_ring_defs = {
                "StructureName": ring_name,
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": derived_ring_colors[index],
                "OperationA": "Union",
                "SourcesA": [target],
                "MarginTypeA": "Expand",
                "ExpA": [thickness_hd_ring + ring_standoff] * 6,
                "OperationB": "Union",
                "SourcesB": ring_avoid_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Avoidance",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **target_ring_defs
            )
            newly_generated_rois.append(target_ring_defs.get("StructureName"))
            # Append the current target to the list of targets to subtract in the next iteration
            ring_avoid_subtract.append(target_ring_defs.get("StructureName"))

    else:
        # Ring_HD
        if generate_ring_hd:
            ring_hd_defs = {
                "StructureName": "Ring_HD",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": [252, 179, 231],
                "SourcesA": PTVList,
                "MarginTypeA": "Expand",
                "ExpA": [ring_standoff + thickness_hd_ring] * 6,
                "OperationA": "Union",
                "SourcesB": ring_avoid_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationB": "Union",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "OperationResult": "Subtraction",
                "StructType": "Avoidance",
            }
            make_boolean_structure(
                patient=patient, case=case, examination=examination, **ring_hd_defs
            )
            newly_generated_rois.append(ring_hd_defs.get("StructureName"))
            # Append RingHD to the structure list for removal from Ring_LD
            ring_avoid_subtract.append(ring_hd_defs.get("StructureName"))
    # Ring_LD
    if generate_ring_ld:
        ring_ld_defs = {
            "StructureName": "Ring_LD",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [232, 201, 223],
            "SourcesA": PTVList,
            "MarginTypeA": "Expand",
            "ExpA": [ring_standoff + thickness_hd_ring + thickness_ld_ring] * 6,
            "OperationA": "Union",
            "SourcesB": ring_avoid_subtract,
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **ring_ld_defs
        )
        newly_generated_rois.append(ring_ld_defs.get("StructureName"))

    # Normal_2cm
    if generate_normal_2cm:
        Normal_2cm_defs = {
            "StructureName": "Normal_2cm",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [183, 87, 145],
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationA": "Union",
            "SourcesB": PTVList,
            "MarginTypeB": "Expand",
            "ExpB": [2] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **Normal_2cm_defs
        )
        newly_generated_rois.append(Normal_2cm_defs.get("StructureName"))

    # If a Brain structure exists, make a Normal_1cm
    StructureName = "Brain"
    roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))
    if generate_normal_1cm or roi_check:
        Normal_1cm_defs = {
            "StructureName": "Normal_1cm",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [183, 87, 145],
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationA": "Union",
            "SourcesB": PTVList,
            "MarginTypeB": "Expand",
            "ExpB": [1] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance",
        }
        make_boolean_structure(
            patient=patient, case=case, examination=examination, **Normal_1cm_defs
        )
        newly_generated_rois.append(Normal_1cm_defs.get("StructureName"))

    if run_status:
        status.finish(text="The script executed successfully")
