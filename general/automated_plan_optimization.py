""" Automated Plan Optimization

    Automatically optimize the current case, examination, plan, beamset using
    input optimization parameters

    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are
           passed to the function as an argument

    Example Usage:
    import optimize_plan from automated_plan_optimization
    optimization_inputs = {
        'initial_max_it': 40,
        'initial_int_it': 7,
        'second_max_it': 25,
        'second_int_it': 5,
        'vary_grid': True,
        'dose_dim1': 0.4,
        'dose_dim2': 0.3,
        'dose_dim3': 0.35,
        'dose_dim4': 0.2,
        'fluence_only': False,
        'reset_beams': True,
        'segment_weight': True,
        'reduce_oar': True,
        'n_iterations': 6}

    optimize_plan(patient=Patient,
                  case=case,
                  plan=plan,
                  beamset=beamset,
                  **optimization_inputs)

    Script Created by RAB 12Dec2019
    Prerequisites:

    Validation Notes:
                  SNS, TomoTherapy, VMAT (seg weight, reduce OAR, variable dose grid)
    Test Patient: 10A:  MR# ZZUWQA_ScTest_30Dec2020,
                        Name: Script_Testing^Automated Plan – Whole Brain
    Test Patient: 11B:  MR# ZZUWQA_ScTest_30Dec2020,
                        Name: Script_Testing^Automated Plan – Whole Brain

    Version history:
    1.0.0 Moved Most functions to the OptimizeOperations library
    1.1.0 Updated to RayStation Version 10A SP1
    1.1.1 Updated to RaySation Version 11B


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2022-Jun-27'
__version__ = '1.1.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10A.SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = None
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__credits__ = ['']


#
import logging
import sys
import PySimpleGUI as sg

import connect
import UserInterface
import OptimizationOperations
from GeneralOperations import logcrit as logcrit
from GeneralOperations import find_scope as find_scope


def set_frame_visibility(window, visible_frame, frames_list):
    for f in frames_list.keys():
        if f in visible_frame:
            window[f].update(visible=True)
        else:
            window[f].update(visible=False)


def optimization_gui(beamset, optimization_inputs):
    # OPTIMIZATION DIALOG
    dialog_name = 'Optimization Inputs'
    frame1 = '-FRAME INITIAL PARAMETERS-'
    frame2 = '-FRAME ITERATION PARAMETERS-'
    frame3 = '-FRAME POST OPTIMIZATION STEPS-'
    frame4 = '-FRAME CUSTOM TREATMENT SETTINGS-'
    k_fluence = '-FLUENCE ONLY-'
    k_reset = '-RESET BEAMS-'
    k_vary = '-VARIABLE DOSE GRID-'
    k_seg = '-SEGMENT WEIGHT OPTIMIZATION-'
    k_reduce_oar = '-REDUCE OAR DOSE-'
    k_reduce_time = '-REDUCE TOMO TREATMENT TIME-'
    k_treat = '-USE TREAT SETTINGS-'
    k_treat_c = '-CUSTOM-'
    k_treat_d = '-DEFAULT-'
    k_treat_n = '-NONE-'
    k_treat_margin = '-CUSTOM TREATMENT MARGINS-'
    k_cold_max = '-MAX COLD ITERATIONS-'
    k_cold_int = '-MAX COLD INTERMEDIATE-'
    k_warm_max = '-MAX WARM ITERATIONS-'
    k_warm_int = '-MAX WARM INTERMEDIATE-'
    k_num = '-NUMBER START ITERATIONS-'

    frames = {frame3: "Post-Optimization Operations",
              frame2: "Optimization Parameters",
              frame1: "Initialization Parameters",
              frame4: "Custom Treatment Settings"}
    check_boxes = {k_fluence: "Fluence calculation only, for dialing in parameters " +
                              "all other values in this window will be ignored",
                   k_reset: "Reset beams (cold start)",
                   k_vary: "Start with a large grid, and decrease gradually",
                   k_seg: "Segment weight calculation",
                   k_reduce_oar: "Reduce OAR Dose",
                   k_reduce_time: "Reduce TomoTherapy Treatment Time"}
    radio_buttons = {
        k_treat: {
            k_treat_d: "Use Default Treatment Settings",
            k_treat_n: "No Treat Modifications",
            k_treat_c: "Use Custom Treatment Settings"}
    }
    text_fields = {k_cold_max: "Maximum number of iterations for initial optimization",
                   k_cold_int: "Intermediate iteration for svd to aperture conversion",
                   k_warm_max: "Maximum iteration used in warm starts",
                   k_warm_int: "Intermediate iteration for full dose conversion warm starts (SMLC)",
                   k_num: "Number of Iterations",
                   k_treat_margin: "Custom treat margins SBRT(<3 mm), Standard(<8 mm)"}
    sg.ChangeLookAndFeel('DarkBlue')

    vmat_frame2_layout = [
        [sg.Push(), sg.Text(text_fields[k_num]),
         sg.Input(4, key=k_num, )],

        [sg.Push(), sg.Text(text_fields[k_cold_max]),
         sg.Input(50, key=k_cold_max)],

        [sg.Push(), sg.Text(text_fields[k_cold_int]),
         sg.Input(10, key=k_cold_int)],

        [sg.Push(), sg.Text(text_fields[k_warm_max]),
         sg.Input(35, key=k_warm_max)],

        [sg.Push(), sg.Text(text_fields[k_warm_int]),
         sg.Input(5, key=k_warm_int)],

        [sg.Radio(radio_buttons[k_treat][k_treat_d],
                  group_id=k_treat,
                  enable_events=True,
                  default=True,
                  visible=True,
                  key=k_treat_d),
         sg.Radio(radio_buttons[k_treat][k_treat_c],
                  group_id=k_treat,
                  enable_events=True,
                  default=False,
                  visible=True,
                  key=k_treat_c, ),
         sg.Radio(radio_buttons[k_treat][k_treat_n],
                  group_id=k_treat,
                  enable_events=True,
                  default=False,
                  visible=True,
                  key=k_treat_n,
                  ),
         ],
        [sg.Frame(
            layout=[
                [sg.Text(text_fields[k_treat_margin])],
                [sg.Input(2.5, key=k_treat_margin)]
            ],
            title=frames[frame4],
            relief=sg.RELIEF_SUNKEN,
            tooltip="Use margins ≤ 3 mm for SBRT(1.5 mm default) and ≤ 8 mm for others",
            visible=False,
            pad=((240, 0), 0),
            key=frame4
        )]
    ]
    vmat_frame3_layout = [[sg.Checkbox(check_boxes[k_vary],
                                       default=False,
                                       enable_events=False,
                                       key=k_vary)],
                          [sg.Checkbox(check_boxes[k_reduce_oar],
                                       default=False,
                                       visible=True,
                                       enable_events=False,
                                       key=k_reduce_oar)],
                          [sg.Checkbox(check_boxes[k_seg],
                                       default=False,
                                       visible=True,
                                       enable_events=False,
                                       key=k_seg)],
                          ]

    tomo_frame2_layout = [
        [sg.Push(), sg.Text(text_fields[k_num]),
         sg.Input(4, key=k_num, )],

        [sg.Push(), sg.Text(text_fields[k_cold_max]),
         sg.Input(50, key=k_cold_max)],

        [sg.Push(), sg.Text(text_fields[k_cold_int]),
         sg.Input(10, key=k_cold_int)],

        [sg.Push(), sg.Text(text_fields[k_warm_max]),
         sg.Input(35, key=k_warm_max)],

        [sg.Push(), sg.Text(text_fields[k_warm_int]),
         sg.Input(5, key=k_warm_int)],
    ]
    tomo_frame3_layout = [[sg.Checkbox(check_boxes[k_vary],
                                       default=False,
                                       enable_events=False,
                                       key=k_vary)],
                          [sg.Checkbox(check_boxes[k_reduce_time],
                                       default=False,
                                       enable_events=False,
                                       visible=True,
                                       k=k_reduce_time)]
                          ]
    if "Tomo" in beamset.DeliveryTechnique:
        frame2_layout = tomo_frame2_layout
        frame3_layout = tomo_frame3_layout
        frames.pop(frame4)
        tomo_dialog = True
    else:
        frame2_layout = vmat_frame2_layout
        frame3_layout = vmat_frame3_layout
        tomo_dialog = False

    top = [
        [sg.Text(dialog_name,
                 size=(55, 1),
                 justification='center',
                 font=("Helvetica", 16),
                 relief=sg.RELIEF_RIDGE, )
         ],
        [sg.Text(f"Please selected the optimization strategy for '{beamset.DicomPlanLabel}'")],
        [
            sg.Frame(
                layout=[

                    [sg.Checkbox(check_boxes[k_fluence],
                                 default=True,
                                 enable_events=True,
                                 key=k_fluence)],
                    [sg.Checkbox(check_boxes[k_reset],
                                 default=False,
                                 enable_events=False,
                                 key=k_reset)],

                ],
                title=frames[frame1],
                relief=sg.RELIEF_SUNKEN,
                tooltip="Initialization Parameters for the optimization",
                visible=True,
                size=(663, 80),
                key=frame1,
            )],
        [
            sg.Frame(
                layout=frame2_layout,
                title=frames[frame2],
                relief=sg.RELIEF_SUNKEN,
                tooltip="Optimization steps",
                visible=False,
                size=(663, 262),
                key=frame2,
            )],
        [
            sg.Frame(
                layout=frame3_layout,
                title=frames[frame3],
                relief=sg.RELIEF_SUNKEN,
                tooltip="Post-optimization parameters",
                visible=False,
                size=(663, 155),
                key=frame3,
            )
        ]
    ]
    bottom = [
        [
            sg.Submit(tooltip='Click to accept and start optimization'),
            sg.Cancel()
        ]
    ]
    layout = [[sg.Column(top)], [sg.Column(bottom)]]
    window = sg.Window(
        'Automated Optimization Parameters',
        layout,
        default_element_size=(10, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            opt_values = None
            break
        elif event == "Submit":
            opt_values = values
            break
        elif event.startswith(k_fluence):
            if values[k_fluence]:
                visible_frame = [frame1]
                set_frame_visibility(window, visible_frame, frames)
            else:
                visible_frame = [frame1, frame2, frame3]
                set_frame_visibility(window, visible_frame, frames)
        elif event.startswith(k_treat_n) or event.startswith(k_treat_d):
            visible_frame = [frame1, frame2, frame3]
            set_frame_visibility(window, visible_frame, frames)
        elif event.startswith(k_treat_c):
            visible_frame = [frame1, frame2, frame3, frame4]
            set_frame_visibility(window, visible_frame, frames)
    window.close()
    # Process results
    if not opt_values:
        sys.exit('Dialog cancelled')
    optimization_inputs['initial_max_it'] = int(opt_values[k_cold_max])
    optimization_inputs['initial_int_it'] = int(opt_values[k_cold_int])
    optimization_inputs['second_max_it'] = int(opt_values[k_warm_max])
    optimization_inputs['second_int_it'] = int(opt_values[k_warm_int])
    optimization_inputs['vary_grid'] = opt_values[k_vary]
    optimization_inputs['fluence_only'] = opt_values[k_fluence]
    optimization_inputs['reset_beams'] = opt_values[k_reset]
    optimization_inputs['n_iterations'] = int(opt_values[k_num])
    if tomo_dialog:
        optimization_inputs['segment_weight'] = False
        optimization_inputs['reduce_oar'] = False
        optimization_inputs['use_treat_settings'] = True
        if opt_values[k_reduce_time]:
            optimization_inputs['reduce_time'] = opt_values[k_reduce_time]
        else:
            optimization_inputs['reduce_time'] = False
    else:
        optimization_inputs['reduce_time'] = False
        if opt_values.get(k_seg):
            optimization_inputs['segment_weight'] = opt_values[k_seg]
        else:
            optimization_inputs['segment_weight'] = False
        if opt_values.get(k_reduce_oar):
            optimization_inputs['reduce_oar'] = opt_values[k_reduce_oar]
        else:
            optimization_inputs['reduce_oar'] = False
        if opt_values[k_treat_n]:
            optimization_inputs['use_treat_settings'] = False
        elif opt_values[k_treat_d]:
            optimization_inputs['use_treat_settings'] = True
            optimization_inputs['treat_margin'] = None
        elif opt_values[k_treat_c]:
            optimization_inputs['use_treat_settings'] = True
            optimization_inputs['treat_margin'] = float(opt_values[k_treat_margin]) / 10.  # convert to cm
        else:
            optimization_inputs['use_treat_settings'] = False
    return optimization_inputs


def main():
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    plan = find_scope(level='Plan')
    beamset = find_scope(level='BeamSet')
    patient_db = find_scope(level='PatientDB')

    optimization_inputs = {
        'patient_db': patient_db,
        'initial_max_it': None,
        'initial_int_it': None,
        'second_max_it': None,
        'second_int_it': None,
        'vary_grid': None,
        'dose_dim1': 0.5,
        'dose_dim2': 0.4,
        'dose_dim3': 0.3,
        'dose_dim4': 0.2,
        'fluence_only': None,
        'reset_beams': None,
        'segment_weight': None,
        'reduce_oar': None,
        'use_treat_settings': None,
        'save': True,
        # Small Target
        # 'small_target': small_target,
        'n_iterations': None, }
    optimization_inputs = optimization_gui(beamset, optimization_inputs)

    (status, message) = OptimizationOperations.optimize_plan(patient=patient,
                                                             case=case,
                                                             exam=exam,
                                                             plan=plan,
                                                             beamset=beamset,
                                                             **optimization_inputs)

    if status:
        logging.info("Optimization report: {}".format(message))
        logging.debug("Optimization successful. Closing")
    else:
        raise IOError("{}".format(message))


if __name__ == '__main__':
    main()
