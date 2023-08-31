import PySimpleGUI as Sg
import sys
import logging
from typing import NamedTuple
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
            size=(int(0.87 * max_check), 1),  # pad=(0, 0))
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


def extract_manual_values(window, passing, failed, check_boxes):
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
            test[KEY_OUT_DOMAIN_NAME],test[KEY_OUT_DESC],KEY_INPUT_TEXT)
        sorted_values[key][input_key] = window[input_key].get()
    key = 'Passing Tests'
    sorted_values[key] = {}
    for test in passing:
        input_key = create_key(
            test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC],KEY_INPUT_TEXT)
        sorted_values[key][input_key] = window[input_key].get()
        # sorted_values[key][create_key(test_domain_name,test_name)] = \
        #     window[input_key].get()
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
                else:
                    logging.debug(f'No match found for {saved_key} during load.')


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


def max_test_length(checks, key):
    max_char = max([len(item[key]) for item in checks])
    return max_char


def calculate_frame_heights(vsize, hsize, check_lines, fail_lines, pass_lines, pix_per_line):
    pix_per_line = int(1.6 * pix_per_line)
    total_lines = check_lines + pass_lines + fail_lines
    # Calculate the sizes
    frame_check = int(check_lines * pix_per_line)
    frame_fail = int(fail_lines * pix_per_line)
    frame_pass = int(pass_lines * pix_per_line)
    frame_x = int(0.99 * hsize)

    total_size = frame_check + frame_pass + frame_fail
    # Check if total size exceeds vsize
    scroll_check = False
    scroll_fail = False
    scroll_pass = False
    if total_size > vsize:
        logging.debug(f'Total size of lines is {total_size} for {vsize}')
        n_check = check_lines
        n_fail = fail_lines
        n_pass = pass_lines
        excess = total_size - vsize
        excess_lines = int(excess / pix_per_line)
        logging.debug(f'Excess lines starts at {excess_lines}')
        iteration = 0
        condense_check = 0
        while excess_lines > 0:
            if n_pass > 5:
                n_pass = 5
                scroll_pass = True
            elif n_fail > 5:
                n_fail = 5
                scroll_fail = True
            else:
                scroll_check = True
                condense_check += 1
                n_check -= condense_check
            total_size = pix_per_line * (n_check + n_pass + n_fail)
            excess = total_size - vsize
            excess_lines = int(excess / pix_per_line)
            iteration += 1
            logging.debug(f'At {iteration} excess lines is {excess_lines}')
        frame_check = int(n_check * pix_per_line)
        frame_fail = int(n_fail * pix_per_line)
        frame_pass = int(n_pass * pix_per_line)

    frame_dict = {
        'check_size': (frame_x, frame_check),
        'pass_size': (frame_x, frame_pass),
        'fail_size': (frame_x, frame_fail),
        'check_scroll': scroll_check,
        'pass_scroll': scroll_pass,
        'fail_scroll': scroll_fail
    }
    return frame_dict


def determine_frame_properties(tab_width, tab_height, key,
                               check_boxes, failed_tests, passing_tests, pix_per_line,
                               save_space=False):
    vsize = tab_height - 6 * pix_per_line if save_space else tab_height - 7 * pix_per_line
    hsize = tab_width
    total_check_lines = len(check_boxes[key])
    # total_fail_lines = sum(1 for comment, result, icon, test_key in failed_tests if test_key == key)
    total_fail_lines = sum(1 for v in failed_tests if v.get(KEY_OUT_TAB) == key)
    total_pass_lines = sum(1 for v in passing_tests if v.get(KEY_OUT_TAB) == key)
    logging.debug(f'Key {key}: {total_pass_lines}, {total_fail_lines}, {total_check_lines}')

    frame_dict = calculate_frame_heights(vsize, hsize, total_check_lines, total_fail_lines,
                                         total_pass_lines, pix_per_line)

    return frame_dict


def make_subframe(input_text, content_list):
    return Sg.Frame(f"   {input_text}", [content_list],
                    pad=(1, 1),
                    expand_x=True,
                    # expand_y=True,
                    background_color='#C3C3C3',
                    border_width=0)


def create_tab_manual_checks(check_boxes, passing_tests,
                             failed_tests, tab_width, tab_height,
                             pix_per_char_width, pix_per_char_height, save_space
                             ):
    max_check = max([len(item[KEY_OUT_DESC]) for key in check_boxes
                     for item in check_boxes[key]])
    tabs = []
    pixels_per_char = 8.3 if save_space else pix_per_char_width
    user_text_x = int(0.3 * tab_width / pixels_per_char) if save_space else \
        int(0.3 * tab_width / pix_per_char_width)
    max_tab_length = int(0.6 * tab_width / pixels_per_char) if save_space else \
        int(0.4 * tab_width / pixels_per_char)

    # Create a tab for each key in check_boxes
    for key in check_boxes:
        # layout = [[Sg.Text('Select an option for each item:')]]
        layout = []
        frame_layout = []
        total_items = 0

        # max_tab_length = 70 #  max_test_length(check_boxes[key], KEY_OUT_DESC)
        frame_data = determine_frame_properties(
            tab_width, tab_height, key, check_boxes, failed_tests, passing_tests,
            pix_per_char_height, save_space)

        for item in check_boxes[key]:
            row1 = create_manual_check_row(item, max_tab_length, user_text_x)
            frame_layout.append(row1)
            total_items += 1

        frame = Sg.Frame(f"{key}: Select an option for each item", [[Sg.Column(frame_layout,
                                                                               size=frame_data['check_size'],
                                                                               scrollable=frame_data['check_scroll'],
                                                                               vertical_scroll_only=True)]],
                         border_width=1)
        layout.append([frame])
        # Failed tests
        # Get the failed tests which belong on this tab
        matching_failed_tests = [test for test in failed_tests if test[KEY_OUT_TAB] == key]
        # Using defaultdict to group tests by domain name
        tests_by_domain = defaultdict(list)
        # Sort tests by domain name
        for test in matching_failed_tests:
            domain_name = test[KEY_OUT_DOMAIN_NAME]
            tests_by_domain[domain_name].append(test)
        rows = defaultdict(list)
        for domain_name in tests_by_domain.keys():
            for v in tests_by_domain[domain_name]:
                comment = v[KEY_OUT_COMMENT]
                icon = v[KEY_OUT_ICON]
                result = v[KEY_OUT_MESSAGE]
                key_name = create_key(domain_name, v[KEY_OUT_DESC], KEY_INPUT_TEXT)
                rows[domain_name].append(
                    create_auto_check_row(
                        comment, result, icon, key_name, max_check,
                        user_text_x))
        if rows:
            subframes = []
            for domains in rows.keys():
                subframes.append([
                    make_subframe(domains,
                                  [Sg.Column([*rows[domains]],
                                             scrollable=frame_data['fail_scroll'],
                                             vertical_scroll_only=True)])])
            frame_failed_tests = Sg.Frame('Failed Tests', subframes,
                                          # TODO: Redo the size calcs to include subframes
                                          # size=frame_data['fail_size']
                                          )
            layout.append([frame_failed_tests])
        # Passing
        matching_passing_tests = [test for test in passing_tests if test[KEY_OUT_TAB] == key]
        tests_by_domain = defaultdict(list)
        for test in matching_passing_tests:
            domain_name = test[KEY_OUT_DOMAIN_NAME]
            tests_by_domain[domain_name].append(test)
        rows = defaultdict(list)
        for domain_name in tests_by_domain.keys():
            for v in tests_by_domain[domain_name]:
                comment = v[KEY_OUT_COMMENT]
                icon = v[KEY_OUT_ICON]
                result = v[KEY_OUT_MESSAGE]
                # key_name = v[KEY_OUT_DESC]
                key_name = create_key(domain_name, v[KEY_OUT_DESC], KEY_INPUT_TEXT)
                rows[domain_name].append(
                    create_auto_check_row(
                        comment, result, icon, key_name, max_check,
                        user_text_x))
        if rows:
            subframes = []
            for domains in rows.keys():
                subframes.append([
                    make_subframe(domains,
                                  [Sg.Column([*rows[domains]],
                                             scrollable=frame_data['pass_scroll'],
                                             vertical_scroll_only=True)])])
            frame_passing_tests = Sg.Frame('Passing Tests', subframes,
                                           # size=frame_data['pass_size']
                                           )
            layout.append([frame_passing_tests])
        tab = Sg.Tab(key, [[Sg.Column(layout)]])
        tabs.append(tab)

    return tabs


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


def merge_dicts(dict1, dict2):
    merged = dict1.copy()  # Start with a copy of dict1

    for key, value in dict2.items():
        if key in merged:
            #
            # Merge unique items from dict2[key] into merged[key]
            merged[key] = [x for x in merged[key] if x not in value] + value
        else:
            #
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
                    rso,item[KEY_OUT_DOMAIN_TYPE])
    return dict1


from collections import defaultdict


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
    ## sorted_results = {}
    for test_level in checks:
        ## sorted_results[test_level] = []
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
            ## sorted_results[test_level].append(parsed_item)
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
