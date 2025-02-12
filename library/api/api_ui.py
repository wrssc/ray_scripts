import logging
from library.api.dispatcher import APIDispatcher

dispatcher = APIDispatcher()  # Create an instance of the dispatcher


def ui_click_plan_optimization_v12(ui):
    # Version 12 specific code
    try:
        ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()
    except Exception as e:
        logging.debug(f'Unable to change viewing windows: {e}')


def ui_click_plan_optimization_v15(ui):
    # Version 15 specific code
    try:
        ui.TitleBar.MenuItem['Plan optimization'].Button_Plan_Optimization.Click()
    except Exception as e:
        logging.debug(f'Unable to change viewing windows: {e}')


def ui_click_plan_design_v12(ui):
    # Version 12 specific code
    try:
        ui.TitleBar.Navigation.MenuItem['Plan design'].Button_Plan_Design.Click()
    except Exception as e:
        logging.debug(f'Unable to change TitleBar-Navigation-MenuItem-Plan design: {e}')


def ui_click_plan_design_v15(ui):
    # Version 15 specific code
    try:
        ui.TitleBar.Navigation.MenuItem['Plan design'].Button.Click()
    except Exception as e:
        logging.debug(f'Unable to change TitleBar-Navigation-MenuItem-Plan design: {e}')


def open_toolpanel_dose_v12(ui):
    # Version 12 specific code
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Dose'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Dose: {e}')
            pass

        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
            ui.ToolPanel.DoseOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Dose Options: {e}')
            pass


def open_toolpanel_dose_v15(ui):
    # Version 15 specific code
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Dose: {e}')
            pass

        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
            ui.ToolPanel.DoseOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Dose Options: {e}')
            pass



#  V 12
def close_toolpanel_dose_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.DoseOptions.ToggleButton.Click()
            ui.ToolPanel.DoseOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - Dose Options: {e}')
            button_open = False



def open_toolpanel_patient_v12(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Patient'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Patient: {e}')
            pass
        try:
            ui.ToolPanel.PatientOptions.ToggleButton.Click()
            ui.ToolPanel.PatientOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Patient Options: {e}')
            pass


def open_toolpanel_patient_v15(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.PatientOptions.ToggleButton.Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Patient: {e}')
            pass
        try:
            ui.ToolPanel.PatientOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Patient Options: {e}')
            pass



def close_toolpanel_patient_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.PatientOptions.ToggleButton.Click()
            ui.ToolPanel.PatientOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - Patient Options: {e}')
            button_open = False



def open_toolpanel_defaults_v12(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Defaults'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Defaults: {e}')
            pass
        try:
            ui.ToolPanel.SaveOptions.ToggleButton.Click()
            ui.ToolPanel.SaveOptions.Button_Next
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Save Options: {e}')
            pass


def open_toolpanel_defaults_v15(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.Defaults.ToggleButton.Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Defaults: {e}')
            pass
        try:
            ui.ToolPanel.SaveOptions.ToggleButton.Click()
            ui.ToolPanel.SaveOptions.Button_Next
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Save Options: {e}')
            pass


def close_toolpanel_defaults_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.SaveOptions.ToggleButton.Click()
            ui.ToolPanel.SaveOptions.Button_Next
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - Save Options: {e}')
            button_open = False


def open_toolpanel_beam_v12(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Beam'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Beam: {e}')
            pass
        try:
            ui.ToolPanel.BeamOptions.ToggleButton.Click()
            ui.ToolPanel.BeamOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Beam Options: {e}')
            pass


def close_toolpanel_beam_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.BeamOptions.ToggleButton.Click()
            ui.ToolPanel.BeamOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - Beam Options: {e}')
            button_open = False


def open_toolpanel_beam_animation_v12(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['Beam animation'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-Beam Animation: {e}')
            pass
        try:
            ui.ToolPanel.AnimationOptions.ToggleButton['Beam animation'].Click()
            ui.ToolPanel.AnimationOptions.ComboBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - Animation Options: {e}')
            pass


def close_toolpanel_beam_animation_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.AnimationOptions.ToggleButton['Beam animation'].Click()
            ui.ToolPanel.AnimationOptions.ComboBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - Animation Options: {e}')
            button_open = False


def open_toolpanel_pet_v12(ui):
    button_open = False
    while not button_open:
        ui.ToolPanel.TabItem['Visualization'].Select()
        try:
            ui.ToolPanel.ToggleButton['PET'].Click()
        except Exception as e:
            logging.debug(f'Unable to select Visualization-PET: {e}')
            pass
        try:
            ui.ToolPanel.PETOptions.ToggleButton.Click()
            ui.ToolPanel.PETOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to select Tool Panel - PET Options: {e}')
            pass


def close_toolpanel_pet_v12(ui):
    button_open = True
    ui.ToolPanel.TabItem['Visualization'].Select()
    while button_open:
        try:
            ui.ToolPanel.PETOptions.ToggleButton.Click()
            ui.ToolPanel.PETOptions.CheckBox
            button_open = True
        except Exception as e:
            logging.debug(f'Unable to Close Tool Panel - PET Options: {e}')
            button_open = False


# End


# REGISTER THESE FUNCTIONS WITH THE DISPATCHER
dispatcher.register('ui_click_plan_optimization', 12, ui_click_plan_optimization_v12)
dispatcher.register('ui_click_plan_optimization', 15, ui_click_plan_optimization_v15)
dispatcher.register('ui_click_plan_design', 12, ui_click_plan_design_v12)
dispatcher.register('ui_click_plan_design', 15, ui_click_plan_design_v15)
dispatcher.register('open_toolpanel_dose', 12, open_toolpanel_dose_v12)
dispatcher.register('open_toolpanel_dose', 15, open_toolpanel_dose_v15)
dispatcher.register('close_toolpanel_dose', 12, close_toolpanel_dose_v12)
dispatcher.register('open_toolpanel_patient', 12, open_toolpanel_patient_v12)
dispatcher.register('close_toolpanel_patient', 12, close_toolpanel_patient_v12)
dispatcher.register('open_toolpanel_defaults', 12, open_toolpanel_defaults_v12)
dispatcher.register('close_toolpanel_defaults', 12, close_toolpanel_defaults_v12)
dispatcher.register('open_toolpanel_beam', 12, open_toolpanel_beam_v12)
dispatcher.register('close_toolpanel_beam', 12, close_toolpanel_beam_v12)
dispatcher.register('open_toolpanel_beam_animation', 12, open_toolpanel_beam_animation_v12)
dispatcher.register('close_toolpanel_beam_animation', 12, close_toolpanel_beam_animation_v12)
dispatcher.register('open_toolpanel_pet', 12, open_toolpanel_pet_v12)
dispatcher.register('close_toolpanel_pet', 12, close_toolpanel_pet_v12)

# Temporarily map V12 to V15 until the V15 functions are determined necessary
dispatcher.register('close_toolpanel_dose', 15, close_toolpanel_dose_v12)
dispatcher.register('open_toolpanel_patient', 15, open_toolpanel_patient_v15)
dispatcher.register('close_toolpanel_patient', 15, close_toolpanel_patient_v12)
dispatcher.register('open_toolpanel_defaults', 15, open_toolpanel_defaults_v12)
dispatcher.register('close_toolpanel_defaults', 15, close_toolpanel_defaults_v12)
dispatcher.register('open_toolpanel_beam', 15, open_toolpanel_beam_v12)
dispatcher.register('close_toolpanel_beam', 15, close_toolpanel_beam_v12)
dispatcher.register('open_toolpanel_beam_animation', 15, open_toolpanel_beam_animation_v12)
dispatcher.register('close_toolpanel_beam_animation', 15, close_toolpanel_beam_animation_v12)
dispatcher.register('open_toolpanel_pet', 15, open_toolpanel_pet_v12)
dispatcher.register('close_toolpanel_pet', 15, close_toolpanel_pet_v12)


@dispatcher.dispatch('ui_click_plan_optimization')
def ui_click_plan_optimization(ui):
    pass


@dispatcher.dispatch('ui_click_plan_design')
def ui_click_plan_design(ui):
    pass


@dispatcher.dispatch('open_toolpanel_dose')
def open_toolpanel_dose(ui):
    pass


@dispatcher.dispatch('close_toolpanel_dose')
def close_toolpanel_dose(ui):
    pass

@dispatcher.dispatch('open_toolpanel_patient')
def open_toolpanel_patient(ui):
    pass

@dispatcher.dispatch('close_toolpanel_patient')
def close_toolpanel_patient(ui):
    pass


@dispatcher.dispatch('open_toolpanel_defaults')
def open_toolpanel_defaults(ui):
    pass


@dispatcher.dispatch('close_toolpanel_defaults')
def close_toolpanel_defaults(ui):
    pass


@dispatcher.dispatch('open_toolpanel_beam')
def open_toolpanel_beam(ui):
    pass


@dispatcher.dispatch('close_toolpanel_beam')
def close_toolpanel_beam(ui):
    pass


@dispatcher.dispatch('open_toolpanel_beam_animation')
def open_toolpanel_beam_animation(ui):
    pass


@dispatcher.dispatch('close_toolpanel_beam_animation')
def close_toolpanel_beam_animation(ui):
    pass


@dispatcher.dispatch('open_toolpanel_pet')
def open_toolpanel_pet(ui):
    pass


@dispatcher.dispatch('close_toolpanel_pet')
def close_toolpanel_pet(ui):
    pass
