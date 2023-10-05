# Import necessary modules and functions
import PySimpleGUI as Sg
import os
import logging
from PlanReview.review_definitions import (
    CHECK_BOXES_PHYSICS_REVIEW, CHECK_BOXES_PHYSICS_REVIEW_3D,
    CHECK_BOXES_PHYSICS_REVIEW_VMAT, CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS,
    CHECK_BOXES_PHYSICS_REVIEW_TOMO3D, CHECK_BOXES_PHYSICS_REVIEW_TOMO,
    PROTOCOL_DIR, OUTPUT_DIR, ICON_PRINT, ICON_LOAD, ICON_ERROR, ICON_SAVE,
    ICON_PAUSE, ICON_START, ICON_CANCEL, ICON_SMALL_PRINT, ICON_SMALL_LOAD,
    ICON_SMALL_ERROR, ICON_SMALL_SAVE, ICON_SMALL_PAUSE, ICON_SMALL_START,
    ICON_SMALL_CANCEL)
from PlanReview.utils import (get_user_name, get_roi_names_from_type,
                              get_user_display_parameters, perform_automated_checks)
from PlanReview.utils.protocol_loading import load_protocols, \
    get_sites, get_all_orders, get_unique_instructions
from PlanReview.utils.constants import *
from PlanReview.guis.gui_report_script_error import report_script_error
from PlanReview.guis.create_side_panel import (
    create_side_panel, load_side_panel, extract_values_side_panel,
    on_side_panel_radio_button_click, is_valid_side_panel)
from PlanReview.guis.create_preplan_tab import (
    load_preplan, extract_values_preplan_tab, validate_preplan_tab,
    calculate_preplan_dose_per_fraction,
    update_preplan_frequencies, update_preplan_instructions,
    update_preplan_protocols, update_preplan_orders,
    create_tab_preplan_information, update_preplan_beamset_rows,
    update_preplan_target_rows)
from PlanReview.guis.create_physics_manual_tab import (
    build_manual_check_box_list, get_tests_from_tree,
    create_tab_manual_checks, on_manual_radio_button_click,
    extract_values_manual_tab, load_manual, process_auto_tests,
    process_check_box_values, is_valid_manual_tab, is_visible_tab)
import json
import connect
from typing import Dict

"""

"""


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
    # logging.debug(f'Values in Save {tuple_key_to_str(values)}')
    patient_output_dir = os.path.join(OUTPUT_DIR,rso.patient.PatientID)
    if not os.path.exists(patient_output_dir):
        os.makedirs(patient_output_dir)
    if os.path.exists(OUTPUT_DIR):
        file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}_review.json"
        with open(os.path.join(patient_output_dir, file_name), "w") as f:
            json.dump(tuple_key_to_str(values), f)
            if not quiet:
                Sg.popup("Review saved successfully!")
        return file_name
    else:
        logging.error("Output directory does not exist.")
        return None


def load_review(window, rso, sites, protocols, instructions, maximum_target_number,
                maximum_beamset_count, check_box_copy, file_name=None):
    if not file_name:
        file_name = f"{rso.patient.PatientID}_" \
                    f"{rso.beamset.DicomPlanLabel}_review.json"
    try:
        with open(os.path.join(OUTPUT_DIR,rso.patient.PatientID,file_name), "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        Sg.popup("No saved review found!")
        return

    values = str_key_to_tuple(values)
    # Add missing keys to the window.key_dict
    update_window_key_dict(window, values.keys())
    # Load preplan frame contents
    load_preplan(window, values, sites, protocols, instructions,
                 maximum_beamset_count, maximum_target_number)
    # Load the manual (check box) tab contents
    load_manual(window, values, check_box_copy)
    # Determine the number of beamsets
    num_beamsets = int(window[KEY_BEAMSET_COUNT].get()) \
        if window[KEY_BEAMSET_COUNT].get() else 1
    # Load the main window data.
    load_side_panel(window, values)
    return num_beamsets


def get_review_gui_values(window, passing_tests, failed_tests, check_boxes):
    """
    Extracts the values entered into the PySimpleGUI dialog and sorts them by keys.
    This is used for saving the review to file and for the report

    Parameters:
    - window: PySimpleGUI Window object representing the GUI
    - passing_tests: list of passing tests from the review_definitions module
    - failed_tests: list of failed tests from the review_definitions module
    - check_boxes: dictionary of completed check boxes the user has filled in

    Returns:
    - sorted_values: dictionary of values sorted by keys
    """

    # Get any data from the first tab
    preplan_values = extract_values_preplan_tab(window)

    # Get values from the side tab
    side_frame_values = extract_values_side_panel(window)

    # Get the data from the first tab
    manual_values = extract_values_manual_tab(window, passing_tests, failed_tests, check_boxes)

    # Merge them into a single dictionary
    sorted_values = merge_dicts(side_frame_values, preplan_values)
    sorted_values = merge_dicts(sorted_values, manual_values)

    return sorted_values


# Event handler for "Done" button
def on_done_button_click(window, values, check_boxes):
    # Check if all the required fields are filled in
    manual_valid = is_valid_manual_tab(window, values, check_boxes)
    side_valid = is_valid_side_panel(window, values)
    is_valid = all([manual_valid, side_valid])
    return is_valid


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


def launch_physics_review_gui(rso):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]

    Returns: None
    """

    # Variable initialization
    ui = connect.get_current('ui')
    failed_tests = []
    passing_tests = []
    check_box_copy = {}
    # GUI setup
    Sg.theme('DefaultNoMoreNagging')
    window_width, window_height, save_space, pix_per_char_width, pix_per_char_height = \
        get_user_display_parameters()

    # In the tree display, set the size of the right column relative to left
    if save_space:
        tab_width = 118 * pix_per_char_width  # Based on top window width
        sidebar_width = int(window_width - tab_width - 30)  # Width of sidebar with 30 pix of greyspace
        comment_width_chars = int(sidebar_width - 114) // pix_per_char_width  # Gap is around 6 char
    else:
        tab_width = 184 * pix_per_char_width  # Based on top window width
        sidebar_width = int(window_width - tab_width - 30)  # Width of sidebar with 30 pix of greyspace
        comment_width_chars = int(sidebar_width - 200) // pix_per_char_width  # Gap is around 6 char
    # Top and bottom (buttons) frame height
    top_height = 2 * pix_per_char_height
    top_width = tab_width + int(5.1 * pix_per_char_width)
    # Tab sizing
    tab_height = window_height - top_height - 4 * pix_per_char_height
    logging.info(f'physics review gui launched with '
                 f'screen width x height: {window_width} x {window_height}. '
                 f'Pixel character width x height: {pix_per_char_width} x'
                 f'{pix_per_char_height}. Space Save {save_space}')
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

    top_image_size = (104, 22) if save_space else (156, 56)
    top_subsample = 1 if save_space else 1
    top_border = 0 if save_space else 2
    top_pad = ((0, 1), (1, 1))
    tab_font = ('Helvetica', '8', 'bold') if save_space else None
    #
    small_icons = {
        "-SAVE-": ICON_SMALL_SAVE,
        "-LOAD-": ICON_SMALL_LOAD,
        "-START-": ICON_SMALL_START,
        "-REPORT-": ICON_SMALL_PRINT,
        "-PAUSE-": ICON_SMALL_PAUSE,
        "-CANCEL-": ICON_SMALL_CANCEL,
        "-ERROR-": ICON_SMALL_ERROR,
    }

    large_icons = {
        "-SAVE-": ICON_SAVE,
        "-LOAD-": ICON_LOAD,
        "-START-": ICON_START,
        "-REPORT-": ICON_PRINT,
        "-PAUSE-": ICON_PAUSE,
        "-CANCEL-": ICON_CANCEL,
        "-ERROR-": ICON_ERROR,
    }

    icons = small_icons if save_space else large_icons

    top_buttons = [Sg.Button('', image_filename=icons[key],
                             image_size=top_image_size,
                             image_subsample=top_subsample,
                             pad=top_pad,
                             border_width=top_border,
                             key=key)
                   for key in icons.keys()]

    top = Sg.Frame('',
                   [top_buttons],
                   vertical_alignment='center',
                   size=(top_width, top_height),
                   )
    # Gather the layout
    layout = [
        [
            Sg.Column([
                [top],
                [Sg.TabGroup([[Sg.Tab('ARIA Info',
                                      create_tab_preplan_information(
                                          protocols, sites, orders, instructions,
                                          beamsets, targets, tab_width, tab_height, save_space),
                                      font=tab_font,
                                      tooltip='Enter information from ARIA documents, '
                                              'which will be used in subsequent automated tests.')
                               ]],
                             key='tab_group')],
            ], ),
            # Side Panel declaration
            Sg.Column(create_side_panel(comment_width_chars,
                                        window_height,
                                        pix_per_char_height),
                      vertical_alignment='top',
                      size=(sidebar_width, window_height))
        ],
    ]

    window = Sg.Window(
        f'{get_user_name()}> Plan Review:{" " * 5}{rso.patient.Name}{" " * 5}{rso.patient.PatientID}',
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
        # Load Event
        elif event == '-LOAD-':
            num_beamsets = load_review(
                window, rso, sites, protocols, instructions,
                maximum_target_number, max_beamset_count,
                check_box_copy, review_file_name)

            if not num_beamsets:
                num_beamsets = 1
        elif event == '-PAUSE-':
            connect.await_user_input('Review Paused. Resume Script Execution to Continue')
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
                tab_group.add_tab(Sg.Tab('Logs', tab1,
                                         key='Review and Logs',
                                         tooltip='Tree view of automated tests and log files generated by scripts',
                                         font=tab_font))
                #
                # Build next tab
                check_box_copy = build_manual_check_box_list(rso, beamsets=[
                    rso.beamset.DicomPlanLabel])

                passing_tests, failed_tests = get_tests_from_tree(tree_children)
                tabs = create_tab_manual_checks(check_box_copy, passing_tests,
                                                failed_tests,
                                                tab_width, tab_height,
                                                pix_per_char_width, pix_per_char_height, save_space)
                for tab in tabs:
                    if is_visible_tab(tab, window):
                        tab_group.add_tab(tab)

                window['Review and Logs'].select()

        #
        # Plan Revision Events
        side_panel_event = f"{KEY_PROCEED_REVISE}{KEY_RADIO}"
        if side_panel_event in event:
            on_side_panel_radio_button_click(window, event)
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
                    get_review_gui_values(window, passing_tests, failed_tests, check_box_copy),
                    quiet=True)

                #
                # Retrieve data from the check-boxes and automated tests
                passing_tests, failed_tests = get_tests_from_tree(tree_children)
                check_list = process_check_box_values(window, check_box_copy)
                check_list.extend(process_auto_tests(window, failed_tests))
                check_list.extend(process_auto_tests(window, passing_tests))
                #
                # Retrieve data from the first tab and side panel
                preplan_data = extract_values_preplan_tab(window)
                sidepanel_data = extract_values_side_panel(window)
                header_data = merge_dicts(preplan_data, sidepanel_data)
                break
        if event == '-SAVE-':
            review_file_name = save_review(
                rso, get_review_gui_values(window, passing_tests, failed_tests,
                                           check_box_copy))

    window.close()

    return check_list, header_data
