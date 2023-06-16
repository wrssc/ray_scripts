from PlanReview.review_definitions import TOMO_DATA, PASS, FAIL
from PlanReview.utils import get_approval_info


def old_check_transfer_approved(rso, ):
    """

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    Returns:
        message (list str): [Pass_Status, Message String]

    """
    child_key = "Transfer Beamset approval status"
    parent_beamset_name = rso.beamset.DicomPlanLabel
    daughter_plan_name = rso.plan.Name + TOMO_DATA['PLAN_TR_SUFFIX']
    if TOMO_DATA['MACHINES'][0] in rso.beamset.MachineReference['MachineName']:
        daughter_machine = TOMO_DATA['MACHINES'][1]
    else:
        daughter_machine = TOMO_DATA['MACHINES'][0]

    daughter_beamset_name = parent_beamset_name[:8] \
                            + TOMO_DATA['PLAN_TR_SUFFIX'] \
                            + daughter_machine[-3:]
    plan_names = [p.Name for p in rso.case.TreatmentPlans]
    beamset_names = [bs.DicomPlanLabel for p in rso.case.TreatmentPlans for bs in p.BeamSets]
    if daughter_beamset_name in beamset_names and daughter_plan_name in plan_names:
        transfer_beamset = rso.case.TreatmentPlans[daughter_plan_name].BeamSets[
            daughter_beamset_name]
    else:
        transfer_beamset = None
        message_str = "Beamset: {} is missing a transfer plan!" \
            .format(rso.beamset.DicomPlanLabel)
        pass_result = FAIL
    if transfer_beamset:
        approval_status = get_approval_info(rso.plan, transfer_beamset)
        if approval_status.beamset_approved:
            message_str = "Transfer Beamset: {} was approved by {} on {}" \
                .format(transfer_beamset.DicomPlanLabel,
                        approval_status.beamset_reviewer,
                        approval_status.beamset_approval_time
                        )
            pass_result = PASS
        else:
            message_str = "Beamset: {} is not approved".format(
                transfer_beamset.DicomPlanLabel)
            pass_result = FAIL
    return pass_result, message_str


def check_transfer_approved(rso, ):
    """
    Check if the transfer beamset is approved for the given beamset.

    Args:
        rso (namedtuple): NamedTuple of ScriptObjects in
                          Raystation [case,exam,plan,beamset,db].

    Returns:
        tuple: Tuple containing a string representing the pass/fail status
               and a message string.

    """
    parent_beamset_name = rso.beamset.DicomPlanLabel
    daughter_plan_name = rso.plan.Name + TOMO_DATA['PLAN_TR_SUFFIX']
    if TOMO_DATA['MACHINES'][0] in rso.beamset.MachineReference['MachineName']:
        daughter_machine = TOMO_DATA['MACHINES'][1]
    else:
        daughter_machine = TOMO_DATA['MACHINES'][0]

    daughter_beamset_name = f"{parent_beamset_name[:8]}" \
                            f"{TOMO_DATA['PLAN_TR_SUFFIX']}" \
                            f"{daughter_machine[-3:]}"

    plan_names = [plan.Name for plan in rso.case.TreatmentPlans]
    beamset_names = [beamset.DicomPlanLabel
                     for plan in rso.case.TreatmentPlans
                     for beamset in plan.BeamSets]

    if daughter_beamset_name not in beamset_names or daughter_plan_name not in plan_names:
        message_str = f"Beamset: {rso.beamset.DicomPlanLabel}" \
                      " is missing a transfer plan!"
        return FAIL, message_str

    transfer_beamset = rso.case.TreatmentPlans[daughter_plan_name] \
        .BeamSets[daughter_beamset_name]
    approval_status = get_approval_info(rso.plan, transfer_beamset)

    if approval_status.beamset_approved:
        message_str = f"Transfer Beamset: {transfer_beamset.DicomPlanLabel}" \
                      f" was approved by {approval_status.beamset_reviewer}" \
                      f" on {approval_status.beamset_approval_time}"
        return PASS, message_str
    else:
        message_str = f"Beamset: {transfer_beamset.DicomPlanLabel}" \
                      " is not approved"
        return FAIL, message_str
