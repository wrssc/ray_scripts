from typing import List, Dict, Union, Any
import PySimpleGUI as Sg
import logging
from PlanReview.review_definitions import ICON_CHECKER
from PlanReview.utils.constants import (
    KEY_USER_COMMENT, KEY_PROCEED_REVISE, KEY_RADIO, KEY_QI_INFO,
    KEY_REVISION_INFO, KEY_SIDE_PANEL, KEY_DOSE_QI, KEY_REVISION_NUMBER,
    KEY_DOSE_REVISION_INFO, KEY_DOSE_QI_INFO, KEY_DOSE_REVISION)
from PlanReview.guis.gui_qa_form import get_qa_form_input_components

#
# Configuration elements for the side panel
# Configuration for Physics Review
comment_width_chars = 40
physics_config = {
    "elements": [
        {"sg_type": "text", "label": "Plan Comments", "key": "Plan Comments", "font": ('Helvetica', 14, 'bold'),
         "text_color": 'blue'},
        {"sg_type": "multiline", "key": KEY_USER_COMMENT, "size": (comment_width_chars, 30), "default_text": ''},
        {"sg_type": "radio", "label": "Proceed", "group_id": "RADIO_SIDE_PANEL",
         "key": f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed"},
        {"sg_type": "radio", "label": "Proceed (QI Issue)", "group_id": "RADIO_SIDE_PANEL",
         "key": f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)",
         "extra": [{"sg_type": "text", "label": "Brief Synopsis of \n QI Issue:", "key": "-QI_TEXT-", "visible": False},
                   {"sg_type": "multiline", "key": KEY_QI_INFO, "size": (comment_width_chars, 4),
                    "default_text": '', "visible": False}]
         },
        {"sg_type": "radio", "label": "Revise", "group_id": "RADIO_SIDE_PANEL",
         "key": f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise",
         "extra": [{"sg_type": "text", "label": "Synopsis of reason \n for Revision:", "key": "-REVISION_TEXT-",
                    "visible": False},
                   {"sg_type": "multiline", "key": KEY_REVISION_INFO, "size": (comment_width_chars, 4),
                    "default_text": '',
                    "visible": False}]
         }
    ]
}

# Configuration for Dosimetry Review
dosimetry_config = {
    "elements": [
        {"sg_type": "text", "label": "Comments to physics", "key": "Dose Comments", "font": ('Helvetica', 12, 'bold'),
         "text_color": 'yellow'},
        {"sg_type": "multiline", "key": KEY_USER_COMMENT, "size": (40, 10), "default_text": ''},
        {"sg_type": "checkbox", "label": "QI Suggestion", "key": f"{KEY_DOSE_QI}", "extra": [
            {"sg_type": "text", "label": "Brief Synopsis of \n QI Issue:", "key": "-QI_TEXT-", "visible": False},
            {"sg_type": "multiline", "key": f"{KEY_DOSE_QI_INFO}", "size": (24, 2), "default_text": '',
             "visible": False}
        ]},
        {"sg_type": "checkbox", "label": "Revise", "key": f"{KEY_DOSE_REVISION}",
         "extra": [{"sg_type": "text", "label": "# of plan revisions:", "key": "-REVISION_#_TEXT-", "visible": False},
                   {"sg_type": "combo", "values": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "key": KEY_REVISION_NUMBER,
                    "visible": False},
                   {"sg_type": "text", "label": "Summary of Revision(s):", "key": "-REVISION_TEXT-",
                    "visible": False},
                   {"sg_type": "multiline", "key": f"{KEY_DOSE_REVISION_INFO}", "size": (24, 2), "default_text": '',
                    "visible": False}
                   ]}
    ]
}


def create_side_panel(comment_width_chars: int, window_height: int,
                      pix_per_char_height: int, save_space: bool = False,
                      review_type: str = 'Physics') -> List[List[Any]]:
    """
    Create a side panel with comment boxes and radio buttons for user interface.

    Args:
        comment_width_chars (int): Width of the comment box in characters.
        window_height (int): Height of the window in pixels.
        pix_per_char_height (int): Pixel height for each character line.
        save_space (bool): Optional argument to save space.
        review_type (str): Type of review being performed.

    Returns:
        List[List[Any]]: Side panel layout for PySimpleGUI.
    """
    # Select the appropriate configuration
    config = dosimetry_config if review_type.lower() == 'dosimetry' else physics_config

    # Calculate the number of lines for the comment box
    comment_line_count = (0.35 * window_height) // pix_per_char_height
    comments_width = comment_width_chars

    # Initialize the side panel layout
    side_panel = []

    # Create UI elements based on the configuration
    for sg_element in config["elements"]:
        if sg_element["sg_type"] == "text":
            side_panel.append([Sg.Text(sg_element["label"], text_color=sg_element.get("text_color", 'black'),
                                       font=sg_element.get("font", ('Helvetica', 12, 'bold')),
                                       key=sg_element["key"], visible=True)])

        elif sg_element["sg_type"] == "multiline":
            side_panel.append([Sg.Multiline(default_text=sg_element["default_text"],
                                            size=sg_element["size"],
                                            autoscroll=True, auto_size_text=True,
                                            key=sg_element["key"],
                                            visible=sg_element.get("visible", True))])

        elif sg_element["sg_type"] == "radio":
            side_panel.append([Sg.Radio(sg_element["label"], group_id=sg_element["group_id"],
                                        default=False, key=sg_element["key"],
                                        enable_events=True)])
            for extra in sg_element.get("extra", []):
                if extra["sg_type"] == "text":
                    side_panel.append([Sg.Text(extra["label"], key=extra["key"],
                                               visible=extra.get("visible", False))])
                elif extra["sg_type"] == "multiline":
                    side_panel.append([Sg.Multiline(default_text=extra["default_text"],
                                                    size=extra["size"], autoscroll=True,
                                                    auto_size_text=True, key=extra["key"],
                                                    visible=extra.get("visible", False))])

        elif sg_element["sg_type"] == "checkbox":
            side_panel.append([Sg.Checkbox(sg_element["label"], default=False, key=sg_element["key"],
                                           enable_events=True)])
            for extra in sg_element.get("extra", []):
                if extra["sg_type"] == "text":
                    side_panel.append([Sg.Text(extra["label"], key=extra["key"],
                                               visible=extra.get("visible", False))])
                elif extra["sg_type"] == "multiline":
                    side_panel.append([Sg.Multiline(default_text=extra["default_text"],
                                                    size=extra["size"], autoscroll=True,
                                                    auto_size_text=True, key=extra["key"],
                                                    visible=extra.get("visible", False))])
                elif extra["sg_type"] == "combo":
                    side_panel.append([Sg.Combo(extra["values"], key=extra["key"],
                                                visible=extra.get("visible", False))])

    # Add the QA form components
    qa_form_components = get_qa_form_input_components(comments_width)
    qa_frame = [
        Sg.Frame('QA Form (not yet forwarded to wiki-form)', qa_form_components, key='-QA-FRAME-', visible=False)]
    side_panel.append(qa_frame)

    # Append the final Image component
    side_panel.append([Sg.Image(filename=ICON_CHECKER, key='-CHECKER-IMAGE-', pad=((0, 0), (0, 0)),
                                size=(300, 300), enable_events=True, tooltip="Launch QA Form")])

    # Define side panel events
    side_panel_events = [element["key"] for element in config["elements"]]
    for sg_element in config["elements"]:
        for extra in sg_element.get("extra", []):
            side_panel_events.append(extra["key"])

    return side_panel, side_panel_events


# def old_create_side_panel(comment_width_chars: int, window_height: int,
#                           pix_per_char_height: int, save_space: bool = False,
#                           review_type: str = 'Physics') -> List[List[Any]]:
#     """
#     Create a side panel with comment boxes and radio buttons for user interface.
#
#     Args:
#         comment_width_chars (int): Width of the comment box in characters.
#         window_height (int): Height of the window in pixels.
#         pix_per_char_height (int): Pixel height for each character line.
#         save_space (bool): Optional argument to save space.
#         review_type (str): Type of review being performed.
#
#     Returns:
#         List[List[Any]]: Side panel layout for PySimpleGUI.
#
#     Pseudocode:
#         1. Calculate the line count for the comment box.
#         2. Create the layout for the side panel.
#         3. Return the side panel layout.
#     """
#     # Calculate the number of lines for the comment box
#
#     comment_line_count = (0.35 * window_height) // pix_per_char_height
#     comments_width = comment_width_chars
#     # int(0.2*comment_width_chars) if save_space \
#     # else int(0.70 * comment_width_chars)
#     revision_width = int(0.6 * comments_width)
#     qa_form_components = get_qa_form_input_components(comments_width)
#     if review_type == 'Dosimetry':
#         side_panel = [
#             # User comments
#             [Sg.Text('Comments to physics', text_color='yellow', font=('Helvetica', 12, 'bold'))],
#             [Sg.Multiline(default_text='', size=(comments_width, comment_line_count),
#                           autoscroll=True, auto_size_text=True, key=KEY_USER_COMMENT,
#                           )],
#             # Create a row for "Proceed (QI Issue)" radio button
#             [Sg.Checkbox("QI Suggestion", default=False,
#                          key=f"{KEY_DOSE_QI}", enable_events=True)],
#             [Sg.Text("Brief Synopsis of \n QI Issue:", enable_events=True, visible=False, key="-QI_TEXT-",
#                      ),
#              Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
#                           auto_size_text=True, enable_events=True, key=f"{KEY_DOSE_QI_INFO}", visible=False,
#                           ),
#              ],
#             # Create a row for "Revise" radio button
#             [Sg.Checkbox("Revise", default=False,
#                          key=f"{KEY_DOSE_REVISION}", enable_events=True),
#              Sg.Combo([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
#                       key=KEY_REVISION_NUMBER, enable_events=True, visible=False, )],
#             [Sg.Text("Synopsis of reason \n for Revision(s):", enable_events=True, justification='left',
#                      visible=False, key="-REVISION_TEXT-",
#                      ## QT expand_x=False, expand_y=False
#                      ),
#              Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
#                           auto_size_text=True, enable_events=True, key=f"{KEY_DOSE_REVISION_INFO}", visible=False,
#                           ## QT expand_x=True, expand_y=True
#                           )]]
#         side_panel_events = [f"{KEY_DOSE_QI}", f"{KEY_DOSE_REVISION}", KEY_REVISION_NUMBER,
#                              f"{KEY_DOSE_REVISION_INFO}"]
#         return side_panel, side_panel_events
#
#     # Create layout for radio buttons
#     side_panel = [
#         # User comments
#         [Sg.Text('Comments', text_color='blue', font=('Helvetica', 12, 'bold'))],
#         [Sg.Multiline(default_text='', size=(comments_width, comment_line_count),
#                       autoscroll=True, auto_size_text=True, key=KEY_USER_COMMENT,  ## QT expand_x=True, expand_y=True,
#                       )],
#         # Create a row for "Proceed" radio button
#         [Sg.Radio(
#             "Proceed", group_id="RADIO_SIDE_PANEL",
#             default=False, key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed", enable_events=True),
#         ],
#         # Create a row for "Proceed (QI Issue)" radio button
#         [Sg.Radio("Proceed (QI Issue)", group_id="RADIO_SIDE_PANEL", default=False,
#                   key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed", enable_events=True)],
#         [Sg.Text("Brief Synopsis of \n QI Issue:", enable_events=True, visible=False, key="-QI_TEXT-",
#                  ## QT expand_x=False, expand_y=False
#                  ),
#          Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
#                       auto_size_text=True, enable_events=True, key=KEY_QI_INFO, visible=False,
#                       ## QT expand_x=True, expand_y=True
#                       )
#          ],
#         # Create a row for "Revise" radio button
#         [Sg.Radio("Revise", group_id="RADIO_SIDE_PANEL", default=False,
#                   key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", enable_events=True)],
#         [Sg.Text("Synopsis of reason \n for Revision:", enable_events=True, justification='left',
#                  visible=False, key="-REVISION_TEXT-",
#                  ## QT expand_x=False, expand_y=False
#                  ),
#          Sg.Multiline(default_text='', size=(revision_width, 2), autoscroll=True,
#                       auto_size_text=True, enable_events=True, key=KEY_REVISION_INFO, visible=False,
#                       ## QT expand_x=True, expand_y=True
#                       )],
#     ]
#     # Add the QA form components
#     # Add the QA form components to an invisible frame
#     qa_frame = [
#         Sg.Frame('QA Form (not yet forwarded to wiki-form)', qa_form_components, key='-QA-FRAME-', visible=False)
#     ]
#
#     # Append the QA frame to the side_panel
#     side_panel.append(qa_frame)
#
#     # Append the final Image component
#     side_panel.append([Sg.Image(filename=ICON_CHECKER, key='-CHECKER-IMAGE-', pad=((0, 0), (0, 0)),
#                                 size=(300, 300), enable_events=True,
#                                 tooltip="Launch QA Form")])
#     side_panel_events = [f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed", f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise",
#                          f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed", KEY_REVISION_INFO, KEY_QI_INFO]
#     return side_panel, side_panel_events


def load_side_panel(window: Sg.Window, values: Dict[str, Any], review_type) -> None:
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
        if field_key in window.key_dict:
            if field_key == KEY_PROCEED_REVISE:
                # Use the radio key to trigger a click event
                load_radio = f"{KEY_PROCEED_REVISE}{KEY_RADIO}{saved_value}"
                on_side_panel_radio_button_click(window, load_radio, review_type)
            elif field_key in [KEY_DOSE_REVISION, KEY_DOSE_QI]:
                window[field_key].update(saved_value)
                on_side_panel_radio_button_click(window, field_key, review_type)
            else:
                window[field_key].update(saved_value)
        else:
            logging.warning(f"During side-panel load key {field_key} not found in window")


# def old_extract_values_side_panel(window: Sg.Window) -> Dict[str, Dict[str, Any]]:
#     """Extracts the current values from the side panel in a PySimpleGUI window.
#
#     Args:
#         window (Sg.Window): The PySimpleGUI window object containing the side panel.
#
#     Returns:
#         Dict[str, Dict[str, Any]]: A dictionary containing a single key-value pair,
#         where the key is 'side_window' and the value is another dictionary
#         containing the current values from the side panel.
#
#     Pseudocode:
#         1. Initialize an empty dictionary for storing side panel values.
#         2. Loop through keys of interest, populating the dictionary with current or default values.
#         3. Handle radio buttons and their associated text fields.
#         4. Return the dictionary.
#     """
#
#     # Initialize an empty dictionary for side panel values
#     side_panel = {}
#
#     # Default values for keys of interest
#     keys_with_defaults = {
#         KEY_USER_COMMENT: '',  # Main window comments
#         KEY_REVISION_INFO: '',  # Revision comments
#         KEY_QI_INFO: ''  # Quality Improvement comments
#     }
#
#     # Extract current or default value for each key
#     for key, default_value in keys_with_defaults.items():
#         side_panel[key] = window[key].get() or default_value
#
#     # Handle radio button states
#     radio_options = {"Proceed": None, "Revise": KEY_REVISION_INFO, "QIProceed": KEY_QI_INFO}
#     for option, text_key in radio_options.items():
#         if window[f"{KEY_PROCEED_REVISE}{KEY_RADIO}{option}"].get():
#             side_panel[KEY_PROCEED_REVISE] = option
#
#             # Clear unrelated text fields
#             for other_option, other_text_key in radio_options.items():
#                 if other_text_key and other_option != option:
#                     side_panel[other_text_key] = ""
#
#             # Update the text field for the selected radio button, if applicable
#             if text_key:
#                 side_panel[text_key] = window[text_key].get()
#             break
#     else:
#         side_panel[KEY_PROCEED_REVISE] = ""
#
#     return {KEY_SIDE_PANEL: side_panel}
#

def extract_values_side_panel(window: Sg.Window, review_type: str) -> Dict[str, Dict[str, Any]]:
    """Extracts the current values from the side panel in a PySimpleGUI window based on review type.

    Args:
        window (sg.Window): The PySimpleGUI window object containing the side panel.
        review_type (str): The type of review ('physics' or 'dosimetry').

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary containing a single key-value pair,
        where the key is 'side_window' and the value is another dictionary
        containing the current values from the side panel.
    """

    # Select the appropriate configuration
    config = dosimetry_config if review_type.lower() == 'dosimetry' else physics_config

    # Initialize an empty dictionary for side panel values
    side_panel = {}

    # Extract current or default value for each element in the configuration
    for element in config["elements"]:
        key = element["key"]
        element_type = element["sg_type"]

        if element_type in ["multiline", "checkbox", "combo"]:
            side_panel[key] = window[key].get() or element.get("default_text", "")
            if "extra" in element.keys():
                for extra in element["extra"]:
                    extra_type = extra["sg_type"]
                    if extra_type == "text":
                        continue
                    extra_key = extra["key"]
                    side_panel[extra_key] = window[extra_key].get() or extra.get("default_text", "")

        elif element_type == "radio":
            group_id = element["group_id"]
            for radio_element in config["elements"]:
                if radio_element["sg_type"] == "radio" and radio_element["group_id"] == group_id:
                    radio_key = radio_element["key"]
                    if window[radio_key].get():
                        side_panel[KEY_PROCEED_REVISE] = radio_element["label"]

                        if "extra" in radio_element:
                            for extra in radio_element["extra"]:
                                if extra["sg_type"] == "text":
                                    continue
                                extra_key = extra["key"]
                                side_panel[extra_key] = window[extra_key].get() or ""
                        break
            else:
                side_panel[KEY_PROCEED_REVISE] = ""

    return {KEY_SIDE_PANEL: side_panel}


# def old_on_side_panel_radio_button_click(window: Sg.Window, event: str, review_type: str) -> None:
#     """Handles radio button clicks in the side panel of a PySimpleGUI window.
#
#     Args:
#         window (Sg.Window): The PySimpleGUI window object containing the radio buttons.
#         event (str): The event string for the clicked radio button.
#         review_type (str): The type of review being performed.
#
#     Returns:
#         None
#     """
#     # Mapping of radio button choices to their visibility settings
#     import logging
#     logging.debug(f"Review type: {review_type}, and event: {event}")
#     if review_type == 'Physics':
#         visibility_map = {
#             'Proceed': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed", False, False),
#             'Revise': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", True, False),
#             'QIProceed': (f"{KEY_PROCEED_REVISE}{KEY_RADIO}QIProceed", False, True)
#         }
#         # Find the radio button choice that was clicked
#         choice = next((key for key, items in visibility_map.items() if event == items[0]), "")
#
#         if choice:
#             radio_key, revision_visibility, qi_visibility = visibility_map[choice]
#             # Update UI components based on the radio button choice
#             window[radio_key].update(value=True)
#             window["-REVISION_TEXT-"].update(visible=revision_visibility)
#             window[KEY_REVISION_INFO].update(visible=revision_visibility)
#             window["-QI_TEXT-"].update(visible=qi_visibility)
#             window[KEY_QI_INFO].update(visible=qi_visibility)
#             window.refresh()
#     elif review_type == 'Dosimetry':
#         if event == KEY_DOSE_REVISION:
#             window[f"{KEY_REVISION_NUMBER}"].update(visible=True)
#             window[f"{KEY_DOSE_REVISION_INFO}"].update(visible=True)
#             window[f"-REVISION_TEXT-"].update(visible=True)
#
#         elif event == KEY_DOSE_QI:
#             window[f"{KEY_DOSE_QI}"].update(visible=False)
#             window[f"{KEY_DOSE_QI_INFO}"].update(visible=False)
#         window.refresh()


def on_side_panel_radio_button_click(window: Sg.Window, event: str, review_type: str) -> None:
    """Handles side panel events in the PySimpleGUI window.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the radio buttons.
        event (str): The event string for the clicked radio button.
        review_type (str): The type of review being performed.

    Returns:
        None
    """

    # Select the appropriate configuration
    config = dosimetry_config if review_type.lower() == 'dosimetry' else physics_config

    # Initialize visibility maps
    radio_visibility_map = {}
    extra_visibility_map = {}

    # Build visibility maps from the configuration
    for element in config["elements"]:
        if element["sg_type"] == "radio":
            radio_visibility_map[element["key"]] = {
                "revision_visibility": False,
                "qi_visibility": False,
                "extra": element.get("extra", [])
            }
            for extra in element.get("extra", []):
                if "qi" in extra["key"].lower():
                    radio_visibility_map[element["key"]]["qi_visibility"] = True
                if "revision" in extra["key"].lower():
                    radio_visibility_map[element["key"]]["revision_visibility"] = True
                extra_visibility_map[extra["key"]] = False

    # Handle radio button click event
    if event in radio_visibility_map:
        # Set all radios in the group to false first
        for radio_key in radio_visibility_map:
            window[radio_key].update(value=False)

        # Set clicked radio to true
        window[event].update(value=True)

        # Update the visibility of extra elements based on the clicked radio
        selected_radio = radio_visibility_map[event]
        for extra in selected_radio["extra"]:
            extra_visibility_map[extra["key"]] = True

        # Apply visibility settings
        for extra_key, visible in extra_visibility_map.items():
            window[extra_key].update(visible=visible)
            window.refresh()

    # Handle checkboxes for dosimetry review
    if review_type.lower() == 'dosimetry':
        if event == KEY_DOSE_REVISION:
            window["-REVISION_#_TEXT-"].update(visible=True)
            window[KEY_REVISION_NUMBER].update(visible=True)
            window[KEY_DOSE_REVISION_INFO].update(visible=True)
            window["-REVISION_TEXT-"].update(visible=True)

        elif event == KEY_DOSE_QI:
            window[KEY_DOSE_QI_INFO].update(visible=True)
            window["-QI_TEXT-"].update(visible=True)

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
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)": ("-QI_TEXT-", KEY_QI_INFO),
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
