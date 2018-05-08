""" Approve Contours and Create TPO

    This script is for physicians to approve their contour set for planning and to
    generate a Treatment Planning Order (TPO) for import into ARIA. As part of TPO
    creation, this script will also add clinical goals and initialize the treatment
    plan(s).

    Finally, dose is computed and then exported after each beamset is created. The DICOM
    export path is set in the configuration settings below. The option to only create
    beams is available by un-checking the "calculate" and "export" runtime options from
    the configuration dialog box.

    This program is free software: you can redistribute it and/or modify it under the
    terms of the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
    PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this
    program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Create-TPO'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import sys

sys.path.append('../library/')
import os
import connect
import UserInterface
import logging
import time
import WriteTpo

# Define the protocol XML directory
protocol_folder = r'../protocols'


def main():
    # Get current patient, case, and exam
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    # Start timer
    tic = time.time()

    # Start script status
    status = UserInterface.ScriptStatus(steps=['Enter plan information for TPO',
                                               'Clean up structure list',
                                               'Approve structures',
                                               'Initialize plan and beamsets',
                                               'Set clinical goals',
                                               'Generate TPO'],
                                        docstring=__doc__,
                                        help=__help__)

    # Display input dialog box for TPO
    status.next_step(text='In order to approve the plan and create a TPO, please fill out the displayed form ' +
                          'with information about the plan. Once completed, click Continue.')

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(os.path.join(os.path.dirname(__file__), protocol_folder))
    response = tpo.show(case=case, exam=exam)
    if response == {}:
        status.finish('This script was cancelled')

    # Re-name/organize structures based on TPO form
    status.next_step(text='The structures are now being renamed and organized based on your input...')
    changes = 0

    for roi in case.PatientModel.RegionsOfInterest:
        approved = False
        for a in case.PatientModel.StructureSets[exam.Name].ApprovedStructureSets:
            try:
                if a.ApprovedRoiStructures[roi.Name].OfRoi.RoiNumber > 0 and a.Review.ApprovalStatus == 'Approved':
                    approved = True
                    logging.debug('Structure {} was approved by {} and therefore will not be modified'.
                                  format(roi.Name, a.Review.ReviewerName))
                    break

            except Exception:
                logging.debug('Structure {} is not list approved by {}'.format(roi.Name, a.Review.ReviewerName))

        if not approved:
            if roi.Name in response['structures'].keys():
                if response['structures'][roi.Name] in response['targets'].keys() and \
                        response['targets'][response['structures'][roi.Name]]['use']:
                    logging.debug('Structure {} renamed to {} and set to Target'.
                                  format(roi.Name, response['structures'][roi.Name]))
                    roi.Name = response['structures'][roi.Name]
                    roi.OrganData.OrganType = 'Target'
                    roi.ExcludeFromExport = False
                    changes += 1

                elif response['structures'][roi.Name] in response['oars'].keys() and \
                        response['oars'][response['structures'][roi.Name]]['use']:
                    logging.debug('Structure {} renamed to {} and set to OAR'.
                                  format(roi.Name, response['structures'][roi.Name]))
                    roi.Name = response['structures'][roi.Name]
                    roi.OrganData.OrganType = 'OrganAtRisk'
                    roi.ExcludeFromExport = False
                    changes += 1

                else:
                    logging.debug('Structure {} is not used, set to Other'.format(roi.Name))
                    roi.OrganData.OrganType = 'Other'
                    roi.ExcludeFromExport = True
                    changes += 1

            else:
                logging.debug('Structure {} is not in TPO template, set to Other'.format(roi.Name))
                roi.OrganData.OrganType = 'Other'
                roi.ExcludeFromExport = True
                changes += 1

    # Prompt user to approve structures
    logging.debug('Prompting user to approve structure set')
    status.next_step(text='You will now be prompted to approve the structure set. Once completed, continue the script.')

    if changes > 0:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient Modeling'].Click()
        ui.TitleBar.MenuItem['Patient Modeling'].Popup.MenuItem['Structure Definition'].Click()
        ui.TabControl_ToolBar.Approval.Select()
        ui.ToolPanel.TabItem._Scripting.Select()
        connect.await_user_input('Approve the structure set now, then continue the script')

    # Create new plan (ICDa-z Protocol)
    status.next_step(text='A new plan will now be created and populated with the TPO template clinical goals...')
    patient.Save()

    for a in range(1, 26):
        plan_name = '{}{} {}'.format(response['diagnosis'][0], chr(64 + a).lower(), response['order'])
        try:
            logging.debug('Plan name already exists: ' + case.TreatmentPlans[plan_name].Name)

        except Exception:
            break

    logging.debug('Creating plan with name {}'.format(plan_name))
    plan = case.AddNewPlan(PlanName=plan_name,
                           PlannedBy='',
                           Comment='{} > {}'.format(response['protocol'], response['order']),
                           ExaminationName=exam.Name,
                           AllowDuplicateNames=False)
    patient.Save()
    plan.SetCurrent()

    # Create beamsets (prefix_middle_R0A0) and set prescription
    beam_prefix = 'Plan'
    for o in response['xml'].findall('order'):
        if o.find('name').text == response['order'] and o.find('prefix') is not None:
            beam_prefix = o.find('prefix').text
            break

    prescriptions = []
    for o in response['xml'].findall('order'):
        if o.find('name').text == response['order']:
            for p in o.findall('prescription'):
                prescriptions.append(p)

    for p in response['xml'].findall('prescription'):
        prescriptions.append(p)

    response['plans'] = []
    for i in range(len(prescriptions)):
        for t in prescriptions[i].findall('technique'):
            if t.text == response['technique'][i]:
                if 'code' in t.attrib:
                    beam_name = beam_prefix + t.attrib['code'] + '{}_R{}A{}'.format(i, 0, 0)

                else:
                    beam_name = beam_prefix + '{}_R{}A{}'.format(i, 0, 0)

                if 'machine' in t.attrib:
                    machine = t.attrib['machine']

                else:
                    machine_db = connect.get_current('MachineDB')
                    machines = machine_db.QueryCommissionedMachineInfo(Filter={})
                    for _i, m in enumerate(machines):
                        if m['IsCommissioned']:
                            machine = m['Name']
                            break

                if 'modality' in t.attrib:
                    modality = t.attrib['modality']

                else:
                    modality = 'Photons'

                if 'technique' in t.attrib:
                    technique = t.attrib['technique']

                else:
                    technique = 'Conformal'

                if exam.PatientPosition == 'HFS':
                    position = 'HeadFirstSupine'

                elif exam.PatientPosition == 'HFP':
                    position = 'HeadFirstProne'

                elif exam.PatientPosition == 'FFS':
                    position = 'FeetFirstSupine'

                elif exam.PatientPosition == 'FFP':
                    position = 'FeetFirstProne'

                elif exam.PatientPosition == 'HFDL':
                    position = 'HeadFirstDecubitusLeft'

                elif exam.PatientPosition == 'HFDL':
                    position = 'HeadFirstDecubitusRight'

                elif exam.PatientPosition == 'FFDL':
                    position = 'FeetFirstDecubitusLeft'

                elif exam.PatientPosition == 'FFDL':
                    position = 'FeetFirstDecubitusRight'

                else:
                    position = 'HeadFirstSupine'

                logging.debug('Creating beamset with name {}, machine {}, modality {}, technique {}'.
                              format(beam_name, machine, modality, technique))
                response['plans'].append(beam_name)
                beamset = plan.AddNewBeamSet(Name=beam_name,
                                             ExaminationName=exam.Name,
                                             MachineName=machine,
                                             Modality=modality,
                                             TreatmentTechnique=technique,
                                             PatientPosition=position,
                                             NumberOfFractions=response['fractions'][i],
                                             CreateSetupBeams=True,
                                             UseLocalizationPointAsSetupIsocenter=False,
                                             Comment='',
                                             RbeModelReference=None,
                                             EnableDynamicTrackingForVero=False,
                                             NewDoseSpecificationPointNames=[],
                                             NewDoseSpecificationPoints=[],
                                             RespiratoryMotionCompensationTechnique='Disabled',
                                             RespiratorySignalSource='Disabled')

                if prescriptions[i].find('roi/name') is not None and \
                        prescriptions[i].find('roi/name').text in response['targets'] and \
                        response['targets'][prescriptions[i].find('roi/name').text]['use']:
                    try:
                        roi_name = ''
                        for roi in case.PatientModel.RegionsOfInterest:
                            if roi.Name == prescriptions[i].find('roi/name').text:
                                logging.debug('Formatted prescription structure {} identified'.format(roi.Name))
                                roi_name = roi.Name
                                break

                        if roi_name == '':
                            for roi in case.PatientModel.RegionsOfInterest:
                                if roi.Name == response['targets'][prescriptions[i].find('roi/name').text]['structure']:
                                    logging.debug('Original prescription structure {} identified'.format(roi.Name))
                                    roi_name = roi.Name
                                    break

                        if roi_name != '':
                            if prescriptions[i].find('roi/type').text == 'DX':
                                vol = float(prescriptions[i].find('roi/volume').text)
                                if len(response['targets'][prescriptions[i].find('roi/name').text]['dose']) > i:
                                    dose = float(response['targets'][prescriptions[i].find('roi/name').text]['dose'][i])
                                else:
                                    dose = float(response['targets'][prescriptions[i].find('roi/name').text]['dose'][0])

                                if 'relative' in prescriptions[i].find('roi/dose').attrib:
                                    rel = float(prescriptions[i].find('roi/dose').attrib['relative'])

                                else:
                                    rel = 1

                                logging.debug('Setting ROI prescription to structure {}'.format(roi_name))
                                beamset.AddDosePrescriptionToRoi(RoiName=roi_name,
                                                                 PrescriptionType='DoseAtVolume',
                                                                 DoseVolume=vol,
                                                                 DoseValue=dose * 100,
                                                                 RelativePrescriptionLevel=rel,
                                                                 AutoScaleDose=True)

                        else:
                            logging.warning('Could not find structure {} to set prescription to on beamset {}'.
                                            format(prescriptions[i].find('roi/name').text, beam_name))

                    except Exception:
                        logging.warning('Error occurred generating prescription for beamset {}'.format(beam_name))

                break

    # Add clinical goals (first order specific, then protocol)
    status.next_step(text='Clinical goals will now be populated based on the selected protocol. You will be prompted ' +
                          'to customize these goals for this plan prior to TPO generation.')
    patient.Save()
    goals = []
    for o in response['xml'].findall('order'):
        if o.find('name').text == response['order']:
            for g in o.findall('goals/roi'):
                if (g.find('name').text in response['oars'] and response['oars'][g.find('name').text]['use']) or \
                        (g.find('name').text in response['targets'] and
                         response['targets'][g.find('name').text]['use']):
                    goals.append(g)

    for g in response['xml'].findall('goals/roi'):
        if (g.find('name').text in response['oars'] and response['oars'][g.find('name').text]['use']) or \
                (g.find('name').text in response['targets'] and
                 response['targets'][g.find('name').text]['use']):
            goals.append(g)

    for g in goals:
        roi_name = ''
        for roi in case.PatientModel.RegionsOfInterest:
            if roi.Name == g.find('name').text:
                roi_name = roi.Name
                break

        if roi_name == '':
            for roi in case.PatientModel.RegionsOfInterest:
                if (g.find('name').text in response['oars'] and
                    roi.Name == response['oars'][g.find('name').text]['structure']) or \
                        (g.find('name').text in response['targets'] and
                         roi.Name == response['targets'][g.find('name').text]['structure']):
                    roi_name = roi.Name
                    break

        if roi_name != '':

            # If this is a VX goal
            if g.find('type').text == 'VX':

                # If greater than or greater than or equal to (RS doesn't distinguish)
                if 'dir' in g.find('type').attrib and \
                        (g.find('type').attrib['dir'] == 'gt' or g.find('type').attrib['dir'] == 'ge'):
                    criteria = 'AtLeast'

                else:
                    criteria = 'AtMost'

                # If this is an absolute volume at dose goal
                if ('units' in g.find('volume').attrib and g.find('volume').attrib['units'] == 'cc') \
                        or float(g.find('volume').text) > 100:
                    goal_type = 'AbsoluteVolumeAtDose'
                    acceptance = float(g.find('volume').text)

                # Otherwise, assume this is a volume at dose goal
                else:
                    goal_type = 'VolumeAtDose'
                    acceptance = float(g.find('volume').text) / 100

                if 'units' in g.find('dose').attrib and g.find('dose').attrib['units'] == '%' and \
                        'roi' in g.find('dose').attrib and g.find('dose').attrib['roi'] in response['targets']:
                    parameter = float(g.find('dose').text) * \
                                sum(response['targets'][g.find('dose').attrib['roi']]['dose'])

                else:
                    parameter = float(g.find('dose').text) * 100

            elif g.find('type').text == 'DX':
                if 'dir' in g.find('type').attrib and \
                        (g.find('type').attrib['dir'] == 'gt' or g.find('type').attrib['dir'] == 'ge'):
                    criteria = 'AtLeast'

                else:
                    criteria = 'AtMost'

                if ('units' in g.find('volume').attrib and g.find('volume').attrib['units'] == 'cc') \
                        or float(g.find('volume').text) > 100:
                    goal_type = 'DoseAtAbsoluteVolume'
                    parameter = float(g.find('volume').text)

                else:
                    goal_type = 'DoseAtVolume'
                    parameter = float(g.find('volume').text) / 100

                acceptance = float(g.find('dose').text) * 100

            elif g.find('type').text == 'Max':
                criteria = 'AtMost'
                goal_type = 'DoseAtAbsoluteVolume'
                acceptance = float(g.find('dose').text) * 100
                if g.find('volume') is not None:
                    parameter = float(g.find('volume').text)

                else:
                    parameter = 0.03

            elif g.find('type').text == 'Min':
                criteria = 'AtLeast'
                goal_type = 'DoseAtAbsoluteVolume'
                acceptance = float(g.find('dose').text) * 100
                if g.find('volume') is not None:
                    parameter = float(g.find('volume').text)

                else:
                    parameter = 0.03

            elif g.find('type').text == 'Mean':
                goal_type = 'AverageDose'
                acceptance = float(g.find('dose').text) * 100
                parameter = None
                if 'dir' in g.find('type').attrib and \
                        (g.find('type').attrib['dir'] == 'gt' or g.find('type').attrib['dir'] == 'ge'):
                    criteria = 'AtLeast'

                else:
                    criteria = 'AtMost'

            else:
                logging.warning('Unknown goal type {} for structure {}'.format(g.find('type').text,
                                                                               g.find('name').text))
                continue

            if g.find('priority') is not None:
                priority = int(g.find('priority').text)

            else:
                priority = 1

            logging.debug('Adding {} constraint {}, {}, {}, {}, priority {}'.format(roi_name,
                                                                                    criteria,
                                                                                    goal_type,
                                                                                    acceptance,
                                                                                    parameter,
                                                                                    priority))
            plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi_name,
                                                                 GoalCriteria=criteria,
                                                                 GoalType=goal_type,
                                                                 AcceptanceLevel=acceptance,
                                                                 ParameterValue=parameter,
                                                                 IsComparativeGoal=False,
                                                                 Priority=priority)

    if len(goals) > 0:
        patient.Save()
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Plan Optimization'].Click()
        ui.TitleBar.MenuItem['Plan Optimization'].Popup.MenuItem['Plan Optimization'].Click()
        ui.Workspace.TabControl['DVH'].TabItem['Clinical Goals'].Select()
        ui.ToolPanel.TabItem._Scripting.Select()
        connect.await_user_input('Customize the clinical goals now, then continue the script')

    # Create TPO PDF
    status.next_step(text='A treatment planning order PDF is now being generated...')
    patient.Save()
    tpo = WriteTpo.pdf(patient=patient,
                       exam=exam,
                       plan=plan,
                       fields=response,
                       overwrite=True)

    # Finish up
    patient.Save()
    time.sleep(1)
    logging.debug('Script completed successfully in {:.3f} seconds'.format(time.time() - tic))
    status.finish('Script completed successfully. You may now import the saved TPO into ARIA and notify dosimetry ' +
                  'that this case is ready for planning.')
    UserInterface.MessageBox('The TPO was saved to {}'.format(tpo), 'TPO Saved')


if __name__ == '__main__':
    main()
