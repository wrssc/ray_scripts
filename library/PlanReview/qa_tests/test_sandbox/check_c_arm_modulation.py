from PlanReview.review_definitions import (PASS, ALERT, FAIL,)

def check_c_arm_modulation(rso):
    """
    Compute the modulation of the beamset.

    Pseudo-code:
    * Determine if the beamset is C-arm based
    * Determine if the plan is VMAT or 3D Conformal
    * If those conditions are met, determine the dose from the
        prescription
    * Sum the beam MU
    * The ratio of total MU to the prescription in cGy should be
      evaluated

    Args:
        rso (NamedTuple): RayStation script objects
    Returns:
        tuple: A tuple containing the status and message

    Test Patient:
        PASS:
        ALERT:
        Note jupyter notebook:
    """

