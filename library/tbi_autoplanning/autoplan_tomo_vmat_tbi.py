"""
Automated TBI Planning Workflow Orchestrator (Tomo/VMAT)

This module coordinates the end-to-end workflow for Total Body Irradiation (TBI) treatment planning
using Tomo and VMAT techniques in RayStation. It provides a user-facing GUI, manages scan and data
initialization, validates prerequisites, and delegates detailed structure creation, planning, and dose
management to supporting modules.

Module Role:
------------
- Acts as the main entry point for TBI planning automation.
- Orchestrates the sequence of planning steps, user prompts, and error handling.
- Delegates detailed operations (structure creation, ROI/POI management, plan building, dose transfer)
  to specialized helper modules within `tbi_autoplanning` and `library`.

Main Workflow Steps:
--------------------
1. **User Input**: Launch a GUI to collect planning parameters (fractions, dose, plan type, kidney sparing, etc.).
2. **Scan Identification & Initialization**: Identify HFS/FFS CT scans and initialize patient/case/exam data structures.
3. **Validation**: Check for required scans, contours, POIs, registrations, and other prerequisites for each planning phase.
4. **Structure Generation**: If selected, delegate to helper modules to generate planning structures and supports.
5. **FFS Planning**: If selected, delegate to helper modules to create and optimize FFS plans (Tomo/VMAT).
6. **HFS Planning**: If selected, delegate to helper modules to create and optimize HFS plans, including background dose handling.
7. **Dose Export & Summation**: If selected, export FFS dose to HFS, update dose grids, and combine dose distributions.
8. **Error Handling & User Prompts**: At each step, validate state and prompt the user for corrections as needed.

Key User-Facing Functions:
--------------------------
- `tbi_gui()`: Launches the main GUI for parameter selection and workflow control.
- `main()`: Orchestrates the overall workflow, calling the appropriate step based on user input.
- `generate_planning_structures(values)`: Delegates structure generation to helper modules.
- `make_ffs_plan(values)`, `make_hfs_plan(values)`: Delegate plan creation to helper modules.
- `optimize_plan(values, plan_orientation)`: Delegates plan optimization.
- `calculate_ffs_on_hfs_image(values)`, `export_ffs_dose(values)`, `export_ffs_dose_to_hfs_plan(values)`: Handle dose transfer and export operations.
- Validation helpers: `check_prerequisites`, `check_ffs_structure_prerequisites`, etc.

High-Level Pseudocode:
----------------------

    def main():
        # 1. Launch GUI and get user selections
        selections = tbi_gui()
        # 2. Identify HFS/FFS scans and initialize patient data
        hfs_exam, ffs_exam = rename_exams(case)
        pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam, ...)
        # 3. For each workflow step selected by the user:
        if selections['Generate Structures']:
            check_prerequisites(...)
            generate_planning_structures(selections)
        if selections['Make FFS Plan']:
            check_prerequisites(...)
            make_ffs_plan(selections)
        if selections['Optimize FFS Plan']:
            check_prerequisites(...)
            optimize_plan(selections, plan_orientation='FFS')
        if selections['Calculate FFS Plan on HFS Image']:
            check_prerequisites(...)
            calculate_ffs_on_hfs_image(selections)
        if selections['Export Background Dose']:
            check_prerequisites(...)
            export_ffs_dose(selections)
        if selections['Make HFS Plan']:
            check_prerequisites(...)
            make_hfs_plan(selections)
        if selections['Optimize HFS Plan']:
            check_prerequisites(...)
            optimize_plan(selections, plan_orientation='HFS')
        # 4. At each step, validate state and prompt user for corrections as needed
        # 5. Finalize workflow

Notes:
------
- Detailed structure/ROI/POI creation, plan building, and dose management are implemented in supporting modules.
- This module focuses on workflow control, user interaction, and error handling.
- For more details on helper functions, see the respective modules in `tbi_autoplanning/` and `library/`.
"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '04-Feb-2025'
__version__ = '0.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '2024SP3'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import logging
from library.api.api_rs import import_raystation_api
connect = import_raystation_api()
import os
import traceback

from typing import Optional, Tuple, List, Dict, Any
try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
import re
import library.AutoPlanOperations as AutoPlanOperations
import library.GeneralOperations as GeneralOperations
from general.AutoPlan import multi_autoplan
from .tbi_plan_builders import beamset_complete, get_tomo_plan_defs, get_vmat_plan_defs
from .dose_transfer import plan_transfer_successful, find_dose_evaluation, \
    get_available_evaluation_doses, get_evaluation_dose_values, rename_hfs_preplan, \
    export_background_dose, potential_transfer_plan_names, potential_transfer_beamset_names, check_empty_plans, \
    calculate_ffs_on_hfs_logic
from .poi_operations import find_pois, get_point_position
from .roi_operations import (roi_has_contours, toggle_ptv_type, make_vmat_planning_structures,
                             material_override_overlap, set_all_ptvs_to_ptv_type)
from .poi_operations import poi_in_list

from .tbi_definitions import PATH_PROTOCOLS, PATH_TO_OUTPUT, PROTOCOL_FILE_TOMO, \
    PROTOCOL_FILE_VMAT, HFS_TOMO_PLAN_NAME, HFS_TOMO_BEAMSET_NAME, FFS_TOMO_BEAMSET_NAME, FFS_TOMO_PLAN_NAME, \
    TOMO_FFS_TRANSFER_NAME, \
    FFS_PLACEHOLDER_NAME, HFS_VMAT_BEAMSET_NAME, HFS_VMAT_PLAN_NAME, FFS_VMAT_BEAMSET_NAME, FFS_VMAT_PLAN_NAME, \
    VMAT_FFS_TRANSFER_NAME, JUNCTION_POINT, EXTERNAL_SETUP, AVOID_HFS_NAME, \
    AVOID_FFS_NAME, SKIN_AVOIDANCE, LUNG_AVOID_NAME, LUNGS_EVAL_NAME, KIDNEY_AVOID_NAME, \
    TARGET_FFS, JUNCTION_PREFIX_FFS, JUNCTION_PREFIX_HFS, HFS_TARGET_EVAL_NAME, FFS_TARGET_EVAL_NAME, \
    HFS_TARGET_NAMES, FFS_TARGET_NAMES, TARGET_HFS, DEFAULT_VOXEL_SIZE, NFX_KEY, TOTAL_DOSE_KEY, VMAT_KEY, TOMO_KEY, KIDNEY_KEY, NO_KIDNEY_KEY, PAUSE_KEY, \
    VMAT_HFS_OPTIMIZATION_CONFIG, VMAT_FFS_OPTIMIZATION_CONFIG, TOMO_HFS_OPTIMIZATION_CONFIG, \
    TOMO_FFS_OPTIMIZATION_CONFIG
from .tbi_utils import update_plan_and_beamset, set_current_plan_beamset, \
    reset_primary_secondary, initialize_patient_data, rename_exams, check_registration, Pd

from .roi_operations import make_structures

script_dir = os.path.dirname(os.path.abspath(__file__))
# general_dir = os.path.join(script_dir, '../../../', 'general')
# sys.path.insert(1, general_dir)

DEBUG = True


def hfs_ffs_exam_present(case) -> Tuple[bool, bool]:
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


def check_prerequisites(pd_ffs: 'Pd', pd_hfs: 'Pd', phase: str, vmat: bool, n_fx: Optional[int] = None, rx: Optional[int] = None, otv_junctions: bool = False) -> None:  # type: ignore
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


def check_external(patient_data) -> bool:
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


def check_ffs_structure_prerequisites(pd_ffs: 'Pd', pd_hfs: 'Pd') -> None:  # type: ignore
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


def check_ffs_plan_prerequisites(pd_ffs: 'Pd', pd_hfs: 'Pd', vmat: bool = False, otv_junctions: bool = False) -> None:  # type: ignore
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
    # Check if there is overlap in the material overides
    overlap, roia, roib = material_override_overlap(pd_ffs, pd_hfs)
    if overlap:
        raise RuntimeError(f'Overlapping material overrides found in {roia} and {roib}')
    if vmat:
        # Check if POIs created by place_ffs_vmat_pois and place_hfs_vmat_pois exist
        try:
            pois_ffs = find_pois(pd_ffs)
            pois_hfs = find_pois(pd_hfs)
        except RuntimeError as e:
            raise RuntimeError(f"Required POIs not found. {str(e)}\n"
                            f'Please run the Generate Structures script first.')

        # Check that each poi has a valid position
        for poi in pois_ffs + pois_hfs:
            try:
                _ = get_point_position(pd_ffs if poi in pois_ffs else pd_hfs, poi)
            except RuntimeError as e:
                raise RuntimeError("Missing position data for POI. " + str(e))


def check_contours(patient_data: 'Pd', roi_list: List[str]) -> List[str]:  # type: ignore
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


def check_plan_validity(patient_data: 'Pd', vmat: bool, n_fx: Optional[int], rx: Optional[int]) -> None:  # type: ignore
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
    # Check if dose grid resolution is correct
    dg = beamset.GetDoseGrid()
    if dg.VoxelSize.x != DEFAULT_VOXEL_SIZE['x'] or dg.VoxelSize.y != DEFAULT_VOXEL_SIZE['y'] \
            or dg.VoxelSize.z != DEFAULT_VOXEL_SIZE['z']:
        raise RuntimeError(f'Beamset {beamset.DicomPlanLabel} has incorrect dose grid resolution.'
                           f' Input: {DEFAULT_VOXEL_SIZE} != Plan: {dg.VoxelSize}')


def check_evaluation_dose_transfer(pd_ffs: 'Pd', pd_hfs: 'Pd') -> None:  # type: ignore
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


def check_exported_plan(pd_ffs: 'Pd', pd_hfs: 'Pd') -> None:  # type: ignore
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


def check_midfield_junctions(patient_data: 'Pd', poi_name_list: List[str]) -> List[str]:  # type: ignore
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


def check_dose_grid(origin_beamset, destination_beamset) -> bool:
    origin_dose_grid = origin_beamset.FractionDose.InDoseGrid
    destination_dose_grid = destination_beamset.FractionDose.InDoseGrid
    return all([
        destination_dose_grid.Corner == origin_dose_grid.Corner,
        destination_dose_grid.NrVoxels == origin_dose_grid.NrVoxels,
        destination_dose_grid.VoxelSize == origin_dose_grid.VoxelSize
    ])


def calculate_ffs_on_hfs_image(values) -> 'Pd':  # type: ignore
    """
    Minimal wrapper that orchestrates the logic, but delegates the heavy-lifting
    to 'calculate_ffs_on_hfs_logic' in 'dose_management.py'.
    """
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]

    # Any "rename_exams" or "initialize_patient_data" can stay here:
    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)

    # Possibly do your check_prerequisites here if you want to keep that flow:
    check_prerequisites(pd_ffs, pd_hfs, '-CALC FFS PLAN ON HFS-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)

    # Now just delegate the main logic to 'dose_management.py'
    pd_ffs = calculate_ffs_on_hfs_logic(
        pd_ffs, pd_hfs, nfx, rx, make_vmat_plan, make_tomo_plan
    )
    return pd_ffs


def export_ffs_dose(values) -> None:
    """
    Export the FFS dose to the HFS exam
        -Initialize patient data
        -Check prerequisites
        -Export the FFS dose to the HFS exam
    :param values: values from the GUI
    :return: None
    """
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]

    temp_case = GeneralOperations.find_scope(level='Case')
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam,
                                             vmat=make_vmat_plan, tomo=make_tomo_plan)

    check_prerequisites(pd_ffs, pd_hfs, '-FFS EXPORT-', make_vmat_plan,
                        n_fx=nfx, rx=rx, otv_junctions=False)
    # Perform a patient save
    pd_ffs.patient.Save()

    error = export_background_dose(pd_ffs, pd_hfs)
    if error:
        raise RuntimeError(error)
    else:
        pd_ffs.patient.Save()


def generate_planning_structures(values) -> None:
    """
    Generate the planning structures for TBI
        -Initialize patient data
        -Check prerequisites
        -Make the planning structures
        -Make the planning structures for VMAT and Tomo
    Args:
        values: (dict) values from the GUI
    Returns:
        None
    """
    # Extract necessary variables from values
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]
    kidney_sparing: bool = values[KIDNEY_KEY]
    make_junctions: bool = False

    # Get patient and case
    temp_case = GeneralOperations.find_scope(level='Case')
    # Rename the HFS/FFS Exams
    hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam = rename_exams(temp_case)

    # Initialize patient data
    pd_hfs, pd_ffs = initialize_patient_data(hfs_exam, ffs_exam)

    # Check prerequisites
    check_prerequisites(pd_ffs, pd_hfs, '-FFS STRUCTURES-', make_vmat_plan, otv_junctions=False)

    # Build the central junctions and lung contours
    logging.debug('Building central junctions and lung contours for '
                  f'VMAT: {make_vmat_plan}, Tomo: {make_tomo_plan}')
    make_structures(pd_hfs, pd_ffs, make_vmat_plan, make_tomo_plan, testing=False,
                    kidney_sparing=kidney_sparing)
    if make_vmat_plan:
        hfs_multiplan, ffs_multiplan = make_vmat_planning_structures(
            pd_hfs, pd_ffs, nfx, rx, make_otvs=False, make_junctions=make_junctions)
    set_all_ptvs_to_ptv_type(pd_ffs, pd_hfs)


def make_ffs_plan(values) -> None:
    # Implement the logic to make FFS plan
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]

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


def optimize_plan(values, plan_orientation: str) -> None:
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]

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
            optimization_config = VMAT_FFS_OPTIMIZATION_CONFIG
        else:
            plan_name = HFS_VMAT_PLAN_NAME
            beamset_name = HFS_VMAT_BEAMSET_NAME
            optimization_config = VMAT_HFS_OPTIMIZATION_CONFIG
    elif make_tomo_plan:
        technique = "TomoHelical"
        protocol_file = PROTOCOL_FILE_TOMO
        if plan_orientation == 'FFS':
            beamset_name = FFS_TOMO_BEAMSET_NAME
            plan_name = FFS_TOMO_PLAN_NAME
            optimization_config = TOMO_FFS_OPTIMIZATION_CONFIG
        else:
            beamset_name = HFS_TOMO_BEAMSET_NAME
            plan_name = HFS_TOMO_PLAN_NAME
            optimization_config = TOMO_HFS_OPTIMIZATION_CONFIG
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
        name=optimization_config,
        bypass_user_prompts=True,
        optimize=True)
    toggle_ptv_type(optimization_rso,
                    rois=unused_target_names,
                    roi_type='Ptv')


def make_hfs_plan(values) -> None:
    """
    Function to make the HFS plan based on the user's selections
    Args:
        values (dict): Dictionary containing the user's selections

    Returns:

    """
    # Implement the logic to make HFS plan
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]
    kidney_sparing: bool = values[KIDNEY_KEY]

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
    tbi_hfs_protocol = multi_autoplan(hfs_multiplan)

    toggle_ptv_type(pd_hfs,
                    rois=FFS_TARGET_NAMES,
                    roi_type='Ptv')
    if error_message:
        raise RuntimeError(error_message)


def export_ffs_dose_to_hfs_plan(values) -> None:
    nfx: int = int(values[NFX_KEY])
    rx: int = int(values[TOTAL_DOSE_KEY])
    make_vmat_plan: bool = values[VMAT_KEY]
    make_tomo_plan: bool = values[TOMO_KEY]
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
    # Export the FFS dose to the HFS plan
    export_background_dose(pd_ffs, pd_hfs)
    if plan_transfer_successful(pd_hfs, pd_ffs, nfx):
        connect.await_user_input('Plan transfer successful, resume the script')


def tbi_gui() -> Dict:
    """
    Displays a GUI for TBI planning parameter selection. The user can choose
    between a Tomo or VMAT plan and specify relevant parameters.

    Returns:
        dict: A dictionary containing the user's selections.
    """

    def make_toggle_button(text: str, key: str, disabled: bool = False) -> Sg.Button:
        return Sg.Button(text, key=key, button_color=('black', 'lightgray'), enable_events=True, disabled=disabled)

    def show_completion_popup(popup_task_name: str) -> None:
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

    def fetch_current_dose_and_fractions() -> Tuple[Optional[int], Optional[int]]:
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
        [Sg.Text('Enter Number of Fractions'), Sg.Input(default_text=fractions or '', key=NFX_KEY)],
        [Sg.Text('Enter TOTAL Dose in cGy'), Sg.Input(default_text=dose or '', key=TOTAL_DOSE_KEY)],
        [Sg.Radio(
            'Generate Tomo Plan', "RADIO1", default=False, key=TOMO_KEY,
            tooltip='Choose only one, but choose wisely', enable_events=True),
            Sg.Radio(
                'Generate VMAT Plan', "RADIO1", default=False, key=VMAT_KEY,
                tooltip='There can be only one.', enable_events=True)],
        [Sg.Radio(
            'Do Kidney sparing', "RADIO2", default=False, key=KIDNEY_KEY,
            tooltip='Kidneys to be spared and excluded from coverage', enable_events=True),
            Sg.Radio(
                'No kidney sparing', "RADIO2", default=False, key=NO_KIDNEY_KEY,
                tooltip='No need for Kidney sparing', enable_events=True)],
        [make_toggle_button('Pause Script', PAUSE_KEY)],
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
        elif event == PAUSE_KEY:
            connect.await_user_input('Script paused. Resume script to continue.')
            window[event].update(button_color=('black', 'lightgray'))
        elif event in ['-FFS STRUCTURES-', '-FFS PLAN-', '-OPT FFS-', '-HFS PLAN-', '-CALC FFS ON HFS-',
                       '-EXPORT FFS-', '-OPT HFS-']:
            # Check if total fractions, total dose, and plan type are selected
            if not values[NFX_KEY] or not values[TOTAL_DOSE_KEY] or not (
                    values.get(TOMO_KEY) or values.get(VMAT_KEY)) or not (
                    values.get(KIDNEY_KEY) or values.get(NO_KIDNEY_KEY)):
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
                        export_ffs_dose(values)
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
    if selections.get(TOMO_KEY, False):
        selections['-MACHINE-'] = "HDA0488"
        selections['-THI-'] = True
    elif selections.get(VMAT_KEY, False):
        selections['-MACHINE-'] = "TrueBeam_NoTrack"
        selections['-THI-'] = False

    return selections


def main() -> None:
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
    testing = True
    # Disable intermediate VMAT junctions and OTVs
    make_junctions = True
    make_otvs = False
    tbi_selections = tbi_gui()


if __name__ == '__main__':
    main()
