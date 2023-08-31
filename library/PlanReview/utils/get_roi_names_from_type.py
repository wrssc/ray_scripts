def get_roi_names_from_type(rso, roi_type):
    rois = []
    if type(roi_type) is not list:
        roi_type = [roi_type]
    for r in rso.case.PatientModel.RegionsOfInterest:
        for t in roi_type:
            if r.Type == t and t == 'External':
                return [r.Name]
            elif r.Type == t:
                rois.append(r.Name)

    return rois
