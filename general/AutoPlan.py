""" UW Templated Planning

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
    TODO: Add a single pysimple gui for this whole program.
    TODO: Add SRS specific planning structure strategy


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
import re
import logging
import connect
import library.StructureOperations as StructureOperations
import library.Objectives as Objectives
import library.BeamOperations as BeamOperations
import library.AutoPlanOperations as AutoPlanOperations
import library.autoplan_whole_brain as autoplan_whole_brain
import FinalDose
from collections import namedtuple
from timeit import default_timer as timer
from library.UserInterface import InputDialog, ScriptStatus
from library.GeneralOperations import logcrit as logcrit
from library.api.api_utils import get_all_commissioned, find_scope
from library.PlanOperations import find_optimization_index, compute_dose


# from Objectives import add_goals_and_objectives_from_protocol


def find_protocol_targets(goal_locations, derived_keywords):
    """
    Extracts protocol targets from the XML data, excluding derived targets.

    Args:
        goal_locations (tuple): XML nodes containing goal information.
        derived_keywords (list): List of regex patterns for derived targets.

    Returns:
        list: Lists of protocol targets and derived targets.
    """
    protocol_targets, derived_targets = [], []
    for s in goal_locations:
        for g in s:
            if int(g.find('priority').text) % 2 == 0:
                g_name = g.find('name').text
                if any(re.search(r, g_name) for r in derived_keywords):
                    derived_targets.append(g_name)
                else:
                    d_name = g.find('dose').attrib.get('roi', "")
                    if g_name not in protocol_targets:
                        protocol_targets.append(g_name)
                    elif d_name and d_name not in protocol_targets:
                        protocol_targets.append(d_name)
    return protocol_targets, derived_targets


def build_target_inputs(protocol_targets, plan_targets):
    """
    Constructs the input dictionaries for the target dialog.

    Args:
        protocol_targets (list): List of protocol targets.
        plan_targets (list): List of plan targets.

    Returns:
        dict: Dictionaries for target inputs, initial values, data types, options, and required fields.
    """
    target_inputs, target_initial, target_datatype, target_options, target_required = {}, {}, {}, {}, []
    i = 1
    for p in protocol_targets:
        k = str(i).zfill(2)
        k_name = f'{k}Aname%{p}'
        k_dose = f'{k}Bdose%{p}'
        target_inputs[k_name] = f'Match a plan target to {p}'
        target_inputs[k_dose] = f'Provide dose for protocol target: {p} Dose in cGy'
        target_options[k_name] = plan_targets
        target_datatype[k_name] = 'combo'
        if i == 1:
            target_required.extend([k_name, k_dose])
        if p in plan_targets:
            target_initial[k_name] = p
        i += 1
    return target_inputs, target_initial, target_datatype, target_options, target_required


def process_target_dialog_response(response):
    """
    Processes the user's response from the target dialog.

    Args:
        response (dict): User response from the dialog.

    Returns:
        tuple: Processed site, number of fractions, and translation map.
    """
    if response == {}:
        logging.info('Target dialog cancelled by user')
        sys.exit('Target dialog cancelled')

    translation_map = {}
    site, num_fx = None, None
    for k, v in response.items():
        if k == '00_nfx':
            num_fx = int(v)
        elif k == '00_site':
            site = str(v)
        elif v:
            i, p = k.split("%", 1)
            if p not in translation_map:
                translation_map[p] = [None] * 3
            if 'name' in i:
                translation_map[p][0] = v
            if 'dose' in i:
                translation_map[p][1] = float(v) / 100.0
                translation_map[p][2] = 'Gy'
    logging.debug('Translation map: {}'.format(translation_map))
    return site, num_fx, translation_map


def target_dialog(case, protocol, order, use_orders=True):
    derived_keywords = ['^.*_Eval.*?$', '^.*_EZ.*?$']
    plan_targets = StructureOperations.find_targets(case=case)  # Find RS targets
    goal_locations = (protocol.findall('./goals/roi'), order.findall('./goals/roi')) if use_orders else (
        protocol.findall('./goals/roi'),)
    protocol_targets, derived_targets = find_protocol_targets(goal_locations, derived_keywords)

    # Build target input dialog
    target_inputs, target_initial, target_datatype, target_options, target_required = build_target_inputs(
        protocol_targets, plan_targets)

    # Additional fields based on 'use_orders'
    if use_orders and order.find('prefix') and "Site" not in order.find('prefix').text:
        site = order.find('prefix').text
    else:
        target_inputs['00_site'] = 'Enter site abbreviation, e.g. BreL for left breast'
        target_datatype['00_site'] = 'text'
        target_required.append('00_site')
    target_inputs['00_nfx'] = 'Number of fractions'
    target_datatype['00_nfx'] = 'text'
    target_required.append('00_nfx')

    # Display dialog
    target_dose_level_dialog = InputDialog(
        inputs=target_inputs,
        title='Input Target Dose Levels',
        datatype=target_datatype,
        initial=target_initial,
        options=target_options,
        required=target_required)

    # Process dialog response
    response = target_dose_level_dialog.show()
    return process_target_dialog_response(response)


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
        beamset_etree = find_beamset_element(protocol, beamset_name=beamset_name)
        if 'Tomo' in beamset_etree.find('technique').text:
            machines = get_all_commissioned(machine_type='Tomo')
        else:
            machines = get_all_commissioned(machine_type='VMAT')
        inputs = {'m': 'Select Machine'}
        datatype = {'m': 'combo'}
        initial = {}
        options = {'m': machines}
        required = ['m']
        logging.debug('inputs {}'.format(inputs))
        logging.debug('datatypes {}'.format(datatype))
        logging.debug('initial {}'.format(initial))
        logging.debug('options {}'.format(options))
    else:
        beamset_name = None
        machines = get_all_commissioned()
        inputs = {'bs': 'Select Beamset', 'm': 'Select Machine'}
        datatype = {'bs': 'combo', 'm': 'combo'}
        initial = {'bs': beamsets[0]}
        options = {'bs': beamsets, 'm': machines}
        required = ['bs', 'm']

    inputs['iso_t'] = 'Isocenter Position'
    initial['iso_t'] = 'All_PTVs'
    datatype['iso_t'] = 'combo'
    options['iso_t'] = order_targets
    required.append('iso_t')

    #
    # Beamset dialog
    selected_beam_parameters = InputDialog(
        inputs=inputs,
        title='Beamset Configuration',
        datatype=datatype,
        initial=initial,
        options=options,
        required=required)
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
    return beamset_name, iso_target, machine


def multi_autoplan(multi_plan_parameters):
    for m in multi_plan_parameters:

        # Shortened key mappings for autoplan parameters
        a = {
            'protocol_name': m['protocol_name'],
            'order_name': m['order_name'],
            'exam': m.get('exam', None),
            'num_fx': m['num_fx'],
            'site': m['site'],
            'machine': m['machine'],
            'translation_map': m.get('translation_map', None),
            'plan_name': m.get('plan_name', None),
            'beamset_name': m.get('beamset_name', None),
            'beamset_template': m.get('beamset_template', None),
            'iso_target': m.get('iso_target', None),
            'iso_poi': m.get('iso_poi', None),
            'iso': m.get('iso', None),
            'user_prompts': m.get('user_prompts', True),
            'beamset_exists_skip': m.get('beamset_exists_skip', False),
            'multi_isocenter': m.get('multi_isocenter', False),
            'optimize': m.get('optimize', True),
            'optimization_instructions': m.get('optimization_instructions', None),
            'ignore_status': True,
        }

        # Logging the parameters in a structured and readable format
        logging.debug(
            f"Starting task for Beamset {a['beamset_name']} on Exam {a['exam']}:\n"
            f"\tProtocol: {a['protocol_name']}, Order: {a['order_name']}\n"
            f"\tSite: {a['site']}, Fractions: {a['num_fx']}, Machine: {a['machine']}\n"
            f"\tIsocenter: Iso: {a['iso']}, Target: {a['iso_target']}, POI: {a['iso_poi']}\n"
            f"\tBeamset Template: {a['beamset_template']}\n"
            f"\tOptimization Enabled: {a['optimize']}, Instructions: {a['optimization_instructions']}\n"
            f"\tOther Settings: Translation Map: {a['translation_map']},\n "
            f"\tUser Prompts: {a['user_prompts']}, "
            f"\tBeamset Skip: {a['beamset_exists_skip']}, "
            f"\tMulti-Isocenter: {a['multi_isocenter']}"
        )

        if not a['beamset_exists_skip']:
            m['rso'] = autoplan(autoplan_parameters=a)
        # If optimization is required, prompt user to continue
        if m['optimize']:
            connect.await_user_input('Completed optimization of current beamset. Please review and continue')
    return multi_plan_parameters


def remove_existing_supports(case, beamset):
    """
    Remove existing support structures from the beamset.
    Args:
        case: The current case object.
        beamset: The current beamset object.
    Returns:
        None
    """
    existing_supports = StructureOperations.find_types(case, roi_type='Support')
    existing_supports += StructureOperations.find_types(case, roi_type='Fixation')
    if existing_supports:
        for s in existing_supports:
            try:
                logging.debug(f'Excluding support structure {s} from beamset {beamset.DicomPlanLabel}')
                beamset.ExcludeRoiFromRadiationSet(RoiName=s)
            except Exception as e:
                logging.warning(f'Error excluding support structure {s} from beamset: {e}')


def include_supports_in_beamset(beamset, supports):
    """
    Include support structures in the beamset radiation set.
    This function attempts to include each support structure in the beamset's radiation set.
    If a support structure is already included, it will log a debug message and continue.
    If an error occurs while including a support structure, it will log a warning message.

    Args:
        beamset: The current beamset object.
        supports: A list of support structure names to be included in the beamset.

    Returns:
        None

    """
    for support in supports:
        try:
            logging.debug(f'Loaded support structure {support} and assigned to beamset'
                          f' {beamset.DicomPlanLabel}')
            beamset.IncludeRoiInRadiationSet(RoiName=support)
        except Exception as e:
            if "The ROI is already included in the beam set" in str(e):
                logging.debug(f'Support structure {support} already included in '
                              f'radiation set {beamset.DicomPlanLabel}')
                pass
            else:
                logging.warning(f'Error loading support structure {support}: {e}')


def copy_plan_set_copy_current(rso, new_plan_name):
    # Copy the plan and create a named tuple for return
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    rso.case.CopyPlan(PlanName=rso.plan.Name,
                      NewPlanName=new_plan_name,
                      KeepBeamSetNames=False)
    rso.patient.Save()
    rso.case.TreatmentPlans[new_plan_name].SetCurrent()
    rso.case.TreatmentPlans[new_plan_name].BeamSets[new_plan_name].SetCurrent()
    #
    # Create the return variable noting that people get whiny about _replace and we should
    # eventually get around to using dataclasses
    pd_out = Pd(error=[],
                patient=find_scope(level='Patient'),
                case=find_scope(level='Case'),
                exam=find_scope(level='Examination'),
                db=find_scope(level='PatientDB'),
                plan=rso.case.TreatmentPlans[new_plan_name],
                beamset=rso.case.TreatmentPlans[new_plan_name].BeamSets[new_plan_name])
    return pd_out


def autoplan(autoplan_parameters, **kwargs):
    ap_report = {}
    background = ""
    derived_keywords = ['^.*_Eval.*?$', '^.*_EZ.*?$']
    #
    # In testing mode, skip the dialog prompts
    if autoplan_parameters:
        input_protocol_name = autoplan_parameters['protocol_name']
        input_order_name = autoplan_parameters['order_name']
        num_fx = autoplan_parameters['num_fx']
        site = autoplan_parameters['site']
        exam_name = autoplan_parameters.get('exam', None)
        translation_map = autoplan_parameters.get('translation_map', None)
        beamset_template = autoplan_parameters.get('beamset_template', None)
        beamset_name = autoplan_parameters.get('beamset_name', None)
        plan_name = autoplan_parameters.get('plan_name', None)
        iso_target = autoplan_parameters.get('iso_target', None)
        iso_poi = autoplan_parameters.get('iso_poi', None)
        iso_dict = autoplan_parameters.get('iso', {})
        multi_isocenter = autoplan_parameters.get('multi_isocenter', False)
        machine = autoplan_parameters['machine']
        user_prompts = autoplan_parameters.get('user_prompts', True)
        optimize = autoplan_parameters.get('optimize', True)
        ignore_status = autoplan_parameters.get('ignore_status', False)
        multi_plan_parameters = kwargs.get('beamset_list', [])
        optimization_instructions = autoplan_parameters.get('optimization_instructions', {})
        if optimization_instructions:
            background = optimization_instructions.get('optimize_with_background', "")
            lock_dose_grid = optimization_instructions.get('lock_dose_grid', False)
    else:
        input_protocol_name = None
        input_order_name = None
        num_fx = None
        user_prompts = True
        beamset_etree = None
        beamset_template = None
        beamset_name = None
        plan_name = None
        iso_target = None
        iso_poi = None
        exam_name = None
        machine = None
        multi_isocenter = None
        iso_dict = {'type': None, 'target': None}
        translation_map = {}
        optimize = True
        lock_dose_grid = False
        ignore_status = False
        multi_plan_parameters = []
    logging.debug(f'Optimization Parameters: user_prompts:'
                  f'{user_prompts}, optimize {optimize}')
    #
    # Hard-coded path to protocols
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    autoplan_folder = r'AutoPlans'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder, institution_folder, autoplan_folder)

    path_to_output = os.path.normpath(
        "Q:\\RadOnc\\RayStation\\RayScripts\\AutoPlanData")
    #
    # Create status steps for dialog
    auto_status = None
    status_index = ""
    script_steps = []
    if not ignore_status:
        script_steps = {
            0: ('Select Protocol (Site)', 'Choose main protocol for autoplan'),
            1: ('Select Treatment Planning Order',
                'Choose the treatment planning order we are using'),
            2: ('Assign Targets/Doses to TPO, Declare number of fractions',
                'Match the protocol targets to current plan'),
            3: ('Select Beamset', 'Chose the beamset you want to load'),
            4: ('Add a plan', 'Building the plan'),
            5: ('Load beamset', 'Beamset specified is being loaded'),
            6: ('Assign any overrides',
                'Review the densities in use in the plan and assign material values'),
            # 6:('Review and assign any overrides',
            # '<name>_Override_TissueTypes are being overridden'),
            7: ('Set the sim-fiducial point',
                'Make sure the localization point matches BBs'),
            8: (
                'Select any blocking/bolus',
                'Ensure the Entrance/Exit is selected for blocked structures'),
            9: ('Support Structure Loading',
                'Ensure the support structures are properly placed'),
            10: ('Load Planning Structures', 'Loading rings, normals, otvs etc'),
            11: ('Loading goals', 'Load goals from the TPO you selected'),
            12: ('Optimize Plan', 'Optimizing plan. Copy and finish')
        }
        steps = []
        instruct = []
        for k, v in script_steps.items():
            steps.append(v[0])
            instruct.append(v[1])

        auto_status = ScriptStatus(
            steps=steps,
            docstring=__doc__,
            help=__help__)
    # Initialize times
    ap_report['time_all'] = [None] * 2
    ap_report['time_user'] = [None] * 2
    ap_report['time_plan'] = [None] * 2
    ap_report['time_roi'] = [None] * 2
    ap_report['time_goals'] = [None] * 2
    ap_report['time_opt'] = [None] * 2
    ap_report['time_final_dose'] = [None] * 2
    # Start the clock
    ap_report['time_all'][0] = timer()
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    exam = None
    if exam_name:
        case = find_scope(level='Case')
        for exam in case.Examinations:
            if exam.Name == exam_name:
                break
    rso = Pd(error=[],
             patient=find_scope(level='Patient'),
             case=find_scope(level='Case'),
             exam=exam if exam else find_scope(level='Examination'),
             db=find_scope(level='PatientDB'),
             plan=None,
             beamset=None)

    # Start user time
    ap_report['time_user'][0] = timer()

    #
    # Select the protocol
    if not ignore_status:
        status_index = 0
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    logging.debug("Loading file {}".format(input_protocol_name))
    (protocol_file, protocol) = AutoPlanOperations.select_protocol(folder=path_protocols,
                                                                   protocol_name=input_protocol_name)
    protocol_name = protocol.find('name').text
    logging.debug(f'Selected protocol:{protocol_name} for loading from file:{protocol_file}')
    # If the protocol_name is UW WholeBrain execute the whole brain script and quit
    if protocol_name == "UW WholeBrain":
        autoplan_whole_brain.main()
        return
    # Select the TPO
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1

    logging.debug("Loading order {}".format(input_order_name))
    order = AutoPlanOperations.select_order(protocol, order_name=input_order_name)
    order_name = order.find('name').text
    logcrit(f"Treatment Planning Order selected: {order.find('name').text}")
    #
    # Determine the protocol prescription parameters
    rx = AutoPlanOperations.find_rx(order)
    #
    # Match the protocol targets and doses to the beamset the user is making
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    if not translation_map:
        # Prompt user for target map
        (site, num_fx, translation_map) = target_dialog(case=rso.case,
                                                        protocol=protocol,
                                                        order=order,
                                                        use_orders=True)
    #
    # Log results of the user target/dose assignments
    log_str = ""
    translation_map = AutoPlanOperations.convert_translation_map(
        translation_map, unit=r'cGy')
    for k, v in rx.rois.items():
        try:
            log_str += '[{p}->{pl}, {pd}->{pld}] '.format(
                p=k, pd=v, pl=translation_map[k][0], pld=translation_map[k][1])
        except KeyError:
            log_str += '[{p}->Unmapped, {pd}->Unmapped]'.format(p=k, pd=v)
    logcrit(f'Number of fractions protocol->beamset: [{rx.fx}->{num_fx}]')
    logcrit(f'Target mapping of [protocol->beamset]: {log_str}')
    #
    # Find all target names to be used
    assigned_targets = [v[0] for v in translation_map.values() if v[0]]
    #
    # Next we need the number of fractions, the beamset to load, and the isocenter position.
    #
    # Isocenter position
    available_targets = StructureOperations.find_targets(case=rso.case)
    # Add All_PTVs to the list of available targets
    if 'All_PTVs' not in available_targets:
        available_targets.append('All_PTVs')

    # TODO: Raystation currently does not support selection of blocked structs
    # via script. Activate this dialog eventually.
    # block_rois = select_blocking(case=rso.case,protocol=protocol,order=order)

    # TODO: Sort machines by technique
    # Machines
    _ = get_all_commissioned(machine_type=None)
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    #
    # Add beamset
    if not beamset_template:
        (beamset_template, iso_target, machine) = beamset_dialog(protocol,
                                                                 available_targets)
    logcrit(
        f'User selected Beamset:{beamset_template}, machine:{machine},'
        f'Isocenter Position:{iso_target}')
    beamset_defs = BeamOperations.BeamSet()
    # Beamset element
    # I think we want to grab a preferred beamset name out of autoplan file or be able to take as
    # input
    # Look for a beamset_template call, if one is found, get the template from beamset_templates dir
    # TODO add modality here based on machine. User chose the machine, so we should be able to
    #   match to the machine attribute in the technique tag of the prescription tag in the order
    delivery_technique = delivery_modality = None
    p = order.find('prescription')
    for t in p.findall('technique'):
        if t.attrib['machine'] == machine:
            delivery_technique = t.attrib['technique']
            delivery_modality = t.attrib['modality']
            break
    if not delivery_modality and not delivery_technique:
        raise RuntimeError('Technique and status are not found in TPO prescription template')
    beamsets = BeamOperations.load_beamsets(beamset_type=delivery_technique,
                                            beamset_modality=delivery_modality)
    beamset_etree = technique_elem = None
    for bt in order.findall('beamset_template'):
        beamset_etree = BeamOperations.find_beamset_element(beamsets)
    # Look for a hard coded beamset in this file.
    for b in protocol.findall('beamset'):
        if b.find('name').text == beamset_template:
            beamset_etree = b
            break

    # Start plan building
    ap_report['time_plan'][0] = timer()
    # Populate the beamset definitions
    beamset_defs.description = beamset_etree.find('description').text
    #
    # We will have some rx structures that will not be created yet.
    beamset_defs.rx_target = translation_map[rx.target][0]  # rx.target
    beamset_defs.rx_volume = rx.idl
    beamset_defs.number_of_fractions = num_fx
    beamset_defs.total_dose = translation_map[rx.target][1]  # rx.dose
    beamset_defs.machine = machine
    beamset_defs.iso_target = iso_target
    beamset_defs.iso_poi = iso_poi
    # Build ALL_PTVs if needed

    if iso_target == 'All_PTVs':
        filtered_list = []
        for ast_tar in assigned_targets:
            derived_sources = [re.search(r, ast_tar) for r in derived_keywords]
            logging.debug(f'Derived sources {derived_sources}')
            if not any(derived_sources):
                filtered_list.append(ast_tar)
        logging.debug(f'Filtered List {filtered_list}')
        StructureOperations.make_all_ptvs(
            patient=rso.patient,
            case=rso.case,
            exam=rso.exam,
            sources=filtered_list
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
    if not beamset_name:
        beamset_defs.name = site[0:4] + '_' + code + '_Auto'
    else:
        beamset_defs.name = beamset_name
    if not plan_name:
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
    # (last_name,first_name) = str(rso.Patient.Name).split("^")
    # out_dict = {
    #     'LastName':last_name,
    #     'FirstName':first_name,
    #     'PatientID':rso.Patient.PatientID,
    #     'Case':rso.Case.Name,
    #     'ExaminationName':rso.exam.Name,
    #     'Diagnosis',
    #     'CTSystem','PlanName','BeamsetName','NumberFractions','NumberTargets',
    #     'Target01','TargetDose01','ProtocolTarget01','Target02','TargetDose02',
    #     'ProtocolTarget02','Target03','TargetDose03','ProtocolTarget03','Target04',
    #     'TargetDose04','ProtocolTarget03','BeamsetPath','BeamsetFile',
    #     'ProtocolBeamset','Machine','Isotarget','PlanningStructurePath',
    #     'PlanningStructureFile','PlanningStructureWorkflow','GoalPath'

    #     'GoalFile','ProtocolName','OrderName','OptimizationPath','OptimizationFile',
    #     'OptimizationWorkflow'
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
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    # Load the existing plan or create a new one
    try:
        info = rso.case.QueryPlanInfo(Filter={'Name': plan_name})
        if info[0]['Name'] == plan_name:
            rso = rso._replace(plan=rso.case.TreatmentPlans[plan_name])
            logging.debug(f'Plan {rso.plan.Name} found and loaded')
    except IndexError:
        rso.case.AddNewPlan(
            PlanName=plan_name,
            PlannedBy='H.A.L.',
            Comment='Diagnosis',
            ExaminationName=rso.exam.Name,
            AllowDuplicateNames=False
        )
        rso = rso._replace(plan=rso.case.TreatmentPlans[plan_name])
        logging.debug(f'Plan {plan_name} created')
        # Plan creation modification requires a patient save

    rso.patient.Save()
    rso.plan.SetCurrent()
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    if multi_isocenter:
        logging.debug(f'Creating a beamset using the following definitions: '
                      f'{beamset_defs.technique}, {beamset_defs.name}')
        logging.debug(f'All beamset definitions:'
                      f'{beamset_defs.technique}, {beamset_defs.name}, {beamset_defs.DicomName}, '
                      f'{beamset_defs.protocol_name}, {beamset_defs.number_of_fractions}, '
                      f'{beamset_defs.total_dose}, {beamset_defs.machine}, {beamset_defs.iso_target}, '
                      f'{beamset_defs.iso_poi}, {beamset_defs.modality}')
        # See if the desired beamset is already in the plan
        rs_beam_set = BeamOperations.create_beamset(patient=rso.patient,
                                                    case=rso.case,
                                                    exam=rso.exam,
                                                    plan=rso.plan,
                                                    dialog=False,
                                                    BeamSet=beamset_defs,
                                                    create_setup_beams=setup_fields,
                                                    rename_existing=False)
        if not rs_beam_set:
            rs_beam_set = rso.plan.BeamSets[beamset_defs.name]
        logging.debug(f'Beamset for multi-isocenter beamset: {rs_beam_set.DicomPlanLabel}')
    else:
        # Load beamset
        rs_beam_set = BeamOperations.create_beamset(patient=rso.patient,
                                                    case=rso.case,
                                                    exam=rso.exam,
                                                    plan=rso.plan,
                                                    dialog=False,
                                                    BeamSet=beamset_defs,
                                                    create_setup_beams=setup_fields,
                                                    rename_existing=True)
        logging.debug(f'Beamset for single-isocenter beamset: {rs_beam_set.DicomPlanLabel}')
    # ok, now make the beamset current
    rso.patient.Save()
    rs_beam_set.SetCurrent()
    rso = rso._replace(beamset=connect.get_current('BeamSet'))
    if background:
        rso.plan.UpdateDependency(
            DependentBeamSetName=rso.beamset.DicomPlanLabel,
            BackgroundBeamSetName=background,
            DependencyUpdate="CreateDependency"
        )
        logging.debug(f'Background beamset {background} added to {rso.beamset.DicomPlanLabel}')

    # Set beams from the protocol
    if multi_plan_parameters:
        logging.debug(f'Setting beams for multi-isocenter beamset')
        for m in multi_plan_parameters:
            iso_target = None
            iso_poi = None
            existing_iso = None
            iso_name = None
            if beamset_defs.iso_target:
                iso_target = beamset_defs.iso_target
                iso_name = iso_target
            elif m['iso']['type'] == 'POI':
                iso_poi = m['iso']['target']
                iso_name = iso_poi
            elif m['iso']['type'] == 'ROI':
                iso_target = m['iso']['target']
                iso_name = m['iso']['target']
            iso_parameters = BeamOperations.find_isocenter_parameters(
                case=rso.case,
                exam=rso.exam,
                beamset=rs_beam_set,
                iso_target=iso_target,
                iso_poi=iso_poi,
                existing_iso=existing_iso,
                lateral_zero=lateral_zero,
                iso_name=iso_name)
            beams = BeamOperations.load_beams_xml(filename=protocol_file,
                                                  beamset_name=beamset_template,
                                                  path=path_protocols)
            # Parse Tomo versus VMAT
            if beamset_defs.technique == 'TomoHelical':
                if len(beams) > 1:
                    logging.error(
                        f'Invalid tomo beamset in {beamset_defs.name}, '
                        f'more than one Tomo beam found.')
                else:
                    beam = beams[0]
                BeamOperations.place_tomo_beam_in_beamset(
                    plan=rso.plan,
                    iso=iso_parameters,
                    beamset=rs_beam_set,
                    beam=beam)
                # Beams loaded successfully
                beams_load = True
            elif beamset_defs.technique == 'VMAT' \
                    or beamset_defs.technique == 'SMLC':
                _ = BeamOperations.place_beams_in_beamset(
                    iso=iso_parameters,
                    plan=rso.plan,
                    beamset=rs_beam_set,
                    beams=beams)
                # Beams loaded successfully
                beams_load = True
            else:
                now_u_dunit = 'Unsupported beamset technique ' \
                              f'{beamset_defs.technique}'
                logging.error(now_u_dunit)
                sys.exit(now_u_dunit)
    else:
        if beamset_defs.iso_target:
            iso_target = beamset_defs.iso_target
            iso_poi = None
            existing_iso = None
            iso_name = iso_target
        elif iso_dict['type'] == 'POI':
            iso_target = None
            iso_poi = iso_dict['target']
            existing_iso = None
            iso_name = iso_poi
        elif iso_dict['type'] == 'ROI':
            iso_target = iso_dict['target']
            iso_poi = None
            existing_iso = None
            iso_name = iso_dict['target']
        else:
            existing_iso = None
            iso_name = None
        beams = BeamOperations.load_beams_xml(filename=protocol_file,
                                              beamset_name=beamset_template,
                                              path=path_protocols)
        # Place isocenter
        logging.debug(
            f'Searching exam {rso.exam.Name} for Iso: Isocenter parameters: iso_target={iso_target}, iso_poi={iso_poi}, existing_iso={existing_iso}, '
            f'lateral_zero={lateral_zero}, iso_name={iso_name}')
        iso_parameters = BeamOperations.find_isocenter_parameters(
            case=rso.case,
            exam=rso.exam,
            beamset=rs_beam_set,
            iso_target=iso_target,
            iso_poi=iso_poi,
            existing_iso=existing_iso,
            lateral_zero=lateral_zero,
            iso_name=iso_name)
        beamset_defs.iso = iso_parameters
        # Parse Tomo versus VMAT
        if beamset_defs.technique == 'TomoHelical':
            if len(beams) > 1:
                logging.error(
                    f'Invalid tomo beamset in {beamset_defs.name}, '
                    f'more than one Tomo beam found.')
            else:
                beam = beams[0]
            BeamOperations.place_tomo_beam_in_beamset(plan=rso.plan,
                                                      iso=beamset_defs.iso,
                                                      beamset=rs_beam_set,
                                                      beam=beam)
            # Beams loaded successfully
            beams_load = True
        elif beamset_defs.technique == 'VMAT' \
                or beamset_defs.technique == 'SMLC':
            BeamOperations.place_beams_in_beamset(plan=rso.plan,
                                                  iso=beamset_defs.iso,
                                                  beamset=rs_beam_set,
                                                  beams=beams)
            # Beams loaded successfully
            beams_load = True
        else:
            now_u_dunit = f'Unsupported beamset technique' \
                          f' {beamset_defs.technique}'
            logging.debug(now_u_dunit)
            sys.exit(now_u_dunit)

    #
    # Beam building complete
    ap_report['time_plan'][1] = timer()
    #
    # Set any overrides
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    if user_prompts:
        connect.await_user_input(
            'Set any required material overrides and continue the script.')
    # TODO: The following line of code can be activated in RS 11
    # AutoPlanOperations.set_overrides(rso)

    #
    # Place the SimFiducial Point
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    if user_prompts:
        AutoPlanOperations.place_fiducial(rso=rso, poi_name='SimFiducials')
    else:
        logging.debug('SimFiducial placement skipped for test')
    #
    # Set any blocking or bolus
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Plan optimization'].Button_Plan_optimization.Click()
        ui.TabControl_Modules.TabItem['Plan optimization'].Button_Plan_optimization.Click()
        ui.Workspace.TabControl['Objectives/constraints'].TabItem['Protect'].Select()
    except:
        logging.debug("Could not click on the patient protection window")
    if not user_prompts:
        logging.info('Blocking page skipped for testing')
    else:
        connect.await_user_input(
            'Navigate to the Plan design page, set any blocking or bolus.')
    #
    if not user_prompts:
        logging.info('Custom goal additions skipped for debugging.')
    else:
        connect.await_user_input('Add any custom goals from the TPO.')
    # TODO: Need this step to be done prior to isocenter placement to ensure no collisions
    #
    # Add support structures here
    # Support structures come from beamset data.
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    try:
        strip_roi_support = beamset_etree.find('roi_support').text
    except AttributeError:
        sys.exit('No support structures specified beamset template')
    if strip_roi_support:
        strip_roi_support = strip_roi_support.replace(" ", "")
        strip_roi_support = strip_roi_support.strip()
        beamset_defs.support_roi = strip_roi_support.split(",")
    logging.debug(f'Beamset support structures: {beamset_defs.support_roi}, '
                  f'user prompts: {user_prompts}, '
                  f'strip_roi_support: {strip_roi_support}')
    if user_prompts and strip_roi_support:
        remove_existing_supports(case=rso.case, beamset=rso.beamset)
        # existing_supports = StructureOperations.find_types(
        #     rso.case, roi_type='Fixation')
        # existing_supports += StructureOperations.find_types(
        #     rso.case, roi_type='Support')
        AutoPlanOperations.load_supports(rso=rso, supports=beamset_defs.support_roi, quiet=user_prompts)
        include_supports_in_beamset(beamset=rso.beamset, supports=beamset_defs.support_roi)
        # for support in beamset_defs.support_roi:
        #    try:
        #        logging.debug(f'Loaded support structure {support} and assigned to beamset'
        #                      f' {rso.beamset.DicomPlanLabel}')
        #        rso.beamset.IncludeRoiInRadiationSet(RoiName=support)
        #    except Exception as e:
        #        if "The ROI is already included in the beam set" in str(e):
        #            logging.debug(f'Support structure {support} already included in '
        #                          f'radiation set {rso.beamset.DicomPlanLabel}')
        #            pass
        #        else:
        #            logging.warning(f'Error loading support structure {support}: {e}')
    else:
        logging.info(f'Loading support {beamset_defs.support_roi} '
                     f'skipped for testing')
    # time_user complete
    ap_report['time_user'][1] = timer()

    # Planning structures added
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    ap_report['time_roi'][0] = timer()
    # Use cGy naming convention
    translation_map = AutoPlanOperations.convert_translation_map(
        translation_map, unit=r'cGy')
    ps_elem = protocol.find('planning_structure_set')
    workflow_name = ps_elem.find('name').text
    make_ps = ps_elem.find('name').attrib.get('make_structures', "True") == "True"
    if make_ps:
        _ = AutoPlanOperations.load_planning_structures(
            case=rso.case,
            filename=protocol_file,
            path=path_protocols,
            workflow_name=workflow_name,
            translation_map=translation_map
        )
    ap_report['time_roi'][1] = timer()
    # If there are eval_targets in the rx object, try to add them now
    if rx.eval_targets:
        try:
            rso.beamset.AddRoiPrescriptionDoseReference(
                RoiName=rx.eval_target,
                DoseVolume=rx.rx_volume,
                PrescriptionType='DoseAtVolume',
                DoseValue=rx.total_dose,
                RelativePrescriptionLevel=1
            )
        except:
            pass
    #
    # Add goals and objectives
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    ap_report['time_goals'][0] = timer()
    translation_map = AutoPlanOperations.convert_translation_map(translation_map, unit=r'Gy')
    _ = Objectives.add_goals_and_objectives_from_protocol(
        case=rso.case,
        plan=rso.plan,
        exam=rso.exam,
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
    if not ignore_status:
        auto_status.next_step(text=script_steps[status_index][1])
        status_index += 1
    rso.patient.Save()
    #
    # Check if this order has been validated. If not give user a bail option
    validation = AutoPlanOperations.find_validation_status(order)
    if user_prompts:
        logging.info(
            f'Validation status ({validation["status"]}) '
            f'check skipped for testing')
    else:
        if not validation['status'] and user_prompts:
            connect.await_user_input(
                f'This template was authored by {validation["author"]}'
                f'and is being tested. '
                f'Continue optimization or stop the script execution.\n'
                f'If you continue, please let the author know how it went and '
                f'check goals!'
            )
        else:
            logging.info(
                f"Autoplan template is fully vetted: {validation['status']}."
                f"Author: {validation['author']}.")
            logging.debug(
                f"Perform final dose on completion {validation['final_dose']}")
            logging.debug(
                f"Copy plan to R0A0 upon completion {validation['copy_final_plan']}")

    ap_report['time_opt'][0] = timer()
    logging.debug(f'Optimize is {optimize}')
    opt_status = AutoPlanOperations.load_configuration_optimize_beamset(
        filename=protocol_file,
        path=path_protocols,
        rso=rso,
        technique=beamset_defs.technique,
        output_data_dir=path_to_output,
        bypass_user_prompts=True,
        optimize=optimize,
        lock_dose_grid=lock_dose_grid,
    )
    ap_report['time_opt'][1] = timer()
    if opt_status:
        # Enable autoscale
        # Find current Beamset Number and determine plan optimization
        opt_indx = find_optimization_index(plan=rso.plan, beamset=rso.beamset,
                                           verbose_logging=False)
        # Turn on autoscale
        if 'Tomo' not in beamset_defs.technique:
            try:
                rso.beamset.SetAutoScaleToPrimaryPrescription(AutoScale=True)
                compute_dose_message = compute_dose(beamset=rso.beamset,
                                                    dose_algorithm='CCDose')
                logging.info(compute_dose_message)
            except Exception as e:
                logging.warning(f'Autoscaling not possible {e}')
        #
        # Run Final Dose Calculation
        if validation['final_dose']:
            ap_report['time_final_dose'][0] = timer()
            try:
                FinalDose.final_dose(site=site[0:4],
                                     technique=beamset_defs.description)
            except:
                logging.debug('Final Dose run unsuccessful')
            ap_report['time_final_dose'][1] = timer()
        #
        rso.patient.Save()
        ap_report['time_all'][1] = timer()
        #
        # Save the patient
        rso.patient.Save()
        if validation['copy_final_plan']:
            pd_out = copy_plan_set_copy_current(rso, new_plan_name)
        else:
            pd_out = rso
        # Update doses
        # rso.beamset.FractionDose.UpdateDoseGridStructures()
        # rso.case.TreatmentPlans[new_plan_name].BeamSets[
        # new_plan_name].FractionDose.UpdateDoseGridStructures()
        # rso.plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
        logging.info('Autoplanning Report')
        logging.info(f'Time in user operations '
                     f'{ap_report["time_user"][1] - ap_report["time_user"][0]} s')
        logging.info(f'Time building plan '
                     f'{ap_report["time_plan"][1] - ap_report["time_plan"][0]} s')
        logging.info(f'Time making planning structs '
                     f'{ap_report["time_roi"][1] - ap_report["time_roi"][0]} s')
        logging.info(f'Time adding goals '
                     f'{ap_report["time_goals"][1] - ap_report["time_goals"][0]} s')
        logging.info(f'Time optimizing '
                     f'{ap_report["time_opt"][1] - ap_report["time_opt"][0]} s')
        logging.info(f'Time in script '
                     f'{ap_report["time_all"][1] - ap_report["time_all"][0]} s')
        return pd_out

        #
        # TODO: Export the autoplan and objectives, weights and goal values
        #
        # TODO: Ask user if they want to anonymize and save. If yes, pull up the TPL and save


def main():
    testing_bypass_dialogs = {
        'protocol_name': 'UW WBHA',
        'order_name': 'Brain-WBRT-Hippocampal Avoidance [30Gy CC001]',
        'num_fx': '10',
        'site': 'Brai',
        'translation_map': '',
        'beamset_name': 'Tomo-Brain-FW2.5',
        'iso_target': 'All_PTVs',
        'machine': 'HDA0488',
        'user_prompts': False}
    autoplan(autoplan_parameters={})


if __name__ == '__main__':
    main()
