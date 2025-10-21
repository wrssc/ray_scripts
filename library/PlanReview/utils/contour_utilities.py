import numpy as np
import logging


def update_derived_geometry(rso, roi_name):
    logging.debug(f'Updating derived geometry for {roi_name}')
    rso.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
        Examination=rso.exam, Algorithm="Auto", )
    # get shape status
    shape_status = rso.case.PatientModel.StructureSets[rso.exam.Name]\
        .RoiGeometries[roi_name].PrimaryShape.DerivedRoiStatus.IsShapeDirty
    logging.debug(f'Shape status: {shape_status} for {roi_name}')
    while shape_status:
        # Try two methods of updating derived geometry
        # rso.case.PatientModel.UpdateDerivedGeometries(
        #    RoiNames=[roi_name], Examination=rso.exam, Algorithm="Auto")
        rso.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
            Examination=rso.exam, Algorithm="Auto", )
        rso.patient.Save()
    return shape_status


def compute_dice_sp_sn_dta(rso, exam_name, target, reference, eval_distance):
    comp_dict = {}
    ss = rso.case.PatientModel.StructureSets[exam_name]
    comp_keys = ['DiceSimilarityCoefficient', 'Precision',
                 'Sensitivity', 'Specificity',
                 'MeanDistanceToAgreement', 'MaxDistanceToAgreement']
    # Get DSC/JAQ/SP/SN
    if ss.RoiGeometries[reference].HasContours() and ss.RoiGeometries[target].HasContours() \
            and ss.RoiGeometries[target].GetRoiVolume() >= 0.01:
        try:
            comp = ss.ComparisonOfRoiGeometries(RoiA=target,
                                                RoiB=reference,
                                                ComputeDistanceToAgreementMeasures=False)
            for k, v in comp.items():
                comp_dict[k] = v

            if comp['Sensitivity'] != 1.0 and eval_distance:
                # RS Crash if DTA is computed with totally overlapping ROIS
                comp = ss.ComparisonOfRoiGeometries(RoiA=target,
                                                    RoiB=reference,
                                                    ComputeDistanceToAgreementMeasures=eval_distance)
                for k, v in comp.items():
                    comp_dict[k] = v
            else:
                comp_dict['Specificity'] = np.NAN
                comp_dict['MeanDistanceToAgreement'] = np.NAN
                comp_dict['MaxDistanceToAgreement'] = np.NAN
        except:
            print(f'Unable to evaluate {target}: {reference}')
            for k in comp_keys:
                comp_dict[k] = np.NAN

    else:
        for k in comp_keys:
            comp_dict[k] = np.NAN
    return comp_dict


def roi_has_contours(rso, roi_name):
    """
    Check if an ROI has contours.

    Args:
        rso: RayStation object containing beamset information.
        roi_name (str): Name of the ROI to check for contours.

    Returns:
        bool: True if the ROI has contours, otherwise False.
    """
    try:
        return rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name].HasContours()
    except Exception as e:
        logging.warning(f"An error occurred while checking for contours in {roi_name}: {e}")
        return False


def unique_roi_name(rso, desired_name):
    """
    Generate a unique ROI name by appending a number to the desired name.

    Args:
        rso: RayStation object containing beamset information.
        desired_name (str): The desired name for the ROI.

    Returns:
        str: A unique ROI name.
    """
    try:
        return rso.case.PatientModel.GetUniqueRoiName(DesiredName=desired_name)
    except Exception as e:
        return None


def create_roi(rso, roi_name, roi_type='Undefined', color="192, 192, 192",
               tissue_name=None, rbe_cell_type_name=None, roi_material=None):
    """
    Create an ROI in RayStation.

    Args:
        rso: NamedTuple of ScriptObjects in RayStation [case, exam, plan, beamset, db].
        roi_name (str): Name of the ROI to create.
        roi_type (str): Type of the ROI to create.
        color (str): Color of the ROI.

    Returns:
        bool: True if the ROI is successfully created, otherwise False.
    """
    try:
        rso.case.PatientModel.CreateRoi(
            Name=roi_name,
            Color=color,
            Type=roi_type,
            TissueName=tissue_name,
            RbeCellTypeName=rbe_cell_type_name,
            RoiMaterial=roi_material,
        )
        return True
    except Exception as e:
        logging.warning(f"An error occurred while creating the ROI {roi_name}: {e}")
        return False


def copy_roi(rso, source_roi_name, suffix='', representation='Contours'):
    """
     Try to copy the geometry of an roi
     Args:
         rso:
         source_roi_name:
            suffix: string to append to the new roi name
            representation: 'Contours' 'Voxels' or 'Triangle Mesh'

     Returns:

     """
    copied_roi = unique_roi_name(rso, source_roi_name + suffix)
    roi_created = create_roi(rso, copied_roi, roi_type='Undefined', color="192, 192, 192")
    if not roi_created:
        return None
    # Make copy using algebra
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    try:
        rso.case.PatientModel.RegionsOfInterest[copied_roi].CreateMarginGeometry(
            SourceRoiName=source_roi_name,
            Examination=rso.exam,
            MarginSettings=margins,
        )
    except Exception as e:
        logging.warning(f"An error occurred while copying the geometry of {source_roi_name}: {e}")
        return None

    # Update derived geometry
    # Set representation
    try:
        rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[copied_roi] \
            .SetRepresentation(Representation=representation)
    except Exception as e:
        logging.warning(f"An error occurred while setting the representation of {copied_roi}: {e}")
        return None

    # Delete derived geometry
    try:
        print(f"Deleting derived geometry of {copied_roi}")
        # rso.case.PatientModel.RegionsOfInterest[copied_roi].DeleteExpression()
    except Exception as e:
        logging.warning(f"An error occurred while deleting the derived geometry of {copied_roi}: {e}")
        return None
    logging.info(f"ROI {source_roi_name} copied to {copied_roi}")

    return copied_roi


def get_voxel_geometry(rso, roi_name):
    """
    Get the voxel geometry of an ROI. If the ROI does not have a voxel representation, set it.

    Args:
        rso: RayStation object containing beamset information.
        roi_name (str): Name of the ROI to get the voxel geometry from.

    Returns:
        RayStationObject: RayStation object containing the voxel geometry of the ROI.
    """
    roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name]
    if hasattr(roi_geometry.PrimaryShape, 'VoxelValues'):
        return roi_geometry
    else:
        try:
            roi_geometry.SetRepresentation(Representation='Voxels')
            return roi_geometry
        except Exception as e:
            logging.warning(f"An error occurred while setting the representation of {roi_name}: {e}")
            return None


def get_voxel_coordinates(roi_geometry):
    """
    Get the DICOM coordinates of all voxels.
    Tested for time, requires ~0.2s for a 512x512x100 volume with ~50k voxels.

    Args:
        roi_geometry (RayStationObject): RayStation object containing the ROI geometry.

    Returns:
        numpy.ndarray: A Numpy Array of DICOM coordinates of the voxels.
    """
    # Extract the shape object
    primary_shape = roi_geometry.PrimaryShape

    #
    # Extract the shape properties
    # Get the corner coordinates
    corner = (primary_shape.Corner.x, primary_shape.Corner.y, primary_shape.Corner.z)

    # Get the voxel size
    voxel_size = (primary_shape.VoxelSize.x, primary_shape.VoxelSize.y, primary_shape.VoxelSize.z)

    # Reshape the 1D values array into a 3D array
    values_3d = primary_shape.VoxelValues.reshape((primary_shape.NrVoxels.z,
                                                   primary_shape.NrVoxels.y,
                                                   primary_shape.NrVoxels.x,))
    # Transpose to x, y, z
    values_3d = np.transpose(values_3d, (2, 1, 0))

    # Find Non-Zero Voxels
    # Get the indices of voxels with full coverage by the ROI
    voxel_indices = np.argwhere(values_3d == 255)
    # Coordinate conversion
    # Convert voxel indices to DICOM coordinates using vectorized operations
    voxel_coords = voxel_indices * voxel_size + corner

    return voxel_coords


def get_voxel_coordinates_direct_optimized(rso, roi_name):
    """
    Uses the API call GetRoiGeometryAsVoxels to get the voxel coordinates directly, avoiding a
    copy of the contour if the representation is not already voxels.
    Add padding to avoid boundary assertion failures
    Get the DICOM coordinates of all voxels using GetRoiGeometryAsVoxels.

    """

    try:
        roi_geometry = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_name]
        # Get the volume of the ROI and set the voxel size accordingly
        volume=roi_geometry.GetRoiVolume()
        if volume<1.0:
            voxel_size_mm=0.5
        elif volume<100.0:
            voxel_size_mm=1.0
        elif volume<1000.0:
            voxel_size_mm=5.0
        else:
            voxel_size_mm=6.0

        bbox = roi_geometry.GetBoundingBox()

        voxel_size_cm = voxel_size_mm / 10.0

        # Calculate bounding box size
        bbox_size = [
            bbox[1].x - bbox[0].x,
            bbox[1].y - bbox[0].y,
            bbox[1].z - bbox[0].z
        ]

        # Add padding to avoid boundary assertion failures
        # The padding should be at least one voxel size to satisfy the assertion
        padding = voxel_size_cm * 10  # Use 10x voxel size for safety

        corner = {
            'x': bbox[0].x - padding,
            'y': bbox[0].y - padding,
            'z': bbox[0].z - padding
        }

        # Calculate number of voxels including padding
        nr_voxels = {
            'x': max(1, int((bbox_size[0] + 2 * padding) / voxel_size_cm)),
            'y': max(1, int((bbox_size[1] + 2 * padding) / voxel_size_cm)),
            'z': max(1, int((bbox_size[2] + 2 * padding) / voxel_size_cm))
        }

        voxel_size_dict = {
            'x': voxel_size_cm,
            'y': voxel_size_cm,
            'z': voxel_size_cm
        }

        # Extract voxel data with padded grid
        try:
            voxel_data = roi_geometry.GetRoiGeometryAsVoxels(
                Corner=corner,
                VoxelSize=voxel_size_dict,
                NrVoxels=nr_voxels
            )
        except Exception as e:
            raise RuntimeError(f"GetRoiGeometryAsVoxels failed for roi {roi_name}: {e}")

        # Process the data
        voxel_values = np.array(voxel_data, dtype=np.uint8)
        non_zero_indices = np.flatnonzero(voxel_values == 255)

        if len(non_zero_indices) == 0:
            return np.empty((0, 3))

        # Convert to 3D coordinates
        total_xy = nr_voxels['x'] * nr_voxels['y']
        z_indices = non_zero_indices // total_xy
        y_indices = (non_zero_indices % total_xy) // nr_voxels['x']
        x_indices = non_zero_indices % nr_voxels['x']

        # Create coordinate array
        voxel_coords = np.empty((len(non_zero_indices), 3))
        corner_array = np.array([corner['x'], corner['y'], corner['z']])
        voxel_size_array = np.array([voxel_size_cm, voxel_size_cm, voxel_size_cm])

        voxel_coords[:, 0] = x_indices * voxel_size_array[0] + corner_array[0]
        voxel_coords[:, 1] = y_indices * voxel_size_array[1] + corner_array[1]
        voxel_coords[:, 2] = z_indices * voxel_size_array[2] + corner_array[2]

        return voxel_coords

    except Exception as e:
        logging.warning(f"GetRoiGeometryAsVoxels failed for {roi_name}: {e}")
        return None

