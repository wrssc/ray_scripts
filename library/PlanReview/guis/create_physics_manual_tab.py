import PySimpleGUI as Sg
import sys
import logging
from math import ceil
from typing import NamedTuple
from collections import defaultdict
from dataclasses import dataclass, field
from PlanReview.review_definitions import (
    PASS, FAIL, ALERT, NA,
    DOMAIN_TYPE, RED_CIRCLE, GREEN_CIRCLE, YELLOW_CIRCLE, BLUE_CIRCLE,
    CHECK_BOXES_PHYSICS_REVIEW, CHECK_BOXES_PHYSICS_REVIEW_3D,
    CHECK_BOXES_PHYSICS_REVIEW_VMAT, CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS,
    CHECK_BOXES_PHYSICS_REVIEW_TOMO3D, CHECK_BOXES_PHYSICS_REVIEW_TOMO)
from PlanReview.utils.constants import *


def create_key(element_type, beamset_index=None, target_index=None):
    """
    Creates a unique key for a GUI element.

    This function constructs a tuple to uniquely identify GUI elements
    especially useful in the context of events in PySimpleGUI. The tuple is
    constructed from the type of the GUI element and optional indices
    for beamsets and targets.

    Args:
        element_type (str): The type of the GUI element. This could be any string
            that describes the element (e.g., 'beamset_num_text', 'target_name', etc.)
        beamset_index (int, optional): The index of the beamset. This is used
            when the GUI element is associated with a specific beamset. Defaults to None.
        target_index (int, optional): The index of the target. This is used
            when the GUI element is associated with a specific target. Defaults to None.


    Returns:
        tuple: A tuple that uniquely identifies a GUI element. It includes the element type
            and, if provided, the beamset and target indices.
    """
    # Start with a tuple containing the element_type
    unique_key = (element_type,)

    # If a beamset index is provided, append it to the tuple
    if beamset_index is not None:
        unique_key += (beamset_index,)

    # If a target index is provided, append it to the tuple
    if target_index is not None:
        unique_key += (target_index,)

    # Return the unique key tuple
    return unique_key


def generate_event_key(*args):
    """
    Generates a unique event key for a GUI element.

    This function constructs a string by joining the string representation of
    each argument with underscores. This can be useful for creating unique event keys
    for PySimpleGUI elements.

    Args:
        *args: A variable number of argument that uniquely identify a GUI element.

    Returns:
        str: A unique event key for a GUI element.
    """
    return "_".join(str(arg) for arg in args)


def create_manual_check_row(item, max_check, user_text_length=80):
    phrases = item[KEY_OUT_OPTIONS].split(',')
    test_name = item[KEY_OUT_DESC]
    row_key = item[KEY_OUT_TEST]
    radios = [Sg.Column(
        [[Sg.Radio(
            phrase,
            group_id=create_key(row_key),
            default=False,
            key=create_key(f'{row_key}{KEY_CHECK}{KEY_RADIO}{phrase}'),
            enable_events=True)]],
        justification='center',
        expand_x=False,
        pad=(0, 0))
        for phrase in phrases
    ]
    row = [Sg.Column(
        [[Sg.Text(
            test_name,
            size=(int(0.79 * max_check), 1),  # pad=(0, 0))
        )
        ]],
        justification='left',
        expand_x=False),
        *radios,
        Sg.Column(
            [[Sg.InputText(
                size=(user_text_length, 1),
                key=create_key(f'{row_key}{KEY_CHECK}{KEY_INPUT_TEXT}'),
                enable_events=True,
                background_color='#E5DECE', pad=(0, 0))]],
            justification='left',
            expand_x=False),
    ]

    return row


def extract_values_manual_tab(window, passing, failed, check_boxes):
    sorted_values = {}
    for key in check_boxes:
        sorted_values[key] = {}
        for item in check_boxes[key]:
            phrases = item[KEY_OUT_OPTIONS].split(',')
            for p in phrases:
                radio_key = create_key(
                    f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}{p}")
                sorted_values[key][radio_key] = window[radio_key].get() \
                    if window[radio_key].get() else None
            input_key = create_key(f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}")
            sorted_values[key][input_key] = window[input_key].get() \
                if window[input_key].get() else None
    # Parse the automated tests after user input
    key = 'Failed Tests'
    sorted_values[key] = {}
    for test in failed:
        input_key = create_key(
            test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC], KEY_INPUT_TEXT)
        sorted_values[key][input_key] = window[input_key].get()
    key = 'Passing Tests'
    sorted_values[key] = {}
    for test in passing:
        input_key = create_key(
            test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC], KEY_INPUT_TEXT)
        sorted_values[key][input_key] = window[input_key].get()
    return sorted_values


def load_manual(window, values, check_boxes):
    for check_level, value_dict in values.items():
        if any((check_level in check_boxes,
                check_level == 'Failed Tests',
                check_level == 'Passing Tests')):

            for key, value in value_dict.items():
                if check_level in check_boxes:
                    saved_key = create_key(key)
                else:
                    saved_key = key
                if saved_key in window.key_dict:
                    window[saved_key].update(value=value)


def search_string(input_string):
    input_string = str(input_string)
    split_str = input_string.split("::", 1)
    if len(split_str) == 2:
        return split_str[0], split_str[1]
    else:
        return None, input_string


def create_auto_check_row(comment, result, icon, key, max_check, user_text_x):
    row = [Sg.Column(
        [[Sg.Image(icon),
          Sg.Text(result, size=(max_check, 1), justification='left')]],
    ),
        Sg.Column([[Sg.InputText(default_text=f"{comment}",
                                 key=key,
                                 size=(user_text_x, 1),
                                 expand_x=True,
                                 enable_events=True,  # pad=((40, 0), (0, 0)),
                                 text_color='#000000',
                                 background_color='#ffffff', border_width=0,
                                 justification='left', tooltip=comment)]]),
    ]
    return row


class FrameSettings:
    def __init__(self, tab_width, tab_height, pix_per_line, checks, passing, failing):
        self.width = int(tab_width)
        self.tab_height = tab_height
        self.pix_per_line = pix_per_line
        self.height = 0
        self.checks = checks
        self.height_user = 0
        self.scroll_user = False
        self.passing = passing
        self.height_pass = 0
        self.scroll_pass = False
        self.failing = failing
        self.height_fail = 0
        self.scroll_fail = False
        self.checks_pix_per_line = ceil(self.pix_per_line * 1.652)
        self.domain_pix_per_line = ceil(self.pix_per_line * 1.21)
        self.auto_pix_per_line = ceil(self.pix_per_line * 1.6)
        # Initialize settings
        self.calculate_initial_settings()

    def calculate_pixel_height(self):
        user_line_count = len(self.checks)
        logging.debug(f'       user has {user_line_count} items * {self.checks_pix_per_line} c_ppl '
                      f'= {int(user_line_count * self.checks_pix_per_line)}')
        return int(user_line_count * self.checks_pix_per_line)

    def calculate_subframe_pixel_height(self, n_items):
        logging.debug(f'            n*a_ppl + d_ppl = {n_items} * {self.auto_pix_per_line} + '
                      f'{self.domain_pix_per_line} = '
                      f'{int(n_items * self.auto_pix_per_line + self.domain_pix_per_line)}')
        return int(n_items * self.auto_pix_per_line + self.domain_pix_per_line)

    def calculate_frame_height(self):
        return self.height_user + self.height_pass + self.height_fail

    def calculate_auto_frame_pixel_height(self, tests):
        height = self.domain_pix_per_line
        for domain, test_list in tests.items():
            item_count = len(test_list)
            logging.debug(f'       domain {domain} has {item_count} items')
            if item_count > 0:
                height += self.calculate_subframe_pixel_height(item_count)
        return height

    def calculate_initial_settings(self):
        self.height_user = self.calculate_pixel_height()
        self.height_pass = self.calculate_auto_frame_pixel_height(tests=self.passing)
        self.height_fail = self.calculate_auto_frame_pixel_height(tests=self.failing)
        self.height = self.calculate_frame_height()


def adjust_each_frame_height(frame_settings):
    max_pass = int(frame_settings.tab_height * 0.25)
    max_fail = int(frame_settings.tab_height * 0.25)
    max_user = int(frame_settings.tab_height * 0.5)

    while frame_settings.height > frame_settings.tab_height:
        excess = frame_settings.height - frame_settings.tab_height
        if frame_settings.height_pass > max_pass:
            frame_settings.height_pass = max_pass if excess >= max_pass else ceil(frame_settings.height_pass - excess)
            frame_settings.scroll_pass = True
        elif frame_settings.height_fail > max_fail:
            frame_settings.height_fail = max_fail if excess >= max_fail else ceil(frame_settings.height_fail - excess)
            frame_settings.scroll_fail = True
        else:
            frame_settings.height_user = max_user if excess >= max_user else ceil(frame_settings.height_user - excess)
            frame_settings.scroll_user = True
            if frame_settings.height > frame_settings.tab_height:
                logging.warning(
                    f'****Dialog adjustment failed: dialog height {frame_settings.height} > available space in tab {frame_settings.tab_height}')
                break

        frame_settings.height = frame_settings.calculate_frame_height()


def make_subframe(input_text, content_list):
    """
    Create a subframe with a specified text header and content.

    Args:
        input_text (str): The header text for the subframe.
        content_list (list): The content to be included in the subframe.

    Returns:
        Sg.Frame: A PySimpleGUI Frame element.
    """
    return Sg.Frame(f"   {input_text}", [content_list],
                    pad=(1, 1),
                    expand_x=True,
                    # expand_y=True,
                    background_color='#C3C3C3',
                    border_width=0)


def create_subframes_for_domain(tests_by_domain, max_check, user_text_x):
    """
    Create subframes for each domain, containing rows with test details.

    Args:
        tests_by_domain (dict): Tests grouped by domain.
        max_check (int): Maximum number of checks.
        user_text_x (int): Positioning for the user text.

    Returns:
        list: List of subframes.
    """
    subframes = []
    rows = defaultdict(list)

    # Loop through each domain to populate rows
    for domain_name in tests_by_domain.keys():
        for v in tests_by_domain[domain_name]:
            comment = v[KEY_OUT_COMMENT]
            icon = v[KEY_OUT_ICON]
            result = v[KEY_OUT_MESSAGE]
            key_name = create_key(domain_name, v[KEY_OUT_DESC], KEY_INPUT_TEXT)

            # Create a row for each check
            rows[domain_name].append(create_auto_check_row(comment, result, icon, key_name, max_check, user_text_x))

        if rows[domain_name]:
            # Create and append subframes for each domain
            subframes.append([make_subframe(domain_name, [
                Sg.Column([*rows[domain_name]],
                          scrollable=False,
                          vertical_scroll_only=True)])])

    return subframes


def auto_checks_in_tab(tests, tab_key):
    return [test for test in tests if test[KEY_OUT_TAB] == tab_key]


def sort_by_domain(tests):
    tests_by_domain = defaultdict(list)
    for test in tests:
        domain_name = test[KEY_OUT_DOMAIN_NAME]
        tests_by_domain[domain_name].append(test)
    return tests_by_domain


def create_tab_manual_checks(check_boxes, passing_tests,
                             failed_tests, tab_width, tab_height,
                             pix_per_char_width, pix_per_char_height, save_space):
    """
    Create a tab with manual checks, failed tests, and passed tests.

    Pseudocode:
    1. Calculate max_check, the maximum length of the descriptions of the manual checks.
    2. Determine the pixel-per-character ratio and the horizontal size for user text based on
       whether space-saving is enabled.
    3. Initialize an empty list, tabs, to hold the individual tab layouts.
    4. Loop through all the keys in check_boxes:
        a. Initialize empty layouts for the frame and the tab.
        b. Determine the frame properties using `determine_frame_properties`.
        c. Create rows for manual checks using `create_manual_check_row` and add to the frame layout.
        d. Create a new frame with the above layout.
        e. Create subframes for Failed Tests:
            i. Filter the failed_tests for the current key.
            ii. Create subframes using `create_subframes_for_domain`.
        f. Create subframes for Passing Tests:
            i. Filter the passing_tests for the current key.
            ii. Create subframes using `create_subframes_for_domain`.
        g. Create a new tab with all the frames and subframes and add it to the list of tabs.
    5. Return the list of tabs.
    Args:
        check_boxes (dict): Dictionary holding check box data.
        passing_tests (list): List of passing tests.
        failed_tests (list): List of failed tests.
        tab_width (int): Width of the tab.
        tab_height (int): Height of the tab.
        pix_per_char_width (int): Pixel width per character.
        pix_per_char_height (int): Pixel height per line.
        save_space (bool): Flag to enable/disable space-saving layout.

    Returns:
        list: List of tabs to be added to the GUI.
    """

    # Calculate the maximum length of the descriptions in check_boxes
    max_checkbox_length = max([len(item[KEY_OUT_DESC]) for key in check_boxes for item in check_boxes[key]])

    # Initialize an empty list to hold individual tab layouts
    tabs = []

    # Determine pixel-per-character ratio
    pixels_per_char = 8.3 if save_space else pix_per_char_width

    # Determine horizontal size for user text
    user_text_x = int(0.25 * tab_width / pixels_per_char) if save_space else int(
        0.28 * tab_width / pix_per_char_width)

    # Specify vertical space available for frames
    vertical_size = tab_height - 6 * pix_per_char_height if save_space \
        else tab_height - 7 * pix_per_char_height


    # Loop through all keys in check_boxes
    for tab_key in check_boxes:
        layout = []  # Initialize empty layout for the tab
        frame_layout = []  # Initialize empty layout for the frame

        # Find the passing/failed tests that are part of this tab
        matching_failed_tests = auto_checks_in_tab(failed_tests, tab_key)
        failed_tests_by_domain = sort_by_domain(matching_failed_tests)

        matching_passing_tests = auto_checks_in_tab(passing_tests, tab_key)
        passing_tests_by_domain = sort_by_domain(matching_passing_tests)

        matching_manual_checks = check_boxes[tab_key]
        max_checkbox_tab_length = max([len(item[KEY_OUT_DESC]) for item in check_boxes[tab_key]])

        # Initialize frame data
        frame_settings = FrameSettings(
            tab_width=int(0.98 * tab_width),
            tab_height=vertical_size,
            pix_per_line=pix_per_char_height,
            checks=check_boxes[tab_key],
            passing=passing_tests_by_domain,
            failing=failed_tests_by_domain)
        # Determine properties like frame size and scroll-ability
        adjust_each_frame_height(frame_settings)

        # Create rows for manual checks and add them to frame layout
        for item in matching_manual_checks:
            manual_row = create_manual_check_row(item, max_checkbox_tab_length, user_text_x)
            frame_layout.append(manual_row)
            frame_layout.append([Sg.HorizontalSeparator(pad=(0, 0))])

        # Override for small screens
        if save_space:
            frame_settings.scroll_user = True
            frame_settings.scroll_fail = True
            frame_settings.scroll_pass = True
            # Turn on horiztonal scrolling for small screens
            vertical_scroll = False
            sb_width = 1
            tab_font = ('Helvetica','8','bold')
        else:
            vertical_scroll = True
            sb_width = 1
            tab_font = None

        # Create a frame with the above layout
        frame = Sg.Frame(f"{tab_key}: Select an option for each item",
                          [[Sg.Column(frame_layout,
                                      size=(frame_settings.width,
                                            frame_settings.height_user),
                                      sbar_width=sb_width,
                                      scrollable=frame_settings.scroll_user,
                                      vertical_scroll_only=vertical_scroll)]],
                          border_width=1)
        layout.append([frame])

        # Create subframes for Failed Tests
        subframes_failed = create_subframes_for_domain(
            failed_tests_by_domain, max_checkbox_length, user_text_x)
        if subframes_failed:
            layout.append([Sg.Frame('Failed Tests',
                                    [[Sg.Column(subframes_failed,
                                                size=(frame_settings.width,
                                                      frame_settings.height_fail),
                                                sbar_width=sb_width,
                                                scrollable=frame_settings.scroll_fail,
                                                vertical_scroll_only=vertical_scroll)]],
                                    )])

        # Create subframes for Passing Tests
        subframes_passing = create_subframes_for_domain(
            passing_tests_by_domain, max_checkbox_length, user_text_x)
        if subframes_passing:
            layout.append([Sg.Frame('Passing Tests',
                                    [[Sg.Column(subframes_passing,
                                                size=(frame_settings.width,
                                                      frame_settings.height_pass),
                                                sbar_width=sb_width,
                                                scrollable=frame_settings.scroll_pass,
                                                vertical_scroll_only=vertical_scroll)]],
                                    )])
        # Final tab layout
        tab = Sg.Tab(tab_key, [[Sg.Column(layout)]],
                     font=tab_font)
        tabs.append(tab)  # Add the tab to the list of tabs

    return tabs  # Return the list of tabs


# Define a function to handle events related to radio buttons
def on_manual_radio_button_click(window, event):
    """
    Updates the color and background of a text input element when a radio button is selected
    """
    prefix, radio = event[0].split(KEY_CHECK + KEY_RADIO)
    if radio == 'No':
        # Update text color and background when the "No" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#000000',
                                 background_color='#ffffff')
    else:
        #
        # Update text color and background when the "Yes/NA" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#ffffff',
                                 background_color='#848884')


def update_window_error(window, key, bg=False):
    error_text_color = '#8B0000'
    error_bg_color = '#8B0000'
    error_bg_text = '#8B0000'
    if bg:
        window[key].update(text_color=error_bg_text,
                           background_color=error_bg_color)
    else:
        window[key].update(text_color=error_text_color)


def check_radio_on(values, keys):
    return any(values[k] for k in keys)


def is_valid_manual_tab(window, values, check_boxes):
    is_valid = True
    for key in check_boxes:
        for item in check_boxes[key]:
            options = ['Yes', 'No', 'NA']
            check_box_radio_keys = [
                create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}{o}')
                for o in options]
            if not check_radio_on(values, check_box_radio_keys):
                for r in check_box_radio_keys:
                    update_window_error(window, r)
                is_valid = False
            else:
                input_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}')
                if values[check_box_radio_keys[1]] and not values[input_key]:
                    update_window_error(window, input_key, bg=True)
                    is_valid = False
    if not is_valid:
        Sg.popup_error('Please fill in all the required fields.')
    return is_valid


def copy_and_filter_checkbox_dict(dict1, dict2):
    # Create filtered copies of dict1 and dict2 without the KEY_REVIEW_TYPE key
    f_dict1 = {k: v for k, v in dict1.items() if k != KEY_REVIEW_TYPE}
    f_dict2 = {k: v for k, v in dict2.items() if k != KEY_REVIEW_TYPE}
    return f_dict1, f_dict2


def merge_dicts(dict1, dict2):
    # Get filtered versions of the dictionaries
    f_dict1, f_dict2 = copy_and_filter_checkbox_dict(dict1, dict2)
    # Create a copy of f_dict1 to start merging
    merged = f_dict1.copy()

    for key, value in f_dict2.items():
        if key in merged:
            # Merge unique items from dict2[key] into merged[key]
            # Filter out duplicate keys
            merged[key] = [d for d in merged[key] if d not in value] + value
        else:
            # Add key and value from dict2 if not in dict1
            merged[key] = value

    # Remove outer level keys with empty lists
    merged = {k: v for k, v in merged.items() if v}

    return merged


def find_domain_name(rso: NamedTuple, domain_level: str) -> str:
    """
    Finds the domain name based on the given Radiotherapy Service Object (RSO)
    and domain level key.

    Args:
        rso (script object): RayStation Script Object containing data for the
            patient, exam, plan, etc.
        domain_level (str): Key for the desired domain level, e.g., "PLAN_KEY".

    Returns:
        str: The domain name corresponding to the given RSO and domain level.

    """
    # Note: It's assumed that DOMAIN_TYPE is defined elsewhere in the code.
    if domain_level == DOMAIN_TYPE['PATIENT_KEY']:
        return rso.patient.PatientID
    if domain_level == DOMAIN_TYPE['EXAM_KEY']:
        return rso.exam.Name
    if domain_level == DOMAIN_TYPE['PLAN_KEY']:
        return rso.plan.Name
    if domain_level == DOMAIN_TYPE['BEAMSET_KEY']:
        return rso.beamset.DicomPlanLabel
    if domain_level == DOMAIN_TYPE['SANDBOX_KEY']:
        return domain_level
    if domain_level == DOMAIN_TYPE['RX_KEY']:
        return rso.beamset.PrimaryDosePrescription
    if domain_level == DOMAIN_TYPE['LOG_KEY']:
        return domain_level


def build_manual_check_box_list(rso, beamsets):
    """
    Depending on the type of beamset we are checking, find the appropriate
    checklist from review_definitions
    :param rso:
    :param beamsets: (list): list of all beamsets
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
        elif technique == 'DynamicArc':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_VMAT
        elif technique == 'SMLC':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_3D
        else:
            sys.exit(f'UNKNOWN TREATMENT TECHNIQUE {technique}')
        dict1 = merge_dicts(dict1, dict2)
        for level in dict1:
            for item in dict1[level]:
                item[KEY_OUT_MESSAGE] = ""
                item[KEY_OUT_COMMENT] = ""
                item[KEY_OUT_ICON] = None
                item[KEY_OUT_DOMAIN_NAME] = find_domain_name(
                    rso, item[KEY_OUT_DOMAIN_TYPE])
    return dict1


# TODO: Evaluate this object to determine if it is worthwhile to create objects for tests
class Domain:
    def __init__(self, domain_type, domain_name):
        self.domain_type = domain_type
        self.domain_name = domain_name
        self.failed_tests = []
        self.passed_tests = []

    def add_test(self, test, pass_fail):
        if pass_fail == PASS:
            self.passed_tests.append(test)
        else:
            self.failed_tests.append(test)


class Test:
    def __init__(self, comment, result, icon, pass_fail):
        review_tab, comment = search_string(comment)
        self.comment = comment
        self.result = result
        self.icon = icon
        self.pass_fail = pass_fail
        self.review_tab = review_tab


def get_tests_from_tree(tree_children):
    """
    Determine all tests that failed and passed from the tree
    :param tree_children:
    :return:
    """
    passing_tests = []
    failed_tests = []
    for domain_type, domain_name, comment, child_key, result, pass_fail, icon in tree_children:
        review_tab, comment = search_string(comment)
        child = {
            KEY_OUT_DOMAIN_TYPE: domain_type,
            KEY_OUT_DOMAIN_NAME: domain_name,
            KEY_OUT_DESC: str(comment),
            KEY_OUT_MESSAGE: str(result),
            KEY_OUT_ICON: str(icon),
            KEY_OUT_RESULT: pass_fail,
            KEY_OUT_TAB: review_tab}
        if pass_fail != PASS:
            child[KEY_OUT_COMMENT] = "Script Fail: Comment Needed"
            failed_tests.append(child)
        else:
            child[KEY_OUT_COMMENT] = ""
            passing_tests.append(child)
    return passing_tests, failed_tests


def process_check_box_values(window, checks):
    """
    Parses the resulting window values and sorts the checkbox values.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        checks (dict): A dictionary containing the checkbox data.

    Returns:
        list: A sorted list containing the checkbox values.
    """
    sorted_results = []
    for test_level in checks:
        for item in checks[test_level]:
            parsed_item = {KEY_OUT_DESC: item[KEY_OUT_DESC]}
            radio_pre = f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}"
            input_key = create_key(f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}")
            if window[create_key(radio_pre + 'Yes')].get():
                parsed_item[KEY_OUT_RESULT] = PASS
                parsed_item[KEY_OUT_ICON] = GREEN_CIRCLE
            elif window[create_key(radio_pre + 'No')].get():
                parsed_item[KEY_OUT_RESULT] = FAIL
                parsed_item[KEY_OUT_ICON] = RED_CIRCLE
            elif window[create_key(radio_pre + 'NA')].get():
                parsed_item[KEY_OUT_RESULT] = NA
                parsed_item[KEY_OUT_ICON] = BLUE_CIRCLE
            else:
                parsed_item[KEY_OUT_RESULT] = ALERT
                parsed_item[KEY_OUT_ICON] = YELLOW_CIRCLE
            parsed_item[KEY_OUT_COMMENT] = window[input_key].get()
            parsed_item[KEY_OUT_TEST_SOURCE] = SOURCE_USER
            parsed_item[KEY_OUT_TAB] = test_level
            # There is no message for user driven tests but the message
            # field is populated for all the auto tests
            parsed_item[KEY_OUT_MESSAGE] = parsed_item[KEY_OUT_RESULT]
            sorted_results.append(parsed_item)
    return sorted_results


def process_auto_tests(window, tests):
    """
    Parses the tests results generated by automation and adds them to a list.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        tests (list): A list of tests, where each item is a dict containing:

            KEY_OUT_DESC: the name of the test
            KEY_OUT_MESSAGE: PASS/FAIL/ALERT
            KEY_OUT_ICON: string containing icon
            KEY_OUT_COMMENT: a placeholder for the default comment
            KEY_OUT_TAB: the plan check module in raystation where this check
                              is performed->Tab on the gui
            KEY_OUT_DOMAIN_TYPE: The type of domain level object from which the test is
                                 taken, i.e. an exam, a beamset, a plan
            KEY_OUT_DOMAIN_NAME: the Name of the domain i.e. Beamset: Pelv_VMA_R0A0

        comment, result, icon file string, and the tab to which this was assigned
            and icon.

    Returns:
        list: A list of parsed failed tests.
    """
    test_list = []
    for test in tests:
        domain_name = test[KEY_OUT_DOMAIN_NAME]
        description = test[KEY_OUT_DESC]
        parsed_item = {
            KEY_OUT_DESC: description,
            KEY_OUT_MESSAGE: test[KEY_OUT_MESSAGE],
            KEY_OUT_COMMENT: window[
                create_key(domain_name, description, KEY_INPUT_TEXT)].get(),
            KEY_OUT_RESULT: test[KEY_OUT_RESULT],
            KEY_OUT_DOMAIN_TYPE: test[KEY_OUT_DOMAIN_TYPE],
            KEY_OUT_DOMAIN_NAME: domain_name,
            KEY_OUT_TAB: test[KEY_OUT_TAB],
            KEY_OUT_TEST_SOURCE: SOURCE_AUTO,

        }
        if test[KEY_OUT_RESULT] == FAIL:
            parsed_item[KEY_OUT_ICON] = RED_CIRCLE
        elif test[KEY_OUT_RESULT] == PASS:
            parsed_item[KEY_OUT_ICON] = GREEN_CIRCLE
        elif test[KEY_OUT_RESULT] == ALERT:
            parsed_item[KEY_OUT_ICON] = YELLOW_CIRCLE
        else:
            parsed_item[KEY_OUT_ICON] = BLUE_CIRCLE
        test_list.append(parsed_item)

    return test_list
