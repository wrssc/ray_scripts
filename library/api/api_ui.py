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


def ui_click_qa_preparation_v12(ui):
    # Version 12 specific code
    try:
        ui.TitleBar.Navigation.MenuItem['QA preparation'].Button_QA_preparation.Click()
    except Exception as e:
        logging.debug(f'Unable to change TitleBar-Navigation-MenuItem-QA preparation: {e}')


def ui_click_qa_preparation_v15(ui):
    # Version 15 specific code
    try:
        ui.TitleBar.Navigation.MenuItem['QA preparation'].Button.Click()
    except Exception as e:
        logging.debug(f'Unable to change TitleBar-Navigation-MenuItem-QA preparation: {e}')


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


def click_apply_clinic_defaults_v12(ui):
    try:
        ui.ToolPanel.SaveOptions.Button_Next['Apply clinic defaults'].Click()
    except Exception as e:
        logging.debug(f'Unable to click Apply clinic defaults: {e}')
        pass


def click_apply_clinic_defaults_v15(ui):
    try:
        ui.ToolPanel.SaveOptions.Button_Apply_clinic_defaults.Click()
    except Exception as e:
        logging.debug(f'Unable to click Apply clinic defaults: {e}')
        pass


def get_toolpanel_options_map_v12(ui):
    # Version 12 specific code
    return {
        'Beam': ("BeamOptions", 'CheckBox'),
        'Dose': ("DoseOptions", 'CheckBox'),
        'Patient': ("PatientOptions", 'CheckBox'),
        'Defaults': ("SaveOptions", 'Button_Next'),
        # 'PET': ("PETOptions", 'CheckBox')
    }

def get_toolpanel_options_map_v15(ui):
    # Version 15 specific code
    return {
        'Beam': ("BeamOptions", 'CheckBox'),
        'Dose': ("DoseOptions", 'CheckBox'),
        'Patient': ("PatientOptions", 'CheckBox'),
        'Defaults': ("SaveOptions", 'Button_Apply_clinic_defaults'),
        # 'PET': ("PETOptions", 'CheckBox')
    }


# REGISTER THESE FUNCTIONS WITH THE DISPATCHER
dispatcher.register('ui_click_plan_optimization', 12, ui_click_plan_optimization_v12)
dispatcher.register('ui_click_plan_design', 12, ui_click_plan_design_v12)
dispatcher.register('ui_click_qa_preparation', 12, ui_click_qa_preparation_v12)
dispatcher.register('get_toolpanel_options_map', 12, get_toolpanel_options_map_v12)
dispatcher.register('click_apply_clinic_defaults', 12, click_apply_clinic_defaults_v12)

# Temporarily map V12 to V15 until the V15 functions are determined necessary
dispatcher.register('ui_click_plan_optimization', 15, ui_click_plan_optimization_v15)
dispatcher.register('ui_click_plan_design', 15, ui_click_plan_design_v15)
dispatcher.register('ui_click_qa_preparation', 15, ui_click_qa_preparation_v15)
dispatcher.register('get_toolpanel_options_map', 15, get_toolpanel_options_map_v15)
dispatcher.register('click_apply_clinic_defaults', 15, click_apply_clinic_defaults_v15)


@dispatcher.dispatch('ui_click_plan_optimization')
def ui_click_plan_optimization(ui):
    pass


@dispatcher.dispatch('ui_click_plan_design')
def ui_click_plan_design(ui):
    pass


@dispatcher.dispatch('ui_click_qa_preparation')
def ui_click_qa_preparation(ui):
    pass


@dispatcher.dispatch('get_toolpanel_options_map')
def get_toolpanel_options_map(ui):
    pass


@dispatcher.dispatch('click_apply_clinic_defaults')
def click_apply_clinic_defaults(ui):
    pass
