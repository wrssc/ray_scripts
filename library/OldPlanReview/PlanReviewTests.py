# Plan Checks
import BeamSetReviewTests
from ReviewDefinitions import *


def check_plan_approved(rso, **kwargs):
    """
    Check if a plan is approved
    Args: rso: Named Tuple of RS script objects
        do_physics_review: Bool: True if expected status of plan is approved

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]

    """
    physics_review = kwargs.get('do_physics_review')
    approval_status = BeamSetReviewTests.approval_info(rso.plan, rso.beamset)
    if approval_status.plan_approved:
        message_str = "Plan: {} was approved by {} on {}".format(
            rso.plan.Name,
            approval_status.plan_reviewer,
            approval_status.plan_approval_time
        )
        pass_result = PASS
    else:
        message_str = "Plan: {} is not approved".format(
            rso.plan.Name)
        if physics_review:
            pass_result = FAIL
        else:
            pass_result = ALERT
    return pass_result, message_str
