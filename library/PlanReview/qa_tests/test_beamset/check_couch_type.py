from PlanReview.review_definitions import TOMO_DATA, TRUEBEAM_DATA, FAIL, \
    PASS, ALERT
from PlanReview.utils import get_machine
from typing import NamedTuple, Tuple


def check_couch_type(rso: NamedTuple) -> Tuple[str, str]:
    """Check Couch Type
       Checks if the correct couch support structures are present in the
       patient plan based on the machine type.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                              [case ('RayStation Case Object'),
                               exam ('RayStation Exam Object'),
                               plan ('RayStation Plan Object'),
                               beamset ('RayStation BeamSet Object'),
                               db ('RayStation Database Object')]

        Returns:
            Tuple[str, str]: First element is the status (PASS/FAIL/ALERT),
                             Second element is the message string.

        Pseudocode:
        1. Retrieve the list of ROI names from the case
        2. Determine the machine name from the first beam of the beamset
        3. Identify the wrong and correct supports based on the machine type
        4. Build an appropriate message string based on the support structures
           found
        5. Determine the result (PASS/FAIL/ALERT)
        6. Return the result and message string

        Test Patients:
            Pass: Patient Needed
            Fail: Patient Needed
    """
    # Abbreviate geometries
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    roi_list = [r.OfRoi.Name for r in rg]
    beam = rso.beamset.Beams[0]
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    wrong_supports = []
    correct_supports = []
    if current_machine.Name in TRUEBEAM_DATA['MACHINES']:
        wrong_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
    elif current_machine.Name in TOMO_DATA['MACHINES']:
        wrong_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
    if wrong_supports:
        message_str = 'Support Structure(s) {} are INCORRECT for  machine {}'.format(
            wrong_supports, current_machine.Name)
        pass_result = FAIL
    elif correct_supports:
        message_str = 'Support Structure(s) {} are correct for machine {}'.format(
            correct_supports, current_machine.Name)
        pass_result = PASS
    else:
        message_str = 'No couch structure found'
        pass_result = ALERT
    # Prepare output
    return pass_result, message_str
