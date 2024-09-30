from typing import List, Dict, Union, Any
import PySimpleGUI as Sg
import logging
from PlanReview.review_definitions import ICON_CHECKER
from PlanReview.utils.constants import (
    KEY_USER_COMMENT, KEY_PROCEED_REVISE, KEY_RADIO, KEY_QI_INFO,
    KEY_REVISION_INFO, KEY_SIDE_PANEL, KEY_DOSE_QI, KEY_REVISION_NUMBER,
    KEY_DOSE_REVISION_INFO, KEY_DOSE_QI_INFO, KEY_DOSE_REVISION, KEY_OUT_DOSE_COMMENT)
from PlanReview.guis.gui_qa_form import get_qa_form_input_components
from PlanReview.utils.email_results import (email_report_qi_issue, email_report_revision, save_report)
from PlanReview.utils.io_file_utils import append_to_csv
from PlanReview.utils import get_user_name

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
        {"sg_type": "multiline", "key": KEY_OUT_DOSE_COMMENT, "size": (comment_width_chars, 10), "default_text": ''},
        {"sg_type": "checkbox", "label": "QI Suggestion", "key": f"{KEY_DOSE_QI}", "extra": [
            {"sg_type": "text", "label": "Brief Synopsis of \n QI Issue:", "key": "-QI_TEXT-", "visible": False},
            {"sg_type": "multiline", "key": f"{KEY_DOSE_QI_INFO}", "size": (comment_width_chars, 2), "default_text": '',
             "visible": False}
        ]},
        {"sg_type": "checkbox", "label": "Revise", "key": f"{KEY_DOSE_REVISION}",
         "extra": [{"sg_type": "text", "label": "# of plan revisions:", "key": "-REVISION_#_TEXT-", "visible": False},
                   {"sg_type": "combo", "values": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "key": KEY_REVISION_NUMBER,
                    "visible": False},
                   {"sg_type": "text", "label": "Summary of Revision(s):", "key": "-REVISION_TEXT-",
                    "visible": False},
                   {"sg_type": "multiline", "key": f"{KEY_DOSE_REVISION_INFO}", "size": (comment_width_chars, 2),
                    "default_text": '', "visible": False}
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


def side_panel_proceed_qi_true(values):
    """ Test to determine if the side panel has QI or Revise selected,
    check both physics and dosimetry configurations."""
    return any(values.get(key) for key in [
        f"{KEY_DOSE_QI}", f"{KEY_DOSE_REVISION}",
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)"])


def side_panel_revision_true(values):
    """ Test to determine if the side panel has Revise selected """
    return values.get(f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", False)


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


def update_qi_revision_tracking(rso, values):
    """
    Generate and distribute a revision report based on the values entered in the
    side panel of the PySimpleGUI window.
    Args:
        rso: (NamedTuple): The RSO object containing the patient and beamset information.
        values: (dict) pySimpleGUI window values

    Returns: None
    """
    is_physics_revision = values.get(f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", False)
    is_dose_revision = values.get(f"{KEY_DOSE_REVISION}", False)
    is_dose_qi = values.get(f"{KEY_DOSE_QI}", False)
    is_physics_qi = values.get(f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)", False)

    user_name = get_user_name()
    # Extract values from the window
    user_comments = values.get(KEY_USER_COMMENT, None)
    dose_comments = values.get(KEY_OUT_DOSE_COMMENT, None)
    revision_comments = values.get(KEY_REVISION_INFO, None)
    dose_revision_comments = values.get(KEY_DOSE_REVISION_INFO, None)
    revision_number = values.get(KEY_REVISION_NUMBER, None)
    dose_qi_text = values.get(KEY_DOSE_QI_INFO, None)
    qi_text = values.get(KEY_QI_INFO, None)

    # Append the report to the CSV file
    append_to_csv(
        patient_id=rso.patient.PatientID,
        beamset_name=rso.beamset.DicomPlanLabel,
        user_name=user_name,
        user_comments=user_comments,
        dose_comments=dose_comments,
        is_physics_revision=is_physics_revision,
        is_dose_revision=is_dose_revision,
        is_dose_qi=is_dose_qi,
        is_physics_qi=is_physics_qi,
        dose_qi_comments=dose_qi_text,
        qi_comments=qi_text,
        revision_comments=revision_comments,
        revision_number=revision_number,
        dose_revision_comments=dose_revision_comments,
    )


def generate_and_distribute_qi_issue_report(rso, values):
    """
    Generate and distribute a QI issue report based on the values entered in the
    side panel of the PySimpleGUI window, and append the report to a CSV file.

    Args:
        rso: (NamedTuple): The RSO object containing the patient and beamset information.
        values: (dict): PySimpleGUI window values.

    Returns:
        None
    """
    user_name = get_user_name()

    # Extract values from the window
    user_comments = values.get(KEY_USER_COMMENT, None)
    dose_comments = values.get(KEY_OUT_DOSE_COMMENT, None)
    dose_qi_text = values.get(KEY_DOSE_QI_INFO, None)
    qi_text = values.get(KEY_QI_INFO, None)

    # Build the report description
    description = (
        f"User Comments:\n\t{user_comments}\n\n"
        f"Dosimetry Comments:\n\t{dose_comments}\n\n"
        f"QI Comments:\n\t{qi_text}\n\n"
        f"Dosimetry QI Comments:\n\t{dose_qi_text}\n\n"
    )

    # Save and email the report
    file_path = save_report(
        report_type='qi_report',
        patient_id=rso.patient.PatientID,
        beamset_name=rso.beamset.DicomPlanLabel,
        user_name=user_name,
        report_text=description
    )
    email_report_qi_issue(file_path)
    # Update the CSV file
    update_qi_revision_tracking(rso, values)


def generate_and_distribute_revision_report(rso, values):
    """
    Generate and distribute a revision report based on the values entered in the
    side panel of the PySimpleGUI window.
    Args:
        rso: (NamedTuple): The RSO object containing the patient and beamset information.
        values: (dict) pySimpleGUI window values

    Returns: None
    """
    user_name = get_user_name()
    # Extract values from the window
    user_comments = values.get(KEY_USER_COMMENT, None)
    dose_comments = values.get(KEY_OUT_DOSE_COMMENT, None)
    revision_comments = values.get(KEY_REVISION_INFO, None)

    # Build the report description
    description = (
        f"User Comments:\n\t{user_comments}\n\n"
        f"Dosimetry Comments:\n\t{dose_comments}\n\n"
        f"Revision Comments:\n\t{revision_comments}"
    )

    # Save and email the report
    file_path = save_report(
        report_type='revision_report',
        patient_id=rso.patient.PatientID,
        beamset_name=rso.beamset.DicomPlanLabel,
        user_name=user_name,
        report_text=description
    )
    email_report_revision(file_path)
    # Update the CSV file
    update_qi_revision_tracking(rso, values)
