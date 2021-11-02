""" UW Autoplanning

    Automatic generation of a plan
    * Loads the ScriptStatus
    * Initializes a report for the script
    * Gets the current patient, case, patient database, and exam
    * User selects autoplan site
    * Selects a treatment planning order from supported list in protocols/UW/Autoplans
    * Prompts the user to set any overrides required for the plan

    Script:
    -Prompts user for protocol and order
    -Loads them from the autoplanning directory
    -Loads planning structures
    -Loads Beams
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons
    -Handle overrides
    Examination and Case must exist up front

    Testing mode:
    input_params is not None
    Bypasses user dialogs based on an input dictionary in input_params.
    Steps bypassed:


    TODO:
    -Return the result of each of the above steps as success or failure. Write result to
     log and to status
    -Output the objective value/plan params to a file for parsing
    -Add timing measurements

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
__date__ = '2021-Mar-03'
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
import xml.etree.ElementTree
import pandas
import re
from collections import OrderedDict, namedtuple
from timeit import default_timer as timer
import csv

import connect
import UserInterface
import GeneralOperations
from GeneralOperations import logcrit as logcrit
import StructureOperations
import Objectives
import BeamOperations
import AutoPlanOperations
from OptimizationOperations import optimize_plan, iter_optimization_config_etree
from PlanOperations import find_optimization_index
# TODO: move autoplan_whole_brain to library
sys.path.insert(1, os.path.join(os.path.dirname(__file__),r'../general'))
import autoplan_whole_brain
import FinalDose
# Insert the general directory into the python path to allow autoplan_whole_brain
# from Objectives import add_goals_and_objectives_from_protocol

def target_dialog(case, protocol, order, use_orders=True):
    # TODO autoload with order data, search prescription, and warn user unassigned are ignored
    # Find RS targets
    plan_targets = StructureOperations.find_targets(case=case)
    protocol_targets = []
    missing_contours = []

    # Build second dialog
    target_inputs = {'00_nfx':'Number of fractions'}
    target_initial = {}
    target_datatype = {'00_nfx':'text'}
    target_options = {}
    target_required = list('00_nfx')
    if use_orders:
        goal_locations = (protocol.findall('./goals/roi'), order.findall('./goals/roi'))
        if order.find('prefix') and "Site" not in order.find('prefix').text:
            site = order.find('prefix').text
        else:
            target_inputs['00_site'] = 'Enter site abbreviation, e.g. BreL for left breast'
            target_datatype['00_site'] = 'text'
            target_required.append('00_site')
    else:
        goal_locations = (protocol.findall('./goals/roi'))
    # Use the following loop to find the targets in protocol matching the names above
    i = 1
    for s in goal_locations:
        for g in s:
            g_name = g.find('name').text
            # Priorities should be even for targets and append unique elements only
            # into the protocol_targets list
            if int(g.find('priority').text) % 2 == 0 and g_name not in protocol_targets:
                protocol_targets.append(g_name)
                k = str(i)
                # Python doesn't sort lists....
                k_name = k.zfill(2) + 'Aname_' + g_name
                k_dose = k.zfill(2) + 'Bdose_' + g_name
                target_inputs[k_name] = 'Match a plan target to ' + g_name
                target_options[k_name] = plan_targets
                target_datatype[k_name] = 'combo'
                target_required.append(k_name)
                target_inputs[
                    k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                target_required.append(k_dose)
                i += 1
                # Exact matches get an initial guess in the dropdown
                for t in plan_targets:
                    if g_name == t:
                        target_initial[k_name] = t

    target_dialog = UserInterface.InputDialog(
        inputs=target_inputs,
        title='Input Target Dose Levels',
        datatype=target_datatype,
        initial=target_initial,
        options=target_options,
        required=[])
    #print
    response = target_dialog.show()
    if response == {}:
        logging.info('Target dialog cancelled by user')
        sys.exit('Target dialog cancelled')

    # Process inputs
    nominal_dose = 0
    translation_map = {}
    for k, v in target_dialog.values.items():
        if k =='00_nfx':
            num_fx = int(v)
        elif k =='00_site':
            site = str(v)
        elif len(v) > 0:
            i, p = k.split("_", 1)
            if p not in translation_map:
                translation_map[p] = [None] * 3
            if 'name' in i:
                # Key name will be the protocol target name
                translation_map[p][0] = v
            if 'dose' in i:
                # Append _dose to the key name
                pd = p + '_dose'
                # Not sure if this loop is still needed
                translation_map[p][1] = (float(v) / 100.)
                translation_map[p][2] = 'Gy'
    return (site, num_fx,translation_map)

def find_beamset_element(protocol, beamset_name):
    beamset_match = []
    for b in protocol.findall('beamset'):
        if b.find('name').text == beamset_name:
            beamset_match.append(b)
    if len(beamset_match) == 1:
        return beamset_match[0]
    else:
        return None

def beamset_dialog(protocol, order_targets):
    # Available beamsets
    beamsets = []
    for b in protocol.findall('beamset/name'):
        beamsets.append(b.text)
    # If one beamset is in the xml file, then prompt for machine names only
    if len(beamsets) == 1:
        beamset_name = beamsets[0]
        beamset_etree = find_beamset_element(protocol, beamset_name = beamset_name)
        if 'Tomo' in beamset_etree.find('technique').text:
            machines = GeneralOperations.get_all_commissioned(machine_type='Tomo')
        else:
            machines = GeneralOperations.get_all_commissioned(machine_type='VMAT')
        inputs={'m' : 'Select Machine'}
        datatype={'m' : 'combo'}
        initial ={}
        options = { 'm' : machines}
        required = ['m']
        logging.debug('inputs {}'.format(inputs))
        logging.debug('datatypes {}'.format(datatype))
        logging.debug('initial {}'.format(initial))
        logging.debug('options {}'.format(options))
    else:
        beamset_name = None
        machines = GeneralOperations.get_all_commissioned()
        inputs={'bs': 'Select Beamset', 'm' : 'Select Machine'}
        datatype={'bs': 'combo', 'm' : 'combo'}
        initial ={'bs': beamsets[0]}
        options = {'bs': beamsets, 'm' : machines}
        required = ['bs', 'm']

    inputs['iso_t'] = 'Isocenter Position'
    initial['iso_t'] = 'All_PTVs'
    datatype['iso_t'] = 'combo'
    options['iso_t'] = order_targets
    required.append('iso_t')

    #
    # Beamset dialog
    selected_beam_parameters = UserInterface.InputDialog(
        inputs=inputs,
        title = 'Beamset Configuration',
        datatype= datatype,
        initial = initial,
        options = options,
        required = required)
    response = selected_beam_parameters.show()
    # Close on cancel
    if response == {}:
        logging.info('Autoload cancelled by user. Beamset data not selected')
        sys.exit('Beamset data not selected. Process cancelled.')
    # Parse responses
    if not beamset_name:
        beamset_name = selected_beam_parameters.values['bs']
    iso_target = selected_beam_parameters.values['iso_t']
    machine = selected_beam_parameters.values['m']
    return (beamset_name, iso_target, machine)

def autoplan(testing_bypass_dialogs = {}):

    ap_report = {}
    #
    # In testing mode, skip the dialog prompts
    if testing_bypass_dialogs:
        input_protocol_name = testing_bypass_dialogs['protocol_name']
        input_order_name=testing_bypass_dialogs['order_name']
        num_fx =testing_bypass_dialogs['num_fx']
        site = testing_bypass_dialogs['site']
        translation_map = testing_bypass_dialogs['translation_map']
        beamset_name = testing_bypass_dialogs['beamset_name']
        iso_target = testing_bypass_dialogs['iso_target']
        machine = testing_bypass_dialogs['machine']
    else:
        input_protocol_name = None
        input_order_name = None
    #
    # Hard-coded path to protocols
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    autoplan_folder = r'AutoPlans'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder, institution_folder, autoplan_folder)
    #
    # Create status steps for dialog
    script_steps = {
        0:('Select Protocol (Site)','Choose main protocol for autoplan'),
        1:('Select Treatment Planning Order','Choose the treatment planning order we are using'),
        2:('Assign Targets/Doses to TPO, Declare number of fractions','Match the protocol targets to current plan'),
        3:('Select Beamset','Chose the beamset you want to load'),
        4:('Add a plan','Building the plan'),
        5:('Load beamset','Beamset specified is being loaded'),
        6:('Assign any overrides', 'Review the densities in use in the plan and assign material values'),
        # 6:('Review and assign any overrides', '<name>_Override_TissueTypes are being overridden'),
        7:('Set the sim-fiducial point','Make sure the localization point matches BBs'),
        8:('Select any directional blocking','Ensure the Entrance/Exit is selected for blocked structures'),
        9:('Support Structure Loading','Ensure the support structures are properly placed'),
        10:('Load Planning Structures','Loading rings, normals, otvs etc'),
        11:('Loading goals','Load goals from the TPO you selected'),
        12:('Optimize Plan','Optimizing plan. Copy and finish')
    }
    steps = []
    instruct = []
    for k, v in script_steps.items():
        steps.append(v[0])
        instruct.append(v[1])

    auto_status = UserInterface.ScriptStatus(
        steps=steps,
        docstring=__doc__,
        help=__help__)
    # Initialize times
    ap_report['time_all'] =  [None] * 2
    ap_report['time_user'] = [None] * 2
    ap_report['time_plan']= [None] * 2
    ap_report['time_roi']=  [None] * 2
    ap_report['time_goals']= [None] * 2
    ap_report['time_opt']=  [None] * 2
    ap_report['time_final_dose']=  [None] * 2
    # Start the clock
    ap_report['time_all'][0] = timer()
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = GeneralOperations.find_scope(level='Examination'),
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = None,
            beamset = None)

    # Start user time
    ap_report['time_user'][0] = timer()
    #
    # Select the protocol
    i = 0
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    (protocol_file, protocol) = AutoPlanOperations.select_protocol(folder=path_protocols,
                                            protocol_name=input_protocol_name)
    protocol_name = protocol.find('name').text
    logging.debug('Selected protocol:{} for loading from file:{}'.format(protocol_name,protocol_file))
    #
    # If the protocol_name is UW WholeBrain execute the wholebrain script and quit
    if protocol_name == "UW WholeBrain":
        autoplan_whole_brain.main()
        sys.exit("Script complete")
    #
    # Select the TPO
    auto_status.next_step(text=script_steps[i][1])
    i += 1

    order = AutoPlanOperations.select_order(protocol,order_name=input_order_name)
    order_name = order.find('name').text
    logging.critical("Treatment Planning Order selected: {}".format(order.find('name').text))
    #
    # Determine the protocol prescription parameters
    rx = AutoPlanOperations.find_rx(order)
    #
    # Match the protocol targets and doses to the beamset the user is making
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    if not testing_bypass_dialogs:
        # Prompt user for target map
        (site, num_fx, translation_map) = target_dialog(case=pd.case,protocol=protocol, order=order, use_orders=True)
    #
    # Log results of the user target/dose assignments
    log_str = ""
    translation_map = AutoPlanOperations.convert_translation_map(translation_map,unit=r'cGy')
    for k, v in rx.rois.items():
        try:
            log_str += '[{p}->{pl}, {pd}->{pld}] '.format(
                     p=k,pd=v,pl=translation_map[k][0],pld=translation_map[k][1])
        except KeyError:
            log_str += '[{p}->Unmapped, {pd}->Unmapped]'.format(p=k,pd=v)
    logcrit('Number of fractions protocol->beamset: [{}->{}]'.format(rx.fx, num_fx))
    logcrit('Target mapping of [protocol->beamset]: {}'.format(log_str))
    #
    # Find all target names to be used
    assigned_targets=[v[0] for v in translation_map.values() if v[0] ]
    for a in assigned_targets:
        logging.debug('Assigned targets are {}'.format(a))
        logging.debug('Assigned target {} is None {}'.format(a,(a is None)))
    #
    # Next we need the number of fractions, the beamset to load, and the isocenter position.
    #
    # Isocenter position
    available_targets = StructureOperations.find_targets(case=pd.case)
    if 'All_PTVs' not in available_targets:
        available_targets.append('All_PTVs')

    # TODO: Raystation currently does not support selection of blocked structs
    # via script. Activate this dialog eventually.
    # block_rois = select_blocking(case=pd.case,protocol=protocol,order=order)

    # TODO: Move to a select function like that one above
    # TODO: Sort machines by technique
    # Machines
    machines = GeneralOperations.get_all_commissioned(machine_type=None)
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    #
    # Add beamset
    if not testing_bypass_dialogs:
        (beamset_name, iso_target, machine) = beamset_dialog(protocol, available_targets)
    logcrit('User selected Beamset:{bs}, machine:{m}, Isocenter Position:{iso}'.format(
                bs=beamset_name, m=machine, iso=iso_target))
    beamset_defs = BeamOperations.BeamSet()
    # Beamset element
    for b in protocol.findall('beamset'):
        if b.find('name').text == beamset_name:
            beamset_etree = b
            break
    # Start plan building
    ap_report['time_plan'][0] = timer()
    # Populate the beamset definitions
    beamset_defs.description = beamset_etree.find('description').text
    beamset_defs.rx_target = translation_map[rx.target][0]#rx.target
    beamset_defs.rx_volume = rx.idl
    beamset_defs.number_of_fractions = num_fx
    beamset_defs.total_dose = translation_map[rx.target][1]# rx.dose
    beamset_defs.machine = machine
    beamset_defs.iso_target = iso_target
    # Build ALL_PTVs if needed
    if iso_target =='All_PTVs':
        StructureOperations.make_all_ptvs(
            patient=pd.patient,
            case=pd.case,
            exam=pd.exam,
            sources = assigned_targets
        )

    # Beamset elements derived from the protocol
    beamset_defs.technique = beamset_etree.find('technique').text
    beamset_defs.protocol_name = beamset_etree.find('name').text
    for t in order.findall('prescription/technique'):
        if 'technique' in t.attrib and t.attrib['technique'] == beamset_defs.technique:
            technique_elem = t
            break
    if not machine:
        beamset_defs.machine = technique_elem.attrib['machine']
    beamset_defs.modality = technique_elem.attrib['modality']
    code = technique_elem.attrib['code']
    beamset_defs.name = site[0:4] + '_' + code + '_Auto'
    plan_name = site[0:4] + '_' + code + '_Auto'
    new_plan_name = site[0:4] + '_' + code + '_R0A0'
    beamset_defs.DicomName = beamset_defs.name
    if beamset_defs.technique == "TomoHelical":
        setup_fields = False
        lateral_zero = True
    else:
        setup_fields = True
        lateral_zero = False
    #
    # TODO Output steps for a future autoplan
    # (last_name,first_name) = str(pd.Patient.Name).split("^")
    # out_dict = {
    #     'LastName':last_name,
    #     'FirstName':first_name,
    #     'PatientID':pd.Patient.PatientID,
    #     'Case':pd.Case.Name,
    #     'ExaminationName':pd.exam.Name,
    #     'Diagnosis',
    #     'CTSystem','PlanName','BeamsetName','NumberFractions','NumberTargets',
    #     'Target01','TargetDose01','ProtocolTarget01','Target02','TargetDose02',
    #     'ProtocolTarget02','Target03','TargetDose03','ProtocolTarget03','Target04',
    #     'TargetDose04','ProtocolTarget03','BeamsetPath','BeamsetFile',
    #     'ProtocolBeamset','Machine','Isotarget','PlanningStructurePath',
    #     'PlanningStructureFile','PlanningStructureWorkflow','GoalPath'
    #     'GoalFile','ProtocolName','OrderName','OptimizationPath','OptimizationFile','OptimizationWorkflow'
    #  }
    #  out_message =

    # location = r'Q:\\RadOnc\RayStation\RayScripts\dev_logs\AutoPlanning'
    # out_dir = order.find('prefix').text + '_' + code
    # os_dir = os.path.join(location,out_dir)
    # file_name = os.join(os_dir,
    #                     order.find('prefix').text + '_' + code + '_Auto' '.csv')
    # if not os.path.isdir(os_dir):
    #     os.mkdir(os_dir)
    #     file_out = open(file_name,"w")
    #     file_out.write(header)
    # elif os.path.isfile(file_name):

    #
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    # Load the existing plan or create a new one
    try:
        info = pd.case.QueryPlanInfo(Filter={'Name': plan_name})
        if info[0]['Name'] == plan_name:
            pd = pd._replace(plan = pd.case.TreatmentPlans[plan_name])
    except IndexError:
        pd.case.AddNewPlan(
            PlanName=plan_name,
            PlannedBy='H.A.L.',
            Comment='Diagnosis',
            ExaminationName=pd.exam.Name,
            AllowDuplicateNames=False
        )
        pd = pd._replace(plan = pd.case.TreatmentPlans[plan_name])
        # Plan creation modification requires a patient save

    pd.patient.Save()
    pd.plan.SetCurrent()
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    # Load beamset
    rs_beam_set = BeamOperations.create_beamset(patient=pd.patient,
                                                case=pd.case,
                                                exam=pd.exam,
                                                plan=pd.plan,
                                                dialog=False,
                                                BeamSet=beamset_defs,
                                                create_setup_beams=setup_fields,
                                                rename_existing=True)
    # ok, now make the beamset current
    pd.patient.Save()
    rs_beam_set.SetCurrent()
    pd = pd._replace(beamset = connect.get_current('BeamSet'))
    # Set beams from the protocol
    beams = BeamOperations.load_beams_xml(filename=protocol_file,
                                          beamset_name=beamset_name,
                                          path=path_protocols)
    # Place isocenter
    try:
        beamset_defs.iso = BeamOperations.find_isocenter_parameters(
            case=pd.case,
            exam=pd.exam,
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
        BeamOperations.place_tomo_beam_in_beamset(plan=pd.plan, iso=beamset_defs.iso,
                                                  beamset=rs_beam_set, beam=beam)
        # Beams loaded successfully
        beams_load = True
    elif beamset_defs.technique == 'VMAT':
        BeamOperations.place_beams_in_beamset(iso=beamset_defs.iso, beamset=rs_beam_set,
                                              beams=beams)
        # Beams loaded successfully
        beams_load = True
    else:
        logging.debug('Unsupported beamset technique {}'.format(beamset_defs.technique))

    #
    # Beam building complete
    ap_report['time_plan'][1] = timer()
    #
    # Set any overrides
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    connect.await_user_input(
         'Set any required material overrides and continue the script.')
    # TODO: The following line of code can be activated in RS 11
    # AutoPlanOperations.set_overrides(pd)

    #
    # Place the SimFiducial Point
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    if testing_bypass_dialogs:
        logging.debug('SimFiducial placement skipped for test')
    else:
        AutoPlanOperations.place_fiducial(pd=pd, poi_name='SimFiducials')
    #
    # Set any blocking
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Plan optimization'].Button_Plan_optimization.Click()
        ui.TabControl_Modules.TabItem['Plan optimization'].Button_Plan_optimization.Click()
        ui.Workspace.TabControl['Objectives/constraints'].TabItem['Protect'].Select()
    except:
        logging.debug("Could not click on the patient protection window")
    if testing_bypass_dialogs:
        logging.info('Blocking page skipped for testing')
    else:
        connect.await_user_input(
            'Navigate to the Plan design page, set any blocking.')
    #
    if testing_bypass_dialogs:
        logging.info('Custom goal additions skipped for debugging.')
    else:
        connect.await_user_input( 'Add any custom goals from the TPO.')
    #
    # Add support structures here
    # Support structures come from beamset data.
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    strip_roi_support = beamset_etree.find('roi_support').text
    strip_roi_support = strip_roi_support.replace(" ","")
    strip_roi_support = strip_roi_support.strip()
    beamset_defs.support_roi = strip_roi_support.split(",")
    if testing_bypass_dialogs:
        logging.info('Loading support {} skipped for testing'.format(beamset_defs.support_roi))
    else:
        AutoPlanOperations.load_supports(pd=pd,supports=beamset_defs.support_roi)
    # time_user complete
    ap_report['time_user'][1] = timer()
    # Trim supports
    StructureOperations.trim_supports(patient=pd.patient,
                                      case=pd.case,
                                      exam=pd.exam)

    # Planning structures added
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    ap_report['time_roi'][0] = timer()
    # Use cGy naming convention
    translation_map = AutoPlanOperations.convert_translation_map(translation_map,unit=r'cGy')
    ps_elem = protocol.find('planning_structure_set')
    workflow_name = ps_elem.find('name').text
    ps_result = AutoPlanOperations.load_planning_structures(
        case=pd.case,
        filename = protocol_file,
        path = path_protocols,
        workflow_name = workflow_name,
        translation_map = translation_map
    )
    ap_report['time_roi'][1] = timer()
    #
    # Add goals and objectives
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    ap_report['time_goals'][0] = timer()
    translation_map = AutoPlanOperations.convert_translation_map(translation_map, unit =r'Gy')
    goals_added = Objectives.add_goals_and_objectives_from_protocol(
            case=pd.case,
            plan=pd.plan,
            exam=pd.exam,
            beamset=rs_beam_set,
            filename=protocol_file,
            path_protocols=path_protocols,
            protocol_name=protocol_name,
            target_map=translation_map,
            order_name=order_name,
            run_status=False,
        )
    ap_report['time_goals'][1] = timer()
    #
    # Optimize using the protocol optimization technique for this delivery type
    auto_status.next_step(text=script_steps[i][1])
    i += 1
    pd.patient.Save()
    ap_report['time_opt'][0] = timer()
    opt_status = AutoPlanOperations.load_configuration_optimize_beamset(
        filename = protocol_file,
        path = path_protocols,
        pd = pd,
        technique = beamset_defs.technique,
        bypass_user_prompts = True
    )
    ap_report['time_opt'][1] = timer()
    # Enable autoscale
    # Find current Beamset Number and determine plan optimization
    opt_indx = find_optimization_index(plan=pd.plan, beamset=pd.beamset,
                                       verbose_logging=False)
    # Turn on autoscale
    if 'Tomo' not in beamset_defs.technique:
        pd.plan.PlanOptimizations[opt_indx].AutoScaleToPrescription = True
        compute_dose_message = PlanOperations.compute_dose(beamset=pd.beamset,dose_algorithm='CCDose')
        logging.info(compute_dose_message)
    else:
        logging.warning('Autoscaling not possible')
    #
    # Run Final Dose Calculation
    ap_report['time_final_dose'][0] = timer()
    try:
        FinalDose.final_dose(site=site[0:4],technique=beamset_defs.description)
    except:
        logging.debug('Final Dose run unsuccessful')
    ap_report['time_final_dose'][1] = timer()
    #
    pd.patient.Save()
    ap_report['time_all'][1] = timer()
    #
    # Save the patient
    pd.patient.Save()
    # Copy the plan and make current
    pd.case.CopyPlan(PlanName=plan_name,NewPlanName=new_plan_name,KeepBeamSetNames=False)
    pd.patient.Save()
    pd.case.TreatmentPlans[new_plan_name].SetCurrent()
    pd.case.TreatmentPlans[new_plan_name].BeamSets[new_plan_name].SetCurrent()
    # Update doses
    # pd.beamset.FractionDose.UpdateDoseGridStructures()
    # pd.case.TreatmentPlans[new_plan_name].Beamsets[new_plan_name].FractionDose.UpdateDoseGridStructures()
    # pd.plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
    logging.info('Autoplanning Report')
    logging.info('Time in user operations {} s'.format(ap_report['time_user'][1]-ap_report['time_user'][0]))
    logging.info('Time building plan {} s'.format(ap_report['time_plan'][1]-ap_report['time_plan'][0]))
    logging.info('Time making planning structs {} s'.format(ap_report['time_roi'][1]-ap_report['time_roi'][0]))
    logging.info('Time adding goals {} s'.format(ap_report['time_goals'][1]-ap_report['time_goals'][0]))
    logging.info('Time optimizing {} s'.format(ap_report['time_opt'][1]-ap_report['time_opt'][0]))
    logging.info('Time in FinalDose {} s'.format(ap_report['time_final_dose'][1]-ap_report['time_final_dose'][0]))
    logging.info('Time in script {} s'.format(ap_report['time_all'][1]-ap_report['time_all'][0]))
    return(pd)

    #
    # TODO: Export the autoplan and objectives, weights and goal values
    #
    # TODO: Ask user if they want to anonymize and save. If yes, pull up the TPL and save

def main():
    autoplan()

if __name__ == '__main__':
    main()