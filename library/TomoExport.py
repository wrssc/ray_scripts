""" Export Tomo Plan to iDMS

    This script will take an existing, approved Tomo plan and send it to two locations
    for treatment on any of two systems. The main advantage of the script is accurate
    tracking of the delivered fractions from either plan.

    The script works as follows:

    -Send the parent plan to RayGateway

    -Copy the parent_plan to the daughter machine and adjust for equivalence

    -Compute the dose in the daughter plan

    -Send the daughter plan to RayGateway

    Version:
    1.0 Support for multiple beamsets (all assumed to be sent at once).

    TODO: Eliminate the hokey dismissal of the script status as an input. (add delete steps
       to existing script status method?)
    TODO: Support single beamset (partial total plan) export
    TODO: Error catching from raygateway, existing plan error? Try to send anyway

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
__date__ = '07-Nov-2019'
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


def export_tomo_plan(patient, exam, case, parent_plan, parent_beamset, script_status, rs_test_only=False, tr_test_only=False):
    # Script will, determine the current machine set for which this beamset is planned
    # Submit the first plan via export method
    # Copy the beamset using the RS CopyAndAdjust method
    # Recompute dose on Copied plan.

    script_status.close()

    steps = ['Approve and save structures/plan']
    # Set up the workflow steps.
    for b in parent_plan.BeamSets:
        steps.append('Export beamset: {} '.format(b.DicomPlanLabel))
    steps.append('Go to iDMS and approve all primary plans')
    steps.append('Create transfer plan')
    for b in parent_plan.BeamSets:
        steps.append('Compute transfer plan dose for {}'.format(b.DicomPlanLabel))
        steps.append('Approve the transfer plan for {}'.format(b.DicomPlanLabel))
    for b in parent_plan.BeamSets:
        steps.append('Export transfer version of {} to iDMS'.format(b.DicomPlanLabel))
    if tr_test_only:
        steps = []
        for b in parent_plan.Beamsets:
            steps.append('Export transfer version of {} to iDMS'.format(b.DicomPlanLabel))
    status = UserInterface.ScriptStatus(steps=steps,
                                        docstring=__doc__,
                                        help=__help__)

    try:
        if parent_beamset.Review.ApprovalStatus == 'Approved':
            logging.debug('Plan status is approved.')
            status.next_step(text='Plan is approved, proceeding with sending the plan')
        else:
            status.aborted()
            logging.warning('Plans must be approved prior to export')
            sys.exit('Plans must be approved prior to export')
    except AttributeError:
        status.aborted()
        logging.warning('Plans must be approved prior to export')
        sys.exit('Plans must be approved prior to export')

    # Send all parent beamsets
    exported_plans = []
    for b in parent_plan.BeamSets:
        parent_beamset = b
        if rs_test_only:
            success = True
        else:
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
                                       bar=True)

        logging.debug('Status of sending parent plan {}_{}: {}'.format(
            parent_plan.Name, parent_beamset.DicomPlanLabel, success))

        if success:
            exported_plans.append(parent_plan.Name + '_' + parent_beamset.DicomPlanLabel)
            status.next_step(text='Parent plan {}_{} was successfully sent to iDMS.'.format(
                parent_plan.Name, parent_beamset.DicomPlanLabel))
        else:
            status.aborted('Unsuccessful export of parent plan to iDMS. Report error to script admin')
            sys.exit('Unsuccessful sending of parent plan')

    export_names = ''

    for s in exported_plans:
        export_names += s + '\n'

    status.next_step(text='Go to iDMS and approve parent plan(s): \n{}'.format(export_names))

    UserInterface.MessageBox(
        'Please go to the iDMS workstation and approve plan(s): \n{} '.format(export_names) +
        'while transfer plans are made.')
    # Uncomment if users struggle with iDMS approval.
    # connect.await_user_input(
    #     'Please go to the iDMS workstation and approve plan(s): \n{} '.format(
    #         export_names) +
    #     'and continue this script, while I make a transfer plan.')

    # Hard coded machine names
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

    status.next_step(text='Transfer plan being created.')
    case.CopyAndAdjustTomoPlanToNewMachine(
        PlanName=parent_plan.Name,
        NewMachineName=daughter_machine,
        OnlyCopyAndChangeMachine=False)
    logging.info('Transfer plan generated for {}: moving {} to {}'.format(
        parent_plan.Name, parent_machine, daughter_machine))
    status.next_step(text='Transfer plan finished, computing dose.')
    patient.Save()

    # Nutty way of naming plans in RS:
    # Transfer Plan Name = Original Plan Name + '_Transferred'
    # For Beamsets:
    # If the number of characters in the Transfer plan name exceeds 14 char:
    #   Take Transfer Plan Name, crop to 14 chars  and add _1
    # Else If less than 14:
    #   If the number of beamsets is 1 don't add the _1
    #   If the number of beamsets is > 1 add the index, e.g. '_2'
    indx = 0
    daughter_plan_name = parent_plan.Name + '_Transferred'
    daughter_plan = case.TreatmentPlans[daughter_plan_name]
    parent_plan_name = parent_plan.Name
    daughter_plan.Name = parent_plan_name + '_Tr'
    patient.Save()

    transfer_export_plans = []
    # Loop through beamsets in the plan
    for b in parent_plan.BeamSets:
        indx += 1
        parent_beamset_name = b.DicomPlanLabel

        if len(daughter_plan_name) >= 14:
            new_bs_name = daughter_plan_name[:14] + '_' + str(indx)
        else:
            if indx == 1:
                new_bs_name = daughter_plan_name
            else:
                new_bs_name = daughter_plan_name + '_' + str(indx)

        daughter_beamset = PlanOperations.find_beamset(plan=daughter_plan,
                                                       beamset_name=new_bs_name,
                                                       exact=True)
        transfer_export_plans.append(new_bs_name)
        if daughter_beamset is None:
            logging.error('No daughter beamset {} found in {}, exiting'.format(
                parent_beamset_name, daughter_plan.Name))
            sys.exit('Could not find transferred beamset for export')
        elif daughter_beamset.FractionationPattern.NumberOfFractions != b.FractionationPattern.NumberOfFractions:
            logging.error('Retrieved wrong beamset for {}, alert script Admin immediately!'.format(b.DicomPlanLabel))
            sys.exit('Retrieved wrong beamset for {}, alert script Admin immediately!'.format(b.DicomPlanLabel))

        daughter_plan.SetCurrent()
        connect.get_current('Plan')
        daughter_beamset.SetCurrent()
        connect.get_current('BeamSet')
        daughter_beamset.ComputeDose(
            ComputeBeamDoses=True,
            DoseAlgorithm="CCDose",
            ForceRecompute=False)

        daughter_beamset.DicomPlanLabel = parent_beamset_name[:8] + '_Tr' + daughter_machine[-3:]
        patient.Save()

        status.next_step(text='Transfer plan dose computed, setting up dose comparison.')

        # This appears to confuse RayStation. Perhaps when the API is a little better integrated with the UI?
        # ui = connect.get_current('ui')
        # try:
        #     ui.TitleBar.MenuItem['Plan Evaluation'].Click()
        #     ui.TitleBar.MenuItem['Plan Evaluation'].Popup.MenuItem['Plan Evaluation'].Click()
        #     ui.TabControl_ToolBar.TabItem._Approval.Select()
        #     ui.ToolPanel.TabItem['Scripting'].Select()
        # except:
        #     logging.debug('Failed to operate the user interface through script again. Proceeding')

        connect.await_user_input(
            'Compare the transfer beamset: {} and parent beamset {}'
            .format(daughter_beamset.DicomPlanLabel, parent_beamset_name)
            + ' dose distributions and continue, if acceptable approve this beamset.')
        status.next_step(text='Transfer plan accepted')

        # Sending report

    # For multiple beamsets, RayStation will not send a beamset to the raygateway for a transferred plan
    # when a single beamset is approved but the plan is not. Thus, we loop though the beamsets again now that
    # all transfer beamsets are approved.
    for b in parent_plan.BeamSets:

        parent_beamset_name = b.DicomPlanLabel
        parent_plan_iDMS_name = parent_plan.Name + ':' + parent_beamset_name
        new_bs_name = parent_beamset_name[:8] + '_Tr' + daughter_machine[-3:]
        daughter_beamset = PlanOperations.find_beamset(plan=daughter_plan,
                                                       beamset_name=new_bs_name,
                                                       exact=True)
        if daughter_beamset is None:
            logging.error('No daughter beamset {} found in {}, exiting'.format(
                parent_beamset_name, daughter_plan.Name))
            sys.exit('Could not find transferred beamset for export')
        elif daughter_beamset.FractionationPattern.NumberOfFractions != b.FractionationPattern.NumberOfFractions:
            logging.error('Retrieved wrong beamset for {}, alert script Admin immediately!'.format(b.DicomPlanLabel))
            sys.exit('Retrieved wrong beamset for {}, alert script Admin immediately!'.format(b.DicomPlanLabel))

        daughter_plan.SetCurrent()
        connect.get_current('Plan')
        daughter_beamset.SetCurrent()
        connect.get_current('BeamSet')
        status.next_step('Exporting {}'.format(daughter_beamset.DicomPlanLabel))
        if rs_test_only:
            success = True
        else:
            logging.debug('Sending {}_{} to iDMS'.format(parent_plan_iDMS_name,daughter_beamset.DicomPlanLabel))
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
        status.next_step('Sent transfer plan to iDMS')

    if success:
        status.finish(text='DICOM export was successful. You can now close this dialog.')

# if __name__ == '__main__':
#    main()
