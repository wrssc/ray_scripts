""" Physics Review with Document
    Run basic plan integrity checks and parse the log file. Meant to be run
    on completed plans.

    Scope: Requires RayStation beamset to be loaded

    Example Usage:

    Prerequisites:


    Version history:
    0.0.0: Testing version, Script created by RAB on May 1st 2022
    1.0.0: Initial version executed on over 150 beamsets. Clinically released.
    1.0.1: Code Clean-up.
           * Deleted extraneous code from physics_review.py
           * Refactor sg as Sg
           * Corrected a bug mapping VMAT optimization to Tomo3D Plan Check.
           * Eliminating unused logging statements in manual tab
           * Fixed a bug causing Report button to need to be pressed twice
           * Added a test on screenshot when reporting errors to handle an empty screenshot
           * Fixed a small-screen scaling issue preventing all dialogs from being displayed
           * Moved "Jaw opening" and "Blocking checks" to more appropriate tabs

           Added features:
           * New column in the review document for user-entered special treatment instructions
           * Reformatted beamset approval time to match the RayStation document format.
           * Refactoring the build_tree function to make it more readable and accommodate
             dosimetry review
           * Further adjustments to the GUI sizes and formatting for small screens
             successfully eliminated horizontal scrolling for all but beamsets on initial
             page
           * Debugged and improved function of check_prv_status to now exclude very
             low dose serial oars from warnings regarding PRV usage
           * Moving the modulation complexity score to sandbox until plan-specific benchmarks for MCS
             are available.


    1.0.2: Minor changes
           * Added a sandbox test to check if the max dose point is within the PTVs and reports
             the value as a percentage of prescribed
           * Refactor of the comparison of user-entered and DICOM date to handle anonymized cases
           * Revised the way special instructions are parsed to handle unused instructions
           * For multiple beamset plans the check lists from all plan types are now combined
           * Exempted anything within the sandbox tab from required user input
           * Changed the way empty review levels are handled to ensure tabs are ordered correctly
           * Fixed a bug causing user-indicated failed tests to be overriden to passing.
           * Fixed a bug with treatment instructions to include the radio-response, e.g.
             "Full Bladder: No"
           * Rephrased the comment in the fraction size check to make clear that the intent of the
             check is to ensure the fraction size is appropriate with the MD.
           * Fixed a bug preventing the order finding script from matching on the appropriate entry in
             the log file.
           * Updated the UW Prostate SBRT template to remove the twice-daily fractionation option
           * Remove the 8 Gy x 1 and 4 Gy x 5 from the check for commonly mistyped fraction sizes
           * Reformatted the gui-handling to exist as a class. This is the first step to restoring the
             test tree during a load.
           * Made the Prior RT and IMD checkboxes Radio buttons, and made them a mandatory entry
           * Modified the clearance testing function to account for whether or not the gantry passes through
             the problem areas in the plan.
           * Modified the clearance testing function to assume a direction to static gantry beams then
             check for collisions in that direction.
           * Enhanced the clearance testing function to account for non-coplanar beams.
    1.0.3: Last update before release
           * Add an option to the radio selection of special instructions to include "None". This gets ignored
             in the report.
           * Incorporated the latest DITTO check for Aria plan transfer
               * Specifically exclude TomoTherapy beamsets from DITTO checks
           * Fixed a bug preventing PriorRT and IMD selections from being included in PDF report
           * Fixed a bug causing TomoTherapy optimization checklists to not be grouped.
           * Ironically, if the PRV check passes, no message was displayed. I did not have a test for this.







    PRERELEASE:
    TODO: Fix the slice spacing check to pick just the pertinent technique
    TODO: Need a required prompt for all entries in the first tab
    TESTS:
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
__version__ = '1.0.2'
__status__ = 'Clinical'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2024, University of Wisconsin Board of Regents'
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
            return 'Physics review canceled'
            # sys.exit('Physics review canceled')

    if do_physics_review:
        # generate_doc(rso, ata=header, test_mode=doc_only)
        generate_pdf(rso, review_data=review_data, test_mode=doc_only)
        Sg.popup('Form submitted successfully.')
