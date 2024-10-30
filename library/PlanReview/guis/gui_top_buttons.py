import PySimpleGUI as Sg
import logging
from PlanReview.review_definitions import (
    ICON_SAVE, ICON_LOAD, ICON_START, ICON_PRINT, ICON_CANCEL, ICON_ERROR, ICON_SUBMIT,
    ICON_SMALL_SAVE, ICON_SMALL_LOAD, ICON_SMALL_START, ICON_SMALL_PRINT,
    ICON_SMALL_CANCEL, ICON_SMALL_ERROR, ICON_SMALL_FINAL,
    ICON_FINAL, ICON_SMALL_SUBMIT)
from PlanReview.utils.io_file_utils import save_review
from PlanReview.guis.progress_bar_tests import display_progress_bar
from PlanReview.guis.parse_gui_values import get_review_gui_values
from PlanReview.guis.create_preplan_tab import (
    validate_preplan_tab, find_site_technique_from_beamset_name, update_preplan_gui_state)
from PlanReview.utils import perform_automated_checks
from PlanReview.guis.build_tree import on_submit_build_tree
from PlanReview.guis.gui_ditto_wrapper import get_ditto_tab
from PlanReview.guis.create_physics_manual_tab import (
    is_visible_tab, build_manual_check_box_list, create_tab_manual_checks,
    is_valid_manual_tab, get_tests_from_tree)
from PlanReview.guis.gui_report_script_error import report_script_error
from PlanReview.guis.parse_gui_values import get_header_checklist_qa_values
from PlanReview.guis.create_side_panel import (
    is_valid_dosimetry_panel, is_valid_physics_panel, side_panel_proceed_qi_true, side_panel_revision_true,
    generate_and_distribute_qi_issue_report, generate_and_distribute_revision_report)
from PlanReview.guis.review_loader import load_review
from library.api.api_user_functions import final_dose


def build_top_buttons(save_space, review_type='Physics'):
    # Top dimensions
    top_image_size = (90, 25) if save_space else (110, 30)
    top_subsample = 1 if save_space else 1
    top_border = 0 if save_space else 0  # 2
    top_pad = ((8, 7), (0, 0)) if save_space else ((12, 12), (0, 0))
    #
    if review_type == 'Physics':
        small_icons = {
            "-SAVE-": (ICON_SMALL_SAVE, "Save the current view"),
            "-LOAD-": (ICON_SMALL_LOAD, "Load a previously saved view"),
            "-START-": (ICON_SMALL_START, "Start the automated tests"),
            "-REPORT-": (ICON_SMALL_PRINT, "Save the current view and create a report"),
            "-CANCEL-": (ICON_SMALL_CANCEL, "Cancel the script execution"),
            "-ERROR-": (ICON_SMALL_ERROR, "Generate an error report"),
        }

        large_icons = {
            "-SAVE-": (ICON_SAVE, "Save the current view"),
            "-LOAD-": (ICON_LOAD, "Load a previously saved view"),
            "-START-": (ICON_START, "Start the automated tests"),
            "-REPORT-": (ICON_PRINT, "Save the current view and create a report"),
            "-CANCEL-": (ICON_CANCEL, "Cancel the script execution"),
            "-ERROR-": (ICON_ERROR, "Generate an error report"),
        }
    else:
        small_icons = {
            "-FINAL-": (ICON_SMALL_FINAL, "Calculate final dose"),
            "-START-": (ICON_SMALL_START, "Start the automated tests"),
            "-SAVE-": (ICON_SMALL_SAVE, "Save the current view"),
            "-LOAD-": (ICON_SMALL_LOAD, "Load a previously saved view"),
            "-SUBMIT-": (ICON_SMALL_SUBMIT, "Submit the review"),
            "-CANCEL-": (ICON_SMALL_CANCEL, "Cancel the script execution"),
            "-ERROR-": (ICON_SMALL_ERROR, "Generate an error report"),
        }

        large_icons = {
            "-FINAL-": (ICON_FINAL, "Calculate final dose"),
            "-START-": (ICON_START, "Start the automated tests"),
            "-SAVE-": (ICON_SAVE, "Save the current view"),
            "-LOAD-": (ICON_LOAD, "Load a previously saved view"),
            "-SUBMIT-": (ICON_SUBMIT, "Submit the review"),
            "-CANCEL-": (ICON_CANCEL, "Cancel the script execution"),
            "-ERROR-": (ICON_ERROR, "Generate an error report"),
        }

    icons = small_icons if save_space else large_icons

    top_buttons = [Sg.Button('', image_filename=icons[key][0],
                             image_size=top_image_size,
                             image_subsample=top_subsample,
                             pad=top_pad,
                             border_width=top_border,
                             tooltip=icons[key][1],
                             key=key)
                   for key in icons.keys()]
    top = Sg.Frame('',
                   [top_buttons],
                   )
    top_events = [key for key in icons.keys()]
    return top, top_events


def handle_top_event(gui_state_manager, event, values):
    status = 'continue'
    if event == '-ERROR-':
        report_script_error(gui_state_manager.rso)
    elif event == '-LOAD-':
        load_review(gui_state_manager)
        # Update the preplan gui state:
        # gui_state_manager.window.read()
        update_preplan_gui_state(gui_state_manager, values)
    elif event == '-SAVE-':
        review_data = get_review_gui_values(gui_state_manager, values)
        # TODO: Move to the get_review_gui_values function
        #       Include tree_data and tree_children
        # review_data['tree_data'] = gui_state_manager.tree_data.to_dict()
        # review_data['tree_children'] = gui_state_manager.tree_children
        gui_state_manager.review_file_name = save_review(
            gui_state_manager.rso, review_data, suffix=gui_state_manager.suffix)
    elif event == '-START-':
        if gui_state_manager.tests_started:
            handle_already_started_tests(gui_state_manager, values)
            if not gui_state_manager.relaunch:
                status = 'continue'
                return status
        # Validate the preplan tab
        preplan_valid, error = validate_preplan_tab(gui_state_manager.window)
        if not preplan_valid:
            popup_message = 'Preplan tab is not valid. Please correct the errors and try again.' \
                            + f'\n{error}'
            Sg.popup(popup_message, title='Warning', keep_on_top=True, font=('Helvetica', '12', 'bold'),
                     button_color=('black', 'white'), background_color='white')
            status = 'continue'
            return status
        handle_start_event(gui_state_manager, values)
    elif event == '-FINAL-':
        # Final dose calculation for Dosimetry review
        # Validate the preplan tab
        preplan_valid, error = validate_preplan_tab(gui_state_manager.window)
        if not preplan_valid:
            popup_message = 'Preplan tab is not valid. Please correct the errors and try again.' \
                            + f'\n{error}'
            Sg.popup(popup_message, title='Warning', keep_on_top=True, font=('Helvetica', '12', 'bold'),
                     button_color=('black', 'white'), background_color='white')
            status = 'continue'
            return status
        # Launch progress bar
        progress_window, progress_bar, progress_text = display_progress_bar(
            title_text='Calculating Final Dose', progress_bar_text='Final dose operation started')
        progress_total = len(gui_state_manager.beamset_names)
        final_doses_performed = 0
        # Run during Dosimetry review
        for beamset_name in gui_state_manager.beamset_names:
            # Update the progress bar
            progress_text.update(f'Calculating Final Dose for {beamset_name}')
            progress_bar.update(
                current_count=int(100 * final_doses_performed / progress_total))
            progress_window.refresh()
            # Retrieve the site and technique
            site, technique = find_site_technique_from_beamset_name(
                beamset_name, len(gui_state_manager.beamset_names), gui_state_manager.window)
            final_dose(site=site, technique=technique, rso=gui_state_manager.rso, beamset_name=beamset_name)
            progress_text.update(f'Completed Final Dose for {beamset_name}')
            final_doses_performed += 1
        progress_window.close()
        # START the automated tests
        gui_state_manager.window.write_event_value('-START-', 'Triggered Programatically')
    elif event == '-REPORT-':
        # Retrieve the passing and failing tests
        if not gui_state_manager.tree_children:
            Sg.popup('No tests have been run yet!')
            return 'continue'
        gui_state_manager.passing_tests, gui_state_manager.failed_tests = get_tests_from_tree(
                gui_state_manager.tree_children)
        is_valid = on_done_button_click(gui_state_manager, values)
        # Perform the form submission logic
        if is_valid:
            # Save the review
            save_review(
                gui_state_manager.rso,
                get_review_gui_values(gui_state_manager, values),
                suffix=gui_state_manager.suffix, quiet=True)
            get_header_checklist_qa_values(gui_state_manager, values)
            if side_panel_proceed_qi_true(values):
                # Generate and email the report
                generate_and_distribute_qi_issue_report(gui_state_manager.rso, values)
            if side_panel_revision_true(values):
                generate_and_distribute_revision_report(gui_state_manager.rso, values)
            return 'break'
    elif event == '-SUBMIT-':
        # Retrieve the passing and failing tests
        if not gui_state_manager.tree_children:
            Sg.popup('No tests have been run yet!')
            return 'continue'
        gui_state_manager.passing_tests, gui_state_manager.failed_tests = get_tests_from_tree(
            gui_state_manager.tree_children)
        manual_valid, side_valid = on_submit_button_click(gui_state_manager, values)
        # Perform the form submission logic
        if side_valid and not manual_valid:
            Sg.popup('Automated tests are showing failing results. Consider cancelling the script,'
                     ' revising the plan and rerunning the tests.')
            Sg.popup_yes_no('Proceed with submission?', title='Warning', keep_on_top=True,
                            font=('Helvetica', '12', 'bold'), button_color=('black', 'white'),
                            background_color='white')
            # If the popup is 'No' return 'cancel'
            if event == 'No':
                return 'cancel'
            else:
                logging.warning('Proceeding with submission despite failing automated tests')
        elif not side_valid:
            Sg.popup('Side panel is not valid. Please correct the errors and try again.')
            return 'continue'
        else:
            # Save the review
            save_review(
                gui_state_manager.rso,
                get_review_gui_values(gui_state_manager, values),
                suffix=gui_state_manager.suffix, quiet=True)
            if side_panel_proceed_qi_true(values):
                # Generate and email the report
                generate_and_distribute_qi_issue_report(gui_state_manager.rso, values)
            if side_panel_revision_true(values):
                generate_and_distribute_revision_report(gui_state_manager.rso, values)
            return 'break'

    return status


def on_submit_button_click(gui_state_manager, values):
    # Check if all the required fields are filled in
    manual_valid = is_valid_manual_tab(gui_state_manager.window, values, gui_state_manager.check_box_copy,
                                       gui_state_manager.failed_tests, response_required=False)
    if gui_state_manager.review_type.lower() == 'dosimetry':
        side_valid = is_valid_dosimetry_panel(gui_state_manager.window, values)
    else:
        side_valid = is_valid_physics_panel(gui_state_manager.window, values)
    return manual_valid, side_valid


def on_done_button_click(gui_state_manager, values):
    # Check if all the required fields are filled in
    manual_valid = is_valid_manual_tab(gui_state_manager.window, values, gui_state_manager.check_box_copy,
                                       gui_state_manager.failed_tests)
    if gui_state_manager.review_type.lower() == 'dosimetry':
        side_valid = is_valid_dosimetry_panel(gui_state_manager.window, values)
    else:
        side_valid = is_valid_physics_panel(gui_state_manager.window, values)
    is_valid = all([manual_valid, side_valid])
    return is_valid


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
        gui_state_manager.relaunch = True
    else:
        gui_state_manager.relaunch = False


def handle_start_event(gui_state_manager, values):
    """
    Handle the '-START-' event in the GUI.

    Parameters:
        gui_state_manager: EventContext object containing the window, rso, gui_dict, and tests_started
        values: Values from the GUI

    Returns:
    """
    # Get the beamset info for review
    beamsets = gui_state_manager.beamset_names
    gui_state_manager.tree_data, gui_state_manager.tree_children = perform_automated_checks(
        gui_state_manager.rso, do_physics_review=True, values=values,
        display_progress=True, beamsets=beamsets)
    gui_state_manager.rso.patient.Save()
    tab_group = gui_state_manager.window['tab_group']
    tab1 = on_submit_build_tree(gui_state_manager.tree_data, gui_state_manager.gui_dict['tab_width'],
                                gui_state_manager.gui_dict['tab_height'],
                                gui_state_manager.gui_dict['pix_per_char_width'],
                                gui_state_manager.gui_dict['pix_per_char_height'])
    # Add the new tab to the tab group layout
    tab_group.add_tab(Sg.Tab('Tree', tab1,
                             key='Review and Logs',
                             tooltip='Tree view of automated tests and log files generated by scripts',
                             font=gui_state_manager.gui_dict['tab_font']))
    if gui_state_manager.review_type == 'Physics':
        # Get the ditto tab list
        ditto_tab_list, gui_state_manager.match_trees = get_ditto_tab_list(gui_state_manager, beamsets)
        # Build next tab
        gui_state_manager.check_box_copy = build_manual_check_box_list(
            gui_state_manager.rso, beamsets=beamsets, review_type=gui_state_manager.review_type,
            chars_per_line=gui_state_manager.gui_dict['check_character_width'])

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
    else:
        tabs = []
        ditto_tab_list = []
    for tab in tabs:
        if is_visible_tab(tab, gui_state_manager.window):
            tab_group.add_tab(tab)
    for tab in ditto_tab_list:
        if tab:
            tab_group.add_tab(tab)

    gui_state_manager.window['Review and Logs'].select()
    gui_state_manager.tests_started = True


def get_ditto_tab_list(gui_state_manager, beamsets):
    """
    Get the ditto tab list and match trees.
    Args:
        gui_state_manager: EventContext object containing the window, rso, gui_dict, and tests_started
        beamsets: List of beamset names

    Returns:
        ditto_tab_list: List of ditto tabs
        match_trees (dict): A dictionary of ElementTree objects

    """
    not_tomo_beamsets = []
    for beamset_name in beamsets:
        for beamset in gui_state_manager.rso.plan.BeamSets:
            if beamset.DicomPlanLabel == beamset_name and "Tomo" not in beamset.DeliveryTechnique:
                not_tomo_beamsets.append(beamset_name)
                break
    ditto_tab_list, match_trees = get_ditto_tab(gui_state_manager.gui_dict['tab_width'],
                                                gui_state_manager.gui_dict['tab_height'], not_tomo_beamsets)

    return ditto_tab_list, match_trees
