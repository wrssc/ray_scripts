from PlanReview.review_definitions import PASS, FAIL


def check_localization(rso):
    poi_coord = {}
    localization_found = False
    for p in rso.case.PatientModel.StructureSets[rso.exam.Name].PoiGeometries:
        if p.OfPoi.Type == 'LocalizationPoint':
            point = p
            poi_coord = p.Point
            localization_found = True
            break
    if poi_coord:
        message_str = f"Localization point {point.OfPoi.Name} exists and " \
                      f"has coordinates."
        pass_result = PASS
    elif localization_found:
        message_str = f"Localization point {point.OfPoi.Name} does not " \
                      f"have coordinates."
        pass_result = FAIL
    else:
        message_str = "No point of type LocalizationPoint found"
        pass_result = FAIL
    return pass_result, message_str
