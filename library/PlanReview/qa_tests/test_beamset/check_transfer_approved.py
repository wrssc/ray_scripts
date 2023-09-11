from typing import NamedTuple, Tuple, Optional
from PlanReview.review_definitions import TOMO_DATA, PASS, FAIL
from PlanReview.utils import get_approval_info

def check_transfer_approved(rso: NamedTuple, **kwargs: Optional[bool]) -> Tuple[str, str]:

    """Check Transfer Approved
        Checks whether a given transfer beamset is approved or not.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]
            **kwargs: Additional keyword arguments (none are utilized in this function).

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                      Second element is the message string

        Pseudocode:
        1. Derive parent and daughter beamset and plan names
        2. Check if daughter beamset and plan exist in case
        3. If they exist, check their approval status
        4. Return PASS or FAIL based on approval status

        Test Patients:
            Pass: Needed
            Fail: Needed

    """
    parent_beamset_name = rso.beamset.DicomPlanLabel
    daughter_plan_name = rso.plan.Name + TOMO_DATA['PLAN_TR_SUFFIX']
    if TOMO_DATA['MACHINES'][1] in rso.beamset.MachineReference['MachineName']:
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
