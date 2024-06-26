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


# REGISTER THESE FUNCTIONS WITH THE DISPATCHER
dispatcher.register('ui_click_plan_optimization', 12, ui_click_plan_optimization_v12)
dispatcher.register('ui_click_plan_optimization', 15, ui_click_plan_optimization_v15)


@dispatcher.dispatch('ui_click_plan_optimization')
def ui_click_plan_optimization(ui):
    pass
