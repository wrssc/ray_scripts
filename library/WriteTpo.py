""" Generate TPO PDF

    The functions in this script create a Treatment Planning Order (TPO) template
    based on the provided patient plan's beamset and clinical goals, along with an
    optional dict of fields. The format of the fields dict is set from the TpoDialog
    class. Currently only PDF files are supported. The following example illustrates
    how to use this package:

    import WriteTpo
    import connect
    WriteTpo.pdf(patient=connect.get_current('Patient')
                 exam=connect.get_current('Exam'),
                 plan=connect.get_current('Plan'))

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Create-TPO'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import time
import os
import logging
import Goals
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Frame, Table, TableStyle, Image, BaseDocTemplate, PageTemplate
from reportlab.platypus import Paragraph as P
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle

# Define the export location
report_folder = r'\\aria\echart'


def pdf(patient, exam, plan, folder=report_folder, fields=None, overwrite=True, priority=4):
    tic = time.time()
    filename = os.path.join(folder, '{}_{}.pdf'.format(patient.Name.replace('^', '_'), plan.Name))
    if overwrite and os.path.isfile(filename):
        logging.debug('Deleting existing file per overwrite flag')
        os.remove(filename)

    # Initialize Platypus document
    logging.debug('Initializing PDF to save to {}'.format(filename))
    doc = BaseDocTemplate(filename,
                          pagesize=letter,
                          pageTemplates=[PageTemplate(id='all',
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
                        'fontSize': 10,
                        'leading': 10,
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
    story = [Table(data=[[Image(os.path.join(os.path.dirname(__file__), 'report_logo.jpg'),
                                width=2 * inch,
                                height=0.4306 * inch),
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
                             [P('<b>Diagnosis:</b>', s), P(' '.join(fields['diagnosis']), s)],
                             [P('<b>Order:</b>', s), P(fields['order'], s)],
                             [P('<b>Planning Image:</b>', s), P('{}, {} {}'.
                                                                format(exam.Name,
                                                                       info['EquipmentModule']['InstitutionName'],
                                                                       info['EquipmentModule']['StationName']), s)],
                             [P('<b>Plan Name:</b>', s), P(plan.Name, s)]
                             ],
                       colWidths=[1.5 * inch, 5 * inch],
                       spaceAfter=0.25 * inch,
                       hAlign='LEFT',
                       style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # If a fields dict was not provided, query the provided plan
    if fields is None:
        fields = {'plans': [], 'fractions': [], 'technique': []}
        for b in plan.BeamSets:
            fields['plans'].append(b.DicomPlanLabel)
            fields['fractions'].append(b.FractionationPattern.NumberOfFractions)
            fields['technique'].append(b.DeliveryTechnique)

    # Generate plan details table
    details_header = [P('<b>Plan Details</b>', s)]
    for p in fields['plans']:
        details_header.append(P('<b>{}</b>'.format(p.replace('_R0A0', '_RXAX')), s))

    details = list([details_header])
    details.append([P('Number of Fractions', s)])
    for n in range(len(fields['plans'])):
        if len(fields['fractions']) > n and fields['fractions'][n] is not None:
            details[-1].append(P('{}'.format(fields['fractions'][n]), s))

        else:
            details[-1].append(details[-1][-1])

    if 'technique' in fields and len(fields['technique']) > 0 and fields['technique'][0] is not None:
        details.append([P('Technique', s)])
        for n in range(len(fields['plans'])):
            details[-1].append(P(fields['technique'][min(n, len(fields['technique'])-1)], s))

    if 'frequency' in fields and len(fields['frequency']) > 0 and fields['frequency'][0] is not None:
        details.append([P('Treatment frequency', s)])
        for n in range(len(fields['plans'])):
            details[-1].append(P(fields['frequency'][min(n, len(fields['frequency']) - 1)], s))

    if 'imaging' in fields and len(fields['imaging']) > 0 and fields['imaging'][0] is not None:
        details.append([P('Image guidance', s)])
        for n in range(len(fields['plans'])):
            details[-1].append(P(fields['imaging'][min(n, len(fields['imaging']) - 1)], s))

    if 'motion' in fields and len(fields['motion']) > 0 and fields['motion'][0] is not None:
        details.append([P('Motion management', s)])
        for n in range(len(fields['plans'])):
            details[-1].append(P(fields['motion'][min(n, len(fields['motion']) - 1)], s))

    width = min(1.5, 4.5 / len(details[0])) * inch
    story.append(Table(data=details,
                       colWidths=[1.5 * inch] + [width] * len(fields['plans']),
                       spaceAfter=0.25 * inch,
                       repeatRows=1,
                       hAlign='LEFT',
                       style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                                         ('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Generate target table
    if 'targets' in fields:
        target_header = [P('<b>Target Dose</b>', s)]
        for p in fields['plans']:
            target_header.append(P('<b>{}</b>'.format(p.replace('_R0A0', '_RXAX')), s))

        if len(fields['plans']) > 1:
            target_header.append(P('<b>Composite</b>', s))

        targets = [target_header]
        for t in fields['targets'].keys():
            if fields['targets'][t]['use']:
                targets.append([P(t, s)])
                c = 0
                for n in range(len(fields['plans'])):
                    if len(fields['targets'][t]['dose']) > n and fields['targets'][t]['dose'][n] > 0:
                        targets[-1].append(P('{} Gy @ {} Gy/fx'.format(fields['targets'][t]['dose'][n],
                                                                       fields['targets'][t]['dose'][n] /
                                                                       fields['fractions'][n]), s))
                        c += fields['targets'][t]['dose'][n]

                    else:
                        targets[-1].append(P(' ', s))

                if len(fields['plans']) > 1:
                    targets[-1].append(P('{} Gy'.format(c), s))

        story.append(Table(data=targets,
                           colWidths=[1.5 * inch] + [width] * (len(targets[0]) - 1),
                           spaceAfter=0.25 * inch,
                           repeatRows=1,
                           hAlign='LEFT',
                           style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                             ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                             ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                                             ('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Generate goals table
    goals_header = [P('<b>Clinical Goals</b>', s)]
    if len(fields['plans']) == 1:
        goals_header.append(P('<b>{}</b>'.format(fields['plans'][0].replace('_R0A0', '_RXAX')), s))

    else:
        goals_header.append(P('<b>Composite</b>', s))

    goals_header.append(P('<b>Priority</b>', s))
    goals_dict = {}
    c = 0
    for f in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
        try:
            c += 1
            if f.PlanningGoal.Priority < priority:
                goal = Goals.print_goal(f, 'eval')
                if goal != '':
                    if '{}{}'.format(f.PlanningGoal.Priority, f.ForRegionOfInterest.Name) in goals_dict:
                        goals_dict['{}{}'.format(f.PlanningGoal.Priority,
                                                 f.ForRegionOfInterest.Name)][1] += '<br/>' + goal

                    else:
                        goals_dict['{}{}'.format(f.PlanningGoal.Priority, f.ForRegionOfInterest.Name)] = \
                            [f.ForRegionOfInterest.Name, goal, f.PlanningGoal.Priority]

                else:
                    logging.warning('Unrecognized type for clinical goal {}'.format(c))

        except Exception:
            logging.warning('An error occurred adding clinical goal {}'.format(c))

    goals = [goals_header]
    oars = []
    for k in sorted(goals_dict.keys()):
        goals.append([P(goals_dict[k][0], s), P(goals_dict[k][1], s), P('{}'.format(goals_dict[k][2]), s)])
        if len(oars) < 5 and ('targets' not in fields or goals_dict[k][0] not in fields['targets']):
            oars.append(goals_dict[k][0])

    story.append(Table(data=goals,
                       colWidths=[1.5 * inch + width * (len(targets[0]) - 2)] + [width] + [0.75 * inch],
                       spaceAfter=0.25 * inch,
                       repeatRows=1,
                       hAlign='LEFT',
                       style=TableStyle([('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                         ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                                         ('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Add billing justification
    modality = '3D'
    for b in plan.BeamSets:
        if b.Modality == 'Photons' and b.PlanGenerationTechnique == 'Imrt':
            modality = 'IMRT'
            break

    justification = 'To avoid complication-inducing doses to the '
    if len(oars) > 1:
        justification += '{} and {}'.format(', '.join(oars[0:-1]), oars[-1])
    elif len(oars) > 0:
        justification += oars[0]
    else:
        justification = 'To avoid excessive dose heterogeneity within the target'

    story.append(Table(data=[[P('<b>Date of Service: </b>', s), P(time.strftime('%m/%d/%Y %I:%M %p',
                                                                                time.localtime()), s)],
                             [P('<b>Reason for {}: </b>'.format(modality), s), P(justification, s)]],
                       colWidths=[1.5 * inch, 5 * inch],
                       spaceAfter=0.25 * inch,
                       hAlign='LEFT',
                       style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Add plan options
    if 'options' in fields:
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

    # Add comments
    if 'comments' in fields and fields['comments'].strip() != '':
        story.append(Table(data=[[P('<b>Comments:</b>', s), P(fields['comments'].replace('\n', '<br/>'), s)]],
                           colWidths=[1.5 * inch, 5 * inch],
                           spaceAfter=0.25 * inch,
                           hAlign='LEFT',
                           style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])))

    # Finish up
    doc.build(story)
    logging.debug('WriteTpo.pdf() completed successfully in {:.3f} seconds'.format(time.time() - tic))
    return filename
