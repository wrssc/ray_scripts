""" Select element
Testing only

Version Notes:
0.0.0 

Attempt to use the select element function to search any xml file regardless of format
I think this will be obsolete. I think we ought to move to pandas dataframes like
structure matching.

Known Issues: 

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
__date__ = '02-Feb-2020'

__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''

__raystation__ = '8.0.B'
__maintainer__ = 'Adam Bayliss'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = ''

import os
import sys
import logging
import random
import csv
import xml
import pandas as pd
import re

# Local imports
import connect
import BeamOperations
import Objectives
import Beams
import StructureOperations
import UserInterface

def test_select_element(patient, case, exam, plan, beamset):
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
            folder=path_protocols
        )
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
    file = 'UWVMAT.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)

    # For debugging we can bypass the dialog by uncommenting the below lines
    BeamSet = BeamOperations.BeamSet()
    BeamSet.name = '2 Arc VMAT - HN Shoulder'
    BeamSet.DicomName = 'Test' + str(random.randint(1, 100))
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

    # Test to load objectives
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWProstate.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    order_name = 'Prostate Only-Hypo [28Fx 7000cGy]'
    objective_elements = Beams.select_element(
        set_level='order',
        set_type=None,
        set_elements='objectives',
        set_level_name=order_name,
        filename=file,
        dialog=False,
        folder=path_protocols,
        verbose_logging=False)
    logging.debug('Objectives are {}'.format(objective_elements))

    plan_targets = StructureOperations.find_targets(case=case)
    translation_map = {plan_targets[0]: '1000'}
    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_n = o.find('name').text
            o_t = o.find('type').text
            o_d = o.find('dose').text
            if o_n in translation_map:
                s_roi = translation_map[o_n][0]
            else:
                s_roi = None

            if "%" in o.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                o_r = o.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                # Correct the relative dose to the user-specified dose levels for this structure
                if o_r in translation_map:

                    s_dose = float(translation_map[o_r][1])  # * float(o_d) / 100
                    Objectives.add_objective(o,
                                             exam=exam,
                                             case=case,
                                             plan=plan,
                                             beamset=beamset,
                                             s_roi=s_roi,
                                             s_dose=s_dose,
                                             s_weight=None,
                                             restrict_beamset=None,
                                             checking=True)
                else:
                    logging.debug(
                        'No match found protocol roi: {}, with a relative dose requiring protocol roi: {}'
                            .format(o_n, o_r))
                    s_dose = 0
                    pass
            else:
                s_dose = None
                Objectives.add_objective(o,
                                         exam=exam,
                                         case=case,
                                         plan=plan,
                                         beamset=beamset,
                                         s_roi=s_roi,
                                         s_dose=s_dose,
                                         s_weight=None,
                                         restrict_beamset=None,
                                         checking=True)

    # Test to activate the dialog and select in select_element functio