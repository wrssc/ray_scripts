""" Fiducials

    0.0.0 Guides user through fiducial placement for prostate SBRT

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
__date__ = '2019-09-05'

__version__ = '0.0.0'
__status__ = 'Validation'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2020-APR-15'
__raystation__ = '8.0 SP B'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2020, University of Wisconsin Board of Regents'

import logging
import sys
import connect
import UserInterface
import BeamOperations
import PlanOperations
import PlanQualityAssuranceTests
from GeneralOperations import find_scope as find_scope
from GeneralOperations import logcrit as logcrit
import StructureOperations
import clr
clr.AddReference("System.Xml")
import System

def main():
    # Get current patient, case, exam, and plan
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    # Launch a dialog for the number of fiducials
    dialog1 = UserInterface.InputDialog(
        inputs={
            '1': "Enter Number of Fiducials",
            # '2': 'Enter the beginning target number, e.g. start numbering at 2 for PTV2, PTV3, PTV4 ...',
            # '3': "Priority 1 goals present: Use Underdosing",
            # '4': "Targets overlap sensitive structures: Use UniformDoses",
            # '5': "Use InnerAir to avoid high-fluence due to cavities",
           # '6': "Select plan type"
        },
        title="Fiducial Generation",
        datatype={
            # '2': "text",
            # '3': "check",
            # '4': "check",
            # '5': "check",
           # '6': "combo"},
        },
        initial={
            '1': "0",
            # '2': "0",
            # '5': ["yes"],
           # '6': ["Concurrent"]
        },
        options={
            # '3': ["yes"],
            # '4': ["yes"],
            # '5': ["yes"],
           # '6': ["Concurrent",
           #       "Sequential Primary+Boost(s)",
           #       "Multiple Separate Targets"],
        },
        required=['1'] # '2', '6']
    )
    dialog1_response = dialog1.show()
    if dialog1_response == {}:
        sys.exit("Fiducial script cancelled")
    num_fiducials = int(dialog1_response['1'])
    logging.debug('User selected {} fiducials'.format(num_fiducials))
    # Find center of patient
    external_roi = StructureOperations.find_types(case=case,roi_type='External')
    if len(external_roi) != 1:
        sys.exit('One and only one external-type object must be defined. {}'
                 .format(len(external_roi)))
    external_center = case.PatientModel.StructureSets[examination.Name] \
                    .RoiGeometries[external_roi].GetCenterOfRoi()
    initial_position = {'x': external_center.x, 
                        'y': external_center.y,
                        'z': external_center.z}
    # Change the window level
    for n in range(num_fiducials):
        point_name = 'Fiducial1_POI' + str(n)
        case.PatientModel.CreatePoi(Examination=exam,
                                    Point=initial_position,
                                    Volume=0,
                                    Name=point_name,
                                    Color='Green',
                                    VisualizationDiameter=1,
                                    Type='Control')
        connect.await_user_input('Zoom in on fiducial {}'.format(n) 
                                 +'place point {} at its geometric center and continue.'.format(point_name)
        )
        fiducial_name = 'Fiducial' + str(n)
        fiducial_geom = StructureOperations.create_roi(case=case,
                                                       examination=exam,
                                                       roi_name=fiducial_name) 

    # Prompt the user to center the cross-hairs on the fiducial

if __name__ == '__main__':
    main()