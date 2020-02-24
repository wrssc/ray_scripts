""" Plan Quality Tests

    A module listing a number of tests that can be used to ensure plan quality

    simfiducial_test: looks for a simfiducial that:
                        exists
                        has finite coordinates
                        and correct type

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.

    1.0.0 Updated with multiple tests including cps, gridsize and external overlap
    1.0.1 Bug fix to handle cases with no External or support structures designated
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2018-09-05'

__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2019-Nov-09'
__raystation__ = '8.b Service Pack 2'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging
import StructureOperations


def simfiducial_test(case, exam, poi=None):
    """Does the sim fiducial point exist, and does it have coordinates?"""
    error = ''

    if poi is None:
        poi = 'SimFiducials'

    sim_fid_exists = any(StructureOperations.exists_poi(case=case, pois=poi))
    if not sim_fid_exists:
        error = 'Localization point {} does not exist!'.format(poi)
        return error

    sim_fid_has_coords = StructureOperations.has_coordinates_poi(case=case, exam=exam, poi=poi)
    if not sim_fid_has_coords:
        error = 'Localization point {} has no coordinates!'.format(poi)
        return error

    poi_type = case.PatientModel.StructureSets[exam.Name].PoiGeometries[poi].OfPoi.Type
    if poi_type != 'LocalizationPoint':
        error = 'Point of Interest {} does not have the type Localization Point'.format(poi)
        return error

    return error


def cps_test(beamset, nominal_cps=2):
    """ Check the control point settings of the vmat optimization"""
    error = ''
    if beamset.DeliveryTechnique == 'DynamicArc':
        for b in beamset.Beams:
            cps_error = False
            logging.debug('Beam name is {}'.format(b.Name))
            s_o = 0
            for s in b.Segments:
                s_i = s.DeltaGantryAngle
                cps_spacing = s_i - s_o
                s_o = s_i
                if cps_spacing > nominal_cps:
                    cps_error = True
            if cps_error:
                error += 'Beam {} has a control point with spacing exceeding {}\n'.format(b.Name, nominal_cps)

    return error


def gridsize_test(beamset, plan_string, nominal_grid_size=0.1):
    """
    Determines if the grid size for the beamset, given the plan type, is correctly set. Returns an error message
    otherwise.
    :param beamset: RS Beamset
    :param plan_string: string (or list) used to indicate a correct grid
    :param nominal_grid_size: nominal grid size
    :return: error: a message
    """

    error = ''
    grid_size = [0, 0, 0]
    for doses in beamset.FractionDose.BeamDoses:
        current_grid = doses.InDoseGrid.VoxelSize
        grid_size = [max(grid_size[0], current_grid.x),
                     max(grid_size[1], current_grid.y),
                     max(grid_size[2], current_grid.z)]
    logging.debug('Dose grid is currently: {} cm'.format(grid_size))

    # Convert input to list
    if type(plan_string) is not list:
        plan_string = [plan_string]

    # If the grid_size is less than nominal and the beamset name contains the plan type, return an error
    if max(grid_size) > nominal_grid_size:
        for p in plan_string:
            if p in beamset.DicomPlanLabel:
                error += 'The dose grid is too large for a plan of type {}, it should be {}'.format(
                    p, nominal_grid_size)

    return error


def external_overlap_test(patient, case, exam):
    """
    Evaluates the overlap with the External type structure and any support structures
    :param patient: RS patient
    :param case: RS case
    :param exam: Rs exam
    :return: error: string message of any overlap, empty string for No error
    """
    error = ''
    structure = StructureOperations.find_types(case, 'External')
    if not structure:
        logging.exception('There is not structure with type External. Designate an external and re-run script')
        error = 'No structures with External DICOM type'

    supports = StructureOperations.find_types(case, 'Support')
    if supports:
        overlap_volume = StructureOperations.check_overlap(patient=patient,
                                                       case=case,
                                                       exam=exam,
                                                       structure=structure,
                                                       rois=supports)
        if overlap_volume > 1:
            error += 'Significant overlap exists between {} and {}'.format(structure, supports)
    else:
        logging.debug('No support structures exist for evaluation of overlap')
        error = 'No support structures'

    return error


class Tomo_Couch_Valid:
    # Class used for tomotherapy couch position validation
    # valid: True if correctly placed (i.e. within 2 cm of isocenter lateral)
    # centroid: centroid of coordinates
    # shifts: None if valid, x, y, z otherwise
    def __init__(self, valid, error, cent_x, iso_x):
        self.valid = valid
        self.error = error
        self.cent_x = cent_x
        self.iso_x = iso_x

    def calculated_lateral_shift(self):
        return self.iso_x - self.cent_x


def tomo_couch_check(case, exam, beamset, tomo_couch_name='TomoCouch', limit=2.0, shift=False):
    """
    Test of the couch centering relative to isocenter
    :param case: RS Case
    :param exam: RS Exam
    :param beamset: RS beamset
    :return: error:
            None if lateral movement less than couch lateral range is implied by isocenter position.
            error otherwise
    """

    couch_exists = StructureOperations.check_roi(case=case, exam=exam, rois=tomo_couch_name)
    error = ''
    if not couch_exists:
        error = 'Exam: {}. Tomotherapy couch structures {} does not exist.'.format(exam.Name, tomo_couch_name)
        return error

    # Get the center coordinate of the isocenter
    for b in beamset.Beams:
        iso_center = b.Isocenter.Position

    # Get the center coordinate of the couch
    couch_center = case.PatientModel.StructureSets[exam.Name].RoiGeometries['TomoCouch'].GetCenterOfRoi()
    shift = iso_center.x - couch_center.x
    if abs(iso_center.x) > limit:
        error = 'Isocenter lateral shift is {0:.2f} cm. '.format(iso_center.x) + \
                'Patient indexing will need to be eliminated for shifts > {}. '.format(limit) + \
                'Put an alert in R&V that the patient will be moved outside what is acheivable mechanically. \n'
    if abs(shift) > limit:
        couch_valid = False
        error += 'The center of the couch differs from the isocenter by {0:.2f} cm. Couch will be moved'.format(shift)
    else:
        couch_valid = True

    if shift:
        return Tomo_Couch_Valid(couch_valid, error, couch_center.x, iso_center.x)
    else:
        return error


