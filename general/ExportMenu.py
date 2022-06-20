""" DICOM Export Menu

    This script presents a menu to the user to select which data to export and to which
    destination. An option is also available, if a plan is loaded, to choose which
    treatment delivery system to convert the plan to. This conversion is performed
    according to the DICOM filters.

    TODO: DICOM filters are not supported at this time for RS-exports to iDMS,
          filtering is disabled, for Tomo plans.

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
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/DICOM-Export'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import logging
import time

import connect
import UserInterface
import DicomExport
import TomoExport


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

    # Check if plan and/or structure set is approved
    status.next_step(text='Prior to export, this script will check if the plan is approved, and will ask if want to ' +
                          'do so prior to approval if not.')
    time.sleep(1)
    patient.Save()
    ignore = False
    if beamset is not None:
        try:
            if plan.Review is None or plan.Review.ApprovalStatus != 'Approved':
                plan_approved = False

            else:
                plan_approved = True

        except Exception:
            plan_approved = False

        if not plan_approved:
            approve = UserInterface.QuestionBox('The selected plan is not currently approved. Would you like to ' +
                                                'approve it prior to export?', 'Approve Plan')
            if approve.yes:
                ui = connect.get_current('ui')
                ui.TitleBar.MenuItem['Plan evaluation'].Click()
                ui.TitleBar.MenuItem['Plan evaluation'].Popup.MenuItem['Plan evaluation'].Click()
                ui_tab_item = ui.TabControl_ToolBar.TabItem
                ui_tab_item._Approval.Select()
                connect.await_user_input('Approve the plan now, then continue the script')

            else:
                logging.warning('The user chose to export the plan without approval')
                ignore = True

        try:
            if case.PatientModel.StructureSets[exam.Name].ApprovedStructureSets[0].Review.ApprovalStatus != 'Approved':
                struct_approved = False

            else:
                struct_approved = True

        except Exception:
            struct_approved = False

        if not struct_approved:
            approve = UserInterface.QuestionBox('The selected structure set is not currently approved. Would you ' +
                                                'like to approve it prior to export?', 'Approve Structure Set')
            if approve.yes:
                ui = connect.get_current('ui')
                ui.TitleBar.MenuItem['Patient modeling'].Click()
                ui.TitleBar.MenuItem['Patient modeling'].Popup.MenuItem['Structure definition'].Click()
                ui.TabControl_ToolBar.Approval.Select()
                connect.await_user_input('Approve the structure set now, then continue the script')

            else:
                logging.warning('The user chose to export the structure set without approval')
                ignore = True
    for b in DicomExport.machines(beamset):
        logging.debug('list of machines is {}'.format(b))

    # At this point we'll diverge from the two strategies for export
    if 'Tomo' in beamset.DeliveryTechnique:
        status.aborted()
        TomoExport.export_tomo_plan(patient=patient,
                                    exam=exam,
                                    case=case,
                                    parent_plan=plan,
                                    parent_beamset=beamset,
                                    script_status=status,
                                    rs_test_only=False)
        return

    # Prompt user for DICOM export details
    status.next_step(text='In the dialog window that appears, check each DICOM destination that you would like to ' +
                          'export to, what should be exported, and if a beamset is loaded, what treatment delivery ' +
                          'system to convert to.')

    # Define filter descriptions
    if 'Tomo' in beamset.DeliveryTechnique:
        filters = ['Create Transfer Plan']
    else:
        filters = ['Ignore machine name',
                   'Internal Target RPM Gated Treatment (NOT ALIGN RT) ',
                   'Reference Point has no geometric location',
                   'No Filters']
        # 'Convert machine energy (FFF)',
        # 'Set couch to (0, 100, 0)',
        # 'Round jaw positions to 0.1 mm',
        # 'Create reference point',
        # 'Reference point has a geometric location',
        # 'Set block tray and slot ID (electrons only)',
        # '180E'
        # 'PRDR Dose Rate']

    # Initialize options to include DICOM destination and data selection. Add more if a plan is also selected
    inputs = {'a': 'Select which data elements to export:',
              'b': 'Check one or more DICOM destinations to export to:',
              'd': 'Ignore DICOM export warnings:'}
    required = ['a', 'b', 'd']
    types = {'a': 'check', 'b': 'check', 'd': 'combo'}
    options = {'a': ['CT', 'Structures'], 'b': DicomExport.destinations(), 'd': ['Yes', 'No']}
    initial = {'a': ['CT', 'Structures'], 'd': 'No'}
    if ignore:
        initial['d'] = 'Yes'
    if beamset is not None and len(DicomExport.machines(beamset)) > 0:
        options['a'].append('Plan')
        initial['a'].append('Plan')
        options['a'].append('Plan Dose')
        initial['a'].append('Plan Dose')
        options['a'].append('Beam Dose')
        inputs['c'] = 'Select which delivery system to export as:'
        required.append('c')
        types['c'] = 'combo'
        options['c'] = DicomExport.machines(beamset)
        if len(options['c']) == 1:
            initial['c'] = options['c'][0]

        inputs['e'] = 'Export options:'
        types['e'] = 'check'
        options['e'] = filters
        initial['e'] = [False, False, False, False]

    dialog = UserInterface.InputDialog(inputs=inputs,
                                       datatype=types,
                                       options=options,
                                       initial=initial,
                                       required=required,
                                       title='Export Options')
    response = dialog.show()
    if response == {}:
        status.finish('DICOM export was cancelled')
        sys.exit('DICOM export was cancelled')

    # Execute DicomExport.send() given user response
    status.next_step(text='The DICOM datasets are now being exported to a temporary directory, converted to a ' +
                          'treatment delivery system, and sent to the selected destination. Please be patient, as ' +
                          'this can take several minutes...')
    if response['d'] == 'Yes':
        ignore = True
        logging.debug('User choose to ignore warnings during DICOM export')

    if beamset is not None:
        f = []

        # Disable filtering for Tomo and RayGateway
        if 'Tomo' in beamset.DeliveryTechnique:
            if not filters[0] in response['e']:
                f.append('duplicate')
            else:
                f = None
            filters = ['x'] * 7
            response['e'] = [False] * 7
            t = None
            response['c'] = None

        else:
            # No filters if option 3 selected
            if filters[3] in response['e']:
                logging.info('User selected to disable all filters in export')
                f = None
                response['e'] = []
                response['c'] = None
                # PRDR Dose Rate
                prdr_dr = None
                # Set Couch
                t = None
                # No reference point
                create_reference_point = None
                # No reference point location
                ref_point_location = None
                # No block names
                block_accessory = None
                block_tray_id = None
                # TODO: PA setting
                # No autopa
                pa_threshold = None
            else:
                if not filters[0] in response['e']:
                    f.append('machine')
                    logging.info('User will apply machine name change to exported plans')
                if filters[1] in response['e']:
                    rpm_gating = True
                    logging.info('User will apply Use Gated tag to RTPlan')
                else:
                    rpm_gating = False
                    logging.info('No internal gating selected for RTPlan')
                if filters[2] in response['e']:
                    ref_point_location = False
                    logging.info('User disabled reference point location definition in export')
                else:
                    ref_point_location = True
                    logging.info('Reference point location preserved in export')
                #
                # Filters to always be applied
                # PRDR Dose Rate
                if '_PRD_' in beamset.DicomPlanLabel:
                    prdr_dr = True
                else:
                    prdr_dr = False
                # Set Couch
                t = [0, 1000, 0]  # Default
                frameless_beamnames = ['_FSR_', '_SRS_']
                alpha = 7.72  # cm
                beta = 36.39  # cm
                gamma = -0.13  # cm
                if any(a in beamset.DicomPlanLabel for a in frameless_beamnames) and \
                        'HeadFirstSupine' in beamset.PatientSetup.OfTreatmentSetup.PatientPosition:
                    try:
                        #
                        # Determine if the DICOM origin was chosen for the set-up location
                        poi_geometry = beamset.PatientSetup.LocalizationPoiGeometrySource.PoiGeometries[0]
                        poi_coordinates = [poi_geometry.Point.x,
                                           poi_geometry.Point.y,
                                           poi_geometry.Point.z]
                        if all(c == 0 for c in poi_coordinates):
                            iso_lat = beamset.Beams[0].Isocenter.Position.x
                            iso_vert = beamset.Beams[0].Isocenter.Position.y
                            iso_long = beamset.Beams[0].Isocenter.Position.z
                            t = [
                                (gamma - iso_lat) * 10.,
                                (beta - iso_long) * 10.,
                                (alpha + iso_vert) * 10.,  # ARIA imports in mm and displays in cm
                            ]
                        logging.debug('SRS/FSR table positions used {}'.format(t))
                    except:
                        logging.debug('Error setting table positions, default used {}'.format(t))
                # Create a reference point
                create_reference_point = True
                # Convert Block names
                block_accessory = True
                block_tray_id = True
                # TODO: PA setting
                pa_threshold = None

    else:
        f = None
        t = None
        response['e'] = []
        response['c'] = None

    success = DicomExport.send(case=case,
                               destination=response['b'],
                               exam=exam,
                               beamset=beamset,
                               ct='CT' in response['a'],
                               structures='Structures' in response['a'],
                               plan='Plan' in response['a'],
                               plan_dose='Plan Dose' in response['a'],
                               beam_dose='Beam Dose' in response['a'],
                               ignore_warnings=ignore,
                               ignore_errors=False,
                               rename=None,
                               filters=f,
                               machine=response['c'],
                               table=t,
                               # round_jaws=filters[2] in response['e'],
                               prescription=create_reference_point,
                               ref_point_location=ref_point_location,
                               block_accessory=block_accessory,
                               block_tray_id=block_tray_id,
                               pa_threshold=pa_threshold,
                               prdr_dr=prdr_dr,
                               rpm_gating=rpm_gating,
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
