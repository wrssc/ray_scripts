from typing import NamedTuple, Tuple
from PlanReview.review_definitions import PASS, FAIL, ALERT, GRID_PREFERENCES
import numpy as np


def calculate_slice_thickness(img_series):
    slice_positions = np.array(img_series.ImageStack.SlicePositions)
    return np.diff(slice_positions)


def check_slice_thickness(rso: NamedTuple) -> Tuple[str, str]:
    """ Check Slice Thickness
        Checks the slice thickness for the current exam and plan type.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]

        Returns:
            Tuple[str, str]: First element is the status (PASS/FAIL/ALERT),
                         Second element is the message string

        Pseudocode:
        1. Initialize empty message string and result variable.
        2. Loop through each plan type in GRID_PREFERENCES.
        3. Check if the current plan label matches any of the PLAN_NAMES in the plan type.
        4. If so, calculate the slice thickness and compare it to the expected slice thickness.
        5. Generate the appropriate message string based on the comparison.
        6. Return the status and message string.
        Example Outcome:
            ('PASS', 'Slice spacing 0.200 cm appropriate for plan type LUNG_SBRT')

        Test Patients:
            Pass: Needed
            Fail: Needed
    """

    message_str = ""
    pass_result = ""
    slice_thickness = np.array([])  # Initialize to empty numpy array

    for plan_type, preferences in GRID_PREFERENCES.items():
        plan_names = preferences.get('PLAN_NAMES', [])
        nominal_slice_thickness = preferences.get('SLICE_THICKNESS', 0.0)

        if any(plan_name in rso.beamset.DicomPlanLabel for plan_name in plan_names):
            for exam_series in rso.exam.Series:
                slice_thickness = calculate_slice_thickness(exam_series)

                if slice_thickness.size > 0:
                    is_thickness_close = np.isclose(slice_thickness, nominal_slice_thickness).all()
                    is_thickness_smaller = all(slice_thickness < nominal_slice_thickness)

                    if is_thickness_close or is_thickness_smaller:
                        message_str = f'Slice spacing {np.amax(slice_thickness):.3f} cm ' \
                                      f'appropriate for plan type {plan_names}'
                        pass_result = PASS
                    else:
                        message_str = f'Slice spacing {np.amax(slice_thickness):.3f} cm ' \
                                      f'TOO LARGE for plan type {plan_names}'
                        pass_result = FAIL
                else:
                    message_str = 'Slice thickness data is missing.'
                    pass_result = ALERT

    if not message_str:
        for exam_series in rso.exam.Series:
            slice_thickness = calculate_slice_thickness(exam_series)
        if slice_thickness.size > 0:
            message_str = f'Plan type unknown, check slice spacing ' \
                          f'{np.axax(slice_thickness):.3f} cm carefully'
            pass_result = ALERT
        else:
            message_str = 'Slice thickness data is missing for unknown plan type.'
            pass_result = ALERT

    return pass_result, message_str

