def get_si_extent(rso, types=None, roi_list=None):
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    initial = [-1000, 1000]
    extent = [-1000, 1000]
    # Generate a list to search
    type_list = []
    rois = []
    if types:
        type_list = [r.OfRoi.Name for r in rg if r.OfRoi.Type in types and r.HasContours()]
    if roi_list:
        rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in roi_list and r.HasContours()]
    check_list = list(set(type_list + rois))

    for r in rg:
        if r.OfRoi.Name in check_list:
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    if extent == initial:
        return None
    else:
        return extent
