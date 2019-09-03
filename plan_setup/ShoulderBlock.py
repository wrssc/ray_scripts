"""Add Shoulder Blocking VMAT Beams
Script to add shoulder blocking using user driven info



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
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Shoulder-Block'
__credits__ = []

import sys
import os
import logging
import connect
import UserInterface
import Beams
import BeamOperations
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
        steps=['SimFiducials point declaration',
               'isocenter Declaration',
               'Left shoulder POI',
               'Right shoulder POI',
               'Add Beams'],
        docstring=__doc__,
        help=__help__)

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = r'beamsets'
    file = 'UWVMAT_Beamsets.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)

    # For debugging we can bypass the dialog by uncommenting the below lines
    BeamSet = BeamOperations.BeamSet()
    BeamSet.name = '2 Arc VMAT - HN Shoulder'
    BeamSet.DicomName = '_____VMA_R_A_'
    BeamSet.technique = 'VMAT'
    BeamSet.machine = 'TrueBeam'
    BeamSet.rx_target = 'PTV_7000'
    BeamSet.iso_target = 'PTV_7000'
    BeamSet.modality = 'Photons'
    BeamSet.total_dose = 7000.
    BeamSet.number_of_fractions = 33
    new_beamset = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=BeamSet)
    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=BeamSet.name,
                                          path=path_protocols)

    # Uncomment for a dialog
    # order_name = None
    # BeamSet = BeamOperations.beamset_dialog(case=case,
    #                                         filename=file,
    #                                         path=path_protocols,
    #                                         order_name=order_name)

    # new_beamset = BeamOperations.create_beamset(patient=patient,
    #                                             case=case,
    #                                             exam=exam,
    #                                             plan=plan,
    #                                             BeamSet=BeamSet, dialog=False)
    # beams = BeamOperations.load_beams_xml(filename=file,
    #                                       beamset_name=BeamSet.protocol_name,
    #                                       path=path_protocols)
    patient.Save()


    logging.debug('Beamset: {} has beams originating from protocol beamset {} in file {} at {}'.format(
        new_beamset.DicomPlanLabel, BeamSet.protocol_name, file, path_protocols))

    logging.debug('now have {} elements in beams'.format(len(beams)))

    new_beamset.SetCurrent()
    # Place isocenter
    try:
        BeamSet.iso = BeamOperations.find_isocenter_parameters(
            case=case,
            exam=exam,
            beamset=new_beamset,
            iso_target=BeamSet.iso_target)

    except Exception:
        logging.warning('Aborting, could not locate center of {}'.format(BeamSet.iso_target))
        sys.exit('Failed to place isocenter')

    for b in beams:
        logging.info(('Loading Beam {}. Type {}, Name {}, Energy {}, StartAngle {}, StopAngle {}, ' +
                      'RotationDirection {}, CollimatorAngle {}, CouchAngle{} ').format(
            b.number, b.technique, b.name,
            b.energy, b.gantry_start_angle,
            b.gantry_stop_angle, b.rotation_dir,
            b.collimator_angle, b.couch_angle))
        logging.info('Rotation {} has type {}'.format(b.rotation_dir, type(b.rotation_dir)))
        rot = str(b.rotation_dir)
        for k, v in BeamSet.iso.iteritems():
            logging.debug("k {} and v {}".format(k, v))

        new_beamset.CreateArcBeam(ArcStopGantryAngle=b.gantry_stop_angle,
                                  ArcRotationDirection=rot,
                                  Energy=b.energy,
                                  IsocenterData=BeamSet.iso,
                                  Name=b.name,
                                  Description=b.name,
                                  GantryAngle=b.gantry_start_angle,
                                  CouchAngle=5,
                                  CollimatorAngle=0)


    PlanOperations.check_localization(case=case, exam=exam, create=True, confirm=False)


if __name__ == '__main__':
    main()
