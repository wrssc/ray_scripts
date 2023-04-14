def get_roi_names_from_type(rso, roi_type):
    rois = []
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            return [r.Name]
        elif r.Type == roi_type:
            rois.append(r.Name)

    return rois
