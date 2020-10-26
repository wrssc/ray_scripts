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
        sino_array = numpy.asarray(sinogram)
        # Mod Factor = Average / Max LOT
        
        # Return a dataframe for json output
        df = pd.DataFrame({'time': time, 
                           'rp':rp, 
                           'total_travel':total_travel,
                           'couch_speed':couch_speed,
                           'sinogram':pd.Series(sinogram)},
                           index=[0])
        
        

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
        output_filename = os.path.join(path, patient_id
                                            + '_'
                                            + beamset_name
                                            + '.json')
        

    # Clinical goals
    