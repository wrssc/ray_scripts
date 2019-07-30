""" Modify Tomo DQA Plan

    Prompts user for Gantry Period for running a TomoDQA

    Version:
    1.0 Load targets as filled. Normalize isodose to prescription, and try to normalize to the
        maximum dose in External or External_Clean

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
__date__ = '29-Jul-2019'
__version__ = '1.0.0'
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

import os
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
        plan = None
        beamset = None

    tic = time.time()
    # Find the correct verification plan for this beamset
    try:
        indx = 0
        bs_name = str(beamset.DicomPlanLabel)
        qa_name = str(plan.VerificationPlans[indx].ForTreatmentPlan.Name)

        while qa_name != bs_name:
            indx += 1

        index_not_found = False

    except IndexError:
        logging.debug('All plans searched through indx = {}'.format(indx))
        index_not_found = True

    if index_not_found:
        logging.warning("verification plan for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")

    else:
        qa_plan = plan.VerificationPlans[indx]
        logging.info('verification plan found, exporting {} for beamset {}'.format(
                plan.VerificationPlans[indx].BeamSet.DicomPlanLabel, beamset.DicomPlanLabel))

    # Initialize options to include DICOM destination and data selection. Add more if a plan is also selected
    inputs = {'a': 'Enter the Gantry period as [ss.ff]:',
              'b': 'Check one or more DICOM destinations to export to:'}
    required = ['a', 'b']
    types = {'b': 'check'}
    options = {'b': DicomExport.destinations()}
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

    success = DicomExport.send(case=case,
                               destination=response['b'],
                               qa_plan=qa_plan,
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
        logging.info('Export script completed successfully in {:.3f} seconds'.format(time.time() - tic))

    else:
        logging.warning('Export script completed with errors in {:.3f} seconds'.format(time.time() - tic))


if __name__ == '__main__':
    main()


