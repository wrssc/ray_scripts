import numpy as np
from PlanReview.review_definitions import PASS, FAIL, TOMO_DATA


def check_tomo_isocenter(rso):
    """
    Checks isocenter for lateral less than 2 cm.
    Check also for any

    Args:
        rso (namedtuple): Named tuple of ScriptObjects
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    isocenter = rso.beamset.Beams[0].Isocenter
    iso_pos_x = isocenter.Position.x
    if np.less_equal(abs(iso_pos_x), TOMO_DATA['LATERAL_ISO_MARGIN']):
        pass_result = PASS
        message_str = \
            f"Isocenter [{rso.beamset.Beams[0].Isocenter.Annotation.Name}] " \
            f"lateral shift is acceptable: {iso_pos_x} < " \
            f"{TOMO_DATA['LATERAL_ISO_MARGIN']} cm"
    else:
        pass_result = FAIL
        message_str = \
            f"Isocenter [{isocenter.Annotation.Name}]"\
            f" lateral shift is inconsistent with indexing: {iso_pos_x}"\
            f" > {TOMO_DATA['LATERAL_ISO_MARGIN']} cm!"
    return pass_result, message_str
