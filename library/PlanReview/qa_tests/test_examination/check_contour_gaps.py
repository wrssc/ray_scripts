import numpy as np
import math
from PlanReview.review_definitions import PASS, FAIL


def get_slice_positions(rso):
    # Get slice positions in linear array
    slice_positions = np.array(rso.exam.Series[0].ImageStack.SlicePositions)
    #
    # Starting corner of the image set
    image_corner = rso.exam.Series[0].ImageStack.Corner
    #
    # Actual z positions
    dicom_slice_positions = image_corner.z + slice_positions
    return dicom_slice_positions


def find_nearest(array, values):
    # Finds the nearest values of the numpy array values in the array, array
    array = np.asarray(array)
    idx = [(np.abs(array - v)).argmin() for v in values]
    return array[idx]


def extract_grid(rg, bb, voxel_size, slice_positions):
    """
    Resample the roi geometry (rg) of an roi onto a grid defined by that roi's bounding box
    Returns a 3D array of the roi resampled onto a grid,
    the values of the returned array are 0-255 depending on how much of that voxel is covered by
    the roi
    The 3D form is [z, y*x] for faster sorting by axial position
    :param rg: rso geometry (case.PatientModel.StructureSets[exam].RoiGeometries[roi])
    :param bb: bounding box
    :param voxel_size: dict {'x','y','z'}: desired voxel size
    :param slice_positions: array of CT slice positions in z
    :return: an array resampled on the grid: [z, x*y]
    """
    # Find nearest CT slices to the bounding box of the geometry
    z0 = find_nearest(slice_positions, [bb[0]['z']])[0]
    z1 = find_nearest(slice_positions, [bb[1]['z']])[0]
    new_grid = {'Corner': {'x': bb[0]['x'], 'y': bb[0]['y'], 'z': bb[0]['z']},
                'NrVoxels': {
                    'x': int(math.ceil(bb[1]['x'] - bb[0]['x']) / voxel_size['x']),
                    'y': int(math.ceil(bb[1]['y'] - bb[0]['y']) / voxel_size['y']),
                    'z': int((z1 - z0) / voxel_size['z'])},
                'VoxelSize': voxel_size}
    resampled = rg.GetRoiGeometryAsVoxels(Corner=new_grid['Corner'],
                                          VoxelSize=new_grid['VoxelSize'],
                                          NrVoxels=new_grid['NrVoxels'])
    return resampled.reshape(new_grid['NrVoxels']['z'],
                             new_grid['NrVoxels']['y'] * new_grid['NrVoxels']['x'])


def find_gaps(rg, voxel_size, slice_positions):
    """
    Find discontinuities in the supplied geometry in the sup/inf direction
    :param rg: rso geometry (case.PatientModel.StructureSets[exam].RoiGeometries[roi])
    :param voxel_size: dict {'x','y','z'}: desired voxel size
    :param slice_positions: array of CT slice positions in z
    :return: a list of slice positions which are missing contours
    """
    # Determine a bounding box for the contour
    bb = rg.GetBoundingBox()
    roi_voxels = extract_grid(rg, bb, voxel_size, slice_positions)
    empty_slices = np.where(~np.any(roi_voxels[:-1], axis=1))[0]
    if empty_slices.size > 0:
        return empty_slices * voxel_size['z'] + bb[0]['z']
    else:
        return None


def consecutive(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) >= stepsize)[0] + 1)


def check_contour_gaps(rso):
    """
    Look for S/I discontinuties in all rois that have contours and are not
    derived by resampling the roi onto a small grid and looking for empty
    slices

    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    :return: message (list str): [Pass_Status, Message String]

    Test Patient:
        Tomo3D_Skin: ZZUWQA_Tomo3D_SkinInvolved: Contours not labeled "Gaps" don't have gaps
        Tomo Leg: ZZUWQA_14Mar2023_01: GTV_Combo has the kinds of gaps I can think of

    """
    # Look through all available rois that have contours for gaps
    message_str = ""
    # All Rois with contours
    rois_with_contours = [rg.OfRoi.Name for rg in
                          rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries if
                          rg.HasContours()]
    # Get slice positions
    slices = get_slice_positions(rso)
    # Get the slice thickness of the CT
    delta_z = slices[1] - slices[0]
    voxel_size = {'x': 0.2, 'y': 0.2, 'z': delta_z}
    # Build a dictionary with key = roi name, and values
    # of the gap strings
    gaps = {}
    for roi in rois_with_contours:
        # Get the roi geometry
        roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi]
        # Find any gaps
        roi_gaps = find_gaps(roi_geometry, voxel_size, slice_positions=slices)
        if roi_gaps is not None:
            # Create an array of the sorted list of unique gap positions
            slices_with_gaps = np.array(sorted(list(set(roi_gaps))))
            gap_positions = []
            gap_groups = consecutive(slices_with_gaps, delta_z + 1e-6)
            for g in gap_groups:
                if g.shape[0] > 1:
                    gap_positions.append("({0:0.1f}-{1:0.1f})"
                                         .format(round(g[0], 1), round(g[-1], 1)))
                else:
                    gap_positions.append("{0:0.1f}".format(round(g[0], 1)))
            gaps[roi] = gap_positions

    if gaps:
        pass_result = FAIL
        message_str = 'Gaps in contours: '
        for roi, gap_positions in gaps.items():
            message_str += f'{roi}{gap_positions} '
        message_str = message_str.replace("'", "").rstrip()
    else:
        pass_result = PASS
        message_str = 'No gaps found in current contour set'
    return pass_result, message_str
