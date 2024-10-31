from typing import List, Dict, Union, Any, Optional, Tuple
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
from dataclasses import dataclass, field

#
# Configuration elements for the side panel
comment_width_chars = 40  # Width of the comment box in characters


@dataclass
class ElementConfig:
    sg_type: str
    label: Optional[str] = ''
    key: Optional[str] = ''
    font: Optional[tuple] = ('Helvetica', 12, 'bold')
    text_color: Optional[str] = 'black'
    size: Optional[tuple] = None
    default_text: Optional[str] = ''
    group_id: Optional[str] = ''
    values: Optional[List[Any]] = field(default_factory=list)
    visible: Optional[bool] = True
    enable_events: Optional[bool] = False
    extra: Optional[List['ElementConfig']] = field(default_factory=list)


@dataclass
class SidePanelConfig:
    elements: List[ElementConfig]


# Configuration for Physics Review
physics_config = SidePanelConfig(elements=[
    ElementConfig(
        sg_type="text",
        label="Plan Comments",
        key="Plan Comments",
        font=('Helvetica', 14, 'bold'),
        text_color='blue'
    ),
    ElementConfig(
        sg_type="multiline",
        key=KEY_USER_COMMENT,
        size=(comment_width_chars, 30),
        default_text=''
    ),
    ElementConfig(
        sg_type="radio",
        label="Proceed",
        group_id=f"{KEY_PROCEED_REVISE}{KEY_RADIO}",
        key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed",
        enable_events=True
    ),
    ElementConfig(
        sg_type="radio",
        label="Proceed (QI Issue)",
        group_id=f"{KEY_PROCEED_REVISE}{KEY_RADIO}",
        key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)",
        enable_events=True,
        extra=[
            ElementConfig(
                sg_type="text",
                label="Brief Synopsis of \n QI Issue:",
                key="-QI_TEXT-",
                visible=False
            ),
            ElementConfig(
                sg_type="multiline",
                key=KEY_QI_INFO,
                size=(comment_width_chars, 4),
                default_text='',
                visible=False
            )
        ]
    ),
    ElementConfig(
        sg_type="radio",
        label="Revise",
        group_id=f"{KEY_PROCEED_REVISE}{KEY_RADIO}",
        key=f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise",
        enable_events=True,
        extra=[
            ElementConfig(
                sg_type="text",
                label="Synopsis of reason \n for Revision:",
                key="-REVISION_TEXT-",
                visible=False
            ),
            ElementConfig(
                sg_type="multiline",
                key=KEY_REVISION_INFO,
                size=(comment_width_chars, 4),
                default_text='',
                visible=False
            )
        ]
    )
])

# Configuration for Dosimetry Review
label_revisions_yes = "Revisions Required"
label_revisions_no = "No Revisions"
label_qi_yes = "QI Issue"
label_qi_no = "QI Issue: None"
dosimetry_config = SidePanelConfig(elements=[
    ElementConfig(
        sg_type="text",
        label="Comments to physics",
        key="Dose Comments",
        font=('Helvetica', 12, 'bold'),
        text_color='yellow'
    ),
    ElementConfig(
        sg_type="multiline",
        key=KEY_OUT_DOSE_COMMENT,
        size=(comment_width_chars, 10),
        default_text=''
    ),
    ElementConfig(
        sg_type="radio",
        label=label_qi_no,
        group_id=f"{KEY_DOSE_QI}{KEY_RADIO}",
        key=f"{KEY_DOSE_QI}{KEY_RADIO}{label_qi_no}",
        enable_events=True
    ),
    ElementConfig(
        sg_type="radio",
        label=f"{label_qi_yes}",
        group_id=f"{KEY_DOSE_QI}{KEY_RADIO}",
        key=f"{KEY_DOSE_QI}{KEY_RADIO}{label_qi_yes}",
        enable_events=True,
        extra=[
            ElementConfig(
                sg_type="text",
                label="Brief Synopsis of \n QI Issue:",
                key="-QI_TEXT-",
                visible=False
            ),
            ElementConfig(
                sg_type="multiline",
                key=f"{KEY_DOSE_QI_INFO}",
                size=(comment_width_chars, 2),
                default_text='',
                visible=False
            )
        ]
    ),
    ElementConfig(
        sg_type="radio",
        label=label_revisions_no,
        group_id=f"{KEY_DOSE_REVISION}{KEY_RADIO}",
        key=f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_no}",
        enable_events=True,
    ),
    ElementConfig(
        sg_type="radio",
        label=label_revisions_yes,
        group_id=f"{KEY_DOSE_REVISION}{KEY_RADIO}",
        key=f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_yes}",
        enable_events=True,
        extra=[
            ElementConfig(
                sg_type="text",
                label="# of plan revisions:",
                key="-REVISION_#_TEXT-",
                visible=False
            ),
            ElementConfig(
                sg_type="combo",
                values=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                key=KEY_REVISION_NUMBER,
                visible=False
            ),
            ElementConfig(
                sg_type="text",
                label="Summary of Revision(s):",
                key="-REVISION_TEXT-",
                visible=False
            ),
            ElementConfig(
                sg_type="multiline",
                key=f"{KEY_DOSE_REVISION_INFO}",
                size=(comment_width_chars, 2),
                default_text='',
                visible=False
            )
        ]
    )
])


def create_side_panel(review_type: str = 'Physics') -> Tuple[List[List[Any]], List]:
    """
    Create a side panel with comment boxes and radio buttons for user interface.

    Args:
        review_type (Optional) (str): The type of review being performed ('Physics' or 'Dosimetry').


    Returns:
        tuple(List, List): side_panel (List[List[Any]]), events (List):
            A list of PySimpleGUI elements for the side panel, and a list of event keys.
    """
    # Select the appropriate configuration
    config = dosimetry_config if review_type.lower() == 'dosimetry' else physics_config

    # Initialize the side panel layout
    side_panel = []

    # Create a mapping of group_ids to radio elements
    radio_groups = {}

    # First pass: collect elements
    for sg_element in config.elements:
        if sg_element.sg_type == "radio":
            group_id = sg_element.group_id
            if group_id not in radio_groups:
                radio_groups[group_id] = []
            radio_groups[group_id].append(sg_element)
        else:
            # For other elements, just add them
            if sg_element.sg_type == "text":
                side_panel.append([Sg.Text(
                    sg_element.label,
                    text_color=sg_element.text_color or 'black',
                    font=sg_element.font or ('Helvetica', 12, 'bold'),
                    key=sg_element.key,
                    visible=sg_element.visible if sg_element.visible is not None else True
                )])

            elif sg_element.sg_type == "multiline":
                side_panel.append([Sg.Multiline(
                    default_text=sg_element.default_text,
                    size=sg_element.size,
                    autoscroll=True, auto_size_text=True,
                    key=sg_element.key,
                    visible=sg_element.visible if sg_element.visible is not None else True
                )])

    # Now, process radio groups
    for group_id, radio_elements in radio_groups.items():
        # Create a row with all radio buttons in this group
        radio_row = []
        for sg_element in radio_elements:
            radio_button = Sg.Radio(
                sg_element.label,
                group_id=sg_element.group_id,
                default=False, key=sg_element.key,
                enable_events=sg_element.enable_events
            )
            radio_row.append(radio_button)
        side_panel.append(radio_row)

        # Now handle 'extra' elements for each radio element
        for sg_element in radio_elements:
            for extra in sg_element.extra:
                if extra.sg_type == "text":
                    side_panel.append([Sg.Text(
                        extra.label,
                        key=extra.key,
                        visible=extra.visible if extra.visible is not None else True
                    )])
                elif extra.sg_type == "multiline":
                    side_panel.append([Sg.Multiline(
                        default_text=extra.default_text,
                        size=extra.size,
                        autoscroll=True,
                        auto_size_text=True,
                        key=extra.key,
                        visible=extra.visible if extra.visible is not None else True
                    )])
                elif extra.sg_type == "combo":
                    side_panel.append([Sg.Combo(
                        extra.values,
                        key=extra.key,
                        visible=extra.visible if extra.visible is not None else True
                    )])

    # Add the QA form components
    qa_form_components = get_qa_form_input_components(comment_width_chars)
    qa_frame = [
        Sg.Frame('QA Form (not yet forwarded to wiki-form)', qa_form_components, key='-QA-FRAME-', visible=False)]
    side_panel.append(qa_frame)

    # Append the final Image component
    side_panel.append([Sg.Image(filename=ICON_CHECKER, key='-CHECKER-IMAGE-', pad=((0, 0), (0, 0)),
                                size=(300, 300), enable_events=True, tooltip="Launch QA Form")])

    # Define side panel events
    side_panel_events = [element.key for element in config.elements]
    for sg_element in config.elements:
        for extra in sg_element.extra:
            side_panel_events.append(extra.key)

    return side_panel, side_panel_events


def load_side_panel(window: Sg.Window, values: Dict[str, Any], review_type) -> None:
    """
    Update the side panel in the main window with saved values.

    Args:
        window (Sg.Window): The PySimpleGUI window object to be updated.
        values (Dict[str, Any]): Dictionary containing saved side panel values.
        review_type: (str): The type of review being performed.

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
        # Check if the field_key is a prefix of any key in window.key_dict.keys()
        matching_keys = [key for key in window.key_dict if isinstance(key, str) and key.startswith(field_key)]
        if matching_keys:
            for _ in matching_keys:
                if field_key == KEY_PROCEED_REVISE:
                    # Use the radio key to trigger a click event
                    load_radio = f"{KEY_PROCEED_REVISE}{KEY_RADIO}{saved_value}"
                    on_side_panel_radio_button_click(window, load_radio, review_type)
                elif field_key == KEY_DOSE_REVISION:
                    # Use the radio key to trigger a click event
                    load_radio = f"{KEY_DOSE_REVISION}{KEY_RADIO}{saved_value}"
                    on_side_panel_radio_button_click(window, load_radio, review_type)
                elif field_key == KEY_DOSE_QI:
                    # Use the radio key to trigger a click event
                    load_radio = f"{KEY_DOSE_QI}{KEY_RADIO}{saved_value}"
                    on_side_panel_radio_button_click(window, load_radio, review_type)
                else:
                    window[field_key].update(saved_value)
        elif field_key == KEY_OUT_DOSE_COMMENT and KEY_USER_COMMENT in window.key_dict:
            # A special case for when a dosimetry review is loaded into a physics review window
            window[KEY_USER_COMMENT].update(saved_value)
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
    for element in config.elements:
        key = element.key
        element_type = element.sg_type

        if element_type in ["multiline", "checkbox", "combo"]:
            side_panel[key] = window[key].get() or element.default_text
            for extra in element.extra:
                extra_type = extra.sg_type
                if extra_type == "text":
                    continue
                extra_key = extra.key
                side_panel[extra_key] = window[extra_key].get() or extra.default_text

        elif element_type == "radio":
            group_id = element.group_id
            for radio_element in [e for e in config.elements if e.sg_type == "radio" and e.group_id == group_id]:
                radio_key = radio_element.key
                if window[radio_key].get():
                    side_panel_key = str(group_id).replace(KEY_RADIO, "")
                    # Now we have multiple possible radio buttons
                    side_panel[side_panel_key] = radio_element.label
                    for extra in radio_element.extra:
                        if extra.sg_type == "text":
                            continue
                        extra_key = extra.key
                        side_panel[extra_key] = window[extra_key].get() or ""
                    break
                else:
                    side_panel[KEY_PROCEED_REVISE] = "Undefined"

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

    # Build a mapping from group_id to radio buttons and their extras
    group_map = {}
    for element in config.elements:
        if element.sg_type == "radio":
            group_id = element.group_id
            if group_id not in group_map:
                group_map[group_id] = []
            group_map[group_id].append(element)

    # Find out which group the event belongs to
    clicked_group_id = None
    for group_id, radios in group_map.items():
        if any(radio.key == event for radio in radios):
            clicked_group_id = group_id
            break

    if clicked_group_id is not None:
        # Update radio buttons in the same group
        for radio in group_map[clicked_group_id]:
            is_selected = (radio.key == event)
            window[radio.key].update(value=is_selected)
            # Update visibility of extras
            for extra in radio.extra:
                window[extra.key].update(visible=is_selected)

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
    return any(values.get(k, False) for k in keys)


def side_panel_proceed_qi_true(values):
    """ Test to determine if the side panel has QI or Revise selected,
    check both physics and dosimetry configurations."""
    return any(values.get(key) for key in [
        f"{KEY_DOSE_QI_INFO}", f"{KEY_DOSE_REVISION_INFO}",
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)"])


def side_panel_revision_true(values):
    """ Test to determine if the side panel has Revise selected """
    return values.get(f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise", False)


def is_valid_side_panel(window: Sg.Window, values: Dict[str, Union[bool, str]],
                        review_type: str = 'physics_review') -> bool:
    """Validates the state of a side panel in a PySimpleGUI window.

    Args:
        window (Sg.Window): The PySimpleGUI window object containing the side panel.
        values (Dict[str, Union[bool, str]]): A dictionary of keys and their current values.
        review_type (str, optional): The type of review being performed. Defaults to 'physics_review'.

    Returns:
        bool: True if the side panel is valid, otherwise False.
    """
    is_valid = True
    if review_type.lower() == 'dosimetry':
        revision_radio_text = {
            f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_no}": (None, None),
            f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_yes}": ("-REVISION_TEXT-", KEY_REVISION_INFO),
            f"{KEY_DOSE_REVISION}{KEY_RADIO}Proceed (QI Issue)": ("-QI_TEXT-", KEY_QI_INFO),
        }
        validation_error_message = 'Please indicate if there are any long term issues for addressing,' \
                                   'and if there were revisions needed extending the planning time.'
    else:
        revision_radio_text = {
            f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed": (None, None),
            f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise": ("-REVISION_TEXT-", KEY_REVISION_INFO),
            f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)": ("-QI_TEXT-", KEY_QI_INFO),
        }
        validation_error_message = 'Proceed or Revise is required to proceed'

    if not check_radio_on(values, list(revision_radio_text.keys())):
        for r in revision_radio_text.keys():
            update_window_error(window, r)
        Sg.popup_error(validation_error_message)
        is_valid = False

    for radio_key, (text_key, input_key) in revision_radio_text.items():
        if text_key and input_key and values.get(radio_key) and not values.get(input_key):
            update_window_error(window, text_key)
            update_window_error(window, input_key)
            Sg.popup_error('Please provide details for revision or QI issue')
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
        is_physics_revision=is_physics_revision,
        is_dose_revision=is_dose_revision,
        is_dose_qi=is_dose_qi,
        is_physics_qi=is_physics_qi,
        revision_number=revision_number,
        user_comments=user_comments,
        dose_comments=dose_comments,
        qi_comments=qi_text,
        dose_qi_comments=dose_qi_text,
        revision_comments=revision_comments,
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


def is_valid_physics_panel(window: Sg.Window, values: Dict[str, Union[bool, str]]) -> bool:
    """Validates the physics review side panel."""
    is_valid = True

    revision_radio_text = {
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed": (None, None),
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Revise": ("-REVISION_TEXT-", KEY_REVISION_INFO),
        f"{KEY_PROCEED_REVISE}{KEY_RADIO}Proceed (QI Issue)": ("-QI_TEXT-", KEY_QI_INFO),
    }
    validation_error_message = 'Proceed or Revise is required to proceed'

    # Check if a radio button is selected
    if not check_radio_on(values, list(revision_radio_text.keys())):
        for r in revision_radio_text.keys():
            update_window_error(window, r)
        Sg.popup_error(validation_error_message)
        is_valid = False

    # Validate extra inputs
    for radio_key, (text_key, input_key) in revision_radio_text.items():
        if text_key and input_key and values.get(radio_key) and not values.get(input_key):
            update_window_error(window, text_key)
            update_window_error(window, input_key)
            Sg.popup_error('Please provide details for revision or QI issue.')
            is_valid = False

    return is_valid


def is_valid_dosimetry_panel(window: Sg.Window, values: Dict[str, Union[bool, str]]) -> bool:
    """Validates the dosimetry review side panel."""
    is_valid = True

    # Define labels and keys for dosimetry validation
    qi_radio_keys = {
        f"{KEY_DOSE_QI}{KEY_RADIO}{label_qi_no}": (None, None),
        f"{KEY_DOSE_QI}{KEY_RADIO}{label_qi_yes}": ("-QI_TEXT-", KEY_DOSE_QI_INFO)
    }

    revision_radio_keys = {
        f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_no}": (None, None),
        f"{KEY_DOSE_REVISION}{KEY_RADIO}{label_revisions_yes}": ("-REVISION_TEXT-", [KEY_REVISION_NUMBER, KEY_DOSE_REVISION_INFO])
    }

    # Validate QI group
    if not check_radio_on(values, list(qi_radio_keys.keys())):
        for r in qi_radio_keys.keys():
            update_window_error(window, r)
        Sg.popup_error('Please indicate if there is a QI issue.')
        is_valid = False

    # Validate extra inputs for QI group
    for radio_key, (text_key, input_key) in qi_radio_keys.items():
        if values.get(radio_key):
            if text_key and input_key and not values.get(input_key):
                update_window_error(window, text_key)
                update_window_error(window, input_key)
                Sg.popup_error('Please provide details for the QI issue.')
                is_valid = False

    # Validate Revisions group
    if not check_radio_on(values, list(revision_radio_keys.keys())):
        for r in revision_radio_keys.keys():
            update_window_error(window, r)
        Sg.popup_error('Please indicate if there are revisions.')
        is_valid = False

    # Validate extra inputs for Revisions group
    for radio_key, (text_key, input_keys) in revision_radio_keys.items():
        if values.get(radio_key):
            if text_key and input_keys:
                missing_inputs = False
                if isinstance(input_keys, list):
                    for input_key in input_keys:
                        if not values.get(input_key):
                            update_window_error(window, input_key)
                            missing_inputs = True
                else:
                    if not values.get(input_keys):
                        update_window_error(window, input_keys)
                        missing_inputs = True
                if missing_inputs:
                    update_window_error(window, text_key)
                    Sg.popup_error('Please provide details for the revisions.')
                    is_valid = False

    return is_valid
