from typing import Dict, Tuple, List, Optional, Any
import logging
import numpy as np
import math
import pandas as pd  # requires pandas
from PlanReview.utils.contour_utilities import (copy_roi, get_voxel_coordinates)

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


def get_isocenter_position(rso, beam_name):
    """
    Get the isocenter position for a beam in the beamset.
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
        beam_name (str): Name of the beam to get the isocenter position for.

    Returns:
        tuple: The isocenter position as a tuple (x, y, z).
    """
    isocenter = rso.beamset.Beams[beam_name].Isocenter.Position
    return isocenter.x, isocenter.y, isocenter.z


def find_gantry_angular_traversal(rso, testing=False):
    """
    Return a list of gantry angles traversed for each beam in a dynamic arc.

    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
        testing (bool): If True, use test values which span possible angles.

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
            Note in testing mode a single beam is used with the full range of angles, keyed by "TestBeam".
    """
    gantry_angles = {}
    if rso.beamset.DeliveryTechnique == "DynamicArc":
        if testing:
            gantry_angles['TestBeam'] = generate_arc_gantry_sweep(180.1, 179.9, clockwise=True)
            return gantry_angles
        else:
            for beam in rso.beamset.Beams:
                gantry_angles[beam.Name] = generate_arc_gantry_sweep(
                    beam.GantryAngle,
                    beam.ArcStopGantryAngle,
                    clockwise=True if beam.ArcRotationDirection == "Clockwise" else False)
    elif rso.beamset.DeliveryTechnique == "SMLC":
        if testing:
            # Generate all gantry angles from 180.1 to 360 then from 0 to 179.9 degrees
            static_beam_angles = np.concatenate([np.arange(180.1, 360, 1), np.arange(0, 180, 1)]).tolist()
            gantry_angles['TestBeam'] = gantry_angular_traversal_static_beams(static_beam_angles)
            return gantry_angles
        else:
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
    - The objective is to change the orientation of the points so that:
       [-X, +X] -> [B wall, A Wall]
       [-Y, +Y] -> [Down, Up]
       [-Z, +Z] -> [Table, Gantry]
    - numpy.ndarray: 3x3 transformation matrix
    """
    if orientation == 'HFS':
        # Head First Supine: No rotation
        return np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, 1]
        ])

    elif orientation == 'HFP':
        # Head First Prone: Rotate 180 degrees around the X-axis
        return np.array([
            [-1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ])

    elif orientation == 'FFS':
        # Feet First Supine: Rotate 180 degrees around the Z-axis
        return np.array([
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFP':
        # Feet First Prone: Rotate 180 degrees around both X and Z axes
        return np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, -1]
        ])

    elif orientation == 'HFDR':
        # Head First Decubitus Right: Rotate -90 degrees around the Z-axis
        return np.array([
            [0, 1, 0],
            [1, 0, 0],
            [0, 0, 1]
        ])

    elif orientation == 'HFDL':
        # Head First Decubitus Left: Rotate +90 degrees around the Z-axis
        return np.array([
            [0, -1, 0],
            [-1, 0, 0],
            [0, 0, 1]
        ])

    elif orientation == 'FFDR':
        # Feet First Decubitus Right: Rotate -90 degrees around Z-axis, then 180 degrees around X-axis
        return np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFDL':
        # Feet First Decubitus Left: Rotate +90 degrees around Z-axis, then 180 degrees around X-axis
        return np.array([
            [0, 1, 0],
            [-1, 0, 0],
            [0, 0, -1]
        ])

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


def old_group_overlapping_angles(overlapping_angles):
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
        if abs(angle - end) <= 2:
            end = angle
        else:
            grouped_ranges.append((start, end))
            start = angle
            end = start

    grouped_ranges.append((start, end))  # Add the last range
    return grouped_ranges


# ================= Collision Detection =================

def determine_contour_type(rso, roi_name):
    roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name]
    if hasattr(roi_geometry.PrimaryShape, 'Contours'):
        return 'Contours'
    elif hasattr(roi_geometry.PrimaryShape, 'VoxelValues'):
        return 'Points'
    else:
        return None


def downsample_points(points, voxel_size=None):
    """
    Downsample points to a voxel grid defined by the given voxel size.
    Args:
        points: (N×3) array of points in the rotated and shifted (isocentric) cartesian coordinate system.
        voxel_size: (list) of voxel sizes in the x, y, z dimensions.

    Returns: downsampled_points: (M×3) array of downsampled points.
    """
    if not voxel_size:
        voxel_size = [0.5, 0.5, 0.5]  # Default voxel size if not provided
    vx, vy, vz = voxel_size
    # Calculate the voxel indices for each point
    ix = np.floor(points[:, 0] / vx).astype(int)
    iy = np.floor(points[:, 1] / vy).astype(int)
    iz = np.floor(points[:, 2] / vz).astype(int)
    # Unique keys for each voxel using large prime numbers to reduce collisions
    keys = ix * 73856093 + iy * 19349663 + iz * 83492791
    unique_keys, unique_indices = np.unique(keys, return_index=True)
    # Return the downsampled points based on unique keys
    return points[unique_indices]


def fast_head_collision_masks_dual(
        points: np.ndarray,
        diameter: float,
        head_length: float,
        offset_fail: float,
        offset_alert: float,
        gantry_angles: np.ndarray
) -> Tuple[Dict[float, np.ndarray], Dict[float, np.ndarray]]:
    """
    Vectorized collision masks using dot & cross math, for all angles at once,
    including pre-filtering and reconstruction of full-length masks.
    Args:
        points: (N×3) array of isocenter‐shifted, couch‐rotated voxels
        diameter: barrel diameter D (cm)
        head_length: total length L of the gantry head (cm)
        offset_fail: radial distance from the isocenter to the front face of the gantry head (cm) for fails
        offset_alert: radial distance from the isocenter to the front face of the gantry head (cm) for alerts
        gantry_angles: 1D array of IEC angles (degrees) to be converted to normal cylindrical coordinates.

    Returns: fail_masks, alert_masks where each is a dict mapping angle -> boolean mask of shape (N,)

    """
    # Radius and half‐length
    R = diameter / 2.0
    half_L = head_length / 2.0
    # Center of the cylinder for fail and alert levels
    center_fail = offset_fail + half_L
    center_alert = offset_alert + half_L
    # Total points
    N = points.shape[0]

    # prefilter radial distances based on the offsets
    r2 = points[:, 0] ** 2 + points[:, 1] ** 2
    keep_alert = r2 > offset_alert ** 2
    keep_fail = r2 > offset_fail ** 2

    # Declare filtered points based on the pre-filtering
    pts_alert = points[keep_alert]
    idx_alert = np.nonzero(keep_alert)[0]
    pts_fail = points[keep_fail]
    idx_fail = np.nonzero(keep_fail)[0]

    # axes for all angles
    # Convert iec angles to cylindrical coordinates
    # e.g. [90 -> 0, 0 -> 90, 270 -> 180, 180 -> 270]
    phi = np.deg2rad((360 - (gantry_angles - 90)) % 360)
    # the unit vector along the central axis
    d = np.stack((np.cos(phi), np.sin(phi), np.zeros_like(phi)), axis=1)

    # centers of the cylinder for fail and alert levels
    C_alert = center_alert * d
    C_fail = center_fail * d

    # relative vectors, i.e. shift points to the cylinder-centered coordinates
    rel_alert = pts_alert[np.newaxis, :, :] - C_alert[:, None, :]
    rel_fail = pts_fail[np.newaxis, :, :] - C_fail[:, None, :]

    # Parallel components of the vectors to the cylinder axis
    t_alert = np.einsum('mni,mi->mn', rel_alert, d)
    # Perpendicular distances squared from the cylinder axis
    r2_alert = np.einsum('mni,mni->mn', rel_alert, rel_alert)
    perp2_alert = r2_alert - t_alert ** 2

    t_fail = np.einsum('mni,mi->mn', rel_fail, d)
    r2_fail = np.einsum('mni,mni->mn', rel_fail, rel_fail)
    perp2_fail = r2_fail - t_fail ** 2

    # Perform the inside cylinder test:
    #   Perpendicular distance squared must be less than or equal to R^2
    #   Parallel component must be within the half-length of the cylinder
    in_alert = (perp2_alert <= R ** 2) & (t_alert >= -half_L) & (t_alert <= half_L)
    in_fail = (perp2_fail <= R ** 2) & (t_fail >= -half_L) & (t_fail <= half_L)

    # scatter back
    fail_masks = {}
    alert_masks = {}
    for i, theta in enumerate(gantry_angles):
        mf = np.zeros(N, dtype=bool)
        ma = np.zeros(N, dtype=bool)
        mf[idx_fail] = in_fail[i]
        ma[idx_alert] = in_alert[i]
        fail_masks[theta] = mf
        alert_masks[theta] = ma

    return fail_masks, alert_masks


def detect_collisions(rso, roi_dict, testing=False):
    """
    Detect collisions at two levels using an analytic cylinder model:
      - Fail level: cylinder center at 41 cm from isocenter
      - Alert level: cylinder center at 38 cm from isocenter
    Args:
        rso: NamedTuple of ScriptObjects in RayStation [case, exam, plan, beamset, db]
        roi_dict: Dictionary of ROIs to check for collisions.
        testing: Boolean indicating whether to run in test mode.

    In test mode:
        * Gantry varies between 180.1 and 179.9 degrees
        * The couch angle varies between 271 and 90 degrees
        * Isocenter position varies relative to the supplied region of interest center
    """
    import time
    from PlanReview.review_definitions import ALERT, PASS, FAIL, SUPPORT_TOLERANCE, TRUEBEAM_MAX_DIAMETER

    # --- head model parameters (cm) ---
    diameter = 76.3  # use the TrueBeam cover diameter (≈76.3 cm)
    length = 84.2  # length of the gantry head (cm)
    h_fail = TRUEBEAM_MAX_DIAMETER / 2 - SUPPORT_TOLERANCE #  36.0 fail offset distance (cm)
    h_alert = TRUEBEAM_MAX_DIAMETER / 2 - SUPPORT_TOLERANCE - 2 #  34.0 alert offset distance (cm)

    bad_gantry_fail = {}
    bad_gantry_alert = {}
    couch_angles_checked = []
    isocenters_checked = []

    # Precompute the gantry‐sweep angles per beam
    # TODO: create a test function option for find_gantry_angular_traversal that returns 180.1 to 179.9
    gantry_sweeps = find_gantry_angular_traversal(rso, testing=testing)
    # TODO: test function will sweep couch angles from 270 to 90 degrees
    # TODO: Need further downsampling for TBIs
    roi_downsampled = {}
    for roi_name, roi_pts in roi_dict.items():
        logging.info(f"Checking ROI: {roi_name} with {len(roi_pts)} points")
        print(f"Checking ROI: {roi_name} with {len(roi_pts)} points")
        if len(roi_pts) > 1e6:
            roi_downsampled[roi_name] = downsample_points(roi_pts, voxel_size=[2, 2, 2])
        elif len(roi_pts) > 1e5:
            roi_downsampled[roi_name] = downsample_points(roi_pts, voxel_size=[0.5, 0.5, 0.5])
        else:
            roi_downsampled[roi_name] = roi_pts

    # TODO: check travel of beams, no sense in repeating the same gantry angles
    for beam in rso.beamset.Beams:
        beam_name = beam.Name
        couch_angle = get_couch_angle(rso, beam_name)
        isocenter = get_isocenter_position(rso, beam_name)
        if couch_angle in couch_angles_checked and isocenter in isocenters_checked:
            continue
        couch_angles_checked.append(couch_angle)
        isocenters_checked.append(isocenter)
        # time_0 = time.perf_counter()
        # Full VMAT/static sweep for this beam
        angles, clockwise = gantry_sweeps[beam_name]
        # time_1 = time.perf_counter()
        # print(f"Time to get gantry angles for beam {beam_name}: {(time_1 - time_0) * 1000:7.2f} ms")
        logging.info(f"Checking beam: {beam_name} with couch angle: {couch_angle} degrees, "
                        f"isocenter: {isocenter} cm, angles: {len(angles)}")

        for roi_name, roi_pts in roi_downsampled.items():
            # print(f"Checking ROI: {roi_name} for beam: {beam_name} which has {len(roi_pts)} points")
            # time_0 = time.perf_counter()
            # 1) shift & rotate the ROI into DICOM‐isocenter space
            pts_dicom = shift_to_isocenter_and_couch_rotate_points(
                rso, roi_pts, beam_name, representation='Points'
            )
            # time_1 = time.perf_counter()
            # print(f"\t * Shift and rotate points: {(time_1 - time_0) * 1000:7.2f} ms")

            # --- NEW CYLINDER‐MODEL METHOD ---------------------
            # Fail‐level: more conservative (head assumed 41 cm away)
            # masks_fail = head_collision_masks(pts_dicom, D, H, h_fail, angles)
            # Fix the y-direction for HFS
            # pts_dicom[:, 1] *= -1
            # Check if the points are too sparse to warrant downsampling
            # if len(pts_dicom) > 1e5:
            #     pts_dicom = downsample_points(pts_dicom, voxel_size=[0.5, 0.5, 0.5])
            #    print(f"\t * Downsampled points to {len(pts_dicom)} points")
            masks_fail, masks_alert = fast_head_collision_masks_dual(
                pts_dicom, diameter, length, h_fail, h_alert, angles
            )
            # 1) pull out only the angles with any collision
            hit_angles = [ang for ang, hit in masks_fail.items() if any(hit)]
            # print(f"\t * Found {len(hit_angles)} fail angles with collisions: {hit_angles}")

            # 2) round to ints, dedupe, sort
            hit_ints = sorted({int(round(ang)) for ang in hit_angles})
            # print(f"\t * Found {len(hit_ints)} unique angles with collisions: {hit_ints}")

            # 3) group into contiguous ranges
            # time_3 = time.perf_counter()
            fail_ranges = old_group_overlapping_angles(hit_ints)
            # time_4 = time.perf_counter()
            if fail_ranges:
                bad_gantry_fail.setdefault(roi_name, {})[beam_name] = (fail_ranges, clockwise)

            # Alert‐level: less conservative (head assumed 38 cm away)
            hits_alert = [ang for ang, hit in masks_alert.items() if any(hit)]
            # 2) round to ints, dedupe, sort
            hit_ints_alert = sorted({int(round(ang)) for ang in hits_alert})
            # 3) group into contiguous ranges
            alert_ranges = old_group_overlapping_angles(hit_ints_alert)
            if alert_ranges:
                bad_gantry_alert.setdefault(roi_name, {})[beam_name] = (alert_ranges, clockwise)
    logging.debug("Collision detection complete: fail_rois=%d alert_rois=%d",
                  len(bad_gantry_fail), len(bad_gantry_alert))
    for roi_name, fail_dict in bad_gantry_fail.items():
        print(f"ROI {roi_name} has {len(fail_dict)} beams with collision issues:")
        for beam_name, (ranges, clockwise) in fail_dict.items():
            print(f"\t{beam_name}: {clockwise}, {ranges}")
    for roi_name, alert_dict in bad_gantry_alert.items():
        print(f"ROI {roi_name} has {len(alert_dict)} beams with alert issues:")
        for beam_name, (ranges, clockwise) in alert_dict.items():
            print(f"\t{beam_name}: {clockwise}, {ranges}")

    return bad_gantry_fail, bad_gantry_alert


def detect_collisions_tomo(rso, roi_dict, external_roi, support_rois, clearance_diameter, clearance_roi,
                           tolerance):
    from PlanReview.review_definitions import PASS, FAIL
    beam_name = rso.beamset.Beams[0].Name
    bore_clearance_issues = []
    # Downsample points
    roi_dict_downsampled = {}
    for roi_name, roi_pts in roi_dict.items():
        if len(roi_pts) > 1e5:
            roi_dict_downsampled[roi_name] = downsample_points(roi_pts, voxel_size=[0.5, 0.5, 0.5])
        else:
            roi_dict_downsampled[roi_name] = roi_pts
    for roi, contour_points in roi_dict_downsampled.items():
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

def ranges_to_side_cutoffs(
    ranges: List[Tuple[int, int]],
    left_edge: float = 179.9,
    right_edge: float = 180.1,
) -> Tuple[float, float]:
    """Reduce blocked ranges to (left_min, right_max) using Varian IEC rules.

    Args:
        ranges: List of contiguous blocked ranges (start,end) in [0,360), start<=end.
        left_edge: Default when no left-side block. Use 179.9 if you prefer strict 180E handling.
        right_edge: Default when no right-side block. Use 180.1 if you prefer strict 180E handling.

    Returns:
        (left_min, right_max). If no block on a side, returns the corresponding edge default.
    """
    left_candidates = []
    right_candidates = []
    for s, e in ranges:
        s = int(s) % 360
        e = int(e) % 360
        if e < s:
            parts = [(s, 359), (0, e)]
        else:
            parts = [(s, e)]
        for a, b in parts:
            # Left side [0,180]
            ls, le = max(a, 0), min(b, 180)
            if ls <= le:
                left_candidates.append(ls)     # pick smallest on left
            # Right side [180,360]
            rs, re = max(a, 180), min(b, 360)
            if rs <= re:
                right_candidates.append(re)    # pick largest on right
    left_min  = min(left_candidates) if left_candidates else left_edge
    right_max = max(right_candidates) if right_candidates else right_edge
    return float(left_min), float(right_max)

def build_beam_clearance_table(
    rso,
    bad_gantry_fail: Dict[str, Dict[str, Tuple[List[Tuple[int,int]], bool]]],
    bad_gantry_alert: Dict[str, Dict[str, Tuple[List[Tuple[int,int]], bool]]],
    *,
    left_edge: float = 179.9,
    right_edge: float = 180.1,
    beam_meta: Optional[Dict[str, Dict[str, Any]]] = None,
    csv_path: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> pd.DataFrame:
    """Create per-ROI, per-beam cutoffs for FAIL/ALERT/PASS with optional metadata and CSV.

    Args:
        rso: RayStation ScriptObjects NamedTuple. Used to enumerate all beams.
        bad_gantry_fail: {roi: {beam: ([(start,end), ...], clockwise_bool)}}
        bad_gantry_alert: same shape for ALERT.
        left_edge, right_edge: defaults when a side has no block.
        beam_meta: optional {beam_name: {"couch_to_iso":..., "lat_offset":..., ...}}
        csv_path: optional CSV output.
        logger: optional logger.

    Returns:
        DataFrame with columns:
          roi, beam, level, direction, ranges, left_min, right_max,
          couch_to_iso?, lat_offset? (if provided), and any extra meta fields.
    """
    rows = []
    all_beams = [b.Name for b in rso.beamset.Beams]

    def add(level_dict: Dict[str, Dict[str, Tuple[List[Tuple[int,int]], bool]]], level: str):
        for roi, beams in level_dict.items():
            for beam, (ranges, clockwise) in beams.items():
                lmin, rmax = ranges_to_side_cutoffs(ranges, left_edge, right_edge)
                meta = beam_meta.get(beam, {}) if beam_meta else {}
                rows.append({
                    "roi": roi,
                    "beam": beam,
                    "level": level,
                    "direction": "CW" if clockwise else "CCW",
                    "ranges": ";".join([f"{int(s)}-{int(e)}" if s!=e else f"{int(s)}" for s,e in ranges]),
                    "left_min": lmin,
                    "right_max": rmax,
                    **meta,
                })

    add(bad_gantry_fail, "FAIL")
    add(bad_gantry_alert, "ALERT")

    # PASS rows for beams not present above
    present = {(r["roi"], r["beam"]) for r in rows}
    rois = sorted(set(list(bad_gantry_fail.keys()) + list(bad_gantry_alert.keys())))
    for roi in rois:
        for beam in all_beams:
            if (roi, beam) in present:
                continue
            meta = beam_meta.get(beam, {}) if beam_meta else {}
            rows.append({
                "roi": roi,
                "beam": beam,
                "level": "PASS",
                "direction": "NA",
                "ranges": "",
                "left_min": left_edge,    # no block -> defaults
                "right_max": right_edge,
                **meta,
            })

    df = pd.DataFrame(rows)
    # Optional severity ordering: FAIL > ALERT > PASS
    cat = pd.CategoricalDtype(categories=["FAIL","ALERT","PASS"], ordered=True)
    if "level" in df:
        df["level"] = df["level"].astype(cat)
    df.sort_values(["roi","beam","level"], inplace=True)

    if logger:
        for roi, sub in df.groupby("roi"):
            worst = "FAIL" if (sub["level"] == "FAIL").any() else ("ALERT" if (sub["level"] == "ALERT").any() else "PASS")
            logger.info("ROI %s summary: worst=%s, beams=%d", roi, worst, sub["beam"].nunique())

    if csv_path:
        df.to_csv(csv_path, index=False)
    return df


def split_points_by_collision_for_angle(
    points_iso_dicom: np.ndarray,
    diameter: float,
    head_length: float,
    offset: float,
    angle_deg: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (colliding_points, clearing_points) for a single IEC angle.

    Args:
        points_iso_dicom: (N,3) points already shifted to iso and rotated by couch.
        diameter: head diameter cm.
        head_length: head length cm.
        offset: center offset from iso cm (use fail or alert offset).
        angle_deg: Varian IEC gantry angle in degrees.

    Returns:
        colliding_points, clearing_points
    """
    R = diameter / 2.0
    half_L = head_length / 2.0
    phi = np.deg2rad((360 - (angle_deg - 90)) % 360)
    d = np.array([np.cos(phi), np.sin(phi), 0.0])                # axis unit vector
    C = (offset + half_L) * d                                    # cylinder center
    rel = points_iso_dicom - C
    t = rel @ d
    perp2 = np.einsum("ij,ij->i", rel, rel) - t**2
    inside = (perp2 <= R**2) & (t >= -half_L) & (t <= half_L)
    return points_iso_dicom[inside], points_iso_dicom[~inside]


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
    supports = get_roi_names_from_type(rso, roi_type='Support', test_has_contours=True)
    supports += get_roi_names_from_type(rso, roi_type='Fixation', test_has_contours=True)
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
            if copied_roi is None:
                logging.warning(f"Failed to copy ROI {roi} to voxel representation.")
                return None
            try:
                roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[copied_roi]
            except Exception as e:
                logging.warning(f"An error occurred while accessing the copied ROI {copied_roi}: {e}")
                return None
            contour_points = get_voxel_coordinates(roi_geometry)
            rois_checked[copied_roi] = contour_points
            rois_to_delete.append(copied_roi)
        else:
            roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi]
            contour_points = get_voxel_coordinates(roi_geometry)
            rois_checked[roi] = contour_points

    return rois_checked, rois_to_delete


def check_isocenter_clearance(rso, **kwargs):
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
    rois_checked = kwargs.get('rois_checked', None)
    rois_to_delete = kwargs.get('rois_to_delete', None)
    # TODO:
    #     Add support_tolerance instead of the hardcoded entry in detect_collisions
    #     Filter the points before the rotation
    # Get the name of the machine-limiting ROI and the tolerance diameter
    clearance_diameter_roi_name, diameter = get_clearance_roi_name_and_diameter(rso, tolerance=SUPPORT_TOLERANCE)
    # Set an ALERT level for any clearance that is within 3 cm of the SUPPORT_TOLERANCE
    # Additional buffer for the clearance diameter
    alert_distance = 3

    # Find external and support ROIs
    external, supports = find_externals_and_supports(rso)
    if not external and not supports:
        return ALERT, f'No Supports or External found, no clearance test performed.'
    if rois_checked is None:
        # Get voxel representations of external and support ROIs
        rois_checked, rois_to_delete = extract_voxel_representation(rso, [external] + supports)
    if not rois_checked:
        return ALERT, f'No valid ROIs found for clearance check.'
    if 'Tomo' in clearance_diameter_roi_name:
        pass_result, message_str = detect_collisions_tomo(
            rso, rois_checked, external, supports, diameter, clearance_diameter_roi_name,
            tolerance=SUPPORT_TOLERANCE)
    else:
        # Check the beams for VMAT or Static Field
        bad_gantry_fail, bad_gantry_alert = detect_collisions(rso, rois_checked)
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
