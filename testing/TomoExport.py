'''Tomo Export Test'''

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
    if 'Tomo' in beamset.DeliveryTechnique:
        machine_1 = 'HDA0488'
        machine_2 = 'HDA0477'
        if machine_1 in beamset.MachineReference['MachineName']:
            parent_machine = machine_1
            daughter_machine = machine_2
        elif machine_2 in beamset.MachineReference['MachineName']:
            parent_machine = machine_2
            daughter_machine = machine_1
        else:
            logging.error('Unknown Tomo System, Aborting')
            sys.exit('Unknown Tomo System: {} Aborting'.format(beamset.MachineReference['MachineName']))

        case.CopyAndAdjustTomoPlanToNewMachine(
                PlanName=plan.Name,
                NewMachineName=daughter_machine,
                OnlyCopyAndChangeMachine=False)


if __name__ == '__main__':
    main()