from PlanReview.review_definitions import TRUEBEAM_DATA, PASS, FAIL


def check_edw_mu(rso):
    """
    Checks to see if all MU are greater than the EDW limit
    Args:
        beamset:

    Returns:
        messages: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_13May2022, C1
        PASS: ChwR_3DC_R0A0
        FAIL: ChwR_3DC_R2A0
    """
    edws = {}
    for b in rso.beamset.Beams:
        try:
            if b.Wedge:
                if 'EDW' in b.Wedge.WedgeID:
                    edws[b.Name] = b.BeamMU
        except AttributeError:
            break
    if edws:
        passing = True
        edw_passes = []
        edw_message = "Beam(s) have EDWs: "
        for bn, mu in edws.items():
            if mu < TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT']:
                passing = False
                edw_message += "{}(MU)={:.2f},".format(bn, mu)
            else:
                edw_passes.append(bn)
        if passing:
            edw_message += "{} all with MU > {}".format(edw_passes,
                                                        TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT'])
        else:
            edw_message += "< {}".format(TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT'])
    else:
        passing = True
        edw_message = "No beams with EDWs found"

    if passing:
        pass_result = PASS
        message_str = edw_message
    else:
        pass_result = FAIL
        message_str = edw_message
    return pass_result, message_str
