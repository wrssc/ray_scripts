"""Add Shoulder Blocking VMAT Beams

This script uses two user defined points placed at the superior acromial-clavicular joint to create a new beamset
with an arc-avoidance region. The lower boundary of the blocked region is set by a margin around the point placement.

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
__date__ = '01-Feb-2018'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8.0.B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Shoulder-Block'
__credits__ = []

import sys
import os
import logging
import connect
import numpy as np
import UserInterface
import BeamOperations
import StructureOperations
import PlanOperations


def main():
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    try:
        patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        exam = connect.get_current("Examination")
    except SystemError:
        raise IOError("No examination loaded. Load patient ct and plan.")

    try:
        plan = connect.get_current("Plan")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")
        sys.exit('This script requires a Beam Set to be loaded')

    # Script will run through the following steps.  We have a logical inconsistency here with making a plan
    # this is likely an optional step
    status = UserInterface.ScriptStatus(
        steps=[
            'Loading Beamset and Isocenter Declaration',
            'Left shoulder POI placement',
            'Right shoulder POI placement',
            'Adjusting Beam limits'],
        docstring=__doc__,
        help=__help__)

    status.next_step('Initial dialog for setting BeamSet parameters')

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWHeadNeck.xml'
    # beamset_folder = r'beamsets'
    # file = 'UWVMAT.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)

    # For debugging we can bypass the dialog by uncommenting the below lines
    order_name = None
    par_beam_set = BeamOperations.beamset_dialog(case=case,
                                                 filename=file,
                                                 path=path_protocols,
                                                 order_name=order_name)

    # Check to see if a beamset with this name exists already. If it does, quit

    rs_beam_set = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=par_beam_set)

    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=par_beam_set.protocol_name,
                                          path=path_protocols)

    logging.debug(
        'Beamset: {} has beams originating from protocol beamset {} in file {} at {}'.format(
            rs_beam_set.DicomPlanLabel, par_beam_set.protocol_name, file, path_protocols))

    # Place isocenter
    try:
        par_beam_set.iso = BeamOperations.find_isocenter_parameters(
            case=case,
            exam=exam,
            beamset=rs_beam_set,
            iso_target=par_beam_set.iso_target)

    except Exception:
        logging.warning('Aborting, could not locate center of {}'.format(par_beam_set.iso_target))
        sys.exit('Failed to place isocenter')

    BeamOperations.place_beams_in_beamset(iso=par_beam_set.iso, beamset=rs_beam_set, beams=beams)

    patient.Save()
    rs_beam_set.SetCurrent()

    status.next_step('Placing left shoulder blocking point')

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient Modeling'].Button_Patient_Modeling.Click()
    except:
        logging.debug("Could not click on the plan Design MenuItem")

    shoulder_poi_left = 'Block_L_Inf_POI'
    shoulder_poi_right = 'Block_R_Inf_POI'
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

    # Test if right is more negative than left
    left = StructureOperations.convert_poi(shoulder_left_position)
    right = StructureOperations.convert_poi(shoulder_right_position)
    if left[0] < right[0]:
        UserInterface.WarningBox(
            'Script aborted, left and right shoulder points appear to be flipped')
        status.finish('Script aborted, left and right shoulder points appear to be flipped')
        sys.exit('Script aborted, left and right shoulder points appear to be flipped')

    machine_ref = rs_beam_set.MachineReference.MachineName
    if machine_ref == 'TrueBeamSTx':
        logging.info('Current Machine is {} setting max jaw limits'.format(machine_ref))
        x1limit = -20
        x2limit = 20
        y1limit = -10.9
        y2limit = 10.9
    elif machine_ref == 'TrueBeam':
        x1limit = -20
        x2limit = 20
        y1limit = -20
        y2limit = 20
    # For a point at (xo, yo, zo) and isocenter at (xi, yi, zi), the value of the y1 jaw (presuming collimator zero),
    # letting xi = 100 cm, is:
    # y1 = xi * (yi - yo)/(xi - xo) = 100 * (yi - yo)/(xi - xo) - note the sign is < 0 if yi < yl
    # (assuming y increases as we move inferior)
    # we will also use the visualization diameter of the point to capture the superior margin we should give the point
    iso_position = par_beam_set.iso['Position']
    isd = 100.
    xi = float(iso_position['x'])
    yi = iso_position['z']

    # Add a margin based on the visualization diameter of the point
    yl_margin = float(
        case.PatientModel.PointsOfInterest[shoulder_poi_left].VisualizationDiameter) / 2.
    yr_margin = float(
        case.PatientModel.PointsOfInterest[shoulder_poi_right].VisualizationDiameter) / 2.

    xl = shoulder_left_position.Point.x
    yl = shoulder_left_position.Point.z
    left_y1 = np.sign(yl - yi) * isd * abs((yl - yi) / (isd - xl - xi)) + yl_margin

    xr = shoulder_right_position.Point.x
    yr = shoulder_right_position.Point.z
    right_y1 = np.sign(yr - yi) * isd * abs((yr - yi) / (isd - xr - xi)) + yr_margin

    logging.info('Left shoulder jaw position on lateral arcs should be {}'.format(left_y1))
    logging.info('Right shoulder jaw position on lateral arcs should be {}'.format(right_y1))

    # Setting beam limits
    opt_index = PlanOperations.find_optimization_index(plan=plan, beamset=rs_beam_set)
    i = 0
    while i is not None:
        try:
            opt_setup = \
            plan.PlanOptimizations[opt_index].OptimizationParameters.TreatmentSetupSettings[i]
            if opt_setup.ForTreatmentSetup.DicomPlanLabel == rs_beam_set.DicomPlanLabel:
                i = None
            else:
                i += 1
        except:
            logging.debug('Could not find the TreatmentSetupSettings corresponding to {}'.format(
                rs_beam_set.DicomPlanLabel))
            sys.exit('Could not find the TreatmentSetupSettings corresponding to {}'.format(
                rs_beam_set.DicomPlanLabel))

    status.next_step('Finalizing beam configuration')
    for b in opt_setup.BeamSettings:
        start = b.ForBeam.GantryAngle
        stop = b.ForBeam.ArcStopGantryAngle
        rot = b.ForBeam.ArcRotationDirection
        right_sided = (start >= 180 and stop >= 180) and \
                      ((start >= 230 and stop <= 290 and rot == 'Clockwise') or
                       (start <= 290 and stop >= 230 and rot == 'CounterClockwise'))
        left_sided = (start <= 180 and stop <= 180) and \
                     ((start <= 70 and stop <= 130 and rot == 'Clockwise') or
                      (start <= 130 and stop >= 70 and rot == 'CounterClockwise'))
        logging.debug('Start={}, Stop={}, Dir={}, Right={}, Left={}'.format(
            start, stop, rot, right_sided, left_sided))

        # Set Left Jaws
        if left_sided or right_sided:
            if right_sided:
                y1_limit = right_y1
            else:
                y1_limit = left_y1

            logging.info(
                'Beam {} enters through the shoulder and will have jaw locked to less than y1 = {}'.format(
                    b.ForBeam.Name, y1_limit))

            success = BeamOperations.check_beam_limits(b.ForBeam.Name, plan=plan,
                                                       beamset=rs_beam_set,
                                                       limit=[x1limit, x2limit, y1_limit, y2limit],
                                                       change=True, verbose_logging=False)
            if not success:
                sys.exit('An error occurred setting beam limits')

    PlanOperations.check_localization(case=case, exam=exam, create=True, confirm=False)
    ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()
    status.finish('Script complete. Optimize normally.')


if __name__ == '__main__':
    main()
