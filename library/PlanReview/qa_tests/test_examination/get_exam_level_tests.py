from PlanReview.review_definitions import REVIEW_LEVELS
from .compare_exam_data_to_preplan import check_exam_date_and_slices
from .check_exam_date import check_exam_date
from .check_exam_data import check_exam_data
from .check_localization import check_localization
from .check_axial_orientation import check_axial_orientation
from .check_image_extent import check_image_extent
from .check_couch_extent import check_couch_extent
from .check_fov_overlap_external import check_fov_overlap_external
from .check_contour_gaps import check_contour_gaps
from .check_support_material import check_support_material
from .get_si_extent import get_si_extent


# from .exam_review_tests import *


def get_exam_level_tests(rso, values=None):
    if not rso.exam:
        return {}
    #
    # Get target length
    target_extent = get_si_extent(rso, types=['Ptv'])
    patient_checks_dict = {
        f"{REVIEW_LEVELS['PREPLAN_DATA']}::DICOM RayStation Comparison":
            (check_exam_data, {}),
        f"{REVIEW_LEVELS['PREPLAN_DATA']}::Exam Date Is Recent":
            (check_exam_date, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Localization Point Exists":
            (check_localization, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Contours are interpolated":
            (check_contour_gaps, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Supports correctly overriden":
            (check_support_material, {}),
        f"{REVIEW_LEVELS['PREPLAN_DATA']}::Image Is Axially Oriented":
            (check_axial_orientation, {}),
    }
    # TODO: If the target extent is NONE, then we ought to try and get one
    #  from dose
    if target_extent:
        patient_checks_dict.update({
            f"{REVIEW_LEVELS['PREPLAN_DATA']}::Image extent sufficient":
                (check_image_extent, {'TARGET_EXTENT': target_extent}),
            f"{REVIEW_LEVELS['PATIENT_MODEL']}::Couch extent sufficient":
                (check_couch_extent, {'TARGET_EXTENT': target_extent}),
            f"{REVIEW_LEVELS['PATIENT_MODEL']}::Edge of scan overlaps patient at key slices":
                (check_fov_overlap_external, {'TARGET_EXTENT': target_extent}),
        })
    if values:
        patient_checks_dict.update({
            f"{REVIEW_LEVELS['PREPLAN_DATA']}::Data Matches CT Document":
                (check_exam_date_and_slices, {'VALUES': values}),
        })
    return patient_checks_dict
