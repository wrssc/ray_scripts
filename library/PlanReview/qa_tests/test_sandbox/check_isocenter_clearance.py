from PlanReview.review_definitions import (
    HDA_MAX_DIAMETER, ALERT, SUPPORT_TOLERANCE, TRUEBEAM_MAX_DIAMETER, PASS, FAIL)
from PlanReview.utils import subtract_roi_sources,get_roi_names_from_type

# TODO: Function that finds all possible angles in coplanar fields
#       and returns as a list rounded to ints
#       if this includes non-coplanar fields, return as a separate list
# TODO: make a function that estimates the angular size of a structure and returns
#       potential gantry locations of this structure as a list of integers


def make_clearance_diameter(rso, clearance_name, diameter, tolerance):
    """Create an ROI representing the diameter of the bore or head for clearance testing.

    Args:
        rso (NamedTuple): A tuple of ScriptObjects in RayStation [case, exam, plan, beamset, db].
        clearance_name (str): Name of the structure to create in the clearance test.
        diameter (float): Diameter of the bore or head.
        tolerance (float): Tolerance for clearance check.

    Returns:
        str: Name of the created ROI if successful, otherwise None.
    """
    #
    # Isocenter position
    iso_pos = rso.beamset.Beams[0].Isocenter.Position
    #
    # Get an unused name
    unique_name = rso.case.PatientModel.GetUniqueRoiName(DesiredName=clearance_name)
    #
    # Align along z
    axis = {"x": 0, "y": 0, "z": 1}
    # Get a bounding box on the current image set for determining patient DICOM origin
    bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
    # Image length
    try:
        idg = rso.beamset.FractionDose.InDoseGrid
        grid_z = [idg.Corner.z]
        z_extent = idg.VoxelSize.z * idg.NrVoxels.z
        grid_z.append(idg.Corner.z + z_extent)
        z_extent = 2. * max([abs(iso_pos.z - z) for z in grid_z])
    except AttributeError:
        # No dose grid! just use the image extent
        z_extent = (bb[1]['z'] - bb[0]['z']) * 2.
    try:
        rso.case.PatientModel.CreateRoi(
            Name=unique_name,
            Color="192, 192, 192",
            Type='Undefined',
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        rso.case.PatientModel.RegionsOfInterest[unique_name].CreateCylinderGeometry(
            Radius=(diameter / 2.) - tolerance,  # Radius of max permissible - tolerance
            Axis=axis,
            Length=z_extent,
            Examination=rso.exam,
            Center=iso_pos,
            Representation="Voxels",
            VoxelSize=1)
        return unique_name
    except:
        return None


def check_isocenter_clearance(rso):
    """
    Using the Bore diameters and assuming only centered couch fields check for overlap with supports
    ! Alert level for any clearance we can't verify
    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    :return: (pass_result, message_str): PASS/FAIL/ALERT, (str) message result of test

    Test Patient:
        ScriptTesting, #ZZUWQA_SCTest_21Nov2022
        PASS: Case 1 Oral_THI_R0A0
        FAIL: Case 1 Oral_T3D_R0A0, Case 2 NecL_T3D_R0A0 (fails on External only)
    """
    message_str = ''
    delete_rois = []
    violation_rois = []
    #
    # Take the first beam
    # TODO: Evaluate the structure at each couch angle in the beams
    # TODO: Determine the range of gantry movements and exclude overlap where the gantry does not
    #  travel.

    beam = rso.beamset.Beams[0]
    ss = rso.case.PatientModel.StructureSets[rso.exam.Name]
    if "Tomo" in str(beam.DeliveryTechnique):
        roi_name = "TomoTherapy bore covers"
        diameter = HDA_MAX_DIAMETER
    else:
        roi_name = "TrueBeam Head"
        diameter = TRUEBEAM_MAX_DIAMETER
    diam_name = make_clearance_diameter(rso, roi_name, diameter, tolerance=SUPPORT_TOLERANCE)
    delete_rois.append(diam_name)
    if not diam_name:
        pass_result = ALERT
        message_str += f'Unable to build the {roi_name}, no clearance test performed.'
        return pass_result, message_str
    #
    # Determine if External or any support overlaps with the expanded version of this structure
    # overlaps
    external = get_roi_names_from_type(rso, roi_type='External')[0]
    supports = get_roi_names_from_type(rso, roi_type='Support')
    rois_checked = [external] + supports
    #
    # Review rois_checked for potential overlap with bore diameter
    for r in rois_checked:
        r_overlap = r + '_overlap'
        r_overlap = subtract_roi_sources(rso, r_overlap,
                                         roi_A=r,
                                         roi_B=diam_name)
        if ss.RoiGeometries[r_overlap].HasContours():
            violation_rois.append(r)
        else:
            delete_rois.append(r_overlap)
    # Delete non-problematic contours
    for d in delete_rois:
        ss.RoiGeometries[d].OfRoi.DeleteRoi()
    if not violation_rois:
        pass_result = PASS
        message_str = f'AT COUCH ZERO: [{[external] + supports}] are ≥' \
                      + f' {SUPPORT_TOLERANCE} cm from {roi_name}'
    elif violation_rois == [external + '_overlap']:
        pass_result = ALERT
        message_str += f'{external} is ≤ {SUPPORT_TOLERANCE} cm from the {roi_name}. '
    else:
        pass_result = FAIL
        message_str += f'{violation_rois} is ≤ {SUPPORT_TOLERANCE} cm from the {roi_name}. '

    return pass_result, message_str