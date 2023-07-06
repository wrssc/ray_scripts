import PySimpleGUI as Sg
import sys
from PlanReview.review_definitions import PASS, FAIL, ALERT, NA, \
    RED_CIRCLE, GREEN_CIRCLE, YELLOW_CIRCLE, BLUE_CIRCLE, \
    CHECK_BOXES_PHYSICS_REVIEW, \
    CHECK_BOXES_PHYSICS_REVIEW_3D, \
    CHECK_BOXES_PHYSICS_REVIEW_VMAT, CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS, \
    CHECK_BOXES_PHYSICS_REVIEW_TOMO3D, CHECK_BOXES_PHYSICS_REVIEW_TOMO
from PlanReview.utils.constants import KEY_CHECK, KEY_RADIO, KEY_INPUT_TEXT


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
        *args: A variable number of arguments that uniquely identify a GUI element.

    Returns:
        str: A unique event key for a GUI element.
    """
    return "_".join(str(arg) for arg in args)


def create_manual_check_row(item, max_check, user_text_length=80):
    phrases = item['options'].split(',')
    test_name = item['test_name']
    row_key = item['key']
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
            size=(int(max_check), 1), # pad=(0, 0))
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
            expand_x=True),
    ]

    return row


def extract_manual_values(window, failed_tests, check_boxes):
    sorted_values = {}
    for key in check_boxes:
        sorted_values[key] = {}
        for item in check_boxes[key]:
            phrases = item['options'].split(',')
            for p in phrases:
                radio_key = create_key(
                    f"{item['key']}{KEY_CHECK}{KEY_RADIO}{p}")
                sorted_values[key][radio_key] = window[radio_key].get() \
                    if window[radio_key].get() else None
            input_key = create_key(f"{item['key']}{KEY_CHECK}{KEY_INPUT_TEXT}")
            sorted_values[key][input_key] = window[input_key].get() \
                if window[input_key].get() else None
    # Parse the failed tests
    key = 'Failed Tests'
    sorted_values[key] = {}
    check_boxes[key] = []
    for comment, result, icon, review_tab in failed_tests:
        sorted_values[key][create_key(comment)] = window[create_key(comment)].get()
    return sorted_values


def load_manual(window, values, check_boxes):
    for check_level, value_dict in values.items():
        if check_level in check_boxes or check_level == 'Failed Tests':
            for key, value in value_dict.items():
                if create_key(key) in window.key_dict:
                    window[create_key(key)].update(value=value)


def search_string(input_string):
    input_string = str(input_string)
    split_str = input_string.split("::", 1)
    if len(split_str) == 2:
        return split_str[0], split_str[1]
    else:
        return None, input_string


def create_auto_check_row(comment, result, icon, key_name, max_check, user_text_x):
    row = [Sg.Column(
        [[Sg.Image(icon),
          Sg.Text(result, size=(max_check,1), justification='left')]],
    ),
        Sg.Column([[Sg.InputText(default_text=f"{comment}: Comment",
                                 key=create_key(key_name),
                                 size=(user_text_x, 1),
                                 expand_x=True,
                                 enable_events=True, # pad=((40, 0), (0, 0)),
                                 text_color='#000000',
                                 background_color='#ffffff', border_width=0,
                                 justification='left', tooltip=comment)]]),
    ]
    return row


def max_test_length(checks, key):
    max_char = max([len(item[key]) for item in checks])
    return max_char

def determine_frame_properties(hsize, vsize, key, check_boxes,
                               failed_tests, passing_tests):
    # Line size
    pix_per_line = 14
    max_text_length = max_test_length(check_boxes[key],'test_name')
    total_check_lines = len(check_boxes[key])
    # Count lines in fail
    total_fail_lines = 0
    for comment, result, icon, test_key in failed_tests:
        if test_key is not None and test_key == key:
            total_fail_lines += 1
    # Count lines in passing
    total_pass_lines = 0
    for v in passing_tests:
        test_key = v['review_tab']
        if test_key is not None and test_key == key:
            total_pass_lines += 1
    total_lines = total_check_lines + total_pass_lines + total_fail_lines
    # Compute sizes
    frame_x = int(0.99 * hsize)
    frame_check = int(vsize * total_check_lines/total_lines)
    frame_pass = 1 if total_pass_lines == 0 else int(vsize*total_pass_lines/total_lines)
    frame_fail = 1 if total_fail_lines == 0 else int(vsize*total_fail_lines/total_lines)
    frame_data = {
        'check_size': (frame_x,frame_check),
        'pass_size': (frame_x, frame_pass),
        'fail_size': (frame_x, frame_fail)
    }
    if total_check_lines > 3:
        frame_data['check_scroll'] = True
    else:
        frame_data['check_scroll'] = False
    if total_pass_lines > 3:
        frame_data['pass_scroll'] = True
    else:
        frame_data['pass_scroll'] = False
    if total_fail_lines > 3:
        frame_data['fail_scroll'] = True
    else:
        frame_data['fail_scroll'] = False
    return frame_data


def create_tab_manual_checks(check_boxes, passing_tests,
                             failed_tests, hsize=1200, vsize=1200):
    max_check = max([len(item['test_name']) for key in check_boxes
                     for item in check_boxes[key]])
    tabs = []
    pixels_per_char = 8
    frame_check_y = int(vsize * 0.6)
    frame_fail_y = int((vsize - frame_check_y) / 2.)
    frame_pass_y = int((vsize - frame_check_y) / 2.)
    frame_x = int(0.99 * hsize)
    user_text_x = int(0.3 * hsize / pixels_per_char)

    # Create a tab for each key in check_boxes
    for key in check_boxes:
        layout = [[Sg.Text('Select an option for each item:')]]
        frame_layout = []
        total_items = 0

        max_tab_length = max_test_length(check_boxes[key], 'test_name')
        frame_data = determine_frame_properties(hsize,vsize,key, check_boxes,failed_tests,passing_tests)

        for item in check_boxes[key]:
            row1 = create_manual_check_row(item, max_tab_length, user_text_x)
            frame_layout.append(row1)
            total_items += 1

        frame = Sg.Frame(key, [[Sg.Column(frame_layout,
                                          size=frame_data['check_size'],
                                          scrollable=frame_data['check_scroll'],
                                          vertical_scroll_only=True)]])
        layout.append([frame])
        # Failed tests
        rows = []
        for comment, result, icon, test_key in failed_tests:
            if test_key is not None and test_key == key:
                rows.append(
                    create_auto_check_row(
                        comment, result, icon, comment, max_check, user_text_x))
        if rows:
            frame_failed_tests = Sg.Frame('Failed Tests',
                                          [[Sg.Column(
                                              [*rows],
                                              size=frame_data['fail_size'],
                                              scrollable=frame_data['fail_scroll'],
                                              vertical_scroll_only=True)]])

            layout.append([frame_failed_tests])
        # Passing tests
        rows = []
        for v in passing_tests:
            test_key = v['review_tab']
            if test_key is not None and test_key == key:
                comment = v['comment']
                icon = v['icon']
                result = v['result']
                key_name = v['test_name']
                rows.append(
                    create_auto_check_row(
                        comment, result, icon, key_name, max_check, user_text_x))
        if rows:
            frame_passed_tests = Sg.Frame('Passing Tests',
                                          [[Sg.Column([*rows],
                                                      size=frame_data['pass_size'],
                                                      scrollable=frame_data['pass_scroll'],
                                                      vertical_scroll_only=True)]])

            layout.append([frame_passed_tests])
        tab = Sg.Tab(key, [[Sg.Column(layout)]])
        tabs.append(tab)

    return tabs


# Define a function to handle events related to radio buttons
def on_manual_radio_button_click(window, event):
    """
    Updates the color and background of a text input element when a radio button is selected
    """
    prefix, radio = event[0].split(KEY_CHECK + KEY_RADIO)
    # indx = event[1]
    if radio == 'No':
        # Update text color and background when the "No" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#000000',
                                 background_color='#ffffff')
    else:
        # Update text color and background when the "Yes/NA" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#ffffff',
                                 background_color='#848884')


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


def build_manual_check_box_list(rso, beamsets):
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
        elif technique == 'DynamicArc':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_VMAT
        elif technique == 'SMLC':
            dict2 = CHECK_BOXES_PHYSICS_REVIEW_3D
        else:
            sys.exit(f'UNKNOWN TREATMENT TECHNIQUE {technique}')
        dict1 = merge_dicts(dict1, dict2)
        for level in dict1:
            for item in dict1[level]:
                item['result'] = ""
                item['comment'] = ""
                item['icon'] = None
    return dict1


def get_manual_failing_tests(tree_children):
    """
    Determine all tests that failed and passed from the tree
    :param tree_children:
    :return:
    """
    passing_tests = []
    # Find failing tests and determine total number of rows
    failed_tests = []
    for comment, child_key, result, pass_fail, icon in tree_children:
        review_tab, comment = search_string(comment)
        if pass_fail != PASS:
            failed_tests.append([comment, str(result), str(icon), review_tab])
        else:
            passing_tests.append(
                {'test_name': str(comment), 'result': str(result),
                 'icon': str(icon),
                 'comment': "Script Pass",
                 'review_tab': review_tab}
            )
    return passing_tests, failed_tests


def process_check_box_values(window, checks):
    """
    Parses the resulting window values and sorts the checkbox values.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        checks (dict): A dictionary containing the checkbox data.

    Returns:
        dict: A sorted dictionary containing the checkbox values.
    """
    sorted_results = {}
    for test_level in checks:
        sorted_results[test_level] = []
        for item in checks[test_level]:
            parsed_item = {'test_name': item['test_name']}
            radio_pre = f"{item['key']}{KEY_CHECK}{KEY_RADIO}"
            input_key = create_key(f"{item['key']}{KEY_CHECK}{KEY_INPUT_TEXT}")
            if window[create_key(radio_pre + 'Yes')].get():
                parsed_item['result'] = PASS
                parsed_item['icon'] = GREEN_CIRCLE
            elif window[create_key(radio_pre + 'No')].get():
                parsed_item['result'] = FAIL
                parsed_item['icon'] = RED_CIRCLE
            elif window[create_key(radio_pre + 'NA')].get():
                parsed_item['result'] = NA
                parsed_item['icon'] = BLUE_CIRCLE
            else:
                parsed_item['result'] = ALERT
                parsed_item['icon'] = YELLOW_CIRCLE
            parsed_item['comment'] = window[input_key].get()
            sorted_results[test_level].append(parsed_item)
    return sorted_results


def process_failed_tests(window, failures):
    """
    Parses the failed tests and adds them to a list.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        failures (list): A list of failed tests, where each item is a tuple containing a
        comment, result, icon file string, and the tab to which this was assigned
            and icon.

    Returns:
        list: A list of parsed failed tests.
    """
    failed_list = []
    for comment, test_result, icon, topic in failures:
        parsed_item = {
            'test_name': repr(comment),
            'result': repr(test_result),
            'icon': RED_CIRCLE,
            'topic': topic,
            'comment': repr(window[create_key(comment)].get())
        }
        failed_list.append(parsed_item)
    return failed_list
