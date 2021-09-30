""" Test-Autoplan.py

    Versions:
    00.00.00 Original submission

    TODO:
    - Extend the initial code to a loop over all test patients
    Known Issues:

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2021-06-23'

__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = ''
__raystation__ = '10'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'

from collections import namedtuple
import copy
import sys
import os
import json
import logging
import math
import connect
sys.path.insert(1, os.path.join(os.path.dirname(__file__),r'../development'))
import AutoPlan
import AutoPlanOperations
import GeneralOperations
from GeneralOperations import logcrit as logcrit
import UserInterface

def inputs(index):
    if index == 0:
        return { 'patient_id': 'ZZUWQA_30Jun2021_Pelvis',
              'first_name': 'Autoplanning',
              'last_name': 'Script_Testing',
              'case_name': 'Case 1',
              'exam_name': 'CT 1',
              'protocol_name': 'UW Tomo3D',
              'order_name': 'Multiple Target Tomo3D',
              'num_fx': 22,
              'site': 'Pelv',
              'translation_map': {'PTV_p':('PTV_Hip_5500', 5500.,r'cGy')},
              'beamset_name': 'Tomo3D_FW50',
              'iso_target': 'PTV_Hip_5500',
              'machine': 'HDA0477',
              'expected': {'dicom_plan_label':'Pelv_3DC_Clin',
                         'dose_at_point':249.99977111816406,
                         'is_clinical': True,
                         'function_value': 0.37199426732751846}
              }
    elif index == 1:
        return { 'patient_id': 'ZZUWQA_30Jun2021_Pelvis',
              'first_name': 'Autoplanning',
              'last_name': 'Script_Testing',
              'case_name': 'Case 2',
              'exam_name': 'CT 1',
              'protocol_name': 'UW Tomo3D',
              'order_name': 'Multiple Target Tomo3D',
              'num_fx': 25,
              'site': 'Pelv',
              'translation_map': {'PTV_p' :('PTV_5040', 5040., r'cGy'),
                                  'PTV_p2':('PTV_4500', 4500., r'cGy')},
              'beamset_name': 'Tomo3D_FW50',
              'iso_target': 'All_PTVs',
              'machine': 'HDA0477',
              'expected': {'dicom_plan_label':'Pelv_3DC_Clin',
                         'dose_at_point':249.99969482421875,
                         'is_clinical': True,
                         'function_value': 0.04005642677956052}
              }


def load_patient(plan_dict):
    patient_data = AutoPlanOperations.load_patient_data(
            patient_id = plan_dict['patient_id'],
            first_name = plan_dict['first_name'],
            last_name = plan_dict['last_name'],
            case_name = plan_dict['case_name'],
            exam_name = plan_dict['exam_name'],
            plan_name = None,
            beamset_name = None)
    return patient_data

def set_all_current(patient_data):
    # Initialize return variable
    Pd = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    patient_data['Case'].SetCurrent()
    connect.get_current('Case')
    # Get current patient, case, exam
    pd = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = GeneralOperations.find_scope(level='Examination'),
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = None,
            beamset = None)
    return pd

def test_result(pd, expected):
    # Test result
    result = {}
    tolerance = 1e-10
    # Shortened RS objects
    beam_doses = pd.beamset.FractionDose.BeamDoses[0]
    objective = pd.plan.PlanOptimizations[0].Objective
    for k, v in expected.items():
        if k == 'dicom_plan_label':
            if pd.beamset.DicomPlanLabel == v:
                result[k] = True
            else:
                result[k] = False
        if k == 'dose_at_point':
            if math.isclose(beam_doses.DoseAtPoint.DoseValue,v,rel_tol=tolerance) :
                result[k] = True
            else:
                result[k] = False
        if k == 'is_clinical':
            if beam_doses.DoseValues.IsClinical == v:
                result[k] = True
            else:
                result[k] = False
        if k == 'function_value':
            if math.isclose(objective.FunctionValue.FunctionValue,v,rel_tol=tolerance):
                result[k] = True
            else:
                result[k] = False
    return result

def main():
    browser = UserInterface.CommonDialog()
    path = browser.folder_browser(title='Select a location for test output')
    file_name = os.path.join(path,'Test_Output.txt')
    with open(file_name, 'w') as file:
        file.write('Testing Results\n') # use `json.loads` to do the reverse
    index = 1
    plan1 = inputs(index)
    # Output Initial Data
    with open(file_name, 'a') as file:
        file.write(json.dumps(plan1)) # use `json.loads` to do the reverse
        file.write("\n")
    # Load patient
    patient_data = load_patient(plan1)
    #with open(file_name, 'a') as file:
    #    file.write('AutoPlanning test Loading: Patient: {}, Case: {}, Exam: {}'.format(
    #        patient_data['Patient'], patient_data['Case'], patient_data['Exam']))
    #    file.write("\n")
    # Set the loaded data current
    pd_in = set_all_current(patient_data)
    # Begin autoplan
    logging.info('Autoplanning test started on PatientID: {}, Case: {}, Exam: {}'.format(
        pd_in.patient.PatientID, pd_in.case.CaseName, pd_in.exam.Name))
    # Run autoplan and get result
    pd = AutoPlan.autoplan(input_params = plan1)

    result = test_result(pd, plan1['expected'])
    with open(file_name, 'a') as file:
        file.write(json.dumps(result)) # use `json.loads` to do the reverse
        file.write("\n")



if __name__ == '__main__':
    main()
