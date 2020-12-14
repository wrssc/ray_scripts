""" Export Plan Data

Open a patient from a patient list (csv)
Load patient
Export:
    -Clinical goals
    -DVH for each contour
    -Beam Parameters
"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '19-Oct-2020'
__version__ = '1.0.0'
__status__ = 'Validation'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8.0b SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2020, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/wrssc/ray_scripts'
__credits__ = []

import connect
import os
import logging
import pandas as pd
import numpy
import UserInterface
import json
import StructureOperations

def output_plan_data(path, input_filename, patient_id, case_name, plan_name, beamset_name,
                  ):
    """
    Write out the status of the optimization for a given patient

    Arguments:
        path {[string]} -- path for output file
        input_filename {[string]} -- name of file for input (.csv)
        patient_id {[string]} -- Patient ID under auto-planning
        case {[string]} -- RS case name
        plan_name {[string]} -- RS Plan name
        beamset_name {[string]} -- RS beamset name
    """

    # Create the output file
    path = os.path.dirname(input_filename)
    output_filename = os.path.join(path, input_filename.replace(".csv", "_output.txt"))
    # Determine if a filename exists and is empty
    if os.path.exists(output_filename) and os.stat(output_filename).st_size != 0:
        output_file = open(output_filename, "a+")
        logging.debug('Output directed to {}'.format(output_filename))
    else:
        # The file does not currently exist or is empty
        output_file = open(output_filename, "w+")
        # Write the header
        output_message = ( "PatientID" + ",\t"
                          + "Case" + ",\t"
                          + "Plan" + ",\t"
                          + "Beamset" + ",\t"
                          + "\n")
        output_file.write(output_message)
        logging.debug('Header written to {}'.format(output_filename))
    #
    output_file = open(output_filename, "a+")
    output_message = \
        patient_id + ",\t" \
        + case_name + ",\t" \
        + plan_name + ",\t" \
        + beamset_name + ",\t" \
        + "\n"
    output_file.write(output_message)
    output_file.close()

def load_patient_data(patient_id, first_name, last_name, case_name, exam_name, plan_name, beamset_name):
    """ Query's database for plan, case, and exam. Returns them as a dict. Saves patient if a 
        new plan is created.

    Arguments:
        patient_id {string} -- Patient's ID in database
        first_name {string} -- Patient first name
        last_name {string} -- Patient Last Name
        case_name {string} -- RS case name
        exam_name {string} -- RS Exam Name
        plan_name {string} -- RS plan
        beamset_name {string} -- RS Beamset

    Returns:
        dict -- {'Case': RS Case Object, 'Exam' RS Exam object,
                 'Plan': RS Plan Object - either existing or new}
    """
    # Initialize return variable
    patient_data = {'Error': [],
                    'Case': None,
                    'Patient': None,
                    'Exam': None,
                    'Plan': None,
                    'Beamset': None}
    db = connect.get_current("PatientDB")
    # Find the patient in the database
    patient_info = db.QueryPatientInfo(
        Filter={
            #'FirstName': '^{0}$'.format(first_name),
            #'LastName': '^{0}$'.format(last_name),
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
    except SystemError:
        patient_data['Error'].append('Case {} not found'.format(case_name))
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
    try:
        info = case.QueryPlanInfo(Filter={'Name': plan_name})
        if info[0]['Name'] == plan_name:
            patient_data['Plan'] = case.TreatmentPlans[plan_name]
    except IndexError:
        patient_data['Error'].append('Plan {} not found').format(plan_name)
        return patient_data
    #
    # Load beamset
    try:
        test_beamset = case.TreatmentPlans[plan_name].BeamSets[beamset_name]
        patient_data['Beamset'] = test_beamset
    except IndexError:
        patient_data['Error'].append('Beamset {} not found'.format(beamset_name))
        return patient_data

    return patient_data

def gather_tomo_beam_params(beamset):
    # Compute time, rotation period, couch speed, pitch
    #   mod factor
    for b in beamset.Beams:
        number_segments = 0
        total_travel = 0
        max_lot = 0
        sinogram = []
        for s in b.Segments:
            number_segments += 1
            leaf_pos = []
            for l in s.LeafOpenFraction:
                leaf_pos.append(l)
            sinogram.append(leaf_pos)
        # Total Time: Projection time x Number of Segments = Total Time
        time = b.BeamMU * number_segments
        # Rotation period: Projection Time * 51
        rp = b.BeamMU * 51.
        # Couch Speed: Total Distance Traveled / Total Time
        total_travel = b.Segments[number_segments-1].CouchYOffset \
                      -b.Segments[0].CouchYOffset
        couch_speed = total_travel / time
        # Pitch: Distance traveled in rotation / field width
        
        # Convert sinogram to numpy array
        sino_array = numpy.array(sinogram)
        # Mod Factor = Average / Max LOT
        mod_factor = sino_array.max()/numpy.mean(sino_array !=0)
        # Declare the tomo dataframe
        dtypes = numpy.dtype([
                    ('time', float), # Total time of plan [s]
                    ('total_travel', float), # Couch travel [cm]
                    ('couch_speed',float), # Speed of couch [cm/s]
                    ('sinogram', object), # List of leaf openings
                    ('mod_factor', float) # Max/Ave_Nonzero
        ])
        data = numpy.empty(0, dtype=dtypes)
        df = pd.DataFrame(data)
        # Return a dataframe for json output
        df.at[0,'time'] = time
        df.at[0,'rp'] = rp
        df.at[0,'total_travel'] = total_travel
        df.at[0,'couch_speed'] = couch_speed
        df.at[0,'sinogram'] = sino_array
        df.at[0,'mod_factor'] = mod_factor
    return df

def get_dvh(roi_name, plan, precision=None):
    # roi_name = name of the roi
    # precision = relative volume precision
    if not precision:
        precision = 0.01 # output 1% increments
    plan_dose = plan.TreatmentCourse.TotalDose
    number_dvh_points = int(1./precision) + 1
    vols = [precision * x for x in range(0,number_dvh_points)]
    dose_values = plan_dose.GetDoseAtRelativeVolumes(RoiName=roi_name, RelativeVolumes=vols)
    dose_array = numpy.column_stack([vols,dose_values])
    return dose_array

def clinical_goal_rois(plan):
    # return all roi's which have a clinical goal
    goal_rois = []
    for e in plan.EvaluationSetup.EvaluationFunctions:
        e_roi = e.ForRegionOfInterest.Name
        if e_roi not in goal_rois:
            goal_rois.append(e_roi)
    return goal_rois

def get_clinical_goal(plan, roi_name=None):
    # Return all clinical goals for an roi or all rois as a dictionary of dictionary
    # Need the Roi, acceptance level, parameter value, type, priority
    # clinical goal value, evaluate clinical goal
    clinical_goal = {}
    i_g = 0

    # Search the list of evaluation functions 
    evaluation_functions = plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions
    for e in evaluation_functions:
        logging.debug('Tracking eval function {}'.format(e.ForRegionOfInterest.Name))
        if roi_name == e.ForRegionOfInterest.Name or not roi_name: 
            clinical_goal[i_g] = {}
            clinical_goal[i_g]['roi'] = e.ForRegionOfInterest.Name
            clinical_goal[i_g]['roi_type'] = e.ForRegionOfInterest.Type
            clinical_goal[i_g]['acceptance_level'] = e.PlanningGoal.AcceptanceLevel
            clinical_goal[i_g]['goal_criteria'] = e.PlanningGoal.GoalCriteria
            clinical_goal[i_g]['parameter_value'] = e.PlanningGoal.ParameterValue
            clinical_goal[i_g]['priority'] = e.PlanningGoal.Priority
            clinical_goal[i_g]['type'] = e.PlanningGoal.Type
            clinical_goal[i_g]['goal_value'] = e.GetClinicalGoalValue()
            clinical_goal[i_g]['goal_evaluation'] = e.EvaluateClinicalGoal()
            logging.debug('Goal found for roi {}'.format(e.ForRegionOfInterest.Name))
            i_g += 1
    return clinical_goal


def main():
    # 
    # Load the current RS database
    ## db = connect.get_current("PatientDB")
    # Prompt the user to open a file
    browser = UserInterface.CommonDialog()
    file_csv = browser.open_file('Select a plan list file', 'CSV Files (*.csv)|*.csv')
    if file_csv != '':
        plan_data = pd.read_csv(file_csv)
    ## Create the output file
    path = os.path.dirname(file_csv)

    ## output_filename = os.path.join(path, file_csv.replace(".csv","_output.txt"))
    # Cycle through the input file
    for index, row in plan_data.iterrows():
        beamset_name = row.BeamsetName
        plan_name = row.PlanName
        patient_id = row.PatientID
        case_name = row.Case
        source_plan = row.SourcePlan
        source_beamset = row.SourceBeamset
        patient_load = False
        #
        # Read the csv into a pandas dataframe
        patient_data = load_patient_data(
            patient_id=patient_id,
            first_name=None,
            #first_name=row.FirstName,
            last_name=None,
            #last_name=row.LastName,
            case_name=case_name,
            exam_name=row.ExaminationName,
            plan_name=plan_name,
            beamset_name = beamset_name
        )
        if not patient_data['Error']:
            logging.debug('Loading Patient:{pt}, Case:{c}, Exam{e}, Plan:{p}, Beamset{b}'.format(
                pt = patient_data['Patient'].Name,
                c = patient_data['Case'].CaseName,
                e = patient_data['Exam'].Name,
                p = patient_data['Plan'].Name,
                b = patient_data['Beamset'].DicomPlanLabel
            ))
        else:
            logging.debug('Error in loading. {e}'.format(e=patient_data['Error']))
            continue
        output_filename = os.path.join(path, patient_id
                                            + '_'
                                            + case_name
                                            + '_'
                                            + plan_name
                                            + '_'
                                            + beamset_name
                                            + '.json')
        # Start building the data dictionary
        data_dict = {'PatientID': patient_id,
                     'Case':case_name,
                     'PlanName':plan_name,
                     'BeamsetName':beamset_name}
        # If there are no goals in this plan, look for another copy of this plan with
        # the optional name given in the input.
        # Copy goals to clinical plan
        dest_eval = patient_data['Plan'].TreatmentCourse.EvaluationSetup
        try:
            dest_eval.EvaluationFunctions[0]
            clinical_goals_missing = False
        except ValueError:
            clinical_goals_missing = True
            
        if clinical_goals_missing:
            try:
                source_eval = patient_data['Case'].TreatmentPlans[source_plan].TreatmentCourse.EvaluationSetup
                for e in source_eval.EvaluationFunctions:
                    dest_eval.CopyClinicalGoal(FunctionToCopy=e)
            except KeyError:
                logging.debug('Unable to find plan {} for goal copy'.format(source_plan))
        patient_data['Patient'].Save()
        # Update patient dose data
        patient_data['Beamset'].FractionDose.UpdateDoseGridStructures()
        patient_data['Plan'].TreatmentCourse.TotalDose.UpdateDoseGridStructures()
        # Find any structure for which there was a clinical goal
        data_dict['goals']= get_clinical_goal(patient_data['Plan'], roi_name=None)
        # Get target and roi DVH data
        target_list = StructureOperations.find_targets(patient_data['Case'])
        rois_list = StructureOperations.find_organs_at_risk(patient_data['Case'])
        for t in target_list:
           data = get_dvh(roi_name=t, plan = patient_data['Plan'],precision=0.001)
           list_data = data.tolist()
           data_dict[t + '_DVH'] = list_data
        for r in rois_list:
           data = get_dvh(roi_name=r, plan = patient_data['Plan'],precision=0.001)
           list_data = data.tolist()
           data_dict[r + '_DVH'] = list_data

        with open(output_filename, 'w') as fp:
            json.dump(data_dict, fp)
        with open(output_filename, 'r') as fp:
            in_data_dict = json.load(fp)




    # Clinical goals
    