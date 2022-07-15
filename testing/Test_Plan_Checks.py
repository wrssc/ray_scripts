""" Plan Check
    Run basic plan integrity checks and parse the log file. Meant to be run
    on completed plans.

    Scope: Requires RayStation beamset to be loaded

    Example Usage:

    Script Created by RAB May 1st 2022
    Prerequisites:

    Version history:


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
__date__ = '2022-May-12'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10A SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__credits__ = ['']

#
# TODO: Steal this
# PROCESS_FUNCTION_DICT = {
#     "BolusID": (return_expected_unique_to_raystation, {}),
#     "DeviceSerialNumber": (return_expected_unique_to_aria, {}),
#     "InstitutionName": (return_expected_unique_to_aria, {}),
#     "InstitutionalDepartmentName": (return_expected_unique_to_aria, {}),
#     "Manufacturer": (return_expected_unique_to_aria, {}),
#     "ManufacturerModelName": (return_expected_unique_to_aria, {}),
#     "ReferencedToleranceTableNumber": (return_expected_unique_to_aria, {}),
#     "ReferencedPatientSetupNumber": (return_expected_mismatch, {"comment": "Numerical value may be different due to field reordering"}),
#     "SoftwareVersions": (return_expected_mismatch, {"comment": "RayStation is not Aria"}),
#     "SourceToSurfaceDistance": (process_ssd, {}),
#     "LeafJawPositions": (assess_near_match, {"tolerance_value": 0.01}),  # 0.01 mm
#     "TableTopLateralPosition": (return_expected_unique_to_aria, {}),
#     "TableTopLongitudinalPosition": (return_expected_unique_to_aria, {}),
#     "TableTopVerticalPosition": (return_expected_unique_to_aria, {}),
#     "TreatmentMachineName": (process_treatment_machine_name, {}),
# }
# if ds1_keyword in PROCESS_FUNCTION_DICT:
#     process_func, kwargs = PROCESS_FUNCTION_DICT[ds1_keyword]
# else:
#     process_func, kwargs = None, None
# TODO: Eliminate parent_key from function call. Each function returns:
#       pass_result, message_string
#       These get added as a list [('Child String - Test Name', pass_result, message_string)]
#       This list gets checked for pass_results
#       This list gets used for a build of elements in a loop
#
# TODO: Check contour interpolation
#   Find Ptv,Ctv, Gtv
#   if goals: get those - otherwise get all
#   check slices for gaps

# TODO: Check for slice alignment and rotation alignment 1899458
# TODO: Check Beamsets for same machine
#
# TODO: Check for same iso, and same number of fractions in
# different beamsets, and flag for merge


# TODO:
#   Check bad regions of Frame

# TODO:
#   def check_plan_name(bs):
#     Check plan name for appropriate
#     Measure target length of prostate for pros

# TODO: Look for big gaps between targets
#   def check_target_spacing(bs):
#     Find all targets
#     Put a box around them
#     look at the gaps and if they exceed some threshold throw an alert

# TODO: Tomo Time Check
#   def check_tomo_time(bs):
#     Look at the plan type. Use the normal tomo mod factors
#     Abdomen; 1.6 - 2.4
#     Brain; 1.6 - 2.4
#     Breast; 2.4 - 2.8
#     Cranio - Spinal; 1.8 - 2.2
#     Extremity; 2.0 - 2.4
#     Gyn; 1.8 - 2.4
#     H & N; 2.2 - 2.6
#     Lung(non - SBRT); 2.4 - 2.8
#     Lung(SBRT); 1.2 - 1.4
#     Pelvis; 1.8 - 2.4
#     Prostate(low; risk)    1.6 - 2.2
#     Prostate(high; risk)    2.0 - 2.4
#

# TODO: Check collisions
#   put a circle down at isocenter equal in dimension to ganty (collimator pin)/bore clearance
#   union patient/supports
#   determine gantry positions
#
# TODO:
#   def - check the front edges of the couch and suspended headboard
#
# TODO:
#   Flag all ROIs not made in MIM with goals
#
# TODO: Stray voxel check/

# TODO: Check clinical goal
#   if a clinical goal is not met, look at the objective list to see if it is constrained
#
#
import datetime
import sys
import os
import logging
import numpy as np
from math import isclose
from collections import namedtuple, OrderedDict
from System import Environment
import PySimpleGUI as sg
import re
from dateutil import parser
import connect
import tkinter as Tk
import pyperclip

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../library'))
import GeneralOperations

icon_dir = os.path.join(os.path.dirname(__file__), "Icons\\")
RED_CIRCLE = os.path.join(icon_dir, "red_circle_icon.png")
GREEN_CIRCLE = os.path.join(icon_dir, "green_circle_icon.png")
BLUE_CIRCLE = os.path.join(icon_dir, "blue_circle_icon.png")

#
# LOG PARSING INFO
LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\logs"
DEV_LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs"
KEEP_PHRASES = [("Critical", "CRITICAL"), ("Warnings", "WARNING"),
                ("Info", "INFO"), ("Debug", "DEBUG")]
#
# EXAM DEFAULTS
# TIME ELAPSED BETWEEN PLAN AND CT
DAYS_SINCE_SIM = 14
#
# CONTOURING DEFAULTS
BOLUS_NAMES = ["bolus"]
# def - check the front edges of the couch and suspended headboard
NO_FLY_NAME = "NoFlyZone_PRV"
#
# PLANNING DEFAULTS
DOSE_FRACTION_PAIRS = [(4, 2000), (5, 2000)]  # Often mixed up fractionations
#
EDW_MU_LIMIT = 20.
#
# DOSE TOLERANCES
NO_FLY_DOSE = 100.  # cGy
PACEMAKER_DOSE = 200.  # cGy
#
# DOSE GRID PREFERENCES
DOSE_GRID_DEFAULT = 0.2  # 2 mm

GRID_PREFERENCES = {
    'SBRT': {
        'PLAN_NAMES': ['LUL', 'LLL', 'RUL', 'RML', 'RLL',
                       'LuLU_SBR', 'LuLL_SBR', 'LuRU_SBR', 'LuRM_SBR', 'LuRL_SBR',
                       'BreR_SBR', 'BreL_SBR', 'Abdo_SBR', 'LivR_SBR', 'Panc_SBR',
                       'Pelv_SBR', 'HipR_SBR', 'HipL_SBR'],
        'DOSE_GRID': 0.15,  # 1.5 mm
        'FRACTION_SIZE_LIMIT': 801,  # cGy
        'SLICE_THICKNESS': 0.2,  # 2.0 mm
    },
    'SBRT_FINE': {
        'PLAN_NAMES': ['Pros_SBR', 'Brai_SBR', 'NecB_SBR', 'NecL_SBR', 'SpiT_SBR', 'SpiL_SBR', 'SpiC_SBR'],
        'DOSE_GRID': 0.15,  # 1.5 mm
        'FRACTION_SIZE_LIMIT': 801,  # cGy
        'SLICE_THICKNESS': 0.1,  # 2.0 mm
    },
    'SRS': {
        'PLAN_NAMES': ['SRS', 'FSR'],
        'DOSE_GRID': 0.1,  # 1.0 mm
        'FRACTION_SIZE_LIMIT': 1500,  # cGy
        'SLICE_THICKNESS': 0.1,  # 1.0 mm
    },
    'TBI': {
        'PLAN_NAMES': ['TBI'],
        'DOSE_GRID': 0.5,  # 5 mm
        'FRACTION_SIZE_LIMIT': None,  # Don't check
        'SLICE_THICKNESS': 0.4,  # 4 mm
    },
    'VMAT': {
        'PLAN_NAMES': ['VMA', '3CA'],
        'DOSE_GRID': 0.3,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.3,  # 3 mm
    },
    'THI': {
        'PLAN_NAMES': ['THI', 'T3D'],
        'DOSE_GRID': 0.3,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.3,  # 3 mm
    },
    '3D': {
        'PLAN_NAMES': ['3DC'],
        'DOSE_GRID': 0.4,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.4,  # 4 mm
    },
}
#
# FIELD OF VIEW SETTINGS
FIELD_OF_VIEW_PREFERENCES = {'NAME': 'FieldOfView',
                             'WALL_SUFFIX': '_Wall',
                             'CONTRACTION': 0.5,  # cm
                             'NAME_INTERSECTION': 'FOV_EXT_INTERSECT',
                             'SI_PTV_BUFFER': 2.0,  # cm
                             }

MCS_TOLERANCES = {'MCS': {'MEAN': 0.369,
                          'SIGMA': 0.152},
                  'LSV': {'MEAN': 0.694,
                          'SIGMA': 0.134},
                  'AAV': {'MEAN': 0.522,
                          'SIGMA': 0.188},
                  }

TOMO_DATA = {'MACHINES': ['HDA0488', 'HDA0477'],
             'PLAN_TR_SUFFIX': r'_Tr',
             'LATERAL_ISO_MARGIN': 2.,  # cm
             'SUPPORTS': ['TomoCouch']
             }

TRUEBEAM_DATA = {'MACHINES': ['TrueBeam', 'TrueBeamSTx'],
                 'SUPPORTS': ['TrueBeamCouch', 'CivcoBaseShell_Cork', 'CivcoInclineShell_Wax',
                              ]}


def comment_to_clipboard(pd):
    #
    # Clear the system clipboard
    r = Tk.Tk()
    r.withdraw()
    r.clipboard_clear()

    #
    # Add data to the beamset comment
    approval_status = approval_info(pd.plan, pd.beamset)
    beamset_comment = approval_status.beamset_approval_time
    # Copy the comment to the system clipboard
    r.clipboard_append(beamset_comment)
    r.update()  # now it stays on the clipboard after the window is closed
    return r


def read_log_file(patient_id):
    """
    Read the lines from the patient log in both clinical and development locations
    Args:
        patient_id: str: contains patient ID

    Returns:
        file_contents: lines of file
    """
    log_file = patient_id + '.txt'
    log_input_file = os.path.join(LOG_DIR, patient_id, log_file)
    dev_log_file = patient_id + '.txt'
    dev_log_input_file = os.path.join(DEV_LOG_DIR, patient_id, dev_log_file)
    try:
        with open(log_input_file) as f:
            file_contents = f.readlines()
    except FileNotFoundError:
        logging.debug("File {} not found in dir {}"
                      .format(log_file, LOG_DIR))
        file_contents = []
    try:
        with open(dev_log_input_file) as f:
            file_contents.append(f.readlines())
    except FileNotFoundError:
        logging.debug("File {} not found in dir {}"
                      .format(dev_log_file, DEV_LOG_DIR))
    return file_contents


def parse_log_file(lines, parent_key, phrases=KEEP_PHRASES):
    """
    Parse the log file lines for the phrase specified
    Args:
        parent_key: The top key for these log entries (typically patient level)
        lines: list of strings from a log file
        phrases: list of tuples
            (level,phrase):
                           level: is a string indicating pass level
                           phrase: is a string to identify lines for return

    Returns:
        message: list of lists of format: [parent key, key, value, result]

    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, Log_Parse_Check
    """
    message = []
    time_stamp_exp = r'(^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(.*)'  # The front timestamp
    re_c = r'^\t(Case: .*)\t'
    re_e = r'(Exam: .*)\t'
    re_p = r'(Plan: .*)\t'
    re_b = r'(Beamset: .*)\t'
    #
    # Declare reg-ex for levels in the log file
    context_exps = OrderedDict()
    context_exps['Beamset'] = re_c + re_e + re_p + re_b
    context_exps['Plan'] = re_c + re_e + re_p
    context_exps['Exam'] = re_c + re_e
    context_exps['Case'] = re_c
    for p in phrases:
        key = 'Log' + p[1]
        message.append([parent_key, key, key, p[0]])
        re_phrase = p[1] + r'.*\.py: '
        for l in lines:
            if p[1] in l:
                l = re.sub(re_phrase, '', l)  # Wipe out the source python program
                # Sort the line into a part for the timestamp and one for remainder
                parsed_l = [part for t in re.findall(time_stamp_exp, l) for part in t]
                parsed_l[1].lstrip()  # front white space
                parsed_l[1].rstrip()  # Remove \n
                deepest_level = None
                for c, exp in context_exps.items():
                    if bool(re.search(exp, parsed_l[1])):
                        levels = OrderedDict()
                        deepest_level = c
                        for g in re.findall(exp, parsed_l[1])[0]:
                            lev_key, lev_val = g.split(': ')
                            levels[lev_key] = lev_val
                        parsed_l[1] = re.sub(exp, '', parsed_l[1])
                        parsed_l[0] += ' ' + deepest_level + ': ' + levels[deepest_level]
                        break
                if not deepest_level:
                    parsed_l[1] = re.sub(r'\t', '', parsed_l[1])
                message.append([key, parsed_l[0], parsed_l[0], parsed_l[1]])
    return message


# PATIENT CHECKS
def match_date(date1, date2):
    if date1:
        p_date1 = parser.parse(date1).date().strftime("%Y-%m-%d")
    else:
        p_date1 = None
    if date2:
        p_date2 = parser.parse(date2).date().strftime("%Y-%m-%d")
    else:
        p_date2 = None

    if p_date1 == p_date2:
        return True, p_date1, p_date2
    else:
        return False, p_date1, p_date2


def match_patient_name(name1, name2):
    # Case insensitive match on First and Last name (strip at ^)
    spl_1 = tuple(re.split(r'\^', name1))
    spl_2 = tuple(re.split(r'\^', name2))
    try:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE)) and \
                bool(re.match(re.escape(spl_1[1]), re.escape(spl_2[1]), re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2
    except IndexError:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2


def match_gender(gender1, gender2):
    # Match M/Male, F/Female, O/Other, Unknown/None
    if gender1:
        if 'Unknown' in gender1[0]:
            gender1 = None
        else:
            l1 = gender1[0]
    if gender2:
        l2 = gender2[0]
    if gender1 and gender2:
        if bool(re.match(l1, l2, re.IGNORECASE)):
            return True, gender1, gender2  # Genders Match
        else:
            return False, gender1, gender2  # Genders are different
    elif gender1:
        return False, gender1, gender2  # Genders are different
    elif gender2:
        return False, gender1, gender2  # Genders are different
    else:
        return False, gender1, gender2  # Genders not specified


def match_exactly(value1, value2):
    if value1 == value2:
        return True, value1, value2
    else:
        return False, value1, value2


def check_exam_data(pd, parent_key):
    """

    Args:
        patient:
        exam:
        parent_key:

    Returns:
        messages: [[str1, ...,],...]: [[parent_key, child_key, messgae display, Pass/Fail/Alert]]
    # TODO: Parse date/time of birth and ignore time of birth
    """

    child_key = 'DICOM Raystation Comparison'
    modality_tag = (0x0008, 0x0060)
    tags = {str(pd.patient.Name): (0x0010, 0x0010, match_patient_name),
            str(pd.patient.PatientID): (0x0010, 0x0020, match_exactly),
            str(pd.patient.Gender): (0x0010, 0x0040, match_gender),
            str(pd.patient.DateOfBirth): (0x0010, 0x0030, match_date)
            }
    get_rs_value = pd.exam.GetStoredDicomTagValueForVerification
    modality = list(get_rs_value(Group=modality_tag[0],
                                 Element=modality_tag[1]).values())[0]  # Get Modality
    message_str = "Attribute: [DICOM vs RS]"
    all_passing = True
    for k, v in tags.items():
        rs_tag = get_rs_value(Group=v[0], Element=v[1])
        for dicom_attr, dicom_val in rs_tag.items():
            match, rs, dcm = v[2](dicom_val, k)
            if match:
                message_str += "{}:[\u2713], ".format(dicom_attr)
            else:
                all_passing = False
                match_str = ' \u2260 '
                message_str += "{0}: [{1}:{2} {3} RS:{4}], " \
                    .format(dicom_attr, modality, dcm, match_str, rs)
    if all_passing:
        pass_result = 'Pass'
    else:
        pass_result = 'Fail'
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_localization(pd, parent_key):
    child_key = 'Localization point exists'
    poi_coord = {}
    localization_found = False
    for p in pd.case.PatientModel.StructureSets[pd.exam.Name].PoiGeometries:
        if p.OfPoi.Type == 'LocalizationPoint':
            point = p
            poi_coord = p.Point
            localization_found = True
            break
    if poi_coord:
        message_str = "Localization point {} exists and has coordinates.".format(point.OfPoi.Name)
        pass_result = "Pass"
    elif localization_found:
        message_str = "Localization point {} does not have coordinates.".format(point.OfPoi.Name)
        pass_result = "Fail"
    else:
        message_str = "No point of type LocalizationPoint found"
        pass_result = "Fail"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def approval_info(plan, beamset):
    """
    Determine if beamset is approved and then if plan is approved. Return data
    Args:
        plan: RS plan object
        beamset: RS beamset object

    Returns:
        approval: NamedTuple.(beamset_approved, beamset_approved, beamset_exported,
                              beamset_reviewer, beamset_approval_time, plan_approved,
                              plan_exported, plan_reviewer, plan_approval_time)
    """
    Approval = namedtuple('Approval',
                          ['beamset_approved',
                           'beamset_exported',
                           'beamset_reviewer',
                           'beamset_approval_time',
                           'plan_approved',
                           'plan_exported',
                           'plan_reviewer',
                           'plan_approval_time'])
    plan_approved = False
    plan_reviewer = ""
    plan_time = ""
    plan_exported = False
    beamset_approved = False
    beamset_reviewer = ""
    beamset_time = ""
    beamset_exported = False
    try:
        if beamset.Review.ApprovalStatus == 'Approved':
            beamset_approved = True
            beamset_reviewer = beamset.Review.ReviewerName
            beamset_time = parser.parse(str(beamset.Review.ReviewTime))
            beamset_exported = beamset.Review.HasBeenExported
            if plan.Review.ApprovalStatus == 'Approved':
                plan_approved = True
                plan_reviewer = plan.Review.ReviewerName
                plan_time = parser.parse(str(plan.Review.ReviewTime))
                plan_exported = plan.Review.HasBeenExported
        else:
            plan_approved = False
            plan_reviewer = plan.Review.ReviewerName
            plan_time = parser.parse(str(plan.Review.ReviewTime))
            plan_exported = plan.Review.HasBeenExported
    except AttributeError:
        pass
    approval = Approval(beamset_approved=beamset_approved,
                        beamset_exported=beamset_exported,
                        beamset_reviewer=beamset_reviewer,
                        beamset_approval_time=beamset_time,
                        plan_approved=plan_approved,
                        plan_exported=plan_exported,
                        plan_reviewer=plan_reviewer,
                        plan_approval_time=plan_time)
    return approval


def check_plan_approved(pd, parent_key):
    """
    Check if a plan is approved
    Args:
        parent_key: parent position in the tree of this child


    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]

    """
    child_key = "Plan approval status"
    approval_status = approval_info(pd.plan, pd.beamset)
    if approval_status.plan_approved:
        message_str = "Plan: {} was approved by {} on {}".format(
            pd.plan.Name,
            approval_status.plan_reviewer,
            approval_status.plan_approval_time
        )
        pass_result = "Pass"
    else:
        message_str = "Plan: {} is not approved".format(
            pd.plan.Name)
        pass_result = "Fail"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_beamset_approved(pd, parent_key):
    """
    Check if a plan is approved
    Args:
        parent_key: parent position in the tree of this child
        pd: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]
    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA

    """
    child_key = "Beamset approval status"
    approval_status = approval_info(pd.plan, pd.beamset)
    if approval_status.beamset_approved:
        message_str = "Beamset: {} was approved by {} on {}".format(
            pd.beamset.DicomPlanLabel,
            approval_status.beamset_reviewer,
            approval_status.beamset_approval_time
        )
        pass_result = "Pass"
    else:
        message_str = "Beamset: {} is not approved".format(
            pd.beamset.DicomPlanLabel)
        pass_result = "Fail"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def compare_exam_date(pd, parent_key):
    """
    Check if date occurred within tolerance
    Ideally we'll use the approval date, if not, we'll use the last saved by,
    if not we'll use right now!
    Args:
        parent_key:
        beamset: RS Beamset Object
        exam: RS Exam
        plan: RS Plan
        tolerance: int: days
    Returns:
        message: [str1, ...,]: [parent_key, child_key, child_key display, result value]
    Test Patient:

        Pass (all but Gender): ZZ_RayStation^CT_Artifact, 20210408SPF
              Case 1: TB_HFS_ArtFilt: Lsha_3DC_R0A0
        Fail: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022:
              ChwL: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    tolerance = DAYS_SINCE_SIM
    child_key = "Exam date is recent"
    dcm_data = list(pd.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020).values())
    approval_status = approval_info(pd.plan, pd.beamset)
    if dcm_data:
        dcm_date = parser.parse(dcm_data[0])
        #
        if approval_status.beamset_approved:
            current_time = parser.parse(str(pd.beamset.Review.ReviewTime))
        else:
            try:
                # Use last saved date if plan not approved
                current_time = parser.parse(str(pd.beamset.ModificationInfo.ModificationTime))
            except AttributeError:
                current_time = datetime.datetime.now()

        elapsed_days = (current_time - dcm_date).days

        if elapsed_days <= tolerance:
            message_str = "Exam {} acquired {} within {} days ({} days) of Plan Date {}" \
                .format(pd.exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Pass"
        else:
            message_str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(pd.exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Fail"
    else:
        message_str = "Exam {} has no apparent study date!".format(pd.exam.Name)
        pass_result = "Alert"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def match_image_directions(pd, parent_key):
    child_key = 'Image is axially oriented'
    # Match the directions that a correctly oriented image should have
    stack_details = {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                     'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                     'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}}
    col_dir = pd.exam.Series[0].ImageStack.ColumnDirection
    row_dir = pd.exam.Series[0].ImageStack.RowDirection
    sli_dir = pd.exam.Series[0].ImageStack.SliceDirection
    message_str = ""
    pass_result = 'Pass'
    if col_dir != stack_details['direction_column'] or \
            sli_dir != stack_details['direction_slice']:
        message_str.append('Exam {} has been rotated and will not transfer to iDMS!'.format(pd.exam.Name))
        pass_result = 'Fail'
    if row_dir != stack_details['direction_row']:
        message_str.append('Exam {} has been rotated or was acquired'.format(pd.exam.Name)
                           + ' with gantry tilt and should be reoriented!')
        pass_result = 'Fail'
    if not message_str:
        message_str = 'Image set {} is not rotated'.format(pd.exam.Name)

    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages
#
# CONTOUR CHECKS
def get_roi_list(case, exam_name=None):
    """
    Get a list of all rois
    Args:
        case: RS case object

    Returns:
        roi_list: [str1,str2,...]: a list of roi names
    """
    roi_list = []
    if exam_name:
        structure_sets = [case.PatientModel.StructureSets[exam_name]]
    else:
        structure_sets = [s for s in case.PatientModel.StructureSets]

    for s in structure_sets:
        for r in s.RoiGeometries:
            if r.OfRoi.Name not in roi_list:
                roi_list.append(r.OfRoi.Name)
    return roi_list


def match_roi_name(roi_names, roi_list):
    """
    Match the structures in case witht
    Args:
        roi_names: [str1, str2, ...]: list of names to search for
        roi_list: [str1, str2, ...]: list of current rois

    Returns:
        matches: [str1, str2, ...]: list of matching rois
    """
    matches = []
    for r_n in roi_names:
        exp_r_n = r'^' + r_n + r'$'
        for m in roi_list:
            if re.search(exp_r_n, m, re.IGNORECASE):
                matches.append(m)
    return matches


def get_roi_geometries(case, exam_name, roi_names):
    all_geometries = get_roi_list(case, exam_name)
    matches = match_roi_name(roi_names, all_geometries)
    matching_geometries = []
    ss = case.PatientModel.StructureSets[exam_name]
    for m in matches:
        if ss.RoiGeometries[m].HasContours():
            matching_geometries.append(ss.RoiGeometries[m])
    return matching_geometries


def get_volumes(geometries):
    vols = {g.OfRoi.Name: g.GetRoiVolume() for g in geometries}
    return vols


def get_external(pd):
    for r in pd.case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            return r.Name
    return None


def make_fov(pd, fov_name):
    try:
        pd.case.PatientModel.CreateRoi(
            Name=fov_name,
            Color="192, 192, 192",
            Type=fov_name,
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        # TODO replace with cylinder creation at [0,0,0]
        #   grab dicom tag: 0018, 1100 Reconstruction Diameter
        pd.case.PatientModel.RegionsOfInterest[fov_name].CreateFieldOfViewROI(
            ExaminationName=pd.exam.Name
        )
        pd.case.PatientModel.StructureSets[pd.exam.Name].SimplifyContours(
            RoiNames=[fov_name],
            MaxNumberOfPoints=20,
            ReduceMaxNumberOfPointsInContours=True,
        )
        return True
    except:
        return False


def make_wall(pd, name, source, exp):
    fov_wall = pd.case.PatientModel.CreateRoi(
        Name=name,
        Color="192, 192, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    pd.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Union',
            "SourceRoiNames": [source],
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [source],
            "MarginSettings": {'Type': 'Contract',
                               'Superior': exp[0],
                               'Inferior': exp[1],
                               'Anterior': exp[2],
                               'Posterior': exp[3],
                               'Right': exp[4],
                               'Left': exp[5],
                               }
        },
        ResultOperation='Subtraction',
        ResultMarginSettings=margins,
    )
    pd.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=pd.exam, Algorithm="Auto"
    )


def intersect_sources(pd, name, sources):
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    intersect = pd.case.PatientModel.CreateRoi(
        Name=name,
        Color="0, 0, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    pd.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Intersection',
            "SourceRoiNames": sources,
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [],
            "MarginSettings": margins,
        },
        ResultOperation='None',
        ResultMarginSettings=margins,
    )
    pd.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=pd.exam, Algorithm="Auto"
    )
    pd.case.PatientModel.RegionsOfInterest[name].DeleteExpression()


def get_targets_si_extent(pd):
    types = ['Ptv']
    rg = pd.case.PatientModel.StructureSets[pd.exam.Name].RoiGeometries
    extent = [-1000., 1000]
    for r in rg:
        if r.OfRoi.Type in types and r.HasContours():
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    return extent


def get_si_extent(pd, types=None, roi_list=None):
    rg = pd.case.PatientModel.StructureSets[pd.exam.Name].RoiGeometries
    initial = [-1000, 1000]
    extent = [-1000, 1000]
    # Generate a list to search
    type_list = []
    rois = []
    if types:
        type_list = [r.OfRoi.Name for r in rg if r.OfRoi.Type in types and r.HasContours]
    if roi_list:
        rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in roi_list and r.HasContours]
    check_list = list(set(type_list + rois))

    for r in rg:
        if r.OfRoi.Name in check_list:
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    if extent == initial:
        return None
    else:
        return extent


def get_slice_positions(pd):
    # Get slice positions in linear array
    slice_positions = np.array(pd.exam.Series[0].ImageStack.SlicePositions)
    #
    # Starting corner
    image_corner = pd.exam.Series[0].ImageStack.Corner
    #
    # Actual z positions
    dicom_slice_positions = image_corner.z + slice_positions
    return dicom_slice_positions


def image_extent_sufficient(pd, parent_key, target_extent=None):
    child_key = 'Image extent sufficient'
    #
    # Get image slices
    bb = pd.exam.Series[0].ImageStack.GetBoundingBox()
    bb_z = [bb[0]['z'], bb[1]['z']]
    z_extent = [min(bb_z), max(bb_z)]
    #
    # Get target length
    if not target_extent:
        target_extent = get_si_extent(pd=pd, types=['Ptv'])
    #
    # Tolerance for SI extent
    #
    # Tolerance for SI extent
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    #
    # Nice strings for output
    z_str = '[' + ('%.2f ' * len(z_extent)) % tuple(z_extent) + ']'
    t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not target_extent:
        message_str = 'No targets found of type Ptv, image extent could not be evaluated'
        pass_result = 'Fail'
    elif z_extent[1] >= buffered_target_extent[1] and z_extent[0] <= buffered_target_extent[0]:
        message_str = 'Planning image extent {} and is at least {:.1f} larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = "Pass"
    elif z_extent[1] < buffered_target_extent[1] or z_extent[0] > buffered_target_extent[0]:
        message_str = 'Planning Image extent:{} is insufficient for accurate calculation.'.format(z_str) \
                      + '(SMALLER THAN :w' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = "Fail"
    else:
        message_str = 'Target length could not be compared to image set'
        pass_result = "Fail"
    # Prepare output
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def couch_type_correct(pd, parent_key):
    child_key = 'Couch type correct'
    # Abbreviate geometries
    rg = pd.case.PatientModel.StructureSets[pd.exam.Name].RoiGeometries
    roi_list = [r.OfRoi.Name for r in rg]
    beam = pd.beamset.Beams[0]
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    wrong_supports = []
    correct_supports = []
    if current_machine.Name in TRUEBEAM_DATA['MACHINES']:
        wrong_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
    elif current_machine.Name in TOMO_DATA['MACHINES']:
        wrong_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
    if wrong_supports:
        message_str = 'Support Structure(s) {} are INCORRECT for  machine {}'.format(
            wrong_supports, current_machine.Name)
        pass_result = "Fail"
    elif correct_supports:
        message_str = 'Support Structure(s) {} are correct for machine {}'.format(
            correct_supports, current_machine.Name)
        pass_result = "Pass"
    else:
        message_str = 'No couch structure found'
        pass_result = "Alert"
    # Prepare output
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def couch_extent_sufficient(pd, parent_key, target_extent=None):
    """
       Check PTV volume extent have supports under them
       Args:
           parent_key:
           pd: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
           target_extent: [min, max extent of target]
       Returns:
           message: [str1, ...,]: [parent_key, child_key, child_key display, result value]
       Test Patient:

           Pass: Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Anal_THI: Anal_THI
           Fail (bad couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: ChwL_3DC: SCV PAB
           Fail (no couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Pros_VMA: Pros_VMA
       """
    # Testing -
    child_key = 'Couch extent sufficient'
    #
    # Get support structure extent
    rg = pd.case.PatientModel.StructureSets[pd.exam.Name].RoiGeometries
    supports = TOMO_DATA['SUPPORTS'] + TRUEBEAM_DATA['SUPPORTS']
    supports = [r.OfRoi.Name for r in rg if r.OfRoi.Name in supports]

    couch_extent = get_si_extent(pd=pd, roi_list=supports)
    if couch_extent:
        # Nice strings for output
        z_str = '[' + ('%.2f ' * len(couch_extent)) % tuple(couch_extent) + ']'
    #
    # Get target length
    if not target_extent:
        target_extent = get_si_extent(pd=pd, types=['Ptv'])
    #
    # Tolerance for SI extent
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    if target_extent:
        # Output string
        t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not couch_extent:
        message_str = 'No support structures found. No couch check possible'
        pass_result = "Fail"
    elif couch_extent[1] >= buffered_target_extent[1] and couch_extent[0] <= buffered_target_extent[0]:
        message_str = 'Supports (' \
                      + ', '.join(supports) \
                      + ') span {} and is at least {:.1f} cm larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = "Pass"
    elif couch_extent[1] < buffered_target_extent[1] or couch_extent[0] > buffered_target_extent[0]:
        message_str = 'Support extent (' \
                      + ', '.join(supports) \
                      + ') :{} is not fully under the target.'.format(z_str) \
                      + '(SMALLER THAN ' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = "Fail"
    else:
        message_str = 'Target length could not be compared to support extent'
        pass_result = "Fail"
    # Prepare output
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def build_tree_element(parent_key, child_key, pass_result, message_str):
    elements = []
    if pass_result == 'Fail':
        icon = RED_CIRCLE
    elif pass_result == 'Pass':
        icon = GREEN_CIRCLE
    elif pass_result == 'Alert':
        icon = BLUE_CIRCLE
    else:
        icon = BLUE_CIRCLE
    elements.append([parent_key, child_key, child_key, pass_result, icon])
    elements.append([child_key, pass_result, message_str, pass_result, icon])
    return elements


def external_overlaps_fov(pd, parent_key, target_extent=None):
    message_str = None
    child_key = "Edge of scan overlaps patient at key slices"
    sources = []
    #
    # Find external
    ext_name = get_external(pd)
    #
    # Check if pre-existing FOV
    fov_name = FIELD_OF_VIEW_PREFERENCES['NAME']
    fov = get_roi_geometries(pd.case, pd.exam.Name, roi_names=[fov_name])
    if fov:
        fov_exists = True
    else:
        fov_exists = make_fov(pd, fov_name)
    #
    # Check initial inputs
    if not ext_name:
        pass_result = "Fail"
        message_str = 'No External'
    if not fov_exists:
        pass_result = "Fail"
        message_str = 'Making ' + fov_name + ' failed.'
    if not message_str:
        #
        # Build walls (sources)
        walls = [
            {'Name': FIELD_OF_VIEW_PREFERENCES['NAME'] + FIELD_OF_VIEW_PREFERENCES['WALL_SUFFIX'],
             'Source': FIELD_OF_VIEW_PREFERENCES['NAME'],
             'In_Expand': [0., 0.] + [FIELD_OF_VIEW_PREFERENCES['CONTRACTION']] * 4,
             },
            {'Name': ext_name + FIELD_OF_VIEW_PREFERENCES['WALL_SUFFIX'],
             'Source': ext_name,
             'In_Expand': [FIELD_OF_VIEW_PREFERENCES['CONTRACTION']] * 6},
        ]
        pm = pd.case.PatientModel
        for w in walls:
            w_name = pm.GetUniqueRoiName(DesiredName=w['Name'])
            make_wall(pd, name=w_name, source=w['Source'], exp=w['In_Expand'])
            sources.append(w_name)
        #
        # Intersect the walls
        intersect_name = pm.GetUniqueRoiName(
            DesiredName=FIELD_OF_VIEW_PREFERENCES['NAME_INTERSECTION'])
        intersect_sources(pd, intersect_name, sources)
        #
        # Get the extent of the targets
        if not target_extent:
            target_extent = get_targets_si_extent(pd)
        #
        # Check if any slices of the intersection are on target slices
        contours = pm.StructureSets[pd.exam.Name].RoiGeometries[intersect_name].PrimaryShape.Contours
        vertices = np.array([[g.x, g.y, g.z] for s in contours for g in s])
        if vertices.size > 0:
            suspect_vertices = np.where(np.logical_and(
                vertices[:, 2] > target_extent[1] - FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER'],
                vertices[:, 2] < target_extent[0] + FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']))
            suspect_slices = np.unique(vertices[suspect_vertices][:, 2])
        else:
            # No overlap of FOV and External
            suspect_slices = np.empty(shape=0)
        #
        # Clean up
        sources.append(intersect_name)
        if not fov:
            sources.append(fov_name)
        for s in sources:
            pm.RegionsOfInterest[s].DeleteRoi()
        if suspect_slices.size > 0:
            pass_result = "Fail"
            message_str = 'Potential FOV issues found on slices {}'.format(suspect_slices)
        else:
            pass_result = "Pass"
            message_str = 'No Potential Overlap with FOV Found'
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


#
# PLAN CHECKS


def pass_control_point_spacing(s, s0, spacing):
    if not s0:
        if s.DeltaGantryAngle <= spacing:
            return True
        else:
            return False
    else:
        if s.DeltaGantryAngle - s0.DeltaGantryAngle <= spacing:
            return True
        else:
            return False


def message_format_control_point_spacing(beam_spacing_failures, spacing):
    # Takes in a message dictionary that is labeled per beam, then parses
    if beam_spacing_failures:
        for b, v in beam_spacing_failures.items():
            message_str = 'Beam {}: Gantry Spacing Exceeds {} in Control Points {}\n' \
                .format(b, spacing, v)
            message_result = "Fail"
    else:
        message_str = "No control points > {} detected".format(spacing)
        message_result = "Pass"
    return message_str, message_result


def check_control_point_spacing(bs, expected, parent_key):
    """
    bs: RayStation beamset
    expected: Integer delineating the gantry angle between control points in a beam
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    """
    child_key = 'Control Point Spacing'
    beam_result = {}
    for b in bs.Beams:
        s0 = None
        fails = []
        for s in b.Segments:
            if not pass_control_point_spacing(s, s0, spacing=expected):
                fails.append(s.SegmentNumber + 1)
            s0 = s
        if fails:
            beam_result[b.Name] = fails
    message_str, pass_result = message_format_control_point_spacing(beam_spacing_failures=beam_result,
                                                                    spacing=expected)
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_transfer_approved(pd, parent_key):
    """

    Args:
        pd: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
        parent_key: parent_node

    Returns:
        message (list str): [Pass_Status, Message String]

    """
    child_key = "Transfer Beamset approval status"
    parent_beamset_name = pd.beamset.DicomPlanLabel
    daughter_plan_name = pd.plan.Name + TOMO_DATA['PLAN_TR_SUFFIX']
    if TOMO_DATA['MACHINES'][0] in pd.beamset.MachineReference['MachineName']:
        daughter_machine = TOMO_DATA['MACHINES'][1]
    else:
        daughter_machine = TOMO_DATA['MACHINES'][0]

    daughter_beamset_name = parent_beamset_name[:8] \
                            + TOMO_DATA['PLAN_TR_SUFFIX'] \
                            + daughter_machine[-3:]
    plan_names = [p.Name for p in pd.case.TreatmentPlans]
    beamset_names = [bs.DicomPlanLabel for p in pd.case.TreatmentPlans for bs in p.BeamSets]
    if daughter_beamset_name in beamset_names and daughter_plan_name in plan_names:
        transfer_beamset = pd.case.TreatmentPlans[daughter_plan_name].BeamSets[daughter_beamset_name]
    else:
        transfer_beamset = None
        message_str = "Beamset: {} is missing a transfer plan!".format(pd.beamset.DicomPlanLabel)
        pass_result = "Fail"
    if transfer_beamset:
        approval_status = approval_info(pd.plan, transfer_beamset)
        if approval_status.beamset_approved:
            message_str = "Transfer Beamset: {} was approved by {} on {}".format(
                transfer_beamset.DicomPlanLabel,
                approval_status.beamset_reviewer,
                approval_status.beamset_approval_time
            )
            pass_result = "Pass"
        else:
            message_str = "Beamset: {} is not approved".format(
                transfer_beamset.DicomPlanLabel)
            pass_result = "Fail"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_edw_MU(beamset, parent_key):
    """
    Checks to see if all MU are greater than the EDW limit
    Args:
        beamset:

    Returns:
        messages: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_13May2022, C1
        PASS: ChwR_3DC_R0A0
        FAIL: ChwR_3DC_R2A0
    """
    child_key = "EDW MU Check"
    edws = {}
    for b in beamset.Beams:
        try:
            if b.Wedge:
                if 'EDW' in b.Wedge.WedgeID:
                    edws[b.Name] = b.BeamMU
        except AttributeError:
            logging.debug('No wedge object in {} with technique {}. Electrons?'.format(
                beamset.DicomPlanLabel, beamset.DeliveryTechnique))
            break
    if edws:
        passing = True
        edw_passes = []
        edw_message = "Beam(s) have EDWs: "
        for bn, mu in edws.items():
            if mu < EDW_MU_LIMIT:
                passing = False
                edw_message += "{}(MU)={:.2f},".format(bn, mu)
            else:
                edw_passes.append(bn)
        if passing:
            edw_message += "{} all with MU > {}".format(edw_passes, EDW_MU_LIMIT)
        else:
            edw_message += "< {}".format(EDW_MU_LIMIT)
    else:
        passing = True
        edw_message = "No beams with EDWs found"

    if passing:
        pass_result = "Pass"
        message_str = edw_message
    else:
        pass_result = "Fail"
        message_str = edw_message
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_common_isocenter(beamset, parent_key, tolerance=1e-12):
    """
    Checks all beams in beamset for shared isocenter

    Args:
        beamset (object):
        parent_key (str): root upon which this check goes
        tolerance (flt): largest acceptable difference in isocenter location
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    child_key = "Isocenter Position Identical"
    initial_beam_name = beamset.Beams[0].Name
    iso_pos_x = beamset.Beams[0].Isocenter.Position.x
    iso_pos_y = beamset.Beams[0].Isocenter.Position.y
    iso_pos_z = beamset.Beams[0].Isocenter.Position.z
    iso_differs = []
    iso_match = []
    for b in beamset.Beams:
        b_iso = b.Isocenter.Position
        if all([isclose(b_iso.x, iso_pos_x, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.y, iso_pos_y, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.z, iso_pos_z, rel_tol=tolerance, abs_tol=0.0)]):
            iso_match.append(b.Name)
        else:
            iso_differs.append(b.Name)
    if iso_differs:
        pass_result = "Fail"
        message_str = "Beam(s) {} differ in isocenter location from beam {}".format(iso_differs, initial_beam_name)
    else:
        pass_result = "Pass"
        message_str = "Beam(s) {} all share the same isocenter to within {} mm".format(iso_match, tolerance)
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_tomo_isocenter(pd, parent_key):
    """
    Checks isocenter for lateral less than 2 cm.

    Args:
        pd (object): Named tuple of ScriptObjects
        parent_key (str): root upon which this check goes
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    child_key = "Isocenter Lateral Acceptable"
    iso_pos_x = pd.beamset.Beams[0].Isocenter.Position.x
    if np.less_equal(abs(iso_pos_x), TOMO_DATA['LATERAL_ISO_MARGIN']):
        pass_result = "Pass"
        message_str = "Isocenter [{}] lateral shift is acceptable: {} < {} cm".format(
            pd.beamset.Beams[0].Isocenter.Annotation.Name,
            iso_pos_x,
            TOMO_DATA['LATERAL_ISO_MARGIN'])
    else:
        pass_result = "Fail"
        message_str = "Isocenter [{}] lateral shift is inconsistent with indexing: {} > {} cm!".format(
            pd.beamset.Beams[0].Isocenter.Name,
            iso_pos_x,
            TOMO_DATA['LATERAL_ISO_MARGIN'])
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_bolus_included(pd, parent_key):
    """

    Args:
        parent_key: str: the key under which this test is performed in the treedata

    Returns:
        message: list of lists of format: [parent key, key, value, result]
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, ChwL
        Pass: Bolus_Roi_Check_Pass: ChwL_VMA_R1A0
        Fail: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    child_key = "Bolus Application"
    exam_name = pd.exam.Name
    roi_list = get_roi_list(pd.case, exam_name=exam_name)
    bolus_names = match_roi_name(roi_names=BOLUS_NAMES, roi_list=roi_list)
    if bolus_names:
        fail_str = "Stucture(s) {} named bolus, ".format(bolus_names) \
                   + "but not applied to beams in beamset {}".format(pd.beamset.DicomPlanLabel)
        try:
            applied_boli = set([bolus.Name for b in pd.beamset.Beams for bolus in b.Boli])
            if any(bn in applied_boli for bn in bolus_names):
                bolus_matches = {bn: [] for bn in bolus_names}
                for ab in applied_boli:
                    bolus_matches[ab].extend([b.Name for b in pd.beamset.Beams
                                              for bolus in b.Boli
                                              if bolus.Name == ab])
                pass_result = "Pass"
                message_str = "".join(
                    ['Roi {0} applied on beams {1}'.format(k, v) for k, v in bolus_matches.items()])
            else:
                pass_result = "Fail"
                message_str = fail_str
        except AttributeError:
            pass_result = "Fail"
            message_str = fail_str
    else:
        message_str = "No rois including {} found for Exam {}".format(BOLUS_NAMES, exam_name)
        pass_result = "Pass"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


# TODO: Add test on currently commissioned beams for timestamp
# DOSE CHECKS
def check_fraction_size(bs, parent_key):
    """
    Check the fraction size for common errors
    Args:
        bs: Raystation Beamset Object

    Returns:
        message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, Fraction_Size_Check
        Pass: Pelv_THI_R0A0
        Fail: Pelv_T3D_R0A0
    """
    child_key = 'Check Fractionation'
    results = {0: 'Fail', 1: 'Alert', 2: 'Pass'}
    num_fx = bs.FractionationPattern.NumberOfFractions
    pass_result = results[2]
    message_str = 'Beamset {} fractionation not flagged'.format(bs.DicomPlanLabel)
    rx_dose = None
    try:
        rx_dose = bs.Prescription.PrimaryDosePrescription.DoseValue
    except AttributeError:
        pass_result = results[1]
        message_str = 'No Prescription is Defined for Beamset'.format(bs.DicomPlanLabel)
    #
    # Look for matches in dose pairs
    if rx_dose:
        for t in DOSE_FRACTION_PAIRS:
            if t[0] == num_fx and t[1] == rx_dose:
                pass_result = results[1]
                message_str = 'Potential fraction/dose transcription error, ' \
                              + 'check with MD to confirm {} fractions should be delivered'.format(num_fx) \
                              + ' and dose per fraction {:.2f} Gy'.format(int(rx_dose / 100. / num_fx))
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_no_fly(pd, parent_key):
    """

    Args:
        pd:

    Returns:
    message (list str): [Pass_Status, Message String]

    Test Patient:
        PASS: Script_Testing, #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
        FAIL: Script_Testing, #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
    """
    child_key = "No Fly Zone Dose Check"
    try:
        no_fly_dose = pd.plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName=NO_FLY_NAME, DoseType='Max')
        if no_fly_dose > NO_FLY_DOSE:
            message_str = "{} is potentially infield. Dose = {:.2f} cGy (exceeding tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = "Fail"
        else:
            message_str = "{} is likely out of field. Dose = {:.2f} cGy (tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = "Pass"
    except Exception as e:
        if "exists no ROI" in e.Message:
            message_str = "No ROI {} found, Incline Board not used"
            pass_result = "Pass"
        else:
            message_str = "Unknown error in looking for incline board info {}".format(e.Message)
            pass_result = "Alert"

    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_dose_grid(pd, parent_key):
    """
    Based on plan name and dose per fraction, determines size of appropriate grid.
    Args:
        pd: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
        parent_key: parent_node

    Returns:
        message (list str): [Pass_Status, Message String]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    child_key = "Dose Grid Size Check"
    #
    # Get beamset dose grid
    rs_grid = pd.beamset.FractionDose.InDoseGrid.VoxelSize
    grid = (rs_grid.x, rs_grid.y, rs_grid.z)
    #
    # Try (if specified to get dose per fraction)
    try:
        total_dose = pd.beamset.Prescription.PrimaryDosePrescription.DoseValue
        num_fx = pd.beamset.FractionationPattern.NumberOfFractions
        fractional_dose = total_dose / float(num_fx)
    except AttributeError:
        num_fx = None
        fractional_dose = None
    #
    # Get beamset name is see if there is a match
    message_str = ""
    pass_result = None
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in pd.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            name_match = []
            for n in v['PLAN_NAMES']:
                if n in pd.beamset.DicomPlanLabel:
                    name_match.append(n)
            violation_list = [i for i in grid if i > v['DOSE_GRID']]
            if violation_list:
                message_str = "Dose grid too large for plan type {}. ".format(name_match) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Fail"
            else:
                message_str = "Dose grid appropriate for plan type {}. ".format(name_match) \
                              + "Grid size is {} cm  and ≤ {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Pass"
        # Look for fraction size violations
        elif v['FRACTION_SIZE_LIMIT']:
            if not fractional_dose:
                message_str = "Dose grid cannot be evaluated for this plan. No fractional dose"
                pass_result = 'Fail'
            elif fractional_dose >= v['FRACTION_SIZE_LIMIT'] and \
                    any([g > v['DOSE_GRID'] for g in grid]):
                message_str = "Dose grid may be too large for this plan based on fractional dose " \
                              + "{:.0f} > {:.0f} cGy. ".format(fractional_dose, v['FRACTION_SIZE_LIMIT']) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Fail"
    # Plan is a default plan. Just Check against defaults
    if not message_str:
        violation_list = [i for i in grid if i > DOSE_GRID_DEFAULT]
        if violation_list:
            message_str = "Dose grid too large. " \
                          + "Grid size is {} cm and should be {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = "Fail"
        else:
            message_str = "Dose grid appropriate." \
                          + "Grid size is {} cm  and ≤ {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = "Pass"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def check_slice_thickness(pd, parent_key):
    """
    Checks the current exam used in this case for appropriate slice thickness
    Args:
        pd: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
        parent_key: beamset parent key
    Returns:
        messages: [[str1, ...,],...]: [[parent_key, child_key, messgae display, Pass/Fail/Alert]]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    child_key = 'Slice thickness Comparison'
    message_str = ""
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in pd.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            nominal_slice_thickness = v['SLICE_THICKNESS']
            for s in pd.exam.Series:
                slice_positions = np.array(s.ImageStack.SlicePositions)
                slice_thickness = np.diff(slice_positions)
                if np.isclose(slice_thickness, nominal_slice_thickness).all() \
                        or all(slice_thickness < nominal_slice_thickness):
                    message_str = 'Slice spacing {:.3f} ≤ {:.3f} cm appropriate for plan type {}'.format(
                        slice_thickness.max(), nominal_slice_thickness, v['PLAN_NAMES'])
                    pass_result = "Pass"
                else:
                    message_str = 'Slice spacing {:.3f} > {:.3f} cm TOO LARGE for plan type {}'.format(
                        slice_thickness.max(), nominal_slice_thickness, v['PLAN_NAMES'])
                    pass_result = "Fail"
    if not message_str:
        for s in pd.exam.Series:
            slice_positions = np.array(s.ImageStack.SlicePositions)
            slice_thickness = np.diff(slice_positions)
        message_str = 'Plan type unknown, check slice spacing {:.3f} cm carefully'.format(
            slice_thickness.max())
        pass_result = "Alert"
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


def closed_leaf_gaps(banks, min_gap_moving):
    threshold = 1e-6
    leaf_gaps = np.empty_like(banks, dtype=bool)
    leaf_gaps[:, 0, :] = abs(banks[:, 0, :] - banks[:, 1, :]) < \
                         (1 + threshold) * min_gap_moving
    leaf_gaps[:, 1, :] = leaf_gaps[:, 0, :]
    return leaf_gaps


def get_segment_number(beam):
    # Get total number of segments in the beam
    try:
        seg_num = 0
        # Find the number of leaves in the first segment to initialize the array
        for s in beam.Segments:
            seg_num += 1
    except:
        return None
    return seg_num


def get_relative_weight(beam):
    # Get each segment weight
    weights = []
    for s in beam.Segments:
        weights.append(s.RelativeWeight)
    return weights


def get_mlc_bank_array(beam):
    # Find the number of segments
    segment_number = get_segment_number(beam)
    if not segment_number:
        return None
    else:
        s0 = beam.Segments[0]
    #
    # Get the number of leaves
    num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])
    # Bank array declaration
    banks = np.empty((num_leaves_per_bank, 2, segment_number))
    # Combine the segments into a single ndarray of size:
    # number of MLCs x number of banks x number of segments
    s_i = 0
    for s in beam.Segments:
        # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
        banks[:, 0, s_i] = s.LeafPositions[0]  # np.dstack((banks, bank))
        banks[:, 1, s_i] = s.LeafPositions[1]
        s_i += 1
    return banks


def filter_banks(beam, banks):
    # MLCs x number of banks x number of segments
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Min gap
    min_gap_moving = current_machine.Physics.MlcPhysics.MinGapMoving
    # Find all closed leaf gaps and zero them
    closed = closed_leaf_gaps(banks, min_gap_moving)
    # Filtered banks is dimension [N_MLC,Bank Index, Control Points]
    filtered_banks = np.copy(banks)
    filtered_banks[closed] = np.nan
    return filtered_banks


def compute_mcs(beam, override_square=False):
    # Step and Shoot
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    #
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    # Absolute value since the relative difference between leaves on the same
    # bank is used
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    weighted_lsv = np.sum(lsv * segment_weights)
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperture_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperture_area / np.sum(beam_ciao)
    weighted_aav = np.sum(aav * segment_weights)
    #
    # MCS calc
    mcsv = np.sum(lsv * aav * segment_weights)
    return weighted_lsv, weighted_aav, mcsv


def compute_mcs_masi(beam, override_square=False):
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    averaged_segment_weights = segment_weights[0:-1]  # Last control point is zero MU
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    vmat_lsv = (lsv[:-1] + lsv[1:]) / 2.
    weighted_vmat_lsv = np.sum(vmat_lsv * segment_weights[:-1])
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperature_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperature_area / np.sum(beam_ciao)
    vmat_aav = (aav[:-1] + aav[1:]) / 2.
    weighted_vmat_aav = np.sum(vmat_aav * segment_weights[:-1])
    #
    # MCS calc
    mcsv = np.sum(vmat_lsv * vmat_aav * averaged_segment_weights)
    return weighted_vmat_lsv, weighted_vmat_aav, mcsv


def get_machine(machine_name):
    """Finds the current machine name from the list of currently commissioned machines
    :param: machine_name (name of the machine in raystation,
    usually this is machine_name = beamset.MachineReference.MachineName
    return: machine (RS object)"""
    machine_db = connect.get_current("MachineDB")
    machine = machine_db.GetTreatmentMachine(machineName=machine_name, lockMode=None)
    return machine


def compute_beam_properties(pd, parent_key):
    # Compute MCS and any other desired beam properties
    child_key = "Beamset Complexity"
    message_str = "[Beam Name: LSV, AAV, MCS] :: "
    tech = pd.beamset.DeliveryTechnique
    pass_result = 'Pass'
    for b in pd.beamset.Beams:
        if tech == 'DynamicArc':
            lsv, aav, mcs = compute_mcs_masi(b)
        elif tech == 'SMLC':
            # TODO Review versus a non segmented case with big opening differences
            lsv, aav, mcs = compute_mcs(b)
        else:
            message_str = 'Error Unknown technique {}'.format(tech)
            break
        message_str += '[{}: '.format(b.Name)
        # LSV
        if lsv < MCS_TOLERANCES['LSV']['MEAN'] - 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} OVERMODULATED,'.format(lsv)
        elif lsv > MCS_TOLERANCES['LSV']['MEAN'] + 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} UNDERMODULATED,'.format(lsv)
        else:
            message_str += '{:.3f},'.format(lsv)
        # AAV
        if aav < MCS_TOLERANCES['AAV']['MEAN'] - 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} OVERMODULATED,'.format(aav)
        elif aav > MCS_TOLERANCES['AAV']['MEAN'] + 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} UNDERMODULATED,'.format(aav)
        else:
            message_str += '{:.3f},'.format(aav)
        # MCS
        if mcs < MCS_TOLERANCES['MCS']['MEAN'] - 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} OVERMODULATED,'.format(mcs)
        elif mcs > MCS_TOLERANCES['MCS']['MEAN'] + 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            pass_result = 'Fail'
            message_str += '{:.3f} UNDERMODULATED,'.format(mcs)
        else:
            message_str += '{:.3f}'.format(mcs)
        message_str += '],'
    messages = build_tree_element(parent_key=parent_key,
                                  child_key=child_key,
                                  pass_result=pass_result,
                                  message_str=message_str)
    return messages


#
#
# Get current user snippet
#    from System import Environment
#
#    from System.DirectoryServices import AccountManagement as am
#    staff_id = Environment.UserName
#    cx = am.PrincipalContext(am.ContextType.Domain)
#    principal = am.UserPrincipal.FindByIdentity(cx, 1, staff_id)

def check_plan():
    #
    try:
        user_name = str(Environment.UserName)
    except Exception as e:
        logging.debug('{}'.format(e))
        user_name = None

    treedata = sg.TreeData()

    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error=[],
            patient=GeneralOperations.find_scope(level='Patient'),
            case=GeneralOperations.find_scope(level='Case'),
            exam=GeneralOperations.find_scope(level='Examination'),
            db=GeneralOperations.find_scope(level='PatientDB'),
            plan=GeneralOperations.find_scope(level='Plan'),
            beamset=GeneralOperations.find_scope(level='BeamSet'))
    r = comment_to_clipboard(pd)
    #
    # Tree Levels
    patient_key = ("pt", "Patient: " + pd.patient.PatientID)
    exam_key = ("e", "Exam: " + pd.exam.Name)
    plan_key = ("p", "Plan: " + pd.plan.Name)
    beamset_key = ("b", "Beam Set: " + pd.beamset.DicomPlanLabel)
    rx_key = ("rx", "Prescription")
    log_key = ("log", "Logging")

    """
    patient_key
        |
         -- Patient Checks
        |
         -- exam_key
                |
                 -- DICOM Checks
        |
         -- structure_key
                |
                 -- Structure Checks
         -- plan_key
                |
                 -- Plan Checks
                 -- beamset_key
                           |
                            -- Beamset Checks
        |
         -- Logs                    
    """
    #
    # Patient check activations
    check_patient_logs = True if pd.patient else False
    check_dicom = True if pd.patient else False
    #
    # Exam check activations
    check_exam_date = True if pd.exam else False
    check_overlap = True if pd.exam else False
    target_extent = get_si_extent(pd, types=['Ptv']) if pd.exam else None
    check_target_extent = True if pd.exam else False
    check_couch_extent = True if pd.exam else False
    check_bb = True if pd.exam else False
    check_rot = True if pd.exam else False
    #
    # Beamset level activations
    check_fx_size = True if pd.beamset else False
    check_bolus_structures = True if pd.beamset else False
    check_iso = True if pd.beamset else False
    check_approval = True if pd.beamset else False
    check_nofly_dose = True if pd.beamset else False
    check_grid = True if pd.beamset else False
    check_st = True if pd.beamset else False
    check_couch_name = True if pd.beamset else False
    # Analyze checks needed by technique
    #
    # Plan check for VMAT
    #
    technique = pd.beamset.DeliveryTechnique if pd.beamset else None
    check_cps = True if technique == 'DynamicArc' else False
    if technique == 'DynamicArc':
        check_tomo_trnsfr_apprvd = False
        check_tomo_iso = False
        if pd.beamset.Beams[0].HasValidSegments:
            check_beam_properties = True
        else:
            check_beam_properties = False
    elif technique == 'SMLC':
        check_tomo_trnsfr_apprvd = False
        check_tomo_iso = False
        try:
            pd.beamset.Beams[0].Segments[0]
            check_beam_properties = True
        except Exception as e:
            logging.debug('Cannot check beamsets yet {}'.format(str(e)))
            check_beam_properties = False
    elif 'Tomo' in technique:
        check_beam_properties = False
        check_tomo_iso = True
        try:
            pd.beamset.Beams[0].Segments[0]
            check_tomo_trnsfr_apprvd = True
        except Exception as e:
            logging.debug('Cannot check beamsets yet {}'.format(str(e)))
            check_tomo_trnsfr_apprvd = False
    else:
        check_beam_properties = False
        check_tomo_trnsfr_apprvd = False
        check_tomo_iso = False
    # Plan check for SMLC
    check_edw = True if technique == 'SMLC' else False

    treedata.Insert("", patient_key[0], patient_key[1], "")
    """
    Patient Level Checks
    """
    #
    # Patient level checks
    exam_level_tests = []
    if check_dicom:
        message_dicom = check_exam_data(pd, parent_key=exam_key[0])
        exam_level_tests.extend(message_dicom)
    #
    # Check date for tolerance
    if check_exam_date:
        message_exam = compare_exam_date(pd, parent_key=exam_key[0])
        exam_level_tests.extend(message_exam)
    if check_target_extent:
        message_image_length = image_extent_sufficient(pd=pd, parent_key=exam_key[0], target_extent=target_extent)
        exam_level_tests.extend(message_image_length)
    if check_couch_extent:
        message_couch_length = couch_extent_sufficient(pd=pd, parent_key=exam_key[0], target_extent=target_extent)
        exam_level_tests.extend(message_couch_length)
    if check_overlap:
        message_fov = external_overlaps_fov(pd=pd, parent_key=exam_key[0], target_extent=target_extent)
        exam_level_tests.extend(message_fov)
    if check_bb:
        message_bb = check_localization(pd=pd, parent_key=exam_key[0])
        exam_level_tests.extend(message_bb)
    if check_rot:
        message_rot = match_image_directions(pd=pd, parent_key=exam_key[0])
        exam_level_tests.extend(message_rot)
    # Exam tests complete. Update value
    exam_level_pass = "Pass"
    exam_icon = GREEN_CIRCLE
    if any([m[3] for m in exam_level_tests if m[3] == "Fail"]):
        exam_level_pass = "Fail"
        exam_icon = RED_CIRCLE
    elif any([m[3] for m in exam_level_tests if m[3] == "Alert"]):
        exam_level_pass = "Alert"
        exam_icon = BLUE_CIRCLE
    treedata.Insert(patient_key[0], exam_key[0], exam_key[1], exam_level_pass, icon=exam_icon)
    if exam_level_tests:
        for m in exam_level_tests:
            treedata.Insert(m[0], m[1], m[2], [m[3]], icon=m[4])  # Note the list of the last entry. Can this be of use?
    """
    Plan Level Checks
    """
    # Plan LevelChecks
    plan_level_tests = []
    if check_approval:
        message_pln_approved = check_plan_approved(pd, parent_key=plan_key[0])
        plan_level_tests.extend(message_pln_approved)

    # Insert Plan Level notes
    plan_level_pass = "Pass"
    plan_icon = GREEN_CIRCLE
    if any([m[3] for m in plan_level_tests if m[3] == "Fail"]):
        plan_level_pass = "Fail"
        plan_icon = RED_CIRCLE
    elif any([m[3] for m in plan_level_tests if m[3] == "Alert"]):
        plan_level_pass = "Alert"
        plan_icon = BLUE_CIRCLE
    treedata.Insert(patient_key[0], plan_key[0], plan_key[1], plan_level_pass, icon=plan_icon)
    if plan_level_tests:
        for m in plan_level_tests:
            treedata.Insert(m[0], m[1], m[2], [m[3]], icon=m[4])  # Note the list of the last entry. Can this be of use?

    #
    # BEAMSET LEVEL CHECKS
    beamset_level_tests = []
    # Check if beamset is approved
    if check_approval:
        message_bs_approved = check_beamset_approved(pd=pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_bs_approved)
    #
    # Look for common isocenter
    if check_iso:
        message_iso = check_common_isocenter(pd.beamset, parent_key=beamset_key[0], tolerance=1e-15)
        beamset_level_tests.extend(message_iso)
    #
    # Check control point spacing
    if check_cps:
        message_cps = check_control_point_spacing(pd.beamset, expected=2., parent_key=beamset_key[0])
        beamset_level_tests.extend(message_cps)
    #
    # Fx size checks
    if check_fx_size:
        message_fx_size = check_fraction_size(pd.beamset, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_fx_size)
    #
    # Slice thickness checks
    if check_st:
        message_st = check_slice_thickness(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_st)
    #
    # EDW Check
    if check_edw:
        message_edw = check_edw_MU(pd.beamset, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_edw)
    #
    # Bolus checks
    if check_bolus_structures:
        message_bolus = check_bolus_included(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_bolus)
    #
    # Check No Fly Zone
    if check_nofly_dose:
        message_nofly = check_no_fly(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_nofly)
    #
    # Check Dose Grid
    if check_grid:
        message_grid = check_dose_grid(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_grid)
    if check_beam_properties:
        message_beam_properties = compute_beam_properties(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_beam_properties)
    if check_tomo_trnsfr_apprvd:
        message_tfr_approved = check_transfer_approved(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_tfr_approved)
    #
    # Look for too lateral isocenter
    if check_tomo_iso:
        message_iso = check_tomo_isocenter(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_iso)
    if check_couch_name:
        message_couch_name = couch_type_correct(pd, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_couch_name)

    #
    # Insert Beamset Level Nodes
    beamset_level_pass = "Pass"
    beamset_icon = GREEN_CIRCLE
    if any([m[3] for m in beamset_level_tests if m[3] == "Fail"]):
        beamset_level_pass = "Fail"
        beamset_icon = RED_CIRCLE
    elif any([m[3] for m in beamset_level_tests if m[3] == "Alert"]):
        beamset_level_pass = "Alert"
        beamset_icon = BLUE_CIRCLE
    treedata.Insert(patient_key[0], beamset_key[0], beamset_key[1], beamset_level_pass, icon=beamset_icon)
    if beamset_level_tests:
        for m in beamset_level_tests:
            treedata.Insert(m[0], m[1], m[2], [m[3]], icon=m[4])  # Note the list of the last entry. Can this be of use?
    #
    # Log Level
    treedata.Insert(patient_key[0], log_key[0], log_key[1], "")
    if check_patient_logs:
        lines = read_log_file(patient_id=pd.patient.PatientID)
        message_logs = parse_log_file(lines=lines, parent_key=log_key[0], phrases=KEEP_PHRASES)
        for m in message_logs:
            treedata.Insert(m[0], m[1], m[2], [m[3]])  # Note the list of the last entry. Can this be of use?

    # Gui
    # TODO is it possible to specify which columns are expanded by pass fail?
    sg.theme('Topanga')
    col_widths = [20]
    col1 = sg.Column([[sg.Frame('ReviewChecks:',
                                [[
                                    sg.Tree(
                                        data=treedata,
                                        headings=['Checks', ],
                                        auto_size_columns=False,
                                        num_rows=40,
                                        col0_width=120,
                                        col_widths=col_widths,
                                        key='-TREE-',
                                        show_expanded=False,
                                        justification="left",
                                        enable_events=True),
                                ], [sg.Button('Ok'), sg.Button('Cancel')]])]], pad=(0, 0))
    layout = [[col1]]

    window = sg.Window('Plan Review: ' + user_name, layout)

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
    window.close()
    r.destroy()


def main():
    check_plan()


if __name__ == '__main__':
    main()
