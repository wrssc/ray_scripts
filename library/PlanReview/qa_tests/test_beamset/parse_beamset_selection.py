import re


def parse_beamset_selection(beamset_name, messages):
    """
    Parse the messages for a specific beamset dialog and return the dialog
    choices as a dictionary.

    Args:
        beamset_name (str): The name of the beamset to look for in the messages.
        messages (list): A list of messages to search through.

    Returns:
        A dictionary containing the beamset template dialog choices.
    """

    # Define regular expressions to search for in the messages
    beamset_template_searches = {
        'Dialog': re.compile(r'(Dialog):\s?(Beamset Template Selection)'),
        'Name': re.compile(r'(TemplateName):\s?(.*)Iso'),
        'NameAlt': re.compile(r'(TemplateName):\s?([^\t]+)'),
        'Isocenter': re.compile(r'(Iso):\s?([^\t]+)'),
        'Energy': re.compile(r'(Energy):\s?([^\t]+)')
    }

    # Initialize the template_data dictionary with default values
    template_data = {
        'Beamset Template Selection': (
            None, 'Beamset {} not set by script'.format(beamset_name)),
        'Template Name': (None, ''),
        'Isocenter': (None, ''),
        'Energy': (None, '')
    }

    # Search through the messages for a beamset dialog matching the beamset name
    for message in messages:
        if re.search(beamset_template_searches['Dialog'],
                     message[3]) and beamset_name in message[1]:
            # Found a matching beamset dialog: extract the template information
            try:
                _, template_name = re.search(beamset_template_searches['Name'],
                                             message[3]).groups()
            except AttributeError:
                _, template_name = re.search(
                    beamset_template_searches['NameAlt'], message[3]).groups()
            _, iso_info = re.search(beamset_template_searches['Isocenter'],
                                    message[3]).groups()
            _, energy = re.search(beamset_template_searches['Energy'],
                                  message[3]).groups()

            # Update the template_data dictionary with the extracted information
            template_data['Beamset Template Selection'] = (None, message[1])
            template_data['Template Name'] = (None, template_name)
            # TODO: Replace with a parse on bracketed entries return
            #  placement method
            template_data['Isocenter'] = (None, iso_info)
            template_data['Energy'] = (None, energy)

    return template_data
