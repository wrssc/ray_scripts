"""Add Shoulder Blocking VMAT Beams

This script uses two user defined points placed at the superior acromial-clavicular joint to
create a region of interest that will define the shoulder. Then deformation images are created
to mimic shrugging of the shoulder. In concert with a robust optimization this is used to replace
the shoulder-block in HN planning.

Version Notes: 1.0.0 Original
1.0.1 Hot Fix to apparent error in version 7 (related to connect being used instead of a
full import)

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
__date__ = '01-Nov-2023'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2023, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Shoulder-Block'
__credits__ = []

import sys
from collections import namedtuple
import logging
import connect
import UserInterface
import numpy as np
import StructureOperations
import GeneralOperations


def convert_poi(poi1):
    """
    Return a poi as a numpy array
    :param poi1:
    :return: poi_arr
    """
    poi_arr = np.array([poi1.Point.x, poi1.Point.y, poi1.Point.z])
    return poi_arr


def make_shoulder_poi(rso, params):
    if any(StructureOperations.exists_poi(case=rso.case,
                                          pois=params['Name'])):
        connect.await_user_input(f'Point {params["Name"]} already exists. Continue?')
    else:
        rso.case.PatientModel.CreatePoi(Examination=rso.exam,
                                        Point={},
                                        Volume=0,
                                        Name=params['Name'],
                                        Color='Green',
                                        VisualizationDiameter=2,
                                        Type='Control')
    connect.await_user_input(
        f'Ensure the point {params["Name"]} is at the {params["Laterality"]} acromial-clavicular joint'
        f' and continue script.')


def correct_poi_laterality(left_poi, right_poi):
    # Test if right is more negative than left
    left = StructureOperations.convert_poi(left_poi)
    right = StructureOperations.convert_poi(right_poi)
    if left[0] < right[0]:
        return False
    else:
        return True


def create_shoulder_deformation(rso, use_poi_from_user=True, quiet=False):
    # Script will run through the following steps.  We have a logical inconsistency here with making a plan
    # this is likely an optional step
    if not quiet:
        status = UserInterface.ScriptStatus(
            steps=[
                'Left shoulder POI placement',
                'Right shoulder POI placement',
                'Generate Deformation Datasets'],
            docstring=__doc__,
            help=__help__)
        status.next_step('Placing left shoulder blocking point')

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient Modeling'].Button_Patient_Modeling.Click()
    except:
        logging.debug("Could not click on the plan Design MenuItem")

    left_params = {'POIName': 'AcromialClavicularJoint_L',
                   'Laterality': 'Left',
                   'Color': 'Green'}
    right_params = {'POIName': 'AcromialClavicularJoint_R',
                    'Laterality': 'Right',
                    'Color': 'Blue'}

    left = make_shoulder_poi(rso, left_params)
    right = make_shoulder_poi(rso, right_params)

    if not correct_poi_laterality(left_poi=left, right_poi=right):
        UserInterface.WarningBox(
            'Script aborted, left and right shoulder points appear to be flipped')
        if not quiet:
            status.finish('Script aborted, left and right shoulder points appear to be flipped')
        sys.exit('Script aborted, left and right shoulder points appear to be flipped')

    logging.debug('Points exist? {}'.format(StructureOperations.exists_poi(case=case, pois=[
        shoulder_poi_right, shoulder_poi_left
    ])))

    if any(StructureOperations.exists_poi(case=case, pois=shoulder_poi_left)):
        connect.await_user_input(
            'Ensure the point {} is at the left acromial-clavicular joint'.format(
                shoulder_poi_left) +
            ' and continue script.')
    else:
        case.PatientModel.CreatePoi(Examination=exam,
                                    Point=par_beam_set.iso['Position'],
                                    Volume=0,
                                    Name=shoulder_poi_left,
                                    Color='Green',
                                    VisualizationDiameter=2,
                                    Type='Control')
        connect.await_user_input(
            'Place the point {} at the left acromial-clavicular joint'.format(shoulder_poi_left) +
            ' and continue script.')

    shoulder_left_position = case.PatientModel.StructureSets[exam.Name].PoiGeometries[
        shoulder_poi_left]
    # TODO: Check the positions to make sure they are the same still.
    logging.debug('The value of the x={}, y={}, z={}'.format(
        shoulder_left_position.Point.x,
        shoulder_left_position.Point.y,
        shoulder_left_position.Point.z))

    status.next_step('Placing right shoulder blocking point')
    if any(StructureOperations.exists_poi(case=case, pois=shoulder_poi_right)):
        connect.await_user_input(
            'Ensure the point {} is at the right acromial-clavicular joint'.format(
                shoulder_poi_right) +
            ' and continue script.')
    else:
        case.PatientModel.CreatePoi(Examination=exam,
                                    Point=par_beam_set.iso['Position'],
                                    Volume=0,
                                    Name=shoulder_poi_right,
                                    Color='Yellow',
                                    VisualizationDiameter=2,
                                    Type='Control')
        connect.await_user_input(
            'Place the point {} at the right acromial-clavicular joint'.format(shoulder_poi_right) +
            ' and continue script.')

    shoulder_right_position = case.PatientModel.StructureSets[exam.Name].PoiGeometries[
        shoulder_poi_right]

    # From here we build the shoulder block
    # Take the point coordinates and add a square that is offset from this point by:
    # Offsets: R/L : Half boxwidth -2 cm, I/S: Box height/2 - 5 cm, A/P: None
    # Dimensions R/L: 15 cm, I/S: 20 cm, A/P: 30
    # The deformation volume is now:
    # Intersect(External,Left) Union Intersect(External,Right)
    # box_x = 15
    # box_y = 30
    # box_z = 20
    # with CompositeAction('Create the right box')
    #   right_box_name = find uniqie
    #   retval_2 = case.PatientModel.CreateRoi(Name="Right_Box",
    #                             Color='Magenta',
    #                             Type='Control',
    #                             TissueName=None,
    #                             RbeCellTypeName=None,
    #                             RoiMaterial=None)
    #   retval_2.CreateBoxGeometry(Size={'x': 15, 'y': 20, 'z': 30},
    #                               Center={'x': shoulder_right_position.Point.x + 2 - box_x/2.,
    #                                    'y': shoulder_right_position.Point.y,
    #                                    'z': shoulder_right_position.Point.z + 5 - box_z/2.},
    #                                    Representation="TriangleMesh",
    #                                    VoxelSize=None)
    # Repeat for left
    # Generate deformation region
    #
    # with CompositeAction('ROI algebra (Shoulder_Deformation_Region, Image set: MidTreatment Synth CT)'):
    #  retval_6.CreateAlgebraGeometry(Examination=examination, Algorithm="Auto", ExpressionA={ 'Operation': "Intersection", 'SourceRoiNames': ["ExternalClean", "Left_Box"], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ExpressionB={ 'Operation': "Intersection", 'SourceRoiNames': ["ExternalClean", "Right_Box"], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ResultOperation="Union", ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })
    #  retval_6.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
    #  retval_6.DeleteExpression()
    #
    # Include the patient exam name in this deformation
    # case.GenerateOrganMotionExaminationGroup(
    # OrganUncertaintySettings={
    #   'Superior': 1,
    #   'Inferior': 2,
    #   'Anterior': 0,
    #   'Posterior': 0,
    #   'Right': 0,
    #   'Left': 0 },
    #   OnlySimulateMaxOrganMotion=True,
    #   SourceExaminationName="MidTreatment Synth CT",
    #   ExaminationGroupName="Shoulder_Motion",
    #   MotionRoiName="Shoulder_Deformation_Region", FixedRoiNames=[])

    #  xl = shoulder_left_position.Point.x
    #  yl = shoulder_left_position.Point.z
    # Call the first box: Box_Right
    ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()
    status.finish('Script complete. Optimize normally.')


def main():
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    rso = Pd(error=[],
             patient=GeneralOperations.find_scope(level='Patient'),
             case=GeneralOperations.find_scope(level='Case'),
             exam=GeneralOperations.find_scope(level='Examination'),
             db=GeneralOperations.find_scope(level='PatientDB'),
             plan=GeneralOperations.find_scope(level='Plan'),
             beamset=GeneralOperations.find_scope(level='BeamSet'))


if __name__ == '__main__':
    main()
