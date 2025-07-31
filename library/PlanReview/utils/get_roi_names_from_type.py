def get_roi_names_from_type(rso, roi_type, test_has_contours=False):
    rois = []
    if type(roi_type) is not list:
        roi_type = [roi_type]
    for r in rso.case.PatientModel.RegionsOfInterest:
        for t in roi_type:
            if r.Type == t and t == 'External':
                return [r.Name]
            elif r.Type == t:
                if test_has_contours:
                    ss = rso.case.PatientModel.StructureSets[rso.exam.Name]
                    if ss.RoiGeometries[r.Name].HasContours():
                        rois.append(r.Name)
                else:
                    # If has_contours is False, we still want to include the ROI
                    # even if it has no contours.
                    rois.append(r.Name)
    return rois
