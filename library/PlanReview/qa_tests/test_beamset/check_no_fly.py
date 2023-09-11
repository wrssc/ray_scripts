from typing import NamedTuple, Tuple
from PlanReview.review_definitions import (
    PASS, ALERT, FAIL, NO_FLY_DOSE, NO_FLY_NAME
)


def build_message(dose: float, tolerance: float, label: str, status: str) -> str:
    """Builds a message string based on the dose comparison."""
    return f"{label} is {'likely out of field' if status == PASS else 'potentially infield'}. " \
           f"Dose = {dose:.2f} cGy (tolerance {tolerance:.2f} cGy)"


def check_no_fly(rso: NamedTuple) -> Tuple[str, str]:
    """ Check No Fly
        Checks if the 'NO_FLY_NAME' ROI is within acceptable dose limits.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                              [case ('RayStation Case Object'),
                               exam ('RayStation Exam Object'),
                               plan ('RayStation Plan Object'),
                               beamset ('RayStation BeamSet Object'),
                               db ('RayStation Database Object')]

    Returns:
        pass_result, message_str (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                    Second element is the message string

    Pseudocode:
    1. Retrieve the dose statistic from RayStation for 'NO_FLY_NAME'
    2. Compare the retrieved dose with 'NO_FLY_DOSE'
    3. Build the appropriate message string based on comparison
    4. Determine the result (PASS/FAIL/ALERT)
    5. Return the result and message

    Test Patients:
        PASS: Script_Testing, #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
        FAIL: Script_Testing, #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
    """
    try:
        # Retrieve the maximum dose to the 'NO_FLY_NAME' region of interest (ROI)
        plan_no_fly_dose = rso.plan.TreatmentCourse.TotalDose.GetDoseStatistic(
            RoiName=NO_FLY_NAME, DoseType='Max')

        # Compare the retrieved dose with the tolerance dose 'NO_FLY_DOSE'
        if plan_no_fly_dose > NO_FLY_DOSE:
            pass_result = FAIL
        else:
            pass_result = PASS

        # Build message string
        message_str = build_message(plan_no_fly_dose, NO_FLY_DOSE, NO_FLY_NAME, pass_result)

    except Exception as e:
        # Check if ROI exists, and handle other exceptions
        if "exists no ROI" in str(e):
            message_str = f"No ROI {NO_FLY_NAME} found, Incline Board not used"
            pass_result = PASS
        else:
            message_str = f"Unknown error in looking for incline board info: {e}"
            pass_result = ALERT

    return pass_result, message_str

