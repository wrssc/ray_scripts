from PlanReview.review_definitions import PASS, FAIL, ALERT
from PlanReview.utils import get_approval_info


def check_beamset_approved(rso, **kwargs):
    """
    Check if a plan is approved
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
        physics_review: Bool: True then beamset is expected to be approved

    Returns:
        message: [str1, ...]: [parent_key, child_key, child_key display, result_value]
    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA

    """
    physics_review = kwargs.get('do_physics_review')

    approval_status = get_approval_info(rso.plan, rso.beamset)
    if approval_status.beamset_approved:
        message_str = "Beamset: {} was approved by {} on {}".format(
            rso.beamset.DicomPlanLabel,
            approval_status.beamset_reviewer,
            approval_status.beamset_approval_time
        )
        pass_result = PASS
    else:
        message_str = "Beamset: {} is not approved".format(
            rso.beamset.DicomPlanLabel)
        if physics_review:
            pass_result = FAIL
        else:
            pass_result = ALERT
    return pass_result, message_str
