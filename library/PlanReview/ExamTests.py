""" Processing Functions for Patient Data

"""
import re
from dateutil import parser
import datetime
import numpy as np
import BeamSetReviewTests
from ReviewDefinitions import *


def match_date(date1, date2):
    p_date1 = p_date2 = None
    if date1:
        p_date1 = parser.parse(date1).date().strftime("%Y-%m-%d")
    if date2:
        p_date2 = parser.parse(date2).date().strftime("%Y-%m-%d")

    if p_date1 == p_date2:
        return True, p_date1, p_date2
    else:
        return False, p_date1, p_date2


def match_patient_name(name1, name2):
    # Case insensitive match on First and Last name (strip at ^)
    spl_1 = tuple(re.split(r'\^', name1))
    spl_2 = tuple(re.split(r'\^', name2))
    try:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE)) and \
                bool(re.match(re.escape(spl_1[1]), re.escape(spl_2[1]), re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2
    except IndexError:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2


def match_gender(gender1, gender2):
    # Match M/Male, F/Female, O/Other, Unknown/None
    if gender1:
        if 'Unknown' in gender1[0]:
            gender1 = None
        else:
            l1 = gender1[0]
    if gender2:
        l2 = gender2[0]
    if gender1 and gender2:
        if bool(re.match(l1, l2, re.IGNORECASE)):
            return True, gender1, gender2  # Genders Match
        else:
            return False, gender1, gender2  # Genders are different
    elif gender1:
        return False, gender1, gender2  # Genders are different
    elif gender2:
        return False, gender1, gender2  # Genders are different
    else:
        return False, gender1, gender2  # Genders not specified


def match_exactly(value1, value2):
    if value1 == value2:
        return True, value1, value2
    else:
        return False, value1, value2


def check_exam_data(rso):
    """

    Args:
        kwargs:'rso': (object): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
    # TODO: Parse date/time of birth and ignore time of birth
    """

    modality_tag = (0x0008, 0x0060)
    tags = {str(rso.patient.Name or ''): (0x0010, 0x0010, match_patient_name),
            str(rso.patient.PatientID or ''): (0x0010, 0x0020, match_exactly),
            str(rso.patient.Gender or ''): (0x0010, 0x0040, match_gender),
            str(rso.patient.DateOfBirth or ''): (0x0010, 0x0030, match_date)
            }
    get_rs_value = rso.exam.GetStoredDicomTagValueForVerification
    modality = list(get_rs_value(Group=modality_tag[0],
                                 Element=modality_tag[1]).values())[0]  # Get Modality
    message_str = "Attribute: [DICOM vs RS]"
    all_passing = True
    for k, v in tags.items():
        rs_tag = get_rs_value(Group=v[0], Element=v[1])
        for dicom_attr, dicom_val in rs_tag.items():
            match, rs, dcm = v[2](dicom_val, k)
            if match:
                message_str += "{}:[\u2713], ".format(dicom_attr)
            else:
                all_passing = False
                match_str = ' \u2260 '
                message_str += "{0}: [{1}:{2} {3} RS:{4}], " \
                    .format(dicom_attr, modality, dcm, match_str, rs)
    if all_passing:
        pass_result = 'Pass'
    else:
        pass_result = 'Fail'
    return pass_result, message_str


def compare_exam_date(rso):
    """
    Check if date occurred within tolerance
    Ideally we'll use the approval date, if not, we'll use the last saved by,
    if not we'll use right now!
    Args:
        kwargs:'rso': (object): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
    Test Patient:

        Pass (all but Gender): ZZ_RayStation^CT_Artifact, 20210408SPF
              Case 1: TB_HFS_ArtFilt: Lsha_3DC_R0A0
        Fail: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022:
              ChwL: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    tolerance = DAYS_SINCE_SIM  # Days since simulation
    dcm_data = list(rso.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020).values())
    approval_status = BeamSetReviewTests.approval_info(rso.plan, rso.beamset)
    if dcm_data:
        dcm_date = parser.parse(dcm_data[0])
        #
        if approval_status.beamset_approved:
            current_time = parser.parse(str(rso.beamset.Review.ReviewTime))
        else:
            try:
                # Use last saved date if plan not approved
                current_time = parser.parse(str(rso.beamset.ModificationInfo.ModificationTime))
            except AttributeError:
                current_time = datetime.datetime.now()

        elapsed_days = (current_time - dcm_date).days

        if elapsed_days <= tolerance:
            message_str = "Exam {} acquired {} within {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Pass"
        else:
            message_str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = "Fail"
    else:
        message_str = "Exam {} has no apparent study date!".format(rso.exam.Name)
        pass_result = "Alert"
    return pass_result, message_str


def get_targets_si_extent(rso):
    types = ['Ptv']
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    extent = [-1000., 1000]
    for r in rg:
        if r.OfRoi.Type in types and r.HasContours():
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    return extent


def get_si_extent(rso, types=None, roi_list=None):
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    initial = [-1000, 1000]
    extent = [-1000, 1000]
    # Generate a list to search
    type_list = []
    rois = []
    if types:
        type_list = [r.OfRoi.Name for r in rg if r.OfRoi.Type in types and r.HasContours()]
    if roi_list:
        rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in roi_list and r.HasContours()]
    check_list = list(set(type_list + rois))

    for r in rg:
        if r.OfRoi.Name in check_list:
            bb = r.GetBoundingBox()
            rg_max = bb[0]['z']
            rg_min = bb[1]['z']
            if rg_max > extent[0]:
                extent[0] = rg_max
            if rg_min < extent[1]:
                extent[1] = rg_min
    if extent == initial:
        return None
    else:
        return extent


def image_extent_sufficient(rso, **kwargs):
    """
    Check if the image extent is long enough to cover the image set and a buffer

    Args:
        kwargs:'rso': (object): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
    Test Patient:

        Pass TODO
        Fail: TODO
    """
    #
    # Target length
    target_extent = kwargs.get('TARGET_EXTENT')
    #
    # Tolerance for SI extent
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    #
    # Get image slices
    bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
    bb_z = [bb[0]['z'], bb[1]['z']]
    z_extent = [min(bb_z), max(bb_z)]
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    #
    # Nice strings for output
    z_str = '[' + ('%.2f ' * len(z_extent)) % tuple(z_extent) + ']'
    t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not target_extent:
        message_str = 'No targets found of type Ptv, image extent could not be evaluated'
        pass_result = 'Fail'
    elif z_extent[1] >= buffered_target_extent[1] and z_extent[0] <= buffered_target_extent[0]:
        message_str = 'Planning image extent {} and is at least {:.1f} larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = "Pass"
    elif z_extent[1] < buffered_target_extent[1] or z_extent[0] > buffered_target_extent[0]:
        message_str = 'Planning Image extent:{} is insufficient for accurate calculation.'.format(z_str) \
                      + '(SMALLER THAN :w' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = "Fail"
    else:
        message_str = 'Target length could not be compared to image set'
        pass_result = "Fail"
    return pass_result, message_str


def couch_extent_sufficient(rso, **kwargs):
    """
       Check PTV volume extent have supports under them
       Args:
           parent_key:
           rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
           target_extent: [min, max extent of target]
       Returns:
            (Pass/Fail/Alert, Message to Display)
       Test Patient:

           Pass: Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Anal_THI: Anal_THI
           Fail (bad couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: ChwL_3DC: SCV PAB
           Fail (no couch): Plan_Review_Script_Testing, ZZUWQA_SCTest_01May2022
                 Case THI: Pros_VMA: Pros_VMA
       """
    target_extent = kwargs.get('TARGET_EXTENT')
    buffer = FIELD_OF_VIEW_PREFERENCES['SI_PTV_BUFFER']
    #
    # Get support structure extent
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    supports = TOMO_DATA['SUPPORTS'] + TRUEBEAM_DATA['SUPPORTS']
    support_rois = [r.OfRoi.Name for r in rg if r.OfRoi.Name in supports]
    couch_extent = get_si_extent(rso=rso, roi_list=supports)

    if couch_extent:
        # Nice strings for output
        z_str = '[' + ('%.2f ' * len(couch_extent)) % tuple(couch_extent) + ']'
    #
    # Tolerance for SI extent
    buffered_target_extent = [target_extent[0] - buffer, target_extent[1] + buffer]
    if target_extent:
        # Output string
        t_str = '[' + ('%.2f ' * len(buffered_target_extent)) % tuple(buffered_target_extent) + ']'
    if not couch_extent:
        message_str = 'No support structures found. No couch check possible'
        pass_result = "Fail"
    elif couch_extent[1] >= buffered_target_extent[1] and couch_extent[0] <= buffered_target_extent[0]:
        message_str = 'Supports (' \
                      + ', '.join(support_rois) \
                      + ') span {} and is at least {:.1f} cm larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = "Pass"
    elif couch_extent[1] < buffered_target_extent[1] or couch_extent[0] > buffered_target_extent[0]:
        message_str = 'Support extent (' \
                      + ', '.join(support_rois) \
                      + ') :{} is not fully under the target.'.format(z_str) \
                      + '(SMALLER THAN ' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = "Fail"
    else:
        message_str = 'Target length could not be compared to support extent'
        pass_result = "Fail"
    # Prepare output
    return pass_result, message_str


def get_external(rso):
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            return r.Name
    return None


# CONTOUR CHECKS
def get_roi_list(case, exam_name=None):
    """
    Get a list of all rois
    Args:
        case: RS case object

    Returns:
        roi_list: [str1,str2,...]: a list of roi names
    """
    roi_list = []
    if exam_name:
        structure_sets = [case.PatientModel.StructureSets[exam_name]]
    else:
        structure_sets = [s for s in case.PatientModel.StructureSets]

    for s in structure_sets:
        for r in s.RoiGeometries:
            if r.OfRoi.Name not in roi_list:
                roi_list.append(r.OfRoi.Name)
    return roi_list


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
    fov_pair = rso.exam.GetStoredDicomTagValueForVerification(Group=0x0018, Element=0x1100)
    image_fov = fov_pair['Reconstruction Diameter']
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


def external_overlaps_fov(rso, **kwargs):
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
        pass_result = "Fail"
        message_str = 'No External'
    if not fov_exists:
        pass_result = "Fail"
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
            make_wall(rso, name=w_name, outer_name=w['Outer_Source'], inner_name=w['Inner_Source'], exp=w['In_Expand'])
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
        contours = pm.StructureSets[rso.exam.Name].RoiGeometries[intersect_name].PrimaryShape.Contours
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
            pass_result = "Fail"
            message_str = 'Potential FOV issues found on slices {}'.format(suspect_slices)
        else:
            pass_result = "Pass"
            message_str = 'No Potential Overlap with FOV Found'
    return pass_result, message_str


def check_localization(rso):
    poi_coord = {}
    localization_found = False
    for p in rso.case.PatientModel.StructureSets[rso.exam.Name].PoiGeometries:
        if p.OfPoi.Type == 'LocalizationPoint':
            point = p
            poi_coord = p.Point
            localization_found = True
            break
    if poi_coord:
        message_str = "Localization point {} exists and has coordinates.".format(point.OfPoi.Name)
        pass_result = "Pass"
    elif localization_found:
        message_str = "Localization point {} does not have coordinates.".format(point.OfPoi.Name)
        pass_result = "Fail"
    else:
        message_str = "No point of type LocalizationPoint found"
        pass_result = "Fail"
    return pass_result, message_str


def match_image_directions(rso):
    # Match the directions that a correctly oriented image should have
    stack_details = {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                     'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                     'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}}
    col_dir = rso.exam.Series[0].ImageStack.ColumnDirection
    row_dir = rso.exam.Series[0].ImageStack.RowDirection
    sli_dir = rso.exam.Series[0].ImageStack.SliceDirection
    message_str = ""
    pass_result = 'Pass'
    if col_dir != stack_details['direction_column'] or \
            sli_dir != stack_details['direction_slice']:
        message_str.append('Exam {} has been rotated and will not transfer to iDMS!'.format(rso.exam.Name))
        pass_result = 'Fail'
    if row_dir != stack_details['direction_row']:
        message_str.append('Exam {} has been rotated or was acquired'.format(rso.exam.Name)
                           + ' with gantry tilt and should be reoriented!')
        pass_result = 'Fail'
    if not message_str:
        message_str = 'Image set {} is not rotated'.format(rso.exam.Name)

    return pass_result, message_str
