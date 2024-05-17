from PlanReview.guis.create_preplan_tab import extract_values_preplan_tab
from PlanReview.guis.create_side_panel import extract_values_side_panel
from PlanReview.guis.create_physics_manual_tab import (
    extract_values_manual_tab, get_tests_from_tree, process_check_box_values, process_auto_tests)
from PlanReview.guis.gui_qa_form import extract_values_qa_form, build_qa_form
from PlanReview.utils.python_utilities import merge_dicts


def get_review_gui_values(gui_state_manager, values):
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
    if gui_state_manager.qa_form_accessible:
        qa_form_values = extract_values_qa_form(gui_state_manager.window)
        sorted_values = merge_dicts(sorted_values, qa_form_values)

    return sorted_values


def get_header_checklist_qa_values(gui_state_manager, values):
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
    if gui_state_manager.qa_form_accessible:
        qa_form_data = build_qa_form(gui_state_manager.rso, gui_state_manager.window)
    else:
        qa_form_data = None
    sidepanel_data = extract_values_side_panel(gui_state_manager.window)
    header_data = merge_dicts(preplan_data, sidepanel_data)

    return header_data,