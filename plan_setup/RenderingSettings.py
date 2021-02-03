""" Render electron 3D View

    Script executes the following steps
    -Make a rendering contour
    -Change its properties
    -Prompt user to hit the set clinic defaults visualization for stable params in the UI
    -Makes changes to the UI settings
    -Prompts user to change light field orientation

    This program is free software: you can redistribute it and/or modify it under the
    terms of the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
    PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this
    program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '0.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Rendering_Settings'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'

import sys
import os
import connect
import UserInterface
import logging
import GeneralOperations
import StructureOperations
from tkinter import *
from tkinter import messagebox
from PIL import ImageTk
#from PIL import Image

def open_toolpanel_dose(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Dose'].Click()
        except:
            pass

        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
            ui.ToolPanel.DoseOptions.CheckBox
            button_open = True
        except:
            pass

def close_toolpanel_dose(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
            ui.ToolPanel.DoseOptions.CheckBox
            button_open = True
        except:
            button_open = False

def open_toolpanel_patient(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Patient'].Click()
        except:
            pass
        try:
            ui.ToolPanel.PatientOptions.ToggleButton.Click()
            ui.ToolPanel.PatientOptions.CheckBox
            button_open = True
        except:
            pass

def close_toolpanel_patient(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.PatientOptions.ToggleButton.Click()
            ui.ToolPanel.PatientOptions.CheckBox
            button_open = True
        except:
            button_open = False

def open_toolpanel_defaults(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Defaults'].Click()
        except:
            pass
        try:
            ui.ToolPanel.SaveOptions.ToggleButton.Click()
            ui.ToolPanel.SaveOptions.Button_Next
            button_open = True
        except:
            pass

def close_toolpanel_defaults(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.SaveOptions.ToggleButton.Click()
            ui.ToolPanel.SaveOptions.Button_Next
            button_open = True
        except:
            button_open = False

def open_toolpanel_beam(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Beam'].Click()
        except:
            pass
        try:
            ui.ToolPanel.BeamOptions.ToggleButton.Click()
            ui.ToolPanel.BeamOptions.CheckBox
            button_open = True
        except:
            pass

def close_toolpanel_beam(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.BeamOptions.ToggleButton.Click()
            ui.ToolPanel.BeamOptions.CheckBox
            button_open = True
        except:
            button_open = False

def open_toolpanel_beam_animation(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Beam animation'].Click()
        except:
            pass
        try:
            ui.ToolPanel.AnimationOptions.ToggleButton['Beam animation'].Click()
            ui.ToolPanel.AnimationOptions.ComboBox
            button_open = True
        except:
            pass

def close_toolpanel_beam_animation(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.AnimationOptions.ToggleButton['Beam animation'].Click()
            ui.ToolPanel.AnimationOptions.ComboBox
            button_open = True
        except:
            button_open = False

def open_toolpanel_pet(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['PET'].Click()
        except:
            pass
        try:
            ui.ToolPanel.PETOptions.ToggleButton.Click()
            ui.ToolPanel.PETOptions.CheckBox
            button_open = True
        except:
            pass

def close_toolpanel_pet(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.PETOptions.ToggleButton.Click()
            ui.ToolPanel.PETOptions.CheckBox
            button_open = True
        except:
            button_open = False

def activate_toolpanel_buttons(ui):
    # Activate all buttons
    open_toolpanel_dose(ui)
    open_toolpanel_patient(ui)
    open_toolpanel_defaults(ui)
    open_toolpanel_beam(ui)
    open_toolpanel_beam_animation(ui)
    open_toolpanel_pet(ui)

def close_toolpanel_buttons(ui):
    # Close the buttons
    close_toolpanel_dose(ui)
    close_toolpanel_patient(ui)
    close_toolpanel_defaults(ui)
    close_toolpanel_beam(ui)
    close_toolpanel_beam_animation(ui)
    close_toolpanel_pet(ui)

def helper_image():
    # Display a helpful image for the next step
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    help_screenshot = r'Electron_Rendering.jpg'
    f=os.path.join(os.path.dirname(__file__),
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
    valid_rs_version = '10.0.1.52'
    # rendering structure name
    render_name = 'z_rendering'
    # Low threshold
    low_threshold = -600
    # Max on CT: TODO find this in CT info
    high_threshold = 3071
    # Get current patient, case, and exam
    ui = GeneralOperations.find_scope(level='ui')
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    beamset = GeneralOperations.find_scope(level='BeamSet')

    # Version check
    raystation_version = ui.GetApplicationVersion()
    if raystation_version not in valid_rs_version:
        sys.exit('Script has not been validated in version {}, only in {}'.format(raystation_version, valid_rs_version))
    # Go to the Plan design window
    ui.TitleBar.MenuItem['Plan design'].Button_Plan_design.Click()
    # Check if this an electron plan
    if 'Electrons' not in beamset.Modality:
        connect.await_user_input('This script requires an electron beamset to be selected')
        beamset = GeneralOperations.find_scope(level='BeamSet')
        if 'Electrons' not in beamset.Modality:
            sys.exit('No electron plan selected')

    # Turn off all contours
    StructureOperations.visualize_none(patient=patient, case=case)
    # Create the rendering ROI
    render_roi_geom = StructureOperations.create_roi(
        case=case,
        examination = exam,
        roi_name = render_name,
        delete_existing = True,
    )
    # Turn its visualization on
    patient.SetRoiVisibility(RoiName=render_name,IsVisible=True)
    # Change its color to  #FFFFFF
    error_color = StructureOperations.change_roi_color(
        case=case,
        roi_name = render_name,
        rgb = [255, 255, 255]
    )
    # Change type to something innocuous
    error_type = StructureOperations.change_roi_type(
        case=case,
        roi_name = render_name,
        roi_type = 'Undefined'
    )
    # Exclude it from export
    error_exclude = StructureOperations.exclude_from_export(
        case=case,
        rois=render_name
    )
    # Retrieve structure
    render_roi = case.PatientModel.RegionsOfInterest[render_name]
    # Get the external for the plan
    external = StructureOperations.find_types(case=case, roi_type="External")
    if external:
        current_external_name = external[0]
        logging.info('Declaring rendering limits within structure {}'
                    .format(current_external_name))
        # Get the exam name
        external_geom = case.PatientModel.StructureSets[exam.Name]\
                        .RoiGeometries[current_external_name]
        b = external_geom.GetBoundingBox()
        external_bb = {
            "MinCorner": {"x": b[0].x, "y": b[0].y, "z": b[0].z},
            "MaxCorner": {"x": b[1].x, "y": b[1].y, "z": b[1].z},
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

    activate_toolpanel_buttons(ui=ui)
    # Patient Options
    # apply clinical defaults
    open_toolpanel_defaults(ui)
    ui.ToolPanel.SaveOptions.Button_Next['Apply clinic defaults'].Click()

    # Turn off POI Names
    open_toolpanel_patient(ui)
    ui.ToolPanel.PatientOptions.CheckBox['POI names'].Click()
    # Dose Options
    open_toolpanel_dose(ui)
    ui.ToolPanel.DoseOptions.CheckBox['Show dose max'].Click()
    ui.ToolPanel.DoseOptions.CheckBox['DSP names'].Click()
    #
    # Beam Options
    open_toolpanel_beam(ui)
    ui.ToolPanel.BeamOptions.CheckBox['Show leaves'].Click()
    #
    # Prompt user to move the view
    ui.ToolPanel.TabItem['Scripting'].Select()
    helper_image()
    connect.await_user_input('Align the view')
    #
    # Tool Panel: Beam Options
    # Turn off Beam Contour
    open_toolpanel_beam(ui)
    ui.ToolPanel.BeamOptions.CheckBox['Contour'].Click()
    ui.ToolPanel.BeamOptions.CheckBox['Center line'].Click()
    ui.ToolPanel.BeamOptions.CheckBox['Show jaws'].Click()
    ui.ToolPanel.BeamOptions.CheckBox['Block'].Click()
    # Turn off Transparent external, just in case a user ignores all guidance
    ui.ToolPanel.BeamOptions.CheckBox['Transparent external ROI'].Click()


    ui.ToolPanel.TabItem['Scripting'].Select()
    connect.await_user_input('Right-Click 3D> Show Beam Parts> Applicator/Isocenter: OFF')
    close_toolpanel_buttons(ui)
    open_toolpanel_patient(ui)
    connect.await_user_input('Adjust the 3D light position to maximize surface features')
    root = Tk()
    root.withdraw()
    messagebox.showinfo(title='Rendering Script Complete',
        message='Right click in the image and Capture a screenshot \n'+
    	        'Select Max size and print the image as: Q:\RadOnc\RayStation\Reports\<Filename>.pdf')
    root.destroy()




if __name__ == '__main__':
    main()
