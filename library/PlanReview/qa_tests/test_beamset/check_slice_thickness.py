import numpy as np
from PlanReview.review_definitions import GRID_PREFERENCES, PASS, FAIL, ALERT


def check_slice_thickness(rso):
    """
    Checks the current exam used in this case for appropriate slice thickness
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    Returns:
        messages: [[str1, ...,],...]: [[parent_key, child_key, messgae display, Pass/Fail/Alert]]

    Test Patient:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """
    message_str = ""
    for k, v in GRID_PREFERENCES.items():
        # Check to see if plan obeys a naming convention we have flagged
        if any([n in rso.beamset.DicomPlanLabel for n in v['PLAN_NAMES']]):
            nominal_slice_thickness = v['SLICE_THICKNESS']
            for s in rso.exam.Series:
                slice_positions = np.array(s.ImageStack.SlicePositions)
                slice_thickness = np.diff(slice_positions)
                if np.isclose(slice_thickness, nominal_slice_thickness).all() \
                        or all(slice_thickness < nominal_slice_thickness):
                    message_str = f'Slice spacing {slice_thickness.max():.3f} ' \
                                  f'≤ {nominal_slice_thickness:.3f} cm appropriate' \
                                  f' for plan type {v["PLAN_NAMES"]}'
                    pass_result = PASS
                else:
                    message_str = 'Slice spacing {:.3f} > {:.3f} cm TOO LARGE for plan type {' \
                                  '}'.format(
                        slice_thickness.max(), nominal_slice_thickness, v['PLAN_NAMES'])
                    pass_result = FAIL
    if not message_str:
        for s in rso.exam.Series:
            slice_positions = np.array(s.ImageStack.SlicePositions)
            slice_thickness = np.diff(slice_positions)
        message_str = 'Plan type unknown, check slice spacing {:.3f} cm carefully'.format(
            slice_thickness.max())
        pass_result = ALERT
    return pass_result, message_str
