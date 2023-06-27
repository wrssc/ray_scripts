from math import isclose
from PlanReview.review_definitions import FAIL, PASS


def check_common_isocenter(rso, **kwargs):
    """
    Checks all beams in beamset for shared isocenter

    Args:
        beamset (object):
        tolerance (flt): largest acceptable difference in isocenter location
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    """
    tolerance = kwargs.get('tolerance')
    initial_beam_name = rso.beamset.Beams[0].Name
    iso_pos_x = rso.beamset.Beams[0].Isocenter.Position.x
    iso_pos_y = rso.beamset.Beams[0].Isocenter.Position.y
    iso_pos_z = rso.beamset.Beams[0].Isocenter.Position.z
    iso_differs = []
    iso_match = []
    for b in rso.beamset.Beams:
        b_iso = b.Isocenter.Position
        if all([isclose(b_iso.x, iso_pos_x, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.y, iso_pos_y, rel_tol=tolerance, abs_tol=0.0),
                isclose(b_iso.z, iso_pos_z, rel_tol=tolerance, abs_tol=0.0)]):
            iso_match.append(b.Name)
        else:
            iso_differs.append(b.Name)
    if iso_differs:
        pass_result = FAIL
        message_str = \
            f"Beam(s) {iso_differs} differ in isocenter location" \
            f"from beam {initial_beam_name}"
    else:
        pass_result = PASS
        message_str = \
            f"Beam(s) {iso_match} all share the same isocenter to within " \
            f"{tolerance} mm"

    return pass_result, message_str
