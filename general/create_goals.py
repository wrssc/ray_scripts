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
import Goals
import UserInterface


def main():
    protocol_folder = r'../protocols/UW_Approved'
    file_name = 'SampleGoal.xml'
    # Get current patient, case, and exam
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    tree = xml.etree.ElementTree.parse(os.path.join(folder, file_name))
    for g in tree.findall('//goals/roi'):
        print 'Adding goal ' + Goals.print_goal(g, 'xml')
        Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()
