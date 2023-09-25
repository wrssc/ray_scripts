from typing import NamedTuple, Tuple, Optional, List
from PlanReview.review_definitions import (
    FIELD_OF_VIEW_PREFERENCES, TOMO_DATA, TRUEBEAM_DATA, PASS, FAIL)
from .get_si_extent import get_si_extent


def format_extent(extent: List[float]) -> str:
    """Formats a list of floats as a string representation of extents."""
    return '[' + ('%.2f ' * len(extent)) % tuple(extent) + ']'


def fetch_support_rois(rg, supports: List[str]) -> List[str]:
    """Fetches the list of support ROIs from rg."""
    return [r.OfRoi.Name for r in rg if r.OfRoi.Name in supports]


def check_couch_extent(rso: NamedTuple, **kwargs: Optional[List[float]]) -> Tuple[str, str]:
    """Check Couch Extent
        Check if PTV volume extents have supports under them.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                              [case ('RayStation Case Object'),
                               exam ('RayStation Exam Object'),
                               plan ('RayStation Plan Object'),
                               beamset ('RayStation BeamSet Object'),
                               db ('RayStation Database Object')]
            **kwargs: Additional keyword arguments, options include:
                'TARGET_EXTENT' (Optional): Extent of the target to compare with the couch extent.

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                      Second element is the message string

        Pseudocode:
            1. Retrieve 'TARGET_EXTENT' from kwargs
            2. Get support structure extents
            3. Determine if the couch extent is adequate for the target
            4. Prepare and return message string and result (PASS/FAIL/ALERT)

        Test Patients:
            Pass: Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022: Case THI: Anal_THI: Anal_THI
            Fail: (bad couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022: Case THI: ChwL_3DC: SCV PAB; (no couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022: Case THI: Pros_VMA: Pros_VMA
    """
    target_extent = kwargs.get('TARGET_EXTENT')
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']

    # Fetch support structure extents
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    supports = TOMO_DATA['SUPPORTS'] + TRUEBEAM_DATA['SUPPORTS']
    support_rois = fetch_support_rois(rg, supports)
    couch_extent = get_si_extent(rso=rso, roi_list=supports)

    # Use helper function to format extent strings
    z_str = format_extent(couch_extent) if couch_extent else None
    t_str = format_extent([target_extent[0] - buffer, target_extent[1] + buffer]) if target_extent else None

    # Determine pass/fail status
    if not couch_extent:
        message_str = 'No support structures found. No couch check possible'
        pass_result = FAIL
    elif couch_extent[1] >= (target_extent[1] + buffer) and couch_extent[0] <= (target_extent[0] - buffer):
        message_str = f'Supports ({", ".join(support_rois)}) span {z_str} and is at least {buffer:.0f} cm larger than S/I target extent {t_str}'
        pass_result = PASS
    else:
        message_str = f'Support extent ({", ".join(support_rois)}): {z_str} is not fully under the target. (SMALLER THAN S/I target extent: {t_str} ± {buffer:.1f} cm)'
        pass_result = FAIL

    return pass_result, message_str
