import os
from docx import Document
from docx.shared import Cm, Inches
from docx.enum.table import WD_ALIGN_VERTICAL
from ..review_definitions import OUTPUT_DIR, UW_HEALTH_LOGO, LEVELS
from ..utils import get_approval_info


def generate_doc(rso, tests):
    # Output file
    file_name = rso.patient.PatientID + "_" + rso.beamset.DicomPlanLabel + \
                ".doc"
    output_file = os.path.join(OUTPUT_DIR, file_name)
    header_text = "Photon VMAT Physics Review"
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
    # Responses to non-scriptable questions
    plan_questions = tests['Test_BeamSet']

    # Begin
    document = Document()
    section = document.sections[0]
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)
    # Add header

    header = section.header
    paragraph = header.paragraphs[0]
    # Add logo
    logo_run = paragraph.add_run()
    logo_run.add_picture(UW_HEALTH_LOGO, width=Inches(1.0))
    text_run = paragraph.add_run()
    text_run.text = '\t' + header_text  # For center align of text
    text_run.style = "Heading 1 Char"

    paragraph = document.add_paragraph()
    # Add Top Row Demographics
    table = document.add_table(rows=2, cols=4, style='Medium Grid 1 Accent 2')
    for index, k in enumerate(demographics):
        row_key = table.rows[0]
        row_value = table.rows[1]
        row_key.cells[index].text = k
        row_value.cells[index].text = demographics[k]
    # Add the plan checks
    paragraph = document.add_paragraph()
    document = add_check_list_table(tests['Test_BeamSet'], document)

    document.save(output_file)
    print('Complete')


def add_check_list_table(check_results, document, title=None):
    n_cols = 3  # Icon, Testname, Result, Comment
    table_properties = {'NCOL': 4,
                        'WIDTH_COL': [(0, 0.25), (1, 1.), (2, 3.), (3, 3.)]}
    table = document.add_table(rows=1, cols=table_properties['NCOL'],
                               style='Light Grid Accent 2')
    i = 0
    for r in enumerate(check_results):
        row = table.rows[i]
        child_list = r[1]
        if i == 0:
            row.cells[0].text = 'Status'
            row.cells[1].text = 'Test Performed'
            row.cells[2].text = 'Result'
            row.cells[3].text = 'Reviewer Comment'
            table.add_row()
            i += 1
        elif child_list[0] not in LEVELS.values():
            row.cells[0].add_paragraph().add_run().add_picture(child_list[4],
                                                               width=Inches(
                                                                   0.2),
                                                               height=Inches(
                                                                   0.2))
            row.cells[1].text = child_list[0]
            row.cells[2].text = child_list[2]
            table.add_row()
            i += 1
        for index, width in table_properties['WIDTH_COL']:
            for cell in table.columns[index].cells:
                cell.width = Inches(width)
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    return document
