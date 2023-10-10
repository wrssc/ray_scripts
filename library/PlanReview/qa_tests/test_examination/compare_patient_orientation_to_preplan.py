from typing import NamedTuple, Tuple
from PlanReview.review_definitions import PASS, FAIL, PATIENT_ORIENTATIONS
from PlanReview.utils import KEY_PATIENT_ORIENTATION


def compare_patient_orientation_to_preplan(rso: NamedTuple, **kwargs) -> Tuple[str, str]:
    """ Check Patient Orientation Against Exam Data
    For an input patient orientation, make sure the patient orientation matches
    the expected orientation.

    Args:
        rso (NamedTuple): ScriptObjects in RayStation containing
                         [case ('RayStation Case Object'),
                          exam ('RayStation Exam Object'),
                          plan ('RayStation Plan Object'),
                          beamset ('RayStation BeamSet Object'),
                          db ('RayStation Database Object')]

    Returns:
        result, message_string (Tuple[str, str]):
            First element is the status (PASS/FAIL/ALERT),
            Second element is the message string

    Pseudocode:
        1. Extract 'patient_orientation' from user-entered value in preplan tab
        2. Retrieve the patient orientation from the exam in use
        3. Compare the two patient orientations

    Test Patients:
        Pass: Any patient with correct orientation.
        Fail: Any patient, just deliberately enter the wrong orientation

    """
    values = kwargs.get('VALUES')
    simulation_patient_orientation = values[KEY_PATIENT_ORIENTATION]
    examination_patient_orientation = rso.exam.PatientPosition
    if examination_patient_orientation != simulation_patient_orientation:
        return FAIL, f"For exam: {rso.exam.Name}: patient orientation from CT SIM: " \
                     f"{simulation_patient_orientation} " \
                     f"DOES NOT MATCH RS: {PATIENT_ORIENTATIONS[examination_patient_orientation]}"
    return PASS, f"For exam: {rso.exam.Name}: patient orientation from CT SIM: "\
                 f"{simulation_patient_orientation} " \
                 f"matches RS: {PATIENT_ORIENTATIONS[examination_patient_orientation]}"
