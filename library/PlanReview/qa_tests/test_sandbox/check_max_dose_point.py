from PlanReview.review_definitions import (PASS, ALERT, FAIL,)
import numpy as np
import math
import logging


def is_roi(rso, roi_name):
    try:
        if rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name].HasContours():
            return True
        return False
    except Exception as e:
        return False


def sort_rois(rso, roi_types):
    roi_type_dict = {}
    for r in roi_types:
        roi_type_dict[r] = []
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type in roi_types:
            if is_roi(rso, r.Name):
                roi_type_dict[r.Type].append(r.Name)
    return roi_type_dict


def check_bounding_box_for_roi(rso, point, roi):
    if is_roi(rso, roi):
        bb = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi].GetBoundingBox()
        if is_point_in_bounding_box(bb, point):
            return True
        else:
            return False
    else:
        return False


def is_point_in_bounding_box(bbox, point):
    """
    Check if a point is within a bounding box.

    Args:
        bbox (list of dicts): A list containing two dictionaries,
                              each with 'x', 'y', and 'z' keys representing
                              the minimum and maximum corners of the bounding box.
        point (dict): A dictionary with 'x', 'y', and 'z' keys representing
                      the point to check.

    Returns:
        bool: True if the point is inside the bounding box, False otherwise.
    """
    min_corner = bbox[0]
    max_corner = bbox[1]

    return (min_corner['x'] <= point['x'] <= max_corner['x'] and
            min_corner['y'] <= point['y'] <= max_corner['y'] and
            min_corner['z'] <= point['z'] <= max_corner['z'])


def is_point_inside_polygon_2d(point, polygon):
    """
    Determine if a 2D point is inside a 2D polygon.

    Imagine a 2D polygon on a plane, defined by its vertices.
    * Place a point somewhere on this plane, either inside or outside the polygon.
    * Draw vectors (arrows) from this point to each vertex of the polygon.
    * For each pair of consecutive vectors (from the point to two neighboring vertices),
      calculate the angle between them. These angles are typically measured in a clockwise
      or counterclockwise direction.
    * Sum all these angles.

    If the point is inside the polygon, the sum of these angles will be approximately 360 degrees (or
    2π radians). If the point is outside the polygon, the sum of the angles will be
    significantly less than 360 degrees. The idea behind this method is that by "walking around"
    the point via the polygon's vertices, you can determine whether the point lies within the polygon's
    bounds based on how much you've had to turn to face each new vertex.

    Args:
        point (numpy.array): A point represented as a numpy array [x, y].
        polygon (numpy.array): A polygon represented as a numpy array [[x1, y1], [x2, y2], ...].

    Returns:
        bool: True if the point is inside the polygon, False otherwise.
    """
    total_angle = 0

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]

        vec1 = p1 - point
        vec2 = p2 - point

        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)

        if norms == 0:
            return False  # The point coincides with a polygon vertex

        angle = np.arccos(dot_product / norms)
        total_angle += angle

    return abs(total_angle) > math.pi


def find_contours_containing_point(contours, point, slice_thick):
    unique_z_values = set()

    # Convert the point to a 2D NumPy array (ignoring z-coordinate)
    point_2d = np.array([point['x'], point['y']])

    for contour in contours:
        # Convert each contour to a NumPy array and separate 2D coordinates
        contour_np = np.array([(p['x'], p['y'], p['z']) for p in contour])
        contour_2d = contour_np[:, :2]  # Take only x and y

        # Extract the z positions
        z_positions = contour_np[:, 2]

        # Check if the z position is within the specified thickness
        if np.any(np.abs(z_positions - point['z']) <= slice_thick):
            # Check if the point is inside the 2D projection of the contour
            if is_point_inside_polygon_2d(point_2d, contour_2d):
                unique_z_values.update(z_positions)
                # If the point is inside the contour, stop searching
                break

    return list(unique_z_values)


def get_slice_thickness(rso):
    z0 = rso.case.PatientModel.StructureSets[rso.exam.Name].OnExamination.Series[0].ImageStack.SlicePositions[0]
    z1 = rso.case.PatientModel.StructureSets[rso.exam.Name].OnExamination.Series[0].ImageStack.SlicePositions[1]
    return abs(z1 - z0)


def get_beamset_dose_at_point(rso,point):
    """
    Determine the maximum dose at the specified point.
    Args:
        rso: (NamedTuple): RayStation script objects
        point: (dict): A dictionary with 'x', 'y', and 'z' keys representing the point to check
    Returns:
        (float): The maximum dose at the specified point in Gy
    """
    maximum_per_fraction_dose = rso.beamset.FractionDose.InterpolateDoseInPoint(
        Point=point, PointFrameOfReference=rso.beamset.FrameOfReference)
    number_of_fractions = rso.beamset.FractionationPattern.NumberOfFractions
    return maximum_per_fraction_dose * number_of_fractions / 100  # cGy to Gy


def check_rx_versus_primary(test_rx, primary_rx):
    """
    Check if the test prescription is the same as the primary prescription.
    Args:
    :param test_rx: (script object): Test prescription
    :param primary_rx: (script object): Primary prescription
    Returns:
    :return: (bool): True if the test prescription is the same as the primary
    """
    if not primary_rx:
        return False
    test_dose = safe_get_attribute(test_rx, 'DoseValue')
    primary_dose = safe_get_attribute(primary_rx, 'DoseValue')
    test_on_structure = safe_get_attribute(test_rx, 'OnStructure')
    primary_on_structure = safe_get_attribute(primary_rx, 'OnStructure')
    if test_on_structure:
        test_structure_name = safe_get_attribute(test_on_structure, 'Name')
    else:
        test_structure_name = None
    if primary_on_structure:
        primary_structure_name = safe_get_attribute(primary_on_structure, 'Name')
    else:
        primary_structure_name = None
    test_dose_volume = safe_get_attribute(test_rx, 'DoseVolume')
    primary_dose_volume = safe_get_attribute(primary_rx, 'DoseVolume')
    test_prescription_type = safe_get_attribute(test_rx, 'PrescriptionType')
    primary_prescription_type = safe_get_attribute(primary_rx, 'PrescriptionType')

    return all(
        [test_dose == primary_dose,
         test_structure_name == primary_structure_name,
         test_dose_volume == primary_dose_volume,
         test_prescription_type == primary_prescription_type
         ]
    )


# Helper function to safely get attributes
def safe_get_attribute(obj, attr=None, default=None):
    if not attr:
        try:
            obj
            return obj
        except Exception as e:
            if str(e).startswith('Object has no member'):
                return default
    else:
        try:
            return getattr(obj, attr)
        except AttributeError:
            return default


def get_beamset_prescriptions(rso):
    """
    Get all prescriptions (noting the primary) and return them as a list of dictionaries.

    Args:
        rso (NamedTuple): RayStation script objects

    Returns:
        dict: A dictionary containing the prescription information with structure names as keys.
              Each value is a tuple with the dose value and a boolean indicating if it's the primary prescription.
    """
    beamset_prescriptions = {}

    # Get primary prescription if exists
    primary_rx = safe_get_attribute(rso.beamset.Prescription, 'PrimaryPrescriptionDoseReference')

    # Function to add prescription to the dictionary
    def add_prescription(rx, is_primary):
        if rx:
            rx_on_structure = safe_get_attribute(rx, 'OnStructure')
            roi_name = safe_get_attribute(rx_on_structure, 'Name', 'None')
            dose_value = safe_get_attribute(rx, 'DoseValue')
            if dose_value:
                dose_value = dose_value / 100 # cGy to Gy
            beamset_prescriptions[roi_name] = (dose_value, is_primary)

    # Add primary prescription
    add_prescription(primary_rx, True)

    # Add other prescriptions
    for other_rx in rso.beamset.Prescription.PrescriptionDoseReferences:
        if not check_rx_versus_primary(other_rx, primary_rx):
            add_prescription(other_rx, False)

    return beamset_prescriptions


def primary_rx_dose(rx_dict):
    for roi, dose_tuple in rx_dict.items():
        if dose_tuple[1]:
            return roi, dose_tuple[0]
    highest_dose = 0
    for roi, dose_tuple in rx_dict.items():
        if dose_tuple[0] > highest_dose:
            highest_dose = dose_tuple[0]
            highest_roi = roi
    return highest_roi, highest_dose


def normalize_rx_dose(point_dose, rx_dose):
    if rx_dose:
        return 100 * point_dose / rx_dose
    else:
        return None


def get_target_rois(beamset_prescriptions, target_types, rso):
    """
    Collect all ROIs from beamset prescriptions and other targets.
    """
    primary_roi, _ = primary_rx_dose(beamset_prescriptions)
    roi_list = [primary_roi] if primary_roi and primary_roi != 'None' else []

    for roi in beamset_prescriptions.keys():
        if roi != 'None' and roi != primary_roi:
            roi_list.append(roi)

    target_dict = sort_rois(rso, target_types)
    for target_list in target_dict.values():
        for t in target_list:
            if t not in roi_list:
                roi_list.append(t)

    return roi_list


def check_max_dose_point(rso):
    """
    Examine the maximum dose point. Ideally the maximum dose point should be
    within a prescription target. If not, then search all targets in the roi list.
    If the maximum dose point is outside of all targets, then return an alert.

    Args:
        rso (NamedTuple): RayStation script objects
    Returns:
        tuple: A tuple containing the status and message

    Test Patient:
        PASS: Script_Testing, ZZUWQA^ScTest_23Nov2023, Medi_VMA_R1A0
        ALERT: Script_Testing, ZZUWQA^ScTest_23Nov2023, ___
        Note jupyter notebook: RAB_ScriptTesting_MaxDose_Within_Targets
    """
    max_dose_point = rso.beamset.FractionDose.GetCoordinateOfMaxDose()
    if max_dose_point is None:
        return ALERT, "Max Dose Point: is undefined"

    slice_thickness = get_slice_thickness(rso)
    maximum_dose = get_beamset_dose_at_point(rso, max_dose_point)
    beamset_prescriptions = get_beamset_prescriptions(rso)
    roi_list = get_target_rois(beamset_prescriptions, ['Ptv', 'Ctv', 'Gtv'], rso)

    for roi in roi_list:
        if check_bounding_box_for_roi(rso, max_dose_point, roi):
            contour = rso.case.PatientModel.StructureSets[rso.exam.Name] \
                .RoiGeometries[roi].PrimaryShape.Contours
            if find_contours_containing_point(contour, max_dose_point, slice_thickness):
                return format_max_dose_message(maximum_dose, roi, max_dose_point, beamset_prescriptions)

    # If not found in any ROI
    return format_max_dose_message_outside_targets(maximum_dose, max_dose_point, beamset_prescriptions)


def format_max_dose_message(maximum_dose, roi, max_dose_point, beamset_prescriptions):
    """
    Format the message when the max dose point is inside an ROI.
    """
    primary_roi, primary_dose = primary_rx_dose(beamset_prescriptions)
    dose_percent_rx = normalize_rx_dose(maximum_dose, primary_dose)
    message_str = f"Max dose {dose_percent_rx:.1f}%Rx in {roi} at " \
                  f"({max_dose_point['x']:.2f}, {max_dose_point['y']:.2f}, " \
                  f"{max_dose_point['z']:.2f})" if dose_percent_rx else \
                  f"Max dose {maximum_dose:.1f} Gy in {roi} at " \
                  f"({max_dose_point['x']:.2f}, {max_dose_point['y']:.2f}, " \
                  f"{max_dose_point['z']:.2f})"
    return PASS, message_str


def format_max_dose_message_outside_targets(maximum_dose, max_dose_point, beamset_prescriptions):
    """
    Format the message when the max dose point is outside all ROIs.
    """
    primary_roi, primary_dose = primary_rx_dose(beamset_prescriptions)
    dose_percent_rx = normalize_rx_dose(maximum_dose, primary_dose)
    message_str = f"Max dose {dose_percent_rx:.1f}%Rx outside all targets at " \
                  f"({max_dose_point['x']:.2f}, {max_dose_point['y']:.2f}, " \
                  f"{max_dose_point['z']:.2f})" if dose_percent_rx else \
                  f"Max dose {maximum_dose:.1f} Gy outside all targets at " \
                  f"({max_dose_point['x']:.2f}, {max_dose_point['y']:.2f}, " \
                  f"{max_dose_point['z']:.2f})"
    return ALERT, message_str

