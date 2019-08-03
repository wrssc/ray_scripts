""" Perform structure operations on Raystation plans

    check_roi
    checks if an ROI has contours

    exists_roi
    checks if ROI is present in the contour list

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


def exists_roi(case, roi):
    """See if roi is in the list"""
    if type(roi) is not list:
        roi = [roi]

    defined_rois = []
    for r in case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)

    roi_exists = []

    for r in roi:
        if r in defined_rois:
            roi_exists.append(True)
        else:
            roi_exists.append(False)

    return roi_exists


def check_roi(case, exam, roi):
    """ See if the provided roi has contours, later check for contiguous"""
    if type(roi) is not list:
        roi = [roi]

    roi_passes = []
    if not any(exists_roi(case=case, roi=roi)):
        for r in roi:
            if case.PatientModel.StructureSets[exam].RoiGeometries[r].HasContours():
                return roi_passes.append(True)
            else:
                return roi_passes.append(False)


def max_coordinates(case, exam, roi):
    """ Returns the maximum coordinates of the roi as a nested dictionary, e.g.
    roi = PTV1
    a = max_coordinates(case=case, exam=exam, roi=roi)
    a['PTV1']['min_x'] = ...

    TODO: Give max Patient L/R/A/P/S/I, and consider creating a type with defined methods"""
    if type(roi) is not list:
        roi = [roi]

    if any(exists_roi(case, roi)):
        logging.warning('Maximum Coordinates of ROI: {} could NOT be determined. ROI does not exist'.format(roi_name))
        return None

    logging.debug('Determining maximum coordinates of ROI: {}'.format(roi_name))

    ret = case.PatientModel.StructureSets[exam.Name]. \
        RoiGeometries[roi].SetRepresentation(Representation='Contours')
    logging.debug('ret of operation is {}'.format(ret))

    max_roi = {}

    for r in roi:
        x = []
        y = []
        z = []

        contours = case.PatientModel.StructureSets[exam].RoiGeometries[roi].PrimaryShape.Contours

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
