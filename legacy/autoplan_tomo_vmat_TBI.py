""" Automated Plan - Tomo/VMAT TBI

    This module contains various functions used in a TBI (Total Body Irradiation)
    treatment planning script.


    1. Launch the GUI and prompt the user for various input parameters related to the treatment.
       - Inputs: None
       - Outputs: User-selected parameters (e.g., number of fractions, total dose, treatment
       machine, etc.)

    2. Identify the HFS (Head First Supine) and FFS (Feet First Supine) CT scans in the patient's
    case.
       - Inputs: None
       - Outputs: HFS and FFS examination objects (`hfs_exam`, `ffs_exam`)

    3. Initialize variables to store information about the patient, case, and examinations for
    HFS and FFS.
       - Inputs: HFS and FFS examination objects
       - Outputs: `pd_hfs` and `patient_data` structures containing relevant information

    4. If FFS structure definitions are enabled:
       a. Load Tomo Supports (e.g., couch supports) for the HFS and FFS scans.
       b. Create a bounding box around the junction point on both scans and set the ROI (Region
       of Interest) there.
       c. Prompt the user to check the fusion alignment of the bony anatomy in the hips.
       d. Load normal MBS (Maximum Base of Support) structures for HFS and FFS.
       e. Build lung contours and avoidance structures on the HFS scan.
       f. Make TBI (Total Body Irradiation) planning structures on the HFS and FFS scans.

    5. If FFS auto-planning is enabled:
       a. Reset the primary and secondary scans to ensure FFS is the primary scan.
       b. Calculate the FFS isocenter coordinates based on the target.
       c. Define the FFS planning protocol with the necessary parameters.
       d. Perform FFS auto-planning and store the output plan and beamset.

    6. If making FFS isodose structures is enabled:
       a. Reset the primary and secondary scans to ensure FFS is the primary scan.
       b. Retrieve isodose names based on predefined junction regions.
       c. Map the junction point by copying non-empty isodose structures from FFS to HFS.
       d. Update the structures in the HFS scan to reflect the mapped isodose structures.

    7. If HFS auto-planning is enabled:
       a. Reset the primary and secondary scans to ensure HFS is the primary scan.
       b. Define the HFS planning protocol with the necessary parameters.
       c. Perform HFS auto-planning and store the output plan and beamset.

    8. If dose summation is enabled:
       a. If HFS and FFS beamsets are not specified, prompt the user to select them.
       b. Update the dose grid of the HFS and FFS beamsets based on the overlapping region.
       c. Recompute all doses in the FFS plan.
       d. Compute the dose on additional sets using the HFS beamset and fraction dose.
       e. Create a dose summation by combining the HFS fraction dose and FFS dose.

    9. Finish the execution of the code.


    Summary of functions:
    check_external: checks if an external file exists.
    check_structure_exists: checks if a structure exists.
    get_most_inferior: gets the most inferior coordinate from an array of coordinates.
    get_center: gets the center coordinate of a list of coordinates.
    find_junction_coords: finds the junction point coordinates between two CT scans.
    place_poi: places a point of interest (POI) on a scan.
    convert_array_to_transform: converts an array to a transform.
    determine_prefix: determines the prefix for a structure name.
    find_roi_prefix: finds the prefix for a ROI structure.
    update_all_remove_expression: updates all instances of a remove expression.
    make_junction_contour: makes the junction contour.
    make_kidneys_contours: makes the kidneys contours.
    make_lung_contours: makes the lung contours.
    get_roi_geometries: gets the geometries of ROIs.
    make_avoid: makes an avoid structure.
    make_ptv: makes a PTV structure.
    make_unsubtracted_dose_structures: makes unsubtracted dose structures.
    make_dose_structures: makes dose structures.
    reset_primary_secondary: resets the primary and secondary scan for a given patient.
    update_dose_grid: updates the dose grid for a given beamset.
    register_images: registers two CT scans.
    load_normal_mbs: loads the normal MBS settings.
    make_tbi_planning_structs: makes the planning structures for a TBI.
    check_fiducials: checks the fiducial points for a given scan.
    calc_ffs_iso: calculates the isocenter for the FFS (Free From Scan) planning.
    make_ffs_isodoses: makes the FFS isodose structures.
    get_new_grid: gets the new dose grid for a given beamset.
    find_transform: finds the transform between two scans.
    transform_poi: transforms a point of interest (POI).
    find_eval_dose: finds the evaluation dose for a given plan.
    tbi_gui: launches a GUI for TBI planning.
    main: runs all of the previous functions.

    Validation Notes:
    Test Patient: MR#

    Version Notes: 0.0.0 Original

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '07-Oct-2021'
__version__ = '0.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11 SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/AutoPlanTomoTBI'
__credits__ = []

import math
import logging
import connect
import sys
import os
import GeneralOperations
import AutoPlanOperations
import StructureOperations
from collections import namedtuple
import numpy as np
import PySimpleGUI as sg

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../general'))
from AutoPlan import autoplan

# Structure template defaults
COUCH_SUPPORT_STRUCTURE_TEMPLATE = "UW Support"
HFS_COUCH_SUPPORT_STRUCTURE_EXAMINATION = "Supine Patient"
COUCH_SOURCE_ROI_NAMES = {
    "TrueBeam": "TrueBeamCouch",
    "TomoTherapy": "TomoCouch"
}
LUNG_AVOID_NAME = "Lungs_m07"
LUNG_EVAL_NAME = "Lungs_Eval"
EXTERNAL_NAME = "ExternalClean"
AVOID_HFS_NAME = "Avoid_HFS"
AVOID_FFS_NAME = "Avoid_FFS"
PROTOCOL_NAME_TOMO = "UW Tomo TBI"
PROTOCOL_NAME_VMAT = "UW VMAT TBI"
ORDER_NAME_FFS_TOMO = "TomoTBI_FFS"
ORDER_NAME_FFS_VMAT = "VMAT_TBI_FFS"
ORDER_TARGET_NAME_FFS = "PTV_p_FFS"
ORDER_NAME_HFS_TOMO = "TomoTBI_HFS"
ORDER_NAME_HFS_VMAT = "VMAT_TBI_HFS"
ORDER_TARGET_NAME_HFS = "PTV_p_HFS"
BEAMSET_FFS_TOMO = "Tomo_TBI_FFS_FW50"
BEAMSET_HFS_TOMO = "Tomo_TBI_HFS_FW50"
BEAMSET_HFS_VMAT = "VMAT-HFS-TBI"
BEAMSET_FFS_VMAT = "VMAT-FFS-TBI"
TARGET_FFS = "PTV_p_FFS"
JUNCTION_PREFIX_FFS = "ffs_junction_"
JUNCTION_PREFIX_HFS = "hfs_junction_"
JUNCTION_POINT = "junction"
HFS_POI = 'HFS_POI'
FFS_POI = 'FFS_POI'
TARGET_HFS = "PTV_p_HFS"
FFS_OVERLAP = 10  # Minimum Overlap
HFS_OVERLAP = 12  # Minimum Overlap
ISO_GAP = 28  # TODO - Consider distributed based on isocenter number or bounding
# box
FW = 39  # 39 cm of MLC based field
JUNCTION_WIDTH = 1.25 * 9  # TODO: Instantiate in junction declaration
FFS_MAX_TREATMENT_LENGTH = 112
FFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past toes
FFS_SHIFT_BUFFER = 1
FFS_TREATMENT_LENGTH = \
    FFS_MAX_TREATMENT_LENGTH - FFS_OVERSHOOT - FFS_SHIFT_BUFFER - JUNCTION_WIDTH
HFS_MAX_TREATMENT_LENGTH = 110
HFS_SHIFT_BUFFER = 1
HFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past top of head
HFS_TREATMENT_LENGTH = \
    HFS_MAX_TREATMENT_LENGTH + HFS_OVERSHOOT + HFS_SHIFT_BUFFER + JUNCTION_WIDTH
MBS_ROIS = {'Kidney_L': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Left)",
                         'RoiName': r"Kidney_L",
                         'RoiColor': "58, 251, 170"},
            'Kidney_R': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Right)",
                         'RoiName': r"Kidney_R",
                         'RoiColor': "250, 57, 105"},
            'Lung_L': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Left)",
                       'RoiName': r"Lung_L",
                       'RoiColor': "253, 122, 9"},
            'Lung_R': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Right)",
                       'RoiName': r"Lung_R",
                       'RoiColor': "54, 247, 223"}}


def check_external(roi_list):
    if any(roi.OfRoi.Type == 'External' for roi in roi_list):
        logging.debug('External contour designated')
        return True
    else:
        logging.debug('No external contour designated')
        connect.await_user_input(
            'No External contour type designated. Give a contour'
            'an External type and continue '
            'script.')
        if any(roi.OfRoi.Type == 'External' for roi in roi_list):
            logging.debug('No external contour designated after'
                          'prompt recommend exit')
            return False


def check_structure_exists(case, structure_name, roi_list, option):
    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if option == 'Delete':
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            logging.warning("check_structure_exists: " +
                            structure_name + 'found - deleting and creating')
        elif option == 'Check':
            connect.await_user_input(
                f'Contour {structure_name} Exists - Verify its accuracy'
                ' and continue script')
        return True
    else:
        logging.info('check_structure_exists: '
                     f'Structure {structure_name} not found,'
                     'and will be created')
        return False


def get_most_inferior(case, exam, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = StructureOperations.check_roi(case, exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = case.PatientModel.StructureSets[exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = case.Examinations[exam.Name].PatientPosition
    if position == 'HFS':
        return bb_roi[0].z
    elif position == 'FFS':
        return bb_roi[0].z
    else:
        return None


def get_most_superior(case, exam, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most superior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = StructureOperations.check_roi(case, exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = case.PatientModel.StructureSets[exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    position = case.Examinations[exam.Name].PatientPosition
    logging.debug(f'Position:{position}, Bounding Box: {bb_roi[0].z}, {bb_roi[1].z}')
    if position == 'HFS':
        return bb_roi[1].z
    elif position == 'FFS':
        return bb_roi[1].z
    else:
        return None


def get_center(case, exam, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = StructureOperations.check_roi(case, exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = case.PatientModel.StructureSets[exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    c = {'x': bb_roi[0].x + (bb_roi[1].x - bb_roi[0].x) / 2,
         'y': bb_roi[0].y + (bb_roi[1].y - bb_roi[0].y) / 2,
         'z': bb_roi[0].z + (bb_roi[1].z - bb_roi[0].z) / 2}
    return c


def place_ffs_vmat_pois(pd_ffs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = StructureOperations.find_types(pd_ffs.case,
                                                     roi_type='External')

    iso_number = math.ceil(FFS_MAX_TREATMENT_LENGTH / (FW - FFS_OVERLAP))
    isocenter_distance = (FFS_MAX_TREATMENT_LENGTH - FW) / (iso_number - 1)
    # Junction location
    colors = ["127, 0, 255",
              "0, 0, 255",
              "0, 127, 255",
              "0, 255, 255",
              "0, 255, 127",
              "0, 255, 0",
              "127, 255, 0",
              "255, 255, 0",
              "255, 127, 0",
              "255, 0, 0",
              "255, 0, 255"]
    pois = []
    coords = {'x': junction.Point.x,
              'y': junction.Point.y}
    for i in range(iso_number):
        coords['z'] = junction.Point.z - FW / 2 - i * isocenter_distance
        poi = make_poi(pd_ffs.case, pd_ffs.exam,
                       coords, name=f"{FFS_POI}{i}", color=colors[i])
        pois.append(poi)
    return pois


def place_hfs_vmat_pois(pd_hfs, junction):
    # create a set of points that ensures coverage from junction point
    # to the limit of the ffs scan
    [external_name] = StructureOperations.find_types(pd_hfs.case,
                                                     roi_type='External')
    j_z = junction.Point.z
    hfs_ext_z = get_most_superior(pd_hfs.case,
                                  pd_hfs.exam,
                                  roi_name=external_name)
    iso_number = math.ceil(HFS_MAX_TREATMENT_LENGTH / (FW - HFS_OVERLAP))
    first_iso_position = j_z - JUNCTION_WIDTH + FW / 2
    last_iso_position = hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - FW / 2
    isocenter_distance = (last_iso_position - first_iso_position) \
                         / (iso_number - 1)

    logging.info(f'Distance from superior most point at {hfs_ext_z} '
                 f'to junction {junction.Point.z:.2f} '
                 f'is {hfs_ext_z - junction.Point.z:.2f} with '
                 f'spaced {isocenter_distance:.2f} requires '
                 f'{iso_number} isocenters')
    if hfs_ext_z + HFS_OVERSHOOT + HFS_SHIFT_BUFFER - junction.Point.z \
            >= HFS_MAX_TREATMENT_LENGTH:
        sys.exit('This patient may be too tall for tx')
    elif isocenter_distance >= FW - HFS_OVERLAP:
        sys.exit(f'Distancing incorrect: FW: {FW} with Overlap {HFS_OVERLAP} '
                 f'with greater computed isocenter distance {isocenter_distance}.')
    # Junction location
    colors = [
        "255, 0, 255", "255, 0, 0", "255, 127, 0",
        "255, 255, 0", "127, 255, 0", "0, 255, 0",
        "0, 255, 127", "0, 255, 255", "0, 127, 255",
        "0, 0, 255", "127, 0, 255", ]
    pois = []
    for i in range(iso_number):
        for p in pd_hfs.case.PatientModel.PointsOfInterest:
            if p.Name == f"{HFS_POI}{i}":
                p.DeleteRoi()
        coords = {'x': junction.Point.x, 'y': junction.Point.y}
        if i != iso_number - 1:
            coords['z'] = junction.Point.z - JUNCTION_WIDTH + FW / 2 \
                          + i * isocenter_distance
        else:
            coords['z'] = last_iso_position

        poi = make_poi(pd_hfs.case, pd_hfs.exam,
                       coords, name=f"{HFS_POI}{i}", color=colors[i])
        pois.append(poi)
    return pois


def make_poi(case, exam, coords, name, color):
    for p in case.PatientModel.PointsOfInterest:
        if p.Name == name:
            p.DeleteRoi()
    _ = StructureOperations.create_poi(
        case=case,
        exam=exam,
        coords=[coords['x'], coords['y'], coords['z']],
        name=name,
        color=color,
        diameter=1,
        rs_type='Control')
    return name


def find_hfff_junction_coords(pd_ffs):
    # Find the inferior most point from the ffs scan on the external
    [external_name] = StructureOperations.find_types(
        pd_ffs.case, roi_type='External')
    ffs_ext_z = get_most_inferior(pd_ffs.case,
                                  pd_ffs.exam,
                                  roi_name=external_name)
    _ = get_most_superior(pd_ffs.case,
                          pd_ffs.exam,
                          roi_name=external_name)
    center = get_center(pd_ffs.case, pd_ffs.exam, external_name)
    return {
        'x': 0,
        'y': center['y'],
        # Place the junction 1/2 field width away from the isocenter
        'z': ffs_ext_z - FFS_OVERSHOOT - FFS_SHIFT_BUFFER \
             + FFS_MAX_TREATMENT_LENGTH
    }


def place_hfff_junction_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    _ = StructureOperations.create_poi(
        case=pd_hfs.case,
        exam=pd_hfs.exam,
        coords=[coord_hfs['x'], coord_hfs['y'], coord_hfs['z']],
        name=JUNCTION_POINT,
        color='Red',
        diameter=1,
        rs_type='Control'
    )


def convert_array_to_transform(t):
    # Converts into the expected values for an RS transform dictionary
    return {'M11': t[0], 'M12': t[1], 'M13': t[2], 'M14': t[3],
            'M21': t[4], 'M22': t[5], 'M23': t[6], 'M24': t[7],
            'M31': t[8], 'M32': t[9], 'M33': t[10], 'M34': t[11],
            'M41': t[12], 'M42': t[13], 'M43': t[14], 'M44': t[15]}


def determine_prefix(exam):
    # Return HFS or FFS depending on exam orientation
    if exam.PatientPosition == 'HFS':
        return 'hfs'
    elif exam.PatientPosition == 'FFS':
        return 'ffs'


def find_roi_prefix(case, roi_match):
    # Return all structures whose name contains roi_prefix
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if roi_match in r.Name:
            found_roi.append(r.Name)
    return found_roi


def update_all_remove_expression(pdata, roi_name):
    # Update the expression for a contour on all exams then remove expression
    for e in pdata.case.PatientModel.StructureSets:
        pdata.case.PatientModel.RegionsOfInterest[roi_name].UpdateDerivedGeometry(
            Examination=pdata.case.Examinations[e.OnExamination.Name],
            Algorithm="Auto"
        )
    try:
        pdata.case.PatientModel.RegionsOfInterest[roi_name].DeleteExpression()
    except Exception as e:
        pass


def make_central_junction_contour(pdata, z_start,
                                  dim_si, dose_level, color=None):
    #  Make the Box Roi and junction region in the area of interest
    #
    # Get exam orientation
    if color is None:
        color = [192, 192, 192]
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.
    elif prefix == 'hfs':
        si = 1.
    else:
        sys.exit(f'Unknown patient orientation {prefix}')
    # Find the name of the external contour
    external_name = StructureOperations.find_types(pdata.case,
                                                   roi_type='External')[0]
    #
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(pdata.case, pdata.exam, roi_name=external_name)
    #
    # Make a box ROI that starts at z_start and ends at z_start + dim_si
    box_name = 'box_' + str(round(z_start, 1))
    box_geom = StructureOperations.create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=box_name,
        delete_existing=True)
    StructureOperations.exclude_from_export(pdata.case, box_name)
    #
    # Make the box geometry
    # Add an overlap factor to ensure no gaps within the junction to lead to
    # unintentional targeting
    overlap_box = 1.02
    box_geom.OfRoi.CreateBoxGeometry(
        Size={'x': abs(bb_external[1].x - bb_external[0].x) + 1,
              'y': abs(bb_external[1].y - bb_external[0].y) + 1,
              'z': dim_si * overlap_box},
        Examination=pdata.exam,
        Center={'x': c_external['x'],
                'y': c_external['y'],
                'z': z_start + si * dim_si / 2.},
        Representation='Voxels',
        VoxelSize=None)
    junction_name = prefix + "_junction_" + str(dose_level)
    logging.debug('Center of the box {}: is {}'.format(junction_name, z_start + si * dim_si / 2.))
    #
    # Boolean Definitions
    temp_defs = {
        "StructureName": junction_name,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Intersection",
        "SourcesA": [external_name, box_name],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    _ = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=junction_name,
        roi_type='Ptv')
    # update_all_remove_expression(patient_data=patient_data,roi_name=box_name)
    update_all_remove_expression(pdata=pdata, roi_name=junction_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_kidneys_contours(pdata, color=None):
    """
        Make the Kidneys
        """
    #
    # Boolean Definitions for Kidneys
    if color is None:
        color = [192, 192, 192]
    kidneys_defs = {
        "StructureName": "Kidneys",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Union",
        "SourcesA": ["Kidney_L", "Kidney_R"],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case,
        examination=pdata.exam, **kidneys_defs)


def make_lung_contours(pdata, color=None):
    """
    Make the Lungs and avoidance structures for lung
    """
    #
    # Boolean Definitions for Lungs
    if color is None:
        color = [192, 192, 192]
    lungs_defs = {
        "StructureName": "Lungs",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Union",
        "SourcesA": ["Lung_L", "Lung_R"],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lungs_defs)
    #
    # Boolean Definitions for Lung Avoidance
    lung_avoid_defs = {
        "StructureName": LUNG_AVOID_NAME,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Union",
        "SourcesA": ["Lungs"],
        "MarginTypeA": "Contract",
        "ExpA": [0.7] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_avoid_defs)
    #
    # Boolean Definitions for Lung Evaluation
    lung_eval_defs = {
        "StructureName": LUNG_AVOID_NAME,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Union",
        "SourcesA": ["Lungs"],
        "MarginTypeA": "Contract",
        "ExpA": [1.0] * 6,
        "OperationB": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **lung_eval_defs)


def get_roi_geometries(case, exam, roi_name):
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


def make_avoid(pdata, z_start, avoid_name, color=None):
    """ Build the avoidance structure used in making the PTV
        patient_data: kind of like PDiddy, but with data, see below
        z_start (float): starting location of the junction
        otv_name (str): Name of the structure to include all avoidance voxels
        avoid_color (opt list[r,g,b]): color of output structure
        Recipe for avoidance volume:
        Take the z_start, build a box that is everything above this position
        Find the intersection with the external.
        If this is the HFS scan, subtract the lung avoidance
    """
    #
    # Find the name of the external contour
    if color is None:
        color = [192, 192, 192]
    external_name = StructureOperations.find_types(pdata.case, roi_type='External')[0]
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.  # SI direction is negative for FFS
        bb_index = 1  # Starting coordinate of bounding box
        additional_avoidances = []  # No other avoidances in FFS orientation
    elif prefix == 'hfs':
        si = 1.  # SI direction is positive for HFS
        bb_index = 0  # Starting coordinate of bounding box
        additional_avoidances = [LUNG_AVOID_NAME]  # Subtract the lung volumes
    #
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name] \
        .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(pdata.case, pdata.exam, roi_name=external_name)
    #
    # Make a box ROI that starts at z_start and ends at z_start + dim_si
    box_name = 'avoid_box_' + str(round(z_start, 1))
    box_geom = StructureOperations.create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=box_name,
        delete_existing=True)
    StructureOperations.exclude_from_export(pdata.case, box_name)
    logging.debug('ROI name is {}'.format(box_geom.OfRoi.Name))
    si_box_size = abs(bb_external[bb_index].z + si * z_start)
    box_geom.OfRoi.CreateBoxGeometry(
        Size={'x': abs(bb_external[1].x - bb_external[0].x) + 1,
              'y': abs(bb_external[1].y - bb_external[0].y) + 1,
              'z': si_box_size},
        Examination=pdata.exam,
        Center={'x': c_external['x'],
                'y': c_external['y'],
                'z': z_start - si * si_box_size / 2.},
        Representation='Voxels',
        VoxelSize=None)
    #
    # Boolean Definitions for Avoidance
    temp_defs = {
        "StructureName": avoid_name,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Intersection",
        "SourcesA": [external_name, box_name],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": additional_avoidances,
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "None",
        "MarginTypeR": "Expand",
        "ExpR": [0., 0., 0.7, 0.7, 0.7, 0.7, 0.7],  # Capture little ditzels evading the external
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    # update_all_remove_expression(patient_data=patient_data,roi_name=box_name)
    update_all_remove_expression(pdata=pdata, roi_name=avoid_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


# TODO: Make PTV_p_Eval_HFS(-skin and 7 mm lungs)
#       Make PTV_p_Eval_FFS(-skin)

def make_ptv(pdata, junction_prefix, avoid_name, color=None):
    # Find all contours matching prefix and along with otv_name return the external minus these
    # objects
    #
    # Get exam orientation
    if color is None:
        color = [192, 192, 192]
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.
        eval_name = "PTV_p_FFS_Eval"
    elif prefix == 'hfs':
        si = 1.
        eval_name = "PTV_p_HFS_Eval"
    #
    # PTV_name
    ptv_name = "PTV_p_" + prefix.upper()
    external_name = StructureOperations.find_types(pdata.case, roi_type='External')[0]
    roi_exclude = find_roi_prefix(pdata.case, roi_match=junction_prefix)
    roi_exclude.append(avoid_name)
    #
    # Boolean Definitions
    temp_defs = {
        "StructureName": ptv_name,
        "ExcludeFromExport": False,
        "VisualizeStructure": False,
        "StructColor": color,
        "OperationA": "Intersection",
        "SourcesA": [external_name],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": roi_exclude,
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "Subtraction",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    _ = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=ptv_name,
        roi_type='Ptv')
    # Make Eval structure
    # Boolean Definitions
    roi_exclude.append('Avoid_Skin_PRV05')
    roi_exclude.append('Lungs')
    temp_defs = {
        "StructureName": eval_name,
        "ExcludeFromExport": False,
        "VisualizeStructure": True,
        "StructColor": [255, 0, 0],
        "OperationA": "Intersection",
        "SourcesA": [external_name],
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": roi_exclude,
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "Subtraction",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    _ = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=eval_name,
        roi_type='Ptv')
    pdata.case.PatientModel.RegionsOfInterest[eval_name].DeleteExpression()


def make_unsubtracted_dose_structures(pdata, rx, dose_thresholds_normalized):
    """
    Make the structure for the dose threshold supplied
    makes unsubtracted_doses (RS Region of Interest Object) with name like <5%Rx>
    patient_data: exactly the same as pdiddy
    rx (float): Prescription (normalizing) dose in cGy
    dose_thresholds_normalized ({dose_roi_names: dose_levels(int)}): percentages of prescription
    dose
    """
    for n, d in dose_thresholds_normalized.items():
        threshold_level = (float(d) / 100.) * float(rx)  # Threshold in cGy
        unsubtracted_roi_name = str(d) + '%Rx'
        raw_name = n + '_raw'
        raw_geometry = StructureOperations.create_roi(
            case=pdata.case,
            examination=pdata.exam,
            roi_name=raw_name,
            delete_existing=True)
        # Get the Region of Interest object
        raw_roi = pdata.case.PatientModel.RegionsOfInterest[raw_name]
        # Make an roi geometry that is at least the threshold level dose
        try:
            raw_roi.CreateRoiGeometryFromDose(
                DoseDistribution=pdata.plan.TreatmentCourse.TotalDose,
                ThresholdLevel=threshold_level)
        except Exception as e:
            logging.debug('Unable to make dose level {}'.format(threshold_level))
        #
        # Initialize the output
        dose_geometry = StructureOperations.create_roi(
            case=pdata.case,
            examination=pdata.exam,
            roi_name=n,
            delete_existing=True)
        # Get the Region of Interest object
        dose_roi = pdata.case.PatientModel.RegionsOfInterest[n]
        temp_defs = {
            "StructureName": n,
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": [192, 192, 192],
            "OperationA": "Intersection",
            "SourcesA": [EXTERNAL_NAME, raw_roi.Name],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Control",
        }
        StructureOperations.make_boolean_structure(
            patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
        # Process the dose roi
        geom = get_roi_geometries(pdata.case, pdata.exam, dose_roi.Name)
        if geom:
            if geom.HasContours():
                dose_roi.DeleteExpression()
                dose_roi.VolumeThreshold(
                    InputRoi=dose_roi,
                    Examination=pdata.exam,
                    MinVolume=1,
                    MaxVolume=200000,
                )
        else:
            logging.debug('Deleting roi {} due to empty'.format(dose_roi.Name))
            dose_roi.DeleteRoi()

        # Clean up
        raw_roi.DeleteRoi()


def make_dose_structures(pdata, isodoses, rx):
    # make doses from structs and return names of created rois
    # The resulting structs will be structures of at least the
    # defined isodose and at most the next highest level
    # isodoses {junction_name_on_ffs_scan: (110%, 100%, 95% Desired Dose in Junction)}
    # return subtracted_isodoses (list): all subtracted and intersected isodoses
    subtract_higher = False  # Used to skip the boolean on the highest level isodose
    [external_name] = StructureOperations.find_types(pdata.case,
                                                     roi_type='External')
    #
    # Resort isodoses, highest to lowest
    isodose_contours = []
    # sorted_isodoses = sorted(isodoses, reverse=True)
    # Avoid circular dependencies by storing raw doses, and delete when finished
    delete_rois = []
    # The output: subtracted doses
    #
    # Loop over each junction contour, starting with the highest dose level
    # and subtracting higher doses for each
    for k, v in isodoses.items():
        # k is prefix + 10 + %Rx: v is (20,10,5)
        # Make a subtracted dose to roi
        # For each dose level defined in the tuple, create structure that overlaps with the
        # junction, removing higher dose levels as we go
        subtracted_isodoses = []  # TODO: Test with just the highest level
        subtract_higher = False  # Flag to skip the first isodose
        for d in v:
            # threshold_level = (float(d)/100.) * rx #in cGy
            #
            # Make unsubtracted (raw) dose
            raw_dose_name = str(d) + '%Rx'
            if raw_dose_name not in delete_rois:
                delete_rois.append(raw_dose_name)
            # Isodose in junction is named:
            # junction_prefix + xx% + _dose_ + %dose, e.g. ffs_junction_10%Rx_dose_5%Rx
            roi_name = k + '_dose_' + raw_dose_name
            roi_geometry = StructureOperations.create_roi(
                case=pdata.case,
                examination=pdata.exam,
                roi_name=roi_name,
                delete_existing=True)
            # Boolean Definitions
            temp_defs = {
                "StructureName": roi_name,
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": [192, 192, 192],
                "OperationA": "Intersection",
                "SourcesA": [k, raw_dose_name, external_name],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                # "SourcesB": subtracted_isodoses,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                # "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Control",
            }
            if subtract_higher:
                temp_defs.update(
                    [("SourcesB", subtracted_isodoses),
                     ("OperationResult", "Subtraction")]
                )
                StructureOperations.make_boolean_structure(
                    patient=pdata.patient, case=pdata.case,
                    examination=pdata.exam, **temp_defs)
                subtracted_isodoses.append(roi_name)
            else:
                temp_defs.update(
                    [("SourcesB", []),
                     ("OperationResult", "None")]
                )
                StructureOperations.make_boolean_structure(
                    patient=pdata.patient, case=pdata.case,
                    examination=pdata.exam, **temp_defs)
                subtracted_isodoses.append(roi_name)
                #
                # Check for empties on this high isodose then try one more dose level
                if not all(StructureOperations.check_roi(pdata.case, pdata.exam, roi_name)):
                    delete_rois.append(roi_name)
                    # TODO: See if there is a tidier way to functionalize this and the above
                    # could just add a 4th dose level: 95, 100, 110, 115 of junction dose
                    raw_dose_name = str(d - 5) + '%Rx'
                    if raw_dose_name not in delete_rois:
                        delete_rois.append(raw_dose_name)
                    roi_name = k + '_dose_' + raw_dose_name
                    roi_geometry = StructureOperations.create_roi(
                        case=pdata.case,
                        examination=pdata.exam,
                        roi_name=roi_name,
                        delete_existing=True)
                    temp_defs["StructureName"] = roi_name
                    temp_defs["SourcesA"] = [k, raw_dose_name, external_name]
                    StructureOperations.make_boolean_structure(
                        patient=pdata.patient,
                        case=pdata.case,
                        examination=pdata.exam,
                        **temp_defs)
                    junct_roi = pdata.case.PatientModel.RegionsOfInterest[roi_name]
                    junct_roi.DeleteExpression()
                    try:
                        junct_roi.VolumeThreshold(
                            InputRoi=junct_roi,
                            Examination=pdata.exam,
                            MinVolume=1,
                            MaxVolume=200000)
                    except:
                        logging.debug('{} is empty'.format(roi_name))
                    subtracted_isodoses.append(roi_name)
            subtract_higher = True  # Start subtracting higher dose values
            isodose_contours.append(roi_name)
    for d in delete_rois:
        pdata.case.PatientModel.RegionsOfInterest[d].DeleteRoi()
    return isodose_contours


def reset_primary_secondary(exam1, exam2):
    # Resets exam 1 as primary and exam2 as secondary
    exam1.SetPrimary()
    exam2.SetSecondary()


def update_dose_grid(pdata):
    # TODO: This still doesn't work. The two dose grids need to be compared using a common
    # point on the patient since the dose grid is relative to the patient on the two scans.

    pm = pdata.case.PatientModel
    dg = pdata.plan.GetDoseGrid()
    bb = [{k: dg.Corner[k] + dg.VoxelSize[k] * dg.NrVoxels[k] for k in dg.Corner.keys()},
          dg.Corner]
    types = ['Ptv', 'Support', 'External']
    #
    # Loop over all structure sets looking for support, external or target types
    # For all found, compute a bounding box and expand the current dose grid if necessary.
    for s in pm.StructureSets:
        for r in s.RoiGeometries:
            if r.OfRoi.Type in types:
                try:
                    bs = s.RoiGeometries[r.OfRoi.Name].GetBoundingBox()
                    for c, v in bs[0].items():
                        if v < bb[0][c]:
                            bb[0][c] = v
                            print('{}:{} is {} < {} '.format(r.OfRoi.Name, c, v, bb[0][c]))
                    for c, v in bs[1].items():
                        if v > bb[1][c]:
                            bb[1][c] = v
                            print('{}:{} is {} > {} '.format(r.OfRoi.Name, c, v, bb[1][c]))
                except Exception as e:
                    no_geom_set = "no geometry set for ROI"
                    if no_geom_set in "{}".format(e.Message):
                        pass
                    else:
                        print(e.Message)

    vs = dg.VoxelSize
    span = {k: abs(bb[1][k] - bb[0][k]) for k in bb[1].keys()}
    update_number_voxels = {k: math.ceil(v / vs[k]) for (k, v) in span.items()}
    pdata.plan.UpdateDoseGrid(Corner=bb[0],
                              VoxelSize=vs,
                              NumberOfVoxels=update_number_voxels)


def check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    approved = False
    # Look through registration objects
    for r in pd_ffs.case.Registrations:
        try:
            _ = r.RegistrationSource
        except AttributeError:
            logging.debug('No approved registrations found')
            approved = False
            break
        if r.RegistrationSource.FromExamination.Name == ffs_scan_name \
                and r.RegistrationSource.ToExamination.Name == hfs_scan_name \
                and r.Review:
            try:
                if r.Review.ApprovalStatus == 'Approved':
                    approved = True
            except AttributeError:
                approved = False
            break
    return approved


def verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    # Check for existing registration, if approved return approved
    # Otherwise look for existing registrations and if they are not approved
    # prompt user to approve them or to allow them to be overwritten
    registrations = False
    # Look through registration objects
    approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        for s in pd_ffs.case.StructureRegistrations:
            if s.FromExamination.Name == hfs_scan_name \
                    and s.ToExamination.Name == ffs_scan_name:
                registrations = True
                if s.Review:
                    try:
                        if s.Review.ApprovalStatus == 'Approved':
                            approved = True
                    except AttributeError:
                        approved = False
                break
    if approved:
        return approved
    else:
        if registrations:
            connect.await_user_input('An existing FFS to HFS registration has been'
                                     ' found.\n Approve it to avoid an overwrite')
            approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)
    return approved


def register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, ):
    # TODO: TESTING GET RID OF THIS
    testing = True
    if not testing:
        # Make external clean on both
        ext_clean = StructureOperations.make_externalclean(
            patient=pd_hfs.patient,
            case=pd_hfs.case,
            examination=pd_hfs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )
        # If this breaks on a clean scan, we will want to see if this exam has contours
        ext_clean = StructureOperations.make_externalclean(
            patient=pd_ffs.patient,
            case=pd_ffs.case,
            examination=pd_ffs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )

    approved = verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=False,
            InitializeImages=True,
            FocusRoisNames=[],
            RegistrationName=None)

        # Refine on bones
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=True,
            InitializeImages=False,
            FocusRoisNames=[],
            RegistrationName=None)
        # Also create a bounding box on both images about the junction point and set the ROI there


def load_normal_mbs(pd_hfs, pd_ffs):
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
    connect.await_user_input('Check the MBS loaded structures on both exams.')


def make_derived_rois(pd_hfs, pd_ffs):
    """
    Make the derived structures for the plan:
    Lungs, Avoid_Skin_PRV05, External_PRV10,
    :param pd_hfs:
    :param pd_ffs:
    :return:
    """
    rois = {'Lungs': 'Lungs', 'Skin_Avoid': 'Avoid_Skin_PRV05',
            'External_Setup': 'External_PRV10'}
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    #
    # Build lung contours and avoidance on the HFS scan
    make_lung_contours(pd_hfs, color=[192, 192, 192])
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
                        'Superior': 1.0,
                        'Inferior': 1.0,
                        'Anterior': 1.0,
                        'Posterior': 1.0,
                        'Right': 1.0,
                        'Left': 1.0})
    # Make skin subtraction
    n_tuples = [pd_hfs, pd_ffs]
    for n in n_tuples:
        StructureOperations.make_wall(
            wall=rois['Skin_Avoid'],
            sources=["ExternalClean"],
            delta=0.5,
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


def make_central_junction_structs(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name):
    """

    Args:
        pd_hfs: hfs named tuple
        pd_ffs: ffs named tuple
        hfs_scan_name:  hfs exam name
        ffs_scan_name:  ffs exam name

    Returns:

    """
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # TODO: Rename Sensibly
    lower_point = find_hfff_junction_coords(pd_ffs)
    place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=lower_point)
    # Get the rigid registration
    ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        FromExamination=ffs_scan_name,
        ToExamination=hfs_scan_name)
    # Convert it to the transform dictionary
    trans_f2h = convert_array_to_transform(ffs_to_hfs)
    # Map the junction point
    pd_ffs.case.MapPoiGeometriesRigidly(
        PoiGeometryNames=[JUNCTION_POINT],
        CreateNewPois=False,
        ReferenceExaminationName=ffs_scan_name,
        TargetExaminationNames=[hfs_scan_name],
        Transformations=[trans_f2h])
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]

    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]

    # IsoDose levels:
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = JUNCTION_WIDTH / len(j_i)
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
        make_central_junction_contour(
            pd_ffs,
            z_start=ffs_poi_junction.Point.z - dim_si * float(i),
            dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx",
            color=dose_levels[j_i[i]])
    make_avoid(
        pd_ffs, z_start=ffs_poi_junction.Point.z, avoid_name=AVOID_FFS_NAME)
    make_ptv(
        pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS,
        avoid_name=AVOID_FFS_NAME)
    #
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    for i in range(len(j_i)):
        z_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i) - i)
        logging.debug('Z location for Junction {} is {}'.format(str(j_i[i]), z_start))
        make_central_junction_contour(pd_hfs,
                                      z_start=z_start,
                                      dim_si=dim_si,
                                      dose_level=str(int(j_i[i])) + "%Rx",
                                      color=dose_levels[j_i[i]])
    #
    # HFS avoid starts at junction point - number of dose levels * dim_si
    hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
    # TODO: underive and delete geometry on avoid volumes defined on incorrect scans
    #       Delete all empty geometriest for junction ffs doses immediately after they are all
    #       created
    #  False     Create HFS and FFS eval structs for treatment
    #       ADD prompt for dir block on avoidances
    # then map them over
    make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
    make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS, avoid_name=AVOID_HFS_NAME)
    return ffs_poi_junction, hfs_poi_junction


def check_fiducials(pd, fiducial_name):
    # Check all potential exams to ensure the fiducial is defined
    fiducial_check = []
    pois = [p.Name for p in pd.case.PatientModel.PointsOfInterest]
    if fiducial_name not in pois:
        return False, False
    for ss in pd.case.PatientModel.StructureSets:
        if not ss.PoiGeometries[fiducial_name].Point:
            fiducial_check.append(False)
        else:
            fiducial_check.append(True)
    return True, all(fiducial_check)


#
# NOT USED YET - CONVERT TO CONTOUR BASED JUNCTIONS
def calculate_junction(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name):
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # TODO: Rename Sensibly
    lower_point = find_hfff_junction_coords(pd_ffs)
    place_hfff_junction_poi(pd_hfs=pd_ffs, coord_hfs=lower_point)
    # Get the rigid registration
    ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        FromExamination=ffs_scan_name,
        ToExamination=hfs_scan_name)
    # Convert it to the transform dictionary
    trans_f2h = convert_array_to_transform(ffs_to_hfs)
    # Map the junction point
    pd_ffs.case.MapPoiGeometriesRigidly(
        PoiGeometryNames=[JUNCTION_POINT],
        CreateNewPois=False,
        ReferenceExaminationName=ffs_scan_name,
        TargetExaminationNames=[hfs_scan_name],
        Transformations=[trans_f2h])
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]

    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # Return poi rs object
    return ({'x': hfs_poi_junction.Point.x,
             'y': hfs_poi_junction.Point.y,
             'z': hfs_poi_junction.Point.z},
            {'x': ffs_poi_junction.Point.x,
             'y': ffs_poi_junction.Point.y,
             'z': ffs_poi_junction.Point.z})


def make_generic_planning_structures(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name):
    hfs_central_junction, ffs_central_junction = calculate_junction(pd_hfs, pd_ffs,
                                                                    hfs_scan_name,
                                                                    ffs_scan_name)
    make_avoid(pd_ffs,
               z_start=ffs_central_junction['z'],
               avoid_name=AVOID_FFS_NAME)
    make_ptv(
        pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS,
        avoid_name=AVOID_FFS_NAME)
    z_junct = ffs_central_junction['z']
    make_generic_junction_structs(pd_ffs, z_junct, pt_orientation='FFS')
    # Repeat for HFS
    # HFS avoid starts at junction point - number of dose levels * dim_si
    z_junct = hfs_central_junction['z']
    hfs_avoid_start = hfs_central_junction['z'] - JUNCTION_WIDTH
    make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
    make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS, avoid_name=AVOID_HFS_NAME)
    make_generic_junction_structs(pd_hfs, z_junct, pt_orientation='HFS')


def make_generic_junction_structs(rs_obj, z_junct, pt_orientation):
    """

    Args:
        pd_hfs: hfs named tuple
        patient_data: ffs named tuple
        hfs_scan_name:  hfs exam name
        ffs_scan_name:  ffs exam name

    Returns:

    """

    # IsoDose levels:
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = JUNCTION_WIDTH / len(j_i)
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
        if pt_orientation == 'HFS':
            z_start = z_junct - dim_si * float(len(j_i) - i)
        elif pt_orientation == 'FFS':
            z_start = z_junct - dim_si * float(i)
        else:
            z_start = None
        make_central_junction_contour(
            rs_obj,
            z_start=z_start,
            dim_si=dim_si,
            dose_level=str(int(j_i[i])) + "%Rx",
            color=dose_levels[j_i[i]])


#
# END


def tomo_calc_ffs_iso(pd_ffs, target):
    fiducial_point_name = 'SimFiducials'
    point_exists, point_defined = check_fiducials(pd_ffs, fiducial_name=fiducial_point_name)
    if not point_exists:
        AutoPlanOperations.place_fiducial(rso=pd_ffs, poi_name='SimFiducials')
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it there too')
        point_exists, point_defined = check_fiducials(pd_ffs, fiducial_name=fiducial_point_name)
    elif not point_defined:
        connect.await_user_input(
            'Place SimFiducial point in FFS, then toggle to HFS and place it there too')

    pm = pd_ffs.case.PatientModel
    sim_coords = pm.StructureSets[pd_ffs.exam.Name].LocalizationPoiGeometry.Point
    target_coords = pm.StructureSets[pd_ffs.exam.Name].RoiGeometries[target].GetCenterOfRoi()
    iso_coord = {'x': 0., 'y': target_coords['y'], 'z': sim_coords['z']}
    iso_name = pm.GetUniqueRoiName(DesiredName='ROI_ffs_iso')
    pm.CreateRoi(Name=iso_name,
                 Color='Pink',
                 Type='Control')
    iso_roi = pm.RegionsOfInterest[iso_name]
    iso_roi.CreateSphereGeometry(Radius=1.0,
                                 Examination=pd_ffs.exam,
                                 Center=iso_coord,
                                 Representation='Voxels',
                                 VoxelSize=0.01)
    return iso_name


def make_ffs_isodoses(pd_hfs, pd_ffs, rx, prefix):
    #
    ffs_scan_name = pd_ffs.exam.Name
    hfs_scan_name = pd_hfs.exam.Name
    ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        FromExamination=ffs_scan_name,
        ToExamination=hfs_scan_name)
    # Convert it to the transform dictionary
    trans_f2h = convert_array_to_transform(ffs_to_hfs)
    # If we pair the junctions and isodoses up front we can do this as one iteration
    # d_i = {<junction_region>: (low95%, med100%, high110%)}
    # Isodoses to get:
    d_i = [5, 10, 15, 20, 25, 30, 35, 40, 45,
           50, 55, 60, 65, 70, 75, 80, 85, 90,
           95, 100, 105, 110, 115]
    #
    # Get clean unsubtracted doses
    doses = dict([(str(d) + '%Rx', d) for d in d_i])
    make_unsubtracted_dose_structures(pd_ffs, rx, doses)
    # Junctions
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    # construct pairs
    j_names = dict([(prefix + str(j) + '%Rx', (j + 10, j, j - 5)) for j in j_i])
    #
    # Generate subtracted dose values
    logging.debug(f'J_Names {j_names} are input to make_dose')
    isodose_names = make_dose_structures(pd_ffs, isodoses=j_names, rx=rx)
    non_empty_isodose_names = []
    for idn in isodose_names:
        dose_roig = get_roi_geometries(pd_ffs.case, pd_ffs.exam, idn)
        if dose_roig.HasContours():
            non_empty_isodose_names.append(idn)
    pd_hfs.case.MapRoiGeometriesRigidly(
        RoiGeometryNames=non_empty_isodose_names,
        CreateNewRois=False,
        ReferenceExaminationName=ffs_scan_name,
        TargetExaminationNames=[hfs_scan_name],
        Transformations=[trans_f2h])


def get_new_grid(case, beamset_a, beamset_b):
    # Return a dose grid for beamset_a that includes all voxels used in beamset_b
    # Update the dose grid for plan a using b's grid.
    dg_a = beamset_a.GetDoseGrid()
    dg_b = beamset_b.GetDoseGrid()
    # Find minimum and maximum extent of beamset_a dose grid
    min_a = {'x': dg_a.Corner['x'],
             'y': dg_a.Corner['y'],
             'z': dg_a.Corner['z']}
    max_a = {'x': dg_a.Corner['x'] + dg_a.VoxelSize['x'] * dg_a.NrVoxels['x'],
             'y': dg_a.Corner['y'] + dg_a.VoxelSize['y'] * dg_a.NrVoxels['y'],
             'z': dg_a.Corner['z'] + dg_a.VoxelSize['z'] * dg_a.NrVoxels['z']}
    # Find minimum and maximum extent of beamset_b dose grid
    min_b = {'x': dg_b.Corner['x'],
             'y': dg_b.Corner['y'],
             'z': dg_b.Corner['z']}
    max_b = {'x': dg_b.Corner['x'] + dg_b.VoxelSize['x'] * dg_b.NrVoxels['x'],
             'y': dg_b.Corner['y'] + dg_b.VoxelSize['y'] * dg_b.NrVoxels['y'],
             'z': dg_b.Corner['z'] + dg_b.VoxelSize['z'] * dg_b.NrVoxels['z']}
    # Transform beamset_b dose grid extrema to image set a coordinates
    t_b_min = transform_poi(case, min_b, beamset_b, beamset_a)
    t_b_max = transform_poi(case, max_b, beamset_b, beamset_a)
    # Find the inferior-most grid
    lower_corner = {'x': min(min_a['x'], t_b_min['x']),
                    'y': min(min_a['y'], t_b_min['y']),
                    'z': min(min_a['z'], t_b_min['z']),
                    }
    # Find the superior-most grid
    upper_corner = {'x': max(max_a['x'], t_b_max['x']),
                    'y': max(max_a['y'], t_b_max['y']),
                    'z': max(max_a['z'], t_b_max['z']),
                    }
    new_grid = {'Corner': {'x': lower_corner['x'], 'y': lower_corner['y'], 'z': lower_corner['z']},
                'NrVoxels': {
                    'x': math.ceil(upper_corner['x'] - lower_corner['x']) / dg_a.VoxelSize['x'],
                    'y': math.ceil(upper_corner['y'] - lower_corner['y']) / dg_a.VoxelSize['y'],
                    'z': math.ceil(upper_corner['z'] - lower_corner['z']) / dg_a.VoxelSize['z']},
                'VoxelSize': dg_a.VoxelSize}
    return new_grid


def find_transform(case, from_name, to_name):
    for r in case.Registrations:
        if r.StructureRegistrations[0].FromExamination.Name == from_name \
                and r.StructureRegistrations[0].ToExamination.Name == to_name:
            return r
    return None


def transform_poi(case, point, from_name, to_name):
    reg = case.GetTransform(FromFrameOfReference=from_name.FrameOfReference,
                            ToFrameOfReference=to_name.FrameOfReference)
    if reg is None:
        reg = case.GetTransform(FromFrameOfReference=to_name.FrameOfReference,
                                ToFrameOfReference=from_name.FrameOfReference)
        if reg is None:
            sys.exit(f'No Registration between {from_name} to {to_name}')
        else:
            reg_inv = np.reshape(reg, (4, 4))
            M = np.linalg.inv(reg_inv)
    else:
        M = np.reshape(reg, (4, 4))

    x = np.array([point['x'], point['y'], point['z'], 1])
    x_p = np.matmul(M, np.transpose(x)).tolist()
    return {'x': x_p[0], 'y': x_p[1], 'z': x_p[2]}


def find_eval_dose(case, beamset_name, exam_name):
    for fe in case.TreatmentDelivery.FractionEvaluations:
        for de in fe.DoseOnExaminations:
            for d in de.DoseEvaluations:
                if d.ForBeamSet.DicomPlanLabel == beamset_name and de.OnExamination.Name == \
                        exam_name:
                    return d


def find_beamset(case, beamset_name):
    for p in case.TreatmentPlans:
        for bs in p.BeamSets:
            if bs.DicomPlanLabel == beamset_name:
                return p, bs
    return None


def tbi_gui(bypass=False):
    """
    Displays a GUI for TBI planning parameter selection.

    Returns:
        Dictionary: A dictionary containing the user's selections.
    """

    if bypass:
        connect.await_user_input('System is in testing mode. No clinical use')
        logging.warning("System in testing mode. No clinical use")
        return {
            '-NFX-': 4,
            '-TDOSE-': 800,
            '-MACHINE-': "HDA0488",
            '-VMAT-MACHINE-': "TrueBeam_NoTrack",
            '-THI-': False,
            '-VMAT-': True,
            '-FFS STRUCTURES-': False,
            '-FFS PLAN-': False,
            '-FFS ISODOSE-': False,
            '-HFS PLAN-': True,
            '-SUM DOSE-': True,
        }

    # User Prompt for Dose/Fractions
    gui_layout = [
        [sg.T('Enter Number of Fractions'), sg.In(key='-NFX-')],
        [sg.T('Enter TOTAL Dose in cGy'), sg.In(key='-TDOSE-')],
        [sg.T('Enter Tomo Treatment Machine'), sg.Combo(["HDA0488"],
                                                        key='-MACHINE-')],
        [sg.T('Enter VMAT Treatment Machine'), sg.Combo(["TrueBeam_NoTrack",
                                                         "TrueBeam"],
                                                        key='-VMAT-MACHINE-')],
        [sg.Checkbox('Generate THI Plan', default=True, key='-THI-')],
        [sg.Checkbox('Generate VMAT Plan', default=True, key='-VMAT-')],
        [sg.Checkbox('Generate FFS Planning Structures', default=True, key='-FFS STRUCTURES-')],
        [sg.Checkbox('Generate FFS Plan', default=True, key='-FFS PLAN-')],
        [sg.Checkbox('Make FFS Isodose Structures', default=True, key='-FFS ISODOSE-')],
        [sg.Checkbox('Make HFS Plan', default=True, key='-HFS PLAN-')],
        [sg.Checkbox('Make Dose Summation', default=True, key='-SUM DOSE-')],
        [sg.B('OK'), sg.B('Cancel')]
    ]

    window = sg.Window('AUTO TBI', gui_layout, default_element_size=(40, 1), grab_anywhere=False)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            selections = {}
            break
        elif event == "OK":
            selections = values
            break
    window.close()

    if selections == {}:
        sys.exit('TBI Script was cancelled')
    else:
        return selections


def main():
    """
    Runs a series of functions to perform TBI planning and dose summation.

    Pseudocode:
    1. Call tbi_gui() function to obtain user input.
    2. Retrieve the necessary variables from user input.
    3. Find HFS and FFS scans, assign them to variables.
    4. Initialize a named tuple for the patient, case, exam, plan, and beamset.
    5. If requested by the user, load couch supports and build lung contours and avoidance on the
    HFS scan.
    6. If requested by the user, plan FFS and HFS.
    7. If requested by the user, make isodoses for FFS.
    8. If requested by the user, perform dose summation.

    Returns: None
    """
    # TODO: Set treatment limit settings on beams for jaw too wide issue
    # Prerequisites for operations:
    # generate_thi_ffs_plan: External, AvoidSkin, External+1
    # generate_vmat_ffs_plan:
    # generate_planning_structs: Lung_L/R, Kidney_L/R,
    # Launch gui
    testing = False
    tbi_selections = tbi_gui(bypass=testing)

    nfx = tbi_selections['-NFX-']
    rx = tbi_selections['-TDOSE-']
    do_structure_definitions = tbi_selections['-FFS STRUCTURES-']
    ffs_autoplan = tbi_selections['-FFS PLAN-']
    make_ffs_isodose_structs = tbi_selections['-FFS ISODOSE-']
    hfs_autoplan = tbi_selections['-HFS PLAN-']
    dose_summation = tbi_selections['-SUM DOSE-']
    tomo_machine = tbi_selections['-MACHINE-']
    vmat_machine = tbi_selections['-VMAT-MACHINE-']
    make_tomo_plan = tbi_selections['-THI-']
    make_vmat_plan = tbi_selections['-VMAT-']

    # Look for HFS/FFS Scans
    temp_case = GeneralOperations.find_scope(level='Case')
    temp_exam = GeneralOperations.find_scope(level='Examination')
    hfs_scan_name = None
    ffs_scan_name = None
    for e in temp_case.Examinations:
        if e.PatientPosition == 'HFS':
            hfs_exam = e
            e.Name = 'HFS'
            hfs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))

        elif e.PatientPosition == 'FFS':
            ffs_exam = e
            e.Name = 'FFS'
            ffs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))
        else:
            sys.exit('unknown exam orientation')
    if not all([hfs_scan_name, ffs_scan_name]):
        sys.exit('This script requires a head first and feet first scan')
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd_hfs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=hfs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=None,
                beamset=None)

    pd_ffs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=ffs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=None,
                beamset=None)

    if do_structure_definitions:
        # TODO: Integrate VMAT option here for TrueBeam couch
        #
        make_derived_rois(pd_hfs, pd_ffs)
        if make_vmat_plan:
            # Load the Tomo Supports for the couch
            AutoPlanOperations.load_supports(rso=pd_hfs,
                                             supports=["TrueBeamCouch", "Baseplate_Override_PMMA"])
            AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TrueBeamCouch"])
        elif make_tomo_plan:
            # Load the Tomo Supports for the couch
            AutoPlanOperations.load_supports(rso=pd_hfs,
                                             supports=["TomoCouch", "Baseplate_Override_PMMA"])
            AutoPlanOperations.load_supports(rso=pd_ffs, supports=["TomoCouch"])

        # # Also create a bounding box on both images about the junction point and set the ROI there
        register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name)

        connect.await_user_input(
            'Check the fusion alignment of the boney anatomy in the hips. Then continue script.')
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        load_normal_mbs(pd_hfs, pd_ffs)
        # Build lung contours and avoidance on the HFS scan
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        make_lung_contours(pd_hfs, color=[192, 192, 192])

        ffs_poi_junction, hfs_poi_junction = make_central_junction_structs(
            pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name)

        # # TODO: CHECK FOR PLANNING STRUCTURES AND THEN ADD ANY MISSING
        # # TODO: underive and delete geometry on avoid volumes defined on incorrect scans
        # #       Delete all empty geometries for junction ffs doses immediately after they are
        # all created
        # #       Create HFS and FFS eval structs for treatment
        # # then map them over
    if ffs_autoplan:
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        #
        # This phase is VMAT-Specific and should be moved to its own function
        # Ideally, we would load the first two beamsets and do the optimization
        # only on them, however, we'd need specific fall off objectives on
        # the last beamset to avoid a lack of robustness.
        # Perhaps optimize  in pairs (0,1), (1,2), (2,3) with the lowest beamset
        # going into the background?
        # FFS Planning
        # FFS protocol declarations
        if make_vmat_plan:
            # FFS Junction
            # Add points for isocenters in VMAT
            ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
                .PoiGeometries[JUNCTION_POINT]
            ffs_pois = place_ffs_vmat_pois(pd_ffs, ffs_poi_junction)
            tbi_vmat_ffs = {
                'user_prompts': True,
                'protocol_name': PROTOCOL_NAME_VMAT,
                'translation_map': {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')},
                'order_name': ORDER_NAME_FFS_VMAT,
                'num_fx': nfx,
                'site': 'FFS_',
                'beamset_name': BEAMSET_FFS_VMAT,
                'beamset_template': BEAMSET_FFS_VMAT,
                'machine': vmat_machine,
                'plan_defs': {
                    'protocol_name': PROTOCOL_NAME_VMAT,
                    'translation_map': {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')},
                    'order_name': ORDER_NAME_FFS_VMAT, },
            }
            multi_plan = {
                'beamset_list': [
                    {'beamset_template': BEAMSET_FFS_VMAT,
                     'num_fx': nfx,
                     'machine': vmat_machine,
                     'site': 'FFS_',
                     'iso': {'type': 'POI', 'target': fp},
                     }
                    for fp in ffs_pois]

            }
            pd_ffs_out = autoplan(autoplan_parameters=tbi_vmat_ffs, **multi_plan)
        #
        # Compute the locations of the isocenters in the VMAT FFS Location
        # Load each treating beamset
        # Load the objectives of the VMAT autoplan
        if make_tomo_plan:
            iso_target = tomo_calc_ffs_iso(pd_ffs, target=JUNCTION_PREFIX_FFS + "90%Rx")
            tbi_ffs_protocol = {
                'protocol_name': PROTOCOL_NAME_TOMO,
                'order_name': ORDER_NAME_FFS_TOMO,
                'num_fx': nfx,
                'site': 'TBI_',
                'translation_map': {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')},
                'beamset_name': BEAMSET_FFS_TOMO,
                'iso_target': iso_target,
                'machine': tomo_machine,
                'user_prompts': True,
            }
            pd_ffs_out = autoplan(autoplan_parameters=tbi_ffs_protocol)

    if make_ffs_isodose_structs and make_tomo_plan:
        # TODO: Redefine acquisition of these to be determined based on
        #  expected TOMO Plan and Beamset Name
        # Get isodoses
        pd_ffs = Pd(error=[],
                    patient=GeneralOperations.find_scope(level='Patient'),
                    case=GeneralOperations.find_scope(level='Case'),
                    exam=ffs_exam,
                    db=GeneralOperations.find_scope(level='PatientDB'),
                    plan=GeneralOperations.find_scope(level='Plan'),
                    beamset=GeneralOperations.find_scope(level='BeamSet'))
        #
        # Make sure the current FFS scan is primary
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)

        pd_ffs.patient.Save()
        pd_ffs.plan.SetCurrent()
        pd_ffs.beamset.SetCurrent()
        prefix = JUNCTION_PREFIX_FFS
        make_ffs_isodoses(pd_hfs, pd_ffs, rx, prefix)

    if hfs_autoplan and make_tomo_plan:
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        #
        # HFS Planning
        # HFS protocol declarations
        tbi_hfs_protocol = {
            'protocol_name': PROTOCOL_NAME_TOMO,
            'order_name': ORDER_NAME_HFS_TOMO,
            'num_fx': nfx,
            'site': 'TBI_',
            'translation_map': {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')},
            'beamset_name': BEAMSET_HFS_TOMO,
            'iso_target': TARGET_HFS,
            'machine': tomo_machine,
            'user_prompts': True,
        }
        pd_hfs_out = autoplan(autoplan_parameters=tbi_hfs_protocol)
    #

    if make_ffs_isodose_structs and make_vmat_plan:
        # Get isodoses
        case = GeneralOperations.find_scope(level='Case')
        # Find the ffs vmat plan
        vmat_ffs_p, vmat_ffs_bs = find_beamset(
            case, beamset_name="FFS__VMA_Auto")
        pd_ffs = Pd(error=[],
                    patient=GeneralOperations.find_scope(level='Patient'),
                    case=case,
                    exam=ffs_exam,
                    db=GeneralOperations.find_scope(level='PatientDB'),
                    plan=vmat_ffs_p,
                    beamset=vmat_ffs_bs)
        #
        # Make sure the current FFS scan is primary
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)

        pd_ffs.patient.Save()
        pd_ffs.plan.SetCurrent()
        pd_ffs.beamset.SetCurrent()
        prefix = JUNCTION_PREFIX_FFS
        make_ffs_isodoses(pd_hfs, pd_ffs, rx, prefix)

    if hfs_autoplan and make_vmat_plan:
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        # HFS Junction
        hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
            .PoiGeometries[JUNCTION_POINT]
        hfs_pois = place_hfs_vmat_pois(pd_hfs, hfs_poi_junction)
        #
        # HFS Planning
        # HFS protocol declarations
        tbi_vmat_hfs = {
            'user_prompts': True,
            'protocol_name': PROTOCOL_NAME_VMAT,
            'translation_map': {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')},
            'order_name': ORDER_NAME_HFS_VMAT,
            'num_fx': nfx,
            'site': 'HFS_',
            'beamset_name': BEAMSET_HFS_VMAT,
            'machine': vmat_machine,
            'plan_defs': {
                'protocol_name': PROTOCOL_NAME_VMAT,
                'translation_map': {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')},
                'order_name': ORDER_NAME_HFS_VMAT, },
        }
        multi_plan = {
            'beamset_list': [
                {'beamset_template': BEAMSET_HFS_VMAT,
                 'num_fx': nfx,
                 'machine': vmat_machine,
                 'site': 'HFS_',
                 'iso': {'type': 'POI', 'target': hp},
                 }
                for hp in hfs_pois]

        }
        pd_hfs_out = autoplan(autoplan_parameters=tbi_vmat_hfs, **multi_plan)

    if dose_summation:
        # Update the current variables if needed.
        # User Prompt for Dose/Fractions
        if not pd_hfs.beamset or not pd_ffs.beamset:

            pd_ffs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=ffs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=None,
                        beamset=None)
            plans = [p.Name for p in pd_ffs.case.TreatmentPlans]

            beamsets = [bs.DicomPlanLabel for p in pd_ffs.case.TreatmentPlans for bs in p.BeamSets]
            sg.ChangeLookAndFeel('DarkPurple4')
            layout = [[sg.Text("FFS Plan")],
                      [sg.Combo(plans, key="-FFS PLAN-",
                                default_value=plans[0],
                                size=(40, 1), )],
                      [sg.Text("FFS Beamset")],
                      [sg.Combo(beamsets, key="-FFS BEAMSET-",
                                default_value=beamsets[0],
                                size=(40, 1))],
                      [sg.Text("HFS Plan")],
                      [sg.Combo(plans, key="-HFS PLAN-",
                                default_value=plans[0],
                                size=(40, 1))],
                      [sg.Text("HFS Beamset")],
                      [sg.Combo(beamsets, key="-HFS BEAMSET-",
                                default_value=beamsets[0],
                                size=(40, 1))],
                      [sg.B('OK'), sg.B('Cancel')]]
            window = sg.Window("BEAMSET ASSIGNMENT",
                               layout)
            while True:
                event, values = window.read()
                if event == sg.WIN_CLOSED or event == "Cancel":
                    selections = None
                    break
                elif event == "OK":
                    selections = values
                    break
            window.close()
            if selections == {}:
                sys.exit('Selection Script was cancelled')

            temp_case = pd_ffs.case
            ffs_plan = None
            hfs_plan = None
            ffs_beamset = None
            hfs_beamset = None

            for tp in temp_case.TreatmentPlans:
                if tp.Name == selections['-FFS PLAN-']:
                    ffs_plan = tp
                    for bs in tp.BeamSets:
                        if bs.DicomPlanLabel == selections['-FFS BEAMSET-']:
                            ffs_beamset = bs
                            break
                if tp.Name == selections['-HFS PLAN-']:
                    hfs_plan = tp
                    for bs in tp.BeamSets:
                        if bs.DicomPlanLabel == selections['-HFS BEAMSET-']:
                            hfs_beamset = bs
                            break
            if not all([ffs_beamset, ffs_plan, hfs_beamset, hfs_plan]):
                sys.exit('No HFS FFS Beamsets defined')

            pd_ffs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=ffs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=ffs_plan,
                        beamset=ffs_beamset)
            pd_hfs = Pd(error=[],
                        patient=GeneralOperations.find_scope(level='Patient'),
                        case=GeneralOperations.find_scope(level='Case'),
                        exam=hfs_exam,
                        db=GeneralOperations.find_scope(level='PatientDB'),
                        plan=hfs_plan,
                        beamset=hfs_beamset)
        new_hfs_grid = get_new_grid(pd_hfs.case, pd_hfs.beamset, pd_ffs.beamset)
        pd_hfs.beamset.UpdateDoseGrid(Corner=new_hfs_grid['Corner'],
                                      VoxelSize=new_hfs_grid['VoxelSize'],
                                      NumberOfVoxels=new_hfs_grid['NrVoxels'])
        new_ffs_grid = get_new_grid(pd_ffs.case, pd_ffs.beamset, pd_hfs.beamset)
        pd_ffs.beamset.UpdateDoseGrid(Corner=new_ffs_grid['Corner'],
                                      VoxelSize=new_ffs_grid['VoxelSize'],
                                      NumberOfVoxels=new_ffs_grid['NrVoxels'])
        # TODO: Recompute all doses in the plan since they seem to be required for summation
        # Recompute all doses:
        for p in pd_ffs.case.TreatmentPlans:
            for b in p.BeamSets:
                try:
                    b.ComputeDose(ComputeBeamDoses=False, DoseAlgorithm='CCDose',
                                  ForceRecompute=False)
                except Exception as e:
                    # Invalid operation error when trying to compute already computed doses
                    pass

        pd_ffs.beamset.ComputeDoseOnAdditionalSets(OnlyOneDosePerImageSet=False,
                                                   AllowGridExpansion=True,
                                                   ExaminationNames=[pd_hfs.exam.Name],
                                                   FractionNumbers=[0],
                                                   ComputeBeamDoses=True)
        # Create summation
        retval_0 = pd_hfs.case.CreateSummedDose(DoseName="TBI",
                                                FractionNumber=0,
                                                DoseDistributions=[pd_hfs.beamset.FractionDose,
                                                                   find_eval_dose(
                                                                       pd_hfs.case,
                                                                       beamset_name=pd_ffs.beamset.DicomPlanLabel,
                                                                       exam_name=pd_hfs.exam.Name)
                                                                   ],
                                                Weights=[nfx, nfx])


if __name__ == '__main__':
    main()
