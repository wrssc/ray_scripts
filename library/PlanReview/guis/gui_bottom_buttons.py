import PySimpleGUI as Sg
from PlanReview.review_definitions import (
    ICON_SCALE_ISODOSE, ICON_SMALL_SCALE_ISODOSE)


def build_bottom_buttons(save_space):
    # Top dimensions
    bottom_image_size = (90, 25) if save_space else (110, 30)
    bottom_subsample = 1 if save_space else 1
    bottom_border = 0 if save_space else 0  # 2
    bottom_pad = ((8, 7), (0, 0)) if save_space else ((12, 12), (0, 0))
    #
    small_icons = {
        "-SCALE-": (ICON_SMALL_SCALE_ISODOSE, "Scale isodose levels and fill targets"),
    }

    large_icons = {
        "-SCALE-": (ICON_SCALE_ISODOSE, "Scale isodose levels and fill targets"),
    }

    icons = small_icons if save_space else large_icons

    bottom_buttons = [Sg.Button('', image_filename=icons[key][0],
                             image_size=bottom_image_size,
                             image_subsample=bottom_subsample,
                             pad=bottom_pad,
                             border_width=bottom_border,
                             tooltip=icons[key][1],
                             key=key)
                   for key in icons.keys()]
    bottom = Sg.Frame('',
                   [bottom_buttons],
                   ## QT vertical_alignment='center',
                   ## size=(top_width, top_height),
                   )

    return bottom
