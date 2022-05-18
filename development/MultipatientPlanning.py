""" Multipatient Planning

    Automatic generation of a curative Head and Neck Plan.
    -Load the patient and case from a user-selected csv file
    -Loads planning structures
    -Loads Beams (or templates)
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons
    Examination and Case must exist up front

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
__date__ = '2021-Jun-'
__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10A SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import sys
import os
import csv
import logging
import xml
import pandas
import numpy as np
import random
import logging
from collections import OrderedDict, namedtuple
from io import BytesIO

import connect
import GeneralOperations
import StructureOperations
import BeamOperations
import UserInterface
from Objectives import add_goals_and_objectives_from_protocol
from OptimizationOperations import optimize_plan, iter_optimization_config_etree
import AutoPlanOperations


def output_status(path, input_filename, patient_id, case_name, plan_name, beamset_name,
                  patient_load, planning_structs, beams_load, clinical_goals_load,
                  plan_optimization_strategy_load, optimization_complete, script_status):
    """
    Write out the status of the optimization for a given patient

    Arguments:
        path {[string]} -- path for output file
        input_filename {[string]} -- name of file for input (.csv)
        patient_id {[string]} -- Patient ID under auto-planning
        case {[string]} -- RS case name
        plan_name {[string]} -- RS Plan name
        beamset_name {[string]} -- RS beamset name
        patient_load {[bool]} -- Did the patient load successfully
        planning_structs {[bool]} -- Were planning structures loaded
        beams_load {[bool]} --  Did Beams load
        clinical_goals_load {[bool]} -- Clinical Goals and Plan Objectives loaded
        plan_optimization_strategy_load {[bool]} -- An optimization strategy was loaded
        optimization_complete {[bool]} -- Optimization ended successfully
        script_status {[string]} -- Error messages if applicable, success otherwise
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
        output_message = ("PatientID" + ",\t"
                          + "Case" + ",\t"
                          + "Plan" + ",\t"
                          + "Beamset" + ",\t"
                          + "Patient Loaded" + ",\t"
                          + "Planning Structs Loaded" + ",\t"
                          + "Beams Loaded" + ",\t"
                          + "Clinical Goals Loaded" + ",\t"
                          + "Optimization Strategy Loaded" + ",\t"
                          + "Optimization Completed" + ",\t"
                          + "Plan Complete" + "\n")
        output_file.write(output_message)
        logging.debug('Header written to {}'.format(output_filename))
    #
    output_file = open(output_filename, "a+")
    if script_status is None:
        script_status = 'success'
    output_message = \
        patient_id + ",\t" \
        + case_name + ",\t" \
        + plan_name + ",\t" \
        + beamset_name + ",\t" \
        + str(patient_load) + ",\t" \
        + str(planning_structs) + ",\t" \
        + str(beams_load) + ",\t" \
        + str(clinical_goals_load) + ",\t" \
        + str(plan_optimization_strategy_load) + ",\t" \
        + str(optimization_complete) + ",\t" \
        + str(script_status) + "\n"
    output_file.write(output_message)
    output_file.close()


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
        patient_data['Error'].append('Case {} not found: {}'.format(case_name, e))
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
        return patient_data

    return patient_data


def invalidate_doses(case):
    # TODO: This one does not work on Tomo plans since MU can't be directly mutated
    # Invalidate all doses in the plan to avoid the prompt to invalidate doses
    for p in case.TreatmentPlans:
        for bs in p.BeamSets:
            for b in bs.Beams:
                original_mu = b.BeamMU
                b.BeamMU = original_mu


def test_inputs_optimization(s):
    e = []
    # Optimization configuration
    key_oc = 'optimization_config'
    wf = s.OptimizationWorkflow
    # No planning structures needed
    if not wf:
        return 'NA'


def test_inputs_planning_structure(case, s):
    e = []  # Errors
    # Planning Structures
    wf = s.PlanningStructureWorkflow  # Named workflow: planning_structure_set>name, or None for skip
    elem = 'planning_structure_set'
    key_ps = 'planning_structure_config'
    if wf:
        file = s.PlanningStructureFile
        path = s.PlanningStructurePath
        path_file = os.path.join(os.path.dirname(__file__), path, file)
        if not path:
            e.append("Empty planning structure path.")
        if not file:
            e.append("Empty planning structure file.")
        if not os.path.isfile(path_file):
            e.append("Planning structure file does not exist: {}".format(path_file))
        # Check the file for a planning_structure_set
        try:
            tree_pp = xml.etree.ElementTree.parse(
                os.path.join(os.path.dirname(__file__), path, file))
            if not tree_pp.findall(elem):
                e.append(
                    "Planning structure file {} does not contain elements: {}".format(path_file,
                                                                                      elem))
                return e
        except:
            e.append('Could not parse {}'.format(path_file))
            return e
        # Check the file for the named workflow
        try:
            dict_pp = StructureOperations.iter_planning_structure_etree(tree_pp)
        except:
            e.append("Could not convert element-tree in {} to dictionary.".format(path_file))
            return e
        # Convert the dict to pandas dataframe and see if it is empty
        df_pp = pandas.DataFrame(dict_pp[key_ps])
        if df_pp.empty:
            e.append("Could not convert dictionary in {} to dataframe.".format(path_file))
        # Slice the dataframe at the workflow name
        df_wf = df_pp[df_pp.name == wf]
        # Check if no match found
        if df_wf.empty:
            e.append("No planning_structure_set in {} with name {}".format(path_file, wf))
            return e
        # Check if more than one match is found
        if df_wf.name.count() > 1:
            e.append(">1 planning_structure_set in {} with name {}".format(path_file, wf))
            return e
        # Check the targets to be used
        plan_targets = list(s.Targets.keys())
        if plan_targets:
            all_targets_exist = StructureOperations.exists_roi(case=case,
                                                               rois=plan_targets,
                                                               return_exists=False)
            if not all(all_targets_exist):
                target_missing = []
                for i, t in enumerate(all_targets_exist):
                    if not t:
                        target_missing.append(plan_targets[i])
                e.append("Missing defined targets: {}".format(target_missing))


def merge_dict(row):
    """
    A variable number of input targets may be used in the csv file
    this function returns a dictionary that can be used to merge target columns
    Arguments:
       row {dataframe row} -- input row from the plan_data dataframe
    Returns:
       [dict] -- dictionary of the form {'PTV1_6000': 6000, ...}
    """
    target_column_exists = True
    target_columns = 0
    target_dict = OrderedDict()
    while target_column_exists:
        try:
            target_name = 'Target' + str(target_columns + 1).zfill(2)
            target_dose = 'TargetDose' + str(target_columns + 1).zfill(2)
            protocol_name = 'Protocol' + target_name
            if not np.isnan(row[target_dose]):
                target_dict[row[protocol_name]] = (row[target_name], row[target_dose], r'cGy')
                # target_dict[row[target_name]] = (row[target_dose], row[protocol_name])
            target_columns += 1
        except KeyError:
            target_column_exists = False
    return target_dict


def main():
    # Prompt the user to open a file
    browser = UserInterface.CommonDialog()
    file_csv = browser.open_file('Select a plan list file', 'CSV Files (*.csv)|*.csv')
    print('Looking in file {}'.format(file_csv))
    dtypes = {'PatientID': str, 'Case': str, 'PlanName': str, 'BeamsetName': str}
    if file_csv != '':
        plan_data = pandas.read_csv(file_csv, converters={
            'PatientID': lambda x: str(x),
            'Case': lambda x: str(x),
            'PlanName': lambda x: str(x),
            'BeamsetName': lambda x: str(x),
        })
        # Merge the target rows into a dictionary containing {[Target Name]:Dose}
        plan_data['Targets'] = plan_data.apply(lambda row: merge_dict(row), axis=1)
        # Replace all nan with ''
        plan_data = plan_data.replace(np.nan, '', regex=True)
    ## Create the output file
    print('The pandas array is {}'.format(plan_data))
    path = os.path.dirname(file_csv)

    # Cycle through the input file
    for index, row in plan_data.iterrows():
        beamset_name = row.BeamsetName
        plan_name = row.PlanName
        patient_id = row.PatientID
        case_name = row.Case
        print('loading PatientID: {i}, Case: {c}, Plan: {p}, Beamset: {b}'.format(
            i=patient_id,
            c=case_name,
            p=plan_name,
            b=beamset_name
        ))
        patient_load = False
        # If the planning structure workflow element is blank, skip planning structures
        if row.PlanningStructureWorkflow:
            planning_structs = False
        else:
            planning_structs = "NA"
        beams_load = False
        clinical_goals_load = False
        plan_optimization_strategy_load = False
        optimization_complete = False
        status_message = ''
        #
        # Read the csv into a pandas dataframe
        patient_data = AutoPlanOperations.load_patient_data(
            patient_id=patient_id,
            first_name=row.FirstName,
            last_name=row.LastName,
            case_name=case_name,
            exam_name=row.ExaminationName,
            plan_name=plan_name,
        )
        # TODO: Investigate any changes unsaved at end of script.
        patient_data['Patient'].Save()

        # Check loading status
        if patient_data['Error']:
            # Go to the next entry
            output_status(
                path=path,
                input_filename=file_csv,
                patient_id=patient_id,
                case_name=case_name,
                plan_name=plan_name,
                beamset_name=beamset_name,
                patient_load=patient_load,
                planning_structs=planning_structs,
                beams_load=beams_load,
                clinical_goals_load=clinical_goals_load,
                plan_optimization_strategy_load=plan_optimization_strategy_load,
                optimization_complete=optimization_complete,
                script_status=patient_data['Error']
            )
            continue
        else:
            patient = patient_data['Patient']
            exam = patient_data['Exam']
            case = patient_data['Case']
            plan = patient_data['Plan']
            case.SetCurrent()
            connect.get_current('Case')
            plan.SetCurrent()
            connect.get_current('Plan')
            patient_load = True
        # Check the HU to density status of this exam.
        if not exam.EquipmentInfo.ImagingSystemReference:
            exam.EquipmentInfo.SetImagingSystemReference(ImagingSystemName=row.CTSystem)
            patient.Save()

        # Invalidate all previous doses:
        invalidate_doses(case=case)

        errors_ps = test_inputs_planning_structure(case, row)
        if errors_ps:
            status_message = errors_ps
            # Go to the next entry
            output_status(
                path=path,
                input_filename=file_csv,
                patient_id=patient_id,
                case_name=case_name,
                plan_name=plan_name,
                beamset_name=beamset_name,
                patient_load=patient_load,
                planning_structs=planning_structs,
                beams_load=beams_load,
                clinical_goals_load=clinical_goals_load,
                plan_optimization_strategy_load=plan_optimization_strategy_load,
                optimization_complete=optimization_complete,
                script_status=status_message
            )
            continue
        planning_structs = AutoPlanOperations.load_planning_structures(case=case,
                                                                       filename=row.PlanningStructureFile,
                                                                       path=row.PlanningStructurePath,
                                                                       workflow_name=row.PlanningStructureWorkflow,
                                                                       translation_map=row.Targets)
        patient.Save()

        # If this beamset is found, then append 1-99 to the name and keep going
        beamset_exists = True
        while beamset_exists:
            info = plan.QueryBeamSetInfo(Filter={'Name': '^{0}'.format(beamset_name)})
            try:
                if info[0]['Name'] == beamset_name:
                    beamset_name = (beamset_name[:14]
                                    + str(random.randint(1, 99)).zfill(2)) \
                        if len(beamset_name) > 14 \
                        else beamset_name + str(random.randint(1, 99)).zfill(2)
            except IndexError:
                beamset_exists = False
        # Resolve the path to the beamset file
        path_protocols = os.path.join(os.path.dirname(__file__),
                                      row.BeamsetPath)
        # Go grab the beamset called protocol_beamset
        # This step is likely not necessary, just know exact beamset name from protocol
        beamset_etree = BeamOperations.Beams.select_element(
            set_level='beamset',
            set_type=None,
            set_elements='beam',
            filename=row.BeamsetFile,
            set_level_name=row.ProtocolBeamset,
            dialog=False,
            folder=path_protocols,
            verbose_logging=False)[0]

        beamset_defs = BeamOperations.BeamSet()
        beamset_defs.rx_target = row.Target01
        beamset_defs.number_of_fractions = row.NumberFractions
        beamset_defs.total_dose = row.TargetDose01
        beamset_defs.machine = row.Machine
        beamset_defs.iso_target = row.Isotarget
        beamset_defs.name = beamset_name
        beamset_defs.DicomName = beamset_name
        beamset_defs.modality = 'Photons'
        # Beamset elements derived from the protocol
        beamset_defs.technique = beamset_etree.find('technique').text
        beamset_defs.protocol_name = beamset_etree.find('name').text
        if beamset_defs.technique == "TomoHelical" or \
                beamset_defs.technique == "TomoDirect":
            lateral_zero = True
        else:
            lateral_zero = False

        order_name = None

        rs_beam_set = BeamOperations.create_beamset(patient=patient,
                                                    case=case,
                                                    exam=exam,
                                                    plan=plan,
                                                    dialog=False,
                                                    BeamSet=beamset_defs,
                                                    create_setup_beams=False)
        # ok, now make the beamset current
        patient.Save()
        rs_beam_set.SetCurrent()
        #
        Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
        patient_tuple = Pd(error=[],
                           patient=GeneralOperations.find_scope(level='Patient'),
                           case=GeneralOperations.find_scope(level='Case'),
                           exam=GeneralOperations.find_scope(level='Examination'),
                           db=GeneralOperations.find_scope(level='PatientDB'),
                           plan=GeneralOperations.find_scope(level='Plan'),
                           beamset=GeneralOperations.find_scope(level='BeamSet'))

        connect.get_current('BeamSet')
        beams = BeamOperations.load_beams_xml(filename=row.BeamsetFile,
                                              beamset_name=row.ProtocolBeamset,
                                              path=path_protocols)

        # Place isocenter
        try:
            beamset_defs.iso = BeamOperations.find_isocenter_parameters(
                case=case,
                exam=exam,
                beamset=rs_beam_set,
                iso_target=beamset_defs.iso_target,
                lateral_zero=lateral_zero)
        except Exception:
            logging.warning(
                'Aborting, could not locate center of {}'.format(beamset_defs.iso_target))
            sys.exit('Failed to place isocenter')
        # Parse Tomo versus VMAT
        if beamset_defs.technique == 'TomoHelical':
            if len(beams) > 1:
                logging.warning('Invalid tomo beamset in {}, more than one Tomo beam found.'.format(
                    beamset_defs.name))
            else:
                beam = beams[0]
            BeamOperations.place_tomo_beam_in_beamset(plan=plan, iso=beamset_defs.iso,
                                                      beamset=rs_beam_set, beam=beam)
            # Beams loaded successfully
            beams_load = True
        elif beamset_defs.technique == 'TomoDirect':
            BeamOperations.place_tomodirect_beams_in_beamset(plan=plan, iso=beamset_defs.iso,
                                                             beamset=rs_beam_set, beams=beams)
            # Beams loaded successfully
            beams_load = True

        elif beamset_defs.technique == 'VMAT':
            BeamOperations.place_beams_in_beamset(iso=beamset_defs.iso, beamset=rs_beam_set,
                                                  beams=beams)
            # Beams loaded successfully
            beams_load = True
        else:
            status_message.append('Unsupported beamset technique {}'.format(beamset_defs.technique))
            logging.debug('Unsupported beamset technique {}'.format(beamset_defs.technique))
        if not beams_load:
            output_status(
                path=path,
                input_filename=file_csv,
                patient_id=patient_id,
                case_name=case_name,
                plan_name=plan_name,
                beamset_name=beamset_name,
                patient_load=patient_load,
                planning_structs=planning_structs,
                beams_load=beams_load,
                clinical_goals_load=clinical_goals_load,
                plan_optimization_strategy_load=plan_optimization_strategy_load,
                optimization_complete=optimization_complete,
                script_status=status_message
            )
            continue

        patient.Save()
        rs_beam_set.SetCurrent()

        # Now add in clinical goals and objectives
        goal_file_name = row.GoalFile
        path_goals = os.path.join(os.path.dirname(__file__),
                                  row.GoalPath)
        protocol_name = row.ProtocolName
        order_name = row.OrderName
        # Translation map: {OrderedDict} protocol_target_name:(plan_target_name, dose in Gy)
        translation_map = OrderedDict()
        for k, v in row.Targets.items():
            translation_map[k] = (v[0], v[1], r'cGy')
        translation_map = AutoPlanOperations.convert_translation_map(translation_map, unit=r'Gy')
        goals_added = add_goals_and_objectives_from_protocol(
            case=case,
            plan=plan,
            beamset=rs_beam_set,
            exam=exam,
            filename=goal_file_name,
            path_protocols=path_goals,
            protocol_name=protocol_name,
            target_map=translation_map,
            order_name=order_name,
            run_status=False,
        )
        if not goals_added:
            clinical_goals_load = True
            logging.info('Clinical goals/objectives added successfully')
        else:
            for e in goals_added:
                status_message.append('{} '.format(e))
            clinical_goals_load = False

        #
        # Optimize the plan
        opt_status = AutoPlanOperations.load_configuration_optimize_beamset(
            filename=row.OptimizationFile,
            path=row.OptimizationPath,
            pd=patient_tuple,
            name=row.OptimizationWorkflow)
        if opt_status:
            beamset_info = plan.QueryBeamSetInfo(Filter={'Name': beamset_name})
            try:
                if beamset_info[0]['HasDose']:
                    optimization_complete = True
                else:
                    optimization_complete = False
                    status_message.append('Optimization unsuccessful')
            except ValueError:
                optimization_complete = False
                status_message.append('Optimization unsuccessful')
        else:
            optimization_complete = opt_status
        patient.Save()
        #
        # Write out results
        output_status(
            path=path,
            input_filename=file_csv,
            patient_id=patient_id,
            case_name=case_name,
            plan_name=plan_name,
            beamset_name=beamset_name,
            patient_load=patient_load,
            planning_structs=planning_structs,
            beams_load=beams_load,
            clinical_goals_load=clinical_goals_load,
            plan_optimization_strategy_load=plan_optimization_strategy_load,
            optimization_complete=optimization_complete,
            script_status=status_message
        )


if __name__ == '__main__':
    main()
