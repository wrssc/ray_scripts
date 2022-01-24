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
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/AutoPlanTomoTBI'
__credits__ = []

from collections import namedtuple
import logging
import connect
import UserInterface
import sys
import GeneralOperations
import AutoPlanOperations
import StructureOperations


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
    [roi_check] = StructureOperations.check_roi(case,exam,rois=roi_name)
    if not roi_check:
        return None
    bb_roi = case.PatientModel.StructureSets[exam.Name]\
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
    [roi_check] = StructureOperations.check_roi(case,exam,rois=roi_name)
    if not roi_check:
        return None
    bb_roi = case.PatientModel.StructureSets[exam.Name]\
                 .RoiGeometries[roi_name].GetBoundingBox()
    c = {'x': bb_roi[0].x +(bb_roi[1].x - bb_roi[0].x)/2,
         'y': bb_roi[0].y +(bb_roi[1].y - bb_roi[0].y)/2,
         'z': bb_roi[0].z +(bb_roi[1].z - bb_roi[0].z)/2}
    return c


def find_junction_coords(pd_hfs):
    # Find which kidney is lower
    # Move this to a function that runs first with Kidneys already defined.
    roi_1 = 'Kidney_L'
    roi_2 = 'Kidney_R'
    [external_name] = StructureOperations.find_types(pd_hfs.case,roi_type='External')
    hfs_roi_1_z = get_most_inferior(pd_hfs.case, pd_hfs.exam, roi_1)
    hfs_roi_2_z = get_most_inferior(pd_hfs.case, pd_hfs.exam, roi_2)
    center = get_center(pd_hfs.case,pd_hfs.exam,external_name)
    return {
        'x': center['x'],
        'y': center['y'],
        'z': min(hfs_roi_1_z, hfs_roi_2_z)
    }

def place_poi(pd_hfs, coord_hfs):
    # Create a junction point and use the coordinates determined above

    poi_status = StructureOperations.create_poi(
        case = pd_hfs.case,
        exam = pd_hfs.exam,
        coords = [coord_hfs['x'], coord_hfs['y'], coord_hfs['z']],
        name = 'Junction',
        color = 'Red',
        diameter=1,
        rs_type = 'Control'
        )

def convert_array_to_transform(t):
    # Converts into the expected values for an RS transform dictionary
    return {'M11':  t[0], 'M12':  t[1], 'M13':  t[2], 'M14':  t[3],
            'M21':  t[4], 'M22':  t[5], 'M23':  t[6], 'M24':  t[7],
            'M31':  t[8], 'M32':  t[9], 'M33': t[10], 'M34': t[11],
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

def update_all_remove_expression(pdata,roi_name):
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

def make_junction_contour(pdata,junct_name,z_start, dim_si, dose_level, color=[192, 192, 192]):
    #  Make the Box Roi and junction region in the area of interest
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix =='ffs':
        si = -1.
    elif prefix == 'hfs':
        si =  1.
    # Find the name of the external contour
    external_name = StructureOperations.find_types(pdata.case,roi_type='External')[0]
    #
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name]\
                 .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(pdata.case,pdata.exam,roi_name=external_name)
    #
    # Make a box ROI that starts at z_start and ends at z_start + dim_si
    box_name = 'box_'+str(round(z_start,1))
    box_geom = StructureOperations.create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=box_name,
        delete_existing=True)
    StructureOperations.exclude_from_export(pdata.case,box_name)
    #
    # Make the box geometry
    box_geom.OfRoi.CreateBoxGeometry(
                Size={'x': abs(bb_external[1].x-bb_external[0].x)+1,
                      'y': abs(bb_external[1].y-bb_external[0].y)+1,
                      'z': dim_si},
                Examination=pdata.exam,
                Center={'x': c_external['x'],
                        'y': c_external['y'],
                        'z': z_start + si * dim_si/2.},
                Representation='Voxels',
                VoxelSize=None)
    junction_name = prefix+"_junction_"+str(dose_level)
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
    update_all_remove_expression(pdata=pdata,roi_name=junction_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()

def make_avoid(pdata,z_start, avoid_name,color=[192, 192, 192]):
    # Take the z_start, build a box that is everything above this position
    # Find the intersection with the external. This is the avoidance volume:
    # avoid_name
    # Find the name of the external contour
    external_name = StructureOperations.find_types(pdata.case,roi_type='External')[0]
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix =='ffs':
        si = -1.
        bb_index = 1
    elif prefix == 'hfs':
        si =  1.
        bb_index = 0
    #
    # Get the Bounding box of the External contour
    bb_external = pdata.case.PatientModel.StructureSets[pdata.exam.Name]\
                 .RoiGeometries[external_name].GetBoundingBox()
    c_external = get_center(pdata.case,pdata.exam,roi_name=external_name)
    #
    # Make a box ROI that starts at z_start and ends at z_start + dim_si
    box_name = 'avoid_box_'+str(round(z_start,1))
    box_geom = StructureOperations.create_roi(
        case=pdata.case,
        examination=pdata.exam,
        roi_name=box_name,
        delete_existing=True)
    StructureOperations.exclude_from_export(pdata.case,box_name)
    logging.debug('ROI name is {}'.format(box_geom.OfRoi.Name))
    si_box_size = abs(bb_external[bb_index].z + si * z_start)
    box_geom.OfRoi.CreateBoxGeometry(
                Size={'x': abs(bb_external[1].x-bb_external[0].x)+1,
                      'y': abs(bb_external[1].y-bb_external[0].y)+1,
                      'z': si_box_size},
                Examination=pdata.exam,
                Center={'x': c_external['x'],
                        'y': c_external['y'],
                        'z': z_start - si * si_box_size/2.},
                Representation='Voxels',
                VoxelSize=None)
    #
    # Boolean Definitions
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
                "SourcesB": [Lung_L,Lung_R],
                "MarginTypeB": "Contract",
                "ExpB": [0.7] * 6,
                "OperationResult": "None",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined",
            }
    StructureOperations.make_boolean_structure(
        patient=pdata.patient, case=pdata.case, examination=pdata.exam, **temp_defs)
    # update_all_remove_expression(pdata=pdata,roi_name=box_name)
    update_all_remove_expression(pdata=pdata,roi_name=avoid_name)
    pdata.case.PatientModel.RegionsOfInterest[box_name].DeleteRoi()


def make_PTV(pdata, junction_prefix, avoid_name,color=[192, 192, 192]):
    # Find all contours matching prefix and along with avoid_name return the external minus these objects
    #
    # Get exam orientation
    prefix = determine_prefix(pdata.exam)
    if prefix =='ffs':
        si = -1.
    elif prefix == 'hfs':
        si =  1.
    #
    # PTV_name
    ptv_name = "PTV_p_" + prefix.upper()
    external_name = StructureOperations.find_types(pdata.case,roi_type='External')[0]
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


def make_dose_structs(pdata,isodoses, rx):
    # make doses from structs and return names of created rois
    # The resulting structs will be structures of at least the
    # defined isodose and at most the next highest level
    # isodoses {junction_name_on_ffs_scan: (110%, 100%, 95% Desired Dose in Junction)}
    #
    subtract_higher = False # Used to skip the boolean on the highest level isodose
    #
    # Resort isodoses, highest to lowest
    isodose_contours = []
    # sorted_isodoses = sorted(isodoses, reverse=True)
    # Avoid circular dependencies by storing raw doses, and delete when finished
    unsubtracted_doses = []
    # The output: subtracted doses
    subtracted_isodoses =[] #TODO: Test with just the highest level
    for k, v in isodoses.items():
        # Make a subtracted dose to roi
        subtract_higher = False
        for d in v:
            threshold_level = (float(d)/100.) * rx #in cGy
            unsubtracted_roi_name = str(d) +'%Rx'
            # Make unsubtracted (raw) dose
            unsubtracted_doses.append(unsubtracted_roi_name)
            raw_geometry = StructureOperations.create_roi(
                case=pdata.case,
                examination=pdata.exam,
                roi_name=unsubtracted_roi_name,
                delete_existing=True)
            raw = pdata.case.PatientModel.RegionsOfInterest[unsubtracted_roi_name]
            raw.CreateRoiGeometryFromDose(
                    DoseDistribution=pdata.plan.TreatmentCourse.TotalDose,
                    ThresholdLevel=threshold_level)
            roi_name = 'ffs_'+ k + '_dose_' + str(d) + '%Rx'
            roi_geometry = StructureOperations.create_roi(
                case=pdata.case,
                examination=pdata.exam,
                roi_name=roi_name,
                delete_existing=True)
            # Boolean Definitions
            if subtract_higher:
                temp_defs = {
                            "StructureName": roi_name,
                            "ExcludeFromExport": False,
                            "VisualizeStructure": False,
                            "StructColor": [192, 192, 192],
                            "OperationA": "Intersection",
                            "SourcesA": [k, unsubtracted_roi_name],
                            "MarginTypeA": "Expand",
                            "ExpA": [0] * 6,
                            "OperationB": "Union",
                            "SourcesB": subtracted_isodoses,
                            "MarginTypeB": "Expand",
                            "ExpB": [0] * 6,
                            "OperationResult": "Subtraction",
                            "MarginTypeR": "Expand",
                            "ExpR": [0] * 6,
                            "StructType": "Control",
                        }
            else:
                temp_defs = {
                            "StructureName": roi_name,
                            "ExcludeFromExport": False,
                            "VisualizeStructure": False,
                            "StructColor": [192, 192, 192],
                            "OperationA": "Union",
                            "SourcesA": [k, unsubtracted_roi_name],
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
            subtract_higher = True # Skip First isodose
            subtracted_isodoses.append(roi_name)
            isodose_contours.append(roi_name)
    for d in unsubtracted_doses:
        pdata.case.PatientModel.RegionsOfInterest[d].DeleteRoi()
    return isodose_contours




def main():
    # TODO: Replace with user prompt
    # Add lungs - 7mm

    hfs_scan_name = 'CT 1'
    ffs_scan_name = 'CT 2'
    # TODO: Target dialog build
    rx = 800. # cGy
    nfx = 4 # Num fraction
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd_hfs = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = GeneralOperations.find_scope(level='Examination'),
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = None,
            beamset = None)
    pd_ffs = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = pd_hfs.case.Examinations[ffs_scan_name],
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = None,
            beamset = None)

    # TODO: Get Exam2 loaded as a pd2
    # Load the Tomo Supports for the couch
    AutoPlanOperations.load_supports(pd=pd_hfs,supports=["TomoCouch"])
    AutoPlanOperations.load_supports(pd=pd_ffs,supports=["TomoCouch"])
    # TODO: Use DJ's couch script
    # Make external clean on both
    external_name = "ExternalClean"
    ext_clean = StructureOperations.make_externalclean(
         patient=pd_hfs.patient,
         case=pd_hfs.case,
         examination=pd_hfs.exam,
         structure_name=external_name,
         suffix=None,
         delete=True,
     )
    externals = StructureOperations.find_types(case=pd_hfs.case, roi_type="External")
    if externals:
        current_external = pd_hfs.case.PatientModel.RegionsOfInterest[externals[0]]
    current_external.CreateExternalGeometries(
        ReferenceExamination=pd_hfs.exam,
        AdditionalExaminationNames=[ffs_scan_name],
        ReferenceThresholdLevel=-250)

    # TODO: No external contour is created on the ffs scan.
    #ext_clean = StructureOperations.make_externalclean(
    #    patient=pd_ffs.patient,
    #    case=pd_ffs.case,
    #    examination=pd_ffs.exam,
    #    structure_name=external_name,
    #    suffix=None,
    #    delete=False,
    #)

    """
    with connect.CompositeAction('Create external (External, Image set: CT 1, CT 2)'):

        retval_0 = pd_hfs.case.PatientModel.CreateRoi(Name=r"ExternalClean",
                                               Color="Green",
                                               Type="External",
                                               TissueName=r"",
                                               RbeCellTypeName=None,
                                               RoiMaterial=None)
        retval_0.CreateExternalGeometries(ReferenceExamination=pd_hfs.exam,
                                          AdditionalExaminationNames=[ffs_scan_name],
                                          ReferenceThresholdLevel=-250)
    """
    # CompositeAction ends


    pd_hfs.case.ComputeRigidImageRegistration(
        FloatingExaminationName=ffs_scan_name,
        ReferenceExaminationName=hfs_scan_name,
        UseOnlyTranslations=False,
        HighWeightOnBones=False,
        InitializeImages=True,
        FocusRoisNames=[],
        RegistrationName=None)

    # Refine on bones
    pd_hfs.case.ComputeRigidImageRegistration(
        FloatingExaminationName=ffs_scan_name,
        ReferenceExaminationName=hfs_scan_name,
        UseOnlyTranslations=False,
        HighWeightOnBones=True,
        InitializeImages=False,
        FocusRoisNames=[],
        RegistrationName=None)
    # TODO: Move to fusion view and create a suitable view for reviewing fusion at hips
    connect.await_user_input(
        'Check the fusion alignment of the boney anatomy in the hips. Then continue script.')

    pd_hfs.case.PatientModel.MBSAutoInitializer(
        MbsRois=[{'CaseType': "Abdomen",
                'ModelName': r"Kidney (Left)",
                'RoiName': r"Kidney_L",
                'RoiColor': "58, 251, 170" },
                {'CaseType': "Abdomen",
                'ModelName': r"Kidney (Right)",
                'RoiName': r"Kidney_R",
                'RoiColor': "250, 57, 105" },
                {'CaseType': "Thorax",
                'ModelName': r"Lung (Left)",
                'RoiName': r"Lung_L",
                'RoiColor': "253, 122, 9" },
                {'CaseType': "Thorax",
                'ModelName': r"Lung (Right)",
                'RoiName': r"Lung_R",
                'RoiColor': "54, 247, 223" }],
                CreateNewRois=True,
                Examination=pd_hfs.exam,
                UseAtlasBasedInitialization=True)

    pd_hfs.case.PatientModel.AdaptMbsMeshes(
        Examination=pd_hfs.exam,
        RoiNames=[r"Lung_L",
                  r"Lung_R",
                  r"Kidney_L",
                  r"Kidney_R"],
        CustomStatistics=None,
        CustomSettings=None)

    # Try a repeat on FFS
    pd_hfs.case.PatientModel.MBSAutoInitializer(
        MbsRois=[{'CaseType': "Abdomen",
                'ModelName': r"Kidney (Left)",
                'RoiName': r"Kidney_L",
                'RoiColor': "58, 251, 170" },
                {'CaseType': "Abdomen",
                'ModelName': r"Kidney (Right)",
                'RoiName': r"Kidney_R",
                'RoiColor': "250, 57, 105" },
                {'CaseType': "Thorax",
                'ModelName': r"Lung (Left)",
                'RoiName': r"Lung_L",
                'RoiColor': "253, 122, 9" },
                {'CaseType': "Thorax",
                'ModelName': r"Lung (Right)",
                'RoiName': r"Lung_R",
                'RoiColor': "54, 247, 223" }],
                CreateNewRois=False,
                Examination=pd_ffs.exam,
                UseAtlasBasedInitialization=True)

    pd_hfs.case.PatientModel.AdaptMbsMeshes(
        Examination=pd_ffs.exam,
        RoiNames=[r"Lung_L",
                  r"Lung_R",
                  r"Kidney_L",
                  r"Kidney_R"],
        CustomStatistics=None,
        CustomSettings=None)

    # TODO: Add a check on all contours
    # Add a prefix_avoid_lung_m07
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
    pd_hfs.case.PatientModel.CreateRoi(
        Name="External_PRV10",
        Color="255, 128, 0",
        Type="IrradiatedVolume",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None)
    pd_hfs.case.PatientModel.RegionsOfInterest['External_PRV10'].SetMarginExpression(
        SourceRoiName=external_name,
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
        PoiGeometryNames=['Junction'],
        CreateNewPois=False,
        ReferenceExaminationName=hfs_scan_name,
        TargetExaminationNames=[ffs_scan_name],
        Transformations=[trans_h2f])

    #
    # FFS Junction
    ffs_poi_junction = pd_ffs.case.PatientModel.StructureSets[pd_ffs.exam.Name]\
                  .PoiGeometries['Junction']
    # IsoDose levels:
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    dim_si = 2.5
    dose_levels = {10:  [127, 0, 255],
                   20:  [0, 0, 255],
                   30:  [0, 127, 255],
                   40:  [0, 255, 255],
                   50:  [0, 255, 127],
                   60:  [0, 255, 0],
                   70:  [127, 255, 0],
                   80:  [255, 255, 0],
                   90:  [255, 127, 0],
                   95:  [255, 0, 0],
                   100: [255, 0, 255]}

    for i in range(len(j_i)):
        make_junction_contour(pd_ffs,
                              junct_name='Junction',
                              z_start=ffs_poi_junction.Point.z - float(i)*dim_si,
                              dim_si = dim_si,
                              dose_level = str(int(j_i[i]))+"%Rx",
                              color=dose_levels[j_i[i]])
    # TODO: Set junction colors to the optimal isodose color
    make_avoid(pd_ffs,z_start=ffs_poi_junction.Point.z,avoid_name="avoid_FFS")
    make_PTV(pdata=pd_ffs,junction_prefix="ffs_junction_",avoid_name="avoid_FFS")
    #
    # HFS Junction
    hfs_poi_junction = pd_hfs.case.PatientModel.StructureSets[pd_hfs.exam.Name]\
                      .PoiGeometries['Junction']
    for i in range(len(j_i)):
        make_junction_contour(pd_hfs,
                              junct_name='Junction',
                              z_start=hfs_poi_junction.Point.z - dim_si * float(len(j_i) - i),
                              dim_si = dim_si,
                              dose_level = str(int(j_i[i]))+"%Rx",
                              color=dose_levels[j_i[i]])
    #
    # HFS avoid starts at junction point - number of dose levels * dim_si
    hfs_avoid_start = hfs_poi_junction.Point.z - dim_si * float(len(j_i))
    # TODO: underive and delete geometry on avoid volumes defined on incorrect scans
    # then map them over
    make_avoid(pd_hfs,z_start=hfs_avoid_start,avoid_name="avoid_HFS")
    make_PTV(pdata=pd_hfs,junction_prefix="hfs_junction_",avoid_name="avoid_HFS")


# Get isodoses
    pd_ffs = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = pd_hfs.case.Examinations[ffs_scan_name],
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = GeneralOperations.find_scope(level='Plan'),
            beamset = GeneralOperations.find_scope(level='BeamSet'))

    ffs_to_hfs = pd_ffs.case.GetTransformForExaminations(
        FromExamination=ffs_scan_name,
        ToExamination=hfs_scan_name)
    # Convert it to the transform dictionary
    trans_f2h = convert_array_to_transform(ffs_to_hfs)
    # If we pair the junctions and isodoses up front we can do this as one iteration
    # d_i = {<junction_region>: (low95%, med100%, high110%)}
    # Isodoses to get:
    j_i = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    d_i = [5, 10, 15, 20, 25, 30, 35, 40, 45,
           50, 55, 60, 65, 70, 75, 80, 85, 90,
           95, 100, 105, 110, 115]
    # construct pairs
    j_names = {}
    for n in j_i:
        name = 'ffs_junction_'+str(n)+'%Rx'
        j_names[name] = (n-5, n, n+10)
        isodose_names = make_dose_structs(pd_ffs, isodoses=j_names, rx=rx)
        break
    # Map the junction point
    pd_hfs.case.MapRoiGeometriesRigidly(
        RoiGeometryNames=isodose_names,
        CreateNewRois=False,
        ReferenceExaminationName=ffs_scan_name,
        TargetExaminationNames=[hfs_scan_name],
        Transformations=[trans_f2h])


    sys.exit('Done')

    sys.exit('Script Complete')
    # Determine the inferior most part of the kidneys in both examinations
    box = case.PatientModel.CreateRoi(Name='Box_1',
                                    Color='Red',
                                    Type='Organ',
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)






    # Script will run through the following steps.  We have a logical inconsistency here with making a plan
    # this is likely an optional step
    status = UserInterface.ScriptStatus(
        steps=['SimFiducials point declaration',
               'Making the target',
               'Verify PTV_WB_xxxx coverage',
               'User Inputs Plan Information',
               'Regions at Risk Generation/Validation',
               'Support Structure Loading',
               'Target (BTV) Generation',
               'Plan Generation (Optional)'],
        docstring=__doc__,
        help=__help__)

    # UW Inputs
    # If machines names change they need to be modified here:
    institution_inputs_machine_name = ['TrueBeamSTx', 'TrueBeam']
    # The s-frame object currently belongs to an examination on rando named: "Supine Patient"
    # if that changes the s-frame load will fail
    institution_inputs_support_structures_examination = "Supine Patient"
    institution_inputs_support_structure_template = "UW Support"
    institution_inputs_source_roi_names = ['S-frame']
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        patient_db = connect.get_current('PatientDB')
    except:
        UserInterface.WarningBox('This script requires a patient, case, and exam to be loaded')
        sys.exit('This script requires a patient, case, and exam to be loaded')

    # Capture the current list of ROI's to avoid saving over them in the future
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries

    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest

    visible_structures = ['PTV_WB_xxxx', 'Lens_L', 'Lens_R']
    invisible_stuctures = [
        'Eye_L',
        'Eye_R',
        'External',
        'S-frame',
        'Avoid',
        'Avoid_Face',
        'Lens_R_PRV05',
        'Lens_L_PRV05',
        'BTV_Brain',
        'BTV_Flash_20',
        'BTV',
        'Brain']
    export_exclude_structs = [
        'Eye_L',
        'Eye_R',
        'Avoid',
        'Avoid_Face',
        'Lens_R_PRV05',
        'Lens_L_PRV05',
        'BTV_Brain',
        'BTV_Flash_20',
        'BTV']
    # Try navigating to the points tab
    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['POI tools'].Select()
        ui.ToolPanel.TabItem['POIs'].Select()
    except:
        logging.debug("Could not click on the patient modeling window")

    # Look for the sim point, if not create a point
    sim_point_found = any(poi.Name == 'SimFiducials' for poi in pois)
    if sim_point_found:
        logging.warning("POI SimFiducials Exists")
        status.next_step(text="SimFiducials Point found, ensure that it is placed properly")
        connect.await_user_input(
            'Ensure Correct placement of the SimFiducials Point and continue script.')
    else:
        poi_status = StructureOperations.create_poi(
            case=case, exam=examination, coords=[0., 0., 0.],
            name="SimFiducials",color="Green", rs_type='LocalizationPoint')
        if poi_status:
            logging.warning('Error detected creating SimFiducial point{}'.format(poi_status))
            sys.exit('Error detected creating SimFiducial point{}'.format(poi_status))
        else:
            status.next_step(text="SimFiducials POI created, ensure that it is placed properly")
            connect.await_user_input(
                'Ensure Correct placement of the SimFiducials Point and continue script.')

    # Generate the target based on an MBS brain contour
    status.next_step(text="The PTV_WB_xxxx target is being generated")
    if not check_structure_exists(case=case, structure_name='PTV_WB_xxxx', roi_list=rois,
                                  option='Check'):
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Brain",
                      'RoiName': "PTV_WB_xxxx",
                      'RoiColor': "255, 255, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)

        case.PatientModel.AdaptMbsMeshes(Examination=examination,
                                         RoiNames=["PTV_WB_xxxx"],
                                         CustomStatistics=None,
                                         CustomSettings=None)

        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(
            Examination=examination,
            CustomStatistics=None,
            CustomSettings=[{'ShapeWeight': 0.5,
                             'TargetWeight': 0.7,
                             'MaxIterations': 70,
                             'OnlyRigidAdaptation': False,
                             'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(
            Examination=examination,
            CustomStatistics=None,
            CustomSettings=[{'ShapeWeight': 0.5,
                             'TargetWeight': 0.5,
                             'MaxIterations': 50,
                             'OnlyRigidAdaptation': False,
                             'ConvergenceCheck': False}])
        status.next_step(text="The target was auto-generated based on the brain," +
                              " and the computer is not very smart. Check the PTV_WB_xxxx carefully")
    else:
        status.next_step(text="Existing target was used. Check the PTV_WB_xxxx carefully")

    case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].Type = "Ptv"

    case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].OrganData.OrganType = "Target"

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['ROI tools'].Select()
        ui.ToolPanel.TabItem['ROIs'].Select()
    except:
        logging.debug("Could not click on the patient modeling window")

    connect.await_user_input(
        'Ensure the PTV_WB_xxxx encompasses the brain and C1 and continue playing the script')

    # Get some user data
    status.next_step(text="Complete plan information - check the TPO for doses " +
                          "and ARIA for the treatment machine")
    # This dialog grabs the relevant parameters to generate the whole brain plan
    input_dialog = UserInterface.InputDialog(
        inputs={
            'input0_make_plan': 'Create the RayStation Plan',
            'input1_plan_name': 'Enter the Plan Name, typically Brai_3DC_R0A0',
            'input2_number_fractions': 'Enter the number of fractions',
            'input3_dose': 'Enter total dose in cGy',
            'input4_choose_machine': 'Choose Treatment Machine'
        },
        title='Whole Brain Plan Input',
        datatype={'input0_make_plan': 'check',
                  'input4_choose_machine': 'combo'
                  },
        initial={
            'input0_make_plan': ['Make Plan'],
            'input1_plan_name': 'Brai_3DC_R0A0',
        },
        options={'input0_make_plan': ['Make Plan'],
                 'input4_choose_machine': institution_inputs_machine_name,
                 },
        required=['input2_number_fractions',
                  'input3_dose',
                  'input4_choose_machine'])

    # Launch the dialog
    response = input_dialog.show()
    # Close on cancel
    if response == {}:
        logging.info('autoplan whole brain cancelled by user')
        sys.exit('autoplan whole brain cancelled by user')
    else:
        logging.debug('User selected {} for make plan'.format(
            input_dialog.values['input0_make_plan']))

    # Parse the outputs
    # User selected that they want a plan-stub made
    if 'Make Plan' in input_dialog.values['input0_make_plan']:
        make_plan = True
    else:
        make_plan = False
    plan_name = input_dialog.values['input1_plan_name']
    number_of_fractions = float(input_dialog.values['input2_number_fractions'])
    total_dose = float(input_dialog.values['input3_dose'])
    plan_machine = input_dialog.values['input4_choose_machine']

    ## patient.Save()

    # MBS generate the globes. Manually draw lenses
    status.next_step(text="Regions at risk will be created including Eyes, Lenses, and Brain.")
    brain_exists = check_structure_exists(case=case,
                                          structure_name='Brain',
                                          roi_list=rois,
                                          option='Check')
    if not brain_exists:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Brain",
                      'RoiName': "Brain",
                      'RoiColor': "255, 255, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Brain'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.0,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
    if any(roi.OfRoi.Name == 'Eye_L' for roi in rois):
        connect.await_user_input('Eye_L Contour Exists - Verify its accuracy and continue script')
    else:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Eye (Left)",
                      'RoiName': "Eye_L",
                      'RoiColor': "255, 128, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Eye_L'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 2.0,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['Eye_L'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.25,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
    if any(roi.OfRoi.Name == 'Eye_R' for roi in rois):
        connect.await_user_input('Eye_R Contour Exists - Verify its accuracy and continue script')
    else:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Eye (Right)",
                      'RoiName': "Eye_R",
                      'RoiColor': "255, 128, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Eye_R'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 2.0,
                'TargetWeight': 1,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['Eye_R'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.25,
                'TargetWeight': 1,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])

    if not check_structure_exists(case=case, structure_name='Lens_L', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name='Lens_L',
                                    Color="Purple",
                                    Type="Organ",
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        connect.await_user_input('Draw the LEFT Lens then continue playing the script')

    if not check_structure_exists(case=case, structure_name='Lens_R', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name="Lens_R",
                                    Color="Purple",
                                    Type="Organ",
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        connect.await_user_input('Draw the RIGHT Lens then continue playing the script')

    if not check_structure_exists(case=case, structure_name='External', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name="External",
                                    Color="Blue",
                                    Type="External",
                                    TissueName="",
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        case.PatientModel.RegionsOfInterest['External'].CreateExternalGeometry(
            Examination=examination,
            ThresholdLevel=-250)
    else:
        if not check_external(rois):
            logging.warning('No External-Type Contour designated-Restart'
                            ' script after choosing External-Type')
            sys.exit

    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Lens_L_PRV05'):
        logging.info('Lens_L_PRV05 not found, generating from expansion')

    case.PatientModel.CreateRoi(
        Name="Lens_L_PRV05",
        Color="255, 128, 0",
        Type="Avoidance",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].SetMarginExpression(
        SourceRoiName="Lens_L",
        MarginSettings={'Type': "Expand",
                        'Superior': 0.5,
                        'Inferior': 0.5,
                        'Anterior': 0.5,
                        'Posterior': 0.5,
                        'Right': 0.5,
                        'Left': 0.5})
    case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].UpdateDerivedGeometry(
        Examination=examination, Algorithm="Auto")

    # The Lens_R prv will always be "remade"
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Lens_R_PRV05'):
        logging.info('Lens_R_PRV05 not found, generating from expansion')

    case.PatientModel.CreateRoi(
        Name="Lens_R_PRV05",
        Color="255, 128, 0",
        Type="Avoidance",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].SetMarginExpression(
        SourceRoiName="Lens_R",
        MarginSettings={'Type': "Expand",
                        'Superior': 0.5,
                        'Inferior': 0.5,
                        'Anterior': 0.5,
                        'Posterior': 0.5,
                        'Right': 0.5,
                        'Left': 0.5})
    case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Avoid'):
        logging.info('Avoid not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="Avoid",
                                Color="255, 128, 128",
                                Type="Avoidance",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Avoid'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["Lens_L_PRV05",
                                        "Lens_R_PRV05"],
                     'MarginSettings': {
                         'Type': "Expand",
                         'Superior': 0,
                         'Inferior': 0,
                         'Anterior': 0,
                         'Posterior': 0,
                         'Right': 0,
                         'Left': 0}},
        ExpressionB={'Operation': "Union",
                     'SourceRoiNames': [],
                     'MarginSettings': {
                         'Type': "Expand",
                         'Superior': 0,
                         'Inferior': 0,
                         'Anterior': 0,
                         'Posterior': 0,
                         'Right': 0,
                         'Left': 0}},
        ResultOperation="None",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})
    case.PatientModel.RegionsOfInterest['Avoid'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # S - frame loading
    status.next_step(text="Roi contouring complete, loading patient immobilization.")
    # Load the S-frame into the current scan based on the structure template input above.
    # This operation is not supported in RS7, however, when we convert to RS8, this should work
    try:
        if check_structure_exists(case=case, roi_list=rois, option='Check',
                                  structure_name='S-frame'):
            logging.info('S-frame found, bugging user')
            connect.await_user_input(
                'S-frame present. ' +
                'Ensure placed correctly then continue script')
        else:
            support_template = patient_db.LoadTemplatePatientModel(
                templateName=institution_inputs_support_structure_template,
                lockMode='Read')

            case.PatientModel.CreateStructuresFromTemplate(
                SourceTemplate=support_template,
                SourceExaminationName=institution_inputs_support_structures_examination,
                SourceRoiNames=institution_inputs_source_roi_names,
                SourcePoiNames=[],
                AssociateStructuresByName=True,
                TargetExamination=examination,
                InitializationOption='AlignImageCenters'
            )
            connect.await_user_input(
                'S-frame automatically loaded. ' +
                'Ensure placed correctly then continue script')

        status.next_step(
            text='S-frame has been loaded. Ensure its alignment and continue the script.')
    except Exception:
        logging.warning('Support structure failed to load and was not found')
        status.next_step(text='S-frame failed to load and was not found. ' +
                              'Load manually and continue script.')
        connect.await_user_input(
            'S-frame failed to load and was not found. ' +
            'Ensure it is loaded and placed correctly then continue script')

    # Creating planning structures for treatment and protect
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='BTV_Brain'):
        logging.info('BTV_Brain not found, generating from expansion')

    status.next_step(text='Building planning structures')

    case.PatientModel.CreateRoi(Name="BTV_Brain", Color="128, 0, 64", Type="Ptv", TissueName=None,
                                RbeCellTypeName=None, RoiMaterial=None)

    case.PatientModel.RegionsOfInterest['BTV_Brain'].SetMarginExpression(
        SourceRoiName="PTV_WB_xxxx",
        MarginSettings={'Type': "Expand",
                        'Superior': 1,
                        'Inferior': 0.5,
                        'Anterior': 0.8,
                        'Posterior': 2,
                        'Right': 1,
                        'Left': 1})
    case.PatientModel.RegionsOfInterest['BTV_Brain'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # Avoid_Face - creates a block that will avoid treating the face
    # This contour extends down 10 cm from the brain itself.  Once this is subtracted
    # from the brain - this will leave only the face
    if not check_structure_exists(case=case,
                                  roi_list=rois,
                                  option='Delete',
                                  structure_name='Avoid_Face'):
        logging.info('Avoid_Face not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="Avoid_Face",
                                Color="255, 128, 128",
                                Type="Organ",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Avoid_Face'].SetMarginExpression(
        SourceRoiName="PTV_WB_xxxx",
        MarginSettings={'Type': "Expand",
                        'Superior': 0,
                        'Inferior': 10,
                        'Anterior': 0,
                        'Posterior': 0,
                        'Right': 0,
                        'Left': 0})
    case.PatientModel.RegionsOfInterest['Avoid_Face'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # BTV_Flash_20: a 2 cm expansion for flash except in the directions the MD's wish to have no flash
    # Per MD's flashed dimensions are superior, anterior, and posterior
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='BTV_Flash_20'):
        logging.info('BTV_Flash_20 not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="BTV_Flash_20",
                                Color="128, 0, 64",
                                Type="Ptv",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)

    case.PatientModel.RegionsOfInterest['BTV_Flash_20'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["PTV_WB_xxxx"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 2,
                                        'Inferior': 0,
                                        'Anterior': 2,
                                        'Posterior': 2,
                                        'Right': 0,
                                        'Left': 0}},
        ExpressionB={'Operation': "Union",
                     'SourceRoiNames': ["Avoid_Face"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ResultOperation="Subtraction",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})

    case.PatientModel.RegionsOfInterest['BTV_Flash_20'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # BTV: the block target volume.  It consists of the BTV_Brain, BTV_Flash_20 with no additional structures
    # We are going to make the BTV as a fixture if we are making a plan so that we can autoset the dose grid
    if not check_structure_exists(case=case, roi_list=rois, option='Delete', structure_name='BTV'):
        logging.info('BTV not found, generating from expansion')

    if make_plan:
        btv_temporary_type = "Fixation"
    else:
        btv_temporary_type = "Ptv"

    case.PatientModel.CreateRoi(Name="BTV",
                                Color="Yellow",
                                Type=btv_temporary_type,
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['BTV'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["BTV_Brain",
                                        "BTV_Flash_20"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ExpressionB={'Operation': "Intersection",
                     'SourceRoiNames': [],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ResultOperation="None",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})

    case.PatientModel.RegionsOfInterest['BTV'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # Change visibility of structures
    for s in visible_structures:
        try:
            patient.SetRoiVisibility(RoiName=s,
                                     IsVisible=True)
        except:
            logging.debug("Structure: {} was not found".format(s))

    for s in invisible_stuctures:
        try:
            patient.SetRoiVisibility(RoiName=s,
                                     IsVisible=False)
        except:
            logging.debug("Structure: {} was not found".format(s))
    # Exclude these from export
    case.PatientModel.ToggleExcludeFromExport(
        ExcludeFromExport=True,
        RegionOfInterests=export_exclude_structs,
        PointsOfInterests=[])

    if make_plan:
        try:
            ui = connect.get_current('ui')
            ui.TitleBar.MenuItem['Plan Design'].Button_Plan_Design.Click()
        except:
            logging.debug("Could not click on the plan Design MenuItem")

        plan_names = [plan_name, 'backup_r1a0']
        # RS 8: plan_names = [plan_name]
        patient.Save()
        # RS 8: eliminate for loop
        for p in plan_names:
            try:
                case.AddNewPlan(
                    PlanName=p,
                    PlannedBy="",
                    Comment="",
                    ExaminationName=examination.Name,
                    AllowDuplicateNames=False)
            except Exception:
                plan_name = p + str(random.randint(1, 999))
                case.AddNewPlan(
                    PlanName=p,
                    PlannedBy="",
                    Comment="",
                    ExaminationName=examination.Name,
                    AllowDuplicateNames=False)
            patient.Save()

            plan = case.TreatmentPlans[p]
            plan.SetCurrent()
            connect.get_current('Plan')
            # Creating a common call to a create beamset wrapper
            # will help the next time the function calls are changed
            # by RaySearch
            beamset_defs = BeamOperations.BeamSet()
            beamset_defs.rx_target = 'PTV_WB_xxxx'
            beamset_defs.number_of_fractions = number_of_fractions
            beamset_defs.total_dose = total_dose
            beamset_defs.machine = plan_machine
            beamset_defs.iso_target = 'PTV_WB_xxxx'
            beamset_defs.name = p
            beamset_defs.DicomName = p
            beamset_defs.modality = 'Photons'
            # Beamset elements derived from the protocol
            beamset_defs.technique = "Conformal"
            beamset_defs.protocol_name = "WBRT"

            beamset = BeamOperations.create_beamset(
                patient=patient,
                exam = examination,
                case=case,
                plan=plan,
                dialog=False,
                BeamSet=beamset_defs,
                create_setup_beams=False
            )

            patient.Save()

            beamset.AddDosePrescriptionToRoi(RoiName='PTV_WB_xxxx',
                                             DoseVolume=80,
                                             PrescriptionType='DoseAtVolume',
                                             DoseValue=total_dose,
                                             RelativePrescriptionLevel=1,
                                             AutoScaleDose=True)
            # Set the BTV type above to allow dose grid to cover
            case.PatientModel.RegionsOfInterest['BTV'].Type = 'Ptv'
            case.PatientModel.RegionsOfInterest['BTV'].OrganData.OrganType = 'Target'

            plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2,
                                               'y': 0.2,
                                               'z': 0.2})
            try:
                isocenter_position = case.PatientModel.StructureSets[examination.Name]. \
                    RoiGeometries['PTV_WB_xxxx'].GetCenterOfRoi()
            except Exception:
                logging.warning('Aborting, could not locate center of PTV_WB_xxxx')
                sys.exit
            ptv_wb_xxxx_center = {'x': isocenter_position.x,
                                  'y': isocenter_position.y,
                                  'z': isocenter_position.z}
            isocenter_parameters = beamset.CreateDefaultIsocenterData(Position=ptv_wb_xxxx_center)
            isocenter_parameters['Name'] = "iso_" + plan_name
            isocenter_parameters['NameOfIsocenterToRef'] = "iso_" + plan_name
            logging.info('Isocenter chosen based on center of PTV_WB_xxxx.' +
                         'Parameters are: x={}, y={}:, z={}, assigned to isocenter name{}'.format(
                             ptv_wb_xxxx_center['x'],
                             ptv_wb_xxxx_center['y'],
                             ptv_wb_xxxx_center['z'],
                             isocenter_parameters['Name']))

            beam_ener = [6, 6]
            beam_names = ['1_Brai_RLat', '2_Brai_LLat']
            beam_descrip = ['1 3DC: MLC Static Field', '2 3DC: MLC Static Field']
            beam_gant = [270, 90]
            beam_col = [0, 0]
            beam_couch = [0, 0]

            for i, b in enumerate(beam_names):
                beamset.CreatePhotonBeam(BeamQualityId=beam_ener[i],
                                     IsocenterData=isocenter_parameters,
                                     Name=b,
                                     Description=beam_descrip[i],
                                     GantryAngle=beam_gant[i],
                                     CouchRotationAngle=beam_couch[i],
                                     CollimatorAngle=beam_col[i])
            beamset.PatientSetup.UseSetupBeams = True
            # Set treat/protect and minimum MU
            for beam in beamset.Beams:
                beam.BeamMU = 1
                beam.SetTreatOrProtectRoi(RoiName='BTV')
                beam.SetTreatOrProtectRoi(RoiName='Avoid')

            beamset.TreatAndProtect(ShowProgress=True)
            # Compute the dose
            beamset.ComputeDose(
                ComputeBeamDoses=True,
                DoseAlgorithm="CCDose",
                ForceRecompute=True)

        # RS 8 delete next three lines
        plan_name_regex = '^' + plan_names[0] + '$'
        plan_information = case.QueryPlanInfo(Filter={'Name': plan_name_regex})
        case.LoadPlan(PlanInfo=plan_information[0])
        try:
            ui = connect.get_current('ui')
            ui.TitleBar.MenuItem['Plan Evaluation'].Button_Plan_Evaluation.Click()
        except:
            logging.debug("Could not click on the plan evaluation MenuItem")

    # Rename PTV per convention
    total_dose_string = str(int(total_dose))
    try:
        case.PatientModel.RegionsOfInterest[
            'PTV_WB_xxxx'].Name = 'PTV_WB_' + total_dose_string.zfill(4)
    except Exception as e:
        logging.debug('error reported {}'.format(e))
        logging.debug('cannot do name change')

    patient.Save()
    plan = case.TreatmentPlans[plan_name]
    plan.SetCurrent()
    connect.get_current('Plan')
    beamset = plan.BeamSets[plan_name]
    patient.Save()
    beamset.SetCurrent()
    connect.get_current('BeamSet')
    BeamOperations.rename_beams()
    # Set the DSP for the plan
    BeamOperations.set_dsp(plan=plan, beam_set=beamset)
    # Round MU
    # The Autoscale hides in the plan optimization hierarchy. Find the correct index.
    indx = PlanOperations.find_optimization_index(plan=plan, beamset=beamset, verbose_logging=False)
    plan.PlanOptimizations[indx].AutoScaleToPrescription = False
    BeamOperations.round_mu(beamset)
    # Round jaws to nearest mm
    logging.debug('Checking for jaw rounding')
    BeamOperations.round_jaws(beamset=beamset)


if __name__ == '__main__':
    main()
