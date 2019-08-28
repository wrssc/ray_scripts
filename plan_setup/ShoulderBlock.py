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

    BeamSet = BeamOperations.BeamSet()
    BeamSet.name = '2 Arc VMAT - HN Shoulder'
    BeamSet.DicomName ='_____VMA_R_A_'
    BeamSet.technique = 'VMAT'
    BeamSet.machine = 'TrueBeam'
    BeamSet.rx_target = 'PTV_7000'
    BeamSet.iso_target = 'PTV_7000'
    BeamSet.modality = 'Photons'
    BeamSet.total_dose = 7000.
    BeamSet.number_of_fractions = 33

    beam_elements = Beams.select_element(set_type='beamset',
                                         set_elements='beam',
                                         set_name=BeamSet.name,
                                         filename=file,
                                         folder=path_protocols)

    new_beamset = BeamOperations.create_beamset(patient=patient,
                                  case=case,
                                  exam=exam,
                                  plan=plan,
                                  dialog=False,
                                  BeamSet=BeamSet)
    beams = []
    for et_beamsets in beam_elements:
        beam_nodes = et_beamsets.findall('./beam')
        for b in beam_nodes:
            beam = BeamOperations.Beam()
            beam.number = b.find('BeamNumber').text
            beam.name = b.find('Name').text
            beam.technique = b.find('DeliveryTechnique').text
            beam.energy = b.find('Energy').text
            beam.gantry_start_angle = b.find('GantryAngle').text
            beam.gantry_stop_angle = b.find('GantryStopAngle').text
            beam.rotation_dir = b.find('ArcRotationDirection').text
            beam.collimator_angle = b.find('CollimatorAngle').text
            beam.couch_angle = b.find('CouchAngle').text
            beams.append(beam)
            logging.info(('Beam {} found. Type {}, Name {}, Energy {}, StartAngle {}, StopAngle {},' +
                         'RotationDirection {}, CollimatorAngle {}, CouchAngle{} ').format(
                             beam.number, beam.technique, beam.name,
                             beam.energy, beam.gantry_start_angle,
                             beam.gantry_stop_angle, beam.rotation_dir,
                             beam.collimator_angle, beam.couch_angle))



    PlanOperations.check_localization(case=case, exam=exam, create=True, confirm=False)


if __name__ == '__main__':
    main()
