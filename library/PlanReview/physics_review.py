""" Physics Review with Document
    Run basic plan integrity checks and parse the log file. Meant to be run
    on completed plans.

    Scope: Requires RayStation beamset to be loaded

    Example Usage:

    Script Created by RAB May 1st 2022
    Prerequisites:


    PRERELEASE:
    TODO: ADD CT ORIENTATION TO PREPLAN DIALOG AND CHECK VS RS
    TODO: ADD TO CRITICAL the CASE, EXAM, PLAN, BEAMSETUID
    TODO: Need a required prompt for all entries in the first tab
    TODO: Basic code for loading multiple reviews at once.
          -Header and tests should be moved under patient plan
          -json files should be moved under patient plan
          -should load the list of user tests and connect them to checkboxes
    TODO: Sizing of the automated test subframes needs to be computed based on items
          present.
    TESTS:
    TODO: ADD PATIENT ORIENTATION TO PREPLAN AND COMPARE TO DICOM
    TODO: Clearance check: LOOK AT WHERE THE BEAM WILL GO!
    POST RELEASE
    TODO: WHEN ONLY ONE BEAMSET IN PLAN DEFAULT TO IT.
    TODO: ADD TYPE CHECK TO THE GTV LIST RATHER THAN JUST A REGEX.
    TODO: ADD BRAIN 1mm language
    TODO: HIGHLIGHT FRAMES THAT SHOULD BE FILLED IN AS RED
    TODO: ADD Patient Name ID to the GUI title
    TODO: Siemens IMAR tags: IMAR: (0029,1041), KERNEL: (0029,1042)
    TESTS
    TODO: USE THE PTVs identified DURING PREPLAN
     AND ENSURE PTVs with GOALS OR OBJECTIVES ARE NOT LARGER
    TODO: FOR EACH CONTOUR WITH A GOAL, CHECK THE LENGTH ON TARGET SLICES
    Unfiled
    TODO:: Set up a mapping table for checks we are pulling out of
           checkboxes and into automated checks
    TODO:: Experiment with very long tool tips for a help prompt under automated checks
    TODO:: DOSIMETRY REVIEW
        -Previous Treatment check boxes along with
        0 Yes: Please refer to D-Evaluation for Prior Radiotherapy document
        -CIED Pacemaker check box:
        0 Yes: Please refer to D-Implantable Cardiac Device Note
        -In the plan, the target is in a Choose One
        location in the patient.  This Choose One   the TPO.
        -'test_name': 'Beam added with no collision via machine geometry'
        'test_name': 'Modulation factor appropriate for plan'}
        'test_name': 'Field width < Target length'
        'test_name': 'Dynamic Jaws used on 2.5 and 5 cm plans'
        'test_name': 'Isocenter lateral offset < 3 cm and In/Out offset < 18 cm'
        3D: RayStation 3D Photon Safety Review
        Electron: RayStation Electron Safety Review
    TODO: Check for same iso, and same number of fractions in
       different beamsets, and flag for merge
    TODO:
       Check bad regions of Frame
    TODO: For a given couch angle, check the arc direction for a kick toward
           gantry rotation
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
       put a circle down at isocenter equal in dimension to ganty (collimator
       pin)/bore clearance
       union patient/supports
       determine gantry positions
    TODO:
       def - check the front edges of the couch and suspended headboard
    TODO:
       Flag all ROIs not made in MIM with goals
    TODO: Stray voxel check/
    TODO: Check clinical goal
       if a clinical goal is not met, look at the objective list to see if it is
       constrained
    TODO: Add test on currently commissioned beams for timestamp
    TODO: Check if an arc has the same couch and start/stop. if so, collimator
     angles should differ
    TODO: FRONT PAGE CHECKS
     * TPO versus doses used in plan
     * CT Orientation
     * Number of slices and scan date
     * Special instructions
     * Energy
    TODO: Objective type is correct: for anything with min goals, should be
     PTV/GTV/CTV
    In parse_order_selection:
    TODO: Take a reg-exp as a list for input for matching a dialog and for
        each desired phrase loop over the phrases for a match
    TODO: Add the target matching that takes place for this step with
        consideration of the pre-logcrit syntax and post-logcrit syntax
    Individual Test improvements:
    TODO: Contour gap check need only include human-drawn contours

    Version history:



    This program is free software: you can redistribute it and/or modify it
    under
    the terms of the GNU General Public License as published by the Free
    Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
    details.

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

import sys
import os
import PySimpleGUI as sg
import logging
from collections import namedtuple
from GeneralOperations import find_scope

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '.'))
from PlanReview.guis import (build_tree_element, build_review_tree,
                             launch_physics_review_gui)
from PlanReview.utils.get_user_name import get_user_name
from PlanReview.review_definitions import DOMAIN_TYPE
from PlanReview.documentation.generate_physics_document import generate_doc
from PlanReview.qa_tests.test_examination import get_exam_level_tests
from PlanReview.qa_tests.test_plan import get_plan_level_tests
from PlanReview.qa_tests.test_beamset import get_beamset_level_tests
from PlanReview.qa_tests.test_beamset import parse_beamset_selection
from PlanReview.qa_tests.test_plan import parse_order_selection
from PlanReview.qa_tests.analyze_logs import retrieve_logs


def automated_check_tree(rso, do_physics_review, beamsets=None):
    """
        Builds and returns a review tree for a radiotherapy treatment plan
        using PySimpleGUI.

        Args:
            rso: The radiotherapy structure object.
            do_physics_review: A boolean value indicating whether to
            perform physics review.

        Returns:
            A tuple containing the tree data and tree children.
    """

    # Tree Levels (move these to tree building)
    patient_key = (DOMAIN_TYPE['PATIENT_KEY'], "Patient: " + rso.patient.PatientID)
    exam_key = (DOMAIN_TYPE['EXAM_KEY'], "Exam: " + rso.exam.Name)
    plan_key = (DOMAIN_TYPE['PLAN_KEY'], "Plan: " + rso.plan.Name)
    beamset_key = (
        DOMAIN_TYPE['BEAMSET_KEY'], "Beam Set: " + rso.beamset.DicomPlanLabel)
    rx_key = (DOMAIN_TYPE['RX_KEY'], "Prescription")
    log_key = (DOMAIN_TYPE['LOG_KEY'], "Logging")
    #

    tree_children = []

    """
    Gather Patient Level Checks
    """
    patient_checks_dict = get_exam_level_tests(rso)
    """
    Gather Plan Level Checks
    """
    plan_checks_dict = get_plan_level_tests(rso, do_physics_review)
    """
    Gather BeamSet Level Checks
    """
    beamset_checks_dict = get_beamset_level_tests(rso, do_physics_review)
    """
    Parse logs
    """
    message_logs = retrieve_logs(rso, log_key)

    # Execute qa_tests
    exam_level_tests = []
    for key, p_func in patient_checks_dict.items():
        pass_result, message = p_func[0](rso=rso, **p_func[1])
        node, child = build_tree_element(parent_key=exam_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        exam_level_tests.extend([node, child])
        tree_children.append(child)

    """
    Execute Plan Level Checks
    """
    # Plan LevelChecks
    plan_level_tests = []
    # Parse the log file for the treatment planning order selected.
    dialog_key = 'Treatment Planning Order Selection'
    tpo_dialog = parse_order_selection(
        beamset_name=rso.beamset.DicomPlanLabel,
        messages=message_logs,
        dialog_key=dialog_key)
    node, child = build_tree_element(parent_key=plan_key[0],
                                     child_key=dialog_key,
                                     pass_result=tpo_dialog[dialog_key][0],
                                     message_str=tpo_dialog[dialog_key][1])
    plan_level_tests.extend([node, child])
    for k, v in tpo_dialog.items():
        if k != dialog_key and all(v):
            node, child = build_tree_element(parent_key=dialog_key,
                                             child_key=k,
                                             pass_result=v[0],
                                             message_str=v[1])
            plan_level_tests.extend([node, child])
            tree_children.append(child)
    # FINISH PLAN LEVEL CHECKS DEFINED IN plan_checks_dict
    for key, pl_func in plan_checks_dict.items():
        pass_result, message = pl_func[0](rso=rso, **pl_func[1])
        node, child = build_tree_element(parent_key=plan_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        plan_level_tests.extend([node, child])
        tree_children.append(child)

    #
    # BEAMSET LEVEL CHECKS
    beamset_level_tests = []

    #
    # Run dialog parse
    dialog_key = 'Beamset Template Selection'
    beamset_dialog = parse_beamset_selection(
        beamset_name=rso.beamset.DicomPlanLabel,
        messages=message_logs)
    node, child = build_tree_element(parent_key=beamset_key[0],
                                     child_key=dialog_key,
                                     pass_result=beamset_dialog[dialog_key][0],
                                     message_str=beamset_dialog[dialog_key][1])
    beamset_level_tests.extend([node, child])
    for k, v in beamset_dialog.items():
        if k != dialog_key and all(v):
            node, child = build_tree_element(parent_key=dialog_key,
                                             child_key=k,
                                             pass_result=v[0],
                                             message_str=v[1])
            beamset_level_tests.extend([node, child])
            tree_children.append(child)

    # Run others
    for key, b_func in beamset_checks_dict.items():
        pass_result, message = b_func[0](rso=rso, **b_func[1])
        node, child = build_tree_element(parent_key=beamset_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        beamset_level_tests.extend([node, child])
        tree_children.append(child)

    tree_data = build_review_tree(rso, exam_level_tests,
                                  plan_level_tests,
                                  beamset_level_tests,
                                  message_logs)
    return tree_data, tree_children


def perform_exam_tests(rso):
    tests = []
    exam_level_tests = get_exam_level_tests(rso)
    for key, p_func in exam_level_tests.items():
        pass_result, message = p_func[0](rso=rso, **p_func[1])
        node, child = build_tree_element(key[0], key[1], pass_result, message)
        tests.append({"exam_level_tests": [node, child]})
    return tests


def perform_plan_tests(rso, do_physics_review):
    tests = []
    plan_level_tests = get_plan_level_tests(rso, do_physics_review)
    for key, p_func in plan_level_tests.items():
        pass_result, message = p_func[0](rso=rso, **p_func[1])
        node, child = build_tree_element(key[0], key[1], pass_result, message)
        tests.append({"plan_level_tests": [node, child]})
    return tests


def perform_beamset_tests(rso, do_physics_review):
    tests = []
    beamset_level_tests = get_beamset_level_tests(rso, do_physics_review)
    for key, b_func in beamset_level_tests.items():
        pass_result, message = b_func[0](rso=rso, **b_func[1])
        node, child = build_tree_element(key[0], key[1], pass_result, message)
        tests.append({"beamset_level_tests": [node, child]})
    return tests


def physics_review(do_physics_review=True, rso=None):
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
             - alt_beamset_key
                    |
                     -- Other Beamset Checks
            |
             -- Logs
    """
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan',
                           'beamset'])
    # Get current patient, case, exam
    rso = Pd(error=[],
             patient=find_scope(level='Patient'),
             case=find_scope(level='Case'),
             exam=find_scope(level='Examination'),
             db=find_scope(level='PatientDB'),
             plan=find_scope(level='Plan'),
             beamset=find_scope(level='BeamSet'))
    #
    user_name = get_user_name()
    logging.info(f'Physics review script launched by {user_name}')

    # tree_data = Sg.TreeData()

    if not rso:
        # Initialize return variable
        Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan',
                               'beamset'])
        # Get current patient, case, exam
        rso = Pd(error=[],
                 patient=find_scope(level='Patient'),
                 case=find_scope(level='Case'),
                 exam=find_scope(level='Examination'),
                 db=find_scope(level='PatientDB'),
                 plan=find_scope(level='Plan'),
                 beamset=find_scope(level='BeamSet'))
    # r = comment_to_clipboard(rso)
    #
    doc_only = False
    if doc_only:
        tests = None
        header = None
    else:
        # Gui
        tests, header = launch_physics_review_gui(rso)
        if not tests and not header:
            sys.exit('Physics review canceled')

    # r.destroy()
    if do_physics_review:
        generate_doc(rso, tests=tests, header_data=header, test_mode=doc_only)
        sg.popup('Form submitted successfully.')
