from PlanReview.review_definitions import FIELD_OF_VIEW_PREFERENCES,PASS,FAIL


def check_image_extent(rso, **kwargs):
    """
    Check if the image extent is long enough to cover the image set and a buffer

    Args:
        rso: (namedtuple): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
    Test Patient:

        Pass TODO
        Fail: TODO
    """
    #
    # Target length
    target_extent = kwargs.get('TARGET_EXTENT')
    #
    # Tolerance for SI extent
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    #
    # Get image slices
    bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
    bb_z = [bb[0]['z'], bb[1]['z']]
    z_extent = [min(bb_z), max(bb_z)]
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    #
    # Nice strings for output
    z_str = '[' + ('%.2f ' * len(z_extent)) % tuple(z_extent) + ']'
    t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not target_extent:
        message_str = 'No targets found of type Ptv, image extent could not be evaluated'
        pass_result = FAIL
    elif z_extent[1] >= buffered_target_extent[1] and z_extent[0] <= buffered_target_extent[0]:
        message_str = f'Planning image extent {z_str} and is at ' \
                      f'least {buffer:.1f} larger than S/I target; extent ' \
                      f'{t_str}'
        pass_result = PASS
    elif z_extent[1] < buffered_target_extent[1] or z_extent[0] > buffered_target_extent[0]:
        message_str = f'Planning Image extent:{z_str} is insufficient for' \
                      f' accurate calculation. (SMALLER THAN than S/I target' \
                      f' extent: {t_str} \xB1 {buffer:.1f} cm)'
        pass_result = FAIL
    else:
        message_str = 'Target length could not be compared to image set'
        pass_result = FAIL
    return pass_result, message_str
