import PySimpleGUI as Sg
from PlanReview.review_definitions import (
    ICON_SAVE, ICON_LOAD, ICON_START, ICON_PRINT, ICON_PAUSE, ICON_CANCEL, ICON_ERROR,
    ICON_SMALL_SAVE, ICON_SMALL_LOAD, ICON_SMALL_START, ICON_SMALL_PRINT,
    ICON_SMALL_PAUSE, ICON_SMALL_CANCEL, ICON_SMALL_ERROR
)


def build_top_buttons(top_width, top_height, save_space):
    # Top dimensions
    top_image_size = (90, 25) if save_space else (110, 30)
    top_subsample = 1 if save_space else 1
    top_border = 0 if save_space else 0  # 2
    top_pad = ((6, 6), (3, 0)) if save_space else ((12, 12), (3, 0))
    #
    small_icons = {
        "-SAVE-": (ICON_SMALL_SAVE, "Save the current view"),
        "-LOAD-": (ICON_SMALL_LOAD, "Load a previously saved view"),
        "-START-": (ICON_SMALL_START, "Start the automated tests"),
        "-REPORT-": (ICON_SMALL_PRINT, "Save the current view and create a report"),
        "-PAUSE-": (ICON_SMALL_PAUSE, "Pause the script to interact in RayStation"),
        "-CANCEL-": (ICON_SMALL_CANCEL, "Cancel the script execution"),
        "-ERROR-": (ICON_SMALL_ERROR, "Generate an error report"),
    }

    large_icons = {
        "-SAVE-": (ICON_SAVE, "Save the current view"),
        "-LOAD-": (ICON_LOAD, "Load a previously saved view"),
        "-START-": (ICON_START, "Start the automated tests"),
        "-REPORT-": (ICON_PRINT, "Save the current view and create a report"),
        "-PAUSE-": (ICON_PAUSE, "Pause the script to interact in RayStation"),
        "-CANCEL-": (ICON_CANCEL, "Cancel the script execution"),
        "-ERROR-": (ICON_ERROR, "Generate an error report"),
    }

    icons = small_icons if save_space else large_icons

    top_buttons = [Sg.Button('', image_filename=icons[key][0],
                             image_size=top_image_size,
                             image_subsample=top_subsample,
                             pad=top_pad,
                             border_width=top_border,
                             tooltip=icons[key][1],
                             key=key)
                   for key in icons.keys()]
    top = Sg.Frame('',
                   [top_buttons],
                   vertical_alignment='center',
                   size=(top_width, top_height),
                   )

    return top
