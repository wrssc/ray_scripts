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
import Goals
import pprint


def main():
    protocol_folder = r'../../protocols/UW'
    file_name = 'UWLung_StandardFractionation.xml'
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

    ptv_md_dose = 60
    ptv_name = 'PTV_MD'

    file_name_with_path = os.path.join(protocol_folder, file_name)
    tree = xml.etree.ElementTree.parse(file_name_with_path)
    root = tree.getroot()

    for g in root.findall('./goals/roi'):
        if g.find('name').text == ptv_name and "%" in g.find('dose').attrib['units']:
            g.find('dose').attrib = "Gy"
            g.find('dose').text = str(ptv_md_dose)
        logging.debug('create_goals.py: Adding goal ' + Goals.print_goal(g, 'xml'))
        Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()

