import time
import os
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Frame, Table, TableStyle, Image, BaseDocTemplate, PageTemplate
from reportlab.platypus import Paragraph as P
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle

# Define the export location
report_folder = r'\\aria\echart'


def pdf(patient, exam, plan, fields, target_priority=2, overwrite=True):
    tic = time.time()
    f = os.path.join(report_folder, '{}_{}.pdf'.format(patient.Name.replace('^', '_'), plan.Name))
    if overwrite and os.path.isfile(f):
        logging.debug('Deleting existing file per overwrite flag')
        os.remove(f)

    # Initialize Platypus document
    logging.debug('Initializing PDF to save to {}'.format(f))
    doc = BaseDocTemplate(f,
                          pagesize=letter,
                          pageTemplates=[PageTemplate(id='allpages',
                                                      frames=[Frame(0.75 * inch, 0.75 * inch, 7 * inch, 9.5 * inch,
                                                                    showBoundary=0)])],
                          showBoundary=0,
                          rightMargin=0.75 * inch,
                          leftMargin=0.75 * inch,
                          bottomMargin=0.75 * inch,
                          topMargin=0.75 * inch,
                          allowSplitting=1,
                          title='Treatment Planning Order',
                          encrypt=None)

    # Define text style
    s = ParagraphStyle({'fontName': 'Helvetica',
                        'fontSize': 11,
                        'leading': 11,
                        'leftIndent': 0,
                        'rightIndent': 0,
                        'firstLineIndent': 0,
                        'encoding': 'Unicode',
                        'alignment': TA_LEFT,
                        'spaceBefore': 0,
                        'spaceAfter': 0,
                        'bulletFontName': 'Helvetica',
                        'bulletFontSize': 10,
                        'bulletIndent': 0,
                        'textColor': colors.black,
                        'backColor': None,
                        'wordWrap': None,
                        'borderWidth': 0,
                        'borderPadding': 0,
                        'borderColor': None,
                        'borderRadius': None,
                        'allowWidows': 1,
                        'allowOrphans': 0,
                        'textTransform': None,
                        'endDots': None,
                        'splitLongWords': 1,
                        'bulletAnchor': 'start',
                        'justifyLastLine': 0,
                        'justifyBreaks': 0})

    # Start report
    story = [Table(data=[[Image('report_logo.jpg', width=2 * inch, height=0.4306 * inch),
                          P('<b><font size=14>' + fields['protocol'] + ' Treatment Planning Order</font></b>', s)]],
                   colWidths=[2.5 * inch, 5 * inch],
                   spaceAfter=0.25 * inch,
                   hAlign='LEFT',
                   style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))]

    # Retrieve CT info
    info = exam.GetAcquisitionDataFromDicom()
    story.append(Table(data=[[P('<b>Name:</b>', s), P(patient.Name.replace('^', ' '), s)],
                             [P('<b>Patient ID:</b>', s), P(patient.PatientID, s)],
                             [P('<b>Date of Birth:</b>', s), P('{}/{}/{}'.format(patient.DateOfBirth.Month,
                                                                                 patient.DateOfBirth.Day,
                                                                                 patient.DateOfBirth.Year), s)],
                             [P('<b>Clinic:</b>', s), P(fields['institution'], s)],
                             [P('<b>Diagnosis:</b>', s), P(fields['diagnosis'], s)],
                             [P('<b>Order:</b>', s), P(fields['order'], s)],
                             [P('<b>Planning Image:</b>', s), P('{}, {} {} ({}/{:02}/{} {:02}:{:02})'.
                                                                format(exam.Name,
                                                                       info['EquipmentModule']['Manufacturer'],
                                                                       info['EquipmentModule'][
                                                                           'ManufacturersModelName'],
                                                                       info['StudyModule']['StudyDateTime'].Month,
                                                                       info['StudyModule']['StudyDateTime'].Day,
                                                                       info['StudyModule']['StudyDateTime'].Year,
                                                                       info['StudyModule']['StudyDateTime'].Hour,
                                                                       info['StudyModule']['StudyDateTime'].Minute), s)]
                             ],
                       colWidths=[1.5 * inch, 5 * inch],
                       spaceAfter=0.25 * inch,
                       hAlign='LEFT'))

    # Generate plan details table
    details_header = [P('<b>Plan Details</b>', s)]
    for p in fields['plans']:
        details_header.append(P('<b>{}</b>'.format(p.replace('_R0A0', '')), s))

    details = [details_header]
    details.append([P('Number of Fractions', s)])
    for f in fields['fractions']:
        details[-1].append(P('{}'.format(f), s))

    if 'technique' in fields:
        details.append([P('Technique', s)])
        for t in fields['technique']:
            details[-1].append(P(t, s))

    if 'frequency' in fields:
        details.append([P('Treatment frequency', s)])
        for f in fields['frequency']:
            details[-1].append(P(f, s))

    if 'imaging' in fields:
        details.append([P('Image guidance', s)])
        for i in fields['imaging']:
            details[-1].append(P(i, s))

    if 'motion' in fields:
        details.append([P('Motion management', s)])
        for m in fields['motion']:
            details[-1].append(P(m, s))

    width = min(1.5, 4.5 / len(details[0])) * inch
    story.append(Table(data=details,
                       colWidths=[1.5 * inch] + [width] * len(fields['plans']),
                       spaceAfter=0.25 * inch,
                       repeatRows=1,
                       hAlign='LEFT',
                       style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue)])))

    # Generate target table
    target_header = [P('<b>Target Dose</b>', s)]
    for p in fields['plans']:
        target_header.append(P('<b>{}</b>'.format(p.replace('_R0A0', '')), s))

    if len(fields['plans']) > 1:
        target_header.append(P('<b>Composite</b>', s))

    target_header.append(P('<b>Priority</b>', s))
    targets = [target_header]
    for t in fields['targets'].keys():
        if fields['targets'][t]['use']:
            targets.append([P(t, s)])
            c = 0
            for n in range(len(fields['plans'])):
                if len(fields['targets'][t]['dose']) > n and fields['targets'][t]['dose'][n] > 0:
                    targets[-1].append(P('D{} > {} Gy'.format(fields['targets'][t]['volume'][n],
                                                              fields['targets'][t]['dose'][n]), s))
                    c += fields['targets'][t]['dose'][n]

                else:
                    targets[-1].append(P(' ', s))

            if len(fields['plans']) > 1:
                targets[-1].append(P('D{} > {} Gy'.format(fields['targets'][t]['volume'][0], c), s))

            targets[-1].append(P('{}'.format(target_priority), s))

    story.append(Table(data=targets,
                       colWidths=[1.5 * inch] + [width] * (len(targets[0]) - 2) + [0.75 * inch],
                       spaceAfter=0.25 * inch,
                       repeatRows=1,
                       hAlign='LEFT',
                       style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue)])))

    # Generate goals table
    goals_header = [P('<b>Clinical Goals</b>', s)]
    if len(fields['plans']) == 1:
        goals_header.append(P('<b>{}</b>'.format(p.replace('_R0A0', '')), s))

    else:
        goals_header.append(P('<b>Composite</b>', s))

    goals_header.append(P('<b>Priority</b>', s))
    goals_dict = {}
    c = 0
    for f in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
        try:
            c += 1
            if f.PlanningGoal.Priority < 4:
                goal = ''
                if f.PlanningGoal.Type == 'VolumeAtDose':
                    if f.PlanningGoal.GoalCriteria == 'AtMost':
                        goal = 'V{} &lt; {}%'.format(f.PlanningGoal.ParameterValue / 100,
                                                     f.PlanningGoal.AcceptanceLevel * 100)

                    else:
                        goal = 'V{} &gt; {}%'.format(f.PlanningGoal.ParameterValue / 100,
                                                     f.PlanningGoal.AcceptanceLevel * 100)

                elif f.PlanningGoal.Type == 'AbsoluteVolumeAtDose':
                    if f.PlanningGoal.GoalCriteria == 'AtMost':
                        goal = 'V{} &lt; {}cc'.format(f.PlanningGoal.ParameterValue / 100,
                                                      f.PlanningGoal.AcceptanceLevel)

                    else:
                        goal = 'V{} &gt; {}cc'.format(f.PlanningGoal.ParameterValue / 100,
                                                      f.PlanningGoal.AcceptanceLevel)

                elif f.PlanningGoal.Type == 'DoseAtVolume':
                    if f.PlanningGoal.GoalCriteria == 'AtMost':
                        goal = 'D{}% &lt; {} Gy'.format(f.PlanningGoal.ParameterValue * 100,
                                                        f.PlanningGoal.AcceptanceLevel / 100)
                    else:
                        goal = 'D{}% &gt; {} Gy'.format(f.PlanningGoal.ParameterValue * 100,
                                                        f.PlanningGoal.AcceptanceLevel / 100)

                elif f.PlanningGoal.Type == 'DoseAtAbsoluteVolume':
                    if f.PlanningGoal.GoalCriteria == 'AtMost':
                        goal = 'D{}cc &lt; {} Gy'.format(f.PlanningGoal.ParameterValue,
                                                         f.PlanningGoal.AcceptanceLevel / 100)
                    else:
                        goal = 'D{}cc &gt; {} Gy'.format(f.PlanningGoal.ParameterValue,
                                                         f.PlanningGoal.AcceptanceLevel / 100)

                elif f.PlanningGoal.Type == 'AverageDose':
                    if f.PlanningGoal.GoalCriteria == 'AtMost':
                        goal = 'Mean &lt; {} Gy'.format(f.PlanningGoal.AcceptanceLevel / 100)

                    else:
                        goal = 'Mean &gt; {} Gy'.format(f.PlanningGoal.AcceptanceLevel / 100)

                if goal != '':
                    if '{}{}'.format(f.PlanningGoal.Priority, f.ForRegionOfInterest.Name) in goals_dict:
                        goals_dict['{}{}'.format(f.PlanningGoal.Priority,
                                                 f.ForRegionOfInterest.Name)][1] += '<br/>' + goal

                    else:
                        goals_dict['{}{}'.format(f.PlanningGoal.Priority, f.ForRegionOfInterest.Name)] = \
                            [f.ForRegionOfInterest.Name, goal, f.PlanningGoal.Priority]

                else:
                    logging.warning('Unrecognized type for clinical goal {}'.format(c))

            else:
                logging.debug('Clinical goal {} has priority greater than 3 and will be skipped'.format(c))

        except Exception:
            logging.warning('An error occurred adding clinical goal {}'.format(c))

    goals = [goals_header]
    for k in sorted(goals_dict.keys()):
        goals.append([P(goals_dict[k][0], s), P(goals_dict[k][1], s), P('{}'.format(goals_dict[k][2]), s)])

    story.append(Table(data=goals,
                       colWidths=[1.5 * inch + width * (len(targets[0]) - 3)] + [width] + [0.75 * inch],
                       spaceAfter=0.25 * inch,
                       repeatRows=1,
                       hAlign='LEFT',
                       style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                                         ('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Generate options and comments tables
    options = []
    for o in sorted(fields['options'].iterkeys()):
        if fields['options'][o]:
            options.append([P('[X]', s), P(o, s)])

        else:
            options.append([P('[&nbsp;&nbsp;]', s), P(o, s)])

    if len(options) > 0:
        options[0].insert(0, P('<b>Plan Options:</b>', s))
        for i in range(1, len(options)):
            options[i].insert(0, P('', s))

    story.append(Table(data=options,
                       colWidths=[1.5 * inch, 0.35 * inch, 4.65 * inch],
                       spaceAfter=0.25 * inch,
                       hAlign='LEFT',
                       style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    story.append(Table(data=[[P('<b>Comments:</b>', s), P(fields['comments'].replace('\n', '<br/>'), s)]],
                       colWidths=[1.5 * inch, 5 * inch],
                       spaceAfter=0.25 * inch,
                       hAlign='LEFT',
                       style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    doc.build(story)
    logging.debug('WriteTpo.pdf() completed successfully in {:.3f} seconds'.format(time.time() - tic))

