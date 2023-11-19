import re
from PlanReview.review_definitions import ALERT, PASS


def determine_energy(energy_str):
    energy_regex = re.compile(r"Energy:\s?([^,]*)")
    energy_match = energy_regex.search(energy_str)
    if energy_match and energy_match.group(1).strip():
        # If there is some text before the comma, return it
        return f'Energy: {energy_match.group(1).strip()}'
    else:
        # If the field is empty or contains only whitespace
        return ''


def determine_iso_method(iso_str):
    # Regular expressions to extract the values for ISO_0, ROI, and POI
    iso_0_regex = re.compile(r"ISO_0':\s*'([^']*)'")
    roi_regex = re.compile(r"ROI':\s*'([^']*)'")
    poi_regex = re.compile(r"POI':\s*'([^']*)'")

    # Extract values
    iso_0_value = iso_0_regex.search(iso_str)
    roi_value = roi_regex.search(iso_str)
    poi_value = poi_regex.search(iso_str)

    # Check each key and return the method with its value
    if iso_0_value and iso_0_value.group(1):
        return f'Existing Isocenter: {iso_0_value.group(1)}'
    elif roi_value and roi_value.group(1):
        return f'Center of Roi: {roi_value.group(1)}'
    elif poi_value and poi_value.group(1):
        return f'At Poi: {poi_value.group(1)}'
    return ''


def extract_match(regex, text):
    """Helper function to extract match using regex."""
    match = re.search(regex, text)
    return match.group(1) if match else None


def parse_beamset_selection(rso, **kwargs):
    """
    Parse the log_messages for a specific beamset dialog and return the dialog choices as a dictionary.

    Args:
        rso (NamedTuple): A namedtuple containing the beamset.
        **kwargs: Additional keyword arguments. Options include:
            'LOG_MESSAGES' (Optional[list]): A list of log_messages to search through.

    Returns:
        tuple: A tuple containing the pass result and a message.
    """
    log_messages = kwargs.get('LOG_MESSAGES', [])
    beamset_name = rso.beamset.DicomPlanLabel
    beamset_id = rso.beamset.UniqueId

    # Regular expressions for parsing log messages
    regexes = {
        'Dialog': re.compile(r'Dialog:\s?Beamset Template Selection'),
        'Name': re.compile(r'TemplateName:\s?(.*?)(?=\s*,\t)'),
        'Isocenter': re.compile(r'Iso:\s?\{([^}]+)\}'),
        'Energy': re.compile(r'Energy:\s?(.*?)(?=,\t|$)')
    }

    # Default result setup
    pass_result = ALERT
    message = f'Beamset {beamset_name} not set by script'

    # Parsing log messages
    for log_line in log_messages:
        if 'Beamset Template Selection' in log_line['Message'] and \
                (beamset_name == log_line['Beamset'] or beamset_id in log_line['BeamsetID']):

            template_name = extract_match(regexes['Name'], log_line['Message'])
            iso_info = extract_match(regexes['Isocenter'], log_line['Message'])
            energy = extract_match(regexes['Energy'], log_line['Message'])

            if template_name:
                iso_method = determine_iso_method(iso_info)
                energy_string = determine_energy(energy)
                pass_result = PASS
                message = f'Template: {template_name}, Isocenter: {iso_method}, Energy: {energy_string}'

    return pass_result, message




