import logging
import os
import json
import pandas as pd
from docx import Document
from docx.table import Table
from docx.shared import Inches, Pt
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION, WD_ORIENTATION
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from PlanReview.review_definitions import (
    OUTPUT_DIR, UW_HEALTH_LOGO, REVIEW_LEVELS)
from PlanReview.utils import get_approval_info
from PlanReview.utils.constants import *

# Document set up
top_margin = 0.2  # (in) top page margin
bottom_margin = 0.2  # (in) bottom page margin
left_margin = 0.25  # (in) left page margin
right_margin = 0.2  # (in) right page margin
page_height = 8.5  # (in) overall page height
row_height = 0.35  # (in) row height
header_height = 0.1875  # (in) secondary header height
footer_height = 0.25  # (in) secondary footer height
table_header_height = 0.375  # (in) Table header row height
table_title_height = 0.25  # (in) Table title
table_spacing = 0.375  # (in) Table spacing
safety_margin = 0.0
# Less than this, use a page break instead of split
min_table_height = table_title_height + table_header_height + 1 * row_height


def set_section_dimensions_and_orientation(section):
    section.left_margin = Inches(left_margin)
    section.right_margin = Inches(right_margin)
    section.top_margin = Inches(top_margin)
    section.bottom_margin = Inches(bottom_margin)
    section.header_distance = Inches(top_margin)
    section.footer_distance = Inches(bottom_margin)
    # Change the orientation of the section to landscape
    section.orientation = WD_ORIENTATION.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width


def generate_doc(rso, tests, header_data, test_mode=False):
    if test_mode:
        tests = read_tests_from_json('tests.json')
        header_data = read_tests_from_json('header.json')
    else:
        dump_tests_to_json(tests, file_name='tests.json')
        dump_tests_to_json(header_data, file_name='header.json')
    tests_df = read_data(tests)
    # Output file
    file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.doc"
    output_file = os.path.join(OUTPUT_DIR, rso.patient.PatientID, file_name)

    # Get approval info:
    approval_status = get_approval_info(rso.plan, rso.beamset)
    if approval_status.beamset_approved:
        current_time = str(rso.beamset.Review.ReviewTime)
    else:
        current_time = 'NA'

    demographics = {
        'Name': rso.patient.Name,
        'MRN': rso.patient.PatientID,
        'Beamset Name': rso.beamset.DicomPlanLabel,
        'Approval Time': current_time}

    # Begin
    document = Document()
    section = document.sections[0]
    set_section_dimensions_and_orientation(section)
    # Add header
    add_page_header(section, rso, first_page=True)
    # Add empty footer to first page
    add_footer(section,rso,first_page=True)

    #
    # Begin body of document
    paragraph = document.add_paragraph()
    #
    # FIRST PAGE
    # Add Top Row Demographics
    table = document.add_table(rows=2, cols=4, style='Medium Grid 1 Accent 2')
    for index, k in enumerate(demographics):
        row_key = table.rows[0]
        row_value = table.rows[1]
        row_key.cells[index].text = k
        row_value.cells[index].text = demographics[k]
    # Add the front page data
    # add_simulation_data_table(document, header_data['-SIMULATION_DATA-'])
    #
    # add_treatment_instructions_table(document, header_data['-TREATMENT_INSTRUCTIONS-'])
    #
    document.add_paragraph('')  # Add spacing between sections
    add_beamset_data_table(document, header_data['-BEAMSET-'], rso)
    add_user_comment(document, header_data[KEY_USER_COMMENT])

    #
    # USER AND AUTOMATED CHECK PAGES
    document.add_page_break()
    document.add_section(WD_SECTION.NEW_PAGE)
    # Add empty second page header
    add_page_header(section, rso, first_page=False)
    # Add footer with patient demographics
    add_footer(section, rso, first_page=False)

    # Add the user checks and failed
    ## automated_passing = tests[KEY_AUTO_PASS]
    ## automated_failing = tests[KEY_AUTO_FAIL]

    available_page_height = get_usable_page()
    adjusted_page_height = available_page_height

    unique_test_levels = tests_df[KEY_OUT_TAB].unique()
    excluded_review_levels = (REVIEW_LEVELS['SANDBOX'])

    for test_level in unique_test_levels:
        if test_level in excluded_review_levels:
            continue  # Skip these test levels

        user_tl_df = tests_df[(tests_df[KEY_OUT_TEST_SOURCE] == SOURCE_USER)
                              & (tests_df[KEY_OUT_TAB] == test_level)]
        # TODO: Get the domain type and review tab in for the user checks
        # TODO: Get the result into the autotests
        fail_tl_df = tests_df[(tests_df[KEY_OUT_TEST_SOURCE] == SOURCE_AUTO)
                              & (tests_df[KEY_OUT_TAB] == test_level)]
        pass_tl_df = tests_df[(tests_df[KEY_OUT_TEST_SOURCE] == SOURCE_AUTO)
                              & (tests_df[KEY_OUT_TAB] == test_level)]

        adjusted_page_height = add_check_table(
            user_tl_df, document, adjusted_page_height,f'{test_level}')

        # Make the list of automated tests
        auto_df = pd.concat([fail_tl_df,pass_tl_df])

        # Add the automated tests
        if not auto_df.empty:
            title = f'{test_level} - Automated Checks'
            adjusted_page_height = add_check_table(
                auto_df, document, adjusted_page_height,title)

            # fails_df = tests_df[tests_df['Topic'] == KEY_AUTO_FAIL]
    #
    # for test_level in tests.keys():
    #     # TODO: Eliminate the automated keys?
    #     if all((test_level != KEY_AUTO_FAIL,
    #             test_level != KEY_AUTO_PASS,
    #             test_level != REVIEW_LEVELS['SANDBOX'])):
    #         adjusted_page_height = add_check_table(
    #             tests[test_level], document, adjusted_page_height,
    #             f'{test_level}')
    #         # Make the list of automated tests
    #         auto_list = []
    #         for fails in automated_failing:
    #             if fails[KEY_OUT_TAB] == test_level:
    #                 auto_list.append(fails)
    #         for passes in automated_passing:
    #            if passes[KEY_OUT_TAB] == test_level:
    #                auto_list.append(passes)
    #
    #         # Add the automated tests
    #         if auto_list:
    #            title = f'{test_level} - Automated Checks'
    #            adjusted_page_height = add_check_table(
    #                auto_list, document, adjusted_page_height, title, df=fails_df)
    document.save(output_file)
    print('Complete')


def get_usable_page():
    available_space = (page_height - top_margin - bottom_margin
                       - header_height - footer_height - safety_margin)
    return available_space


def estimate_table_length(number_of_rows: int) -> float:
    """
    Estimate the length of the table based on the number of rows and the
    height of each row.

    Args:
    number_of_rows (int): The number of rows in the table.

    Returns:
    float: The estimated length of the table in inches.
    """
    table_length = table_spacing + table_title_height \
                   + table_header_height + number_of_rows * row_height
    return table_length


def add_check_table(check_df, document, adjusted_page_height, title):
    available_page_height = get_usable_page()
    logging.debug(f'\n**** {title} ****')
    test1_df, test2_df = split_list(check_df, adjusted_page_height)
    if not test1_df.empty and not test2_df.empty:
        add_check_list_table(test1_df, document, title=f'{title}')
        table_length = estimate_table_length(len(test2_df))
        document.add_page_break()
        adjusted_page_height = available_page_height - table_length
        add_check_list_table(test2_df, document, title=f'{title} - Cont')
    elif not test2_df.empty:
        document.add_page_break()
        table_length = estimate_table_length(len(test2_df))
        adjusted_page_height = available_page_height - table_length
        add_check_list_table(test2_df, document, title=f'{title}')
    else:
        add_check_list_table(test1_df, document, title=f'{title}')
        table_length = estimate_table_length(len(test1_df))
        adjusted_page_height = adjusted_page_height - table_length
    return adjusted_page_height

def old_add_check_table(check_list, document, adjusted_page_height, title):
    available_page_height = get_usable_page()
    logging.debug(f'\n**** {title} ****')
    test1, test2 = split_list(check_list, adjusted_page_height)
    if test1 and test2:
        # This table will be split
        add_check_list_table(test1, document, title=f'{title}')
        # We will have a page break. So adjust space taken on next page.
        table_length = estimate_table_length(len(test2))
        document.add_page_break()
        adjusted_page_height = available_page_height - table_length
        add_check_list_table(test2, document, title=f'{title} - Cont')
    elif test2:
        # This table should be moved to the next page
        document.add_page_break()
        table_length = estimate_table_length(len(test2))
        adjusted_page_height = available_page_height - table_length
        add_check_list_table(test2, document, title=f'{title}')
    else:
        # This table will fit on the current page
        add_check_list_table(test1, document, title=f'{title}')
        table_length = estimate_table_length(len(test1))
        adjusted_page_height = adjusted_page_height - table_length
    return adjusted_page_height


def determine_doc_type(rso):
    planning_technique = rso.beamset.PlanGenerationTechnique
    delivery_technique = rso.beamset.DeliveryTechnique
    if delivery_technique == 'DynamicArc' and planning_technique == 'Conformal':
        header_text = 'Photon Conformal Arc'
    elif delivery_technique == 'DynamicArc' and planning_technique == 'Imrt':
        header_text = 'Photon VMAT'
    elif delivery_technique == 'ApplicatorAndCutout':
        header_text = 'Electron'
    elif delivery_technique == 'TomoHelical':
        if 'T3D' not in rso.beamset.DicomPlanLabel:
            header_text = 'TomoHelical'
        else:
            header_text = 'Tomo3D'
    elif delivery_technique == 'SMLC':
        if planning_technique == 'Imrt':
            header_text = 'Static Field IMRT'
        else:
            header_text = '3D'
    else:
        header_text = 'Unsupported Technique'
    header_text = header_text + ' Physics Review'
    return header_text


def add_page_header(section, rso, first_page=False):
    # Add header
    header = section.header
    header_paragraph = header.paragraphs[0]

    if first_page:
        # Add logo
        logo_width = 2.5
        logo_height = logo_width * 240 / 920
        logo_run = header_paragraph.add_run()
        _ = logo_run.add_picture(UW_HEALTH_LOGO,
                                 width=Inches(logo_width),
                                 height=Inches(logo_height))
        # Get document header title
        header_text = '\t' * 2 + determine_doc_type(rso)
    else:
        header.is_linked_to_previous = False
        header_text = ""
    header_run = header_paragraph.add_run()
    header_run.text = header_text
    header_run.style = "Heading 1 Char"


def add_footer(section, rso, first_page=False):
    demographics = {
        'Name': rso.patient.Name,
        'MRN': rso.patient.PatientID,
        'Beamset Name': rso.beamset.DicomPlanLabel, }
    if first_page:
        footer = section.footer
        footer_paragraph = footer.paragraphs[0]
        footer_run = footer_paragraph.add_run()
        footer_run.text = ""  # no footer content for first page
    else:
        footer = section.footer
        footer.is_linked_to_previous = False
        footer_paragraph = footer.paragraphs[0]
        footer_run = footer_paragraph.add_run()
        footer_run.text = "\t".join(
            [key + ':' + value for key, value in demographics.items()])
        footer_run.style = "Heading 4 Char"

def split_list(check_df, available_page):
    table_length = estimate_table_length(len(check_df))
    usable = get_usable_page()
    logging.debug(f'Page Available: {available_page:.2f}, '
                  f'and Table length: {table_length:.2f}')
    if table_length <= available_page:
        check_df_1 = check_df
        check_df_2 = pd.DataFrame()  # Empty DataFrame
    else:
        if available_page < min_table_height:
            check_df_1 = pd.DataFrame()  # Empty DataFrame
            check_df_2 = check_df
        else:
            check_df_1, check_df_2 = find_split(check_df, available_page)

    return check_df_1, check_df_2


def old_split_list(check_list, available_page):
    table_length = estimate_table_length(len(check_list))
    usable = get_usable_page()
    logging.debug(f'Page Available: {available_page:.2f}, '
                  f'and Table length: {table_length:.2f}')
    if table_length <= available_page:
        check_list_1 = check_list
        check_list_2 = []
        logging.debug(f'Only need table1 Len: {len(check_list_1)}')
    else:
        if available_page < min_table_height:
            check_list_1 = []
            check_list_2 = check_list
            logging.debug(f'Start table2 on next page Len: {len(check_list_2)}')
        else:
            check_list_1, check_list_2 = find_split(check_list, available_page)
            logging.debug(f'Split table Len: {len(check_list)} '
                          f'into table1 Len: {len(check_list_1)} and '
                          f'table2 Len: {len(check_list_2)}')

    return check_list_1, check_list_2


def find_split(check_df, space):
    i = 0
    table_length = estimate_table_length(len(check_df))
    while table_length > space:
        table_length = estimate_table_length(len(check_df) - i)
        i += 1
    check_df_1 = check_df.iloc[:len(check_df) - i]
    check_df_2 = check_df.iloc[len(check_df) - i:]
    return check_df_1, check_df_2

def old_find_split(check_list, space):
    i = 0
    table_length = estimate_table_length(len(check_list))
    while table_length > space:
        table_length = estimate_table_length(len(check_list) - i)
        i += 1
    check_list_1 = check_list[:len(check_list) - i]
    check_list_2 = check_list[len(check_list) - i:]
    return check_list_1, check_list_2


def add_check_list_table(df: pd.DataFrame, document: Document,
                         title: str = None) -> Table:
    """
    Adds a table to the document for the given check results. Page breaks are
    added only if the table does not fit on the current page.

    Args:
    check_results (list): List of check results to be added to the table.
    document (Document): The document to add the table to.
    title (str, optional): The title of the table. Defaults to None.

    Returns:
    Table: The created table.
    :type df: pd.Dataframe
    """
    # Set row height
    table_row_height = Inches(row_height)
    # Calculate estimated table length
    table_length = estimate_table_length(len(df))

    # Get page, header and footer sizes from the first section of the document
    # section = document.sections[0]
    # page_height = section.page_height.inches
    # top_margin = section.top_margin.inches
    # bottom_margin = section.bottom_margin.inches

    if title:
        table_title = document.add_paragraph()
        table_title.style = document.styles['Heading 1']
        table_title.add_run(title)

    # Calculate the available width for the table
    page_width = document.sections[-1].page_width.inches
    # left_margin = document.sections[-1].left_margin.inches
    # right_margin = document.sections[-1].right_margin.inches

    available_width = page_width - left_margin - right_margin - 0.5  # Subtract 0.5 inches for

    # Set the column widths (widths are in proportion to the amount of text)
    long_keys = [KEY_OUT_TEST, KEY_OUT_MESSAGE, KEY_OUT_COMMENT]
    # col_text_width = [max([len(check[key])
    #                        for check in check_results]) for key in long_keys]
    # total_text_width = sum(col_text_width)
#
#     col_widths = [0.5] + [(text_width / total_text_width) * available_width
#                           for text_width in col_text_width]
#
#     table_properties = {'NCOL': 4, 'WIDTH_COL': [
#         (i, Inches(w)) for i, w in enumerate(col_widths)]}
    # Determine the maximum length of text for each key
    col_text_width = [df[col].str.len().max() for col in long_keys]
    total_text_width = sum(col_text_width)

    # Calculate proportional column widths
    col_widths = [0.5] + [
        (text_width / total_text_width) * available_width
        for text_width in col_text_width
    ]

    table_properties = {'NCOL': 4, 'WIDTH_COL': [
        (i, Inches(w)) for i, w in enumerate(col_widths)
    ]}

    table = document.add_table(
        rows=1, cols=table_properties['NCOL'], style='Light Grid Accent 2')
    # Set the header attribute to True to repeat column headers
    table.header = True

    row = table.rows[0]
    row.height = table_row_height
    row.cells[0].text = 'Status'
    row.cells[1].text = 'Test Performed'
    row.cells[2].text = 'Result'
    row.cells[3].text = 'Reviewer Comment'
    i = 1
    for _, check in df.iterrows():
        table.add_row()
        row = table.rows[i]
        icon_paragraph = row.cells[0].paragraphs[0]
        icon_run = icon_paragraph.add_run()
        icon_run.add_picture(
            check[KEY_OUT_ICON], width=Inches(0.15), height=Inches(0.15))
        icon_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        row.cells[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        row.cells[1].text = check[KEY_OUT_TEST]
        row.cells[2].text = check[KEY_OUT_MESSAGE]
        row.cells[3].text = check[KEY_OUT_COMMENT]
        i += 1

        # i = 1
    # for check in check_results:
    #     table.add_row()
    #     row = table.rows[i]
    #     # Center the icon horizontally and vertically
    #     icon_paragraph = row.cells[0].paragraphs[0]
    #     icon_run = icon_paragraph.add_run()
    #     icon_run.add_picture(
    #         check[KEY_OUT_ICON], width=Inches(0.15), height=Inches(0.15))
    #     # Center horizontally
    #     icon_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    #     # Center vertically
    #     row.cells[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    #     row.cells[1].text = check[KEY_OUT_TEST]
    #     row.cells[2].text = check[KEY_OUT_MESSAGE]
    #     row.cells[3].text = check[KEY_OUT_COMMENT]
    #     i += 1

        # Set row height
        row.height = table_row_height

        for index, width in table_properties['WIDTH_COL']:
            if index < len(table.columns):  # Ensure the index is within the valid range
                for cell in table.columns[index].cells:
                    cell.width = width
                    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                    # Adjust font size and style for cell text
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(10)  # Set font size to 10pt
                            run.font.name = 'Arial'  # Set font to Arial

    return table


# Function to add a table row with given data
def add_table_row(table, data):
    row = table.add_row()
    for i, value in enumerate(data):
        row.cells[i].text = str(value)
        row.cells[i].paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER


def add_simulation_data_table(doc, data):
    simulation_table = doc.add_table(rows=1, cols=2)
    simulation_table.style = 'Table Grid'
    header_cells = simulation_table.rows[0].cells
    header_cells[0].text = 'Key'
    header_cells[1].text = 'Value'

    for key, value in data.items():
        add_table_row(simulation_table, (key, value))

    doc.add_paragraph('')  # Add spacing between sections


def add_user_comment(doc, data):
    comment_table = doc.add_table(rows=2, cols=1)
    comment_table.style = 'Light List Accent 2'
    comment_table.cell(0,0).text = 'User Comments'
    comment_table.cell(1,0).text = str(data[KEY_USER_COMMENT])


def add_treatment_instructions_table(doc, data):
    instructions_table = doc.add_table(rows=1, cols=3)
    instructions_table.style = 'Table Grid'
    header_cells = instructions_table.rows[0].cells
    header_cells[0].text = 'Radio Button State'
    header_cells[1].text = 'Selected Option'
    header_cells[2].text = 'Value'

    for key, value in data.items():
        if key[0].startswith('-INSTRUCTION--RADIO-'):
            radio_state = key[0].split('-')[-1]
            index = key[1]
            combo_key = ('-INSTRUCTION--COMBO-', index)
            input_text_key = ('-INSTRUCTION--INPUT-TEXT-', index)
            if combo_key in data:
                selected_option = data[combo_key]
            elif input_text_key in data:
                selected_option = data[input_text_key]
            else:
                selected_option = ''
            add_table_row(instructions_table,
                          (radio_state, selected_option, value))

    doc.add_paragraph('')  # Add spacing between sections


def add_beamset_data_table(doc, data, rso):
    logging.debug(f'Beamset keys {data.keys()}')
    beamset_count = data["-BEAMSET--COUNT-"]
    beamset_table = doc.add_table(rows=1, cols=2)
    beamset_table.style = 'Medium Grid 1 Accent 2'

    # Set the first column width to 1.5 inches
    for cell in beamset_table.column_cells(0):
        cell.width = Inches(1.5)

    # Set the headers for the main table
    header_cells = beamset_table.rows[0].cells
    header_cells[0].text = 'Beamset'
    header_cells[1].text = 'Beamset Details'

    # Loop through beamsets
    for i in range(beamset_count):
        beamset_number = ("-BEAMSET_SELECT-", i)
        beamset_name = data[beamset_number]
        row = beamset_table.add_row()
        row.cells[0].text = beamset_name

        # Add a nested table for beamset details
        nested_table = row.cells[1].add_table(rows=3, cols=2)
        nested_table.style = 'Medium Grid 2 Accent 2'

        # Add Number of Fractions row
        nested_table.cell(0, 0).text = "Number of Fractions"
        nested_table.cell(0, 1).text = str(data[("-BEAMSET--N_FRACTIONS-", i)])

        # Add Approval Status row
        approval_status = get_approval_info(
            rso.plan, rso.plan.BeamSets[beamset_name])
        if approval_status.beamset_approved:
            approval_date = str(
                rso.plan.BeamSets[beamset_name].Review.ReviewTime)
        else:
            approval_date = 'NA'
        nested_table.cell(1, 0).text = "Beamset Approval Date"
        nested_table.cell(1, 1).text = approval_date

        # Add Targets nested table
        targets_table = nested_table.cell(2, 1).add_table(rows=1, cols=3)
        targets_table.style = 'Medium Grid 2 Accent 2'

        # Set the headers for the targets table
        header_cells = targets_table.rows[0].cells
        header_cells[0].text = 'Target Name'
        header_cells[1].text = 'Dose per Fraction (Gy)'
        header_cells[2].text = 'Total Dose (Gy)'

        # Loop through targets
        target_count = data[("-BEAMSET--TARGET_COUNT-", i)]
        for j in range(target_count):
            target_name = data[("-BEAMSET--TARGET-NAME", i, j)]
            fraction_dose = data[("-BEAMSET--FRACTION-DOSE-", i, j)]
            total_dose = data[("-BEAMSET--DOSE-", i, j)]
            add_table_row(targets_table, (target_name,
                                          fraction_dose, total_dose))

    # Add spacing between sections
    doc.add_paragraph('')


def dump_tests_to_json(tests, file_name="tests.json"):
    full_path_file_name = os.path.join(OUTPUT_DIR, file_name)
    with open(full_path_file_name, 'w') as outfile:
        json.dump(tuple_key_to_str(tests), outfile)


def read_tests_from_json(file_name="tests.json"):
    full_path_file_name = os.path.join(OUTPUT_DIR, file_name)
    with open(full_path_file_name, 'r') as infile:
        tests = json.load(infile)
    tests = str_key_to_tuple(tests)
    return tests


#
# TODO: Optional export to pdf
# from docx2pdf import convert
# file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.docx"  # Change the file
# output_file = os.path.join(OUTPUT_DIR, file_name)
# pdf_file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.pdf"
# pdf_output_file = os.path.join(OUTPUT_DIR, pdf_file_name)
# document.save(output_file)  # Save the document as a DOCX file
# convert(output_file, pdf_output_file)  # Convert the DOCX file to a PDF file
# os.remove(output_file)  # Remove the DOCX file after conversion, if needed


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


def read_data(data):
    return pd.DataFrame(data)
def flatten_data(data):
    rows = []
    for topic, tests in data.items():
        for test in tests:
            row = {'Topic': topic}
            row.update(test)
            rows.append(row)
    return pd.DataFrame(rows)
