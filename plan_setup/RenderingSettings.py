"""Rendering Electron 3D View

This script automates the creation and configuration of a 3D rendering view for electron beam
treatment plans within RayStation. It performs a series of operations to streamline the visualization
process, ensuring that the view is optimized for clinical review and documentation.

Key Operations:
    1. Rendering Contour Creation:
       - Creates a rendering Region of Interest (ROI) with a preset name ('z_rendering').
       - Sets grayscale thresholds based on CT values (low: -600, high: 3071).
       - Adjusts ROI properties: sets visibility, changes color to white (#FFFFFF), updates ROI type,
         and excludes the ROI from export.
       - If an external structure is present, uses its bounding box to define rendering limits.

    2. User Interface Adjustments:
       - Activates and toggles necessary tool panels (Visualization, Beam, Patient, Dose) within the UI.
       - Prompts the user to apply clinical defaults and perform manual adjustments (e.g., light field
         orientation, view alignment).
       - Displays a helper image (located at '../protocols/UW/Electron_Rendering.jpg') to guide the user.

    3. Plan Validation:
       - Checks that the RayStation version is one of the validated versions (12.0.0.932, 15.1.0.852).
       - Ensures the active plan is an electron beam plan, prompting the user if a non-electron plan is selected.

Usage:
    Run this script from within RayStation when an electron plan is active. Follow the on-screen
    instructions to apply clinical defaults, adjust visualization settings, and capture a final screenshot.

Dependencies:
    - Standard Python modules: sys, os, logging, tkinter.
    - External libraries: PIL (Pillow) for image handling.
    - Custom modules: connect, library.GeneralOperations, library.StructureOperations, and library.api.api_ui.
    - A helper image located at: '../protocols/UW/Electron_Rendering.jpg'.

RayStation Compatibility:
    This script has been validated for RayStation versions: 12.0.0.932 and 15.1.0.852.
    It will exit if run on an unsupported version.

License:
    This program is free software: you can redistribute it and/or modify it under the terms of the GNU
    General Public License as published by the Free Software Foundation, either version 3 of the License,
    or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
    even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
    Public License for more details.

    You should have received a copy of the GNU General Public License along with this program.
    If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Rendering_Settings'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'

import sys
import os
import connect
import logging
from library.GeneralOperations import find_scope
from library.StructureOperations import (visualize_none, create_roi, change_roi_color, change_roi_type,
                                         exclude_from_export, find_types)
from tkinter import *
from tkinter import messagebox
from PIL import ImageTk
from library.api.api_ui import (
    ui_click_plan_design,
    click_apply_clinic_defaults,
    get_toolpanel_options_map
)


# In most cases in the tool panel ui, the object, say ui.ToolPanel.BeamOptions, won't
# be available for clicking unless the ToolPanel is open and the Toggle Button for
# BeamOptions is clicked first.
# For example:
# ui.ToolPanel.ToggleButton['Beam'].Click() must
# be executed for ui.ToolPanel.BeamOptions to be available for clicking.


import logging

class RayStationUIManager:
    """Manages RayStation UI interactions for rendering operations.

    This class encapsulates methods to open and close various panels and options,
    using an options mapping to determine which UI elements to target.
    """

    def __init__(self, ui):
        """
        Args:
            ui: The RayStation UI object.
        """
        self.ui = ui

    def is_toolpanel_open(self):
        """Check if the tool panel is open."""
        parent = self.ui.ToolPanel
        toggle_button = parent.ToggleButton
        # If the panel only contains the default minimal attributes, consider it closed.
        return not (len(dir(parent)) == 2 and ['_0'] == dir(toggle_button))

    def select_tabitem(self, tab_name):
        """Select a specific tab item in the tool panel.

        Args:
            tab_name (str): The name of the tab to select (e.g., 'Visualization').
        """
        if f"_{tab_name}" in dir(self.ui.ToolPanel.TabItem):
            self.ui.ToolPanel.TabItem[tab_name].Select()
        else:
            logging.error(f"Tab '{tab_name}' not found in ToolPanel.")

    def open_toolpanel_and_select_visualization(self, max_attempts=10):
        """Open the tool panel and select the Visualization tab.

        Uses a loop with a maximum number of attempts to prevent infinite loops.
        """
        attempts = 0
        while not self.is_toolpanel_open() and attempts < max_attempts:
            # Try clicking the default toggle button
            if '_0' in dir(self.ui.ToolPanel.ToggleButton):
                self.ui.ToolPanel.ToggleButton[0].Click()
            attempts += 1
        self.select_tabitem('Visualization')
        if attempts >= max_attempts:
            logging.warning("ToolPanel did not open after maximum attempts.")

    def ui_element_present(self, parent, child_name):
        """Check if a given child element is present in the parent's attributes.

        Args:
            parent: The parent UI object.
            child_name: The name of the child element to check.

        Returns:
            bool: True if present, False otherwise.
        """
        return child_name in dir(parent)

    def ensure_toggle_button_exists(self, panel_object_name, panel_key):
        """Ensure the toggle button for a specific panel exists by clicking if needed.

        Args:
            panel_object_name (str): The name of the panel object.
            panel_key (str): The key used to identify the toggle button.
        """
        if not self.ui_element_present(self.ui.ToolPanel, panel_object_name):
            try:
                self.ui.ToolPanel.ToggleButton[panel_key].Click()
            except Exception as e:
                logging.error(f"Error ensuring toggle button exists for {panel_object_name}: {e}")
                raise

    def open_panel_option(self, panel_object_name, check_attr, max_attempts=10):
        """Open a specific panel option until the UI element is available.

        Args:
            panel_object_name (str): The attribute name of the panel option (e.g., 'PatientOptions').
            check_attr (str): The attribute that must appear once the panel is open.
            max_attempts (int): Maximum number of attempts to click the toggle.
        """
        panel_object = getattr(self.ui.ToolPanel, panel_object_name, None)
        if panel_object is None:
            logging.error(f"Panel {panel_object_name} not found.")
            return

        attempts = 0
        while not self.ui_element_present(panel_object, check_attr) and attempts < max_attempts:
            panel_object.ToggleButton.Click()
            attempts += 1
        if attempts >= max_attempts:
            logging.warning(f"Panel option '{panel_object_name}' did not open after {max_attempts} attempts.")

    def close_panel_option(self, panel_object_name, check_attr, max_attempts=10):
        """Close a specific panel option until the UI element is no longer present.

        Args:
            panel_object_name (str): The attribute name of the panel option (e.g., 'BeamOptions').
            check_attr (str): The attribute that indicates the panel is open.
            max_attempts (int): Maximum number of attempts to click the toggle.
        """
        panel_object = getattr(self.ui.ToolPanel, panel_object_name, None)
        if panel_object is None:
            logging.error(f"Panel {panel_object_name} not found.")
            return

        attempts = 0
        while self.ui_element_present(panel_object, check_attr) and attempts < max_attempts:
            if hasattr(panel_object, 'ToggleButton') and self.ui_element_present(panel_object.ToggleButton, 'Click'):
                panel_object.ToggleButton.Click()
            attempts += 1
        if attempts >= max_attempts:
            logging.warning(f"Panel option '{panel_object_name}' did not close after {max_attempts} attempts.")

    def open_panels(self, options_map, panel_key=None):
        """Open one or more panels based on the options map.

        Args:
            options_map (dict): Mapping of panel keys to tuples of (panel_object_name, check_attr).
            panel_key (str, optional): If provided, only process the given panel.
        """
        self.open_toolpanel_and_select_visualization()
        panels = options_map if panel_key is None else {panel_key: options_map[panel_key]}
        for key, (panel_object_name, check_attr) in panels.items():
            # Ensure the panel is present; if not, create it by clicking its toggle button.
            if not self.ui_element_present(self.ui.ToolPanel, panel_object_name):
                self.ensure_toggle_button_exists(panel_object_name, key)
            self.open_panel_option(panel_object_name, check_attr)

    def close_panels(self, options_map, panel_key=None):
        """Close one or more panels based on the options map.

        Args:
            options_map (dict): Mapping of panel keys to tuples of (panel_object_name, check_attr).
            panel_key (str, optional): If provided, only process the given panel.
        """
        # Ensure the Visualization tab is active so the panels are in the current UI context.
        self.open_toolpanel_and_select_visualization()
        panels = options_map if panel_key is None else {panel_key: options_map[panel_key]}
        for key, (panel_object_name, check_attr) in panels.items():
            self.close_panel_option(panel_object_name, check_attr)

    def click_ui_element(self, element_accessor):
        """Click on a specific UI element.

        Args:
            element_accessor (Callable): A function (or lambda) that returns the UI element to click.
                Example: lambda: self.ui.ToolPanel.PatientOptions.CheckBox['POI names']
        """
        try:
            element = element_accessor()
            element.Click()
        except Exception as e:
            logging.error("Error clicking UI element: " + str(e))
            raise

# Example usage:

# Assume 'ui' is obtained via find_scope(level='ui')
# Also assume that get_toolpanel_options_map(ui) returns a dictionary like:
# {
#     'Patient': ('PatientOptions', 'CheckBox'),
#     'Dose': ('DoseOptions', 'CheckBox'),
#     'Beam': ('BeamOptions', 'CheckBox'),
#     'Defaults': ('DefaultsOptions', 'Button'),
# }

def ensure_toggle_button_exists(ui, panel_object_name, panel_key):
    open_toolpanel_and_select_visualization(ui)
    ui.ToolPanel.TabItem['Visualization'].Select()
    try:
        if not has_ui_element(ui.ToolPanel, panel_object_name):
            ui.ToolPanel.ToggleButton[panel_key].Click()
    except Exception as e:
        print(f"Error creating toggle button for {panel_object_name}: {e}")
        pass


def is_toolpanel_open(ui):
    parent = ui.ToolPanel
    toggle_button = parent.ToggleButton
    parent_dir = dir(parent)
    toggle_dir = dir(toggle_button)
    if len(parent_dir) == 2 and ['_0'] == toggle_dir:
        return False
    return True


def open_toolpanel_and_select_visualization(ui):
    while not is_toolpanel_open(ui):
        if '_0' in dir(ui.ToolPanel.ToggleButton):
            ui.ToolPanel.ToggleButton[0].Click()
    ui.ToolPanel.TabItem['Visualization'].Select()


def open_panel_option(ui, parent, panel_object_name, check_attr):
    open_toolpanel_and_select_visualization(ui)
    panel_object = getattr(parent, panel_object_name, None)
    button_open = False
    while not button_open:
        if not has_ui_element(panel_object, check_attr):
            panel_object.ToggleButton.Click()
        if has_ui_element(panel_object, check_attr):
            button_open = True


def close_panel_option(ui, parent, panel_object_name, check_attr):
    parent.TabItem['Visualization'].Select()
    panel_object = getattr(parent, panel_object_name, None)
    if panel_object is None:
        # Option panel is not active
        return
    if not has_ui_element(panel_object, check_attr):
        # CheckBox or Button is missing, panel is not active
        return
    button_open = True
    while button_open:
        if has_ui_element(panel_object.ToggleButton, 'Click'):
            panel_object.ToggleButton.Click()
        if not has_ui_element(panel_object, check_attr):
            button_open = False


def has_ui_element(parent, child):
    return child in dir(parent)


def open_panels(ui, options_map, panel=None):
    if panel:
        mapping = {panel: options_map[panel]}
    else:
        mapping = options_map
    parent = ui.ToolPanel
    for panel_key, (panel_object_name, check_attr) in mapping.items():
        if not has_ui_element(parent, panel_object_name):
            # Initialize the panel if it is not present
            ensure_toggle_button_exists(ui, panel_object_name=panel_object_name,
                                        panel_key=panel_key)
        open_panel_option(ui, parent, panel_object_name, check_attr)


def close_panels(ui, options_map, panel=None):
    # Close the buttons
    if panel:
        mapping = {panel: options_map[panel]}
    else:
        mapping = options_map
    parent = ui.ToolPanel
    for panel, (panel_object_name, check_attr) in mapping.items():
        close_panel_option(ui, parent, panel_object_name, check_attr)


def helper_image():
    # Display a helpful image for the next step
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    help_screenshot = r'Electron_Rendering.jpg'
    f = os.path.join(os.path.dirname(__file__),
                     protocol_folder,
                     institution_folder,
                     help_screenshot)

    canvas = Canvas(width=1300, height=734, bg='black')
    canvas.pack(expand='yes', fill='both')

    image = ImageTk.PhotoImage(file=f)
    canvas.create_image(1, 1, image=image, anchor='nw')

    mainloop()


def main():
    # Specify valid version of raystation
    valid_rs_version = ['12.0.0.932', '15.1.0.852', '15.1.3.15']

    # rendering structure name
    render_name = 'z_rendering'
    # Low threshold
    low_threshold = -600
    # Max on CT: TODO find this in CT info
    high_threshold = 3071
    # Get current patient, case, and exam
    ui = find_scope(level='ui')
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    beamset = find_scope(level='BeamSet')
    ui_manager = RayStationUIManager(ui)

    # Version check
    raystation_version = ui.GetApplicationVersion()
    if raystation_version not in valid_rs_version:
        sys.exit('Script has not been validated in version {}, only in {}'.format(raystation_version, valid_rs_version))
    # Go to the Plan design window
    ui_click_plan_design(ui)
    # Check if this an electron plan
    if 'Electrons' not in beamset.Modality:
        connect.await_user_input('This script requires an electron beamset to be selected')
        beamset = find_scope(level='BeamSet')
        if 'Electrons' not in beamset.Modality:
            sys.exit('No electron plan selected')

    # Turn off all contours
    visualize_none(patient=patient, case=case)
    # Create the rendering ROI
    render_roi_geom = create_roi(
        case=case,
        examination=exam,
        roi_name=render_name,
        delete_existing=True,
    )
    # Turn its visualization on
    patient.SetRoiVisibility(RoiName=render_name, IsVisible=True)
    # Change its color to  #FFFFFF
    error_color = change_roi_color(
        case=case,
        roi_name=render_name,
        rgb=[255, 255, 255]
    )
    # Change type to something innocuous
    error_type = change_roi_type(
        case=case,
        roi_name=render_name,
        roi_type='Undefined'
    )
    # Exclude it from export
    error_exclude = exclude_from_export(
        case=case,
        rois=render_name
    )
    # Retrieve structure
    render_roi = case.PatientModel.RegionsOfInterest[render_name]
    # Get the external for the plan
    external = find_types(case=case, roi_type="External")
    if external:
        current_external_name = external[0]
        logging.info('Declaring rendering limits within structure {}'
                     .format(current_external_name))
        # Get the exam name
        external_geom = case.PatientModel.StructureSets[exam.Name] \
            .RoiGeometries[current_external_name]
        bounding_box = external_geom.GetBoundingBox()
        external_bb = {
            "MinCorner": {"x": bounding_box[0].x, "y": bounding_box[0].y, "z": bounding_box[0].z},
            "MaxCorner": {"x": bounding_box[1].x, "y": bounding_box[1].y, "z": bounding_box[1].z},
        }
        # Make it now
        render_roi.GrayLevelThreshold(
            Examination=exam,
            LowThreshold=low_threshold,
            HighThreshold=high_threshold,
            PetUnit="",
            CbctUnit=None,
            BoundingBox=external_bb
        )
    else:
        # Make it now without a bounding box
        render_roi.GrayLevelThreshold(
            Examination=exam,
            LowThreshold=low_threshold,
            HighThreshold=high_threshold,
            PetUnit="",
            CbctUnit=None,
            BoundingBox=None
        )
    # Fill holes
    case.PatientModel.StructureSets[exam.Name].SimplifyContours(
        RoiNames=[render_name],
        RemoveHoles3D=True,
        RemoveSmallContours=False,
        AreaThreshold=None,
        ReduceMaxNumberOfPointsInContours=False,
        MaxNumberOfPoints=None,
        CreateCopyOfRoi=False,
        ResolveOverlappingContours=False
    )


    # Get RS-version specific options map
    options_map = get_toolpanel_options_map(ui)
    # apply clinical defaults
    ui_manager.open_toolpanel_and_select_visualization()
    ui_manager.open_panels(options_map, panel_key='Defaults')
    # Patient Options
    # Open the Patient panel
    ui_manager.open_panels(options_map, panel_key='Patient')
    click_apply_clinic_defaults(ui)

    # Click the "POI names" checkbox within the Patient Options panel.
    ui_manager.click_ui_element(lambda: ui.ToolPanel.PatientOptions.CheckBox['POI names'])
    # Dose Options
    ui_manager.open_panels(options_map, panel_key='Dose')
    ui_manager.click_ui_element(lambda: ui.ToolPanel.DoseOptions.CheckBox['Show max value'])
    ui_manager.click_ui_element(lambda: ui.ToolPanel.DoseOptions.CheckBox['DSP names'])
    #
    # Beam Options
    ui_manager.open_panels(options_map, panel_key='Beam')
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Show leaves'])
    #
    # Prompt user to move the view
    ui_manager.select_tabitem('Scripting')
    helper_image()
    connect.await_user_input('Align the view')
    #
    # Tool Panel: Beam Options
    ui_manager.open_panels(options_map, panel_key='Beam')
    # Turn off Beam Contour
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Contour'])
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Center line'])
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Show jaws'])
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Block'])
    ui_manager.click_ui_element(lambda: ui.ToolPanel.BeamOptions.CheckBox['Transparent external ROI'])

    ui_manager.select_tabitem('Scripting')
    connect.await_user_input('Right-Click 3D> Show Beam Parts> Applicator/Isocenter: OFF')
    ui_manager.close_panels(options_map)
    ui_manager.open_panels(options_map, panel_key='Patient')
    connect.await_user_input('Adjust the 3D light position to maximize surface features')
    root = Tk()
    root.withdraw()
    messagebox.showinfo(title='Rendering Script Complete',
                        message='Right click in the image and Capture a screenshot \n' +
                                'Select Max size and print the image as: Q:\RadOnc\RayStation\Reports\<Filename>.pdf')
    root.destroy()


if __name__ == '__main__':
    main()
