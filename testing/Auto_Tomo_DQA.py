""" Make Tomo DQA Plans

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
    TODO: When export to the RayGateWay is supported using the above method,
          enable multiple destinations to be selected.

    Version:

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
__date__ = '25-Sep-2020'
__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8b.SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import sys
from collections import namedtuple
import logging
import re
import numpy as np
import connect
import UserInterface
import DicomExport

TomoParams = namedtuple('TomoParams',['gantry_period', 'time', 'couch_speed', 'total_travel'])

def compute_couch_travel_helical(beam):
    # Take first and last segment, compute distance
    number_of_segments = len(beam.Segments)
    first_segment = beam.Segments[0]
    last_segment = beam.Segments[number_of_segments-1]
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
    last_segment = beam.Segments[number_of_segments-1]
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
    convert_input = float_input * 10 # cm-> mm
    return convert_input

def make_qa_plan_name(name):
    # Should replace PRD, THI with DQA
    search_re = re.compile(r'(THI)|(PRD)')
    return re.sub(search_re,'DQA',name)

def qa_plan_exists(plan, qa_plan_name):
    # Return true if plan exists false otherwise
    verification_plans = plan.VerificationPlans
    for vp in verification_plans:
        if vp.OfRadiationSet.DicomPlanLabel == qa_plan_name:
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
            PhantomName=r"Delta4 (TrueBeam)",
            PhantomId=r"ZZIMRTQA",
            QAPlanName=qa_plan_name,
            IsoCenter={ 'x': 0, 'y': 0, 'z': 0 },
            DoseGrid={ 'x': 0.2, 'y': 0.2, 'z': 0.2 },
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=0,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=None,
            MotionSynchronizationTechniqueSettings={
                'DisplayName': None,
                'MotionSynchronizationSettings': None,
                'RespiratoryIntervalTime': None,
                'RespiratoryPhaseGatingDutyCycleTimePercentage': None },
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
            PhantomName=r"Delta4_HFS_0X_0Y TomoHDA",
            PhantomId=r"20191017PMH-QA",
            # PhantomName=r"TomoHDA Delta4_HFS_X0_Y0",
            # PhantomId=r"20191004PMH-D4QA",
            QAPlanName=qa_plan_name,
            IsoCenter={ 'x': 0, 'y': 0, 'z': 0 },
            DoseGrid={ 'x': 0.2, 'y': 0.2, 'z': 0.2 },
            GantryAngle=None,
            CollimatorAngle=None,
            CouchRotationAngle=None,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=None,
            MotionSynchronizationTechniqueSettings={
                'DisplayName': None,
                'MotionSynchronizationSettings': None,
                'RespiratoryIntervalTime': None,
                'RespiratoryPhaseGatingDutyCycleTimePercentage': None },
            RemoveCompensators=False,
            EnableDynamicTracking=False)
        qa_plan = find_qa_plan(plan, beamset, qa_plan_name)
        return qa_plan
    except Exception as e:
        UserInterface.WarningBox('QA Plan failed to create: {}'.format(e))
        sys.exit('QA Plan failed to create {}'.format(e))


def prompt_qa_name(qa_plan_name):
    # Prompt the user for a qa plan name and return response
    required = ['Name']
    types = {'Name':'text'}
    initial = {}
    options = {}
    inputs={}
    inputs['Name'] = 'Provide Desired DQA Plan Name'
    title = 'DQA Plan Name '+ qa_plan_name + 'is Taken'
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

def prompt_beamsets(plan):
    # Prompt the user for all beamsets that need qa plan
    #
    # Find all beamsets in this plan
    names = []
    for b in plan.BeamSets:
        names.append(b.DicomPlanLabel)
    # Initialize the dialog
    required = ['0',]
    types = {'0':'check' }
    # Initialize options to include DICOM destination and data selection. Add more if a plan is also selected
    options = {'0':names}
    initial = {}
    inputs = {}
    inputs['0'] = 'Select the beamsets needing a dqa plan'
    dialog = UserInterface.InputDialog(inputs=inputs,
                                       datatype=types,
                                       options=options,
                                       initial=initial,
                                       required=required,
                                       title='Select Beamsets For DQA')
    response = dialog.show()
    if response == {}:
        sys.exit('DICOM export was cancelled')
    else:
        return response['0']

def find_dose_centroid(vp, beamset, percent_max=None):
    """
    Find the centroid of points at or above 80% or percent_max of the maximum dose in the grid
    :param plan: current plan
    :param beam_set: current beamset
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
    #logging.info('Tolerance used for the supplied dose {} agreement was > {} Gy'.format(rx, rx * t_init))

    #logging.debug('Finding centroid of matching dose points')
    length = rx_points.shape[0]  # total number of points
    n_x_pos = rx_points[:, 0] * xsize + xcorner + xsize / 2  # points in RS coordinates
    n_y_pos = rx_points[:, 1] * ysize + ycorner + ysize / 2
    n_z_pos = rx_points[:, 2] * zsize + zcorner + zsize / 2
    xpos = np.sum(n_x_pos) / length  # average position
    ypos = np.sum(n_y_pos) / length
    zpos = np.sum(n_z_pos) / length

    return {'x':xpos, 'y':ypos, 'z':zpos}

def shift_tomo_iso(verification_plan):
    a = find_dose_centroid(vp=verification_plan,
                          beamset=verification_plan.BeamSet,
                          percent_max = 80)
    shift = {'x': -1.* a['x'], 'y': -1.* a['y'], 'z': 0. }
    beams = verification_plan.BeamSet.Beams
    for b in beams:
        b.Isocenter.EditIsocenter(Position=shift)

def shift_iso(verification_plan, percent_dose_region = 80.):
    # Using the input verification plan object find the center of the
    # percent_dose_region * max dose volume.
    # If the center is more than 90 mm from the center of the phantom, shift longitudinally.
    # Find the closest shift in 5 cm intervals to put the detector dense region in the
    # center of the high isodose.
    shift = {}
    beams = verification_plan.BeamSet.Beams
    a = find_dose_centroid(vp=verification_plan,
                          beamset=verification_plan.BeamSet,
                          percent_max = percent_dose_region)
    x_grid = [-150., -100., -50., 0., 50., 100., 150.]
    y_grid = [-150., -100., -50., 0., 50., 100., 150.]
    z_grid = [-90., 0., 90.]
    shift['x'] = min(x_grid, key=lambda x:abs(x-a['x']))
    shift['y'] = min(y_grid, key=lambda x:abs(x-a['y']))
    shift['z'] = min(z_grid, key=lambda x:abs(x-a['z']))
    logging.info('During DQA creation, the center of the dose profile was at [x,y,z]: [{:.2f},{:.2f},{:.2f}]. '.format(a['x'],a['y'],a['z'])
                 +'Closest shift coordinates are [x,y,z]: [{},{},{}]'.format(shift['x'],shift['y'],shift['z']))
    #shift = {'x':a['x'], 'y':a['y']}
    # shift if 90 mm is closer to center
    #if a['z'] > 90.:
    #    shift['z'] = 90.
    #elif a['z'] < -90.:
    #    shift['z'] = -90.
    #else:
    #    shift['z'] = 0.
    # Shift the isocenters
    for b in beams:
        b.Isocenter.EditIsocenter(Position=shift)
    return shift


def main():
    # Get current patient, case, exam, plan, and beamset
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

    beamset_list = prompt_beamsets(plan)
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


        qa_plan_name = beamset.DicomPlanLabel
        if qa_plan_exists(plan,qa_plan_name):
            qa_plan_name = prompt_qa_name(qa_plan_name)
        # Make a qa plan with the name of the beamset
        if 'Tomo' in beamset.DeliveryTechnique:
            verification_plan = make_tomo_qa_plan(plan, beamset, qa_plan_name)
        else:
            verification_plan = make_vmat_qa_plan(plan, beamset, qa_plan_name)

        bypass_export_check =True
        qa_beamset = verification_plan.BeamSet
        current_technique = qa_beamset.DeliveryTechnique
        logging.info("Selected Beamset:QAPlan {}:{}"
                     .format(beamset.DicomPlanLabel,qa_beamset.DicomPlanLabel))
        if 'Tomo' in current_technique:
            shift_tomo_iso(verification_plan)
            verification_plan.BeamSet.ComputeDose(DoseAlgorithm='CCDose')
            # This plan needs to go to the Delta4 Dicom location and the user
            # needs to manually send it to the RayGateway
            beam_data = {}
            for b in qa_beamset.Beams:
                TomoResult=compute_tomo_params(b)
                beam_data[b.Name] = TomoResult

                logging.debug('Beam {} has GP: {}, CS:{}, Time:{}'.format(
                    b.Name, TomoResult.gantry_period,
                    TomoResult.couch_speed, TomoResult.time))

            if current_technique == 'TomoHelical' and len(beam_data.keys()) == 1:
                formatted_response = '{:.2f}'.format(round(TomoResult.gantry_period, 2))
                logging.info("Gantry period filter to be used. Gantry Period (ss.ff) = {} ".format(
                    formatted_response))
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
                                    bypass_export_check = bypass_export_check,
                                    rename=None,
                                    gantry_period=formatted_response,
                                    filters=['tomo_dqa'],
                                    bar=False)
            elif current_technique == 'TomoDirect':
                formatted_response = {}
                for k in beam_data.keys():
                    strip_response = '{:.6f}'.format(beam_data[k].couch_speed)
                    # Convert to mm
                    formatted_response[k] = convert_couch_speed_to_mm(strip_response)
                    #
                    logging.info("Couch speed filter to be used. Couch speed for beam:{} is {} (mm/s)"
                                .format(k, formatted_response[k]))
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
                                    bypass_export_check = bypass_export_check,
                                    rename=None,
                                    couch_speed=formatted_response,
                                    filters=['tomo_dqa'],
                                    bar=False)
        else:
            shifts = shift_iso(verification_plan)
            if any(shifts.values()) > 0.:
                verification_plan.BeamSet.ComputeDose(DoseAlgorithm='CCDose')

    # Finish up
    if success:
        logging.info('Export script completed successfully')

    else:
        logging.warning('Export script completed with errors')


if __name__ == '__main__':
    main()
