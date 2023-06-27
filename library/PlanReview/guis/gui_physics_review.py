# Import necessary modules and functions
import PySimpleGUI as sg
import os
import logging
from PlanReview.review_definitions import PASS, \
    CHECK_BOXES_PHYSICS_REVIEW, \
    CHECK_BOXES_PHYSICS_REVIEW_3D, \
    CHECK_BOXES_PHYSICS_REVIEW_VMAT, CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS, \
    CHECK_BOXES_PHYSICS_REVIEW_TOMO3D, CHECK_BOXES_PHYSICS_REVIEW_TOMO, \
    PROTOCOL_DIR, OUTPUT_DIR
from PlanReview.utils import get_user_name, get_roi_names_from_type
from PlanReview.utils.protocol_loading import load_protocols, \
    get_sites, get_all_orders, get_unique_instructions
from PlanReview.utils.constants import *
from PlanReview.utils.perform_automated_checks import perform_automated_checks
from PlanReview.guis.gui_report_script_error import report_script_error
from PlanReview.guis.create_preplan_tab import load_preplan, \
    extract_preplan_values, \
    calculate_preplan_dose_per_fraction, update_preplan_frequencies, \
    update_preplan_instructions, update_preplan_protocols, \
    update_preplan_orders, create_preplan_information_tab, \
    update_preplan_beamset_rows, update_preplan_target_rows
from PlanReview.guis.create_physics_manual_tab import build_manual_check_box_list, \
    get_manual_failing_tests, create_tab_manual_checks, \
    on_manual_radio_button_click, extract_manual_values, load_manual, \
    process_failed_tests, process_check_box_values
import json
import connect

# PRERELEASE:
#
# TODO: ADD CT ORIENTATION TO PREPLAN DIALOG AND CHECK VS RS
# TODO: TPO DROPDOWN NEEDS MORE LINES FOR ORDER SELECTION
# TODO: EXPAND THE SELECTIONS FOR ORDERS!!!
# TODO: ADD TO CRITICAL the CASE, EXAM, PLAN, BEAMSETUID
# TODO: SANDBOX TESTS
# TODO:: Build a sandbox test directory in which to put tests that have not been fully reviewed
# TODO: ADD COMMENT SECTION
# TODO:: Get Users resolution before setting above
# TODO: MAKE GUI WORK BASED ON USER RESOLUTION
# TODO: Need a required prompt for all entries in the first tab
# TODO:: Get all window sizing standardized to hsize,vsize
# TESTS:
# TODO: ADD PATIENT ORIENTATION TO PREPLAN AND COMPARE TO DICOM
#
# POST RELEASE
# TODO: WHEN ONLY ONE BEAMSET IN PLAN DEFAULT TO IT.
# TODO: ADD TYPE CHECK TO THE GTV LIST RATHER THAN JUST A REGEX.
# TODO: ADD BRAIN 1mm language
# TODO: ADD MULTI_BEAMSET CHECKS
# TODO: HIGHLIGHT FRAMES THAT SHOULD BE FILLED IN AS RED
# TODO: ADD Patient Name ID to the GUI title
# TODO: Siemens IMAR tags: IMAR: (0029,1041), KERNEL: (0029,1042)
#
# TESTS
# TODO: USE THE PTVs identified DURING PREPLAN
#  AND ENSURE PTVs with GOALS OR OBJECTIVES ARE NOT LARGER
# TODO: FOR EACH CONTOUR WITH A GOAL, CHECK THE LENGTH ON TARGET SLICES
#
# Unfiled
# TODO:: Set up a mapping table for checks we are pulling out of
#        checkboxes and into automated checks
# TODO:: Experiment with very long tool tips for a help prompt under automated checks

"""

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

TODO: Check Beamsets for same machine

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

"""


def create_key(element_type, beamset_i=None, target_i=None):
    """
    Create a key for a GUI element using a dictionary.

    Parameters:
    element_type (str): The type of the GUI element (e.g., 'beamset_num_text', 'target_name', etc.).
    beamset_i (int, optional): The index of the beamset, if applicable.
    target_i (int, optional): The index of the target, if applicable.

    Returns:
    tuple: A tuple containing the element type and optional beamset/target indices.
    """
    key = (element_type,)
    if beamset_i is not None:
        key += (beamset_i,)
    if target_i is not None:
        key += (target_i,)
    return key


def generate_event_key(*args):
    return "_".join(str(arg) for arg in args)


def tuple_key_to_str(value):
    if isinstance(value, dict):
        return {tuple_key_to_str(k): tuple_key_to_str(v) for k, v in value.items()}
    elif isinstance(value, tuple):
        return '||'.join(map(str, value))
    return value


def str_key_to_tuple(value):
    if isinstance(value, dict):
        return {str_key_to_tuple(k): str_key_to_tuple(v) for k, v in value.items()}
    elif isinstance(value, str) and '||' in value:
        return tuple(int(x) if x.isdigit() else x for x in value.split('||'))
    return value


def update_window_key_dict(window, keys):
    for key in keys:
        if key not in window.key_dict:
            window.key_dict[key] = None


def save_review(rso, values):
    file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}_review.json"
    with open(os.path.join(OUTPUT_DIR, file_name), "w") as f:
        json.dump(tuple_key_to_str(values), f)
    sg.popup("Review saved successfully!")
    return file_name


def load_review(window, rso, sites, protocols, instructions, maximum_target_number,
                maximum_beamset_count, check_box_copy, file_name=None):
    if not file_name:
        file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}_review.json"
    try:
        with open(os.path.join(OUTPUT_DIR, file_name), "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        sg.popup("No saved review found!")
        return
    order_name = None
    protocol = None

    values = str_key_to_tuple(values)
    # Add missing keys to the window.key_dict
    update_window_key_dict(window, values.keys())

    load_preplan(window, values, sites, protocols, instructions, maximum_beamset_count,
                 maximum_target_number)
    load_manual(window, values, check_box_copy)
    num_beamsets = int(window[KEY_BEAMSET_COUNT].get()) \
        if window[KEY_BEAMSET_COUNT].get() else 1
    return num_beamsets


def get_review_gui_values(window, failed_tests, check_boxes, comment_box):
    """
    Extracts the values entered into the PySimpleGUI dialog and sorts them by keys.

    Parameters:
    - window: PySimpleGUI Window object representing the GUI
    - failed_tests: list of failed tests from the review_definitions module
    - check_boxes: dictionary of completed check boxes the user has filled in
    - comment_box: dictionary with contents of the Comments frame.

    Returns:
    - sorted_values: dictionary of values sorted by keys
    """
    #
    # Get any data from the first tab
    if window[KEY_BEAMSET_COUNT].get():
        preplan_values = extract_preplan_values(
            window,
            num_beamsets=int(window[KEY_BEAMSET_COUNT].get()))
    else:
        preplan_values = extract_preplan_values(window, num_beamsets=1)

    manual_values = extract_manual_values(window, failed_tests, check_boxes, comment_box)
    sorted_values = merge_dicts(preplan_values, manual_values)

    return sorted_values


# Event handler for "Done" button
def on_done_button_click(window, values, check_boxes):
    # Check if all the required fields are filled in
    is_valid = True
    # TODO: Split up based on tab and move to separate files
    for key in check_boxes:
        for item in check_boxes[key]:
            radio_y_key = create_key(f'{item["key"]}{KEY_CHECK}{KEY_RADIO}Yes')
            radio_no_key = create_key(f'{item["key"]}{KEY_CHECK}{KEY_RADIO}No')
            radio_na_key = create_key(f'{item["key"]}{KEY_CHECK}{KEY_RADIO}NA')
            input_key = create_key(f'{item["key"]}{KEY_CHECK}{KEY_INPUT_TEXT}')
            value_defined = any(values[k] for k in [radio_na_key, radio_y_key, radio_no_key])
            if not value_defined:
                window[radio_y_key].update(text_color='#8B0000')
                window[radio_no_key].update(text_color='#8B0000')
                window[radio_na_key].update(text_color='#8B0000')
                is_valid = False
            if values[radio_no_key] and not values[input_key]:
                window[input_key].update(text_color='#ffffff',
                                         background_color='#8B0000')
                is_valid = False

    if not is_valid:
        sg.popup_error('Please fill in all the required fields.')
    return is_valid


def display_progress_bar():
    layout = [[sg.Text('Running tests...')],
              [sg.ProgressBar(max_value=100, orientation='h', size=(30, 20),
                              key='progressbar')]]

    window = sg.Window('Progress', layout, no_titlebar=True,
                       keep_on_top=True, finalize=True)

    progress_bar = window['progressbar']
    progress_bar.UpdateBar(0)

    return window, progress_bar


def run_tests(rso, do_physics_review, progress_bar, values):
    # Run the automated checks
    tree_data, tree_children = perform_automated_checks(rso, do_physics_review,
                                                        progress_bar, values)

    return tree_data, tree_children


def run_tests_in_thread(rso, do_physics_review, progress_bar, values):
    tree_data, tree_children = run_tests(rso, do_physics_review,
                                         progress_bar, values)

    # Update the progress bar
    progress_bar.UpdateBar(100)

    # Close the progress bar window
    return tree_data, tree_children


def sanitize_dict(d):
    return {k: repr(v) for k, v in d.items()}


def do_automated_tests(rso, do_physics_review, beamsets, values):
    """
    Run the automated check script within the GUI on multiple beamsets
    :param rso:
    :param do_physics_review:
    :param beamsets:
    :return:
    - tree_data: sg tree data object
    - tree_children: a list for conversion into tree subsides
    """
    tree_data, tree_children = perform_automated_checks(rso, do_physics_review,
                                                        values, beamsets=beamsets)
    return tree_data, tree_children


def on_submit_build_tree(tree_data, left_width, right_width):
    tree_layout = [[sg.Frame('ReviewChecks:',
                             [[sg.Tree(
                                 data=tree_data,
                                 headings=['Result'],
                                 auto_size_columns=False,
                                 num_rows=50,
                                 col0_width=left_width,
                                 col_widths=[right_width],
                                 key='-TREE-',
                                 show_expanded=True,
                                 justification="left",
                                 vertical_scroll_only=True,
                                 enable_events=True)]],
                             pad=(0, 0))]]
    return tree_layout


def get_failing_tests(tree_children, check_box_copy):
    for level in check_box_copy:
        for item in check_box_copy[level]:
            item['result'] = ""
            item['comment'] = ""
            item['icon'] = None
    passing_tests = []
    # Find failing tests and determine total number of rows
    failed_tests = []
    for comment, _, result, pass_fail, icon in tree_children:
        if pass_fail != PASS:
            failed_tests.append([comment, result, icon])
        else:
            passing_tests.append(
                {'test_name': comment, 'result': result, 'icon': icon,
                 'comment': "Script Pass"}
            )
    return passing_tests, failed_tests


def merge_dicts(dict1, dict2):
    merged = dict1.copy()  # Start with a copy of dict1

    for key, value in dict2.items():
        if key in merged:
            # Merge unique items from dict2[key] into merged[key]
            merged[key] = [x for x in merged[key] if x not in value] + value
        else:
            # Add key and value from dict2 if not in dict1
            merged[key] = value

    # Remove outer level keys with empty lists
    merged = {k: v for k, v in merged.items() if v}

    return merged


def build_check_box_list(rso, beamsets):
    """
    Depending on the type of beamset we are checking, find the appropriate
    checklist from review_definitions
    :param rso:
    :param beamsets (list): list of all beamsets
    :return: checks dictionary
    """
    dict1 = CHECK_BOXES_PHYSICS_REVIEW
    for beamset_name in beamsets:
        technique = rso.plan.BeamSets[beamset_name].DeliveryTechnique
        if technique == 'TomoHelical' and 'T3D' in beamset_name:
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_TOMO3D
        elif technique == 'TomoHelical':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_TOMO
        elif technique == 'ApplicatorAndCutout':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS
        elif technique == 'VMAT':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_VMAT
        elif technique == 'SMLC':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_3D
        dict1 = merge_dicts(dict1, dict2)
    return dict1


def launch_physics_review_gui(rso):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
    - tree_data: sg tree data object
    - tree_children: a list for conversion into tree subsides

    Returns: None
    """

    # GUI setup
    sg.theme('DefaultNoMoreNagging')
    # Tab sizing
    hlines = 64
    left_width = 120
    right_width = 10
    width_fac = 9  # Average should be around 8 pixels per char
    height_fac = 14  # Average pixel height should be 18 char per line
    hsize = (left_width + right_width) * width_fac
    vsize = hlines * height_fac
    # Variable initialization
    failed_tests = []
    passing_tests = []
    check_box_copy = {}

    # First Frame:
    protocols = load_protocols(PROTOCOL_DIR)
    protocol = None
    sites = get_sites(protocols)
    orders = get_all_orders(protocols)
    instructions = get_unique_instructions(protocols)
    beamsets = [b.DicomPlanLabel for b in rso.plan.BeamSets]
    max_beamset_count = len(beamsets)
    targets = get_roi_names_from_type(rso, roi_type=['Ptv', 'Gtv'])
    if targets:
        maximum_target_number = len(targets)
    else:
        maximum_target_number = 10

    # Top Menu Frame
    top = [[
        sg.Button('Save',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
        sg.Button('Load',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
        sg.Button('Pause Script',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
        sg.Button('Start Tests',
                  key='submit_button',
                  #   button_color=('white', 'blue'),
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
    ]]
    # Bottom Frame
    bottom = [[
        sg.Button('Cancel',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
        sg.Button('Done',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2),
        sg.Button('Report Error',
                  size=(8, 2),
                  pad=((0, 60), (1, 1)),
                  border_width=2,
                  key='report_error', ),
    ]]
    # Comment Frame
    side = [[sg.Text('Comments', text_color='blue', font=('Arial', 12, 'bold'))],
            [sg.Multiline(default_text='',
                          size=(30, int(0.9 * hlines)),
                          autoscroll=True,
                          auto_size_text=True,
                          key=create_key('-USER-COMMENTS-'))
             ]]

    layout = [
        [sg.Column([
            [sg.Frame('', top, vertical_alignment='top')],
            [sg.TabGroup([[sg.Tab('External Information',
                                  create_preplan_information_tab(protocols,
                                                                 sites,
                                                                 orders,
                                                                 instructions,
                                                                 beamsets,
                                                                 targets, ))
                           ]],
                         key='tab_group')],
            [sg.Frame('', bottom, vertical_alignment='bottom')]
        ], ),
            sg.Column([[sg.VSeperator()]]),
            # Vertical line to separate the comments from the left side of the GUI
            sg.Column(side, vertical_alignment='top')],
    ]

    window = sg.Window('Plan Review: ' + get_user_name(),
                       layout,
                       resizable=True)
    review_file_name = None

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            check_dict = {}
            header_data = {}
            break

        elif event == 'Load':
            num_beamsets = load_review(window, rso, sites, protocols,
                                       instructions, maximum_target_number,
                                       max_beamset_count, check_box_copy, review_file_name)
            logging.debug(f'Values are {tuple_key_to_str(values)}')
            logging.debug(f'Sim data {values[KEY_SIM_DATE]}, {values[KEY_SLICES]}')

            if not num_beamsets:
                num_beamsets = 1

        elif event == 'Pause Script':
            connect.await_user_input('Review Paused. Resume Script to Continue')
        elif event == 'report_error':
            report_script_error(rso)
        #
        # First tab Events
        elif event == KEY_SITE_SELECT:
            site_name = values[KEY_SITE_SELECT]
            update_preplan_protocols(window, site_name, KEY_PROTOCOL_SELECT, protocols)
        # Update the potential protocol choices based on those for this site
        elif event == KEY_PROTOCOL_SELECT:
            protocol = protocols[values[KEY_PROTOCOL_SELECT]]
            update_preplan_orders(window, protocol, KEY_ORDER_SELECT)
        elif event == KEY_ORDER_SELECT:
            order_name = values[KEY_ORDER_SELECT]
            update_preplan_frequencies(window, protocol, order_name)
            update_preplan_instructions(window, protocol, order_name, instructions)

        # Trigger update_beamset_rows when the number of beamsets changes
        elif KEY_BEAMSET_COUNT in event:
            num_beamsets = int(values[event])
            update_preplan_beamset_rows(window, values, num_beamsets,
                                        max_beamset_count, maximum_target_number)

        if KEY_BEAMSET_TARGET_COUNT in event:
            _, beamset_i = event
            num_targets = int(values[event])
            update_preplan_target_rows(window, num_targets, beamset_i,
                                       maximum_target_number)

        # Trigger calculate_dose_per_fraction when the dose value changes
        if KEY_BEAMSET_DOSE in event:
            _, beamset_i, target_i = event
            calculate_preplan_dose_per_fraction(values, window, beamset_i, target_i)

        # Trigger calculate_dose_per_fraction when the number of fractions in a beamset changes
        if KEY_BEAMSET + KEY_FRACTIONS in event:
            _, beamset_i = event
            target_i = None
            calculate_preplan_dose_per_fraction(values, window, beamset_i, target_i)

        if event == 'submit_button':
            num_beamsets = int(values.get(KEY_BEAMSET_COUNT, 1))
            # Display the progress bar
            progress_window, progress_bar = display_progress_bar()
            tree_data, tree_children = run_tests_in_thread(
                rso, True, progress_bar, values)
            progress_window.close()

            extracted_values = extract_preplan_values(window, num_beamsets)
            tab_group = window['tab_group']
            tab1 = on_submit_build_tree(tree_data,
                                        left_width=left_width,
                                        right_width=right_width)
            # Add the new tab to the tab group layout
            tab_group.add_tab(sg.Tab('Review and Logs', tab1,
                                     key='Review and Logs'))
            #
            # Build next tab
            check_box_copy = build_manual_check_box_list(rso, beamsets=[
                rso.beamset.DicomPlanLabel])
            passing_tests, failed_tests = get_manual_failing_tests(
                tree_children, )
            # TODO: Eliminate this
            i = 0
            for p in passing_tests:
                i += 1
                logging.debug(f'Passing test{i}: {p}')
            i = 0
            for f in failed_tests:
                i += 1
                logging.debug(f'Failed test{i}: {f}')
            # TODO END
            tabs = create_tab_manual_checks(check_box_copy, passing_tests,
                                            failed_tests,
                                            hsize=hsize, vsize=vsize)
            for tab in tabs:
                tab_group.add_tab(tab)

            window['Review and Logs'].select()

        #
        # Manual Tab Events
        if type(event) is tuple:
            if KEY_CHECK + KEY_RADIO in event[0]:
                on_manual_radio_button_click(window, event)

        elif event == 'Done':
            is_valid = on_done_button_click(window, values, check_box_copy)
            # Perform the form submission logic
            if is_valid:
                passing_tests, failed_tests = get_manual_failing_tests(tree_children)
                pros_fails = process_failed_tests(window, failed_tests)
                check_dict = process_check_box_values(window, check_box_copy)
                check_dict['Automated Failed Tests'] = pros_fails
                check_dict['Automated Passing Tests'] = passing_tests
                header_data = extract_preplan_values(window, num_beamsets)
                break
        if event == 'Save':
            review_file_name = save_review(rso, get_review_gui_values(window, failed_tests,
                                                                      check_box_copy))

    window.close()

    return check_dict, header_data
