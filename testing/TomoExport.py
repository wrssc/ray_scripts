'''Tomo Export Test'''

import sys
import logging
import time
import connect
import UserInterface
import DicomExport
import PlanOperations


def main():
    # Script will, determine the current machine set for which this beamset is planned
    # Submit the first plan via export method
    # Copy the beamset using the RS CopyAndAdjust method
    # Recompute dose on Copied plan.
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
        # success = DicomExport.send(case=case,
        #                            destination='RayGateway',
        #                            exam=exam,
        #                            beamset=parent_beamset,
        #                            ct=True,
        #                            structures=True,
        #                            plan=True,
        #                            plan_dose=True,
        #                            beam_dose=False,
        #                            ignore_warnings=True,
        #                            ignore_errors=False,
        #                            rename=None,
        #                            filters=None,
        #                            machine=None,
        #                            table=None,
        #                            round_jaws=False,
        #                            prescription=False,
        #                            block_accessory=False,
        #                            block_tray_id=False,
        #                            bar=True)

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

        parent_beamset_name = parent_beamset.DicomPlanLabel
        daughter_plan_name = parent_plan.Name + '_Transferred'
        daughter_plan = case.TreatmentPlans[daughter_plan_name]

        daughter_beamset = PlanOperations.find_beamset(plan=daughter_plan,
                                                       beamset_name=parent_beamset_name,
                                                       exact=False)
        daughter_plan.SetCurrent()
        connect.get_current('Plan')
        daughter_beamset.SetCurrent()
        connect.get_current('BeamSet')
        daughter_beamset.ComputeDose(
            ComputeBeamDoses=True,
            DoseAlgorithm="CCDose",
            ForceRecompute=False)
        patient.Save()
        success = DicomExport.send(case=case,
                                   destination='RayGateway',
                                   parent_plan=parent_plan.Name+':'+parent_beamset_name,
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