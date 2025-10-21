import numpy as np
from scipy.spatial import distance
from scipy.spatial.transform import Rotation as R
import pandas as pd
import time
import logging
from StructureOperations import exists_poi


TB_STX_LEAF_CENTERS = np.array(
    [
        -10.75,
        -10.25,
        -9.75,
        -9.25,
        -8.75,
        -8.25,
        -7.75,
        -7.25,
        -6.75,
        -6.25,
        -5.75,
        -5.25,
        -4.75,
        -4.25,
        -3.875,
        -3.625,
        -3.375,
        -3.125,
        -2.875,
        -2.625,
        -2.375,
        -2.125,
        -1.875,
        -1.625,
        -1.375,
        -1.125,
        -0.875,
        -0.625,
        -0.375,
        -0.125,
        0.125,
        0.375,
        0.625,
        0.875,
        1.125,
        1.375,
        1.625,
        1.875,
        2.125,
        2.375,
        2.625,
        2.875,
        3.125,
        3.375,
        3.625,
        3.875,
        4.25,
        4.75,
        5.25,
        5.75,
        6.25,
        6.75,
        7.25,
        7.75,
        8.25,
        8.75,
        9.25,
        9.75,
        10.25,
        10.75,
    ]
)

TB_STX_WIDTHS = np.array(
    [
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.25,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
    ]
)

TB_M120_LEAF_CENTERS = np.array(
    [
        -19.5,
        -18.5,
        -17.5,
        -16.5,
        -15.5,
        -14.5,
        -13.5,
        -12.5,
        -11.5,
        -10.5,
        -9.75,
        -9.25,
        -8.75,
        -8.25,
        -7.75,
        -7.25,
        -6.75,
        -6.25,
        -5.75,
        -5.25,
        -4.75,
        -4.25,
        -3.75,
        -3.25,
        -2.75,
        -2.25,
        -1.75,
        -1.25,
        -0.75,
        -0.25,
        0.25,
        0.75,
        1.25,
        1.75,
        2.25,
        2.75,
        3.25,
        3.75,
        4.25,
        4.75,
        5.25,
        5.75,
        6.25,
        6.75,
        7.25,
        7.75,
        8.25,
        8.75,
        9.25,
        9.75,
        10.5,
        11.5,
        12.5,
        13.5,
        14.5,
        15.5,
        16.5,
        17.5,
        18.5,
        19.5,
    ]
)

TB_M120_WIDTHS = np.array(
    [
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        0.5,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
        1.0,
    ]
)

Y_LEAF_BOUNDS = {
    "TrueBeamSTx": (
        TB_STX_LEAF_CENTERS - TB_STX_WIDTHS / 2,
        TB_STX_LEAF_CENTERS + TB_STX_WIDTHS / 2,
    ),
    "TrueBeam": (
        TB_M120_LEAF_CENTERS - TB_M120_WIDTHS / 2,
        TB_M120_LEAF_CENTERS + TB_M120_WIDTHS / 2,
    ),
}


def convert_roi_geometries_to_list_of_points(roi_geometries):
    """Converts the ROI geometries to a list of points

    PARAMETERS
    ----------
    roi_geometries

    RETURNS
    -------
    np.array
        A numpy array containing the Cartesian coordinates for all of the
        points in all of the ROI geometries.
    """

    assert isinstance(roi_geometries, list), "roi_geometries must be a list"

    list_of_points = []
    for organ in roi_geometries:
        for plane in organ.PrimaryShape.Contours:
            for point in plane:
                loc = list(point.values())
                list_of_points.append(loc)

    return np.array(list_of_points)


def get_dose_grid_point_list_from_beam_set(beam_set):
    dose_grid = beam_set.FractionDose.InDoseGrid
    isocenter = beam_set.Beams[0].Isocenter.Position

    corner = dose_grid.Corner
    n_vox = dose_grid.NrVoxels
    voxel_size = dose_grid.VoxelSize

    collector = []
    for dim in ["x", "y", "z"]:
        centers = (
            (corner[dim] + voxel_size[dim] / 2)
            + voxel_size[dim] * np.arange(n_vox[dim])
            - isocenter[dim]
        )
        collector.append(centers)

    x_p = collector[2]
    y_p = collector[1]
    z_p = collector[0]

    return np.flip(np.vstack(np.meshgrid(x_p, y_p, z_p)).reshape(3, -1).T, 1)


def map_gantry_angle(angle):
    if angle < 0:
        return angle + 360
    elif angle >= 360:
        return angle - 360
    else:
        return angle


def points_in_bounds(x, y, xmin, xmax, ymin, ymax):
    """Takes a list of points x and y and returns True if inside limits

    PARAMETERS
    ----------
    x : np.array
        A list of x-coordinates
    y : np.array
        A list of y-coordinates
    xmin : float
        The minimum x boundary
    xmax : float
        The maximum x boundary
    ymin : float
        The minimum y boundary
    ymax : float
        The maximum y boundary

    RETURNS
    -------
    np.array of Bool
    True if point is inside limits, else False.
    """

    assert isinstance(x, np.ndarray), "x must be an np.array"
    assert isinstance(y, np.ndarray), "y must be an np.array"
    assert len(x) == len(y), "x and y must have same length"

    in_x_bounds = np.logical_and(xmin < x, x < xmax)
    in_y_bounds = np.logical_and(ymin < y, y < ymax)
    return np.logical_and(in_x_bounds, in_y_bounds)


def distance_from_rectangle(x, y, xmin, xmax, ymin, ymax):
    """Takes a list of points x and y and returns the distance from the a rectangle

    PARAMETERS
    ----------
    x : np.array
        A list of x-coordinates
    y : np.array
        A list of y-coordinates
    xmin : float
        The minimum x boundary
    xmax : float
        The maximum x boundary
    ymin : float
        The minimum y boundary
    ymax : float
        The maximum y boundary

    RETURNS
    -------
    np.array of Bool
    True if point is inside limits, else False.
    """

    assert isinstance(x, np.ndarray), "x must be an np.array"
    assert isinstance(y, np.ndarray), "y must be an np.array"
    assert len(x) == len(y), "x and y must have same length"

    zeros = np.zeros(x.size)
    dx = np.maximum.reduce([xmin - x, zeros, x - xmax])
    dy = np.maximum.reduce([ymin - y, zeros, y - ymax])

    return np.sqrt(dx * dx + dy * dy)


def get_isoplane_projection_of_points(
    list_of_points,
    list_of_gantry_angles=np.array([0]),
    list_of_collimator_angles=np.array([0]),
    list_of_couch_angles=np.array([0]),
    SAD=100,
):
    """Projects a list of points into the beams-eye-view

    PARAMETERS
    ----------
    list_of_points : np.array
        An Mx3 numpy array containing M points. Each row is a point in
        Cartesian coordinates.
    list_of_gantry_angles : np.array
        An Nx1 numpy array containing N gantry angles, one for each of the N
        control points in plan. (degrees, IEC 61217) (default is [0])
    list_of_collimator_angles : np.array
        An Nx1 numpy array containing N collimator angles, one for each of the
        N control points in plan. (degrees, IEC 61217) (default is [0])
    list_of_couch_angles : np.array
        An Nx1 numpy array containing N couch angles, one for each of the
        N control points in plan. (degrees, IEC 61217) (default is [0])
    SAD : float
        The machine source-to-axis distance in cm (default is 100)

    RETURNS
    -------
    tuple : (np.array, np.array, np.array)
        Returns u, v and r, all MxN matrices. u and v are BEV coordinates for
        the M structure points and N control points, and r is the distance from
        each point to the source.
    """

    """
    First, we are going to define an orthogonal coordinate system.
    Vectors e_u and e_v define the BEV plane, while e_s defines
    the central axis of the beam
    """

    assert isinstance(
        list_of_gantry_angles, np.ndarray
    ), "list_of_gantry_angles must be an np.array"
    assert isinstance(
        list_of_collimator_angles, np.ndarray
    ), "list_of_collimator_angles must be an np.array"
    assert isinstance(
        list_of_couch_angles, np.ndarray
    ), "list_of_couch_angles must be an np.array"
    assert len(list_of_gantry_angles) == len(
        list_of_collimator_angles
    ), "list_of_gantry_angles and list_of_collimator_angles must have same length"
    assert len(list_of_gantry_angles) == len(
        list_of_couch_angles
    ), "list_of_gantry_angles and list_of_couch_angles must have same length"

    # Generate a rotation matrix to account for gantry angle
    rot_z = R.from_euler(
        "z", list_of_gantry_angles, degrees=True
    ).as_matrix()  # DOUBLE CHECK FOR SIGN

    # Define a unit vector, e_s, that points from the origin to the
    # photon source. We start with a vector pointing in the positive y
    # direction, then rotate it around the z-axis by the gantry angle
    e_s = np.matmul(rot_z, np.array([0, 1, 0]).transpose())

    # Define a vector, S, −s*e_s, where e_s is the unit vector from
    # the origin(isocenter) to the source and s is the source-to-axis distance (SAD)
    s = SAD
    S = -s * e_s

    # Define e_v, which points in the positive z direction, as another basis vector
    e_v = np.array([0, 0, 1]).transpose()

    # Define e_u as the third basis vector using a cross product
    e_u = -np.cross(e_v, e_s)  # DOUBLE CHECK FOR SIGN

    # Generate a rotation matrix to account for couch angle
    rot_y = R.from_euler(
        "y", list_of_couch_angles, degrees=True
    ).as_matrix()  # DOUBLE CHECK FOR SIGN

    # Rotate e_s, e_v, e_u, S about the y-axis to account for couch rotation
    e_s = np.einsum("...ij,...j", rot_y, e_s)
    e_v = np.einsum("...ij,...j", rot_y, e_v)
    e_u = np.einsum("...ij,...j", rot_y, e_u)
    S = np.einsum("...ij,...j", rot_y, S)

    """
    e_u and e_v define the beams-eye-view plane perpendicular to the source-origin axis
    Right now, it is oriented with e_v in the z-direction. This will give the correct BEV at 
    collimator angle zero, but we need to rotate e_u and e_v for other collimator angles.
    We will construct a rotation matrix using R.from_rotvec function from scipy, then 
    update e_u and e_v based on the user-provided collimator angle
    """
    coll_rad = -list_of_collimator_angles * np.pi / 180.0  # DOUBLE CHECK SIGN
    rot_coll = R.from_rotvec(np.matmul(np.diag(coll_rad), e_s)).as_matrix()
    e_u = np.einsum("...ij,...j", rot_coll, e_u)
    e_v = np.einsum("...ij,...j", rot_coll, e_v)

    """
    We now have our coordinate system in the BEV. The next step is to
    calculate the transformation between Cartesian and BEV coordinates.
    We will use the equations in the following publication:
    https://iopscience.iop.org/article/10.1088/0031-9155/55/23/002/meta
    P = Matrix of points in Cartesian coordiantes
    P_0 = The points of P projected onto an isocenter plane orthogonal to e_s

    From this, we can calculate the BEV coodinates u and v
    u = P_0 dot e_u
    v = P_0 dot e_v

    The distance from the source (S) to the points (P) is also valuable. We will
    call this r = ||(P-S)||. This value is useful for determining if a given point is
    in front of or behind isocenter (or other stuff in the BEV)
    """
    P = list_of_points

    # Supersize S and P for broadcasting
    SS = S[None, :, :]
    PP = P[:, None, :]

    PP_minus_SS = PP - SS
    PP_0 = (
        SS
        - (s**2) * (PP_minus_SS) / np.einsum("...k,...k", PP_minus_SS, SS)[:, :, None]
    )
    u = np.einsum("...k,...k", PP_0, e_u)
    v = np.einsum("...k,...k", PP_0, e_v)
    r = np.linalg.norm(PP_minus_SS, axis=2)

    # Return u, v and r in a tuple
    return (u, v, r)


def get_isoplane_projection_of_points_verbose(
    list_of_points,
    list_of_gantry_angles=np.array([0]),
    list_of_collimator_angles=np.array([0]),
    list_of_couch_angles=np.array([0]),
    SAD=100,
):
    """Projects a list of points into the beams-eye-view

    PARAMETERS
    ----------
    list_of_points : np.array
        An Mx3 numpy array containing M points. Each row is a point in
        Cartesian coordinates.
    list_of_gantry_angles : np.array
        An Nx1 numpy array containing N gantry angles, one for each of the N
        control points in plan. (degrees, IEC 61217) (default is [0])
    list_of_collimator_angles : np.array
        An Nx1 numpy array containing N collimator angles, one for each of the
        N control points in plan. (degrees, IEC 61217) (default is [0])
    list_of_couch_angles : np.array
        An Nx1 numpy array containing N couch angles, one for each of the
        N control points in plan. (degrees, IEC 61217) (default is [0])
    SAD : float
        The machine source-to-axis distance in cm (default is 100)

    RETURNS
    -------
    tuple : (np.array, np.array, np.array)
        Returns u, v and r, all MxN matrices. u and v are BEV coordinates for
        the M structure points and N control points, and r is the distance from
        each point to the source.
    """

    """
    First, we are going to define an orthogonal coordinate system.
    Vectors e_u and e_v define the BEV plane, while e_s defines
    the central axis of the beam
    """

    assert isinstance(
        list_of_gantry_angles, np.ndarray
    ), "list_of_gantry_angles must be an np.array"
    assert isinstance(
        list_of_collimator_angles, np.ndarray
    ), "list_of_collimator_angles must be an np.array"
    assert isinstance(
        list_of_couch_angles, np.ndarray
    ), "list_of_couch_angles must be an np.array"
    assert len(list_of_gantry_angles) == len(
        list_of_collimator_angles
    ), "list_of_gantry_angles and list_of_collimator_angles must have same length"
    assert len(list_of_gantry_angles) == len(
        list_of_couch_angles
    ), "list_of_gantry_angles and list_of_couch_angles must have same length"

    # Generate a rotation matrix to account for gantry angle
    rot_z = R.from_euler(
        "z", list_of_gantry_angles, degrees=True
    ).as_matrix()  # DOUBLE CHECK FOR SIGN

    # Define a unit vector, e_s, that points from the origin to the
    # photon source. We start with a vector pointing in the positive y
    # direction, then rotate it around the z-axis by the gantry angle
    e_s = np.matmul(rot_z, np.array([0, 1, 0]).transpose())

    # Define a vector, S, −s*e_s, where e_s is the unit vector from
    # the origin(isocenter) to the source and s is the source-to-axis distance (SAD)
    s = SAD
    S = -s * e_s

    # Define e_v, which points in the positive z direction, as another basis vector
    e_v = np.array([0, 0, 1]).transpose()

    # Define e_u as the third basis vector using a cross product
    e_u = -np.cross(e_v, e_s)  # DOUBLE CHECK FOR SIGN

    # Generate a rotation matrix to account for couch angle
    rot_y = R.from_euler(
        "y", list_of_couch_angles, degrees=True
    ).as_matrix()  # DOUBLE CHECK FOR SIGN

    # Rotate e_s, e_v, e_u, S about the y-axis to account for couch rotation
    e_s = np.einsum("...ij,...j", rot_y, e_s)
    e_v = np.einsum("...ij,...j", rot_y, e_v)
    e_u = np.einsum("...ij,...j", rot_y, e_u)
    S = np.einsum("...ij,...j", rot_y, S)

    """
    e_u and e_v define the beams-eye-view plane perpendicular to the source-origin axis
    Right now, it is oriented with e_v in the z-direction. This will give the correct BEV at 
    collimator angle zero, but we need to rotate e_u and e_v for other collimator angles.
    We will construct a rotation matrix using R.from_rotvec function from scipy, then 
    update e_u and e_v based on the user-provided collimator angle
    """
    coll_rad = -list_of_collimator_angles * np.pi / 180.0  # DOUBLE CHECK SIGN
    rot_coll = R.from_rotvec(np.matmul(np.diag(coll_rad), e_s)).as_matrix()
    e_u = np.einsum("...ij,...j", rot_coll, e_u)
    e_v = np.einsum("...ij,...j", rot_coll, e_v)

    """
    We now have our coordinate system in the BEV. The next step is to
    calculate the transformation between Cartesian and BEV coordinates.
    We will use the equations in the following publication:
    https://iopscience.iop.org/article/10.1088/0031-9155/55/23/002/meta
    P = Matrix of points in Cartesian coordiantes
    P_0 = The points of P projected onto an isocenter plane orthogonal to e_s

    From this, we can calculate the BEV coodinates u and v
    u = P_0 dot e_u
    v = P_0 dot e_v

    The distance from the source (S) to the points (P) is also valuable. We will
    call this r = ||(P-S)||. This value is useful for determining if a given point is
    in front of or behind isocenter (or other stuff in the BEV)
    """
    P = list_of_points

    # Supersize S and P for broadcasting
    SS = S[None, :, :]
    PP = P[:, None, :]

    PP_minus_SS = PP - SS
    PP_0 = (
        SS
        - (s**2) * (PP_minus_SS) / np.einsum("...k,...k", PP_minus_SS, SS)[:, :, None]
    )
    u = np.einsum("...k,...k", PP_0, e_u)
    v = np.einsum("...k,...k", PP_0, e_v)
    r = np.linalg.norm(PP_minus_SS, axis=2)

    # Return
    return (u, v, r, e_u, e_v, e_s)


def distance_from_jaws(x, y, list_of_rectangles):
    """Takes a list of N points x and y and returns the distance from M rectangles

    PARAMETERS
    ----------
    x : np.array
        A numpy array of NxM values.
    y : np.array
        A numpy array of NxM values.
    list_of_rectangles : np.array
        A numpy array of Mx4 values. Each of the M rows is a list of
        boundaries [xmin, xmax, ymin, ymax] for each rectangle

    RETURNS
    -------
    np.array (NxM)
    Distance from each point (N) to the jaws for each control point (M)
    """

    assert isinstance(x, np.ndarray), "x must be an np.array"
    assert isinstance(y, np.ndarray), "y must be an np.array"
    assert isinstance(
        list_of_rectangles, np.ndarray
    ), "list_of_rectangles must be an np.array"
    assert x.shape == y.shape, "x and y must have same shape"
    assert (
        x.shape[1] == list_of_rectangles.shape[0]
    ), "axis=1 of x,y must match axis=0 of list_of_rectangles"

    xmin = list_of_rectangles[:, 0]
    xmax = list_of_rectangles[:, 1]
    ymin = list_of_rectangles[:, 2]
    ymax = list_of_rectangles[:, 3]

    zeros = np.zeros(x.shape)
    dx = np.maximum.reduce([xmin[None, :] - x, zeros, x - xmax[None, :]])
    dy = np.maximum.reduce([ymin[None, :] - y, zeros, y - ymax[None, :]])

    return np.sqrt(dx * dx + dy * dy)


def distance_from_jaws_verbose(x, y, list_of_rectangles):
    """Takes a list of N points x and y and returns the distance from M rectangles

    PARAMETERS
    ----------
    x : np.array
        A numpy array of NxM values.
    y : np.array
        A numpy array of NxM values.
    list_of_rectangles : np.array
        A numpy array of Mx4 values. Each of the M rows is a list of
        boundaries [xmin, xmax, ymin, ymax] for each rectangle

    RETURNS
    -------
    np.array (NxM)
    Distance from each point (N) to the jaws for each control point (M)
    """

    assert isinstance(x, np.ndarray), "x must be an np.array"
    assert isinstance(y, np.ndarray), "y must be an np.array"
    assert isinstance(
        list_of_rectangles, np.ndarray
    ), "list_of_rectangles must be an np.array"
    assert x.shape == y.shape, "x and y must have same shape"
    assert (
        x.shape[1] == list_of_rectangles.shape[0]
    ), "axis=1 of x,y must match axis=0 of list_of_rectangles"

    xmin = list_of_rectangles[:, 0]
    xmax = list_of_rectangles[:, 1]
    ymin = list_of_rectangles[:, 2]
    ymax = list_of_rectangles[:, 3]

    zeros = np.zeros(x.shape)
    dx = np.maximum.reduce([xmin[None, :] - x, zeros, x - xmax[None, :]])
    dy = np.maximum.reduce([ymin[None, :] - y, zeros, y - ymax[None, :]])

    return np.sqrt(dx * dx + dy * dy), dx, dy


def get_device_dist_to_field_edge(
    case,
    beam_set,
    examination,
    roi_name,
):

    verbose_output = True

    def report_runtime(start_time, label):
        elapsed_time = time.time() - start_time
        logging.debug(f"{label}: {elapsed_time:.2f} seconds")

    start_time = time.time()

    list_of_cp_descriptions = []
    list_of_gant_angles = []
    list_of_coll_angles = []
    list_of_couch_angles = []
    list_of_jaw_positions = []
    list_of_MLC_positions = []
    iso_np = np.array(list(beam_set.Beams[0].Isocenter.Position.values()))

    report_runtime(start_time, "Starting collection of beam data.")

    for beam in beam_set.Beams:
        beam_desc = beam.Name

        machine_name = beam.MachineReference.MachineName
        Y1, Y2 = Y_LEAF_BOUNDS[machine_name]

        for segment in beam.Segments:
            segment_desc = segment.SegmentNumber + 1  # +1 since CPs start at 1 in RS
            segment_string = f"{beam_desc}, Control Point {segment_desc}: "
            segment_string += (
                f"Gantry = {beam.GantryAngle + segment.DeltaGantryAngle} deg, "
            )
            segment_string += f"Collimator = {segment.CollimatorAngle} deg, "
            segment_string += (
                f"Couch = {beam.CouchRotationAngle + segment.DeltaCouchAngle} deg"
            )
            list_of_cp_descriptions.append(segment_string)

            list_of_gant_angles.append(
                map_gantry_angle(beam.GantryAngle + segment.DeltaGantryAngle)
            )
            list_of_coll_angles.append(map_gantry_angle(segment.CollimatorAngle))
            list_of_couch_angles.append(
                map_gantry_angle(beam.CouchRotationAngle + segment.DeltaCouchAngle)
            )
            list_of_jaw_positions.append(list(segment.JawPositions))

            bank_A = segment.LeafPositions[0]
            bank_B = segment.LeafPositions[1]

            for a, b, y1, y2 in zip(bank_A, bank_B, Y1, Y2):
                list_of_MLC_positions.append([a, b, y1, y2])

    list_of_gant_angles = np.array(list_of_gant_angles)
    list_of_coll_angles = np.array(list_of_coll_angles)
    list_of_couch_angles = np.array(list_of_couch_angles)
    list_of_jaw_positions = np.array(list_of_jaw_positions)
    list_of_MLC_positions = np.array(list_of_MLC_positions)
    list_of_MLC_positions = np.reshape(
        list_of_MLC_positions, (list_of_MLC_positions.shape[0] // 60, 60, 4)
    )

    report_runtime(start_time, "Completed collection of beam data.")
    report_runtime(start_time, "Starting collection of ROI data.")

    organ_list = [roi_name]
    organs = [
        case.PatientModel.StructureSets[examination.Name].RoiGeometries[organ]
        for organ in organ_list
    ]
    organ_coords = convert_roi_geometries_to_list_of_points(organs) - iso_np

    report_runtime(start_time, "Completed collection of ROI data.")
    report_runtime(start_time, "Starting projection of ROI data into BEV.")

    if verbose_output:
        (u, v, r, e_u, e_v, e_s) = get_isoplane_projection_of_points_verbose(
            organ_coords,
            list_of_gantry_angles=list_of_gant_angles,
            list_of_collimator_angles=list_of_coll_angles,
            list_of_couch_angles=list_of_couch_angles,
        )
    else:
        u, v, _ = get_isoplane_projection_of_points(
            organ_coords,
            list_of_gantry_angles=list_of_gant_angles,
            list_of_collimator_angles=list_of_coll_angles,
            list_of_couch_angles=list_of_couch_angles,
        )

    report_runtime(start_time, "Completed projection of ROI data into BEV.")
    report_runtime(start_time, "Starting calculation of distances from collimator.")

    if verbose_output:
        rect_dist, du, dv = distance_from_jaws_verbose(u, v, list_of_jaw_positions)
    else:
        rect_dist = distance_from_jaws(u, v, list_of_jaw_positions)

    report_runtime(start_time, "Completed calculation of distances from collimator.")
    report_runtime(start_time, "Starting determination of min value")

    # Construct string
    min_dist = np.min(rect_dist, axis=None)
    roi_point, control_point = np.unravel_index(
        np.argmin(rect_dist, axis=None), rect_dist.shape
    )
    if verbose_output:

        # Delete any current POIs pertaining to CIEDs
        cied_pois = ["Closest Approach - CIED", "Closest Approach - Ray"]

        for poi in cied_pois:
            if exists_poi(case=case, pois=poi)[0]:
                case.PatientModel.PointsOfInterest[poi].DeleteRoi()

        # Create POI at ROI location of closest approach
        xyz_closest_approach = organ_coords[roi_point] + iso_np
        case.PatientModel.CreatePoi(
            Examination=examination,
            Point={
                "x": xyz_closest_approach[0],
                "y": xyz_closest_approach[1],
                "z": xyz_closest_approach[2],
            },
            Name="Closest Approach - CIED",
            Color="Yellow",
            VisualizationDiameter=0.1,
            Type="DoseRegion",
        )
        # Create POI at the ray of closest approach
        mag_factor = r[roi_point, control_point] / 100

        if u[roi_point, control_point] > list_of_jaw_positions[control_point, 1]:
            u_shift = -mag_factor * du[roi_point, control_point] * e_u[control_point]
        else:
            u_shift = mag_factor * du[roi_point, control_point] * e_u[control_point]

        if v[roi_point, control_point] > list_of_jaw_positions[control_point, 3]:
            v_shift = -mag_factor * dv[roi_point, control_point] * e_v[control_point]
        else:
            v_shift = mag_factor * dv[roi_point, control_point] * e_v[control_point]

        xyz_closest_ray = xyz_closest_approach + u_shift + v_shift
        case.PatientModel.CreatePoi(
            Examination=examination,
            Point={
                "x": xyz_closest_ray[0],
                "y": xyz_closest_ray[1],
                "z": xyz_closest_ray[2],
            },
            Name="Closest Approach - Ray",
            Color="Yellow",
            VisualizationDiameter=0.1,
            Type="DoseRegion",
        )

    report_runtime(start_time, "Completed determination of min value.")

    min_dist_description = f"The minimum distance of {min_dist} cm occurred for {list_of_cp_descriptions[control_point]}.\nThe DICOM location of nearest approach is {organ_coords[roi_point]+iso_np}"

    return np.min(rect_dist), min_dist_description


def get_device_D0_03cc(case, beam_set, examination, roi_name):
    """Returns the D0.03cc to the roi_name for plan"""

    roi_geometry = case.PatientModel.StructureSets[examination.Name].RoiGeometries[
        roi_name
    ]

    pct_dose = 0.03 / roi_geometry.GetRoiVolume()

    dose_per_fraction_in_cGy = beam_set.FractionDose.GetDoseAtRelativeVolumes(
        RoiName=roi_name, RelativeVolumes=[pct_dose]
    )
    number_of_fractions = beam_set.FractionationPattern.NumberOfFractions

    return dose_per_fraction_in_cGy[0] / 100 * number_of_fractions


def get_beamset_beam_quality(beam_set):
    df = pd.DataFrame()

    beamset_modality = beam_set.Modality
    for beam in beam_set.Beams:
        beam_quality = beam.BeamQualityId

        beam_has_neutrons = True
        if beamset_modality == "Electrons":
            if (beam_quality == "6") or (beam_quality == "9") or (beam_quality == "12"):
                beam_has_neutrons = False

        if beamset_modality == "Photons":
            if (
                (beam_quality == "6")
                or (beam_quality == "10")
                or (beam_quality == "6 FFF")
                or (beam_quality == "10 FFF")
            ):
                beam_has_neutrons = False

        entry_dict = {
            "Beamset Name": beam_set.DicomPlanLabel,
            "Beamset Modality": [beamset_modality],
            "Beamset Delivery Technique": beam_set.DeliveryTechnique,
            "Beamset Plan Generation Technique": beam_set.PlanGenerationTechnique,
            "Beam Name": beam.Name,
            "Beam Quality": [beam_quality],
            "Beam Has Neutrons": [beam_has_neutrons],
        }

        entry_df = pd.DataFrame(entry_dict)
        df = pd.concat([df, entry_df])

    return df
