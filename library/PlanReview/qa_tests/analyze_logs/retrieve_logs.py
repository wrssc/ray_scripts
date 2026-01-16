import re
import os
import uuid
from collections import OrderedDict
from ...review_definitions import LOG_DIR, DEV_LOG_DIR, KEEP_PHRASES, DOMAIN_TYPE


def generate_unique_id():
    return str(uuid.uuid4())


def read_log_file(patient_id):
    """
    Read the lines from the patient log in both clinical and development
    locations
    Args:
        patient_id: str: contains patient ID

    Returns:
        file_contents: lines of file
    """
    from library.api.api_rs import import_raystation_api
    rs = import_raystation_api()
    log_file = f"{patient_id}.txt"
    log_input_file = os.path.join(LOG_DIR, patient_id, log_file)
    dev_log_file = f"{patient_id}.txt"
    dev_log_input_file = os.path.join(DEV_LOG_DIR, patient_id, dev_log_file)

    file_contents = []

    try:
        with open(log_input_file) as f:
            file_contents += f.readlines()
    except FileNotFoundError:
        pass

    try:
        with open(dev_log_input_file) as f:
            file_contents += f.readlines()
    except FileNotFoundError:
        pass

    if not file_contents:
        rs.await_user_input(
            f"Neither file:{log_file} not found in dir:{LOG_DIR} "
            + f"nor file:{dev_log_file} not found in dir:{DEV_LOG_DIR} "
            + f"this is likely a major error. Proceed? "
        )

    return file_contents


def extract_timestamp(line):
    """
    Extracts the date and time separately from a log line.

    Args:
        line (str): A line from the log file.

    Returns:
        tuple: A tuple containing the extracted date, time, and the remainder of the line.
    """
    timestamp_exp = r'(^\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})'
    match = re.search(timestamp_exp, line)
    if match:
        return match.group(1), match.group(2), line[match.end():].strip()
    else:
        return None, None, line


def extract_context(line, context_patterns):
    """
    Extracts the context based on provided patterns.

    Args:
        line (str): A line from the log file.
        context_patterns (OrderedDict): Patterns for context extraction.

    Returns:
        tuple: A tuple containing context, a dictionary of levels, and the match object.
    """
    for context, pattern in context_patterns.items():
        match = re.search(pattern, line)
        if match:
            context_data = match.groups()
            # Replace None with empty string
            context_data = [data if data is not None else '' for data in context_data]
            keys = ['Case', 'Exam', 'Plan', 'PlanID', 'Beamset', 'BeamsetID'] if context == 'Beamset' else ['Case', 'Exam', 'Plan']
            levels = dict(zip(keys, context_data))
            return context, levels, match
    return None, {}, None


def parse_log_file(lines, parent_key, phrases):
    """
    Parses the log file lines for specified phrases and extracts relevant information.

    Args:
        parent_key (str): The top key for these log entries, typically at the patient level.
        lines (list of str): List of strings from a log file.
        phrases (list of tuples): List of tuples (level, phrase) where:
                                  - level is a string indicating pass level,
                                  - phrase is a string to identify lines for return.

    Returns:
        list of lists: A list of lists, each in the format [parent key, key, value, result].
    """

    message = []
    context_patterns = OrderedDict({
        'Beamset': r'Case: (.*?)\s*(?:\t|\|)\s*Exam: (.*?)\s*(?:\t|\|)\s*Plan: (.*?)(?:\s*(?:\t|\|)\s*PlanId: (.*?))?(?:\s*(?:\t|\|)\s*)?Beamset: (.*?)(?:\s*(?:\t|\|)\s*BeamsetId: (.*?))?(?:\s*(?:\t|\|))',
        'Plan': r'Case: (.*?)\s*(?:\t|\|)\s*Exam: (.*?)\s*(?:\t|\|)\s*Plan: (.*?)',
        'Exam': r'Case: (.*?)\s*(?:\t|\|)\s*Exam: (.*?)',
        'Case': r'Case: (.*?)'
    })

    source_pattern = re.compile(r'([a-zA-Z0-9_]+\.py):')

    for level, phrase in phrases:
        phrase_pattern = re.compile(re.escape(phrase) + r'.*\.py: ')

        for line in lines:
            if phrase in line:
                message_dict = {
                    'Date': '',
                    'Time': '',
                    'Log_Level': 'Log'+phrase,
                    'Message': '',
                    'Deepest_Context': '',
                    'Case': '',
                    'Exam': '',
                    'Plan': '',
                    'Beamset': '',
                    'PlanID': '',
                    'BeamsetID': '',
                    'Source': '',
                }
                source_match = source_pattern.search(line)
                line = phrase_pattern.sub('', line)
                date, timestamp, remainder = extract_timestamp(line)
                if source_match:
                    message_dict['Source'] = source_match.group(1)
                if date:
                    message_dict['Date'] = date
                if timestamp:
                    message_dict['Time'] = timestamp

                context, levels, match = extract_context(remainder, context_patterns)
                if context:
                    message_dict['Deepest_Context'] = context
                    for key in message_dict.keys():
                        if key in levels.keys():
                            message_dict[key] = levels[key]
                    line_content = f"{remainder[len(match.group(0)):].strip()}" if match else remainder
                    message_dict['Message'] = line_content
                else:
                    line_content = re.sub(r'\t', '', remainder)
                    message_dict['Message'] = line_content
                # Key is the parent key, next entry is the child key,
                # third entry is displayed value in first column. Fourth
                message.append(message_dict)

    return message


def retrieve_logs(rso):
    """
    Retrieves the logs from the log file for the specified patient.
    :param rso: NamedTuple of ScriptObjects in Raystation [case,exam,plan,beamset,db]
    :return: list of lists: A list of lists, each in the format [parent key, key, value, result].
    """
    log_key = (DOMAIN_TYPE['LOG_KEY'], "Logging")
    if not rso.patient:
        return None
    lines = read_log_file(patient_id=rso.patient.PatientID)
    message_logs = parse_log_file(lines=lines, parent_key=log_key[0],
                                  phrases=KEEP_PHRASES)
    return message_logs
