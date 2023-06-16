from PlanReview.review_definitions import TRUEBEAM_DATA, PASS, FAIL


def check_edw_field_size(rso):
    """
    Checks to see if all Y jaws  are greater than the EDW limit
    Y1=IN : -10 cm ≤ Y2 ≤ 10 cm & 4 ≤ Y2 - Y1 ≤ 30
    Y2=OUT: -10 cm ≤ Y1 ≤ 10 cm & 4 ≤ Y2 - Y1 ≤ 30

    Args:
     rso: NamedTuple: Named tuple of rs objects

    Returns:
        messages: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_13May2022, C1
        PASS: ChwR_3DC_R0A0
        FAIL: EDW_Fail - Note that as of RS 11B the jaws can't be made to violate max limits.
    """
    edws = {}
    for b in rso.beamset.Beams:
        try:
            if b.Wedge:
                if 'EDW' in b.Wedge.WedgeID:
                    edws[b.Name] = (b.Wedge.Orientation,
                                    b.Segments[0].JawPositions[0],
                                    b.Segments[0].JawPositions[1],
                                    b.Segments[0].JawPositions[2],
                                    b.Segments[0].JawPositions[3])
        except AttributeError:
            break
    if edws:
        passing = True
        edw_passes = []
        edw_message = "Beam(s) have EDWs: "
        for bn, jaw in edws.items():
            orientation = jaw[0]
            x1 = jaw[1]
            x2 = jaw[2]
            y1 = jaw[3]
            y2 = jaw[4]
            if x2 - x1 > TRUEBEAM_DATA['EDW_LIMITS']['X-MAX']:
                passing = False
                edw_message += f"{bn} X-Jaw Overextended:{x2 - x1:.2f} > " \
                               + f"{TRUEBEAM_DATA['EDW_LIMITS']['X-MAX']}. "
            elif x2 - x1 < TRUEBEAM_DATA['EDW_LIMITS']['X-MIN']:
                passing = False
                edw_message += f"{bn} X-Jaw Field Too Small: {x2 - x1:.2f} < " \
                               + f"{TRUEBEAM_DATA['EDW_LIMITS']['X-MIN']}. "
            elif orientation == 'In':
                if y2 < -1. * TRUEBEAM_DATA['EDW_LIMITS']['Y1-IN'] \
                        or y2 > TRUEBEAM_DATA['EDW_LIMITS']['Y1-IN']:
                    passing = False
                    edw_message += f"{bn} Jaw Overextended: |Y2: {y2:.2f}| > " \
                                   + f"{TRUEBEAM_DATA['EDW_LIMITS']['Y1-IN']}. "
                elif y2 - y1 < TRUEBEAM_DATA['EDW_LIMITS']['Y-MIN']:
                    passing = False
                    edw_message += f"{bn} Field Too Small: (Y2 - Y1):({y2:.2f} - {y1:.2f}) < " \
                                   + f"{TRUEBEAM_DATA['EDW_LIMITS']['Y-MIN']} cm. "
                else:
                    edw_passes.append(bn)
            elif orientation == 'Out':
                if y1 < -1. * TRUEBEAM_DATA['EDW_LIMITS']['Y2-OUT'] \
                        or y1 > TRUEBEAM_DATA['EDW_LIMITS']['Y2-OUT']:
                    passing = False
                    edw_message += f"{bn} Jaw Overextended: |Y1: {y1:.2f}| > " \
                                   + f"{TRUEBEAM_DATA['EDW_LIMITS']['Y2-OUT']}. "
                elif y2 - y1 < TRUEBEAM_DATA['EDW_LIMITS']['Y-MIN']:
                    passing = False
                    edw_message += f"{bn} Field Too Small: (Y2 - Y1):({y2:.2f} - {y1:.2f}) < " \
                                   + f"{TRUEBEAM_DATA['EDW_LIMITS']['Y-MIN']} cm. "
                else:
                    edw_passes.append(bn)
            else:
                edw_passes.append(bn)
        if passing:
            edw_message += "{} all with deliverable field sizes. ".format(edw_passes)
    else:
        passing = True
        edw_message = "No beams with EDWs found. "

    if passing:
        pass_result = PASS
        message_str = edw_message
    else:
        pass_result = FAIL
        message_str = edw_message
    return pass_result, message_str
