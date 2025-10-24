from typing import Tuple, NamedTuple, Optional
from PlanReview.review_definitions import PASS, FAIL, ALERT, STAFF_XML_PATH
from PlanReview.utils import (
    get_approval_info, find_groupname_by_userid, is_valid_approver)

VALID_APPROVAL_GROUPS = ["Oncologist"]


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
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA also Validation/ZZUWQA_20Jan2021: MultiBeamset Script_Testing
    """
    import logging
    do_physics_review = kwargs.get('do_physics_review', False)

    approval_status = get_approval_info(rso.plan, rso.beamset)
    logging.debug(approval_status)
    if approval_status.beamset_approved:
        if not approval_status.beamset_reviewer and not approval_status.plan_reviewer:
            message_str = f"Beamset: {rso.beamset.DicomPlanLabel} does not have valid approval data"
            pass_result = ALERT
            return pass_result, message_str
        group_name = find_groupname_by_userid(approval_status.beamset_reviewer)
        if is_valid_approver(group_name, VALID_APPROVAL_GROUPS):
            message_str = f"Beamset: {rso.beamset.DicomPlanLabel} was approved by " \
                          f"{approval_status.beamset_reviewer}, (Staff {group_name}) " \
                          f"on {approval_status.beamset_approval_time}"
            pass_result = PASS
        else:
            message_str = f"Beamset: {rso.beamset.DicomPlanLabel} approval INVALID. Approved by " \
                          f"{approval_status.beamset_reviewer}, ({group_name}) " \
                          f"on {approval_status.beamset_approval_time}"
            pass_result = FAIL

    else:
        message_str = f"Beamset: {rso.plan.Name} is not approved."
        if do_physics_review:
            pass_result = FAIL
        else:
            pass_result = PASS
            message_str += " (Dosimetry Safety Review)"
    return pass_result, message_str
