import PySimpleGUI as sg


def get_support_structures_GUI(
    examination,
):

    support_structure_values = None

    civco_incline_board_angles = [
        'Flat',
        '5 deg',
        '7.5 deg',
        '10 deg',
        '12.5 deg',
        '15 deg',
        '17.5 deg',
        '20 deg',
        '22.5 deg',
        '25 deg',
    ]

    sg.ChangeLookAndFeel('DarkAmber')

    layout = [
        [
            sg.Text(
                'Support Structure Selection',
                size=(30, 1),
                justification='center',
                font=("Helvetica", 25),
                relief=sg.RELIEF_RIDGE
            ),
        ],
        [
            sg.Text('Please select support structures for the active image set.')
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Radio(
                            'TrueBeam',
                            "RADIOCOUCH",
                            default=True,
                            size=(10,1),
                            key="-COUCH TRUEBEAM-"
                        )
                    ],
                    [
                        sg.Radio(
                            'TomoTherapy',
                            "RADIOCOUCH",
                            size=(10,1),
                            key="-COUCH TOMO-"
                        )
                    ],
                                        [
                        sg.Radio(
                            'None',
                            "RADIOCOUCH",
                            size=(10,1),
                            key="-COUCH NONE-"
                        )
                    ],
                ],
                title='Treatment Table',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a treatment table',
            ),
        ],
        [
            sg.Checkbox(
                'Use Civco Incline Breast Board',
                enable_events=True,
                key="-USE CIVCO-"
            )
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Text('Incline Angle'),
                        sg.Combo(
                            civco_incline_board_angles,
                            readonly=True,
                            default_value="7.5 deg",
                            key='-INCLINE ANGLE-'
                        )
                    ],
                    [
                        sg.Checkbox(
                            'Use Wingboard',
                            enable_events=True,
                            key="-USE WINGBOARD-"
                        )
                    ],
                    [
                        sg.Frame(
                            layout=[
                                [
                                    sg.Text('Wingboard Index'),
                                    sg.Slider(
                                        range=(0, 75),
                                        orientation='h',
                                        size=(34, 20),
                                        default_value=50,
                                        key="-WINGBOARD INDEX-",
                                    )
                                ]
                            ],
                            title='Wingboard Options',
                            relief=sg.RELIEF_SUNKEN,
                            tooltip='Select a wingboard position',
                            visible=False,
                            key="-FRAME WINGBOARD-",
                        )
                    ],
                ],
                title='Civco Incline Breast Board Options',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a breast board options',
                visible=False,
                key="-FRAME CIVCO-",
            ),
        ],
        [
            sg.Submit(tooltip='Click to submit this window'),
            sg.Cancel()
        ]
    ]

    civco_visible, wingboard_visible = False, False

    window = sg.Window(
        'Support Structure Selection',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Cancel":
            break
        elif event == "Submit":
            support_structure_values = values
            break
        elif event.startswith('-USE CIVCO-'):
            civco_visible = not civco_visible
            window['-FRAME CIVCO-'].update(visible=civco_visible)

        elif event.startswith('-USE WINGBOARD-'):
            wingboard_visible = not wingboard_visible
            window['-FRAME WINGBOARD-'].update(visible=wingboard_visible)

    window.close()

    return support_structure_values

vals = get_support_structures_GUI("exam")
print(vals)
