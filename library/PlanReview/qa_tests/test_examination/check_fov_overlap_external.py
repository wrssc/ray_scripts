import re
import numpy as np
from PlanReview.review_definitions import (FIELD_OF_VIEW_PREFERENCES,
PASS, FAIL, )
from .get_targets_si_extent import get_targets_si_extent
from .get_roi_list import get_roi_list


def match_roi_name(roi_names, roi_list):
    """
    Match the structures in case witht
    Args:
        roi_names: [str1, str2, ...]: list of names to search for
        roi_list: [str1, str2, ...]: list of current rois

    Returns:
        matches: [str1, str2, ...]: list of matching rois
    """
    matches = []
    for r_n in roi_names:
        exp_r_n = r'^' + r_n + r'$'
        for m in roi_list:
            if re.search(exp_r_n, m, re.IGNORECASE):
                matches.append(m)
    return matches


def get_roi_geometries(case, exam_name, roi_names):
    all_geometries = get_roi_list(case, exam_name)
    matches = match_roi_name(roi_names, all_geometries)
    matching_geometries = []
    ss = case.PatientModel.StructureSets[exam_name]
    for m in matches:
        if ss.RoiGeometries[m].HasContours():
            matching_geometries.append(ss.RoiGeometries[m])
    return matching_geometries


def make_fov(rso, fov_name, inner_fov_name):
    # FOV parameters
    # Get the reconstruction diameter which is the actual FOV
    #   grab dicom tag: 0018, 1100 'Reconstruction Diameter'
    try:
        fov_pair = rso.exam.GetStoredDicomTagValueForVerification(Group=0x0018, Element=0x1100)
        image_fov = fov_pair['Reconstruction Diameter']
    except Exception as e:  # This has been wiped in some anonymous datasets
        bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
        image_fov = bb[1].x - bb[0].x
    fov_outer = float(image_fov) / 10.  # mm-> cm
    fov_inner = float(image_fov) / 10. - 1.  # mm-> cm
    #
    # Align along z
    axis = {"x": 0, "y": 0, "z": 1}
    # Get a bounding box on the current image set for determining patient DICOM origin
    bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
    # Image length
    z_extent = bb[1]['z'] - bb[0]['z']
    center = {'x': (bb[0]['x'] + bb[1]['x']) / 2.,  # x_min + (x_max - x_min)/2
              'y': (bb[0]['y'] + bb[1]['y']) / 2.,
              'z': (bb[0]['z'] + bb[1]['z']) / 2.}
    fovs = {fov_name: fov_outer, inner_fov_name: fov_inner}
    try:
        for name, diam in fovs.items():
            rso.case.PatientModel.CreateRoi(
                Name=name,
                Color="192, 192, 192",
                Type='Undefined',
                TissueName=None,
                RbeCellTypeName=None,
                RoiMaterial=None,
            )
            rso.case.PatientModel.RegionsOfInterest[name].CreateCylinderGeometry(
                Radius=diam / 2.,  # Cylinder is half the FOV
                Axis=axis,
                Length=z_extent,
                Examination=rso.exam,
                Center=center,
                Representation="Voxels",
                VoxelSize=1)
        return True
    except:
        return False


def make_wall(rso, name, outer_name, inner_name, exp):
    fov_wall = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="192, 192, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Union',
            "SourceRoiNames": [outer_name],
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [inner_name],
            "MarginSettings": {"Type": 'Contract',
                               "Superior": exp[0],
                               "Inferior": exp[1],
                               "Anterior": exp[2],
                               "Posterior": exp[3],
                               "Right": exp[4],
                               "Left": exp[5]}
        },
        ResultOperation='Subtraction',
        ResultMarginSettings=margins,
    )
    rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=rso.exam, Algorithm="Auto"
    )


def subtract_sources(rso, name, roi_A, roi_B):
    name = rso.case.PatientModel.GetUniqueRoiName(DesiredName=name)
    wall_intersection = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="255, 080, 225",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
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
        rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
            ExpressionA={
                "Operation": 'Union',
                "SourceRoiNames": [roi_A],
                "MarginSettings": margins,
            },
            ExpressionB={
                "Operation": 'Union',
                "SourceRoiNames": [roi_B],
                "MarginSettings": margins,
            },
            ResultOperation='Subtraction',
            ResultMarginSettings=margins,
        )
        rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
            Examination=rso.exam, Algorithm="Auto"
        )
        return name
    except:
        return None


def intersect_sources(rso, name, sources):
    margins = {
        "Type": 'Expand',
        "Superior": 0,
        "Inferior": 0,
        "Anterior": 0,
        "Posterior": 0,
        "Right": 0,
        "Left": 0,
    }
    intersect = rso.case.PatientModel.CreateRoi(
        Name=name,
        Color="0, 0, 192",
        Type="Undefined",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None,
    )
    rso.case.PatientModel.RegionsOfInterest[name].SetAlgebraExpression(
        ExpressionA={
            "Operation": 'Intersection',
            "SourceRoiNames": sources,
            "MarginSettings": margins,
        },
        ExpressionB={
            "Operation": 'Union',
            "SourceRoiNames": [],
            "MarginSettings": margins,
        },
        ResultOperation='None',
        ResultMarginSettings=margins,
    )
    rso.case.PatientModel.RegionsOfInterest[name].UpdateDerivedGeometry(
        Examination=rso.exam, Algorithm="Auto"
    )
    rso.case.PatientModel.RegionsOfInterest[name].DeleteExpression()


def get_external(rso):
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            return r.Name
    return None


def check_fov_overlap_external(rso, **kwargs):
    """
           Check if the field of view overlaps on slices where the target is close by
           Args:
               rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
               target_extent: [min, max extent of target]
           Returns:
                (Pass/Fail/Alert, Message to Display)
           Test Patient:

               Pass: TODO
               Fail: TODO
    """
    target_extent = kwargs.get('TARGET_EXTENT')
    fov_name = FIELD_OF_VIEW_PREFERENCES['NAME']
    inner_fov_name = fov_name + '_Inner'
    wall_suffix = FIELD_OF_VIEW_PREFERENCES['WALL_SUFFIX']
    contraction = FIELD_OF_VIEW_PREFERENCES['CONTRACTION']
    name_intersection_roi = FIELD_OF_VIEW_PREFERENCES['NAME_INTERSECTION']
    message_str = None
    pass_result = None
    sources = [inner_fov_name]
    #
    # Find external
    ext_name = get_external(rso)
    #
    # Check if pre-existing FOV
    fov = get_roi_geometries(rso.case, rso.exam.Name, roi_names=[fov_name])
    if fov:
        fov_exists = True
    else:
        fov_exists = make_fov(rso, fov_name, inner_fov_name)
        sources.append(fov_name)
    #
    # Check initial inputs
    if not ext_name:
        pass_result = FAIL
        message_str = 'No External'
    if not fov_exists:
        pass_result = FAIL
        message_str = 'Making ' + fov_name + ' failed.'
    if not message_str:
        #
        # Build walls (sources)
        walls = [
            {'Name': fov_name + wall_suffix,
             'Outer_Source': fov_name,
             'Inner_Source': inner_fov_name,
             'In_Expand': [0.] * 6},
            {'Name': ext_name + wall_suffix,
             'Outer_Source': ext_name,
             'Inner_Source': ext_name,
             'In_Expand': [contraction] * 6},
        ]
        pm = rso.case.PatientModel
        for w in walls:
            w_name = pm.GetUniqueRoiName(DesiredName=w['Name'])
            make_wall(rso, name=w_name, outer_name=w['Outer_Source'], inner_name=w['Inner_Source'],
                      exp=w['In_Expand'])
            sources.append(w_name)
        #
        # Intersect the walls
        intersect_name = pm.GetUniqueRoiName(DesiredName=name_intersection_roi)
        intersect_sources(rso, intersect_name, sources)
        #
        # Get the extent of the targets
        if not target_extent:
            target_extent = get_targets_si_extent(rso)
        #
        # Check if any slices of the intersection are on target slices
        contours = pm.StructureSets[rso.exam.Name].RoiGeometries[
            intersect_name].PrimaryShape.Contours
        vertices = np.array([[g.x, g.y, g.z] for s in contours for g in s])
        if vertices.size > 0:
            suspect_vertices = np.where(np.logical_and(
                vertices[:, 2] > target_extent[1] - FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER'],
                vertices[:, 2] < target_extent[0] + FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']))
            suspect_slices = np.unique(vertices[suspect_vertices][:, 2])
        else:
            # No overlap of FOV and External
            suspect_slices = np.empty(shape=0)
        #
        # Clean up
        sources.append(intersect_name)
        for s in sources:
            pm.RegionsOfInterest[s].DeleteRoi()
        if suspect_slices.size > 0:
            pass_result = FAIL
            message_str = 'Potential FOV issues found on slices {}'.format(suspect_slices)
        else:
            pass_result = PASS
            message_str = 'No Potential Overlap with FOV Found'
    return pass_result, message_str

