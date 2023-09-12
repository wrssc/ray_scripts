from typing import NamedTuple, List, Dict, Tuple, Any, Optional
from PlanReview_V0_BetaTesting.review_definitions import PASS, FAIL


def message_format_control_point_spacing(
    beam_spacing_failures: Dict[str, List[int]],
    spacing: int
) -> Tuple[str, str]:
    """
    Formats the control point spacing message and result.

    Args:
        beam_spacing_failures (Dict[str, List[int]]): Dictionary containing beam names and the corresponding failing control points.
        spacing (int): The maximum allowed gantry angle between control points.

    Returns:
        Tuple[str, str]: First element is the message string,
                         Second element is the status (PASS/FAIL).
    """
    # Takes in a message dictionary that is labeled per beam, then parses
    if beam_spacing_failures:
        for b, v in beam_spacing_failures.items():
            message_str = 'Beam {}: Gantry Spacing Exceeds {} in Control Points {}\n' \
                .format(b, spacing, v)
            message_result = FAIL
    else:
        message_str = "No control points > {} detected".format(spacing)
        message_result = PASS
    return message_str, message_result


def pass_control_point_spacing(s: Any, s0: Optional[Any], spacing: int) -> bool:
    """
        Checks whether the gantry angle between control points is within a specified limit.

        Args:
            s (Any): The current control point.
            s0 (Optional[Any]): The previous control point.
            spacing (int): The maximum allowed gantry angle between control points.

        Returns:
            bool: True if the spacing is acceptable, False otherwise.
    """
    if not s0:
        if s.DeltaGantryAngle <= spacing:
            return True
        else:
            return False
    else:
        if s.DeltaGantryAngle - s0.DeltaGantryAngle <= spacing:
            return True
        else:
            return False


def check_control_point_spacing(rso: NamedTuple,**kwargs) -> Tuple[str, str]:
    """ Check Control Point Spacing
    Checks the gantry angle between control points in a beamset.

    Args:
        rso (NamedTuple): ScriptObjects in Raystation containing [case, exam, plan, beamset, db].
        expected (Optional[int]): Expected gantry angle between control points, provided through kwargs.

    Returns:
        Tuple[str, str]: First element is the result (PASS/FAIL),
                            Second element is the message string.

    Pseudocode:
        1. Extract 'expected' from kwargs.
        2. Loop through beams in the beamset.
        3. For each beam, loop through control points and apply 'pass_control_point_spacing' function.
        4. Store failed control points and prepare the message string using 'message_format_control_point_spacing' function.
        5. Return the result and message string.

    Test Patients:
        Pass: None provided
        Fail: None Provided
    """
    expected = kwargs.get('expected')
    beam_result = {}
    for b in rso.beamset.Beams:
        s0 = None
        fails = []
        for s in b.Segments:
            if not pass_control_point_spacing(s, s0, spacing=expected):
                fails.append(s.SegmentNumber + 1)
            s0 = s
        if fails:
            beam_result[b.Name] = fails
    message_str, pass_result = message_format_control_point_spacing(
        beam_spacing_failures=beam_result,
        spacing=expected)
    return pass_result, message_str
