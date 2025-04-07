import numpy as np
import math
from PlanReview.utils.contour_utilities import (copy_roi, get_voxel_coordinates)
import logging

tomotherapy_clearance = 130  # cm. Conservative estimate of tomo couch throw
truebeam_clearance = 200  # cm. Measured from scale drawings of the TrueBeam at Couch=0
truebeam_iso_to_laserguard = 100  # cm. Distance from isocenter to the laser guard on the TrueBeam
length_of_interest = 50  # cm. The length of support structures or external contours that are reviewed


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


def find_gantry_angular_traversal(rso):
    """
    Return a list of gantry angles traversed for each beam in a dynamic arc.

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]

    Returns:
        dict:
            A dictionary of the form:
            {
                "<beam_name>": (np.array of gantry angles, bool indicating clockwise)
            }

            Where:
            - The key is the beam name (str).
            - The value is a tuple consisting of:
                - A numpy array representing the sequence of gantry angles swept by the beam.
                - A boolean indicating the direction of rotation (True for clockwise, False for counterclockwise).
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
# Retrieve orientation transformation matrix
def get_orientation_transform(orientation):
    """
    Returns the transformation matrix based on the patient orientation.

    Parameters:
    - orientation (str): Patient orientation (e.g., 'HFS', 'HFP', 'FFS', 'FFP', 'HFDR', 'HFDL', 'FFDR', 'FFDL')

    Returns:
    - numpy.ndarray: 3x3 transformation matrix
    """
    if orientation == 'HFS':
        # Head First Supine: No rotation
        return np.identity(3)

    elif orientation == 'HFP':
        # Head First Prone: Rotate 180 degrees around the X-axis
        return np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFS':
        # Feet First Supine: Rotate 180 degrees around the Z-axis
        return np.array([
            [-1, 0, 0],
            [0, 1, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFP':
        # Feet First Prone: Rotate 180 degrees around both X and Z axes
        return np.array([
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, 1]
        ])

    elif orientation == 'HFDR':
        # Head First Decubitus Right: Rotate -90 degrees around the Z-axis
        return np.array([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])

    elif orientation == 'HFDL':
        # Head First Decubitus Left: Rotate +90 degrees around the Z-axis
        return np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])

    elif orientation == 'FFDR':
        # Feet First Decubitus Right: Rotate -90 degrees around Z-axis, then 180 degrees around X-axis
        Rz_neg_90 = np.array([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])
        Rx_180 = np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, -1]
        ])
        return Rx_180 @ Rz_neg_90  # Matrix multiplication

    elif orientation == 'FFDL':
        # Feet First Decubitus Left: Rotate +90 degrees around Z-axis, then 180 degrees around X-axis
        Rz_pos_90 = np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])
        Rx_180 = np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, -1]
        ])
        return Rx_180 @ Rz_pos_90  # Matrix multiplication

    else:
        raise ValueError(f"Unsupported orientation: {orientation}")


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
    # Convert the isocenter point to a numpy array
    isocenter_point = np.array([(rso.beamset.Beams[beam_name].Isocenter.Position.x,
                                 rso.beamset.Beams[beam_name].Isocenter.Position.y,
                                 rso.beamset.Beams[beam_name].Isocenter.Position.z)])
    # Subtract the isocenter point from all points
    isocentered_contours = all_points - isocenter_point
    # At this point, we need to transform all to the DICOM reference frame
    # +X is toward the A wall, +Y is toward the roof, +Z is toward the gantry
    # Get the patient orientation
    orientation = rso.exam.PatientPosition
    # Get the orientation transformation matrix
    orientation_matrix = get_orientation_transform(orientation)
    # Rotate all points by the orientation matrix
    # In this coordinate system:
    room_frame_of_reference_points = np.dot(isocentered_contours, orientation_matrix.T)
    # Get the couch angle
    if not couch_angle:
        couch_angle = get_couch_angle(rso, beam_name)
    couch_angle_rad = math.radians(couch_angle)
    #
    # Now we will make a rotation matrix to account for the couch angle
    # Y-axis increases downwards in DICOM, so we need to negate the sin term
    rotation_matrix_dicom = np.array([
        [math.cos(couch_angle_rad), 0, -math.sin(couch_angle_rad)],
        [0, 1, 0],
        [math.sin(couch_angle_rad), 0, math.cos(couch_angle_rad)]
    ])
    # Rotate all points by the rotation matrix
    rotated_points = np.dot(room_frame_of_reference_points, rotation_matrix_dicom.T)
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


def find_contour_angle_ranges(rso, contours, beam_name, representation='Contours', shift=True):
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
    # Get sorted cylindrical angles in the DICOM reference frame rotated by couch plane
    # sorted_angles = get_sorted_cylindrical_angles_dicom(rso, contours, beam_name, representation)
    sorted_angles = get_sorted_cylindrical_angles_dicom(truncated_clearance_volumes)

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


def determine_contour_type(rso, roi_name):
    roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name]
    if hasattr(roi_geometry.PrimaryShape, 'Contours'):
        return 'Contours'
    elif hasattr(roi_geometry.PrimaryShape, 'VoxelValues'):
        return 'Points'
    else:
        return None


def find_overlapping_angles_for_beam(gantry_ranges, beam_name, contour_ranges):
    """
    Given a dictionary of gantry ranges and a target beam name, find any overlapping angles
    between the beam's gantry range and the provided contour ranges.

    Args:
        gantry_ranges (dict): A dictionary of the form {beam_name: (np.array of gantry angles, bool clockwise)}
        beam_name (str): The name of the beam for which to find overlapping angles.
        contour_ranges (list): List of angle ranges (tuples) representing contour intersection angles.

    Returns:
        tuple or (None, None):
            If overlap is found:
                (list of overlapping angle ranges, bool clockwise_direction)
            Otherwise:
                (None, None)
    """
    if beam_name not in gantry_ranges:
        return None, None

    gantry_range, clockwise = gantry_ranges[beam_name]
    overlapping_angles = check_overlap(gantry_range, contour_ranges)

    if overlapping_angles:
        return overlapping_angles, clockwise
    return None, None


def detect_collisions(rso, roi_dict, clearance_diameter_fail, clearance_diameter_alert):
    """
    Detect collisions at two levels:
    - Fail level: using clearance_diameter_fail
    - Alert level: using clearance_diameter_alert

    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    :param roi_dict: dict, {roi_name: np.array of points in the roi}
    :param clearance_diameter_fail: float, stricter diameter threshold for failure
    :param clearance_diameter_alert: float, looser diameter threshold for alerts
    :return: (bad_gantry_fail, bad_gantry_alert): Two dicts with similar structure.
        bad_gantry_fail: {roi: {beam_name: ([angle_ranges], clockwise_bool)}}
        bad_gantry_alert: {roi: {beam_name: ([angle_ranges], clockwise_bool)}}
    """
    couch_angles_checked = []
    bad_gantry_fail = {}
    bad_gantry_alert = {}

    for beam in rso.beamset.Beams:
        beam_name = beam.Name
        couch_angle = get_couch_angle(rso, beam_name)
        if couch_angle in couch_angles_checked:
            continue

        for roi, roi_point_array in roi_dict.items():
            rotated_points = shift_to_isocenter_and_couch_rotate_points(
                rso, roi_point_array, beam_name, representation='Points'
            )

            # First check fail-level clearance
            violation_points_fail, _ = filter_points_outside_diameter_and_length(
                rotated_points, clearance_diameter_fail
            )

            # Determine gantry ranges
            gantry_angle_ranges = find_gantry_angular_traversal(rso)

            if violation_points_fail.size > 0:
                # Determine gantry angles that fail
                contour_angle_ranges = find_contour_angle_ranges(rso, violation_points_fail, beam_name,
                                                                 representation='Points', shift=False)
                if contour_angle_ranges:
                    overlapping_angles, clockwise = find_overlapping_angles_for_beam(
                        gantry_angle_ranges, beam_name, contour_angle_ranges
                    )
                    if overlapping_angles:
                        if roi not in bad_gantry_fail:
                            bad_gantry_fail[roi] = {}
                        bad_gantry_fail[roi][beam_name] = overlapping_angles, clockwise
            else:
                # Check alert-level clearance
                violation_points_alert, _ = filter_points_outside_diameter_and_length(
                    rotated_points, clearance_diameter_alert
                )
                if violation_points_alert.size > 0:
                    # Determine gantry angles that cause alert
                    contour_angle_ranges = find_contour_angle_ranges(rso, violation_points_alert, beam_name,
                                                                     representation='Points', shift=False)
                    if contour_angle_ranges:
                        overlapping_angles, clockwise = find_overlapping_angles_for_beam(
                            gantry_angle_ranges, beam_name, contour_angle_ranges
                        )
                        if overlapping_angles:
                            if roi not in bad_gantry_alert:
                                bad_gantry_alert[roi] = {}
                            bad_gantry_alert[roi][beam_name] = overlapping_angles, clockwise

        couch_angles_checked.append(couch_angle)

    return bad_gantry_fail, bad_gantry_alert


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
        bore_clearance_points, _ = filter_in_bore_clearing_points_tomo(shifted_points,
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
    supports += get_roi_names_from_type(rso, roi_type='Fixation')
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
        Collision_Check, ZZUWQA_Collisions,
        FAIL: Case 2 Collision_Check_2, ZZUWQA_ScTest_01Oct2024 Brai_PRD_R0A0 
            (actual clinical failure - Fails on Qfix for Beam 1 (RPO)
        PASS: Case 2 Collision_Check_2, ZZUWQA_ScTest_01Oct2024 Brai_PRD_R0A1
            (passes without the RPO beam - clinical solution).
    """
    # Get the name of the machine-limiting ROI and the tolerance diameter
    clearance_diameter_roi_name, diameter = get_clearance_roi_name_and_diameter(rso, tolerance=SUPPORT_TOLERANCE)
    # Set an ALERT level for any clearance that is within 3 cm of the SUPPORT_TOLERANCE
    # Additional buffer for the clearance diameter
    alert_distance = 3
    clearance_diameter_alert = diameter - 2 * alert_distance

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
        bad_gantry_fail, bad_gantry_alert = detect_collisions(rso, rois_checked, diameter, clearance_diameter_alert)
        if type(bad_gantry_fail) == str:
            # An internal error occurred. Print the error message and return an ALERT level.
            return ALERT, bad_gantry_fail
        elif bad_gantry_fail:
            # There are collisions that fail the clearance test
            message_str = format_beam_collisions(bad_gantry_fail)
            pass_result = FAIL
        elif bad_gantry_alert:
            # No fail level but there are collisions that are close to failure
            message_str = format_beam_collisions(bad_gantry_alert)
            pass_result = ALERT
        else:
            pass_result = PASS
            message_str = f'{[external] + supports} are ≥' \
                          + f' {int(SUPPORT_TOLERANCE + alert_distance)} ' \
                          + f'cm from {clearance_diameter_roi_name}'
    # Delete script contours
    delete_rois(rso, rois_to_delete)
    return pass_result, message_str
