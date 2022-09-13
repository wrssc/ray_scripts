""" Make DQA Plans

    The delta4 software needs the gantry period to load the plan, however
    it doesn't live as a native object in RS. The user is prompted to enter it
    then the data is exported to a temporary directory and this information is
    input.
    This script:
    -Checks for a beamset to be loaded
    -Generates QA Plans for the current beamset using a centered delta4
     phantom
    -Sends the QA Plan to the Delta4 Dicom Destination
    -Waits for the user to export this plan to iDMS
    -Asks user to load the transfer plan
    -Generates a dqa for this transfer plan on the centered delta 4
    -Sends the QA plan to delta 4
    -prompts user to send plan to iDMS
    -Exports using the ValidationPlan.ScriptableQADicomExport method.
    -Copies pertinent data to the user clipboard.
    TODO: When export to the RayGateWay is supported using the above method,
          enable multiple destinations to be selected.

    Version:
    0.0.0 Testing
    0.0.1 Changed format of output message
    0.0.2 Debugging small changes in the 11 B interface and improving user dialogs

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

__author__ = 'Adam Bayliss and Patrick Hill'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '09-Aug-2022'
__version__ = '0.0.2'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import sys
import logging
import os
import re
import numpy as np
import connect
import UserInterface
import DicomExport
from collections import namedtuple, OrderedDict
from datetime import datetime
import pyperclip
import PySimpleGUI as sg

clinic_options = {'--MACHINES--': ['TrueBeam1358', 'TrueBeam2588', 'TrueBeam2871',
                                   'TrueBeam3744', 'HDA0477', 'HDA0488'],
                  '--QA_DEVICES--': ['Plus_01 (UH)', 'Plus_02 (JC)', 'Plus_03 (EC)',
                                     'Plus_04 (UH)', 'Plus_05 (EC)'],
                  '--X_GRID--': [-3.0, -2.0, -1.0, 0., 1.0, 2.0, 3.0, ],
                  '--Y_GRID--': [-16., -14., -12., -10., -8., -6., -4., -2., 0.,
                                 16., 14., 12., 10., 8., 6., 4., 2.],
                  '--Z_GRID--': [-9., -6., -3., 0., 3., 6., 9.],
                  '--CENTROID SHIFT FACTOR--': 0.5,  # 50%
                  '--TOMO ISO ROUND': 0.5,  # cm
                  '--VMAT_QA_PHANTOM--': r"Delta4 (TrueBeam)",
                  '--VMAT_PHANTOM_ID--': r"ZZIMRTQA",
                  '--TOMO_QA_PHANTOM--': r"Delta4_HFS_0X_0Y TomoHDA",
                  '--TOMO_PHANTOM_ID--': r"20191017PMH-QA"}
#
# Phantom properties for TOMO
# TODO Find a way of getting the current database name
# Options in Validation
# clinic_options['--TOMO_QA_PHANTOM--'] = r"TomoHDA Delta4_HFS_X0_Y0"  # Validation
# clinic_options['--TOMO_PHANTOM_ID--'] = r"20191004PMH-D4QA"  # Validation
#
# Phantom properties for VMAT
#
# Declare the named tuple for storing computed TomoTherapy parameters
TomoParams = namedtuple('TomoParams', ['gantry_period', 'time', 'couch_speed', 'total_travel'])


# Determine the TomoTherapy couch travel using the Y-offset of the first/last segment
def compute_couch_travel_helical(beam):
    # Take first and last segment, compute distance
    number_of_segments = len(beam.Segments)
    first_segment = beam.Segments[0]
    last_segment = beam.Segments[number_of_segments - 1]
    couch_travel = abs(last_segment.CouchYOffset - first_segment.CouchYOffset)
    return couch_travel


def compute_pitch_direct(beam):
    first_segment = beam.Segments[0]
    second_segment = beam.Segments[1]
    y_travel_per_projection = abs(second_segment.CouchYOffset - first_segment.CouchYOffset)
    pitch = round(y_travel_per_projection, 3)
    return pitch


def compute_couch_travel_direct(beam):
    # Take first and last segment, compute distance
    number_of_segments = len(beam.Segments)
    first_segment = beam.Segments[0]
    last_segment = beam.Segments[number_of_segments - 1]
    pitch = compute_pitch_direct(beam)
    couch_travel = pitch + abs(last_segment.CouchYOffset - first_segment.CouchYOffset)
    return couch_travel


def compute_tomo_params(beam):
    # Rs Beam object, return a named tuple
    number_segments = len(beam.Segments)
    # Total Time: Projection time x Number of Segments = Total Time
    time = beam.BeamMU * number_segments
    # Rotation period: Projection Time * 51
    if beam.DeliveryTechnique == "TomoHelical":
        gantry_period = beam.BeamMU * 51.
        total_travel = compute_couch_travel_helical(beam)
        # Couch Speed: Total Distance Traveled / Total Time
    else:
        total_travel = compute_couch_travel_direct(beam)
        gantry_period = None
    couch_speed = total_travel / time
    return TomoParams(gantry_period=gantry_period, time=time, couch_speed=couch_speed, total_travel=total_travel)


def convert_couch_speed_to_mm(str_input):
    # Convert incoming str_input to a couch speed in mm/sec and return a string
    float_input = float(str_input)
    convert_input = float_input * 10  # cm-> mm
    return convert_input


def make_qa_plan_name(name):
    # Should replace PRD, THI with DQA
    search_re = re.compile(r'(THI)|(PRD)')
    return re.sub(search_re, 'DQA', name)


def qa_plan_exists(plan, qa_plan_name):
    # Return true if plan exists false otherwise
    verification_plans = plan.VerificationPlans
    for vp in verification_plans:
        if vp.BeamSet.DicomPlanLabel == qa_plan_name:
            return True
    return False


def find_qa_plan(plan, beamset, qa_plan_name):
    # Check the list of verification plans to see which belongs to a given beamset
    # check to see if the qa_plan matches the
    verification_plans = plan.VerificationPlans
    for vp in verification_plans:
        if vp.OfRadiationSet.DicomPlanLabel == beamset.DicomPlanLabel \
                and vp.BeamSet.DicomPlanLabel == qa_plan_name:
            return vp
    return None


def make_vmat_qa_plan(plan, beamset, qa_plan_name):
    # Make a qa plan
    try:
        beamset.CreateQAPlan(
            PhantomName=clinic_options['--VMAT_QA_PHANTOM--'],
            PhantomId=clinic_options['--VMAT_PHANTOM_ID--'],
            QAPlanName=qa_plan_name,
            IsoCenter={'x': 0, 'y': 0, 'z': 0},
            DoseGrid={'x': 0.2, 'y': 0.2, 'z': 0.2},
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=0,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=None,
            MotionSynchronizationTechniqueSettings=None,
            RemoveCompensators=False,
            EnableDynamicTracking=False)
        qa_plan = find_qa_plan(plan, beamset, qa_plan_name)
        logging.debug('qa plan creation complete returning {}'.format(qa_plan.BeamSet.DicomPlanLabel))
        return qa_plan
    except Exception as e:
        try:
            UserInterface.WarningBox('QA Plan failed to create: {}'.format(e.Message))
            sys.exit('QA Plan failed to create {}'.format(e.Message))
        except:
            UserInterface.WarningBox('QA Plan failed to create: {}'.format(e))
            sys.exit('QA Plan failed to create {}'.format(e))


def make_tomo_qa_plan(plan, beamset, qa_plan_name):
    # Make a qa plan
    try:
        beamset.CreateQAPlan(
            PhantomName=clinic_options['--TOMO_QA_PHANTOM--'],
            PhantomId=clinic_options['--TOMO_PHANTOM_ID--'],
            QAPlanName=qa_plan_name,
            IsoCenter={'x': 0, 'y': 0, 'z': 0},
            DoseGrid={'x': 0.2, 'y': 0.2, 'z': 0.2},
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=None,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=None,
            MotionSynchronizationTechniqueSettings=None,
            RemoveCompensators=False,
            EnableDynamicTracking=False)
        qa_plan = find_qa_plan(plan, beamset, qa_plan_name)
        return qa_plan
    except Exception as e:
        UserInterface.WarningBox('QA Plan failed to create: {}'.format(e))
        sys.exit('QA Plan failed to create {}'.format(e))


def get_timestamp(beamset):
    # Get the approval time-stamp for the parent beamset
    if beamset.Review is None:
        logging.info('No approval status set.')
        approval_time = 'Not set.'
        return approval_time
    else:
        if str(beamset.Review.ApprovalStatus) == 'Approved':
            time_stamp = str(beamset.Review.ReviewTime)
            date_object = datetime.strptime(time_stamp, '%m/%d/%Y %I:%M:%S %p')
            approval_time = str(date_object)
            return approval_time
        else:
            logging.info('QA is generated from unapproved plan')
            approval_time = 'Not set.'
            return approval_time


def build_string_clip(beamset, responses, verification_plan):
    # Build a comment to insert in the plan dialog and copy it to the clipboard
    dialog_dict = OrderedDict()
    iso = verification_plan.BeamSet.Beams[0].Isocenter.Position
    dialog_dict['TDS'] = responses['-TDS-']
    dialog_dict['Delta4'] = responses['-Delta4-']
    dialog_dict['RSA'] = get_timestamp(beamset)
    dialog_dict['By'] = os.getenv('username')
    dialog_dict['X-shift'] = "{:.1f} mm".format(10. * iso['x'])
    dialog_dict['Y-shift'] = "{:.1f} mm".format(10. * iso['y'])
    dialog_dict['Z-shift'] = "{:.1f} mm".format(10. * iso['z'])

    comment = ""
    for k, v in dialog_dict.items():
        comment += "{}: {}\n".format(k, v)
    return comment


def comment_to_clipboard(beamset, responses, verification_plan):
    #
    # Add data to the beamset comment
    beamset_comment = build_string_clip(beamset, responses, verification_plan)
    verification_plan.BeamSet.Comment = beamset_comment
    pyperclip.copy(beamset_comment)
    return pyperclip.paste()


def prompt_qa_name(qa_plan_name):
    # Prompt the user for a qa plan name and return response
    # Initialize dialog
    initial = {}
    options = {}
    inputs = {'Name': 'Provide Desired DQA Plan Name'}
    required = ['Name']
    types = {'Name': 'text'}
    #
    title = 'DQA Plan Name ' + qa_plan_name + 'is Taken'
    dialog = UserInterface.InputDialog(inputs=inputs,
                                       datatype=types,
                                       options=options,
                                       initial=initial,
                                       required=required,
                                       title='Export Options')
    response = dialog.show()
    if response == {}:
        sys.exit('No plan name provided. Perhaps go delete the qa plan: {}'
                 .format(qa_plan_name))
    else:
        return response['Name']


def qa_gui(plan):
    # Find all beamsets in this plan
    beamset_list = [b.DicomPlanLabel for b in plan.BeamSets]
    # Get Delta4 Names
    delta4_list = clinic_options['--QA_DEVICES--']
    tds_list = clinic_options['--MACHINES--']

    # Build Dialog
    dialog_name = 'QA Plan Building'
    frames = ['-PLAN PARAMETERS-', '-DELIVERY PARAMETERS-', 'BEAMSET NAME']
    sg.ChangeLookAndFeel('DarkPurple4')
    layout = [
        [sg.Text(dialog_name,
                 size=(20, 1),
                 justification='center',
                 font=("Helvetica", 16),
                 relief=sg.RELIEF_RIDGE), ],
        [sg.Frame(
            layout=[[sg.Text(f'Beamsets for DQA:')],
                    [sg.Listbox(beamset_list,
                                size=(30, 3),
                                key="-BEAMSETS-",
                                default_values=beamset_list[0],
                                select_mode='extended',
                                enable_events=True)],
                    [sg.Text(f'Treatment Delivery System:')],
                    [sg.Combo(tds_list,
                              size=(20, 1),
                              key='-TDS-', )]],
            title='Plan Parameter Selection',
            relief=sg.RELIEF_SUNKEN,
            key=frames[0],
            tooltip='Select Beamsets to QA and Delivery System')],
        [sg.Frame(
            layout=[[sg.Text(f'Delta4 Unit For QA:')],
                    [sg.Combo(delta4_list,
                              size=(20, 1),
                              key='-Delta4-', )],
                    [sg.Checkbox('Center Dose On Phantom',
                                 key='-SHIFT PHANTOM-',
                                 default=True),
                     ]],
            title='Delivery Parameters',
            relief=sg.RELIEF_SUNKEN,
            key=frames[1],
            tooltip='Select delivery parameters for the DQA')],
        [sg.Submit(tooltip='Click to submit this window'),
         sg.Cancel()],
    ]
    window = sg.Window(
        'DQA Setup',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            qa_selections = None
            break
        elif event == "Submit":
            qa_selections = values
            break
    window.close()
    if qa_selections == {}:
        sys.exit('QA Script was cancelled')
    else:
        return qa_selections


def find_dose_centroid(vp, beamset, percent_max=None):
    """
    Find the centroid of points at or above 80% or percent_max of the maximum dose in the grid
    :param vp: current  verification plan
    :param beamset: current beamset
    :param percent_max: percentage of maximum dose, above which points will be included
    :return: a list of [x, y, z] coordinates on the dose grid
    """
    # Get the MU weights of each beam
    tot = 0.
    for b in beamset.Beams:
        tot += b.BeamMU

    # Search the fractional dose grid
    # The dose grid is stored by RS as a numpy array
    pd = beamset.FractionDose.DoseValues.DoseData

    # The dose grid is stored [z: I/S, y: P/A, x: R/L]
    pd = pd.swapaxes(0, 2)

    if percent_max is None:
        rx = np.amax(pd) * 80. / 100.
    else:
        rx = np.amax(pd) * percent_max / 100.

    tolerance = 1e-2

    xcorner = vp.DoseGridStructures.InDoseGrid.Corner.x
    ycorner = vp.DoseGridStructures.InDoseGrid.Corner.y
    zcorner = vp.DoseGridStructures.InDoseGrid.Corner.z
    xsize = vp.DoseGridStructures.InDoseGrid.VoxelSize.x
    ysize = vp.DoseGridStructures.InDoseGrid.VoxelSize.y
    zsize = vp.DoseGridStructures.InDoseGrid.VoxelSize.z

    rx_points = np.array([])
    # Find the an array of points with dose > rx
    # if there are no points with this dose, look for points with a lower percentage
    t = 1
    while rx_points.size == 0:
        t_init = t
        rx_points = np.argwhere(pd >= rx * t)
        t = t_init - tolerance
    # logging.info('Tolerance used for the supplied dose {} agreement was > {} Gy'.format(rx, rx * t_init))

    # logging.debug('Finding centroid of matching dose points')
    length = rx_points.shape[0]  # total number of points
    n_x_pos = rx_points[:, 0] * xsize + xcorner + xsize / 2  # points in RS coordinates
    n_y_pos = rx_points[:, 1] * ysize + ycorner + ysize / 2
    n_z_pos = rx_points[:, 2] * zsize + zcorner + zsize / 2
    xpos = np.sum(n_x_pos) / length  # average position
    ypos = np.sum(n_y_pos) / length
    zpos = np.sum(n_z_pos) / length

    return {'x': xpos, 'y': ypos, 'z': zpos}


def shift_tomo_iso(verification_plan):
    a = find_dose_centroid(vp=verification_plan,
                           beamset=verification_plan.BeamSet,
                           percent_max=80)
    z_shift = a['z'] if abs(a['z'] < 9.) else 0.
    shift = {'x': -1. * a['x'], 'y': -1. * a['y'], 'z': -1. * z_shift}
    beams = verification_plan.BeamSet.Beams
    iso_name = "".join((verification_plan.BeamSet.DicomPlanLabel,
                        f"_X:{shift['x']:03.0f}",
                        f"_Y:{shift['y']:03.0f}",
                        f"_Z:{shift['z']:03.0f}"))
    logging.info("During DQA creation, the center of the dose profile was at " +
                 f"[x,y,z]: [{shift['x']:.2f},{shift['y']:.2f},{shift['z']:.2f}].")
    for b in beams:
        b.Isocenter.EditIsocenter(Name=iso_name, Position=shift, Color="Purple")


def shift_iso(verification_plan, percent_dose_region=80.):
    # Using the input verification plan object find the center of the
    # percent_dose_region * max dose volume.
    # If the center is more than 90 mm from the center of the phantom, shift longitudinally.
    # Find the closest shift in 5 cm intervals to put the detector dense region in the
    # center of the high isodose.
    shift = {}
    beams = verification_plan.BeamSet.Beams
    a = find_dose_centroid(vp=verification_plan,
                           beamset=verification_plan.BeamSet,
                           percent_max=percent_dose_region)
    optimal_shift = {
        'x': a['x'] * clinic_options['--CENTROID SHIFT FACTOR--'],
        'y': a['y'] * clinic_options['--CENTROID SHIFT FACTOR--'],
        'z': a['z'] * clinic_options['--CENTROID SHIFT FACTOR--'],
    }
    x_grid = clinic_options['--X_GRID--']
    y_grid = clinic_options['--Y_GRID--']
    z_grid = clinic_options['--Z_GRID--']
    shift['x'] = min(x_grid, key=lambda x: abs(optimal_shift['x'] - x))
    shift['y'] = min(y_grid, key=lambda y: abs(optimal_shift['y'] - y))
    shift['z'] = min(z_grid, key=lambda z: abs(optimal_shift['z'] - z))
    logging.info(
        "During DQA creation, the center of the dose profile was at [x,y,z]: [{:.2f},{:.2f},{:.2f}]. ".format(a['x'],
                                                                                                              a['y'],
                                                                                                              a['z'])
        + "Closest shift coordinates are [x,y,z]: [{},{},{}]".format(shift['x'], shift['y'], shift['z']))
    iso_name = "".join((verification_plan.BeamSet.DicomPlanLabel,
                        f"_X:{shift['x']:03.0f}",
                        f"_Y:{shift['y']:03.0f}",
                        f"_Z:{shift['z']:03.0f}"))
    # Shift the isocenter of the beams
    for b in beams:
        b.Isocenter.EditIsocenter(Name=iso_name, Position=shift, Color="Purple")
    return shift


def main():
    # Get current patient, case, exam, plan, and beamset
    # TODO: Add dialog for dose to bypass DQA review
    bypass_review = False
    program_success = []
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    try:
        plan = connect.get_current('Plan')

    except Exception:
        logging.debug('A plan is not loaded; plan export options will be disabled')
        UserInterface.WarningBox('This script requires a plan to be loaded')
        sys.exit('This script requires a plan to be loaded')
    #
    # Clear the system clipboard
    # r = Tk()
    # r.withdraw()
    # r.clipboard_clear()

    user_prompt = qa_gui(plan)
    if not user_prompt:
        sys.exit('Dialog canceled')
    # user_prompt = prompt_beamsets(plan)
    beamset_list = user_prompt['-BEAMSETS-']
    bypass_export_check = True
    for b in beamset_list:
        try:
            beamset = plan.BeamSets[b]
            beamset.SetCurrent()
        except Exception as e:
            if 'Changes must be saved' in e.Message:
                patient.Save()
                beamset = plan.BeamSets[b]
                beamset.SetCurrent()

            else:
                logging.warning('Unable to load beamset {}'.format(b))
                sys.exit('Unable to load beamset {}'.format(b))

        # Find the correct verification plan for this beamset
        logging.debug('Looking through verifications plans for plan {} and beamset {}'.format(
            plan.Name, beamset.DicomPlanLabel))

        # Make a qa plan with the name of the beamset
        if 'Tomo' in beamset.DeliveryTechnique:
            qa_plan_name = b.replace('_THI_', '_DQA_')
            if qa_plan_name == b:
                qa_plan_name = qa_plan_name[:-4] + '_DQA'
                logging.info('Beamset {} does not follow THI convention.'.format(
                    beamset.DicomPlanLabel
                ))
            if qa_plan_exists(plan, qa_plan_name):
                qa_plan_name = prompt_qa_name(qa_plan_name)
            verification_plan = make_tomo_qa_plan(plan, beamset, qa_plan_name)
        else:
            qa_plan_name = beamset.DicomPlanLabel
            if qa_plan_exists(plan, qa_plan_name):
                qa_plan_name = prompt_qa_name(qa_plan_name)
            verification_plan = make_vmat_qa_plan(plan, beamset, qa_plan_name)

        qa_beamset = verification_plan.BeamSet
        #
        # Update log
        current_technique = qa_beamset.DeliveryTechnique
        logging.info("Selected Beamset:QAPlan {}:{}"
                     .format(beamset.DicomPlanLabel, qa_beamset.DicomPlanLabel))

        if 'Tomo' in current_technique:
            if user_prompt['-SHIFT PHANTOM-']:
                shift_tomo_iso(verification_plan)
                verification_plan.BeamSet.ComputeDose(DoseAlgorithm='CCDose')
            #
            if not bypass_review:
                connect.await_user_input('Please review and adjust the plan.\n'
                                         + 'Resume the script to export\n'
                                         + 'Final Plan Parameters will be copied to the clipboard')
            comment_str = comment_to_clipboard(beamset, user_prompt, verification_plan)
            logging.info(comment_str.replace("\n", ", "))

            # This plan needs to go to the Delta4 Dicom location and the user
            # needs to manually send it to the RayGateway
            beam_data = {}
            for b in qa_beamset.Beams:
                tomo_result = compute_tomo_params(b)
                beam_data[b.Name] = tomo_result

                logging.debug('Beam {} has GP: {}, CS:{}, Time:{}'.format(
                    b.Name, tomo_result.gantry_period,
                    tomo_result.couch_speed, tomo_result.time))

            if current_technique == 'TomoHelical' and len(beam_data.keys()) == 1:
                formatted_response = '{:.2f}'.format(round(tomo_result.gantry_period, 2))
                logging.info("Gantry period filter to be used. Gantry Period (ss.ff) = {} ".format(
                    formatted_response))
                patient.Save()
                success = DicomExport.send(case=case,
                                           destination='Delta4',
                                           qa_plan=verification_plan,
                                           exam=False,
                                           beamset=False,
                                           ct=False,
                                           structures=False,
                                           plan=False,
                                           plan_dose=False,
                                           beam_dose=False,
                                           ignore_warnings=False,
                                           ignore_errors=False,
                                           bypass_export_check=bypass_export_check,
                                           rename=None,
                                           gantry_period=formatted_response,
                                           filters=['tomo_dqa'],
                                           bar=False)
            elif current_technique == 'TomoDirect':
                # if not bypass_review:
                #     connect.await_user_input('Please review and adjust the plan.\n'
                #                              + 'Resume the script to export\n'
                #                              + 'Final Plan Parameters will be copied to the clipboard')
                # comment_str = comment_to_clipboard(beamset, user_prompt, verification_plan)
                # logging.info("Post User Interactions:" + comment_str.replace("\n", ", "))
                formatted_response = {}
                for k in beam_data.keys():
                    strip_response = '{:.6f}'.format(beam_data[k].couch_speed)
                    # Convert to mm
                    formatted_response[k] = convert_couch_speed_to_mm(strip_response)
                    #
                    logging.info("Couch speed filter to be used. Couch speed for beam:{} is {} (mm/s)"
                                 .format(k, formatted_response[k]))
                patient.Save()
                success = DicomExport.send(case=case,
                                           destination='Delta4',
                                           qa_plan=verification_plan,
                                           exam=False,
                                           beamset=False,
                                           ct=False,
                                           structures=False,
                                           plan=False,
                                           plan_dose=False,
                                           beam_dose=False,
                                           ignore_warnings=False,
                                           ignore_errors=False,
                                           bypass_export_check=bypass_export_check,
                                           rename=None,
                                           couch_speed=formatted_response,
                                           filters=['tomo_dqa'],
                                           bar=False)
                program_success.append(success)
        else:
            if user_prompt['-SHIFT PHANTOM-']:
                shifts = shift_iso(verification_plan)
                if any(shifts.values()) > 0.:
                    verification_plan.BeamSet.ComputeDose(DoseAlgorithm='CCDose')
            if not bypass_review:
                connect.await_user_input('Please review and adjust the plan.\n'
                                         + 'Resume the script to export\n'
                                         + 'Final Plan Parameters will be copied to the clipboard')
            comment_str = comment_to_clipboard(beamset, user_prompt, verification_plan)
            logging.info("Post User Interactions:" + comment_str.replace("\n", ", "))
            patient.Save()
            success = DicomExport.send(case=case,
                                       destination='Delta4',
                                       qa_plan=verification_plan,
                                       exam=False,
                                       beamset=None,
                                       ct=False,
                                       structures=False,
                                       plan=None,
                                       plan_dose=True,
                                       beam_dose=True,
                                       ignore_warnings=True,
                                       ignore_errors=False,
                                       bypass_export_check=bypass_export_check,
                                       rename=None,
                                       couch_speed=None,
                                       filters=[],
                                       bar=False)

            success = True
            program_success.append(success)

    # Finish up
    if all(program_success):
        logging.info('QA script completed successfully')
    else:
        logging.warning('QA script completed with errors')
    # Clean up dialog


if __name__ == '__main__':
    main()
