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
    if not gui_state_manager.review_file_name:
        gui_state_manager.review_file_name = f"{gui_state_manager.rso.patient.PatientID}_" \
                    f"{gui_state_manager.rso.beamset.DicomPlanLabel}{gui_state_manager.suffix}"
    try:
        with open(os.path.join(OUTPUT_DIR, gui_state_manager.rso.patient.PatientID,
                               gui_state_manager.review_file_name), "r") as f:
            values = json.load(f)
    except FileNotFoundError:
        Sg.popup("No saved review found!")
        return

    values = str_key_to_tuple(values)
    # Add missing keys to the window.key_dict
    update_window_key_dict(gui_state_manager.window, values.keys())
    # Load preplan frame contents
    load_preplan(gui_state_manager.window, values,
                 gui_state_manager.sites,
                 gui_state_manager.protocols,
                 gui_state_manager.instructions,
                 gui_state_manager.maximum_beamset_count,
                 gui_state_manager.maximum_target_number)
    # Load the manual (check box) tab contents
    load_manual(gui_state_manager.window, values, gui_state_manager.check_box_copy)
    # Load the main window data.
    load_side_panel(gui_state_manager.window, values, gui_state_manager.review_type)
    # Load the QA form
    if gui_state_manager.qa_form_accessible:
        load_qa_form(gui_state_manager.window, values)

