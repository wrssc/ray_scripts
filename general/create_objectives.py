""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""
import sys
import os
import logging
import datetime
import xml.etree.ElementTree
import connect
import Objectives
import UserInterface


def select_objective_protocol():
    """
    Prompt user to select the objective xml file they want to use
    :return: tree: Elementtree with user-selected objectives loaded
    """
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    # os join autoresolves the path
    path_objectives = os.path.join(os.path.dirname(__file__),
                                   protocol_folder,
                                   institution_folder)

    # Review specified directory for any objectiveset tags
    logging.debug('Searching folder {} for objectivesets'.format(path_objectives))
    objective_sets = {}
    for f in os.listdir(path_objectives):
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(path_objectives, f))
            if tree.getroot().tag == 'objectiveset':
                n = tree.find('name').text
                logging.debug('Found objectiveset {} in {}'.format(n, f))
                # Debugging fun
                if n in objective_sets:
                    # objective_sets[n].extend(tree.getroot())
                    logging.debug("Objective set {} already in list".format(n))
                else:
                    objective_sets[n] = tree#.getroot()
                    logging.debug("type of tree is {}".format(type(tree)))
                    logging.debug("type of tree.getroot is {}".format(type(tree.getroot())))
    # Augment the list to include all xml files found with an "objectiveset" tag in name
    input_dialog = UserInterface.InputDialog(
        inputs={'i': 'Select Objective Set'},
        title='Objective Selection',
        datatype={'i': 'combo'},
        initial={},
        options={'i': list(objective_sets.keys())},
        required=['i'])
    response = input_dialog.show()
    # Close on cancel
    if response == {}:
        logging.info('create_objective cancelled by user')
   ##     status.finish('User cancelled create objective creation.')
        sys.exit('create_objective cancelled by user')
    for k in input_dialog.values:
        logging.debug('This is key {} value {}'.format(k,input_dialog.values[k]))

    # logging.debug('user selected {}').format(input_dialog.values['i'])
    tree = objective_sets[input_dialog.values['i']]
    # tree = Objectives.select_objectives(input_dialog.values['i'])
    return tree


def main():
    """ Temp chunk of code to try to open an xml file"""
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        plan = connect.get_current("Plan")
        beamset = connect.get_current("BeamSet")
    except:
        logging.warning("patient, case and examination must be loaded")

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'planning_structs_conventional.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder, file)
    tree = Objectives.select_objectives(filename=path_protocols)
    tree = select_objective_protocol()
    logging.debug("selected file {}".format(path_protocols))
    # TODO::
    # Extend this for multiple objective sets found within a file
    # Consider adding functionality for protocols, orders, etc...
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    if tree.getroot().tag == 'objectiveset':
        logging.debug("parsing xml: {}".format(file))
        n = tree.find('name').text
        logging.debug('Found protocol {} in {}'.format(n, file))
        objectiveset = tree.getroot()
        objectives = objectiveset.findall('./objectives/roi')
        for o in objectives:
            o_name = o.find('name').text
            o_type = o.find('type').text
            # TESTING ONLY - TO DO ELIMINATE THIS NEXT LINE
            # This will need to be a user supplied dose level.
            if o.find('dose').attrib['units'] == '%':
                s_dose = '50'
            else:
                s_dose = None

            Objectives.add_objective(o,
                                     plan=plan,
                                     beamset=beamset,
                                     s_roi=None,
                                     s_dose=s_dose,
                                     s_weight=None,
                                     restrict_beamset=None)
    else:
        logging.debug('Could not find objective set using tree = {}'.format(tree))


if __name__ == '__main__':
    main()
