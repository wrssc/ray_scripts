from typing import NamedTuple, Tuple
from PlanReview_V0_BetaTesting.review_definitions import GRID_PREFERENCES, \
    PASS, FAIL, DOSE_GRID_DEFAULT


def check_dose_grid(rso: NamedTuple) -> Tuple[str, str]:
    """Check Dose Grid
       Determines the appropriate grid size based on the plan name and dose per fraction.

    Args:
        rso (NamedTuple): ScriptObjects in RayStation containing
                         [case ('RayStation Case Object'),
                          exam ('RayStation Exam Object'),
                          plan ('RayStation Plan Object'),
                          beamset ('RayStation BeamSet Object'),
                          db ('RayStation Database Object')]

    Returns:
        Tuple[str, str]: First element is the status (PASS/FAIL),
                         Second element is the message string

    Pseudocode:
    1. Extract the dose grid dimensions from the beamset in rso
    2. Try to calculate the fractional dose from the beamset in rso
    3. Initialize an empty message string and a variable for pass_result
    4. Iterate over the keys and values in GRID_PREFERENCES
        * Check if the plan name in the beamset matches any of the PLAN_NAMES in GRID_PREFERENCES
            ** If so, compare the grid size with the corresponding DOSE_GRID in GRID_PREFERENCES
            ** Update message string and pass_result based on the comparison
        * If no plan name match, check for fraction size violations using FRACTION_SIZE_LIMIT
            ** Update message string and pass_result accordingly
    5. If no plan-specific grid preferences apply, use a default grid size to check
    6. Return the result (PASS/FAIL) and the message string

    Test Patients:
        Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
        Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: PROS_SBR
    """

    # Extract dose grid dimensions from the given RayStation object's beamset
    dose_grid_voxel_size = rso.beamset.FractionDose.InDoseGrid.VoxelSize
    dose_grid_dimensions = (dose_grid_voxel_size.x, dose_grid_voxel_size.y, dose_grid_voxel_size.z)

    # Attempt to calculate fractional dose from the prescription if available
    try:
        prescribed_total_dose = rso.beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue
        number_of_fractions = rso.beamset.FractionationPattern.NumberOfFractions
        fractional_dose = prescribed_total_dose / float(number_of_fractions)
    except AttributeError:
        fractional_dose = None

    # Initialize result and message variables
    evaluation_result = None
    evaluation_message = ""

    # Check against plan-specific grid preferences
    for plan_type, preferences in GRID_PREFERENCES.items():
        # If current plan name matches any in the list of plan names for this type
        if any(plan_name in rso.beamset.DicomPlanLabel for plan_name in preferences['PLAN_NAMES']):
            matched_plans = [plan_name for plan_name in preferences['PLAN_NAMES'] if
                             plan_name in rso.beamset.DicomPlanLabel]

            # Check if any of the dose grid dimensions exceed the recommended size
            violating_dimensions = [dim for dim in dose_grid_dimensions if dim > preferences['DOSE_GRID']]

            if violating_dimensions:
                evaluation_message = f"Dose grid too large for plan type {matched_plans}. " \
                                     f"Grid size is {dose_grid_dimensions} cm " \
                                     f"and should be {preferences['DOSE_GRID']} cm"
                evaluation_result = FAIL
            else:
                evaluation_message = f"Dose grid appropriate for plan type {matched_plans}. " \
                                     f"Grid size is {dose_grid_dimensions} cm"
                evaluation_result = PASS

        # Check for fractional dose violations if no plan name matched
        elif preferences['FRACTION_SIZE_LIMIT']:
            if fractional_dose is None:
                evaluation_message = "Dose grid cannot be evaluated for this plan. " \
                                     "No fractional dose available."
                evaluation_result = FAIL
            elif fractional_dose >= preferences['FRACTION_SIZE_LIMIT'] and any(
                    dim > preferences['DOSE_GRID'] for dim in dose_grid_dimensions):
                evaluation_message = f"Dose grid may be too large for this plan based on " \
                                     f"fractional dose {fractional_dose:.0f} > " \
                                     f"{preferences['FRACTION_SIZE_LIMIT']:.0f} cGy. " \
                                     f"Grid size is {dose_grid_dimensions} cm and " \
                                     f"should be {preferences['DOSE_GRID']} cm"
                evaluation_result = FAIL

    # If no specific grid preferences were applicable, evaluate against a default grid size
    if evaluation_message == "":
        violating_dimensions = [dim for dim in dose_grid_dimensions if dim > DOSE_GRID_DEFAULT]
        if violating_dimensions:
            evaluation_message = f"Dose grid too large. Grid size is {dose_grid_dimensions} cm " \
                                 f"and should be {DOSE_GRID_DEFAULT} cm"
            evaluation_result = FAIL
        else:
            evaluation_message = f"Dose grid appropriate. Grid size is {dose_grid_dimensions} cm"
            evaluation_result = PASS

    return evaluation_result, evaluation_message

