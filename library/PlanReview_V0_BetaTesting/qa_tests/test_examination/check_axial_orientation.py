from typing import NamedTuple, Tuple, Dict, Optional
from PlanReview_V0_BetaTesting.review_definitions import PASS, FAIL


def check_axial_orientation(rso: NamedTuple, **kwargs: Optional[bool]) -> Tuple[str, str]:
    """Check Axial Orientation
       Validates the orientation of the patient images by comparing it against a pre-defined set of rules
       based on the patient's position.

    Args:
        rso (NamedTuple): ScriptObjects in RayStation containing
                          [case ('RayStation Case Object'),
                           exam ('RayStation Exam Object'),
                           plan ('RayStation Plan Object'),
                           beamset ('RayStation BeamSet Object'),
                           db ('RayStation Database Object')]
        **kwargs: Additional keyword arguments (not used).

    Returns:
        pass_result, message_str (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                          Second element is the message string.

    Pseudocode:
    1. Get patient position from the exam.
    2. Define the expected direction vectors for each patient position.
    3. Compare the actual direction vectors of the image stack with the expected ones.
    4. Generate a message string based on the comparison.
    5. Return the pass/fail result and the message string.

    Test Patients:
        Pass:
        Fail:

    """
    # Match the directions that a correctly oriented image should have
    patient_position = str(rso.exam.PatientPosition)

    stack_details = {
        'FFDL': {'direction_column': {'x': int(1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(-1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFDR': {'direction_column': {'x': int(-1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFP': {'direction_column': {'x': int(0), 'y': int(-1), 'z': int(0)},
                'direction_row': {'x': int(-1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFS': {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFS': {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFDL': {'direction_column': {'x': int(1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(-1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFDR': {'direction_column': {'x': int(-1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFP': {'direction_column': {'x': int(0), 'y': int(-1), 'z': int(0)},
                'direction_row': {'x': int(-1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
    }
    col_dir = rso.exam.Series[0].ImageStack.ColumnDirection
    row_dir = rso.exam.Series[0].ImageStack.RowDirection
    sli_dir = rso.exam.Series[0].ImageStack.SliceDirection
    message_str = ""
    pass_result = PASS
    if col_dir != stack_details[patient_position]['direction_column'] or \
            sli_dir != stack_details[patient_position]['direction_slice']:
        message_str += f"Exam {rso.exam.Name} has been rotated and will not transfer to iDMS!"
        pass_result = FAIL
    if row_dir != stack_details[patient_position]['direction_row']:
        message_str += f"Exam {rso.exam.Name} has been rotated or was acquired" \
                       + " with gantry tilt and should be reoriented!"
        pass_result = FAIL
    if not message_str:
        message_str = 'Image set {} is not rotated'.format(rso.exam.Name)

    return pass_result, message_str
