""" Tomo Plan transfer

    A temporary plan transfer module that will unfortunately not allow for DQA plans to be properly exported
    due to a plan name conflict. Main purpose is to allow an existing patient plan to be copied as a transfer
    (daughter - nonPrimary plan in iDMS).

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
import time
import connect
import UserInterface
import DicomExport
import PlanOperations
import BeamOperations


def main():
    # Script will, determine the current machine set for which this beamset is planned
    # Submit the first plan via export method
    # Copy the beamset using the RS CopyAndAdjust method
    # Recompute dose on Copied plan.
    # TODO: Determine the number of beamsets belonging to this plan, and if they are approved, send all

    # Get current patient, case, exam, plan, and beamset
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    try:
        parent_plan = connect.get_current('Plan')
        parent_beamset = connect.get_current('BeamSet')

    except Exception:
        logging.debug('A plan and/or beamset is not loaded; plan export options will be disabled')
        parent_plan = None
        parent_beamset = None

    if 'Tomo' in parent_beamset.DeliveryTechnique:
        success = True

        logging.debug('Status of sending parent plan: {}'.format(success))
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
        daughter_plan.Name = parent_plan.Name[:8] + '_Tr'
        daughter_beamset.DicomPlanLabel = parent_beamset_name[:8] + '_Tr' + daughter_machine[-3:]
        # Cannot set DSP's once the plan is created or a DICOM failure occurs
        # BeamOperations.set_dsp(plan=daughter_plan, beam_set=daughter_beamset)

        patient.Save()
        # Plans must be approved in iDMS prior to sending the transfer plan.
        connect.await_user_input(
            'Please go to the iDMS workstation and approve plan {}, '.format(parent_plan.Name) +
            'Then continue script')
        parent_plan_iDMS_name = parent_plan.Name + ':' + parent_beamset_name
        # daughter_beamset.SendTransferredPlanToRayGateway(RayGatewayTitle='RAYGATEWAY',PreviousBeamSet=parent_plan_iDMS_name,OriginalBeamSet=parent_plan_iDMS_name,IgnorePreConditionWarnings=True)

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


if __name__ == '__main__':
    main()
