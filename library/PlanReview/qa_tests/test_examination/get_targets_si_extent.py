def get_targets_si_extent(rso):
    types = ['Ptv']
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    extent = [1000., -1000]
    for r in rg:
        if r.OfRoi.Type in types and r.HasContours():
            bb = r.GetBoundingBox()
            rg_min = bb[0]['z']
            rg_max = bb[1]['z']
            if rg_min < extent[0]:
                extent[0] = rg_min
            if rg_max > extent[1]:
                extent[1] = rg_max
    return extent