
from PlanReview.review_definitions import MATERIALS, FAIL, PASS
from .get_roi_list import get_roi_list


def check_support_material(rso):
    """
    For the list of accepted supports defined in ReviewDefinitions.py->Materials
    assure the correct material name has been assigned
    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    :return: message (list str): [Pass_Status, Message String]
    """
    rois = get_roi_list(rso.case)
    message_str = ""
    correct_supports = []
    for r in rois:
        try:
            correct_material_name = MATERIALS[r]
        except KeyError:
            continue
        try:
            material_name = rso.case.PatientModel.RegionsOfInterest[r].RoiMaterial.OfMaterial.Name
            if material_name != correct_material_name:
                message_str += r + ' incorrectly assigned as ' + material_name
            else:
                correct_supports.append(r)
        except AttributeError:
            message_str += r + ' not overriden! '
    if message_str:
        pass_result = FAIL
    else:
        pass_result = PASS
        if correct_supports:
            message_str = "Supports [" + ",".join(correct_supports) + "] Correctly overriden"
        else:
            message_str = "No supports found"
    return pass_result, message_str