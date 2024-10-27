import os
import json
import PySimpleGUI as Sg
from PlanReview.review_definitions import OUTPUT_DIR
from PlanReview.utils.io_file_utils import str_key_to_tuple
from PlanReview.utils.python_utilities import update_window_key_dict
from PlanReview.guis.create_preplan_tab import load_preplan
from PlanReview.guis.create_physics_manual_tab import load_manual
from PlanReview.guis.create_side_panel import load_side_panel
from PlanReview.guis.gui_qa_form import load_qa_form


def load_review(gui_state_manager):
    """Load review data into the GUI based on the current state of the GUI state manager.

    This function attempts to load the review data from a JSON file. It first tries to load the
    file with the review type suffix. If that file is not found, it attempts to load a file with
    the dosimetry review suffix. If neither file is found, a popup message is shown.

    Args:
        gui_state_manager (GuiState): The state manager object that holds the current state of the GUI.

    Returns:
        None
    """
    if not gui_state_manager.review_file_name:
        # Generate the review file name based on patient ID, beamset label, and suffix
        gui_state_manager.review_file_name = f"{gui_state_manager.rso.patient.PatientID}_" \
                    f"{gui_state_manager.rso.beamset.DicomPlanLabel}{gui_state_manager.suffix}"

    def try_load_file(file_path):
        """Attempt to load a JSON file from the given file path.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            dict or None: The loaded JSON data if successful, None if the file is not found.
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    # Try loading the primary review file
    review_file_path = os.path.join(OUTPUT_DIR, gui_state_manager.rso.patient.PatientID, gui_state_manager.review_file_name)
    values = try_load_file(review_file_path)

    # If primary review file is not found, try loading the dosimetry review file
    if values is None:

        dosimetry_review_file_name = f"{gui_state_manager.rso.patient.PatientID}_" \
                    f"{gui_state_manager.rso.beamset.DicomPlanLabel}_dosimetry_review.json"
        dosimetry_review_file_path = os.path.join(OUTPUT_DIR, gui_state_manager.rso.patient.PatientID, dosimetry_review_file_name)
        values = try_load_file(dosimetry_review_file_path)
        # If dosimetry review file is found, ask the user if they want to use the data
        if values is not None:
            response = Sg.popup_yes_no("Dosimetry Review data found. Do you want to populate the form with this data?")
            if response == 'No':
                values = None

    # If neither file is found, display a popup message and return
    if values is None:
        Sg.popup("No saved review found! If you saved one, try opening the corresponding beamset.")
        return

    # Convert string keys in the loaded JSON data to tuples
    values = str_key_to_tuple(values)
    # Add missing keys to the window's key dictionary
    update_window_key_dict(gui_state_manager.window, values.keys())
    # Load preplan frame contents
    load_preplan(gui_state_manager.window, values,
                 gui_state_manager.sites,
                 gui_state_manager.protocols,
                 gui_state_manager.instructions,
                 gui_state_manager.maximum_beamset_count,
                 gui_state_manager.maximum_target_number,
                 gui_state_manager.rso,
                 gui_state_manager.review_type)
    # Load the manual (check box) tab contents
    load_manual(gui_state_manager.window, values, gui_state_manager.check_box_copy)
    # Load the main window data
    load_side_panel(gui_state_manager.window, values, gui_state_manager.review_type)
    # Load the QA form if accessible
    if gui_state_manager.qa_form_accessible:
        load_qa_form(gui_state_manager.window, values)

