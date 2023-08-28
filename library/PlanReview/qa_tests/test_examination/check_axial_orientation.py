from PlanReview.review_definitions import PASS, FAIL


def check_axial_orientation(rso):
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
