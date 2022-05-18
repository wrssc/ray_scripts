""" Export Tomo DQA Plan to QA Destination

    The delta4 software needs the gantry period to load the plan, however
    it doesn't live as a native object in RS. The user is prompted to enter it
    then the data is exported to a temporary directory and this information is
    input.
    This script:
    -Checks for a beamset to be loaded
    -Finds all QA plans which have the OfRadiationSet-DicomPlanLabel matching
     the current beamset.
    -Prompts the user to choose the desired plan for export, gantry period and
     dicom destination
    -Exports using the ValidationPlan.ScriptableQADicomExport method.
    TODO: When export to the RayGateWay is supported using the above method,
          enable multiple destinations to be selected.

    Version:
    1.0 Modify RS RTPlans to include a gantry period, needed by the Delta4 software,
        then send them to the specified destination with scp.

    1.0.1 Modify to allow for multiple qa plans. Prompt user for gantry period and directly
          send data. User is now asked to match the treatment plan they wish to send and no longer
          need delete multiple plans.

    1.0.2 Always bypass the diff checking on the tomo DQA plans. For long treatment fields
          this was taking a really long time and causing the association to time out.

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
import connect
import logging
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
        beamset = connect.get_current('BeamSet')

    except Exception:
        logging.debug('A plan and/or beamset is not loaded; plan export options will be disabled')
        UserInterface.WarningBox('This script requires a plan and beamset to be loaded')
        sys.exit('This script requires a plan and beamset to be loaded')

    # Find the correct verification plan for this beamset
    logging.debug('Looking through verifications plans for plan {} and beamset {}'.format(
        plan.Name, beamset.DicomPlanLabel))

    verification_plans = plan.VerificationPlans
    matched_qa_plans = {}
    # TODO: Extend for multiple verification plans
    for vp in verification_plans:
        logging.debug('vp is {}'.format(vp.BeamSet.DicomPlanLabel))
        if vp.OfRadiationSet.DicomPlanLabel == beamset.DicomPlanLabel:
            matched_qa_plans[vp.BeamSet.DicomPlanLabel] = vp

    if not matched_qa_plans:
        logging.warning("verification plan for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")

    #
    # Initialize the dialog
    required = ['0','00']
    types = {'0':'combo', '00': 'check'}
    # Initialize options to include DICOM destination and data selection. Add more if a plan is also selected
    options = {'0':matched_qa_plans.keys(),'00': DicomExport.destinations()}
    initial = {}
    inputs = {}
    inputs['0'] = 'Select the DQA Plan to export'
    inputs['00'] = 'Check one or more DICOM destinations to export to:'
    # if current_technique == 'TomoHelical':
    #     inputs['b'] = 'Enter the Gantry period as [ss.ff]:'
    #     types ['b'] = 'text'
    # elif current_technique =='TomoDirect':
    #     i = 0
    #     key_list = []
    #     for b in beamset.Beams:
    #         key_list.append(b.Name)
    #         inputs[b.Name] = 'Enter the couch speed of beam: ' + b.Name + ' in [cm/sec]:'
    #         types[b.Name] = 'text'
    #         required.append(b.Name)
    #         i += 1
    # Build the dialog
    dialog = UserInterface.InputDialog(inputs=inputs,
                                       datatype=types,
                                       options=options,
                                       initial=initial,
                                       required=required,
                                       title='Export Options')
    response = dialog.show()
    if response == {}:
        sys.exit('DICOM export was cancelled')
    # Link root to selected protocol ElementTree
    bypass_export_check =True
    selected_qa_plan = matched_qa_plans[response['0']]
    daughter_beamset = selected_qa_plan.BeamSet
    current_technique = daughter_beamset.DeliveryTechnique
    logging.info("Selected Beamset:QAPlan {}:{}"
                 .format(beamset.DicomPlanLabel,daughter_beamset.DicomPlanLabel))

    beam_data = {}
    for b in daughter_beamset.Beams:
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
                               destination=response['00'],
                               qa_plan=selected_qa_plan,
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
                               destination=response['00'],
                               qa_plan=selected_qa_plan,
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


    # Finish up
    if success:
        logging.info('Export script completed successfully')

    else:
        logging.warning('Export script completed with errors')


if __name__ == '__main__':
    main()
