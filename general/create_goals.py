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
    # Get current patient, case, exam, and plan
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
    # Without adding another attribute to the goals list, here's what we need to do
    targets = ['PTV', 'ITV', 'GTV']
    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

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
    print input_dialog.show()
    # Store the number of targets
    input_targets = int(input_dialog.values['input0'])
    logging.info("create_goals.py: user input {} targets for protocol: {}".format(
        input_targets, input_dialog.values['input1']
    ))
    # To load the xml from file directly, without use of the TPO load:
    # path_file = path_file = os.path.join(os.path.dirname(__file__),
    #                                     protocol_folder, institution_folder, file_name)
    # tree = xml.etree.ElementTree.parse(path_file)
    # tree = tpo.protocols[input_protocol]
    # root = tree.getroot()
    root = tpo.protocols[input_dialog.values['input1']]
    protocol_targets = []
    for g in root.findall('./goals/roi'):
        # Ugh, gotta be a more pythonic way to do this loop
        # ? for g, t in ((a,b) for a in root.findall('./goals/roi') for b in targets)
        for t in targets:
            if t in g.find('name').text and g.find('name').text not in protocol_targets:
                protocol_targets.append(g.find('name').text)
    logging.debug("protocol contains {} targets called: {}".format(
        len(protocol_targets), protocol_targets))

    # Second dialog
    # Find RS targets
    target_matches = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'Ptv':
            target_matches.append(r.Name)

    final_inputs = {}
    final_options = {}
    final_datatype = {}
    final_required = []

    # Add an input for every target name and dose
    for i in range(1, input_targets):
        k_name = str(2 * i - 1)
        k_dose = str(2 * i)
        final_inputs[k_name] = 'Target' + str(i) + ' name'
        final_inputs[k_dose] = 'Target' + str(i) + ' Dose in cGy'
        final_options[k_name] = target_matches
        final_datatype[k_name] = 'combo'
        final_required.append(k_name)
        final_required.append(k_dose)
    # Grab the number of inputs so far and start new input
    i = len(final_inputs) + 1
   ## for t in protocol_targets:
   ##     print t
   ##     final_inputs[str(i)] = 'Match protocol target:' + str(t) + ' to one of these'
   ##     final_options[str(i)] = target_matches
   ##     i += 1
    # Loop over user identified targets that have no corresponding match.
    for k, v in final_inputs.iteritems():
        logging.debug("create_goals.py: Inputs created as name, value: {} : {}".format(
            k, v))
    # TODO: Add the matching elements here, for the number of targets found in the protocol
    #   add an input key and a combo-box
    #   key name should be: 'Target found with name' + protocol_targets[p] select the target
    #   from the target list matching this target
    #   if input_targets > protocol_targets
    #   all other: Protocol does not have instructions for all of your targets:
    #   the script should have a checkbox for SBRT coverage, differential dose, same as first target


    final_dialog = UserInterface.InputDialog(
        inputs=final_inputs,
        title='Input Clinical Goals',
        datatype=final_datatype,
        initial={},
        options=final_options,
        required=final_required)
    print final_dialog.show()



#       if g.find('name').text == ptv_name and "%" in g.find('dose').attrib['units']:
#           g.find('dose').attrib = "Gy"
#           g.find('dose').text = str(ptv_md_dose)
#       logging.debug('create_goals.py: Adding goal ' + Goals.print_goal(g, 'xml'))
#       Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()
