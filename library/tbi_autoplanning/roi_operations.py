# roi_operations.py
from typing import Optional, List
from collections import namedtuple
import sys
import logging
import connect
import math

from library.StructureOperations import (
    create_roi, make_boolean_structure, change_roi_type,
    find_types, exclude_from_export, make_wall)
import library.AutoPlanOperations as AutoPlanOperations
from .tbi_definitions import (
    CENTRAL_JUNCTION_WIDTH, FFS_MAX_TREATMENT_LENGTH, LUNG_AVOID_MARGIN, LUNGS_EVAL_MARGIN, \
    KIDNEYS, KIDNEY_AVOID_MARGIN, COLORS, MBS_ROIS, EXTERNAL_NAME, EXTERNAL_SETUP, EXTERNAL_SETUP_EXP, \
    SKIN_AVOIDANCE_CONTRACT, HFS_TARGET_NAMES, FFS_TARGET_NAMES,\
    LUNG_AVOID_NAME, FFS_TARGET_EVAL_NAME, HFS_TARGET_EVAL_NAME, SKIN_AVOIDANCE, \
    LUNGS_EVAL_NAME, KIDNEY_AVOID_NAME, AVOID_HFS_NAME, AVOID_FFS_NAME, LUNGS, \
    JUNCTION_PREFIX_FFS, JUNCTION_PREFIX_HFS, JUNCTION_POINT
)
from .tbi_utils import reset_primary_secondary, determine_prefix, register_images, get_center, Pd

from .poi_operations import (
    validate_poi_name, get_most_inferior, get_most_superior, find_hfff_junction_coords, find_pois, get_point_position,
    place_hfff_junction_poi, determine_junction_pair, place_hfs_vmat_pois, place_ffs_vmat_pois, estimate_patient_height)
from .tbi_plan_builders import get_vmat_plan_defs


def get_roi_geometry(case: object, exam: object, roi_name: str) -> object:
    """
    Retrieves the geometry of a specified ROI for a given exam.

    Args:
        case (object): The RayStation case object.
        exam (object): The RayStation exam object.
        roi_name (str): The name of the ROI to retrieve geometry for.

    Returns:
        object: The geometry object for the specified ROI.
    """
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


# ROI Existence and basic checks
def roi_in_list(case: object, structure_name: str, roi_list: Optional[List[str]] = None) -> bool:
    """
    Checks if a structure name exists in the case or in a provided list.

    Args:
        case (object): The RayStation case object.
        structure_name (str): The name of the structure (ROI) to check.
        roi_list (Optional[List[str]]): An optional list of ROI names to check against.

    Returns:
        bool: True if the structure exists in the case or list, False otherwise.
    """
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


def roi_has_contours(patient_data: Pd, structure_name: str) -> bool:
    """
    Checks if a given ROI has any contours in the patient data.

    Args:
        patient_data (Pd): The patient data dataclass instance.
        structure_name (str): The name of the ROI to check.

    Returns:
        bool: True if the ROI has contours, False otherwise.
    """
    logging.debug(f'Checking for contours in {patient_data.case.CaseName} for {structure_name}')
    if roi_in_list(patient_data.case, structure_name):
        roi_geom = get_roi_geometry(patient_data.case, patient_data.exam, structure_name)
        logging.debug(f'ROI {structure_name} has contours: {roi_geom.HasContours()}')
        if roi_geom.HasContours():
            return True
    return False


def find_roi_prefix(case: object, roi_match: str) -> List[str]:
    """
    Finds all ROI names in the case that start with the given prefix.

    Args:
        case (object): The RayStation case object.
        roi_match (str): The prefix to match ROI names against.

    Returns:
        List[str]: A list of ROI names that match the prefix.
    """
    # Return all structures whose name contains roi_prefix
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_match in r.Name:
            found_roi.append(r.Name)
    return found_roi


# =================================================================
# ROI Creation and Deletion
# =================================================================
def delete_roi(case: object, structure_name: str) -> bool:
    """
    Deletes an ROI from the case if it exists.

    Args:
        case (object): The RayStation case object.
        structure_name (str): The name of the ROI to delete.

    Returns:
        bool: True if the ROI was deleted, False otherwise.
    """
    if roi_in_list(case, structure_name):
        try:
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            return True
        except Exception as e:
            logging.warning(f'Could not delete {structure_name}: {e}')
            return False
    else:
        return True


def copy_roi(case: object, source_roi: str, target_roi: str) -> bool:
    """
    Copies an ROI from source to target within the case.

    Args:
        case (object): The RayStation case object.
        source_roi (str): The name of the source ROI.
        target_roi (str): The name of the target ROI.

    Returns:
        bool: True if the ROI was copied successfully, False otherwise.
    """
    copy_roi_name = case.PatientModel.GetUniqueRoiName(DesiredName=f'{source_roi}_copy')
    _ = create_roi(
        case=case,
        examination=case.Examinations[source_roi.split('_')[0]], # Assuming source_roi is like 'External_copy'
        roi_name=copy_roi_name,
    )
    roi_defs = get_boolean_defs(
        roi_name=copy_roi_name,
        a_sources=[source_roi],
        a_operation="Intersection",
    )
    make_boolean_structure(
        patient=case.Patient, case=case, examination=case.Examinations[source_roi.split('_')[0]], **roi_defs)
    # Update derived status and delete derivation
    update_all_remove_expression(case, roi_name=copy_roi_name)

    return True # Changed to True as per new_code


# =================================================================
# Derived roi updates and copying
# =================================================================
def update_all_remove_expression(pdata: Pd, roi_name: str) -> None:
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


def check_list(var: object, length: int, element_type: type, default: object) -> object:
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
        roi_name: str, a_sources: List[str], a_operation: str, a_exp: Optional[List[float]] = None, a_margin_type: str = "Expand",
        b_sources: Optional[List[str]] = None, b_operation: str = "Union", b_exp: Optional[List[float]] = None, b_margin_type: str = "Expand",
        r_exp: Optional[List[float]] = None, r_margin_type: str = "Expand", result: str = "None",
        color: Optional[List[int]] = None, export: bool = False, visualize: bool = False, roi_type: str = "Undefined"
) -> dict:
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


def volume_threshold_roi(patient_data: Pd, roi_name: str, min_vol: float = 1., max_vol: float = 1.e6) -> bool:
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


def subtract_b_from_a(pdata: Pd, a_list: List[str], b_list: List[str], result_name: str) -> str:
    # Check for circular references
    if result_name in a_list:
        copy_result_name = copy_roi(pdata.case, result_name, result_name) # Changed to copy_roi
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
def make_box(patient_data: Pd, box_name: str, length: Optional[float] = None, z_center: Optional[float] = None) -> str:
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
        # Need to make multiple boxes if length is greater than 200
        n_box = math.ceil(length / 200)
        box_length = length / n_box
    else:
        n_box = 1
        box_length = length
    logging.debug(f'Measured length of external contour: {bb_external[1].z - bb_external[0].z}')
    logging.debug(f'Building a box with length {length} centered at {z_center}')
    logging.debug(f'Number of boxes: {n_box} with length {box_length}')
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
        # Boolean Definitions for creating a union of the boxes
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




def make_central_junction_contour(pdata: Pd, z_inf_box: float,
                                  dim_si: float, dose_level: str, color: Optional[List[int]] = None, j_name: Optional[str] = None) -> None:
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


def material_override_overlap(pd_ffs: Pd, pd_hfs: Pd) -> tuple:
    check_struct = {
        'HFS': (pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name],
                find_types(pd_hfs.case, roi_type='Support')),
        'FFS': (pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name],
                find_types(pd_ffs.case, roi_type='Support')),
    }
    for key, (ss, support) in check_struct.items():
        # Use the ComparisonOfRoiGeometries to check each contour to measure
        # if there is any overlap with every other contour
        if len(support) > 1:
            for i in range(len(support)-1):
                for j in range(i + 1, len(support)):
                    if ss.RoiGeometries[support[i]].HasContours() and \
                            ss.RoiGeometries[support[j]].HasContours():
                        compare = ss.ComparisonOfRoiGeometries(
                            RoiA=support[i],
                            RoiB=support[j],
                            ComputeDistanceToAgreementMeasures=False)
                        if compare['DiceSimilarityCoefficient'] > 0.001:
                            return True, support[i], support[j]
    return False, None, None


def make_avoid(pdata: Pd, z_start: float, avoid_name: str, color: Optional[List[int]] = None) -> None:
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


def make_ptv(pdata: Pd, junction_prefix: str, avoid_name: str, color: Optional[List[int]] = None, kidney_sparing: bool = False) -> List[str]:
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


def make_lung_contours(pdata: Pd, color: Optional[List[int]] = None) -> None:
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


def make_kidney_contours(pdata: Pd, color: Optional[List[int]] = None) -> None:
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


def make_otv(pdata: Pd, poi_name: str, point_index: int,
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


def make_generic_junction_structs(rs_obj: Pd, z_junction: float, junction_width: float,
                                  j_name: Optional[str] = None,
                                  reverse: bool = False,
                                  j_range: Optional[range] = None) -> None:
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
def cut_rois_to_image(source: Pd, destination: Pd,
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
def transform_object(source: Pd, destination: Pd,
                     pois: Optional[List[str]] = None, rois: Optional[List[str]] = None) -> None:
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


def make_midfield_junctions(rs_obj: Pd, poi_name_list: List[str], junction_width: float) -> None:
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


def determine_otv_center_length(pdata: Pd, poi_name: str, orientation: str, junction_pair: tuple) -> tuple:
    """
    Args:
        pdata (named tuple): RS objects
        poi_name (str): the name of the point of interest (isocenter)
        orientation (str):'ffs' or 'hfs'
        junction_pair (tuple): widths of two junctions around poi
    Returns:
        tuple: otv_center, otv_length
    """
    pois = find_pois(pdata)
    poi0 = get_point_position(pdata, poi_name)
    poi_index = pois.index(poi_name)
    logging.debug(f'Current poi {poi_name}: index {poi_index}')
    if orientation == 'hfs':
        if poi_index == 0:
            [external_name] = find_types(pdata.case,
                                         roi_type='External')
            sup_extent = get_most_superior(pdata, external_name)
            # Inferior extent at junction edge
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            #    logging.debug(f'{poi_name}:: Inferior point {pois[poi_index+1]}:'
            #                  f' z {poi_inf.z}, Placed at inf_extent {inf_extent}')
            otv_length = sup_extent - inf_extent
            otv_center = inf_extent + otv_length / 2
        elif poi_index == len(pois) - 1:
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            # Inferior extent at junction point
            poi_inf = get_point_position(pdata, JUNCTION_POINT)
            inf_extent = poi_inf.z
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        else:
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        return otv_center, otv_length
    else:
        if poi_index == 0:
            poi_sup = get_point_position(pdata, JUNCTION_POINT)
            sup_extent = poi_sup.z - junction_pair[0]
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
            logging.debug(f'{poi_name}:: otv_length {otv_length}, otv_center {otv_center}')
        elif poi_index == len(pois) - 1:
            [external_name] = find_types(pdata.case,
                                         roi_type='External')
            inf_extent = get_most_inferior(pdata, external_name)
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        else:
            poi_inf = get_point_position(pdata, pois[poi_index + 1])
            i_diff = poi0.z - poi_inf.z
            inf_extent = poi_inf.z + junction_pair[1] / 2 + i_diff / 2
            poi_sup = get_point_position(pdata, pois[poi_index - 1])
            s_diff = poi_sup.z - poi0.z
            sup_extent = poi_sup.z - junction_pair[0] / 2 - s_diff / 2
            otv_length = sup_extent - inf_extent
            otv_center = sup_extent - otv_length / 2
        return otv_center, otv_length


def make_central_junction_structs(pd_hfs: Pd, pd_ffs: Pd, kidney_sparing: bool) -> tuple:
    """

    Args:
        pd_hfs: hfs named tuple
        pd_ffs: ffs named tuple
        kidney_sparing: Boolean to determine if kidney sparing is used

    Returns:

    """
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # Set the central junction point, and map it to the hfs scan
    hfs_poi_junction, ffs_poi_junction = calculate_junction(pd_hfs, pd_ffs)
    # IsoDose levels declaration and colors.
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = CENTRAL_JUNCTION_WIDTH / len(j_i)
    dose_levels = {10: [127, 0, 255],
                   20: [0, 0, 255],
                   30: [0, 127, 255],
                   40: [0, 255, 255],
                   50: [0, 255, 127],
                   60: [0, 255, 0],
                   70: [127, 255, 0],
                   80: [255, 255, 0],
                   90: [255, 127, 0],
                   95: [255, 0, 0],
                   100: [255, 0, 255]}

    for i in range(len(j_i)):
        # Place the inferior-most edge of box-10% to be at one box width from
        # the junction
        roi_inf_box_edge = ffs_poi_junction.Point.z - dim_si * float(i + 1)
        make_central_junction_contour(
            pd_ffs,
            z_inf_box=roi_inf_box_edge,
            dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx",
            color=dose_levels[j_i[i]])
    make_avoid(pd_ffs, z_start=ffs_poi_junction.Point.z,
               avoid_name=AVOID_FFS_NAME)
    ffs_ptv_list = make_ptv(pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS,
                            avoid_name=AVOID_FFS_NAME, kidney_sparing=False)
    cut_rois_to_image(pd_ffs, pd_hfs, ffs_ptv_list)

    for i in range(len(j_i)):
        # Place the inferior edge of the HFS junction at:
        # junction_z - N_isodose_levels * box width
        roi_inf_box_edge = hfs_poi_junction.Point.z \
                           - dim_si * float(len(j_i) - i)
        logging.debug(
            f'Z location for Junction {str(j_i[i])} is {roi_inf_box_edge}')
        make_central_junction_contour(
            pd_hfs, z_inf_box=roi_inf_box_edge, dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx", color=dose_levels[j_i[i]])
    #
    # HFS avoid starts at junction point - number of dose levels * dim_si
    hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
    make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
    hfs_ptv_list = make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS,
                            avoid_name=AVOID_HFS_NAME, kidney_sparing=kidney_sparing)
    cut_rois_to_image(pd_hfs, pd_ffs, hfs_ptv_list)

    return ffs_poi_junction, hfs_poi_junction


def calculate_junction(pd_hfs: Pd, pd_ffs: Pd) -> tuple:
    # Determine the central junction using ffs scan
    central_junction_start = find_hfff_junction_coords(pd_ffs)
    # Place junction point
    place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=central_junction_start)
    # Map the junction point to the hfs scan
    transform_object(source=pd_ffs, destination=pd_hfs, pois=[JUNCTION_POINT],
                     rois=None)
    # Check patient height
    patient_height = estimate_patient_height(pd_hfs, pd_ffs, external_roi_name="ExternalClean")
    # If the patient height * 0.6 is less than max treatment length, then use 0.6 * patient height
    # use an alternative method to set the junction point
    if patient_height * 0.6 < FFS_MAX_TREATMENT_LENGTH:
        ffs_treatment_length = int(patient_height * 0.6)
        logging.info(f'Patient height is {patient_height} cm, '
                     f'using 60% of patient height as treatment length: {ffs_treatment_length} cm')
        central_junction_start = find_hfff_junction_coords(pd_ffs,
                                                           max_treatment_length=ffs_treatment_length)
        place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=central_junction_start)
        transform_object(source=pd_ffs, destination=pd_hfs, pois=[JUNCTION_POINT],
                         rois=None)

    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # Return poi rs object
    return hfs_poi_junction, ffs_poi_junction


def convert_array_to_transform(t: list) -> dict:
    # Converts into the expected values for an RS transform dictionary
    return {'M11': t[0], 'M12': t[1], 'M13': t[2], 'M14': t[3],
            'M21': t[4], 'M22': t[5], 'M23': t[6], 'M24': t[7],
            'M31': t[8], 'M32': t[9], 'M33': t[10], 'M34': t[11],
            'M41': t[12], 'M42': t[13], 'M43': t[14], 'M44': t[15]}


def set_all_ptvs_to_ptv_type(pd_ffs: Pd, pd_hfs: Pd) -> None:
    """
    Sets all PTVs to the correct type for both FFS and HFS patient data.

    Args:
        pd_ffs (Pd): Patient data for feet-first supine.
        pd_hfs (Pd): Patient data for head-first supine.

    Returns:
        None
    """
    all_ptvs = HFS_TARGET_NAMES + FFS_TARGET_NAMES
    toggle_ptv_type(pd_ffs,rois=all_ptvs, roi_type='Ptv')
    toggle_ptv_type(pd_hfs,rois=all_ptvs, roi_type='Ptv')


def toggle_ptv_type(rs_obj: Pd, rois: List[str], roi_type: str) -> None:
    """
    Sets the type of the specified ROIs to the given type for the provided patient data.

    Args:
        rs_obj (Pd): The patient data dataclass.
        rois (List[str]): List of ROI names to update.
        roi_type (str): The type to set for the ROIs.

    Returns:
        None
    """
    # Sometimes in the course of RayStation planning, we need to change our type
    # 'cause of stupid dose grids.
    for r in rois:
        change_roi_type(rs_obj.case, roi_name=r, roi_type=roi_type)


def make_vmat_planning_structures(pd_hfs: Pd, pd_ffs: Pd, nfx: int, rx: int, make_otvs: bool = False, make_junctions: bool = False) -> tuple:
    """
    Creates VMAT planning structures for HFS and FFS patient data.

    Args:
        pd_hfs (Pd): Patient data for head-first supine.
        pd_ffs (Pd): Patient data for feet-first supine.
        nfx (int): Number of fractions.
        rx (int): Total dose.
        make_otvs (bool, optional): Whether to create OTVs. Defaults to False.
        make_junctions (bool, optional): Whether to create junctions. Defaults to False.

    Returns:
        tuple: Tuple containing HFS and FFS multiplan objects.
    """
    #
    # HFS
    # Add points for isocenters in VMAT
    hfs_poi_junction = pd_hfs.case.PatientModel \
        .StructureSets[pd_hfs.exam.Name].PoiGeometries[JUNCTION_POINT]
    hfs_junction_width = place_hfs_vmat_pois(pd_hfs, hfs_poi_junction)
    hfs_pois = find_pois(pd_hfs)
    if make_junctions:
        # Add the midfield junctions
        make_midfield_junctions(pd_hfs, hfs_pois, junction_width=hfs_junction_width)
    if make_otvs:
        # Iterate over POIs and create OTVs
        for index, point in enumerate(hfs_pois):
            make_otv(pd_hfs, point, index, hfs_junction_width, hfs_pois)

    # Do the same for FFS
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    ffs_junction_width = place_ffs_vmat_pois(
        pd_ffs, ffs_poi_junction, len(hfs_pois))
    ffs_pois = find_pois(pd_ffs)
    if make_junctions:
        make_midfield_junctions(pd_ffs, ffs_pois, junction_width=ffs_junction_width)
    if make_otvs:
        for index, point in enumerate(ffs_pois):
            make_otv(pd_ffs, point, index, ffs_junction_width, ffs_pois)

    hfs_multiplan, ffs_multiplan = get_vmat_plan_defs(
        pd_hfs, hfs_pois, ffs_pois, nfx=nfx, rx=rx, )
    return hfs_multiplan, ffs_multiplan


def load_normal_mbs(pd_hfs: Pd, pd_ffs: Pd, quiet: bool = False) -> None:
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # TODO: CHECK FOR PLANNING STRUCTURES AND THEN ADD ANY MISSING
    # Loop through MBS rois, if present, pop.
    rois = [r.OfRoi.Name for r in
            pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name].RoiGeometries
            if r.HasContours]
    logging.debug('Type of MBS_ROIS is {} '.format(type(MBS_ROIS)))
    mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
    adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
    #
    # Begin making planning structures
    if mbs_list:
        pd_hfs.case.PatientModel.MBSAutoInitializer(
            MbsRois=mbs_list,
            CreateNewRois=True,
            Examination=pd_hfs.exam,
            UseAtlasBasedInitialization=True)
        connect.await_user_input('Review placement of MBS structures')

    if adapt_list:
        pd_hfs.case.PatientModel.AdaptMbsMeshes(
            Examination=pd_hfs.exam,
            RoiNames=adapt_list,
            CustomStatistics=None,
            CustomSettings=None)
    # Loop through MBS rois, if present, pop.
    rois = [r.OfRoi.Name for r in
            pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name].RoiGeometries
            if r.HasContours]
    mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
    adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
    # Try a repeat on FFS
    if mbs_list:
        pd_ffs.case.PatientModel.MBSAutoInitializer(
            MbsRois=mbs_list,
            CreateNewRois=False,
            Examination=pd_ffs.exam,
            UseAtlasBasedInitialization=True)
    if adapt_list:
        pd_hfs.case.PatientModel.AdaptMbsMeshes(
            Examination=pd_ffs.exam,
            RoiNames=adapt_list,
            CustomStatistics=None,
            CustomSettings=None)
    if not quiet:
        connect.await_user_input('Check the MBS loaded structures on both exams.')


def make_derived_rois(pd_hfs: Pd, pd_ffs: Pd) -> None:
    """
    Make the derived structures for the plan:
    LUNGS, KIDNEYS, SKIN_AVOIDANCE, EXTERNAL_SETUP,
    :param pd_hfs:
    :param pd_ffs:
    :return:
    """
    rois = {'Lungs': LUNGS, 'Skin_Avoid': SKIN_AVOIDANCE,
            'External_Setup': EXTERNAL_SETUP}
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    #
    # Build lung contours and avoidance on the HFS scan
    make_lung_contours(pd_hfs, color=[192, 192, 192])
    make_kidney_contours(pd_hfs, color=[192, 192, 192])
    #
    # Make the External_PRV10 set up structure
    try:
        pd_hfs.case.PatientModel.CreateRoi(
            Name=rois['External_Setup'],
            Color="255, 128, 0",
            Type="IrradiatedVolume",
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None)
    except Exception as e:
        if "There already exists" in "{}".format(e):
            pass

    # Create geometry for the External_PRV10
    pd_hfs.case.PatientModel.RegionsOfInterest[rois['External_Setup']] \
        .SetMarginExpression(
        SourceRoiName=EXTERNAL_NAME,
        MarginSettings={'Type': "Expand",
                        'Superior': EXTERNAL_SETUP_EXP,
                        'Inferior': EXTERNAL_SETUP_EXP,
                        'Anterior': EXTERNAL_SETUP_EXP,
                        'Posterior': EXTERNAL_SETUP_EXP,
                        'Right': EXTERNAL_SETUP_EXP,
                        'Left': EXTERNAL_SETUP_EXP})
    # Make skin subtraction
    n_tuples = [pd_hfs, pd_ffs]
    for n in n_tuples:
        make_wall(
            wall=rois['Skin_Avoid'],
            sources=["ExternalClean"],
            delta=SKIN_AVOIDANCE_CONTRACT,
            patient=n.patient,
            case=n.case,
            examination=n.exam,
            inner=True,
            struct_type="Organ")
        #
        n.case.PatientModel.RegionsOfInterest[rois['External_Setup']] \
            .UpdateDerivedGeometry(
            Examination=n.exam,
            Algorithm="Auto")


def make_structures(pd_hfs: Pd, pd_ffs: Pd, make_vmat_plan: bool, make_tomo_plan: bool, kidney_sparing: bool, testing: bool = False) -> None:
    hfs_scan_name = pd_hfs.exam.Name
    ffs_scan_name = pd_ffs.exam.Name
    make_derived_rois(pd_hfs, pd_ffs)
    if make_vmat_plan:
        # Load the Tomo Supports for the couch
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        AutoPlanOperations.load_supports(rso=pd_hfs,
                                         supports=["TrueBeamCouch", "Baseplate_Override_PMMA"],
                                         quiet=testing)
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TrueBeamCouch"],
                                         quiet=testing)
    elif make_tomo_plan:
        # Load TrueBeam couch and baseplate
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        AutoPlanOperations.load_supports(rso=pd_hfs,
                                         supports=["TomoCouch", "Baseplate_Override_PMMA"],
                                         quiet=testing)
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TomoCouch"],
                                         quiet=testing)

    register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, testing)
    if not testing:
        connect.await_user_input(
            'Check the fusion alignment of the boney anatomy in the hips.\n '
            'Approve the registration.\n Then continue script.')

    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    load_normal_mbs(pd_hfs, pd_ffs, quiet=testing)
    # Build lung contours & avoidance on the HFS scan
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    make_lung_contours(pd_hfs, color=[192, 192, 192])

    ffs_poi_junction, hfs_poi_junction = make_central_junction_structs(
        pd_hfs, pd_ffs, kidney_sparing=kidney_sparing)
