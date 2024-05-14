# Import necessary modules and functions
import os
import logging
import json
import PySimpleGUI as Sg
from PlanReview.review_definitions import (PROTOCOL_DIR, OUTPUT_DIR)
from PlanReview.utils import (get_user_name, get_roi_names_from_type,
                              get_user_display_parameters, perform_automated_checks)
from PlanReview.utils.protocol_loading import load_protocols, \
    get_sites, get_all_orders, get_unique_instructions
from PlanReview.utils.constants import *
from PlanReview.utils.python_utilities import (update_window_key_dict, merge_dicts)
from PlanReview.utils.io_file_utils import (str_key_to_tuple, save_review)
from PlanReview.guis.gui_report_script_error import report_script_error
from PlanReview.guis.create_side_panel import (
    create_side_panel, load_side_panel, extract_values_side_panel,
    on_side_panel_radio_button_click, is_valid_side_panel)
from PlanReview.guis.gui_qa_form import (
    build_qa_form, extract_values_qa_form, load_qa_form, on_checker_image_click)
from PlanReview.guis.create_preplan_tab import (
    load_preplan, extract_values_preplan_tab, validate_preplan_tab,
    calculate_preplan_dose_per_fraction,
    update_preplan_frequencies, update_preplan_instructions,
    update_preplan_protocols, update_preplan_orders,
    create_tab_preplan_information, update_preplan_beamset_rows,
    update_preplan_target_rows)
from PlanReview.guis.build_tree import on_submit_build_tree
from PlanReview.guis.create_physics_manual_tab import (
    build_manual_check_box_list, get_tests_from_tree,
    create_tab_manual_checks, on_manual_radio_button_click,
    extract_values_manual_tab, load_manual, process_auto_tests,
    process_check_box_values, is_valid_manual_tab, is_visible_tab)
from PlanReview.guis.gui_top_buttons import build_top_buttons
from PlanReview.guis.gui_bottom_buttons import build_bottom_buttons
from PlanReview.guis.gui_ditto_wrapper import get_ditto_tab, on_ditto_element_click


def load_review(gui_state_manager, sites, protocols, instructions, maximum_target_number,
                maximum_beamset_count, file_name=None, qa_form_accessible=False):
    if not file_name:
        file_name = f"{gui_state_manager.rso.patient.PatientID}_" \
                    f"{gui_state_manager.rso.beamset.DicomPlanLabel}_review.json"
    try:
        with open(os.path.join(OUTPUT_DIR, gui_state_manager.rso.patient.PatientID, file_name), "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        Sg.popup("No saved review found!")
        return

    values = str_key_to_tuple(values)
    # Add missing keys to the window.key_dict
    update_window_key_dict(gui_state_manager.window, values.keys())
    # Load preplan frame contents
    load_preplan(gui_state_manager.window, values, sites, protocols, instructions,
                 maximum_beamset_count, maximum_target_number)
    # Load the manual (check box) tab contents
    load_manual(gui_state_manager.window, values, gui_state_manager.check_box_copy)
    # Load the main window data.
    load_side_panel(gui_state_manager.window, values)
    # Load the QA form
    if qa_form_accessible:
        load_qa_form(gui_state_manager.window, values)
    # return num_beamsets


def get_review_gui_values(gui_state_manager, values, qa_form_accessible=False):
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
    preplan_values = extract_values_preplan_tab(gui_state_manager.window)

    # Get values from the side tab
    side_frame_values = extract_values_side_panel(gui_state_manager.window)

    # Get the data from the first tab
    manual_values = extract_values_manual_tab(values, gui_state_manager.passing_tests,
                                              gui_state_manager.failed_tests, gui_state_manager.check_box_copy)

    # Merge them into a single dictionary
    sorted_values = merge_dicts(side_frame_values, preplan_values)
    sorted_values = merge_dicts(sorted_values, manual_values)
    # Get values from the qa form
    if qa_form_accessible:
        qa_form_values = extract_values_qa_form(gui_state_manager.window)
        sorted_values = merge_dicts(sorted_values, qa_form_values)

    return sorted_values


# Event handler for "Done" button
def on_done_button_click(gui_state_manager, values):
    # Check if all the required fields are filled in
    manual_valid = is_valid_manual_tab(gui_state_manager.window, values, gui_state_manager.check_box_copy,
                                       gui_state_manager.failed_tests)
    side_valid = is_valid_side_panel(gui_state_manager.window, values)
    is_valid = all([manual_valid, side_valid])
    return is_valid


def initialize_gui_dict():
    gui_dict = {}
    window_width, window_height, save_space, pix_per_char_width, pix_per_char_height = \
        get_user_display_parameters()
    gui_dict['window_width'] = window_width
    gui_dict['window_height'] = window_height
    gui_dict['save_space'] = save_space
    gui_dict['pix_per_char_width'] = pix_per_char_width
    gui_dict['pix_per_char_height'] = pix_per_char_height
    logging.info(f'physics review gui launched with '
                 f'screen width x height: {window_width} x {window_height}. '
                 f'Pixel character width x height: {pix_per_char_width} x'
                 f'{pix_per_char_height}. Space Save {save_space}')
    if save_space:
        gui_dict['tab_width'] = 120 * pix_per_char_width  # Based on top window width
        # Width of sidebar with 30 pix of greyspace
        gui_dict['sidebar_width'] = int(window_width - gui_dict['tab_width'] - 30)
        # Gap is around 6 char
        gui_dict['comment_width_chars'] = int(gui_dict['sidebar_width'] - 120) // pix_per_char_width
        gui_dict['user_text_width'] = 20
        gui_dict['check_character_width'] = 70  # Character wrap limit in check boxes
    else:
        gui_dict['tab_width'] = 154 * pix_per_char_width
        gui_dict['sidebar_width'] = int(window_width - gui_dict['tab_width'] - 30)
        gui_dict['comment_width_chars'] = int(gui_dict['sidebar_width'] - 200) // pix_per_char_width
        gui_dict['user_text_width'] = 24
        gui_dict['check_character_width'] = 96
    # Top and bottom (buttons) frame height
    gui_dict['top_height'] = 2 * pix_per_char_height
    gui_dict['top_width'] = gui_dict['tab_width'] + int(5.1 * pix_per_char_width)
    gui_dict['tab_font'] = ('Helvetica', '8', 'bold') if save_space else None
    gui_dict['bottom_height'] = 2 * pix_per_char_height
    gui_dict['bottom_width'] = gui_dict['tab_width'] + int(5.1 * pix_per_char_width)
    # Tab sizing
    gui_dict['tab_height'] = window_height - gui_dict['top_height'] - 4 * pix_per_char_height - gui_dict[
        'bottom_height']
    return gui_dict


def handle_already_started_tests(gui_state_manager, values):
    """
    Handle the case where the tests have already been started.

    Returns:
        Boolean indicating if the GUI needs to be relaunched
    """
    sg_popup = Sg.popup_yes_no('Tests already started! Clear the review and start over?',
                               title='Warning',
                               keep_on_top=True,
                               font=('Helvetica', '12', 'bold'),
                               button_color=('black', 'white'),
                               background_color='white')
    if sg_popup == 'Yes':
        save_review(gui_state_manager.rso,
                    get_review_gui_values(gui_state_manager, values),
                    quiet=True)
        Sg.popup('Review saved to file. Load prior results and start tests after GUI is relaunched', )
        gui_state_manager.window.close()
        return True
    else:
        return False


def get_ditto_tab_list(gui_state_manager, beamsets):
    """
    Get the ditto tab list and match trees.
    Args:
        gui_state_manager:
        beamsets:

    Returns:

    """
    ditto_tab_list = []
    match_trees = {}
    for beamset in gui_state_manager.rso.plan.BeamSets:
        if "Tomo" not in beamset.DeliveryTechnique:
            ditto_tab_list, match_trees = get_ditto_tab(gui_state_manager.gui_dict['tab_width'],
                                                        gui_state_manager.gui_dict['tab_height'], beamsets)
    return ditto_tab_list, match_trees


def handle_start_event(gui_state_manager, beamsets, values):
    """
    Handle the '-START-' event in the GUI.

    Parameters:
        gui_state_manager: EventContext object containing the window, rso, gui_dict, and tests_started
        beamsets: List of beamset names
        values: Values from the GUI

    Returns:
    """

    preplan_valid = validate_preplan_tab(gui_state_manager.window)
    if preplan_valid:
        # Get the beamset info for review
        tree_data, gui_state_manager.tree_children = perform_automated_checks(
            gui_state_manager.rso, do_physics_review=True, values=values,
            display_progress=True, beamsets=beamsets)
        gui_state_manager.rso.patient.Save()
        ditto_tab_list, match_trees = get_ditto_tab_list(gui_state_manager, beamsets)
        tab_group = gui_state_manager.window['tab_group']
        tab1 = on_submit_build_tree(tree_data, gui_state_manager.gui_dict['tab_width'],
                                    gui_state_manager.gui_dict['tab_height'],
                                    gui_state_manager.gui_dict['pix_per_char_width'],
                                    gui_state_manager.gui_dict['pix_per_char_height'])
        # Add the new tab to the tab group layout
        tab_group.add_tab(Sg.Tab('Logs', tab1,
                                 key='Review and Logs',
                                 tooltip='Tree view of automated tests and log files generated by scripts',
                                 font=gui_state_manager.gui_dict['tab_font']))
        # Build next tab
        gui_state_manager.check_box_copy = build_manual_check_box_list(gui_state_manager.rso, beamsets=beamsets,
                                                                       chars_per_line=gui_state_manager.gui_dict[
                                                                           'check_character_width'])

        gui_state_manager.passing_tests, gui_state_manager.failed_tests = get_tests_from_tree(
            gui_state_manager.tree_children)
        tabs = create_tab_manual_checks(gui_state_manager.check_box_copy, gui_state_manager.passing_tests,
                                        gui_state_manager.failed_tests,
                                        gui_state_manager.gui_dict['tab_width'],
                                        gui_state_manager.gui_dict['tab_height'],
                                        gui_state_manager.gui_dict['pix_per_char_width'],
                                        gui_state_manager.gui_dict['pix_per_char_height'],
                                        gui_state_manager.gui_dict['save_space'],
                                        gui_state_manager.gui_dict['user_text_width'],
                                        gui_state_manager.gui_dict['check_character_width'])
        for tab in tabs:
            if is_visible_tab(tab, gui_state_manager.window):
                tab_group.add_tab(tab)
        for tab in ditto_tab_list:
            if tab:
                tab_group.add_tab(tab)

        gui_state_manager.window['Review and Logs'].select()
        gui_state_manager.tests_started = True


class GuiState:
    def __init__(self, rso, relaunch=False, tests_started=False):
        self.window = None
        self.rso = rso
        self.gui_dict = {}
        self.tests_started = tests_started
        self.check_list = []
        self.check_box_copy = {}
        self.passing_tests = []
        self.failed_tests = []
        self.review_file_name = None
        self.tree_children = None
        self.match_trees = None
        self.qa_form_accessible = True
        self.relaunch = relaunch


def launch_physics_review_gui(rso, relaunch=False):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
    - relaunch: Boolean indicating if the GUI starts from scratch or if it is relaunched

    Returns: None
    """
    import connect
    qa_form_accessible = True
    # Context initialization
    gui_state_manager = GuiState(rso, relaunch=relaunch, tests_started=False)
    # Variable initialization
    header_data = {}
    qa_form_data = {}
    # tree_children = None
    match_trees = None
    # GUI setup
    Sg.theme('DefaultNoMoreNagging')
    gui_state_manager.gui_dict = initialize_gui_dict()

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
    # Top frame
    top = build_top_buttons(gui_state_manager.gui_dict['save_space'])
    # Top frame
    bottom = build_bottom_buttons(gui_state_manager.gui_dict['save_space'])
    # Gather the layout
    layout = [
        [
            Sg.Column([
                [top],
                [Sg.TabGroup([[Sg.Tab('ARIA Info',
                                      create_tab_preplan_information(
                                          protocols, sites, orders, instructions,
                                          beamsets, targets,
                                          gui_state_manager.gui_dict['tab_width'],
                                          gui_state_manager.gui_dict['tab_height'],
                                          gui_state_manager.gui_dict['save_space']),
                                      font=gui_state_manager.gui_dict['tab_font'],
                                      tooltip='Enter information from ARIA documents, '
                                              'which will be used in subsequent automated tests.')
                               ]],
                             key='tab_group')],
                [bottom]
            ],
            ),
            # Side Panel declaration
            Sg.Column(create_side_panel(
                gui_state_manager.gui_dict['comment_width_chars'],
                gui_state_manager.gui_dict['window_height'],
                gui_state_manager.gui_dict['pix_per_char_height']),
                size=(gui_state_manager.gui_dict['sidebar_width'],
                      gui_state_manager.gui_dict['window_height'])),
        ],
    ]

    gui_state_manager.window = Sg.Window(
        f'{get_user_name()}> Plan Review:{" " * 5}{rso.patient.Name}{" " * 5}{rso.patient.PatientID}',
        layout,
        resizable=True,
        size=(gui_state_manager.gui_dict['window_width'], gui_state_manager.gui_dict['window_height']), )
    review_file_name = None

    while True:  # Event Loop
        event, values = gui_state_manager.window.read()
        if event in (Sg.WIN_CLOSED, '-CANCEL-'):
            return {}
        # Load Event
        elif event == '-LOAD-':
            load_review(gui_state_manager, sites, protocols, instructions,
                        maximum_target_number, max_beamset_count, review_file_name)
        elif event == '-PAUSE-':
            connect.await_user_input('Review Paused. Resume Script Execution to Continue')
        elif event == '-ERROR-':
            report_script_error(gui_state_manager.rso)
        #
        # First tab Events
        elif event == KEY_SITE_SELECT:
            site_name = values[KEY_SITE_SELECT]
            update_preplan_protocols(gui_state_manager.window, site_name, KEY_PROTOCOL_SELECT,
                                     protocols)
        # Update the potential protocol choices based on those for this site
        elif event == KEY_PROTOCOL_SELECT:
            protocol = protocols[values[KEY_PROTOCOL_SELECT]]
            update_preplan_orders(gui_state_manager.window, protocol, KEY_ORDER_SELECT)
        elif event == KEY_ORDER_SELECT:
            order_name = values[KEY_ORDER_SELECT]
            update_preplan_frequencies(gui_state_manager.window, protocol, order_name)
            update_preplan_instructions(gui_state_manager.window, protocol, order_name,
                                        instructions)
        # Trigger update_beamset_rows when the number of beamsets changes
        elif KEY_BEAMSET_COUNT in event:
            num_beamsets = int(values[event])
            update_preplan_beamset_rows(
                gui_state_manager.window, values, num_beamsets, max_beamset_count,
                maximum_target_number)

        if KEY_BEAMSET_TARGET_COUNT in event:
            _, beamset_i = event
            num_targets = int(values[event])
            update_preplan_target_rows(gui_state_manager.window, num_targets, beamset_i,
                                       maximum_target_number)

        # Trigger calculate_dose_per_fraction when the dose value changes
        if KEY_BEAMSET_DOSE in event:
            _, beamset_i, target_i = event
            calculate_preplan_dose_per_fraction(
                values, gui_state_manager.window, beamset_i, target_i)

        # Trigger calculate_dose_per_fraction when the number of fractions in a beamset changes
        if KEY_BEAMSET + KEY_FRACTIONS in event:
            _, beamset_i = event
            target_i = None
            calculate_preplan_dose_per_fraction(values, gui_state_manager.window, beamset_i, target_i)

        if event == '-START-':
            if gui_state_manager.tests_started:
                relaunch = handle_already_started_tests(gui_state_manager, values)
                if relaunch:
                    break
                else:
                    continue
            handle_start_event(gui_state_manager, beamsets, values)
        # Update to Ditto
        # Check if the event starts with '-DITTO_TREE_' and if there are beamsets to process
        print(event)
        if '-APTR_TREE_' in event and beamsets and match_trees:
            on_ditto_element_click(gui_state_manager.window, values, event, beamsets, match_trees)
        #
        # Plan Revision Events
        side_panel_event = f"{KEY_PROCEED_REVISE}{KEY_RADIO}"
        if side_panel_event in event:
            on_side_panel_radio_button_click(gui_state_manager.window, event)
        # #
        # Manual Tab Events
        if type(event) is tuple:
            if KEY_CHECK + KEY_RADIO in event[0]:
                on_manual_radio_button_click(gui_state_manager.window, event)

        elif event == '-REPORT-':
            # Retrieve the passing and failing tests
            if not gui_state_manager.tree_children:
                Sg.popup('No tests have been run yet!')
                continue
            gui_state_manager.passing_tests, gui_state_manager.failed_tests = get_tests_from_tree(
                gui_state_manager.tree_children)
            is_valid = on_done_button_click(gui_state_manager, values)
            # Perform the form submission logic
            if is_valid:
                # Save the review
                save_review(
                    gui_state_manager.rso,
                    get_review_gui_values(gui_state_manager, values),
                    suffix="_review.json", quiet=True)
                #
                # Retrieve data from the check-boxes and automated tests
                gui_state_manager.passing_tests, gui_state_manager.failed_tests = get_tests_from_tree(
                    gui_state_manager.tree_children)
                gui_state_manager.check_list = process_check_box_values(gui_state_manager.window, values,
                                                                        gui_state_manager.check_box_copy)
                gui_state_manager.check_list.extend(
                    process_auto_tests(gui_state_manager.window, gui_state_manager.failed_tests))
                gui_state_manager.check_list.extend(
                    process_auto_tests(gui_state_manager.window, gui_state_manager.passing_tests))
                #
                # Retrieve data from the first tab and side panel
                preplan_data = extract_values_preplan_tab(gui_state_manager.window)
                if qa_form_accessible:
                    qa_form_data = build_qa_form(gui_state_manager.rso, gui_state_manager.window)
                else:
                    qa_form_data = None
                sidepanel_data = extract_values_side_panel(gui_state_manager.window)
                header_data = merge_dicts(preplan_data, sidepanel_data)
                break
        if event == '-SAVE-':
            review_file_name = save_review(
                gui_state_manager.rso, get_review_gui_values(gui_state_manager, values))
        if qa_form_accessible:
            if event == '-CHECKER-IMAGE-':
                on_checker_image_click(gui_state_manager.window, event)
                on_side_panel_radio_button_click(gui_state_manager.window, event)

    gui_state_manager.window.close()
    if relaunch:
        launch_physics_review_gui(gui_state_manager.rso, relaunch=True)

    if gui_state_manager.check_list:
        if qa_form_accessible:
            return_dict = {KEY_TESTS: gui_state_manager.check_list, KEY_HEADER: header_data, KEY_QA_FORM: qa_form_data}
        else:
            return_dict = {KEY_TESTS: gui_state_manager.check_list, KEY_HEADER: header_data, KEY_QA_FORM: {}}
    else:
        return_dict = {}

    return return_dict
