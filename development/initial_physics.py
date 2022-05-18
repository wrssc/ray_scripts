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
import datetime
import sys
import os
import logging
from math import isclose
from collections import namedtuple, OrderedDict
from System import Environment
import PySimpleGUI as sg
import re
from dateutil import parser

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
        'PLAN_NAMES': ['SBR', 'FSR'],
        'DOSE_GRID': 0.15,  # 1.5 mm
        'FRACTION_SIZE_LIMIT': 801,  # cGy
        'SLICE_THICKNESS': 0.1,  # 1.0 mm
    },
    'SRS': {
        'PLAN_NAMES': ['SRS'],
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
}


# TBI


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
    try:
        p_date1 = parser.parse(date1).date()
        p_date2 = parser.parse(date2).date()
        if p_date1 == p_date2:
            return True, date1, date2
        else:
            return False, date1, date2
    except TypeError:
        return False, None, None
    except parser.ParserError:
        return False, None, None


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
    # Match M/Male, F/Female, O/Other
    if gender1:
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


def check_exam_data(patient, exam, parent_key):
    """

    Args:
        patient:
        exam:
        parent_key:

    Returns:
        messages: [[str1, ...,],...]: [[parent_key, child_key, messgae display, Pass/Fail/Alert]]
    """

    child_key = 'DICOM Raystation Comparison'
    modality_tag = (0x0008, 0x0060)
    tags = {str(patient.Name): (0x0010, 0x0010, match_patient_name),
            str(patient.PatientID): (0x0010, 0x0020, match_exactly),
            str(patient.Gender): (0x0010, 0x0040, match_gender),
            str(patient.DateOfBirth): (0x0010, 0x0030, match_date)
            }
    messages = []
    get_rs_value = exam.GetStoredDicomTagValueForVerification
    modality = list(get_rs_value(Group=modality_tag[0],
                                 Element=modality_tag[1]).values())[0]  # Get Modality
    all_passing = True
    for k, v in tags.items():
        rs_tag = get_rs_value(Group=v[0], Element=v[1])
        for dicom_attr, dicom_val in rs_tag.items():
            match, rs, dcm = v[2](dicom_val, k)
            if match:
                match_str = 'matches '
                pass_msg = "Pass"
                icon = GREEN_CIRCLE
            else:
                all_passing = False
                match_str = 'FAILS to match '
                pass_msg = "Fail"
                icon = RED_CIRCLE
            message_str = "{0} of DICOM {1}: {2} {3}RS: {4}" \
                .format(dicom_attr, modality, dcm, match_str, rs)
            messages.append([child_key, dicom_attr, message_str, pass_msg, icon])
    if all_passing:
        messages.insert(0, [parent_key, child_key, child_key, "Pass", GREEN_CIRCLE])
    else:
        messages.insert(0, [parent_key, child_key, child_key, "Fail", RED_CIRCLE])
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


def check_plan_approved(plan, beamset, parent_key):
    """
    Check if a plan is approved
    Args:
        parent_key: parent position in the tree of this child
        plan: RS plan object
        beamset: RS beamset object


    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]

    """
    messages = []
    child_key = "Plan approval status"
    approval_status = approval_info(plan, beamset)
    if approval_status.plan_approved:
        message_str = "Plan: {} was approved by {} on {}".format(
            plan.Name,
            approval_status.plan_reviewer,
            approval_status.plan_approval_time
        )
        pass_result = "Pass"
        icon = GREEN_CIRCLE
    else:
        message_str = "Plan: {} is not approved".format(
            plan.Name)
        pass_result = "Fail"
        icon = RED_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
    return messages


def check_beamset_approved(pd, parent_key):
    """
    Check if a plan is approved
    Args:
        parent_key: parent position in the tree of this child
        pd: (NamedTuple Containing beamset and plan RS objects)

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]
    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA

    """
    messages = []
    child_key = "Beamset approval status"
    approval_status = approval_info(pd.plan, pd.beamset)
    if approval_status.beamset_approved:
        message_str = "Beamset: {} was approved by {} on {}".format(
            pd.beamset.DicomPlanLabel,
            approval_status.beamset_reviewer,
            approval_status.beamset_approval_time
        )
        pass_result = "Pass"
        icon = GREEN_CIRCLE
    else:
        message_str = "Beamset: {} is not approved".format(
            pd.beamset.DicomPlanLabel)
        pass_result = "Fail"
        icon = RED_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
    return messages


def compare_exam_date(exam, plan, beamset, tolerance, parent_key):
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
    child_key = "Exam date is recent"
    dcm_data = list(exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020).values())
    messages = []
    approval_status = approval_info(plan, beamset)
    if dcm_data:
        dcm_date = parser.parse(dcm_data[0])
        #
        if approval_status.beamset_approved:
            current_time = parser.parse(str(beamset.Review.ReviewTime))
        else:
            try:
                # Use last saved date if plan not approved
                current_time = parser.parse(str(beamset.ModificationInfo.ModificationTime))
            except AttributeError:
                current_time = datetime.datetime.now()

        elapsed_days = (current_time - dcm_date).days

        if elapsed_days <= tolerance:
            message_str = "Exam {} acquired {} within {} days ({} days) of Plan Date {}" \
                .format(exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Pass"
            icon = GREEN_CIRCLE
        else:
            message_str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Fail"
            icon = RED_CIRCLE
    else:
        message_str = "Exam {} has no apparent study date!".format(exam.Name)
        pass_result = "Alert"
        icon = BLUE_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
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
        exp_r_n = r_n
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
            icon = RED_CIRCLE
    else:
        message_str = "No control points > {} detected".format(spacing)
        message_result = "Pass"
        icon = GREEN_CIRCLE
    return message_str, message_result, icon


def check_control_point_spacing(bs, expected, parent_key):
    """
    bs: RayStation beamset
    expected: Integer delineating the gantry angle between control points in a beam
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    """
    child_key = 'Control Point Spacing'
    beam_result = {}
    messages = []
    for b in bs.Beams:
        s0 = None
        fails = []
        for s in b.Segments:
            if not pass_control_point_spacing(s, s0, spacing=expected):
                fails.append(s.SegmentNumber + 1)
            s0 = s
        if fails:
            beam_result[b.Name] = fails
    message_str, pass_result, icon = message_format_control_point_spacing(beam_spacing_failures=beam_result,
                                                                          spacing=expected)
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])

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
    messages = []
    edws = {}
    for b in beamset.Beams:
        if b.Wedge:
            if 'EDW' in b.Wedge.WedgeID:
                edws[b.Name] = b.BeamMU
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
        icon = GREEN_CIRCLE
        message_str = edw_message
    else:
        pass_result = "Fail"
        icon = RED_CIRCLE
        message_str = edw_message
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
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
    messages = []
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
        icon = RED_CIRCLE
    else:
        pass_result = "Pass"
        message_str = "Beam(s) {} all share the same isocenter to within {} mm".format(iso_match, tolerance)
        icon = GREEN_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
    return messages


def check_bolus_included(case, beamset, parent_key):
    """

    Args:
        case: RS Case Object
        beamset:  RS Beamset Object
        parent_key: str: the key under which this test is performed in the treedata

    Returns:
        message: list of lists of format: [parent key, key, value, result]
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, ChwL
        Pass: Bolus_Roi_Check_Pass: ChwL_VMA_R1A0
        Fail: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    child_key = "Bolus Application"
    messages = []
    exam_name = beamset.PatientSetup.LocalizationPoiGeometrySource.OnExamination.Name
    roi_list = get_roi_list(case, exam_name=exam_name)
    bolus_names = match_roi_name(roi_names=BOLUS_NAMES, roi_list=roi_list)
    if bolus_names:
        fail_str = "Stucture(s) {} named bolus, ".format(bolus_names) \
                   + "but not applied to beams in beamset {}".format(beamset.DicomPlanLabel)
        try:
            applied_boli = set([bolus.Name for b in beamset.Beams for bolus in b.Boli])
            if any(bn in applied_boli for bn in bolus_names):
                bolus_matches = {bn: [] for bn in bolus_names}
                for ab in applied_boli:
                    bolus_matches[ab].extend([b.Name for b in beamset.Beams
                                              for bolus in b.Boli
                                              if bolus.Name == ab])
                pass_result = "Pass"
                icon = GREEN_CIRCLE
                message_str = "".join(
                    ['Roi {0} applied on beams {1}'.format(k, v) for k, v in bolus_matches.items()])
            else:
                pass_result = "Fail"
                icon = RED_CIRCLE
                message_str = fail_str
        except AttributeError:
            pass_result = "Fail"
            icon = RED_CIRCLE
            message_str = fail_str
    else:
        message_str = "No rois including {} found for Exam {}".format(BOLUS_NAMES, exam_name)
        pass_result = "Pass"
        icon = GREEN_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
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
    messages = []
    results = {0: 'Fail', 1: 'Alert', 2: 'Pass'}
    num_fx = bs.FractionationPattern.NumberOfFractions
    pass_result = results[2]
    icon = GREEN_CIRCLE
    message_str = 'Beamset {} fractionation not flagged'.format(bs.DicomPlanLabel)
    rx_dose = None
    try:
        rx_dose = bs.Prescription.PrimaryDosePrescription.DoseValue
    except AttributeError:
        pass_result = results[1]
        icon = BLUE_CIRCLE
        message_str = 'No Prescription is Defined for Beamset'.format(bs.DicomPlanLabel)
    #
    # Look for matches in dose pairs
    if rx_dose:
        for t in DOSE_FRACTION_PAIRS:
            if t[0] == num_fx and t[1] == rx_dose:
                pass_result = results[1]
                icon = BLUE_CIRCLE
                message_str = 'Potential fraction/dose transcription error, ' \
                              + 'check with MD to confirm {} fractions should be delivered'.format(num_fx) \
                              + ' and dose per fraction {:.2f} Gy'.format(int(rx_dose / 100. / num_fx))
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
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
    messages = []
    child_key = "No Fly Zone Dose Check"
    try:
        no_fly_dose = pd.plan.TreatmentCourse.TotalDose.GetDoseStatistic(RoiName=NO_FLY_NAME, DoseType='Max')
        if no_fly_dose > NO_FLY_DOSE:
            message_str = "{} is potentially infield. Dose = {:.2f} cGy (exceeding tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = "Fail"
            icon = RED_CIRCLE
        else:
            message_str = "{} is likely out of field. Dose = {:.2f} cGy (tolerance {:.2f} cGy)".format(
                NO_FLY_NAME, no_fly_dose, NO_FLY_DOSE)
            pass_result = "Pass"
            icon = GREEN_CIRCLE
    except Exception as e:
        if "exists no ROI" in e.Message:
            message_str = "No ROI {} found, Incline Board not used"
            pass_result = "Pass"
            icon = GREEN_CIRCLE
        else:
            message_str = "Unknown error in looking for incline board info {}".format(e.Message)
            pass_result = "Alert"
            icon = BLUE_CIRCLE

    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
    return messages


def check_dose_grid(pd, parent_key):
    """
    Based on plan name and dose per fraction, determines size of appropriate grid.
    Args:
        pd: NamedTuple with a beamset
        parent_key: parent_node

    Returns:
        message (list str): [Pass_Status, Message String]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    messages = []
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
    icon = None
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in pd.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            violation_list = [i for i in grid if i > v['DOSE_GRID']]
            if violation_list:
                message_str = "Dose grid too large for plan type {}. ".format(v['PLAN_NAMES']) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Fail"
                icon = RED_CIRCLE
            else:
                message_str = "Dose grid appropriate for plan type {}. ".format(v['PLAN_NAMES']) \
                              + "Grid size is {} cm  and ≤ {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Pass"
                icon = GREEN_CIRCLE
        # Look for fraction size violations
        elif v['FRACTION_SIZE_LIMIT']:
            if fractional_dose >= v['FRACTION_SIZE_LIMIT']:
                message_str = "Dose grid may be too large for this plan based on fractional dose " \
                              + "{:.0f} > {:.0f} cGy. ".format(fractional_dose, v['FRACTION_SIZE_LIMIT']) \
                              + "Grid size is {} cm and should be {} cm".format(grid, v['DOSE_GRID'])
                pass_result = "Fail"
                icon = RED_CIRCLE
    # Plan is a default plan. Just Check against defaults
    if not message_str:
        violation_list = [i for i in grid if i > DOSE_GRID_DEFAULT]
        if violation_list:
            message_str = "Dose grid too large. " \
                          + "Grid size is {} cm and should be {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = "Fail"
            icon = RED_CIRCLE
        else:
            message_str = "Dose grid appropriate." \
                          + "Grid size is {} cm  and ≤ {} cm".format(grid, DOSE_GRID_DEFAULT)
            pass_result = "Pass"
            icon = GREEN_CIRCLE
    messages.append([parent_key, child_key, child_key, pass_result, icon])
    messages.append([child_key, pass_result, message_str, pass_result, icon])
    return messages


# def check_plan_name(bs):
# Check plan name for appropriate
# Measure target length of prostate for pros

# def check_target_spacing(bs):
# Find all targets
# Put a box around them
# look at the gaps and if they exceed some threshold throw an alert

# def check_tomo_time(bs):
# Look at the plan type. Use the normal tomo mod factors
# Abdomen; 1.6 - 2.4
# Brain; 1.6 - 2.4
# Breast; 2.4 - 2.8
# Cranio - Spinal; 1.8 - 2.2
# Extremity; 2.0 - 2.4
# Gyn; 1.8 - 2.4
# H & N; 2.2 - 2.6
# Lung(non - SBRT); 2.4 - 2.8
# Lung(SBRT); 1.2 - 1.4
# Pelvis; 1.8 - 2.4
# Prostate(low; risk)    1.6 - 2.2
# Prostate(high; risk)    2.0 - 2.4
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
    #
    try:
        user_name = str(Environment.UserName)
    except:
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
    # Analyze checks needed by technique
    #
    # Plan check for VMAT
    #
    if pd.beamset.DeliveryTechnique == "DynamicArc":
        check_cps = True
    else:
        check_cps = False
    # TODO: Move these based on the status of the get current operations above
    check_fx_size = True
    check_patient_logs = True
    check_bolus_structures = True
    check_iso = True
    check_edw = True
    check_dicom = True
    check_exam_date = True
    check_approval = True
    check_nofly_dose = True
    check_grid = True

    treedata.Insert("", patient_key[0], patient_key[1], "")
    """
    Patient Level Checks
    """
    #
    # Patient level checks
    exam_level_tests = []
    if check_dicom:
        message_dicom = check_exam_data(pd.patient, pd.exam, parent_key=exam_key[0])
        exam_level_tests.extend(message_dicom)
    #
    # Check date for tolerance
    if check_exam_date:
        message_exam = compare_exam_date(beamset=pd.beamset, plan=pd.plan,
                                         exam=pd.exam, tolerance=DAYS_SINCE_SIM,
                                         parent_key=exam_key[0])
        exam_level_tests.extend(message_exam)
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
        message_pln_approved = check_plan_approved(plan=pd.plan, beamset=pd.beamset, parent_key=plan_key[0])
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
    # EDW Check
    if check_edw:
        message_edw = check_edw_MU(pd.beamset, parent_key=beamset_key[0])
        beamset_level_tests.extend(message_edw)
    #
    # Bolus checks
    if check_bolus_structures:
        message_bolus = check_bolus_included(case=pd.case,
                                             beamset=pd.beamset, parent_key=beamset_key[0])
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
    treedata.Insert(plan_key[0], beamset_key[0], beamset_key[1], beamset_level_pass, icon=beamset_icon)
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
    layout = [
        [sg.Tree(
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
        ],
        [sg.Button('Ok'), sg.Button('Cancel')]
    ]

    window = sg.Window('Plan Review' + user_name, layout)

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        print(event, values)
    window.close()


def main():
    check_plan()


if __name__ == '__main__':
    main()
