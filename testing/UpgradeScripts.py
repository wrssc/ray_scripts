""" Upgrade Versions

"""
import os
import connect
from collections import namedtuple
from GeneralOperations import find_scope
import logging

STRUCTURE_TEMPLATE_LOCATION = r'U:\\UWHealth\\RadOnc\\ShareAll\\RayStation\\11B\\Templates\\Structure\\10A_Versions\\'


def build_file_list():
    file_list = []
    for file in os.listdir(STRUCTURE_TEMPLATE_LOCATION):
        if file.endswith(".rsbak"):
            file_list.append(os.path.join(STRUCTURE_TEMPLATE_LOCATION, file))
    return file_list


def load_structure_templates(pd):
    files = build_file_list()
    for f in files:
        logging.debug("Loading {}".format(f))
        pd.db.ImportStructureTemplate(FileName=f)


def main():
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error=[],
            patient=find_scope(level='Patient'),
            case=find_scope(level='Case'),
            exam=find_scope(level='Examination'),
            db=find_scope(level='PatientDB'),
            plan=None,  # find_scope(level='Plan'),
            beamset=None, )  # find_scope(level='BeamSet'))
    load_structure_templates(pd)


if __name__ == '__main__':
    main()
