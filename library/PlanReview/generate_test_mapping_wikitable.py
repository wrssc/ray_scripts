""" Wikitable for physics review

    Provides a wiki table for all automated tests

"""
import os
import sys
import pandas as pd
import re
import ast
from pathlib import Path
from typing import Tuple, Optional
sys.path.insert(1, os.path.join(os.path.dirname(__file__), '.'))
import PlanReview
import PlanReview.review_definitions as review_definitions
from PlanReview.utils.constants import (
    KEY_REVIEW_TYPE, KEY_AUTOMATED_TESTS, KEY_STATUS, KEY_OUT_TEST,
    KEY_AUTOMATION, KEY_OUT_DESC, KEY_AUTO_REVIEW_DATE,)


def parse_file_header(file_path: str) -> Tuple[str, str, str, str, str]:
    test_name = ""
    test_desc = ""
    test_pass_patient = ""
    test_fail_patient = ""
    test_pseudocode = ""

    target_function = Path(file_path).stem  # Get the target function name from the file name

    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == target_function:
            docstring = ast.get_docstring(node)
            if docstring:
                lines = docstring.split("\n")
                test_name = lines[0].strip()
                test_desc = lines[1].strip()

                # Extract Pseudocode
                pseudocode_lines = []
                capturing = False
                for line in lines:
                    if "Pseudocode:" in line:
                        capturing = True
                        continue
                    if capturing and line.strip():
                        pseudocode_lines.append(line.strip())
                    elif capturing and not line.strip():
                        capturing = False
                test_pseudocode = "\n".join(pseudocode_lines)

                # Extract Test Patients
                for i, line in enumerate(lines):
                    if "Test Patients:" in line:
                        test_pass_patient = lines[i + 1].split(":")[1].strip()
                        test_fail_patient = lines[i + 2].split(":")[1].strip()

    return test_name, test_desc, test_pass_patient, test_fail_patient, test_pseudocode


# Modified create_table function for points 2, 3, 4
def create_table_data(review_levels_list, automated_tests_folder, key_replaced, key_out_desc):
    data = []
    for review_levels_dict in review_levels_list:
        for review_level, manual_tests in review_levels_dict.items():
            if type(manual_tests) == list:
                for manual_test in manual_tests:
                    if key_replaced in manual_test:
                        if KEY_AUTOMATED_TESTS in manual_test[key_replaced]:
                            print('Key replaced found')
                            automation_dict = manual_test[key_replaced]
                            if automation_dict:
                                replaced_file_paths = [Path(automated_tests_folder) / test.replace('.', '/') for test in
                                                       automation_dict[KEY_AUTOMATED_TESTS]]

                                for replaced_file_path in replaced_file_paths:
                                    replaced_file_path = Path(str(replaced_file_path) + '.py')
                                    if replaced_file_path.exists():
                                        test_name, test_desc, test_pass_patient, test_fail_patient, test_pseudocode = parse_file_header(
                                            replaced_file_path)
                                        row = {
                                            'Automated_Test': replaced_file_path.name,
                                            # 'Automated_Test': replaced_file_path.name.split('.')[0],
                                            'Manual_Test': manual_test[key_out_desc],
                                            KEY_OUT_TEST: manual_test.get(KEY_OUT_TEST, 'NA'),  # Point 3
                                            KEY_REVIEW_TYPE: review_levels_dict.get(KEY_REVIEW_TYPE, 'NA'),  # Point 4
                                            KEY_STATUS: automation_dict.get(KEY_STATUS, 'None'),  # Point 4
                                            KEY_AUTO_REVIEW_DATE: automation_dict.get(KEY_AUTO_REVIEW_DATE, 'NA'),  # Point 4
                                            'Test_Name': test_name,
                                            'Description': test_desc,
                                            'Passing_Patient': test_pass_patient,
                                            'Failing_Patient': test_fail_patient,
                                            'Pseudocode': test_pseudocode,
                                        }
                                        data.append(row)
    if data:
        tables = pd.DataFrame(data)

    return tables


def sanitize_wiki_text(text):
    text = text.replace("•", "*")  # Replace bullets
    text = re.sub(r'\d+\.', '#', text)  # Replace numbered list items
    return text


def write_wikitable(df, output_file_path, table_title: Optional[str] = ""):
    with open(output_file_path, 'a') as f:  # Changed mode to 'a' for appending
        if table_title:
            f.write(f"=== {table_title} ===\n")
        f.write('{| class="wikitable sortable"\n')

        # Specifying column headers directly
        f.write("! Automated Test !! Automated Test File !! Manual Test "
                "!! Description !! Passing_Patient !! Failing_Patient "
                "!! Pseudocode !! Review Type !! Test Status !! "
                "Test Review Date\n")

        for _, row in df.iterrows():
            sanitized_desc = sanitize_wiki_text(row['Description'])
            sanitized_pseudocode = sanitize_wiki_text(row['Pseudocode'])

            # Writing the rows directly with new columns
            f.write(
                f"|-\n| {row['Test_Name']} || {row['Automated_Test']} || {row['Manual_Test']} || {sanitized_desc} || "
                f"{row['Passing_Patient']} || {row['Failing_Patient']} || \n{sanitized_pseudocode}\n || "
                f"{row[KEY_REVIEW_TYPE]} || {row[KEY_STATUS]} || {row[KEY_AUTO_REVIEW_DATE]}\n")

        f.write("|}\n\n")  # Added an extra newline for separation


def generate_test_mapping_wikitable():
    # Your manual tests from review_definitions.py
    dict_names = []
    for attribute_name in dir(review_definitions):
        attribute = getattr(review_definitions, attribute_name)
        if isinstance(attribute, dict) and KEY_REVIEW_TYPE in attribute:
            dict_names.append(attribute)

    plan_review_dir = Path(PlanReview.__path__[0])

    # Define the folder where automated test Python files are kept, relative to PlanReview_V0_BetaTesting
    AUTOMATED_TESTS_FOLDER = plan_review_dir
    # Define the output file path
    OUTPUT_FILE_PATH = os.path.join(review_definitions.OUTPUT_DIR, 'output_wikitable.txt')
    # Clear existing file content
    open(OUTPUT_FILE_PATH, 'w').close()

    # Create DataFrame
    df = create_table_data(dict_names, AUTOMATED_TESTS_FOLDER, KEY_AUTOMATION,
                      KEY_OUT_DESC)

    # Filtering DataFrames based on KEY_REVIEW_TYPE
    physics_df = df[df[KEY_REVIEW_TYPE].str.contains("Physics")]
    dosimetry_df = df[df[KEY_REVIEW_TYPE].str.contains("Dosimetry")]

    # Writing Physics table
    write_wikitable(physics_df, OUTPUT_FILE_PATH, table_title="Physics Review")

    # Writing Dosimetry table
    write_wikitable(dosimetry_df, OUTPUT_FILE_PATH, table_title="Dosimetry Review")
