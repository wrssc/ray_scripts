from typing import NamedTuple, Tuple
import re
from PlanReview.review_definitions import PASS, FAIL, ALERT


def check_prv_status(rso: NamedTuple) -> Tuple[str, str]:
    """Check PRV Status
        Verifies if priority 0 constraints are used on non-targets and
        assesses if the corresponding PRV should be defined, have contours,
        and be used in optimization.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                     Second element is the message string

        Pseudocode:
            1. Extract ROIs that are not targets
            2. Identify serial OAR constraints
            3. Check if PRVs are defined and used in optimization for serial OARs
            4. Build the appropriate message string based on PRV checks
            5. Determine the result (PASS/FAIL)
            6. Return the result and message

        Test Patients:
            Pass: Script_Testing^PRV_Script, ZZUWQA_ScTest_23Nov2023
            Fail: Script_Testing^PRV_Script, ZZUWQA_ScTest_23Nov2023
    """
    tolerance = 50
    rois = [r.Name for r in rso.case.PatientModel.RegionsOfInterest if
            r.OrganData.OrganType != 'Target']
    exclusions = ['Normal', 'Ring', 'PRV', 'Chestwall', 'Brain-PTV', 'Bag_Bowel']
    message_str = ''
    pass_result = PASS
    try:
        serial_oars = []
        for e in rso.plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
            pg = e.PlanningGoal
            if pg.GoalCriteria == 'AtMost' and \
                    (pg.Priority == 1 or pg.Priority>1000) and \
                    (pg.Type == 'DoseAtAbsoluteVolume' or pg.Type == 'DoseAtVolume'):
                include = True
                roi_name = e.ForRegionOfInterest.Name
                for ex in exclusions:
                    if re.match("^.*" + ex + ".*$", roi_name):
                        include = False
                if include and e.ForRegionOfInterest.Name not in serial_oars:
                    serial_oars.append(e.ForRegionOfInterest.Name)
    except:
        message_str = 'No evaluation goals found'
        return pass_result, message_str

    if not serial_oars:
        message_str = 'No serial oar constraints found'
        return pass_result, message_str
    prvs = []
    no_prvs = []

    for so in serial_oars:
        match = None
        for r in rois:
            if re.match("^" + so + "_PRV.*", r):
                match = r
        if match:
            prvs.append([so, match, False, False])
        else:
            no_prvs.append(so)
    # Serial organ does not have a PRV defined!
    if no_prvs:
        message_str = f'Serial Organs lacking PRV: {", ".join(map(str,no_prvs))}. '
        pass_result = FAIL
    # Find the plan optimization
    plan_optimization = None
    for po in rso.plan.PlanOptimizations:
        for opt_bs in po.OptimizedBeamSets:
            if opt_bs.DicomPlanLabel == rso.beamset.DicomPlanLabel:
                plan_optimization = po
                break
    if not plan_optimization:
        return ALERT, f'No plan optimization found for {rso.beamset.DicomPlanLabel}'

    # Look for an objective on the serial organ, if one is present, then look for one on the prv
    for p in prvs:
        try:
            for cf in plan_optimization.Objective.ConstituentFunctions:
                if cf.ForRegionOfInterest.Name == p[1]:
                    p[3] = True  # The prv was used in the optimization
                elif cf.ForRegionOfInterest.Name == p[0]:
                    p[2] = True  # The oar was used in the optimization
        except AttributeError:
            return ALERT, f'No objective found for {rso.beamset.DicomPlanLabel}'
    # PRVs is then: [serial_oar, oar_prv, oar_used_in_optimization, prv_used_in_optimization]
    # Test if Serial organ used in optimization, but the prv was not!
    not_used_str = []
    used_str = []  # PRVs used in optimization
    serial_not_used = []  # Serial oars not used in optimization
    for p in prvs:
        if p[2]:
            if p[3]:
                used_str.append(p[1])  # Both oar_prv and oar were used in optimization
            else:
                not_used_str.append(p[1])  # Only the oar was used in the optimization
        else:
            if p[3]:
                used_str.append(p[1])  # PRV was used but OAR was not.
            else:
                # Although this structure had a priority 1 or undefined constraint
                # it was not used in the optimization
                serial_not_used.append(p[0])

    if not_used_str:
        message_str += f'PRVs unused in optimization: {", ".join(map(str,not_used_str))}. '
        pass_result = FAIL
    else:
        if serial_not_used:
            serial_negligible = {}
            serial_not_negligible = {}
            for s in serial_not_used:
                for e in rso.plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
                    if e.ForRegionOfInterest.Name == s:
                        pg = e.PlanningGoal
                        if pg.GoalCriteria == 'AtMost' and \
                                (pg.Priority == 1 or pg.Priority > 1000) and \
                                (pg.Type == 'DoseAtAbsoluteVolume' or pg.Type == 'DoseAtVolume'):
                            goal_value = e.GetClinicalGoalValue()
                            pass_level = e.PlanningGoal.AcceptanceLevel
                            if goal_value < pass_level * tolerance / 100.:
                                serial_negligible[s] = goal_value
                            else:
                                serial_not_negligible[s] = goal_value
            if serial_not_negligible:
                message_str += f"Unused OARS have high dose"\
                               f" \u2265 {int(tolerance)}% clinical goal: " \
                               + format_oars_dict(serial_not_negligible)
                pass_result = FAIL
            else:
                message_str += f"Unused OARS have negligible dose"\
                               f" \u2264 {int(tolerance)}% clinical goal: "\
                               + format_oars_dict(serial_negligible)
    return pass_result, message_str


def format_oars_dict(oars_dict):
    """
    Format a dictionary of OARs (Organs at Risk) with their doses in cGy
    to a string representation with doses in Gy.

    Args:
        oars_dict (dict): A dictionary with organ names as keys and doses in cGy as values.

    Returns:
        str: A formatted string representation of the OARs with doses in Gy.
    """
    formatted_items = []
    for organ, dose_cgy in oars_dict.items():
        dose_gy = dose_cgy / 100  # Convert from cGy to Gy
        formatted_items.append(f"[{organ}, {dose_gy:.1f} Gy]")

    return ', '.join(formatted_items)
