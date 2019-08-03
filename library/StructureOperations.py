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

    logging.debug('roi_exists {} for rois {}'.format(roi_exists, rois))

    return roi_exists


def check_roi(case, exam, rois):
    """ See if the provided rois has contours, later check for contiguous"""
    if type(rois) is not list:
        rois = [rois]

    roi_passes = []

    if all(exists_roi(case=case, rois=rois)):
        for r in rois:
            if case.PatientModel.StructureSets[exam].RoiGeometries[r].HasContours():
                roi_passes.append(True)
            else:
                roi_passes.append(False)

        logging.debug('roi_exists {} for rois {}'.format(roi_passes, rois))
        return roi_passes

    else:
        roi_passes = [False]
        logging.warning('ROIs {} may be missing'.format(rois))


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

