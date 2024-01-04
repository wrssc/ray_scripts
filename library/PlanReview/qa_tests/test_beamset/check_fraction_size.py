from typing import Tuple, NamedTuple
from PlanReview.review_definitions import (
    PASS, ALERT, DOSE_FRACTION_PAIRS
)


def check_fraction_size(rso: NamedTuple) -> Tuple[int, str]:
    """ Check Fraction Size

    Checks the fraction size for common errors based on predefined
    often-mixed-up fractionations (DOSE_FRACTION_PAIRS).

    Args:
        rso (NamedTuple): RayStation Beamset Object containing
                          information about the plan's fractionation.

    Returns:
        Tuple[int, str]: First element is the result (PASS/ALERT/FAIL),
                         Second element is the detailed message string.

    Pseudocode:
    1. Extract fractionation details from rso.
    2. Initialize result variables.
    3. Try to get the Prescription dose.
    4. Check for matching dose pairs from the DOSE_FRACTION_PAIRS list.
    5. Build the appropriate message string based on the checks.
    6. Return the result and message.

    Test Patients:
        Pass: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022: Pelv_THI_R0A0
        Fail: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022: Pelv_T3D_R0A0
    """

    # Number of fractions from the RayStation Beamset Object
    num_fx = rso.beamset.FractionationPattern.NumberOfFractions

    # Default result is PASS
    pass_result = PASS

    # Default message
    message_str = f'Beamset {rso.beamset.DicomPlanLabel} fractionation not flagged'

    # Initialize prescription dose to None
    rx_dose = None

    # Try to extract the Prescription dose
    try:
        rx_dose = rso.beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue
    except AttributeError:
        # ALERT if prescription is not defined
        pass_result = ALERT
        message_str = f'No Prescription is Defined for Beamset: {rso.beamset.DicomPlanLabel}'

    # Constant for converting cGy to Gy
    cgy_to_gy_conversion = 100.0

    # Check for matching dose pairs in DOSE_FRACTION_PAIRS, which contains often mixed-up fractionations
    if rx_dose is not None:
        for dose_fraction_pair in DOSE_FRACTION_PAIRS:
            if dose_fraction_pair[0] == num_fx and dose_fraction_pair[1] == rx_dose:
                pass_result = ALERT
                dose_per_fraction = int(rx_dose / cgy_to_gy_conversion / num_fx)
                message_str = f"Verify with MD: {num_fx} fractions at {dose_per_fraction:.2f}" \
                              " Gy/fraction due to high risk of transcription error."

    return pass_result, message_str
