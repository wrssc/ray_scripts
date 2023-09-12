from math import isclose
from typing import Tuple, Optional
from PlanReview_V0_BetaTesting.review_definitions import FAIL, PASS


def check_common_isocenter(rso, **kwargs) -> Tuple[str, str]:
    """ Check common isocenter
    Checks all beams in a given beamset for shared isocenter.

    Args:
        rso (NamedTuple): ScriptObjects in Raystation containing [case,exam,plan,beamset,db].
        tolerance (Optional[float]): Largest acceptable difference in isocenter location in mm.

    Returns:
        Tuple[str, str]: First element is the status (PASS/FAIL),
                         Second element is the message string.

    Pseudocode:
        1. Extract 'tolerance' from kwargs
        2. Retrieve isocenter positions for the first beam
        3. Loop through all beams to compare isocenter positions
        4. Build the appropriate message string based on isocenter match or difference
        5. Determine the result (PASS/FAIL)
        6. Return the result and message

    Test Patients:
        Pass: (Provide relevant test cases where this check will pass)
        Fail: (Provide relevant test cases where this check will fail)
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
