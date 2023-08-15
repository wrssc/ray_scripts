from PlanReview.review_definitions import (
    PASS, ALERT, FAIL, DOSE_FRACTION_PAIRS)


def check_fraction_size(rso):
    """
    Check the fraction size for common errors
    Args:
        rso (namedtuple): RayStation Beamset Object

    Returns:
        message: List of ['Test Name Key', 'Pass/Fail', 'Detailed Message']
    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, Fraction_Size_Check
        Pass: Pelv_THI_R0A0
        Fail: Pelv_T3D_R0A0
    """
    child_key = 'Check Fractionation'
    results = {0: FAIL, 1: ALERT, 2: PASS}
    num_fx = rso.beamset.FractionationPattern.NumberOfFractions
    pass_result = results[2]
    message_str = f'Beamset {rso.beamset.DicomPlanLabel}' \
                  f' fractionation not flagged'
    rx_dose = None
    try:
        rx_dose = rso.beamset.Prescription. \
            PrimaryPrescriptionDoseReference.DoseValue
    except AttributeError:
        pass_result = results[1]
        message_str = f'No Prescription is Defined for Beamset: ' \
                      f'{rso.beamset.DicomPlanLabel}'
    #
    # Look for matches in dose pairs
    if rx_dose:
        for t in DOSE_FRACTION_PAIRS:
            if t[0] == num_fx and t[1] == rx_dose:
                pass_result = results[1]
                dose_per_fraction = int(rx_dose / 100. / num_fx)
                message_str = \
                    f'Potential fraction/dose transcription error, check ' \
                    f'with MD to confirm {num_fx} fractions should be ' \
                    f'delivered and dose per fraction {dose_per_fraction:.2f} Gy'
    return pass_result, message_str
