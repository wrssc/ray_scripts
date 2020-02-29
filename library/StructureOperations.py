""" Perform structure operations on Raystation plans

    check_roi
    checks if an ROI has contours

    exists_roi
    checks if ROI is present in the contour list

    max_roi
    checks for maximum extent of an roi

    Versions:
    01.00.00 Original submission

    Known Issues:

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2019-08-03'

__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = ''
__raystation__ = '8.0.SPB'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging
import os
import sys
import connect
import clr

clr.AddReference('System.Drawing')
import System.Drawing
import numpy as np
import xml
import Xml_Out
import UserInterface
from GeneralOperations import logcrit as logcrit

import re


def exclude_from_export(case, rois):
    """Toggle export
    :param case: current case
    :param rois: name of structure to exclude"""

    if type(rois) is not list:
        rois = [rois]

    try:
        case.PatientModel.ToggleExcludeFromExport(
            ExcludeFromExport=True,
            RegionOfInterests=rois,
            PointsOfInterests=[])

    except Exception:
        logging.warning('Unable to exclude {} from export'.format(rois))


def include_in_export(case, rois):
    """Toggle export to true
    :param case: current case
    :param rois: name of structure to exclude"""

    if type(rois) is not list:
        rois = [rois]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    for r in defined_rois:
        if r in rois:
            try:
                case.PatientModel.ToggleExcludeFromExport(
                    ExcludeFromExport=False,
                    RegionOfInterests=r,
                    PointsOfInterests=[])

            except Exception:
                logging.warning('Unable to include {} in export'.format(rois))
        else:
            try:
                case.PatientModel.ToggleExcludeFromExport(
                    ExcludeFromExport=True,
                    RegionOfInterests=r,
                    PointsOfInterests=[])

            except Exception:
                logging.warning('Unable to exclude {} from export'.format(rois))


def exists_roi(case, rois):
    """See if rois is in the list"""
    if type(rois) is not list:
        rois = [rois]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    roi_exists = []

    for r in rois:
        if r in defined_rois:
            roi_exists.append(True)
        else:
            roi_exists.append(False)

    return roi_exists


def exists_poi(case, pois):
    """See if rois is in the list"""
    if type(pois) is not list:
        pois = [pois]

    defined_pois = []
    for p in case.PatientModel.PointsOfInterest:
        defined_pois.append(p.Name)

    poi_exists = []

    for p in pois:
        i = 0
        exact_match = False
        if p in defined_pois:
            while i < len(defined_pois):
                if p == defined_pois[i]:
                    logging.debug('{} is an exact match to {}'.format(p, defined_pois[i]))
                    exact_match = True
                i += 1
            if exact_match:
                poi_exists.append(True)
            else:
                poi_exists.append(False)
        else:
            poi_exists.append(False)

    return poi_exists


def has_coordinates_poi(case, exam, poi):
    """See if pois have locations
    Currently this script will simply look to see if the coordinates are finite.

    :param case: desired RS case object from connect
    :param exam: desired RS exam object from connect
    :param poi: type(str) of an existing point of interest name

    TODO Accept an optional ROI as an input, if we have one, then
        Add a bounding box check using:
            case.PatientModel.StructureSets[exam.Name].RoiGeometries['External'].GetBoundingBox
    Usage:
        import StructureOperations
        test = StructureOperations.has_coordinates_poi(case=case, exam=exam, poi='SimFiducials')"""

    poi_position = case.PatientModel.StructureSets[exam.Name].PoiGeometries[poi]
    test_points = [abs(poi_position.Point.x) < 1e5, abs(poi_position.Point.y) < 1e5, abs(poi_position.Point.z < 1e5)]
    if all(test_points):
        return True
    else:
        return False


def check_roi(case, exam, rois):
    """ See if the provided rois has contours, later check for contiguous"""
    if type(rois) is not list:
        rois = [rois]

    roi_passes = []

    if all(exists_roi(case=case, rois=rois)):

        for r in rois:
            if case.PatientModel.StructureSets[exam.Name].RoiGeometries[r].HasContours():
                roi_passes.append(True)
            else:
                roi_passes.append(False)

        return roi_passes

    else:

        return [False]


def max_coordinates(case, exam, rois):
    """ Returns the maximum coordinates of the rois as a nested dictionary, e.g.
    rois = PTV1
    a = max_coordinates(case=case, exam=exam, rois=rois)
    a['PTV1']['min_x'] = ...

    TODO: Give max Patient L/R/A/P/S/I, and consider creating a type with defined methods"""
    if type(rois) is not list:
        rois = [rois]

    if any(exists_roi(case, rois)):
        logging.warning('Maximum Coordinates of ROI: {} could NOT be determined. ROI does not exist'.format(rois))
        return None

    logging.debug('Determining maximum coordinates of ROI: {}'.format(rois))

    ret = case.PatientModel.StructureSets[exam.Name]. \
        RoiGeometries[rois].SetRepresentation(Representation='Contours')
    logging.debug('ret of operation is {}'.format(ret))

    max_roi = {}

    for r in rois:
        x = []
        y = []
        z = []

        contours = case.PatientModel.StructureSets[exam].RoiGeometries[rois].PrimaryShape.Contours

        for contour in contours:
            for point in contour:
                x.append(point.x)
                y.append(point.y)
                z.append(point.z)

        max_roi[r] = {'min_x': min(x),
                      'max_x': max(x),
                      'max_y': min(y),
                      'min_y': max(y),
                      'min_z': min(z),
                      'max_z': max(z)}
        return max_roi


def define_sys_color(rgb):
    """ Takes an rgb list and converts to a Color object useable by RS
    :param rgb: an rgb color list, e.g. [128, 132, 256]
    :return Color object"""

    return System.Drawing.Color.FromArgb(255, rgb[0], rgb[1], rgb[2])


def find_targets(case):
    """
    Find all structures with type 'Target' within the current case. Return the matches as a list
    :param case: Current RS Case
    :return: plan_targets # A List of targets
    """

    # Find RS targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.OrganData.OrganType == 'Target':
            plan_targets.append(r.Name)
    # Add user threat: empty PTV list.
    if not plan_targets:
        connect.await_user_input("The target list is empty." +
                                 " Please apply type PTV to the targets and continue.")
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == 'Target':
                plan_targets.append(r.Name)
    if plan_targets:
        return plan_targets
    else:
        sys.exit('Script cancelled')


def check_structure_exists(case, structure_name, roi_list=None, option='Check', exam=None):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: a list of available ROI's as RS RoiGeometries to check against
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
        Wait - prompt user to create structure if not found
    :param exam: Current RS exam, if supplied the script deletes geometry only, otherwise contour is deleted
    :return: Logical - True if structure is present in ROI List, false otherwise
    """

    # If no roi_list is given, build it using all roi in the case
    if roi_list is None and exam is None:
        logging.warning('Inappropriate call to check_structure_exists. If roi_list = None, then exam must be supplied ')
        sys.exit()
    if roi_list is None:
        roi_list = []
        for r in case.PatientModel.StructureSets[exam.Name].RoiGeometries:
            roi_list.append(r)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if exam is not None:
            structure_has_contours_on_exam = \
                case.PatientModel.StructureSets[exam.Name].RoiGeometries[structure_name].HasContours()
        else:
            structure_has_contours_on_exam = False

        if option == 'Delete':
            if structure_has_contours_on_exam:
                case.PatientModel.StructureSets[exam.Name].RoiGeometries[structure_name].DeleteGeometry()
                logging.warning(structure_name + 'found - deleting geometry')
                return False
            else:
                case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
                logging.warning(structure_name + 'found - deleting and creating')
                return True
        elif option == 'Check':
            if structure_has_contours_on_exam:
                logging.info('Structure {} has contours on exam {}'.format(structure_name,exam.Name))
            else:
                logging.info(structure_name + 'found')
            return True
        elif option == 'Wait':
            if structure_has_contours_on_exam:
                logging.info('Structure {} has contours on exam {}'.format(structure_name,exam.Name))
                return True
            else:
                logging.info('Structure {} not found on exam {}, prompted user to create'.format(
                    structure_name, exam.Name))
                connect.await_user_input(
                    'Create the structure {} and continue script.'.format(structure_name))
    else:
        logging.info(structure_name + 'not found')
        return False


def convert_poi(poi1):
    """
    Return a poi as a numpy array
    :param poi1:
    :return: poi_arr
    """

    poi_arr = np.array([poi1.Point.x, poi1.Point.y, poi1.Point.z])
    return poi_arr


def levenshtein_match(item, arr, num_matches=None):
    """[match,dist]=__levenshtein_match(item,arr)"""

    # Initialize return args
    if num_matches is None:
        num_matches = 1

    dist = [max(len(item), min(map(len, arr)))] * num_matches
    match = [None] * num_matches

    # Loop through array of options
    for a in arr:
        v0 = range(len(a) + 1) + [0]
        v1 = [0] * len(v0)
        for b in range(len(item)):
            v1[0] = b + 1
            for c in range(len(a)):
                if item[b].lower() == a[c].lower():
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c])

                else:
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c] + 1)

            v0, v1 = v1, v0

        for i, d in enumerate(dist):
            if v0[len(a)] < d:
                dist.insert(i, v0[len(a)])
                dist.pop()
                match.insert(i, a)
                match.pop()
                break

    return match, dist


def find_normal_structures_match(rois, site=None, num_matches=None, protocol_file=None):
    """Return a unique structure dictionary from supplied element tree"""
    target_list = ['OTV', 'sOTV', '_EZ_', 'ring', 'PTV', 'ITV', 'GTV']
    protocol_folders = [r'../protocols']
    institution_folders = [r'']
    files = [[r'../protocols', r'', r'TG-263.xml'],
             [r'../protocols', r'UW', r'']]
    paths = []
    for i, f in enumerate(files):
        secondary_protocol_folder = f[0]
        institution_folder = f[1]
        paths.append(os.path.join(os.path.dirname(__file__),
                                  secondary_protocol_folder,
                                  institution_folder))
    # secondary_protocol_folder = r'../protocols'
    # secondary_filename = r'TG-263.xml'
    # path_to_secondary_sets = os.path.join(os.path.dirname(__file__),
    #                                      secondary_protocol_folder)
    logging.debug('Searching folder {} for rois'.format(paths[1]))
    standard_names = []
    for f in os.listdir(paths[1]):
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(paths[1], f))
            prot_rois = tree.findall('.//roi')
            for r in prot_rois:
                if not any(i in r.find('name').text for i in standard_names):
                    standard_names.append(r.find('name').text)
    match_threshold = 0.6
    if num_matches is None:
        num_matches = 1

    tree = xml.etree.ElementTree.parse(os.path.join(paths[0], files[0][2]))
    roi263 = tree.findall('./' + 'roi')
    # Check aliases first (look in TG-263 to see if an alias is there).
    aliases = {}
    matched_rois = {}
    for r in roi263:
        if r.find('Alias').text is not None:
            alias = r.find('Alias').text
            aliases[r.find('name').text] = alias.split(',')

    for r in roi263:
        standard_names.append(r.find('name').text)

    # beg_left = re.compile('L_*'.re.IGNORECASE)
    # end_left = re.compile('*_L')

    for r in rois:
        [match, dist] = levenshtein_match(r, standard_names, num_matches)
        matched_rois[r] = []
        for a_key, a_val in aliases.iteritems():
            for v in a_val:
                if r in v:
                    matched_rois[r].append(a_key)
        for i, d in enumerate(dist):
            if d < len(r) * match_threshold:
                # Return Criteria
                if match[i] not in matched_rois[r]:
                    if '_L' in match[i] and ('_R' in r or 'R_' in r):
                        logging.debug('Roi {}: Leven. Match {} not added to avoid L/R mismatch'.format(
                            r, match[i]))
                    elif '_R' in match[i] and ('_L' in r or 'L_' in r):
                        logging.debug('Roi {}: Leven. Match {} not added to avoid R/L mismatch'.format(
                            r, match[i]))
                    else:
                        matched_rois[r].append(match[i])

    return matched_rois


def check_overlap(patient, case, exam, structure, rois):
    """
    Checks the overlap of strucure with the roi list defined in rois.
    Returns the volume of overlap
    :param exam:
    :param case: RS Case
    :param structure: List of target structures for overlap
    :param rois: List of structures which will be checked for overlap with structure
    :return: vol
    """
    exist_list = exists_roi(case, rois)
    roi_index = 0
    rois_verif = []
    # Check all incoming rois to see if they exist in the list
    for r in exist_list:
        if r:
            rois_verif.append(rois[roi_index])
        roi_index += 1
    logging.debug('Found the following in evaluation of overlap with {}: '.format(
        structure, rois_verif))

    overlap_name = 'z_overlap'
    for r in structure:
        overlap_name += '_' + r

    overlap_defs = {
        "StructureName": overlap_name,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": " 192, 192, 192",
        "OperationA": "Union",
        "SourcesA": structure,
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": rois_verif,
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationResult": "Intersection",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined"}
    make_boolean_structure(patient=patient, case=case, examination=exam,
                           **overlap_defs)
    vol = None
    try:
        t = case.PatientModel.StructureSets[exam.Name]. \
            RoiGeometries[overlap_name]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.info('{} has no contours, index undefined'.format(overlap_name))
    except:
        logging.warning('Error getting volume for {}, volume => 0.0'.format(overlap_name))

    logging.debug('Calculated volume of overlap of {} is {}'.format(overlap_name, vol))
    case.PatientModel.RegionsOfInterest[overlap_name].DeleteRoi()
    return vol


def find_types(case, roi_type):
    """
    Return a list of all structures that in exist in the roi list with type roi_type
    :param patient:
    :param case:
    :param exam:
    :param type:
    :return: found_roi
    """
    found_roi = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == roi_type:
            found_roi.append(r.Name)
    return found_roi


def translate_roi(case, exam, roi, shifts):
    """
    Translate (only) an roi according to the shifts
    :param case:
    :param exam:
    :param roi:
    :param shifts: a dictionary containing shifts, e.g.
        shifts = {'x': 1.0, 'y':1.0, 'z':1.0} would shift in each direction 1 cm
    :return: centroid of shifted roi
    """
    x = shifts['x']
    y = shifts['y']
    z = shifts['z']
    transform_matrix = {'M11': 1, 'M12': 0, 'M13': 0, 'M14': x,
                        'M21': 0, 'M22': 1, 'M23': 0, 'M24': y,
                        'M31': 0, 'M32': 0, 'M33': 1, 'M34': z,
                        'M41': 0, 'M42': 0, 'M43': 0, 'M44': 1}
    case.PatientModel.RegionsOfInterest['TomoCouch'].TransformROI3D(
        Examination=exam, TransformationMatrix=transform_matrix)
    # case.PatientModel.StructureSets[exam].RoiGeometries[roi].TransformROI3D(
    #    Examination=exam,TransformationMatrix=transform_matrix)


def match_roi(case, exam, plan, beamset, plan_rois, protocol_rois):
    """
    Matches a input list of plan_rois (user-defined) to protocol, outputs data to a log
    :param case:
    :param exam:
    :param plan:
    :param beamset:
    :param plan_rois:
    :param protocol_rois:
    :return:
    """
    import UserInterface
    # test_select_element(patient=patient, case=case, plan=plan, beamset=beamset, exam=exam)

    matches = find_normal_structures_match(rois=protocol_rois)
    # Track correct matches
    correct = 0

    for r in protocol_rois:
        if r == matches[r]:
            correct += 1

    logging.debug('Correct matches using identical structures {} / {}'.format(correct, len(plan_rois)))

    matches = find_normal_structures_match(rois=plan_rois, num_matches=5)
    for k, v in matches.iteritems():
        logging.debug('Match key {k} and response {v}'.format(k=k, v=v))

    # Make dialog inputs
    inputs = {}
    datatype = {}
    options = {}
    initial = {}
    for k, v in matches.iteritems():
        inputs[k] = k
        datatype[k] = 'combo'
        options[k] = v
        for item in v:
            if item == k:
                initial[k] = item
                break

    matchy_dialog = UserInterface.InputDialog(
        inputs=inputs,
        title='Matchy Matchy',
        datatype=datatype,
        initial=initial,
        options=matches,
        required={})
    # Launch the dialog
    response = matchy_dialog.show()
    if response is not None:
        # Link root to selected protocol ElementTree
        for k, v in response.iteritems():
            logging.debug('Match key {k} and response {v}'.format(k=k, v=v))
        logging.info("Matches selected: {}".format(
            matchy_dialog))

        correct = 0

        m_logs = r'Q:\\RadOnc\RayStation\RayScripts\dev_logs'
        with open(os.path.normpath('{}/Matched_Structures.txt').format(m_logs), 'a') as match_file:
            match_file.write('PlanName: {pn} :: '.format(pn=beamset.DicomPlanLabel))
        # for r in rois:
        #    if r == matches[r]:
        #        correct += 1
        with open(os.path.normpath('{}/Matched_Structures.txt').format(m_logs), 'a') as match_file:
            for k, v in response.iteritems():
                match_file.write('{v}: {k}, '.format(k=k, v=v))
            match_file.write('\n '.format(k=k, v=v))
        logging.debug('Correct matches on test set {} / {}'.format(correct, len(plan_rois)))


def create_roi(patient, case, examination, roi_name, overwrite=True, suffix=None):
    """
    Thoughtful creation of strucutures that can determine if the structure exists,
    determine the geometry exists on this examination
    -Create it with a suffix
    :param patient:
    :param case:
    :param examination:
    :param overwrite:
    :param suffix: append the suffix string to the name of a contour
    :return: new_structure_name: the name of the new-structure created or None for an error
    """
    if overwrite:
        check_structure_exists(case=case, structure_name=roi_name, option='Delete')
    else:
        check_structure_exists(case=case, structure_name=roi_name, option='Check')


def make_boolean_structure(patient, case, examination, **kwargs):
    StructureName = kwargs.get("StructureName")
    ExcludeFromExport = kwargs.get("ExcludeFromExport")
    VisualizeStructure = kwargs.get("VisualizeStructure")
    StructColor = kwargs.get("StructColor")
    SourcesA = kwargs.get("SourcesA")
    MarginTypeA = kwargs.get("MarginTypeA")
    ExpA = kwargs.get("ExpA")
    OperationA = kwargs.get("OperationA")
    SourcesB = kwargs.get("SourcesB")
    MarginTypeB = kwargs.get("MarginTypeB")
    ExpB = kwargs.get("ExpB")
    OperationB = kwargs.get("OperationB")
    MarginTypeR = kwargs.get("MarginTypeR")
    ExpR = kwargs.get("ExpR")
    OperationResult = kwargs.get("OperationResult")
    StructType = kwargs.get("StructType")
    if 'VisualizationType' in kwargs:
        VisualizationType = kwargs.get("VisualizationType")
    else:
        VisualizationType = 'contour'

    try:
        case.PatientModel.RegionsOfInterest[StructureName]
        logging.warning("make_boolean_structure: Structure " + StructureName +
                        " exists.  This will be overwritten in this examination")
    except:
        case.PatientModel.CreateRoi(Name=StructureName,
                                    Color=StructColor,
                                    Type=StructType,
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)

    case.PatientModel.RegionsOfInterest[StructureName].SetAlgebraExpression(
        ExpressionA={'Operation': OperationA, 'SourceRoiNames': SourcesA,
                     'MarginSettings': {'Type': MarginTypeA,
                                        'Superior': ExpA[0],
                                        'Inferior': ExpA[1],
                                        'Anterior': ExpA[2],
                                        'Posterior': ExpA[3],
                                        'Right': ExpA[4],
                                        'Left': ExpA[5]
                                        }},
        ExpressionB={'Operation': OperationB, 'SourceRoiNames': SourcesB,
                     'MarginSettings': {'Type': MarginTypeB,
                                        'Superior': ExpB[0],
                                        'Inferior': ExpB[1],
                                        'Anterior': ExpB[2],
                                        'Posterior': ExpB[3],
                                        'Right': ExpB[4],
                                        'Left': ExpB[5]}},
        ResultOperation=OperationResult,
        ResultMarginSettings={'Type': MarginTypeR,
                              'Superior': ExpR[0],
                              'Inferior': ExpR[1],
                              'Anterior': ExpR[2],
                              'Posterior': ExpR[3],
                              'Right': ExpR[4],
                              'Left': ExpR[5]})
    if ExcludeFromExport:
        exclude_from_export(case=case, rois=StructureName)

    case.PatientModel.RegionsOfInterest[StructureName].UpdateDerivedGeometry(
        Examination=examination, Algorithm="Auto")
    patient.SetRoiVisibility(RoiName=StructureName,
                             IsVisible=VisualizeStructure)
    patient.Set2DvisualizationForRoi(RoiName=StructureName,
                                     Mode=VisualizationType)


def make_wall(wall, sources, delta, patient, case, examination, inner=True, struct_type="Undefined"):
    """

    :param wall: Name of wall contour
    :param sources: List of source structures
    :param delta: contraction
    :param patient: current patient
    :param case: current case
    :param inner: logical create an inner wall (true) or ring
    :param examination: current exam
    :return:
    """

    if inner:
        a = [0] * 6
        b = [delta] * 6
    else:
        a = [delta] * 6
        b = [0] * 6

    wall_defs = {
        "StructureName": wall,
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": " Blue",
        "OperationA": "Union",
        "SourcesA": sources,
        "MarginTypeA": "Expand",
        "ExpA": a,
        "OperationB": "Union",
        "SourcesB": sources,
        "MarginTypeB": "Contract",
        "ExpB": b,
        "OperationResult": "Subtraction",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": struct_type}
    make_boolean_structure(patient=patient,
                           case=case,
                           examination=examination,
                           **wall_defs)


def make_inner_air(PTVlist, external, patient, case, examination, inner_air_HU=-900):
    """

    :param PTVlist: list of target structures to search near for air pockets
    :param external: string name of external to use in the definition
    :param patient: current patient
    :param case: current case
    :param examination: current examination
    :param inner_air_HU: optional parameter to define upper threshold of air volumes
    :return: new_structs: a list of newly created structures
    """
    new_structs = []
    # Automated build of the Air contour
    try:
        retval_AIR = case.PatientModel.RegionsOfInterest["Air"]
    except:
        retval_AIR = case.PatientModel.CreateRoi(Name="Air",
                                                 Color="Green",
                                                 Type="Undefined",
                                                 TissueName=None,
                                                 RbeCellTypeName=None,
                                                 RoiMaterial=None)
        new_structs.append("Air")
    patient.SetRoiVisibility(RoiName='Air', IsVisible=False)
    exclude_from_export(case=case, rois='Air')

    retval_AIR.GrayLevelThreshold(Examination=examination,
                                  LowThreshold=-1024,
                                  HighThreshold=inner_air_HU,
                                  PetUnit="",
                                  CbctUnit=None,
                                  BoundingBox=None)

    inner_air_sources = ["Air", external]
    inner_air_defs = {
        "StructureName": "InnerAir",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": " SaddleBrown",
        "OperationA": "Intersection",
        "SourcesA": inner_air_sources,
        "MarginTypeA": "Expand",
        "ExpA": [0] * 6,
        "OperationB": "Union",
        "SourcesB": PTVlist,
        "MarginTypeB": "Expand",
        "ExpB": [1] * 6,
        "OperationResult": "Intersection",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "StructType": "Undefined"}
    make_boolean_structure(patient=patient,
                           case=case,
                           examination=examination,
                           **inner_air_defs)

    # Define the inner_air structure at the Patient Model level
    inner_air_pm = case.PatientModel.RegionsOfInterest['InnerAir']
    # Define the inner_air structure at the examination level
    inner_air_ex = case.PatientModel.StructureSets[examination.Name]. \
        RoiGeometries['InnerAir']

    # If the InnerAir structure has contours clean them
    if inner_air_ex.HasContours():
        inner_air_pm.VolumeThreshold(InputRoi=inner_air_pm,
                                     Examination=examination,
                                     MinVolume=0.1,
                                     MaxVolume=500)
        # Check for emptied contours
        if not inner_air_ex.HasContours():
            logging.debug("make_inner_air: Volume Thresholding has eliminated InnerAir contours")
    else:
        logging.debug("make_inner_air: No air contours were found near the targets")

    return new_structs


def planning_structures(generate_ptvs=True,
                        generate_ptv_evals=True,
                        generate_otvs=True,
                        generate_skin=True,
                        generate_inner_air=True,
                        generate_field_of_view=True,
                        generate_ring_hd=True,
                        generate_ring_ld=True,
                        generate_normal_2cm=True,
                        generate_combined_ptv=True,
                        skin_contraction=0.3,
                        run_status=True,
                        dialog1_response=None,
                        dialog2_response=None,
                        dialog3_response=None,
                        dialog4_response=None,
                        dialog5_response=None):
    """
    Generate Planning Structures

    This script is designed to help you make planning structures.  Prior to starting you should determine:
    All structures to be treated, and their doses
    All structures with priority 1 goals (they are going to be selected for UnderDose)
    All structures where hot-spots are undesirable but underdosing is not desired.  They will be placed in
    the UniformDose ROI.


    Raystation script to make structures used for planning.

    Note:
    Using the Standard InputDialog
    We have several calls
    The first will determine the target doses and whether we are uniform or underdosing
    Based on those responses:
    Select and Approve underdose selections
    Select and Approve uniform dose selections
    The second non-optional call prompts the user to use:
    -Target-specific rings
    -Specify desired standoffs in the rings closest to the target

    Inputs:
    None, though eventually the common uniform and underdose should be dumped into xml files
    and stored in protocols

    Usage:

    Version History:
    1.0.1: Hot fix to repair inconsistency when underdose is not used but uniform dose is.
    1.0.2: Adding "inner air" as an optional feature
    1.0.3 Hot fix to repair error in definition of sOTVu: Currently taking union of PTV and
    not_OTV - should be intersection.
    1.0.4 Bug fix for upgrade to RS 8 - replaced the toggling of the exclude from export with
    the required method.
    1.0.4b Save the user mapping for this structure set as an xml file to be loaded by create_goals
    1.0.5 Exclude InnerAir and FOV from Export, add IGRT Alignment Structure
    1.0.6 Added the Normal_1cm structure to the list


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.

    :param generate_ptvs:
    :param generate_ptv_evals:
    :param generate_otvs:
    :param generate_skin:
    :param generate_inner_air:
    :param generate_field_of_view:
    :param generate_ring_hd:
    :param generate_ring_ld:
    :param generate_normal_2cm:
    :param generate_combined_ptv:
    :param skin_contraction: Contraction in cm to be used in the definition of the skin contour
    :return:
    """
    __author__ = 'Adam Bayliss'
    __contact__ = 'rabayliss@wisc.edu'
    __version__ = '1.0.5'
    __license__ = 'GPLv3'
    __help__ = 'https://github.com/wrssc/ray_scripts/wiki/User-Interface'
    __copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
    # The following list allows different elements of the code to be toggled
    # No guarantee can be made that things will work if elements are turned off
    # all dependencies are not really resolved
    # TODO: Move this down to where the translation map gets declared
    # Xml_Out.save_structure_map()

    # InnerAir Parameters
    # Upper Bound on the air volume to be removed from target coverage considerations
    InnerAirHU = -900

    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
    except:
        logging.warning("patient, case and examination must be loaded")

    if run_status:
        status = UserInterface.ScriptStatus(
            steps=['User Input',
                   'Support elements Generation',
                   'Target Generation',
                   'Ring Generation'],
            docstring=__doc__,
            help=__help__)

    # Keep track of all rois that are created
    newly_generated_rois = []

    # If a Brain structure exists, make a Normal_1cm
    # TODO: Move this to a protocol creation
    StructureName = 'Brain'
    roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))
    if roi_check:
        generate_normal_1cm = True
    else:
        generate_normal_1cm = False

    # Redraw the clean external volume if necessary
    StructureName = 'ExternalClean'
    roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))

    if roi_check:
        retval_ExternalClean = case.PatientModel.RegionsOfInterest[StructureName]
        retval_ExternalClean.SetAsExternal()
        case.PatientModel.StructureSets[examination.Name].SimplifyContours(RoiNames=[StructureName],
                                                                           RemoveHoles3D=True,
                                                                           RemoveSmallContours=False,
                                                                           AreaThreshold=None,
                                                                           ReduceMaxNumberOfPointsInContours=False,
                                                                           MaxNumberOfPoints=None,
                                                                           CreateCopyOfRoi=False,
                                                                           ResolveOverlappingContours=False)
        retval_ExternalClean.Color = define_sys_color([234, 192, 134])
        logging.warning("Structure " + StructureName +
                        " exists.  Using predefined structure after removing holes and changing color.")

    else:
        StructureName = 'ExternalClean'
        retval_ExternalClean = case.PatientModel.CreateRoi(Name=StructureName,
                                                           Color="234, 192, 134",
                                                           Type="External",
                                                           TissueName="",
                                                           RbeCellTypeName=None,
                                                           RoiMaterial=None)
        retval_ExternalClean.CreateExternalGeometry(Examination=examination,
                                                    ThresholdLevel=None)
        InExternalClean = case.PatientModel.RegionsOfInterest[StructureName]
        retval_ExternalClean.VolumeThreshold(InputRoi=InExternalClean,
                                             Examination=examination,
                                             MinVolume=1,
                                             MaxVolume=200000)
        retval_ExternalClean.SetAsExternal()
        case.PatientModel.StructureSets[examination.Name].SimplifyContours(RoiNames=[StructureName],
                                                                           RemoveHoles3D=True,
                                                                           RemoveSmallContours=False,
                                                                           AreaThreshold=None,
                                                                           ReduceMaxNumberOfPointsInContours=False,
                                                                           MaxNumberOfPoints=None,
                                                                           CreateCopyOfRoi=False,
                                                                           ResolveOverlappingContours=False)
        newly_generated_rois.append('ExternalClean')

    if run_status:
        status.next_step(text='Please fill out the following input dialogs')
    # Commonly underdoses structures
    # Plan structures matched in this list will be selected for checkbox elements below
    # TODO: move this list to the xml file for a given protocol
    UnderStructureChoices = [
        'GreatVes',
        'A_Aorta',
        'Bag_Bowel',
        'Bowel_Small',
        'Bowel_Large',
        'BrachialPlex_L_PRV05',
        'BrachialPlex_L',
        'BrachialPlex_R',
        'BrachialPlex_R_PRV05',
        'Brainstem',
        'Bronchus',
        'Bronchus_L',
        'Bronchus_R'
        'CaudaEquina',
        'Cochlea_L',
        'Cochlea_R',
        'Duodenum',
        'Esophagus',
        'Genitalia',
        'Heart',
        'Eye_L',
        'Eye_R',
        'Hippocampus_L',
        'Hippocampus_L_PRV05',
        'Hippocampus_R',
        'Hippocampus_R_PRV05',
        'Lens_R',
        'Lens_L',
        'OpticChiasm',
        'OpticNerv_L',
        'OpticNerv_R',
        'Rectum',
        'SpinalCord',
        'SpinalCord_PRV02',
        'Trachea',
        'V_Pulmonary',
    ]

    # Common uniformly dosed areas
    # Plan structures matched in this list will be selected for checkbox elements below
    UniformStructureChoices = [
        'A_Aorta_PRV05',
        'Bag_Bowel',
        'Bladder',
        'Bowel_Small',
        'Bowel_Large',
        'Brainstem',
        'Brainstem_PRV03',
        'Bronchus_PRV05',
        'Bronchus_L_PRV05',
        'Bronchus_R_PRV05',
        'CaudaEquina_PRV05',
        'Cochlea_L_PRV05',
        'Cochlea_R_PRV05',
        'Esophagus',
        'Esophagus_PRV05',
        'Duodenum_PRV05',
        'Heart',
        'Larynx',
        'Lens_L_PRV05',
        'Lens_R_PRV05',
        'Lips',
        'Mandible',
        'Musc_Constrict',
        'OpticChiasm_PRV03',
        'OpticNerv_L_PRV03',
        'OpticNerv_R_PRV03',
        'Rectum',
        'SpinalCord',
        'SpinalCord_PRV05',
        'Stomach',
        'Trachea',
        'V_Pulmonary_PRV05',
        'Vulva',
    ]

    # Prompt the user for the number of targets, uniform dose needed, sbrt flag, underdose needed
    if dialog1_response is None:

        dialog1 = UserInterface.InputDialog(
            inputs={
                '1': 'Enter Number of Targets',
                # Not yet '2': 'Select Plan Intent',
                '3': 'Priority 1 goals present: Use Underdosing',
                '4': 'Targets overlap sensitive structures: Use UniformDoses',
                '5': 'Use InnerAir to avoid high-fluence due to cavities',
                # '6': 'SBRT'
            },
            title='Planning Structures and Goal Selection',
            datatype={  # Not yet '2': 'combo',
                '3': 'check',
                '4': 'check',
                '5': 'check',
            },  # '6': 'check'},
            initial={'1': '0',
                     '5': ['yes']},
            options={
                # Not yet,  Not yet.  '2': ['Single Target/Dose', 'Concurrent', 'Primary+Boost', 'Multiple Separate Targets'],
                '3': ['yes'],
                '4': ['yes'],
                '5': ['yes'],
                # '6': ['yes']
            },
            required=['1']  # , Not Yet'2']
        )
        dialog1_response = dialog1.show()
        if dialog1_response == {}:
            sys.exit('Planning Structures and Goal Selection was cancelled')
        # Parse number of targets
        number_of_targets = int(dialog1_response['1'])
        # User selected that Underdose is required
        if 'yes' in dialog1_response['3']:
            generate_underdose = True
        else:
            generate_underdose = False
        # User selected that Uniformdose is required
        if 'yes' in dialog1_response['4']:
            generate_uniformdose = True
        else:
            generate_uniformdose = False
        # User selected that InnerAir is required
        if 'yes' in dialog1_response['5']:
            generate_inner_air = True
        else:
            generate_inner_air = False
    else:
        # TODO rename dialog1_response something better like structure scope
        number_of_targets = dialog1_response['number_of_targets']
        generate_underdose = dialog1_response['generate_underdose']
        generate_uniformdose = dialog1_response['generate_uniformdose']
        generate_inner_air = dialog1_response['generate_inner_air']

    logging.debug('User selected {} for UnderDose'.format(generate_underdose))
    logging.debug('User selected {} for UniformDose'.format(generate_uniformdose))
    logging.debug('User selected {} for InnerAir'.format(generate_inner_air))
    # Determine if targets using the skin are in place

    # Find all the target names and generate the potential dropdown list for the cases
    # Use the above list for Uniform Structure Choices and Underdose choices, then
    # autoassign to the potential dropdowns
    TargetMatches = []
    UniformMatches = []
    UnderMatches = []
    AllOars = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'Ptv':
            TargetMatches.append(r.Name)
        if r.Name in UniformStructureChoices:
            UniformMatches.append(r.Name)
        if r.Name in UnderStructureChoices:
            UnderMatches.append(r.Name)
        if r.OrganData.OrganType == 'OrganAtRisk':
            AllOars.append(r.Name)

    translation_mapping = {}
    if dialog2_response is not None:
        input_source_list = [None] * number_of_targets
        source_doses = [None] * number_of_targets
        indx = 0
        for k, v in dialog2_response.iteritems():
            input_source_list[indx] = k
            source_doses[indx] = str(int(v))
            indx += 1

    else:
        t_i = {}
        t_o = {}
        t_d = {}
        t_r = []
        for i in range(1, number_of_targets + 1):
            j = str(i)
            k_name = j.zfill(2) + '_Aname'
            k_dose = j.zfill(2) + '_Bdose'
            t_name = 'PTV' + str(i)
            t_i[k_name] = 'Match an existing plan target to ' + t_name + ':'
            t_o[k_name] = TargetMatches
            t_d[k_name] = 'combo'
            t_r.append(k_name)
            t_i[k_dose] = 'Provide dose for plan target ' + t_name + ' in cGy:'
            t_r.append(k_dose)

        dialog2 = UserInterface.InputDialog(
            inputs=t_i,
            title='Input Target Dose Levels',
            datatype=t_d,
            initial={},
            options=t_o,
            required=t_r
        )

        dialog2_response = dialog2.show()

        if dialog2_response == {}:
            sys.exit('Planning Structures and Goal Selection was cancelled')
        # Parse the output from initial_dialog
        # We are going to take a user input input_source_list and convert them into PTV's used for planning
        # input_source_list consists of the user-specified targets to be massaged into PTV1, PTV2, .... below

        # TODO: Replace the separate input_source_list and source_doses lists with a dictionary or a tuple
        # Process inputs
        input_source_list = [None] * number_of_targets
        source_doses = [None] * number_of_targets
        for k, v in dialog2_response.iteritems():
            # Grab the first two characters in the key and convert to an index
            i_char = k[:2]
            indx = int(i_char) - 1
            if len(v) > 0:
                if 'name' in k:
                    input_source_list[indx] = v
                if 'dose' in k:
                    source_doses[indx] = v
            else:
                logging.warning('No dialog elements returned. Script unsuccessful')

    # Generate Scan Lengths
    if generate_combined_ptv:
        logging.debug("Creating All_PTVs ROI using Sources: {}"
                      .format(input_source_list))
        # Generate the UnderDose structure
        all_ptv_defs = {
            "StructureName": "All_PTVs",
            "ExcludeFromExport": False,
            "VisualizeStructure": False,
            "StructColor": " Red",
            "OperationA": "Union",
            "SourcesA": input_source_list,
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Ptv"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **all_ptv_defs)
        newly_generated_rois.append('All_PTVs')

    logcrit('Target List: [%s]' % ', '.join(map(str, input_source_list)))
    logcrit('Proceeding with target list: [%s]' % ', '.join(map(str, input_source_list)))
    logcrit('Proceeding with target doses: [%s]' % ', '.join(map(str, source_doses)))

    # Get a list of underdose objects from the user consisting of up to 3 inputs
    if dialog3_response is not None:
        underdose_structures = dialog3_response['structures']
        underdose_standoff = dialog3_response['standoff']
        logging.debug("Underdose list selected: {}"
                      .format(underdose_structures))
    else:
        # Underdose dialog call
        if generate_underdose:
            under_dose_dialog = UserInterface.InputDialog(
                title='UnderDose',
                inputs={
                    'input1_underdose': 'Select UnderDose Structures',
                    'input2_underdose': 'Select UnderDose OAR',
                    'input3_underdose': 'Select UnderDose OAR',
                    'input4_under_standoff': 'UnderDose Standoff: x cm gap between targets and UnderDose volume'},
                datatype={
                    'input1_underdose': 'check',
                    'input2_underdose': 'combo',
                    'input3_underdose': 'combo'},
                initial={'input4_under_standoff': '0.4'},
                options={
                    'input1_underdose': UnderMatches,
                    'input2_underdose': AllOars,
                    'input3_underdose': AllOars},
                required=[])
            under_dose_dialog.show()
            underdose_structures = []
            try:
                underdose_structures.extend(under_dose_dialog.values['input1_underdose'])
            except KeyError:
                pass
            try:
                underdose_structures.extend([under_dose_dialog.values['input2_underdose']])
            except KeyError:
                pass
            try:
                underdose_structures.extend([under_dose_dialog.values['input3_underdose']])
            except KeyError:
                pass
            underdose_standoff = float(under_dose_dialog.values['input4_under_standoff'])
            logging.debug("Underdose list selected: {}"
                          .format(underdose_structures))

    # UniformDose dialog call
    if dialog4_response is not None:

        uniformdose_structures = dialog4_response['structures']
        uniformdose_standoff = dialog4_response['standoff']
        logging.debug("Uniform Dose list selected: {}"
                      .format(uniformdose_structures))
    else:
        if generate_uniformdose:
            uniformdose_dialog = UserInterface.InputDialog(
                title='UniformDose Selection',
                inputs={
                    'input1_uniform': 'Select UniformDose Structures',
                    'input2_uniform': 'Select UniformDose OAR',
                    'input3_uniform': 'Select UniformDose OAR',
                    'input4_uniform_standoff': 'UniformDose Standoff: x cm gap between targets and UniformDose volume'},
                datatype={
                    'input1_uniform': 'check',
                    'input2_uniform': 'combo',
                    'input3_uniform': 'combo'},
                initial={'input4_uniform_standoff': '0.4'},
                options={
                    'input1_uniform': UniformMatches,
                    'input2_uniform': AllOars,
                    'input3_uniform': AllOars},
                required=[])
            uniformdose_dialog.show()
            uniformdose_structures = []
            try:
                uniformdose_structures.extend(uniformdose_dialog.values['input1_uniform'])
            except KeyError:
                pass
            try:
                uniformdose_structures.extend([uniformdose_dialog.values['input2_uniform']])
            except KeyError:
                pass
            try:
                uniformdose_structures.extend([uniformdose_dialog.values['input3_uniform']])
            except KeyError:
                pass
            uniformdose_standoff = float(uniformdose_dialog.values['input4_uniform_standoff'])
            logging.debug("Uniform Dose list selected: {}"
                          .format(uniformdose_structures))

    if dialog5_response is not None:
        generate_target_skin = dialog5_response['target_skin']
        generate_ring_hd = dialog5_response['ring_hd']
        generate_target_rings = dialog5_response['target_rings']
        thickness_hd_ring = dialog5_response['thick_hd_ring']
        thickness_ld_ring = dialog5_response['thick_ld_ring']
        ring_standoff = dialog5_response['ring_standoff']
        otv_standoff = dialog5_response['otv_standoff']
    else:
        # OPTIONS DIALOG
        options_dialog = UserInterface.InputDialog(
            title='Options',
            inputs={
                'input1_otv_standoff': 'OTV Standoff: x cm gap between higher dose targets',
                'input2_ring_standoff': 'Ring Standoff: x cm gap between targets and rings',
                'input3_skintarget': 'Preserve skin dose using skin-specific targets',
                'input4_targetrings': 'Make target-specific High Dose (HD) rings',
                'input5_thick_hd_ring': 'Thickness of the High Dose (HD) ring',
                'input6_thick_ld_ring': 'Thickness of the Low Dose (LD) ring', },
            datatype={
                'input3_skintarget': 'check',
                'input4_targetrings': 'check'},
            initial={'input1_otv_standoff': '0.3',
                     'input2_ring_standoff': '0.2',
                     'input5_thick_hd_ring': '2',
                     'input6_thick_ld_ring': '7'},
            options={
                'input3_skintarget': ['Preserve Skin Dose'],
                'input4_targetrings': ['Use target-specific rings']},
            required=[])

        options_response = options_dialog.show()
        if options_response == {}:
            sys.exit('Selection of planning structure options was cancelled')
        # Determine if targets using the skin are in place
        try:
            if 'Preserve Skin Dose' in options_response['input3_skintarget']:
                generate_target_skin = True
            else:
                generate_target_skin = False
        except KeyError:
            generate_target_skin = False

        # User wants target specific rings or no
        try:
            if 'Use target-specific rings' in options_response['input4_targetrings']:
                generate_target_rings = True
                generate_ring_hd = False
            else:
                generate_target_rings = False
        except KeyError:
            generate_target_rings = False

        logging.debug("User Selected Preserve Skin Dose: {}".format(generate_target_skin))

        logging.debug("User Selected target Rings: {}".format(generate_target_rings))

        # DATA PARSING FOR THE OPTIONS MENU
        # Stand - Off Values - Gaps between structures
        # cm gap between higher dose targets (used for OTV volumes)
        otv_standoff = float(options_response['input1_otv_standoff'])

        # ring_standoff: cm Expansion between targets and rings
        ring_standoff = float(options_response['input2_ring_standoff'])

        # Ring thicknesses
        thickness_hd_ring = float(options_response['input5_thick_hd_ring'])
        thickness_ld_ring = float(options_response['input6_thick_ld_ring'])

    if run_status:
        status.next_step(text='Support structures used for removing air, skin, and overlap being generated')

    if generate_ptvs:
        # Build the name list for the targets
        PTVPrefix = "PTV"
        OTVPrefix = "OTV"
        sotvu_prefix = "sOTVu"
        # Generate a list of names for the PTV's, Evals, OTV's and EZ (exclusion zones)
        PTVList = []
        PTVEvalList = []
        OTVList = []
        PTVEZList = []
        sotvu_list = []
        high_med_low_targets = False
        numbered_targets = True
        for index, target in enumerate(input_source_list):
            if high_med_low_targets:
                NumMids = len(input_source_list) - 2
                if index == 0:
                    PTVName = PTVPrefix + "_High"
                    PTVEvalName = PTVPrefix + "_Eval_High"
                    PTVEZName = PTVPrefix + "_EZ_High"
                    OTVName = OTVPrefix + "_High"
                    sotvu_name = sotvu_prefix + "_High"
                elif index == len(input_source_list) - 1:
                    PTVName = PTVPrefix + "_Low"
                    PTVEvalName = PTVPrefix + "_Eval_Low"
                    PTVEZName = PTVPrefix + "_EZ_Low"
                    OTVName = OTVPrefix + "_Low"
                    sotvu_name = sotvu_prefix + "_Low"
                else:
                    MidTargetNumber = index - 1
                    PTVName = PTVPrefix + "_Mid" + str(MidTargetNumber)
                    PTVEvalName = PTVPrefix + "_Eval_Mid" + str(MidTargetNumber)
                    PTVEZName = PTVPrefix + "_EZ_Mid" + str(MidTargetNumber)
                    OTVName = OTVPrefix + "_Mid" + str(MidTargetNumber)
                    sotvu_name = sotvu_prefix + "_Mid" + str(MidTargetNumber)
            elif numbered_targets:
                PTVName = PTVPrefix + str(index + 1) + '_' + source_doses[index]
                PTVEvalName = PTVPrefix + str(index + 1) + '_Eval_' + source_doses[index]
                PTVEZName = PTVPrefix + str(index + 1) + '_EZ_' + source_doses[index]
                OTVName = OTVPrefix + str(index + 1) + '_' + source_doses[index]
                sotvu_name = sotvu_prefix + str(index + 1) + '_' + source_doses[index]
            PTVList.append(PTVName)
            translation_mapping[PTVName] = [input_source_list[index],
                                            str(source_doses[index])]
            PTVEvalList.append(PTVEvalName)
            PTVEZList.append(PTVEZName)
            translation_mapping[OTVName] = [input_source_list[index],
                                            str(source_doses[index])]
            OTVList.append(OTVName)
            sotvu_list.append(sotvu_name)
    else:
        logging.warning("Generate PTV's off - a nonsupported operation")

    TargetColors = ["Red", "Green", "Blue", "Yellow", "Orange", "Purple"]

    for k, v in translation_mapping.iteritems():
        logging.debug('The translation map k is {} and v {}'.format(
            k, v))

    if generate_skin:
        make_wall(
            wall="Skin_PRV03",
            sources=["ExternalClean"],
            delta=skin_contraction,
            patient=patient,
            case=case,
            examination=examination,
            inner=True,
            struct_type="Organ")
        newly_generated_rois.append('Skin_PRV03')

    # Generate the UnderDose structure and the UnderDose_Exp structure
    if generate_underdose:
        logging.debug("Creating UnderDose ROI using Sources: {}"
                      .format(underdose_structures))
        # Generate the UnderDose structure
        underdose_defs = {
            "StructureName": "UnderDose",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": " Blue",
            "OperationA": "Union",
            "SourcesA": underdose_structures,
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **underdose_defs)
        newly_generated_rois.append('UnderDose')
        UnderDoseExp_defs = {
            "StructureName": "UnderDose_Exp",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": " 192, 192, 192",
            "OperationA": "Union",
            "SourcesA": underdose_structures,
            "MarginTypeA": "Expand",
            "ExpA": [underdose_standoff] * 6,
            "OperationB": "Union",
            "SourcesB": [],
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "None",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined"}
        make_boolean_structure(patient=patient, case=case, examination=examination,
                               **UnderDoseExp_defs)
        newly_generated_rois.append('UnderDose_Exp')

    # Generate the UniformDose structure
    if generate_uniformdose:
        logging.debug("Creating UniformDose ROI using Sources: {}"
                      .format(uniformdose_structures))
        if generate_underdose:
            logging.debug("UnderDose structures required, excluding overlap from UniformDose")
            uniformdose_defs = {
                "StructureName": "UniformDose",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": " Blue",
                "OperationA": "Union",
                "SourcesA": uniformdose_structures,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": underdose_structures,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined"}
        else:
            uniformdose_defs = {
                "StructureName": "UniformDose",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": " Blue",
                "OperationA": "Union",
                "SourcesA": uniformdose_structures,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": [],
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "None",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Undefined"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **uniformdose_defs)
        newly_generated_rois.append('UniformDose')

    if run_status:
        status.next_step(text='Targets being generated')
    # Make the primary targets, PTV1... these are limited by external and overlapping targets
    if generate_ptvs:
        # Limit each target to the ExternalClean surface
        ptv_sources = ['ExternalClean']
        # Initially, there are no targets to use in the subtraction
        subtract_targets = []
        for i, t in enumerate(input_source_list):
            logging.debug("Creating target {} using {}".format(PTVList[i], t))
            ptv_sources.append(t)
            if i == 0:
                ptv_definitions = {
                    "StructureName": PTVList[i],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    'VisualizationType': 'Filled',
                    "StructColor": TargetColors[i],
                    "OperationA": "Union",
                    "SourcesA": [t],
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": [],
                    "MarginTypeB": "Expand",
                    "ExpB": [0] * 6,
                    "OperationResult": "None",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv"}
            else:
                ptv_definitions = {
                    "StructureName": PTVList[i],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    'VisualizationType': 'Filled',
                    "StructColor": TargetColors[i],
                    "OperationA": "Union",
                    "SourcesA": [t],
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": subtract_targets,
                    "MarginTypeB": "Expand",
                    "ExpB": [0] * 6,
                    "OperationResult": "Subtraction",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv"}
            logging.debug("Creating main target {}: {}"
                          .format(i, PTVList[i]))
            make_boolean_structure(patient=patient, case=case, examination=examination, **ptv_definitions)
            newly_generated_rois.append(ptv_definitions.get("StructureName"))
            subtract_targets.append(PTVList[i])

    # Make the InnerAir structure
    if generate_inner_air:
        air_list = make_inner_air(PTVlist=PTVList,
                                  external='ExternalClean',
                                  patient=patient,
                                  case=case,
                                  examination=examination,
                                  inner_air_HU=InnerAirHU)
        newly_generated_rois.append(air_list)
        logging.debug("Built Air and InnerAir structures.")
    else:
        try:
            # If InnerAir is found, it's geometry should be blanked out.
            StructureName = "InnerAir"
            retval_innerair = case.PatientModel.RegionsOfInterest[StructureName]
            logging.warning("Structure " + StructureName + " exists. Geometry will be redefined")
            case.PatientModel.StructureSets[examination.Name]. \
                RoiGeometries['InnerAir'].DeleteGeometry()
            case.PatientModel.CreateRoi(Name='InnerAir',
                                        Color="SaddleBrown",
                                        Type="Undefined",
                                        TissueName=None,
                                        RbeCellTypeName=None,
                                        RoiMaterial=None)
        except:
            case.PatientModel.CreateRoi(Name='InnerAir',
                                        Color="SaddleBrown",
                                        Type="Undefined",
                                        TissueName=None,
                                        RbeCellTypeName=None,
                                        RoiMaterial=None)

    # Generate a rough field of view contour.  It should really be put in with the dependent structures
    if generate_field_of_view:
        # Automated build of the Air contour
        fov_name = 'FieldOfView'
        try:
            patient.SetRoiVisibility(RoiName=fov_name,
                                     IsVisible=False)
        except:
            case.PatientModel.CreateRoi(Name=fov_name,
                                        Color="192, 192, 192",
                                        Type="FieldOfView",
                                        TissueName=None,
                                        RbeCellTypeName=None,
                                        RoiMaterial=None)
            case.PatientModel.RegionsOfInterest[fov_name].CreateFieldOfViewROI(
                ExaminationName=examination.Name)
            case.PatientModel.StructureSets[examination.Name].SimplifyContours(
                RoiNames=[fov_name],
                MaxNumberOfPoints=20,
                ReduceMaxNumberOfPointsInContours=True
            )
            patient.SetRoiVisibility(RoiName=fov_name,
                                     IsVisible=False)
            exclude_from_export(case=case, rois=fov_name)
            newly_generated_rois.append(fov_name)

    # Make the PTVEZ objects now
    if generate_underdose:
        # Loop over the PTV_EZs
        for index, target in enumerate(PTVList):
            ptv_ez_name = 'PTV' + str(index + 1) + '_EZ'
            logging.debug("Creating exclusion zone target {}: {}"
                          .format(str(index + 1), ptv_ez_name))
            # Generate the PTV_EZ
            PTVEZ_defs = {
                "StructureName": PTVEZList[index],
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": TargetColors[index],
                "OperationA": "Union",
                "SourcesA": [target],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": ["UnderDose"],
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Intersection",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv"}
            make_boolean_structure(
                patient=patient,
                case=case,
                examination=examination,
                **PTVEZ_defs)
            newly_generated_rois.append(PTVEZ_defs.get("StructureName"))

    # We will subtract the adjoining air, skin, or Priority 1 ROI that overlaps the target
    if generate_ptv_evals:
        if generate_underdose:
            eval_subtract = ['Skin_PRV03', 'InnerAir', 'UnderDose']
            logging.debug("Removing the following from eval structures"
                          .format(eval_subtract))
            if not any(exists_roi(case=case, rois=eval_subtract)):
                logging.error('Missing structure needed for UnderDose: {} needed'.format(
                    eval_subtract))
                sys.exit('Missing structure needed for UnderDose: {} needed'.format(
                    eval_subtract))

        else:
            eval_subtract = ['Skin_PRV03', 'InnerAir']
            logging.debug("Removing the following from eval structures"
                          .format(eval_subtract))
            if not any(exists_roi(case=case, rois=eval_subtract)):
                logging.error('Missing structure needed for UnderDose: {} needed'.format(
                    eval_subtract))
                sys.exit('Missing structure needed for UnderDose: {} needed'.format(
                    eval_subtract))

        for index, target in enumerate(PTVList):
            logging.debug("Creating evaluation target {}: {}"
                          .format(str(index + 1), PTVEvalList[index]))
            # Set the Sources Structure for Evals
            PTVEval_defs = {
                "StructureName": PTVEvalList[index],
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": TargetColors[index],
                "OperationA": "Intersection",
                "SourcesA": [target, "ExternalClean"],
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "SourcesB": eval_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv"}
            make_boolean_structure(patient=patient,
                                   case=case,
                                   examination=examination,
                                   **PTVEval_defs)
            newly_generated_rois.append(PTVEval_defs.get("StructureName"))
            # Append the current target to the list of targets to subtract in the next iteration
            eval_subtract.append(target)

    # Generate the OTV's
    # Build a region called z_derived_not_exp_underdose that does not include the underdose expansion
    if generate_otvs:
        otv_intersect = []
        if generate_underdose:
            otv_subtract = ['Skin_PRV03', 'InnerAir', 'UnderDose_Exp']
        else:
            otv_subtract = ['Skin_PRV03', 'InnerAir']
        logging.debug("otvs will not include {}"
                      .format(otv_subtract))

        not_otv_definitions = {
            "StructureName": "z_derived_not_otv",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": "192, 192, 192",
            "OperationA": "Union",
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationB": "Union",
            "SourcesB": otv_subtract,
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationResult": "Subtraction",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "StructType": "Undefined"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **not_otv_definitions)
        newly_generated_rois.append(not_otv_definitions.get("StructureName"))
        otv_intersect.append(not_otv_definitions.get("StructureName"))

        # otv_subtract will store the expanded higher dose targets
        otv_subtract = []
        for index, target in enumerate(PTVList):
            OTV_defs = {
                "StructureName": OTVList[index],
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": TargetColors[index],
                "OperationA": "Intersection",
                "SourcesA": [target] + otv_intersect,
                "MarginTypeA": "Expand",
                "ExpA": [0] * 6,
                "OperationB": "Union",
                "MarginTypeB": "Expand",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Ptv"}
            if index == 0:
                OTV_defs['SourcesB'] = []
                OTV_defs['OperationResult'] = "None"
                OTV_defs['ExpB'] = [0] * 6
            else:
                OTV_defs['SourcesB'] = otv_subtract
                OTV_defs['OperationResult'] = "Subtraction"
                OTV_defs['ExpB'] = [otv_standoff] * 6

            make_boolean_structure(patient=patient,
                                   case=case,
                                   examination=examination,
                                   **OTV_defs)
            otv_subtract.append(PTVList[index])
            newly_generated_rois.append(OTV_defs.get("StructureName"))

            # make the sOTVu structures now
        if generate_uniformdose:
            # Loop over the sOTVu's
            for index, target in enumerate(PTVList):
                logging.debug("Creating uniform zone target {}: {}"
                              .format(str(index + 1), sotvu_name))
                # Generate the sOTVu
                sotvu_defs = {
                    "StructureName": sotvu_list[index],
                    "ExcludeFromExport": True,
                    "VisualizeStructure": False,
                    "StructColor": TargetColors[index],
                    "OperationA": "Intersection",
                    "SourcesA": [target] + otv_intersect,
                    "MarginTypeA": "Expand",
                    "ExpA": [0] * 6,
                    "OperationB": "Union",
                    "SourcesB": ["UniformDose"],
                    "MarginTypeB": "Expand",
                    "ExpB": [uniformdose_standoff] * 6,
                    "OperationResult": "Intersection",
                    "MarginTypeR": "Expand",
                    "ExpR": [0] * 6,
                    "StructType": "Ptv"}
                make_boolean_structure(
                    patient=patient,
                    case=case,
                    examination=examination,
                    **sotvu_defs)
                newly_generated_rois.append(sotvu_defs.get("StructureName"))

    # Target creation complete moving on to rings
    if run_status:
        status.next_step(text='Rings being generated')

    # RINGS

    # First make an ExternalClean-limited expansion volume
    # This will be the outer boundary for any expansion: a

    z_derived_exp_ext_defs = {
        "StructureName": "z_derived_exp_ext",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": " 192, 192, 192",
        "SourcesA": [fov_name],
        "MarginTypeA": "Expand",
        "ExpA": [8] * 6,
        "OperationA": "Union",
        "SourcesB": ["ExternalClean"],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationB": "Union",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "OperationResult": "Subtraction",
        "StructType": "Undefined"}
    make_boolean_structure(patient=patient,
                           case=case,
                           examination=examination,
                           **z_derived_exp_ext_defs)
    newly_generated_rois.append(z_derived_exp_ext_defs.get("StructureName"))

    # This structure will be all targets plus the standoff: b
    z_derived_targets_plus_standoff_ring_defs = {
        "StructureName": "z_derived_targets_plus_standoff_ring_defs",
        "ExcludeFromExport": True,
        "VisualizeStructure": False,
        "StructColor": " 192, 192, 192",
        "SourcesA": PTVList,
        "MarginTypeA": "Expand",
        "ExpA": [ring_standoff] * 6,
        "OperationA": "Union",
        "SourcesB": [],
        "MarginTypeB": "Expand",
        "ExpB": [0] * 6,
        "OperationB": "Union",
        "MarginTypeR": "Expand",
        "ExpR": [0] * 6,
        "OperationResult": "None",
        "StructType": "Undefined"}
    make_boolean_structure(patient=patient,
                           case=case,
                           examination=examination,
                           **z_derived_targets_plus_standoff_ring_defs)
    newly_generated_rois.append(
        z_derived_targets_plus_standoff_ring_defs.get("StructureName"))
    # Now generate a ring for each target
    # Each iteration will add the higher dose targets and rings to the subtract list for subsequent rings
    # ring(i) = [PTV(i) + thickness] - [a + b + PTV(i-1)]
    # where ring_avoid_subtract = [a + b + PTV(i-1)]
    ring_avoid_subtract = [z_derived_exp_ext_defs.get("StructureName"),
                           z_derived_targets_plus_standoff_ring_defs.get("StructureName")]

    if generate_target_rings:
        logging.debug('Target specific rings being constructed')
        for index, target in enumerate(PTVList):
            ring_name = "ring" + str(index + 1) + "_" + source_doses[index]
            target_ring_defs = {
                "StructureName": ring_name,
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": TargetColors[index],
                "OperationA": "Union",
                "SourcesA": [target],
                "MarginTypeA": "Expand",
                "ExpA": [thickness_hd_ring +
                         ring_standoff] * 6,
                "OperationB": "Union",
                "SourcesB": ring_avoid_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationResult": "Subtraction",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "StructType": "Avoidance"}
            make_boolean_structure(patient=patient,
                                   case=case,
                                   examination=examination,
                                   **target_ring_defs)
            newly_generated_rois.append(target_ring_defs.get("StructureName"))
            # Append the current target to the list of targets to subtract in the next iteration
            ring_avoid_subtract.append(target_ring_defs.get("StructureName"))

    else:
        # Ring_HD
        if generate_ring_hd:
            ring_hd_defs = {
                "StructureName": "Ring_HD",
                "ExcludeFromExport": True,
                "VisualizeStructure": False,
                "StructColor": " 255, 0, 255",
                "SourcesA": PTVList,
                "MarginTypeA": "Expand",
                "ExpA": [ring_standoff +
                         thickness_hd_ring] * 6,
                "OperationA": "Union",
                "SourcesB": ring_avoid_subtract,
                "MarginTypeB": "Expand",
                "ExpB": [0] * 6,
                "OperationB": "Union",
                "MarginTypeR": "Expand",
                "ExpR": [0] * 6,
                "OperationResult": "Subtraction",
                "StructType": "Avoidance"}
            make_boolean_structure(patient=patient,
                                   case=case,
                                   examination=examination,
                                   **ring_hd_defs)
            newly_generated_rois.append(ring_hd_defs.get("StructureName"))
            # Append RingHD to the structure list for removal from Ring_LD
            ring_avoid_subtract.append(ring_hd_defs.get("StructureName"))
    # Ring_LD
    if generate_ring_ld:
        ring_ld_defs = {
            "StructureName": "Ring_LD",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": " 255, 0, 255",
            "SourcesA": PTVList,
            "MarginTypeA": "Expand",
            "ExpA": [ring_standoff +
                     thickness_hd_ring +
                     thickness_ld_ring] * 6,
            "OperationA": "Union",
            "SourcesB": ring_avoid_subtract,
            "MarginTypeB": "Expand",
            "ExpB": [0] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **ring_ld_defs)
        newly_generated_rois.append(ring_ld_defs.get("StructureName"))

    # Normal_2cm
    if generate_normal_2cm:
        Normal_2cm_defs = {
            "StructureName": "Normal_2cm",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": " 255, 0, 255",
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationA": "Union",
            "SourcesB": PTVList,
            "MarginTypeB": "Expand",
            "ExpB": [2] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **Normal_2cm_defs)
        newly_generated_rois.append(Normal_2cm_defs.get("StructureName"))

    if generate_normal_1cm:
        Normal_1cm_defs = {
            "StructureName": "Normal_1cm",
            "ExcludeFromExport": True,
            "VisualizeStructure": False,
            "StructColor": " 255, 0, 255",
            "SourcesA": ["ExternalClean"],
            "MarginTypeA": "Expand",
            "ExpA": [0] * 6,
            "OperationA": "Union",
            "SourcesB": PTVList,
            "MarginTypeB": "Expand",
            "ExpB": [1] * 6,
            "OperationB": "Union",
            "MarginTypeR": "Expand",
            "ExpR": [0] * 6,
            "OperationResult": "Subtraction",
            "StructType": "Avoidance"}
        make_boolean_structure(patient=patient,
                               case=case,
                               examination=examination,
                               **Normal_1cm_defs)
        newly_generated_rois.append(Normal_1cm_defs.get("StructureName"))

    if run_status:
        status.finish(text='The script executed successfully')
