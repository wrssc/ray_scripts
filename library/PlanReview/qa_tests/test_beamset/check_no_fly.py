from PlanReview.review_definitions import (
    PASS, ALERT, FAIL, NO_FLY_DOSE, NO_FLY_NAME)
def check_no_fly(rso):
    """

    Args:
        rso:

    Returns:
    message (list str): [Pass_Status, Message String]

    Test Patient:
        PASS: Script_Testing, #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
        FAIL: Script_Testing, #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
    """
    try:
        plan_no_fly_dose = rso.plan.TreatmentCourse.TotalDose.GetDoseStatistic(
            RoiName=NO_FLY_NAME, DoseType='Max')
        if plan_no_fly_dose > NO_FLY_DOSE:
            message_str = f"{NO_FLY_NAME} is potentially infield. Dose = " \
                f"{plan_no_fly_dose:.2f} cGy (exceeding tolerance " \
                f" {NO_FLY_DOSE:.2f} cGy)"
            pass_result = FAIL
        else:
            message_str = f"{NO_FLY_NAME} is likely out of field." \
                          f" Dose = {plan_no_fly_dose:.2f} cGy (tolerance " \
                          f"{NO_FLY_DOSE:.2f}; cGy)"
            pass_result = PASS
    except Exception as e:
        if "exists no ROI" in "{}".format(e):
            message_str = f"No ROI {NO_FLY_NAME} found, Incline Board not used"
            pass_result = PASS
        else:
            message_str = f"Unknown error in looking for incline board" \
                          f" info {e.Message}"
            pass_result = ALERT

    return pass_result, message_str
