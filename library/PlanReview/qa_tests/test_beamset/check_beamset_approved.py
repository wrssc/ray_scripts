from typing import Tuple, NamedTuple, Optional
from PlanReview.review_definitions import PASS, FAIL, ALERT
from PlanReview.utils import get_approval_info


def build_message(
        beamset_label: str,
        reviewer: str,
        approval_time: str,
        is_approved: bool
    ) -> str:
    """Helper function to build message string."""
    if is_approved:
        return f"Beamset: {beamset_label} was approved by {reviewer} on {approval_time}"
    else:
        return f"Beamset: {beamset_label} is not approved"


def check_beamset_approved(rso: NamedTuple, **kwargs: Optional[bool]) -> Tuple[str, str]:
    """ Check Beamset Approved
        Checks whether a given beamset is approved or not.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]
            **kwargs: Additional keyword arguments, options include:
                - do_physics_review (Optional[bool]): If True, the beamset is expected to be approved.

    Returns:
        result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                         Second element is the message string

    Pseudocode:
    1. Extract 'do_physics_review' from kwargs
    2. Retrieve approval status from 'get_approval_info' function
    3. Build the appropriate message string based on approval status
    4. Determine the result (PASS/FAIL/ALERT)
    5. Return the result and message

    Test Patients:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
    """

    do_physics_review = kwargs.get('do_physics_review', False)

    approval_status = get_approval_info(rso.plan, rso.beamset)
    message_str = build_message(
        rso.beamset.DicomPlanLabel,
        approval_status.beamset_reviewer,
        approval_status.beamset_approval_time,
        approval_status.beamset_approved
    )

    if approval_status.beamset_approved:
        result = PASS
    else:
        result = FAIL if do_physics_review else ALERT

    return result, message_str

