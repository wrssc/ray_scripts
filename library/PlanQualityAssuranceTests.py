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
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2018-09-05'

__version__ = '1.0.4'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2019-Nov-09'
__raystation__ = '8.b Service Pack 2'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


import connect
import logging
import BeamOperations
import StructureOperations
import PlanOperations

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
