from typing import List, Dict, Union, Any, NamedTuple
import PySimpleGUI as Sg
from PlanReview.review_definitions import ICON_CHECKER
from PlanReview.utils.constants import (
    KEY_USER_COMMENT, KEY_PROCEED_REVISE, KEY_RADIO, KEY_QI_INFO, KEY_REVISION_INFO,
    KEY_SIDE_PANEL)
from PlanReview.guis.gui_qa_form import get_qa_form_input_components


def create_side_panel(comment_width_chars: int, window_height: int,
                      pix_per_char_height: int, save_space: bool = False) -> List[List[Any]]:
    """
    Create a side panel with comment boxes and radio buttons for user interface.

    Args:
        comment_width_chars (int): Width of the comment box in characters.
        window_height (int): Height of the window in pixels.
        pix_per_char_height (int): Pixel height for each character line.
        save_space (bool): Optional argument to save space.

    Returns:
        List[List[Any]]: Side panel layout for PySimpleGUI.

    Pseudocode:
        1. Calculate the line count for the comment box.
        2. Create the layout for the side panel.
        3. Return the side panel layout.
    """

    # Calculate the number of lines for the comment box

    comment_line_count = (0.35 * window_height) // pix_per_char_height
    comments_width = comment_width_chars
    # int(0.2*comment_width_chars) if save_space \
    # else int(0.70 * comment_width_chars)
    revision_width = int(0.6 * comments_width)
    qa_form_components = get_qa_form_input_components(comments_width)

    # Create layout for radio buttons
    side_panel = [
        # User comments
        [Sg.Text('Comments', text_color='blue', font=('Helvetica', 12, 'bold'))],
        [Sg.Multiline(default_text='', size=(comments_width, comment_line_count),
                      autoscroll=True, auto_size_text=True, key=KEY_USER_COMMENT, expand_x=True, expand_y=True)],
        # Create a row for "Proceed" radio button
        [Sg.Radio(
            "Proceed", group_id="RADIO_SIDE_PANEL",
            default=False, key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed", enable_events=True),
        ],
        # Create a row for "Proceed (QI Issue)" radio button
        [Sg.Radio("Proceed (QI Issue)", group_id="RADIO_SIDE_PANEL", default=False,
                  key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed", enable_events=True)],
        [Sg.Text("Brief Synopsis of \n QI Issue:", enable_events=True, visible=False, key="-QI_TEXT-", expand_x=False,
                 expand_y=False),
         Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
                      auto_size_text=True, enable_events=True, key=KEY_QI_INFO, visible=False, expand_x=True,
                      expand_y=True)
         ],
        # Create a row for "Revise" radio button
        [Sg.Radio("Revise", group_id="RADIO_SIDE_PANEL", default=False,
                  key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", enable_events=True)],
        [Sg.Text("Synopsis of reason \n for Revision:", enable_events=True, justification='left',
                 visible=False, key="-REVISION_TEXT-", expand_x=False, expand_y=False),
         Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
                      auto_size_text=True, enable_events=True, key=KEY_REVISION_INFO, visible=False, expand_x=True,
                      expand_y=True)],
    ]
    # Add the QA form components
    # Add the QA form components to an invisible frame
    qa_frame = [
        Sg.Frame('QA Form (not yet forwarded to wiki-form)', qa_form_components, key='-QA-FRAME-', visible=False)
    ]

    # Append the QA frame to the side_panel
    side_panel.append(qa_frame)

    # Append the final Image component
    side_panel.append([Sg.Image(filename=ICON_CHECKER, key='-CHECKER-IMAGE-', pad=((0, 0), (0, 0)),
                                size=(300, 300), enable_events=True,
                                tooltip="Launch QA Form")])

    return side_panel


def load_side_panel(window: Sg.Window, values: Dict[str, Any]) -> None:
    """
    Update the side panel in the main window with saved values.

    Args:
        window (Sg.Window): The PySimpleGUI window object to be updated.
        values (Dict[str, Any]): Dictionary containing saved side panel values.

    Returns:
        None

    Pseudocode:
        1. Retrieve saved side panel data from input values.
        2. Loop through each key-value pair.
        3. Update the window accordingly.
    """

    # Extract data for the side panel from the main window's saved values
    side_panel_values = values.get(KEY_SIDE_PANEL, {})

    # Loop through each key-value pair to update the window
    for field_key, saved_value in side_panel_values.items():
        if field_key == KEY_PROCEED_REVISE:
            # Use the radio key to trigger a click event
            load_radio = f"{KEY_PROCEED_REVISE}{KEY_RADIO}{saved_value}"
            on_side_panel_radio_button_click(window, load_radio)
        else:
            window[field_key].update(saved_value)


def extract_values_side_panel(window: Sg.Window) -> Dict[str, Dict[str, Any]]:
    """Extracts the current values from the side panel in a PySimpleGUI window.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the side panel.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary containing a single key-value pair,
        where the key is 'side_window' and the value is another dictionary
        containing the current values from the side panel.

    Pseudocode:
        1. Initialize an empty dictionary for storing side panel values.
        2. Loop through keys of interest, populating the dictionary with current or default values.
        3. Handle radio buttons and their associated text fields.
        4. Return the dictionary.
    """

    # Initialize an empty dictionary for side panel values
    side_panel = {}

    # Default values for keys of interest
    keys_with_defaults = {
        KEY_USER_COMMENT: '',  # Main window comments
        KEY_REVISION_INFO: '',  # Revision comments
        KEY_QI_INFO: ''  # Quality Improvement comments
    }

    # Extract current or default value for each key
    for key, default_value in keys_with_defaults.items():
        side_panel[key] = window[key].get() or default_value

    # Handle radio button states
    radio_options = {"Proceed": None, "Revise": KEY_REVISION_INFO, "QIProceed": KEY_QI_INFO}
    for option, text_key in radio_options.items():
        if window[f"{KEY_PROCEED_REVISE}{KEY_RADIO}{option}"].get():
            side_panel[KEY_PROCEED_REVISE] = option

            # Clear unrelated text fields
            for other_option, other_text_key in radio_options.items():
                if other_text_key and other_option != option:
                    side_panel[other_text_key] = ""

            # Update the text field for the selected radio button, if applicable
            if text_key:
                side_panel[text_key] = window[text_key].get()
            break
    else:
        side_panel[KEY_PROCEED_REVISE] = ""

    return {KEY_SIDE_PANEL: side_panel}


def on_side_panel_radio_button_click(window: Sg.Window, event: str) -> None:
    """Handles radio button clicks in the side panel of a PySimpleGUI window.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the radio buttons.
        event (str): The event string for the clicked radio button.

    Returns:
        None
    """
    # Mapping of radio button choices to their visibility settings
    visibility_map = {
        'Proceed': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed", False, False),
        'Revise': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", True, False),
        'QIProceed': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed", False, True)
    }

    # Find the radio button choice that was clicked
    choice = next((key for key, items in visibility_map.items() if event == items[0]), "")

    if choice:
        radio_key, revision_visibility, qi_visibility = visibility_map[choice]
        # Update UI components based on the radio button choice
        window[radio_key].update(value=True)
        window["-REVISION_TEXT-"].update(visible=revision_visibility)
        window[KEY_REVISION_INFO].update(visible=revision_visibility)
        window["-QI_TEXT-"].update(visible=qi_visibility)
        window[KEY_QI_INFO].update(visible=qi_visibility)
        window.refresh()


def update_window_error(window: Sg.Window, key: str, bg: bool = False) -> None:
    """Updates the text color of a PySimpleGUI window element to indicate an error.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the element.
        key (str): The key of the element to update.
        bg (bool, optional): Whether to update the background color as well. Defaults to False.

    Returns:
        None
    """
    error_text_color = '#8B0000'
    if bg:
        window[key].update(text_color=error_text_color, background_color=error_text_color)
    else:
        window[key].update(text_color=error_text_color)


def check_radio_on(values: Dict[str, Union[bool, str]], keys: List[str]) -> bool:
    """Checks if any radio buttons are selected based on their keys and values.

    Args:
        values (Dict[str, Union[bool, str]]): A dictionary of keys and their current values.
        keys (List[str]): A list of keys corresponding to radio buttons.

    Returns:
        bool: True if any radio button is selected, otherwise False.
    """
    return any(values[k] for k in keys)


def is_valid_side_panel(window: Sg.Window, values: Dict[str, Union[bool, str]]) -> bool:
    """Validates the state of a side panel in a PySimpleGUI window.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the side panel.
        values (Dict[str, Union[bool, str]]): A dictionary of keys and their current values.

    Returns:
        bool: True if the side panel is valid, otherwise False.
    """
    is_valid = True

    revision_radio_text = {
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed": (None, None),
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise": ("-REVISION_TEXT-", KEY_REVISION_INFO),
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed": ("-QI_TEXT-", KEY_QI_INFO),
    }

    if not check_radio_on(values, list(revision_radio_text.keys())):
        for r in revision_radio_text.keys():
            update_window_error(window, r)
        Sg.popup_error('Proceed or Revise is required to proceed')
        is_valid = False

    for radio_key, (text_key, input_key) in revision_radio_text.items():
        if text_key and input_key and values[radio_key] and not values[input_key]:
            update_window_error(window, text_key)
            update_window_error(window, input_key)
            Sg.popup_error('Please provide a reason for revision or a QI suggestion')
            is_valid = False

    return is_valid


