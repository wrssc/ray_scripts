"""
Check each beam for clearance issues with support structures or external contours in tomotherapy and TrueBeam plans.
"""
__author__ = "Adam Bayliss"
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2025-Oct-02'
__version__ = '1.0.0'
__status__ = 'Clinical'
__deprecated__ = False
__raystation__ = '2025'
__maintainer__ = 'One maintainer'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__credits__ = ['']
from typing import Dict, Tuple, List, Optional, Any
import logging
import numpy as np
import math
import pandas as pd
from PlanReview.review_definitions import HDA_MAX_DIAMETER, HDA_ALERT_DIAMETER, HDA_COUCH_THROW, TRUEBEAM_COVER_DIAMETER
from PlanReview.utils.contour_utilities import (get_voxel_coordinates_direct_optimized)

tomotherapy_clearance = 130  # cm. Conservative estimate of tomo couch throw
truebeam_clearance = 200  # cm. Measured from scale drawings of the TrueBeam at Couch=0
truebeam_iso_to_laserguard = 100  # cm. Distance from isocenter to the laser guard on the TrueBeam
length_of_interest = 50  # cm. The length of support structures or external contours that are reviewed


# ================= RayStation Utilities =================
def get_couch_angle(beamset, beam_name):
    """
    Get the couch angle for a beam in the beamset.

    Args:
        beamset (object): The beamset object
        beam_name (str): Name of the beam to get the couch angle for.

    Returns:
        float: The couch angle in degrees.
    """
    return beamset.Beams[beam_name].CouchRotationAngle


def get_isocenter_position(beamset, beam_name):
    """
    Get the isocenter position for a beam in the beamset.
    Args:
        beamset (object): The beamset object
        beam_name (str): Name of the beam to get the isocenter position for.

    Returns:
        tuple: The isocenter position as a tuple (x, y, z).
    """
    isocenter = beamset.Beams[beam_name].Isocenter.Position
    return isocenter.x, isocenter.y, isocenter.z


def find_gantry_angular_traversal(beamset, testing=False):
    """
    Return a list of gantry angles traversed for each beam in a dynamic arc.

    Args:
              beamset (object): The beamset object
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
    if beamset.DeliveryTechnique == "DynamicArc":
        gantry_angles = find_dynamic_gantry_angular_traversal(beamset, testing)
    elif beamset.DeliveryTechnique == "SMLC":
        gantry_angles = find_static_gantry_angular_traversal(beamset, testing)
    elif 'Tomo' in beamset.DeliveryTechnique:
        gantry_angles = {beamset.Beams[0].Name: (np.array([0.0]), False)}
    return gantry_angles


def find_dynamic_gantry_angular_traversal(beamset, testing=False):
    gantry_angles = {}
    if beamset.DeliveryTechnique == "DynamicArc":
        if testing:
            gantry_angles['TestBeam'] = generate_arc_gantry_sweep(180.1, 179.9, clockwise=True)
            return gantry_angles
        else:
            for beam in beamset.Beams:
                gantry_angles[beam.Name] = generate_arc_gantry_sweep(
                    beam.GantryAngle,
                    beam.ArcStopGantryAngle,
                    clockwise=True if beam.ArcRotationDirection == "Clockwise" else False)
    return gantry_angles


def find_static_gantry_angular_traversal(beamset, testing=False):
    """ Return a list of gantry angles traversed for each beam in a static field plan.
    Args:
           beamset (object): The beamset object
        testing (bool): If True, use test values which span possible angles.
    Returns:
        dict:
            A dictionary of the form:
            {
                "<beam_name>": (np.array of all beam where the couch is the same gantry angles,
                bool indicating clockwise)
            }
            Where:
            - The key is the beam name (str).
            - The value is a tuple consisting of:
                - A numpy array representing the sequence of gantry angles swept by the beam.
                - A boolean indicating the direction of rotation (True for clockwise, False for counterclockwise).
            Note in testing mode a single beam is used with the full range of angles, keyed by "TestBeam".
    """
    gantry_angles = {}
    couch_angles_dict = {}
    for beam in beamset.Beams:
        couch_angle = get_couch_angle(beamset, beam.Name)
        if couch_angle not in couch_angles_dict:
            couch_angles_dict[couch_angle] = []
        if beam.Name is not None:
            couch_angles_dict[couch_angle].append(beam)
    for couch_angle, beams in couch_angles_dict.items():
        if testing:
            # Generate all gantry angles from 180.1 to 360 then from 0 to 179.9 degrees
            static_beam_angles = np.concatenate([np.arange(180.1, 360, 1), np.arange(0, 180, 1)]).tolist()
            gantry_angles['TestBeam'] = gantry_angular_traversal_static_beams(static_beam_angles)
            return gantry_angles
        else:
            static_beam_angles = [b.GantryAngle for b in beams if b.GantryAngle is not None]
            for b in beams:
                gantry_angles[b.Name] = gantry_angular_traversal_static_beams(static_beam_angles)
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


def get_clearance_roi_name_and_diameter(rso, collision_tolerance=None, alert_tolerance=None, head_length=None,
                                        head_diameter=None):
    """
    Get the appropriate ROI name for the type of treatment machine along with the diameter of the bore or head.
    Args:
        rso: NamedTuple of ScriptObjects in Raystation [case, exam, plan, beamset, db]
        collision_tolerance: The tolerance to be used for the bore or head diameter
        alert_tolerance: The tolerance to be used for the bore or head diameter (value is the closest to the TrueBeam
                         collisional alert tolerance, i.e. the audible warning at the TrueBeam)
        head_length: The length of the gantry head (cm). If None, a default value will be used based on the machine type.

    Returns:
        dict: A dictionary with keys:
            'roi_name': The name of the ROI to be used for clearance checking.
            'diameter': The diameter of the bore or head (cm).
            'alert_tolerance': The tolerance to be used for clearance checking.
            'collision_tolerance': The tolerance to be used for clearance checking.
    """
    from PlanReview.review_definitions import (HDA_MAX_DIAMETER, TRUEBEAM_MAX_DIAMETER, TRUEBEAM_HEAD_LENGTH,
    TRUEBEAM_COVER_DIAMETER, SUPPORT_TOLERANCE_ALERT, SUPPORT_TOLERANCE_COLLISION)
    if collision_tolerance is None:
        collision_tolerance = SUPPORT_TOLERANCE_COLLISION
    if alert_tolerance is None:
        alert_tolerance = SUPPORT_TOLERANCE_ALERT
    if head_length is None:
        head_length = TRUEBEAM_HEAD_LENGTH
    if head_diameter is None:
        head_diameter = TRUEBEAM_COVER_DIAMETER

    beam_technique = get_treatment_technique(rso)
    if "Tomo" in beam_technique:
        return {
            'roi_name': 'TomoTherapy bore covers',
            'diameter': HDA_MAX_DIAMETER,
            'alert_tolerance': alert_tolerance,
            'collision_tolerance': collision_tolerance,
            'head_length': None,
            'COVER_DIAMETER': None
        }
    else:
        return {
            'roi_name': 'TrueBeam Head',
            'diameter': TRUEBEAM_MAX_DIAMETER,
            'alert_tolerance': alert_tolerance,
            'collision_tolerance': collision_tolerance,
            'head_length': head_length,
            'COVER_DIAMETER': head_diameter
        }


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


def filter_in_bore_clearing_points_tomo(points, fail_diameter, alert_diameter, couch_travel=None):
    """
    Filter points that are outside the given diameter in the XY plane and
    inside the Z range specified by the length of interest.

    Args:
        points (np.array): Numpy array of points with shape (N, 3), where each row is [x, y, z].

            Points have been shifted to the isocenter frame of reference.

    Returns:
        tuple: (np.array, np.array): numpy arrays containing only the points outside the diameter
        and inside the length_of_interest, and points not matching these conditions.
    """
    # TODO: replace with actual couch travel in the plan + a margin
    if couch_travel is None:
        couch_travel = (-HDA_COUCH_THROW/2 , HDA_COUCH_THROW/2)  # Default couch travel range if not provided
    # Calculate the radial distance in the XY plane for each point
    radial_distances = np.sqrt(points[:, 0] ** 2 + points[:, 1] ** 2)

    # Filter points where radial distance exceeds half the diameter
    outside_diameter_fail_mask = radial_distances > (fail_diameter / 2)
    outside_diameter_alert_mask = radial_distances > (alert_diameter / 2)

    # Create a mask for points outside the maximum couch throw
    # These points are not of interest for collision detection
    outside_length_mask = (points[:, 2] < couch_travel[0]) | (points[:, 2] > couch_travel[1])
    # Create Fail, Alert masks
    fail_mask = outside_diameter_fail_mask & ~outside_length_mask
    alert_mask = outside_diameter_alert_mask & ~outside_length_mask & ~fail_mask
    return fail_mask, alert_mask


# ================= Cylindrical Angle Calculations =================
# Retrieve orientation transformation matrix
def get_orientation_transform(orientation):
    """
    Returns the transformation matrix based on the patient orientation.
    Note the coordinate system is currently in the DICOM patient frame of reference and will be
    transformed to the room frame of reference.
    - The objective is to change the orientation of the points so that:
       [-X, +X] -> [B wall, A Wall]
       [-Y, +Y] -> [Down, Up]
       [-Z, +Z] -> [Table, Gantry]

    Parameters:
    - orientation (str): Patient orientation (e.g., 'HFS', 'HFP', 'FFS', 'FFP', 'HFDR', 'HFDL', 'FFDR', 'FFDL')

    Returns:
    - numpy.ndarray: 3x3 transformation matrix
    """
    if orientation == 'HFS':
        # Head First Supine: Rotate 180 degrees around the Y-axis
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
        # Feet First Supine: Rotate 180 degrees around both X, Y, and Z axes
        return np.array([
            [-1, 0, 0],
            [0, -1, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFP':
        # Feet First Prone: Rotate 180 degrees around the Y and Z axes
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
        # Feet First Decubitus Right: Rotate -90 degrees around the Z-axis, then 180 degrees around X-axis
        return np.array([
            [0, -1, 0],
            [1, 0, 0],
            [0, 0, -1]
        ])

    elif orientation == 'FFDL':
        # Feet First Decubitus Left: Rotate +90 degrees around the Z-axis, then 180 degrees around X-axis
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
    if couch_angle is None:
        couch_angle = get_couch_angle(rso.beamset, beam_name)
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


def build_beam_groups(beamset):
    """
    Groups beams by (couch_angle, isocenter) combination to avoid redundant angle checks.

    Args:
        beamset: The beamset object containing the beams.

    Returns:
        dict: A dictionary where each key is a tuple (couch_angle, isocenter) and the value is:
            'beams': a list of dictionaries with keys:
                'name': beam name,
                'angles': list of gantry angles for the beam,
                'clockwise': boolean indicating direction of rotation,
            'all_angles': a set of all gantry angles for the group,
            'angle_to_beams': a mapping of each angle to the list of beams that use it.
    """
    beam_groups = {}
    for beam in beamset.Beams:
        beam_name = beam.Name
        couch_angle = get_couch_angle(beamset, beam_name)
        isocenter = get_isocenter_position(beamset, beam_name)

        # Create a key for grouping beams with same couch and isocenter
        group_key = (couch_angle, isocenter)

        if group_key not in beam_groups:
            beam_groups[group_key] = {
                'beams': [],
                'all_angles': set(),
                'angle_to_beams': {}  # maps each angle to list of beams that use it
            }

        # Get gantry sweep for this beam
        gantry_sweeps = find_gantry_angular_traversal(beamset)
        angles, clockwise = gantry_sweeps[beam_name]

        beam_info = {
            'name': beam_name,
            'angles': angles,
            'clockwise': clockwise
        }

        beam_groups[group_key]['beams'].append(beam_info)

        # Track which angles belong to which beams
        for angle in angles:
            beam_groups[group_key]['all_angles'].add(angle)
            if angle not in beam_groups[group_key]['angle_to_beams']:
                beam_groups[group_key]['angle_to_beams'][angle] = []
            beam_groups[group_key]['angle_to_beams'][angle].append(beam_name)

    return beam_groups

def get_head_collision_masks(
        points: np.ndarray,
        diameter: float,
        head_length: float,
        offset_fail: float,
        offset_alert: float,
        gantry_angles: np.ndarray,
        debug: bool = False
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

    # Can't possibly collide filter
    # prefilter radial distances based on the offsets, if they are less than the offset, they can't collide
    r2 = points[:, 0] ** 2 + points[:, 1] ** 2
    keep_alert = r2 > offset_alert ** 2
    keep_fail = r2 > offset_fail ** 2

    # Declare filtered points based on the pre-filtering
    pts_alert = points[keep_alert]
    idx_alert = np.nonzero(keep_alert)[0]
    pts_fail = points[keep_fail]
    idx_fail = np.nonzero(keep_fail)[0]

    # Build a beam direction unit vector for all gantry angles and convert them
    # to standard cylindrical coordinates for vector math
    # axes for all angles
    # Convert iec angles to cylindrical coordinates
    # e.g. [90 -> 0, 0 -> 90, 270 -> 180, 180 -> 270]
    gantry_angles = np.atleast_1d(gantry_angles)
    phi = np.deg2rad((360 - (gantry_angles - 90)) % 360)
    # the unit vector along the central axis
    d = np.stack((np.cos(phi), np.sin(phi), np.zeros_like(phi)), axis=1)

    # centers of the cylinder for fail and alert levels
    C_alert = center_alert * d
    C_fail = center_fail * d

    # relative vectors, i.e. shift points to the cylinder-centered coordinates
    # rel_* [ i, j, :] is the vector from the center of the cylinder at gantry angle i to point j
    # rel_* [ i, j, 0] is the x component of that vector
    # rel_* [ i, j, 1] is the y component of that vector
    # rel_* [ i, j, 2] is the z component of that vector
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


def detect_collisions(rso, roi_dict, clearance_dict, testing=False, downsample_large_rois=False):
    """
    Detect collisions at two levels using an analytic cylinder model with optimized beam grouping.
    Beams with same isocenter and couch angle are grouped to avoid redundant angle checks.

    Args:
        rso: NamedTuple of ScriptObjects in RayStation [case, exam, plan, beamset, db]
        roi_dict: Dictionary of ROIs to check for collisions.
        clearance_dict: Dictionary of clearance parameters with keys:
            'roi_name': Name of the ROI to check for collisions.
            'diameter': Diameter of the bore or head (cm).
            'alert_tolerance': Tolerance for alert level (cm).
            'collision_tolerance': Tolerance for fail level (cm).
            'head_length': Length of the gantry head (cm).
        testing: Boolean indicating whether to run in test mode.

     Detect collisions at two levels using an analytic cylinder model:
      - Fail level: cylinder center at TrueBeam max radius - clearance_dict['collision_tolerance'] cm from isocenter
      - Alert level: cylinder center at TrueBeam max radius - clearance_dict['alert_tolerance'] cm from isocenter


    In test mode:
        * Gantry varies between 180.1 and 179.9 degrees
        * The couch angle varies between 271 and 90 degrees
        * Isocenter position varies relative to the supplied region of interest center

    """
    from PlanReview.review_definitions import SUPPORT_TOLERANCE_COLLISION ,SUPPORT_TOLERANCE_ALERT, TRUEBEAM_MAX_DIAMETER

    # --- head model parameters (cm) ---
    diameter = clearance_dict['COVER_DIAMETER']
    # Distance from isocenter to front face of gantry head (cm), empirically determined to match TrueBeam collision
    h_fail = clearance_dict['diameter'] / 2 - clearance_dict['collision_tolerance']
    # Distance from isocenter to front face of gantry head (cm) [empirically determined to match TrueBeam collision
    # detection alert]
    h_alert = clearance_dict['diameter'] / 2 - clearance_dict['alert_tolerance']
    # Length of the gantry head (cm)
    length = clearance_dict['head_length']

    bad_gantry_fail = {}
    bad_gantry_alert = {}

    # Group beams by (couch_angle, isocenter) combination
    beam_groups = build_beam_groups(rso.beamset)

    # Downsample ROIs once
    roi_downsampled = {}
    if downsample_large_rois:
        for roi_name, roi_pts in roi_dict.items():
            if len(roi_pts) > 1e6:
                logging.debug(f"Downsampling ROI {roi_name} from {len(roi_pts)} points to voxel size 20mm")
                roi_downsampled[roi_name] = downsample_points(roi_pts, voxel_size=[20, 20, 20])
            elif len(roi_pts) > 1e3:
                logging.debug(f"Downsampling ROI {roi_name} from {len(roi_pts)} points to voxel size 20mm")
                roi_downsampled[roi_name] = downsample_points(roi_pts, voxel_size=[10, 10, 10])
            else:
                roi_downsampled[roi_name] = roi_pts
        roi_dict = roi_downsampled


    # Process each beam group
    for (couch_angle, isocenter), group_info in beam_groups.items():
        logging.info(f"Checking beam group: couch={couch_angle}°, iso={isocenter}")
        # Get unique angles across all beams in this group
        unique_angles = np.array(sorted(group_info['all_angles']))

        for roi_name, roi_pts in roi_dict.items():
            # Use first beam for coordinate transformation (same for all beams in group)
            representative_beam = group_info['beams'][0]['name']

            # Transform points to DICOM-isocenter space
            pts_dicom = shift_to_isocenter_and_couch_rotate_points(
                rso, roi_pts, representative_beam, representation='Points'
            )

            # Check collisions for all unique angles at once
            masks_fail, masks_alert = get_head_collision_masks(
                pts_dicom, diameter, length, h_fail, h_alert, unique_angles
            )

            # Find angles with collisions
            fail_angles = [ang for ang, hit in masks_fail.items() if any(hit)]
            alert_angles = [ang for ang, hit in masks_alert.items() if any(hit)]

            # Map collision angles back to affected beams
            if fail_angles or alert_angles:
                # Process fail collisions
                if fail_angles:
                    fail_angles_int = sorted({int(round(ang)) for ang in fail_angles})

                    # For each beam in the group, determine which collision angles affect it
                    for beam_info in group_info['beams']:
                        beam_name = beam_info['name']
                        beam_angles = set(beam_info['angles'])

                        # Find collision angles that intersect with this beam's angles
                        beam_fail_angles = [ang for ang in fail_angles_int
                                            if any(abs(ang - beam_ang) <= 1 for beam_ang in beam_angles)]

                        if beam_fail_angles:
                            fail_ranges = group_overlapping_angles(beam_fail_angles)
                            bad_gantry_fail.setdefault(roi_name, {})[beam_name] = (
                                fail_ranges, beam_info['clockwise']
                            )

                # Process alert collisions (similar logic)
                if alert_angles:
                    alert_angles_int = sorted({int(round(ang)) for ang in alert_angles})

                    for beam_info in group_info['beams']:
                        beam_name = beam_info['name']
                        beam_angles = set(beam_info['angles'])

                        beam_alert_angles = [ang for ang in alert_angles_int
                                             if any(abs(ang - beam_ang) <= 1 for beam_ang in beam_angles)]

                        if beam_alert_angles:
                            alert_ranges = group_overlapping_angles(beam_alert_angles)
                            bad_gantry_alert.setdefault(roi_name, {})[beam_name] = (
                                alert_ranges, beam_info['clockwise']
                            )

    logging.debug("Collision detection complete: fail_rois=%d alert_rois=%d",
                  len(bad_gantry_fail), len(bad_gantry_alert))

    # Debug output
    if testing:
        # TODO: output to an output file: retrive location from logging config
        #       then parse and summarize
        for roi_name, fail_dict in bad_gantry_fail.items():
            if "TrueBeam" in roi_name:
                print(f"Beamset: {rso.beamset.DicomPlanLabel}")
                print(f"\t ROI {roi_name} has {len(fail_dict)} beams with collision issues:")
                for beam_name, (ranges, clockwise) in fail_dict.items():
                    print(f"\t\t{beam_name}: {clockwise}, {ranges}")


    return bad_gantry_fail, bad_gantry_alert


def detect_collisions_tomo(rso, roi_dict, external_roi, support_rois, clearance_dict):
    from PlanReview.review_definitions import PASS, FAIL, ALERT
    beam_name = rso.beamset.Beams[0].Name
    fail_rois = []
    alert_rois = []
    clearance_roi = clearance_dict['roi_name'] # 'TomoTherapy bore covers'
    diameter = clearance_dict['diameter']
    collision_tolerance = clearance_dict['collision_tolerance']
    alert_tolerance = clearance_dict['alert_tolerance']
    fail_diameter = diameter - 2 * collision_tolerance # cm
    alert_diameter = diameter - 2 * alert_tolerance # cm
    for roi, contour_points in roi_dict.items():
        shifted_points = shift_to_isocenter_and_couch_rotate_points(rso, contour_points,
                                                                    beam_name,
                                                                    representation='Points',
                                                                    couch_angle=0)
        fail_mask, alert_mask = filter_in_bore_clearing_points_tomo(
            shifted_points, fail_diameter, alert_diameter)
        # bore_clearance_points, _ = filter_in_bore_clearing_points_tomo(shifted_points,
        #                                                                clearance_diameter)
        bore_clearance_fail = shifted_points[fail_mask]
        bore_clearance_alert = shifted_points[alert_mask]
        # Check if any points are within the tolerance distance from the bore surface
        if bore_clearance_fail.size > 0:
            fail_rois.append(roi)
        if bore_clearance_alert.size > 0:
            alert_rois.append(roi)

    # Determine pass, fail, or alert status based on cleaned violations
    if not fail_rois and not alert_rois:
        return PASS, (f'No collisions detected. {external_roi} and {", ".join(support_rois)}'
                      f'are ≥ {alert_tolerance} cm from {clearance_roi}.')
    elif not fail_rois and alert_rois:
        alert_str = ', '.join(alert_rois)
        return ALERT, (f'Warning: {alert_str} is ≤ {alert_tolerance} cm'
                       f'from the {clearance_roi}, but no hard collisions detected. Isocenter should be adjusted.')
    else:
        violation_str = ', '.join(fail_rois)
        return FAIL, (f'{violation_str} is ≤ {collision_tolerance} cm '
                      f'from the {clearance_roi}. Isocenter must be adjusted.')


# ================= Output Formatting =================
def abbreviate_name(name):
    """ Abbreviate structure names longer than 4 characters """
    length = 5
    if len(name) <= length:
        return name
    else:
        return name[:length]


def format_beam_collisions(bad_gantry, alert=False):
    if not alert:
        output = ["Collision! Adjust Iso or these angles: "]
    else:
        output = ["Warning collision model violated! Adjust Iso or these angles: "]
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
    for roi in rois:
        contour_points = get_voxel_coordinates_direct_optimized(rso, roi)
        rois_checked[roi] = contour_points

    return rois_checked


# ================= Main Function =================
def check_isocenter_clearance(rso, **kwargs):
    from PlanReview.review_definitions import ( PASS, ALERT, FAIL)
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
    :param rso: NamedTuple of ScriptObjects in RayStation [case,exam,plan,beamset,db]
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
    override_support_tolerance_collision = kwargs.get('tolerance_override_collision', None)
    override_support_tolerance_alert = kwargs.get('tolerance_override_alert', None)
    head_diameter_override = kwargs.get('head_diameter_override', None)
    # Get the name of the machine-limiting ROI and the tolerance diameter
    clearance_elements = get_clearance_roi_name_and_diameter(
        rso, collision_tolerance=override_support_tolerance_collision, alert_tolerance=override_support_tolerance_alert,
        head_length=None, head_diameter=head_diameter_override)
    collision_tolerance = clearance_elements['collision_tolerance']
    alert_distance = clearance_elements['alert_tolerance']
    clearance_diameter_roi_name = clearance_elements['roi_name']

    # Find external and support ROIs
    external, supports = find_externals_and_supports(rso)
    if not external and not supports:
        return ALERT, f'No Supports or External found, no clearance test performed.'
    if rois_checked is None:
        # Get voxel representations of external and support ROIs
        rois_checked = extract_voxel_representation(rso, [external] + supports)
    if not rois_checked:
        return ALERT, f'No valid ROIs found for clearance check.'
    if 'Tomo' in clearance_elements['roi_name']:
        pass_result, message_str = detect_collisions_tomo( rso, rois_checked, external, supports, clearance_elements)
    else:
        # Check the beams for VMAT or Static Field
        bad_gantry_fail, bad_gantry_alert = detect_collisions( rso, rois_checked, clearance_elements)
        if type(bad_gantry_fail) == str:
            # An internal error occurred. Print the error message and return an ALERT level.
            return ALERT, bad_gantry_fail
        elif bad_gantry_fail:
            # There are collisions that fail the clearance test
            message_str = format_beam_collisions(bad_gantry_fail, alert=False)
            pass_result = FAIL
        elif bad_gantry_alert:
            # No fail level but there are collisions that are close to failure
            message_str = format_beam_collisions(bad_gantry_alert, alert=True)
            pass_result = ALERT
        else:
            pass_result = PASS
            message_str = f'{[external] + supports} are ≥' \
                          + f' {alert_distance:.1f} ' \
                          + f'cm from {clearance_diameter_roi_name}'
    # Delete script contours
    # delete_rois(rso, rois_to_delete)
    return pass_result, message_str
