"""
Create the information entry prompt for the dose and physics review
"""

import PySimpleGUI as Sg
import sys
import logging
from PlanReview.utils.protocol_loading import get_order_instructions, \
    site_protocol_list, order_dict, load_plan_names, get_frequencies
from PlanReview.utils.constants import *
from PlanReview.review_definitions import PROTOCOL_DIR, PATIENT_ORIENTATIONS


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


def create_beamset_layout(beamsets, targets):
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
        single_beamset_layout = [
            [Sg.Text(f'Beamset {i + 1} Name',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET_COUNT + KEY_T, i)),
             Sg.Combo(values=beamsets, key=create_key(KEY_BEAMSET_SELECT, i),
                      visible=bs_visible, size=(header_sizes[0], 1))],
            [Sg.Text(f'Number of targets in Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)),
             Sg.Combo(values=list(range(1, max_targets + 1)),
                      key=create_key(KEY_BEAMSET_TARGET_COUNT, i),
                      visible=bs_visible,
                      size=(header_sizes[1], 1),
                      enable_events=True)],
            [Sg.Text(f'Number of fractions in Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)),
             Sg.Input(key=create_key(KEY_BEAMSET + KEY_FRACTIONS, i),
                      visible=bs_visible, size=(header_sizes[2], 1),
                      enable_events=True), ]
        ]
        # Add target layout to the beamset layout
        single_beamset_layout.extend(create_target_layout(i, targets))
        row_pair.append(Sg.Frame(f'Beamset {i + 1}',
                                 single_beamset_layout,
                                 key=create_key(KEY_BEAMSET + KEY_F, i),
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


def update_preplan_beamset_rows(main_window, values, num_beamsets, max_beamsets, max_targets):
    """
    Updates the visibility of beamset rows in the GUI based on the user's selection.

    Args:
        main_window (Sg.Window): The main PySimpleGUI window.
        values (dict): The dictionary containing the current values of the window elements.
        num_beamsets (int): The number of beamsets selected by the user.
        max_beamsets (int): The maximum number of beamsets in the plan.
        max_targets (int): The maximum number of targets in the plan.

    """
    # Update the visibility of target rows based on the user's selection of the number of targets
    # in each beamset
    for beamset_index in range(num_beamsets):
        num_targets_value = values[create_key(KEY_BEAMSET_TARGET_COUNT, beamset_index)]
        if num_targets_value:
            num_targets = int(num_targets_value)
            update_preplan_target_rows(main_window, num_targets, beamset_index, max_targets)

    # Update the visibility of beamset rows based on the user's selection
    for i in range(max_beamsets):
        is_visible = i < num_beamsets
        main_window[create_key(KEY_BEAMSET + KEY_F, i)].update(
            visible=is_visible)  # Update the visibility of the frame
        main_window[create_key(KEY_BEAMSET_COUNT + KEY_T, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_SELECT, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_TARGET_COUNT, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS, i)].update(visible=is_visible)
    main_window.refresh()
    main_window['-COLUMN_BEAMSETS-'].contents_changed()


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
                    key=create_key('beamset_header', beamset_i, 0), visible=False),
            Sg.Text(header_texts[1], size=(header_sizes[1], 1),
                    key=create_key('beamset_header', beamset_i, 1), visible=False),
            Sg.Text(header_texts[2], size=(header_sizes[2], 1),
                    key=create_key('beamset_header', beamset_i, 2), visible=False),
        ]
    ]

    for i in range(max_targets):
        target_layout.append([
            Sg.Text(f'Target {i + 1}: ', visible=False,
                    key=create_key(KEY_BEAMSET_TARGET_NAME + KEY_T, beamset_i, i)),
            Sg.Combo(values=target_combo_values,
                     key=create_key(KEY_BEAMSET_TARGET_NAME, beamset_i, i),
                     visible=False,
                     size=(header_sizes[0], 1)),
            Sg.Input(key=create_key(KEY_BEAMSET_DOSE, beamset_i, i), visible=False,
                     size=(header_sizes[1], 1),
                     justification='c',
                     enable_events=True),
            Sg.Text('', key=create_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i),
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
        main_window[create_key(KEY_BEAMSET_TARGET_NAME + KEY_T, beamset_i, i)].update(
            visible=is_visible)
        main_window[create_key(KEY_BEAMSET_TARGET_NAME, beamset_i, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_DOSE, beamset_i, i)].update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i)].update(
            visible=is_visible)

    # Update the visibility of header texts
    for i in range(3):
        main_window[create_key('beamset_header', beamset_i, i)].update(
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
        num_targets = values[create_key(KEY_BEAMSET_TARGET_COUNT, beamset_i)]
        if num_targets:
            for i in range(int(num_targets)):
                total_dose = values[create_key(KEY_BEAMSET_DOSE, beamset_i, i)]
                num_fractions = values[create_key(KEY_BEAMSET + KEY_FRACTIONS, beamset_i)]
                if num_fractions and total_dose:
                    dose_per_fraction = calculate_single_dose_per_fraction(total_dose,
                                                                           num_fractions)
                    if dose_per_fraction:
                        main_window[create_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i)].update(
                            dose_per_fraction)
    else:
        total_dose = values[create_key(KEY_BEAMSET_DOSE, beamset_i, target_i)]
        num_fractions = values[create_key(KEY_BEAMSET + KEY_FRACTIONS, beamset_i)]
        if total_dose and num_fractions:
            dose_per_fraction = calculate_single_dose_per_fraction(total_dose, num_fractions)
            if dose_per_fraction:
                main_window[create_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, target_i)].update(
                    dose_per_fraction)


def create_radio_buttons(radio_phrases, text, indx):
    phrases = radio_phrases.split(',')
    radio_buttons = [Sg.Radio(text=phrase,
                              group_id=create_key(text + KEY_RADIO, indx),
                              key=create_key(text + KEY_RADIO + phrase, indx),
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
                    key=create_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
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
                    key=create_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
                    visible=False, ),
                Sg.InputText(
                    "Notes",
                    size=(20, 1),
                    enable_events=True,
                    key=create_key(KEY_TX_INST + inst_text + KEY_INPUT_TEXT, inst['indx']),
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
                    key=create_key(KEY_TX_INST + KEY_T + inst_text, inst['indx']),
                    visible=False, ),
                Sg.Combo(
                    phrases,
                    default_value='',
                    size=max_row_size(phrases),
                    tooltip='Select Appropriate Instruction',
                    enable_events=True,
                    key=create_key(KEY_TX_INST + inst_text + KEY_COMBO, inst['indx']),
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
                                   tab_width, tab_height, save_space=False):
    """
    Create the layout for the CT Scan tab in the main window.

    Parameters:
    beamsets (list): A list of available beamsets.
    targets (list): A list of available targets.
    """

    def create_space():
        return [Sg.Text('', size=(5, 1))] if not save_space else []

    maximum_beamset_count = len(beamsets)
    # Create the layout for the beamset information section
    beamset_layout = create_beamset_layout(beamsets, targets)
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
                                            create_key(KEY_IMD+KEY_RADIO),
                                            key=create_key(KEY_IMD+KEY_RADIO+'-YES')),
                                   Sg.Radio('No',
                                            create_key(KEY_IMD+KEY_RADIO),
                                            key=create_key(KEY_IMD+KEY_RADIO+'-NO'))],
                                  [Sg.Text('History of Prior Radiotherapy: ', pad=(20, 0)),
                                   Sg.Radio('Yes',
                                            create_key(KEY_PRIOR_RT+KEY_RADIO),
                                            key=create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES')),
                                   Sg.Radio('No',
                                            create_key(KEY_PRIOR_RT+KEY_RADIO),
                                            key=create_key(KEY_PRIOR_RT+KEY_RADIO+'-NO'))],
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


def validate_preplan_tab(window):
    """
    Validate the information entered in the CT Scan tab.
    Required data includes:
    - Number of beamsets
    - CT scan date
    - CT scan slices
    - Patient orientation
    - Implanted medical device indication
    - History of prior radiotherapy indication

    Args:
        window: The main PySimpleGUI window object.

    Returns: True if the information is valid, False otherwise.
    """
    # Extract the values from the window
    preplan_dict = extract_values_preplan_tab(window)
    # Determine the number of beamsets
    num_beamsets = int(preplan_dict[KEY_BEAMSET][KEY_BEAMSET_COUNT])
    # Beamset information is required
    if not num_beamsets:
        Sg.popup('Number of beamsets needed to proceed')
        return False
    beamsets = [preplan_dict[KEY_BEAMSET][create_key(KEY_BEAMSET_SELECT, i)]
                for i in range(num_beamsets)]
    if not all(beamsets):
        Sg.popup(f'All beamset names required for {num_beamsets} beamsets')
        return False
    # CT slice information is required
    slices = preplan_dict[KEY_SIMULATION_DATA][KEY_SLICES]
    if not slices:
        Sg.popup('Select number of slices in planning scan')
        return False
    # A CT scan date is required
    date = preplan_dict[KEY_SIMULATION_DATA][KEY_SIM_DATE]
    if not date:
        Sg.popup('Select Scan Date')
        return False
    # Pacemaker/ICD information is required
    if not (window[create_key(KEY_IMD+KEY_RADIO+'-YES')].get() or
            window[create_key(KEY_IMD+KEY_RADIO+'-NO')].get()):
        Sg.popup('Please select if an Implanted Medical Device is present')
        return False
    # Prior RT is required
    if not (window[create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES')].get() or
            window[create_key(KEY_PRIOR_RT+KEY_RADIO+'-NO')].get()):
        Sg.popup('Please select if there is a History of Prior Radiotherapy')
        return False
    return True


def extract_values_preplan_tab(main_window):
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
            main_window[create_key(KEY_IMD+KEY_RADIO+'-YES')].get()
            if main_window[create_key(KEY_IMD+KEY_RADIO+'-YES')].get else '',
        KEY_PRIOR_RT:
            main_window[create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES')].get()
            if main_window[create_key(KEY_PRIOR_RT+KEY_RADIO+'-YES')].get else '',
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
    beamset_dict = {KEY_BEAMSET_COUNT: main_window[KEY_BEAMSET_COUNT].get()
    if main_window[KEY_BEAMSET_COUNT].get() else ''}
    for i in range(num_beamsets):
        beamset_dict[create_key(KEY_BEAMSET_SELECT, i)] = \
            main_window[create_key(KEY_BEAMSET_SELECT, i)].get() \
                if main_window[create_key(KEY_BEAMSET_SELECT, i)].get() \
                else ''
        beamset_dict[create_key(KEY_BEAMSET + KEY_FRACTIONS, i)] = \
            int(main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS, i)].get()) \
                if main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS, i)].get() \
                else 0
        num_targets = \
            int(main_window[create_key(KEY_BEAMSET_TARGET_COUNT, i)].get()
                ) \
                if main_window[create_key(KEY_BEAMSET_TARGET_COUNT, i)].get() \
                else 0
        beamset_dict[create_key(KEY_BEAMSET_TARGET_COUNT, i)] = \
            num_targets
        for j in range(num_targets):  # assuming num_targets is defined somewhere
            for key in [KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE, KEY_BEAMSET_FRACTION_DOSE]:
                window_key = create_key(key, i, j)
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
                 maximum_beamset_count, maximum_target_number):
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
        elif key == KEY_IMD:
            window[create_key(KEY_IMD + KEY_RADIO + '-YES')].update(value=value)
            window[create_key(KEY_IMD + KEY_RADIO + '-NO')].update(value=not value)
        # Handle the radio button for History of Prior Radiotherapy
        elif key == KEY_PRIOR_RT:
            window[create_key(KEY_PRIOR_RT + KEY_RADIO + '-YES')].update(value=value)
            window[create_key(KEY_PRIOR_RT + KEY_RADIO + '-NO')].update(value=not value)

        else:
            window[key](value)

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
        window[key].update(value=value)
    num_beamsets = beamset_data.get(KEY_BEAMSET_COUNT, None)
    if num_beamsets:
        flattened_values = {k: v for inner_dict in values.values()
                            for k, v in inner_dict.items()}
        update_preplan_beamset_rows(window, flattened_values, num_beamsets,
                                    maximum_beamset_count, maximum_target_number)
