""" Automated Plan - Tomo/VMAT TBI

    This module contains various functions used in a TBI (Total Body Irradiation)
    treatment planning script.


    1. Launch the GUI and prompt the user for various input parameters related to the treatment.
       - Inputs: None
       - Outputs: User-selected parameters (e.g., number of fractions, total dose, treatment
       machine, etc.)

    2. Identify the HFS (Head First Supine) and FFS (Feet First Supine) CT scans in the patient's
    case.
       - Inputs: None
       - Outputs: HFS and FFS examination objects (`hfs_exam`, `ffs_exam`)

    3. Initialize variables to store information about the patient, case, and examinations for
    HFS and FFS.
       - Inputs: HFS and FFS examination objects
       - Outputs: `pd_hfs` and `patient_data` structures containing relevant information

    4. If FFS structure definitions are enabled:
       a. Load Tomo Supports (e.g., couch supports) for the HFS and FFS scans.
       b. Create a bounding box around the junction point on both scans and set the ROI (Region
       of Interest) there.
       c. Prompt the user to check the fusion alignment of the bony anatomy in the hips.
       d. Load normal MBS (Maximum Base of Support) structures for HFS and FFS.
       e. Build lung contours and avoidance structures on the HFS scan.
       f. Make TBI (Total Body Irradiation) planning structures on the HFS and FFS scans.

    5. If FFS auto-planning is enabled:
       a. Reset the primary and secondary scans to ensure FFS is the primary scan.
       b. Calculate the FFS isocenter coordinates based on the target.
       c. Define the FFS planning protocol with the necessary parameters.
       d. Perform FFS auto-planning and store the output plan and beamset.

    6. If making FFS isodose structures is enabled:
       a. Reset the primary and secondary scans to ensure FFS is the primary scan.
       b. Retrieve isodose names based on predefined junction regions.
       c. Map the junction point by copying non-empty isodose structures from FFS to HFS.
       d. Update the structures in the HFS scan to reflect the mapped isodose structures.

    7. If HFS auto-planning is enabled:
       a. Reset the primary and secondary scans to ensure HFS is the primary scan.
       b. Define the HFS planning protocol with the necessary parameters.
       c. Perform HFS auto-planning and store the output plan and beamset.

    8. If dose summation is enabled:
       a. If HFS and FFS beamsets are not specified, prompt the user to select them.
       b. Update the dose grid of the HFS and FFS beamsets based on the overlapping region.
       c. Recompute all doses in the FFS plan.
       d. Compute the dose on additional sets using the HFS beamset and fraction dose.
       e. Create a dose summation by combining the HFS fraction dose and FFS dose.

    9. Finish the execution of the code.


    Summary of functions:
    check_external: checks if an external file exists.
    check_structure_exists: checks if a structure exists.
    get_most_inferior: gets the most inferior coordinate from an array of coordinates.
    get_center: gets the center coordinate of a list of coordinates.
    find_junction_coords: finds the junction point coordinates between two CT scans.
    place_poi: places a point of interest (POI) on a scan.
    convert_array_to_transform: converts an array to a transform.
    determine_prefix: determines the prefix for a structure name.
    find_roi_prefix: finds the prefix for a ROI structure.
    update_all_remove_expression: updates all instances of a remove expression.
    make_junction_contour: makes the junction contour.
    make_kidneys_contours: makes the kidneys contours.
    make_lung_contours: makes the lung contours.
    get_roi_geometries: gets the geometries of ROIs.
    make_avoid: makes an avoid structure.
    make_ptv: makes a PTV structure.
    make_unsubtracted_dose_structures: makes unsubtracted dose structures.
    make_dose_structures: makes dose structures.
    reset_primary_secondary: resets the primary and secondary scan for a given patient.
    update_dose_grid: updates the dose grid for a given beamset.
    register_images: registers two CT scans.
    load_normal_mbs: loads the normal MBS settings.
    make_tbi_planning_structs: makes the planning structures for a TBI.
    check_fiducials: checks the fiducial points for a given scan.
    calc_ffs_iso: calculates the isocenter for the FFS (Free From Scan) planning.
    make_ffs_isodoses: makes the FFS isodose structures.
    get_new_grid: gets the new dose grid for a given beamset.
    find_transform: finds the transform between two scans.
    transform_poi: transforms a point of interest (POI).
    find_eval_dose: finds the evaluation dose for a given plan.
    tbi_gui: launches a GUI for TBI planning.
    main: runs all of the previous functions.

    Validation Notes:
    Test Patient: MR#

    Version Notes: 0.0.0 Original
                   0.0.1 Avoid robust planning
    TODO: Need Handling for patients that are too short to keep junction in pelvis
    TODO: Need instant warning about VMAT height limits
    TODO: Incorrect definition of the PTV_p_FFS structure since it includes the
        entire External for the FFS plan.

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '07-Oct-2021'
__version__ = '0.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11 SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/AutoPlanTomoTBI'
__credits__ = []

import math
import logging
import connect
import sys
import os
import GeneralOperations
import AutoPlanOperations
from StructureOperations import (create_roi, create_poi,
                                 make_wall, make_externalclean, make_boolean_structure, check_roi,
                                 find_types, exclude_from_export, change_roi_type)
from collections import namedtuple
import numpy as np
import PySimpleGUI as Sg
import re
from typing import Optional, List

script_dir = os.path.dirname(os.path.abspath(__file__))
general_dir = os.path.join(script_dir, '..', 'general')
sys.path.insert(1, general_dir)
from AutoPlan import multi_autoplan, autoplan  # noqa: E402

#
# PROTOCOL/ORDER/BEAMSET INPUTS
PROTOCOL_NAME_TOMO = "UW Tomo TBI"
PROTOCOL_NAME_VMAT = "UW VMAT TBI"
ORDER_NAME_FFS_TOMO = "TomoTBI_FFS"
ORDER_TARGET_NAME_FFS = "PTV_p_FFS"
ORDER_NAME_HFS_TOMO = "TomoTBI_HFS"
SUP_HFS_ORDER, MID_HFS_ORDER, INF_HFS_ORDER = 'VMAT_TBI_HFS_HEAD', \
    'VMAT_TBI_HFS_CHEST_ABD', \
    'VMAT_TBI_HFS_PELVIS'
SUP_FFS_ORDER, MID_FFS_ORDER, INF_FFS_ORDER = 'VMAT_TBI_FFS_PELVIS', \
    'VMAT_TBI_FFS_LEGS', \
    'VMAT_TBI_FFS_FEET'
ORDER_TARGET_NAME_HFS = "PTV_p_HFS"
BEAMSET_TEMPLATE_FFS_TOMO = "Tomo_TBI_FFS_FW50"
BEAMSET_NAME_FFS_TOMO = "FFS__TBI_Tomo"
BEAMSET_TEMPLATE_HFS_TOMO = "Tomo_TBI_HFS_FW50"
BEAMSET_NAME_HFS_TOMO = "HFS__TBI_Tomo"
BEAMSET_HFS_VMAT = "VMAT-HFS-TBI"
BEAMSET_FFS_VMAT = "VMAT-FFS-TBI"
TOMO_MACHINE = "HDA0488"
VMAT_MACHINE = "TrueBeam"
#
# CLEARANCE ASSUMPTIONS FOR VMAT
MIN_FFS_OVERLAP = 2  # Minimum Overlap
HFS_OVERLAP = 5  # Minimum Overlap
FW = 39  # 39 cm of MLC based field
CENTRAL_JUNCTION_WIDTH = 1.2 * 9
# FFS_MAX_TREATMENT_LENGTH = 111.5
FFS_MAX_TREATMENT_LENGTH = 99  # TODO - A fudge - based junction placement on packing HFS
FFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past toes
FFS_SHIFT_BUFFER = 2
FFS_TREATMENT_LENGTH = (FFS_MAX_TREATMENT_LENGTH
                        - FFS_OVERSHOOT
                        - FFS_SHIFT_BUFFER
                        - CENTRAL_JUNCTION_WIDTH)
FFS_ISO_NUMBER = math.ceil(FFS_MAX_TREATMENT_LENGTH / (FW - MIN_FFS_OVERLAP))
HFS_MAX_TREATMENT_LENGTH = 114.5
HFS_SHIFT_BUFFER = 2
HFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past top of head
HFS_TREATMENT_LENGTH = (HFS_MAX_TREATMENT_LENGTH
                        + HFS_OVERSHOOT
                        + HFS_SHIFT_BUFFER
                        + CENTRAL_JUNCTION_WIDTH)
# CONTOUR AND POI CONVENTIONS
JUNCTION_POINT = "junction"
HFS_POI = 'HFS_POI'
FFS_POI = 'FFS_POI'
EXTERNAL_SETUP = 'External_PRV10'
EXTERNAL_SETUP_EXP = 1.0  # cm expansion
EXTERNAL_NAME = "ExternalClean"
AVOID_HFS_NAME = "Avoid_HFS"
AVOID_FFS_NAME = "Avoid_FFS"
TARGET_FFS = "PTV_p_FFS"
TARGET_HFS = "PTV_p_HFS"
EVAL_SUFFIX = "_Eval"
JUNCTION_PREFIX_FFS = "ffs_junction_"
JUNCTION_PREFIX_HFS = "hfs_junction_"
SKIN_AVOIDANCE = 'Avoid_Skin_PRV05'
SKIN_AVOIDANCE_CONTRACT = 0.5  # cm contraction
LUNG_AVOID_NAME = "Lungs_m07"
LUNGS = "Lungs"
LUNGS_EVAL_MARGIN = 1.0  # cm contraction for margin
LUNGS_EVAL_NAME = LUNGS + "_m10"
HFS_CONTOURS = ["Lung_L", "Lung_R", "Kidney_R", "Kidney_L", LUNG_AVOID_NAME,
                LUNGS_EVAL_NAME, AVOID_HFS_NAME, TARGET_HFS]
FFS_CONTOURS = ["Kidney_R", "Kidney_L", AVOID_FFS_NAME, TARGET_FFS]

MBS_ROIS = {'Kidney_L': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Left)",
                         'RoiName': r"Kidney_L",
                         'RoiColor': "58, 251, 170"},
            'Kidney_R': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Right)",
                         'RoiName': r"Kidney_R",
                         'RoiColor': "250, 57, 105"},
            'Lung_L': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Left)",
                       'RoiName': r"Lung_L",
                       'RoiColor': "253, 122, 9"},
            'Lung_R': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Right)",
                       'RoiName': r"Lung_R",
                       'RoiColor': "54, 247, 223"}}
COLORS = [[127, 0, 255], [0, 0, 255], [0, 127, 255], [0, 255, 255],
          [0, 255, 127], [0, 255, 0], [127, 255, 0], [255, 255, 0],
          [255, 127, 0], [255, 0, 0], [255, 0, 255]]


def rename_exams(case):
    hfs_scan_name = ""
    hfs_exam = None
    ffs_scan_name = ""
    ffs_exam = None
    num_exams = 0
    for e in case.Examinations:
        if e.PatientPosition == 'HFS':
            hfs_exam = e
            e.Name = 'HFS'
            hfs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))

        elif e.PatientPosition == 'FFS':
            ffs_exam = e
            e.Name = 'FFS'
            ffs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))
        else:
            raise RuntimeError('unknown exam orientation')
        num_exams += 1
    if not hfs_scan_name or not hfs_exam:
        raise RuntimeError('Could not find an HFS examination')
    if not ffs_scan_name or not ffs_exam:
        raise RuntimeError('Could not find an FFS examination')
    if not all([hfs_scan_name, ffs_scan_name]):
        raise RuntimeError('This script requires a head first and feet first scan')
    if num_exams > 2:
        raise RuntimeError('This script assumes two exams. One in the HFS '
                           'position and the other in FFS position. '
                           f'The number of exams in this case is {num_exams} '
                           f'and could lead to ambiguity. Exiting')
    return hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam


def check_prerequisites(pd_ffs, pd_hfs, do_structure_definition,
                        make_vmat_plan):
    """
    Check if prerequisite points, contours, registrations are present based on work expected
    :param pd_ffs: patient data for feet-first supine
    :param pd_hfs: patient data for head-first supine
    :param do_structure_definition: boolean indicating whether to do structure definition
    :param make_vmat_plan: if True, check for pois and midfield junction structures
    :raises RuntimeError: if any prerequisite is missing
    """
    patient_data = [pd_ffs, pd_hfs]

    # Check external contours
    for pdat in patient_data:
        if not check_external(pdat):
            raise RuntimeError(f'Exam {pdat.exam.Name} has an invalid external contour')
    if not do_structure_definition:
        # Contours for Lung, Kidney, supports, central junction, and image registration should be present
        hfs_missing = check_contours(pd_hfs, HFS_CONTOURS)
        ffs_missing = check_contours(pd_ffs, FFS_CONTOURS)
        if hfs_missing or ffs_missing:
            logging.error(f'Missing contours: HFS {hfs_missing}, FFS {ffs_missing}')
            raise RuntimeError(f'Missing contours: HFS {hfs_missing}, FFS {ffs_missing}')
        # Check junction contours
        dose_levels = [str(i * 10) + "%Rx" for i in range(1, 10)]
        for pdat in patient_data:
            prefix = determine_prefix(pdat.exam)
            junction_contours = [f'{prefix}_junction_{dose}' for dose in dose_levels]
            missing_junctions = check_contours(pdat, junction_contours)
            if missing_junctions:
                raise RuntimeError(f'Missing junction contours in {pdat.exam.Name}: {missing_junctions}')
    if make_vmat_plan and not do_structure_definition:
        # Check if POIs created by place_ffs_vmat_pois and place_hfs_vmat_pois exist
        try:
            pois_ffs = find_pois(pd_ffs)
            pois_hfs = find_pois(pd_hfs)
        except RuntimeError as e:
            raise RuntimeError("Required POIs not found. " + str(e))

        # Check that each poi has a valid position
        for poi in pois_ffs + pois_hfs:
            try:
                _ = get_point_position(pd_ffs if poi in pois_ffs else pd_hfs, poi)
            except RuntimeError as e:
                raise RuntimeError("Missing position data for POI. " + str(e))

        # Check if the junctions created by make_midfield_junctions are present
        missing_junctions_ffs = check_midfield_junctions(pd_ffs, pois_ffs)
        missing_junctions_hfs = check_midfield_junctions(pd_hfs, pois_hfs)

        if missing_junctions_ffs or missing_junctions_hfs:
            raise RuntimeError(f'Missing junctions: FFS {missing_junctions_ffs}, HFS {missing_junctions_hfs}')


def check_external(patient_data):
    """
    Check if the patient data has valid external contours
    :param patient_data: data for a single patient
    :return: boolean indicating whether the data has valid external contours
    """
    roi_list = [r for r in patient_data.case.PatientModel.RegionsOfInterest]

    external_roi = next((r for r in roi_list if r.Type == "External"), None)
    if not external_roi:
        logging.debug('No external contour designated')
        connect.await_user_input(
            'No External contour type designated. Give a contour an External type and continue script.')
        return any(roi.Type == "External" for roi in roi_list)

    if not roi_has_contours(patient_data, external_roi.Name):
        logging.debug(f'External {external_roi.Name} is missing contours on {patient_data.exam}')
        connect.await_user_input(f'External {external_roi.Name} is missing contours on {patient_data.exam}')
        return roi_has_contours(patient_data, external_roi.Name)

    logging.debug(f'External {external_roi.Name} checked for contours: {patient_data.exam}')
    return True


def check_contours(patient_data, roi_list):
    """
    Check if the patient data has all required contours
    :param patient_data: data for a single patient
    :param roi_list: list of names of required contours
    :return: list of names of missing contours, empty if all are present
    """
    missing_contours = []
    for r in roi_list:
        if not roi_has_contours(patient_data, r):
            missing_contours.append(r)
    return missing_contours


def toggle_ptv_type(rs_obj, rois, roi_type):
    # Sometimes in the course of RayStation planning, we need to change our type
    # 'cause of stupid dose grids.
    for r in rois:
        change_roi_type(rs_obj.case, roi_name=r, roi_type=roi_type)


def check_midfield_junctions(patient_data, poi_name_list):
    """
    Check if junctions created by make_midfield_junctions are present in patient data.

    :param patient_data: patient data
    :param poi_name_list: list of poi names used in make_midfield_junctions
    :returns: List of missing junctions. Empty if all junctions are present.
    """
    missing_junctions = []

    for i in range(len(poi_name_list) - 1):
        try:
            n0 = int(poi_name_list[i][-1])
            n1 = int(poi_name_list[i + 1][-1])
        except ValueError:
            raise RuntimeError(f'Error: The name of the POI does not contain '
                               f'an integer in the last digit.')

        junction_name = f'_iso{n0}{n1}_junction_'

        # check if this junction exists in the patient_data's structure sets
        rois = [r for r in patient_data.case.PatientModel.RegionsOfInterest]
        matching_roi = None
        no_contours = True

        junction_pattern = re.compile(junction_name + r"\d$")

        for roi in rois:
            if re.search(junction_pattern, roi.Name):
                matching_roi = roi
                # Check if the ROI has contours
                if roi_has_contours(patient_data, roi.Name):
                    no_contours = False
                break  # Exit the loop as soon as the first match is found
        if matching_roi is None or no_contours:
            missing_junctions.append(junction_name)

    return missing_junctions


def roi_in_list(case, structure_name, roi_list=None):
    if not roi_list:
        roi_obj_list = [r for r in case.PatientModel.RegionsOfInterest]
    else:
        roi_obj_list = []
        for n in roi_list:
            roi_obj_list += [r for r in case.PatientModel.RegionsOfInterest
                             if r.Name == n]

    if any(roi.Name == structure_name for roi in roi_obj_list):
        return True
    else:
        return False


def delete_roi(case, structure_name):
    if roi_in_list(case, structure_name):
        try:
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            return True
        except Exception as e:
            logging.warning(f'Could not delete {structure_name}: {e}')
            return False
    else:
        return True


def roi_has_contours(patient_data, structure_name):
    if roi_in_list(patient_data.case, structure_name):
        roi_geom = get_roi_geometry(patient_data.case, patient_data.exam, structure_name)
        if roi_geom.HasContours():
            return True
    return False


def volume_threshold_roi(patient_data, roi_name, min_vol=1., max_vol=1.e6):
    if roi_in_list(patient_data.case, roi_name):
        if roi_has_contours(patient_data, roi_name):
            roi = patient_data.case.PatientModel.RegionsOfInterest[roi_name]
            try:
                roi.VolumeThreshold(
                    InputRoi=roi,
                    Examination=patient_data.exam,
                    MinVolume=min_vol,
                    MaxVolume=max_vol
                )
                if roi_has_contours(patient_data, roi_name):
                    return True
                else:
                    logging.warning(f'Volume thresholding of roi {roi_name} '
                                    f'With Volume MIN/MAX {min_vol}/{max_vol}'
                                    f'Resulted in empty contour')
                    return False
            except Exception as e:
                logging.warning(f'Unable to perform volume thresholding for '
                                f'{roi_name}: {e}')
                return False
        else:
            logging.debug(f'Unable to threshold {roi_name} due to no contours')
            return False
    else:
        logging.debug(f'Unable to threshold {roi_name}: roi not found')
        return False


def get_most_inferior(patient_data, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(patient_data.case, patient_data.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = patient_data.case.PatientModel.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = patient_data.case.Examinations[patient_data.exam.Name].PatientPosition
    if position == 'HFS':
        return bb_roi[0].z
    elif position == 'FFS':
        return bb_roi[0].z
    else:
        return None


def get_most_superior(patient_data, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most superior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(patient_data.case, patient_data.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = patient_data.case.PatientModel.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = patient_data.case.Examinations[patient_data.exam.Name].PatientPosition
    logging.debug(f'Position:{position}, Bounding Box: {bb_roi[0].z}, {bb_roi[1].z}')
    if position == 'HFS':
        return bb_roi[1].z
    elif position == 'FFS':
        return bb_roi[1].z
    else:
        return None


def get_center(rs_obj, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(rs_obj.case, rs_obj.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    c = {'x': bb_roi[0].x + (bb_roi[1].x - bb_roi[0].x) / 2,
         'y': bb_roi[0].y + (bb_roi[1].y - bb_roi[0].y) / 2,
         'z': bb_roi[0].z + (bb_roi[1].z - bb_roi[0].z) / 2}
    return c


def place_ffs_vmat_pois(pd_ffs, junction, offset):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_ffs.case,
                                 roi_type='External')

    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    last_iso_position = ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + FW / 2
    first_iso_position = junction.Point.z - FW / 2
    isocenter_distance = ((first_iso_position - last_iso_position)
                          / (FFS_ISO_NUMBER - 1))
    ffs_junction_width = FW - isocenter_distance
    logging.info(f'Distance from inferior most point at {ffs_ext_z:.2f} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {float(ffs_ext_z - junction.Point.z):.2f} with '
                 f'spacing {isocenter_distance:.2f} requires '
                 f'{FFS_ISO_NUMBER} isocenters, '
                 f'with an overlap of {ffs_junction_width}')
    # Junction location
    pois = []
    coords = {'x': junction.Point.x,
              'y': junction.Point.y}
    for i in range(FFS_ISO_NUMBER):
        if i != FFS_ISO_NUMBER - 1:
            coords['z'] = first_iso_position - i * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i + offset + 1]]
        color = ",".join(color_lst)
        poi = make_poi(pd_ffs.case, pd_ffs.exam,
                       coords, name=f"{FFS_POI}{i + offset + 1}",
                       color=color)
        pois.append(poi)

    return ffs_junction_width


def make_midfield_junctions(rs_obj, poi_name_list, junction_width):
    # Determine the coordinates of each isocenter
    # Find the mid-point between isocenter pairs
    # Put a junction point at + 1/2 junction width from this point
    # Build the structures
    _ = rs_obj.case.Examinations[rs_obj.exam.Name].PatientPosition
    for i in range(len(poi_name_list) - 1):
        poi_geom0 = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name].PoiGeometries[
            poi_name_list[i]]
        poi_geom1 = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name].PoiGeometries[
            poi_name_list[i + 1]]

        try:
            n0 = int(poi_geom0.OfPoi.Name[-1])
            n1 = int(poi_geom1.OfPoi.Name[-1])
        except ValueError:
            logging.error(
                f'Error: The name of the POI does not contain an '
                f'integer in the last digit.')
            raise RuntimeError(f'Error: The name of the POI does not contain '
                               f'an integer in the last digit.')
            # Handle the error condition here, such as setting default values or terminating the
            # program.
            # For example, you can set n0 and n1 to 0 or None to indicate the error condition.

        z_diff = poi_geom0.Point.z - poi_geom1.Point.z
        z_junct = poi_geom0.Point.z - z_diff / 2 + junction_width / 2

        logging.info(
            f'Point {poi_geom0.OfPoi.Name} at z = {poi_geom0.Point.z:.2f} is separated from '
            f'point {poi_geom1.OfPoi.Name} at z = {poi_geom1.Point.z:.2f} by {z_diff:.2f} cm. '
            f'So the beginning of the junction {junction_width:.2f} will be placed at '
            f'{z_junct:.2f}')

        # with junction width
        make_generic_junction_structs(rs_obj, z_junct, junction_width,
                                      j_name=f'_iso{n0}{n1}')


def place_hfs_vmat_pois(pd_hfs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_hfs.case,
                                 roi_type='External')
    j_z = junction.Point.z
    hfs_ext_z = get_most_superior(pd_hfs, roi_name=external_name)
    hfs_treatment_length = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z
    iso_number = math.ceil(hfs_treatment_length / (FW - HFS_OVERLAP))
    last_iso_position = j_z - CENTRAL_JUNCTION_WIDTH + FW / 2
    first_iso_position = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - FW / 2
    isocenter_distance = (first_iso_position - last_iso_position) / (iso_number - 1)
    hfs_junction_width = FW - isocenter_distance

    logging.info(f'Distance from superior most point at {hfs_ext_z} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {hfs_ext_z - junction.Point.z:.2f} with '
                 f'spaced {isocenter_distance:.2f} requires '
                 f'{iso_number} isocenters')
    if hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z \
            >= HFS_MAX_TREATMENT_LENGTH:
        sys.exit('This patient may be too tall for tx')
    elif isocenter_distance >= FW - HFS_OVERLAP:
        # Increase the isocenter number by 1
        iso_number += 1
        isocenter_distance = (first_iso_position - last_iso_position) / (iso_number - 1)
        hfs_junction_width = FW - isocenter_distance
        logging.info(f'Distancing incorrect: FW: {FW} with Overlap {HFS_OVERLAP} '
                     f'with greater computed isocenter distance {isocenter_distance},'
                     f' increasing isocenter by 1 to {iso_number}')

    # Junction location
    pois = []
    for i in range(iso_number):
        for p in pd_hfs.case.PatientModel.PointsOfInterest:
            if p.Name == f"{HFS_POI}{i + 1}":
                p.DeleteRoi()
        coords = {'x': junction.Point.x, 'y': junction.Point.y}
        if i != iso_number - 1:
            coords['z'] = junction.Point.z - CENTRAL_JUNCTION_WIDTH + FW / 2 \
                          + (iso_number - 1 - i) * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i]]
        color = ",".join(color_lst)
        poi = make_poi(pd_hfs.case, pd_hfs.exam,
                       coords, name=f"{HFS_POI}{i + 1}", color=color)
        pois.append(poi)
    return hfs_junction_width


def make_poi(case, exam, coords, name, color):
    for p in case.PatientModel.PointsOfInterest:
        if p.Name == name:
            p.DeleteRoi()
    _ = create_poi(
        case=case,
        exam=exam,
        coords=[coords['x'], coords['y'], coords['z']],
        name=name,
        color=color,
        diameter=1,
        rs_type='Control')
    return name


def find_hfff_junction_coords(pd_ffs):
    # Find the inferior most point from the ffs scan on the external
    [external_name] = find_types(
        pd_ffs.case, roi_type='External')
    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    _ = get_most_superior(pd_ffs, roi_name=external_name)
    center = get_center(pd_ffs, external_name)
    return {
        'x': 0,
        'y': center['y'],
        # Place the junction 1/2 field width away from the isocenter
        'z': ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + FFS_MAX_TREATMENT_LENGTH
    }


def place_hfff_junction_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    _ = create_poi(
        case=pd_hfs.case,
        exam=pd_hfs.exam,
        coords=[coord_hfs['x'], coord_hfs['y'], coord_hfs['z']],
        name=JUNCTION_POINT,
        color='Red',
        diameter=1,
        rs_type='Control'
    )


def convert_array_to_transform(t):
    # Converts into the expected values for an RS transform dictionary
    return {'M11': t[0], 'M12': t[1], 'M13': t[2], 'M14': t[3],
            'M21': t[4], 'M22': t[5], 'M23': t[6], 'M24': t[7],
            'M31': t[8], 'M32': t[9], 'M33': t[10], 'M34': t[11],
            'M41': t[12], 'M42': t[13], 'M43': t[14], 'M44': t[15]}


def determine_prefix(exam):
    # Return HFS or FFS depending on exam orientation
    if exam.PatientPosition == 'HFS':
        return 'hfs'
    elif exam.PatientPosition == 'FFS':
        return 'ffs'


def find_roi_prefix(case, roi_match):
    # Return all structures whose name contains roi_prefix
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_match in r.Name:
            found_roi.append(r.Name)
    return found_roi


def update_all_remove_expression(pdata, roi_name):
    # Update the expression for a contour on all exams then remove expression
    for e in pdata.case.PatientModel.StructureSets:
        try:
            pdata.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
                Examination=pdata.case.Examinations[e.OnExamination.Name],
                Algorithm="Auto"
            )
        except Exception as err:
            logging.debug(f'Error in updating geometry for {roi_name}: {err}')

    try:
        pdata.case.PatientModel.RegionsOfInterest[roi_name].DeleteExpression()
    except Exception as err:
        logging.debug(f'Error in eliminating derived for {roi_name}: {err}')
        pass


def validate_poi_name(poi_name):
    """
    Validate the format of the POI name. The last character should be an integer.

    Args:
        poi_name (str): The name of the POI.

    Returns:
        int: The integer at the end of the POI name.
    """
    try:
        return int(poi_name[-1])
    except ValueError:
        logging.error(f'Error: The name of the POI {poi_name} '
                      'does not contain an integer in the last digit.')
        raise ValueError(f'Error: The name of the POI {poi_name} does not '
                         'contain an integer in the last digit.')


def determine_junction_pair(index, pois, junction_width, orientation):
    """
    Determine the junction pair based on patient orientation and POI index.

    Args:
        index (int): Index of the POI in the list.
        pois (list): List of POIs.
        junction_width (float): Width of the junction.
        orientation (str): Orientation of the patient - 'HFS' or 'FFS'.

    Returns:
        tuple: The junction pair.
    """
    if orientation == 'HFS':
        if index == 0:
            return 0, junction_width
        elif index == len(pois) - 1:
            return junction_width, CENTRAL_JUNCTION_WIDTH
        else:
            return junction_width, junction_width
    elif orientation == 'FFS':
        if index == 0:
            return CENTRAL_JUNCTION_WIDTH, junction_width
        elif index == len(pois) - 1:
            return junction_width, 0
        else:
            return junction_width, junction_width


# Define a function to extract the number from the string using a regex
def extract_number(s):
    match = re.search(r'\d+$', s)
    return int(match.group()) if match else float('inf')


def sort_pois(pois):
    # Sort the list using the custom sorting key
    return sorted(pois, key=extract_number)


def find_pois(pdata):
    """
    Args:
        pdata (named tuple): RS objects
    Returns:
        list: sorted points of interest with orientation-determined suffix
    """
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        suffix = FFS_POI
    else:
        suffix = HFS_POI
    pois = [p.Name for p in pdata.case.PatientModel.PointsOfInterest
            if suffix in p.Name]
    if pois:
        return sort_pois(pois)
    else:
        raise RuntimeError(f'No POIS with name beginning with {suffix} '
                           f'found in exam {pdata.exam.Name}')


def get_point_position(pdata, poi_name):
    try:
        poi_geom0 = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
            .PoiGeometries[poi_name]
    except KeyError:
        raise RuntimeError(f'No position data found for point {poi_name}')
    return poi_geom0.Point


def determine_otv_center_length(pdata, poi_name, orientation, junction_pair):
    """
    Args:
        pdata (named tuple): RS objects
        poi_name (str): the name of the point of interest (isocenter)
        orientation (str):'ffs' or 'hfs'
        junction_pair (tuple): widths of two junctions around poi
    Returns:
        tuple: otv_center, otv_length
    """
    pois = find_pois(pdata)
    poi0 = get_point_position(pdata, poi_name)
    poi_index = pois.index(poi_name)
    logging.debug(f'Current poi {poi_name}: index {poi_index}')
    if orientation == 'hfs':
        if poi_index == 0:
            [external_name] = find_types(pdata.case,
                                         roi_type='External')
            sup_extent = get_most_superior(pdata, external_name)
            # Inferior extent at junction edge
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            #    logging.debug(f'{poi_name}:: Inferior point {pois[poi_index+1]}:'
            #                  f' z {poi_inf.z}, Placed at inf_extent {inf_extent}')
            otv_length = sup_extent - inf_extent
            otv_center = inf_extent + otv_length / 2
        elif poi_index == len(pois) - 1:
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            # Inferior extent at junction point
            poi_inf = get_point_position(pdata, JUNCTION_POINT)
            inf_extent = poi_inf.z
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        else:
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        return otv_center, otv_length
    else:
        if poi_index == 0:
            poi_sup = get_point_position(pdata, JUNCTION_POINT)
            sup_extent = poi_sup.z - junction_pair[0]
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
            logging.debug(f'{poi_name}:: otv_length {otv_length}, otv_center {otv_center}')
        elif poi_index == len(pois) - 1:
            [external_name] = find_types(pdata.case,
                                         roi_type='External')
            inf_extent = get_most_inferior(pdata, external_name)
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        else:
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        return otv_center, otv_length


def make_box(patient_data, box_name, length=None, z_center=None):
    case = patient_data.case
    exam = patient_data.exam
    patient_model = case.PatientModel
    #
    # Get the Bounding box of the External contour
    external_name = find_types(case,
                               roi_type='External')[0]
    bb_external = patient_model.StructureSets[exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(patient_data, roi_name=external_name)
    z_center = c_external['z'] if z_center is None else z_center
    length = bb_external[1].z - bb_external[0].z if length is None else length
    # Create the box
    box_geom = create_roi(
        case=case,
        examination=exam,
        roi_name=box_name,
        delete_existing=True)
    box_geom.OfRoi.CreateBoxGeometry(
        Size={'x': abs(bb_external[1].x - bb_external[0].x) + 2,
              'y': abs(bb_external[1].y - bb_external[0].y) + 2,
              'z': length},
        Examination=patient_data.exam,
        Center={'x': c_external['x'],
                'y': c_external['y'],
                'z': z_center},
        Representation='Voxels',
        VoxelSize=None)
    # Exclude it from export
    exclude_from_export(case, box_name)
    if roi_has_contours(patient_data, box_name):
        return box_name
    else:
        raise RuntimeError(f"Unable to generate a box geometry for {box_name} "
                           f"on exam {exam.Name}")


def make_central_junction_contour(pdata, z_inf_box,
                                  dim_si, dose_level, color=None, j_name=None):
    #  Make the Box Roi and junction region in the area of interest
    #
    # Get exam orientation
    if color is None:
        color = [192, 192, 192]
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = 1.
    elif prefix == 'hfs':
        si = 1.
    else:
        sys.exit(f'Unknown patient orientation {prefix}')
    # Find the name of the external contour
    external_name = find_types(pdata.case,
                               roi_type='External')[0]
    box_name = 'box_' + str(round(z_inf_box, 1))
    overlap_box = 1.001
    box_name = make_box(pdata, box_name,
                        length=dim_si * overlap_box,
                        z_center=z_inf_box + si * dim_si / 2.)
    #
    # Make junction by intersecting external with the box
    junction_name = f'{prefix}{j_name if j_name else ""}_junction_{dose_level}'
    temp_defs = get_boolean_defs(
        roi_name=junction_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        color=color,
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    _ = change_roi_type(
        case=pdata.case,
        roi_name=junction_name,
        roi_type='Ptv')
    update_all_remove_expression(pdata=pdata, roi_name=junction_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_kidneys_contours(pdata, color=None):
    """
        Make the Kidneys
        """
    #
    # Boolean Definitions for Kidneys
    kidneys_defs = get_boolean_defs(
        roi_name="Kidneys",
        a_sources=["Kidney_L", "Kidney_R"],
        a_operation="Union",
        color=color,
        export=True,
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case,
        examination=pdata.exam, **kidneys_defs)


def make_lung_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    lungs_defs = get_boolean_defs(
        roi_name="Lungs",
        a_sources=["Lung_L", "Lung_R"],
        a_operation="Union",
        color=color,
        export=True,
        roi_type="Organ"
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lungs_defs)
    lung_avoid_defs = get_boolean_defs(
        roi_name=LUNG_AVOID_NAME,
        a_sources=["Lungs"],
        a_operation="Union",
        a_exp=[0.7] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_avoid_defs)
    #
    # Boolean Definitions for Lung Evaluation
    lung_eval_defs = get_boolean_defs(
        roi_name=LUNGS_EVAL_NAME,
        a_sources=["Lungs"],
        a_operation="Union",
        a_exp=[LUNGS_EVAL_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_eval_defs)


def get_roi_geometry(case, exam, roi_name):
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


def make_otv(pdata: namedtuple, poi_name: str, point_index: int,
             junction_width: float, pois: List[str], color: Optional[List[int]] = None) -> None:
    """
    Generate the optimization target volume used in inverse planning.
    It consists of the entire patient (using the External) at the location of
    the isocenter minus the junctions.

    Args:
        pdata (PatientData): Patient data.
        poi_name (str): Point of interest.
        point_index (int): Index of the point.
        junction_width (float): Width of the junction.
        pois (List[str]): List of points of interest.
        color (Optional[List[int]]): Color for the OTV.

    Returns:
        None
    """
    # Ensure the poi contains an integer at the end.
    iso_number = validate_poi_name(poi_name)
    # Get patient orientation
    orientation = pdata.case.Examinations[pdata.exam.Name].PatientPosition
    junction_pair = determine_junction_pair(point_index, pois, junction_width, orientation)

    patient_model = pdata.case.PatientModel
    if color is None:
        color = COLORS[iso_number]
    # Find the name of the external contour
    external_name = find_types(pdata.case, roi_type='External')[0]

    # Set OTV name
    otv_name = f'OTV_iso{iso_number}'

    # Get exam orientation
    additional_avoidances = []
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        additional_avoidances = [
            r.Name for r in patient_model.RegionsOfInterest if 'junction' in r.Name]
        additional_avoidances.append(AVOID_FFS_NAME)
    elif prefix == 'hfs':
        additional_avoidances = [
            r.Name for r in patient_model.RegionsOfInterest if 'junction' in r.Name]
        additional_avoidances.append(LUNG_AVOID_NAME)
        additional_avoidances.append(AVOID_HFS_NAME)

    # Make the box geometry
    z_center, length = determine_otv_center_length(
        pdata, poi_name, prefix, junction_pair)
    box_name = 'otv_box_' + str(round(int(poi_name[-1]), 1))
    box_name = make_box(pdata, box_name, length=length, z_center=z_center)

    temp_definitions = get_boolean_defs(
        roi_name=otv_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        b_sources=additional_avoidances,
        b_operation="Union",
        r_exp=[0.01] * 6,
        r_margin_type="Contract",
        result="Subtraction",
        color=color,
        roi_type="Ptv",
    )

    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_definitions)

    update_all_remove_expression(pdata=pdata, roi_name=otv_name)

    _ = volume_threshold_roi(pdata, otv_name, min_vol=0.1)

    patient_model.RegionsOfInterest[box_name].DeleteRoi()


def make_avoid(pdata, z_start, avoid_name, color=None):
    """ Build the avoidance structure used in making the PTV
        patient_data: kind of like PDiddy, but with data, see below
        isocenter_position (float): starting location of the junction
        otv_name (str): Name of the structure to include all avoidance voxels
        avoid_color (opt list[r,g,b]): color of output structure
        Recipe for avoidance volume:
        Take the isocenter_position, build a box that is everything above this position
        Find the intersection with the external.
        If this is the HFS scan, subtract the lung avoidance
    """
    #
    # Find the name of the external contour
    external_name = find_types(pdata.case, roi_type='External')[0]
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.  # SI direction is negative for FFS
        bb_index = 1  # Starting coordinate of bounding box
        additional_avoidances = []  # No other avoidances in FFS orientation
    else:
        si = 1.  # SI direction is positive for HFS
        bb_index = 0  # Starting coordinate of bounding box
        additional_avoidances = [LUNG_AVOID_NAME]  # Subtract the lung volumes
    #
    # Make a box ROI that starts at isocenter_position and ends at isocenter_position + dim_si
    box_name = 'avoid_box_' + str(round(z_start, 1))
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    si_box_size = abs(bb_external[bb_index].z + si * z_start)
    box_name = make_box(pdata, box_name,
                        length=si_box_size,
                        z_center=z_start - si * si_box_size / 2.)
    # Boolean Definitions for Avoidance
    temp_defs = get_boolean_defs(
        roi_name=avoid_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        b_sources=additional_avoidances,
        r_exp=[0., 0., 0.7, 0.7, 0.7, 0.7, 0.7],
        color=color
    )
    make_boolean_structure(patient=pdata.patient, case=pdata.case,
                           examination=pdata.exam, **temp_defs)
    update_all_remove_expression(pdata=pdata, roi_name=avoid_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


# TODO: Make PTV_p_Eval_HFS(-skin and 7 mm lungs)
#       Make PTV_p_Eval_FFS(-skin)

def make_ptv(pdata, junction_prefix, avoid_name, color=None):
    # Find all contours matching prefix and along with otv_name
    # return the external minus these objects
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        eval_name = TARGET_FFS + EVAL_SUFFIX
    else:
        eval_name = TARGET_HFS + EVAL_SUFFIX
    #
    # PTV_name
    ptv_name = "PTV_p_" + prefix.upper()
    external_name = find_types(pdata.case, roi_type='External')[0]
    roi_exclude = find_roi_prefix(pdata.case, roi_match=junction_prefix)
    logging.debug(f'Rois added to exclude are {roi_exclude}')
    roi_exclude.append(avoid_name)
    #
    # Boolean Definitions
    temp_defs = get_boolean_defs(
        roi_name=ptv_name, a_sources=[external_name],
        a_operation="Intersection", b_sources=roi_exclude, b_operation="Union",
        result="Subtraction", visualize=False, color=color, roi_type='Ptv')
    make_boolean_structure(patient=pdata.patient, case=pdata.case,
                           examination=pdata.exam, **temp_defs)
    # Make Eval structure
    # Boolean Definitions
    roi_exclude.append('Avoid_Skin_PRV05')
    roi_exclude.append('Lungs')
    temp_defs = get_boolean_defs(
        roi_name=eval_name, a_sources=[external_name],
        a_operation="Intersection", b_sources=roi_exclude, b_operation="Union",
        result="Subtraction", color=[255, 0, 0], visualize=True,
        roi_type="Ptv")
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    pdata.case.PatientModel.RegionsOfInterest[ptv_name].DeleteExpression()
    pdata.case.PatientModel.RegionsOfInterest[eval_name].DeleteExpression()
    return [ptv_name, eval_name]


def check_list(var, length, element_type, default):
    """
    Check if a variable is a list of a certain length and type.

    :param var: Variable to be checked.
    :param length: Desired length of the list.
    :param element_type: Desired type of list elements.
    :param default: Default value to be returned if the check fails.
    :return: The variable if it passes the check, otherwise the default value.
    """
    if isinstance(var, list) and len(var) == length \
            and all(isinstance(c, element_type) for c in var):
        return var
    else:
        return default


def get_boolean_defs(
        roi_name, a_sources, a_operation, a_exp=None, a_margin_type="Expand",
        b_sources=None, b_operation="Union", b_exp=None, b_margin_type="Expand",
        r_exp=None, r_margin_type="Expand", result="None",
        color=None, export=False, visualize=False, roi_type="Undefined"
):
    """
    Returns a dictionary with Boolean structure definitions.

    Parameters are structure properties and have default values.
    If an argument is not provided, the default value is used.

    :param roi_name: Name of the ROI.
    :param a_sources: List of sources for Operation A.
    :param a_operation: Operation A.
    :param a_exp: Expansion parameters for Operation A. Default is [0]*6.
    :param a_margin_type: Margin type for Operation A. Default is "Expand".
    :param b_sources: List of sources for Operation B. Default is None (equivalent to empty list).
    :param b_operation: Operation B. Default is "Union".
    :param b_exp: Expansion parameters for Operation B. Default is [0]*6.
    :param b_margin_type: Margin type for Operation B. Default is "Expand".
    :param r_exp: Expansion parameters for Resulting operation. Default is [0]*6.
    :param r_margin_type: Margin type for Resulting operation. Default is "Expand".
    :param result: Result of A/B  None, Intersection, Subtraction. Default is None
    :param color: List representing the color of the structure. Default is [192, 192, 192].
    :param export: Boolean to indicate if the structure should be
                   excluded from export. Default is False.
    :param visualize: Boolean to indicate if the structure should be visualized. Default is False.
    :param roi_type: Type of the structure. Default is "Unknown".
    :return: Dictionary with Boolean structure definitions.
    """

    a_exp = check_list(a_exp, 6, float, [0] * 6)
    b_sources = b_sources if b_sources is not None else []
    b_exp = check_list(b_exp, 6, float, [0] * 6)
    r_exp = check_list(r_exp, 6, float, [0] * 6)
    color = check_list(color, 3, int, [192, 192, 192])

    definitions = {
        "StructureName": roi_name,
        "ExcludeFromExport": not export,
        "VisualizeStructure": visualize,
        "StructColor": color,
        "OperationA": a_operation,
        "SourcesA": a_sources,
        "MarginTypeA": a_margin_type,
        "ExpA": a_exp,
        "SourcesB": b_sources,
        "OperationB": b_operation,
        "MarginTypeB": b_margin_type,
        "ExpB": b_exp,
        "MarginTypeR": r_margin_type,
        "ExpR": r_exp,
        "OperationResult": result,
        "StructType": roi_type,
    }

    return definitions


def make_unsubtracted_dose_structures(pdata, rx, dose_thresholds_normalized):
    """
    Make the structure for the dose threshold supplied
    makes unsubtracted_doses (RS Region of Interest Object) with name like <5%Rx>
    patient_data: exactly the same as pdiddy
    rx (float): Prescription (normalizing) dose in cGy
    dose_thresholds_normalized ({dose_roi_names: dose_levels(int)}): percentages of prescription
    dose
    """
    for n, d in dose_thresholds_normalized.items():
        threshold_level = (float(d) / 100.) * float(rx)  # Threshold in cGy
        raw_name = n + '_raw'
        _ = create_roi(
            case=pdata.case,
            examination=pdata.exam,
            roi_name=raw_name,
            delete_existing=True)
        # Get the Region of Interest object
        raw_roi = pdata.case.PatientModel.RegionsOfInterest[raw_name]
        # Make an roi geometry that is at least the threshold level dose
        try:
            raw_roi.CreateRoiGeometryFromDose(
                DoseDistribution=pdata.plan.TreatmentCourse.TotalDose,
                ThresholdLevel=threshold_level)
        except Exception as e:
            logging.debug('Unable to make dose level {}'.format(threshold_level))
        #
        # Initialize the output
        _ = create_roi(
            case=pdata.case,
            examination=pdata.exam,
            roi_name=n,
            delete_existing=True)
        # Get the Region of Interest object
        dose_roi = pdata.case.PatientModel.RegionsOfInterest[n]
        temp_defs = get_boolean_defs(
            roi_name=n,
            a_sources=[EXTERNAL_NAME, raw_roi.Name],
            a_operation="Intersection",
            roi_type="Control"
        )
        make_boolean_structure(
            patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
        # Process the dose roi
        if roi_has_contours(pdata, dose_roi.Name):
            dose_roi.DeleteExpression()
        else:
            logging.debug('Deleting roi {} due to empty'.format(dose_roi.Name))
            dose_roi.DeleteRoi()

        # Clean up
        raw_roi.DeleteRoi()


def find_nonempty_isodose(pdata, dose_level, prefix, external_name, color):
    delete_rois = []
    found_sufficient_dose_level = False
    while not found_sufficient_dose_level:
        raw_dose_name = str(dose_level - 5) + '%Rx'
        if raw_dose_name not in delete_rois:
            delete_rois.append(raw_dose_name)
        roi_name = prefix + '_dose_' + raw_dose_name
        _ = create_roi(
            case=pdata.case,
            examination=pdata.exam,
            roi_name=roi_name,
            delete_existing=True)
        temp_defs = get_boolean_defs(
            roi_name=roi_name,
            a_sources=[prefix, raw_dose_name, external_name],
            a_operation="Intersection",
            color=color,
            roi_type="Control",
        )
        make_boolean_structure(
            patient=pdata.patient,
            case=pdata.case,
            examination=pdata.exam,
            **temp_defs)
        junct_roi = pdata.case.PatientModel.RegionsOfInterest[roi_name]
        junct_roi.DeleteExpression()
        _ = volume_threshold_roi(pdata, roi_name)
        if roi_has_contours(pdata, roi_name):
            found_sufficient_dose_level = True
    return delete_rois


def make_dose_structures(pdata, isodoses):
    """
     Create dose structures based from given isodose levels.
    These structures represent areas that receive at least the specified dose level,
    but not more than the next highest level.
    :param pdata: Object containing the patient case and examination information.
    :param isodoses:   Dictionary with junction name on FFS scan as key and tuple of dose
    levels as value. {junction_name_on_ffs_scan: (110%, 100%, 95% Desired Dose in Junction)}
    :return:  subtracted_isodoses (list): all subtracted and intersected isodoses
    """
    subtract_higher = False  # Used to skip the boolean on the highest level isodose
    [external_name] = find_types(pdata.case, roi_type='External')
    isodose_contours = []
    delete_rois = []
    colors = [[255, 230, 230], [153, 255, 179], [204, 230, 255]]
    #
    # Loop over each junction contour, starting with the highest dose level
    # and subtracting higher doses for each
    for prefix, v in isodoses.items():

        # k is prefix + 10 + %Rx: v is (20,10,5)
        # Make a subtracted dose to roi
        # For each dose level defined in the tuple, create structure that overlaps with the
        # junction, removing higher dose levels as we go
        subtracted_isodoses = []
        subtract_higher = False  # Flag to skip the first isodose
        di = 0
        for dose_level in v:
            # Make non-subtracted (raw) dose
            raw_dose_name = str(dose_level) + '%Rx'
            if raw_dose_name not in delete_rois:
                delete_rois.append(raw_dose_name)
            # Isodose in junction is named:
            # junction_prefix + xx% + _dose_ + %dose, e.g. ffs_junction_10%Rx_dose_5%Rx
            roi_name = prefix + '_dose_' + raw_dose_name
            _ = create_roi(
                case=pdata.case,
                examination=pdata.exam,
                roi_name=roi_name,
                delete_existing=True)

            if subtract_higher:
                temp_defs = get_boolean_defs(
                    roi_name=roi_name,
                    a_sources=[prefix, raw_dose_name, external_name],
                    a_operation="Intersection",
                    b_sources=subtracted_isodoses,
                    result="Subtraction",
                    color=colors[di],
                    roi_type="Control",
                )
            else:
                temp_defs = get_boolean_defs(
                    roi_name=roi_name,
                    a_sources=[prefix, raw_dose_name, external_name],
                    a_operation="Intersection",
                    color=colors[di],
                    roi_type="Control",
                )
            make_boolean_structure(
                patient=pdata.patient, case=pdata.case,
                examination=pdata.exam, **temp_defs)
            subtracted_isodoses.append(roi_name)
            #
            # Check for empties on this high isodose then try more dose levels
            if not roi_has_contours(pdata, roi_name):
                delete_rois.append(roi_name)
                additional_deletes = find_nonempty_isodose(
                    pdata, dose_level=dose_level,
                    prefix=prefix, external_name=external_name, color=di)
                delete_rois += additional_deletes
            subtract_higher = True  # Start subtracting higher dose values
            di += 1
            isodose_contours.append(roi_name)
    for i in isodose_contours:
        update_all_remove_expression(pdata, i)
        _ = volume_threshold_roi(pdata, i)

    for dose_level in delete_rois:
        pdata.case.PatientModel.RegionsOfInterest[dose_level].DeleteRoi()
    return isodose_contours


def reset_primary_secondary(exam1, exam2):
    # Resets exam 1 as primary and exam2 as secondary
    exam1.SetPrimary()
    exam2.SetSecondary()


def update_dose_grid(pdata):
    # TODO: This still doesn't work. The two dose grids need to be compared using a common
    # point on the patient since the dose grid is relative to the patient on the two scans.

    pm = pdata.case.PatientModel
    dg = pdata.plan.GetDoseGrid()
    bb = [{k: dg.Corner[k] + dg.VoxelSize[k] * dg.NrVoxels[k] for k in dg.Corner.keys()},
          dg.Corner]
    types = ['Ptv', 'Support', 'External']
    #
    # Loop over all structure sets looking for support, external or target types
    # For all found, compute a bounding box and expand the current dose grid if necessary.
    for s in pm.StructureSets:
        for r in s.RoiGeometries:
            if r.OfRoi.Type in types:
                try:
                    bs = s.RoiGeometries[r.OfRoi.Name].GetBoundingBox()
                    for c, v in bs[0].items():
                        if v < bb[0][c]:
                            bb[0][c] = v
                            print('{}:{} is {} < {} '.format(r.OfRoi.Name, c, v, bb[0][c]))
                    for c, v in bs[1].items():
                        if v > bb[1][c]:
                            bb[1][c] = v
                            print('{}:{} is {} > {} '.format(r.OfRoi.Name, c, v, bb[1][c]))
                except Exception as e:
                    no_geom_set = "no geometry set for ROI"
                    if no_geom_set in f"{e}":
                        pass
                    else:
                        logging.warning(f'Error in updating dose grid: {e}')

    vs = dg.VoxelSize
    span = {k: abs(bb[1][k] - bb[0][k]) for k in bb[1].keys()}
    update_number_voxels = {k: math.ceil(v / vs[k]) for (k, v) in span.items()}
    pdata.plan.UpdateDoseGrid(Corner=bb[0],
                              VoxelSize=vs,
                              NumberOfVoxels=update_number_voxels)


def check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    approved = False
    # Look through registration objects
    for r in pd_ffs.case.Registrations:
        try:
            _ = r.RegistrationSource
        except AttributeError:
            logging.debug('No approved registrations found')
            approved = False
            break
        if r.RegistrationSource.FromExamination.Name == ffs_scan_name \
                and r.RegistrationSource.ToExamination.Name == hfs_scan_name \
                and r.Review:
            try:
                if r.Review.ApprovalStatus == 'Approved':
                    approved = True
            except AttributeError:
                approved = False
            break
    return approved


def verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    # Check for existing registration, if approved return approved
    # Otherwise look for existing registrations and if they are not approved
    # prompt user to approve them or to allow them to be overwritten
    registrations = False
    # Look through registration objects
    approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        for s in pd_ffs.case.StructureRegistrations:
            if s.FromExamination.Name == hfs_scan_name \
                    and s.ToExamination.Name == ffs_scan_name:
                registrations = True
                if s.Review:
                    try:
                        if s.Review.ApprovalStatus == 'Approved':
                            approved = True
                    except AttributeError:
                        approved = False
                break
    if approved:
        return approved
    else:
        if registrations:
            connect.await_user_input('An existing FFS to HFS registration has been'
                                     ' found.\n Approve it to avoid an overwrite')
            approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)
    return approved


def register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, testing):
    if not testing:
        # Make external clean on both
        ext_clean = make_externalclean(
            patient=pd_hfs.patient,
            case=pd_hfs.case,
            examination=pd_hfs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )
        # If this breaks on a clean scan, we will want to see if this exam has contours
        ext_clean = make_externalclean(
            patient=pd_ffs.patient,
            case=pd_ffs.case,
            examination=pd_ffs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )

    # TODO: Review - this isn't catching correctly. approved is False
    approved = verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=False,
            InitializeImages=True,
            FocusRoisNames=[],
            RegistrationName=None)

        # Refine on bones
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=True,
            InitializeImages=False,
            FocusRoisNames=[],
            RegistrationName=None)
        if not testing:
            connect.await_user_input(
                'Check the fusion alignment of the boney anatomy in the hips. Then continue '
                'script.')
    else:
        logging.info(f'Approved registration found between {pd_ffs.exam.Name} and {pd_hfs.exam.Name}.')


def load_normal_mbs(pd_hfs, pd_ffs, quiet=False):
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # TODO: CHECK FOR PLANNING STRUCTURES AND THEN ADD ANY MISSING
    # Loop through MBS rois, if present, pop.
    rois = [r.OfRoi.Name for r in
            pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name].RoiGeometries
            if r.HasContours]
    logging.debug('Type of MBS_ROIS is {} '.format(type(MBS_ROIS)))
    mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
    adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
    #
    # Begin making planning structures
    if mbs_list:
        pd_hfs.case.PatientModel.MBSAutoInitializer(
            MbsRois=mbs_list,
            CreateNewRois=True,
            Examination=pd_hfs.exam,
            UseAtlasBasedInitialization=True)
        connect.await_user_input('Review placement of MBS structures')

    if adapt_list:
        pd_hfs.case.PatientModel.AdaptMbsMeshes(
            Examination=pd_hfs.exam,
            RoiNames=adapt_list,
            CustomStatistics=None,
            CustomSettings=None)
    # Loop through MBS rois, if present, pop.
    rois = [r.OfRoi.Name for r in
            pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name].RoiGeometries
            if r.HasContours]
    mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
    adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
    # Try a repeat on FFS
    if mbs_list:
        pd_ffs.case.PatientModel.MBSAutoInitializer(
            MbsRois=mbs_list,
            CreateNewRois=False,
            Examination=pd_ffs.exam,
            UseAtlasBasedInitialization=True)
    if adapt_list:
        pd_hfs.case.PatientModel.AdaptMbsMeshes(
            Examination=pd_ffs.exam,
            RoiNames=adapt_list,
            CustomStatistics=None,
            CustomSettings=None)
    if not quiet:
        connect.await_user_input('Check the MBS loaded structures on both exams.')


def make_derived_rois(pd_hfs, pd_ffs):
    """
    Make the derived structures for the plan:
    Lungs, Avoid_Skin_PRV05, External_PRV10,
    :param pd_hfs:
    :param pd_ffs:
    :return:
    """
    rois = {'Lungs': LUNGS, 'Skin_Avoid': SKIN_AVOIDANCE,
            'External_Setup': EXTERNAL_SETUP}
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    #
    # Build lung contours and avoidance on the HFS scan
    make_lung_contours(pd_hfs, color=[192, 192, 192])
    #
    # Make the External_PRV10 set up structure
    try:
        pd_hfs.case.PatientModel.CreateRoi(
            Name=rois['External_Setup'],
            Color="255, 128, 0",
            Type="IrradiatedVolume",
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None)
    except Exception as e:
        if "There already exists" in "{}".format(e):
            pass

    # Create geometry for the External_PRV10
    pd_hfs.case.PatientModel.RegionsOfInterest[rois['External_Setup']] \
        .SetMarginExpression(
        SourceRoiName=EXTERNAL_NAME,
        MarginSettings={'Type': "Expand",
                        'Superior': EXTERNAL_SETUP_EXP,
                        'Inferior': EXTERNAL_SETUP_EXP,
                        'Anterior': EXTERNAL_SETUP_EXP,
                        'Posterior': EXTERNAL_SETUP_EXP,
                        'Right': EXTERNAL_SETUP_EXP,
                        'Left': EXTERNAL_SETUP_EXP})
    # Make skin subtraction
    n_tuples = [pd_hfs, pd_ffs]
    for n in n_tuples:
        make_wall(
            wall=rois['Skin_Avoid'],
            sources=["ExternalClean"],
            delta=SKIN_AVOIDANCE_CONTRACT,
            patient=n.patient,
            case=n.case,
            examination=n.exam,
            inner=True,
            struct_type="Organ")
        #
        n.case.PatientModel.RegionsOfInterest[rois['External_Setup']] \
            .UpdateDerivedGeometry(
            Examination=n.exam,
            Algorithm="Auto")


def make_central_junction_structs(pd_hfs, pd_ffs):
    """

    Args:
        pd_hfs: hfs named tuple
        pd_ffs: ffs named tuple

    Returns:

    """
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # Set the central junction point, and map it to the hfs scan
    hfs_poi_junction, ffs_poi_junction = calculate_junction(pd_hfs, pd_ffs)
    # IsoDose levels declaration and colors.
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = CENTRAL_JUNCTION_WIDTH / len(j_i)
    dose_levels = {10: [127, 0, 255],
                   20: [0, 0, 255],
                   30: [0, 127, 255],
                   40: [0, 255, 255],
                   50: [0, 255, 127],
                   60: [0, 255, 0],
                   70: [127, 255, 0],
                   80: [255, 255, 0],
                   90: [255, 127, 0],
                   95: [255, 0, 0],
                   100: [255, 0, 255]}

    for i in range(len(j_i)):
        # Place the inferior-most edge of box-10% to be at one box width from
        # the junction
        roi_inf_box_edge = ffs_poi_junction.Point.z - dim_si * float(i + 1)
        make_central_junction_contour(
            pd_ffs,
            z_inf_box=roi_inf_box_edge,
            dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx",
            color=dose_levels[j_i[i]])
    make_avoid(pd_ffs, z_start=ffs_poi_junction.Point.z,
               avoid_name=AVOID_FFS_NAME)
    ffs_ptv_list = make_ptv(pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS,
                            avoid_name=AVOID_FFS_NAME)
    cut_rois_to_image(pd_ffs, pd_hfs, ffs_ptv_list)

    for i in range(len(j_i)):
        # Place the inferior edge of the HFS junction at:
        # junction_z - N_isodose_levels * box width
        roi_inf_box_edge = hfs_poi_junction.Point.z \
                           - dim_si * float(len(j_i) - i)
        logging.debug(
            f'Z location for Junction {str(j_i[i])} is {roi_inf_box_edge}')
        make_central_junction_contour(
            pd_hfs, z_inf_box=roi_inf_box_edge, dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx", color=dose_levels[j_i[i]])
    #
    # HFS avoid starts at junction point - number of dose levels * dim_si
    hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
    make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
    hfs_ptv_list = make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS,
                            avoid_name=AVOID_HFS_NAME)
    cut_rois_to_image(pd_hfs, pd_ffs, hfs_ptv_list)

    return ffs_poi_junction, hfs_poi_junction


def check_fiducials(pd, fiducial_name):
    # Check all potential exams to ensure the fiducial is defined
    fiducial_check = []
    pois = [p.Name for p in pd.case.PatientModel.PointsOfInterest]
    if fiducial_name not in pois:
        return False, False
    for ss in pd.case.PatientModel.StructureSets:
        if not ss.PoiGeometries[fiducial_name].Point:
            fiducial_check.append(False)
        else:
            fiducial_check.append(True)
    return True, all(fiducial_check)


def multiplan_data(rso, hfs_pois, ffs_pois, nfx, rx):
    """
        This function generates data dictionaries for multiple plan treatments.

        Args:
            hfs_pois (list): A list of HFS (Head-First Supine) Points of Interest (POIs).
            ffs_pois (list): A list of FFS (Feet-First Supine) POIs.
            nfx (int): Number of fractions.
            rx (int): Radiation dose.

        Returns:
            tuple: Returns two lists of dictionaries, hfs_dict and ffs_dict, that include data
            for HFS and FFS plans respectively.
    """
    # Define the structure sets for various numbers of isocenters
    hfs_data = {
        5: [
            'TBI_HFS_5Pelv',
            'TBI_HFS_4AbdI',
            'TBI_HFS_3AbdS',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        4: [
            'TBI_HFS_4Pelv',
            'TBI_HFS_3Abdo',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        3: [
            'TBI_HFS_3Pelv',
            'TBI_HFS_2Chst',
            'TBI_HFS_1Head',
        ],
        2: [
            'TBI_HFS_2Pelv',
            'TBI_HFS_1Head',
        ],
        1: [
            'TBI_HFS_1Pelv'],
        0: ['']}
    offset = len(hfs_pois)
    ffs_data = {
        5: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}FemS',
            f'TBI_FFS_{offset + 3}FemI',
            f'TBI_FFS_{offset + 4}Knee',
            f'TBI_FFS_{offset + 5}Feet'],
        4:
            [f'TBI_FFS_{offset + 1}Pelv',
             f'TBI_FFS_{offset + 2}Femr',
             f'TBI_FFS_{offset + 3}Knee',
             f'TBI_FFS_{offset + 4}Feet'],

        3: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}Legs',
            f'TBI_FFS_{offset + 3}Feet', ],
        2: [
            f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}Feet', ],
        1: [
            f'TBI_FFS_{offset + 1}Pelv',
        ],
        0: ['']
    }
    # Select beamset names depending on the number of POIs
    hfs_beamset_names, ffs_beamset_names = hfs_data[len(hfs_pois)], ffs_data[len(ffs_pois)]

    def create_translation_map(i, total_points, j_range, site, rx, offset):
        """
            Creates a translation map for the given site and point in the range.

            Args:
                i (int): Current point index.
                total_points (int): Total number of points.
                j_range (range): Range object.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                rx (int): Radiation dose in rx.
                offset (int): Offset value.

            Returns:
                dict: Translation map:
                    'ROI Name in xml': ('Plan ROI Name, Dose, Dose units', e.g.
                    'OTV_iso':('OTV_iso1',800,'cGy')
            """
        translation_map = {}
        for j in j_range:
            # Define the indices used for 'HFS_' and other sites
            if site == 'HFS_':
                prefix = 'hfs'
            else:
                prefix = 'ffs'

            # Set the sup_value and inf_value keys for each point
            sup_key = f'Sup_{j}'
            inf_key = f'Inf_{j}'
            sup_value = (f'{prefix}_iso{offset + i}{offset + i + 1}_junction_{j}', rx, r'cGy')
            inf_value = (f'{prefix}_iso{offset + i + 1}{offset + i + 2}_junction_{j}', rx, r'cGy')

            # Assign the sup_value and inf_value to the translation_map
            if i == 0 or i == total_points - 1:
                key = inf_key if i == 0 else sup_key
                value = inf_value if i == 0 else sup_value
                translation_map[key] = value
            else:  # Middle points
                translation_map[sup_key] = sup_value
                translation_map[inf_key] = inf_value
            # Set the OTV mapping
            translation_map['OTV_iso'] = (f'OTV_iso{i + offset + 1}', rx, r'cGy')

        return translation_map

    def create_optimization_instructions(i, pois, site, prior_beamset_name):
        """
            Creates optimization instructions for a given site.

            Args:
                i (int): Current index.
                pois (list): List of Points of Interest.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                prior_beamset_name (str): Name of the prior beamset that was optimized.

            Returns:
                dict: Optimization instructions.
            """
        optimization_instructions = {}
        if site == 'HFS_':
            optimization_instructions['optimize_with'] = None
            optimization_instructions['order'] = len(pois) - i
            optimization_instructions['optimize_with_background'] = prior_beamset_name  # list(
            # range(i, len(pois) - 1 - i))
        else:
            optimization_instructions['optimize_with'] = None
            optimization_instructions['order'] = i + offset
            optimization_instructions[
                'optimize_with_background'] = prior_beamset_name  # list(range(offset, offset + i))
        return optimization_instructions

    def beamset_complete(rso, beamset_name):
        """
        Check the beamsets for one with a matching name. If found, and has dose
        return True
        :param rso: raystation object (namedtuple)
        :param beamset_name: name of beamset to check
        :return: True: beamset found and has dose. False: no beamset with dose
                       found
        """
        beamset_exists = False
        beamset_has_valid_segments = False
        beamset_has_dose = False
        beamsets = [bs for p in rso.case.TreatmentPlans for bs in p.BeamSets]
        for bs in beamsets:
            if bs.DicomPlanLabel == beamset_name:
                # Check that each beam has valid segments
                valid_segments = [b.HasValidSegments for b in bs.Beams]
                if all(valid_segments):
                    beamset_has_valid_segments = True
                    # Check for dose
                    if bs.FractionDose.DoseValues is not None:
                        beamset_has_dose = True
                break
        return all(
            [beamset_exists, beamset_has_valid_segments, beamset_has_dose])

    def create_dict(pois, beamset_names, template, sup_order, mid_order, inf_order, site,
                    order_target_name, target, offset=0):
        """
            Creates a dictionary of plan parameters.

            Args:
                pois (list): List of Points of Interest.
                beamset_names (list): List of beamset names.
                template (str): Template name.
                sup_order (str): Order of supine isocenters.
                mid_order (str): Order of midline isocenters.
                inf_order (str): Order of prone isocenters.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                order_target_name (str): Name of the target for order.
                target (str): Target name.
                offset (int, optional): Offset value. Defaults to 0.

            Returns:
                list: List of dictionaries, each representing a plan.
        """
        dictionary = []
        prior_beamset_name = ""
        for i, n in enumerate(beamset_names):
            j_range = range(1, 10, 1)
            if site == "HFS_":
                target_poi = pois[len(pois) - 1 - i]
                order_name = inf_order if i == 0 else sup_order if i == len(pois) - 1 else mid_order
                translation_map = create_translation_map(
                    len(pois) - 1 - i, len(pois), j_range, site, rx, offset)
            else:
                target_poi = pois[i]
                order_name = inf_order if i == len(pois) - 1 else sup_order if i == 0 else mid_order
                translation_map = create_translation_map(i, len(pois), j_range, site, rx, offset)
            optimization_instructions = create_optimization_instructions(i, pois, site,
                                                                         prior_beamset_name)
            dictionary.append({
                    'protocol_name': PROTOCOL_NAME_VMAT,
                    'translation_map': {order_target_name: (target, rx, r'cGy'), **translation_map},
                    'order_name': order_name,
                    'planning_strategy': 'Sequential',
                    'optimization_instructions': optimization_instructions,
                    'num_fx': nfx,
                    'site': site,
                    'beamset_name': n,
                    'machine': VMAT_MACHINE,
                    'beamset_template': template,
                    'beamset_exists_skip': beamset_complete(rso,n),
                    'iso': {'type': 'POI', 'target': target_poi},
                    'optimize': True,
                    'user_prompts': False,
                })
            prior_beamset_name = n
        return dictionary

    hfs_dict = create_dict(hfs_pois, hfs_beamset_names, BEAMSET_HFS_VMAT, SUP_HFS_ORDER,
                           MID_HFS_ORDER, INF_HFS_ORDER, 'HFS_', ORDER_TARGET_NAME_HFS,
                           TARGET_HFS)
    ffs_dict = create_dict(ffs_pois, ffs_beamset_names, BEAMSET_FFS_VMAT, SUP_FFS_ORDER,
                           MID_FFS_ORDER, INF_FFS_ORDER, 'FFS_', ORDER_TARGET_NAME_FFS,
                           TARGET_FFS, offset=len(hfs_pois))

    return hfs_dict, ffs_dict


def transform_object(source: namedtuple, destination: namedtuple,
                     pois: list = None, rois: list = None) -> None:
    """
    This function obtains transformation from one examination to another,
    and applies it to points of interest (POIs) and regions of interest (ROIs).

    The function resets primary and secondary exams before performing
    transformations.
    The direction of transformation can be from 'ffs_to_hfs' or 'hfs_to_ffs'.

    Args:
        source (namedtuple): Object containing the patient case and examination
            information for the source of the rois/pois
        destination (namedtuple): Object containing the patient case and
            examination information for destination exam
        pois (list, optional): List of names of points of interest to
            transform. Defaults to None.
        rois (list, optional): List of names of regions of interest to
            transform. Defaults to None.

    Returns:
        None
    """

    prefix = determine_prefix(source.exam)
    if prefix == 'ffs':
        direction = 'ffs_to_hfs'
        ffs_scan_name = source.exam.Name
        hfs_scan_name = destination.exam.Name
        reset_primary_secondary(source.exam, destination.exam)
    else:
        direction = 'hfs_to_ffs'
        hfs_scan_name = source.exam.Name
        ffs_scan_name = destination.exam.Name
        reset_primary_secondary(destination.exam, source.exam)

    # Define the two operations and their respective methods
    operations = {
        'ffs_to_hfs': {
            'transformation': source.case.GetTransformForExaminations(
                FromExamination=ffs_scan_name, ToExamination=hfs_scan_name),
        },
        'hfs_to_ffs': {
            'transformation': source.case.GetTransformForExaminations(
                FromExamination=hfs_scan_name, ToExamination=ffs_scan_name),
        }
    }

    # Check if the direction is valid and perform transformations
    if direction in operations:
        # Convert the transformation details to a dictionary
        trans_list = source.case.GetTransformForExaminations(
            FromExamination=source.exam.Name,
            ToExamination=destination.exam.Name)
        trans = convert_array_to_transform(trans_list)
        # Apply transformation to POIs and ROIs if provided
        if pois:
            source.case.MapPoiGeometriesRigidly(
                PoiGeometryNames=pois, CreateNewPois=False,
                ReferenceExaminationName=source.exam.Name,
                TargetExaminationNames=[destination.exam.Name],
                Transformations=[trans])

        if rois:
            source.case.MapRoiGeometriesRigidly(
                RoiGeometryNames=rois, CreateNewRois=False,
                ReferenceExaminationName=source.exam.Name,
                TargetExaminationNames=[destination.exam.Name],
                Transformations=[trans])


def cut_rois_to_image(source: namedtuple, destination: namedtuple,
                      rois: list) -> None:
    """
    This function uses the cuts a transformed roi to the size of the
    external in the destination image.
    It creates a large box to ensure the entire source contour will be
    included, then it subtracts the external volume in the destination
    image.

    Args:
        source (namedtuple): Object containing patient case and examination
            information for the source examination.
        destination (namedtuple): Object containing patient case and examination information for the destination examination.
        rois (list): List of names of regions of interest to transform.

    Returns:
        None
    """

    # Maximum possible height for bounding box (in cm)
    wadlow = 272

    # Placeholder for ROIs to be deleted
    delete_list = []

    # Create a bounding box larger than possible body size
    big_box = make_box(destination, box_name='big_box', length=wadlow)
    delete_list.append(big_box)

    # Create a bounding box as large as the external examination
    box_name = make_box(destination, box_name=f'fov_box')
    delete_list.append(box_name)

    # Subtract smaller box from the large one
    destination.case.PatientModel.RoiSubtractionPostProcessing(
        Examination=destination.exam,
        SubtractionConfiguration={big_box: [box_name]})

    # Transform ROIs according to the determined direction
    transform_object(source, destination, rois=rois)

    # Subtract any regions outside of the destination set from the ROIs
    for roi in rois:
        destination.case.PatientModel.RoiSubtractionPostProcessing(
            Examination=destination.exam,
            SubtractionConfiguration={roi: [big_box]})

    # Delete temporary ROIs
    for roi_to_delete in delete_list:
        delete_roi(source.case, roi_to_delete)


def calculate_junction(pd_hfs, pd_ffs):
    # Determine the central junction using ffs scan
    central_junction_start = find_hfff_junction_coords(pd_ffs)
    # Place junction point
    place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=central_junction_start)
    # Map the junction point to the hfs scan
    transform_object(source=pd_ffs, destination=pd_hfs, pois=[JUNCTION_POINT],
                     rois=None)
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # Return poi rs object
    return hfs_poi_junction, ffs_poi_junction


def make_generic_junction_structs(rs_obj: namedtuple, z_junction: float, junction_width: float,
                                  j_name: Optional[str] = None,
                                  reverse: bool = False,
                                  j_range: Optional[range] = None):
    """
    Create generic junction structures at specified z-positions.

    Args:
        rs_obj: The object representing the RS file.
        z_junction: The z-position of the junction.
        junction_width: The width of the junction.
        j_name: Name of the junction structure.
        reverse: Flag indicating whether the junctions should be created in reverse order.
        j_range: Custom range of junction values.

    Returns:
        None
    """

    # IsoDose levels
    if j_range:
        j_i = j_range
    else:
        j_i = range(1, 10, 1)

    dim_si = junction_width / len(j_i)

    # Assign colors to dose levels
    if len(j_i) >= len(COLORS):
        color_levels = {j: COLORS[i] for i, j in enumerate(j_i)}
    else:
        color_levels = {j: COLORS[i % len(COLORS)] for i, j in enumerate(j_i)}

    for i in range(len(j_i)):
        if reverse:
            z_start = z_junction - dim_si * float(i)
        else:
            z_start = z_junction - dim_si * float(len(j_i) - i)

        make_central_junction_contour(
            rs_obj,
            z_inf_box=z_start,
            dim_si=dim_si,
            dose_level=str(int(j_i[i])),
            color=color_levels[j_i[i]],
            j_name=j_name)


def tomo_calc_iso(patient_data, target):
    """
    This function creates a fiducial point (SimFiducial) if it does not exist,
    and prompts the user to place it. It then calculates the coordinates of an
    isocenter and creates an ROI named 'ROI_<ffs/hfs>_iso' at that location.

    Args:
        patient_data (Object): Object containing the patient case and
            examination information.
        target (str): Name of the target ROI.

    Returns:
        iso_name (str): Name of the created isocenter ROI.
    """

    fiducial_point_name = 'SimFiducials'

    # Check if fiducials exist and are defined
    point_exists, point_defined = check_fiducials(
        patient_data, fiducial_name=fiducial_point_name)

    if not point_exists:
        # If fiducial point doesn't exist, create one
        AutoPlanOperations.place_fiducial(
            rso=patient_data, poi_name='SimFiducials')

        # Prompt the user to place the fiducial point in both FFS and HFS
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it '
            'there too')
        point_exists, point_defined = check_fiducials(
            patient_data, fiducial_name=fiducial_point_name)
    elif not point_defined:
        # If fiducial point exists but is not defined, prompt the user to
        # define it
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it '
            'there too')

    pm = patient_data.case.PatientModel

    # Retrieve the coordinates of the fiducial point and the center of the
    # target ROI
    sim_coordinates = pm.StructureSets[patient_data.exam.Name] \
        .LocalizationPoiGeometry.Point
    target_coordinates = pm.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[target].GetCenterOfRoi()

    # Define isocenter coordinates
    iso_coord = {
        'x': 0., 'y': target_coordinates['y'], 'z': sim_coordinates['z']}

    # Get prefix
    prefix = determine_prefix(patient_data.exam)

    # Create a unique name for the new ROI
    iso_name = pm.GetUniqueRoiName(
        DesiredName=f'{prefix}_iso')

    # Create new ROI at the isocenter
    pm.CreateRoi(Name=iso_name,
                 Color='Pink',
                 Type='Control')
    iso_roi = pm.RegionsOfInterest[iso_name]

    # Define the geometry of the new ROI as a small sphere at the isocenter
    iso_roi.CreateSphereGeometry(Radius=1.0,
                                 Examination=patient_data.exam,
                                 Center=iso_coord,
                                 Representation='Voxels',
                                 VoxelSize=0.01)

    return iso_name


def make_ffs_isodoses(pd_hfs, pd_ffs, rx, prefix):
    #
    ffs_scan_name = pd_ffs.exam.Name
    hfs_scan_name = pd_hfs.exam.Name
    ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        FromExamination=ffs_scan_name,
        ToExamination=hfs_scan_name)
    # Convert it to the transform dictionary
    trans_f2h = convert_array_to_transform(ffs_to_hfs)
    # If we pair the junctions and isodoses up front we can do this as one iteration
    # d_i = {<junction_region>: (low95%, med100%, high110%)}
    # Isodoses to get:
    d_i = [5, 10, 15, 20, 25, 30, 35, 40, 45,
           50, 55, 60, 65, 70, 75, 80, 85, 90,
           95, 100, 105, 110, 115]
    #
    # Get clean unsubtracted doses
    doses = dict([(str(d) + '%Rx', d) for d in d_i])
    make_unsubtracted_dose_structures(pd_ffs, rx, doses)
    #
    # Junctions
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    # construct pairs
    j_names = dict([(prefix + str(j) + '%Rx', (j + 10, j, j - 5)) for j in j_i])
    #
    # Generate subtracted dose values
    isodose_names = make_dose_structures(pd_ffs, isodoses=j_names)
    non_empty_isodose_names = []
    for idn in isodose_names:
        threshold_success = volume_threshold_roi(pd_ffs, idn)
        if threshold_success:
            non_empty_isodose_names.append(idn)
    pd_hfs.case.MapRoiGeometriesRigidly(
        RoiGeometryNames=non_empty_isodose_names,
        CreateNewRois=False,
        ReferenceExaminationName=ffs_scan_name,
        TargetExaminationNames=[hfs_scan_name],
        Transformations=[trans_f2h])


def get_new_grid(case, beamset_a, beamset_b):
    # Return a dose grid for beamset_a that includes all voxels used in beamset_b
    # Update the dose grid for plan a using b's grid.
    dg_a = beamset_a.GetDoseGrid()
    dg_b = beamset_b.GetDoseGrid()
    # Find minimum and maximum extent of beamset_a dose grid
    min_a = {'x': dg_a.Corner['x'],
             'y': dg_a.Corner['y'],
             'z': dg_a.Corner['z']}
    max_a = {'x': dg_a.Corner['x'] + dg_a.VoxelSize['x'] * dg_a.NrVoxels['x'],
             'y': dg_a.Corner['y'] + dg_a.VoxelSize['y'] * dg_a.NrVoxels['y'],
             'z': dg_a.Corner['z'] + dg_a.VoxelSize['z'] * dg_a.NrVoxels['z']}
    # Find minimum and maximum extent of beamset_b dose grid
    min_b = {'x': dg_b.Corner['x'],
             'y': dg_b.Corner['y'],
             'z': dg_b.Corner['z']}
    max_b = {'x': dg_b.Corner['x'] + dg_b.VoxelSize['x'] * dg_b.NrVoxels['x'],
             'y': dg_b.Corner['y'] + dg_b.VoxelSize['y'] * dg_b.NrVoxels['y'],
             'z': dg_b.Corner['z'] + dg_b.VoxelSize['z'] * dg_b.NrVoxels['z']}
    # Transform beamset_b dose grid extrema to image set a coordinates
    t_b_min = transform_poi(case, min_b, beamset_b, beamset_a)
    t_b_max = transform_poi(case, max_b, beamset_b, beamset_a)
    # Find the inferior-most grid
    lower_corner = {'x': min(min_a['x'], t_b_min['x']),
                    'y': min(min_a['y'], t_b_min['y']),
                    'z': min(min_a['z'], t_b_min['z']),
                    }
    # Find the superior-most grid
    upper_corner = {'x': max(max_a['x'], t_b_max['x']),
                    'y': max(max_a['y'], t_b_max['y']),
                    'z': max(max_a['z'], t_b_max['z']),
                    }
    new_grid = {'Corner': {'x': lower_corner['x'], 'y': lower_corner['y'], 'z': lower_corner['z']},
                'NrVoxels': {
                    'x': math.ceil(upper_corner['x'] - lower_corner['x']) / dg_a.VoxelSize['x'],
                    'y': math.ceil(upper_corner['y'] - lower_corner['y']) / dg_a.VoxelSize['y'],
                    'z': math.ceil(upper_corner['z'] - lower_corner['z']) / dg_a.VoxelSize['z']},
                'VoxelSize': dg_a.VoxelSize}
    return new_grid


def find_transform(case, from_name, to_name):
    for r in case.Registrations:
        if r.StructureRegistrations[0].FromExamination.Name == from_name \
                and r.StructureRegistrations[0].ToExamination.Name == to_name:
            return r
    return None


def transform_poi(case: object, point: dict, from_name: object, to_name: object) -> dict:
    """
    Transforms a point of interest (POI) between two frames of reference.

    Args:
        case (RS case object): The case object that includes the transformation details.
        point (dict): Dictionary containing the x, y, z coordinates of the point.
        from_name (object): The source frame of reference.
        to_name (object): The target frame of reference.

    Returns:
        dict: The transformed coordinates {'x': x, 'y': y, 'z': z}.

    Pseudocode:
        1. Get the transformation between the source and target frames of reference.
        2. If no transformation is found, try the reverse transformation.
        3. If still not found, raise an error.
        4. Transform the given point using the transformation matrix.
    """
    # Get the transformation from the source to the target frame of reference
    reg = case.GetTransform(FromFrameOfReference=from_name.FrameOfReference,
                            ToFrameOfReference=to_name.FrameOfReference)
    if reg is None:
        # Try the reverse transformation if the direct transformation is not found
        reg = case.GetTransform(FromFrameOfReference=to_name.FrameOfReference,
                                ToFrameOfReference=from_name.FrameOfReference)
        if reg is None:
            raise RuntimeError(f'No Registration between {from_name} to {to_name}')
        else:
            reg_inv = np.reshape(reg, (4, 4))
            transform_matrix = np.linalg.inv(reg_inv)
    else:
        transform_matrix = np.reshape(reg, (4, 4))

    x = np.array([point['x'], point['y'], point['z'], 1])
    x_transformed, y_transformed, z_transformed, _ = np.matmul(transform_matrix, np.transpose(x)).tolist()
    return {'x': x_transformed, 'y': y_transformed, 'z': z_transformed}


def find_eval_dose(case, beamset_name: str, exam_name: str):
    """
    Function to find and evaluate dose calculations.

    Parameters:
    case : The case to find dose calculations in.
    beamset_name : The name of the beamset to match.
    exam_name : The name of the examination to match.

    Returns:
    tuple : Tuple containing a boolean and the matched dose calculation.
            If no match is found, returns (False, None)
    """

    def find_matching_doses():
        """
        Helper function to find doses that match the beamset_name
        and exam_name.

        Returns:
        list : List of tuples, where each tuple is a matched dose
               and its associated length.
        """
        return [(d, len(d.DoseValues.DoseData) if d.DoseValues else 0)
                for fe in case.TreatmentDelivery.FractionEvaluations
                for de in fe.DoseOnExaminations
                for d in de.DoseEvaluations
                if d.ForBeamSet.DicomPlanLabel == beamset_name
                and de.OnExamination.Name == exam_name]

    matching_doses = find_matching_doses()

    if len(matching_doses) == 0:
        return False, None

    if len(matching_doses) == 1 and matching_doses[0][1] > 1:
        return True, matching_doses[0][0]

    largest_dose = max(matching_doses, key=lambda x: x[1])
    if largest_dose[1] > 0:
        return True, largest_dose[0]

    raise RuntimeError(
        f'Too Many Dose calcs found for {beamset_name}. '
        f'Try deleting some of the plan evaluations and rerunning the script.')


def find_beamset(case, beamset_name):
    for p in case.TreatmentPlans:
        for bs in p.BeamSets:
            if bs.DicomPlanLabel == beamset_name:
                return p, bs
    return None


def dose_summation_gui(case, plans, beamsets):
    Sg.ChangeLookAndFeel('DarkPurple4')
    layout = [[Sg.Text("FFS Plan")],
              [Sg.Combo(plans, key="-FFS PLAN-",
                        default_value=plans[0],
                        size=(40, 1), )],
              [Sg.Text("FFS Beamset")],
              [Sg.Combo(beamsets, key="-FFS BEAMSET-",
                        default_value=beamsets[0],
                        size=(40, 1))],
              [Sg.Text("HFS Plan")],
              [Sg.Combo(plans, key="-HFS PLAN-",
                        default_value=plans[0],
                        size=(40, 1))],
              [Sg.Text("HFS Beamset")],
              [Sg.Combo(beamsets, key="-HFS BEAMSET-",
                        default_value=beamsets[0],
                        size=(40, 1))],
              [Sg.B('OK'), Sg.B('Cancel')]]
    window = Sg.Window("BEAMSET ASSIGNMENT",
                       layout)
    while True:
        event, values = window.read()
        if event == Sg.WIN_CLOSED or event == "Cancel":
            selections = None
            break
        elif event == "OK":
            selections = values
            break
    window.close()
    if selections == {}:
        sys.exit('Selection Script was cancelled')
    ffs_plan = None
    hfs_plan = None
    ffs_beamset = None
    hfs_beamset = None

    for tp in case.TreatmentPlans:
        if tp.Name == selections['-FFS PLAN-']:
            ffs_plan = tp
            for bs in tp.BeamSets:
                if bs.DicomPlanLabel == selections['-FFS BEAMSET-']:
                    ffs_beamset = bs
                    break
        if tp.Name == selections['-HFS PLAN-']:
            hfs_plan = tp
            for bs in tp.BeamSets:
                if bs.DicomPlanLabel == selections['-HFS BEAMSET-']:
                    hfs_beamset = bs
                    break
    if not all([ffs_beamset, ffs_plan, hfs_beamset, hfs_plan]):
        sys.exit('No HFS FFS Beamsets defined')
    else:
        return ffs_plan, ffs_beamset, hfs_plan, hfs_beamset


def make_structures(pd_hfs, pd_ffs,
                    make_vmat_plan, make_tomo_plan, testing=False):
    hfs_scan_name = pd_hfs.exam.Name
    ffs_scan_name = pd_ffs.exam.Name
    make_derived_rois(pd_hfs, pd_ffs)
    if make_vmat_plan:
        # Load the Tomo Supports for the couch
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        AutoPlanOperations.load_supports(rso=pd_hfs,
                                         supports=["TrueBeamCouch", "Baseplate_Override_PMMA"],
                                         quiet=testing)
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TrueBeamCouch"],
                                         quiet=testing)
    elif make_tomo_plan:
        # Load TrueBeam couch and baseplate
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        AutoPlanOperations.load_supports(rso=pd_hfs,
                                         supports=["TomoCouch", "Baseplate_Override_PMMA"],
                                         quiet=testing)
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TomoCouch"],
                                         quiet=testing)

    register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, testing)

    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    load_normal_mbs(pd_hfs, pd_ffs, quiet=testing)
    # Build lung contours & avoidance on the HFS scan
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    make_lung_contours(pd_hfs, color=[192, 192, 192])

    ffs_poi_junction, hfs_poi_junction = make_central_junction_structs(
        pd_hfs, pd_ffs)


def make_vmat_planning_structures(pd_hfs, pd_ffs, nfx, rx):
    #
    # HFS
    # Add points for isocenters in VMAT
    hfs_poi_junction = pd_hfs.case.PatientModel \
        .StructureSets[pd_hfs.exam.Name].PoiGeometries[JUNCTION_POINT]
    hfs_junction_width = place_hfs_vmat_pois(pd_hfs, hfs_poi_junction)
    hfs_pois = find_pois(pd_hfs)
    # Add the midfield junctions
    make_midfield_junctions(pd_hfs, hfs_pois, junction_width=hfs_junction_width)
    # Iterate over POIs and create OTVs
    for index, point in enumerate(hfs_pois):
        make_otv(pd_hfs, point, index, hfs_junction_width, hfs_pois)

    # Do the same for FFS
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    ffs_junction_width = place_ffs_vmat_pois(
        pd_ffs, ffs_poi_junction, len(hfs_pois))
    ffs_pois = find_pois(pd_ffs)
    make_midfield_junctions(pd_ffs, ffs_pois, junction_width=ffs_junction_width)
    for index, point in enumerate(ffs_pois):
        make_otv(pd_ffs, point, index, ffs_junction_width, ffs_pois)

    hfs_multiplan, ffs_multiplan = multiplan_data(
        pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx)
    return hfs_multiplan, ffs_multiplan


def tbi_gui(bypass=False):
    """
    Displays a GUI for TBI planning parameter selection. The user can choose
    between a Tomo or VMAT plan and specify relevant parameters.

    Args:
        bypass (bool): Whether to bypass the GUI and return test parameters.

    Returns:
        dict: A dictionary containing the user's selections.

    Raises:
        RuntimeError: If the GUI is cancelled without making selections.
    """
    gui_width = 40
    if bypass:
        connect.await_user_input('System is in testing mode. No clinical use')
        logging.warning("System in testing mode. No clinical use")
        return {
            '-NFX-': 4,
            '-TOTAL DOSE-': 800,
            '-MACHINE-': "HDA0488",
            # '-MACHINE-': "TrueBeam_NoTrack",
            '-THI-': True,
            '-VMAT-': False,
            '-FFS PLAN-': False,
            '-HFS PLAN-': True,
            '-FFS ISODOSE-': False,
            '-FFS STRUCTURES-': False,
            '-SUM DOSE-': True
        }

    # User Prompt for Dose/Fractions
    gui_layout = [
        [Sg.Text('Enter Number of Fractions'), Sg.Input(key='-NFX-')],
        [Sg.Text('Enter TOTAL Dose in cGy'), Sg.Input(key='-TOTAL DOSE-')],
        [Sg.Radio(
            'Generate Tomo Plan', "RADIO1", default=True, key='-TOMO-',
            tooltip='Choose only one, but choose wisely', enable_events=True),
            Sg.Radio(
                'Generate VMAT Plan', "RADIO1", default=False, key='-VMAT-',
                tooltip='There can be only one.', enable_events=True)],
        [Sg.Checkbox(
            'Generate Planning Structures', default=True,
            key='-FFS STRUCTURES-',
            tooltip='Lungs, central junction, kidneys, etc...')],
        [Sg.Checkbox('Make FFS Plan', default=True, key='-FFS PLAN-')],
        [Sg.Checkbox('Make FFS Junction Isodose Structures',
                     default=True, key='-FFS ISODOSE-')],
        [Sg.Checkbox('Make HFS Plan', default=True, key='-HFS PLAN-')],
        [Sg.Checkbox('Make Dose Summation', default=True, key='-SUM DOSE-')],
        [Sg.Button('OK'), Sg.Button('Cancel')]
    ]

    window = Sg.Window('AUTO TBI SELECTIONS', gui_layout,
                       default_element_size=(gui_width, 1), grab_anywhere=False)

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED or event == "Cancel":
            selections = {}
            break
        elif event == "OK":
            selections = values
            break

    window.close()

    if not selections:
        raise RuntimeError('TBI Script was cancelled')
    if selections['-TOMO-']:
        selections['-MACHINE-'] = "HDA0488"
        selections['-THI-'] = True
    elif selections['-VMAT-']:
        selections['-MACHINE-'] = "TrueBeam_NoTrack"
        selections['-THI-'] = False

    return selections


def main():
    """
    Runs a series of functions to perform TBI planning and dose summation.

    Pseudocode:
    1. Call tbi_gui() function to obtain user input.
    2. Retrieve the necessary variables from user input.
    3. Find HFS and FFS scans, assign them to variables.
    4. Initialize a named tuple for the patient, case, exam, plan, and beamset.
    5. If requested by the user, load couch supports and build lung contours and avoidance on the
    HFS scan.
    6. If requested by the user, plan FFS and HFS.
    7. If requested by the user, make isodoses for FFS.
    8. If requested by the user, perform dose summation.

    Returns: None
    """
    # Prerequisites for operations:
    # generate_thi_ffs_plan: External, AvoidSkin, External+1
    # Launch gui
    testing = False
    tbi_selections = tbi_gui(bypass=testing)

    nfx = tbi_selections['-NFX-']
    rx = tbi_selections['-TOTAL DOSE-']
    do_structure_definitions = tbi_selections['-FFS STRUCTURES-']
    ffs_autoplan = tbi_selections['-FFS PLAN-']
    make_ffs_isodose_structs = tbi_selections['-FFS ISODOSE-']
    hfs_autoplan = tbi_selections['-HFS PLAN-']
    dose_summation = tbi_selections['-SUM DOSE-']
    make_tomo_plan = tbi_selections['-THI-']
    make_vmat_plan = tbi_selections['-VMAT-']

    # Rename the HFS/FFS Exams
    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)

    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd_hfs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=hfs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=None,
                beamset=None)

    pd_ffs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=ffs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=None,
                beamset=None)
    check_prerequisites(pd_ffs, pd_hfs, do_structure_definitions, make_vmat_plan)

    if do_structure_definitions:
        make_structures(pd_hfs, pd_ffs, make_vmat_plan, make_tomo_plan, testing)
        if make_vmat_plan:
            hfs_multiplan, ffs_multiplan = make_vmat_planning_structures(pd_hfs, pd_ffs, nfx, rx)

    if ffs_autoplan:
        toggle_ptv_type(pd_ffs,
                        rois=[TARGET_HFS, TARGET_HFS + EVAL_SUFFIX],
                        roi_type='Undefined')
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        #
        # FFS Planning
        # FFS protocol declarations
        if make_vmat_plan:
            # Compute the locations of the isocenters in the VMAT FFS Location
            hfs_pois = find_pois(pd_hfs)
            ffs_pois = find_pois(pd_ffs)
            #
            # Load each treating beamset and the objectives of the VMAT autoplan
            hfs_multiplan, ffs_multiplan = multiplan_data(
                pd_ffs, hfs_pois, ffs_pois, nfx=nfx, rx=rx)
            pd_ffs_out = multi_autoplan(ffs_multiplan)
        if make_tomo_plan:
            reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
            iso_target = tomo_calc_iso(
                pd_ffs,
                target=JUNCTION_PREFIX_FFS + "10%Rx")
            tbi_ffs_protocol = {
                'protocol_name': PROTOCOL_NAME_TOMO,
                'translation_map': {
                    ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')},
                'order_name': ORDER_NAME_FFS_TOMO,
                'exam': pd_ffs.exam.Name,
                'planning_strategy': 'Sequential',
                'optimization_instructions': {},
                'num_fx': nfx,
                'site': 'TBI_',
                'beamset_name': BEAMSET_NAME_FFS_TOMO,
                'machine': TOMO_MACHINE,
                'beamset_template': BEAMSET_TEMPLATE_FFS_TOMO,
                'iso': {'type': 'ROI', 'target': iso_target},
                'optimize': True,
                'user_prompts': True,
            }
            pd_ffs_out = multi_autoplan([tbi_ffs_protocol])
        toggle_ptv_type(pd_ffs,
                    rois=[TARGET_HFS, TARGET_HFS + EVAL_SUFFIX],
                    roi_type='Ptv')
    #
    # Make Dose contours for FFS plan and transfer them to HFS scan
    if make_ffs_isodose_structs and make_tomo_plan:
        # TODO: Redefine acquisition of these to be determined based on
        #  expected TOMO Plan and Beamset Name
        # Get isodoses
        pd_ffs = Pd(error=[],
                    patient=GeneralOperations.find_scope(level='Patient'),
                    case=GeneralOperations.find_scope(level='Case'),
                    exam=ffs_exam,
                    db=GeneralOperations.find_scope(level='PatientDB'),
                    plan=GeneralOperations.find_scope(level='Plan'),
                    beamset=GeneralOperations.find_scope(level='BeamSet'))
        #
        # Make sure the current FFS scan is primary
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)

        pd_ffs.patient.Save()
        pd_ffs.plan.SetCurrent()
        pd_ffs.beamset.SetCurrent()
        make_ffs_isodoses(pd_hfs, pd_ffs, rx, JUNCTION_PREFIX_FFS)

    if make_ffs_isodose_structs and make_vmat_plan:
        # Get isodoses
        case = GeneralOperations.find_scope(level='Case')
        # Find the ffs vmat plan
        hfs_pois = find_pois(pd_hfs)
        ffs_pois = find_pois(pd_ffs)
        hfs_multiplan, ffs_multiplan = multiplan_data(
            pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx)
        vmat_ffs_p, vmat_ffs_bs = find_beamset(
            case, beamset_name=ffs_multiplan[0]['beamset_name'])
        pd_ffs = Pd(error=[],
                    patient=GeneralOperations.find_scope(level='Patient'),
                    case=case,
                    exam=ffs_exam,
                    db=GeneralOperations.find_scope(level='PatientDB'),
                    plan=vmat_ffs_p,
                    beamset=vmat_ffs_bs)
        #
        # Make sure the current FFS scan is primary
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)

        pd_ffs.patient.Save()
        pd_ffs.plan.SetCurrent()
        pd_ffs.beamset.SetCurrent()
        prefix = JUNCTION_PREFIX_FFS
        make_ffs_isodoses(pd_hfs, pd_ffs, rx, prefix)
    #
    # HFS Planning
    if hfs_autoplan:
        toggle_ptv_type(pd_hfs,
                        rois=[TARGET_FFS, TARGET_FFS + EVAL_SUFFIX],
                        roi_type='Undefined')
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)

        if make_tomo_plan:
            # HFS protocol declarations
            iso_target = tomo_calc_iso(pd_hfs, target=TARGET_HFS)
            tbi_hfs_protocol = {
                'protocol_name': PROTOCOL_NAME_TOMO,
                'translation_map': {
                    ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')},
                'order_name': ORDER_NAME_HFS_TOMO,
                'planning_strategy': 'Sequential',
                'optimization_instructions': {},
                'num_fx': nfx,
                'site': 'TBI_',
                'beamset_name': BEAMSET_NAME_HFS_TOMO,
                'machine': TOMO_MACHINE,
                'beamset_template': BEAMSET_TEMPLATE_HFS_TOMO,
                'iso': {'type': 'ROI', 'target': iso_target},
                'optimize': True,
                'user_prompts': True,
            }
            tbi_hfs_protocol = multi_autoplan([tbi_hfs_protocol])
        #
        elif make_vmat_plan:
            #
            # HFS Junction
            hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
                .PoiGeometries[JUNCTION_POINT]
            hfs_pois = [p.Name for p in pd_hfs.case.PatientModel.PointsOfInterest
                        if HFS_POI in p.Name]
            ffs_pois = [p.Name for p in pd_ffs.case.PatientModel.PointsOfInterest
                        if FFS_POI in p.Name]
            # HFS protocol declarations
            hfs_multiplan, ffs_multiplan = multiplan_data(
                pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx)
            tbi_hfs_protocol = multi_autoplan(hfs_multiplan)
        else:
            raise RuntimeError(
                'Plan selected that is not VMAT or TOMO. Exiting')
        toggle_ptv_type(tbi_hfs_protocol['rso'],
                        rois=[TARGET_FFS, TARGET_FFS + EVAL_SUFFIX],
                        roi_type='Ptv')

    if dose_summation:
        # Update the current variables if needed.
        # User Prompt for Dose/Fractions
        if not pd_hfs.beamset or not pd_ffs.beamset:
            pd_ffs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=ffs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=None,
                        beamset=None)
            plans = [p.Name for p in pd_ffs.case.TreatmentPlans]

            beamsets = [bs.DicomPlanLabel for p in pd_ffs.case.TreatmentPlans for bs in p.BeamSets]

            ffs_plan, ffs_beamset, hfs_plan, hfs_beamset = dose_summation_gui(pd_ffs.case, plans, beamsets)

            pd_ffs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=ffs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=ffs_plan,
                        beamset=ffs_beamset)
            pd_hfs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=hfs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=hfs_plan,
                        beamset=hfs_beamset)
        new_hfs_grid = get_new_grid(pd_hfs.case, pd_hfs.beamset, pd_ffs.beamset)
        pd_hfs.beamset.UpdateDoseGrid(Corner=new_hfs_grid['Corner'],
                                      VoxelSize=new_hfs_grid['VoxelSize'],
                                      NumberOfVoxels=new_hfs_grid['NrVoxels'])
        new_ffs_grid = get_new_grid(pd_ffs.case, pd_ffs.beamset, pd_hfs.beamset)
        pd_ffs.beamset.UpdateDoseGrid(Corner=new_ffs_grid['Corner'],
                                      VoxelSize=new_ffs_grid['VoxelSize'],
                                      NumberOfVoxels=new_ffs_grid['NrVoxels'])
        # Recompute selected doses on adjusted dose grid
        for b in [pd_ffs.beamset, pd_hfs.beamset]:
            try:
                b.ComputeDose(ComputeBeamDoses=False, DoseAlgorithm='CCDose',
                              ForceRecompute=False)
            except Exception as e:
                logging.debug(f'During dose summation, '
                              f'dose computation failed for {b.DicomPlanLabel}: {e}')
                pass

        pd_ffs.beamset.ComputeDoseOnAdditionalSets(
            OnlyOneDosePerImageSet=False,
            AllowGridExpansion=True,
            ExaminationNames=[pd_hfs.exam.Name],
            FractionNumbers=[0],
            ComputeBeamDoses=True)
        ffs_dose, ffs_dose_found = find_eval_dose(pd_hfs.case,
                                                  pd_ffs.beamset.DicomPlanLabel,
                                                  pd_hfs.exam.Name)
        if not ffs_dose_found:
            raise RuntimeError('Unable to compute FFS dose on HFS examination'
                               f'Report error to script {__author__}')

        try:
            # Create summation
            _ = pd_hfs.case.CreateSummedDose(
                DoseName="TBI",
                FractionNumber=0,
                DoseDistributions=[pd_hfs.beamset.FractionDose, ffs_dose],
                Weights=[nfx] * 2)  # 2 for two dose grids
        except Exception as e:
            logging.warning(
                f'Could not sum doses in {pd_hfs.beamset.DicomPlanLabel}: '
                f'and FFS: {pd_ffs.beamset.DicomPlanLabel}: Error: {e}')
            raise RuntimeError('Could not sum doses, report error to '
                               'script developer')


if __name__ == '__main__':
    main()
