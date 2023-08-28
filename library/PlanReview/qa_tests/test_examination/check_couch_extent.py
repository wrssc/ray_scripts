from PlanReview.review_definitions import (
    FIELD_OF_VIEW_PREFERENCES, TOMO_DATA, TRUEBEAM_DATA, PASS, FAIL)
from .get_si_extent import get_si_extent


def check_couch_extent(rso, **kwargs):
    """
       Check PTV volume extent have supports under them
       Args:
           parent_key:
           rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
           target_extent: [min, max extent of target]
       Returns:
            (Pass/Fail/Alert, Message to Display)
       Test Patient:

           Pass: Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Anal_THI: Anal_THI
           Fail (bad couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: ChwL_3DC: SCV PAB
           Fail (no couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Pros_VMA: Pros_VMA
       """
    target_extent = kwargs.get('TARGET_EXTENT')
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    #
    # Get support structure extent
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    supports = TOMO_DATA['SUPPORTS'] + TRUEBEAM_DATA['SUPPORTS']
    support_rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in supports]
    couch_extent = get_si_extent(rso=rso, roi_list=supports)

    if couch_extent:
        # Nice strings for output
        z_str = '[' + ('%.2f ' * len(couch_extent)) % tuple(couch_extent) + ']'
    #
    # Tolerance for SI extent
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    if target_extent:
        # Output string
        t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not couch_extent:
        message_str = 'No support structures found. No couch check possible'
        pass_result = FAIL
    elif couch_extent[1] >= buffered_target_extent[1] and \
            couch_extent[0] <= buffered_target_extent[0]:
        message_str = 'Supports (' + ', '.join(support_rois) + f') ' \
                      + f'span {z_str} and is at least {buffer:.1f} cm larger ' \
                      + f'than S/I target extent {t_str}'
        pass_result = PASS
    elif couch_extent[1] < buffered_target_extent[1] or \
            couch_extent[0] > buffered_target_extent[0]:
        message_str = 'Support extent (' + ', '.join(support_rois) + ') ' \
                      + f':{z_str} is not fully under the target.' \
                      + f'(SMALLER THAN than S/I target extent: {t_str} \xB1 ' \
                      + f'{buffer:.1f} cm)'
        pass_result = FAIL
    else:
        message_str = 'Target length could not be compared to support extent'
        pass_result = FAIL
    # Prepare output
    return pass_result, message_str
