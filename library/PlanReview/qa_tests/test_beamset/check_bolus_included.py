from PlanReview.review_definitions import BOLUS_NAMES, PASS, FAIL
from PlanReview.utils import get_roi_list, match_roi_name


def check_bolus_included(rso):
    """

    Args:

    Returns:
        message: list of lists of format: [parent key, key, value, result]
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, ChwL
        Pass: Bolus_Roi_Check_Pass: ChwL_VMA_R1A0
        Fail: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    child_key = "Bolus Application"
    exam_name = rso.exam.Name
    roi_list = get_roi_list(rso.case, exam_name=exam_name)
    bolus_names = match_roi_name(roi_names=BOLUS_NAMES, roi_list=roi_list)
    if bolus_names:
        fail_str = "Stucture(s) {} named bolus, ".format(bolus_names) \
                   + "but not applied to beams in beamset {}".format(rso.beamset.DicomPlanLabel)
        try:
            applied_boli = set([bolus.Name for b in rso.beamset.Beams for bolus in b.Boli])
            if any(bn in applied_boli for bn in bolus_names):
                bolus_matches = {bn: [] for bn in bolus_names}
                for ab in applied_boli:
                    bolus_matches[ab].extend([b.Name for b in rso.beamset.Beams
                                              for bolus in b.Boli
                                              if bolus.Name == ab])
                pass_result = PASS
                message_str = "".join(
                    ['Roi {0} applied on beams {1}'.format(k, v) for k, v in bolus_matches.items()])
            else:
                pass_result = FAIL
                message_str = fail_str
        except AttributeError:
            pass_result = FAIL
            message_str = fail_str
    else:
        message_str = "No rois including {} found for Exam {}".format(BOLUS_NAMES, exam_name)
        pass_result = PASS
    return pass_result, message_str
