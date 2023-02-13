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
__date__ = '2022-Aug-03'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__credits__ = ['']

"""

 TODO: Check Beamsets for same machine

 TODO: Check for same iso, and same number of fractions in
   different beamsets, and flag for merge

 TODO:
   Check bad regions of Frame

 TODO:
   def check_plan_name(bs):
     Check plan name for appropriate
     Measure target length of prostate for pros

 TODO: Look for big gaps between targets
   def check_target_spacing(bs):
     Find all targets
     Put a box around them
     look at the gaps and if they exceed some threshold throw an alert

 TODO: If beamsets are approved
    Check the Entrance/Exit is blocked on some things
    Check that treat settings are used/appropriate
    
 TODO: Tomo Time Check
   def check_tomo_time(bs):
     Look at the plan type. Use the normal tomo mod factors
     Abdomen; 1.6 - 2.4
     Brain; 1.6 - 2.4
     Breast; 2.4 - 2.8
     Cranio - Spinal; 1.8 - 2.2
     Extremity; 2.0 - 2.4
     Gyn; 1.8 - 2.4
     H & N; 2.2 - 2.6
     Lung(non - SBRT); 2.4 - 2.8
     Lung(SBRT); 1.2 - 1.4
     Pelvis; 1.8 - 2.4
     Prostate(low; risk)    1.6 - 2.2
     Prostate(high; risk)    2.0 - 2.4


 TODO: Check collisions
   put a circle down at isocenter equal in dimension to ganty (collimator pin)/bore clearance
   union patient/supports
   determine gantry positions

 TODO:
   def - check the front edges of the couch and suspended headboard

 TODO:
   Flag all ROIs not made in MIM with goals

 TODO: Stray voxel check/

 TODO: Check clinical goal
   if a clinical goal is not met, look at the objective list to see if it is constrained
   
 TODO: Add test on currently commissioned beams for timestamp


"""
import sys
import os
import logging
import PySimpleGUI as sg
import re
import tkinter as Tk
from collections import namedtuple, OrderedDict
from System import Environment
from datetime import datetime

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../library'))
sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../library/PlanReview'))
import ExamTests
import BeamSetReviewTests
import PlanReviewTests
from ReviewDefinitions import *
import GeneralOperations


def comment_to_clipboard(rso):
    #
    # Clear the system clipboard
    r = Tk.Tk()
    r.withdraw()
    r.clipboard_clear()

    #
    # Add data to the beamset comment
    approval_status = BeamSetReviewTests.approval_info(rso.plan, rso.beamset)
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
    re_b = r'(Beamset: [^\t|\s]+)'  # Terminate after this level
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
                            lev_key, lev_val = re.split(': ', g, maxsplit=1)
                            levels[lev_key] = lev_val
                        parsed_l[1] = re.sub(exp, '', parsed_l[1])
                        parsed_l[0] += ' ' + deepest_level + ': ' + levels[deepest_level]
                        break
                if not deepest_level:
                    parsed_l[1] = re.sub(r'\t', '', parsed_l[1])
                message.append([key, parsed_l[0], parsed_l[0], parsed_l[1]])
    return message


def parse_treatment_planning_order_selection(beamset_name, messages, dialog_key):
    """
    Using the beamset name and the log file, use regex to find a phrase identifying the
    template name used in the treatment planning order for this beamset.
    Args:
        beamset_name: <str> name of current beamset
        messages: [ <str> ]: list of strings
        dialog_key: key to be used for top level entry in the tree

    Returns:

    TODO: Take a reg-exp as a list for input for matching a dialog and for each desired phrase
          loop over the phrases for a match
    TODO: Add the target matching that takes place for this step with consideration of the
          pre-logcrit syntax and post-logcrit syntax


    """
    # Parse the dialogs for specific key phrases related to the beamset dialog
    beamset_template_searches = {'Dialog': re.compile(
        r'(Treatment Planning Order selected:\s?)(.*)$')}
    template_data = {dialog_key: (ALERT,
                                  f'Treatment Planning for Beamset {beamset_name} goals manually defined')}
    for m in messages:
        template_search = re.search(beamset_template_searches['Dialog'], m[3])
        if template_search and beamset_name in m[1]:
            # Found the TPO Dialog. Lets display it
            # Note that it is a little sloppy, since this will always grab the last match in the log file
            k, template_name = template_search.groups()
            template_data[dialog_key] = (None, template_name)
    return template_data


def parse_beamset_selection(beamset_name, messages, dialog_key):
    # Go in here and if the message line matches the beamset_name
    # then return all the choices in this dialog as a list of tuples

    # Parse the dialogs for specific key phrases related to the beamset dialog
    beamset_template_searches = {'Dialog': re.compile(r'(Dialog):\s?(Beamset Template Selection)'),
                                 'Name': re.compile(r'(TemplateName):\s?(.*)Iso'),
                                 'NameAlt': re.compile(r'(TemplateName):\s?([^\t]+)'),
                                 'Isocenter': re.compile(r'(Iso):\s?([^\t]+)'),
                                 'Energy': re.compile(r'(Energy):\s?([^\t]+)')}
    # Find all the message lines that relate to a beamset dialog
    dialog_key = 'Beamset Template Selection'
    template_data = {dialog_key: (ALERT, 'Beamset {} not set by script'.format(beamset_name))}
    # loop over all lines in the template
    for m in messages:
        if re.search(beamset_template_searches['Dialog'], m[3]) and beamset_name in m[1]:
            # This is a beamset dialog: add it to the beamset listings
            # Get the template name
            try:
                k, template_name = re.search(beamset_template_searches['Name'], m[3]).groups()
            except AttributeError:
                k, template_name = re.search(beamset_template_searches['NameAlt'], m[3]).groups()
            # Get the isocenter information
            k, iso_info = re.search(beamset_template_searches['Isocenter'], m[3]).groups()
            k, energy = re.search(beamset_template_searches['Energy'], m[3]).groups()
            template_data[dialog_key] = (None, m[1])
            template_data['Template Name'] = (None, template_name)
            # TODO: Replace with a parse on bracketed entries return placement method
            template_data['Isocenter'] = (None, iso_info)
            template_data['Energy'] = (None, energy)
    return template_data


def build_tree_element(parent_key, child_key, pass_result, message_str):
    """
    Build the element for the output message to be inserted in the tree
    Args:
        parent_key: <str> parent node
        child_key:  <str> child node (current)
        pass_result: <str> "Pass", "Fail", "Alert", ""
        message_str: <str> User message

    Returns:
        node for insertion: <list>
        [ [parent node, child node, child node (placeholder for expension), pass result, icon],\
          [child key, pass result, message_str, pass result, icon] ]
    """
    elements = []
    if pass_result == FAIL:
        icon = RED_CIRCLE
    elif pass_result == PASS:
        icon = GREEN_CIRCLE
    elif pass_result == ALERT:
        icon = YELLOW_CIRCLE
    else:
        icon = BLUE_CIRCLE
    elements.append([parent_key, child_key, child_key, pass_result, icon])
    elements.append([child_key, parent_key + '.' + child_key, message_str, pass_result, icon])
    return elements


def build_document_row(child_key, pass_result, message_str, comment=None):
    """
    Build a single row of the
    :param child_key:
    :param pass_result:
    :param message_str:
    :param comment:
    :return: a list containing the elements for the document
    [icon, child_key, message_str, comment]
    """
    elements = []
    if pass_result == FAIL:
        icon = RED_CIRCLE
    elif pass_result == PASS:
        icon = GREEN_CIRCLE
    elif pass_result == ALERT:
        icon = YELLOW_CIRCLE
    else:
        icon = BLUE_CIRCLE
    if type(message_str) is list and len(message_str) == 2:
        elements.append([message_str[1][4], message_str[1][0], message_str[1][2], comment])
    else:
        elements.append([icon, child_key, message_str, comment])
    return elements


def parse_level_tests(level_tests):
    # Insert Level Nodes
    pass_str = PASS
    level_pass = pass_str
    icon = GREEN_CIRCLE
    if any([l[3] for l in level_tests if l[3] == FAIL]):
        level_pass = FAIL
        icon = RED_CIRCLE
    elif any([l[3] for l in level_tests if l[3] == ALERT]):
        level_pass = ALERT
        icon = YELLOW_CIRCLE
    return level_pass, icon


def insert_tests_return_fails(level_tests, treedata, fails):
    if level_tests:
        for m in level_tests:
            treedata.Insert(m[0], m[1], m[2], [m[3], ""], icon=m[4])  # Consider adding Comment field in list
            if m[1] == FAIL or m[1] == ALERT:
                fails.append(f"TEST: {m[0]}: {m[1]}: {m[2]}")
        return True
    else:
        return False


def get_exam_level_tests(rso):
    #
    # Get target length
    target_extent = ExamTests.get_si_extent(rso, types=['Ptv'])
    patient_checks_dict = {
        "DICOM RayStation Comparison":
            (ExamTests.check_exam_data, {}),
        "Exam Date Is Recent":
            (ExamTests.compare_exam_date, {}),
        "Localization Point Exists":
            (ExamTests.check_localization, {}),
        "Contours are interpolated":
            (ExamTests.check_contour_gaps, {}),
        "Image Is Axially Oriented":
            (ExamTests.match_image_directions, {}),
    }
    # TODO: If the target extent is NONE, then we ought to try and get one from dose
    if target_extent:
        patient_checks_dict.update({
            "Image extent sufficient":
                (ExamTests.image_extent_sufficient, {'TARGET_EXTENT': target_extent}),
            "Couch extent sufficient":
                (ExamTests.couch_extent_sufficient, {'TARGET_EXTENT': target_extent}),
            "Edge of scan overlaps patient at key slices":
                (ExamTests.external_overlaps_fov, {'TARGET_EXTENT': target_extent}),
        })
    return patient_checks_dict


def get_plan_level_tests(rso, physics_review=True):
    plan_checks_dict = {
        "Plan approval status":
            (PlanReviewTests.check_plan_approved, {"physics_review": physics_review})
    }
    return plan_checks_dict


def get_beamset_level_tests(rso, physics_review=True):
    beamset_checks_dict = {
        "Beamset approval status":
            (BeamSetReviewTests.check_beamset_approved, {"physics_review": physics_review}),
        "Isocenter Position Identical":
            (BeamSetReviewTests.check_common_isocenter, {"tolerance": 1e-15}),
        "Check Fractionation":
            (BeamSetReviewTests.check_fraction_size, {}),
        "Slice Thickness Comparison":
            (BeamSetReviewTests.check_slice_thickness, {}),
        "Bolus Application":
            (BeamSetReviewTests.check_bolus_included, {}),
        "No Fly Zone Dose Check":
            (BeamSetReviewTests.check_no_fly, {}),
        "Check for pacemaker compliance":
            (BeamSetReviewTests.check_pacemaker, {}),
        "Dose Grid Size Check":
            (BeamSetReviewTests.check_dose_grid, {}),
        "Planning Risk Volume Assessment":
            (BeamSetReviewTests.check_prv_status, {}),
        "Couch Zero Full Rotation Clearance Check":
            (BeamSetReviewTests.check_isocenter_clearance, {}),
    }

    # Plan check for VMAT
    #
    technique = rso.beamset.DeliveryTechnique if rso.beamset else None
    if technique == 'DynamicArc':
        if rso.beamset.Beams[0].HasValidSegments:
            beamset_checks_dict["Control Point Spacing"] = (
                BeamSetReviewTests.check_control_point_spacing, {'expected': 2.})
            beamset_checks_dict["Beamset Complexity"] = (BeamSetReviewTests.compute_beam_properties, {})
    elif technique == 'SMLC':
        try:
            rso.beamset.Beams[0].Segments[0]  # Determine if beams have segments
            beamset_checks_dict["Beamset Complexity"] = (BeamSetReviewTests.compute_beam_properties, {})
            beamset_checks_dict["EDW MU Check"] = (BeamSetReviewTests.check_edw_MU, {})
            beamset_checks_dict["EDW FieldSize Check"] = (BeamSetReviewTests.check_edw_field_size, {})
        except Exception as e:
            logging.debug('Cannot check beamsets yet {}'.format(str(e)))
    elif 'Tomo' in technique:
        try:
            rso.beamset.Beams[0].Segments[0]  # Determine if beams have segments
            beamset_checks_dict["Isocenter Lateral Acceptable"] = (BeamSetReviewTests.check_tomo_isocenter, {})
            beamset_checks_dict["Modulation Factor Acceptable"] = (BeamSetReviewTests.check_mod_factor, {})
            beamset_checks_dict["Transfer BeamSet Approval Status"] = (BeamSetReviewTests.check_transfer_approved, {})
        except Exception as e:
            logging.debug('Cannot check beamsets yet {}'.format(str(e)))
    return beamset_checks_dict


#
#
# Get current user snippet
#    from System import Environment
#
#    from System.DirectoryServices import AccountManagement as am
#    staff_id = Environment.UserName
#    cx = am.PrincipalContext(am.ContextType.Domain)
#    principal = am.UserPrincipal.FindByIdentity(cx, 1, staff_id)

def check_plan(physics_review=True, rso=None):
    #
    try:
        user_name = str(Environment.UserName)
    except Exception as e:
        logging.debug('{}'.format(e))
        user_name = None

    treedata = sg.TreeData()

    if not rso:
        # Initialize return variable
        Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
        # Get current patient, case, exam
        rso = Pd(error=[],
                 patient=GeneralOperations.find_scope(level='Patient'),
                 case=GeneralOperations.find_scope(level='Case'),
                 exam=GeneralOperations.find_scope(level='Examination'),
                 db=GeneralOperations.find_scope(level='PatientDB'),
                 plan=GeneralOperations.find_scope(level='Plan'),
                 beamset=GeneralOperations.find_scope(level='BeamSet'))
    r = comment_to_clipboard(rso)
    #
    # Tree Levels
    patient_key = (LEVELS['PATIENT_KEY'], "Patient: " + rso.patient.PatientID)
    exam_key = (LEVELS['EXAM_KEY'], "Exam: " + rso.exam.Name)
    plan_key = (LEVELS['PLAN_KEY'], "Plan: " + rso.plan.Name)
    beamset_key = (LEVELS['BEAMSET_KEY'], "Beam Set: " + rso.beamset.DicomPlanLabel)
    rx_key = (LEVELS['RX_KEY'], "Prescription")
    log_key = (LEVELS['LOG_KEY'], "Logging")
    #

    test_results = []

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
         - beamset_key
                |
                 -- Beamset Checks
        |
         -- Logs                    
    """
    """
    Gather Patient Level Checks
    """
    if rso.exam:
        patient_checks_dict = get_exam_level_tests(rso)
    check_patient_logs = True if rso.patient else False
    plan_checks_dict = {}
    """
    Gather Plan Level Checks
    """
    if rso.plan:
        plan_checks_dict = get_plan_level_tests(rso, physics_review)
    #
    """
    Gather BeamSet Level Checks
    """
    if rso.beamset:
        beamset_checks_dict = get_beamset_level_tests(rso, physics_review)
    """
    Parse logs
    """
    if check_patient_logs:
        lines = read_log_file(patient_id=rso.patient.PatientID)
        message_logs = parse_log_file(lines=lines, parent_key=log_key[0], phrases=KEEP_PHRASES)
    # Execute tests
    exam_level_tests = []
    exam_level_doc = []
    for key, p_func in patient_checks_dict.items():
        pass_result, message = p_func[0](rso=rso, **p_func[1])
        message_dicom = build_tree_element(parent_key=exam_key[0],
                                           child_key=key,
                                           pass_result=pass_result,
                                           message_str=message)
        exam_level_tests.extend(message_dicom)
        document_dicom = build_document_row(child_key=key,
                                            message_str=message,
                                            pass_result=pass_result,
                                            comment="exam comment")
        exam_level_doc.extend(document_dicom)

    """
    Execute Plan Level Checks
    """
    # Plan LevelChecks
    plan_level_tests = []
    plan_level_doc = []
    for key, pl_func in plan_checks_dict.items():
        pass_result, message = pl_func[0](rso=rso, **pl_func[1])
        message = build_tree_element(parent_key=plan_key[0],
                                     child_key=key,
                                     pass_result=pass_result,
                                     message_str=message)
        plan_level_tests.extend(message)
        document_plan = build_document_row(child_key=key,
                                           message_str=message,
                                           pass_result=pass_result,
                                           comment="plan comment")
        plan_level_doc.extend(document_plan)

    #
    # BEAMSET LEVEL CHECKS
    beamset_level_tests = []
    beamset_level_doc = []

    #
    # Run dialog parse
    dialog_key = 'Beamset Template Selection'
    beamset_dialog = parse_beamset_selection(beamset_name=rso.beamset.DicomPlanLabel,
                                             messages=message_logs,
                                             dialog_key=dialog_key)
    message = build_tree_element(parent_key=beamset_key[0],
                                 child_key=dialog_key,
                                 pass_result=beamset_dialog[dialog_key][0],
                                 message_str=beamset_dialog[dialog_key][1])
    beamset_level_tests.extend(message)
    document_beamset = build_document_row(child_key=dialog_key,
                                          message_str=beamset_dialog[dialog_key][1],
                                          pass_result=beamset_dialog[dialog_key][0],
                                          comment="beamset comment")
    beamset_level_doc.extend(document_beamset)
    for k, v in beamset_dialog.items():
        if k != dialog_key:
            message = build_tree_element(parent_key=dialog_key,
                                         child_key=k,
                                         pass_result=v[0],
                                         message_str=v[1])
            beamset_level_tests.extend(message)
            document_beamset = build_document_row(child_key=k,
                                                  message_str=v[1],
                                                  pass_result=v[0],
                                                  comment="beamset comment")
            beamset_level_doc.extend(document_beamset)
    # Read the treatment planning order selection
    dialog_key = 'Treatment Planning Order Selection'
    tpo_dialog = parse_treatment_planning_order_selection(beamset_name=rso.beamset.DicomPlanLabel,
                                                          messages=message_logs,
                                                          dialog_key=dialog_key)
    message = build_tree_element(parent_key=beamset_key[0],
                                 child_key=dialog_key,
                                 pass_result=tpo_dialog[dialog_key][0],
                                 message_str=tpo_dialog[dialog_key][1])
    beamset_level_tests.extend(message)
    document_beamset = build_document_row(child_key=dialog_key,
                                          message_str=tpo_dialog[dialog_key][1],
                                          pass_result=tpo_dialog[dialog_key][0],
                                          comment="beamset comment")
    beamset_level_doc.extend(document_beamset)
    for k, v in tpo_dialog.items():
        if k != dialog_key:
            message = build_tree_element(parent_key=dialog_key,
                                         child_key=k,
                                         pass_result=v[0],
                                         message_str=v[1])
            beamset_level_tests.extend(message)
            document_beamset = build_document_row(child_key=k,
                                                  message_str=v[1],
                                                  pass_result=v[0],
                                                  comment="beamset comment")
            beamset_level_doc.extend(document_beamset)
    # Run others
    for key, b_func in beamset_checks_dict.items():
        pass_result, message = b_func[0](rso=rso, **b_func[1])
        message = build_tree_element(parent_key=beamset_key[0],
                                     child_key=key,
                                     pass_result=pass_result,
                                     message_str=message)
        beamset_level_tests.extend(message)
        document_beamset = build_document_row(child_key=beamset_key[0],
                                              message_str=message,
                                              pass_result=pass_result,
                                              comment="beamset comment")
        beamset_level_doc.extend(document_beamset)
    # TREE BUILDING
    #
    # Insert main (patient) node
    patient_level_pass, patient_icon = parse_level_tests(exam_level_tests + plan_level_tests + beamset_level_tests)
    treedata.Insert("", patient_key[0], patient_key[1], patient_level_pass, icon=patient_icon)
    # Insert Exam Level Nodes
    exam_level_pass, exam_icon = parse_level_tests(exam_level_tests)
    treedata.Insert(patient_key[0], exam_key[0], exam_key[1], exam_level_pass, icon=exam_icon)
    performed_tests_exams = insert_tests_return_fails(exam_level_tests, treedata, test_results)
    # Insert Plan Level notes
    plan_level_pass, plan_icon = parse_level_tests(plan_level_tests)
    treedata.Insert(patient_key[0], plan_key[0], plan_key[1], plan_level_pass, icon=plan_icon)
    performed_tests_plans = insert_tests_return_fails(plan_level_tests, treedata, test_results)
    #
    # Insert Beamset Level Nodes
    beamset_level_pass, beamset_icon = parse_level_tests(beamset_level_tests)
    treedata.Insert(patient_key[0], beamset_key[0], beamset_key[1], beamset_level_pass, icon=beamset_icon)
    performed_tests_beamsets = insert_tests_return_fails(beamset_level_tests, treedata, test_results)
    #
    # Log Level
    treedata.Insert(patient_key[0], log_key[0], log_key[1], "")
    if check_patient_logs:
        for m in message_logs:
            treedata.Insert(m[0], m[1], m[2], [m[3]])  # Note the list of the last entry. Can this be of use?

    # Gui
    # TODO is it possible to specify which columns are expanded by pass fail?
    sg.theme('Topanga')
    col_widths = [20]
    comment_visible = False
    bottom = [[sg.Button('Cancel'),
              sg.Button('Comment'),
               sg.Frame('',
                        [[sg.InputText('Replace',key='-COMMENT TEXT-'),
                          sg.Button('Ok')]],
                        visible=comment_visible,
                        key='-COMMENT TEXT VISIBLE-'
                        )
               ,
              sg.Button('Done')]]
    col1 = sg.Frame('ReviewChecks:',
                    [
                        [
                            sg.Tree(
                                data=treedata,
                                headings=['Result', 'Comment'],
                                auto_size_columns=False,
                                num_rows=40,
                                col0_width=120,
                                col_widths=col_widths,
                                key='-TREE-',
                                show_expanded=False,
                                justification="left",
                                enable_events=True),
                        ],
                        [sg.Frame('', bottom)],
                    ],
                    pad=(0, 0))
    layout = [[col1]]

    window = sg.Window('Plan Review: ' + user_name, layout)

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event in 'Done':
            if test_results and not physics_review:
                now = datetime.now()
                dt_string = now.strftime("(%H:%M) %B %d, %Y")
                logging.warning("Review Script Warnings/Errors present at {}".format(dt_string))
                for tr in test_results:
                    logging.warning(f"\t{tr}")
            break
        elif event in 'Comment':
            logging.debug(f'Event noted {event}, with values{values}')
            active_node = values['-TREE-'][0]
            logging.debug(f'Key is {treedata[active_node]}')
            # window['-COMMENT TEXT-'].update(window[active_node].get_text())
            # window['-COMMENT TEXT VISIBLE-'].update(visible=True)
            #{'-TREE-': ['BEAMSET_LEVEL.Beamset Template Selection'],
            # '-COMMENT TEXT-': "{'-TREE-': ['PLAN_LEVEL.Plan approval status'], ""'-COMMENT TEXT-': ''}"}

    window.close()
    r.destroy()
    return {'Test_Exam': exam_level_tests,
            'Test_Plan': plan_level_tests,
            'Test_BeamSet': beamset_level_tests}


from docx import Document
from docx.shared import Inches
from docx.enum.table import WD_ALIGN_VERTICAL
import parser


def generate_doc(rso, tests):
    # Output file
    file_name = rso.patient.PatientID + "_" + rso.beamset.DicomPlanLabel + ".doc"
    output_file = os.path.join(OUTPUT_DIR, file_name)
    header_text = "Photon VMAT Physics Review"
    # Get approval info:
    approval_status = BeamSetReviewTests.approval_info(rso.plan, rso.beamset)
    if approval_status.beamset_approved:
        current_time = str(rso.beamset.Review.ReviewTime)
    else:
        current_time = 'NA'

    demographics = {
        'Name': rso.patient.Name,
        'MRN': rso.patient.PatientID,
        'Beamset Name': rso.beamset.DicomPlanLabel,
        'Approval Time': current_time}
    # Responses to non-scriptable questions
    plan_questions = tests['Test_BeamSet']
    # plan_questions = [('Plan Name consistent with TPO', 'Y', 'Sample Input'),
    #                   ('Plan approved by MD', 'NA', 'Preplan'),
    #                   ]

    # Begin
    document = Document()
    section = document.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    # Add header

    header = section.header
    paragraph = header.paragraphs[0]
    # Add logo
    logo_run = paragraph.add_run()
    logo_run.add_picture(UW_HEALTH_LOGO, width=Inches(1.0))
    text_run = paragraph.add_run()
    text_run.text = '\t' + header_text  # For center align of text
    text_run.style = "Heading 1 Char"

    paragraph = document.add_paragraph()
    # Add Top Row Demographics
    table = document.add_table(rows=2, cols=4, style='Medium Grid 1 Accent 2')
    for index, k in enumerate(demographics):
        row_key = table.rows[0]
        row_value = table.rows[1]
        row_key.cells[index].text = k
        row_value.cells[index].text = demographics[k]
    # Add the plan checks
    paragraph = document.add_paragraph()
    document = add_check_list_table(tests['Test_BeamSet'], document)

    document.save(output_file)
    print('Complete')


def add_check_list_table(check_results, document, title=None):
    logging.debug(f'{check_results}')
    n_cols = 3  # Icon, Testname, Result, Comment
    table_properties = {'NCOL': 4,
                        'WIDTH_COL': [(0, 0.25), (1, 1.), (2, 3.), (3, 3.)]}
    table = document.add_table(rows=1, cols=table_properties['NCOL'],
                               style='Light Grid Accent 2')
    i = 0
    for r in enumerate(check_results):
        row = table.rows[i]
        child_list = r[1]
        if i == 0:
            row.cells[0].text = 'Status'
            row.cells[1].text = 'Test Performed'
            row.cells[2].text = 'Result'
            row.cells[3].text = 'Reviewer Comment'
            table.add_row()
            i += 1
        elif child_list[0] not in LEVELS.values():
            logging.debug('Child list {}'.format(child_list))
            row.cells[0].add_paragraph().add_run().add_picture(child_list[4],
                                                               width=Inches(0.2),
                                                               height=Inches(0.2))
            row.cells[1].text = child_list[0]
            row.cells[2].text = child_list[2]
            table.add_row()
            i += 1
        for index, width in table_properties['WIDTH_COL']:
            for cell in table.columns[index].cells:
                cell.width = Inches(width)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    return document


def main(physics_review=True):
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    rso = Pd(error=[],
             patient=GeneralOperations.find_scope(level='Patient'),
             case=GeneralOperations.find_scope(level='Case'),
             exam=GeneralOperations.find_scope(level='Examination'),
             db=GeneralOperations.find_scope(level='PatientDB'),
             plan=GeneralOperations.find_scope(level='Plan'),
             beamset=GeneralOperations.find_scope(level='BeamSet'))
    tests = check_plan(physics_review, rso=rso)
    generate_doc(rso, tests=tests)


if __name__ == '__main__':
    main()
