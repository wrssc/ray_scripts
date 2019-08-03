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

    rois = []
    for r in case.PatientModel.RegionsOfInterest:
        rois.append(r.Name)
    if roi in rois:
        return True
    else:
        return False

def check_roi(case, exam, roi):
    """ See if the provided roi has contours, later check for contiguous"""
    if exists_roi(case=case, roi=roi):
        if case.PatientModel.StructureSets[exam].RoiGeometries[roi].HasContours()
            return True
        else
            return False

def max_coordinates(case, exam, roi_name):
    """ Returns the maximum coordinates of the roi in roi_name
    TODO: Give max Patient L/R/A/P/S/I"""

    if exists_roi(case, roi_name):
        logging.debug('Determining maximum coordinates of ROI: {}'.format(roi_name))
    else:
        logging.warning('Maximum Coordinates of ROI: {} could NOT be determined. ROI does not exist'.format(roi_name))
        return None

    ret = case.PatientModel.StructureSets[exam.Name].\
        RoiGeometries[roi_name].SetRepresentation(Representation=’Contours’)
    logging.debug('ret of operation is {}'.format(ret))

    contours = case.PatientModel.StructureSets[exam].RoiGeometries[roi_name].PrimaryShape.Contours

    x = []
    y = []
    z = []

    for contour in contours:
        for point in contour:
            x.append(point.x)
            y.append(point.y)
            z.append(point.z)

    max_roi = {}
    max_roi['min_x'] = min(x)
    max_roi['max_x'] = max(x)
    max_roi['max_y'] = min(y)
    max_roi['min_y'] = max(y)
    max_roi['min_z'] = min(z)
    max_roi['max_z'] = max(z)