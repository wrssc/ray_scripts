""" Multi-Patient VMAT Optimization
    
    Using a user specified csv file mulitple patients are loaded and optimized 
    using the OptimizePlan.py function defined in ray_scripts/library
    
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
__date__ = '2018-04-06'
__version__ = '1.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.0.0'
__maintainer__ = 'One maintainer'
__email__ =  'maintainer@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['This friend', 'That friend', 'etc']
import sys
import csv
from connect import *
sys.path.insert(0,r"/Volumes/Physics/bayliss/RayStation/Python Scripts/Testing_AutoOptimize")
from OptimizePlan import OptimizePlan
from collections import namedtuple

''' Attempt to load and optimize a patient '''

# Plan optimization parameters

OptimizationParameters = { 
    "InitialMaxIt"	:	50,
    "InitialIntIt"	:	10,
    "SecondMaxIt"		:	30,
    "SecondIntIt"		:	15,
    "DoseDim1"		:	0.5,
    "DoseDim2"		:	0.4,
    "DoseDim3"		:	0.3,
    "DoseDim4"		:	0.2,
    "NIterations"		:	12}

# Open the csv delimited file containing the list of patients to be reoptimized
# Ensure that the first row is a header for the columns
Row = namedtuple('Row',('FirstName','LastName','PatientID','Case','PlanName','BeamsetName'))
#filecsv =r"Z:\Physics\bayliss\RayStation\Python Scripts\Testing_AutoOptimize\Test_FileRead.csv"
filecsv =r"Test_FileRead.csv"
with open(filecsv,'r') as f:
    r = csv.reader(f, delimiter=',')
    r.next() # Skip header
    rows = [Row(*l) for l in r]

file_object = open("output.txt",'w')
output_message = "PatientID"  + "\tPlan Name" + "\tBeamSet Name" + "\tStatus\n"
file_object.write(output_message)
file_object.close()
# Header was skipped.  Start with rows[0], the first data line in the csv
i = 0
db = get_current("PatientDB")
for Row in rows:
#for i in range(1,10):
    last_name = rows[i].LastName
    first_name = rows[i].FirstName
    patient_id = rows[i].PatientID
    plan_name = rows[i].PlanName
    beamset_name = rows[i].BeamsetName
    case_name = rows[i].Case
    print "Beamset = ",beamset_name
    # Select patient based on name
    patient_info = db.QueryPatientInfo(Filter={
        'FirstName':'^{0}$'.format(first_name), 'LastName':'^{0}$'.format(last_name),'PatientID':'^{0}$'.format(patient_id)})
    if len(patient_info) != 1: # If no (or more than one) patient matches the criteria, exit the script
        print "No patient named {0} {1} found in the database".format(first_name, last_name)
        sys.exit()
    try: 
        patient = db.LoadPatient(PatientInfo=patient_info[0])
        case = patient.Cases[case_name]
        case.SetCurrent()
        plan = case.TreatmentPlans[plan_name]
        plan.SetCurrent()
        beamset = plan.BeamSets[beamset_name]
        beamset.SetCurrent()
        OptimizePlan(patient, case, plan, beamset, OptimizationParameters)
        patient.Save()
        file_object = open("output.txt",'a')
        output_message = patient_id + "\t" + plan_name + "\t" + beamset_name + "\tsuccess\n"
        file_object.write(output_message)
        file_object.close()
    except:
        file_object = open("output.txt",'a')
        output_message = patient_id + "\t" + plan_name + "\t" + beamset_name + "\tFAIL\n"
        file_object.write(output_message)
        file_object.close()
    i += 1
