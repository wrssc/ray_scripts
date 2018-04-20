""" DICOM Export Menu

    This script presents a menu to the user to select which data to export and to which
    destinations. An option is also available, if a plan is loaded, to choose which
    treatment delivery system to convert the plan to. This conversion is performed
    according to the DICOM filters.

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/DICOM-Export'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import logging
import time
import connect
import UserInterface
import DicomExport


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

    # Start timer
    tic = time.time()

    # Initialize script status
    status = UserInterface.ScriptStatus(steps=['Approve and save structures/plan',
                                               'Select DICOM data and destination',
                                               'Apply filters and export'],
                                        docstring=__doc__,
                                        help=__help__)

    # Check if plan is approved
    status.next_step(text='Prior to export, this script will check if the plan is approved, and will ask if want to ' +
                          'do so prior to approval if not.')
    patient.Save()
    warnings = True
    if beamset is not None and plan.Review.ApprovalStatus != 'Approved':
        approve = UserInterface.QuestionBox('The selected plan is not currently approved. Would you like to approve ' +
                                            'it prior to export?', 'Approve Plan')
        if approve.yes:
            connect.await_user_input('Approve the plan now, then continue the script')

        else:
            logging.warning('The user chose to export the plan without approval')
            warnings = False

    # Check if structure set is approved
    if beamset is not None:
        try:
            if case.PatientModel.StructureSets[exam.Name].ApprovedStructureSets[0].Review.ApprovalStatus == 'Approved':
                struct_approval = True

            else:
                struct_approval = False

        except Exception:
            struct_approval = False

        if not struct_approval:
            approve = UserInterface.QuestionBox('The selected structure set is not currently approved. Would you ' +
                                                'like to approve it prior to export?', 'Approve Structure Set')
            if approve.yes:
                connect.await_user_input('Approve the structure set now, then continue the script')

            else:
                logging.warning('The user chose to export the structure set without approval')
                warnings = False

    # Prompt user for DICOM export details
    status.next_step(text='In the dialog window that appears, check each DICOM destination that you would like to ' +
                          'export to, what should be exported, and if a beamset is loaded, what treatment delivery ' +
                          'system to convert to.')
    inputs = {}
    options = {}
    initial = {}
    types = {}
    required = []

    # Display option to select DICOM destinations
    inputs['a'] = 'Check one or more DICOM destinations to export to:'
    required.append('a')
    types['a'] = 'check'
    options['a'] = DicomExport.destinations()

    # Display option to select data to export
    inputs['b'] = 'Select which data elements to export:'
    required.append('b')
    types['b'] = 'check'
    options['b'] = ['CT', 'Structures']
    initial['b'] = ['CT', 'Structures']

    # If a beamset is also loaded, allow other options
    if beamset is not None:
        options['b'].append('Plan')
        initial['b'].append('Plan')
        options['b'].append('Plan Dose')
        initial['b'].append('Plan Dose')
        options['b'].append('Beam Dose')
        inputs['c'] = 'Select which delivery system to export as:'
        required.append('c')
        types['c'] = 'combo'
        options['c'] = DicomExport.machines(beamset)

    dialog = UserInterface.InputDialog(inputs=inputs, options=options, initial=initial, required=required)
    response = dialog.show()
    if response == {}:
        status.finish('DICOM export was cancelled')
        sys.exit('DICOM export was cancelled')

    if 'Plan' not in response['b'] and 'Plan Dose' not in response['b'] and 'Beam Dose' not in response['b']:
        beamset = None

    # Execute DicomExport.send() given user response
    status.next_step(text='The DICOM datasets are now being exported to a temporary directory, converted to a ' +
                          'treatment delivery system, and sent to each selected destination. Please be patient, as ' +
                          'this can take several minutes...')
    success = DicomExport.send(case=case,
                               destination=response['a'],
                               exam=exam,
                               beamset=beamset,
                               structures='Structures' in response['b'],
                               plandose='Plan Dose' in response['b'],
                               beamdose='Beam Dose' in response['b'],
                               ignore_warnings=warnings,
                               ignore_errors=False,
                               anonymize=None,
                               filters=['machine', 'energy'],
                               machine=response['c'],
                               bar=True)

    # Finish up
    if success:
        logging.info('Export script completed successfully in {:.3f} seconds'.format(time.time() - tic))
        status.finish(text='DICOM export was successful. You can now close this dialog.')

    else:
        logging.warning('Export script completed with errors in {:.3f} seconds'.format(time.time() - tic))
        status.finish(text='DICOM export finished but with errors. You can now close this dialog.')


if __name__ == '__main__':
    main()
