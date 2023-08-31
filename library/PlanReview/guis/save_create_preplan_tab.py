"""
Create the information entry prompt for the dose and physics review
"""
import PySimpleGUI as sg
import sys
from PlanReview.utils.protocol_loading import get_order_instructions, \
    site_protocol_list, order_dict, load_plan_names, get_frequencies
from PlanReview.utils.constants import *
from PlanReview.review_definitions import PROTOCOL_DIR


def create_key(element_type, beamset_i=None, target_i=None):
    """
    Create a key for a GUI element using a dictionary.

    Parameters:
    element_type (str): The type of the GUI element (e.g., 'beamset_num_text', 'target_name', etc.).
    beamset_i (int, optional): The index of the beamset, if applicable.
    target_i (int, optional): The index of the target, if applicable.

    Returns:
    tuple: A tuple containing the element type and optional beamset/target indices.
    """
    key = (element_type,)
    if beamset_i is not None:
        key += (beamset_i,)
    if target_i is not None:
        key += (target_i,)
    return key


def generate_event_key(*args):
    return "_".join(str(arg) for arg in args)


def create_beamset_layout(beamsets, targets):
    """
    Create the layout for the beamset section.

    Parameters:
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
    header_sizes = [20, 20, 20]

    beamset_layout = []

    # Create layout for each beamset
    for i in range(num_beamsets):
        single_beamset_layout = [
            [sg.Text(f'Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET_COUNT + KEY_T, i)),
             sg.Combo(values=beamsets, key=create_key(KEY_BEAMSET_SELECT, i),
                      visible=bs_visible, size=(header_sizes[0], 1))],
            [sg.Text(f'Number of targets in Beamset {i + 1}',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)),
             sg.Combo(values=list(range(1, max_targets + 1)),
                      key=create_key(KEY_BEAMSET_TARGET_COUNT, i),
                      visible=bs_visible,
                      size=(header_sizes[1], 1),
                      enable_events=True)],
            [sg.Text(f'Number of Fractions',
                     visible=bs_visible,
                     key=create_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)),
             sg.Input(key=create_key(KEY_BEAMSET + KEY_FRACTIONS, i),
                      visible=bs_visible, size=(header_sizes[2], 1),
                      enable_events=True), ]
        ]
        # Add target layout to the beamset layout
        single_beamset_layout.extend(create_target_layout(i, targets))
        beamset_layout.append(sg.Frame(f'Beamset {i + 1}',
                                       single_beamset_layout,
                                       key=create_key(KEY_BEAMSET + KEY_F, i),
                                       font=('Helvetica', 10, 'bold'),
                                       title_color='blue',
                                       visible=bs_visible))

    return beamset_layout


def update_preplan_beamset_rows(main_window, values, num_beamsets, max_beamsets, max_targets):
    """
    Update the visibility of beamset rows based on the user's selection.

    Parameters:
    main_window (Sg.Window): The main PySimpleGUI window.
    values (dict): The dictionary containing the current values of the window elements.
    num_beamsets (int): The number of beamsets selected by the user.
    max_beamsets (int): The maximum number of beamsets in plan
    max_targets (int): The maximum number of targets in plan
    """
    # Update the visibility of target rows based on the user's selection of the number of targets
    # in each beamset
    for beamset_i in range(num_beamsets):
        num_targets_value = values[create_key(KEY_BEAMSET_TARGET_COUNT, beamset_i)]
        if num_targets_value:
            num_targets = int(num_targets_value)
            update_preplan_target_rows(main_window, num_targets, beamset_i, max_targets)

    # Update the visibility of beamset rows based on the user's selection
    for i in range(max_beamsets):
        is_visible = i < num_beamsets
        main_window[create_key(KEY_BEAMSET + KEY_F, i)] \
            .update(visible=is_visible)  # Update the visibility of the frame
        main_window[create_key(KEY_BEAMSET_COUNT + KEY_T, i)] \
            .update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_SELECT, i)] \
            .update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_TARGET_COUNT + KEY_T, i)] \
            .update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET_TARGET_COUNT, i)] \
            .update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS + KEY_T, i)] \
            .update(visible=is_visible)
        main_window[create_key(KEY_BEAMSET + KEY_FRACTIONS, i)] \
            .update(visible=is_visible)


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

    header_texts = ['Target Name', 'Total Dose [Gy]', 'Dose per Fraction [Gy]']
    header_sizes = [max(max_combo_value_length, len(text)) for text in header_texts]

    target_layout = [
        [
            sg.Text('', size=(10, 1)),  # Empty space
            sg.Text(header_texts[0], size=(header_sizes[0], 1),
                    key=create_key('beamset_header', beamset_i, 0), visible=False),
            sg.Text(header_texts[1], size=(header_sizes[1], 1),
                    key=create_key('beamset_header', beamset_i, 1), visible=False),
            sg.Text(header_texts[2], size=(header_sizes[2], 1),
                    key=create_key('beamset_header', beamset_i, 2), visible=False),
        ]
    ]

    for i in range(max_targets):
        target_layout.append([
            sg.Text(f'Target {i + 1}: ', visible=False,
                    key=create_key(KEY_BEAMSET_TARGET_NAME + KEY_T, beamset_i, i)),
            sg.Combo(values=target_combo_values,
                     key=create_key(KEY_BEAMSET_TARGET_NAME, beamset_i, i),
                     visible=False,
                     size=(header_sizes[0], 1)),
            sg.Input(key=create_key(KEY_BEAMSET_DOSE, beamset_i, i), visible=False,
                     size=(header_sizes[1], 1),
                     enable_events=True),
            sg.Text('', key=create_key(KEY_BEAMSET_FRACTION_DOSE, beamset_i, i),
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
    radio_buttons = [sg.Radio(text=phrase,
                              group_id=create_key(text + '-RADIO-', indx),
                              key=create_key(text + '-RADIO-' + phrase, indx),
                              enable_events=True,
                              visible=False)
                     for phrase in phrases]
    return radio_buttons


def max_width(options):
    return max(len(value) for value in options)


def max_row_size(options):
    length = max_width(options)
    additional_chars = 2
    return length + additional_chars, 1


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
        sg.Text(
            text_entries['site'],
            justification=text_just,
            size=max_row_size([text_entries['site']]),
            key=KEY_SITE_SELECT + KEY_T,
        ),
        sg.Combo(
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
        sg.Text(
            text_entries['protocol'],
            justification=text_just,
            size=max_row_size([text_entries['protocol']]),
            enable_events=True,
            key=KEY_PROTOCOL_SELECT + KEY_T,
            visible=False
        ),
        sg.Combo(
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
        sg.Text(
            text_entries['tpo'],
            justification=text_just,
            size=max_row_size([text_entries['tpo']]),
            enable_events=True,
            key=KEY_ORDER_SELECT + KEY_T,
            visible=False
        ),
        sg.Combo(
            orders,
            default_value='',
            size=max_row_size(orders.keys()),
            tooltip='Select Treatment Planning Order',
            enable_events=True,
            key=KEY_ORDER_SELECT,
            visible=False)]
    #
    # Treatment and imaging frequency
    tf_combo = [
        sg.Text(
            text_entries['tf'],
            justification=text_just,
            size=max_row_size([text_entries['tf']]),
            enable_events=True,
            key=KEY_TREAT_FREQ + KEY_T,
            visible=False
        ),
        sg.Combo(
            [],
            key=KEY_TREAT_FREQ,
            size=(16, 1),
            visible=False)
    ]
    if_combo = [
        sg.Text(
            text_entries['sf'],
            justification=text_just,
            size=max_row_size([text_entries['tf']]),
            enable_events=True,
            key=KEY_IMAGING_FREQ + KEY_T,
            visible=False
        ),
        sg.Combo([],
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
        if inst['radio']:
            row = [
                sg.T(
                    inst['text'],
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_key(KEY_TX_INST + KEY_T, inst['indx']),
                    visible=False, ),
                *create_radio_buttons(inst['radio'],
                                      KEY_TX_INST, inst['indx'])
            ]
        elif inst['comment']:
            row = [
                sg.T(
                    inst['text'],
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_key(KEY_TX_INST + KEY_T, inst['indx']),
                    visible=False, ),
                sg.InputText(
                    "Notes",
                    size=(20, 1),
                    enable_events=True,
                    key=create_key(KEY_TX_INST + KEY_INPUT_TEXT, inst['indx']),
                    visible=False,
                )
            ]
        elif inst['combo']:
            phrases = inst['combo'].split(',')
            row = [
                sg.T(
                    inst['text'],
                    justification=text_just,
                    size=instruction_size,
                    enable_events=True,
                    key=create_key(KEY_TX_INST + KEY_T, inst['indx']),
                    visible=False, ),
                sg.Combo(
                    phrases,
                    default_value='',
                    size=max_row_size(phrases),
                    tooltip='Select Appropriate Instruction',
                    enable_events=True,
                    key=create_key(KEY_TX_INST + KEY_COMBO, inst['indx']),
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


def get_instruction(inst, instructions):
    for i in instructions:
        tests = [inst[key] == i[key] for key in inst.keys()]
        if all(tests):
            return i
    sys.exit('No matching instruction found. Order outside protocols?')


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
                               size=max_row_size(options))
    window[KEY_ORDER_SELECT + KEY_T].update(visible=True)
    window[KEY_ORDER_SELECT].update(visible=True)


def update_plan_names(window, plan_name_event, plan_name_dict, current_plan_name):
    if not current_plan_name:
        current_plan_name = 'Select Plan Abbreviation'
    plan_names = []
    for k, v in plan_name_dict.items():
        plan_names.append(v)
    window[plan_name_event].update(value=current_plan_name, values=plan_names)


def create_preplan_information_tab(protocols, sites, orders, instructions, beamsets, targets):
    """
    Create the layout for the CT Scan tab in the main window.

    Parameters:
    beamsets (list): A list of available beamsets.
    targets (list): A list of available targets.
    """
    maximum_beamset_count = len(beamsets)
    # Create the layout for the beamset information section
    beamset_layout = create_beamset_layout(beamsets, targets)
    # Create the layout for treatment planning order selection
    order_selection_layout = create_order_selection_layout(protocols, sites,
                                                           orders, instructions)

    # Create the overall layout for the CT Scan tab
    ct_scan_layout = [
        # CT Information frame
        [sg.Frame('CT Information',
                  [
                      [sg.Text('', size=(5, 1))],  # Empty space
                      [sg.Text('CT Scan Date:', pad=(20, 0)), sg.Text('', key=KEY_SIM_DATE),
                       sg.CalendarButton('Select date', target=KEY_SIM_DATE, key='calendar',
                                         format='%Y-%m-%d')],
                      [sg.Text('Number of CT Slices: ', pad=(20, 0)),
                       sg.Input(key=KEY_SLICES, size=(10, 1))],
                      [sg.Text('', size=(5, 1))],  # Empty space
                  ],
                  element_justification='l',
                  font=('Helvetica', 11, 'bold'))
         ],

        # Treatment Instructions frame
        [sg.Frame('Treatment Planning Order Information',
                  [[sg.Column(order_selection_layout,
                              scrollable=True,
                              vertical_scroll_only=True,
                              size=(800, 400))]],
                  font=('Helvetica', 11, 'bold'),
                  element_justification='l',
                  size=(800, 400),
                  )
         ],

        # Beamset Information frame
        [sg.Frame('Beamset Information',
                  [
                      [sg.Text('', size=(5, 1))],  # Empty space
                      [sg.Text('Number of BeamSets: '),
                       sg.Combo(list(range(1, maximum_beamset_count + 1)),
                                key=KEY_BEAMSET_COUNT,
                                default_value=1,
                                size=(10, 1),
                                enable_events=True)
                       ],
                      [sg.Text('', size=(5, 1))],  # Empty space
                      beamset_layout,
                      [sg.Text('', size=(5, 1))],  # Empty space
                  ],
                  font=('Helvetica', 11, 'bold'),
                  element_justification='l')],

    ]

    # Add a submit button column on the right
    ct_scan_layout_with_submit = [[sg.Column(ct_scan_layout,
                                             element_justification='l',
                                             pad=(10, 0)),
                                   ]]

    return ct_scan_layout_with_submit


def extract_preplan_values(main_window, num_beamsets=1):
    """
    Extract the values from the PySimpleGUI window and return them in a dictionary.

    Parameters:
    main_window (Sg.Window): The main PySimpleGUI window object.
    num_beamsets (int): The number of beamsets selected by the user,
    if nothing selected, then user will have chosen 1.

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
                if isinstance(instruction_element, sg.Input):
                    treatment_instructions[key] = value.get()
                elif isinstance(instruction_element, sg.Combo):
                    treatment_instructions[key] = value.get()
                elif isinstance(instruction_element, sg.Radio):
                    treatment_instructions[key] = value.get()

    # Get the Beamset Information values
    beamset_dict = {}
    beamset_dict[KEY_BEAMSET_COUNT] = main_window[KEY_BEAMSET_COUNT].get() \
        if main_window[KEY_BEAMSET_COUNT].get() else ''
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
                    beamset_dict[tuple_key_to_str(window_key)] = main_window[window_key].get()
    values_dict = {
        KEY_SIMULATION_DATA: simulation_dict,
        KEY_TX_INST_SET: treatment_instructions,
        KEY_BEAMSET: beamset_dict
    }

    return values_dict


def tuple_key_to_str(value):
    if isinstance(value, dict):
        return {tuple_key_to_str(k): tuple_key_to_str(v) for k, v in value.items()}
    elif isinstance(value, tuple):
        return '||'.join(map(str, value))
    return value


def load_preplan(window, values, sites, protocols, instructions, maximum_beamset_count,
                 maximum_target_number):
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
        else:
            window[key](value)

    # Handle the radio keys and other elements in the Treatment Planning Order Information frame
    treatment_instructions = values.get(KEY_TX_INST_SET, {})
    for key, value in treatment_instructions.items():
        window[key].update(value=value)
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
