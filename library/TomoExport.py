""" Export Tomo Plan to iDMS

    This script will take an existing, approved Tomo plan and send it to two locations
    for treatment on any of two systems. The main advantage of the script is accurate
    tracking of the delivered fractions from either plan. The script works as follows:
    -Send the parent plan to RayGateway
    -Copy the parent_plan to the daughter machine and adjust for equivalence
    -Compute the dose in the daughter plan
    -Send the daughter plan to RayGateway

    Version:
    1.0


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
__help__ = ''
__credits__ = []

import sys
import logging
import connect
import UserInterface
import DicomExport
import PlanOperations


def export_tomo_plan(patient, exam, case, parent_plan, parent_beamset, script_status):
    # Script will, determine the current machine set for which this beamset is planned
    # Submit the first plan via export method
    # Copy the beamset using the RS CopyAndAdjust method
    # Recompute dose on Copied plan.
    # TODO: Determine the number of beamsets belonging to this plan, and if they are approved, send all

    status = UserInterface.ScriptStatus(steps=['Approve and save structures/plan',
                                               'Send Primary plan to iDMS',
                                               'Go to iDMS and set Primary plan to approved',
                                               'Create Transfer Plan',
                                               'Compute the transfer plan dose',
                                               'Approve the transfer plan',
                                               'Create a transfer plan report',
                                               'Export the transfer plan to iDMS'],
                                        docstring=__doc__,
                                        help=__help__)
    if parent_beamset.Review.ApprovalStatus == 'Approved':
        logging.debug('Plan status is approved.')
        status.next_step(text='Plan is approved, proceeding with sending the plan')
    else:
        status.aborted()
        logging.warning('Plans must be approved prior to export')
        sys.exit('Plans must be approved prior to export')

    status.next_step(text='Proceeding with sending the parent plan'.format(parent_plan.Name))

    success = DicomExport.send(case=case,
                               destination='RayGateway',
                               exam=exam,
                               beamset=parent_beamset,
                               ct=True,
                               structures=True,
                               plan=True,
                               plan_dose=True,
                               beam_dose=False,
                               ignore_warnings=True,
                               ignore_errors=False,
                               rename=None,
                               filters=None,
                               machine=None,
                               table=None,
                               round_jaws=False,
                               prescription=False,
                               block_accessory=False,
                               block_tray_id=False,
                               bar=False)

    logging.debug('Status of sending parent plan: {}'.format(success))

    if success:
        status.next_step(text='Parent plan was successfully sent to iDMS. Go to iDMS and approve parent plan')
        connect.await_user_input(
            'Please go to the iDMS workstation and approve plan {}, '.format(parent_plan.Name) +
            'continue this script, while I make a transfer plan.')
    else:
        status.aborted('Unsuccessful export of parent plan to iDMS. Report error to script admin')
        sys.exit('Unsuccessful sending of parent plan')

    machine_1 = 'HDA0488'
    machine_2 = 'HDA0477'
    if machine_1 in parent_beamset.MachineReference['MachineName']:
        parent_machine = machine_1
        daughter_machine = machine_2
    elif machine_2 in parent_beamset.MachineReference['MachineName']:
        parent_machine = machine_2
        daughter_machine = machine_1
    else:
        logging.error('Unknown Tomo System, Aborting')
        sys.exit('Unknown Tomo System: {} Aborting'.format(parent_beamset.MachineReference['MachineName']))

    case.CopyAndAdjustTomoPlanToNewMachine(
        PlanName=parent_plan.Name,
        NewMachineName=daughter_machine,
        OnlyCopyAndChangeMachine=False)
    status.next_step(text='Transfer plan created.')
    patient.Save()

    parent_beamset_name = parent_beamset.DicomPlanLabel
    daughter_plan_name = parent_plan.Name + '_Transferred'
    daughter_plan = case.TreatmentPlans[daughter_plan_name]

    daughter_beamset = PlanOperations.find_beamset(plan=daughter_plan,
                                                   beamset_name=parent_plan.Name[:8],
                                                   exact=False)
    if daughter_beamset is None:
        logging.error('No daughter beamset {} found in {}, exiting'.format(
            parent_beamset_name, daughter_plan.Name))
        sys.exit('Could not find transferred beamset for export')

    daughter_plan.SetCurrent()
    connect.get_current('Plan')
    daughter_beamset.SetCurrent()
    connect.get_current('BeamSet')
    daughter_beamset.ComputeDose(
        ComputeBeamDoses=True,
        DoseAlgorithm="CCDose",
        ForceRecompute=False)
    status.next_step(text='Transfer plan dose computed.')
    daughter_plan.Name = parent_plan.Name[:8] + '_Tr'
    daughter_beamset.DicomPlanLabel = parent_beamset_name[:8] + '_Tr' + daughter_machine[-3:]
    # Cannot set DSP's once the plan is created or a DICOM failure occurs
    # BeamOperations.set_dsp(plan=daughter_plan, beam_set=daughter_beamset)

    patient.Save()
    # Plans must be approved in iDMS prior to sending the transfer plan.
    connect.await_user_input(
        'Warning go to the iDMS workstation and approve plan {} if you have not done so'.format(parent_plan.Name) +
        ' then continue script')
    parent_plan_iDMS_name = parent_plan.Name + ':' + parent_beamset_name

    ui = connect.get_current('ui')
    ui.TitleBar.MenuItem['Plan Evaluation'].Click()
    ui.TitleBar.MenuItem['Plan Evaluation'].Popup.MenuItem['Plan Evaluation'].Click()
    ui.TabControl_ToolBar.ToolBarGroup['_0'].RayPanelDropDownItem.DropDownButton_Select_layout.Click()
    connect.await_user_input('Compare the transfer and parent plan dose distributions and continue')
    ui.TabControl_ToolBar.TabItem._Approval.Select()
    ui.ToolPanel.TabItem['Scripting'].Select()
    connect.await_user_input('Approve the plan now, then continue the script')

    # Sending report
    status.next_step('Transfer plan approved. Creating transfer plan report')
    status.next_step('Sending transfer plan to iDMS')

    success = DicomExport.send(case=case,
                               destination='RayGateway',
                               parent_plan=parent_plan_iDMS_name,
                               exam=exam,
                               beamset=daughter_beamset,
                               ct=True,
                               structures=True,
                               plan=True,
                               plan_dose=True,
                               beam_dose=False,
                               ignore_warnings=True,
                               ignore_errors=False,
                               rename=None,
                               filters=None,
                               machine=None,
                               table=None,
                               round_jaws=False,
                               prescription=False,
                               block_accessory=False,
                               block_tray_id=False,
                               bar=True)

# if __name__ == '__main__':
#    main()
