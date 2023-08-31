import re
import os
import connect
from collections import OrderedDict
from ...review_definitions import LOG_DIR, DEV_LOG_DIR, KEEP_PHRASES


def read_log_file(patient_id):
    """
    Read the lines from the patient log in both clinical and development
    locations
    Args:
        patient_id: str: contains patient ID

    Returns:
        file_contents: lines of file
    """
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
        connect.await_user_input(
            f"Neither file:{log_file} not found in dir:{LOG_DIR} "
            + f"nor file:{dev_log_file} not found in dir:{DEV_LOG_DIR} "
            + f"this is likely a major error. Proceed? "
        )

    return file_contents


def parse_log_file(lines, parent_key, phrases=KEEP_PHRASES):
    """
    Parse the log file lines for the phrase specified
    Args:
        parent_key: The top key for these log entries (typically patient level)
        lines: list of strings from a log file
        phrases: list of tuples
            (level,phrase):
                           level: is a string indicating pass level
                           phrase: is a string to identify lines for return

    Returns:
        message: list of lists of format: [parent key, key, value, result]

    Test Patient:
        Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, Log_Parse_Check
    """
    message = []
    time_stamp_exp = r'(^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(.*)'  # The
    # front timestamp
    re_c = r'^\t(Case: .*)\t'
    re_e = r'(Exam: .*)\t'
    re_p = r'(Plan: .*)\t'
    re_b = r'(Beamset: [^\t|\s]+)'  # Terminate after this level

    # Declare reg-ex for levels in the log file
    context_exps = OrderedDict()
    context_exps['Beamset'] = re_c + re_e + re_p + re_b
    context_exps['Plan'] = re_c + re_e + re_p
    context_exps['Exam'] = re_c + re_e
    context_exps['Case'] = re_c

    for p in phrases:
        key = 'Log' + p[1]
        message.append([parent_key, key, key, p[0]])
        re_phrase = p[1] + r'.*\.py: '

        for line in lines:
            if p[1] in line:
                # Remove the source python program from the line
                line = re.sub(re_phrase, '', line)

                # Sort the line into a part for the timestamp and one for
                # remainder
                parsed_l = [part for t in re.findall(time_stamp_exp, line) for
                            part in t]
                parsed_l[1] = parsed_l[
                    1].lstrip().rstrip()  # Remove front and back white space

                deepest_level = None
                for c, exp in context_exps.items():
                    if bool(re.search(exp, parsed_l[1])):
                        levels = OrderedDict()
                        deepest_level = c
                        for g in re.findall(exp, parsed_l[1])[0]:
                            lev_key, lev_val = re.split(': ', g, maxsplit=1)
                            levels[lev_key] = lev_val
                        parsed_l[1] = re.sub(exp, '', parsed_l[1])
                        parsed_l[0] += ' ' + deepest_level + ': ' + levels[
                            deepest_level]
                        break

                if not deepest_level:
                    parsed_l[1] = re.sub(r'\t', '', parsed_l[1])

                message.append([key, parsed_l[0], parsed_l[0], parsed_l[1]])

    return message


def retrieve_logs(rso, log_key):
    if not rso.patient:
        return None
    lines = read_log_file(patient_id=rso.patient.PatientID)
    message_logs = parse_log_file(lines=lines, parent_key=log_key[0],
                                  phrases=KEEP_PHRASES)
    return message_logs
