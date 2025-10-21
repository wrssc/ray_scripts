import logging
def get_si_extent(rso, types=None, roi_list=None):
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    initial = [1000, -1000]
    extent = [1000, -1000]
    # Generate a list to search
    type_list = []
    rois = []
    if types:
        type_list = [r.OfRoi.Name for r in rg if r.OfRoi.Type in types and r.HasContours()]
    if roi_list:
        rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in roi_list and r.HasContours()]
    check_list = list(set(type_list + rois))

    for r in rg:
        logging.debug(f'Checking {r.OfRoi.Name}')
        if r.OfRoi.Name in check_list:
            bb = r.GetBoundingBox()
            rg_min = bb[0]['z']
            rg_max = bb[1]['z']
            logging.debug(f'Extent for {r.OfRoi.Name} is rg_min < extent[0]? {rg_min}: {extent[0]} and'
                            f' rg_max > extent[1]? {rg_max}: {extent[1]}')
            if rg_min < extent[0]:
                extent[0] = rg_min
            if rg_max > extent[1]:
                extent[1] = rg_max
    if extent == initial:
        return None
    else:
        return extent
