""" Physics Review with Document
    Run basic plan integrity checks and parse the log file. Meant to be run
    on completed plans.

    Scope: Requires RayStation beamset to be loaded

    Example Usage:

    Prerequisites:


    PRERELEASE:
    TODO: Need a required prompt for all entries in the first tab
    TESTS:
    TODO: Clearance check: LOOK AT WHERE THE BEAM WILL GO!
    TODO: Add a check on MU/rx in cGy and flag over the 5
    TODO: For GTV, and CTV types. Are these all within a PTV?
    POST RELEASE
    TODO: WHEN ONLY ONE BEAMSET IN PLAN DEFAULT TO IT.
    TODO: ADD TYPE CHECK TO THE GTV LIST RATHER THAN JUST A REGEX.
    TODO: ADD BRAIN 1mm language
    TODO: HIGHLIGHT FRAMES THAT SHOULD BE FILLED IN AS RED
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
     * Special instructions
     * Energy
    TODO: Objective type is correct: for anything with min goals, should be
     PTV/GTV/CTV
    TODO: If head and neck plan check for inner air structure

    In parse_order_selection:
    TODO: Take a reg-exp as a list for input for matching a dialog and for
        each desired phrase loop over the phrases for a match
    TODO: Add the target matching that takes place for this step with
        consideration of the pre-logcrit syntax and post-logcrit syntax
    Individual Test improvements:
    TODO: Contour gap check need only include human-drawn contours

    Version history:
    0.0.0: Testing version, Script created by RAB on May 1st 2022
    1.0.0: Initial version executed on over 150 beamsets. Clinically released.
    1.0.1: Code Clean-up.
           * Deleted extraneous code from physics_review.py
           * Refactor sg as Sg
           * Corrected a bug mapping VMAT optimization to Tomo3D Plan Check.
           * Eliminating unused logging statements in manual tab
           * Fixed a bug causing Report button to need to be pressed twice

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
__date__ = '2023-Nov-20'
__version__ = '1.0.1'
__status__ = 'Clinical'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__credits__ = ['']

import sys
import os
import PySimpleGUI as Sg
import logging
from collections import namedtuple
from GeneralOperations import find_scope
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '.'))
from PlanReview.guis import launch_physics_review_gui
from PlanReview.utils.get_user_name import get_user_name
from PlanReview.documentation.generate_physics_pdf import generate_pdf


def physics_review(do_physics_review=True):
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

    # Uncomment to simply run the tree
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
    doc_only = False
    if doc_only:
        review_data = None
    else:
        # Gui
        review_data = launch_physics_review_gui(rso)
        if not review_data:
            sys.exit('Physics review canceled')

    if do_physics_review:
        # generate_doc(rso, ata=header, test_mode=doc_only)
        generate_pdf(rso, review_data=review_data, test_mode=doc_only)
        Sg.popup('Form submitted successfully.')
