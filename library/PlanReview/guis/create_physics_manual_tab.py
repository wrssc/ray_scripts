import PySimpleGUI as Sg
import sys
import logging
from math import ceil
from typing import NamedTuple
from collections import defaultdict
import textwrap
from PlanReview.review_definitions import (
    PASS, FAIL, ALERT, NA, REVIEW_LEVELS, DOMAIN_TYPE,
    RED_CIRCLE, GREEN_CIRCLE, YELLOW_CIRCLE, BLUE_CIRCLE,
    CHECK_BOXES_PHYSICS_REVIEW, REVIEW_TYPES, TECHNIQUE_MAP,
    CHECK_BOXES_DOSIMETRY_SAFETY, )
from PlanReview.utils.constants import *


def create_key(element_type, beamset_index=None, target_index=None):
    """
    Creates a unique key for a GUI element.

    This function constructs a tuple to uniquely identify GUI elements
    especially useful in the context of events in PySimpleGUI. The tuple is
    constructed from the type of the GUI element and optional indices
    for beamsets and targets.

    Args:
        element_type (str): The type of the GUI element. This could be any string
            that describes the element (e.g., 'beamset_num_text', 'target_name', etc.)
        beamset_index (int, optional): The index of the beamset. This is used
            when the GUI element is associated with a specific beamset. Defaults to None.
        target_index (int, optional): The index of the target. This is used
            when the GUI element is associated with a specific target. Defaults to None.


    Returns:
        tuple: A tuple that uniquely identifies a GUI element. It includes the element type
            and, if provided, the beamset and target indices.
    """
    # Start with a tuple containing the element_type
    unique_key = (element_type,)

    # If a beamset index is provided, append it to the tuple
    if beamset_index is not None:
        unique_key += (beamset_index,)

    # If a target index is provided, append it to the tuple
    if target_index is not None:
        unique_key += (target_index,)

    # Return the unique key tuple
    return unique_key


def generate_event_key(*args):
    """
    Generates a unique event key for a GUI element.

    This function constructs a string by joining the string representation of
    each argument with underscores. This can be useful for creating unique event keys
    for PySimpleGUI elements.

    Args:
        *args: A variable number of argument that uniquely identify a GUI element.

    Returns:
        str: A unique event key for a GUI element.
    """
    return "_".join(str(arg) for arg in args)


def create_manual_check_row(item, word_wrap_limit, user_text_length=80, ):
    phrases = item[KEY_OUT_OPTIONS].split(',')
    test_name = item[KEY_OUT_DESC]
    # Count characters till a new line:
    row_key = item[KEY_OUT_TEST]
    # Count the nuber of lines in test_name
    line_count = test_name.count('\n') + 1
    input_text_function = Sg.Multiline if line_count > 1 else Sg.InputText
    radios = [Sg.Column(
        [[Sg.Radio(phrase,
                   group_id=create_key(row_key),
                   default=False,
                   key=create_key(f'{row_key}{KEY_CHECK}{KEY_RADIO}{phrase}'),
                   enable_events=True)]],
        justification='right', expand_x=False,
        pad=(0, 0))
        for phrase in phrases
    ]
    row = [Sg.Column(
        [[Sg.Text(test_name, )]],
        justification='left',
        expand_x=True
    ),
        *radios,
        Sg.Column(
            [[input_text_function(
                size=(user_text_length, line_count),
                key=create_key(f'{row_key}{KEY_CHECK}{KEY_INPUT_TEXT}'),
                enable_events=True,
                background_color='#E5DECE', pad=(0, 0))]],
            justification='right', expand_x=False
        ),
    ]

    return row, line_count


def excluded_check_boxes(key, values):
    # Check if conditions are met to include the key in the extracted values
    exclude_check = False
    # Check if prior rt was selected
    prior_rt = values.get(create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES'), False)
    imd = values.get(create_key(KEY_IMD+KEY_RADIO+'-YES'), False)
    if key == REVIEW_LEVELS['PRIOR_RT'] and not prior_rt:
        exclude_check = True
    if key == REVIEW_LEVELS['IMPLANTED_DEVICE'] and not imd:
        exclude_check = True
    return exclude_check


def extract_values_manual_tab(values, passing, failed, check_boxes):
    sorted_values = {}
    for key in check_boxes:
        sorted_values[key] = {}
        for item in check_boxes[key]:
            if excluded_check_boxes(key, values):
                continue
            phrases = item[KEY_OUT_OPTIONS].split(',')
            for p in phrases:
                radio_key = create_key(
                    f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}{p}")
                sorted_values[key][radio_key] = values.get(radio_key, None)
            input_key = create_key(f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}")
            sorted_values[key][input_key] = values.get(input_key, None)
    # Parse the automated tests after user input
    key = 'Failed Tests'
    sorted_values[key] = {}
    for test in failed:
        input_key = create_key(
            test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC], KEY_INPUT_TEXT)
        sorted_values[key][input_key] = values.get(input_key, None)
    key = 'Passing Tests'
    sorted_values[key] = {}
    for test in passing:
        input_key = create_key(
            test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC], KEY_INPUT_TEXT)
        sorted_values[key][input_key] = values.get(input_key, None)
    return sorted_values


def load_manual(window, values, check_boxes):
    for check_level, value_dict in values.items():
        if any((check_level in check_boxes,
                check_level == 'Failed Tests',
                check_level == 'Passing Tests')):

            for key, value in value_dict.items():
                if check_level in check_boxes:
                    saved_key = create_key(key)
                else:
                    saved_key = key
                if saved_key in window.key_dict:
                    window[saved_key].update(value=value)


def search_string(input_string):
    input_string = str(input_string)
    split_str = input_string.split("::", 1)
    if len(split_str) == 2:
        return split_str[0], split_str[1]
    else:
        return None, input_string


def insert_line_breaks(text, max_line_length):
    words = text.split()
    lines = []
    current_line = ""
    line_count = 0

    i = 0
    while i < len(words):
        word = words[i]

        if len(current_line) + len(word) + 1 <= max_line_length:
            if current_line:
                current_line += " "
            current_line += word
        else:
            # Look ahead to see if the next word fits into the remaining space
            if i + 1 < len(words) and len(words[i + 1]) + 1 <= max_line_length - len(current_line):
                current_line += " " + words[i + 1]
                i += 1  # Skip the next word as we have already added it
            else:
                lines.append(current_line)
                current_line = word
                line_count += 1

        i += 1

    if current_line:
        lines.append(current_line)
        line_count += 1

    broken_text = "\n".join(lines)
    return broken_text, line_count


def create_auto_check_row(comment, result, icon, key, user_text_x, save_space):
    lines = 1
    max_line_length = 80 if save_space else 100
    if len(result) >= max_line_length:
        broken_result, lines = insert_line_breaks(result, max_line_length)
    else:
        broken_result = result

    row = [
        Sg.Column([
            [Sg.Image(icon), Sg.Text(broken_result,
                                     size=(int(0.78 * max_line_length), lines), justification='left')],
        ], pad=(0, 0),
            justification='left', expand_x=True
        ),
        Sg.Column([
            [Sg.InputText(default_text=f"{comment}",
                          key=key, size=(user_text_x, lines),
                          enable_events=True, text_color='#000000',
                          background_color='#ffffff',
                          ## QT border_width=0,
                          justification='left',
                          tooltip=comment, pad=(0, 0))],
        ],
            justification='left', expand_x=False
        ),
    ]

    return row, lines


class FrameSettings:
    def __init__(self, tab_width, tab_height, pix_per_line, checks, passing, failing, quiet=True):
        self.width = int(tab_width)
        self.tab_height = tab_height
        self.pix_per_line = pix_per_line
        self.height = 0
        self.checks = checks
        self.height_user = 0
        self.scroll_user = False
        self.passing = passing
        self.height_pass = 0
        self.scroll_pass = False
        self.failing = failing
        self.height_fail = 0
        self.scroll_fail = False
        self.subframe_scroll = False
        self.quiet = quiet
        self.checks_pix_per_line = ceil(self.pix_per_line * 1.652)
        self.domain_pix_per_line = ceil(self.pix_per_line * 1.21)
        self.auto_pix_per_line = ceil(self.pix_per_line * 1.6)
        # Initialize settings
        self.calculate_initial_settings()

    def calculate_pixel_height(self):
        if not self.quiet:
            logging.debug(f'---Calculating frame height: {self.checks[0].get(KEY_OUT_DESC)}')
        user_line_count = 0
        check_count = 0
        for check in self.checks:
            description = check.get(KEY_OUT_DESC)
            user_line_count += description.count('\n')
            check_count += 1
        return int((check_count + 0.60 * user_line_count) * self.checks_pix_per_line)

    def calculate_subframe_pixel_height(self, n_items):
        return int(n_items * self.auto_pix_per_line + self.domain_pix_per_line)

    def calculate_frame_height(self):
        return self.height_user + self.height_pass + self.height_fail

    def count_wrapped_lines(self, text, max_line_length):
        _, line_count = insert_line_breaks(text, max_line_length)
        return line_count

    def calculate_auto_frame_pixel_height(self, tests):
        if len(tests) == 0:
            return 0
        height = self.domain_pix_per_line
        for domain, test_list in tests.items():
            item_count = len(test_list)
            if item_count > 0:
                # Calculate additional height based on the number of wrapped lines
                wrapped_lines_count = 0
                for test in test_list:
                    result = test[KEY_OUT_MESSAGE]  # Assuming result is stored in this key
                    wrapped_lines_count += self.count_wrapped_lines(result, 100)  # Assuming 90 as max_line_length

                # Calculate the height for this subframe, incorporating the wrapped_lines_count
                subframe_height = self.calculate_subframe_pixel_height(wrapped_lines_count)
                height += subframe_height

        return height

    def calculate_initial_settings(self):
        self.height_user = self.calculate_pixel_height()
        self.height_pass = self.calculate_auto_frame_pixel_height(tests=self.passing)
        self.height_fail = self.calculate_auto_frame_pixel_height(tests=self.failing)
        self.height = self.calculate_frame_height()
        if not self.quiet:
            logging.debug(f'---Initial frame settings calculated:')
            logging.debug(f'    User Frame:')
            logging.debug(f'  User Frame Height: {self.height_user}')
            logging.debug(f'    Pass Frame:')
            logging.debug(f'  Pass Frame Height: {self.height_pass}')
            logging.debug(f'    Fail Frame:')
            logging.debug(f'  Fail Frame Height: {self.height_fail}')
            logging.debug(f'  Total Frame Height: {self.height}')


def adjust_each_frame_height(frame_settings, use_logging=False):
    max_user, max_pass, max_fail = 0, 0, 0
    if frame_settings.height_user and frame_settings.height_pass and frame_settings.height_fail:
        max_pass = max_fail = int(frame_settings.tab_height * 0.25)
        max_user = int(frame_settings.tab_height * 0.35)
    elif frame_settings.height_user and (frame_settings.height_pass or frame_settings.height_fail):
        max_pass = max_fail = int(frame_settings.tab_height * 0.45)
        max_user = int(frame_settings.tab_height * 0.45)
    else:
        max_user = int(frame_settings.tab_height*0.9)
    # Evaluate tab width
    if frame_settings.width < 800:
        frame_settings.scroll_user = True
    if use_logging:
        if frame_settings.height < frame_settings.tab_height:
            logging.debug(f'---Frame Settings not adjusted:')
            logging.debug(f'  User Frame Height: {frame_settings.height_user}')
            logging.debug(f'  Pass Frame Height: {frame_settings.height_pass}')
            logging.debug(f'  Fail Frame Height: {frame_settings.height_fail}')
            logging.debug(f'  Total Frame Height: {frame_settings.height}')

    while frame_settings.height > frame_settings.tab_height:
        excess = frame_settings.height - 0.9*frame_settings.tab_height
        if frame_settings.height_pass > max_pass:
            frame_settings.height_pass = max_pass if excess >= max_pass else ceil(frame_settings.height_pass - excess)
            frame_settings.scroll_pass = True
        elif frame_settings.height_fail > max_fail:
            frame_settings.height_fail = max_fail if excess >= max_fail else ceil(frame_settings.height_fail - excess)
            frame_settings.scroll_fail = True
        else:
            frame_settings.height_user = max_user if excess >= max_user else ceil(frame_settings.height_user - excess)
            frame_settings.scroll_user = True
            if frame_settings.height > frame_settings.tab_height:
                if use_logging:
                    logging.warning(
                        f'****Dialog adjustment failed: dialog height {frame_settings.height} > available space in tab {frame_settings.tab_height}')
                    logging.warning(f'  User Frame Height: {frame_settings.height_user}')
                    logging.warning(f'  Pass Frame Height: {frame_settings.height_pass}')
                    logging.warning(f'  Fail Frame Height: {frame_settings.height_fail}')
                    logging.warning(f'  Total Frame Height: {frame_settings.height}')
                break

        frame_settings.height = frame_settings.calculate_frame_height()
        if use_logging:
            logging.debug(f'----Frame Settings adjusted:')
            logging.debug(f'  User Frame Height: {frame_settings.height_user}')
            logging.debug(f'  Pass Frame Height: {frame_settings.height_pass}')
            logging.debug(f'  Fail Frame Height: {frame_settings.height_fail}')
            logging.debug(f'  Total Frame Height: {frame_settings.height}')


def make_subframe(input_text, content_list):
    """
    Create a subframe with a specified text header and content.

    Args:
        input_text (str): The header text for the subframe.
        content_list (list): The content to be included in the subframe.

    Returns:
        Sg.Frame: A PySimpleGUI Frame element.
    """
    return Sg.Frame(f"   {input_text}", [content_list],
                    pad=(1, 1),
                    # expand_x=True,
                    # expand_y=True,
                    background_color='#C3C3C3',
                    border_width=0)


def create_subframes_for_domain(tests_by_domain, user_text_x, frame_settings, save_space):
    """
    Create subframes for each domain, containing rows with test details.

    This function iterates through each domain in the tests_by_domain dictionary,
    creating rows for each test with details like comments, icons, and results.
    These rows are assembled into subframes for each domain.

    Args:
        tests_by_domain (dict): A dictionary grouping tests by their domain.
        user_text_x (int): X-coordinate for positioning user-related text.
        frame_settings (obj): Width of the subframe.
        save_space (bool): Flag to determine if scrolling is to be enabled for saving space.

    Returns:
        list: A list of subframes, each containing detailed rows of tests for a domain.
    """

    subframes = []
    for domain_name, tests in tests_by_domain.items():
        rows = []
        line_count_per_domain = 0

        for test in tests:
            # Extracting test details
            comment = test[KEY_OUT_COMMENT]
            icon = test[KEY_OUT_ICON]
            result = test[KEY_OUT_MESSAGE]
            key_name = create_key(domain_name, test[KEY_OUT_DESC], KEY_INPUT_TEXT)

            # Creating a row for each test
            row, lines = create_auto_check_row(comment, result, icon, key_name, user_text_x, save_space)
            line_count_per_domain += lines
            rows.append(row)
            rows.append([Sg.HorizontalSeparator(pad=(0, 0))])

        if rows:
            # Defining subframe characteristics
            # subframe_size = (int(0.98 * frame_settings.width), line_count_per_domain * 30)

            # Creating and appending subframes for each domain
            subframes.append([make_subframe(domain_name, [
                Sg.Column(rows,  # size=subframe_size,
                          scrollable=frame_settings.subframe_scroll,
                          ## QT vertical_scroll_only=vertical_scroll_only
                          )])])

    return subframes


def auto_checks_in_tab(tests, tab_key):
    return [test for test in tests if test[KEY_OUT_TAB] == tab_key]


def sort_by_domain(tests):
    tests_by_domain = defaultdict(list)
    for test in tests:
        domain_name = test[KEY_OUT_DOMAIN_NAME]
        tests_by_domain[domain_name].append(test)
    return tests_by_domain


def create_bulleted_string(title, sentences, chars_per_line):
    """
    Create a bulleted string with a title and list of sentences,
    formatted with word wrapping and title padding.

    Args:
        title (str): The title of the list.
        sentences (list of str): A list of sentences to include in the
            bulleted list.
        chars_per_line (int): The maximum number of characters per line.

    Returns:
        str: A formatted string with the title and bulleted list,
            wrapped and indented as needed.
    """
    # Define the indentation
    wrap_indent = ' ' * 6

    # Pad the title if it's shorter than chars_per_line
    padded_title = f"**{title}**".ljust(chars_per_line)
    wrap_title = textwrap.fill(padded_title,
                               width=chars_per_line)

    # Create a list starting with the padded title
    output_list = [wrap_title]

    # Add each sentence as a new line with a bullet point, wrapped and indented
    for sentence in sentences:
        wrapped_text = textwrap.fill(f"\u2022 {sentence}",
                                     width=chars_per_line,
                                     subsequent_indent=wrap_indent,
                                     break_long_words=True,
                                     break_on_hyphens=False)
        output_list.append(wrapped_text)

    # Join the list into a single string separated by new lines
    output_string = "\n".join(output_list)

    return output_string


def create_tab_manual_checks(check_boxes, passing_tests,
                             failed_tests, tab_width, tab_height,
                             pix_per_char_width, pix_per_char_height, save_space,
                             user_text_width, check_character_width):
    """
    Create a tab with manual checks, failed tests, and passed tests.

    Pseudocode:
    1. Calculate max_check, the maximum length of the descriptions of the manual checks.
    2. Determine the pixel-per-character ratio and the horizontal size for user text based on
       whether space-saving is enabled.
    3. Initialize an empty list, tabs, to hold the individual tab layouts.
    4. Loop through all the keys in check_boxes:
        a. Initialize empty layouts for the frame and the tab.
        b. Determine the frame properties using `determine_frame_properties`.
        c. Create rows for manual checks using `create_manual_check_row` and add to the frame layout.
        d. Create a new frame with the above layout.
        e. Create subframes for Failed Tests:
            i. Filter the failed_tests for the current key.
            ii. Create subframes using `create_subframes_for_domain`.
        f. Create subframes for Passing Tests:
            i. Filter the passing_tests for the current key.
            ii. Create subframes using `create_subframes_for_domain`.
        g. Create a new tab with all the frames and subframes and add it to the list of tabs.
    5. Return the list of tabs.
    Args:
        check_boxes (dict): Dictionary holding check box data.
        passing_tests (list): List of passing tests.
        failed_tests (list): List of failed tests.
        tab_width (int): Width of the tab.
        tab_height (int): Height of the tab.
        pix_per_char_width (int): Pixel width per character.
        pix_per_char_height (int): Pixel height per line.
        save_space (bool): Flag to enable/disable space-saving layout.

    Returns:
        list: List of tabs to be added to the GUI.
    """

    # Calculate the maximum length of the descriptions in check_boxes
    max_checkbox_length = max([0,
                               *[len(item[KEY_OUT_DESC]) for key in check_boxes for item in check_boxes[key]]])

    # Initialize an empty list to hold individual tab layouts
    tabs = []

    # Determine pixel-per-character ratio
    pixels_per_char = 8.3 if save_space else pix_per_char_width

    # Determine horizontal size for user text
    # user_text_x = int(20 * tab_width / pix_per_char_width) if save_space else int(
    #   0.20 * tab_width / pix_per_char_width)
    user_text_x = user_text_width

    # Specify vertical space available for frames
    vertical_size = tab_height - 0 * pix_per_char_height if save_space \
        else tab_height - 7 * pix_per_char_height

    # Loop through all keys in check_boxes
    for tab_key in check_boxes:
        layout = []  # Initialize empty layout for the tab
        frame_layout = []  # Initialize empty layout for the frame

        # Find the passing/failed tests that are part of this tab
        matching_failed_tests = auto_checks_in_tab(failed_tests, tab_key)
        failed_tests_by_domain = sort_by_domain(matching_failed_tests)

        matching_passing_tests = auto_checks_in_tab(passing_tests, tab_key)
        passing_tests_by_domain = sort_by_domain(matching_passing_tests)

        matching_manual_checks = check_boxes[tab_key]
        # Determine the maximum length of the descriptions in check_boxes
        # max_checkbox_tab_length = 65 if save_space else 100
        max_checkbox_tab_length = check_character_width
        row_count = 0
        for item in matching_manual_checks:
            description = item.get(KEY_OUT_DESC, None)
            row_count += description.count('\n') + 1

        # Initialize frame data
        frame_settings = FrameSettings(
            tab_width=int(0.98 * tab_width),
            tab_height=vertical_size,
            pix_per_line=pix_per_char_height,
            checks=check_boxes[tab_key],
            passing=passing_tests_by_domain,
            failing=failed_tests_by_domain,
            quiet=True)
        # Determine properties like frame size and scroll-ability
        adjust_each_frame_height(frame_settings)

        # Create rows for manual checks and add them to frame layout

        for item in matching_manual_checks:
            manual_row, line_count = create_manual_check_row(
                item, max_checkbox_tab_length, user_text_x)
            frame_layout.append(manual_row)
            frame_layout.append([Sg.HorizontalSeparator(pad=(0, 0))])

        # Override for small screens
        if save_space:
            vertical_scroll = False
            sb_width = 1
            tab_font = ('Helvetica', '8', 'bold')
        else:
            vertical_scroll = frame_settings.scroll_user
            sb_width = 1
            tab_font = None

        # Create a frame with the above layout
        frame = Sg.Frame(f"{tab_key}: Select an option for each item",
                         [[Sg.Column(frame_layout,
                                     size=(frame_settings.width,
                                           frame_settings.height_user),
                                     ## QT sbar_width=sb_width,vertical_scroll_only=vertical_scroll,
                                     vertical_scroll_only=True,
                                     scrollable=frame_settings.scroll_user,
                                     )]],
                         border_width=1)
        layout.append([frame])

        # Create subframes for Failed Tests
        subframes_failed = create_subframes_for_domain(
            failed_tests_by_domain, user_text_x, frame_settings, save_space)

        # Check if there are any subframes and construct the layout accordingly
        if subframes_failed:
            layout.append([Sg.Frame('Failed Tests',
                                    [[Sg.Column(subframes_failed,
                                                size=(frame_settings.width, frame_settings.height_fail),
                                                ## QT sbar_width=sb_width,vertical_scroll_only=vertical_scroll,
                                                scrollable=frame_settings.scroll_fail,
                                                vertical_scroll_only=True
                                                )]],
                                    )])

        # Create subframes for Passing Tests
        subframes_passing = create_subframes_for_domain(
            passing_tests_by_domain, user_text_x, frame_settings, save_space)
        if subframes_passing:
            layout.append([Sg.Frame('Passing Tests',
                                    [[Sg.Column(subframes_passing,
                                                size=(frame_settings.width,
                                                      frame_settings.height_pass),
                                                ## QT sbar_width=sb_width,vertical_scroll_only=vertical_scroll,
                                                scrollable=frame_settings.scroll_pass,
                                                vertical_scroll_only=True
                                                )]],
                                    )])
        # Final tab layout
        tab_title = tab_key[:9] if save_space else tab_key[:13]
        tab = Sg.Tab(tab_title, [[Sg.Column(layout)]],
                     font=tab_font, key=tab_key, tooltip=tab_key)
        tabs.append(tab)  # Add the tab to the list of tabs

    return tabs  # Return the list of tabs


def is_visible_tab(tab, window):
    visible = True
    # Logic for determining if a tab should be visible or not
    if tab.__dict__.get('Key', None) == REVIEW_LEVELS['IMPLANTED_DEVICE']:
        if not window[create_key(KEY_IMD+KEY_RADIO+'-YES')].get():
            visible = False
    elif tab.__dict__.get('Key', None) == REVIEW_LEVELS['PRIOR_RT']:
        if not window[create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES')].get():
            visible = False
    return visible


# Define a function to handle events related to radio buttons
def on_manual_radio_button_click(window, event):
    """
    Updates the color and background of a text input element when a radio button is selected
    """
    prefix, radio = event[0].split(KEY_CHECK + KEY_RADIO)
    if radio == 'No':
        # Update text color and background when the "No" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#000000',
                                 background_color='#ffffff')
    else:
        #
        # Update text color and background when the "Yes/NA" radio button is selected
        input_key = create_key(prefix + KEY_CHECK + KEY_INPUT_TEXT)
        window[input_key].update(text_color='#ffffff',
                                 background_color='#848884')


def update_window_error(window, key, bg=False):
    error_text_color = '#8B0000'
    error_bg_color = '#8B0000'
    error_bg_text = '#ffffff'
    if bg:
        window[key].update(text_color=error_bg_text,
                           background_color=error_bg_color)
    else:
        window[key].update(text_color=error_text_color)


def check_radio_on(values, keys):
    return any(values[k] for k in keys)


def is_valid_automated_test(window, failed_tests, response_required=True):
    is_valid = True
    if response_required:
        for test in failed_tests:
            if test[KEY_OUT_DOMAIN_TYPE] == DOMAIN_TYPE['SANDBOX_KEY']:
                continue
            window_key = create_key(test[KEY_OUT_DOMAIN_NAME], test[KEY_OUT_DESC],
                                    KEY_INPUT_TEXT)
            comment = window[window_key].get()
            if comment == FAILED_AUTOMATED_TEST:
                new_update_window_error(window, [window_key], bg=True)
                is_valid = False
            elif not comment or comment == FAILED_AUTOMATED_TEST:
                new_update_window_error(window, [window_key], bg=True)
                is_valid = False
    return is_valid


def new_update_window_error(window, keys, bg=False):
    error_text_color = '#8B0000'
    error_bg_color = '#8B0000'
    error_bg_text = '#ffffff'

    for key in keys:
        if bg:
            window[key].update(text_color=error_bg_text, background_color=error_bg_color)
        else:
            window[key].update(text_color=error_text_color)


def is_valid_manual_tab(window, values, check_boxes, failed_tests, response_required=True):
    is_valid = True
    is_valid_auto = True

    if response_required:
        for key, items in check_boxes.items():
            for item in items:
                if excluded_check_boxes(key, values) or key == REVIEW_LEVELS['SANDBOX']:
                    continue
                logging.debug(f'---Checkbox information:{key}: {item}')

                options = ['Yes', 'No']
                check_box_radio_keys = [
                    create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}{o}') for o in options
                ]
                input_key = create_key(f'{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}')

                if not any(values[k] for k in check_box_radio_keys):
                    new_update_window_error(window, check_box_radio_keys)
                    is_valid = False

                if values[check_box_radio_keys[1]] and not values[input_key]:
                    new_update_window_error(window, [input_key], bg=True)
                    is_valid = False

        is_valid_auto = is_valid_automated_test(window, failed_tests)

        if not is_valid or not is_valid_auto:
            Sg.popup_error('Please fill in all the required fields.')

    return all([is_valid, is_valid_auto])


def copy_and_filter_checkbox_dict(checkbox_dict1, checkbox_dict2):
    """
    Create filtered copies of checkbox_dict1 and checkbox_dict2
    without the KEY_REVIEW_TYPE key.

    Args:
        checkbox_dict1: First CHECK_BOX dictionary.
        checkbox_dict2: Second CHECK_BOX dictionary.

    Returns:
        filtered_dict1: Filtered copy of checkbox_dict1.
        filtered_dict2: Filtered copy of checkbox_dict2.
    """
    filtered_dict1 = {k: v for k, v in checkbox_dict1.items() if k != KEY_REVIEW_TYPE}
    filtered_dict2 = {k: v for k, v in checkbox_dict2.items() if k != KEY_REVIEW_TYPE}
    return filtered_dict1, filtered_dict2


def merge_dicts(checkbox_dict1, checkbox_dict2):
    """
    Merges two CHECK_BOX dictionaries of the form:
        {
            REVIEW_LEVEL['LEVEL_KEY']: [
                {
                    KEY_OUT_TEST: 'Test Name',
                    # Other test-related key-value pairs...
                },
                # Additional test dictionaries...
            ],
            # Additional review levels...
        }
    Removes empty review levels and duplicate tests.

    Args:
        checkbox_dict1: a CHECK_BOX dictionary
        checkbox_dict2: the CHECK_BOX dictionary to be merged into checkbox_dict1

    Returns:
        merged: a merged CHECK_BOX dictionary with the KEY_REVIEW_TYPE key removed and
                duplicate tests removed

    """
    merged, checkbox_dict2_filtered = copy_and_filter_checkbox_dict(checkbox_dict1, checkbox_dict2)
    keys_in_merged = [
        item[KEY_OUT_TEST] for review_level, review_list in merged.items() for item in review_list]
    for review_level, review_list in checkbox_dict2_filtered.items():
        if review_level in merged:
            for check_box_dict in review_list:
                if check_box_dict[KEY_OUT_TEST] not in keys_in_merged:
                    merged[review_level].append({k: v for k, v in check_box_dict.items()})
                    keys_in_merged.append(check_box_dict[KEY_OUT_TEST])
        elif review_list:
            merged[review_level] = review_list
            keys_in_merged.extend([item[KEY_OUT_TEST] for item in review_list])
    # Double check that there are no empty review levels
    merged = {k: v for k, v in merged.items() if v}

    return merged


def find_domain_name(rso: NamedTuple, domain_level: str) -> str:
    """
    Finds the domain name based on the given Radiotherapy Service Object (RSO)
    and domain level key.

    Args:
        rso (script object): RayStation Script Object containing data for the
            patient, exam, plan, etc.
        domain_level (str): Key for the desired domain level, e.g., "PLAN_KEY".

    Returns:
        str: The domain name corresponding to the given RSO and domain level.

    """
    # Note: It's assumed that DOMAIN_TYPE is defined elsewhere in the code.
    if domain_level == DOMAIN_TYPE['PATIENT_KEY']:
        return rso.patient.PatientID
    if domain_level == DOMAIN_TYPE['EXAM_KEY']:
        return rso.exam.Name
    if domain_level == DOMAIN_TYPE['PLAN_KEY']:
        return rso.plan.Name
    if domain_level == DOMAIN_TYPE['BEAMSET_KEY']:
        return rso.beamset.DicomPlanLabel
    if domain_level == DOMAIN_TYPE['SANDBOX_KEY']:
        return domain_level
    if domain_level == DOMAIN_TYPE['RX_KEY']:
        return rso.beamset.PrimaryDosePrescription
    if domain_level == DOMAIN_TYPE['LOG_KEY']:
        return domain_level


def consolidate_dicts(review_level, chars_per_line):
    grouped = {}
    consolidated_list = []

    for item in review_level:
        check_group = item.get(KEY_OUT_CHECK_GROUP)
        if check_group:
            group_key = check_group.get('KEY')
            if group_key in grouped:
                grouped[group_key].append(item[KEY_OUT_DESC])
            else:
                grouped[group_key] = [item[KEY_OUT_DESC]]
        else:
            consolidated_list.append(item)

    for check_group_key, group_description in grouped.items():
        # Search for the first item with the matching 'KEY' in KEY_OUT_CHECK_GROUP
        first_item = next(item for item in review_level if
                          item.get(KEY_OUT_CHECK_GROUP, {}).get('KEY') == check_group_key)
        new_dict = {
            KEY_OUT_TEST: first_item[KEY_OUT_CHECK_GROUP]['KEY'],
            KEY_OUT_DESC: create_bulleted_string(first_item[KEY_OUT_CHECK_GROUP]['TEXT'],
                                                 sentences=group_description,
                                                 chars_per_line=chars_per_line),
            KEY_OUT_DOMAIN_TYPE: first_item[KEY_OUT_DOMAIN_TYPE],
            KEY_OUT_OPTIONS: first_item[KEY_OUT_OPTIONS].replace("NA,", ""),
            KEY_AUTOMATION: {},
        }
        consolidated_list.append(new_dict)

    return consolidated_list


def build_manual_check_box_list(rso, beamsets, review_type="Physics", chars_per_line=100):
    """
    Depending on the type of beamset we are checking, find the appropriate
    checklist from review_definitions
    :param rso:
    :param beamsets: (list): list of all beamsets
    :param review_type: (str): "Physics" or "Dosimetry"
    :return: checks dictionary
    """
    if review_type not in REVIEW_TYPES:
        sys.exit(f'UNKNOWN REVIEW TYPE {review_type}')
    # Initialize the checklist with the selected review type
    checklist = CHECK_BOXES_PHYSICS_REVIEW if review_type == "Physics" else CHECK_BOXES_DOSIMETRY_SAFETY
    # Add in technique-specific checklist
    for beamset_name in beamsets:
        technique = rso.plan.BeamSets[beamset_name].DeliveryTechnique
        modality = rso.plan.BeamSets[beamset_name].Modality
        # Check if technique-specific checklist exists
        if "T3D" in beamset_name:
            technique_checklist = TECHNIQUE_MAP["T3D"][review_type]
        elif "Electrons" in modality:
            technique_checklist = TECHNIQUE_MAP["SMLC_Electrons"][review_type]
        elif technique in TECHNIQUE_MAP:
            technique_checklist = TECHNIQUE_MAP[technique][review_type]
        else:
            sys.exit(f'UNKNOWN TREATMENT TECHNIQUE {technique}')
        checklist = merge_dicts(checklist, technique_checklist)

        for level in checklist:
            for item in checklist[level]:
                item[KEY_OUT_MESSAGE] = ""
                item[KEY_OUT_COMMENT] = ""
                item[KEY_OUT_ICON] = None
                item[KEY_OUT_DOMAIN_NAME] = find_domain_name(
                    rso, item[KEY_OUT_DOMAIN_TYPE])
    # Filter the checks that have been replaced with automation
    filtered_checklist = {}
    for level in checklist:
        filtered_checklist[level] = []
        for item in checklist[level]:
            # Determine if this test has been replaced with automation.
            if is_replaced(item):
                logging.info(f'This checkbox from the {review_type} review: {item[KEY_OUT_DESC]}: '
                             f'has been replaced with an automated test.')
                continue
            else:
                filtered_checklist[level].append(item)
    grouped_checks = {}
    for review_level, check_list in filtered_checklist.items():
        grouped_checks[review_level] = consolidate_dicts(check_list, chars_per_line=chars_per_line)

    return grouped_checks


def is_replaced(item):
    replaced_status = item.get(KEY_AUTOMATION, {}).get(KEY_STATUS, False)
    return replaced_status == REPLACED


def get_tests_from_tree(tree_children):
    """
    Determine all tests that failed and passed from the tree
    :param tree_children:
    :return:
    """
    passing_tests = []
    failed_tests = []
    for domain_type, domain_name, comment, child_key, result, pass_fail, icon in tree_children:
        review_tab, comment = search_string(comment)
        child = {
            KEY_OUT_DOMAIN_TYPE: domain_type,
            KEY_OUT_DOMAIN_NAME: domain_name,
            KEY_OUT_DESC: str(comment),
            KEY_OUT_MESSAGE: str(result),
            KEY_OUT_ICON: str(icon),
            KEY_OUT_RESULT: pass_fail,
            KEY_OUT_TAB: review_tab}
        if pass_fail != PASS:
            child[KEY_OUT_COMMENT] = FAILED_AUTOMATED_TEST
            failed_tests.append(child)
        else:
            child[KEY_OUT_COMMENT] = ""
            passing_tests.append(child)
    return passing_tests, failed_tests


def get_key(components, values):
    key_string = "".join(components)
    logging.debug(f'---Getting the key {key_string}')

    # Check if the radio button is selected based on its key
    return values.get(create_key(key_string), False)


def process_check_box_values(window, values, checks):
    """
    Parses the resulting window values and sorts the checkbox values.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        values (dict): A dictionary containing the window values
        checks (dict): A dictionary containing the checkbox data.

    Returns:
        list: A sorted list containing the checkbox values.
    """
    sorted_results = []
    for test_level in checks:
        for item in checks[test_level]:
            parsed_item = {KEY_OUT_DESC: item[KEY_OUT_DESC]}
            radio_pre = f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_RADIO}"
            input_key = create_key(f"{item[KEY_OUT_TEST]}{KEY_CHECK}{KEY_INPUT_TEXT}")
            if excluded_check_boxes(test_level, values):
                continue
            if get_key([radio_pre, 'Yes'], values):
                parsed_item[KEY_OUT_RESULT] = PASS
                parsed_item[KEY_OUT_ICON] = GREEN_CIRCLE
            elif get_key([radio_pre, 'No'], values):
                parsed_item[KEY_OUT_RESULT] = FAIL
                parsed_item[KEY_OUT_ICON] = RED_CIRCLE
            elif get_key([radio_pre, 'NA'], values):
                parsed_item[KEY_OUT_RESULT] = NA
                parsed_item[KEY_OUT_ICON] = BLUE_CIRCLE
            else:
                parsed_item[KEY_OUT_RESULT] = ALERT
                parsed_item[KEY_OUT_ICON] = YELLOW_CIRCLE
            parsed_item[KEY_OUT_COMMENT] = window[input_key].get()
            parsed_item[KEY_OUT_TEST_SOURCE] = SOURCE_USER
            parsed_item[KEY_OUT_TAB] = test_level
            # There is no message for user driven tests but the message
            # field is populated for all the auto tests
            parsed_item[KEY_OUT_MESSAGE] = parsed_item[KEY_OUT_RESULT]
            sorted_results.append(parsed_item)
    return sorted_results


def process_auto_tests(window, tests):
    """
    Parses the tests results generated by automation and adds them to a list.

    Args:
        window (PySimpleGUI.Window): The PySimpleGUI window object.
        tests (list): A list of tests, where each item is a dict containing:

            KEY_OUT_DESC: the name of the test
            KEY_OUT_MESSAGE: PASS/FAIL/ALERT
            KEY_OUT_ICON: string containing icon
            KEY_OUT_COMMENT: a placeholder for the default comment
            KEY_OUT_TAB: the plan check module in raystation where this check
                              is performed->Tab on the gui
            KEY_OUT_DOMAIN_TYPE: The type of domain level object from which the test is
                                 taken, i.e. an exam, a beamset, a plan
            KEY_OUT_DOMAIN_NAME: the Name of the domain i.e. Beamset: Pelv_VMA_R0A0

        comment, result, icon file string, and the tab to which this was assigned
            and icon.

    Returns:
        list: A list of parsed failed tests.
    """
    test_list = []
    for test in tests:
        domain_name = test[KEY_OUT_DOMAIN_NAME]
        description = test[KEY_OUT_DESC]
        parsed_item = {
            KEY_OUT_DESC: description,
            KEY_OUT_MESSAGE: test[KEY_OUT_MESSAGE],
            KEY_OUT_COMMENT: window[
                create_key(domain_name, description, KEY_INPUT_TEXT)].get(),
            KEY_OUT_RESULT: test[KEY_OUT_RESULT],
            KEY_OUT_DOMAIN_TYPE: test[KEY_OUT_DOMAIN_TYPE],
            KEY_OUT_DOMAIN_NAME: domain_name,
            KEY_OUT_TAB: test[KEY_OUT_TAB],
            KEY_OUT_TEST_SOURCE: SOURCE_AUTO,

        }
        if test[KEY_OUT_RESULT] == FAIL:
            parsed_item[KEY_OUT_ICON] = RED_CIRCLE
        elif test[KEY_OUT_RESULT] == PASS:
            parsed_item[KEY_OUT_ICON] = GREEN_CIRCLE
        elif test[KEY_OUT_RESULT] == ALERT:
            parsed_item[KEY_OUT_ICON] = YELLOW_CIRCLE
        else:
            parsed_item[KEY_OUT_ICON] = BLUE_CIRCLE
        test_list.append(parsed_item)

    return test_list
