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

import connect
import logging
import UserInterface
import DicomExport
import sys


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

    # Initialize options to include DICOM destination and data selection. Add more if a plan is also selected
    inputs = {'0': 'Select the DQA Plan to export',
              'a': 'Enter the Gantry period as [ss.ff]:',
              'b': 'Check one or more DICOM destinations to export to:'}
    required = ['0', 'a', 'b']
    types = {'0':'combo','b': 'check'}
    options = {'0':matched_qa_plans.keys(),'b': DicomExport.destinations()}
    initial = {}

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
    logging.info("Gantry period filter to be used. Gantry Period (ss.ff) = {} ".format(
        response['a']))
    selected_qa_plan = matched_qa_plans[response['0']]
    logging.info("Selected Beamset:QAPlan {}:{}"
                 .format(beamset.DicomPlanLabel,selected_qa_plan.BeamSet.DicomPlanLabel))
    

    daughter_beamset = selected_qa_plan.BeamSet
    success = DicomExport.send(case=case,
                               destination=response['b'],
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
                               gantry_period=response['a'],
                               filters=['tomo_dqa'],
                               bar=False)

    # Finish up
    if success:
        logging.info('Export script completed successfully')

    else:
        logging.warning('Export script completed with errors')


if __name__ == '__main__':
    main()
