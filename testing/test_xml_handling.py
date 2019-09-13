"""Testing xml handling



Version Notes: 1.0.0 Original

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
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Test_IO'
__credits__ = []

import os
import sys
import logging
import connect
import BeamOperations
import Beams
import random


def test_select_element(patient, case, exam, plan):
    """Testing for the selection of elements from different levels in a protocol xml file"""
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWHeadNeck.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    # Test 1:L
    # Try to get a list of beamsets located in
    set_levels = ['beamset', 'order']
    set_type = [None, 'beamset']
    on_screen_message = 'TESTING of XML-element find'

    for i, sl in enumerate(set_levels):
        on_screen_message += 'Test find a list of beamsets in the {} protocol '.format(file)
        logging.debug('Using {} and {}'.format(sl, set_type[i]))
        available_beamsets = Beams.select_element(
            set_level=sl,
            set_type=set_type[i],
            set_elements='beam',
            filename=file,
            dialog=False,
            folder=path_protocols)
        logging.debug('Available beamsets include: {}'.format(available_beamsets))
        if not available_beamsets:
            on_screen_message += 'FAIL: Could not Find Beamset at protocol level'
        else:
            for bs in available_beamsets:
                on_screen_message += 'Beamset {} found \n'.format(bs)

    # Uncomment for a dialog
    order_name = None
    BeamSet = BeamOperations.beamset_dialog(case=case,
                                             filename=file,
                                             path=path_protocols,
                                             order_name=order_name)

    # new_beamset = BeamOperations.create_beamset(patient=patient,
    #                                             case=case,
    #                                             exam=exam,
    #                                             plan=plan,
    #                                             dialog=False,
    #                                             BeamSet=BeamSet)

    # beams = BeamOperations.load_beams_xml(filename=file,
    #                                       beamset_name=BeamSet.protocol_name,
    #                                       path=path_protocols)

    # Test an exact load of a specific beamset
    beamset_folder = r'beamsets'
    file = 'UWVMAT_Beamsets.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)

    # For debugging we can bypass the dialog by uncommenting the below lines
    BeamSet = BeamOperations.BeamSet()
    BeamSet.name = '2 Arc VMAT - HN Shoulder'
    BeamSet.DicomName = 'Test'+str(random.randint(1, 100))
    BeamSet.technique = 'VMAT'
    BeamSet.machine = 'TrueBeam'
    BeamSet.rx_target = 'PTV_7000'
    BeamSet.iso_target = 'PTV_7000'
    BeamSet.modality = 'Photons'
    BeamSet.total_dose = 7000.
    BeamSet.number_of_fractions = 33
    BeamSet.protocol_name = '2 Arc VMAT - HN Shoulder'

    new_beamset = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=BeamSet)

    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=BeamSet.protocol_name,
                                          path=path_protocols)


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

    test_select_element(patient=patient, case=case, plan=plan, exam=exam)


if __name__ == '__main__':
    main()
