# Import necessary modules and functions
import PySimpleGUI as sg
import logging
from PlanReview.review_definitions import CHECK_BOXES, PASS
from PlanReview.utils import get_user_name
from PlanReview.guis.gui_report_script_error import report_script_error
import json


def save_review(values):
    with open("review.json", "w") as f:
        json.dump(values, f)
    sg.popup("Review saved successfully!")


def load_review(window):
    try:
        with open("review.json", "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        sg.popup("No saved review found!")
        return
    for key, value in values.items():
        if key in CHECK_BOXES:
            for item in CHECK_BOXES[key]:
                radio_key = f"{item['key']}_RADIO"
                input_key = f"{item['key']}_INPUT"
                window[radio_key + '_YNA'](value[item['key']] == 'Yes/NA')
                window[radio_key + '_NO'](value[item['key']] == 'No')
                window[input_key](value[input_key])
        else:
            if key in window.key_dict:
                window[key](value)


def get_review_gui_values(window, failed_tests):
    """
    Extracts the values entered in the PySimpleGUI dialog and sorts them by keys.

    Parameters:
    - window: PySimpleGUI Window object representing the GUI
    - failed_tests: list of failed tests from the review_definitions module

    Returns:
    - sorted_values: dictionary of values sorted by keys
    """
    sorted_values = {}
    for key in CHECK_BOXES:
        sorted_values[key] = {}
        for item in CHECK_BOXES[key]:
            radio_key = f"{item['key']}_RADIO"
            input_key = f"{item['key']}_INPUT"
            if window[radio_key + '_YNA'].get():
                sorted_values[key][item['key']] = 'Yes/NA'
            elif window[radio_key + '_NO'].get():
                sorted_values[key][item['key']] = 'No'
            else:
                sorted_values[key][item['key']] = None
            sorted_values[key][input_key] = window[input_key].get()
    # Parse the failed tests
    key = 'Failed Tests'
    sorted_values[key] = {}
    for comment, result, icon in failed_tests:
        sorted_values[key][comment] = window[comment].get()

    return sorted_values


# Define a function to handle events related to radio buttons
def on_radio_button_click(window, event):
    """
    Updates the color and background of a text input element when a radio button is selected
    """
    if event.endswith('_RADIO_NO'):
        # Update text color and background when the "No" radio button is selected
        input_key = event.replace('_RADIO_NO', '_INPUT')
        window[input_key].update(text_color='#000000',
                                 background_color='#ffffff')
    if event.endswith('_RADIO_YNA'):
        # Update text color and background when the "Yes/NA" radio button is selected
        input_key = event.replace('_RADIO_YNA', '_INPUT')
        window[input_key].update(text_color='#ffffff',
                                 background_color='#848884')


# Event handler for "Done" button
def on_done_button_click(window, values):
    # Check if all the required fields are filled in
    is_valid = True
    for key in CHECK_BOXES:
        for item in CHECK_BOXES[key]:
            radio_yna_key = f'{item["key"]}_RADIO_YNA'
            radio_no_key = f'{item["key"]}_RADIO_NO'
            input_key = f'{item["key"]}_INPUT'
            if not values[radio_yna_key] and not values[radio_no_key]:
                window[radio_yna_key].update(text_color='#8B0000')
                window[radio_no_key].update(text_color='#8B0000')
                is_valid = False
            if values[radio_no_key] and not values[input_key]:
                window[input_key].update(text_color='#ffffff',
                                         background_color='#8B0000')
                is_valid = False

    if is_valid:
        # Perform the form submission logic
        sg.popup('Form submitted successfully.')
    else:
        sg.popup_error('Please fill in all the required fields.')
    return is_valid


def create_tab_manual_checks(failed_tests, main_width):
    """
    Creates a PySimpleGUI tab with multiple frames, each containing a checklist of options.
    """
    # Determine the maximum length of any checklist item
    max_check = max([len(item['text']) for key in CHECK_BOXES
                     for item in CHECK_BOXES[key]])

    # Create the list of elements for each key in CHECK_BOXES
    layout = [[sg.Text('Select an option for each item:')]]
    for key in CHECK_BOXES:
        # Create a frame for the current key
        frame_layout = []
        total_items = 0
        for item in CHECK_BOXES[key]:
            # Checklist item text and Radio buttons on the same row
            row1 = [sg.Text(item['text'], ),  # size=(max_check, 2)),
                    sg.Radio('Yes/NA', f'{item["key"]}_RADIO', default=False,
                             key=f'{item["key"]}_RADIO_YNA', enable_events=True),
                    sg.Radio('No', f'{item["key"]}_RADIO', default=False,
                             key=f'{item["key"]}_RADIO_NO', enable_events=True),
                    sg.InputText(size=(int(max_check * 1.2), 1),
                                 key=f'{item["key"]}_INPUT',
                                 enable_events=True,
                                 background_color='#E5DECE')
                    ]
            frame_layout.append(row1)
            total_items += 1
        if total_items > 5:
            scroll = True
            v_size = 150
        else:
            scroll = False
            v_size = 0
        frame = sg.Frame(key, [[sg.Column(frame_layout,
                                          scrollable=scroll,
                                          vertical_scroll_only=True,
                                          size=(1300, v_size))]])

        layout.append([frame])

    # Create frames for failed qa_tests
    rows = []
    for comment, result, icon in failed_tests:
        rows.append([sg.Image(icon),
                     sg.Text(result, size=(max_check, None),
                             auto_size_text=True, justification='left'),
                     sg.InputText(default_text=f"{comment}: Comment",
                                  key=comment,
                                  size=(int(1.1 * max_check), None),
                                  enable_events=True, pad=((40, 0), (0, 0)),
                                  text_color='#000000',
                                  background_color='#ffffff', border_width=0,
                                  justification='left', tooltip=comment)])

    frame_failed_tests = sg.Frame('Failed Tests',
                                  [[sg.Column([*rows],
                                              scrollable=True,
                                              vertical_scroll_only=True,
                                              size=(1300, 150))]])
    layout.append([frame_failed_tests])

    # Create and return the tab
    tab = sg.Tab('Miller Time', layout)
    return tab


def launch_physics_review_gui(rso, tree_data, tree_children):
    """
    Function to launch a GUI for reviewing physics checks and logs.

    Parameters:
    - rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
    - tree_data: sg tree data object
    - tree_children: a list for conversion into tree subsides

    Returns: None
    """

    # GUI setup
    sg.theme('LightBrown1')
    left_width = 140
    right_width = 10
    # Find failing tests and determine total number of rows
    failed_tests = []
    for comment, _, result, pass_fail, icon in tree_children:
        if pass_fail != PASS:
            failed_tests.append([comment, result, icon])
    tab2 = create_tab_manual_checks(failed_tests, left_width + right_width)

    # Bottom Frame
    bottom = [[
        sg.Button('Save'),
        sg.Button('Load'),
        sg.Button('Report Error', key='report_error'),
        sg.Button('Cancel'),
        sg.Button('Done'),
    ]]
    tab1 = [[sg.Frame('ReviewChecks:',
                      [[sg.Tree(
                          data=tree_data,
                          headings=['Result'],
                          auto_size_columns=False,
                          num_rows=60,
                          col0_width=left_width,
                          col_widths=[right_width],
                          key='-TREE-',
                          show_expanded=True,
                          justification="left",
                          vertical_scroll_only=True,
                          enable_events=True)]],
                      pad=(0, 0))]]

    layout = [[sg.TabGroup([[sg.Tab('Review and Logs', tab1)],
                            [tab2]])],
              [sg.Frame('', bottom)],
              ]

    window = sg.Window('Plan Review: ' + get_user_name(), layout)

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break
        elif event in 'Done':
            is_valid = on_done_button_click(window, values)
            if is_valid:
                dialog_values = get_review_gui_values(window, failed_tests)
                logging.debug(f'Dialog values {dialog_values}')
                break
        if event == 'Save':
            save_review(get_review_gui_values(window, failed_tests))
        elif event == 'Load':
            load_review(window)
        elif event == 'report_error':
            report_script_error(rso)
        elif event.endswith('_RADIO_NO'):
            on_radio_button_click(window, event)
        elif event.endswith('_RADIO_YNA'):
            on_radio_button_click(window, event)

    window.close()
