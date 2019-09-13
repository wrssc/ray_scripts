""" Add Beams

    Contains functions required to load objectives from xml files
    add the beams to RayStation.
"""
import sys
import os
import logging
import xml.etree.ElementTree
import UserInterface


def select_element(set_level, set_type, set_elements,
                   folder=None, filename=None,
                   set_level_name=None, set_type_name=None,
                   protocol=None, dialog=True, verbose_logging=True):
    """
    Function to select the correct element from an xml file
    User will supply a folder, in which case, they will need to select from all files found
    a filename, in which case they select from all sets found
    a set_name which returns the exact element-tree match for that set.

    :param set_type: is the xml tag of the structure to find. Accepted: objectiveset, beamset
    :param set_elements: are the leaves within the set_type (i.e. beams or objectives
    :param set_type_name the <name> entry of the set_type from xml file
    :param set_level: (optional) the elementtree level where we expect the set_type to live,
        this can be used to eliminate set_types which are living at the protocol (root) level.
        If there are multiple set_type entries at this level, the et_list will have multiple entries
        Examples include: <plan> <protocol>
    :param folder: folder from os to search within and prompt user to select appropriate protocol
    :param filename: os joined protocol name, used to directly open a file
    :param protocol: ElementTree-Element of the objectiveset you want

    :return: et_list: elementtree list of elements with objectives and/or objectivesets

    Usage:
    TODO: Update these use cases for the new script.
    USE CASE 1:
    ## User knows the file the order is housed in but wants to select the order
    # Prompt user to select an order out of a specific file (UWBrainCNS.xml) located in
    # ../protocols/UW
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file, folder=path_protocols)


    USE CASE 2:
    ## User knows the exact order that needs to be loaded. Return only the selected order and
    ## any objectivesets in the protocol
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    order_name = 'GBM Brain 6000cGy in 30Fx [Single-Phase Stupp]'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file,
                                                              folder=path_protocols,
                                                              order_name=order_name)
    USE CASE 3:
    ## User will select a default objectiveset from the standard objectives directory
    objective_elements = Objectives.select_objective_protocol()

    USE CASE 4:
    ## User supplies ordername and protocol element:
    objective_elements = Objectives.select_objective_protocol(order_name=order_name,
                                                              protocol=protocol)

    TODO: Searching:
        1) Folder should be non-optional.
            If only a folder is supplied all set_types with non None set_elements are returned
        2) Filename is optional. Look in there only if supplied.
        3)
    TODO: Two options for output:
        1) when user gives a set_name then et_list should contain a single element or None
        2) when set_name is None, et_list should consist of all set_types that have non-empty set_elements
        3) set_level should be optional


    """
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    objectives_folder = r'objectives'

    et_level = './' + set_level
    # et_type = './' + set_type
    et_element = './' + set_elements
    et_list = []
    sets = {}

    # First search the file list to be searched depending on the supplied information
    # output a list of files that are to be scanned
    if filename is not None:
        # User directly supplied the filename of the protocol or file containing the set
        path_to_sets = folder
        if set_type_name is not None:
            if folder is None:
                path_to_sets = os.path.join(os.path.dirname(__file__),
                                            protocol_folder,
                                            institution_folder)
                if verbose_logging:
                    logging.debug('Using a default path of {}'.format(path_to_sets))

            if filename.endswith('.xml'):
                # Parse the xml file
                tree = xml.etree.ElementTree.parse(os.path.join(path_to_sets, filename))
                if verbose_logging:
                    logging.debug('tree root is {}'.format(tree.getroot().tag))
                # Search first for a top level set
                sets = tree.findall('./' + set_type)
                if verbose_logging:
                    logging.debug('sets is {}'.format(sets))
                for s in sets:
                    if verbose_logging:
                        logging.debug('set name is {}'.format(set_type_name))
                    if s.find('name').text == set_type_name:
                        et_list.append(s)
                        return et_list
                    else:
                        logging.warning('No matching {} found with name {}'.format(set_type, set_type_name))
        else:
            file_list = [filename]


    elif folder and not filename:
        # User wants to select the protocol or objectiveset from a list of xml files
        path_to_sets = os.path.join(os.path.dirname(__file__),
                                    protocol_folder,
                                    institution_folder)
        file_list = os.listdir(path_to_sets)
    else:
        # If no information was supplied look in the objectives folder
        path_to_sets = os.path.join(os.path.dirname(__file__),
                                    protocol_folder,
                                    institution_folder,
                                    objectives_folder)
        file_list = os.listdir(path_to_sets)

    # Return variable. A list of ET Elements
    if protocol is not None:
        # Search first for a top level objectiveset
        # Find the objectivesets:
        # These get loaded for protocols regardless of orders
        protocol_set = protocol.findall(et_type)
        for p in protocol_set:
            et_list.append(p)
        levels = protocol.findall(et_level)
        # Search the orders to find those with objectives and return the candidates
        # for the selectable objectives
        for l in levels:
            elements = l.findall(et_element)
            if elements:
                n = l.find('name').text
                sets[n] = l
            else:
                if verbose_logging:
                    logging.debug('No objects of type {} found in {}'.format(set_type, l.find('name').text))
    else:
        for f in file_list:
            if f.endswith('.xml'):
                # Parse the xml file
                tree = xml.etree.ElementTree.parse(os.path.join(path_to_sets, f))
                if verbose_logging:
                    logging.debug('tree root level is {}'.format(tree.getroot().tag))
                # Search first for a top level set. This would be a file of beamsets, goalsets, or objectivesets
                # Find the parents
                levels = tree.findall('./' + set_level)
                for l in levels:
                    if verbose_logging:
                        logging.debug('Examining set level {}: {}'.format(set_level, l.find('name').text))
                    if set_type is None:
                        logging.debug('The parent is levels and children are just groups of elements return levels')
                        # Make a set of set_types that contain elements and are unique.
                        e = l.findall('./' + set_elements)
                        if e is not None:
                            n = l.find('name').text
                            if n not in sets:
                                sets[n] = l
                                if verbose_logging:
                                    logging.debug("Set {} added to list".format(n))
                            else:
                                if verbose_logging:
                                    logging.debug("Set {} already in list".format(n))
                        else:
                            if verbose_logging:
                                logging.debug('No elements of type {} are found in {}'.format(set_elements, set_level))
                    else:
                        logging.debug('The parent is levels and the children are sets, return sets')
                        types = l.findall('./' + set_type)
                        logging.debug('Found types is {} for set_type {}'.format(types,set_type))
                        for t in types:
                            if verbose_logging:
                                logging.debug('Examining set type {}: {}'.format(set_type, t.find('name').text))
                            e = t.findall('./' + set_elements)
                            if e is not None:
                                n = t.find('name').text
                                if n not in sets:
                                    sets[n] = t
                                    if verbose_logging:
                                        logging.debug("Set {} added to list".format(n))
                                else:
                                    if verbose_logging:
                                        logging.debug("Set {} already in list".format(n))
                            else:
                                if verbose_logging:
                                    logging.debug('No elements of type {} are found in {}'.format(
                                        set_elements, t.find('name').text))
                # Sets now is a dictionary with keys given by the appropriate parent.
                # contains a list of all element trees that contain elements.
                # need to apply filters

    # Augment the list to include all xml files found with an "objectiveset" tag in name
    if set_type_name is not None:
        try:
            selected_order = sets[set_type_name]
        except KeyError:
            # This order doesn't appear to match one that has objectives in it
            # Pass an empty entry
            if verbose_logging:
                logging.debug(
                    'Level: {} has no {}. Protocol {} being used'.format(set_type_name, set_elements, set_elements))
            selected_order = None
    elif set_level_name is not None:
        try:
            selected_order = sets[set_level_name]
        except KeyError:
            # This order doesn't appear to match one that has objectives in it
            # Pass an empty entry
            if verbose_logging:
                logging.debug(
                    'Level: {} has no {}. Protocol {} being used'.format(set_type_name, set_elements, set_elements))
            selected_order = None
    elif dialog:
        input_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Objective Set'},
            title='Objective Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(sets.keys())},
            required=['i'])
        response = input_dialog.show()
        # Close on cancel
        if response == {}:
            logging.info('create_objective cancelled by user')
            sys.exit('create_objective cancelled by user')
        else:
            if verbose_logging:
                logging.debug('User selected order: {} for objectives'.format(
                    input_dialog.values['i']))
            selected_order = sets[input_dialog.values['i']]
    else:
        # Return the list of all sets found
        return list(sets.keys())

    # Add the order to the returned list
    if selected_order is not None:
        et_list.append(selected_order)

    if et_list is not None:
        for e in et_list:
            logging.info('Objective list to be loaded {}'.format(
                e.find('name').text))
    else:
        logging.warning('objective files were not found')

    return et_list
