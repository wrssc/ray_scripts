import xml.etree.ElementTree
import logging  # noqa: F401
from collections import OrderedDict

import os
import xml.etree.ElementTree
from PlanReview.utils.constants import KEY_TREAT_FREQ, KEY_IMAGING_FREQ, KEY_O, KEY_D


def load_protocols(folder):
    """
    Load protocols from XML files in the specified folder.

    Args:
        folder (str): The file folder containing XML files of protocols.

    Returns:
        dict: A dictionary containing protocol names as keys and a list containing
              the protocol ElementTree and the file path as values.
    """
    protocols = {}
    # Search protocol list, parsing each XML file for protocols and goalsets
    for f in os.listdir(folder):
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(folder, f))
            if tree.getroot().tag == 'protocol':
                n = tree.find('name').text
                protocols[n] = [None, None]
                protocols[n][0] = tree.getroot()
                protocols[n][1] = f
    return protocols


def load_plan_names(folder):
    """
    Load plan names from XML files in the specified folder.

    Args:
        folder (str): The file folder containing XML files of plan names.

    Returns:
        dict: A dictionary containing plan names as keys and a tuple with the
              AnatomicGroup and Description as values.
    """
    plan_names = {}
    for f in os.listdir(folder):
        if f.endswith('xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(folder, f))
            if tree.getroot().tag == 'BodySite':
                site_elements = tree.findall('Site')
                for s in site_elements:
                    n = s.find('SiteName').text
                    plan_names[n] = (s.find('AnatomicGroup').text,
                                     s.find('Description').text)
    return plan_names


def get_sites(protocols):
    """
    Get a list of unique site names from the given protocol dictionary.

    Args:
        protocols (dict): A dictionary of protocols, where keys are protocol names
                          and values are xml.etree.ElementTree.Element instances.

    Returns:
        list: A list of unique site names found in the protocols.
    """
    sites = []
    for _, p in protocols.items():
        raw_sites = p[0].find('AnatomicGroup').text.replace(", ", "")
        sites += raw_sites.split(",")
    return list(set(sites))


def site_protocol_list(protocols, site_name):
    """
    Get a dictionary of protocols matching the given site name.

    Args:
        protocols (dict): A dictionary of protocols, where keys are protocol names
                          and values are xml.etree.ElementTree.Element instances.
        site_name (str): The site name to match.

    Returns:
        dict: A dictionary of matching protocols, where keys are protocol names
              and values are xml.etree.ElementTree.Element instances.
    """
    matching_protocols = {}
    for n, p in protocols.items():
        if site_name in p[0].find('AnatomicGroup').text:
            matching_protocols[n] = p[0]
    return matching_protocols


def find_protocol(protocols,protocol_name):
    for n, p in protocols.items():
        if protocol_name in p[0].find('name').text:
            return {n: p}


def order_dict(protocol):
    """
    Create a dictionary of orders from a given protocol element tree.

    Args:
        protocol (xml.etree.ElementTree.Element): A protocol element parsed from XML.

    Returns:
        dict: A dictionary of orders, where keys are order names and
              values are xml.etree.ElementTree.Element instances.
    """
    orders = {}
    for o in protocol[0].findall('order'):
        orders[o.find('name').text] = o
    return orders


def get_all_orders(protocols):
    """
    Get a dictionary of all orders from the given protocol dictionary.

    Args:
        protocols (dict): A dictionary of protocols, where keys are protocol names
                          and values are xml.etree.ElementTree.Element instances.

    Returns:
        dict: A dictionary of all orders, where keys are order names
              and values are xml.etree.ElementTree.Element instances.
    """
    orders = {}
    for _, p in protocols.items():
        for o in p[0].findall('order'):
            orders[o.find('name').text] = o
    return orders


def find_order(protocol, order_name):
    """
    Find an order within a protocol element tree by its name. If more than one instance
    of the same order name is found or if no match is found, return None.

    Args:
        protocol (xml.etree.ElementTree.Element): A protocol element parsed from XML.
        order_name (str): The name of the order to search for.

    Returns:
        xml.etree.ElementTree.Element or None: An order element matching the provided name, or None
                                               if the name is not found or multiple instances are found.
    """
    orders = order_dict(protocol)
    matched_orders = [o for k, o in orders.items() if k == order_name]

    if len(matched_orders) == 1:
        return matched_orders[0]
    else:
        return None


def get_frequencies(protocol, order_name):
    """
    Get the treatment frequency and imaging frequency for a given order name within a protocol.

    Args:
        protocol (ElementTree): An ElementTree object representing the protocol XML.
        order_name (str): The name of the order to search for.

    Returns:
        dict: A dictionary containing the treatment frequency and imaging frequency for the given order name.
            The dictionary contains the following keys: 'treatment_frequency_options', 'treatment_frequency_default',
            'imaging_frequency_options', and 'imaging_frequency_default'.
            If the order or prescription is not found, an empty dictionary is returned.
    """
    order = find_order(protocol, order_name)
    frequencies = {}

    if order is not None:
        prescription = order.find('prescription')

        if prescription is not None:
            treatment_frequency = prescription.find('treatment_frequency')
            imaging_frequency = prescription.find('imaging_frequency')

            if treatment_frequency is not None:
                options = treatment_frequency.findall('option')
                default_options = [opt for opt in options if opt.attrib.get('default', 'false') == 'true']

                frequencies[KEY_TREAT_FREQ+KEY_O] = [opt.text if opt.text is not None else '' for opt in options]
                frequencies[KEY_TREAT_FREQ+KEY_D] = default_options[0].text if default_options else ''

            if imaging_frequency is not None:
                options = imaging_frequency.findall('option')
                default_options = [opt for opt in options if opt.attrib.get('default', 'false') == 'true']

                frequencies[KEY_IMAGING_FREQ+KEY_O] = [opt.text if opt.text is not None else '' for opt in options]
                frequencies[KEY_IMAGING_FREQ+KEY_D] = default_options[0].text if default_options else ''

    return frequencies


def get_order_instructions(protocol, order_name):
    """
    Get the instructions for a given order name within a protocol.

    Args:
        protocol (ElementTree): An ElementTree object representing the protocol XML.
        order_name (str): The name of the order to search for.

    Returns:
        list: A list of dictionaries representing the instructions for the given order name.
            Each dictionary contains the following keys: 'type', 'radio', 'combo', 'comment', and 'text'.
            If the order or prescription is not found, an empty list is returned.
    """
    order = find_order(protocol, order_name)
    instructions = []

    if order is not None:
        prescription = order.find('prescription')

        if prescription is not None:
            order_instructions = prescription.findall('Instruction')

            for inst in order_instructions:
                instruction = {
                    'type': inst.attrib.get('type', ''),
                    'radio': inst.attrib.get('radio', ''),
                    'combo': inst.attrib.get('combo', ''),
                    'comment': inst.attrib.get('comment', ''),
                    'text': inst.text if inst.text is not None else '',
                }
                instructions.append(instruction)

    return instructions

import logging
from typing import List, Dict


def inst_unique(all_dict: List[Dict[str, str]], new_dict: Dict[str, str]) -> int:
    """
    Finds the index of the first dictionary in `all_dict` that has all key-value pairs
    from `new_dict` (excluding 'indx').

    Args:
        all_dict (List[Dict[str, str]]): A list of dictionaries to search through.
        new_dict (Dict[str, str]): The dictionary to match against `all_dict`.

    Returns:
        int: The index of the first matching dictionary in `all_dict`, or -1 if no match is found.
    """
    # Remove the 'indx' key from the new dictionary
    new_dict_no_indx = {k.lower(): v.lower() for k, v in new_dict.items() if k.lower() != 'indx'}

    # Iterate over each dictionary in all_dict
    for i, d in enumerate(all_dict):
        # Remove the 'indx' key from the current dictionary
        curr_dict_no_indx = {k.lower(): v.lower() for k, v in d.items() if k.lower() != 'indx'}
        # Check if the current dictionary contains all key-value pairs in the new dictionary
        if all([k in curr_dict_no_indx and curr_dict_no_indx[k] == v for k, v in new_dict_no_indx.items()]):
            return False

    # No match found inst is unique in the set
    return True


def get_unique_instructions(protocols):
    all_unique_orders = get_all_orders(protocols)
    all_unique_instructions = []
    indx = 0
    for order_name, order_element in all_unique_orders.items():
        # Get the protocol containing the current order_element
        protocol = [protocol for _, protocol in protocols.items()
                    if order_element in protocol[0].findall('order')][0]

        order_instructions = get_order_instructions(protocol, order_name)
        for inst in order_instructions:
            if inst_unique(all_unique_instructions, inst):
                inst['indx'] = indx
                all_unique_instructions.append(inst)
                indx += 1

    return all_unique_instructions


def find_plan_abbrev(protocol, order_name):
    # Look to see if there is a list of suggested plan abbreviations
    order = find_order(protocol, order_name)
    prefixes = None
    if order:
        raw_str = order.find('prefix').text
        raw_str.replace(", ", "")
        prefixes = list(set(raw_str.split(",")))
    return prefixes


def get_site_plan_names(protocol, order_name, plan_names):
    matches = {}
    top_picks = {}
    all_matches = OrderedDict()
    # Sort by suggested order name
    suggested_names = find_plan_abbrev(protocol, order_name)

    for n, d in plan_names.items():
        if d[0] == protocol[0].find('AnatomicGroup').text:
            if n in suggested_names:
                top_picks[n] = n + ': ' + d[1]
            else:
                matches[n] = n + ': ' + d[1]
    for k, v in top_picks.items():
        all_matches[k] = v
    for k, v in matches.items():
        all_matches[k] = v
    return all_matches




