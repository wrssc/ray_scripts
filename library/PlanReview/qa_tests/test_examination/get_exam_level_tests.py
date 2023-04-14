from PlanReview.qa_tests.test_examination import exam_review_tests


def get_exam_level_tests(rso):
    if not rso.exam:
        return {}
    #
    # Get target length
    target_extent = exam_review_tests.get_si_extent(rso, types=['Ptv'])
    patient_checks_dict = {
        "DICOM RayStation Comparison":
            (exam_review_tests.check_exam_data, {}),
        "Exam Date Is Recent":
            (exam_review_tests.compare_exam_date, {}),
        "Localization Point Exists":
            (exam_review_tests.check_localization, {}),
        "Contours are interpolated":
            (exam_review_tests.check_contour_gaps, {}),
        "Supports correctly overriden":
            (exam_review_tests.check_support_material, {}),
        "Image Is Axially Oriented":
            (exam_review_tests.match_image_directions, {}),
    }
    # TODO: If the target extent is NONE, then we ought to try and get one
    #  from dose
    if target_extent:
        patient_checks_dict.update({
            "Image extent sufficient":
                (exam_review_tests.image_extent_sufficient,
                 {'TARGET_EXTENT': target_extent}),
            "Couch extent sufficient":
                (exam_review_tests.couch_extent_sufficient,
                 {'TARGET_EXTENT': target_extent}),
            "Edge of scan overlaps patient at key slices":
                (exam_review_tests.external_overlaps_fov,
                 {'TARGET_EXTENT': target_extent}),
        })
    return patient_checks_dict
