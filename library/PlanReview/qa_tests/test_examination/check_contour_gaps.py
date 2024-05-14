from typing import NamedTuple, Tuple
import numpy as np
import math
import re
from library.PlanReview.review_definitions import PASS, FAIL
import logging


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
    if roi_voxels is None:
        return None
    empty_slices = np.where(~np.any(roi_voxels[:-1], axis=1))[0]
    if empty_slices.size > 0:
        return empty_slices * voxel_size['z'] + bb[0]['z']
    else:
        return None


def consecutive(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) >= stepsize)[0] + 1)


def check_for_valid_contours(rso):
    geom_list = []
    for rg in rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries:
        if rg.HasContours() and hasattr(rg.PrimaryShape, 'Contours'):
            geom_list.append(rg)
    return geom_list

def get_contour_list(rso):
    contour_list = []
    # All Rois with contours
    rois_with_contours = check_for_valid_contours(rso)
    organ_types = ['Target', 'OrganAtRisk']
    roi_types = ['Ptv', 'Ctv', 'Gtv', 'Organ']
    # Define exclusion patterns
    exclude_from_contour_analysis = ['NoFlyZone_PRV', '^OTV.*', '^PTV.*_Eval$']

    # ROI names if they have a type match in review_types
    for rg in rois_with_contours:
        if rg.OfRoi.OrganData.OrganType in organ_types and \
                rg.OfRoi.Type in roi_types:
            if not any(re.search(pattern, rg.OfRoi.Name) for pattern in exclude_from_contour_analysis):
                contour_list.append(rg.OfRoi.Name)
    return contour_list


def check_contour_gaps(rso: NamedTuple) -> Tuple[str, str]:
    """ Check Contour Gaps
        Look for Superior/Inferior discontinuities in all ROIs that have contours and are not
        derived. The function resamples the ROI onto a small grid and looks for empty slices.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL),
                                                       Second element is the message string.

        Pseudocode:
        1. Look through all available ROIs that have contours for gaps.
        2. Get slice positions from 'get_slice_positions' function.
        3. Determine voxel size based on CT slice thickness.
        4. For each ROI:
            a. Use 'find_gaps' function to detect gaps in ROI.
               i. Determine a bounding box for the ROI contour.
              ii. Resample the ROI onto a grid defined by the bounding box.
             iii. Look for any slices without contour data (empty slices).
              iv. If found, store these slice positions as gaps.
        5. Accumulate gaps and related information into a message string.
        6. Determine the result (PASS/FAIL) based on gap detection.
        7. Return the result and message string.

    Test Patients:
        Pass: Tomo3D_Skin: ZZUWQA_Tomo3D_SkinInvolved: Contours not labeled "Gaps" don't have gaps
        Fail: Tomo Leg: ZZUWQA_14Mar2023_01: GTV_Combo has the kinds of gaps I can think of

    """
    # Look through all available rois that have contours for gaps
    message_str = ""
    rois_to_check = get_contour_list(rso)
    # Get slice positions
    slices = get_slice_positions(rso)
    # Get the slice thickness of the CT
    delta_z = slices[1] - slices[0]
    voxel_size = {'x': 0.2, 'y': 0.2, 'z': delta_z}
    # Build a dictionary with key = roi name, and values
    # of the gap strings
    gaps = {}
    for roi in rois_to_check:
        # Get the roi geometry
        logging.debug(f'Checking {roi}')
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
