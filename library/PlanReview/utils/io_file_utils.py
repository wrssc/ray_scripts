import os
import glob
import re
from datetime import datetime
import json
from PlanReview.review_definitions import OUTPUT_DIR


def generate_filename():
    now = datetime.now()
    filename = now.strftime("%Y%m%d_%H%M%S")
    return filename


def generate_file_path(patient_output_dir, patient_output_prefix, file_suffix):
    return os.path.join(patient_output_dir, f"{patient_output_prefix}{file_suffix}")


def find_latest_files(patient_output_dir, file_prefix, file_suffixes):
    latest_files = {}
    datetime_pattern = re.compile(r'(\d{8})_(\d{6})')

    for suffix in file_suffixes:
        search_pattern = os.path.join(patient_output_dir, f"{file_prefix}*{suffix}")
        files = glob.glob(search_pattern)

        # Extract datetime from filenames and sort them
        sorted_files = sorted(
            files, key=lambda x: datetime.strptime(
                ''.join(datetime_pattern.findall(x)[0]), "%Y%m%d%H%M%S")
            if datetime_pattern.findall(x) else None,
            reverse=True
        )

        # Take the most recent file
        latest_files[suffix] = sorted_files[0] if sorted_files else None

    return latest_files.get("tests.json"), latest_files.get("header.json")


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