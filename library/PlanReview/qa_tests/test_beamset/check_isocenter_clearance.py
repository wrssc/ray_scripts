import numpy as np
import math
from functools import reduce
from PlanReview.utils.contour_utilities import (create_roi, unique_roi_name, copy_roi,
                                                roi_has_contours, get_voxel_coordinates)
import logging

tomotherapy_clearance = 130  # cm. Conservative estimate of tomo couch throw
truebeam_clearance = 200  # cm. Measured from scale drawings of the TrueBeam at Couch=0
# TODO: Need a special alert when the patient will collide with the TrueBeam laser guard covers
truebeam_iso_to_laserguard = 100  # cm. Distance from isocenter to the laser guard on the TrueBeam
length_of_interest = 50  # cm. The length of support structures or external contours that are reviewed


def print_or_log(message, log=False):
    if log:
        logging.debug(message)
    else:
        print(message)


# ================= RayStation Utilities =================
def get_couch_angle(rso, beam_name):
    """
    Get the couch angle for a beam in the beamset.

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
        beam_name (str): Name of the beam to get the couch angle for.

    Returns:
        float: The couch angle in degrees.
    """
    return rso.beamset.Beams[beam_name].CouchRotationAngle


def gantry_angular_traversal(rso):
    """
    Return a list of gantry angles traversed for each beam in a dynamic arc.

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]

    Returns:
        dict: Dictionary of beam names and list of gantry angles to check
    """
    gantry_angles = {}
    if rso.beamset.DeliveryTechnique == "DynamicArc":
        for beam in rso.beamset.Beams:
            gantry_angles[beam.Name] = generate_arc_gantry_sweep(
                beam.GantryAngle,
                beam.ArcStopGantryAngle,
                clockwise=True if beam.ArcRotationDirection == "Clockwise" else False)
    elif rso.beamset.DeliveryTechnique == "SMLC":
        static_beam_angles = [beam.GantryAngle for beam in rso.beamset.Beams if beam.GantryAngle is not None]
        gantry_angles[rso.beamset.Beams[0].Name] = gantry_angular_traversal_static_beams(static_beam_angles)
    return gantry_angles


def delete_rois(rso, rois_to_delete):
    ss = rso.case.PatientModel.StructureSets[rso.exam.Name]
    for d in rois_to_delete:
        try:
            ss.RoiGeometries[d].OfRoi.DeleteRoi()
        except Exception as e:
            logging.warning(f"An error occurred while deleting {d}: {e}")
            continue


def get_first_beam(rso):
    try:
        return rso.beamset.Beams[0]
    except Exception as e:
        logging.warning(f"An error occurred while getting the first beam: {e}")
        return None


def get_clearance_roi_name_and_diameter(rso, tolerance=0):
    """
    Get the appropriate ROI name for the type of treatment machine along with the diameter of the bore or head.
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
        tolerance: The tolerance to be used for the bore or head diameter

    Returns:
        tuple: The ROI name and the diameter of the bore or head.
    """
    from PlanReview.review_definitions import (HDA_MAX_DIAMETER, TRUEBEAM_MAX_DIAMETER)
    beam_technique = get_treatment_technique(rso)
    if "Tomo" in beam_technique:
        return "TomoTherapy bore covers", HDA_MAX_DIAMETER - 2 * tolerance
    else:
        return "TrueBeam Head", TRUEBEAM_MAX_DIAMETER - 2 * tolerance


def get_treatment_technique(rso):
    """
    Get the treatment technique for the first beam in the beamset.

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]

    Returns:
        str: The treatment technique for the first beam in the beamset.
    """
    beam = get_first_beam(rso)
    if beam is None:
        return None
    return beam.DeliveryTechnique


# ================= Geometry Utilities =================
def convert_angle_from_cartesian_to_varian_iec(x, y):
    """
    Convert an angle from the cylindrical coordinate system to the Varian IEC coordinate system.

    This conversion is necessary for aligning angles within the context of Varian equipment, which uses a different
    reference frame than the standard cylindrical coordinate system.

    Args:
        x (float): The x-coordinate in the rotated and shifted (isocentric) cartesian coordinate system.
        y (float): The y-coordinate in the rotated and shifted (isocentric) cartesian coordinate system.

    Returns:
        float: The corresponding angle in degrees in the Varian IEC coordinate system.
    """
    cylindrical_angle = np.degrees(np.arctan2(y, x))
    varian_iec_angle = (90 + cylindrical_angle) % 360
    return varian_iec_angle


# ================= Gantry Angle Calculations =================
def generate_arc_gantry_sweep(start_angle, stop_angle, clockwise=True):
    """
    Generate a sequence of gantry angles for an arc.

    Args:
        start_angle (float): The start gantry angle in cylindrical coordinates.
        stop_angle (float): The stop gantry angle in cylindrical coordinates.
        clockwise (bool): Direction of rotation, clockwise if True, else counterclockwise.

    Returns:
        np.array: An array of gantry angles for the sweep.
    """
    if clockwise:
        if start_angle > stop_angle:
            stop_angle += 360  # Adjust for wrap-around in clockwise direction
        angles = np.arange(start_angle, stop_angle + 1) % 360
    else:
        if start_angle < stop_angle:
            start_angle += 360  # Adjust for wrap-around in counterclockwise direction
        angles = np.arange(start_angle, stop_angle - 1, -1) % 360

    return angles, clockwise


def gantry_angular_traversal_static_beams(beam_gantry_angles):
    """
    Generate a sequence of gantry angles for a static field plan in an arc motion.

    Args:
        beam_gantry_angles (list): List of gantry angles in the treatment plan.

    Returns:
        np.array: An array of gantry angles for the sweep.
    """
    # Find the beam closest to 180 degrees
    closest_to_180 = min(beam_gantry_angles, key=lambda x: min(abs(x - 180), abs(x - 540)))

    # Determine the direction of sweep
    clockwise = closest_to_180 > 180

    # Find the beam on the other side closest to 180 degrees
    if clockwise:
        other_side_angles = [angle for angle in beam_gantry_angles if angle < 180]
        last_angle = max(other_side_angles) if other_side_angles else min(beam_gantry_angles)
    else:
        other_side_angles = [angle for angle in beam_gantry_angles if angle > 180]
        last_angle = min(other_side_angles) if other_side_angles else max(beam_gantry_angles)

    # Generate the sweep
    return generate_arc_gantry_sweep(round(closest_to_180), round(last_angle), clockwise)


def filter_points_outside_diameter_and_length(points, diameter):
    """
    Filter points that are outside the given diameter in the XY plane and outside the Z range specified by the length of interest.

    Args:
        points (np.array): Numpy array of points with shape (N, 3), where each row is [x, y, z].
        diameter (float): The diameter in the XY plane.

    Returns:
        np.array: A numpy array containing only the points outside the diameter and length_of_interest.
    """
    # Calculate the radial distance in the XY plane for each point
    radial_distances = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)

    # Filter points where radial distance exceeds half the diameter
    outside_diameter_mask = radial_distances > (diameter / 2)

    # Filter points where Z exceeds the length_of_interest
    outside_length_mask = points[:, 2] > truebeam_iso_to_laserguard
    outside_length_mask |= points[:, 2] < -truebeam_clearance

    # Combine both masks: either outside diameter or outside length
    outside_mask = outside_diameter_mask | outside_length_mask

    # Return points that are outside both conditions and inside both conditions
    return points[outside_mask], points[~outside_mask]


def filter_in_bore_clearing_points_tomo(points, diameter):
    """
    Filter points that are outside the given diameter in the XY plane and
    inside the Z range specified by the length of interest.

    Args:
        points (np.array): Numpy array of points with shape (N, 3), where each row is [x, y, z].

            Points have been shifted to the isocenter frame of reference.
        diameter (float): The diameter in the XY plane.

    Returns:
        tuple: (np.array, np.array): numpy arrays containing only the points outside the diameter
        and inside the length_of_interest, and points not matching these conditions.
    """
    # Calculate the radial distance in the XY plane for each point
    radial_distances = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)

    # Filter points where radial distance exceeds half the diameter
    outside_diameter_mask = radial_distances > (diameter / 2)

    # Create a mask for points outside the maximum couch throw
    # points from -65 to the top of the image should be included
    outside_length_mask = points[:, 2] > - tomotherapy_clearance / 2

    # Combine both masks: outside diameter and inside the interesting length
    outside_mask = outside_diameter_mask & outside_length_mask
    return points[outside_mask], points[~outside_mask]

# ================= Cylindrical Angle Calculations =================


def shift_to_isocenter_and_couch_rotate_points(rso, contours, beam_name, representation='Contours',
                                               couch_angle=None):
    """
    Shift the contours to the isocenter and rotate them by the couch angle.
    Args:
        rso: the RayStation object containing beamset information.
        contours: a list of contours, each a list of dictionaries with 'x', 'y', 'z' coordinates. or
                    a numpy array of points.
        beam_name: the name of the beam in the RayStation object.
        representation: 'Contours' (the RayStation contour object)
                or 'Points' (a numpy array of points).
        couch_angle: the couch angle in degrees.

    Returns:
          np.array: A numpy array of points in the rotated and shifted (isocentric) cartesian coordinate system.
    """
    if representation == 'Contours':
        all_points = np.concatenate([np.array([(p.x, p.y, p.z) for p in contour]) for contour in contours])
    elif representation == 'Points':
        all_points = contours
    else:
        all_points = None
    # Print the first 5 points
    # print_or_log(f"\t First 5 points: {all_points[:5]}")
    # Convert the isocenter point to a numpy array
    isocenter_point = np.array([(rso.beamset.Beams[beam_name].Isocenter.Position.x,
                                 rso.beamset.Beams[beam_name].Isocenter.Position.y,
                                 rso.beamset.Beams[beam_name].Isocenter.Position.z)])
    # Print the iso center point
    # print_or_log(f"\t Isocenter point: {isocenter_point}")
    # Subtract the isocenter point from all points
    isocentered_contours = all_points - isocenter_point
    # Get the couch angle
    if not couch_angle:
        couch_angle = get_couch_angle(rso, beam_name)
    # Print the beam name and couch angle
    # print_or_log(f"\t Beam name: {beam_name}, Couch angle: {couch_angle}")
    couch_angle_rad = math.radians(couch_angle)
    # print_or_log(f"\t Couch angle in radians: {couch_angle_rad}")
    #
    # Now we will make a rotation matrix to account for the couch angle
    # Y-axis increases downwards in DICOM, so we need to negate the sin term
    rotation_matrix_dicom = np.array([
        [math.cos(couch_angle_rad), 0, -math.sin(couch_angle_rad)],
        [0, 1, 0],
        [math.sin(couch_angle_rad), 0, math.cos(couch_angle_rad)]
    ])
    # Nicely print the rotation matrix
    # print_or_log(f"\t Rotation matrix: {rotation_matrix_dicom}")
    # Rotate all points by the rotation matrix
    rotated_points = np.dot(isocentered_contours, rotation_matrix_dicom.T)
    return rotated_points


def truncate_collision_volumes_in_z(rotated_points):
    return rotated_points[np.abs(rotated_points[:, 2]) < length_of_interest / 2]


def get_sorted_cylindrical_angles_dicom(rotated_points):
    """
    Vectorized calculation, rounding, and sorting of gantry angles for all points in all contours in the
    DICOM reference frame.
    Args:
        rotated_points (np.array): A numpy array of points in the rotated and shifted (isocentric) cartesian
                                   coordinate system. [x, y, z] where x is left-right, y is anterior-posterior,
                                   and z is superior-inferior.
    Returns:
        list: Sorted list of rounded gantry angles.
    """
    # rotated_points = shift_to_isocenter_and_couch_rotate_points(rso, contours, beam_name, representation)
    # Limit the rotated points in z to be centered around the length of interest
    # rotated_points = rotated_points[np.abs(rotated_points[:, 2]) < length_of_interest / 2]
    # Convert to cylindrical coordinates
    x = rotated_points[:, 0]
    y = rotated_points[:, 1]
    # Remap these to Varian gantry angles:
    varian_angles = convert_angle_from_cartesian_to_varian_iec(x, y)
    # Round and sort angles
    rounded_angles = np.round(varian_angles)
    return sorted(set(rounded_angles))


def contour_angle_ranges(rso, contours, beam_name, representation='Contours', shift=True):
    """
    Calculates the cylindrical angle ranges for all contours within the frame of reference of the rotated
    clearance zone. Once computed, the ranges are made contiguous.
    A range is considered contiguous if it is within 2 degrees of another range.
    Accounts for the mechanical limit at 270 degrees (Varian 180).

    Args:
        rso: RayStation object containing beamset information.
        contours (list): A list of contours, each a list of dictionaries with 'x', 'y', 'z' coordinates.
        beam_name (str): The name of the beam in the RayStation object.
        representation (str): The representation of the contours, either 'Contours' (the RayStation contour object)
                              or 'Points' (a numpy array of points).

    Returns:
        list: A list of tuples representing the merged min and max angles over all contours.
    """
    if shift:
        # Shift the contours to the isocenter and rotate them by the couch angle
        rotated_points = shift_to_isocenter_and_couch_rotate_points(rso, contours, beam_name, representation)
        # Limit the rotated points in z to be centered around the length of interest
        truncated_clearance_volumes = truncate_collision_volumes_in_z(rotated_points)
    else:
        truncated_clearance_volumes = contours
    # print out the first 5 points
    # print_or_log(f"\t First 5 points: {rotated_points[:5]}")
    # Get sorted cylindrical angles in the DICOM reference frame rotated by couch plane
    # sorted_angles = get_sorted_cylindrical_angles_dicom(rso, contours, beam_name, representation)
    sorted_angles = get_sorted_cylindrical_angles_dicom(truncated_clearance_volumes)
    # print_or_log(f"\t Sorted angles: {sorted_angles}")

    if not sorted_angles:
        return []

    # Initialize the first range
    merged_ranges = [(sorted_angles[0], sorted_angles[0])]

    for angle in sorted_angles[1:]:
        last_range_start, last_range_end = merged_ranges[-1]

        # Check if current angle is contiguous with the last range
        if last_range_end >= 179 and angle <= 181:  # Special handling for mechanical limit at 180 degrees
            continue  # Skip adding angles around the mechanical limit
        elif angle - last_range_end <= 2:
            # Extend the current range
            merged_ranges[-1] = (last_range_start, angle)
        else:
            # Start a new range
            merged_ranges.append((angle, angle))

    return merged_ranges


def group_overlapping_angles(overlapping_angles):
    """
    Groups overlapping angles into ranges.

    Args:
        overlapping_angles (list): A sorted list of overlapping angles.

    Returns:
        list: A list of tuples representing the start and end of each range of overlapping angles.
    """
    if not overlapping_angles:
        return []

    grouped_ranges = []
    start = overlapping_angles[0]
    end = start

    for angle in overlapping_angles[1:]:
        if angle - end <= 1:
            end = angle
        else:
            grouped_ranges.append((start, end))
            start = angle
            end = start

    grouped_ranges.append((start, end))  # Add the last range
    return grouped_ranges


# ================= Collision Detection =================
def check_overlap(np_gantry_angles, contour_ranges):
    """
    Identifies and returns the overlapping angles between the gantry sweep and contour angle ranges.

    Args:
        np_gantry_angles (np.array): Array of gantry angles from the sweep.
        contour_ranges (list): List of tuples representing min and max angles of contours.

    Returns:
        list: A list of angles where the gantry sweep overlaps with contour ranges.
    """
    overlapping_angles = []

    for start, end in contour_ranges:
        overlap = [angle for angle in np_gantry_angles if start <= angle <= end]
        overlapping_angles.extend(overlap)
    grouped_ranges = group_overlapping_angles(overlapping_angles)

    return grouped_ranges

#
# def check_bounding_box_overlap(rso, roi1_name, roi2_name):
#     """
#     Check for overlap between the bounding boxes of two ROIs.
#     Uses Separating Axis Theorem (SAT) to check for overlap on all axes since
#     the bounding boxes are always aligned with the axes.
#
#     Args:
#         rso: RayStation object containing beamset information.
#         roi1_name (str): Name of the first ROI.
#         roi2_name (str): Name of the second ROI.
#
#     Returns:
#         bool: True if the bounding boxes overlap, otherwise False.
#     """
#     if not roi_has_contours(rso, roi1_name) or not roi_has_contours(rso, roi2_name):
#         return False
#     roi1_bb = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi1_name].GetBoundingBox()
#     roi2_bb = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi2_name].GetBoundingBox()
#
#     for axis in ['x', 'y', 'z']:
#         if roi1_bb[1][axis] < roi2_bb[0][axis] or roi1_bb[0][axis] > roi2_bb[1][axis]:
#             return False  # No overlap on this axis
#
#     return True  # Overlap on all axes


# def check_for_overlap(rso, rois_checked, diam_name_dict, rois_to_delete):
#     """
#     Check for overlap between the expanded structure and the external and support structures.
#     Args:
#         rso: RayStation object containing beamset information.
#         rois_checked: list of ROIs to check for overlap
#         diam_name_dict: a dictionary of beam names and the clearance ROIs associated with them
#         rois_to_delete: a list of ROIs to delete after the check is complete
#
#     Returns:
#         violation_rois: a dictionary of beam names and the ROIs that are in violation
#
#     """
#     from PlanReview.utils import subtract_roi_sources
#     # Create the dictionary of beam names and the ROIs that are in violation
#     violation_rois = {}
#     couch_angle_checked = []
#     # Using the rotated isocenter clearance zone for beam 1, check for overlap with external and supports
#     for beam_name, (diam_name, couch_angle) in diam_name_dict.items():
#         violation_rois[beam_name] = []
#         # Skip if we've already checked this couch angle
#         if diam_name in couch_angle_checked:
#             for b, (d, c) in diam_name_dict.items():
#                 if d == diam_name:
#                     violation_rois[beam_name] = violation_rois[b]
#                     break
#         else:
#             # Check for overlap with external and supports and store them as rois to later delete
#             for r in rois_checked:
#                 print_or_log(f"Checking for overlap between {diam_name} and {r}")
#                 # Check for overlap with the external and supports only if the bounding boxes overlap
#                 # Simplifying contours in this step did not result in a speedup
#                 if check_bounding_box_overlap(rso, r, diam_name):
#                     r_overlap_name = r + '_overlap' + f'_{str(int(couch_angle)).zfill(3)}'
#                     _ = subtract_roi_sources(rso, r_overlap_name, roi_A=r, roi_B=diam_name)
#                     # Delete the expression for the subtracted ROI
#                     rso.case.PatientModel.RegionsOfInterest[r_overlap_name].DeleteExpression()
#                     if roi_has_contours(rso, r_overlap_name):
#                         print_or_log(f"If the gantry passes through through {r_overlap_name}, it will collide")
#                         violation_rois[beam_name].append(r_overlap_name)
#                     rois_to_delete.append(r_overlap_name)
#             couch_angle_checked.append(diam_name)
#     return violation_rois


def determine_contour_type(rso, roi_name):
    roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name]
    if hasattr(roi_geometry.PrimaryShape, 'Contours'):
        return 'Contours'
    elif hasattr(roi_geometry.PrimaryShape, 'VoxelValues'):
        return 'Points'
    else:
        return None


def detect_collisions(rso, roi_dict, clearance_diameter):
    couch_angles_checked = []
    bad_gantry = {}
    for beam in rso.beamset.Beams:
        beam_name = beam.Name
        couch_angle = get_couch_angle(rso, beam_name)
        if couch_angle in couch_angles_checked:
            continue
        else:
            for roi, contour_points in roi_dict.items():
                # Retrieve the geometry of the ROI
                rotated_points = shift_to_isocenter_and_couch_rotate_points(rso, contour_points, beam_name,
                                                                            representation='Points')
                # Determine if the rotated points are outside the clearance volume diameter
                # Limit x and y to the diameter of the bore and z to the length of interest
                violation_points, _ = filter_points_outside_diameter_and_length(rotated_points, clearance_diameter)
                # If the numpy array is empty then there are no points outside the clearance volume
                if violation_points.size > 0:
                    # Evaluate the gantry angles which will be affected by the collision
                    contour_ranges = contour_angle_ranges(rso, violation_points,
                                                          beam_name, representation='Points', shift=False)
                    if not contour_ranges:
                        continue
                    gantry_ranges = gantry_angular_traversal(rso)
                    for bn, (gantry_range, clockwise) in gantry_ranges.items():
                        if bn != beam_name:
                            continue
                        overlapping_angles = check_overlap(gantry_range, contour_ranges)
                        if overlapping_angles:
                            if roi not in bad_gantry:
                                bad_gantry[roi] = {}
                            bad_gantry[roi][bn] = overlapping_angles, clockwise
            couch_angles_checked.append(couch_angle)
    return bad_gantry


def detect_collisions_tomo(rso, roi_dict, external_roi, support_rois, clearance_diameter, clearance_roi,
                           tolerance):
    from PlanReview.review_definitions import PASS, FAIL
    beam_name = rso.beamset.Beams[0].Name
    bore_clearance_issues = []
    for roi, contour_points in roi_dict.items():
        shifted_points = shift_to_isocenter_and_couch_rotate_points(rso, contour_points,
                                                                    beam_name,
                                                                    representation='Points',
                                                                    couch_angle=0)
        bore_clearance_points,_ = filter_in_bore_clearing_points_tomo(shifted_points,
                                                                    clearance_diameter)
        if bore_clearance_points.size > 0:
            bore_clearance_issues.append(roi)

    # Determine pass, fail, or alert status based on cleaned violations
    if not bore_clearance_issues:
        return PASS, f'No collisions detected. {external_roi} and {", ".join(support_rois)} are ≥ {tolerance} cm from ' \
                     f'{clearance_roi}.'
    else:
        violation_str = ', '.join(bore_clearance_issues)
        return FAIL, f'{violation_str} is ≤ {tolerance} cm from the {clearance_roi}.'


# ================= Output Formatting =================
def abbreviate_name(name):
    """ Abbreviate structure names longer than 4 characters """
    length = 5
    if len(name) <= length:
        return name
    else:
        return name[:length]


def format_beam_collisions(bad_gantry):
    output = ["Collision! To avoid reduce gantry angles by 42\u00B1: "]
    beam_collisions = {}

    # Process each contour and beam
    for contour, beams in bad_gantry.items():
        # Abbreviate the contour name
        base_contour_name = abbreviate_name(contour.rsplit('_overlap_', 1)[0] if '_overlap_' in contour else contour)

        for beam, (angles, clockwise) in beams.items():
            direction = "CW" if clockwise else "CCW"
            # Convert angle ranges to integers and format them
            angle_info = [f"{int(start)}-{int(end)}" if int(start) != int(end) else str(int(start)) for start, end in
                          angles]

            # Create a collision detail entry
            collision_detail = f"{base_contour_name} ({'/'.join(angle_info)})"

            # Group by beam and direction, include direction after beam name
            key = f"{beam}:{direction}"

            # Append or create a new entry for this beam and direction
            beam_collisions.setdefault(key, []).append(collision_detail)

    # Format the output
    for beam, collision_details in beam_collisions.items():
        output.append(f"{beam} strikes {'; '.join(collision_details)}")

    return ' '.join(output)


# ================= Main Function =================


def find_externals_and_supports(rso):
    """
    Retrieve the external and support ROIs from the RayStation object.

    Args:
        rso: NamedTuple of ScriptObjects in RayStation.

    Returns:
        tuple: external ROI name and list of support ROIs.
    """
    from PlanReview.utils import get_roi_names_from_type
    external = get_roi_names_from_type(rso, roi_type='External')[0]
    supports = get_roi_names_from_type(rso, roi_type='Support')
    return external, supports


def extract_voxel_representation(rso, rois):
    """
    Convert ROIs to voxel representation if necessary and return their voxel coordinates.

    Args:
        rso: NamedTuple of ScriptObjects in RayStation.
        rois: List of ROIs to convert to voxel representation.

    Returns:
        tuple: Dictionary of ROI names and their voxel coordinates, and list of temporary ROIs to delete.
    """
    rois_checked = {}
    rois_to_delete = []

    for roi in rois:
        roi_type = determine_contour_type(rso, roi)
        if roi_type != 'Points':
            copied_roi = copy_roi(rso, roi, suffix="_voxels", representation="Voxels")
            roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[copied_roi]
            contour_points = get_voxel_coordinates(roi_geometry)
            rois_checked[copied_roi] = contour_points
            rois_to_delete.append(copied_roi)
        else:
            roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi]
            contour_points = get_voxel_coordinates(roi_geometry)
            rois_checked[roi] = contour_points

    return rois_checked, rois_to_delete


def check_isocenter_clearance(rso):
    from PlanReview.review_definitions import (ALERT, SUPPORT_TOLERANCE,
                                               PASS, FAIL)
    """
    Check clearance of patient setup by evaluating if any external or support ROIs overlap the clearance structure
    around the isocenter, based on couch angle and gantry traversal.

    Pseudocode:
    1. Retrieve clearance ROI name and diameter for checking collision.
    2. Get external and support ROIs and ensure they exist.
    3. Convert ROI contours to voxel representation if necessary and store them.
    4. For each beam, shift and rotate the points to the isocenter and check for clearance violations.
    5. If violations are found, calculate gantry angles affected by collisions.
    6. Return pass/fail/alert based on the presence of violations.
    7. Clean up temporary ROIs used in the process.
    
    
    ! Alert level for any clearance we can't verify
    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    :return: (pass_result, message_str): PASS/FAIL/ALERT, (str) message result of test

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_21Nov2022
        PASS: Case 1 Oral_THI_R0A0, NecL_VMA_LowerIso
        FAIL: Case 1 Oral_T3D_R0A0, Case 2 NecL_T3D_R0A0 (fails on External, S-frame)
        FAIL: Case 1 NecB_NonCoplanar fails on every beam for the External, S-frame, TomoCouch and Box.
              Gantry angles verified.
        FAIL: Case 2 Contains a deliberately distorted ExternalClean to flag an angle around 305 degrees.
    Test Patient:
        Collision_Check, ZZUWQA_Collisions
        
    """
    clearance_diameter_roi_name, diameter = get_clearance_roi_name_and_diameter(rso, tolerance=SUPPORT_TOLERANCE)

    # Find external and support ROIs
    external, supports = find_externals_and_supports(rso)
    if not external and not supports:
        return ALERT, f'No Supports or External found, no clearance test performed.'
    # Get voxel representations of external and support ROIs
    rois_checked, rois_to_delete = extract_voxel_representation(rso, [external] + supports)
    if 'Tomo' in clearance_diameter_roi_name:
        pass_result, message_str = detect_collisions_tomo(
            rso, rois_checked, external, supports, diameter, clearance_diameter_roi_name,
            tolerance=SUPPORT_TOLERANCE)
    else:
        # Check the beams for VMAT or Static Field
        bad_gantry_angles = detect_collisions(rso, rois_checked, diameter)
        if type(bad_gantry_angles) == str:
            return ALERT, bad_gantry_angles
        elif bad_gantry_angles:
            message_str = format_beam_collisions(bad_gantry_angles)
            pass_result = FAIL
        else:
            pass_result = PASS
            message_str = f'{[external] + supports} are ≥' \
                          + f' {SUPPORT_TOLERANCE} cm from {clearance_diameter_roi_name}'
        # Delete script contours
    delete_rois(rso, rois_to_delete)
    return pass_result, message_str
