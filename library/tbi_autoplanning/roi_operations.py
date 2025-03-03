# poi_roi_operations.py
import logging
from typing import Optional, List
from collections import namedtuple
from library.StructureOperations import (
    create_roi, create_poi, change_roi_type, make_boolean_structure,
    find_types, exclude_from_export)
from .tbi_definitions import (LUNGS, LUNG_AVOID_NAME, LUNG_AVOID_MARGIN,
                              LUNGS_EVAL_NAME, LUNGS_EVAL_MARGIN,
                              KIDNEYS, KIDNEY_AVOID_NAME, KIDNEY_AVOID_MARGIN,
                              AVOID_FFS_NAME, AVOID_HFS_NAME, SKIN_AVOIDANCE,
                              FFS_TARGET_EVAL_NAME, HFS_TARGET_EVAL_NAME,
                              COLORS)


def get_roi_geometry(case, exam, roi_name):
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


# ROI Existence and basic checks
def roi_in_list(case, structure_name, roi_list=None):
    if not roi_list:
        roi_obj_list = [r for r in case.PatientModel.RegionsOfInterest]
    else:
        roi_obj_list = []
        for n in roi_list:
            roi_obj_list += [r for r in case.PatientModel.RegionsOfInterest
                             if r.Name == n]

    if any(roi.Name == structure_name for roi in roi_obj_list):
        return True
    else:
        return False


def poi_in_list(case, poi_name, poi_list=None):
    if not poi_list:
        poi_obj_list = [p for p in case.PatientModel.PointsOfInterest]
    else:
        poi_obj_list = []
        for n in poi_list:
            poi_obj_list += [p for p in case.PatientModel.PointsOfInterest
                             if p.Name == n]

    if any(poi.Name == poi_name for poi in poi_obj_list):
        return True
    else:
        return False


def roi_has_contours(patient_data, structure_name):
    logging.debug(f'Checking for contours in {patient_data.case.CaseName} for {structure_name}')
    if roi_in_list(patient_data.case, structure_name):
        roi_geom = get_roi_geometry(patient_data.case, patient_data.exam, structure_name)
        logging.debug(f'ROI {structure_name} has contours: {roi_geom.HasContours()}')
        if roi_geom.HasContours():
            return True
    return False


def find_roi_prefix(case, roi_match):
    # Return all structures whose name contains roi_prefix
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_match in r.Name:
            found_roi.append(r.Name)
    return found_roi


def toggle_ptv_type(rs_obj, rois, roi_type):
    # Sometimes in the course of RayStation planning, we need to change our type
    # 'cause of stupid dose grids.
    for r in rois:
        change_roi_type(rs_obj.case, roi_name=r, roi_type=roi_type)


def validate_poi_name(poi_name):
    """
    Validate the format of the POI name. The last character should be an integer.

    Args:
        poi_name (str): The name of the POI.

    Returns:
        int: The integer at the end of the POI name.
    """
    try:
        return int(poi_name[-1])
    except ValueError:
        logging.error(f'Error: The name of the POI {poi_name} '
                      'does not contain an integer in the last digit.')
        raise ValueError(f'Error: The name of the POI {poi_name} does not '
                         'contain an integer in the last digit.')


# =================================================================
# ROI Creation and Deletion
# =================================================================
def delete_roi(case, structure_name):
    if roi_in_list(case, structure_name):
        try:
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            return True
        except Exception as e:
            logging.warning(f'Could not delete {structure_name}: {e}')
            return False
    else:
        return True


def copy_roi(pdata, roi_name):
    copy_roi_name = pdata.case.PatientModel.GetUniqueRoiName(DesiredName=f'{roi_name}_copy')
    _ = create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=copy_roi_name,
    )
    roi_defs = get_boolean_defs(
        roi_name=copy_roi_name,
        a_sources=[roi_name],
        a_operation="Intersection",
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **roi_defs)
    # Update derived status and delete derivation
    update_all_remove_expression(pdata, roi_name=copy_roi_name)

    return copy_roi_name




# =================================================================
# Derived roi updates and copying
# =================================================================
def update_all_remove_expression(pdata, roi_name):
    # Update the expression for a contour on all exams then remove expression
    for e in pdata.case.PatientModel.StructureSets:
        try:
            pdata.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
                Examination=pdata.case.Examinations[e.OnExamination.Name],
                Algorithm="Auto"
            )
        except Exception as err:
            logging.debug(f'Error in updating geometry for {roi_name}: {err}')

    try:
        pdata.case.PatientModel.RegionsOfInterest[roi_name].DeleteExpression()
    except Exception as err:
        logging.debug(f'Error in eliminating derived for {roi_name}: {err}')
        pass


def check_list(var, length, element_type, default):
    """
    Check if a variable is a list of a certain length and type.

    :param var: Variable to be checked.
    :param length: Desired length of the list.
    :param element_type: Desired type of list elements.
    :param default: Default value to be returned if the check fails.
    :return: The variable if it passes the check, otherwise the default value.
    """
    if isinstance(var, list) and len(var) == length \
            and all(isinstance(c, element_type) for c in var):
        return var
    else:
        return default


def get_boolean_defs(
        roi_name, a_sources, a_operation, a_exp=None, a_margin_type="Expand",
        b_sources=None, b_operation="Union", b_exp=None, b_margin_type="Expand",
        r_exp=None, r_margin_type="Expand", result="None",
        color=None, export=False, visualize=False, roi_type="Undefined"
):
    """
    Returns a dictionary with Boolean structure definitions.

    Parameters are structure properties and have default values.
    If an argument is not provided, the default value is used.

    :param roi_name: Name of the ROI.
    :param a_sources: List of sources for Operation A.
    :param a_operation: Operation A.
    :param a_exp: Expansion parameters for Operation A. Default is [0]*6.
    :param a_margin_type: Margin type for Operation A. Default is "Expand".
    :param b_sources: List of sources for Operation B. Default is None (equivalent to empty list).
    :param b_operation: Operation B. Default is "Union".
    :param b_exp: Expansion parameters for Operation B. Default is [0]*6.
    :param b_margin_type: Margin type for Operation B. Default is "Expand".
    :param r_exp: Expansion parameters for Resulting operation. Default is [0]*6.
    :param r_margin_type: Margin type for Resulting operation. Default is "Expand".
    :param result: Result of A/B  None, Intersection, Subtraction. Default is None
    :param color: List representing the color of the structure. Default is [192, 192, 192].
    :param export: Boolean to indicate if the structure should be
                   excluded from export. Default is False.
    :param visualize: Boolean to indicate if the structure should be visualized. Default is False.
    :param roi_type: Type of the structure. Default is "Unknown".
    :return: Dictionary with Boolean structure definitions.
    """

    a_exp = check_list(a_exp, 6, float, [0] * 6)
    b_sources = b_sources if b_sources is not None else []
    b_exp = check_list(b_exp, 6, float, [0] * 6)
    r_exp = check_list(r_exp, 6, float, [0] * 6)
    color = check_list(color, 3, int, [192, 192, 192])

    definitions = {
        "StructureName": roi_name,
        "ExcludeFromExport": not export,
        "VisualizeStructure": visualize,
        "StructColor": color,
        "OperationA": a_operation,
        "SourcesA": a_sources,
        "MarginTypeA": a_margin_type,
        "ExpA": a_exp,
        "SourcesB": b_sources,
        "OperationB": b_operation,
        "MarginTypeB": b_margin_type,
        "ExpB": b_exp,
        "MarginTypeR": r_margin_type,
        "ExpR": r_exp,
        "OperationResult": result,
        "StructType": roi_type,
    }

    return definitions


def volume_threshold_roi(patient_data, roi_name, min_vol=1., max_vol=1.e6):
    if roi_in_list(patient_data.case, roi_name):
        if roi_has_contours(patient_data, roi_name):
            roi = patient_data.case.PatientModel.RegionsOfInterest[roi_name]
            try:
                roi.VolumeThreshold(
                    InputRoi=roi,
                    Examination=patient_data.exam,
                    MinVolume=min_vol,
                    MaxVolume=max_vol
                )
                if roi_has_contours(patient_data, roi_name):
                    return True
                else:
                    logging.warning(f'Volume thresholding of roi {roi_name} '
                                    f'With Volume MIN/MAX {min_vol}/{max_vol}'
                                    f'Resulted in empty contour')
                    return False
            except Exception as e:
                logging.warning(f'Unable to perform volume thresholding for '
                                f'{roi_name}: {e}')
                return False
        else:
            logging.debug(f'Unable to threshold {roi_name} due to no contours')
            return False
    else:
        logging.debug(f'Unable to threshold {roi_name}: roi not found')
        return False


def subtract_b_from_a(pdata, a_list, b_list, result_name):
    # Check for circular references
    if result_name in a_list:
        copy_result_name = copy_roi(pdata, result_name)
        # Modify the a_list to use the copied roi
        a_list[a_list.index(result_name)] = copy_result_name
    else:
        copy_result_name = None

    roi_defs = get_boolean_defs(
        roi_name=result_name,
        a_sources=a_list,
        a_operation="Intersection",
        b_sources=b_list,
        b_operation="Union",
        r_exp=[0.00] * 6,
        r_margin_type="Expand",
        result="Subtraction",
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case,
        examination=pdata.exam, **roi_defs)
    try:
        pdata.case.PatientModel.RegionsOfInterest[result_name].UpdateDerivedGeometry(
            Examination=pdata.case.Examinations[pdata.exam.OnExamination.Name],
            Algorithm="Auto"
        )
    except Exception as err:
        logging.debug(f'Error in updating geometry for {result_name}: {err}')

    if copy_result_name:
        pdata.case.PatientModel.RegionsOfInterest[copy_result_name].DeleteRoi()

    return result_name


# =================================================================
# Generic Shape Creation & Composite ROI Builders
# =================================================================
def make_box(patient_data, box_name, length=None, z_center=None):
    case = patient_data.case
    exam = patient_data.exam
    patient_model = case.PatientModel
    #
    # Get the Bounding box of the External contour
    external_name = find_types(case, roi_type='External')[0]
    bb_external = patient_model.StructureSets[exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(patient_data, roi_name=external_name)
    z_center = c_external['z'] if z_center is None else z_center
    length = bb_external[1].z - bb_external[0].z if length is None else length
    if length > 200:
        # Need to make multiple boxes
        n_box = int(length / 200)
        box_length = length / n_box
    else:
        n_box = 1
        box_length = length
    logging.debug(f'Measured length of external contour: {bb_external[1].z - bb_external[0].z}')
    logging.debug(f'Building a box with length {length} centered at {z_center}')
    delete_boxes = []
    for i in range(n_box):
        # Create the box
        box_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=box_name + f'_{i}' if n_box > 1 else box_name,
            delete_existing=True)
        z_center = z_center + i * box_length
        box_geom.OfRoi.CreateBoxGeometry(
            Size={'x': abs(bb_external[1].x - bb_external[0].x) + 2,
                  'y': abs(bb_external[1].y - bb_external[0].y) + 2,
                  'z': box_length},
            Examination=patient_data.exam,
            Center={'x': c_external['x'],
                    'y': c_external['y'],
                    'z': z_center},
            Representation='Voxels',
            VoxelSize=None)
        delete_boxes.append(box_name + f'_{i}')
    if n_box > 1:
        #
        # Boolean Definitions for Kidneys
        box_defs = get_boolean_defs(
            roi_name=box_name,
            a_sources=delete_boxes,
            a_operation="Union",
            export=False,
        )
        make_boolean_structure(
            patient=patient_data.patient, case=case,
            examination=exam, **box_defs)
        for b in delete_boxes:
            case.PatientModel.RegionsOfInterest[b].DeleteRoi()
    # Exclude it from export
    exclude_from_export(case, box_name)
    if roi_has_contours(patient_data, box_name):
        return box_name
    else:
        raise RuntimeError(f"Unable to generate a box geometry for {box_name} "
                           f"on exam {exam.Name}")




def make_central_junction_contour(pdata, z_inf_box,
                                  dim_si, dose_level, color=None, j_name=None):
    #  Make the Box Roi and junction region in the area of interest
    #
    # Get exam orientation
    if color is None:
        color = [192, 192, 192]
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = 1.
    elif prefix == 'hfs':
        si = 1.
    else:
        sys.exit(f'Unknown patient orientation {prefix}')
    # Find the name of the external contour
    external_name = find_types(pdata.case,
                               roi_type='External')[0]
    box_name = 'box_' + str(round(z_inf_box, 1))
    overlap_box = 1.001
    box_name = make_box(pdata, box_name,
                        length=dim_si * overlap_box,
                        z_center=z_inf_box + si * dim_si / 2.)
    #
    # Make junction by intersecting external with the box
    junction_name = f'{prefix}{j_name if j_name else ""}_junction_{dose_level}'
    temp_defs = get_boolean_defs(
        roi_name=junction_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        color=color,
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    _ = change_roi_type(
        case=pdata.case,
        roi_name=junction_name,
        roi_type='Ptv')
    update_all_remove_expression(pdata=pdata, roi_name=junction_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_avoid(pdata, z_start, avoid_name, color=None):
    """ Build the avoidance structure used in making the PTV
        patient_data: kind of like PDiddy, but with data, see below
        isocenter_position (float): starting location of the junction
        otv_name (str): Name of the structure to include all avoidance voxels
        avoid_color (opt list[r,g,b]): color of output structure
        Recipe for avoidance volume:
        Take the isocenter_position, build a box that is everything above this position
        Find the intersection with the external.
        If this is the HFS scan, subtract the lung avoidance
    """
    #
    # Find the name of the external contour
    external_name = find_types(pdata.case, roi_type='External')[0]
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.  # SI direction is negative for FFS
        bb_index = 1  # Starting coordinate of bounding box
        additional_avoidances = []  # No other avoidances in FFS orientation
    else:
        si = 1.  # SI direction is positive for HFS
        bb_index = 0  # Starting coordinate of bounding box
        additional_avoidances = [LUNG_AVOID_NAME]  # Subtract the lung volumes
    #
    # Make a box ROI that starts at isocenter_position and ends at isocenter_position + dim_si
    box_name = 'avoid_box_' + str(round(z_start, 1))
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    si_box_size = abs(bb_external[bb_index].z + si * z_start)
    box_name = make_box(pdata, box_name,
                        length=si_box_size,
                        z_center=z_start - si * si_box_size / 2.)
    # Boolean Definitions for Avoidance
    temp_defs = get_boolean_defs(
        roi_name=avoid_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        b_sources=additional_avoidances,
        r_exp=[0., 0., 0.7, 0.7, 0.7, 0.7, 0.7],
        color=color
    )
    make_boolean_structure(patient=pdata.patient, case=pdata.case,
                           examination=pdata.exam, **temp_defs)
    update_all_remove_expression(pdata=pdata, roi_name=avoid_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_ptv(pdata, junction_prefix, avoid_name, color=None, kidney_sparing=False):
    # Find all contours matching prefix and along with otv_name
    # return the external minus these objects
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        eval_name = FFS_TARGET_EVAL_NAME
    else:
        eval_name = HFS_TARGET_EVAL_NAME
    #
    # PTV_name
    ptv_name = "PTV_p_" + prefix.upper()
    external_name = find_types(pdata.case, roi_type='External')[0]
    roi_exclude = find_roi_prefix(pdata.case, roi_match=junction_prefix)
    logging.debug(f'Rois added to exclude are {roi_exclude}')
    roi_exclude.append(avoid_name)
    #
    # Boolean Definitions
    temp_defs = get_boolean_defs(
        roi_name=ptv_name, a_sources=[external_name],
        a_operation="Intersection", b_sources=roi_exclude, b_operation="Union",
        result="Subtraction", visualize=False, color=color, roi_type='Ptv')
    make_boolean_structure(patient=pdata.patient, case=pdata.case,
                           examination=pdata.exam, **temp_defs)
    # Make Eval structure
    # Boolean Definitions
    roi_exclude.append(SKIN_AVOIDANCE)
    roi_exclude.append(LUNGS_EVAL_NAME)
    if kidney_sparing:
        roi_exclude.append(KIDNEY_AVOID_NAME)
    temp_defs = get_boolean_defs(
        roi_name=eval_name, a_sources=[external_name],
        a_operation="Intersection", b_sources=roi_exclude, b_operation="Union",
        result="Subtraction", color=[255, 0, 0], visualize=True,
        roi_type="Ptv")
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    pdata.case.PatientModel.RegionsOfInterest[ptv_name].DeleteExpression()
    pdata.case.PatientModel.RegionsOfInterest[eval_name].DeleteExpression()
    return [ptv_name, eval_name]


def make_lung_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    lungs_defs = get_boolean_defs(
        roi_name=LUNGS,
        a_sources=["Lung_L", "Lung_R"],
        a_operation="Union",
        color=color,
        export=True,
        roi_type="Organ"
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lungs_defs)
    lung_avoid_defs = get_boolean_defs(
        roi_name=LUNG_AVOID_NAME,
        a_sources=[LUNGS],
        a_operation="Union",
        a_exp=[LUNG_AVOID_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_avoid_defs)
    #
    # Boolean Definitions for Lung Evaluation
    lung_eval_defs = get_boolean_defs(
        roi_name=LUNGS_EVAL_NAME,
        a_sources=[LUNGS],
        a_operation="Union",
        a_exp=[LUNGS_EVAL_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_eval_defs)


def make_kidney_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    kidneys_defs = get_boolean_defs(
        roi_name=KIDNEYS,
        a_sources=["Kidney_L", "Kidney_R"],
        a_operation="Union",
        color=color,
        export=True,
        roi_type="Organ"
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **kidneys_defs)
    kidneys_avoid_defs = get_boolean_defs(
        roi_name=KIDNEY_AVOID_NAME,
        a_sources=[KIDNEYS],
        a_operation="Union",
        a_exp=[KIDNEY_AVOID_MARGIN] * 6,
        a_margin_type="Contract",
        color=color,
        roi_type='Organ',
    )
    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **kidneys_avoid_defs)


def make_otv(pdata: namedtuple, poi_name: str, point_index: int,
             junction_width: float, pois: List[str], color: Optional[List[int]] = None) -> None:
    """
    Generate the optimization target volume used in inverse planning.
    It consists of the entire patient (using the External) at the location of
    the isocenter minus the junctions.

    Args:
        pdata (PatientData): Patient data.
        poi_name (str): Point of interest.
        point_index (int): Index of the point.
        junction_width (float): Width of the junction.
        pois (List[str]): List of points of interest.
        color (Optional[List[int]]): Color for the OTV.

    Returns:
        None
    """
    # Ensure the poi contains an integer at the end.
    iso_number = validate_poi_name(poi_name)
    # Get patient orientation
    orientation = pdata.case.Examinations[pdata.exam.Name].PatientPosition
    junction_pair = determine_junction_pair(point_index, pois, junction_width, orientation)

    patient_model = pdata.case.PatientModel
    if color is None:
        color = COLORS[iso_number]
    # Find the name of the external contour
    external_name = find_types(pdata.case, roi_type='External')[0]

    # Set OTV name
    otv_name = f'OTV_iso{iso_number}'

    # Get exam orientation
    additional_avoidances = []
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        additional_avoidances = [
            r.Name for r in patient_model.RegionsOfInterest if 'junction' in r.Name]
        additional_avoidances.append(AVOID_FFS_NAME)
    elif prefix == 'hfs':
        additional_avoidances = [
            r.Name for r in patient_model.RegionsOfInterest if 'junction' in r.Name]
        additional_avoidances.append(LUNG_AVOID_NAME)
        additional_avoidances.append(AVOID_HFS_NAME)

    # Make the box geometry
    z_center, length = determine_otv_center_length(
        pdata, poi_name, prefix, junction_pair)
    box_name = 'otv_box_' + str(round(int(poi_name[-1]), 1))
    box_name = make_box(pdata, box_name, length=length, z_center=z_center)

    temp_definitions = get_boolean_defs(
        roi_name=otv_name,
        a_sources=[external_name, box_name],
        a_operation="Intersection",
        b_sources=additional_avoidances,
        b_operation="Union",
        r_exp=[0.01] * 6,
        r_margin_type="Contract",
        result="Subtraction",
        color=color,
        roi_type="Ptv",
    )

    make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_definitions)

    update_all_remove_expression(pdata=pdata, roi_name=otv_name)

    _ = volume_threshold_roi(pdata, otv_name, min_vol=0.1)

    patient_model.RegionsOfInterest[box_name].DeleteRoi()


def make_generic_junction_structs(rs_obj: namedtuple, z_junction: float, junction_width: float,
                                  j_name: Optional[str] = None,
                                  reverse: bool = False,
                                  j_range: Optional[range] = None):
    """
    Create generic junction structures at specified z-positions.

    Args:
        rs_obj: The object representing the RS file.
        z_junction: The z-position of the junction.
        junction_width: The width of the junction.
        j_name: Name of the junction structure.
        reverse: Flag indicating whether the junctions should be created in reverse order.
        j_range: Custom range of junction values.

    Returns:
        None
    """

    # IsoDose levels
    if j_range:
        j_i = j_range
    else:
        j_i = range(1, 10, 1)

    dim_si = junction_width / len(j_i)

    # Assign colors to dose levels
    if len(j_i) >= len(COLORS):
        color_levels = {j: COLORS[i] for i, j in enumerate(j_i)}
    else:
        color_levels = {j: COLORS[i % len(COLORS)] for i, j in enumerate(j_i)}

    for i in range(len(j_i)):
        if reverse:
            z_start = z_junction - dim_si * float(i)
        else:
            z_start = z_junction - dim_si * float(len(j_i) - i)

        make_central_junction_contour(
            rs_obj,
            z_inf_box=z_start,
            dim_si=dim_si,
            dose_level=str(int(j_i[i])),
            color=color_levels[j_i[i]],
            j_name=j_name)


# ===================================
# MULTI-ROI OPERATIONS
# ===================================
def cut_rois_to_image(source: namedtuple, destination: namedtuple,
                      rois: list) -> None:
    """
    This function uses the cuts a transformed roi to the size of the
    external in the destination image.
    It creates a large box to ensure the entire source contour will be
    included, then it subtracts the external volume in the destination
    image.

    Args:
        source (namedtuple): Object containing patient case and examination
            information for the source examination.
        destination (namedtuple): Object containing patient case and examination information for the destination examination.
        rois (list): List of names of regions of interest to transform.

    Returns:
        None
    """

    # Maximum possible height for bounding box (in cm)
    wadlow = 272  # 272 cm is the maximum height of a human but in RS 2024a is the maximum

    # Placeholder for ROIs to be deleted
    delete_list = []

    # Create a bounding box larger than possible body size
    big_box = make_box(destination, box_name='big_box', length=wadlow)
    delete_list.append(big_box)

    # Create a bounding box as large as the external examination
    box_name = make_box(destination, box_name=f'fov_box')
    delete_list.append(box_name)

    # Subtract smaller box from the large one
    # Switch to boolean subtraction
    subtraction_box_name = destination.case.PatientModel.GetUniqueRoiName(DesiredName='SubtractionBox')

    subtraction_box_name = subtract_b_from_a(
        pdata=destination,
        a_list=[big_box],
        b_list=[box_name],
        result_name=subtraction_box_name,
    )
    delete_list.append(subtraction_box_name)

    # Transform ROIs according to the determined direction
    transform_object(source, destination, rois=rois)

    # Subtract any regions outside of the destination set from the ROIs
    for roi in rois:
        subtraction_box_name = subtract_b_from_a(
            pdata=destination,
            a_list=[roi],
            b_list=[subtraction_box_name],
            result_name=roi,
        )

    # Delete temporary ROIs
    for roi_to_delete in delete_list:
        delete_roi(source.case, roi_to_delete)

# ===================================
# TRANSFORMATIONS
# ===================================
def transform_object(source: namedtuple, destination: namedtuple,
                     pois: list = None, rois: list = None) -> None:
    """
    This function obtains transformation from one examination to another,
    and applies it to points of interest (POIs) and regions of interest (ROIs).

    The function resets primary and secondary exams before performing
    transformations.
    The direction of transformation can be from 'ffs_to_hfs' or 'hfs_to_ffs'.

    Args:
        source (namedtuple): Object containing the patient case and examination
            information for the source of the rois/pois
        destination (namedtuple): Object containing the patient case and
            examination information for destination exam
        pois (list, optional): List of names of points of interest to
            transform. Defaults to None.
        rois (list, optional): List of names of regions of interest to
            transform. Defaults to None.

    Returns:
        None
    """

    prefix = determine_prefix(source.exam)
    if prefix == 'ffs':
        direction = 'ffs_to_hfs'
        ffs_scan_name = source.exam.Name
        hfs_scan_name = destination.exam.Name
        reset_primary_secondary(source.exam, destination.exam)
    else:
        direction = 'hfs_to_ffs'
        hfs_scan_name = source.exam.Name
        ffs_scan_name = destination.exam.Name
        reset_primary_secondary(destination.exam, source.exam)

    # Define the two operations and their respective methods
    operations = {
        'ffs_to_hfs': {
            'transformation': source.case.GetTransformForExaminations(
                FromExamination=ffs_scan_name, ToExamination=hfs_scan_name),
        },
        'hfs_to_ffs': {
            'transformation': source.case.GetTransformForExaminations(
                FromExamination=hfs_scan_name, ToExamination=ffs_scan_name),
        }
    }

    # Check if the direction is valid and perform transformations
    if direction in operations:
        # Convert the transformation details to a dictionary
        trans_list = source.case.GetTransformForExaminations(
            FromExamination=source.exam.Name,
            ToExamination=destination.exam.Name)
        trans = convert_array_to_transform(trans_list)
        # Apply transformation to POIs and ROIs if provided
        if pois:
            source.case.MapPoiGeometriesRigidly(
                PoiGeometryNames=pois, CreateNewPois=False,
                ReferenceExaminationName=source.exam.Name,
                TargetExaminationNames=[destination.exam.Name],
                Transformations=[trans])

        if rois:
            source.case.MapRoiGeometriesRigidly(
                RoiGeometryNames=rois, CreateNewRois=False,
                ReferenceExaminationName=source.exam.Name,
                TargetExaminationNames=[destination.exam.Name],
                Transformations=[trans])


def get_center(rs_obj, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(rs_obj.case, rs_obj.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    c = {'x': bb_roi[0].x + (bb_roi[1].x - bb_roi[0].x) / 2,
         'y': bb_roi[0].y + (bb_roi[1].y - bb_roi[0].y) / 2,
         'z': bb_roi[0].z + (bb_roi[1].z - bb_roi[0].z) / 2}
    return c


def place_ffs_vmat_pois(pd_ffs, junction, offset):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_ffs.case,
                                 roi_type='External')

    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    last_iso_position = round_iso(ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + FW / 2)
    first_iso_position = round_iso(junction.Point.z - FW / 2)
    isocenter_distance = ((first_iso_position - last_iso_position)
                          / (FFS_ISO_NUMBER - 1))
    isocenter_distance = round_iso(isocenter_distance)
    ffs_junction_width = FW - isocenter_distance
    logging.info(f'Distance from inferior most point at {ffs_ext_z:.2f} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {float(ffs_ext_z - junction.Point.z):.2f} with '
                 f'spacing {isocenter_distance:.2f} requires '
                 f'{FFS_ISO_NUMBER} isocenters, '
                 f'with an overlap of {ffs_junction_width}')
    # Junction location
    pois = []
    # Round the positions of the isocenter to the nearest mm.
    coords = {'x': round_iso(junction.Point.x),
              'y': round_iso(junction.Point.y)}
    for i in range(FFS_ISO_NUMBER):
        if i != FFS_ISO_NUMBER - 1:
            coords['z'] = first_iso_position - i * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i + offset + 1]]
        color = ",".join(color_lst)
        poi = make_poi(pd_ffs.case, pd_ffs.exam,
                       coords, name=f"{FFS_POI}{i + offset + 1}",
                       color=color)
        pois.append(poi)

    return ffs_junction_width


def make_midfield_junctions(rs_obj, poi_name_list, junction_width):
    # Determine the coordinates of each isocenter
    # Find the mid-point between isocenter pairs
    # Put a junction point at + 1/2 junction width from this point
    # Build the structures
    _ = rs_obj.case.Examinations[rs_obj.exam.Name].PatientPosition
    for i in range(len(poi_name_list) - 1):
        poi_geom0 = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name].PoiGeometries[
            poi_name_list[i]]
        poi_geom1 = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name].PoiGeometries[
            poi_name_list[i + 1]]

        try:
            n0 = int(poi_geom0.OfPoi.Name[-1])
            n1 = int(poi_geom1.OfPoi.Name[-1])
        except ValueError:
            logging.error(
                f'Error: The name of the POI does not contain an '
                f'integer in the last digit.')
            raise RuntimeError(f'Error: The name of the POI does not contain '
                               f'an integer in the last digit.')
            # Handle the error condition here, such as setting default values or terminating the
            # program.
            # For example, you can set n0 and n1 to 0 or None to indicate the error condition.

        z_diff = poi_geom0.Point.z - poi_geom1.Point.z
        z_junct = poi_geom0.Point.z - z_diff / 2 + junction_width / 2

        logging.info(
            f'Point {poi_geom0.OfPoi.Name} at z = {poi_geom0.Point.z:.2f} is separated from '
            f'point {poi_geom1.OfPoi.Name} at z = {poi_geom1.Point.z:.2f} by {z_diff:.2f} cm. '
            f'So the beginning of the junction {junction_width:.2f} will be placed at '
            f'{z_junct:.2f}')

        # Make two mid-field junctions
        make_generic_junction_structs(rs_obj, z_junct, junction_width,
                                      j_name=f'_iso{n0}{n1}', j_range=range(1, 3))


def place_hfs_vmat_pois(pd_hfs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = find_types(pd_hfs.case,
                                 roi_type='External')
    j_z = junction.Point.z
    hfs_ext_z = get_most_superior(pd_hfs, roi_name=external_name)
    hfs_treatment_length = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z
    iso_number = math.ceil(hfs_treatment_length / (FW - HFS_OVERLAP))
    last_iso_position = round_iso(j_z - CENTRAL_JUNCTION_WIDTH + FW / 2)
    first_iso_position = round_iso(hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - FW / 2)
    isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
    hfs_junction_width = FW - isocenter_distance

    logging.info(f'Distance from superior most point at {hfs_ext_z} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {hfs_ext_z - junction.Point.z:.2f} with '
                 f'spaced {isocenter_distance:.2f} requires '
                 f'{iso_number} isocenters')
    if hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - j_z \
            >= HFS_MAX_TREATMENT_LENGTH:
        sys.exit('This patient may be too tall for tx')
    elif isocenter_distance >= FW - HFS_OVERLAP:
        # Increase the isocenter number by 1
        iso_number += 1
        isocenter_distance = round_iso((first_iso_position - last_iso_position) / (iso_number - 1))
        hfs_junction_width = FW - isocenter_distance
        logging.info(f'Distancing incorrect: FW: {FW} with Overlap {HFS_OVERLAP} '
                     f'with greater computed isocenter distance {isocenter_distance},'
                     f' increasing isocenter by 1 to {iso_number}')

    # Junction location
    pois = []
    for i in range(iso_number):
        for p in pd_hfs.case.PatientModel.PointsOfInterest:
            if p.Name == f"{HFS_POI}{i + 1}":
                p.DeleteRoi()
        coords = {'x': junction.Point.x, 'y': junction.Point.y}
        if i != iso_number - 1:
            coords['z'] = junction.Point.z - CENTRAL_JUNCTION_WIDTH + FW / 2 \
                          + (iso_number - 1 - i) * isocenter_distance
        else:
            coords['z'] = last_iso_position
        color_lst = [str(c) for c in COLORS[i]]
        color = ",".join(color_lst)
        poi = make_poi(pd_hfs.case, pd_hfs.exam,
                       coords, name=f"{HFS_POI}{i + 1}", color=color)
        pois.append(poi)
    return hfs_junction_width


def make_poi(case, exam, coords, name, color):
    for p in case.PatientModel.PointsOfInterest:
        if p.Name == name:
            p.DeleteRoi()
    _ = create_poi(
        case=case,
        exam=exam,
        coords=[coords['x'], coords['y'], coords['z']],
        name=name,
        color=color,
        diameter=1,
        rs_type='Control')
    return name


def find_hfff_junction_coords(pd_ffs, max_treatment_length=FFS_MAX_TREATMENT_LENGTH):
    # Find the inferior most point from the ffs scan on the external
    [external_name] = find_types(
        pd_ffs.case, roi_type='External')
    ffs_ext_z = get_most_inferior(pd_ffs, roi_name=external_name)
    _ = get_most_superior(pd_ffs, roi_name=external_name)
    center = get_center(pd_ffs, external_name)
    return {
        'x': 0,
        'y': center['y'],
        # Place the junction 1/2 field width away from the isocenter
        'z': ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER + max_treatment_length
    }


def place_hfff_junction_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    _ = create_poi(
        case=pd_hfs.case,
        exam=pd_hfs.exam,
        coords=[coord_hfs['x'], coord_hfs['y'], coord_hfs['z']],
        name=JUNCTION_POINT,
        color='Red',
        diameter=1,
        rs_type='Control'
    )












