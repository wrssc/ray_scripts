try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
from typing import Tuple
from PIL import ImageFont


def pil_get_element_size(text, font_size, font_name):
    font = ImageFont.truetype(font_name, font_size)
    size = font.getsize(text)
    return size


def get_text_element_size(text: str) -> Tuple[int, int]:
    """
    Given a text, this function creates an invisible window with the text, and
    then it calculates and returns the width and height of the text in pixels.

    Args:
        text (str): The input text to calculate size for.

    Returns:
        size_text (Tuple[int, int]): The width and height of the text in pixels.
    """
    layout = [[Sg.Text(text, key='text')]]
    window = Sg.Window('Invisible Window',
                       layout,
                       alpha_channel=0, finalize=True)
    window.read(timeout=0)
    size_text = window['text'].get_size()
    window.close()
    return size_text


def get_user_display_parameters(review_type) -> Tuple[int, int, bool, int, int]:
    """
    This function determines some parameters related to the user's display.
    It calculates the dimensions of the window and the number of pixels per character.
    It also checks if the screen height is less than or equal to 1080 to save space.

    Returns:
        window_width (int): The width of the window in pixels.
        window_height (int): The height of the window in pixels.
        save_space (bool): If True, we will save space because the screen height is
                           less than or equal to 1080.
        pixels_per_char_width (int): The width of a character in pixels.
        pixels_per_char_height (int): The height of a character in pixels.
    """
    minimum_vertical_resolution = 1300
    sample_sentence = "A quick brown fox jumps over a lazy dog."
    # width_pixels, height_pixels = pil_get_element_size(sample_sentence, 11, 'times.ttf')
    width_pixels, height_pixels = get_text_element_size(sample_sentence)

    # calculating the number of pixels per character
    pixels_per_char = width_pixels // len(sample_sentence)
    screen_width, screen_height = Sg.Window.get_screen_size()
    ## # Create a QPoint object with (0, 0) coordinates
    ## point = Sg.QtCore.QPoint()
    ## screen_width = Sg.QtWidgets.QDesktopWidget().screenGeometry(point).width()
    ## screen_height = Sg.QtWidgets.QDesktopWidget().screenGeometry(point).height()
    window_height = 800 if screen_height<minimum_vertical_resolution else 1000
    window_width = 1100 if screen_height<minimum_vertical_resolution else 1310
    # check if we need to save space
    save_space = screen_height <= minimum_vertical_resolution
    pixels_per_char_width = pixels_per_char
    pixels_per_char_height = height_pixels

    return (window_width, window_height, save_space,
            pixels_per_char_width, pixels_per_char_height)
