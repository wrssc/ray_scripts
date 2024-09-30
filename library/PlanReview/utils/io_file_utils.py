import os
import glob
import re
import logging
import PySimpleGUI as Sg
from datetime import datetime
import json
from PlanReview.review_definitions import OUTPUT_DIR, DATAFILE_EVENT_LIST
from PlanReview.utils.python_utilities import clean_string, OperationCancelledException
import time
import csv


def generate_filename():
    now = datetime.now()
    filename = now.strftime("%Y%m%d_%H%M%S")
    return filename


def generate_file_path(patient_output_dir, patient_output_prefix, file_suffix):
    return os.path.join(patient_output_dir, f"{patient_output_prefix}{file_suffix}")


def find_latest_file(patient_output_dir, patient_id, beamset_name, file_suffix):
    datetime_pattern = re.compile(r'(\d{8})_(\d{6})')

    search_pattern = os.path.join(patient_output_dir, f"{patient_id}_{beamset_name}_*_{file_suffix}")
    files = glob.glob(search_pattern)

    # Extract datetime from filenames and sort them
    sorted_files = sorted(
        files,
        key=lambda x: datetime.strptime(
            ''.join(datetime_pattern.findall(x)[0]), "%Y%m%d%H%M%S"
        ) if datetime_pattern.findall(x) else None,
        reverse=True
    )

    # Take the most recent file
    return sorted_files[0] if sorted_files else None


def dump_tests_to_json(tests, file_names=None):
    if file_names is None:
        file_names = []
    for f in file_names:
        with open(f, 'w') as outfile:
            json.dump(tuple_key_to_str(tests), outfile)


def read_tests_from_json(file_name="tests.json"):
    full_path_file_name = os.path.join(OUTPUT_DIR, file_name)
    with open(full_path_file_name, 'r') as infile:
        tests = json.load(infile)
    tests = str_key_to_tuple(tests)
    return tests


def tuple_key_to_str(value):
    if isinstance(value, dict):
        return {tuple_key_to_str(k): tuple_key_to_str(v) for k, v in value.items()}
    elif isinstance(value, tuple):
        return '||'.join(map(str, value))
    return value


def str_key_to_tuple(value):
    if isinstance(value, dict):
        return {str_key_to_tuple(k): str_key_to_tuple(v) for k, v in value.items()}
    elif isinstance(value, str) and '||' in value:
        return tuple(int(x) if x.isdigit() else x for x in value.split('||'))
    return value


def save_review(rso, values, suffix="_review.json", quiet=False):
    patient_output_dir = os.path.join(OUTPUT_DIR, rso.patient.PatientID)
    if not os.path.exists(patient_output_dir):
        os.makedirs(patient_output_dir)
    if os.path.exists(OUTPUT_DIR):
        file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}{suffix}"
        with open(os.path.join(patient_output_dir, file_name), "w") as f:
            json.dump(tuple_key_to_str(values), f)
            if not quiet:
                Sg.popup("Review saved successfully!")
        return file_name
    else:
        logging.error("Output directory does not exist.")
        return None


def append_to_csv(patient_id, beamset_name, user_name,
                  user_comments, dose_comments, is_physics_revision, is_dose_revision, is_dose_qi, is_physics_qi,
                  qi_comments=None, dose_qi_comments=None,
                  revision_number=None, revision_comments=None, dose_revision_comments=None):
    """
    Append a new incident report to a CSV file. If the file does not exist, create it and add headers.

    Args:
        patient_id (str): The patient ID.
        beamset_name (str): The name of the beamset.
        user_name (str): The name of the user.
        user_comments (str): The user's comments in the comment box.
        dose_comments (str): The user's comments in the dosimetry comment box.
        is_physics_revision (bool): Indicates if it is a physics revision.
        is_dose_revision (bool): Indicates if it is a dose revision.
        is_dose_qi (bool): Indicates if it is a dose QI.
        is_physics_qi (bool): Indicates if it is a physics QI.
        qi_comments (str): The comments in the QI proceed box.
        dose_qi_comments (str): The comments in the dosimetry QI box.
        revision_comments (str): The comments in the revision box.
        revision_number (str): The revision number indicated by the dosimetrist.
        dose_revision_comments (str): The comments in the dosimetry revision box.

    Returns:
        None
    """
    # Get the current time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Prepare the row data
    # Before writing we need to strip anything that will cause a line break or formatting issues
    row = [patient_id, beamset_name, user_name, current_time,
           is_physics_revision, is_dose_revision, is_dose_qi, is_physics_qi,
           clean_string(user_comments), clean_string(dose_comments),
           clean_string(qi_comments), clean_string(dose_qi_comments),
           revision_number, clean_string(revision_comments), clean_string(dose_revision_comments)]

    # Load file path
    csv_file_path = DATAFILE_EVENT_LIST

    # Check if the file exists
    file_exists = os.path.isfile(csv_file_path)

    while True:
        try:
            with open(csv_file_path, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists:
                    header = ['Patient Id', 'Beamset Name', 'User Name', 'Time',
                              'Is Physics Revision', 'Is Dose Revision', 'Is Dose QI', 'Is Physics QI', 'User Comments',
                              'QI Comments', 'Dosimetry QI Comments', 'Revision Number', 'Revision Comments',
                              'Dosimetry Revision Comments']
                    writer.writerow(header)
                    file_exists = True
                writer.writerow(row)
            Sg.popup('Data successfully written to the CSV file.')
            break
        except PermissionError:
            choice = Sg.popup_yes_no(f'Permission Error: The CSV file {csv_file_path} is open in another application.\n'
                                     'Please close the file and click "Yes" to retry, or "No" to cancel.',
                                     title='File In Use')
            if choice == 'Yes':
                time.sleep(1)
                continue
            else:
                raise OperationCancelledException('Operation cancelled by user.')
        except Exception as e:
            Sg.popup_error(f'An unexpected error occurred: {e}')
            break

