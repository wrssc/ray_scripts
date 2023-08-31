def get_roi_list(case, exam_name=None):
    """
    Get a list of all rois
    Args:
        case: RS case object

    Returns:
        roi_list: [str1,str2,...]: a list of roi names
    """
    roi_list = []
    if exam_name:
        structure_sets = [case.PatientModel.StructureSets[exam_name]]
    else:
        structure_sets = [s for s in case.PatientModel.StructureSets]

    for s in structure_sets:
        for r in s.RoiGeometries:
            if r.OfRoi.Name not in roi_list:
                roi_list.append(r.OfRoi.Name)
    return roi_list
