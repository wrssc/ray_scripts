"""
Create the information entry prompt for the dose and physics review
"""

try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
import sys
import logging
from library.PlanReview.utils.protocol_loading import get_order_instructions, \
    site_protocol_list, order_dict, load_plan_names, get_frequencies
from library.PlanReview.utils.constants import *
from library.PlanReview.review_definitions import (
    PROTOCOL_DIR, PATIENT_ORIENTATIONS, TECHNIQUE_TYPES)


def create_tuple_key(element_type, beamset_index=None, target_index=None):
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


def update_listbox(window, values, key, text):
    filtered_values = [value for value in values if text.lower() in value.lower()]
    window[key].update(values=filtered_values)


def update_billing_combo(window, key, technique, modality):
    billing_choices = TECHNIQUE_TYPES.get((technique, modality), [])
    if not billing_choices:
        Sg.popup_error(f'{modality} {technique} appears to be an unsupported technique/modality')
    else:
        current_value = window[key].get()
        if current_value in billing_choices:
            # Move the current value to the top of the list
            billing_choices.remove(current_value)
            billing_choices.insert(0, current_value)
        window[key].update(values=billing_choices, value=current_value)


def update_site_input(window, key, beamset_name):
    default_site = beamset_name[0:4]
    current_value = window[key].get()
    if not current_value:
        window[key].update(value=default_site)


def create_site_billing_row(fill_row, index, visible):
    # Flatten the SITE_CLASSIFICATION dictionary to get all beamset aliases
    # beamset_aliases = extract_beamset_aliases(SITE_CLASSIFICATION)
    site_row = []
    billing_row = []
    if fill_row:
        site_row = [Sg.Text('Enter a site name, e.g. BreL',
                            visible=visible,
                            size=(20, 1),
                            key=create_tuple_key(KEY_DOSE_SITE + KEY_T, index),
                            enable_events=True),
                    Sg.Input(key=create_tuple_key(KEY_DOSE_SITE, index),
                             size=(10, 1),
                             visible=visible,
                             enable_events=True),
                    ]
        # sg.Input(size=(20, 1), key='-INPUT-', enable_events=True),
        # Sg.Listbox(key=create_tuple_key(KEY_DOSE_SITE, index),
        #            values=beamset_aliases,
        #            size=(20, 1),
        #            enable_events=True)]
        billing_row = [Sg.Text('Select treatment technique',
                               visible=visible,
                               key=create_tuple_key(KEY_DOSE_BILL + KEY_T, index),
                               enable_events=True),
                       Sg.Combo(['Unknown Technique/Modality'],
                                size=(20, 1),
                                key=create_tuple_key(KEY_DOSE_BILL, index),
                                visible=visible,
                                enable_events=True)]
    return site_row, billing_row


def create_beamset_layout(beamsets, targets, include_site_billing=False):
    """
    Creates the layout for the beamset section in the GUI.

    This function generates the layout for the beamset section, including
    beamset selection, target count, and fractions count.

    Args:
        beamsets (list): The list of available beamsets.
        targets (list): The list of available targets.

    Returns:
        list: The layout for the beamset section.
    """
    num_beamsets = len(beamsets)
    if num_beamsets == 1:
        bs_visible = True
    else:
        bs_visible = False
    max_targets = len(targets)

    # Define header texts and sizes for columns in the beamset layout
    header_sizes = [16, 3, 3]

    beamset_layout = []
    row_pair = []
    # Create layout for each beamset
    for i in range(num_beamsets):
        site_row, billing_row = create_site_billing_row(include_site_billing, i, bs_visible)
        single_beamset_layout = [
            [Sg.Text(f'Beamset {i + 1} Name',
                     visible=bs_visible,
                     key=create_tuple_key(KEY_BEAMSET_COUNT + KEY_T, i)),
             Sg.Combo(values=beamsets, key=create_tuple_key(KEY_BEAMSET_SELECT, i),
                      visible=bs_visible, size=(header_sizes[0], 1),
                      enable_events=True)],
            site_row, billing_row,
            [Sg.Text(f'Number of targets in Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_tuple_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)),
             Sg.Combo(values=list(range(1, max_targets + 1)),
                      key=create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i),
                      visible=bs_visible,
                      size=(header_sizes[1], 1),
                      enable_events=True)],
            [Sg.Text(f'Number of fractions in Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)),
             Sg.Input(key=create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i),
                      visible=bs_visible, size=(header_sizes[2], 1),
                      enable_events=True), ]
        ]
        # Add target layout to the beamset layout
        single_beamset_layout.extend(create_target_layout(i, targets))
        row_pair.append(Sg.Frame(f'Beamset {i + 1}',
                                 single_beamset_layout,
                                 key=create_tuple_key(KEY_BEAMSET + KEY_F, i),
                                 font=('Helvetica', 10, 'bold'),
                                 title_color='blue',
                                 ## QT vertical_alignment='top',
                                 visible=bs_visible))
        if len(row_pair) == 2:
            beamset_layout.append(row_pair)
            row_pair = []
    if row_pair:
        beamset_layout.append(row_pair)
    return beamset_layout


# Extract all beamset aliases from the SITE_CLASSIFICATION dictionary
def extract_beamset_aliases(site_classification):
    beamset_aliases = []
    for site, site_info in site_classification.items():
        beamset_aliases.extend(site_info.get('beamset_aliases', []))
        for subsite, subsite_info in site_info.get('Subsites', {}).items():
            beamset_aliases.extend(subsite_info.get('beamset_aliases', []))
            for subsubsite, subsubsite_info in subsite_info.get('Subsites', {}).items():
                beamset_aliases.extend(subsubsite_info.get('beamset_aliases', []))
    return beamset_aliases


def update_preplan_beamset_rows(main_window, values, num_beamsets, max_beamsets, max_targets,
                                review_type='Physics'):
    """
    Updates the visibility of beamset rows in the GUI based on the user's selection.

    Args:
        main_window (Sg.Window): The main PySimpleGUI window.
        values (dict): The dictionary containing the current values of the window elements.
        num_beamsets (int): The number of beamsets selected by the user.
        max_beamsets (int): The maximum number of beamsets in the plan.
        max_targets (int): The maximum number of targets in the plan.
        review_type (str): The type of review being performed. Defaults to 'Physics'.

    """
    # Add rows for site and billing information if the review type is dosimetry
    if review_type.lower() == 'dosimetry':
        include_site_billing = True
    else:
        include_site_billing = False
    # Update the visibility of target rows based on the user's selection of the number of targets
    # in each beamset
    for beamset_index in range(num_beamsets):
        num_targets_value = values[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, beamset_index)]
        if num_targets_value:
            num_targets = int(num_targets_value)
            update_preplan_target_rows(main_window, num_targets, beamset_index, max_targets)

    # Update the visibility of beamset rows based on the user's selection
    for i in range(max_beamsets):
        is_visible = i < num_beamsets
        main_window[create_tuple_key(KEY_BEAMSET + KEY_F, i)].update(
            visible=is_visible)  # Update the visibility of the frame
        main_window[create_tuple_key(KEY_BEAMSET_COUNT + KEY_T, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_SELECT, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i)].update(visible=is_visible)
        if include_site_billing:
            main_window[create_tuple_key(KEY_DOSE_SITE + KEY_T, i)].update(visible=is_visible)
            main_window[create_tuple_key(KEY_DOSE_SITE, i)].update(visible=is_visible)
            main_window[create_tuple_key(KEY_DOSE_BILL + KEY_T, i)].update(visible=is_visible)
            main_window[create_tuple_key(KEY_DOSE_BILL, i)].update(visible=is_visible)
    main_window.refresh()
    main_window['-COLUMN_BEAMSETS-'].contents_changed()


def update_site_billing_visibility(main_window, values, num_beamsets):
    return None


def create_target_layout(beamset_i, targets):
    """
    Create the layout for target selection, total dose, and dose per fraction for each beamset.

    Parameters:
    max_targets (int): The maximum number of targets allowed in the layout.
    beamset_i (int): The index of the current beamset.
    targets (list): A list of target options for the user to choose from.

    Returns:
    list: A list containing the target layout for the specified beamset.
    """
    target_combo_values = targets
    max_targets = len(targets)
    max_combo_value_length = max(len(value) for value in target_combo_values)

    header_texts = ['Target Name', 'Plan Dose (Gy)', 'Fract Dose (Gy)']
    header_sizes = [max(max_combo_value_length, len(header_texts[0])),
                    len(header_texts[1]) - 2, len(header_texts[2]) - 2]

    target_layout = [
        [
            Sg.Text('', size=(6, 1)),  # Empty space
            Sg.Text(header_texts[0], size=(header_sizes[0], 1),
                    key=create_tuple_key('beamset_header', beamset_i, 0), visible=False),
            Sg.Text(header_texts[1], size=(header_sizes[1], 1),
                    key=create_tuple_key('beamset_header', beamset_i, 1), visible=False),
            Sg.Text(header_texts[2], size=(header_sizes[2], 1),
                    key=create_tuple_key('beamset_header', beamset_i, 2), visible=False),
        ]
    ]

    for i in range(max_targets):
        target_layout.append([
            Sg.Text(f'Target {i + 1}: ', visible=False,
                    key=create_tuple_key(KEY_BEAMSET_TARGET_NAME + KEY_T, beamset_i, i)),
            Sg.Combo(values=target_combo_values,
                     key=create_tuple_key(KEY_BEAMSET_TARGET_NAME, beamset_i, i),
                     visible=False,
                     size=(header_sizes[0], 1)),
            Sg.Input(key=create_tuple_key(KEY_BEAMSET_DOSE, beamset_i, i), visible=False,
                     size=(header_sizes[1], 1),
                     justification='c',
                     enable_events=True),
            Sg.Text('', key=create_tuple_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i),
                    visible=False,
                    justification='c',
                    size=(header_sizes[2], 1))
        ])

    return target_layout


def update_preplan_target_rows(main_window, num_targets, beamset_i, maximum_target_number):
    """
    Update the visibility of target rows based on the number of targets in the specified beamset.

    Parameters:
    main_window (Sg.Window): The main PySimpleGUI window object.
    num_targets (int): The number of targets in the specified beamset.
    beamset_i (int): The index of the current beamset.
    """
    for i in range(maximum_target_number):
        is_visible = i < num_targets
        main_window[create_tuple_key(KEY_BEAMSET_TARGET_NAME + KEY_T, beamset_i, i)].update(
            visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_TARGET_NAME, beamset_i, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_DOSE, beamset_i, i)].update(visible=is_visible)
        main_window[create_tuple_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i)].update(
            visible=is_visible)

    # Update the visibility of header texts
    for i in range(3):
        main_window[create_tuple_key('beamset_header', beamset_i, i)].update(
            visible=True if num_targets > 0 else False)
    main_window.refresh()
    main_window['-COLUMN_BEAMSETS-'].contents_changed()


def calculate_single_dose_per_fraction(total_dose, num_fractions):
    """
    Calculate the dose per fraction based on the total dose and the number of fractions.

    Parameters:
    total_dose (str): The total dose as a string (e.g. '60').
    num_fractions (str): The number of fractions as a string (e.g. '30').

    Returns:
    str: The dose per fraction as a string formatted to 3 decimal places (e.g. '2.000'),
    or None if the input is invalid.
    """
    try:
        dose_per_fraction = round(float(total_dose) / float(num_fractions), 2)
        return f'{dose_per_fraction:.3f}'
    except ValueError:
        return None
    except ZeroDivisionError:
        return None


def calculate_preplan_dose_per_fraction(values, main_window, beamset_i, target_i=None):
    """
    Calculate the dose per fraction for either all targets in a beamset or a single target.

    Parameters:
    values (dict): A dictionary containing the values of the input fields.
    main_window (Sg.Window): The main PySimpleGUI window object.
    beamset_i (int): The index of the current beamset.
    target_i (int, optional): The index of a single target. If None, calculations will be done
    for all targets in the beamset.
    """
    if not target_i:
        num_targets = values[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, beamset_i)]
        if num_targets:
            for i in range(int(num_targets)):
                total_dose = values[create_tuple_key(KEY_BEAMSET_DOSE, beamset_i, i)]
                num_fractions = values[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, beamset_i)]
                if num_fractions and total_dose:
                    dose_per_fraction = calculate_single_dose_per_fraction(total_dose,
                                                                           num_fractions)
                    if dose_per_fraction:
                        main_window[create_tuple_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i)].update(
                            dose_per_fraction)
    else:
        total_dose = values[create_tuple_key(KEY_BEAMSET_DOSE, beamset_i, target_i)]
        num_fractions = values[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, beamset_i)]
        if total_dose and num_fractions:
            dose_per_fraction = calculate_single_dose_per_fraction(total_dose, num_fractions)
            if dose_per_fraction:
                main_window[create_tuple_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, target_i)].update(
                    dose_per_fraction)


def create_radio_buttons(radio_phrases, text, indx):
    phrases = radio_phrases.split(',')
    radio_buttons = [Sg.Radio(text=phrase,
                              group_id=create_tuple_key(text + KEY_RADIO, indx),
                              key=create_tuple_key(text + KEY_RADIO + phrase, indx),
                              enable_events=True,
                              visible=False)
                     for phrase in phrases]
    return radio_buttons


def max_width(options):
    return max(len(value) for value in options)


def max_row_size(options):
    width = max_width(options)
    additional_chars = 2
    return width + additional_chars, 1


def max_visible_count(options):
    length = len(options)
    width = max_width(options)
    additional_chars = 2
    return width + additional_chars, length


def create_order_selection_layout(protocols, sites, orders, instructions):
    """

    :param protocols:
    :param sites:
    :param orders:
    :param instructions:
    :return:
    """
    plan_names = load_plan_names(PROTOCOL_DIR)
    text_entries = {'site': 'Body Site', 'protocol': 'Protocol',
                    'tpo': 'Treatment Planning Order',
                    'tf': 'Treatment Frequency',
                    'sf': 'Imaging Frequency'}
    # Initialization
    text_just = 'left'
    #
    # Site Selection
    site_combo = [
        Sg.Text(
            text_entries['site'],
            justification=text_just,
            size=max_row_size([text_entries['site']]),
            key=KEY_SITE_SELECT + KEY_T,
        ),
        Sg.Combo(
            sites,
            default_value='Select Site',
            key=KEY_SITE_SELECT,
            size=max_row_size(sites + ['Select Site']),
            tooltip='Select Site',
            enable_events=True,
            visible=True)]
    #
    # Protocol Selection
    protocol_combo = [
        Sg.Text(
            text_entries['protocol'],
            justification=text_just,
            size=max_row_size([text_entries['protocol']]),
            enable_events=True,
            key=KEY_PROTOCOL_SELECT + KEY_T,
            visible=False
        ),
        Sg.Combo(
            protocols,
            default_value='',
            size=max_row_size(protocols.keys()),
            tooltip='Select Protocol',
            enable_events=True,
            key=KEY_PROTOCOL_SELECT,
            visible=False)]
    #
    # Order Selection
    order_combo = [
        Sg.Text(
            text_entries['tpo'],
            justification=text_just,
            size=max_row_size([text_entries['tpo']]),
            enable_events=True,
            key=KEY_ORDER_SELECT + KEY_T,
            visible=False
        ),
        Sg.Combo(
            orders,
            default_value='',
            size=max_visible_count(orders.keys()),
            tooltip='Select Treatment Planning Order',
            enable_events=True,
            key=KEY_ORDER_SELECT,
            visible=False)]
    #
    # Treatment and imaging frequency
    tf_combo = [
        Sg.Text(
            text_entries['tf'],
            justification=text_just,
            size=max_row_size([text_entries['tf']]),
            enable_events=True,
            key=KEY_TREAT_FREQ + KEY_T,
            visible=False
        ),
        Sg.Combo(
            [],
            key=KEY_TREAT_FREQ,
            size=(16, 1),
            visible=False)
    ]
    if_combo = [
        Sg.Text(
            text_entries['sf'],
            justification=text_just,
            size=max_row_size([text_entries['tf']]),
            enable_events=True,
            key=KEY_IMAGING_FREQ + KEY_T,
            visible=False
        ),
        Sg.Combo([],
                 size=(16, 1),
                 key=KEY_IMAGING_FREQ,
                 visible=False)
    ]
    #
    # Order Instructions
    special_instructions = []
    treatment_instructions = []
    instruction_size = max_row_size([inst['text'] for inst in instructions])
    for inst in instructions:
        row = None
        inst_text = inst['text']
        if inst['radio']:
            row = [
                Sg.T(
                    inst_text,
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_tuple_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
                    visible=False, ),
                *create_radio_buttons(inst['radio'],
                                      KEY_TX_INST + inst_text, inst['indx'])
            ]
        elif inst['comment']:
            row = [
                Sg.T(
                    inst_text,
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_tuple_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
                    visible=False, ),
                Sg.InputText(
                    "Notes",
                    size=(20, 1),
                    enable_events=True,
                    key=create_tuple_key(KEY_TX_INST + inst_text + KEY_INPUT_TEXT, inst['indx']),
                    visible=False,
                )
            ]
        elif inst['combo']:
            phrases = inst['combo'].split(',')
            row = [
                Sg.T(
                    inst_text,
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_tuple_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
                    visible=False, ),
                Sg.Combo(
                    phrases,
                    default_value='',
                    size=max_row_size(phrases),
                    tooltip='Select Appropriate Instruction',
                    enable_events=True,
                    key=create_tuple_key(KEY_TX_INST + inst_text + KEY_COMBO, inst['indx']),
                    visible=False
                )
            ]
        if inst['type'] == 'Special Instructions':
            special_instructions.append(row)
        elif inst['type'] == "Treatment Instructions":
            treatment_instructions.append(row)

        # Build layout
    layout = [site_combo, protocol_combo, order_combo, tf_combo, if_combo]
    layout.extend(special_instructions)
    layout.extend(treatment_instructions)
    return layout


def update_preplan_frequencies(window, protocol, order_name):
    frequencies = get_frequencies(protocol, order_name)

    if frequencies:
        window[KEY_TREAT_FREQ + KEY_T].update(visible=True)
        window[KEY_TREAT_FREQ].update(
            values=frequencies[KEY_TREAT_FREQ + KEY_O],
            set_to_index=frequencies[KEY_TREAT_FREQ + KEY_O].index(
                frequencies[KEY_TREAT_FREQ + KEY_D])
            if frequencies[KEY_TREAT_FREQ + KEY_D] in
               frequencies[KEY_TREAT_FREQ + KEY_O]
            else None,
            visible=True)
        window[KEY_IMAGING_FREQ + KEY_T].update(visible=True)
        window[KEY_IMAGING_FREQ].update(
            values=frequencies[KEY_IMAGING_FREQ + KEY_O],
            set_to_index=frequencies[KEY_IMAGING_FREQ + KEY_O].index(
                frequencies[KEY_IMAGING_FREQ + KEY_D])
            if frequencies[KEY_IMAGING_FREQ + KEY_D]
               in frequencies[KEY_IMAGING_FREQ + KEY_O]
            else None,
            visible=True)
    else:
        window[KEY_IMAGING_FREQ + KEY_T].update(visible=False)
        window[KEY_TREAT_FREQ + KEY_T].update(visible=False)
        window[KEY_TREAT_FREQ].update(values=[], visible=False)
        window[KEY_IMAGING_FREQ].update(values=[], visible=False)


def get_instruction(inst, instructions):
    for i in instructions:
        tests = [inst[key] == i[key] for key in inst.keys()]
        if all(tests):
            return i
    sys.exit('No matching instruction found. Order outside protocols?')


def update_preplan_instructions(main_window, protocol, order_name, instructions):
    # Turn on the order instructions that match those in this order
    order_instructions = get_order_instructions(protocol, order_name)

    # Turn all instructions off
    for mw_key in main_window.key_dict:
        if type(mw_key) is tuple:
            if KEY_TX_INST in mw_key[0]:
                main_window[mw_key].update(visible=False)

    # Turn on instructions specific to this order
    for o_i in order_instructions:
        # Find the indx of this instruction
        inst = get_instruction(o_i, instructions)
        for mw_key in main_window.key_dict:
            if type(mw_key) is tuple:
                if len(mw_key) > 1:
                    if inst['indx'] == mw_key[1] and KEY_TX_INST in mw_key[0]:
                        main_window[mw_key].update(visible=True)


def update_preplan_protocols(window, site_name, protocol_event, protocols):
    options = list(site_protocol_list(protocols, site_name).keys())
    window[protocol_event].update(value='', values=options)
    window[KEY_PROTOCOL_SELECT + KEY_T].update(visible=True)
    window[KEY_PROTOCOL_SELECT].update(visible=True)


def update_preplan_orders(window, protocol, order_event):
    options = list(order_dict(protocol).keys())
    window[order_event].update(value='',
                               values=options,
                               size=max_visible_count(options))
    window[KEY_ORDER_SELECT + KEY_T].update(visible=True)
    window[KEY_ORDER_SELECT].update(visible=True)


def update_plan_names(window, plan_name_event, plan_name_dict, current_plan_name):
    if not current_plan_name:
        current_plan_name = 'Select Plan Abbreviation'
    plan_names = []
    for k, v in plan_name_dict.items():
        plan_names.append(v)
    window[plan_name_event].update(value=current_plan_name, values=plan_names)


def create_tab_preplan_information(protocols, sites, orders,
                                   instructions, beamsets, targets,
                                   tab_width, tab_height, save_space=False,
                                   review_type='Physics'):
    """
    Create the layout for the CT Scan tab in the main window.

    Parameters:
    beamsets (list): A list of available beamsets.
    targets (list): A list of available targets.
    """

    def create_space():
        return [Sg.Text('', size=(5, 1))] if not save_space else []

    if review_type.lower() == 'dosimetry':
        include_site_billing = True
    else:
        include_site_billing = False
    print(f'Include Site Billing: {include_site_billing}')
    maximum_beamset_count = len(beamsets)
    # Create the layout for the beamset information section
    beamset_layout = create_beamset_layout(beamsets, targets, include_site_billing)
    # Create the layout for treatment planning order selection
    order_selection_layout = create_order_selection_layout(protocols, sites,
                                                           orders, instructions)
    frame_x = int(0.985 * tab_width) if save_space else tab_width
    frame_ct_y = int(tab_height * 0.18) if save_space else int(tab_height * 0.20)
    frame_tpo_y = int(0.42 * tab_height) if save_space else int(tab_height * 0.42)
    frame_bs_y = int(tab_height - frame_ct_y - frame_tpo_y)
    column_x = int(frame_x * 0.95)
    vertical_scroll = False if save_space else True
    scroll_for_small = True if save_space else False
    # Create the overall layout for the CT Scan tab
    ct_scan_layout = [
        # CT Information frame
        [Sg.Frame('ARIA CT Simulation Form ',
                  [
                      [Sg.Column([[Sg.Text('CT Scan Date:', pad=(20, 0)),
                                   Sg.Input('', key=KEY_SIM_DATE,
                                            size=(10, 1)),
                                   Sg.CalendarButton('Select date', target=KEY_SIM_DATE,
                                                     ## QT format='%Y-%m-%d'
                                                     )],
                                  [Sg.Text('Number of CT Slices: ', pad=(20, 0)),
                                   Sg.Input(key=KEY_SLICES, size=(10, 1))],
                                  [Sg.Text('Patient Orientation: ', pad=(20, 0)),
                                   Sg.Combo(list(PATIENT_ORIENTATIONS.keys()),
                                            default_value=None, key=KEY_PATIENT_ORIENTATION), ],
                                  [Sg.Text('Implanted Medical Device Present: ', pad=(20, 0)),
                                   Sg.Radio('Yes',
                                            group_id=KEY_IMD + KEY_RADIO,
                                            key=KEY_IMD + KEY_RADIO + '-YES'),
                                   Sg.Radio('No',
                                            group_id=KEY_IMD + KEY_RADIO,
                                            key=KEY_IMD + KEY_RADIO + '-NO')],
                                  [Sg.Text('History of Prior Radiotherapy: ', pad=(20, 0)),
                                   Sg.Radio('Yes',
                                            group_id=KEY_PRIOR_RT + KEY_RADIO,
                                            key=KEY_PRIOR_RT + KEY_RADIO + '-YES'),
                                   Sg.Radio('No',
                                            group_id=KEY_PRIOR_RT + KEY_RADIO,
                                            key=KEY_PRIOR_RT + KEY_RADIO + '-NO')],
                                  ],
                                 scrollable=scroll_for_small,
                                 vertical_scroll_only=True,
                                 size=(frame_x, frame_ct_y))],
                  ],
                  element_justification='l',
                  size=(frame_x, frame_ct_y),
                  font=('Helvetica', 11, 'bold'))
         ],

        # Treatment Instructions frame
        [Sg.Frame('ARIA Treatment Planning Order Information',
                  [
                      [Sg.Column(order_selection_layout,
                                 scrollable=True,
                                 vertical_scroll_only=True,
                                 key=KEY_ORDER_SELECT,
                                 size=(frame_x, frame_tpo_y))]],
                  font=('Helvetica', 11, 'bold'),
                  element_justification='l',
                  size=(frame_x, frame_tpo_y),
                  )
         ],

        # Beamset Information frame
        [Sg.Frame('Beamset Information',
                  [[Sg.Column([[Sg.Text('Number of BeamSets: '),
                                Sg.Combo(list(range(1, maximum_beamset_count + 1)),
                                         key=KEY_BEAMSET_COUNT,
                                         default_value=1,
                                         size=(8, 1),
                                         enable_events=True)
                                ],
                               *beamset_layout,
                               ],
                              size=(column_x, int(0.95 * frame_bs_y)),
                              key='-COLUMN_BEAMSETS-',
                              scrollable=True,
                              ## Qt vertical_scroll_only=vertical_scroll,
                              )]],
                  size=(frame_x, frame_bs_y),
                  font=('Helvetica', 11, 'bold'),
                  element_justification='l')],

    ]

    # Add a submit button column on the right
    ct_scan_layout_with_submit = [[Sg.Column(ct_scan_layout,
                                             element_justification='l',
                                             pad=(10, 0)),
                                   ]]

    return ct_scan_layout_with_submit


def validate_aria_information(window, preplan_dict):
    # CT slice information is required
    slices = preplan_dict[KEY_SIMULATION_DATA][KEY_SLICES]
    if not slices:
        popup_message = 'Select number of slices in planning scan'
        return False, popup_message
    # A CT scan date is required
    date = preplan_dict[KEY_SIMULATION_DATA][KEY_SIM_DATE]
    if not date:
        popup_message = 'Select Scan Date'
        return False, popup_message
    # Pacemaker/ICD information is required
    if not (window[KEY_IMD + KEY_RADIO + '-YES'].get() or
            window[KEY_IMD + KEY_RADIO + '-NO'].get()):
        popup_message = 'Please select if an Implanted Medical Device is present'
        return False, popup_message
    # Prior RT is required
    if not (window[KEY_PRIOR_RT + KEY_RADIO + '-YES'].get() or
            window[KEY_PRIOR_RT + KEY_RADIO + '-NO'].get()):
        popup_message = 'Please select if there is a History of Prior Radiotherapy'
        return False, popup_message
    return True, ''


def validate_beamset_information(preplan_dict):
    popup_message = ''
    # Determine the number of beamsets
    if preplan_dict.get(KEY_BEAMSET, {}).get(KEY_BEAMSET_COUNT) is None:
        popup_message += 'Number of beamsets needed to proceed.\n'
        num_beamsets = 0
    else:
        logging.debug(f'Keys in use prior to fail: KEY_BEAMSET {KEY_BEAMSET}, '
                      f'KEY_BEAMSET_COUNT {KEY_BEAMSET_COUNT}: value in preplan'
                      f' {preplan_dict[KEY_BEAMSET][KEY_BEAMSET_COUNT]}')
        num_beamsets = int(preplan_dict[KEY_BEAMSET][KEY_BEAMSET_COUNT])
    # Beamset information is required
    for i in range(num_beamsets):
        beamset_message = ''
        beamset_key = create_tuple_key(KEY_BEAMSET_SELECT, i)
        beamset_name = preplan_dict.get(KEY_BEAMSET, {}).get(beamset_key, None)
        if beamset_name is None or beamset_name == '':
            beamset_message += f'\t Beamset {i + 1} name required.\n'
        # Number of fractions for each beamset is required
        fractions_key = create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i)
        n_fractions = preplan_dict[KEY_BEAMSET].get(fractions_key, 0)
        if n_fractions <= 0:
            beamset_message += f'\t Nonzero fractions are required for beamset {i + 1}.\n'
        # Number of targets for each beamset is required
        target_key = create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)
        n_targets = preplan_dict.get(KEY_BEAMSET, {}).get(target_key, 0)
        if n_targets is None or n_targets <= 0:
            beamset_message += f'\t Number of targets required for beamset {i + 1}.\n'
        if beamset_message != '':
            popup_message += f'Beamset {i + 1}:\n' + beamset_message
        # Target information is required
        for j in range(n_targets):
            target_message = ''
            target_name_key = create_tuple_key(KEY_BEAMSET_TARGET_NAME, i, j)
            target_name = preplan_dict.get(KEY_BEAMSET, {}).get(target_name_key, None)
            if target_name is None:
                target_message += f'\t\t missing target name for target {j + 1}.\n'
            target_dose_key = create_tuple_key(KEY_BEAMSET_DOSE, i, j)
            target_dose = preplan_dict.get(KEY_BEAMSET, {}).get(target_dose_key, None)
            if target_dose is None:
                target_message += f'\t\t missing target dose for target {j + 1}.\n'
            if target_message:
                popup_message += f'\t All target information required for beamset {i + 1}:\n' + target_message
    if popup_message:
        return False, popup_message
    else:
        return True, ''


def log_window_contents(window, max_length=16):
    log_message = 'Window Contents:\n'
    event, values = window.read()
    for key, value in values.items():
        value_str = str(value)
        if len(value_str) > max_length:
            value_str = value_str[:max_length] + '...'
        log_message += f'{key}: {value_str}\n'
    logging.info(log_message)


def validate_preplan_tab(window):
    """
    Validate the information entered into the ARIA Information tab.

    Required data includes:
    ARIA CT SIMULATION FORM:
        - CT scan date
        - CT scan slices
        - Patient orientation
        - Implanted medical device indication
        - History of prior radiotherapy indication
    BEAMSET INFORMATION:
        - Number of beamsets
        FOR EACH BEAMSET:
            - Number of fractions
            - Beamset names
            - Number of targets
            - Target names
            - Total dose for each target

    Args:
        window: The main PySimpleGUI window object.

    Returns: True if the information is valid, False otherwise.
    """
    error_message = ''
    # Extract the values from the window
    preplan_dict = extract_values_preplan_tab(window)
    # Validate the ARIA Information tab
    valid_aria, aria_message = validate_aria_information(window, preplan_dict)
    # Validate the Beamset Information tab
    valid_beamset, beamset_message = validate_beamset_information(preplan_dict)
    if not valid_aria or not valid_beamset:
        error_message += aria_message + beamset_message
        return False, error_message
    else:
        return True, None


def update_preplan_gui_state(gui_state_manager, values):
    # Update the beamset information
    number_of_beamsets_picked = gui_state_manager.window[KEY_BEAMSET_COUNT].get() \
        if gui_state_manager.window[KEY_BEAMSET_COUNT].get() else None
    if number_of_beamsets_picked is None:
        logging.warning('During preplan gui state update Number of beamsets not selected.')
    gui_state_manager.beamset_number_choice = number_of_beamsets_picked
    # Update the beamset names
    gui_state_manager.beamset_names = []
    for i in range(number_of_beamsets_picked):
        beamset_name = gui_state_manager.window[create_tuple_key(KEY_BEAMSET_SELECT, i)].get()
        if beamset_name == '':
            continue
        if beamset_name not in gui_state_manager.beamset_names:
            gui_state_manager.beamset_names.append(beamset_name)
        # Update Dosimetry Site and Billing Information
        if gui_state_manager.review_type == 'Dosimetry':
            secondary_update_site_technique(gui_state_manager.window,
                                            gui_state_manager.rso,
                                            beamset_name, i)


def get_value_from_window(main_window, key):
    """Check if the key is in the window and return its value if present.

    Args:
        main_window (Sg.Window): The main PySimpleGUI window object.
        key: The key to check in the window.

    Returns:
        tuple: (bool, value) where the bool indicates if the key is present,
               and the value is the value associated with the key or None.
    """
    if key in main_window.key_dict:
        value = main_window[key].get()
        if value:
            return True, value
        return True, None
    return False, None


def extract_values_preplan_tab(main_window):
    """
    Extract the values from the PySimpleGUI window and return them in a dictionary.

    Parameters:
    main_window (Sg.Window): The main PySimpleGUI window object.

    Returns:
    dict: A dictionary containing the values of the input fields.
    """
    simulation_dict = {}

    keys_to_extract = [
        KEY_SIM_DATE, KEY_SLICES, KEY_PATIENT_ORIENTATION,
        KEY_IMD + KEY_RADIO + '-YES',
        KEY_PRIOR_RT + KEY_RADIO + '-YES',
        KEY_SITE_SELECT, KEY_PROTOCOL_SELECT, KEY_ORDER_SELECT,
        KEY_IMAGING_FREQ, KEY_TREAT_FREQ
    ]

    for key in keys_to_extract:
        present, value = get_value_from_window(main_window, key)
        if present:
            simulation_dict[key] = value if value else ''

    # Capture the selected radio buttons, comboboxes, and text inputs
    treatment_instructions = {}
    for key, element in main_window.key_dict.items():
        if isinstance(key, tuple) and len(key) == 2:
            instruction_key, instruction_idx = key
            if KEY_TX_INST in instruction_key:
                present, instruction_value = get_value_from_window(main_window, key)
                if present:
                    treatment_instructions[key] = instruction_value if instruction_value else ''

    # Get the Beamset Information values
    beamset_dict = {}
    present, value = get_value_from_window(main_window, KEY_BEAMSET_COUNT)
    num_beamsets = int(value) if present and value else 1
    beamset_dict[KEY_BEAMSET_COUNT] = value if present and value else ''

    for i in range(num_beamsets):
        beamset_keys = [
            create_tuple_key(KEY_BEAMSET_SELECT, i),
            create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i),
            create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i),
            create_tuple_key(KEY_DOSE_SITE, i),
            create_tuple_key(KEY_DOSE_BILL, i)
        ]

        for beamset_key in beamset_keys:
            present, value = get_value_from_window(main_window, beamset_key)
            if present:
                if KEY_FRACTIONS in beamset_key[0]:
                    beamset_dict[beamset_key] = int(value) if value else 0
                else:
                    beamset_dict[beamset_key] = value if value else ''

        # If the target count has not been selected, it will not be an integer, return 0
        if not isinstance(beamset_dict[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)], int):
            num_targets = 0
        else:
            num_targets = beamset_dict.get(create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i), 0)

        for j in range(num_targets):
            for key in [KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE, KEY_BEAMSET_FRACTION_DOSE]:
                window_key = create_tuple_key(key, i, j)
                present, value = get_value_from_window(main_window, window_key)
                if present:
                    beamset_dict[window_key] = value if value else ''

    values_dict = {
        KEY_SIMULATION_DATA: simulation_dict,
        KEY_TX_INST_SET: treatment_instructions,
        KEY_BEAMSET: beamset_dict,
    }

    return values_dict


def old_extract_values_preplan_tab(main_window):
    """
    Extract the values from the PySimpleGUI window and return them in a dictionary.

    Parameters:
    main_window (Sg.Window): The main PySimpleGUI window object.

    Returns:
    dict: A dictionary containing the values of the input fields.
    """
    simulation_dict = {
        # Get the CT Information values
        KEY_SIM_DATE:
            main_window[KEY_SIM_DATE].get()
            if main_window[KEY_SIM_DATE].get() else '',
        KEY_SLICES:
            main_window[KEY_SLICES].get()
            if main_window[KEY_SLICES].get() else '',
        KEY_PATIENT_ORIENTATION:
            main_window[KEY_PATIENT_ORIENTATION].get()
            if main_window[KEY_PATIENT_ORIENTATION].get() else '',
        KEY_IMD:
            main_window[KEY_IMD + KEY_RADIO + '-YES'].get()
            if main_window[KEY_IMD + KEY_RADIO + '-YES'].get else '',
        KEY_PRIOR_RT:
            main_window[KEY_PRIOR_RT + KEY_RADIO + '-YES'].get()
            if main_window[KEY_PRIOR_RT + KEY_RADIO + '-YES'].get else '',
        # Get the Treatment Instructions values
        KEY_SITE_SELECT:
            main_window[KEY_SITE_SELECT].get()
            if main_window[KEY_SITE_SELECT].get() else '',
        KEY_PROTOCOL_SELECT:
            main_window[KEY_PROTOCOL_SELECT].get()
            if main_window[KEY_PROTOCOL_SELECT].get() else '',
        KEY_ORDER_SELECT:
            main_window[KEY_ORDER_SELECT].get()
            if main_window[KEY_ORDER_SELECT].get() else '',
        KEY_IMAGING_FREQ:
            main_window[KEY_IMAGING_FREQ].get()
            if main_window[KEY_IMAGING_FREQ].get() else '',
        KEY_TREAT_FREQ:
            main_window[KEY_TREAT_FREQ].get()
            if main_window[KEY_TREAT_FREQ].get() else '',
    }

    # Capture the selected radio buttons, comboboxes, and text inputs
    treatment_instructions = {}
    for key, value in main_window.key_dict.items():
        if isinstance(key, tuple) and len(key) == 2:
            instruction_key, instruction_idx = key
            if KEY_TX_INST in instruction_key:
                instruction_element = main_window[key]
                if isinstance(instruction_element, Sg.Input):
                    treatment_instructions[key] = value.get()
                elif isinstance(instruction_element, Sg.Combo):
                    treatment_instructions[key] = value.get()
                elif isinstance(instruction_element, Sg.Radio):
                    treatment_instructions[key] = value.get()

    # Get the Beamset Information values
    num_beamsets = main_window[KEY_BEAMSET_COUNT].get() \
        if main_window[KEY_BEAMSET_COUNT].get() else 1
    beamset_dict = {
        KEY_BEAMSET_COUNT: main_window[KEY_BEAMSET_COUNT].get()
        if main_window[KEY_BEAMSET_COUNT].get() else ''}
    for i in range(num_beamsets):
        beamset_dict[create_tuple_key(KEY_BEAMSET_SELECT, i)] = \
            main_window[create_tuple_key(KEY_BEAMSET_SELECT, i)].get() \
                if main_window[create_tuple_key(KEY_BEAMSET_SELECT, i)].get() \
                else ''
        beamset_dict[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i)] = \
            int(main_window[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i)].get()) \
                if main_window[create_tuple_key(KEY_BEAMSET + KEY_FRACTIONS, i)].get() \
                else -1
        num_targets = \
            int(main_window[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)].get()
                ) \
                if main_window[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)].get() \
                else -1
        beamset_dict[create_tuple_key(KEY_BEAMSET_TARGET_COUNT, i)] = \
            num_targets
        beamset_dict[create_tuple_key(KEY_DOSE_SITE, i)] = \
            main_window[create_tuple_key(KEY_DOSE_SITE, i)].get() \
                if main_window[create_tuple_key(KEY_DOSE_SITE, i)].get() \
                else ''
        beamset_dict[create_tuple_key(KEY_DOSE_BILL, i)] = \
            main_window[create_tuple_key(KEY_DOSE_BILL, i)].get() \
                if main_window[create_tuple_key(KEY_DOSE_BILL, i)].get() \
                else ''
        for j in range(num_targets):  # assuming num_targets is defined somewhere
            for key in [KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE, KEY_BEAMSET_FRACTION_DOSE]:
                window_key = create_tuple_key(key, i, j)
                if main_window[window_key].get():
                    beamset_dict[window_key] = main_window[window_key].get()
    values_dict = {
        KEY_SIMULATION_DATA: simulation_dict,
        KEY_TX_INST_SET: treatment_instructions,
        KEY_BEAMSET: beamset_dict,
    }

    return values_dict


def tuple_key_to_str(value):
    if isinstance(value, dict):
        return {tuple_key_to_str(k): tuple_key_to_str(v) for k, v in value.items()}
    elif isinstance(value, tuple):
        return '||'.join(map(str, value))
    return value


def load_preplan(window, values, sites, protocols, instructions,
                 maximum_beamset_count, maximum_target_number, rso, review_type='Physics'):
    order_name = None
    protocol = None

    simulation_data = values.get(KEY_SIMULATION_DATA, {})
    for key, value in simulation_data.items():
        if key == KEY_SITE_SELECT:
            site_name = value
            window[KEY_SITE_SELECT].update(values=sites,
                                           value=site_name)
            update_preplan_protocols(window, site_name, KEY_PROTOCOL_SELECT, protocols)
        elif key == KEY_PROTOCOL_SELECT and value:
            window[KEY_PROTOCOL_SELECT].update(value=value)
            protocol = protocols[value]
            update_preplan_orders(window, protocol, KEY_ORDER_SELECT)
        elif key == KEY_ORDER_SELECT and value:
            window[KEY_ORDER_SELECT].update(value=value)
            protocol = protocols[values[KEY_SIMULATION_DATA][KEY_PROTOCOL_SELECT]]
            order_name = value
            update_preplan_frequencies(window, protocol, order_name)
            update_preplan_instructions(window, protocol, order_name, instructions)
            continue
        # Handle the radio button for Implanted Medical Devices
        elif key == KEY_IMD + KEY_RADIO + '-YES':
            window[KEY_IMD + KEY_RADIO + '-YES'].update(value=value)
            window[KEY_IMD + KEY_RADIO + '-NO'].update(value=not value)
        # Handle the radio button for History of Prior Radiotherapy
        elif key == KEY_PRIOR_RT + KEY_RADIO + '-YES':
            window[KEY_PRIOR_RT + KEY_RADIO + '-YES'].update(value=value)
            window[KEY_PRIOR_RT + KEY_RADIO + '-NO'].update(value=not value)
        else:
            if key in window.key_dict:
                window[key].update(value=value)
            else:
                logging.warning(f'Key {key} not found in window')
                continue

    # Handle the radio keys and other elements in the Treatment Planning Order Information frame
    treatment_instructions = values.get(KEY_TX_INST_SET, {})
    for key, value in treatment_instructions.items():
        try:
            if key in window.key_dict:
                window[key].update(value=value)
            else:
                # If an xml protocol is changed, then the instruction number may be different
                # The key is a tuple, so see if there is a match on the first element in keys
                # then match to whatever second element is in the tuple
                for k in window.key_dict:
                    if type(k) is tuple:
                        if k[0] == key[0]:
                            window[k].update(value=value)
                            break
        except KeyError:
            logging.warning(f'Key {key} not found in window')
            continue
    if order_name and protocol:
        update_preplan_instructions(window, protocol, order_name, instructions)
    #
    beamset_data = values.get(KEY_BEAMSET, {})
    for key, value in beamset_data.items():
        if key in window.key_dict:
            window[key].update(value=value)
        else:
            logging.warning(f'During load, key {key} not found in window')
    num_beamsets = beamset_data.get(KEY_BEAMSET_COUNT, None)
    if num_beamsets:
        flattened_values = {k: v for inner_dict in values.values()
                            for k, v in inner_dict.items()}
        update_preplan_beamset_rows(window, flattened_values, num_beamsets,
                                    maximum_beamset_count, maximum_target_number, review_type)
        if review_type == 'Dosimetry':
            for i in range(num_beamsets):
                # See if the beamset names have already been loaded then try to load dosimetry
                # data
                beamset_name = beamset_data.get(create_tuple_key(KEY_BEAMSET_SELECT, i), None)
                if beamset_name:
                    secondary_update_site_technique(window, rso, beamset_name, i)
                    # If there was already site and technique selections load them
                    window[create_tuple_key(KEY_DOSE_SITE, i)].update(
                        value=beamset_data.get(create_tuple_key(KEY_DOSE_SITE, i), ''))
                    window[create_tuple_key(KEY_DOSE_BILL, i)].update(
                        value=beamset_data.get(create_tuple_key(KEY_DOSE_BILL, i), ''))


def secondary_update_site_technique(window, rso, beamset_name, index):
    technique, modality = get_technique_and_modality(beamset_name, rso)
    if not modality or not technique:
        logging.warning(f'No modality {modality} or technique {technique} found for beamset {beamset_name}')
        Sg.popup('No modality or technique found for beamset')
        return
    update_billing_combo(window, create_tuple_key(KEY_DOSE_BILL, index), technique, modality)
    update_site_input(window, create_tuple_key(KEY_DOSE_SITE, index), beamset_name)


def get_technique_and_modality(beamset_name, rso):
    for beamset in rso.plan.BeamSets:
        if beamset.DicomPlanLabel == beamset_name:
            technique = beamset.DeliveryTechnique
            modality = beamset.Modality
            return technique, modality
    return None, None


def find_site_technique_from_beamset_name(beamset_name, num_beamsets, main_window):
    """
    Find the site and technique associated with a beamset name.
    Args:
        beamset_name: The name of the beamset.
        num_beamsets: The number of beamsets.
        main_window: The main PySimpleGUI window object.

    Returns:
        str: The site associated with the beamset name.
        str: The technique associated with the beamset name.
    """

    for i in range(num_beamsets):
        beamset_select_key = create_tuple_key(KEY_BEAMSET_SELECT, i)
        dose_site_key = create_tuple_key(KEY_DOSE_SITE, i)
        dose_bill_key = create_tuple_key(KEY_DOSE_BILL, i)

        beamset_select_value = main_window[beamset_select_key].get() \
            if main_window[beamset_select_key].get() else ''
        if beamset_select_value == beamset_name:
            dose_site_value = main_window[dose_site_key].get() \
                if main_window[dose_site_key].get() else ''
            dose_bill_value = main_window[dose_bill_key].get() \
                if main_window[dose_bill_key].get() else ''
            return dose_site_value, dose_bill_value
    return None, None
