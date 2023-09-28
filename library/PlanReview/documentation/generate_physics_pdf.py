import os
from dataclasses import dataclass
from functools import partial
import json
import pandas as pd
from PlanReview.review_definitions import (
    OUTPUT_DIR, LOG_DIR, UW_HEALTH_LOGO, REVIEW_LEVELS, FAIL, PASS, ALERT, RED_CIRCLE,
    GREEN_CIRCLE)
from PlanReview.utils import get_approval_info
from PlanReview.utils.constants import (
    KEY_BEAMSET, KEY_SIDE_PANEL, KEY_OUT_DOMAIN_NAME, KEY_OUT_TEST_SOURCE, SOURCE_USER, KEY_USER_COMMENT,
    KEY_OUT_TAB, KEY_OUT_RESULT, SOURCE_AUTO, KEY_OUT_DESC, KEY_OUT_MESSAGE, KEY_OUT_COMMENT, KEY_OUT_ICON,
    KEY_PROCEED_REVISE, KEY_REVISION_INFO, KEY_BEAMSET_COUNT, KEY_BEAMSET_SELECT, KEY_BEAMSET_FRACTION_COUNT,
    KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE, KEY_BEAMSET_FRACTION_DOSE, KEY_BEAMSET_TARGET_COUNT,
)
from PlanReview.utils.io_file_utils import *
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle, Image
from reportlab.platypus import (SimpleDocTemplate,PageTemplate, Frame, PageBreak, Paragraph)
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def hex_to_reportlab_color(hex_color):
    # Remove any '#' at the beginning if present
    hex_color = hex_color.lstrip('#')

    # Convert the hexadecimal color code to RGB values
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    # Create a ReportLab color object using RGB values
    reportlab_color = colors.Color(r, g, b)

    return reportlab_color


@dataclass
class ReportConfig:
    TOP_MARGIN = 0.25 * inch
    BOTTOM_MARGIN = 0.25 * inch
    LEFT_MARGIN = 0.6 * inch
    RIGHT_MARGIN = 0.2 * inch
    PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)
    ROW_HEIGHT = 0.375 * inch
    TABLE_HEADER_HEIGHT = 0.375 * inch
    TABLE_TITLE_HEIGHT = 0.25 * inch
    TABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN #- 0.2 * inch
    UW_RED = hex_to_reportlab_color("#c5050c")
    UW_DARK_RED = hex_to_reportlab_color("#9b0000")
    UW_WHITE = hex_to_reportlab_color("#f7f7f7")
    UW_GRAY = hex_to_reportlab_color("#dadfe1")
    UW_DARK_GRAY = hex_to_reportlab_color("#282728")
    UW_TEXT = hex_to_reportlab_color("#333333")


def myFirstPage(canvas, doc,rso):
    canvas.saveState()
    logo_width = 2.5 * inch
    logo_height = logo_width * 240 / 920
    logo_image = Image(UW_HEALTH_LOGO, width=logo_width, height=logo_height)
    logo_image.drawOn(canvas, doc.leftMargin, doc.height - logo_height)

    # Get document header title
    header_text = determine_doc_type(rso)
    # Move the text to the right (adjust the X-coordinate)
    header_text_x = doc.leftMargin + logo_width + 30  # Horizontal Adjust
    header_text_y = doc.height - logo_height // 1.5

    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(header_text_x, header_text_y, header_text)
    canvas.restoreState()

def myLaterPages(canvas, doc,rso):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    demographics = {
        'Name': rso.patient.Name,
        'MRN': rso.patient.PatientID,
        'Beamset Name': rso.beamset.DicomPlanLabel,
    }
    footer_text = "  ".join([f"{key}: {value}" for key, value in demographics.items()])
    footer_text_x = doc.leftMargin
    footer_text_y = doc.bottomMargin-2
    canvas.drawString(footer_text_x, footer_text_y, footer_text)
    # canvas.drawString(inch, 0.75 * inch, f"Page {doc.page}")
    canvas.restoreState()


def generate_pdf(rso, tests, header_data, test_mode=False):
    config = ReportConfig()
    physics_review_dir = os.path.join(LOG_DIR, "PhysicsReviews")
    patient_output_dir = os.path.join(OUTPUT_DIR, rso.patient.PatientID)
    alt_patient_output_dir = r"Q:\\RadOnc\RayStation\Reports\PhysicsReviewBetaOnly"
    patient_output_prefix = f"{rso.patient.PatientID}_" \
                            f"{rso.beamset.DicomPlanLabel}_" \
                            f"{generate_filename()}"

    if test_mode:
        latest_test_file, latest_header_file = find_latest_files(
            patient_output_dir, f"{rso.patient.PatientID}_{rso.beamset.DicomPlanLabel}_",
            ["tests.json", "header.json"])
        tests = read_tests_from_json(latest_test_file) if latest_test_file else None
        header_data = read_tests_from_json(latest_header_file) if latest_header_file else None
    else:
        test_files = [
            generate_file_path(
                patient_output_dir, patient_output_prefix, "_tests.json"),
            generate_file_path(
                physics_review_dir, patient_output_prefix, "_tests.json")
        ]
        header_files = [
            generate_file_path(
                patient_output_dir, patient_output_prefix, "_header.json"),
            generate_file_path(
                physics_review_dir, patient_output_prefix, "_header.json")
        ]
        dump_tests_to_json(tests, file_names=test_files)
        dump_tests_to_json(header_data, file_names=header_files)

    tests_df = read_data(tests)

    # Output file
    output_file = generate_file_path(
        patient_output_dir, patient_output_prefix, ".pdf")
    beta_output_file = generate_file_path(
        alt_patient_output_dir, patient_output_prefix, ".pdf"
    )

    # Create a PDF document
    pdf_filename = beta_output_file
    doc = SimpleDocTemplate(pdf_filename,
                            pagesize=(config.PAGE_WIDTH, config.PAGE_HEIGHT),
                            topMargin=config.TOP_MARGIN,
                            bottomMargin=config.BOTTOM_MARGIN,
                            leftMargin=config.LEFT_MARGIN,
                            rightMagin=config.RIGHT_MARGIN)

    # Create a custom PageTemplate for the header and footer
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width,
                  doc.height - 0.75 * inch, id='header')
    footer_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width,
                  doc.height, id='footer')

    # Use functools.partial to create a partially applied function with custom data (rso)
    first_page_template = PageTemplate(id='first', frames=[frame],
                                       onPage=partial(myFirstPage,rso=rso))
    later_page_template = PageTemplate(frames=[footer_frame], id="laterPages",
                                       onPage=partial(myLaterPages,rso=rso))
    # Add the template to the document
    doc.addPageTemplates([first_page_template,later_page_template])

    # Create a list to store flowables (elements that go into the PDF)
    story = []

    # Create a table and apply the custom style
    main_table = create_beamset_data_table(header_data[KEY_BEAMSET], rso, config)
    story.append(main_table)
    # story.append(Spacer(1, 12))  # Add space between sections
    story.append(PageBreak())

    # Add table using add_check_list_table function
    checklist_tables = generate_tables_from_dataframe(tests_df, story, config)  # Pass centered_frame
    for table in checklist_tables:
        story.append(table)

    # Build the PDF document
    doc.build(story,onFirstPage=partial(myFirstPage,rso=rso),
              onLaterPages=partial(myLaterPages,rso=rso))


def read_data(data):
    return pd.DataFrame(data)


def str_key_to_tuple(value):
    if isinstance(value, dict):
        return {str_key_to_tuple(k): str_key_to_tuple(v) for k, v in value.items()}
    elif isinstance(value, str) and '||' in value:
        return tuple(int(x) if x.isdigit() else x for x in value.split('||'))
    return value


def generate_tables_from_dataframe(df, story, config):
    tables = []
    #
    excluded_review_levels = (REVIEW_LEVELS['SANDBOX'])
    # Define custom ordering for 'RESULT'
    result_order = {FAIL: 0, ALERT: 1, PASS: 2}
    unique_test_levels = df[KEY_OUT_TAB].unique()

    for test_level in unique_test_levels:
        if test_level in excluded_review_levels:
            continue  # Don't include these test levels in the report

        # Put in the user-entered data
        user_tl_df = df[(df[KEY_OUT_TEST_SOURCE] == SOURCE_USER)
                        & (df[KEY_OUT_TAB] == test_level)].copy()
        # Sort DataFrame based on custom ordering
        user_tl_df['sort_key'] = user_tl_df[KEY_OUT_RESULT].map(result_order)
        user_tl_df.sort_values(by='sort_key', inplace=True)

        # Add the manual check table
        tables.append(
            add_check_list_table(user_tl_df, story, config, title=f'{test_level}'))

        # Auto Checks
        # Find all automated checks from source
        auto_tl_df = df[(df[KEY_OUT_TEST_SOURCE] == SOURCE_AUTO)
                        & (df[KEY_OUT_TAB] == test_level)].copy()
        # Map the 'RESULT' values to the custom order and create a new column for sorting
        auto_tl_df['sort_key_result'] = auto_tl_df[KEY_OUT_RESULT].map(result_order)

        # Sort the DataFrame by 'KEY_OUT_DOMAIN_NAME' and the custom order
        auto_tl_df.sort_values(by=[KEY_OUT_DOMAIN_NAME, 'sort_key_result'], inplace=True)

        # Drop the temporary sorting column
        auto_tl_df.drop('sort_key_result', axis=1, inplace=True)

        # Add the automated tests
        if not auto_tl_df.empty:
            title = f'{test_level} - Automated Checks'
            tables.append(
            add_check_list_table(auto_tl_df, story, config, title=f'{title}'))
            # story.append(PageBreak())  # Add a page break between sections
    return tables

def calculate_column_widths(df, headers):
    """
    Calculate the fractional width of each column based on the longest content in each column
    while ensuring that each column is at least wide enough to accommodate its header.

    Args:
    df (pd.DataFrame): The DataFrame containing the data.
    headers (list): A list of column headers.

    Returns:
    list: A list of fractional widths for each column.
    """
    column_widths = []
    max_overall = 0
    for header in headers:
        if df[header].astype(str).apply(len).max() > max_overall:
            max_overall = df[header].astype(str).apply(len).max()

    for header in headers:
        # Find the maximum length in each column (excluding header)
        max_length = df[header].astype(str).apply(len).max()
        # Compare the maximum content length with the header length
        width = max(max_length, len(header), 0.1 * max_overall)
        column_widths.append(width)

    # Normalize the column widths to sum up to 1.0
    total_width = sum(column_widths)
    column_widths = [width / total_width for width in column_widths]

    return column_widths


def make_paragraph(text, style=None):
    if not style:
        style = getSampleStyleSheet()['Normal']
    return Paragraph(text, style)


def add_check_list_table(df, story, config, title=None):
    # Define table styles
    style = getSampleStyleSheet()
    label_style = getSampleStyleSheet()['Heading6']
    label_style.textColor = config.UW_WHITE
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_GRAY),
        ('BACKGROUND', (0, 1), (-1, 1), config.UW_DARK_RED),
        ('TEXTCOLOR', (0, 0), (-1, 1), config.UW_WHITE),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('SPAN', (0,0),(-1,0)),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 1), (0, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.25, config.UW_DARK_GRAY),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [config.UW_GRAY, config.UW_WHITE]),
        ('ROUNDEDCORNERS',[2, 2, 2, 2]),
        ('VALIGN', (0,0), (-1,-1),'MIDDLE'),
        #('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ])

    # Create a table data list
    data = [[title,"", "", ""],
            [make_paragraph('Status', style=label_style),
             make_paragraph('Test Performed', style=label_style),
             make_paragraph('Result', style=label_style),
             make_paragraph('Reviewer Comment', style=label_style)]]

    for _, check in df.iterrows():
        icon_image = Image(check[KEY_OUT_ICON],  ## width=0.18 * inch, height=0.18 * inch,
                           hAlign="CENTER", lazy=1)
        desc_paragraph = make_paragraph(check[KEY_OUT_DESC])
        message_paragraph = make_paragraph(check[KEY_OUT_MESSAGE])
        comment_paragraph = make_paragraph(check[KEY_OUT_COMMENT])

        data.append([icon_image, desc_paragraph, message_paragraph, comment_paragraph])

    cols = calculate_column_widths(df, [KEY_OUT_DESC, KEY_OUT_MESSAGE, KEY_OUT_COMMENT])
    # Create the table
    col_width = [0.6 * inch]
    width = config.TABLE_WIDTH - col_width[0]
    col_width.extend([c * width for c in cols])
    table = Table(data, colWidths=col_width,
                  splitByRow=1,
                  repeatRows=(0,1),
                  spaceAfter=30,
                  )
    # table = Table(data, splitByRow=1, hAlign='CENTER')

    # Apply the table style
    table.setStyle(table_style)
    return table


def create_beamset_data_table(data, rso, config):
    table_data = [["Beamset", "Beamset Details"]]
    bold_rows = []
    beamset_count = data[KEY_BEAMSET_COUNT]
    for i in range(beamset_count):
        beamset_number = (KEY_BEAMSET_SELECT, i)
        beamset_name = data[beamset_number]

        table_data.append([beamset_name, ""])
        bold_rows.append(len(table_data) - 1)  # Keep track of the row to be made bold

        add_row(table_data, "Number of Fractions", str(data[(KEY_BEAMSET_FRACTION_COUNT, i)]))

        approval_status = get_approval_info(rso.plan, rso.plan.BeamSets[beamset_name])
        approval_date = str(
            rso.plan.BeamSets[beamset_name].Review.ReviewTime) if approval_status.beamset_approved else 'NA'
        add_row(table_data, "Beamset Approval Date", approval_date)

        targets_table_data = [["Target Name", "Dose per Fraction (Gy)", "Total Dose (Gy)"]]
        target_count = data[(KEY_BEAMSET_TARGET_COUNT, i)]

        for j in range(target_count):
            target_name = data[(KEY_BEAMSET_TARGET_NAME, i, j)]
            fraction_dose = str(data[(KEY_BEAMSET_FRACTION_DOSE, i, j)])
            total_dose = str(data[(KEY_BEAMSET_DOSE, i, j)])
            targets_table_data.append([target_name, fraction_dose, total_dose])

        targets_table = create_targets_nested_table(targets_table_data, config)
        table_data.append(["", targets_table])

    main_table = create_beamsets_table(table_data, bold_rows, config)
    return main_table


def create_targets_nested_table(data, config):
    col_fractions = [0.23, 0.16, 0.12]
    column_widths = [c * config.TABLE_WIDTH for c in col_fractions]
    nested_table = Table(data, colWidths=column_widths)
    nested_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_RED),
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, config.UW_DARK_GRAY),
        ('GRID', (0, 1), (-1, -1), 1, config.UW_DARK_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [config.UW_RED, config.UW_GRAY])
    ]))
    return nested_table


def add_row(table_data, cell1, cell2):
    table_data.append([cell1, cell2])


def create_beamsets_table(data, bold_rows, config):
    main_table = Table(data,spaceAfter=30)
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_GRAY),  # First row
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),  # First row
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),  # First row
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), config.UW_DARK_RED),
        ('GRID', (0, 0), (-1, -1), 1, config.UW_DARK_GRAY),
        ('ROUNDEDCORNERS',[2, 2, 2, 2]),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [config.UW_RED, config.UW_GRAY])
    ]))

    for row in bold_rows:
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, row), (-1, row), config.UW_DARK_GRAY),
            ('TEXTCOLOR', (0, row), (-1, row), config.UW_WHITE),
            ('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold'),
            ('SPAN', (0, row), (-1, row)),
        ]))

    return main_table


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
