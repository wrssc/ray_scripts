# Plan Checks
import BeamSetReviewTests


def check_plan_approved(pd):
    """
    Check if a plan is approved
    Args:

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]

    """
    approval_status = BeamSetReviewTests.approval_info(pd.plan, pd.beamset)
    if approval_status.plan_approved:
        message_str = "Plan: {} was approved by {} on {}".format(
            pd.plan.Name,
            approval_status.plan_reviewer,
            approval_status.plan_approval_time
        )
        pass_result = "Pass"
    else:
        message_str = "Plan: {} is not approved".format(
            pd.plan.Name)
        pass_result = "Fail"
    return pass_result, message_str
