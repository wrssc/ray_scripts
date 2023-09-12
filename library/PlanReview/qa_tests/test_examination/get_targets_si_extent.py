def get_targets_si_extent(rso):
    types = ['Ptv']
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    extent = [-1000., 1000]
    for r in rg:
        if r.OfRoi.Type in types and r.HasContours():
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    return extent