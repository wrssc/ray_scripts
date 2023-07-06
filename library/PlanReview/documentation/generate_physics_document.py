import logging
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION, WD_ORIENTATION
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from PlanReview.review_definitions import OUTPUT_DIR, UW_HEALTH_LOGO
from PlanReview.utils import get_approval_info
import json


def generate_doc(rso, tests, header_data, test_mode=False):
    if test_mode:
        tests = read_tests_from_json('tests.json')
        header_data = read_tests_from_json('header.json')
    else:
        dump_tests_to_json(tests, file_name='tests.json')
        dump_tests_to_json(header_data, file_name='header.json')
    # logging.debug(f'Header data is {json.dumps(tuple_key_to_str(header_data))}\n\n')
    # Output file
    file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.doc"
    output_file = os.path.join(OUTPUT_DIR,rso.patient.PatientID,file_name)

    footer_text = "Photon VMAT Physics Review"
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
    # Document set up
    top_margin = 0.2
    bottom_margin = 0.2
    left_margin = 0.2
    right_margin = 0.2

    # Begin
    document = Document()
    section = document.sections[0]
    section.left_margin = Inches(left_margin)
    section.right_margin = Inches(right_margin)
    section.top_margin = Inches(top_margin)
    section.bottom_margin = Inches(bottom_margin)

    # Change the orientation of the section to landscape
    section.orientation = WD_ORIENTATION.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    # Add header
    header = section.header
    paragraph = header.paragraphs[0]
    # Add logo
    logo_width = 2.5
    logo_height = logo_width * 240/920
    logo_run = paragraph.add_run()
    logo_shape = logo_run.add_picture(UW_HEALTH_LOGO,
                                      width=Inches(logo_width),
                                      height=Inches(logo_height))

    # Add footer_text
    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_run = footer_paragraph.add_run()
    footer_run.text = footer_text
    footer_run.style = "Heading 1 Char"
    #
    # Begin body of document
    paragraph = document.add_paragraph()
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
    # Add the user checks and failed
    for test_level in tests.keys():
        # Create a new section for the test level
        if document.paragraphs:
            document.add_page_break()
            document.add_section(WD_SECTION.NEW_PAGE)

        section = document.sections[-1]

        # Use the single-column table function here
        add_check_list_table_single(
            tests[test_level], document, title=test_level)

    document.save(output_file)
    print('Complete')


def add_check_list_table_single(check_results, document, title=None):
    # Add table title if provided
    if title:
        table_title = document.add_paragraph()
        table_title.style = document.styles['Title']
        table_title.add_run(title)

    # Calculate the available width for the table
    page_width = document.sections[-1].page_width.inches
    left_margin = document.sections[-1].left_margin.inches
    right_margin = document.sections[-1].right_margin.inches
    available_width = page_width - left_margin - \
        right_margin - 0.5  # Subtract 0.5 inches for
    # the first column

    # Set the column widths (widths are in proportion to the amount of text)
    long_keys = ['test_name', 'result', 'comment']
    col_text_width = [max([len(check[key])
                          for check in check_results]) for key in long_keys]
    total_text_width = sum(col_text_width)
    for check in check_results:
        logging.debug(
            f'{check["test_name"]}, {check["result"]}, {check["comment"]}')
        logging.debug(f'Col width, {len(check["test_name"])},'
                      f'{len(check["result"])}'
                      f'{len(check["comment"])}'
                      )

    col_widths = [0.5] + [(text_width / total_text_width) * available_width
                          for text_width in col_text_width]

    table_properties = {'NCOL': 4, 'WIDTH_COL': [
        (i, Inches(w)) for i, w in enumerate(col_widths)]}

    table = document.add_table(
        rows=1, cols=table_properties['NCOL'], style='Light Grid Accent 2')
    # Set the header attribute to True to repeat column headers
    table.header = True

    # Set row height
    row_height = Inches(0.315)

    row = table.rows[0]
    row.cells[0].text = 'Status'
    row.cells[1].text = 'Test Performed'
    row.cells[2].text = 'Result'
    row.cells[3].text = 'Reviewer Comment'
    i = 1
    for check in check_results:
        table.add_row()
        row = table.rows[i]
        # Center the icon horizontally and vertically
        icon_paragraph = row.cells[0].paragraphs[0]
        icon_run = icon_paragraph.add_run()
        icon_run.add_picture(
            check['icon'], width=Inches(0.15), height=Inches(0.15))
        # Center horizontally
        icon_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        # Center vertically
        row.cells[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        row.cells[1].text = check['test_name']
        row.cells[2].text = check['result']
        row.cells[3].text = check['comment']
        i += 1

        # Set row height
        row.height = row_height

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
#  from docx2pdf import convert
#  file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.docx"  # Change the file
#  output_file = os.path.join(OUTPUT_DIR, file_name)
#  pdf_file_name = f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}.pdf"
#  pdf_output_file = os.path.join(OUTPUT_DIR, pdf_file_name)
#  document.save(output_file)  # Save the document as a DOCX file
#  convert(output_file, pdf_output_file)  # Convert the DOCX file to a PDF file
#  os.remove(output_file)  # Remove the DOCX file after conversion, if needed


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
