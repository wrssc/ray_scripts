# Import necessary modules and functions
import PySimpleGUI as Sg
import os
import logging
import warnings
from PlanReview.review_definitions import (
    CHECK_BOXES_PHYSICS_REVIEW, CHECK_BOXES_PHYSICS_REVIEW_3D,
    CHECK_BOXES_PHYSICS_REVIEW_VMAT, CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS,
    CHECK_BOXES_PHYSICS_REVIEW_TOMO3D, CHECK_BOXES_PHYSICS_REVIEW_TOMO,
    PROTOCOL_DIR, OUTPUT_DIR, ICON_PRINT, ICON_LOAD, ICON_ERROR, ICON_SAVE,
    ICON_PAUSE, ICON_START, ICON_CANCEL)
from PlanReview.utils import (get_user_name, get_roi_names_from_type,
                              get_user_display_parameters, perform_automated_checks)
from PlanReview.utils.protocol_loading import load_protocols, \
    get_sites, get_all_orders, get_unique_instructions
from PlanReview.utils.constants import *
from PlanReview.guis.gui_report_script_error import report_script_error
from PlanReview.guis.create_preplan_tab import (
    load_preplan, extract_preplan_values, validate_preplan_tab,
    calculate_preplan_dose_per_fraction,
    update_preplan_frequencies, update_preplan_instructions,
    update_preplan_protocols, update_preplan_orders,
    create_preplan_information_tab, update_preplan_beamset_rows,
    update_preplan_target_rows, )
from PlanReview.guis.create_physics_manual_tab import (
    build_manual_check_box_list, get_tests_from_tree,
    create_tab_manual_checks, on_manual_radio_button_click,
    extract_manual_values, load_manual, process_auto_tests,
    process_check_box_values)
import json
import connect

# PRERELEASE:
#
# TODO: ADD CT ORIENTATION TO PREPLAN DIALOG AND CHECK VS RS
# TODO: TPO DROPDOWN NEEDS MORE LINES FOR ORDER SELECTION
# TODO: EXPAND THE SELECTIONS FOR ORDERS!!!
# TODO: ADD TO CRITICAL the CASE, EXAM, PLAN, BEAMSETUID
# TODO: Need a required prompt for all entries in the first tab
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


def log_to_file(dict_of_dicts):
    if type(dict_of_dicts) is dict:
        for key, value in dict_of_dicts.items():
            # Use json.dumps to pretty-print each dictionary
            formatted_dict = json.dumps(value, indent=4)
            logging.debug('Key: %s\nDictionary:\n%s', key, formatted_dict)
    elif isinstance(dict_of_dicts, list):
        for value in dict_of_dicts:
            logging.debug(f'Value from list is: {value}')


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
        return {
            str_key_to_tuple(k): str_key_to_tuple(v) for k, v in value.items()}
    elif isinstance(value, str) and '||' in value:
        return tuple(int(x) if x.isdigit() else x for x in value.split('||'))
    return value


def update_window_key_dict(window, keys):
    for key in keys:
        if key not in window.key_dict:
            window.key_dict[key] = None


def save_review(rso, values, quiet=False):
    logging.debug(f'Values in Save {tuple_key_to_str(values)}')
    file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}_review.json"
    with open(os.path.join(OUTPUT_DIR, file_name), "w") as f:
        json.dump(tuple_key_to_str(values), f)
        if not quiet:
            Sg.popup("Review saved successfully!")
    return file_name


def load_main_window(window, values):
    # All Keys
    # logging.debug(f'Window data is {list(window.AllKeysDict.keys())}')
    ## for key, value in values.items():
    ##     try:
    ##         logging.debug(f"Checking window {key} with {value}")
    ##     except:
    ##         pass
    main_window_data = values.get(KEY_MAIN_WINDOW, {})
    ## logging.debug(f"Loading main window data: {main_window_data}")
    for key, value in main_window_data.items():
        ## logging.debug(f"Updating window {key} with {value}")
        window[key].update(value)


def load_review(window, rso, sites, protocols, instructions, maximum_target_number,
                maximum_beamset_count, check_box_copy, file_name=None):
    if not file_name:
        file_name = f"{rso.patient.PatientID}_" \
                    f"{rso.beamset.DicomPlanLabel}_review.json"
    try:
        with open(os.path.join(OUTPUT_DIR, file_name), "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        Sg.popup("No saved review found!")
        return

    values = str_key_to_tuple(values)
    # Add missing keys to the window.key_dict
    update_window_key_dict(window, values.keys())
    # Load the main window data. Right now it is KEY_USER_COMMENT
    load_main_window(window, values)
    # Load preplan frame contents
    load_preplan(window, values, sites, protocols, instructions,
                 maximum_beamset_count, maximum_target_number)
    # Load the manual (check box) tab contents
    load_manual(window, values, check_box_copy)
    # Determine the number of beamsets
    num_beamsets = int(window[KEY_BEAMSET_COUNT].get()) \
        if window[KEY_BEAMSET_COUNT].get() else 1
    return num_beamsets


def get_review_gui_values(window, passing_tests, failed_tests, check_boxes, comment_box_key):
    """
    Extracts the values entered into the PySimpleGUI dialog and sorts them by keys.

    Parameters:
    - window: PySimpleGUI Window object representing the GUI
    - passing_tests: list of passing tests from the review_definitions module
    - failed_tests: list of failed tests from the review_definitions module
    - check_boxes: dictionary of completed check boxes the user has filled in

    Returns:
    - sorted_values: dictionary of values sorted by keys
    """
    #
    # Get any data from the first tab
    preplan_values = extract_preplan_values(window)
    #
    # Get the data from the comment box if any.
    if window[comment_box_key].get():
        main_window_values = {
            KEY_MAIN_WINDOW: {comment_box_key: window[KEY_USER_COMMENT].get()}}
    else:
        main_window_values = {KEY_MAIN_WINDOW: {KEY_USER_COMMENT: ''}}
    # Get the data from the first tab
    manual_values = extract_manual_values(window, passing_tests, failed_tests, check_boxes)
    manual_values.update(main_window_values)
    sorted_values = merge_dicts(preplan_values, manual_values)

    return sorted_values


# Event handler for "Done" button
def on_done_button_click(window, values, check_boxes):
    # Check if all the required fields are filled in
    is_valid = True
    for key in check_boxes:
        for item in check_boxes[key]:
            radio_y_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}Yes')
            radio_no_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}No')
            radio_na_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}NA')
            input_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}')
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
        Sg.popup_error('Please fill in all the required fields.')
    return is_valid


def sanitize_dict(d):
    return {k: repr(v) for k, v in d.items()}


def on_submit_build_tree(tree_data, tab_width, tab_height, pix_per_char_width, pix_per_line):
    right_width = 10
    left_width = int((tab_width - right_width * pix_per_char_width
                      - 60 * pix_per_char_width) / pix_per_char_width)
    num_rows = int(tab_height / pix_per_line)
    tree_layout = [[Sg.Frame('Automated Review:',
                             [[Sg.Tree(
                                 data=tree_data,
                                 headings=['Result'],
                                 auto_size_columns=False,
                                 num_rows=num_rows,
                                 col0_width=left_width,
                                 col_widths=[right_width],
                                 key='-TREE-',
                                 show_expanded=True,
                                 justification="left",
                                 vertical_scroll_only=True,
                                 expand_x=True,
                                 expand_y=True,
                                 enable_events=True)]],
                             pad=(0, 0),
                             size=(tab_width, tab_height))]]
    return tree_layout


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
        else:
            logging.warning(f'Technique {technique} unknown. No custom checks'
                            f'programmed')
            dict2 = {}
        dict1 = merge_dicts(dict1, dict2)
    return dict1


def get_text_element_size(text: str):
    window = Sg.Window('Invisible Window',
                       [[Sg.Text(text, key='text')],
                        ],
                       alpha_channel=0, finalize=True)
    window.read(timeout=0)
    size_text = window['text'].get_size()
    window.close()
    return size_text


def launch_physics_review_gui(rso):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]

    Returns: None
    """

    # Variable initialization
    failed_tests = []
    passing_tests = []
    check_box_copy = {}
    # GUI setup
    Sg.theme('DefaultNoMoreNagging')
    window_width, window_height, save_space, pix_per_char_width, pix_per_char_height = \
        get_user_display_parameters()
    # In the tree display, set the size of the right column relative to left
    tab_width = 200 * pix_per_char_width
    comment_width_chars = int(
        (window_width - tab_width - 7 * pix_per_char_width) / pix_per_char_width)  # Gap is around 6 char
    # Top and bottom (buttons) frame height
    top_height = 2 * pix_per_char_height
    top_width = tab_width + 5 * pix_per_char_width
    bottom_height = 2 * pix_per_char_height
    bottom_width = tab_width + 5 * pix_per_char_width
    # Tab sizing
    tab_height = window_height - bottom_height - top_height - 4 * pix_per_char_height
    tab_width_chars = int(tab_width / pix_per_char_width) if save_space else tab_width / pix_per_char_width
    #
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

    top_image_size = (156, 56)
    top_pad = ((0, int(tab_width_chars * 0.08)), (1, 1))
    #
    # Top Menu Frame
    top = Sg.Frame('',
                   [[
                       Sg.Button('',
                                 image_filename=ICON_SAVE,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-SAVE-'),
                       Sg.Button('',
                                 image_filename=ICON_LOAD,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-LOAD-'),
                       Sg.Button('',
                                 image_filename=ICON_START,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-START-'),
                       Sg.Button('',
                                 image_filename=ICON_PRINT,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-REPORT-'),
                       Sg.ReadFormButton('',
                                 image_filename=ICON_PAUSE,
                                         image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-PAUSE-'),
                       Sg.Button('',
                                 image_filename=ICON_CANCEL,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-CANCEL-'),
                       Sg.Button('',
                                 image_filename=ICON_ERROR,
                                 image_size=top_image_size,
                                 pad=top_pad,
                                 border_width=2,
                                 key='-ERROR-'),
                   ]],
                   vertical_alignment='center',
                   size=(top_width, top_height),
                   )
    #
    # Comment box size
    comment_line_count = int(window_height / pix_per_char_height)
    #
    # Comment Frame
    side = [[Sg.Text('Comments', text_color='blue', font=('Arial', 12, 'bold'))],
            [Sg.Multiline(default_text='',
                          size=(comment_width_chars, comment_line_count),
                          autoscroll=True,
                          auto_size_text=True,
                          key=KEY_USER_COMMENT)
             ]]
    #
    # Gather the layout
    layout = [
        [
            Sg.Column([
                [top],
                [Sg.TabGroup([[Sg.Tab('External Information',
                                      create_preplan_information_tab(
                                          protocols, sites, orders, instructions,
                                          beamsets, targets, tab_width, tab_height, save_space))
                               ]],
                             key='tab_group')],
                # [bottom]
            ], ),
            # Vertical line to separate the comments from the left side
            Sg.Column([[Sg.VSeperator()]]),
            Sg.Column(side, vertical_alignment='top')
        ],
    ]

    window = Sg.Window(
        f'Plan Review: {get_user_name()}',
        layout,
        resizable=True,
        size=(window_width, window_height))
    review_file_name = None

    while True:  # Event Loop
        event, values = window.read()
        if event in (Sg.WIN_CLOSED, '-CANCEL-'):
            check_list = []
            header_data = {}
            break

        elif event == '-LOAD-':
            num_beamsets = load_review(
                window, rso, sites, protocols, instructions,
                maximum_target_number, max_beamset_count,
                check_box_copy, review_file_name)

            if not num_beamsets:
                num_beamsets = 1

        elif event == '-PAUSE-':
            connect.await_user_input('Review Paused. Resume Script to Continue')
        elif event == '-ERROR-':
            report_script_error(rso)
        #
        # First tab Events
        elif event == KEY_SITE_SELECT:
            site_name = values[KEY_SITE_SELECT]
            update_preplan_protocols(window, site_name, KEY_PROTOCOL_SELECT,
                                     protocols)
        # Update the potential protocol choices based on those for this site
        elif event == KEY_PROTOCOL_SELECT:
            protocol = protocols[values[KEY_PROTOCOL_SELECT]]
            update_preplan_orders(window, protocol, KEY_ORDER_SELECT)
        elif event == KEY_ORDER_SELECT:
            order_name = values[KEY_ORDER_SELECT]
            update_preplan_frequencies(window, protocol, order_name)
            update_preplan_instructions(window, protocol, order_name,
                                        instructions)

        # Trigger update_beamset_rows when the number of beamsets changes
        elif KEY_BEAMSET_COUNT in event:
            num_beamsets = int(values[event])
            update_preplan_beamset_rows(
                window, values, num_beamsets, max_beamset_count,
                maximum_target_number)

        if KEY_BEAMSET_TARGET_COUNT in event:
            _, beamset_i = event
            num_targets = int(values[event])
            update_preplan_target_rows(window, num_targets, beamset_i,
                                       maximum_target_number)

        # Trigger calculate_dose_per_fraction when the dose value changes
        if KEY_BEAMSET_DOSE in event:
            _, beamset_i, target_i = event
            calculate_preplan_dose_per_fraction(
                values, window, beamset_i, target_i)

        # Trigger calculate_dose_per_fraction when the number of fractions in a beamset changes
        if KEY_BEAMSET + KEY_FRACTIONS in event:
            _, beamset_i = event
            target_i = None
            calculate_preplan_dose_per_fraction(values, window, beamset_i, target_i)

        if event == '-START-':
            preplan_valid = validate_preplan_tab(window)
            if preplan_valid:
                #
                # Get the beamset info for review
                tree_data, tree_children = perform_automated_checks(
                    rso, do_physics_review=True, values=values,
                    display_progress=True, beamsets=beamsets)
                tab_group = window['tab_group']
                tab1 = on_submit_build_tree(
                    tree_data, tab_width, tab_height, pix_per_char_width, pix_per_char_height)
                # Add the new tab to the tab group layout
                tab_group.add_tab(Sg.Tab('Review and Logs', tab1,
                                         key='Review and Logs'))
                #
                # Build next tab
                # TODO: USERS MAY WANT SEPARATE TESTS FOR EACH BEAMSET
                check_box_copy = build_manual_check_box_list(rso, beamsets=[
                    rso.beamset.DicomPlanLabel])

                passing_tests, failed_tests = get_tests_from_tree(tree_children)
                tabs = create_tab_manual_checks(check_box_copy, passing_tests,
                                                failed_tests,
                                                tab_width, tab_height,
                                                pix_per_char_width, pix_per_char_height, save_space)
                for tab in tabs:
                    tab_group.add_tab(tab)

                window['Review and Logs'].select()

        #
        # Manual Tab Events
        if type(event) is tuple:
            if KEY_CHECK + KEY_RADIO in event[0]:
                on_manual_radio_button_click(window, event)

        elif event == '-REPORT-':
            is_valid = on_done_button_click(window, values, check_box_copy)
            # Perform the form submission logic
            if is_valid:
                # Save the review
                review_file_name = save_review(
                    rso,
                    get_review_gui_values(window, passing_tests, failed_tests,
                                          check_box_copy, KEY_USER_COMMENT),
                    quiet=True)

                passing_tests, failed_tests = get_tests_from_tree(tree_children)
                pros_pass = process_auto_tests(window, passing_tests)
                pros_fails = process_auto_tests(window, failed_tests)
                check_list = process_check_box_values(window, check_box_copy)
                check_list.extend(pros_fails)
                check_list.extend(pros_pass)
                header_data = extract_preplan_values(window)
                break
        if event == '-SAVE-':
            review_file_name = save_review(
                rso, get_review_gui_values(window, passing_tests, failed_tests,
                                           check_box_copy, KEY_USER_COMMENT))

    window.close()

    return check_list, header_data
