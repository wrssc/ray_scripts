# Check if the plan is approved by an MD
from PlanReview.utils import get_approval_info
from PlanReview.utils.get_approval_info import find_groupname_by_userid, is_valid_approver, find_username_by_userid
from PlanReview.review_definitions import PASS, FAIL, ALERT


VALID_APPROVAL_GROUPS = ["Oncologist"]


def check_plan_approved(rso, **kwargs):
    """
    Check if a plan is approved
    Args: rso: Named Tuple of RS script objects
        do_physics_review: Bool: True if expected status of plan is approved

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]

    """
    physics_review = kwargs.get('do_physics_review')
    approval_status = get_approval_info(rso.plan, rso.beamset)
    if approval_status.plan_approved:
        if not approval_status.plan_reviewer:
            message_str = f"Plan: {rso.plan.Name} does not have valid approval data"
            pass_result = ALERT
            return pass_result, message_str
        group_name = find_groupname_by_userid(approval_status.plan_reviewer)
        user_name = find_username_by_userid(approval_status.plan_reviewer)
        if is_valid_approver(group_name, VALID_APPROVAL_GROUPS):
            message_str = f"Plan: {rso.plan.Name} was approved by " \
                          f"{user_name}, (Staff {group_name}) " \
                          f"on {approval_status.plan_approval_time}"
            pass_result = PASS
        else:
            message_str = f"Plan: {rso.plan.Name} approval INVALID. Approved by " \
                          f"{user_name}, ({group_name}) " \
                          f"on {approval_status.plan_approval_time}"
            pass_result = FAIL
    else:
        if approval_status.beamset_approved:
            message_str = f"Plan: {rso.plan.Name} is mutable but beamset: {rso.beamset.DicomPlanLabel} is approved"
            pass_result = ALERT
            return pass_result, message_str
        message_str = f"Plan: {rso.plan.Name} is not approved"
        if physics_review:
            pass_result = FAIL
        else:
            message_str += " (Dosimetry Safety Review)"
            pass_result = PASS
    return pass_result, message_str
