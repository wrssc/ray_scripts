try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
from typing import Any, Dict, NamedTuple
from PlanReview.review_definitions import ICON_CHECKER
from PlanReview.utils import (find_username_by_userid, get_user_name, find_groupname_by_userid,
                              is_valid_approver, get_approval_info)
from PlanReview.utils.constants import (KEY_QA, KEY_REVISION_INFO,
                                        QA_FORM_MANUAL, KEY_QI_INFO)

from typing import Dict
import datetime


def build_qa_form(rso: NamedTuple, window: Sg.Window) -> Dict[str, Any]:
    """
    Constructs a QA form dictionary from a given window and RSO object.

    Pseudocode:
    - Define a mapping for treatment techniques.
    - Extract initial values from the window.
    - Add date and patient information to the form.
    - Find usernames and physician approval details.
    - Parse occurrence dates and times.
    - Remove temporary keys and add additional details from the window.
    - Return the completed QA form dictionary.

    Args:
        rso: A named tuple containing information about the patient, plan, and beamset.
        window: The PySimpleGUI window object containing form elements.

    Returns:
        A dictionary with keys and values for the QA form.
    """

    # Define the technique mapping
    technique_mapping = {
        'SMLC': '3D', 'Conformal': '3D', 'DynamicArc': 'IMRT/VMAT',
        'DMLC': 'IMRT/VMAT', 'ConformalArc': '3D', 'TomoHelical': 'IMRT/VMAT',
        'TomoDirect': 'IMRT/VMAT'
    }

    # Extract QA form values and add the report date
    qa_form = extract_values_qa_form(window)[KEY_QA]
    qa_form['report_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Add patient information
    qa_form.update({
        'patient_name': rso.patient.Name,
        'mr_num': rso.patient.PatientID,
        'who_discovered': get_user_name_with_domain_prefix(),
        'attending_physician': get_attending_physician_name_if_approved(rso),
        'where_in_proc_discovered': 'Pre-Treatment QA Review (e.g. Physics Plan Check)',
        'anatomical_site': rso.case.BodySite,
        'pertinent_treatment_technique': get_pertinent_treatment_technique(rso, technique_mapping)
    })

    # Parse occurrence details
    parse_occurrence_details(qa_form, rso)

    # Add additional details from the window
    add_additional_window_details(qa_form, window)

    return qa_form


def parse_occurrence_details(qa_form: Dict[str, Any], rso: NamedTuple) -> None:
    """
    Parses and formats the occurrence dates and times for the QA form based on the RSO object.

    Args:
        qa_form: The QA form dictionary to which the occurrence details will be added.
        rso: The RSO object containing information required to parse the occurrence details.
    """
    # Conditional logic based on the 'occurrence_choice' field in the form
    if qa_form['occurrence_choice'] == 'Simulation Date':
        # Extract study date and acquisition time from the RSO object
        study_date = rso.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020)['Study Date']
        acquisition_time = rso.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0032)['Acquisition Time']

        # Parse and reformat the study date
        year, month, day = study_date.split('-')
        qa_form['occurrence_date'] = f"{month}/{day}/{year}"

        # Parse and reformat the acquisition time
        hour, minute, second = acquisition_time.split(':')
        hour = int(hour)
        am_pm = 'PM' if hour > 12 else 'AM'
        hour = hour - 12 if hour > 12 else hour
        qa_form['occurrence_time'] = f"{hour:02}:{minute}:{second}"
        qa_form['am_pm'] = am_pm

    elif qa_form['occurrence_choice'] == 'Plan Date':
        # Extract approval date and time from the RSO object
        approval_status = get_approval_info(rso.plan, rso.beamset)
        date_obj = approval_status.beamset_approval_time or approval_status.plan_approval_time
        parsed_date = _parse_date_object(date_obj)

        # Format date and time separately
        qa_form['occurrence_date'] = parsed_date.strftime("%m/%d/%Y")
        qa_form['occurrence_time'] = parsed_date.strftime("%I:%M:%S")
        qa_form['am_pm'] = parsed_date.strftime("%p")


def add_additional_window_details(qa_form: Dict[str, Any], window: Sg.Window) -> None:
    """
    Adds additional details to the QA form from the window fields.

    Args:
        qa_form: The QA form dictionary to which additional details will be added.
        window: The PySimpleGUI window object containing form elements.
    """
    # Remove temporary keys
    qa_form.pop('occurrence_choice', None)

    # Iterate over manual form items and update the form with values from the window
    for item in QA_FORM_MANUAL:
        if item['KEY'] in window.AllKeysDict:
            qa_form[item['KEY']] = window[item['KEY']].get()

    # Get the synopsis from the window if available
    qa_form['synopsis'] = window[KEY_QI_INFO].get() or window[KEY_REVISION_INFO].get()


# Helper function to parse date objects or strings
def _parse_date_object(date_obj: Any) -> datetime.datetime:
    """
    Parses a date object or string into a datetime object.

    Args:
        date_obj: The date object or string to parse.

    Returns:
        A datetime object.
    """
    if isinstance(date_obj, str):
        return datetime.datetime.strptime(date_obj, "%m/%d/%Y %I:%M:%S %p")
    elif isinstance(date_obj, datetime.datetime):
        return date_obj
    else:
        raise TypeError("date_obj is neither a datetime object nor a string.")


def extract_values_qa_form(window: Sg.Window) -> Dict[str, Any]:
    # Initialize qa form dictionary
    qa_form = {}

    # Add in default values for the manual QA form
    for field in QA_FORM_MANUAL:
        qa_form[field['KEY']] = ''

    # Extract current or default value for each key
    for key, default_value in qa_form.items():
        qa_form[key] = window[key].get() or default_value
    return {KEY_QA: qa_form}


def on_checker_image_click(window: Sg.Window, event: str) -> None:
    # Hide the checker image and display the QA form fields
    window['-CHECKER-IMAGE-'].update(visible=False)
    window['-QA-FRAME-'].update(visible=True)


def load_qa_form(window: Sg.Window, values: Dict[str, Any]) -> None:
    """ Update the QA form in the main window with saved values."""
    qa_form_values = values.get(KEY_QA, {})
    if qa_form_values:
        window['-QA-FRAME-'].update(visible=True)
        window['-CHECKER-IMAGE-'].update(visible=False)
    for field_key, saved_value in qa_form_values.items():
        window[field_key].update(saved_value)


def get_qa_form_input_components(width):
    """
    Create a list of input components for the QA form based on the QA_FORM_DICT.
    """
    qa_form_inputs = []

    for details in QA_FORM_MANUAL:
        if 'OPTIONS' in details:
            # It's a Combo input
            qa_form_inputs.append(
                [Sg.Text(details['TEXT'], enable_events=True,
                         key=f"'TEXT_{details['KEY']}")])
            qa_form_inputs.append(
                [Sg.Combo(details['OPTIONS'], size=(int(width * 0.6), 1), enable_events=True,
                          key=details['KEY'], tooltip=details['TEXT'])]
            )
        elif details['KEY'] == 'description':
            # It's a Multiline input
            qa_form_inputs.append(
                [Sg.Text(details['TEXT'], enable_events=True,
                         key=f"'TEXT_{details['KEY']}")])
            qa_form_inputs.append(
                [Sg.Multiline(size=(width, 10), enable_events=True,
                              key=details['KEY'], tooltip=details['TEXT'])]
            )
        else:
            # It's a standard InputText
            qa_form_inputs.append(
                [Sg.Text(details['TEXT'], enable_events=True,
                         key=f"'TEXT_{details['KEY']}")])
            qa_form_inputs.append(
                [Sg.InputText(size=(width, 1), enable_events=True,
                              key=details['KEY'], tooltip=details['TEXT'])]
            )

    return qa_form_inputs


def get_user_name_with_domain_prefix() -> str:
    """
    Retrieves the current user's name with a domain prefix.

    Returns:
        A string representing the user's name with a domain prefix.
    """
    user_id = get_user_name()
    domain_prefix = "uwhis\\"  # Assuming 'uwhis' is the domain prefix used in your organization.
    user_name = find_username_by_userid(f"{domain_prefix}{user_id}")
    return user_name


def get_attending_physician_name_if_approved(rso: NamedTuple) -> str:
    """
    Retrieves the attending physician's name if the plan is approved.

    Args:
        rso: The RSO object containing approval status information.

    Returns:
        The attending physician's name if available, otherwise an empty string.
    """
    approval_status = get_approval_info(rso.plan, rso.beamset)
    if approval_status.beamset_approved:
        group_name = find_groupname_by_userid(approval_status.beamset_reviewer)
        if is_valid_approver(group_name, ['Oncologist']):
            md_name = find_username_by_userid(approval_status.beamset_reviewer)
            return md_name
    return ''


def get_pertinent_treatment_technique(rso: NamedTuple, technique_mapping: dict) -> str:
    """
    Determines the pertinent treatment technique based on the RSO object and a given mapping.

    Args:
        rso: The RSO object containing the beamset delivery technique.
        technique_mapping: A dictionary mapping delivery techniques to treatment techniques.

    Returns:
        A string representing the pertinent treatment technique.
    """
    treatment_technique = technique_mapping.get(rso.beamset.DeliveryTechnique, 'Unknown')
    if treatment_technique == '3D' and rso.beamset.Modality == 'Electrons':
        return 'Electrons'
    return treatment_technique




