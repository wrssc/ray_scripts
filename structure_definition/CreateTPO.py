""" Approve Contours and Create TPO

    This script is for physicians to approve their contour set for planning and to
    generate a Treatment Planning Order (TPO) for import into ARIA. As part of TPO
    creation, this script will also add clinical goals and initialize the treatment
    plan(s).

    Finally, dose is computed and then exported after each beamset is created. The DICOM
    export path is set in the configuration settings below. The option to only create
    beams is available by un-checking the "calculate" and "export" runtime options from
    the configuration dialog box.

    This program is free software: you can redistribute it and/or modify it under the
    terms of the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
    PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this
    program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Create-TPO'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import sys
import os
import connect
import UserInterface
import logging
import time

# Define the protocol XML directory
protocol_folder = '../protocols'


def main():

    # Get current patient, case, and exam
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    # Start timer
    tic = time.time()

    # Start script status
    status = UserInterface.ScriptStatus(steps=['Enter plan information for TPO',
                                               'Clean up structure list',
                                               'Approve structures',
                                               'Initialize plan',
                                               'Set clinical goals',
                                               'Generate TPO'],
                                        docstring=__doc__,
                                        help=__help__)

    # Display input dialog box for TPO
    status.next_step(text='In order to approve the plan and create a TPO, please fill out the displayed form ' +
                          'with information about the plan. Once completed, click Continue.')

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(os.path.join(os.path.dirname(__file__), protocol_folder))
    response = tpo.show(case=case, exam=exam)
    if response == {}:
        status.finish('This script was cancelled')

    # Re-name/organize structures based on TPO form
    status.next_step(text='The structures are now being renamed and organized based on your input...')
    changes = 0
    for roi in case.PatientModel.RegionsOfInterest:
        approved = False
        for a in case.PatientModel.StructureSets[exam.Name].ApprovedStructureSets:

            try:
                if a.ApprovedRoiStructures[roi.Name].HasContours() and a.Review.ApprovalStatus == 'Approved':
                    approved = True
                    logging.debug('Structure {} was approved by {} and therefore will not be modified'.
                                  format(roi.Name, a.Review.ReviewerName))

            except Exception:
                    logging.debug('Structure {} is not list approved by {}'.format(roi.Name, a.Review.ReviewerName))

        if not approved:
            if roi.Name in response.structures.keys():
                if response.structures[roi.Name] in response.targets.keys() and \
                        response.targets[response.structures[roi.Name]]['use']:
                    logging.debug('Structure {} renamed to {} and set to Target'.format(roi.Name,
                                                                                        response.structures[roi.Name]))
                    roi.Name = response.structures[roi.Name]
                    roi.OrganData.OrganType = 'Target'
                    roi.ExcludeFromExport = False
                    changes += 1

                elif response.structures[roi.Name] in response.oars.keys() and \
                        response.oars[response.structures[roi.Name]]['use']:
                    logging.debug('Structure {} renamed to {} and set to OAR'.format(roi.Name,
                                                                                     response.structures[roi.Name]))
                    roi.Name = response.structures[roi.Name]
                    roi.OrganData.OrganType = 'OrganAtRisk'
                    roi.ExcludeFromExport = False
                    changes += 1

                else:
                    logging.debug('Structure {} is not used, set to Other'.format(roi.Name))
                    roi.OrganData.OrganType = 'Other'
                    roi.ExcludeFromExport = True
                    changes += 1

            else:
                logging.debug('Structure {} is not in TPO template, set to Other'.format(roi.Name))
                roi.OrganData.OrganType = 'Other'
                roi.ExcludeFromExport = True
                changes += 1

    # Prompt user to approve structures
    status.next_step(text='You will now be prompted to approve the structure set. Once completed, continue the script.')
    if changes > 0:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient Modeling'].Click()
        ui.TitleBar.MenuItem['Patient Modeling'].Popup.MenuItem['Structure Definition'].Click()
        ui.TabControl_ToolBar.Approval.Select()
        connect.await_user_input('Approve the structure set now, then continue the script')

    # Create new plan (ICDa-z Protocol) and beam sets (prefix_mod_R0A0)
    status.next_step(text='A new plan will now be created and populated with the TPO template clinical goals...')
    patient.Save()
    for a in range(1, 26):
        plan_name = '{}{} {}'.format(response['diagnosis'][0], ord(64+a).lower(), response['order'])
        try:
            logging.debug('Plan name already exists: ' + case.TreatmentPlans[plan_name].Name)

        except Exception:
            break

    case.AddNewPlan(PlanName=plan_name)

    """ Beamset name
    name = 'Plan'
    for o in response['xml'].findall('order'):
        if o.find('name') == response['order'] and o.find('prefix') is not None:
            name = o.find('prefix').text
            break
    if response['modality'] == 'VMAT':
        name += '_VMA'

    elif response['modality'] == '3DCRT':
        name += '_3DC'

    elif response['modality'] == 'Electrons':
        name += '_ELE'

    name += '_R0A0'
    """



    #
    # TODO: steps 5 through 6
    #

    # Finish up
    patient.Save()
    time.sleep(1)
    logging.debug('Script completed successfully in {:.3f} seconds'.format(time.time() - tic))
    status.finish('Script completed successfully. You may now import the saved TPO into ARIA and notify dosimetry ' +
                  'that this case is ready for planning.')


if __name__ == '__main__':
    main()
