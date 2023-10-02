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
            Pass: Needed
            Fail: Needed
    """

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
                if include:
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
            prvs.append((so, match, False, False))
        else:
            no_prvs.append(so)
    # Serial organ does not have a PRV defined!
    if no_prvs:
        message_str = f'Serial Organs lacking PRV: {", ".join(map(str,no_prvs))}. '
        pass_result = FAIL
    # Look for an objective on the serial organ, if one is present, then look for one on the prv
    for p in prvs:
        for po in rso.plan.PlanOptimizations:
            if po.OptimizedBeamSets.DicomPlanLabel == rso.beamset.DicomPlanLabel:
                for cf in po.Objective.ConsituentFunctions:
                    if cf.ForRegionOfInterest.Name == p[1]:
                        p[3] = True  # The prv was used in the optimization
                    elif cf.ForRegionOfInterest.Name == p[0]:
                        p[2] = True  # The oar was used in the optimization
    # Test if Serial organ used in optimization, but the prv was not!
    not_used_str = []
    used_str = []
    serial_not_used = []
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
            message_str += f"For {', '.join(map(str,serial_not_used))}: goals with high" \
                           f" (or undefined) priority were excluded from optimization."
            pass_result = ALERT
    return pass_result, message_str
