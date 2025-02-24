""" Automated Plan - Tomo VMAT TBI
This module implements functions for Total Body Irradiation (TBI) treatment planning
using Tomo and VMAT techniques. It supports a complete workflow from user input and
scan identification to plan optimization and dose summation.

Workflow Overview:
------------------
1. User Input:
   - Launch a GUI to capture treatment parameters (e.g., number of fractions, total dose,
     treatment machine).
2. Scan Identification:
   - Identify HFS (Head First Supine) and FFS (Feet First Supine) CT scans in the patient case.
3. Data Initialization:
   - Initialize patient, case, and examination data structures.
4. Structure Generation (if enabled):
   - Load couch supports, create junction ROIs, and verify fusion alignment.
   - Generate normal MBS, lung contours, and TBI planning structures.
5. FFS Planning (if enabled):
   - Reset scans, compute FFS isocenter coordinates, define planning protocols, and perform
     auto-planning.
6. FFS Isodose Structures (if enabled):
   - Reset scans, retrieve isodose names, map junction points between FFS and HFS, and update ROIs.
7. HFS Planning (if enabled):
   - Reset scans, define HFS protocols, and perform auto-planning with background dose evaluation.
8. Dose Summation (if enabled):
   - Prompt for beamset selection (if necessary), update dose grids, recompute doses, and combine
     HFS and FFS dose distributions.
9. Finalization:
   - Complete the TBI planning process.

Key Functions Summary:
-----------------------
- Validation and Setup:
    check_external, check_structure_exists, get_most_inferior, get_center.
- ROI and Transformation:
    find_junction_coords, place_poi, convert_array_to_transform, determine_prefix,
    find_roi_prefix, update_all_remove_expression.
- Structure Creation:
    make_junction_contour, make_kidneys_contours, make_lung_contours, get_roi_geometries,
    make_avoid, make_ptv, make_dose_structures.
- Scan and Dose Management:
    reset_primary_secondary, rescale_dose_grid_to_all_scans, register_images,
    load_normal_mbs, make_tbi_planning_structs, check_fiducials,
    calc_ffs_iso, make_ffs_isodoses.
- Plan Execution and GUI:
    transform_poi, find_eval_dose, tbi_gui, main.

Validation:
-----------
Test Patient: MR#

Version History:
----------------
0.0.0 - Original version.
0.0.1 - Updated to avoid robust planning.

TODO:
    - Handle patients that are too short to maintain a pelvis junction.
    - Provide immediate warnings about VMAT height limits.
    - Consider adding functionality for the script to create individual feet OTVs.
    - Larger changes:
            - Add a "separate beamset" button to facilitate splitting beamsets.
            - Optionally, copy the plan pre-split as a backup.
        - Improve isocenter placement for shorter patients (i.e., lower junction placement) and support a single orientation.
            - Use reliable estimates of patient height to calculate isocenter positions.
            - Consider manual placement of the junction—but be cautious about potential clearance issues.

License:
--------
This program is free software under the GNU General Public License (GPLv3 or later).
See <http://www.gnu.org/licenses/> for details.
"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '04-Feb-2025'
__version__ = '0.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11 SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/AutoPlanTomoTBI'
__credits__ = []

import math
import logging
import connect
import sys
import os
import shutil
import datetime
import traceback
import GeneralOperations
import AutoPlanOperations
from StructureOperations import (create_roi, create_poi,
                                 make_wall, make_externalclean, make_boolean_structure, check_roi,
                                 find_types, exclude_from_export, change_roi_type)
from roi_operations import (roi_in_list)
from collections import namedtuple
import PySimpleGUI as Sg
import re
from typing import Optional, List

script_dir = os.path.dirname(os.path.abspath(__file__))
# general_dir = os.path.join(script_dir, '../../../', 'general')
# sys.path.insert(1, general_dir)
from library.api.api_case import get_rigid_registrations
from general.AutoPlan import multi_autoplan  # noqa: E402

DEBUG = True
# Hard-coded path to protocols
PROTOCOL_FOLDER = r'../../protocols'
INSTITUTION_FOLDER = r'UW'
AUTOPLAN_FOLDER = r'AutoPlans'
PATH_PROTOCOLS = os.path.join(os.path.dirname(__file__),
                              PROTOCOL_FOLDER, INSTITUTION_FOLDER, AUTOPLAN_FOLDER)

PATH_TO_OUTPUT = os.path.normpath(
    "Q:\\RadOnc\\RayStation\\RayScripts\\AutoPlanData")
DICOM_PATH = os.path.normpath('\\\\m-rayscon02587\\DicomImageStorage')

# PROTOCOL/ORDER/BEAMSET INPUTS
# TOMO PROTOCOL
PROTOCOL_FILE_TOMO = "TomoTBI.xml"
PROTOCOL_NAME_TOMO = "UW Tomo TBI"
ORDER_NAME_FFS_TOMO = "TomoTBI_FFS"
ORDER_NAME_HFS_TOMO = "TomoTBI_HFS"
ORDER_NAME_HFS_KIDNEY_TOMO = "TomoTBI_Kidney_HFS"
BEAMSET_TEMPLATE_FFS_TOMO = "Tomo_TBI_FFS_FW50"
BEAMSET_TEMPLATE_HFS_TOMO = "Tomo_TBI_HFS_FW50"
TOMO_MACHINE = "HDA0488"
# VMAT PROTOCOL
PROTOCOL_FILE_VMAT = "UW_VMAT_TBI.xml"
PROTOCOL_NAME_VMAT = "UW VMAT TBI"
BEAMSET_HFS_VMAT = "VMAT-HFS-TBI"
BEAMSET_FFS_VMAT = "VMAT-FFS-TBI"
VMAT_MACHINE = "TrueBeam"
# ORDER NAMES
HFS_PELVIS_ORDER_NAME = 'VMAT_TBI_HFS_PELVIS_UPDATED'
HFS_PELVIS_KIDNEY_ORDER_NAME = 'VMAT_TBI_HFS_PELVIS_KIDNEY'
HFS_CHEST_ORDER_NAME = 'VMAT_TBI_HFS_CHEST_NOOBJ'
HFS_HEAD_ORDER_NAME = 'VMAT_TBI_HFS_HEAD_NOOBJ'
FFS_PELVIS_ORDER_NAME = 'VMAT_TBI_FFS_PELVIS_UPDATED'
FFS_LEGS_ORDER_NAME = 'VMAT_TBI_FFS_LEGS_NOOBJ'
FFS_FEET_ORDER_NAME = 'VMAT_TBI_FFS_FEET_NOOBJ'

ORDER_TARGET_NAME_FFS = "PTV_p_FFS"
ORDER_TARGET_NAME_HFS = "PTV_p_HFS"
# PLAN CONVENTIONS
DEFAULT_VOXEL_SIZE = {'x': 0.4, 'y': 0.4, 'z': 0.4}  # [cm]
# TOMO PLAN CONVENTIONS
HFS_TOMO_PLAN_NAME = "HFS__TBI_Tomo_Auto"
HFS_TOMO_BEAMSET_NAME = "HFS__TBI_Tomo"
FFS_TOMO_BEAMSET_NAME = "FFS__TBI_Tomo"
FFS_TOMO_PLAN_NAME = "FFS__TBI_Tomo_Auto"
TOMO_FFS_TRANSFER_NAME = "Tomo_FFS_Trnsfr"
FFS_PLACEHOLDER_NAME = "Empty plan"  # Default name assigned by RS upon plan import
# VMAT PLAN CONVENTIONS
HFS_VMAT_BEAMSET_NAME = "HFS__VMA"
HFS_VMAT_PLAN_NAME = HFS_VMAT_BEAMSET_NAME + "_Auto"
FFS_VMAT_BEAMSET_NAME = "FFS__VMA"
FFS_VMAT_PLAN_NAME = FFS_VMAT_BEAMSET_NAME + "_Auto"
VMAT_FFS_TRANSFER_NAME = "VMAT_FFS_Trnsfr"
# CLEARANCE ASSUMPTIONS FOR VMAT
MIN_FFS_OVERLAP = 2  # Minimum Overlap
HFS_OVERLAP = 5  # Minimum Overlap
FW = 39  # 39 cm of MLC based field
CENTRAL_JUNCTION_WIDTH = 1.2 * 9
# FFS_MAX_TREATMENT_LENGTH = 111.5
FFS_MAX_TREATMENT_LENGTH = 99  # TODO - A fudge - based junction placement on packing HFS
#  replace with a function of patient height
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
# POI:
JUNCTION_POINT = "junction"
HFS_POI = 'HFS_POI'
FFS_POI = 'FFS_POI'
# CONTOURS:
EXTERNAL_SETUP = 'External_PRV10'
EXTERNAL_SETUP_EXP = 1.0  # cm expansion
EXTERNAL_NAME = "ExternalClean"
AVOID_HFS_NAME = "Avoid_HFS"
AVOID_FFS_NAME = "Avoid_FFS"
SKIN_AVOIDANCE = 'Avoid_Skin_PRV05'
SKIN_AVOIDANCE_CONTRACT = 0.5  # cm contraction
LUNG_AVOID_NAME = "Lungs_m07"
LUNG_AVOID_MARGIN = 0.7  # cm contraction
LUNGS = "Lungs"
LUNGS_EVAL_MARGIN = 1.0  # cm contraction for margin
LUNGS_EVAL_NAME = LUNGS + "_m10"
KIDNEYS = "Kidneys"
KIDNEY_AVOID_NAME = KIDNEYS + "_m05"
KIDNEY_AVOID_MARGIN = 0.5  # cm contraction
# TARGET CONTOURS:
TARGET_FFS = "PTV_p_FFS"
TARGET_HFS = "PTV_p_HFS"
EVAL_SUFFIX = "_Eval"
JUNCTION_PREFIX_FFS = "ffs_junction_"
JUNCTION_PREFIX_HFS = "hfs_junction_"
HFS_TARGET_EVAL_NAME = TARGET_HFS + EVAL_SUFFIX
FFS_TARGET_EVAL_NAME = TARGET_FFS + EVAL_SUFFIX
HFS_TARGET_NAMES = [TARGET_HFS, HFS_TARGET_EVAL_NAME]
FFS_TARGET_NAMES = [TARGET_FFS, FFS_TARGET_EVAL_NAME]
# ALL CONTOURS

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
COLORS = [[127, 0, 255],
          [0, 0, 255],
          [0, 127, 255],
          [0, 255, 255],
          [0, 255, 127],
          [0, 255, 0],
          [127, 255, 0],
          [255, 255, 0],
          [255, 127, 0],
          [255, 0, 0],
          [255, 0, 255]]


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


def hfs_ffs_exam_present(case):
    """
    Check if the case has both HFS and FFS exams
    :param case: patient case
    :return: True if both HFS and FFS exams are present, False otherwise
    """
    hfs_exam = False
    ffs_exam = False
    for e in case.Examinations:
        if e.PatientPosition == 'HFS':
            hfs_exam = True
        elif e.PatientPosition == 'FFS':
            ffs_exam = True
    return hfs_exam, ffs_exam


def check_prerequisites(pd_ffs, pd_hfs, phase, vmat, n_fx=None, rx=None, otv_junctions=False):
    """
    Check if prerequisite points, contours, registrations are present based on work expected
    :param pd_ffs: patient data for feet-first supine
    :param pd_hfs: patient data for head-first supine
    :param phase: phase of planning
    :param otv_junctions: whether to check for junctions
    :raises RuntimeError: if any prerequisite is missing

    FFS Planning:
        Generate Structures:
            * A case with a CT scan in the FFS position
            * A case with a CT scan in the HFS position
            VMAT:
            TOMO:
        Make FFS Plan:
            * check_contours(pd_hfs, PREPLANNING_HFS_CONTOUR_NAMES) and check_contours(pd_ffs, PREPLANNING_FFS_CONTOUR_NAMES)
            * Kidneys, Skin_Avoid, External_PRV10, Avoid_FFS,
            * ffs_junction_10%,... on FFS exam
            * hfs_junction_10%,... on HFS exam
            * Points: junction, SimFiducials on both exams
            * PTV_HFS, PTV_HFS_Eval, PTV_FFS, PTV_FFS_Eval on both exams
            VMAT:
                find_pois(pd_ffs) and find_pois(pd_hfs)
            TOMO:
        Optimize FFS Plan:
            All the stuff for FFS planning +
            VMAT:
                An existing plan called FFS__VMA_Auto, beamset FFS__VMA
            TOMO:
                An existing plan called FFS__Tomo_Auto, beamset FFS__Tomo

    HFS Planning:
        Calculate FFS Plan on HFS Image:
            VMAT:
                All the stuff for Optimize FFS Plan
                A plan called FFS__VMA_Auto, beamset FFS__VMA with valid beams segments
            TOMO:
        Make HFS Plan:
            VMAT:
                All the stuff for Calculate FFS Plan on HFS Image
                A valid evaluation dose existing on the HFS image set from the FFS plan
            TOMO:
        Optimize HFS Plan:
            * check_contours(pd_hfs, PREPLANNING_HFS_CONTOUR_NAMES) and check_contours(pd_ffs, PREPLANNING_FFS_CONTOUR_NAMES)
            VMAT:
                find_pois(pd_ffs) and find_pois(pd_hfs)
            TOMO:

    Post-Planning
        Separate Beamsets
            VMAT:
                An existing plan called FFS__VMA_Auto, beamset FFS__VMA
                An existing plan called HFS__VMA_Auto, beamset HFS__VMA
                Valid Beams and Beamsets for all of these with calculated dose
                Plan for HFS should have a background dose evaluation of FFS plan
        Composite Dose...
    """
    if phase == '-FFS STRUCTURES-':
        check_ffs_structure_prerequisites(pd_ffs, pd_hfs)
    if '-FFS PLAN-' in phase:
        check_ffs_structure_prerequisites(pd_ffs, pd_hfs)
        check_ffs_plan_prerequisites(pd_ffs, pd_hfs, vmat, otv_junctions)
    if '-CALC FFS PLAN ON HFS-' in phase:
        check_ffs_structure_prerequisites(pd_ffs, pd_hfs)
        check_ffs_plan_prerequisites(pd_ffs, pd_hfs, vmat, otv_junctions)
        check_plan_validity(pd_ffs, vmat, n_fx, rx)
    if '-FFS EXPORT-' in phase:
        check_ffs_structure_prerequisites(pd_ffs, pd_hfs)
        check_ffs_plan_prerequisites(pd_ffs, pd_hfs, vmat, otv_junctions)
        check_plan_validity(pd_ffs, vmat, n_fx, rx)
        check_evaluation_dose_transfer(pd_ffs, pd_hfs)
        check_empty_plans(pd_ffs, pd_hfs, exists=False, unique=False)
    if '-HFS PLAN-' in phase:
        check_ffs_structure_prerequisites(pd_ffs, pd_hfs)
        check_ffs_plan_prerequisites(pd_ffs, pd_hfs, vmat, otv_junctions)
        check_plan_validity(pd_ffs, vmat, n_fx, rx)
        check_evaluation_dose_transfer(pd_ffs, pd_hfs)
        if not plan_transfer_successful(pd_hfs, pd_ffs, n_fx):
            check_empty_plans(pd_ffs, pd_hfs, exists=True, unique=True)
            check_exported_plan(pd_ffs, pd_hfs)


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


def check_ffs_structure_prerequisites(pd_ffs, pd_hfs):
    PRECONTOURING_HFS_CONTOUR_NAMES = ["Lung_L", "Lung_R", "Kidney_R", "Kidney_L"]
    PRECONTOURING_FFS_CONTOUR_NAMES = ["Kidney_R", "Kidney_L", "Leg_Distal_R", "Leg_Distal_L"]
    patient_data = [pd_ffs, pd_hfs]
    # Check external contours
    for pdat in patient_data:
        if not check_external(pdat):
            raise RuntimeError(f'Exam {pdat.exam.Name} has an invalid external contour')
    # Check current case for HFS and FFS scans
    for pdat in patient_data:
        hfs_scan_present, ffs_scan_present = hfs_ffs_exam_present(pdat.case)
        if not hfs_scan_present or not ffs_scan_present:
            raise RuntimeError('This script requires a head first and feet first scan'
                               f' in the case {pdat.case.CaseName}: HFS {hfs_scan_present}, FFS {ffs_scan_present}')
    # Check for missing pre-contouring contours
    logging.debug(f'HFS: Checking precontouring contours for Case {pd_hfs.case.CaseName} '
                  f'Exam: {pd_hfs.exam.Name}, for {PRECONTOURING_HFS_CONTOUR_NAMES}')
    hfs_missing = check_contours(pd_hfs, PRECONTOURING_HFS_CONTOUR_NAMES)
    logging.debug(f'FFS: Checking precontouring contours for Case {pd_ffs.case.CaseName} '
                  f'Exam: {pd_ffs.exam.Name}, for {PRECONTOURING_FFS_CONTOUR_NAMES}')
    ffs_missing = check_contours(pd_ffs, PRECONTOURING_FFS_CONTOUR_NAMES)
    if hfs_missing or ffs_missing:
        logging.error(f'Missing precontouring contours: HFS {hfs_missing}, FFS {ffs_missing}')
        raise RuntimeError(f'Missing precontouring contours: HFS {hfs_missing}, FFS {ffs_missing}')


def check_ffs_plan_prerequisites(pd_ffs, pd_hfs, vmat=False, otv_junctions=False):
    PREPLANNING_HFS_CONTOUR_NAMES = [
        "Lung_L", "Lung_R", "Kidney_R", "Kidney_L", LUNG_AVOID_NAME, KIDNEY_AVOID_NAME,
        LUNGS_EVAL_NAME, SKIN_AVOIDANCE, EXTERNAL_SETUP, AVOID_HFS_NAME, TARGET_HFS, HFS_TARGET_EVAL_NAME]
    PREPLANNING_FFS_CONTOUR_NAMES = [
        "Kidney_R", "Kidney_L", SKIN_AVOIDANCE, EXTERNAL_SETUP, AVOID_FFS_NAME, TARGET_FFS, FFS_TARGET_EVAL_NAME]
    POI_NAMES = [JUNCTION_POINT, 'SimFiducials']
    FFS_JUNCTION = [JUNCTION_PREFIX_FFS + str(i * 10) + "%Rx" for i in range(1, 10)]
    HFS_JUNCTION = [JUNCTION_PREFIX_HFS + str(i * 10) + "%Rx" for i in range(1, 10)]
    hfs_missing = check_contours(pd_hfs, PREPLANNING_HFS_CONTOUR_NAMES)
    ffs_missing = check_contours(pd_ffs, PREPLANNING_FFS_CONTOUR_NAMES)
    if hfs_missing or ffs_missing:
        logging.error(f'Missing contours: HFS {hfs_missing}, FFS {ffs_missing}, please run'
                      f'the Generate Structures script first')
        raise RuntimeError(f'Missing contours: HFS {hfs_missing}, FFS {ffs_missing}')
    # Check junction contours
    hfs_junction_missing = check_contours(pd_hfs, HFS_JUNCTION)
    ffs_junction_missing = check_contours(pd_ffs, FFS_JUNCTION)
    if hfs_junction_missing or ffs_junction_missing:
        raise RuntimeError(f'Missing junction contours in HFS {hfs_junction_missing}, FFS {ffs_junction_missing}')
    # Check for junction and SimFiducials
    for p in POI_NAMES:
        for pd in [pd_ffs, pd_hfs]:
            # Check if the POI exists
            if not poi_in_list(pd.case, p):
                raise RuntimeError(f'Missing POI {p} in {pd.exam.Name}')
            # Check if the POI has a valid position
            _ = get_point_position(pd, p)
    # Check registrations for an HFS to FFS registration
    check_registration(pd_hfs, pd_ffs)
    if vmat:
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


def check_contours(patient_data, roi_list):
    """
    Check if the patient data has all required contours
    :param patient_data: data for a single patient
    :param roi_list: list of names of required contours
    :param exam_name: name of the exam to check
    :return: list of names of missing contours, empty if all are present
    """
    logging.debug(f'Checking contours for Case {patient_data.case.CaseName} '
                  f'Exam: {patient_data.exam.Name}: {roi_list}')
    missing_contours = []
    for r in roi_list:
        if not roi_has_contours(patient_data, r):
            missing_contours.append(r)
    return missing_contours


def check_registration(pdata_hfs, pdata_ffs):
    registrations = [r for r in pdata_hfs.case.Registrations]
    hfs_exam_name = pdata_hfs.exam.Name
    ffs_exam_name = pdata_ffs.exam.Name
    ffs_to_hfs_found = False
    try:
        for r in registrations:
            # Backwards, potential API bug?
            if r.RegistrationSource.FromExamination.Name == ffs_exam_name \
                    and r.RegistrationSource.ToExamination.Name == hfs_exam_name:
                ffs_to_hfs_found = True
                break
    except Exception as e:
        if "Object has no member 'RegistrationSource'" in str(e):
            raise RuntimeError('Approve the registration between HFS and FFS')
        logging.error(f'Error checking registration: {e}')
        raise RuntimeError(f'No registration from HFS to FFS found:  {e}')
    if not ffs_to_hfs_found:
        raise RuntimeError('No registration from HFS to FFS found')


def check_plan_validity(patient_data, vmat, n_fx, rx):
    if vmat:
        try:
            plan = patient_data.case.TreatmentPlans[f'{FFS_VMAT_PLAN_NAME}']
        except Exception as e:
            raise RuntimeError(f'No plan {FFS_VMAT_PLAN_NAME} found: {e}')
        try:
            beamset = plan.BeamSets[FFS_VMAT_BEAMSET_NAME]
        except Exception as e:
            raise RuntimeError(f'No beamset {FFS_VMAT_BEAMSET_NAME} found in plan {FFS_VMAT_PLAN_NAME}: {e}')
    else:
        try:
            plan = patient_data.case.TreatmentPlans[FFS_TOMO_PLAN_NAME]
        except Exception as e:
            raise RuntimeError(f'No plan {FFS_TOMO_PLAN_NAME} found: {e}')
        try:
            beamset = plan.BeamSets[FFS_TOMO_BEAMSET_NAME]
        except Exception as e:
            raise RuntimeError(f'No beamset {FFS_TOMO_BEAMSET_NAME} found in plan {FFS_TOMO_PLAN_NAME}: {e}')
    beamset_exists, beamset_has_valid_segments, beamset_has_dose = beamset_complete(patient_data,
                                                                                    beamset.DicomPlanLabel)
    if not beamset_exists:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} does not exist')
    if not beamset_has_valid_segments:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} does not have valid segments')
    if not beamset_has_dose:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} is not calculated')
    # Check if the plan has the correct number of fractions and prescription
    if beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue != rx:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} has incorrect prescription dose'
                           f' Input: {beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue} != '
                           f' Plan: {rx}')
    if beamset.FractionationPattern.NumberOfFractions != n_fx:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} has incorrect number of fractions.'
                           f' Input: {n_fx} != Plan: {beamset.FractionationPattern.NumberOfFractions}')


def check_evaluation_dose_transfer(pd_ffs, pd_hfs):
    evaluation_doses = get_available_evaluation_doses(pd_ffs.case)
    if not evaluation_doses:
        raise RuntimeError('No evaluation doses found: Run the Calculate FFS Plan on HFS Image script first')
    eval_dose = get_evaluation_dose_values(pd_ffs.beamset.DicomPlanLabel,
                                           pd_hfs.exam.Name,
                                           'HFS',
                                           evaluation_doses)
    if eval_dose is None:
        raise RuntimeError(f'No evaluation dose found for {pd_ffs.beamset.DicomPlanLabel} '
                           f'on {pd_hfs.exam.Name}')


def plan_transfer_successful(pd_hfs, pd_ffs, nfx):
    # Look through the existing plans in the HFS representation,
    # and check if the FFS plan has been transferred
    # Find the corresponding dose evaluation
    _, ffs_dose_evaluation = find_dose_evaluation(pd_ffs, pd_hfs)

    modality = pd_ffs.beamset.DeliveryTechnique
    hfs_transfer_name = TOMO_FFS_TRANSFER_NAME if modality == 'TomoHelical' else VMAT_FFS_TRANSFER_NAME
    hfs_plan_name = HFS_TOMO_PLAN_NAME if modality == 'TomoHelical' else HFS_VMAT_PLAN_NAME

    uid = None
    if ffs_dose_evaluation:
        uid = ffs_dose_evaluation.ModificationInfo.DicomUID
    for tp in pd_hfs.case.TreatmentPlans:
        if hfs_plan_name == tp.Name:
            for bs in tp.BeamSets:
                logging.debug(f'Checking beamset {bs.DicomPlanLabel} for {hfs_transfer_name}')
                if bs.DicomPlanLabel == hfs_transfer_name:
                    is_clinical = bs.IsApprovedToUseAsBackgroundDose()
                    is_scaled = bs.FractionationPattern.NumberOfFractions == nfx
                    logging.debug(f'Beamset {bs.DicomPlanLabel} is clinical: {is_clinical}, '
                                  f'is scaled: {is_scaled}')
                    logging.debug(f'Beamset {bs.DicomPlanLabel} comment: {bs.Comment}'
                                  f'UID: {uid}')
                    if uid:
                        if f'<FFS_UID>:{uid}' in bs.Comment and is_clinical and is_scaled:
                            return True
        elif FFS_PLACEHOLDER_NAME == tp.Name:
            for bs in tp.BeamSets:
                logging.debug(f'Checking beamset {bs.DicomPlanLabel} for {FFS_PLACEHOLDER_NAME}')
                if FFS_PLACEHOLDER_NAME == bs.DicomPlanLabel:
                    logging.debug(f'Beamset {bs.DicomPlanLabel} comment: {bs.Comment}'
                                  f'UID: {uid}')
                    if f'<FFS_UID>:{uid}' in bs.Comment:
                        return True
    return False


def find_dose_evaluation(pd_ffs, pd_hfs):
    """
    Find the dose evaluation for the FFS plan on the HFS exam and
    the dose evaluation
    """
    fraction_evaluations = [f for f in pd_ffs.case.TreatmentDelivery.FractionEvaluations]
    ffs_dose_on_examination = None
    ffs_dose_evaluation = None
    for f in fraction_evaluations:
        for dose_exam in f.DoseOnExaminations:
            dose_eval = dose_exam.DoseEvaluations[0]
            if dose_eval.ForBeamSet.DicomPlanLabel == pd_ffs.beamset.DicomPlanLabel and \
                    dose_exam.OnExamination.Name == pd_hfs.exam.Name and \
                    dose_exam.OnExamination.PatientPosition == pd_hfs.exam.PatientPosition:
                ffs_dose_evaluation = dose_eval
                ffs_dose_on_examination = dose_exam
    return ffs_dose_on_examination, ffs_dose_evaluation


def check_empty_plans(pd_ffs, pd_hfs, exists=True, unique=True):
    # Check for containers already existing in the hfs plan.
    empty_plans = []
    hfs_plan_names = potential_transfer_plan_names(pd_ffs)
    for tp in pd_hfs.case.TreatmentPlans:
        logging.debug(f'Looking in {tp.Name} for {hfs_plan_names}')
        if any([n in tp.Name for n in hfs_plan_names]):
            empty_plans.append(tp.Name)
    if exists:
        if len(empty_plans) == 0:
            raise RuntimeError(
                f'No {FFS_PLACEHOLDER_NAME} found in the HFS exam, run the export script first')
        elif len(empty_plans) > 1:
            raise RuntimeError(f'Multiple plans with name {hfs_plan_names} found in the HFS exam, delete all '
                               f'plans with plan name "{hfs_plan_names}" and re-export the FFS plan')
    else:
        if len(empty_plans) > 0:
            raise RuntimeError(f'{FFS_PLACEHOLDER_NAME} found in the HFS exam, delete all plans with'
                               f'plan name "{FFS_PLACEHOLDER_NAME}" and re-export the FFS plan')
    if unique and len(empty_plans) > 1:
        raise RuntimeError(
            f'Multiple plans with name {FFS_PLACEHOLDER_NAME} found in the HFS exam, delete all plans with'
            f'plan name "{FFS_PLACEHOLDER_NAME}" and re-export the FFS plan')


def potential_transfer_plan_names(pd_ffs):
    modality = pd_ffs.beamset.DeliveryTechnique
    return [FFS_PLACEHOLDER_NAME, HFS_TOMO_PLAN_NAME] if modality == 'TomoHelical' \
        else [FFS_PLACEHOLDER_NAME, HFS_VMAT_PLAN_NAME]


def potential_transfer_beamset_names(pd_ffs):
    modality = pd_ffs.beamset.DeliveryTechnique
    return [FFS_PLACEHOLDER_NAME, TOMO_FFS_TRANSFER_NAME] if modality == 'TomoHelical' \
        else [FFS_PLACEHOLDER_NAME, VMAT_FFS_TRANSFER_NAME]


def check_exported_plan(pd_ffs, pd_hfs):
    _, ffs_dose_evaluation = find_dose_evaluation(pd_ffs, pd_hfs)
    uid = None
    if ffs_dose_evaluation:
        uid = ffs_dose_evaluation.ModificationInfo.DicomUID
    if not uid:
        raise RuntimeError(f'No UID found for the FFS plan on the HFS exam, run the export script first')

    hfs_plan_names = potential_transfer_plan_names(pd_ffs)
    hfs_beamset_names = potential_transfer_beamset_names(pd_ffs)
    empty_plan = None
    for tp in pd_hfs.case.TreatmentPlans:
        if any([n in tp.Name for n in hfs_plan_names]):
            empty_plan = tp
            break
    if not empty_plan:
        raise RuntimeError(
            f'No plan {FFS_PLACEHOLDER_NAME} found in the HFS exam, run the export script first')
    empty_beamset = None
    for bs in empty_plan.BeamSets:
        if any([n in bs.DicomPlanLabel for n in hfs_beamset_names]):
            empty_beamset = bs
            break
    if not empty_beamset:
        raise RuntimeError(f'No beamset found for {hfs_beamset_names}, please re-export the FFS plan')
    if not empty_beamset.FractionDose.DoseValues.AlgorithmProperties.DoseAlgorithm == 'Imported':
        raise RuntimeError(f'{empty_beamset.DicomPlanLabel} beamset does not have an imported dose. '
                           f'Please re-export the FFS plan')
    if not empty_beamset.HasImportedDose():
        raise RuntimeError(f'{empty_beamset.DicomPlanLabel} beamset does not have an imported dose type. '
                           f'Please re-export the FFS plan')
    if f'<FFS_UID:{uid}>' not in empty_beamset.Comment:
        raise RuntimeError(f'{empty_beamset.DicomPlanLabel} beamset does not have a matching UID. '
                           f'Please re-export the FFS plan')




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


def estimate_patient_height(pd_hfs, pd_ffs, external_roi_name="External", junction_name="junction"):
    """
    Estimate patient height using HFS and FFS scans.

    The function obtains the top (head) and bottom (feet) positions from the external ROI
    and uses a common junction point (defined in both scans) to cross-check the computation.

    Args:
        pd_hfs: Patient data for the HFS (Head First Supine) scan.
        pd_ffs: Patient data for the FFS (Feet First Supine) scan.
        external_roi_name (str): Name of the external ROI. Default is "External".
        junction_name (str): Name of the junction POI. Default is "junction".

    Returns:
        float: Estimated patient height (in the same unit as the z-coordinate, typically centimeters).
    """
    # Retrieve the superior-most z-coordinate from the HFS scan (e.g., top of the head)
    head_top = get_most_superior(pd_hfs, external_roi_name)

    # Retrieve the inferior-most z-coordinate from the FFS scan (e.g., bottom of the feet)
    feet_bottom = get_most_inferior(pd_ffs, external_roi_name)

    # Retrieve the z-coordinate of the junction point from both scans
    junction_hfs_z = get_point_position(pd_hfs, junction_name).z
    junction_ffs_z = get_point_position(pd_ffs, junction_name).z

    # For clarity, compute distances above and below the junction point:
    head_to_junction = head_top - junction_hfs_z  # distance from head to junction
    junction_to_feet = junction_ffs_z - feet_bottom  # distance from junction to feet

    # The estimated patient height is the sum of these two distances.
    estimated_height = head_to_junction + junction_to_feet

    logging.info(f"Patient height estimation: {estimated_height:.2f} cm")

    return estimated_height


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


def round_iso(iso):
    return math.ceil(iso * 10) / 10


def place_ffs_vmat_pois(pd_ffs, junction, offset):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_ffs.case,
                                 roi_type='External')

    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    last_iso_position = round_iso(ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + FW / 2)
    first_iso_position = round_iso(junction.Point.z - FW / 2)
    isocenter_distance = ((first_iso_position - last_iso_position)
                          / (FFS_ISO_NUMBER - 1))
    isocenter_distance = round_iso(isocenter_distance)
    ffs_junction_width = FW - isocenter_distance
    logging.info(f'Distance from inferior most point at {ffs_ext_z:.2f} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {float(ffs_ext_z - junction.Point.z):.2f} with '
                 f'spacing {isocenter_distance:.2f} requires '
                 f'{FFS_ISO_NUMBER} isocenters, '
                 f'with an overlap of {ffs_junction_width}')
    # Junction location
    pois = []
    # Round the positions of the isocenter to the nearest mm.
    coords = {'x': round_iso(junction.Point.x),
              'y': round_iso(junction.Point.y)}
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

        # Make two mid-field junctions
        make_generic_junction_structs(rs_obj, z_junct, junction_width,
                                      j_name=f'_iso{n0}{n1}', j_range=range(1, 3))


def place_hfs_vmat_pois(pd_hfs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_hfs.case,
                                 roi_type='External')
    j_z = junction.Point.z
    hfs_ext_z = get_most_superior(pd_hfs, roi_name=external_name)
    hfs_treatment_length = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z
    iso_number = math.ceil(hfs_treatment_length / (FW - HFS_OVERLAP))
    last_iso_position = round_iso(j_z - CENTRAL_JUNCTION_WIDTH + FW / 2)
    first_iso_position = round_iso(hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - FW / 2)
    isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
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
        isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
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


def find_hfff_junction_coords(pd_ffs, max_treatment_length=FFS_MAX_TREATMENT_LENGTH):
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
        'z': ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + max_treatment_length
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
    external_name = find_types(case, roi_type='External')[0]
    bb_external = patient_model.StructureSets[exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(patient_data, roi_name=external_name)
    z_center = c_external['z'] if z_center is None else z_center
    length = bb_external[1].z - bb_external[0].z if length is None else length
    if length > 200:
        # Need to make multiple boxes
        n_box = int(length / 200)
        box_length = length / n_box
    else:
        n_box = 1
        box_length = length
    logging.debug(f'Measured length of external contour: {bb_external[1].z - bb_external[0].z}')
    logging.debug(f'Building a box with length {length} centered at {z_center}')
    delete_boxes = []
    for i in range(n_box):
        # Create the box
        box_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=box_name + f'_{i}' if n_box > 1 else box_name,
            delete_existing=True)
        z_center = z_center + i * box_length
        box_geom.OfRoi.CreateBoxGeometry(
            Size={'x': abs(bb_external[1].x - bb_external[0].x) + 2,
                  'y': abs(bb_external[1].y - bb_external[0].y) + 2,
                  'z': box_length},
            Examination=patient_data.exam,
            Center={'x': c_external['x'],
                    'y': c_external['y'],
                    'z': z_center},
            Representation='Voxels',
            VoxelSize=None)
        delete_boxes.append(box_name + f'_{i}')
    if n_box > 1:
        #
        # Boolean Definitions for Kidneys
        box_defs = get_boolean_defs(
            roi_name=box_name,
            a_sources=delete_boxes,
            a_operation="Union",
            export=False,
        )
        make_boolean_structure(
            patient=patient_data.patient, case=case,
            examination=exam, **box_defs)
        for b in delete_boxes:
            case.PatientModel.RegionsOfInterest[b].DeleteRoi()
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


def make_lung_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    lungs_defs = get_boolean_defs(
        roi_name=LUNGS,
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
        a_sources=[LUNGS],
        a_operation="Union",
        a_exp=[LUNG_AVOID_MARGIN] * 6,
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
        a_sources=[LUNGS],
        a_operation="Union",
        a_exp=[LUNGS_EVAL_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_eval_defs)


def make_kidney_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    kidneys_defs = get_boolean_defs(
        roi_name=KIDNEYS,
        a_sources=["Kidney_L", "Kidney_R"],
        a_operation="Union",
        color=color,
        export=True,
        roi_type="Organ"
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **kidneys_defs)
    kidneys_avoid_defs = get_boolean_defs(
        roi_name=KIDNEY_AVOID_NAME,
        a_sources=[KIDNEYS],
        a_operation="Union",
        a_exp=[KIDNEY_AVOID_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **kidneys_avoid_defs)





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


def make_ptv(pdata, junction_prefix, avoid_name, color=None, kidney_sparing=False):
    # Find all contours matching prefix and along with otv_name
    # return the external minus these objects
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        eval_name = FFS_TARGET_EVAL_NAME
    else:
        eval_name = HFS_TARGET_EVAL_NAME
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
    roi_exclude.append(SKIN_AVOIDANCE)
    roi_exclude.append(LUNGS_EVAL_NAME)
    if kidney_sparing:
        roi_exclude.append(KIDNEY_AVOID_NAME)
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


def reset_primary_secondary(exam1, exam2):
    # Resets exam 1 as primary and exam2 as secondary
    exam1.SetPrimary()
    exam2.SetSecondary()


def rescale_dose_grid_to_all_scans(pdata):
    """Rescale dose grid to cover all scans.

    We compute a bounding box from all ROI geometries (PTVs, Support, External).
    We then potentially shift and enlarge the dose grid if necessary.
    Specifically, if the modality is TomoHelical, we apply a fudge factor of 1.1
    that lowers the corner in the Y direction by 10% of the original bounding-box size
    and thus increases the Y dimension by 10%.
    """

    pm = pdata.case.PatientModel
    dg = pdata.beamset.GetDoseGrid()
    modality = pdata.beamset.DeliveryTechnique

    origin_frame_of_reference = pdata.beamset.FrameOfReference
    origin_exam_name = pdata.exam.Name

    logging.debug(f'Current dose grid corner: {dg.Corner}, '
                  f'Voxel size: {dg.VoxelSize}, '
                  f'Number of voxels: {dg.NrVoxels}')

    # Build initial bounding box from the current dose grid
    bb = [
        dg.Corner,
        {k: dg.Corner[k] + dg.VoxelSize[k] * dg.NrVoxels[k]
         for k in dg.Corner.keys()}
    ]
    logging.debug(f'Current dose grid bounding box: {bb}')

    # Types of ROIs to consider
    types = ['Ptv', 'Support', 'External']

    # Collect all structure sets and adjust bounding box as needed
    for s in pm.StructureSets:
        structure_frame_of_reference = s.OnExamination.EquipmentInfo.FrameOfReference
        transform_needed = (structure_frame_of_reference != origin_frame_of_reference)
        destination_name = s.OnExamination.Name if transform_needed else None

        if transform_needed:
            logging.debug(f'Need to transform from {origin_exam_name} to {destination_name}')

        for r in s.RoiGeometries:
            if r.OfRoi.Type in types:
                try:
                    bs = s.RoiGeometries[r.OfRoi.Name].GetBoundingBox()
                    # Transform bounding box if needed
                    bs_tr = ([
                                 pdata.case.TransformPointFromExaminationToExamination(
                                     FromExamination=destination_name,
                                     ToExamination=origin_exam_name,
                                     Point=b) for b in bs
                             ] if transform_needed else bs)
                    # Extend the bounding box if needed
                    for c, v in bs_tr[0].items():
                        if v < bb[0][c]:
                            logging.debug(f'Lower corner extended in {c} '
                                          f'from {bb[0][c]} to {v}')
                            bb[0][c] = v
                    for c, v in bs_tr[1].items():
                        if v > bb[1][c]:
                            logging.debug(f'Upper corner extended in {c} '
                                          f'from {bb[1][c]} to {v}')
                            bb[1][c] = v

                except Exception as e:
                    no_geom_set = "no geometry set for ROI"
                    if no_geom_set not in str(e):
                        logging.warning(f'Error in updating dose grid: {e}')

    # Prepare new grid specs
    vs = dg.VoxelSize
    span = {k: abs(bb[1][k] - bb[0][k]) for k in bb[1].keys()}
    logging.debug(f'New dose grid span after expansions: {span}')

    update_number_voxels = {
        k: math.ceil(v / vs[k]) for (k, v) in span.items()
    }

    # Check if we need to update dose grid
    needs_update = (
            update_number_voxels != dg.NrVoxels
            or bb[0] != dg.Corner
            or vs != dg.VoxelSize
    )

    logging.debug(f'Corner: {bb[0]}, '
                  f'Voxel size: {vs}, '
                  f'Number of voxels: {update_number_voxels}, '
                  f'Dose grid update needed: {needs_update}')

    # Update the dose grid if needed
    if needs_update:
        pdata.beamset.UpdateDoseGrid(
            Corner=bb[0],
            VoxelSize=vs,
            NumberOfVoxels=update_number_voxels
        )

    return needs_update


def check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    approved = False
    # Look through registration objects
    registrations = get_rigid_registrations(pd_ffs.case)
    for r in registrations:
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
                'Check the fusion alignment of the boney anatomy in the hips.\n '
                'Approve the registration.\n Then continue script.')
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
    LUNGS, KIDNEYS, SKIN_AVOIDANCE, EXTERNAL_SETUP,
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
    make_kidney_contours(pd_hfs, color=[192, 192, 192])
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


def make_central_junction_structs(pd_hfs, pd_ffs, kidney_sparing):
    """

    Args:
        pd_hfs: hfs named tuple
        pd_ffs: ffs named tuple
        kidney_sparing: Boolean to determine if kidney sparing is used

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
                            avoid_name=AVOID_FFS_NAME, kidney_sparing=False)
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
                            avoid_name=AVOID_HFS_NAME, kidney_sparing=kidney_sparing)
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


def beamset_complete(rso, beamset_name):
    """Check if a beamset with a matching name exists and if it has valid segments and dose.

    Searches through all TreatmentPlans in the provided RSO object for a beamset whose
    DicomPlanLabel matches the given beamset_name. If found, it then validates each beam
    in the beamset by ensuring that for each beam, BeamMU > 0 and either:
      - The DeliveryTechnique is 'TomoHelical', or
      - The beam has valid segments (HasValidSegments is True).
    Finally, it checks if the beamset has associated dose values.

    Args:
        rso: A RayStation object with a nested structure (e.g., rso.case.TreatmentPlans).
        beamset_name: The name of the beamset to search for.

    Returns:
        A list of booleans in the order:
          [beamset_exists, beamset_has_valid_segments, beamset_has_dose]
    """
    # Find the beamset with the matching name, if it exists.
    beamset = next(
        (bs for plan in rso.case.TreatmentPlans for bs in plan.BeamSets
         if bs.DicomPlanLabel == beamset_name),
        None
    )

    # If no beamset is found, return all False.
    if beamset is None:
        return [False, False, False]

    # Mark that the beamset exists.
    beamset_exists = True

    # Validate each beam: Must have BeamMU > 0 and either be 'TomoHelical' or have valid segments.
    beamset_has_valid_segments = all(
        b.BeamMU > 0 and (b.DeliveryTechnique == 'TomoHelical' or b.HasValidSegments)
        for b in beamset.Beams
    )

    # Check that the beamset has dose values.
    beamset_has_dose = beamset.FractionDose.DoseValues is not None

    return [beamset_exists, beamset_has_valid_segments, beamset_has_dose]


def get_tomo_plan_defs(rso, target, nfx, rx, optimize=False, kidney_sparing=False):
    iso_target = tomo_calc_iso(rso, target=target)
    protocol = {
        'protocol_name': PROTOCOL_NAME_TOMO,
        'planning_strategy': 'Sequential',
        'num_fx': nfx,
        'site': 'TBI_',
        'machine': TOMO_MACHINE,
        'iso': {'type': 'ROI', 'target': iso_target},
        'optimize': optimize,
        'user_prompts': False,
        'rso': None,
    }

    if rso.exam.PatientPosition == 'HFS':
        # HFS protocol declarations
        protocol['translation_map'] = {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')}
        protocol['order_name'] = ORDER_NAME_HFS_KIDNEY_TOMO if kidney_sparing else ORDER_NAME_HFS_TOMO
        protocol['plan_name'] = HFS_TOMO_PLAN_NAME
        protocol['beamset_name'] = HFS_TOMO_BEAMSET_NAME
        protocol['beamset_template'] = BEAMSET_TEMPLATE_HFS_TOMO
        protocol['optimization_instructions'] = {'optimize_with': None,
                                                 'optimize_with_background': TOMO_FFS_TRANSFER_NAME,
                                                 'lock_dose_grid': True}
    elif rso.exam.PatientPosition == 'FFS':
        # FFS protocol declarations
        protocol['translation_map'] = {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')}
        protocol['order_name'] = ORDER_NAME_FFS_TOMO
        protocol['plan_name'] = FFS_TOMO_PLAN_NAME
        protocol['beamset_name'] = FFS_TOMO_BEAMSET_NAME
        protocol['beamset_template'] = BEAMSET_TEMPLATE_FFS_TOMO
        protocol['optimization_instructions'] = {'optimize_with': None,
                                                 'optimize_with_background': None,
                                                 'lock_dose_grid': False}
    return protocol


def get_vmat_plan_defs(rso, hfs_pois, ffs_pois, nfx, rx, optimize=False, kidney_sparing=False):
    """
        This function generates data dictionaries for multiple plan treatments.

        Args:
            rso (object): RayStation object.
            hfs_pois (list): A list of HFS (Head-First Supine) Points of Interest (POIs).
            ffs_pois (list): A list of FFS (Feet-First Supine) POIs.
            nfx (int): Number of fractions.
            rx (int): Radiation dose.
            optimize (bool): If True, optimization should be performed.
            kidney_sparing (bool): If True, kidney sparing takes place.

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
            f'TBI_FFS_{offset + 2}LegS',
            f'TBI_FFS_{offset + 3}LegI',
            f'TBI_FFS_{offset + 4}Knee',
            f'TBI_FFS_{offset + 5}Feet'],
        4: [f'TBI_FFS_{offset + 1}Pelv',
            f'TBI_FFS_{offset + 2}LegS',
            f'TBI_FFS_{offset + 3}LegI',
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
        if site == 'HFS_':
            prefix = 'hfs'
            translation_map = {HFS_TARGET_EVAL_NAME: (f'{HFS_TARGET_EVAL_NAME}', rx, r'cGy')}
        else:
            prefix = 'ffs'
            translation_map = {FFS_TARGET_EVAL_NAME: (f'{FFS_TARGET_EVAL_NAME}', rx, r'cGy')}
        for j in j_range:
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
        optimization_instructions = {'optimize_with': None, 'lock_dose_grid': True}
        if site == 'HFS_':
            optimization_instructions['order'] = len(pois) - i
            optimization_instructions['optimize_with_background'] = VMAT_FFS_TRANSFER_NAME
        return optimization_instructions

    def get_xml_config(patient_position, n_pts):
        if kidney_sparing:
            pelvis_order_name = HFS_PELVIS_KIDNEY_ORDER_NAME
        else:
            pelvis_order_name = HFS_PELVIS_ORDER_NAME
        HFS_5ISO_XML_CONFIG = {0: (pelvis_order_name, 'TBI_HFS_5Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_4AbdI'),
                               2: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_3AbdS'),
                               3: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               4: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_5ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_6Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_7LegS'),
                               2: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_8LegI'),
                               3: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_9Knee'),
                               4: (FFS_FEET_ORDER_NAME, 'TBI_FFS_10Feet')}
        HFS_4ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_4Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_3Abdo'),
                               2: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               3: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_4ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_5Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_6LegS'),
                               2: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_7LegI'),
                               3: (FFS_FEET_ORDER_NAME, 'TBI_FFS_8Feet')}
        HFS_3ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_3Pelv'),
                               1: (HFS_CHEST_ORDER_NAME, 'TBI_HFS_2Chst'),
                               2: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_3ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_4Pelv'),
                               1: (FFS_LEGS_ORDER_NAME, 'TBI_FFS_5Leg'),
                               2: (FFS_FEET_ORDER_NAME, 'TBI_FFS_6Feet')}
        HFS_2ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_2Pelv'),
                               1: (HFS_HEAD_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_2ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_3Pelv'),
                               1: (FFS_FEET_ORDER_NAME, 'TBI_FFS_4Feet')}
        HFS_1ISO_XML_CONFIG = {0: (HFS_PELVIS_ORDER_NAME, 'TBI_HFS_1Head')}
        FFS_1ISO_XML_CONFIG = {0: (FFS_PELVIS_ORDER_NAME, 'TBI_FFS_2Pelv')}
        HFS_XML_CONFIG = {5: HFS_5ISO_XML_CONFIG,
                          4: HFS_4ISO_XML_CONFIG,
                          3: HFS_3ISO_XML_CONFIG,
                          2: HFS_2ISO_XML_CONFIG,
                          1: HFS_1ISO_XML_CONFIG}
        FFS_XML_CONFIG = {5: FFS_5ISO_XML_CONFIG,
                          4: FFS_4ISO_XML_CONFIG,
                          3: FFS_3ISO_XML_CONFIG,
                          2: FFS_2ISO_XML_CONFIG,
                          1: FFS_1ISO_XML_CONFIG}
        if patient_position == 'HFS':
            return HFS_XML_CONFIG[n_pts]
        else:
            return FFS_XML_CONFIG[n_pts]

    def create_dict(pois, beamset_names,
                    site, order_target_name, target, name_offset=0):
        """
            Creates a dictionary of plan parameters.

            Args:
                pois (list): List of Points of Interest.
                beamset_names (list): List of beamset names.
                site (str): Site name, either 'HFS_' or 'FFS_'.
                order_target_name (str): Name of the target for order.
                target (str): Target name.
                name_offset (int, optional): Offset value. Defaults to 0.

            Returns:
                list: List of dictionaries, each representing a plan.
        """
        dictionary = []
        prior_beamset_name = ""
        for i, n in enumerate(beamset_names):
            # Provide a range of potential number of beamsets. Max is 10
            j_range = range(1, 10, 1)
            # Based on its position in the POI list set the TPO for goals/objectives, and assign a beamset
            # template
            # USing the XML templates defined aboue determine the correct template based on the
            # number of pois and the length of the keys
            n_pts = len(pois)
            if site == "HFS_":
                target_poi = pois[len(pois) - 1 - i]
                xml_config = get_xml_config('HFS', n_pts)
                order_name = xml_config[i][0]
                template = xml_config[i][1]
                logging.debug(f'Order name is {order_name} and template is {template}')
                translation_map = create_translation_map(
                    len(pois) - 1 - i, len(pois), j_range, site, rx, name_offset)
                exam_name = "HFS"
            else:
                target_poi = pois[i]
                xml_config = get_xml_config('FFS', n_pts)
                order_name = xml_config[i][0]
                template = xml_config[i][1]
                logging.debug(f'Order name is {order_name} and template is {template}')
                translation_map = create_translation_map(i, len(pois), j_range, site, rx, name_offset)
                exam_name = "FFS"
            optimization_instructions = create_optimization_instructions(i, pois, site,
                                                                         prior_beamset_name)
            dictionary.append({
                'protocol_name': PROTOCOL_NAME_VMAT,
                'translation_map': {order_target_name: (target, rx, r'cGy'), **translation_map},
                'order_name': order_name,
                'exam': exam_name,
                'planning_strategy': 'Sequential',
                'optimization_instructions': optimization_instructions,
                'num_fx': nfx,
                'site': site,
                'plan_name': HFS_VMAT_PLAN_NAME if site == 'HFS_' else FFS_VMAT_PLAN_NAME,
                'beamset_name': HFS_VMAT_BEAMSET_NAME if site == 'HFS_' else FFS_VMAT_BEAMSET_NAME,
                'machine': VMAT_MACHINE,
                'beamset_template': template,
                'beamset_exists_skip': all(beamset_complete(rso, n)),
                'multi_isocenter': True,
                'iso': {'type': 'POI', 'target': target_poi},
                'optimize': optimize,
                'user_prompts': False,
            })
            prior_beamset_name = n
        return dictionary

    hfs_dict = create_dict(pois=hfs_pois,
                           beamset_names=hfs_beamset_names,
                           site='HFS_',
                           order_target_name=ORDER_TARGET_NAME_HFS,
                           target=TARGET_HFS)
    ffs_dict = create_dict(pois=ffs_pois,
                           beamset_names=ffs_beamset_names,
                           site='FFS_',
                           order_target_name=ORDER_TARGET_NAME_FFS,
                           target=TARGET_FFS,
                           name_offset=len(hfs_pois))

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


def copy_roi(pdata, roi_name):
    copy_roi_name = pdata.case.PatientModel.GetUniqueRoiName(DesiredName=f'{roi_name}_copy')
    _ = create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=copy_roi_name,
    )
    roi_defs = get_boolean_defs(
        roi_name=copy_roi_name,
        a_sources=[roi_name],
        a_operation="Intersection",
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **roi_defs)
    # Update derived status and delete derivation
    update_all_remove_expression(pdata, roi_name=copy_roi_name)

    return copy_roi_name


def subtract_b_from_a(pdata, a_list, b_list, result_name):
    # Check for circular references
    if result_name in a_list:
        copy_result_name = copy_roi(pdata, result_name)
        # Modify the a_list to use the copied roi
        a_list[a_list.index(result_name)] = copy_result_name
    else:
        copy_result_name = None

    roi_defs = get_boolean_defs(
        roi_name=result_name,
        a_sources=a_list,
        a_operation="Intersection",
        b_sources=b_list,
        b_operation="Union",
        r_exp=[0.00] * 6,
        r_margin_type="Expand",
        result="Subtraction",
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case,
        examination=pdata.exam, **roi_defs)
    try:
        pdata.case.PatientModel.RegionsOfInterest[result_name].UpdateDerivedGeometry(
            Examination=pdata.case.Examinations[pdata.exam.OnExamination.Name],
            Algorithm="Auto"
        )
    except Exception as err:
        logging.debug(f'Error in updating geometry for {result_name}: {err}')

    if copy_result_name:
        pdata.case.PatientModel.RegionsOfInterest[copy_result_name].DeleteRoi()

    return result_name


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
    wadlow = 272  # 272 cm is the maximum height of a human but in RS 2024a is the maximum

    # Placeholder for ROIs to be deleted
    delete_list = []

    # Create a bounding box larger than possible body size
    big_box = make_box(destination, box_name='big_box', length=wadlow)
    delete_list.append(big_box)

    # Create a bounding box as large as the external examination
    box_name = make_box(destination, box_name=f'fov_box')
    delete_list.append(box_name)

    # Subtract smaller box from the large one
    # Switch to boolean subtraction
    subtraction_box_name = destination.case.PatientModel.GetUniqueRoiName(DesiredName='SubtractionBox')

    subtraction_box_name = subtract_b_from_a(
        pdata=destination,
        a_list=[big_box],
        b_list=[box_name],
        result_name=subtraction_box_name,
    )
    delete_list.append(subtraction_box_name)

    # Transform ROIs according to the determined direction
    transform_object(source, destination, rois=rois)

    # Subtract any regions outside of the destination set from the ROIs
    for roi in rois:
        subtraction_box_name = subtract_b_from_a(
            pdata=destination,
            a_list=[roi],
            b_list=[subtraction_box_name],
            result_name=roi,
        )

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
    # Check patient height
    patient_height = estimate_patient_height(pd_hfs, pd_ffs, external_roi_name="ExternalClean")
    # If the patient height * 0.6 is less than max treatment length, then use 0.6 * patient height
    # use an alternative method to set the junction point
    if patient_height * 0.6 < FFS_MAX_TREATMENT_LENGTH:
        ffs_treatment_length = int(patient_height * 0.6)
        logging.info(f'Patient height is {patient_height} cm, '
                     f'using 60% of patient height as treatment length: {ffs_treatment_length} cm')
        central_junction_start = find_hfff_junction_coords(pd_ffs,
                                                           max_treatment_length=ffs_treatment_length)
        place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=central_junction_start)
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


# Dose Transfer Functions
def get_available_evaluation_doses(case):
    evaluation_doses = []
    fraction_evaluations = [f for f in case.TreatmentDelivery.FractionEvaluations]
    for f in fraction_evaluations:
        for dose_exam in f.DoseOnExaminations:
            if len(dose_exam.DoseEvaluations) > 1:
                raise RuntimeError(f'More than one dose evaluation found for {dose_exam.OnExamination.Name}')
            dose_eval = dose_exam.DoseEvaluations[0]
            eval_dose = {'Origin Beamset': dose_eval.ForBeamSet.DicomPlanLabel,
                         'Destination Exam': dose_exam.OnExamination.Name,
                         'Destination Patient Position': dose_exam.OnExamination.PatientPosition,
                         'DICOM UID': dose_eval.ModificationInfo.DicomUID,
                         'Versioning Status': dose_eval.VersioningStatus.IsVersionSameAsCurrent,
                         'Dose Evaluation': dose_eval}
            evaluation_doses.append(eval_dose)
    return evaluation_doses


def get_evaluation_dose_values(origin_beamset, destination_exam, destination_patient_position, evaluation_doses):
    for de in evaluation_doses:
        if de['Origin Beamset'] == origin_beamset and \
                de['Destination Exam'] == destination_exam and \
                de['Destination Patient Position'] == destination_patient_position:
            return de['Dose Evaluation'].DoseValues.DoseData
    return None


def check_dose_grid(origin_beamset, destination_beamset):
    origin_dose_grid = origin_beamset.FractionDose.InDoseGrid
    destination_dose_grid = destination_beamset.FractionDose.InDoseGrid
    return all([
        destination_dose_grid.Corner == origin_dose_grid.Corner,
        destination_dose_grid.NrVoxels == origin_dose_grid.NrVoxels,
        destination_dose_grid.VoxelSize == origin_dose_grid.VoxelSize
    ])


# Make a new plan and FFS transfer
def rename_hfs_preplan(case, input_plan_name, input_beamset_name, output_plan_name, output_beamset_name):
    # Check if the plan already exists
    for p in case.TreatmentPlans:
        if p.Name == input_plan_name:
            p.Name = output_plan_name
            break
    if not p:
        return None
    # Check if the beamset already exists
    for bs in p.BeamSets:
        if bs.DicomPlanLabel == input_beamset_name:
            bs.DicomPlanLabel = output_beamset_name
    # Verify the
    return case.TreatmentPlans[output_plan_name]


def dose_calc_gui(case, plans, beamsets):
    Sg.ChangeLookAndFeel('DarkPurple4')
    layout = [[Sg.Text("FFS Plan")],
              [Sg.Combo(plans, key="-FFS PLAN-",
                        default_value=plans[0],
                        size=(40, 1),
                        enable_events=True)],
              [Sg.Text("FFS Beamset")],
              [Sg.Combo(beamsets, key="-FFS BEAMSET-",
                        default_value=beamsets[0],
                        size=(40, 1),
                        enable_events=True)],
              [Sg.B('OK'), Sg.B('Cancel')]]
    window = Sg.Window("BEAMSET ASSIGNMENT",
                       layout)
    while True:
        event, values = window.read()
        if event == Sg.WIN_CLOSED or event == "Cancel":
            selections = None
            break
        elif event == "-FFS PLAN-":
            # Update beamset combo based on selected plan
            selected_plan_name = values['-FFS PLAN-']
            selected_plan = next((tp for tp in case.TreatmentPlans if tp.Name == selected_plan_name), None)
            logging.debug(f'Selected Plan: {selected_plan.Name}')
            if selected_plan:
                beamsets = [bs.DicomPlanLabel for bs in selected_plan.BeamSets]
                window['-FFS BEAMSET-'].update(values=beamsets, value=beamsets[0] if beamsets else '')
            else:
                window['-FFS BEAMSET-'].update(values=[], value='')
        elif event == "OK":
            selections = values
            break
    window.close()
    if selections == {}:
        sys.exit('Selection Script was cancelled')
    ffs_plan = None
    ffs_beamset = None

    for tp in case.TreatmentPlans:
        if tp.Name == selections['-FFS PLAN-']:
            ffs_plan = tp
            for bs in tp.BeamSets:
                if bs.DicomPlanLabel == selections['-FFS BEAMSET-']:
                    ffs_beamset = bs
                    break
    if not all([ffs_beamset, ffs_plan]):
        sys.exit('No FFS Beamsets defined')
    else:
        return ffs_plan, ffs_beamset


def make_structures(pd_hfs, pd_ffs,
                    make_vmat_plan, make_tomo_plan, kidney_sparing, testing=False):
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
        pd_hfs, pd_ffs, kidney_sparing=kidney_sparing)


def make_vmat_planning_structures(pd_hfs, pd_ffs, nfx, rx, make_otvs=True, make_junctions=True):
    #
    # HFS
    # Add points for isocenters in VMAT
    hfs_poi_junction = pd_hfs.case.PatientModel \
        .StructureSets[pd_hfs.exam.Name].PoiGeometries[JUNCTION_POINT]
    hfs_junction_width = place_hfs_vmat_pois(pd_hfs, hfs_poi_junction)
    hfs_pois = find_pois(pd_hfs)
    if make_junctions:
        # Add the midfield junctions
        make_midfield_junctions(pd_hfs, hfs_pois, junction_width=hfs_junction_width)
    if make_otvs:
        # Iterate over POIs and create OTVs
        for index, point in enumerate(hfs_pois):
            make_otv(pd_hfs, point, index, hfs_junction_width, hfs_pois)

    # Do the same for FFS
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    ffs_junction_width = place_ffs_vmat_pois(
        pd_ffs, ffs_poi_junction, len(hfs_pois))
    ffs_pois = find_pois(pd_ffs)
    if make_junctions:
        make_midfield_junctions(pd_ffs, ffs_pois, junction_width=ffs_junction_width)
    if make_otvs:
        for index, point in enumerate(ffs_pois):
            make_otv(pd_ffs, point, index, ffs_junction_width, ffs_pois)

    hfs_multiplan, ffs_multiplan = get_vmat_plan_defs(
        pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx, )
    return hfs_multiplan, ffs_multiplan


def tbi_gui():
    """
    Displays a GUI for TBI planning parameter selection. The user can choose
    between a Tomo or VMAT plan and specify relevant parameters.

    Returns:
        dict: A dictionary containing the user's selections.
    """

    def make_toggle_button(text, key, disabled=False):
        return Sg.Button(text, key=key, button_color=('black', 'lightgray'), enable_events=True, disabled=disabled)

    def show_completion_popup(popup_task_name):
        """Display a popup with a specific style that does not affect the rest of the application.

        Args:
            popup_task_name (str): The name of the completed task.
        """
        # Define the specific colors for this popup
        popup_bg_color = "#F0F8FF"  # AliceBlue
        popup_text_color = "green"
        popup_button_color = ("white", "green")

        # Define the layout with element-specific styling
        popup_layout = [
            [Sg.Text(f"{popup_task_name} is complete! 😊",
                     font=("Helvetica", 20),
                     justification="center",
                     background_color=popup_bg_color,
                     text_color=popup_text_color)],
            [Sg.Button("OK",
                       font=("Helvetica", 16),
                       button_color=popup_button_color)]
        ]

        # Create the window with the desired background color
        popup_window = Sg.Window("Success", popup_layout, element_justification="center",
                                 background_color=popup_bg_color, finalize=True)
        while True:
            popup_event, _ = popup_window.read()
            if popup_event in (Sg.WIN_CLOSED, "OK"):
                break
        popup_window.close()

    def fetch_current_dose_and_fractions():
        """Fetches the current number of fractions and total dose.

        Returns:
            tuple: A tuple containing (fractions, dose) or (None, None) if unavailable.
        """
        try:
            # Logic to retrieve dose and fractions from the system (mocked here)
            beamset = GeneralOperations.find_scope(level='BeamSet')
            n_fractions = beamset.FractionationPattern.NumberOfFractions
            rx_dose = beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue
            return int(n_fractions), int(rx_dose)
        except Exception as error_message:
            logging.error(f"Error fetching current dose and fractions: {error_message}")
            return None, None

    # Fetch pre-populated values for fractions and dose
    fractions, dose = fetch_current_dose_and_fractions()

    # Define the GUI layout
    gui_layout = [
        [Sg.Text('Enter Number of Fractions'), Sg.Input(default_text=fractions or '', key='-NFX-')],
        [Sg.Text('Enter TOTAL Dose in cGy'), Sg.Input(default_text=dose or '', key='-TOTAL DOSE-')],
        [Sg.Radio(
            'Generate Tomo Plan', "RADIO1", default=False, key='-TOMO-',
            tooltip='Choose only one, but choose wisely', enable_events=True),
            Sg.Radio(
                'Generate VMAT Plan', "RADIO1", default=False, key='-VMAT-',
                tooltip='There can be only one.', enable_events=True)],
        [Sg.Radio(
            'Do Kidney sparing', "RADIO2", default=False, key='-KIDNEY-',
            tooltip='Kidneys to be spared and excluded from coverage', enable_events=True),
            Sg.Radio(
                'No kidney sparing', "RADIO2", default=False, key='-NO KIDNEY-',
                tooltip='No need for Kidney sparing', enable_events=True)],
        [make_toggle_button('Pause Script', '-PAUSE-')],
        [Sg.Column([
            [Sg.Frame("FFS Planning", [
                [make_toggle_button('Generate Structures', '-FFS STRUCTURES-')],
                [make_toggle_button('Make FFS Plan', '-FFS PLAN-')],
                [make_toggle_button('Optimize FFS Plan', '-OPT FFS-')]
            ])]
        ]),
            Sg.Column([
                [Sg.Frame("HFS Planning", [
                    [make_toggle_button('Calculate FFS Plan on HFS Image', '-CALC FFS ON HFS-')],
                    [make_toggle_button('Export Background Dose', '-EXPORT FFS-')],
                    [make_toggle_button('Make HFS Plan', '-HFS PLAN-')],
                    [make_toggle_button('Optimize HFS Plan', '-OPT HFS-')]
                ])]
            ]),
            Sg.Column([
                [Sg.Frame("Post-Planning", [
                    [make_toggle_button('Copy Plans (Placeholder)', '-COPY PLANS-', disabled=True)],
                    [make_toggle_button('Separate Beamsets (Placeholder)', '-SEPARATE BEAMSETS-', disabled=True)],
                    [make_toggle_button('Placeholder', '-PLACEHOLDER-', disabled=True)]
                ])]
            ])
        ],
        [Sg.Button('OK'), Sg.Button('Cancel')]
    ]

    # Initialize the window
    window = Sg.Window('AUTO TBI SELECTIONS', gui_layout, grab_anywhere=False, location=(100, 100))
    selections = {}

    while True:
        event, values = window.read()
        if event == Sg.WINDOW_CLOSED or event == "Cancel":
            selections = {}
            break
        elif event == "OK":
            selections.update(values)
            break
        elif event == '-PAUSE-':
            connect.await_user_input('Script paused. Resume script to continue.')
            window[event].update(button_color=('black', 'lightgray'))
        elif event in ['-FFS STRUCTURES-', '-FFS PLAN-', '-OPT FFS-', '-HFS PLAN-', '-CALC FFS ON HFS-',
                       '-EXPORT FFS-', '-OPT HFS-']:
            # Check if total fractions, total dose, and plan type are selected
            if not values['-NFX-'] or not values['-TOTAL DOSE-'] or not (
                    values.get('-TOMO-') or values.get('-VMAT-')) or not (
                    values.get('-KIDNEY-') or values.get('-NO KIDNEY-')):
                Sg.popup_error(
                    'Please enter Number of Fractions, Total Dose, '
                    'select Plan Type (Tomo or VMAT) and kidney sparing before proceeding.')
            else:
                task_name = ''
                # Set the button color to indicate it is running
                window[event].update(button_color=('white', 'blue'))
                window.refresh()
                # Call the associated function with actual logic
                try:
                    if event == '-FFS STRUCTURES-':
                        generate_planning_structures(values)
                        task_name = 'Planning Structure Generation'
                    elif event == '-FFS PLAN-':
                        make_ffs_plan(values)
                        task_name = 'FFS Plan Creation'
                    elif event == '-OPT FFS-':
                        optimize_plan(values, plan_orientation='FFS')
                        task_name = 'FFS Plan Optimization'
                    elif event == '-CALC FFS ON HFS-':
                        calculate_ffs_on_hfs_image(values)
                        task_name = 'FFS Plan Calculation on HFS Image'
                    elif event == '-EXPORT FFS-':
                        export_background_dose(values)
                        task_name = 'Background Dose Export'
                    elif event == '-HFS PLAN-':
                        make_hfs_plan(values)
                        task_name = 'HFS Plan Creation'
                    elif event == '-OPT HFS-':
                        optimize_plan(values, plan_orientation='HFS')
                        task_name = 'HFS Plan Optimization'
                except Exception as e:
                    if DEBUG:
                        traceback.print_exc()
                        logging.error("An error occurred: %s\nTraceback:\n%s", e, traceback.format_exc())
                        Sg.popup_error(f"An error occurred: {e}\n\n {traceback.format_exc()}.")
                    else:
                        Sg.popup_error(f"An error occurred: {e}")
                # Reset the button color
                finally:
                    if task_name:
                        show_completion_popup(task_name)
                    window[event].update(button_color=('black', 'lightgray'))
        else:
            # Other events
            pass

    window.close()

    if not selections:
        raise RuntimeError('TBI Script was cancelled')
    if selections.get('-TOMO-', False):
        selections['-MACHINE-'] = "HDA0488"
        selections['-THI-'] = True
    elif selections.get('-VMAT-', False):
        selections['-MACHINE-'] = "TrueBeam_NoTrack"
        selections['-THI-'] = False

    return selections


def generate_planning_structures(values):
    # Extract necessary variables from values
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']
    kidney_sparing = values['-KIDNEY-']
    make_junctions = False

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    # Rename the HFS/FFS Exams
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)

    # Initialize patient data
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam)

    # Check prerequisites
    check_prerequisites(pd_ffs, pd_hfs, '-FFS STRUCTURES-', make_vmat_plan, otv_junctions=False)

    # Build the central junctions and lung contours
    make_structures(pd_hfs, pd_ffs, make_vmat_plan, make_tomo_plan, testing=False,
                    kidney_sparing=kidney_sparing)
    if make_vmat_plan:
        hfs_multiplan, ffs_multiplan = make_vmat_planning_structures(
            pd_hfs, pd_ffs, nfx, rx, make_otvs=False, make_junctions=make_junctions)
    toggle_ptv_type(pd_ffs,
                    rois=HFS_TARGET_NAMES,
                    roi_type='Ptv')
    toggle_ptv_type(pd_ffs,
                    rois=FFS_TARGET_NAMES,
                    roi_type='Ptv')


def make_ffs_plan(values):
    # Implement the logic to make FFS plan
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    # Rename the HFS/FFS Exams
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)

    # Initialize patient data
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)

    # Check prerequisites
    check_prerequisites(pd_ffs, pd_hfs, '-FFS PLAN-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)

    toggle_ptv_type(pd_ffs,
                    rois=FFS_TARGET_NAMES,
                    roi_type='Ptv')
    toggle_ptv_type(pd_ffs,
                    rois=HFS_TARGET_NAMES,
                    roi_type='Undefined')
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)

    if make_vmat_plan:
        # Compute the locations of the isocenters in the VMAT FFS Location
        hfs_pois = find_pois(pd_hfs)
        ffs_pois = find_pois(pd_ffs)
        # Load each treating beamset and the objectives of the VMAT autoplan
        hfs_multiplan, ffs_multiplan = get_vmat_plan_defs(
            pd_ffs, hfs_pois, ffs_pois, nfx=nfx, rx=rx, )
        pd_ffs_out = multi_autoplan(ffs_multiplan)
    if make_tomo_plan:
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        tbi_ffs_protocol = get_tomo_plan_defs(pd_ffs, JUNCTION_PREFIX_FFS + "10%Rx",
                                              nfx, rx, optimize=False, )
        pd_ffs_out = multi_autoplan([tbi_ffs_protocol])
    toggle_ptv_type(pd_ffs,
                    rois=HFS_TARGET_NAMES,
                    roi_type='Ptv')


def optimize_plan(values, plan_orientation):
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    # Rename the HFS/FFS Exams
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)

    # Initialize patient data
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)

    if plan_orientation == 'FFS':
        check_prerequisites(pd_ffs, pd_hfs, '-FFS PLAN-', make_vmat_plan,
                            n_fx=nfx, rx=rx, otv_junctions=False)
        optimization_rso = pd_ffs
        unused_rso = pd_hfs
        unused_target_names = HFS_TARGET_NAMES
    else:
        check_prerequisites(pd_ffs, pd_hfs, '-HFS PLAN-', make_vmat_plan,
                            n_fx=nfx, rx=rx, otv_junctions=False)
        optimization_rso = pd_hfs
        unused_target_names = FFS_TARGET_NAMES
        unused_rso = pd_ffs

    toggle_ptv_type(optimization_rso,
                    rois=unused_target_names,
                    roi_type='Undefined')
    reset_primary_secondary(optimization_rso.exam, unused_rso.exam)

    if make_vmat_plan:
        technique = 'VMAT'
        protocol_file = PROTOCOL_FILE_VMAT
        if plan_orientation == 'FFS':
            plan_name = FFS_VMAT_PLAN_NAME
            beamset_name = FFS_VMAT_BEAMSET_NAME
        else:
            plan_name = HFS_VMAT_PLAN_NAME
            beamset_name = HFS_VMAT_BEAMSET_NAME
    elif make_tomo_plan:
        technique = "TomoHelical"
        protocol_file = PROTOCOL_FILE_TOMO
        if plan_orientation == 'FFS':
            beamset_name = FFS_TOMO_BEAMSET_NAME
            plan_name = FFS_TOMO_PLAN_NAME
        else:
            beamset_name = HFS_TOMO_BEAMSET_NAME
            plan_name = HFS_TOMO_PLAN_NAME
    else:
        raise RuntimeError('Unsupported Plan Type during optimization aborted')
    optimization_rso = update_plan_and_beamset(optimization_rso,
                                               beamset_name=beamset_name,
                                               plan_name=plan_name)
    opt_status = AutoPlanOperations.load_configuration_optimize_beamset(
        filename=protocol_file,
        path=PATH_PROTOCOLS,
        rso=optimization_rso,
        technique=technique,
        output_data_dir=PATH_TO_OUTPUT,
        bypass_user_prompts=True,
        optimize=True)
    toggle_ptv_type(optimization_rso,
                    rois=unused_target_names,
                    roi_type='Ptv')


def make_hfs_plan(values):
    """
    Function to make the HFS plan based on the user's selections
    Args:
        values (dict): Dictionary containing the user's selections

    Returns:

    """
    # Implement the logic to make HFS plan
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']
    kidney_sparing = values['-KIDNEY-']

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)
    # Check prerequisites
    check_prerequisites(pd_ffs, pd_hfs, '-HFS PLAN-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)

    toggle_ptv_type(pd_hfs,
                    rois=HFS_TARGET_NAMES,
                    roi_type='Ptv')
    # Temporarily set the type of the FFS targets to undefined
    toggle_ptv_type(pd_hfs,
                    rois=FFS_TARGET_NAMES,
                    roi_type='Undefined')
    reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
    error_message = ''
    output_plan_name = HFS_TOMO_PLAN_NAME if make_tomo_plan else HFS_VMAT_PLAN_NAME
    output_beamset_name = TOMO_FFS_TRANSFER_NAME if make_tomo_plan else VMAT_FFS_TRANSFER_NAME
    hfs_plan = rename_hfs_preplan(pd_hfs.case,
                                  input_plan_name=FFS_PLACEHOLDER_NAME,
                                  input_beamset_name=FFS_PLACEHOLDER_NAME,
                                  output_plan_name=output_plan_name,
                                  output_beamset_name=output_beamset_name)
    if hfs_plan is None:
        raise RuntimeError(f'Could not find HFS Plan: {FFS_PLACEHOLDER_NAME}, rerun export')
    pd_hfs = update_plan_and_beamset(pd_hfs, output_beamset_name, plan_name=output_plan_name)
    set_current_plan_beamset(pd_hfs)
    # Do some polishing
    # Change the Rx in the FFS transfer plan
    # Change the comment
    pd_hfs.plan.Comments = "HFS Plan using FFS Dose as background"
    pd_hfs.plan.PlannedBy = "H.A.L."
    #
    beamset_fractions = pd_hfs.beamset.FractionationPattern.NumberOfFractions
    while beamset_fractions != nfx:
        connect.await_user_input(f'Set the number of fractions in {output_beamset_name}')
        beamset_fractions = pd_hfs.beamset.FractionationPattern.NumberOfFractions
    is_clinical_dose = pd_hfs.beamset.IsApprovedToUseAsBackgroundDose()
    while not is_clinical_dose:
        connect.await_user_input(f'Edit the plan {output_beamset_name}: '
                                 f'select "Consider imported dose clinical"')
        is_clinical_dose = pd_hfs.beamset.IsApprovedToUseAsBackgroundDose()

    if make_tomo_plan:
        tbi_hfs_protocol = get_tomo_plan_defs(pd_hfs, TARGET_HFS, nfx, rx,
                                              optimize=False, kidney_sparing=kidney_sparing)
        hfs_multiplan = [tbi_hfs_protocol]

    else:
        # and that an FFS plan is present.
        hfs_pois = find_pois(pd_hfs)
        ffs_pois = find_pois(pd_ffs)
        hfs_multiplan, ffs_multiplan = get_vmat_plan_defs(pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx,
                                                          kidney_sparing=kidney_sparing)
    try:
        tbi_hfs_protocol = multi_autoplan(hfs_multiplan)
    except Exception as e:
        error_message = f'Error in multi_autoplan: {e}'

    toggle_ptv_type(pd_hfs,
                    rois=FFS_TARGET_NAMES,
                    roi_type='Ptv')
    if error_message:
        raise RuntimeError(error_message)


def calculate_ffs_on_hfs_image(values):
    # Extract necessary variables from values
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)
    check_prerequisites(pd_ffs, pd_hfs, '-CALC FFS PLAN ON HFS-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)

    # Update the current variables if needed.
    if not pd_ffs.beamset:
        # Function to allow user to select plans and beamsets for dose summation
        case = pd_ffs.case
        plans = [p.Name for p in case.TreatmentPlans]
        beamsets = [bs.DicomPlanLabel for p in case.TreatmentPlans for bs in p.BeamSets]

        # Assume GUI function dose_summation_gui returns selected plans and beamsets
        ffs_plan, ffs_beamset = dose_calc_gui(case, plans, beamsets)

        pd_ffs = pd_ffs._replace(plan=ffs_plan, beamset=ffs_beamset)

    grid_updated = rescale_dose_grid_to_all_scans(pd_ffs)
    # Recompute selected doses on adjusted dose grid
    try:
        if grid_updated:
            pd_ffs.beamset.ComputeDose(ComputeBeamDoses=False, DoseAlgorithm='CCDose',
                                       ForceRecompute=False)
            pd_ffs.patient.Save()
    except Exception as e:
        logging.debug(f'During dose summation, '
                      f'dose computation failed for {pd_ffs.beamset.DicomPlanLabel}: {e}')
        pass
    # Compute the dose on the HFS image
    pd_ffs.beamset.ComputeDoseOnAdditionalSets(
        OnlyOneDosePerImageSet=True,
        AllowGridExpansion=True,
        ExaminationNames=[hfs_scan_name],
        FractionNumbers=[0],
        ComputeBeamDoses=True)
    # Perform a patient save, required for modification info in
    # TreatmentDelivery.FractionEvaluations.DoseOnExaminations.DoseEvaluations.ModificationInfo to be populated
    pd_ffs.patient.Save()


def export_background_dose(values):
    def convert_net_to_datetime(net_time):
        # Convert to datetime from NET
        return datetime.datetime(
            net_time.Year,
            net_time.Month,
            net_time.Day,
            net_time.Hour,
            net_time.Minute,
            net_time.Second,
        )

    def find_patient_directory(repo_path, patient_id, expected_date):
        """
        Search a given path for a directory name containing a specific patient_id.

        Args:
            repo_path (str): The base path to search in.
            patient_id (str): The patient ID to look for.
            expected_date (str): The modification date for the dose file

        Returns:
            str: The full path to the directory if found, or None if not found.
        """
        # Walk through the directory tree
        for root, dirs, _ in os.walk(repo_path):
            for directory in dirs:
                if patient_id in directory and expected_date in directory:
                    return os.path.join(root, directory)
        return None

    def check_datetime_match(dose_datetime: datetime, s: dict) -> bool:
        """Return True if `dose_datetime` (e.g. '2/5/2025 10:43:25 AM') matches
        the dictionary s={'SeriesDate':'YYYYMMDD','SeriesTime':'HHMMSS'}
        *except* the 'SS' in SeriesTime are not real seconds. We only compare
        up through Year/Month/Day and Hour/Minute (ignoring actual seconds).

        """
        # Extract year, month, day from 'SeriesDate' => 'YYYYMMDD'
        try:
            year = int(s['SeriesDate'][0:4])
            month = int(s['SeriesDate'][4:6])
            day = int(s['SeriesDate'][6:8])
        except (ValueError, KeyError, IndexError):
            return False
        # Extract hour, minute from 'SeriesTime' => 'HHMMSS' but 'SS' are just chars
        # So we only parse HH and MM
        try:
            hour = int(s['SeriesTime'][0:2])  # e.g. '10'
            minute = int(s['SeriesTime'][2:4])  # e.g. '43'
        except (ValueError, KeyError, IndexError):
            return False

        # Build a datetime from SeriesDate + SeriesTime, ignoring "SS"
        series_datetime = datetime.datetime(year, month, day, hour, minute, 0)

        # Nullify seconds/microseconds in parsed_datetime
        parsed_datetime_no_sec = dose_datetime.replace(second=0, microsecond=0)
        return parsed_datetime_no_sec == series_datetime

    def get_series_to_import(pd, ffs_dose, ffs_eval, patient_data_path):
        # Get parameters prior to export
        dicom_elements_dict = {
            'study_instance_uid': (0x0020, 0x00d),
            # 'series_instance_uid': (0x0020, 0x00e), 'sop_instance_uid': (0x0008, 0x0018),
            'patient_id': (0x0010, 0x0020), }
        # Build arguments to import function
        series_or_instances = get_dicom_entries(dicom_elements_dict, ffs_dose.OnExamination)
        # Query patients from path by patient ID to obtain full series data
        matching_patients = pd.db.QueryPatientsFromPath(Path=patient_data_path,
                                                        SearchCriterias={'PatientID': pd.patient.PatientID})
        if not matching_patients:
            raise RuntimeError(f'Patient not found in {patient_data_path}, export not performed')
        elif len(matching_patients) > 1:
            raise RuntimeError(f'Multiple patients found in {patient_data_path}, export not performed')
        else:
            matching_patient = matching_patients[0]
        # Query all the studies of the matching patient
        studies = pd.db.QueryStudiesFromPath(Path=patient_data_path, SearchCriterias=matching_patient)
        # Query all the series from all the matching studies
        series = []
        for study in studies:
            series += pd.db.QuerySeriesFromPath(Path=patient_data_path, SearchCriterias=study)
        # Filter queried series to only contain the series of the current patient
        # Get time in format M/D/YYYY H:MM:SS AM/PM
        modification_time = ffs_eval.ModificationInfo.ModificationTime
        modification_datetime = convert_net_to_datetime(modification_time)

        matching_series = []
        for entry in series:
            # Evaluate each condition separately so we can see which fails
            sid_match = (entry['StudyInstanceUID'] == series_or_instances['StudyInstanceUID'])
            no_beam = ("Beam" not in entry['SeriesDescription'])
            fx_dose = ("Evaluation Fx Dose" in entry['SeriesDescription'])
            date_match = check_datetime_match(modification_datetime, entry)
            is_rtdose = (entry['Modality'] == 'RTDOSE')

            if all([sid_match, no_beam, fx_dose, date_match, is_rtdose]):
                matching_series.append(entry)
            else:
                logging.debug(
                    "Series not matched: SID:%s ->%s, Beam:%s, FxDose:%s, DateMatch:%s, Modality:%s => %s",
                    sid_match, entry['StudyInstanceUID'],
                    no_beam, fx_dose,
                    date_match, is_rtdose,
                    entry
                )
        # Parse the RT DOSE
        return matching_series

    def remove_directory_contents_with_prompt(dir_path: str) -> bool:
        """Prompt user to confirm removal of all files/folders inside `dir_path`.

        If user confirms, recursively deletes everything inside `dir_path`.
        Returns True if removal was confirmed and completed, False otherwise.
        """
        if not os.path.exists(dir_path):
            Sg.popup_error(f"The path {dir_path} does not exist.")
            return False

        layout = [
            [Sg.Text("Multiple exported dose files were located leading to potentially importing the incorrect dose.\n"
                     f"Would you like to remove all contents of:\n{dir_path}?")],
            [Sg.Button("Yes", key="-YES-"), Sg.Button("No", key="-NO-")]
        ]
        window = Sg.Window("Confirm Deletion", layout, modal=True)

        user_choice = None
        while True:
            event, _ = window.read()
            if event in (Sg.WIN_CLOSED, "-NO-"):
                user_choice = False
                break
            elif event == "-YES-":
                user_choice = True
                break
        window.close()
        if user_choice:
            # Remove everything inside dir_path, but keep dir_path itself
            for item_name in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item_name)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            Sg.popup("Contents removed successfully.")
            return True
        else:
            Sg.popup("Deletion canceled.")
            return False

    # Implement the logic to make HFS plan
    nfx = int(values['-NFX-'])
    rx = int(values['-TOTAL DOSE-'])
    make_vmat_plan = values['-VMAT-']
    make_tomo_plan = values['-TOMO-']
    # Has to be done manually currently
    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)
    # Check prerequisites
    check_prerequisites(pd_ffs, pd_hfs, '-FFS EXPORT-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)
    # Set current to avoid the bug in export
    set_current_plan_beamset(pd_ffs)
    ffs_dose_on_examination, ffs_dose_evaluation = find_dose_evaluation(pd_ffs, pd_hfs)
    if not ffs_dose_on_examination:
        raise RuntimeError(f'No FFS Dose found for {pd_ffs.beamset.DicomPlanLabel} on {pd_hfs.exam.Name}')
    # Grab the uid for later use
    uid = ffs_dose_evaluation.ModificationInfo.DicomUID
    dicom_name = ffs_dose_evaluation.ForBeamSet.DicomPlanLabel
    pt_position = ffs_dose_evaluation.ForBeamSet.PatientPosition
    mod_datetime = ffs_dose_evaluation.ModificationInfo.ModificationTime
    py_datetime = convert_net_to_datetime(mod_datetime)
    # Extract the date from parsed_datetime and convert to YYYYMMDD
    mod_date = py_datetime.strftime("%Y%m%d")
    # Path to the DICOM repository
    patient_path = find_patient_directory(DICOM_PATH, pd_ffs.patient.PatientID, mod_date)

    # Ask the user to export
    connect.await_user_input(f'Export to Target: PACS-RayStation\n '
                             f'Evaluation Fx Dose {FFS_VMAT_PLAN_NAME} (HFS)\n'
                             f'Make sure to deselect beam doses')
    # Check the repo directory for the presence of a patient directory
    if not patient_path:
        raise RuntimeError(f'Patient directory not found in {patient_path}, export not performed')
    series_to_import = get_series_to_import(pd_ffs, ffs_dose_on_examination, ffs_dose_evaluation, patient_path)
    if len(series_to_import) > 1:
        data_cleared = remove_directory_contents_with_prompt(patient_path)
        if data_cleared:
            raise RuntimeError(f'Restart the background dose export')
        else:
            raise RuntimeError(f'Multiple series found in {patient_path}, export not performed: '
                               f'clear the directory and restart the background dose export')
    elif len(series_to_import) == 0:
        raise RuntimeError(f"No dose export found in {patient_path} for {pd_ffs.beamset.DicomPlanLabel}, "
                           "import to 'Empty plan' not performed")
    logging.debug(f'Series to import: {series_to_import}')
    warnings = pd_hfs.patient.ImportDataFromPath(
        Path=patient_path,
        CaseName=pd_hfs.case.CaseName,
        SeriesOrInstances=series_to_import,
    )
    if "A dummy plan has been created for an image set" not in warnings:
        raise RuntimeError(f'Warnings during import: {warnings}')
    # Add the UID to the comments of the dummy plan
    check_empty_plans(pd_ffs, pd_hfs, exists=True, unique=True)
    # Assuming no error was thrown, get the UID of the transferred beamset
    empty_plan = pd_hfs.case.TreatmentPlans[FFS_PLACEHOLDER_NAME]
    empty_beamset = empty_plan.BeamSets[FFS_PLACEHOLDER_NAME]
    empty_beamset.Comment = f'{dicom_name}\n' \
                            f'{pt_position}\n' \
                            f'{mod_datetime}\n' \
                            f'<FFS_UID:{uid}>'
    if plan_transfer_successful(pd_hfs, pd_ffs, nfx):
        connect.await_user_input('Plan transfer successful, resume the script')


def get_dicom_entries(dicom_elements, api_dicom_object):
    """
    Fetches DICOM tag values for the given elements.
    """
    series_or_instances = {}
    for key, (group, element) in dicom_elements.items():
        dicom_entry = api_dicom_object.GetStoredDicomTagValueForVerification(
            Group=group, Element=element
        )
        if dicom_entry:  # Ensure dicom_entry is not None or empty
            series_or_instances.update(
                {"".join(name.split()): identifier for name, identifier in dicom_entry.items()}
            )
    return series_or_instances


def initialize_patient_data(hfs_exam, ffs_exam, vmat=False, tomo=False):
    # Initialize patient data structures
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    case = GeneralOperations.find_scope(level='Case')
    hfs_plan = None
    hfs_beamset = None
    ffs_plan = None
    ffs_beamset = None
    if vmat:
        hfs_plan_name = HFS_VMAT_PLAN_NAME
        hfs_beamset_name = HFS_VMAT_BEAMSET_NAME
        ffs_plan_name = FFS_VMAT_PLAN_NAME
        ffs_beamset_name = FFS_VMAT_BEAMSET_NAME
    if tomo:
        hfs_plan_name = HFS_TOMO_PLAN_NAME
        hfs_beamset_name = HFS_TOMO_BEAMSET_NAME
        ffs_plan_name = FFS_TOMO_PLAN_NAME
        ffs_beamset_name = FFS_TOMO_BEAMSET_NAME
    if tomo or vmat:
        try:
            ffs_plan = case.TreatmentPlans[ffs_plan_name]
            ffs_beamset = ffs_plan.BeamSets[ffs_beamset_name]
        except Exception as e:
            logging.info(f'Could not find FFS plan {ffs_plan_name} in {case.CaseName}: {e}')
        try:
            hfs_plan = case.TreatmentPlans[hfs_plan_name]
            hfs_beamset = hfs_plan.BeamSets[hfs_beamset_name]
        except Exception as e:
            logging.info(f'Could not find HFS plan {hfs_plan_name} in {case.CaseName}: {e}')

    pd_hfs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=hfs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=hfs_plan,
                beamset=hfs_beamset)

    pd_ffs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=ffs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=ffs_plan,
                beamset=ffs_beamset)

    return pd_hfs, pd_ffs


def update_plan_and_beamset(pd, beamset_name, plan_name=None):
    # Update the plan and beamset for the given patient data
    case = pd.case
    if not plan_name:
        plan = [p for p in case.TreatmentPlans if any(bs.DicomPlanLabel == beamset_name for bs in p.BeamSets)]
        plan = plan[0]
        beamset = [bs for bs in plan.BeamSets if bs.DicomPlanLabel == beamset_name][0]
    else:
        plan = [p for p in case.TreatmentPlans if p.Name == plan_name]
        plan = plan[0]
        beamset = [bs for bs in plan.BeamSets if bs.DicomPlanLabel == beamset_name][0]
    if not plan or not beamset:
        raise RuntimeError(f'Plan with beamset {beamset_name} not found')
    pd = pd._replace(plan=plan, beamset=beamset)
    return pd


def set_current_plan_beamset(pd):
    """ Set the current plan and beamset for the given patient data """
    if pd.plan and pd.beamset:
        pd.patient.Save()
        pd.plan.SetCurrent()
        pd.beamset.SetCurrent()


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
    # Disable intermediate VMAT junctions and OTVs
    make_junctions = True
    make_otvs = False
    tbi_selections = tbi_gui()


if __name__ == '__main__':
    main()
