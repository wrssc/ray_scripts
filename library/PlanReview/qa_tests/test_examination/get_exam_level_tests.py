from .compare_exam_data_to_preplan import check_exam_date_and_slices
from .exam_review_tests import *


def get_exam_level_tests(rso, values=None):
    if not rso.exam:
        return {}
    #
    # Get target length
    target_extent = get_si_extent(rso, types=['Ptv'])
    patient_checks_dict = {
        "DICOM RayStation Comparison":
            (check_exam_data, {}),
        "Exam Date Is Recent":
            (compare_exam_date, {}),
        "Localization Point Exists":
            (check_localization, {}),
        "Contours are interpolated":
            (check_contour_gaps, {}),
        "Supports correctly overriden":
            (check_support_material, {}),
        "Image Is Axially Oriented":
            (match_image_directions, {}),
    }
    # TODO: If the target extent is NONE, then we ought to try and get one
    #  from dose
    if target_extent:
        patient_checks_dict.update({
            "Image extent sufficient":
                (image_extent_sufficient,
                 {'TARGET_EXTENT': target_extent}),
            "Couch extent sufficient":
                (couch_extent_sufficient,
                 {'TARGET_EXTENT': target_extent}),
            "Edge of scan overlaps patient at key slices":
                (external_overlaps_fov,
                 {'TARGET_EXTENT': target_extent}),
        })
    if values:
        patient_checks_dict.update({
            "Exam Data Matches CT Document":
                (check_exam_date_and_slices, {'VALUES': values}),
        })
    return patient_checks_dict
