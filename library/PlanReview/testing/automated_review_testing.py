"""
Create a function that will loop over a list of test patient and preplan data and run the review_test_patient function
"""
def review_test_patient(rso, preplan_data, review_type='Physics'):
    """
    Function to review a test patient by setting the plan and beamset, launching the review GUI,
    filling in preplan data, and interacting with available buttons.

    Parameters:
    - rso: NamedTuple of ScriptObjects in RayStation [case, exam, plan, beamset, db]
    - preplan_data: Dictionary containing preplan data to fill in the GUI
    - review_type: String indicating the type of review, either 'Physics' or 'Dosimetry'

    Returns: None
    """
    import connect
    import logging
    import PySimpleGUI as Sg

    try:
        # Step 1: Open test patient and set current plan and beamset
        case = rso.case
        plan = rso.plan
        beamset = rso.beamset

        # Set the current case, plan, and beamset
        case.SetCurrent()
        plan.SetCurrent()
        beamset.SetCurrent()

        # Step 2: Launch the review GUI
        gui_state_manager = launch_physics_review_gui(rso, review_type=review_type)

        # Step 3: Fill in preplan data
        for key, value in preplan_data.items():
            element = gui_state_manager.window[key]
            if element.Type == Sg.ELEM_TYPE_INPUT or element.Type == Sg.ELEM_TYPE_COMBO:
                element.Update(value)
            elif element.Type == Sg.ELEM_TYPE_RADIO:
                element.Update(value)

        # Step 4: Hit all buttons available to a user
        for button in gui_state_manager.window.AllKeysDict:
            element = gui_state_manager.window[button]
            if element.Type == Sg.ELEM_TYPE_BUTTON:
                element.Click()

        # Step 5: Check for errors and alert if any are found
        if gui_state_manager.window.FindElementWithFocus():
            error_message = gui_state_manager.window.FindElementWithFocus().Get()
            if 'Error' in error_message:
                raise Exception(error_message)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        Sg.Popup(f"An error occurred during the review: {e}")

# Example usage
from collections import namedtuple

# Assuming rso is already defined with the required NamedTuple
rso = namedtuple('RSO', ['case', 'exam', 'plan', 'beamset', 'db'])

# Example preplan data
preplan_data = {
    'KEY_SIM_DATE': '2024-06-01',
    'KEY_SLICES': '100',
    'KEY_PATIENT_ORIENTATION': 'HFS',
    'KEY_IMD+KEY_RADIO-YES': True,
    'KEY_PRIOR_RT+KEY_RADIO-NO': True,
    'KEY_SITE_SELECT': 'Head and Neck',
    'KEY_PROTOCOL_SELECT': 'Protocol A',
    'KEY_ORDER_SELECT': 'Order 1',
    'KEY_IMAGING_FREQ': 'Weekly',
    'KEY_TREAT_FREQ': 'Daily',
    # Beamset and target fields
    'KEY_BEAMSET_COUNT': 2,
    ('KEY_BEAMSET_SELECT', 0): 'Beamset 1',
    ('KEY_BEAMSET_SELECT', 1): 'Beamset 2',
    ('KEY_BEAMSET_TARGET_COUNT', 0): 1,
    ('KEY_BEAMSET_TARGET_COUNT', 1): 2,
    ('KEY_BEAMSET_DOSE', 0, 0): '50',
    ('KEY_BEAMSET_DOSE', 1, 0): '60',
    ('KEY_BEAMSET_DOSE', 1, 1): '30',
    ('KEY_BEAMSET_FRACTION_DOSE', 0, 0): '2.5',
    ('KEY_BEAMSET_FRACTION_DOSE', 1, 0): '2.0',
    ('KEY_BEAMSET_FRACTION_DOSE', 1, 1): '1.5',
    ('KEY_BEAMSET+KEY_FRACTIONS', 0): 20,
    ('KEY_BEAMSET+KEY_FRACTIONS', 1): 30,
    # Add more preplan data as needed
}

review_test_patient(rso, preplan_data)
