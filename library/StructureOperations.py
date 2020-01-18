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
    test_points = [abs(poi_position.Point.x) < 1e5 , abs(poi_position.Point.y) < 1e5, abs(poi_position.Point.z < 1e5)]
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


def check_structure_exists(case, structure_name, roi_list=None, option='Check'):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: complete list of all available ROI's.
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
    :return: Logical - True if structure is present in ROI List, false otherwise
    """

    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for r in case.PatientModel.RegionsOfInterest:
            roi_list.append(r.Name)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if option == 'Delete':
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            logging.warning(structure_name + 'found - deleting and creating')
        elif option == 'Check':
            logging.info(structure_name + 'found')
        return True
    elif option == 'Wait':
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

    tree = xml.etree.ElementTree.parse(os.path.join(paths[0],files[0][2]))
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
    transform_matrix = {'M11':1, 'M12':0, 'M13':0, 'M14':x,
                        'M21':0, 'M22':1, 'M23':0, 'M24':y,
                        'M31':0, 'M32':0, 'M33':1, 'M34':z,
                        'M41':0, 'M42':0, 'M43':0, 'M44':1}
    case.PatientModel.RegionsOfInterest['TomoCouch'].TransformROI3D(
        Examination=exam,TransformationMatrix=transform_matrix)
    # case.PatientModel.StructureSets[exam].RoiGeometries[roi].TransformROI3D(
    #    Examination=exam,TransformationMatrix=transform_matrix)


def match_roi(case, exam, plan, beamset, plan_rois, protocol_rois):
    import UserInterface
    # test_select_element(patient=patient, case=case, plan=plan, beamset=beamset, exam=exam)

    matches = find_normal_structures_match(rois=protocol_rois)
    correct = 0

    for r in protocol_rois:
        if r == matches[r]:
            correct += 1

    logging.debug('Correct matches using identical structures {} / {}'.format(correct, len(plan_rois)))

    rois = ['Cord', 'L_Kidney', 'KidneyL', 'Lkidney']
    matches = find_normal_structures_match(rois=rois, num_matches=5)
    logging.debug('Del: matches are {} {}'.format(matches.keys(), matches.values()))
    # Make dialog inputs
    inputs = {}
    datatype = {}
    options = {}
    for k, v in matches.iteritems():
        inputs[k] = k
        datatype[k] = 'combo'
        options[k] = v

    matchy_dialog = UserInterface.InputDialog(
        inputs=inputs,
        title='Matchy Matchy Dialog',
        datatype=datatype,
        initial={},
        options=matches,
        required=matches.keys())
    # Launch the dialog
    response = matchy_dialog.show()
    # Link root to selected protocol ElementTree
    logging.info("Matches selected: {}".format(
        matchy_dialog))

    correct = 0

    m_logs = r'Q:\\RadOnc\RayStation\RayScripts\dev_logs'
    with open(os.path.normpath('{}/Matched_Structures.txt').format(m_logs), 'a') as match_file:
        match_file.write('Patient entry\n')
    for r in rois:
        if r == matches[r]:
            correct += 1
            with open(os.path.normpath('{}/Matched_Structures.txt').format(m_logs), 'a') as match_file:
                match_file.write('{}\t{}\n'.format(r, matches[r]))
    logging.debug('Correct matches on test set {} / {}'.format(correct, len(rois)))
