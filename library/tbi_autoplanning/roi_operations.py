"""

"""
import logging
from StructureSetOperations import change_roi_type


def get_roi_geometry(case, exam, roi_name):
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


# ROI Existence and basic checks
def roi_in_list(case, structure_name, roi_list=None):
    if not roi_list:
        roi_obj_list = [r for r in case.PatientModel.RegionsOfInterest]
    else:
        roi_obj_list = []
        for n in roi_list:
            roi_obj_list += [r for r in case.PatientModel.RegionsOfInterest
                             if r.Name == n]

    if any(roi.Name == structure_name for roi in roi_obj_list):
        return True
    else:
        return False


def poi_in_list(case, poi_name, poi_list=None):
    if not poi_list:
        poi_obj_list = [p for p in case.PatientModel.PointsOfInterest]
    else:
        poi_obj_list = []
        for n in poi_list:
            poi_obj_list += [p for p in case.PatientModel.PointsOfInterest
                             if p.Name == n]

    if any(poi.Name == poi_name for poi in poi_obj_list):
        return True
    else:
        return False


def roi_has_contours(patient_data, structure_name):
    logging.debug(f'Checking for contours in {patient_data.case.CaseName} for {structure_name}')
    if roi_in_list(patient_data.case, structure_name):
        roi_geom = get_roi_geometry(patient_data.case, patient_data.exam, structure_name)
        logging.debug(f'ROI {structure_name} has contours: {roi_geom.HasContours()}')
        if roi_geom.HasContours():
            return True
    return False


def find_roi_prefix(case, roi_match):
    # Return all structures whose name contains roi_prefix
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_match in r.Name:
            found_roi.append(r.Name)
    return found_roi


def toggle_ptv_type(rs_obj, rois, roi_type):
    # Sometimes in the course of RayStation planning, we need to change our type
    # 'cause of stupid dose grids.
    for r in rois:
        change_roi_type(rs_obj.case, roi_name=r, roi_type=roi_type)


# ROI Creation and Deletion
def delete_roi(case, structure_name):
    if roi_in_list(case, structure_name):
        try:
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            return True
        except Exception as e:
            logging.warning(f'Could not delete {structure_name}: {e}')
            return False
    else:
        return True





