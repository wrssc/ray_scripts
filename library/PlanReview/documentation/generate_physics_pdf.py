from dataclasses import dataclass
from typing import NamedTuple
from functools import partial
from datetime import datetime
import pandas as pd
from PlanReview.review_definitions import (
    LOG_DIR, UW_HEALTH_LOGO, REVIEW_LEVELS, FAIL, PASS, ALERT, RED_CIRCLE, GREEN_CIRCLE)
from PlanReview.utils import get_approval_info
from PlanReview.utils.constants import (
    KEY_BEAMSET, KEY_SIDE_PANEL, KEY_OUT_DOMAIN_NAME, KEY_OUT_TEST_SOURCE, SOURCE_USER, KEY_USER_COMMENT,
    KEY_OUT_TAB, KEY_OUT_RESULT, SOURCE_AUTO, KEY_OUT_DESC, KEY_OUT_MESSAGE, KEY_OUT_COMMENT, KEY_OUT_ICON,
    KEY_PROCEED_REVISE, KEY_REVISION_INFO, KEY_BEAMSET_COUNT, KEY_BEAMSET_SELECT, KEY_BEAMSET_FRACTION_COUNT,
    KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE, KEY_BEAMSET_FRACTION_DOSE, KEY_BEAMSET_TARGET_COUNT,
    KEY_IMD, KEY_PRIOR_RT, KEY_IMAGING_FREQ, KEY_TREAT_FREQ, KEY_PATIENT_ORIENTATION, KEY_SIM_DATE,
    KEY_SIMULATION_DATA, KEY_HEADER, KEY_TESTS, KEY_TX_INST, KEY_TX_INST_SET, KEY_RADIO, KEY_COMBO
)
from PlanReview.utils.io_file_utils import *
from reportlab.lib.pagesizes import landscape, letter
from reportlab.platypus import Table, TableStyle, Image
from reportlab.platypus import (SimpleDocTemplate, PageTemplate, Frame, PageBreak, Paragraph)
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def hex_to_reportlab_color(str_color):
    # Remove any '#' at the beginning if present
    hex_color = str_color.lstrip('#')

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
    TABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN  # - 0.2 * inch
    NARROW_TABLE_WIDTH = TABLE_WIDTH * 1
    UW_RED = hex_to_reportlab_color("#c5050c")
    UW_ROSE = hex_to_reportlab_color("#ffc2c2")
    UW_DARK_RED = hex_to_reportlab_color("#9b0000")
    UW_WHITE = hex_to_reportlab_color("#f7f7f7")
    UW_GRAY = hex_to_reportlab_color("#dadfe1")
    UW_DARK_GRAY = hex_to_reportlab_color("#282728")
    UW_BLUE = hex_to_reportlab_color("#0479a8")
    UW_TEXT = hex_to_reportlab_color("#333333")


def generate_pdf(rso, review_data, test_mode=False):
    config = ReportConfig()
    physics_review_dir = os.path.join(LOG_DIR, "PhysicsReviews")
    patient_output_dir = os.path.join(OUTPUT_DIR, rso.patient.PatientID)
    report_output_dir = r"Q:\\RadOnc\RayStation\Reports\PhysicsReview"
    patient_output_prefix = f"{rso.patient.PatientID}_" \
                            f"{rso.beamset.DicomPlanLabel}_" \
                            f"{generate_filename()}"

    if test_mode:
        latest_test_file = find_latest_file(
            patient_output_dir,
            f"{rso.patient.PatientID}",f"{rso.beamset.DicomPlanLabel}","review_data.json")
        patient_data = read_tests_from_json(latest_test_file)
        tests = patient_data[KEY_TESTS] if patient_data else None
        header_data = patient_data[KEY_HEADER] if patient_data else None
    else:
        if not review_data:
            return
        review_files = [
            generate_file_path(
                patient_output_dir, patient_output_prefix, "_review_data.json"),
            generate_file_path(
                physics_review_dir, patient_output_prefix, "_review_data.json")
        ]
        dump_tests_to_json(review_data, file_names=review_files)
        tests = read_tests_from_json(review_files[0])[KEY_TESTS]
        header_data = read_tests_from_json(review_files[0])[KEY_HEADER]
        # dump_tests_to_json(header_data, file_names=header_files)

    tests_df = read_data(tests)

    # Output file
    # output_file = generate_file_path(
    #     patient_output_dir, patient_output_prefix, ".pdf")
    output_file = generate_file_path(
        report_output_dir, patient_output_prefix, ".pdf"
      )

    # Create a PDF document
    pdf_filename = output_file
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
                                       onPage=partial(my_first_page, rso=rso))
    later_page_template = PageTemplate(frames=[footer_frame], id="laterPages",
                                       onPage=partial(myLaterPages, rso, header_data[KEY_BEAMSET]))
    # Add the template to the document
    doc.addPageTemplates([first_page_template, later_page_template])

    # Create a list to store flowables (elements that go into the PDF)
    story = []
    # Create demographics table
    demo_table = create_demographics_table(header_data[KEY_BEAMSET], rso, config)
    story.append(demo_table)
    # Create a table and apply the custom style
    main_table = create_beamset_data_table(header_data[KEY_BEAMSET], rso, config)
    story.append(main_table)
    # Create the treatment instructions table
    instructions_table = add_treatment_instructions_table(header_data[KEY_SIMULATION_DATA],
                                                          header_data[KEY_TX_INST_SET],
                                                          config)
    story.append(instructions_table)
    # Add reviewer comments
    review_table = add_reviewer_approval(header_data[KEY_SIDE_PANEL], config)
    story.append(review_table)
    # story.append(Spacer(1, 12))  # Add space between sections
    story.append(PageBreak())

    # Add table using add_check_list_table function
    generate_tables_from_dataframe(tests_df, story, config)  # Pass centered_frame

    # Build the PDF document
    doc.build(story, onFirstPage=partial(my_first_page, rso=rso),
              onLaterPages=partial(myLaterPages, rso=rso, data=header_data[KEY_BEAMSET]))


def read_data(data):
    return pd.DataFrame(data)


def str_key_to_tuple(value):
    if isinstance(value, dict):
        return {str_key_to_tuple(k): str_key_to_tuple(v) for k, v in value.items()}
    elif isinstance(value, str) and '||' in value:
        return tuple(int(x) if x.isdigit() else x for x in value.split('||'))
    return value


def generate_tables_from_dataframe(df, story, config):
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
        add_check_list_table(user_tl_df, story, config, title=f'{test_level}')

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
            add_check_list_table(auto_tl_df, story, config, title=f'{title}',
                                 display_domain_name=True)


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
        width = max(max_length, len(header), 0.12 * max_overall)
        column_widths.append(width)

    # Normalize the column widths to sum up to 1.0
    total_width = sum(column_widths)
    column_widths = [width / total_width for width in column_widths]

    return column_widths


def make_paragraph(text, style=None):
    character_map = {
        "\u00a0": "&nbsp;",
        "\n": "<br/>",
        "\r": "<br/>",
        "\t": "&nbsp;&nbsp;&nbsp;&nbsp;",
        "* ": "&bull;&nbsp;"
    }
    # Convert **text** to <b>text</b>
    text = text.replace("**", "<b>", 1).replace("**", "</b>", 1)

    for unicode, html in character_map.items():
        text = text.replace(unicode, html)

    if not style:
        style = getSampleStyleSheet()['Normal']

    return Paragraph(text, style)


def add_check_list_table(df, story, config, title=None,display_domain_name=False):
    # Define table styles
    style = getSampleStyleSheet()
    label_style = style['Heading6']
    label_style.textColor = config.UW_WHITE
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_GRAY),
        ('BACKGROUND', (0, 1), (-1, 1), config.UW_DARK_RED),
        ('TEXTCOLOR', (0, 0), (-1, 1), config.UW_WHITE),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 1), (0, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.25, config.UW_DARK_GRAY),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [config.UW_GRAY, config.UW_WHITE]),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ])

    # Create a table data list
    if not display_domain_name:
        data = [[title, "", "", ""],
                [make_paragraph('Status', style=label_style),
                 make_paragraph('Test Performed', style=label_style),
                make_paragraph('Result', style=label_style),
                make_paragraph('Reviewer Comment', style=label_style)]]
    else:
        data = [[title, "", "", ""],]

    last_domain_name = None  # to keep track of domain name changes
    domain_header_rows = []  # to keep track of rows with domain headers

    for _, check in df.iterrows():
        # Check if domain name has changed and insert header row if required
        if display_domain_name and check[KEY_OUT_DOMAIN_NAME] != last_domain_name:
            domain_header = make_paragraph(check[KEY_OUT_DOMAIN_NAME], style=label_style)
            data.append([domain_header, "", "", ""])
            domain_header_rows.append(len(data) - 1)  # Keep track of the row index
            last_domain_name = check[KEY_OUT_DOMAIN_NAME]
            data.append([make_paragraph('Status', style=label_style),
                         make_paragraph('Test Performed', style=label_style),
                         make_paragraph('Result', style=label_style),
                         make_paragraph('Reviewer Comment', style=label_style)])
        # Add regular rows
        icon_image = Image(check[KEY_OUT_ICON],
                           hAlign="CENTER", lazy=1)
        desc_paragraph = make_paragraph(check[KEY_OUT_DESC])
        message_paragraph = make_paragraph(check[KEY_OUT_MESSAGE])
        comment_paragraph = make_paragraph(check[KEY_OUT_COMMENT])

        data.append([icon_image, desc_paragraph, message_paragraph, comment_paragraph])
    # Update the table style for the domain header rows
    for row_idx in domain_header_rows:
        table_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), config.UW_DARK_GRAY)
        table_style.add('BACKGROUND', (0, row_idx + 1), (-1, row_idx + 1), config.UW_DARK_RED)
        table_style.add('SPAN', (0, row_idx), (-1, row_idx))  # Span the columns for domain name
        table_style.add('ALIGN', (0, row_idx), (-1, row_idx), 'CENTER')

    cols = calculate_column_widths(df, [KEY_OUT_DESC, KEY_OUT_MESSAGE, KEY_OUT_COMMENT])
    # Create the table
    col_width = [0.6 * inch]
    width = config.TABLE_WIDTH - col_width[0]
    col_width.extend([c * width for c in cols])
    table = Table(data, colWidths=col_width,
                  splitByRow=1,
                  repeatRows=(0, 1),
                  spaceAfter=30,
                  )
    # Apply the table style
    table.setStyle(table_style)
    story.append(table)


def convert_time(time_input):
    """
    Converts a datetime object to a 24-hour clock format string.

    Args:
        time_input (datetime): A datetime object in any format.

    Returns:
        str: A string representation of the input datetime in 24-hour clock format (e.g., "2023-11-17 14:04:30").
    """
    time_str = str(time_input)
    input_format = "%m/%d/%Y %I:%M:%S %p"  # 12-hour clock format
    # Parse the input string into a datetime object
    date_time_obj = datetime.strptime(time_str, input_format)
    output_format = "%Y-%m-%d %H:%M:%S"  # 24-hour clock format
    formatted_string = datetime.strftime(date_time_obj, output_format)
    return formatted_string


def create_demographics_table(data: dict, rso: NamedTuple, config: dict) -> str:
    """
    Creates a demographics table based on input data, RSO object, and configuration.

    Args:
        data (dict): Input data containing beamset information.
        rso (object): RayStation named tuple
        config (dict): Configuration parameters.

    Returns:
        str: A string representing the demographics table.
    """
    table_data = [["Patient Name", "MRN", "Beamset Name", "Approval Date"]]
    beamset_count = data[KEY_BEAMSET_COUNT]

    for i in range(beamset_count):
        beamset_number = (KEY_BEAMSET_SELECT, i)
        beamset_name = data[beamset_number]
        approval_status = get_approval_info(rso.plan, rso.plan.BeamSets[beamset_name])

        if approval_status.beamset_approved:
            approval_date = convert_time(rso.plan.BeamSets[beamset_name].Review.ReviewTime)
        else:
            approval_date = "NA"

        if i == 0:
            patient_name = rearrange_name(str(rso.patient.Name))
            patient_id = rso.patient.PatientID
        else:
            patient_name = ""
            patient_id = ""

        table_data.append([str(patient_name), str(patient_id),
                           str(beamset_name), str(approval_date)])

    demo_table = build_demographics_table(table_data, config)
    return demo_table


def build_demographics_table(data, config):
    col_fractions = [0.279, 0.221, 0.221, 0.278]
    column_widths = [c * config.NARROW_TABLE_WIDTH for c in col_fractions]
    demo_table = Table(data, colWidths=column_widths, spaceAfter=30)
    demo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_GRAY),  # First row
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),  # First row
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),  # First row
        ('BACKGROUND', (0, 1), (1, -1), config.UW_DARK_RED),  # First row
        ('TEXTCOLOR', (0, 1), (1, -1), config.UW_WHITE),  # First row
        ('VALIGN', (0, 1), (1, -1), 'MIDDLE'),
        ('SPAN', (0, 1), (0, -1)),
        ('SPAN', (1, 1), (1, -1)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), config.UW_DARK_RED),
        ('GRID', (0, 0), (-1, -1), 1, config.UW_DARK_GRAY),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
        ('ROWBACKGROUNDS', (2, 1), (-1, -1), [config.UW_WHITE, config.UW_GRAY])
    ]))
    return demo_table


def parse_high_risk_boolean(value, config):
    if value:
        style = getSampleStyleSheet()['Normal']
        style.fontName = 'Helvetica-Bold'
        style.backColor = config.UW_BLUE
        style.textColor = config.UW_WHITE
        return "Yes", style
    else:
        return "No", getSampleStyleSheet()['Normal']


def parse_special_instructions(data):
    """
    Parse and extract special instructions from the given data.

    This function iterates through a dictionary of data, where keys are tuples
    and values are instruction details. It extracts and formats special instructions
    based on predefined key patterns and conditions. Only unique instructions with
    relevant values are included in the output.

    Parameters:
    data (dict): A dictionary containing keys as tuples and values as instruction details.

    Returns:
    str: A formatted string containing the extracted special instructions.

    Notes:
    - Handles 'radio' and 'combo' type instructions differently.
    - Filters out instructions with empty, 'false', or duplicate values.
    """
    special_instructions_text = ""

    for tuple_key, value in data.items():
        key, instruction_number = tuple_key
        # Check for 'radio' type instructions
        if key.startswith(KEY_TX_INST) and KEY_RADIO in key:
            _, instruction_name, response_type, radio_value = key.split('-')[1:]
            # Check if the instruction is already seen or has 'false' value
            if not value:
                continue
            special_instructions_text += f"* {instruction_name}: {radio_value}\n"
        # Check for 'combo' type instructions
        elif KEY_COMBO in key:
            _, instruction_name, response_type, _ = key.split('-')[1:]
            # Ignore empty instructions
            if not value.strip():
                continue
            special_instructions_text += f"* {instruction_name}: {value}\n"
    return special_instructions_text


def add_treatment_instructions_table(simulation_set, special_instructions, config):
    hstyle = getSampleStyleSheet()['Normal']
    hstyle.textColor = config.UW_WHITE
    hstyle.fontName = 'Helvetica-Bold'

    table_data = [
        [  # make_paragraph("Simulation Date", hstyle),
            # make_paragraph("Patient Orientation", hstyle),
            make_paragraph("Prior Radiotherapy", hstyle),
            make_paragraph("Implanted Medical Device", hstyle),
            make_paragraph("Imaging Frequency", hstyle),
            make_paragraph("Treatment Frequency", hstyle),
            make_paragraph("Special Instructions", hstyle)]
    ]

    # Extract data from the header dictionary
    simulation_date = simulation_set.get(KEY_SIM_DATE, "Not Specified")
    patient_orientation = simulation_set.get(KEY_PATIENT_ORIENTATION, "Not Specified")
    prior_radiotherapy = simulation_set.get(KEY_PRIOR_RT, "Not Specified")
    implanted_medical_device = simulation_set.get(KEY_IMD, "Not Specified")
    imaging_frequency = simulation_set.get(KEY_IMAGING_FREQ, "Not Specified")
    treatment_frequency = simulation_set.get(KEY_TREAT_FREQ, "Not Specified")

    # Replace the boolean with Yes/No
    prior_rt_text, prior_rt_style = parse_high_risk_boolean(prior_radiotherapy, config)
    implant_text, implant_style = parse_high_risk_boolean(implanted_medical_device, config)
    # Look at special instructions
    si_text = parse_special_instructions(special_instructions)

    table_data.append([  # make_paragraph(simulation_date),
        # make_paragraph(patient_orientation),
        make_paragraph(prior_rt_text,
                       style=prior_rt_style),
        make_paragraph(implant_text,
                       style=implant_style),
        make_paragraph(imaging_frequency),
        make_paragraph(treatment_frequency),
        make_paragraph(si_text)])

    # Configure column widths and build the table
    col_fractions = [0.18, 0.18, 0.18, 0.18, 0.28]
    treatment_instructions_table = build_treatment_instructions_table(table_data, config, col_fractions)

    return treatment_instructions_table


def build_treatment_instructions_table(data, config, col_fractions):
    column_widths = [c * config.TABLE_WIDTH for c in col_fractions]
    treatment_instructions_table = Table(data,
                                         splitByRow=0,
                                         colWidths=column_widths,
                                         spaceAfter=30)
    treatment_instructions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_RED),  # First row
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),  # First row
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
        ('BACKGROUND', (0, 1), (-1, 1), config.UW_WHITE),  # First row
        ('GRID', (0, 0), (-1, -1), 0.1, config.UW_DARK_GRAY),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    return treatment_instructions_table


def row_proceed_revise(data):
    status_mapping = {
        "Revise": ("Revise", str(data.get(KEY_REVISION_INFO, "")), RED_CIRCLE),
        "Proceed": ("Proceed", "", GREEN_CIRCLE),
        "QIProceed": ("Proceed", "", GREEN_CIRCLE),
    }
    recommendation, comment, icon = status_mapping.get(data[KEY_PROCEED_REVISE], ("", "", ""))
    return recommendation, comment, icon


def add_reviewer_approval(data, config):
    hstyle = getSampleStyleSheet()['Normal']
    hstyle.textColor = config.UW_WHITE
    hstyle.fontName = 'Helvetica-Bold'
    table_data = [[make_paragraph("Status", hstyle),
                   make_paragraph("Proceed or\nRevise", hstyle),
                   make_paragraph("Reason for Revision", hstyle),
                   make_paragraph("Physicist Comments", hstyle)]]
    # Get status
    recommendation, status_comment, icon = row_proceed_revise(data)
    istyle = getSampleStyleSheet()['Normal']
    if status_comment:
        istyle.fontName = 'Helvetica-BoldOblique'
        istyle.backColor = config.UW_BLUE
        istyle.textColor = config.UW_WHITE
        status_comment = make_paragraph(status_comment, istyle)
        col_fractions = [0.06, 0.1, 0.35, 0.50]
    else:
        istyle.fontName = 'Helvetica-Oblique'
        recommendation = make_paragraph(recommendation, istyle)
        status_comment = make_paragraph("NA", istyle)
        col_fractions = [0.06, 0.1, 0.15, 0.69]
    physics_comment = make_paragraph(str(data[KEY_USER_COMMENT]))
    icon_image = Image(icon, hAlign="CENTER", lazy=1)
    table_data.append([icon_image, recommendation, status_comment, physics_comment])
    reviewer_table = build_reviewer_table(table_data, config, col_fractions)
    return reviewer_table


def build_reviewer_table(data, config, col_fractions):
    reviewer_table = Table(data,
                           splitByRow=0,
                           colWidths=[c * config.TABLE_WIDTH for c in col_fractions],
                           spaceAfter=0)
    reviewer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_RED),  # First row
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),  # First row
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
        ('BACKGROUND', (0, 1), (-1, 1), config.UW_WHITE),  # First row
        ('GRID', (0, 0), (-1, -1), 0.1, config.UW_DARK_GRAY),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    return reviewer_table


def create_beamset_data_table(data, rso, config):
    """
    Creates a beamset data table based on input data, RSO object, and configuration.
    Args:
        data:
        rso: (NamedTuple): Raystation Script Objects
        config:

    Returns:

    """
    table_data = [["Beamset Summary", ""]]
    bold_rows = []
    nested_table_rows = []
    beamset_count = data[KEY_BEAMSET_COUNT]
    for i in range(beamset_count):
        beamset_number = (KEY_BEAMSET_SELECT, i)
        beamset_name = data[beamset_number]

        table_data.append([beamset_name, "Beamset Details"])
        bold_rows.append(len(table_data) - 1)  # Keep track of the row to be made bold

        dicom_uid = rso.plan.BeamSets[beamset_name].ModificationInfo.DicomUID
        add_row(table_data, "Beamset DICOM UID", dicom_uid)

        add_row(table_data, "Number of Fractions", str(data[(KEY_BEAMSET_FRACTION_COUNT, i)]))

        targets_table_data = [["Target Name", "Dose per Fraction (Gy)", "Total Dose (Gy)"]]
        target_count = data[(KEY_BEAMSET_TARGET_COUNT, i)]

        for j in range(target_count):
            target_name = data[(KEY_BEAMSET_TARGET_NAME, i, j)]
            fraction_dose = str(data[(KEY_BEAMSET_FRACTION_DOSE, i, j)])
            total_dose = str(data[(KEY_BEAMSET_DOSE, i, j)])
            targets_table_data.append([target_name, fraction_dose, total_dose])

        targets_table = create_targets_nested_table(targets_table_data, config)
        table_data.append(["", targets_table])
        nested_table_rows.append(len(table_data) - 1)

    main_table = create_beamsets_table(table_data, bold_rows, nested_table_rows, config)
    return main_table


def create_targets_nested_table(data, config):
    col_fractions = [0.23, 0.16, 0.12]
    column_widths = [c * config.TABLE_WIDTH for c in col_fractions]
    nested_table = Table(data, colWidths=column_widths)
    nested_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_RED),
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, config.UW_DARK_GRAY),
        ('GRID', (0, 1), (-1, -1), 1, config.UW_DARK_GRAY),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [config.UW_WHITE, config.UW_ROSE])
    ]))
    return nested_table


def add_row(table_data, cell1, cell2):
    table_data.append([cell1, cell2])


def create_beamsets_table(data, bold_rows, nested_table_rows, config):
    col_fractions = [0.4, 0.6]
    main_table = Table(data,
                       splitByRow=0,
                       colWidths=[c * config.NARROW_TABLE_WIDTH for c in col_fractions],
                       spaceAfter=30)
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), config.UW_DARK_GRAY),  # First row
        ('TEXTCOLOR', (0, 0), (-1, 0), config.UW_WHITE),  # First row
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # First row
        ('SPAN', (0, 0), (-1, 0)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), config.UW_DARK_RED),
        ('GRID', (0, 0), (-1, -1), 1, config.UW_DARK_GRAY),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [config.UW_WHITE, config.UW_GRAY])
    ]))

    for row in bold_rows:
        main_table.setStyle(TableStyle([
            ('BACKGROUND', (0, row), (-1, row), config.UW_DARK_RED),
            ('TEXTCOLOR', (0, row), (-1, row), config.UW_WHITE),
            ('FONTNAME', (0, row), (-1, row), 'Helvetica-Bold'),
        ]))
    for row in nested_table_rows:
        main_table.setStyle(TableStyle([
            ('ALIGN', (1, row), (1, row), 'CENTER'),
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


def my_first_page(canvas, doc, rso):
    canvas.saveState()
    logo_width = 2.5 * inch
    logo_height = logo_width * 240 / 920
    logo_image = Image(UW_HEALTH_LOGO, width=logo_width, height=logo_height)
    logo_image.drawOn(canvas, doc.leftMargin, doc.height - logo_height)

    # Get document header title
    header_text = determine_doc_type(rso)
    # Move the text to the right (adjust the X-coordinate)
    header_x = doc.leftMargin + logo_width + 30  # Horizontal Adjust
    header_y = doc.height - logo_height // 1.5

    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(header_x, header_y, header_text)
    canvas.restoreState()


def myLaterPages(canvas, doc, rso, data):
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 8)
    beamsets = []
    beamset_count = data[KEY_BEAMSET_COUNT]
    for i in range(beamset_count):
        beamset_number = (KEY_BEAMSET_SELECT, i)
        beamset_name = data[beamset_number]
        beamsets.append(beamset_name)
    demographics = {
        'Name': rearrange_name(str(rso.patient.Name)),
        'MRN': str(rso.patient.PatientID),
        'Beamset Name(s)': ", ".join(beamsets)
    }
    footer_text = ";  ".join([f"{key}: {value}" for key, value in demographics.items()])
    footer_x = doc.leftMargin
    footer_y = doc.bottomMargin - 2
    canvas.drawString(footer_x, footer_y, footer_text)
    canvas.drawString(doc.leftMargin + doc.width, footer_y, f"{doc.page}")
    canvas.restoreState()


def rearrange_name(input_str):
    # Split the input string using "^" as the delimiter
    name = input_str.split("^")

    # Check if there is more than one name
    if len(name) > 1:
        # Rearrange the list of parts and join them with a space between
        rearranged_str = " ".join(name[1:] + [name[0]])
    else:
        # If there's only one part, return the original input
        rearranged_str = input_str

    return rearranged_str
