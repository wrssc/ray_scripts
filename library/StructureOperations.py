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
    """Return a unique structure list from supplied element tree"""
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
    protocol_names = []
    for f in os.listdir(paths[1]):
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(paths[1], f))
            prot_rois = tree.findall('.//roi')
            for r in prot_rois:
                if not any(i in r.find('name').text for i in protocol_names):
                    protocol_names.append(r.find('name').text)
    match_threshold = 0.6
    if num_matches is None:
        num_matches = 1

    standard_names = []
    tree = xml.etree.ElementTree.parse(os.path.join(paths[0],files[0][2]))
    roi263 = tree.findall('./' + 'roi')
    logging.debug('found {} in {}'.format(len(roi263), files[0][2]))
    for r in roi263:
        standard_names.append(r.find('name').text)

    logging.debug('Found {} TG-263 rois'.format(len(standard_names)))

    matched_rois = {}
    for r in rois:
        [match, dist] = levenshtein_match(r, protocol_names, num_matches)
        logging.debug('Protocol matches: {} and returned {} with dist {}'.format(r, match, dist))
        matched_rois[r] = []
        for i, d in enumerate(dist):
            if d < len(r) * match_threshold:
                matched_rois[r].append(match[i])
                logging.debug('matched {} with {}'.format(r, match[i]))
            else:
                logging.debug('Lev threshold not met for roi {} using m {} with d {}'.format(
                    r, match[i], d))

    for r in rois:
        [match, dist] = levenshtein_match(r, standard_names, num_matches)
        logging.debug('Standard names: {} and returned {} with dist {}'.format(r, match, dist))
        # matched_rois[r] = []
        for i, d in enumerate(dist):
            if d < len(r) * match_threshold:
                matched_rois[r].append(match[i])
                logging.debug('matched {} with {}'.format(r, match[i]))
            else:
                logging.debug('Lev threshold not met for roi {} using m {} with d {}'.format(
                    r, match[i], d))

    return matched_rois
