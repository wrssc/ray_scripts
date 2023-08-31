import re
from PlanReview.review_definitions import PASS, FAIL


def check_prv_status(rso):
    """
    If priority 0 constraints (or undefined priority) constraints are used on a non-target,
    and the non-target
    has maximum dose constrained a PRV should be defined, have contours, and be used in the
    optimization
    :param rso:
    :return:
    """

    rois = [r.Name for r in rso.case.PatientModel.RegionsOfInterest if
            r.OrganData.OrganType != 'Target']
    exclusions = ['Normal', 'Ring', 'PRV', 'Chestwall']
    message_str = ''
    pass_result = PASS
    try:
        serial_oars = []
        for e in rso.plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
            pg = e.PlanningGoal
            if pg.GoalCriteria == 'AtMost' and \
                    (pg.Priority == 1 or not pg.Priority) and \
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
    # Look for a objective on the serial organ, if one is present, then look for one on the prv
    for p in prvs:
        for po in rso.plan.PlanOptimizations:
            if po.OptimizedBeamSets.DicomPlanLabel == rso.beamset.DicomPlanLabel:
                for cf in po.Objective.ConsituentFunctions:
                    if cf.ForRegionOfInterest.Name == p[1]:
                        p[3] = True
                    elif cf.ForRegionOfInterest.Name == p[0]:
                        p[2] = True
    # Serial organ does not have a PRV defined!
    if no_prvs:
        message_str = 'Serial Organs without PRV: '
        for n in no_prvs:
            message_str += n + ' '
        message_str += '. '
        pass_result = FAIL
    # Serial organ used in optimization, but the prv was not!
    not_used_str = ''
    used_str = ''
    serial_not_used = ''
    for p in prvs:
        if p[2]:
            if p[3]:
                used_str += p[1] + ' '
            else:
                not_used_str += p[1] + ' '
        else:
            serial_not_used += p[0] + ' '

    if not_used_str:
        message_str += f'PRVs unused in optimization: [{not_used_str}]'
        pass_result = FAIL
    else:
        if not message_str and (used_str or serial_not_used):
            message_str += f"Serial PRV used [{used_str}]. Serial Organ unused[{serial_not_used}]"
    return pass_result, message_str
