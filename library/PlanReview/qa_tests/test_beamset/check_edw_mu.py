from typing import List, Tuple, NamedTuple
from PlanReview.review_definitions import TRUEBEAM_DATA, PASS, FAIL


def get_edw_beams(beams: List[object]) -> dict:
    """
    Helper function to get beams with EDWs.
    """
    edw_dict = {}
    for b in beams:
        try:
            if 'EDW' in b.Wedge.WedgeID:
                edw_dict[b.Name] = b.BeamMU
        except AttributeError:
            continue

    return edw_dict


def check_edw_mu(rso: NamedTuple) -> Tuple[str, str]:
    """
    Check if all Monitor Units (MU) are greater than the EDW limit.

    Args:
        rso: NamedTuple containing RayStation script objects.
            E.g., rso.beamset refers to the RayStation beamset script object.

    Returns:
        Tuple of (pass_result: str, message_str: str)

    Pseudocode:
        1. Extract beams with EDWs from the provided RayStation object
        2. Check if MU values for these beams are within specified limits
        3. Generate a message based on the check results
        4. Return the message and pass/fail status

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_13May2022, C1
        PASS: ChwR_3DC_R0A0
        FAIL: ChwR_3DC_R2A0
    """
    edws = get_edw_beams(rso.beamset.Beams)

    if edws:
        passing, message_str = validate_edw_limits(edws)
    else:
        passing = True
        message_str = "No beams with EDWs found"

    pass_result = PASS if passing else FAIL
    return pass_result, message_str


def validate_edw_limits(edws: dict) -> Tuple[bool, str]:
    """
    Helper function to validate if the MU values for EDW beams meet the limits.
    """
    passing = all(mu >= TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT'] for mu in edws.values())

    if passing:
        edw_names = ', '.join(edws.keys())
        message_str = f"Beam(s) have EDWs: {edw_names} all with MU > {TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT']}"
    else:
        failing_beams = [(bn, mu) for bn, mu in edws.items() if mu < TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT']]
        message_str = f"Beam(s) have EDWs: {', '.join(f'{bn}(MU)={mu:.2f}' for bn, mu in failing_beams)} < {TRUEBEAM_DATA['EDW_LIMITS']['MU_LIMIT']}"

    return passing, message_str

