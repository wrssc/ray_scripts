from PlanReview.review_definitions import PASS, FAIL


def message_format_control_point_spacing(beam_spacing_failures, spacing):
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


def pass_control_point_spacing(s, s0, spacing):
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


def check_control_point_spacing(rso, **kwargs):
    """
    bs: RayStation beamset
    expected: Integer delineating the gantry angle between control points in a beam
    Returns:
            message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
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
