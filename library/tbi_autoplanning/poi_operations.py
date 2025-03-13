import math
import logging
import sys
import re
from library.StructureOperations import find_types, create_poi, check_roi
from .tbi_definitions import HFS_OVERLAP, FW, CENTRAL_JUNCTION_WIDTH, FFS_MAX_TREATMENT_LENGTH, \
    FFS_OVERSHOOT, FFS_SHIFT_BUFFER, FFS_ISO_NUMBER, HFS_MAX_TREATMENT_LENGTH, HFS_SHIFT_BUFFER, HFS_OVERSHOOT, \
    JUNCTION_POINT, HFS_POI, FFS_POI, COLORS
from .tbi_utils import determine_prefix, get_center


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


def validate_poi_name(poi_name):
    """
    Validate the format of the POI name. The last character should be an integer.

    Args:
        poi_name (str): The name of the POI.

    Returns:
        int: The integer at the end of the POI name.
    """
    try:
        return int(poi_name[-1])
    except ValueError:
        logging.error(f'Error: The name of the POI {poi_name} '
                      'does not contain an integer in the last digit.')
        raise ValueError(f'Error: The name of the POI {poi_name} does not '
                         'contain an integer in the last digit.')


def place_ffs_vmat_pois(pd_ffs, junction, offset):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_ffs.case,
                                 roi_type='External')

    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    last_iso_position = round_iso(ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + FW / 2)
    first_iso_position = round_iso(junction.Point.z - FW / 2)
    isocenter_distance = ((first_iso_position - last_iso_position)
                          / (FFS_ISO_NUMBER - 1))
    isocenter_distance = round_iso(isocenter_distance)
    ffs_junction_width = FW - isocenter_distance
    logging.info(f'Distance from inferior most point at {ffs_ext_z:.2f} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {float(ffs_ext_z - junction.Point.z):.2f} with '
                 f'spacing {isocenter_distance:.2f} requires '
                 f'{FFS_ISO_NUMBER} isocenters, '
                 f'with an overlap of {ffs_junction_width}')
    # Junction location
    pois = []
    # Round the positions of the isocenter to the nearest mm.
    coords = {'x': round_iso(junction.Point.x),
              'y': round_iso(junction.Point.y)}
    for i in range(FFS_ISO_NUMBER):
        if i != FFS_ISO_NUMBER - 1:
            coords['z'] = first_iso_position - i * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i + offset + 1]]
        color = ",".join(color_lst)
        poi = make_poi(pd_ffs.case, pd_ffs.exam,
                       coords, name=f"{FFS_POI}{i + offset + 1}",
                       color=color)
        pois.append(poi)

    return ffs_junction_width


def place_hfs_vmat_pois(pd_hfs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_hfs.case,
                                 roi_type='External')
    j_z = junction.Point.z
    hfs_ext_z = get_most_superior(pd_hfs, roi_name=external_name)
    hfs_treatment_length = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z
    iso_number = math.ceil(hfs_treatment_length / (FW - HFS_OVERLAP))
    last_iso_position = round_iso(j_z - CENTRAL_JUNCTION_WIDTH + FW / 2)
    first_iso_position = round_iso(hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - FW / 2)
    isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
    hfs_junction_width = FW - isocenter_distance

    logging.info(f'Distance from superior most point at {hfs_ext_z} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {hfs_ext_z - junction.Point.z:.2f} with '
                 f'spaced {isocenter_distance:.2f} requires '
                 f'{iso_number} isocenters')
    if hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z \
            >= HFS_MAX_TREATMENT_LENGTH:
        sys.exit('This patient may be too tall for tx')
    elif isocenter_distance >= FW - HFS_OVERLAP:
        # Increase the isocenter number by 1
        iso_number += 1
        isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
        hfs_junction_width = FW - isocenter_distance
        logging.info(f'Distancing incorrect: FW: {FW} with Overlap {HFS_OVERLAP} '
                     f'with greater computed isocenter distance {isocenter_distance},'
                     f' increasing isocenter by 1 to {iso_number}')

    # Junction location
    pois = []
    for i in range(iso_number):
        for p in pd_hfs.case.PatientModel.PointsOfInterest:
            if p.Name == f"{HFS_POI}{i + 1}":
                p.DeleteRoi()
        coords = {'x': junction.Point.x, 'y': junction.Point.y}
        if i != iso_number - 1:
            coords['z'] = junction.Point.z - CENTRAL_JUNCTION_WIDTH + FW / 2 \
                          + (iso_number - 1 - i) * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i]]
        color = ",".join(color_lst)
        poi = make_poi(pd_hfs.case, pd_hfs.exam,
                       coords, name=f"{HFS_POI}{i + 1}", color=color)
        pois.append(poi)
    return hfs_junction_width


def make_poi(case, exam, coords, name, color):
    for p in case.PatientModel.PointsOfInterest:
        if p.Name == name:
            p.DeleteRoi()
    _ = create_poi(
        case=case,
        exam=exam,
        coords=[coords['x'], coords['y'], coords['z']],
        name=name,
        color=color,
        diameter=1,
        rs_type='Control')
    return name


def find_hfff_junction_coords(pd_ffs, max_treatment_length=FFS_MAX_TREATMENT_LENGTH):
    # Find the inferior most point from the ffs scan on the external
    [external_name] = find_types(
        pd_ffs.case, roi_type='External')
    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    _ = get_most_superior(pd_ffs, roi_name=external_name)
    center = get_center(pd_ffs, external_name)
    return {
        'x': 0,
        'y': center['y'],
        # Place the junction 1/2 field width away from the isocenter
        'z': ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + max_treatment_length
    }


def place_hfff_junction_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    _ = create_poi(
        case=pd_hfs.case,
        exam=pd_hfs.exam,
        coords=[coord_hfs['x'], coord_hfs['y'], coord_hfs['z']],
        name=JUNCTION_POINT,
        color='Red',
        diameter=1,
        rs_type='Control'
    )


def round_iso(iso):
    return math.ceil(iso * 10) / 10


def sort_pois(pois):
    # Sort the list using the custom sorting key
    return sorted(pois, key=extract_number)


def extract_number(s):
    match = re.search(r'\d+$', s)
    return int(match.group()) if match else float('inf')


def determine_junction_pair(index, pois, junction_width, orientation):
    """
    Determine the junction pair based on patient orientation and POI index.

    Args:
        index (int): Index of the POI in the list.
        pois (list): List of POIs.
        junction_width (float): Width of the junction.
        orientation (str): Orientation of the patient - 'HFS' or 'FFS'.

    Returns:
        tuple: The junction pair.
    """
    if orientation == 'HFS':
        if index == 0:
            return 0, junction_width
        elif index == len(pois) - 1:
            return junction_width, CENTRAL_JUNCTION_WIDTH
        else:
            return junction_width, junction_width
    elif orientation == 'FFS':
        if index == 0:
            return CENTRAL_JUNCTION_WIDTH, junction_width
        elif index == len(pois) - 1:
            return junction_width, 0
        else:
            return junction_width, junction_width


def find_pois(pdata):
    """
    Args:
        pdata (named tuple): RS objects
    Returns:
        list: sorted points of interest with orientation-determined suffix
    """
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        suffix = FFS_POI
    else:
        suffix = HFS_POI
    pois = [p.Name for p in pdata.case.PatientModel.PointsOfInterest
            if suffix in p.Name]
    if pois:
        return sort_pois(pois)
    else:
        raise RuntimeError(f'No POIS with name beginning with {suffix} '
                           f'found in exam {pdata.exam.Name}')


def get_point_position(pdata, poi_name):
    try:
        poi_geom0 = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
            .PoiGeometries[poi_name]
    except KeyError:
        raise RuntimeError(f'No position data found for point {poi_name}')
    return poi_geom0.Point


def get_most_inferior(patient_data, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(patient_data.case, patient_data.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = patient_data.case.PatientModel.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = patient_data.case.Examinations[patient_data.exam.Name].PatientPosition
    if position == 'HFS':
        return bb_roi[0].z
    elif position == 'FFS':
        return bb_roi[0].z
    else:
        return None


def get_most_superior(patient_data, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most superior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(patient_data.case, patient_data.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = patient_data.case.PatientModel.StructureSets[patient_data.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = patient_data.case.Examinations[patient_data.exam.Name].PatientPosition
    logging.debug(f'Position:{position}, Bounding Box: {bb_roi[0].z}, {bb_roi[1].z}')
    if position == 'HFS':
        return bb_roi[1].z
    elif position == 'FFS':
        return bb_roi[1].z
    else:
        return None


def estimate_patient_height(pd_hfs, pd_ffs, external_roi_name="External", junction_name="junction"):
    """
    Estimate patient height using HFS and FFS scans.

    The function obtains the top (head) and bottom (feet) positions from the external ROI
    and uses a common junction point (defined in both scans) to cross-check the computation.

    Args:
        pd_hfs: Patient data for the HFS (Head First Supine) scan.
        pd_ffs: Patient data for the FFS (Feet First Supine) scan.
        external_roi_name (str): Name of the external ROI. Default is "External".
        junction_name (str): Name of the junction POI. Default is "junction".

    Returns:
        float: Estimated patient height (in the same unit as the z-coordinate, typically centimeters).
    """
    # Retrieve the superior-most z-coordinate from the HFS scan (e.g., top of the head)
    head_top = get_most_superior(pd_hfs, external_roi_name)

    # Retrieve the inferior-most z-coordinate from the FFS scan (e.g., bottom of the feet)
    feet_bottom = get_most_inferior(pd_ffs, external_roi_name)

    # Retrieve the z-coordinate of the junction point from both scans
    junction_hfs_z = get_point_position(pd_hfs, junction_name).z
    junction_ffs_z = get_point_position(pd_ffs, junction_name).z

    # For clarity, compute distances above and below the junction point:
    head_to_junction = head_top - junction_hfs_z  # distance from head to junction
    junction_to_feet = junction_ffs_z - feet_bottom  # distance from junction to feet

    # The estimated patient height is the sum of these two distances.
    estimated_height = head_to_junction + junction_to_feet

    logging.info(f"Patient height estimation: {estimated_height:.2f} cm")

    return estimated_height
