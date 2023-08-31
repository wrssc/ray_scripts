""" Processing Functions for Patient Data

"""
import re
import math
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
    Checks the RayStation plan information versus the native CT DICOM header.
    Patient Name match is a case insensitive comparison excluding middle name
    Gender match on M/F/O vs M/F/O/Unknown/None
    Date of birth match by using parser to pull a Y/M/D date ignoring time
    PatientID is an exact match (string equality)
    Args:
        kwargs:'rso': (object): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
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
    message_str = "[DICOM vs RS]: "
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
        pass_result = PASS
    else:
        pass_result = FAIL
    return pass_result, message_str


def compare_exam_date(rso):
    """
    Check if examination date occurred within tolerance set by DAYS_SINCE_SIM
    First it checks for a RayStation approval date, then we'll use the last saved by,
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
        try:
            dcm_date = parser.parse(dcm_data[0])
        except TypeError:
            DEFAULT_DATE = datetime.datetime(datetime.MINYEAR, 1, 1)
            dcm_date = parser.parse(str(DEFAULT_DATE))
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
            pass_result = PASS
        else:
            message_str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days, current_time.date())
            pass_result = FAIL
    else:
        message_str = "Exam {} has no apparent study date!".format(rso.exam.Name)
        pass_result = ALERT
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
        pass_result = FAIL
    elif z_extent[1] >= buffered_target_extent[1] and z_extent[0] <= buffered_target_extent[0]:
        message_str = 'Planning image extent {} and is at least {:.1f} larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = PASS
    elif z_extent[1] < buffered_target_extent[1] or z_extent[0] > buffered_target_extent[0]:
        message_str = 'Planning Image extent:{} is insufficient for accurate calculation.'.format(z_str) \
                      + '(SMALLER THAN :w' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = FAIL
    else:
        message_str = 'Target length could not be compared to image set'
        pass_result = FAIL
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
        pass_result = FAIL
    elif couch_extent[1] >= buffered_target_extent[1] and couch_extent[0] <= buffered_target_extent[0]:
        message_str = 'Supports (' \
                      + ', '.join(support_rois) \
                      + ') span {} and is at least {:.1f} cm larger than S/I target extent {}'.format(
            z_str, buffer, t_str)
        pass_result = PASS
    elif couch_extent[1] < buffered_target_extent[1] or couch_extent[0] > buffered_target_extent[0]:
        message_str = 'Support extent (' \
                      + ', '.join(support_rois) \
                      + ') :{} is not fully under the target.'.format(z_str) \
                      + '(SMALLER THAN ' \
                        'than S/I target extent: {} \xB1 {:.1f} cm)'.format(t_str, buffer)
        pass_result = FAIL
    else:
        message_str = 'Target length could not be compared to support extent'
        pass_result = FAIL
    # Prepare output
    return pass_result, message_str


def get_external(rso):
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            return r.Name
    return None


def get_supports(rso):
    supports = []
    for r in rso.case.PatientModel.RegionsOfInterest:
        if r.Type == 'Support':
            supports.append(r.Name)
    return supports


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
    try:
        fov_pair = rso.exam.GetStoredDicomTagValueForVerification(Group=0x0018, Element=0x1100)
        image_fov = fov_pair['Reconstruction Diameter']
    except Exception as e:  # This has been wiped in some anonymous datasets
        bb = rso.exam.Series[0].ImageStack.GetBoundingBox()
        image_fov = bb[1].x - bb[0].x
    fov_outer = float(image_fov) / 10.  # mm-> cm
    fov_inner = float(image_fov) / 10. - 2.  # mm-> cm
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
    exclude_from_export = []
    to_delete = [inner_fov_name]
    sources = []
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
        to_delete.append(fov_name)
        exclude_from_export.append(fov_name)
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
            make_wall(rso, name=w_name, outer_name=w['Outer_Source'], inner_name=w['Inner_Source'], exp=w['In_Expand'])
            sources.append(w_name)
            to_delete.append(w_name)
            exclude_from_export.append(w_name)
        #
        # Intersect the walls
        intersect_name = pm.GetUniqueRoiName(DesiredName=name_intersection_roi)
        intersect_sources(rso, intersect_name, sources)
        exclude_from_export.append(intersect_name)
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
        for e in exclude_from_export:
            try:
                rso.case.PatientModel.ToggleExcludeFromExport(ExcludeFromExport=True,
                                                              RegionOfInterests=[e],
                                                              PointsOfInterests=[])
            except:
                pass
        to_delete.append(intersect_name)

        for s in to_delete:
            pm.RegionsOfInterest[s].DeleteRoi()
        if suspect_slices.size > 0:
            pass_result = FAIL
            message_str = 'Potential FOV issues found on slices {}'.format(suspect_slices)
        else:
            pass_result = PASS
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
        pass_result = PASS
    elif localization_found:
        message_str = "Localization point {} does not have coordinates.".format(point.OfPoi.Name)
        pass_result = FAIL
    else:
        message_str = "No point of type LocalizationPoint found"
        pass_result = FAIL
    return pass_result, message_str


def find_nearest(array, values):
    # Finds the nearest values of the numpy array values in the array, array
    array = np.asarray(array)
    idx = [(np.abs(array - v)).argmin() for v in values]
    return array[idx]


def check_support_material(rso):
    """
    For the list of accepted supports defined in ReviewDefinitions.py->Materials
    assure the correct material name has been assigned
    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]

    :return: message (list str): [Pass_Status, Message String]
    """
    rois = get_roi_list(rso.case)
    message_str = ""
    correct_supports = []
    for r in rois:
        try:
            correct_material_name = MATERIALS[r]
        except KeyError:
            continue
        try:
            material_name = rso.case.PatientModel.RegionsOfInterest[r].RoiMaterial.OfMaterial.Name
            if material_name != correct_material_name:
                message_str += r + ' incorrectly assigned as ' + material_name
            else:
                correct_supports.append(r)
        except AttributeError:
            message_str += r + ' not overriden! '
    if message_str:
        pass_result = FAIL
    else:
        pass_result = PASS
        if correct_supports:
            message_str = "Supports [" + ",".join(correct_supports) + "] Correctly overriden"
        else:
            message_str = "No supports found"
    return pass_result, message_str


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


def extract_grid(rg, bb, voxel_size, slice_positions):
    """
    Resample the roi geometry (rg) of an roi onto a grid defined by that roi's bounding box
    Returns a 3D array of the roi resampled onto a grid,
    the values of the returned array are 0-255 depending on how much of that voxel is covered by the roi
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
                'NrVoxels': {'x': int(math.ceil(bb[1]['x'] - bb[0]['x']) / voxel_size['x']),
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
    Look for S/I discontinuties in all rois that have contours and are not derived by resampling
    the roi
    onto a small grid and looking for empty slices
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


def match_image_directions(rso):
    # Match the directions that a correctly oriented image should have
    patient_position = str(rso.exam.PatientPosition)

    stack_details = {
        'FFDL': {'direction_column': {'x': int(1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(-1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFDR': {'direction_column': {'x': int(-1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFP': {'direction_column': {'x': int(0), 'y': int(-1), 'z': int(0)},
                'direction_row': {'x': int(-1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'FFS': {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFS': {'direction_column': {'x': int(0), 'y': int(1), 'z': int(0)},
                'direction_row': {'x': int(1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFDL': {'direction_column': {'x': int(1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(-1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFDR': {'direction_column': {'x': int(-1), 'y': int(0), 'z': int(0)},
                 'direction_row': {'x': int(0), 'y': int(1), 'z': int(0)},
                 'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
        'HFP': {'direction_column': {'x': int(0), 'y': int(-1), 'z': int(0)},
                'direction_row': {'x': int(-1), 'y': int(0), 'z': int(0)},
                'direction_slice': {'x': int(0), 'y': int(0), 'z': int(1)}},
    }
    col_dir = rso.exam.Series[0].ImageStack.ColumnDirection
    row_dir = rso.exam.Series[0].ImageStack.RowDirection
    sli_dir = rso.exam.Series[0].ImageStack.SliceDirection
    message_str = ""
    pass_result = PASS
    if col_dir != stack_details[patient_position]['direction_column'] or \
            sli_dir != stack_details[patient_position]['direction_slice']:
        message_str += f"Exam {rso.exam.Name} has been rotated and will not transfer to iDMS!"
        pass_result = FAIL
    if row_dir != stack_details[patient_position]['direction_row']:
        message_str += f"Exam {rso.exam.Name} has been rotated or was acquired" \
                       + " with gantry tilt and should be reoriented!"
        pass_result = FAIL
    if not message_str:
        message_str = 'Image set {} is not rotated'.format(rso.exam.Name)

    return pass_result, message_str


def exists_roi(case, rois, return_exists=False):
    """See if rois is in the list
    If return_exists is True return the names of the existing rois,
    If it is False, return a boolean list of each structure's existence
    """
    if type(rois) is not list:
        rois = [rois]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    roi_exists = []

    for r in rois:
        pattern = r"^" + r + "$"
        if any(
                re.match(pattern, current_roi, re.IGNORECASE)
                for current_roi in defined_rois
        ):
            if return_exists:
                roi_exists.append(r)
            else:
                roi_exists.append(True)
        else:
            if not return_exists:
                roi_exists.append(False)

    return roi_exists


def case_insensitive_structure_search(case, structure_name, roi_list=None):
    """
    Check if a case insensitive match to the structure_name exists and
    return the name or None
    :param case: raystation case
    :param structure_name:structure name to be tested
    :param roi_list: list of rois to look in, if not specified, use all rois
    :return: list of names defined in RayStation, if only one structure is found return a string
             or [] if no match was found.
    """
    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r.OfRoi.Name not in roi_list:
                    roi_list.append(r.OfRoi.Name)

    matched_rois = []
    for current_roi in roi_list:
        if re.search(r"^" + structure_name + "$", current_roi, re.IGNORECASE):
            if not re.search(r"^" + structure_name + "$", current_roi):
                matched_rois.append(current_roi)
    if len(matched_rois) == 1:
        matched_rois = matched_rois[0]
    return matched_rois


def check_structure_exists(
        case, structure_name, roi_list=None,
        option="Check", exam=None):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: a list of available ROIs as RS RoiGeometries to check
                     against
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
        Wait - prompt user to create structure if not found
    :param exam: Current RS exam, if supplied the script deletes geometry only,
                 otherwise contour is deleted
    :return: Logical - True if structure is present in ROI List,
                       False otherwise
    """

    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r not in roi_list:
                    roi_list.append(r)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if exam is not None:
            structure_has_contours_on_exam = (
                case.PatientModel.StructureSets[exam.Name]
                    .RoiGeometries[structure_name]
                    .HasContours()
            )
        else:
            structure_has_contours_on_exam = False

        if option == "Delete":
            if structure_has_contours_on_exam:
                case.PatientModel.StructureSets[exam.Name].RoiGeometries[
                    structure_name
                ].DeleteGeometry()
                return False
            else:
                case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
                return True
        elif option == "Check":
            if exam is not None and structure_has_contours_on_exam:
                # logging.info("Structure {} has contours on exam {}".format(structure_name, exam.Name))
                return True
            elif exam is not None:
                # logging.info("Structure {} has no contours on exam {}".format(structure_name, exam.Name))
                return False
            else:
                # logging.info("Structure {} exists in this Case {}".format(structure_name, case.Name))
                return True
        elif option == "Wait":
            if structure_has_contours_on_exam:
                # logging.info("Structure {} has contours on exam {}".format(structure_name, exam.Name))
                return True
            else:
                connect.await_user_input("Create the structure {} and continue script."
                                         .format(structure_name))
    else:
        return False


def structure_approved(case, roi_name, examination=None):
    """
    Check if structure is approved anywhere in this patient, if an exam is supplied
    only the exam supplied is checked for the approved contour
    :param case: RS case
    :param roi_name: string containing name of roi
    :param examination: RS examination object
    :return: True if structure is approved somewhere
    """
    struct_exists = exists_roi(case=case, rois=roi_name)
    # If the structure is undefined, then is is not approved
    if not struct_exists:
        return False
    else:
        for s in case.PatientModel.StructureSets:
            if examination is not None and s.OnExamination.Name != examination.Name:
                continue
            else:
                for a in s.SubStructureSets:
                    try:
                        if a.Review.ApprovalStatus == 'Approved':
                            for r in a.RoiStuctures:
                                if r.OfRoi.Name == roi_name:
                                    return True
                    except AttributeError:
                        continue
        return False


def create_roi(case, examination, roi_name, delete_existing=None, suffix=None):
    """
    Thoughtful creation of structures that can determine if the structure exists,
    determine the geometry exists on this examination
    -Create it with a suffix if the geometry exists and is locked on the current examination
    Is the structure name already in use?
        *<No>  -> Make it and return the RoiGeometry on this examination
        *<Yes> Are there contours defined for roi_name in this case?
            **<No> -> return the RoiGeometry on this examination
            **<Yes> Is the geometry approved somewhere in the case?
                ***<No> Either delete it (delete_existing), or prompt the user to decide to delete or supply a suffix
                ***<Yes> Is the geometry approved on this exam?
                    ****<No> -> Either delete it (delete_existing),
                                or append a supplied or default suffix
                    ****<Yes> -> Return None (delete_existing),
                                 or append a supplied or default suffix
    :param case:
    :param examination:
    :param roi_name: string containing name of roi to be created
    :param delete_existing: delete any existing roi with name roi_name so long as it isn't approved
    :param suffix: append the suffix string to the name of a contour
    :return: new_structure_name: the RoiGeometries object of roi_name or its suffix-modified name
    """
    # First we want to work with the case insensitive match to the structure name supplied
    roi_name_ci = case_insensitive_structure_search(case=case, structure_name=roi_name)
    # Convert this from a list to an individual structure
    roi_name_exists = check_structure_exists(
        case=case, option="Check", structure_name=roi_name
    )
    # struct_exists is true if the roi_name is already defined
    if roi_name_ci:
        struct_exists = True
    elif roi_name_exists:
        roi_name_ci = roi_name
        struct_exists = True
    else:
        roi_name_ci = roi_name
        struct_exists = False

    # geometry_exists_in_case is True if any examination
    # in this case has contours for this roi_name_ci
    geometry_exists_in_case = check_structure_exists(
        case=case, structure_name=roi_name_ci, option="Check"
    )
    # geometry_exists is True if this examination has contours
    geometry_exists = check_structure_exists(
        case=case, structure_name=roi_name_ci, option="Check", exam=examination
    )
    # Look through all structure sets in the patient to see if
    # roi name is approved on an exam in this patient
    geometry_approved = structure_approved(
        case=case, roi_name=roi_name_ci, examination=examination
    )
    # If the call has been made without a suffix or deletion instructions, prompt user.
    if delete_existing is None and suffix is None:
        if geometry_exists and not geometry_approved:
            # Prompt the user to make a decision between deleting existing geometry and a suffix
            suffix = dialog_create_roi()
            if suffix is None:
                delete_existing = True
            else:
                delete_existing = False

    if struct_exists:
        # Does the existing structure have any contours defined
        if geometry_exists_in_case:
            # Are the existing contours on this exam?
            if geometry_exists:
                # Is the existing geometry approved?
                if geometry_approved:
                    # TODO if delete_existing is selected, prompt the user to unapprove or quit
                    if delete_existing:
                        # Delete the existing geometry and return
                        # the empty geometry on the current exam
                        return None
                    else:
                        # We can't delete the existing approved geometry, so we'll need to append
                        i = 0
                        if suffix is None:
                            suffix = "_R"
                        updated_roi_name = roi_name + suffix + str(i)
                        while any(exists_roi(case=case, rois=updated_roi_name)):
                            i += 1
                            updated_roi_name = roi_name + suffix + str(i)
                        # Make a new roi using the updated name
                        case.PatientModel.CreateRoi(Name=updated_roi_name)
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[updated_roi_name]
                else:
                    # The geometry is not approved on this examination
                    if delete_existing:
                        # Delete the existing geometry and return
                        # the empty geometry on the current exam
                        case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                            roi_name_ci
                        ].DeleteGeometry
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[roi_name_ci]
                    else:
                        # We don't want to delete the existing geometry, so we'll need to append
                        if suffix is None:
                            suffix = "_R"
                        i = 1
                        updated_roi_name = roi_name + suffix + str(i)
                        while any(exists_roi(case=case, rois=updated_roi_name)):
                            logging.debug(
                                "Roi {} found in list. Checking next available.".format(
                                    updated_roi_name
                                )
                            )
                            i += 1
                            updated_roi_name = roi_name + suffix + str(i)
                        # Make a new roi using the updated name
                        case.PatientModel.CreateRoi(Name=updated_roi_name)
                        return case.PatientModel.StructureSets[
                            examination.Name
                        ].RoiGeometries[updated_roi_name]
            else:
                # Geometry exists but not on the current exam,
                # return the empty geometry on the current exam
                return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                    roi_name_ci
                ]
        else:
            # The existing structure is empty on all exams,
            # return the empty geometry on the current exam
            return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
                roi_name_ci
            ]
    else:
        # The roi does not exist, so make it and return the empty geometry for this exam
        case.PatientModel.CreateRoi(Name=roi_name_ci)
        return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
            roi_name_ci
        ]


def make_high_z(case, exam, desired_name):
    threshold = 3025  # Highest HU value on the scanner
    # Redraw the ExternalClean structure if necessary
    if check_structure_exists(
            case=case,
            structure_name=desired_name,
            exam=exam,
            option="Check"):
        roi_geom = case.PatientModel.StructureSets[exam.Name].RoiGeometries[
            desired_name]
    else:
        roi_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=desired_name,
            delete_existing=False,
            suffix="",
        )
    if not roi_geom.HasContours():
        roi_geom.GrayLevelThreshold(Examination=exam,
                                    LowThreshold=int(0.9 * threshold),
                                    HighThreshold=threshold,
                                    PetUnit="",
                                    CbctUnit=None,
                                    BoundingBox=None)
