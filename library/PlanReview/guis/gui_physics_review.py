# Import necessary modules and functions
import logging
import PySimpleGUI as Sg
from PlanReview.review_definitions import PROTOCOL_DIR
from PlanReview.utils import (get_user_name, get_roi_names_from_type,
                              get_user_display_parameters)
from PlanReview.utils.protocol_loading import (
    load_protocols, get_sites, get_all_orders, get_unique_instructions)
from PlanReview.utils.constants import *
from PlanReview.guis.create_side_panel import (
    create_side_panel, on_side_panel_radio_button_click)
from PlanReview.guis.gui_qa_form import on_checker_image_click
from PlanReview.guis.create_preplan_tab import (
    calculate_preplan_dose_per_fraction,
    update_preplan_frequencies, update_preplan_instructions,
    update_preplan_protocols, update_preplan_orders,
    create_tab_preplan_information, update_preplan_beamset_rows,
    update_preplan_target_rows, update_preplan_gui_state)
from PlanReview.guis.create_physics_manual_tab import on_manual_radio_button_click
from PlanReview.guis.gui_top_buttons import build_top_buttons, handle_top_event
from PlanReview.guis.gui_bottom_buttons import build_bottom_buttons, bottom_event
from PlanReview.guis.gui_ditto_wrapper import on_ditto_element_click


def initialize_gui_dict(review_type='Physics'):
    gui_dict = {}
    window_width, window_height, save_space, pix_per_char_width, pix_per_char_height = \
        get_user_display_parameters(review_type=review_type)
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
        gui_dict['user_text_width'] = 20
        gui_dict['check_character_width'] = 70  # Character wrap limit in check boxes
        gui_dict['tab_width'] = 120 * pix_per_char_width  # Based on top window width
        # Width of sidebar with 30 pix of greyspace
        gui_dict['sidebar_width'] = int(window_width - gui_dict['tab_width'] - 30)
        # Gap is around 6 char
        # gui_dict['comment_width_chars'] = int(gui_dict['sidebar_width'] - 120) // pix_per_char_width
    else:
        gui_dict['user_text_width'] = 24
        gui_dict['check_character_width'] = 96
        gui_dict['tab_width'] = 154 * pix_per_char_width
        gui_dict['sidebar_width'] = int(window_width - gui_dict['tab_width'] - 30)
        gui_dict['comment_width_chars'] = int(gui_dict['sidebar_width'] - 200) // pix_per_char_width
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


class GuiState:
    def __init__(self, rso, relaunch=False, tests_started=False, review_type='Physics'):
        self.window = None
        self.rso = rso
        self.gui_dict = {}
        self.tests_started = tests_started
        self.check_list = []
        self.check_box_copy = {}
        self.passing_tests = []
        self.failed_tests = []
        self.header_data = {}
        self.qa_form_data = {}
        self.review_type = review_type
        self.tree_children = None
        self.match_trees = None
        self.qa_form_accessible = False
        self.relaunch = relaunch
        self.maximum_target_number = None
        self.maximum_beamset_count = None
        self.preplan_valid = False
        self.beamset_number_choice = None
        self.beamset_names = []
        self.sites = []
        self.protocols = {}
        self.orders = {}
        self.instructions = []
        self.review_file_name = None
        if review_type == 'Physics':
            self.suffix = "_review.json"
            self.manual_tabs = True
            self.side_panel = True
        else:
            self.suffix = "_dosimetry_review.json"
            self.manual_tabs = False
            self.side_panel = True


def get_technique_and_modality(beamset_name, rso):
    for beamset in rso.plan.BeamSets:
        if beamset.DicomPlanLabel == beamset_name:
            modality = beamset.Modality
            technique = beamset.DeliveryTechnique
            return technique, modality
    return None, None


def launch_physics_review_gui(rso, relaunch=False, review_type='Physics'):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
    - relaunch: Boolean indicating if the GUI starts from scratch or if it is relaunched

    Returns: None
    """
    # Context initialization
    if review_type == 'Dosimetry':
        Sg.theme('Purple')
        dialog_title = 'Dosimetry Review'
    else:
        Sg.theme('DefaultNoMoreNagging')
        dialog_title = 'Physics Review'
    gui_state_manager = GuiState(rso, relaunch=relaunch, tests_started=False, review_type=review_type)
    # Variable initialization
    match_trees = None
    # GUI setup
    gui_state_manager.gui_dict = initialize_gui_dict(review_type=review_type)

    #
    # First Frame:
    gui_state_manager.protocols = load_protocols(PROTOCOL_DIR)
    protocol = None
    gui_state_manager.sites = get_sites(gui_state_manager.protocols)
    gui_state_manager.orders = get_all_orders(gui_state_manager.protocols)
    gui_state_manager.instructions = get_unique_instructions(gui_state_manager.protocols)
    gui_state_manager.beamset_names = [b.DicomPlanLabel for b in rso.plan.BeamSets]
    gui_state_manager.maximum_beamset_count = len(gui_state_manager.beamset_names)
    targets = get_roi_names_from_type(rso, roi_type=['Ptv', 'Gtv'])
    if targets:
        gui_state_manager.maximum_target_number = len(targets)
    else:
        gui_state_manager.maximum_target_number = 10
    # Top frame
    top, top_events = build_top_buttons(gui_state_manager.gui_dict['save_space'],
                                        review_type=gui_state_manager.review_type)
    # Bottom frame
    bottom, bottom_events = build_bottom_buttons(gui_state_manager.gui_dict['save_space'])
    # Side Panel
    side_panel, side_panel_events = create_side_panel(
        review_type=gui_state_manager.review_type)
    # Gather the layout
    layout = [
        [
            Sg.Column([
                [top],
                [Sg.TabGroup([[Sg.Tab('ARIA Info',
                                      create_tab_preplan_information(
                                          gui_state_manager.protocols,
                                          gui_state_manager.sites,
                                          gui_state_manager.orders,
                                          gui_state_manager.instructions,
                                          gui_state_manager.beamset_names, targets,
                                          gui_state_manager.gui_dict['tab_width'],
                                          gui_state_manager.gui_dict['tab_height'],
                                          gui_state_manager.gui_dict['save_space'],
                                          gui_state_manager.review_type),
                                      font=gui_state_manager.gui_dict['tab_font'],
                                      tooltip='Enter information from ARIA documents, '
                                              'which will be used in subsequent automated tests.')
                               ]],
                             key='tab_group')],
                [bottom]
            ],
            ),
            # Side Panel declaration
            Sg.Column(side_panel,
                      size=(gui_state_manager.gui_dict['sidebar_width'],
                            gui_state_manager.gui_dict['window_height']),
                      )
        ],
    ]

    gui_state_manager.window = Sg.Window(
        f'{get_user_name()}> {dialog_title}:{" " * 5}{rso.patient.Name}{" " * 5}{rso.patient.PatientID}',
        layout,
        resizable=True,
        size=(gui_state_manager.gui_dict['window_width'], gui_state_manager.gui_dict['window_height']), )

    # Event Loop
    while True:
        event, values = gui_state_manager.window.read()
        if event in (Sg.WIN_CLOSED, '-CANCEL-'):
            return {}
        # Top Panel Events Section
        elif event in top_events:
            status = handle_top_event(gui_state_manager, event, values)
            if status == 'break':
                break
            elif status == 'continue':
                continue
            elif status == 'cancel':
                return {}
        # Bottom Panel Events Section
        elif event in bottom_events:
            bottom_event(gui_state_manager, event, values)
        # Plan Revision Events Section
        elif event in side_panel_events:
            on_side_panel_radio_button_click(gui_state_manager.window, event, gui_state_manager.review_type)
        # First tab Events
        elif event == KEY_SITE_SELECT:
            site_name = values[KEY_SITE_SELECT]
            update_preplan_protocols(gui_state_manager.window, site_name, KEY_PROTOCOL_SELECT,
                                     gui_state_manager.protocols)
        # Update the potential protocol choices based on those for this site
        elif event == KEY_PROTOCOL_SELECT:
            protocol = gui_state_manager.protocols[values[KEY_PROTOCOL_SELECT]]
            update_preplan_orders(gui_state_manager.window, protocol, KEY_ORDER_SELECT)
        elif event == KEY_ORDER_SELECT:
            order_name = values[KEY_ORDER_SELECT]
            update_preplan_frequencies(gui_state_manager.window, protocol, order_name)
            update_preplan_instructions(gui_state_manager.window, protocol, order_name,
                                        gui_state_manager.instructions)
        # Trigger update_beamset_rows when the number of beamsets changes
        elif KEY_BEAMSET_COUNT in event:
            gui_state_manager.beamset_number_choice = int(values[event])
            update_preplan_beamset_rows(
                gui_state_manager.window, values,
                int(values[event]),
                gui_state_manager.maximum_beamset_count,
                gui_state_manager.maximum_target_number,
                gui_state_manager.review_type)

        elif KEY_BEAMSET_TARGET_COUNT in event:
            _, beamset_i = event
            num_targets = int(values[event])
            update_preplan_target_rows(gui_state_manager.window, num_targets, beamset_i,
                                       gui_state_manager.maximum_target_number)

        # Trigger calculate_dose_per_fraction when the dose value changes
        elif KEY_BEAMSET_DOSE in event:
            _, beamset_i, target_i = event
            calculate_preplan_dose_per_fraction(
                values, gui_state_manager.window, beamset_i, target_i)

        # Trigger calculate_dose_per_fraction when the number of fractions in a beamset changes
        elif KEY_BEAMSET + KEY_FRACTIONS in event:
            _, beamset_i = event
            target_i = None
            calculate_preplan_dose_per_fraction(values, gui_state_manager.window, beamset_i, target_i)

        # Trigger an update to the gui_state_manager when the user selects a beamset
        elif KEY_BEAMSET_SELECT in event:
            update_preplan_gui_state(gui_state_manager, values)
        # Update to Ditto
        # Check if the event starts with '-APTR_TREE_' and if there are beamsets to process
        # TODO: not currently working
        elif '-APTR_TREE_' in event:
            logging.debug(f'Event is {event} and beamset names are {gui_state_manager.beamset_names}')
            logging.debug(f'Match trees are {gui_state_manager.match_trees}')
            if gui_state_manager.beamset_names and match_trees:
                on_ditto_element_click(gui_state_manager.window, values, event,
                                       gui_state_manager.beamset_names, match_trees)
        # Manual Tab Events
        elif type(event) is tuple:
            if KEY_CHECK + KEY_RADIO in event[0]:
                on_manual_radio_button_click(gui_state_manager.window, event)
        elif event == '-CHECKER-IMAGE-':
            logging.debug(f'Checker image clicked show form: {gui_state_manager.qa_form_accessible}')
            if gui_state_manager.qa_form_accessible:
                on_checker_image_click(gui_state_manager.window, event)
                # on_side_panel_radio_button_click(gui_state_manager.window, event)

    gui_state_manager.window.close()
    if gui_state_manager.relaunch:
        launch_physics_review_gui(gui_state_manager.rso, relaunch=True)

    if gui_state_manager.check_list:
        return_dict = {KEY_TESTS: gui_state_manager.check_list,
                       KEY_HEADER: gui_state_manager.header_data,
                       KEY_QA_FORM: gui_state_manager.qa_form_data}
    else:
        return_dict = {}

    return return_dict
