import PySimpleGUI as Sg
from typing import Tuple


def get_text_element_size(text: str) -> Tuple[int, int]:
    """
    Given a text, this function creates an invisible window with the text, and
    then it calculates and returns the width and height of the text in pixels.

    Args:
        text (str): The input text to calculate size for.

    Returns:
        size_text (Tuple[int, int]): The width and height of the text in pixels.
    """
    window = Sg.Window('Invisible Window', [[Sg.Text(text, key='text')]],
                       alpha_channel=0, finalize=True)
    window.read(timeout=0)
    size_text = window['text'].get_size()
    window.close()
    return size_text


def get_user_display_parameters() -> Tuple[int, int, bool, int, int]:
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
    sample_sentence = "A quick brown fox jumps over a lazy dog."
    width_pixels, height_pixels = get_text_element_size(sample_sentence)

    # calculating the number of pixels per character
    pixels_per_char = width_pixels // len(sample_sentence)
    screen_width, screen_height = Sg.Window.get_screen_size()

    # deciding the fraction of screen to be used for window
    height_fraction = 0.80 if screen_height <= 1080 else 0.75
    width_fraction = 0.82 if screen_height <= 1080 else 0.7

    # calculating window dimensions
    window_width = int(width_fraction * screen_width)
    window_height = int(height_fraction * screen_height)

    # check if we need to save space
    save_space = screen_height <= 1080
    pixels_per_char_width = pixels_per_char
    pixels_per_char_height = height_pixels

    return (window_width, window_height, save_space,
            pixels_per_char_width, pixels_per_char_height)
