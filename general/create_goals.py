""" Create Clinical Goals and Objectives

    Add clinical goals and objectives in RayStation given user supplied inputs

    Inputs::


"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import os
import logging
import datetime
import xml.etree.ElementTree
import connect
import UserInterface
import WriteTpo
import Goals


def main():
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file_name = 'UWLung_StandardFractionation.xml'
    path_file = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder, file_name)
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    # Get current patient, case, and exam
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        plan = connect.get_current('Plan')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient and plan to be loaded')
        sys.exit('This script requires a patient and plan to be loaded')

    # TODO: replace all the hardcoded options with a user interface prompt

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)
    print tpo.protocols

    ptv_md_dose = 60
    ptv_name = 'PTV_MD'

    # This dialog grabs the relevant parameters to generate the whole brain plan
    input_dialog = UserInterface.InputDialog(
        inputs={
            'input0': 'Number of targets',
            'input1': 'Select Protocol',
        },
        title='Initial Input Clinical Goals',
        datatype={'input1': 'combo'},
        initial={},
        options={'input1': list(tpo.protocols.keys())},
        required=['input0', 'input1'])

    # Launch the dialog
    inputs = input_dialog.show()
    print input_dialog['input1']
    file_name = input_dialog['input1']
    path_file = path_file = os.path.join(os.path.dirname(__file__),
                                         protocol_folder, institution_folder, file_name)

    # file_name_with_path = os.path.join(protocol_folder,file_name)

    tree = xml.etree.ElementTree.parse(path_file)
    root = tree.getroot()

    for g in root.findall('./goals/roi'):
        if g.find('name').text == ptv_name and "%" in g.find('dose').attrib['units']:
            g.find('dose').attrib = "Gy"
            g.find('dose').text = str(ptv_md_dose)
        logging.debug('create_goals.py: Adding goal ' + Goals.print_goal(g, 'xml'))
        Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()
