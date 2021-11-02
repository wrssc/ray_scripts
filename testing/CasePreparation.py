""" Case Preparation

    TODO: Add automatic backup to anonymous file

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2021-Apr-13'
__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
__credits__ = ['']
__help__ = 'TODO: No Help'
import sys
import os
import logging
from collections import namedtuple
import connect
import GeneralOperations
import StructureOperations

sys.path.append(os.path.join(os.path.dirname(__file__), "..//structure_definition"))
import StructureMatching

def load_patient_data(patient_id, first_name, last_name, case_name, exam_name, plan_name):
    """ Query's database for plan, case, and exam. Returns them as a dict. Saves patient if a
        new plan is created.

    Arguments:
        patient_id {string} -- Patient's ID in database
        first_name {string} -- Patient first name
        last_name {string} -- Patient Last Name
        case_name {string} -- RS case name
        exam_name {string} -- RS Exam Name
        plan_name {string} -- RS plan

    Returns:
        dict -- {'Case': RS Case Object, 'Exam' RS Exam object,
                 'Plan': RS Plan Object - either existing or new}
    """
    # Initialize return variable
    patient_data = {'Error': [],
                    'Case': None,
                    'Patient': None,
                    'Exam': None,
                    'Plan': None}
    db = connect.get_current("PatientDB")
    # Find the patient in the database
    patient_info = db.QueryPatientInfo(
        Filter={
            'FirstName': '^{0}$'.format(first_name),
            'LastName': '^{0}$'.format(last_name),
            'PatientID': '^{0}$'.format(patient_id)
        }
    )
    if len(patient_info) != 1:
        patient_data['Error'] = ['Patient {} {}, ID: {} not found'.format(
            first_name, last_name, patient_id
        )]
        return patient_data
    else:
        # Set the appropriate parameters for this patient
        patient = db.LoadPatient(PatientInfo=patient_info[0])
        patient_data['Patient'] = patient
    # Load case
    # See if the case exists
    try:
        case = patient.Cases[case_name]
        patient_data['Case'] = case
    except Exception as e:
        patient_data['Error'].append('Case {} not found: {}'.format(case_name,e))
        return patient_data
    #
    # Load examination
    try:
        info = db.QueryExaminationInfo(PatientInfo=patient_info[0],
                                       Filter={'Name': exam_name})
        if info[0]['Name'] == exam_name:
            ## Raystation sets the value of an anonymized CT ID to -sys.maxint -1
            ##   causing the ID key to be non unique.
            ## info_name = {'Name': exam_name}
            ## exam = case.LoadExamination( ExaminationInfo = info_name)
            exam = case.Examinations[exam_name]
            patient_data['Exam'] = exam
    except IndexError:
        patient_data['Error'].append('Exam {} not found'.format(exam_name))
        return patient_data
    #
    # Load the plan indicated
    # If the plan is found, cool. just make it current
    if plan_name:
        try:
            info = case.QueryPlanInfo(Filter={'Name': plan_name})
            if info[0]['Name'] == plan_name:
                patient_data['Plan'] = case.TreatmentPlans[plan_name]
        except IndexError:
            case.AddNewPlan(
                PlanName=plan_name,
                PlannedBy='H.A.L.',
                Comment='Diagnosis',
                ExaminationName=exam.Name,
                AllowDuplicateNames=False
            )
            patient_data['Plan'] = case.TreatmentPlans[plan_name]
            # Plan creation modification requires a patient save
            patient.Save()
        try:
            test_plan = case.TreatmentPlans[plan_name]
        except IndexError:
            patient_data['Error'].append('Plan {} not found'.format(plan_name))
    else:
        try:
            patient_data['Plan'] = case.TreatmentPlans[0]
        except:
            patient_data['Plan'] = None

    return patient_data

def main():
    # Load overlap volume data
    # Run Tg-263 script
    # Identify targets
    # Select TPO used
    # Output csv file
    #
    # Initialize return variable
    patient_id = 'ZZUWQA_30Jan2020_Pelvis'
    first_name = 'Test'
    last_name = 'ZZUWQA_Testing_Tomo3D'
    exam_name = 'CT 1'

    for i in range(0,30):

        case_name = 'Case ' + str(i + 1)
        print('Case is {}'.format(case_name))
        patient_data = load_patient_data(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                case_name=case_name,
                exam_name=exam_name,
                plan_name=None,
                )
        print('Proceeding with patient {}, case {}'.format(patient_data['Patient'],
                                                           patient_data['Case']))
        patient_data['Case'].SetCurrent()
        if patient_data['Plan']:
            patient_data['Plan'].SetCurrent()
        StructureMatching.main()
        connect.await_user_input(
        'Fill in input.csv with target data and output.csv with clinical plan')
        patient_data['Patient'].Save()


#    Pd = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
 #   pd = Pd(error = [],
 #          patient = GeneralOperations.find_scope(level='Patient'),
 #          case = GeneralOperations.find_scope(level='Case'),
 #          exam = GeneralOperations.find_scope(level='Examination'),
 #          db = GeneralOperations.find_scope(level='PatientDB'),
 #          plan = None,
 #          beamset = None)
    # sources = ['Heart']
    # for i in range(1,10):
    #     mm = str(i) *
    #     n = sources[0] + "_" + str(i)
    #     delta = float(i)*0.5
    #     try:
    #         w = StructureOperations.make_wall(wall=n, sources=sources,
    #                                       delta=delta, patient=pd.patient,
    #                                       case=pd.case, examination=pd.exam,
    #                                       inner=False, struct_type="Undefined")
    #     except Exception as e:
    #         logging.debug('e is {}'.format(e))
    #     sources.append(n)


if __name__ == '__main__':
    main()