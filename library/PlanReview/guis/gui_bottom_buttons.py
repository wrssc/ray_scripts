try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
from PlanReview.review_definitions import (
    ICON_SCALE_ISODOSE, ICON_SMALL_SCALE_ISODOSE, ICON_SMALL_MATERIAL, ICON_MATERIAL,
    ICON_SMALL_WINDOW_LEVEL, ICON_WINDOW_LEVEL, ICON_PAUSE, ICON_SMALL_PAUSE)
from .isodose_visualization import change_visualization_isodose
import connect

window_level_dict = {
    'Bone': (450, 1600),
    'Brain': (35, 100),
    'Dental': (400, 2000),
    'Inner Ear': (700, 4000),
    'Larnyx': (40, 250),
    'Lung': (-600, 1600),
    'Mediastinum': (40, 400),
    'Pelvis': (250, 1000),
    'Soft Tissue': (40, 350),
    'Spine': (35, 300),
    'Vertebrae': (350, 2000),
    'Xtra-Z': (1150, 2700),
}


def build_bottom_buttons(save_space):
    # Top dimensions
    bottom_image_size = (90, 25) if save_space else (110, 30)
    bottom_subsample = 1 if save_space else 1
    bottom_border = 0 if save_space else 0  # 2
    bottom_pad = ((32, 28), (0, 0)) if save_space else ((48, 48), (0, 0))
    #
    small_icons = {
        "-PAUSE-": (ICON_SMALL_PAUSE, "Pause the script to interact in RayStation"),
        "-SCALE-": (ICON_SMALL_SCALE_ISODOSE, "Scale isodose levels and fill targets"),
        "-MATERIAL-": (ICON_SMALL_MATERIAL, "Toggle between image set and material view"),
        "-WL-": (ICON_SMALL_WINDOW_LEVEL, "Window level images"),
    }

    large_icons = {
        "-PAUSE-": (ICON_PAUSE, "Pause the script to interact with RayStation"),
        "-SCALE-": (ICON_SCALE_ISODOSE, "Scale isodose levels and fill targets"),
        "-MATERIAL-": (ICON_MATERIAL, "Toggle between image set and material view"),
        "-WL-": (ICON_WINDOW_LEVEL, "Window level images"),
    }

    icons = small_icons if save_space else large_icons

    bottom_buttons = [Sg.Button('', image_filename=icons[key][0],
                                image_size=bottom_image_size,
                                image_subsample=bottom_subsample,
                                pad=bottom_pad,
                                border_width=bottom_border,
                                tooltip=icons[key][1],
                                visible=True,
                                enable_events=True,
                                key=key)
                      for key in icons.keys()]
    wl_combo, wl_combo_key = build_window_level_combo()
    bottom_buttons.append(wl_combo)
    bottom = Sg.Frame('', [bottom_buttons],)
    bottom_events = [key for key in icons.keys()]
    bottom_events.append(wl_combo_key)

    return bottom, bottom_events


def build_window_level_combo():
    """
    Build the window level combo box
    Returns:
        combo: PySimpleGUI Combo object
        combo_key: str
    """
    combo_key = '-COMBO_WL-'
    combo = Sg.Combo([w for w in window_level_dict.keys()],
                     key=combo_key, visible=False, enable_events=True,
                     size=(16, 1))
    return combo, combo_key


def on_window_level_combo(rso, selection):
    if selection in window_level_dict.keys():
        level, window = window_level_dict[selection]
        rso.exam.Series[0].LevelWindow = {'x': level, 'y': window}
    else:
        print(f'Error: {selection} not in window_level_dict')


def bottom_event(gui_state_manager, event, values):
    if event == '-SCALE-':
        on_isodose_scale_click(gui_state_manager.rso)
    elif event == '-MATERIAL-':
        on_toggle_material_click()
    elif event == '-WL-':
        on_window_level_click(gui_state_manager.window)
    elif event == '-COMBO_WL-':
        on_window_level_combo(gui_state_manager.rso, values['-COMBO_WL-'])
    elif event == '-PAUSE-':
        connect.await_user_input('Review Paused. Resume Script Execution to Continue')


def on_isodose_scale_click(rso):
    change_visualization_isodose(rso)


def search_tab_items(ui):
    tab_item_combinations = [
        ('2D | Image_0', '2D | Image', 'Image set'),
        ('2D | Material_0', '2D | Material', 'Material'),
        ('2D | Material', '2D | Material', 'Material'),
        ('2D | Image', '2D | Image', 'Image set'),
        ('2D | Image_1', '2D | Image', 'Image set'),
        ('2D | Material_1', '2D | Material', 'Material')]
    material_choice = None
    selected_tab_item = None
    for tab_control_name, tab_item_name, material_or_image in tab_item_combinations:
        try:
            selected_tab_item = ui.Workspace.TabControl[tab_control_name].TabItem[tab_item_name]
            material_choice = material_or_image
            return selected_tab_item, material_choice
        except Exception as e:
            print(f'Error selecting tab control {tab_control_name}')
            print(e)
            if 'not present in the collection' in str(e):
                continue
    return selected_tab_item, material_choice


def find_tab_item_and_material_dropdown(ui):
    """
    Find the tab item and material choice
    """
    selected_tab_item, material_choice = search_tab_items(ui)
    if selected_tab_item is None:
        click_patient_modeling(ui)
        selected_tab_item, material_choice = search_tab_items(ui)
    return selected_tab_item, material_choice


def click_patient_modeling(ui):
    try:
        ui.TitleBar.Navigation.MenuItem['Patient modeling'].Button.Click()
    except Exception as e:
        print(f'Error clicking Patient modeling {e}')
        pass


def on_toggle_material_click():
    ui = connect.get_current('ui')
    # Determine if we have one 2d view or more
    tab_item, current_view = find_tab_item_and_material_dropdown(ui)
    if current_view is None:
        return None
    try:
        # Activate drop down
        tab_item.ShowImageSetOrMaterialVM.DropDownButton.Click()
        ui_busy = True
        while ui_busy:
            if not ui.IsUpdating():
                ui_busy = False
        # Select the opposite view of current
        if current_view == 'Image set':
            tab_item.ShowImageSetOrMaterialVM.DropDownButton.Popup.MenuItem['Material'].Click()
        else:
            tab_item.ShowImageSetOrMaterialVM.DropDownButton.Popup.MenuItem['Image set'].Click()
    except Exception as e:
        print(f'Error toggling material view {current_view}: {e}')
        pass


def on_window_level_click(window):
    window['-WL-'].update(visible=False)
    window['-COMBO_WL-'].update(visible=True)
