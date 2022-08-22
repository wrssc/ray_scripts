""" Automated Plan - TomoTBI

    How To Use:

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
__raystation__ = '10A SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
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
import PySimpleGUI as sg

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../general'))
from AutoPlan import autoplan

# Structure template defaults
COUCH_SUPPORT_STRUCTURE_TEMPLATE = "UW Support"
HFS_COUCH_SUPPORT_STRUCTURE_EXAMINATION = "Supine Patient"
HFS_COUCH_SUPPORT_STRUCTURE_EXAMINATION = "Supine Patient"
COUCH_SOURCE_ROI_NAMES = {
    "TrueBeam": "TrueBeamCouch",
    "TomoTherapy": "TomoCouch"
}
LUNG_AVOID_NAME = "Lungs_m07"
EXTERNAL_NAME = "ExternalClean"
AVOID_HFS_NAME = "Avoid_HFS"
AVOID_FFS_NAME = "Avoid_FFS"
PROTOCOL_NAME = "UW Tomo TBI"
ORDER_NAME_FFS = "TomoTBI_FFS"
ORDER_TARGET_NAME_FFS = "PTV_p_FFS"
ORDER_NAME_HFS = "TomoTBI_HFS"
ORDER_TARGET_NAME_HFS = "PTV_p_HFS"
ORDER_NAME_HFS = "TomoTBI_HFS"
BEAMSET_FFS = "Tomo_TBI_FFS_FW50"
BEAMSET_HFS = "Tomo_TBI_HFS_FW50"
TARGET_FFS = "PTV_p_FFS"
JUNCTION_PREFIX_FFS = "ffs_junction_"
JUNCTION_PREFIX_HFS = "hfs_junction_"
JUNCTION_POINT = "junction"
TARGET_HFS = "PTV_p_HFS"
MACHINE = "HDA0488"
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
            'No External contour type designated. Give a contour an External type and continue script.')
        if any(roi.OfRoi.Type == 'External' for roi in roi_list):
            logging.debug('No external contour designated after prompt recommend exit')
            return False


def check_structure_exists(case, structure_name, roi_list, option):
    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if option == 'Delete':
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            logging.warning("check_structure_exists: " +
                            structure_name + 'found - deleting and creating')
        elif option == 'Check':
            connect.await_user_input(
                'Contour {} Exists - Verify its accuracy and continue script'.format(
                    structure_name))
        return True
    else:
        logging.info('check_structure_exists: '
                     'Structure {} not found, and will be created'.format(structure_name))
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


def find_junction_coords(pd_hfs):
    # Find which kidney is lower
    # Move this to a function that runs first with Kidneys already defined.
    roi_1 = 'Kidney_L'
    roi_2 = 'Kidney_R'
    [external_name] = StructureOperations.find_types(pd_hfs.case, roi_type='External')
    hfs_roi_1_z = get_most_inferior(pd_hfs.case, pd_hfs.exam, roi_1)
    hfs_roi_2_z = get_most_inferior(pd_hfs.case, pd_hfs.exam, roi_2)
    center = get_center(pd_hfs.case, pd_hfs.exam, external_name)
    return {
        'x': center['x'],
        'y': center['y'],
        'z': min(hfs_roi_1_z, hfs_roi_2_z)
    }


def place_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    poi_status = StructureOperations.create_poi(
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
    # Return all structures who's name contains roi_prefix
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
    except:
        pass


def make_junction_contour(pdata, junct_name, z_start, dim_si, dose_level, color=[192, 192, 192]):
    #  Make the Box Roi and junction region in the area of interest
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix == 'ffs':
        si = -1.
    elif prefix == 'hfs':
        si = 1.
    # Find the name of the external contour
    external_name = StructureOperations.find_types(pdata.case, roi_type='External')[0]
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
    type_msg = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=junction_name,
        roi_type='Ptv')
    # update_all_remove_expression(pdata=pdata,roi_name=box_name)
    update_all_remove_expression(pdata=pdata, roi_name=junction_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_lung_contours(pdata, color=[192, 192, 192]):
    """
    Make the Lungs and avoidance structures for lung
    """
    #
    # Boolean Definitions for Lungs
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


def get_roi_geometries(case, exam, roi_name):
    for roig in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
        if roig.OfRoi.Name == roi_name:
            return roig
    return None


def make_avoid(pdata, z_start, avoid_name, color=[192, 192, 192]):
    """ Build the avoidance structure used in making the PTV
        pdata: kind of like PDiddy, but with data, see below
        z_start (float): starting location of the junction
        avoid_name (str): Name of the structure to include all avoidance voxels
        avoid_color (opt list[r,g,b]): color of output structure
        Recipe for avoidance volume:
        Take the z_start, build a box that is everything above this position
        Find the intersection with the external.
        If this is the HFS scan, subtract the lung avoidance
    """
    #
    # Find the name of the external contour
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
        "ExpR": [0., 0., 0.3, 0.3, 0.3, 0.3, 0.3],  # Capture little ditzels evading the external
        "StructType": "Undefined",
    }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    # update_all_remove_expression(pdata=pdata,roi_name=box_name)
    update_all_remove_expression(pdata=pdata, roi_name=avoid_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


# TODO: Make PTV_p_Eval_HFS(-skin and 7 mm lungs)
#       Make PTV_p_Eval_FFS(-skin)

def make_ptv(pdata, junction_prefix, avoid_name, color=[192, 192, 192]):
    # Find all contours matching prefix and along with avoid_name return the external minus these objects
    #
    # Get exam orientation
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
    type_msg = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=ptv_name,
        roi_type='Ptv')
    # Make Eval structure

    # Boolean Definitions
    roi_exclude.append('Avoid_Skin_PRV05')
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
    type_msg = StructureOperations.change_roi_type(
        case=pdata.case,
        roi_name=eval_name,
        roi_type='Ptv')
    pdata.case.PatientModel.RegionsOfInterest[eval_name].DeleteExpression()


def make_unsubtracted_dose_structures(pdata, rx, dose_thresholds_normalized):
    """
    Make the structure for the dose threshold supplied
    makes unsubtracted_doses (RS Region of Interest Object) with name like <5%Rx>
    pdata: exactly the same as pdiddy
    rx (float): Prescription (normalizing) dose in cGy
    dose_thresholds_normalized ({dose_roi_names: dose_levels(int)}): percentages of prescription dose
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
        #
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
                "SourcesA": [k, raw_dose_name],
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
                    patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
                subtracted_isodoses.append(roi_name)
            else:
                temp_defs.update(
                    [("SourcesB", []),
                     ("OperationResult", "None")]
                )
                StructureOperations.make_boolean_structure(
                    patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
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
                    temp_defs["SourcesA"] = [k, raw_dose_name]
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
    # for i in isodose_contours:
    #     try:
    #         update_all_remove_expression(pdata, i)
    #     except:
    #         pass
    for d in delete_rois:
        pdata.case.PatientModel.RegionsOfInterest[d].DeleteRoi()
    return isodose_contours


def reset_primary_secondary(exam1, exam2):
    # Resets exam 1 as primary and exam2 as secondary
    exam1.SetPrimary()
    exam2.SetSecondary()


def update_dose_grid(pdata):
    # TODO: This still dooesn't work. The two dose grids need to be compared using a common
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


def register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, ):
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

    pd_hfs.case.ComputeGrayLevelBasedRigidRegistration(
        FloatingExaminationName=ffs_scan_name,
        ReferenceExaminationName=hfs_scan_name,
        UseOnlyTranslations=False,
        HighWeightOnBones=False,
        InitializeImages=True,
        FocusRoisNames=[],
        RegistrationName=None)

    # Refine on bones
    pd_hfs.case.ComputeGrayLevelBasedRigidRegistration(
        FloatingExaminationName=ffs_scan_name,
        ReferenceExaminationName=hfs_scan_name,
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
    rois = [r.OfRoi.Name for r in pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name].RoiGeometries
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
    rois = [r.OfRoi.Name for r in pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name].RoiGeometries
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


def make_tbi_planning_structs(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name):
    reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    #
    # Build lung contours and avoidance on the HFS scan
    make_lung_contours(pd_hfs, color=[192, 192, 192])
    #
    # Make skin subtraction
    StructureOperations.make_wall(
        wall="Avoid_Skin_PRV05",
        sources=["ExternalClean"],
        delta=0.5,
        patient=pd_hfs.patient,
        case=pd_hfs.case,
        examination=pd_hfs.exam,
        inner=True,
        struct_type="Organ")
    #
    StructureOperations.make_wall(
        wall="Avoid_Skin_PRV05",
        sources=["ExternalClean"],
        delta=0.5,
        patient=pd_ffs.patient,
        case=pd_ffs.case,
        examination=pd_ffs.exam,
        inner=True,
        struct_type="Organ")

    #
    try:
        pd_hfs.case.PatientModel.CreateRoi(
            Name="External_PRV10",
            Color="255, 128, 0",
            Type="IrradiatedVolume",
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None)
    except Exception as e:
        if "There already exists" in "{}".format(e):
            pass
    pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].SetMarginExpression(
        SourceRoiName=EXTERNAL_NAME,
        MarginSettings={'Type': "Expand",
                        'Superior': 1.0,
                        'Inferior': 1.0,
                        'Anterior': 1.0,
                        'Posterior': 1.0,
                        'Right': 1.0,
                        'Left': 1.0})
    pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].UpdateDerivedGeometry(
        Examination=pd_hfs.exam, Algorithm="Auto")

    # TODO: Rename Sensibly
    lower_point = find_junction_coords(pd_hfs)
    place_poi(pd_hfs=pd_hfs, coord_hfs=lower_point)
    # Get the rigid registration
    hfs_to_ffs = pd_hfs.case.GetTransformForExaminations(
        FromExamination=hfs_scan_name,
        ToExamination=ffs_scan_name)
    # Convert it to the transform dictionary
    trans_h2f = convert_array_to_transform(hfs_to_ffs)
    # Map the junction point
    pd_hfs.case.MapPoiGeometriesRigidly(
        PoiGeometryNames=[JUNCTION_POINT],
        CreateNewPois=False,
        ReferenceExaminationName=hfs_scan_name,
        TargetExaminationNames=[ffs_scan_name],
        Transformations=[trans_h2f])

    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    # IsoDose levels:
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = 2.5
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
        make_junction_contour(pd_ffs,
                              junct_name='Junction',
                              z_start=ffs_poi_junction.Point.z - dim_si * float(i),
                              dim_si=dim_si,
                              dose_level=str(int(j_i[i])) + "%Rx",
                              color=dose_levels[j_i[i]])
    # TODO: Set junction colors to the optimal isodose color
    make_avoid(pd_ffs, z_start=ffs_poi_junction.Point.z, avoid_name=AVOID_FFS_NAME)
    make_ptv(pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS, avoid_name=AVOID_FFS_NAME)
    #
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        .PoiGeometries[JUNCTION_POINT]
    for i in range(len(j_i)):
        z_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i) - i)
        logging.debug('Z location for Junction {} is {}'.format(str(j_i[i]), z_start))
        make_junction_contour(pd_hfs,
                              junct_name='Junction',
                              z_start=z_start,
                              dim_si=dim_si,
                              dose_level=str(int(j_i[i])) + "%Rx",
                              color=dose_levels[j_i[i]])
    #
    # HFS avoid starts at junction point - number of dose levels * dim_si
    hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
    # TODO: underive and delete geometry on avoid volumes defined on incorrect scans
    #       Delete all empty geometriest for junction ffs doses immediately after they are all created
    #  False     Create HFS and FFS eval structs for treatment
    #       ADD prompt for dir block on avoidances
    # then map them over
    make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
    make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS, avoid_name=AVOID_HFS_NAME)


def calc_ffs_iso(pd_ffs, target):
    pois = [p.Name for p in pd_ffs.case.PatientModel.PointsOfInterest]
    if 'SimFiducials' not in pois:
        connect.await_user_input('Place SimFiducial point')
    pm = pd_ffs.case.PatientModel
    sim_coords = pm.StructureSets[pd_ffs.exam.Name].LocalizationPoiGeometry.Point
    target_coords = pm.StructureSets[pd_ffs.exam.Name].RoiGeometries[target].GetCenterOfRoi()
    iso_coord = {'x': 0., 'y': target_coords['y'], 'z': sim_coords['z']}
    iso_name = pm.GetUniqueRoiName(DesiredName='ROI_ffs_iso')
    pm.CreateRoi(Name=iso_name,
                 Color='Pink',
                 Type='Bolus')
    iso_roi = pm.RegionsOfInterest[iso_name]
    iso_roi.CreateSphereGeometry(Radius=1.0,
                                 Examination=pd_ffs.exam,
                                 Center=iso_coord,
                                 Representation='Voxels',
                                 VoxelSize=0.01)
    return iso_name


def make_ffs_isodoses(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, rx):
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
    j_names = dict([(JUNCTION_PREFIX_FFS + str(j) + '%Rx', (j + 10, j, j - 5)) for j in j_i])
    #
    # Generate subtracted dose values
    isodose_names = make_dose_structures(pd_ffs, isodoses=j_names, rx=rx)
    # for n in j_i:
    #     name = JUNCTION_PREFIX_FFS +str(n)+'%Rx'
    #     j_names[name] = (n+10, n, n-5)
    #     isodose_names = make_dose_structures(pd_ffs, isodoses=j_names, rx=rx)
    #     break
    # Map the junction point
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


def main():
    # User Prompt for Dose/Fractions
    event, values = sg.Window('AUTO TBI',
                              [[sg.T('Enter Number of Fractions'), sg.In(key='-NFX-')],
                               [sg.T('Enter TOTAL Dose in cGy'), sg.In(key='-TDOSE-')],
                               [sg.B('OK'), sg.B('Cancel')]]).read(close=True)

    nfx = values['-NFX-']
    rx = values['-TDOSE-']

    # Look for HFS/FFS Scans
    temp_case = GeneralOperations.find_scope(level='Case')
    temp_exam = GeneralOperations.find_scope(level='Examination')
    for e in temp_case.Examinations:
        if e.PatientPosition == 'HFS':
            hfs_exam = e
            hfs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))
        elif e.PatientPosition == 'FFS':
            ffs_exam = e
            ffs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))
        else:
            sys.exit('unknown exam orientation')
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
    # TODO: GET RID OF THESE AND REPLACE WITH A CREATE STRUCTS ONLY
    do_this = False
    if do_this:
        # TODO: Get current on the hfs scan since it seems like the couch is failing to load
        #
        # Load the Tomo Supports for the couch
        AutoPlanOperations.load_supports(pd=pd_hfs, supports=["TomoCouch"])
        AutoPlanOperations.load_supports(pd=pd_ffs, supports=["TomoCouch"])

        # # Make external clean on both
        # ext_clean = StructureOperations.make_externalclean(
        #     patient=pd_hfs.patient,
        #     case=pd_hfs.case,
        #     examination=pd_hfs.exam,
        #     structure_name=EXTERNAL_NAME,
        #     suffix=None,
        #     delete=False,
        # )
        # # If this breaks on a clean scan, we will want to see if this exam has contours
        # ext_clean = StructureOperations.make_externalclean(
        #     patient=pd_ffs.patient,
        #     case=pd_ffs.case,
        #     examination=pd_ffs.exam,
        #     structure_name=EXTERNAL_NAME,
        #     suffix=None,
        #     delete=False,
        # )
        #
        # pd_hfs.case.ComputeRigidImageRegistration(
        #     FloatingExaminationName=ffs_scan_name,
        #     ReferenceExaminationName=hfs_scan_name,
        #     UseOnlyTranslations=False,
        #     HighWeightOnBones=False,
        #     InitializeImages=True,
        #     FocusRoisNames=[],
        #     RegistrationName=None)
        #
        # # Refine on bones
        # pd_hfs.case.ComputeRigidImageRegistration(
        #     FloatingExaminationName=ffs_scan_name,
        #     ReferenceExaminationName=hfs_scan_name,
        #     UseOnlyTranslations=False,
        #     HighWeightOnBones=True,
        #     InitializeImages=False,
        #     FocusRoisNames=[],
        #     RegistrationName=None)
        # # Also create a bounding box on both images about the junction point and set the ROI there
        register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name)

        connect.await_user_input(
            'Check the fusion alignment of the boney anatomy in the hips. Then continue script.')
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        # TODO: CHECK FOR PLANNING STRUCTURES AND THEN ADD ANY MISSING
        #
        # Begin making planning structures

        # pd_hfs.case.PatientModel.MBSAutoInitializer(
        #     MbsRois=MBS_ROIS,
        #     CreateNewRois=True,
        #     Examination=pd_hfs.exam,
        #     UseAtlasBasedInitialization=False)
        # connect.await_user_input('Review placement of MBS structures')
        #
        # pd_hfs.case.PatientModel.AdaptMbsMeshes(
        #     Examination=pd_hfs.exam,
        #     RoiNames=[r"Lung_L",
        #               r"Lung_R",
        #               r"Kidney_L",
        #               r"Kidney_R"],
        #     CustomStatistics=None,
        #     CustomSettings=None)
        #
        # # Try a repeat on FFS
        # pd_ffs.case.PatientModel.MBSAutoInitializer(
        #     MbsRois=[{'CaseType': "Abdomen",
        #               'ModelName': r"Kidney (Left)",
        #               'RoiName': r"Kidney_L",
        #               'RoiColor': "58, 251, 170"},
        #              {'CaseType': "Abdomen",
        #               'ModelName': r"Kidney (Right)",
        #               'RoiName': r"Kidney_R",
        #               'RoiColor': "250, 57, 105"},
        #              {'CaseType': "Thorax",
        #               'ModelName': r"Lung (Left)",
        #               'RoiName': r"Lung_L",
        #               'RoiColor': "253, 122, 9"},
        #              {'CaseType': "Thorax",
        #               'ModelName': r"Lung (Right)",
        #               'RoiName': r"Lung_R",
        #               'RoiColor': "54, 247, 223"}],
        #     CreateNewRois=False,
        #     Examination=pd_ffs.exam,
        #     UseAtlasBasedInitialization=True)
        # connect.await_user_input('Review placement of MBS structures')
        #
        # pd_ffs.case.PatientModel.AdaptMbsMeshes(
        #     Examination=pd_ffs.exam,
        #     RoiNames=[r"Lung_L",
        #               r"Lung_R",
        #               r"Kidney_L",
        #               r"Kidney_R"],
        #     CustomStatistics=None,
        #     CustomSettings=None)
        #
        # connect.await_user_input('Check the MBS loaded structures on both exams.')
        # reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        #
        #
        # Make skin subtraction
        # StructureOperations.make_wall(
        #     wall="Avoid_Skin_PRV05",
        #     sources=["ExternalClean"],
        #     delta=0.5,
        #     patient=pd_hfs.patient,
        #     case=pd_hfs.case,
        #     examination=pd_hfs.exam,
        #     inner=True,
        #     struct_type="Organ")
        # #
        # StructureOperations.make_wall(
        #     wall="Avoid_Skin_PRV05",
        #     sources=["ExternalClean"],
        #     delta=0.5,
        #     patient=pd_ffs.patient,
        #     case=pd_ffs.case,
        #     examination=pd_ffs.exam,
        #     inner=True,
        #     struct_type="Organ")
        #
        # #
        # pd_hfs.case.PatientModel.CreateRoi(
        #     Name="External_PRV10",
        #     Color="255, 128, 0",
        #     Type="IrradiatedVolume",
        #     TissueName=None,
        #     RbeCellTypeName=None,
        #     RoiMaterial=None)
        # pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].SetMarginExpression(
        #     SourceRoiName=EXTERNAL_NAME,
        #     MarginSettings={'Type': "Expand",
        #                     'Superior': 1.0,
        #                     'Inferior': 1.0,
        #                     'Anterior': 1.0,
        #                     'Posterior': 1.0,
        #                     'Right': 1.0,
        #                     'Left': 1.0})
        # pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].UpdateDerivedGeometry(
        #     Examination=pd_hfs.exam, Algorithm="Auto")

        # TODO: Rename Sensibly
        # lower_point = find_junction_coords(pd_hfs)
        # place_poi(pd_hfs=pd_hfs, coord_hfs=lower_point)
        # # Get the rigid registration
        # hfs_to_ffs = pd_hfs.case.GetTransformForExaminations(
        #     FromExamination=hfs_scan_name,
        #     ToExamination=ffs_scan_name)
        # # Convert it to the transform dictionary
        # trans_h2f = convert_array_to_transform(hfs_to_ffs)
        # # Map the junction point
        # pd_hfs.case.MapPoiGeometriesRigidly(
        #     PoiGeometryNames=[JUNCTION_POINT],
        #     CreateNewPois=False,
        #     ReferenceExaminationName=hfs_scan_name,
        #     TargetExaminationNames=[ffs_scan_name],
        #     Transformations=[trans_h2f])

        load_normal_mbs(pd_hfs, pd_ffs)
        # Build lung contours and avoidance on the HFS scan
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        make_lung_contours(pd_hfs, color=[192, 192, 192])
        make_tbi_planning_structs(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name)
        # # TODO: CHECK FOR PLANNING STRUCTURES AND THEN ADD ANY MISSING
        # # Loop through MBS rois, if present, pop.
        # rois = [r.OfRoi.Name for r in pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name].RoiGeometries
        #         if r.HasContours]
        # logging.debug('Type of MBS_ROIS is {} '.format(type(MBS_ROIS)))
        # mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
        # adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
        # #
        # # Begin making planning structures
        # pd_hfs.case.PatientModel.MBSAutoInitializer(
        #     MbsRois=mbs_list,
        #     CreateNewRois=True,
        #     Examination=pd_hfs.exam,
        #     UseAtlasBasedInitialization=True)
        # connect.await_user_input('Review placement of MBS structures')
        #
        # pd_hfs.case.PatientModel.AdaptMbsMeshes(
        #     Examination=pd_hfs.exam,
        #     RoiNames=adapt_list,
        #     CustomStatistics=None,
        #     CustomSettings=None)
        # # Loop through MBS rois, if present, pop.
        # rois = [r.OfRoi.Name for r in pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name].RoiGeometries
        #         if r.HasContours]
        # mbs_list = [v for k, v in MBS_ROIS.items() if k not in rois]
        # adapt_list = [k for k in MBS_ROIS.keys() if k not in rois]
        # # Try a repeat on FFS
        # pd_ffs.case.PatientModel.MBSAutoInitializer(
        #     MbsRois=mbs_list,
        #     CreateNewRois=False,
        #     Examination=pd_ffs.exam,
        #     UseAtlasBasedInitialization=True)

    # do_this = True
    # if do_this:
    # reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
    # #
    # # Build lung contours and avoidance on the HFS scan
    # make_lung_contours(pd_hfs, color=[192, 192, 192])
    # #
    # # Make skin subtraction
    # StructureOperations.make_wall(
    #     wall="Avoid_Skin_PRV05",
    #     sources=["ExternalClean"],
    #     delta=0.5,
        #     patient=pd_hfs.patient,
        #     case=pd_hfs.case,
        #     examination=pd_hfs.exam,
        #     inner=True,
        #     struct_type="Organ")
        # #
        # StructureOperations.make_wall(
        #     wall="Avoid_Skin_PRV05",
        #     sources=["ExternalClean"],
        #     delta=0.5,
        #     patient=pd_ffs.patient,
        #     case=pd_ffs.case,
        #     examination=pd_ffs.exam,
        #     inner=True,
        #     struct_type="Organ")
        #
        # #
        # pd_hfs.case.PatientModel.CreateRoi(
        #     Name="External_PRV10",
        #     Color="255, 128, 0",
        #     Type="IrradiatedVolume",
        #     TissueName=None,
        #     RbeCellTypeName=None,
        #     RoiMaterial=None)
        # pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].SetMarginExpression(
        #     SourceRoiName=EXTERNAL_NAME,
        #     MarginSettings={'Type': "Expand",
        #                     'Superior': 1.0,
        #                     'Inferior': 1.0,
        #                     'Anterior': 1.0,
        #                     'Posterior': 1.0,
        #                     'Right': 1.0,
        #                     'Left': 1.0})
        # pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].UpdateDerivedGeometry(
        #     Examination=pd_hfs.exam, Algorithm="Auto")
        #
        # # TODO: Rename Sensibly
        # lower_point = find_junction_coords(pd_hfs)
        # place_poi(pd_hfs=pd_hfs, coord_hfs=lower_point)
        # # Get the rigid registration
        # hfs_to_ffs = pd_hfs.case.GetTransformForExaminations(
        #     FromExamination=hfs_scan_name,
        #     ToExamination=ffs_scan_name)
    # # Convert it to the transform dictionary
    # trans_h2f = convert_array_to_transform(hfs_to_ffs)
    # # Map the junction point
    # pd_hfs.case.MapPoiGeometriesRigidly(
    #     PoiGeometryNames=[JUNCTION_POINT],
    #     CreateNewPois=False,
    #     ReferenceExaminationName=hfs_scan_name,
    #     TargetExaminationNames=[ffs_scan_name],
    #     Transformations=[trans_h2f])

    # do_this = True
    # if do_this:
    #     make_tbi_planning_structs(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name)
    # #
    # # FFS Junction
    # ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name] \
    #     .PoiGeometries[JUNCTION_POINT]
    # # IsoDose levels:
    # j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    # dim_si = 2.5
    # dose_levels = {10: [127, 0, 255],
    #                20: [0, 0, 255],
    #                30: [0, 127, 255],
        #                40: [0, 255, 255],
        #                50: [0, 255, 127],
        #                60: [0, 255, 0],
        #                70: [127, 255, 0],
        #                80: [255, 255, 0],
        #                90: [255, 127, 0],
        #                95: [255, 0, 0],
        #                100: [255, 0, 255]}
        #
        # for i in range(len(j_i)):
        #     make_junction_contour(pd_ffs,
        #                           junct_name='Junction',
        #                           z_start=ffs_poi_junction.Point.z - dim_si * float(i),
        #                           dim_si=dim_si,
        #                           dose_level=str(int(j_i[i])) + "%Rx",
        #                           color=dose_levels[j_i[i]])
        # # TODO: Set junction colors to the optimal isodose color
        # make_avoid(pd_ffs, z_start=ffs_poi_junction.Point.z, avoid_name=AVOID_FFS_NAME)
        # make_ptv(pdata=pd_ffs, junction_prefix=JUNCTION_PREFIX_FFS, avoid_name=AVOID_FFS_NAME)
        # #
        # # HFS Junction
        # hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name] \
        #     .PoiGeometries[JUNCTION_POINT]
        # for i in range(len(j_i)):
        #     z_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i) - i)
        #     logging.debug('Z location for Junction {} is {}'.format(str(j_i[i]), z_start))
        #     make_junction_contour(pd_hfs,
        #                           junct_name='Junction',
        #                           z_start=z_start,
        #                           dim_si=dim_si,
        #                           dose_level=str(int(j_i[i])) + "%Rx",
        #                           color=dose_levels[j_i[i]])
        # #
        # # HFS avoid starts at junction point - number of dose levels * dim_si
        # hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
        # # TODO: underive and delete geometry on avoid volumes defined on incorrect scans
        # #       Delete all empty geometriest for junction ffs doses immediately after they are all created
        # #       Create HFS and FFS eval structs for treatment
        # # then map them over
        # make_avoid(pd_hfs, z_start=hfs_avoid_start, avoid_name=AVOID_HFS_NAME)
        # make_ptv(pdata=pd_hfs, junction_prefix=JUNCTION_PREFIX_HFS, avoid_name=AVOID_HFS_NAME)
    do_this = False
    if do_this:
        reset_primary_secondary(pd_ffs.exam, pd_hfs.exam)
        #
        # FFS Planning
        # FFS protocol declarations
        iso_target = calc_ffs_iso(pd_ffs, target=JUNCTION_PREFIX_FFS + "90%Rx")
        tbi_ffs_protocol = {
            'protocol_name': PROTOCOL_NAME,
            'order_name': ORDER_NAME_FFS,
            'num_fx': nfx,
            'site': 'TBI_',
            'translation_map': {ORDER_TARGET_NAME_FFS: (TARGET_FFS, rx, r'cGy')},
            'beamset_name': BEAMSET_FFS,
            'iso_target': iso_target,
            'machine': MACHINE,
            'user_prompts': True,
        }
        pd_ffs_out = autoplan(testing_bypass_dialogs=tbi_ffs_protocol)
    do_this = True
    if do_this:
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

        make_ffs_isodoses(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, rx)
        # ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        #     FromExamination=ffs_scan_name,
        #     ToExamination=hfs_scan_name)
        # # Convert it to the transform dictionary
        # trans_f2h = convert_array_to_transform(ffs_to_hfs)
        # # If we pair the junctions and isodoses up front we can do this as one iteration
        # # d_i = {<junction_region>: (low95%, med100%, high110%)}
        # # Isodoses to get:
        # d_i = [5, 10, 15, 20, 25, 30, 35, 40, 45,
        #        50, 55, 60, 65, 70, 75, 80, 85, 90,
        #        95, 100, 105, 110, 115]
        # #
        # # Get clean unsubtracted doses
        # doses = dict([(str(d) + '%Rx', d) for d in d_i])
        # make_unsubtracted_dose_structures(pd_ffs, rx, doses)
        # # Junctions
        # j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        # # construct pairs
        # j_names = dict([(JUNCTION_PREFIX_FFS + str(j) + '%Rx', (j + 10, j, j - 5)) for j in j_i])
        # #
        # # Generate subtracted dose values
        # isodose_names = make_dose_structures(pd_ffs, isodoses=j_names, rx=rx)
        # # for n in j_i:
        # #     name = JUNCTION_PREFIX_FFS +str(n)+'%Rx'
        # #     j_names[name] = (n+10, n, n-5)
        # #     isodose_names = make_dose_structures(pd_ffs, isodoses=j_names, rx=rx)
        # #     break
        # # Map the junction point
        # non_empty_isodose_names = []
        # for idn in isodose_names:
        #     dose_roig = get_roi_geometries(pd_hfs.case, pd_hfs.exam, idn)
        #     if dose_roig.HasContours():
        #         non_empty_isodose_names.append(idn)
        # pd_hfs.case.MapRoiGeometriesRigidly(
        #     RoiGeometryNames=non_empty_isodose_names,
        #     CreateNewRois=False,
        #     ReferenceExaminationName=ffs_scan_name,
        #     TargetExaminationNames=[hfs_scan_name],
        #     Transformations=[trans_f2h])

    do_this = True
    if do_this:
        reset_primary_secondary(pd_hfs.exam, pd_ffs.exam)
        #
        # HFS Planning
        # HFS protocol declarations
        tbi_hfs_protocol = {
            'protocol_name': PROTOCOL_NAME,
            'order_name': ORDER_NAME_HFS,
            'num_fx': nfx,
            'site': 'TBI_',
            'translation_map': {ORDER_TARGET_NAME_HFS: (TARGET_HFS, rx, r'cGy')},
            'beamset_name': BEAMSET_HFS,
            'iso_target': TARGET_HFS,
            'machine': MACHINE,
            'user_prompts': True,
        }
        pd_hfs_out = autoplan(testing_bypass_dialogs=tbi_hfs_protocol)
    #
    # TODO: Build a plan sum of the FFS and HFS plans (will need to get a larger dose grid for the HFS plan)


if __name__ == '__main__':
    main()
