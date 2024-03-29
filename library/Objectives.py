""" Create Clinical Goals and Objectives

Add clinical goals and objectives in RayStation given user supplied inputs
At this time, we are looking in the UW protocols directory for a
list of approved protocols

We may want to extend this main function to a simple function which would potentially
take the path as an argument.

Script will ask user for a protocol and potentially an order.  It will then find the
doses that are to be used. If protocol defined doses exist and matches are found to
target names it will load those first.

Inputs::
	None at this time

Dependencies::
	Note that protocols are assumed to have even priorities describing targets

Version History::

1.0.0 initial release supporting HN, Prostate, and lung (non-SBRT)

1.0.1 supporting SBRT, brain, and knowledge-based goals for RTOG-SBRT Lung

2.0.0 Adding the clinical objectives for IMRT

2.0.1 HotFix for an error with a target that is too large for RTOG goals.


Add objectives

Contains functions required to load objectives from xml files
add the objectives to RayStation. Contains functions for reassignment of an
objective when the target name is not matched
"""

import sys
import os
import logging
import xml.etree.ElementTree
from collections import OrderedDict
import re
import math
import UserInterface
import StructureOperations
import Goals
import connect
from GeneralOperations import logcrit as logcrit
from GeneralOperations import find_scope as find_scope

GENERIC_PLANNING_STRUCTURE_NAMES = ['OTV1_', 'sOTVu1_', 'OTV1_EZ_',
                                    'PTV1_', 'PTV1_Eval_', 'PTV1_EZ_',
                                    'ring1_']


def find_optimization_index(plan, beamset):
    """

    :param case: current case
    :param plan: current plan
    :param beamset: current beamset
    :return: OptIndex: index of the optimization used by the current beamset
    """
    # Find current BeamSet Number and determine plan optimization
    indices = []
    for OptIndex, opts in enumerate(plan.PlanOptimizations):
        try:
            o = opts.OptimizedBeamSets[beamset.DicomPlanLabel]
            indices.append(OptIndex)
        except:
            pass
    # Ensure we have a unique match or exit
    if len(indices) == 1:
        # Found our index.  We will use a shorthand for the remainder of the code
        OptIndex = indices[0]
        plan_optimization = plan.PlanOptimizations[OptIndex]
    elif len(indices) == 0:
        logging.warning("Beamset optimization for {} could not be found."
                        .format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")
    elif len(indices) > 1:
        logging.warning("Beamset has multiple optimizations, cannot proceed")
        sys.exit("Multiple beamset optimizations found in current plan.Cannot proceed")
    return OptIndex


def add_mco(plan, beamset):
    # Find the current optimization index
    # If no mco, make one
    # TODO: Turn off autonavigate!
    opt_index = find_optimization_index(plan, beamset)
    po = plan.PlanOptimizations[opt_index]
    try:
        po.CreateMco()
    except:
        logging.debug('Create MCO exists already')


def select_objective_protocol(folder=None, filename=None, order_name=None, protocol=None):
    """
    Function to select the location of the objectives to be loaded within the plan.

    This function can be used to load a raw objectiveset list from an xml file or
    can be used to search a protocol level xml file and load desired objectives.

    The locations of all the orders containing of objectives is identified and the
    element containing this order is returned. All the
    objectiveset elements are returned as well.

    :param filename: os joined protocol name, used to directly open a file
    :param folder: folder from os to search within and prompt user to select appropriate protocol
    :param order_name: the name of order level element from xml file
    :param protocol: ElementTree-Element of the objectiveset you want

    :return: et_list: elementtree list of elements with objectives and/or objectivesets

    Usage:
    USE CASE 1:
    ## User knows the file the order is housed in but wants to select the order
    # Prompt user to select an order out of a specific file (UWBrainCNS.xml) located in
    # ../protocols/UW
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file, folder=path_protocols)

    USE CASE 2:
    ## User knows the exact order that needs to be loaded. Return only the selected order and
    ## any objectivesets in the protocol
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    order_name = 'GBM Brain 6000cGy in 30Fx [Single-Phase Stupp]'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file,
                                                              folder=path_protocols,
                                                              order_name=order_name)
    USE CASE 3:
    ## User will select a default objectiveset from the standard objectives directory
    objective_elements = Objectives.select_objective_protocol()

    USE CASE 4:
    ## User supplies ordername and protocol element:
    objective_elements = Objectives.select_objective_protocol(order_name=order_name,
                                                              protocol=protocol)

    """
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    objectives_folder = r'objectives'

    # First search the file list to be searched depending on the supplied information
    # output a list of files that are to be scanned
    if filename:
        # User directly supplied the filename of the protocol or objectiveset
        path_objectives = folder
        file_list = [filename]
    elif folder and not filename:
        # User wants to select the protocol or objectiveset from a list of xml files
        path_objectives = os.path.join(os.path.dirname(__file__),
                                       protocol_folder,
                                       institution_folder)
        file_list = os.listdir(path_objectives)
    else:
        # If no information was supplied look in the objectives folder
        path_objectives = os.path.join(os.path.dirname(__file__),
                                       protocol_folder,
                                       institution_folder,
                                       objectives_folder)
        file_list = os.listdir(path_objectives)

    objective_sets = {}
    # Return variable. A list of ET Elements
    et_list = []
    if protocol is not None:
        # Search first for a top level objectiveset
        # Find the objectivesets:
        # These get loaded for protocols regardless of orders
        protocol_obj_set = protocol.findall('./objectiveset')
        for p in protocol_obj_set:
            et_list.append(p)
        orders = protocol.findall('./order')
        # Search the orders to find those with objectives and return the candidates
        # for the selectable objectives
        for o in orders:
            objectives = o.findall('./objectives')
            if objectives:
                n = o.find('name').text
                objective_sets[n] = o
            else:
                logging.debug('No objectives found in {}'.format(o.find('name').text))
    else:
        for f in file_list:
            if f.endswith('.xml'):
                # Parse the xml file
                tree = xml.etree.ElementTree.parse(os.path.join(path_objectives, f))
                # Search first for a top level objectiveset
                if tree.getroot().tag == 'objectiveset':
                    n = tree.find('name').text
                    if n in objective_sets:
                        # objective_sets[n].extend(tree.getroot())
                        logging.debug("Objective set {} already in list".format(n))
                    else:
                        objective_sets[n] = tree
                        et_list.append(tree)
                elif tree.getroot().tag == 'protocol':
                    # Find the objectivesets:
                    # These get loaded for protocols regardless of orders
                    protocol_obj_set = tree.findall('./objectiveset')
                    for p in protocol_obj_set:
                        et_list.append(p)
                    orders = tree.findall('./order')
                    # Search the orders to find those with objectives and return the candidates
                    # for the selectable objectives
                    for o in orders:
                        objectives = o.findall('./objectives')
                        if objectives:
                            n = o.find('name').text
                            objective_sets[n] = o
                        else:
                            logging.debug('No objectives found in {}'.format(o.find('name').text))

    # Augment the list to include all xml files found with an "objectiveset" tag in name
    if order_name is not None:
        try:
            selected_order = objective_sets[order_name]
        except KeyError:
            # This order doesn't appear to match one that has objectives in it
            # Pass an empty entry
            logging.debug(
                'Order: {} has no objectives. Protocol objectives being used'.format(order_name))
            selected_order = None
    else:
        input_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Objective Set'},
            title='Objective Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(objective_sets.keys())},
            required=['i'])
        response = input_dialog.show()
        # Close on cancel
        if response == {}:
            logging.info('create_objective cancelled by user')
            sys.exit('create_objective cancelled by user')
        else:
            logging.debug('User selected order: {} for objectives'.format(
                input_dialog.values['i']))
            selected_order = objective_sets[input_dialog.values['i']]
    # Add the order to the returned list
    if selected_order is not None:
        et_list.append(selected_order)

    if et_list is not None:
        for e in et_list:
            logcrit('Objective list to be loaded {}'.format(
                e.find('name').text))
    else:
        logging.warning('objective files were not found')

    return et_list


def reformat_objectives(objective_elements, translation_map=None):
    """
    This function takes the desired protocol file, order-based keyword?, and a dictionary of mappings
    dictionary format: key = xml name, value = desired entry
    :return:
    """
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    # TODO: Go back to planning structs and generate a mapping to be used for OTVs, etc
    #  but for now, we'll match to the closest suffix

    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_n = o.find('name').text
            # o_t = o.find('type').text
            if o.find('dose'):
                o_d = o.find('dose').text
            else:
                o_d = None
            # logging.debug('ROI: {} has a goal of type: {} with a dose level: {}%'.format(
            #    o_n, o_t, o_d))
            if o_n in translation_map:
                s_roi = translation_map[o_n][0]
                o.find('name').text = s_roi
            # logging.debug('translation map used {} mapped to {}'.format(
            #     o_n, s_roi))
            else:
                s_roi = None

            if "%" in o.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                o_r = o.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                # Correct the relative dose to the user-specified dose levels for this structure
                if o_r in translation_map:
                    # Change the dose attribute to absolute
                    # TODO:: these change the xml object, might be needed for datamining project
                    o.find('dose').attrib['units'] = "Gy"
                    o.find('dose').attrib['roi'] = translation_map[o_r][0]
                    s_dose = float(translation_map[o_r][1]) * float(o_d) / 100
                    o.find('dose').text = str(s_dose)
                # logging.debug('Reassigned protocol dose attribute name:' +
                #               '{} to {}, for dose:{}% to {} Gy'.format(
                #                   o_r, o.find('dose').attrib['roi'], o_d, o.find('dose').text))
                else:
                    logging.warning('Unsuccessful match between relative dose goal for ROI: ' +
                                    '{}. '.format(o_r) +
                                    'The user did not match an existing roi to one required for this goal. ' +
                                    'An arbitrary value of 0 may be added')
                    s_dose = 0
                    pass
        return objective_elements


def add_objective(obj, exam, case, plan, beamset,
                  s_roi=None, s_dose=None,
                  s_weight=None, restrict_beamset=None, checking=False):
    """
    adds an objective function to the optimization in RayStation after
    :param obj: child (roi-tag) of an ElementTree - consider mak
    :param exam: RS Exam
    :param case: RS case
    :param plan: RS plan
    :param beamset: RS beamset
    :param s_roi: substitute roi for the name tag
    :param s_dose: substitute dose for the dose tag, str dose in Gy, this will be used as
                    reference dose in Dose Fall Off operations
    :param s_weight: substitute weight from protocol-defined tag, str weight
    :param restrict_beamset: if co-optimization is used, this is needed to restrict an objective to a
                            given beamset
    :return: (none) although obj is directly modified by this function
    """
    # Parse the objectives
    #
    # If an roi was specified replace the name tag

    if s_roi:
        protocol_roi = obj.find('name').text
        roi = s_roi
        obj.find('name').text = roi

    else:
        protocol_roi = obj.find('name').text
        roi = obj.find('name').text
    #
    # Determine if MCO constraints are to be added
    if obj.find('mco') is None:
        mco = False
        mco_constraint = False
        mco_alara = False
    else:
        if obj.find('mco').text == "Constraint":
            mco = True
            mco_constraint = True
            mco_alara = False
        elif obj.find('mco').text == "ALARA":
            mco = True
            mco_constraint = False
            mco_alara = True
        elif obj.find('mco').text == "Objective":
            mco = True
            mco_constraint = False
            mco_alara = False
        else:
            mco = False
            mco_alara = False
            mco_constraint = False
    if checking:
        roi_check = all(StructureOperations.check_roi(case=case, exam=exam, rois=roi))

        if not roi_check:
            logging.warning(
                "Objective skipped for protocol ROI: {} since plan roi {} has no contours".format(
                    protocol_roi, roi))
            return

    if s_roi:
        logging.debug("Objective for protocol ROI: {} substituted with plan ROI: {}".format(
            protocol_roi, s_roi))
    #
    # Deal with relative or absolute volumes, modify the volume tag
    # (RayStation only allows relative volume roi's
    # TODO: Check how to find existence of a tag in elementtree
    # TODO: Clean up the debugging in here to one message
    if obj.find('volume') is None:
        volume = None
    else:
        # If the user specified an absolute volume convert this into %
        if obj.find('volume').attrib["units"] == "cc":
            try:
                t = case.PatientModel.StructureSets[exam.Name]. \
                    RoiGeometries[roi]
                if t.HasContours():
                    roi_vol = t.GetRoiVolume()
                    volume = int(float(obj.find('volume').text) / roi_vol)
                    logging.debug('ROI: {} Protocol volume {} substituted with {}'.format(
                        obj.find('name').text, obj.find('volume').text, volume))
                    obj.find('volume').text = str(volume)
                    obj.find('volume').attrib["units"] = "%"
                else:
                    logging.warning('{} has no contours, index undefined'.format(roi))
            except:
                logging.warning('Error getting volume for {}, volume => 0.0'.format(roi))
        elif obj.find('volume').attrib["units"] == "%":
            volume = int(obj.find('volume').text)
    # Modify the dose tag if relative
    if s_dose:
        if obj.find('dose').attrib["units"] == "%":
            weighted_dose = float(s_dose) * float(obj.find('dose').text) / 100
            logging.debug('ROI: {} Protocol dose {} {} substituted with {} Gy'.format(
                obj.find('name').text, obj.find('dose').text, obj.find('dose').attrib["units"],
                weighted_dose))
            if obj.find('type').text == 'DFO':
                low_dose = float(s_dose) * float(obj.find('dose').attrib['low']) / 100
                obj.find('dose').attrib['low'] = low_dose

            obj.find('dose').attrib["units"] = "Gy"
            # Change the element to the substitute dose times the percentage of the reference
            obj.find('dose').text = weighted_dose
            dose = float(obj.find('dose').text) * 100
        else:
            logging.debug('ROI: {} Protocol dose {} {} substituted with {} Gy'.format(
                obj.find('name').text, obj.find('dose').text, obj.find('dose').attrib["units"],
                s_dose))
            obj.find('dose').text = float(s_dose) * 100
            dose = float(obj.find('dose').text) * 100
    else:
        if obj.find('dose').attrib["units"] == "BED":
            ab = float(obj.find('dose').attrib["ab"])
            bed = float(obj.find('dose').text)
            num_fx = float(beamset.FractionationPattern.NumberOfFractions)
            logging.debug(
                f'Solving Dose for {bed:.0f} Gy_{ab:.0f} in {num_fx:.0f}')
            dose = bed_calculation(bed, alphabeta=ab, num_fx=num_fx)
            logging.info(
                f'{obj.find("name").text} Dose for {bed:.0f} Gy_{ab:.0f} in {num_fx:.0f} fractions is {dose:.0f} Gy')
        else:
            dose = float(obj.find('dose').text) * 100
    #
    # Read the weight variable
    if s_weight:
        logging.debug('ROI: {} Protocol weight {} substituted with {}'.format(
            obj.find('name').text, obj.find('weight').text, s_weight))
        obj.find('weight').text = s_weight
        weight = float(s_weight)
    else:
        weight = float(obj.find('weight').text)
    # Correct type to RS supported naming
    # If the objective does not require directional evaluation (like those in obj_types)
    # we can reassign directly. Otherwise, we need to parse direction.
    obj_types = {'Max': 'MaxDose',
                 'Min': 'MinDose',
                 'UD': 'UniformDose',
                 'MinEud': 'MinEud',
                 'MaxEud': 'MaxEud',
                 'TarEud': 'TargetEud',
                 'DFO': 'DoseFallOff'}
    if obj.find('type').text in obj_types:
        function_type = obj_types[obj.find('type').text]
    elif obj.find('type').text == 'DX':
        if obj.find('type').attrib['dir'] == "ge" or obj.find('type').attrib['dir'] == "gt":
            function_type = 'MinDvh'
        elif obj.find('type').attrib['dir'] == "le" or obj.find('type').attrib['dir'] == "lt":
            function_type = 'MaxDvh'
    else:
        logging.debug('Unsupported function type for ROI: {} with type: {}'.format(
            obj.find('name').text, obj.find('type').text))
    #
    # Add special types
    if 'Eud' in obj.find('type').text:
        eud_a = float(obj.find('type').attrib['a'])
    if 'constraint' not in obj.find('type').attrib:
        constraint = False
    else:
        if obj.find('type').attrib['constraint'] == 'True':
            constraint = True
        elif obj.find('type').attrib['constraint'] == 'False':
            constraint = False
        else:
            logging.warning('Unsupported constraint specification {}'.format(
                obj.find('type').attrib['constraint']))
    if 'adapt' in obj.find('type').attrib:
        if obj.find('type').attrib['adapt'] == 'True':
            adapt_dose = True
        elif obj.find('type').attrib['adapt'] == 'False':
            adapt_dose = False
        else:
            logging.warning('Unsupported type for attribute {}'.format(
                obj.find('type').attrib['adapt']))
    if obj.find('type').text == 'DFO':
        if obj.find('dose').attrib['units'] == "%":
            high_dose = 100 * float(s_dose) * float(obj.find('dose').text) / 100
            low_dose = 100 * float(s_dose) * float(obj.find('dose').attrib['low']) / 100
        elif obj.find('dose').attrib['units'] == "Gy":
            high_dose = 100 * float(obj.find('dose').text)
            low_dose = 100 * float(obj.find('dose').attrib['low'])
        else:
            logging.warning('Unsupported doses for Dose Fall Off')
        if 'dist' in obj.find('type').attrib:
            low_dose_dist = float(obj.find('type').attrib['dist'])
        else:
            logging.warning('Unknown low dose distance for Dose Fall Off')
        logging.debug('DFO object found.  High Dose: {}, Low Dose: {}, Distance: {}'.format(
            high_dose, low_dose, low_dose_dist))
    if 'robust' in obj.find('type').attrib:
        if obj.find('type').attrib['robust'] == 'False':
            robust = False
        elif obj.find('type').attrib['robust'] == 'True':
            robust = True
        else:
            logging.warning(
                'Unsupported robustness type {}'.format(obj.find('type').attrib['robust']))
    else:
        robust = False

    OptIndex = find_optimization_index(plan=plan, beamset=beamset)
    plan_optimization = plan.PlanOptimizations[OptIndex]

    # Add the objective
    o = plan_optimization.AddOptimizationFunction(FunctionType=function_type,
                                                  RoiName=roi,
                                                  IsConstraint=constraint,
                                                  RestrictAllBeamsIndividually=False,
                                                  RestrictToBeam=None,
                                                  IsRobust=robust,
                                                  RestrictToBeamSet=restrict_beamset,
                                                  UseRbeDose=False)
    o.DoseFunctionParameters.Weight = weight
    if volume:
        o.DoseFunctionParameters.PercentVolume = volume
    if 'Eud' in function_type:
        o.DoseFunctionParameters.EudParameterA = eud_a
    # Dose fall off type of optimization option.
    if function_type == 'DoseFallOff':
        o.DoseFunctionParameters.HighDoseLevel = high_dose
        o.DoseFunctionParameters.LowDoseLevel = low_dose
        o.DoseFunctionParameters.LowDoseDistance = low_dose_dist
        o.DoseFunctionParameters.AdaptToTargetDoseLevels = adapt_dose
    # For all types other than DoseFallOff, the dose is simply entered here
    else:
        o.DoseFunctionParameters.DoseLevel = dose
    logging.debug("Added objective for ROI: " +
                  f"{roi}, type {function_type}, dose {dose}, weight {weight},"
                  f" for beamset {beamset.DicomPlanLabel}"
                  f" with restriction: {restrict_beamset}")
    # Add the mco objective
    if mco:
        add_mco(plan, beamset)
        if mco_alara:
            # Hijack function type
            mco_function_type = "MaxEud"
            eud_a = 1
        else:
            mco_function_type = function_type

        mco_o = plan_optimization.Mco.TemplateOptimizationProblem.AddOptimizationFunction(
            FunctionType=mco_function_type,
            RoiName=roi,
            IsConstraint=mco_constraint,
            RestrictAllBeamsIndividually=False,
            RestrictToBeam=None,
            IsRobust=robust,
            RestrictToBeamSet=restrict_beamset,
            UseRbeDose=False)
        if mco_alara:
            mco_o.DoseFunctionParameters.EudParameterA = eud_a
            mco_o.DoseFunctionParameters.DoseLevel = 0.
            logging.info("Added MCO objective for ROI: " +
                         "{}, type {}, dose {}, for beamset {} with restriction: {}".format(
                             roi, mco_function_type, 0., beamset.DicomPlanLabel, restrict_beamset))
        else:
            if volume:
                mco_o.DoseFunctionParameters.PercentVolume = volume
            if 'Eud' in function_type:
                mco_o.DoseFunctionParameters.EudParameterA = eud_a
            # Dose fall off type of optimization option.
            if function_type == 'DoseFallOff':
                mco_o.DoseFunctionParameters.HighDoseLevel = high_dose
                mco_o.DoseFunctionParameters.LowDoseLevel = low_dose
                mco_o.DoseFunctionParameters.LowDoseDistance = low_dose_dist
                mco_o.DoseFunctionParameters.AdaptToTargetDoseLevels = adapt_dose
            # For all types other than DoseFallOff, the dose is simply entered here
            else:
                mco_o.DoseFunctionParameters.DoseLevel = dose
            logging.info("Added MCO objective for ROI: " +
                         "{}, type {}, dose {}, for beamset {} with restriction: {}".format(
                             roi, mco_function_type, dose, beamset.DicomPlanLabel, restrict_beamset))


# def add_robust_optimization(plan_optimization, position_uncertainty,
#     density_uncertainty = 0, postion_uncertainty_setting="Universal", compute_exact=False,nonplanning_exams=[] ):
#    # Oodles of good stuff
#    plan_optimization.OptimizationParameters.SaveRobustnessParameters(PositionUncertaintyAnterior=0.3,
#        PositionUncertaintyPosterior=0,
#        PositionUncertaintySuperior=0,
#        PositionUncertaintyInferior=0,
#        PositionUncertaintyLeft=0,
#        PositionUncertaintyRight=0.3,
#        DensityUncertainty=0,
#        PositionUncertaintySetting="Universal",
#        IndependentLeftRight=True,
#        IndependentAnteriorPosterior=True,
#        IndependentSuperiorInferior=True,
#        ComputeExactScenarioDoses=False,
#        NamesOfNonPlanningExaminations=[])

def rtog_sbrt_dgi(case, examination, target, flag, isodose=None):
    """
    implementation of the RTOG limits for DGI and PITV modified to allow the
    use of the conformity index

    :param case: name of current case
    :param examination: current examination object
    :param target: roi to be used for evaluation of knowledge-based goal
    :param flag: type of goal to be used
    :param isodose: optional for inputing a relative dose value
    :return: a float that is the desired index or dose
    """
    prot_vol = [1.8, 3.8, 7.4, 13.2, 22, 34, 50, 70, 95, 126, 163]
    if flag == 'rtog_sbr_dgi_minor':
        index = [0.17, 0.18, 0.20, 0.21, 0.22, 0.23, 0.25, 0.29, 0.30, 0.32, 0.34]
        logging.debug('rtog_sbrt_dgi: Minor DGI selected.')
    elif flag == 'rtog_sbr_dgi_major':
        index = [0.13, 0.15, 0.17, 0.17, 0.18, 0.19, 0.20, 0.21, 0.23, 0.25, 0.27]
        logging.debug('rtog_sbrt_dgi: Major DGI selected.')
    elif flag == 'rtog_sbr_norm2_major':
        unscaled_index = [0.57, 0.57, 0.58, 0.58, 0.63, 0.68, 0.77, 0.86, 0.89, 0.91, 0.94]
        index = [i * float(isodose) for i in unscaled_index]
        logging.debug(
            'rtog_sbrt_dgi: Major Normal_2cm selected. Index scaled by dose {}'.format(isodose))
    elif flag == 'rtog_sbr_norm2_minor':
        unscaled_index = [0.50, 0.50, 0.50, 0.50, 0.54, 0.58, 0.62, 0.66, 0.70, 0.73, 0.77]
        index = [i * float(isodose) for i in unscaled_index]
        logging.debug(
            'rtog_sbrt_dgi: Minor Normal_2cm selected. Index scaled by dose {}'.format(isodose))
    else:
        logging.warning("rtog_sbrt_dgi: Unknown flag used in call. Returning zero")
        return 0.0

    vol = 0.0
    try:
        t = case.PatientModel.StructureSets[examination.Name]. \
            RoiGeometries[target]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.warning('rtog_sbrt_dgi: {} has no contours, index undefined'.format(target))
    except:
        logging.warning('rtog_sbrt_dgi: Error getting volume for {}, volume => 0.0'.format(target))

    # Compute density from the actual dose grid representation
    # fd = beamset.FractionDose
    # roi = fd.GetDoseGridRoi(RoiName=target)
    # vol = roi.RoiVolumeDistribution.TotalVolume
    # logging.debug('Type of roi {}'.format(type(roi)))
    if abs(vol) <= 1e-9:
        logging.warning('rtog_sbrt_dgi: Volume is 0.0 for {}'.format(target))
    else:
        logging.debug('rtog_sbrt_dgi: Volume for {} is {}'.format(
            target, vol))
    v = prot_vol[0]
    i = 0
    # Find first volume exceeding target volume or find the end of the list
    while v <= vol and i <= len(prot_vol) - 2:
        i += 1
        v = prot_vol[i]
    # Exceptions for target volumes exceeding or smaller than the minimum volume
    if i == 0:
        logging.warning('rtog_sbrt_dgi.py: Target volume < RTOG volume limits' +
                        '  returning lowest available index{}'.format(index[i]))
        return index[i]
    elif i == len(prot_vol) - 1:
        message = f'Target volume {vol:.2f} > RTOG volume limits {prot_vol[i]:.2f}' \
                  + ' returning goals for highest available volume'
        connect.await_user_input(message)
        logging.warning(message)
        return index[i]
    # Interpolate on i and i - 1
    else:
        interp = index[i - 1] + (vol - prot_vol[i - 1]) * (
                (index[i] - index[i - 1]) / (prot_vol[i] - prot_vol[i - 1]))
        logging.info('rtog_sbrt_dgi: {} volume is {}, index = {}. '.format(
            target, vol, interp))
        logging.debug('Table searched lower bound on volume ' +
                      'interpolating volumes: ({}, {}) and index: ({}, {})'.format(
                          prot_vol[i - 1], prot_vol[i], index[i - 1], index[i]
                      ))
        return interp


def residual_volume(structure_name, goal_volume, case, exam):
    """
    Used for finding the remaining volume in terms of the total.  Use for limits
    that must preserve a certain number of cc exposed below a limit
    :param structure_name: structure to evaluate the volume
    :param goal_volume: desired residual volume
    :param case: current case
    :param exam: current exam
    :return: the residual volume as a percentage of the total or zero if volume is undefined
    """
    vol = 0.0
    try:
        t = case.PatientModel.StructureSets[exam.Name]. \
            RoiGeometries[structure_name]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.warning(
                'residual_volume: {} has no contours, index undefined'.format(structure_name))
    except:
        logging.warning(
            'residual_volume: Error getting volume for {}, volume => 0.0'.format(structure_name))

    if abs(vol) <= 1e-9:
        logging.warning('residual_volume: Volume is 0.0 for {}'.format(structure_name))
        return 0
    else:
        logging.debug('residual_volume: Volume for {} is {}'.format(
            structure_name, vol))
        residual_percentage = 100 * (vol - float(goal_volume)) / vol
        return residual_percentage


def solve_quadratic(a, b, c):
    """
    Solve the quadratic equation of form
    ax^2 + bx +c = 0
    :param a: coefficient of squared term
    :param b: coefficient of linear term
    :param c: constant term
    :return:
    """
    d = (b * b) - (4 * a * c)
    if d > 0.:
        root1 = (-b - math.sqrt(d)) / (2 * a)
        root2 = (-b + math.sqrt(d)) / (2 * a)
        if root1 > root2:
            return root1, root2
        else:
            return root2, root1
    else:
        return None, None


def bed_calculation(bed, alphabeta, num_fx):
    """
    Compute the physical dose for the current fractionation given the BED
    BED = Total dose * (1 + (Fraction dose / αβ))
    Solve:
        D^2 + N * αβ * D - N * αβ * BED
    :param bed: Biologically effective dose in Gy_αβ
    :param alphabeta: alpha beta ratio
    :param num_fx: number of fractions in current plan
    :return: The input BED converted to the fraction dose
    """
    dose1, dose2 = solve_quadratic(a=1.,
                                   b=num_fx * alphabeta,
                                   c=-1. * num_fx * alphabeta * bed)
    logging.debug(f'Dose for {bed:.0f} Gy_{alphabeta:.0f} in {num_fx:.0f} fractions is ({dose1:.0f},{dose2:.0f}) Gy')
    if dose1 and dose2:
        return dose1
    else:
        return None


def conditional_overlap(structure_name, goal_volume, case, exam, comp_structure, isodose):
    """Evaluate the overlap between structure_name and comp_structure
    then modify goal volume and dose.
    If overlap return a dmax limit on a percentage of the comp_structure prescription dose
    If no overlap return an absolute dose limit on an absolute volume
    :param structure_name:
    :param goal_volume:
    :param case:
    :param exam:
    :param comp_structure:
    """


# TODO: This module needs to be written to evaluate overlap and put a goal volume based on residual


def knowledge_based_goal(structure_name, goal_type, case, exam,
                         isodose=None,
                         res_vol=None,
                         comp_structure=None,
                         num_fx=None,
                         alphabeta=None):
    """
    knowledge_based_goals will handle the knowledge based goals by goal type
    at this time the
    :param structure_name: structure to which goal should be applied
    :param goal_type: string flag for which the
    :param case: RS case object
    :param exam: RS examination object
    :param isodose: target dose level
    :param res_vol: target residual volume
    :param comp_structure: a comparison structure for conditional evaluation
    :return: know_analysis - dictionary containing the elements that need to be changed
    """
    know_analysis = {}
    if goal_type in ['rtog_sbr_dgi_minor', 'rtog_sbr_dgi_major']:
        know_analysis['index'] = rtog_sbrt_dgi(case=case,
                                               examination=exam,
                                               target=structure_name,
                                               flag=goal_type)
    elif goal_type in ['rtog_sbr_norm2_major', 'rtog_sbr_norm2_minor']:
        know_analysis['dose'] = rtog_sbrt_dgi(case=case,
                                              examination=exam,
                                              target=structure_name,
                                              flag=goal_type,
                                              isodose=isodose)
    elif goal_type in ['resid_vol']:
        know_analysis['volume'] = residual_volume(structure_name=structure_name,
                                                  goal_volume=res_vol,
                                                  case=case,
                                                  exam=exam)
        know_analysis['units'] = '%'
    elif goal_type in ['BED']:
        know_analysis['dose'] = bed_calculation(bed=isodose,
                                                alphabeta=alphabeta,
                                                num_fx=num_fx)
    elif goal_type in ['overlap']:
        know_analysis = conditional_overlap(structure_name=structure_name,
                                            goal_volume=res_vol,
                                            case=case,
                                            exam=exam,
                                            comp_structure=comp_structure,
                                            isodose=isodose)
    else:
        know_analysis['error'] = True
        logging.warning('knowledge_based_goal: Unsupported knowledge-based goal')

    return know_analysis


def make_target_names(target_name, num_targets):
    # Built a list of targets split at the number in the target_name and incorporating
    # up to num_targets
    # return the target list
    spl = re.split(r'(\d)', target_name)
    return [spl[0] + str(i) + spl[2] for i in range(1, num_targets + 1)]


def target_match(t, r):
    # Search for a name of the form: t+ 3 to 4 digits, in r
    # and return the value of r if found
    expr = re.compile(r'^(' + t + r')\d{3,4}$')
    roi_found = re.match(expr, r)
    if roi_found:
        return roi_found.group(0)
    else:
        return None


def add_goals_and_objectives_from_protocol(case, plan, beamset, exam,
                                           filename=None, path_protocols=None, protocol_name=None,
                                           target_map=None, order_name=None, run_status=True):
    """Add Clinical Goals and Objectives from Protocol

    Add clinical goals and objectives in RayStation given user supplied inputs
    At this time, we are looking in the UW protocols directory for a
    list of approved protocols

    We may want to extend this main function to a simple function which would potentially
    take the path as an argument.

    Script will ask user for a protocol and potentially an order.  It will then find the
    doses that are to be used. If protocol defined doses exist and matches are found to
    target names it will load those first.

    Inputs::
        None at this time

    Dependencies::
        Note that protocols are assumed to have even priorities describing targets

    TODO: Change the main to a callable function taking the protocol path as an input`
    TODO: Add goal loop for secondary - unspecified target goals
    TODO: Potentially an issue here with objectiveset loading. Some objectives seems to be disappearing

    Version History:
    1.0.0 initial release supporting HN, Prostate, and lung (non-SBRT)
    1.0.1 supporting SBRT, brain, and knowledge-based goals for RTOG-SBRT Lung
    2.0.0 Adding the clinical objectives for IMRT
    3.0.0 Making the clinical goals and objectives callable with protocol input.

    Function will take the optional input of the protocol file name

    Keyword Arguments:
        patient {[type]} -- [description] (default: {None})
        case {[type]} -- [description] (default: {None})
        plan {[type]} -- [description] (default: {None})
        beamset {[type]} -- [description] (default: {None})
        exam {[type]} -- [description] (default: {None})
        filename {[type]} -- [description] (default: {None})
        path_protocols {[type]} -- [description] (default: {None})
        run_status {bool} -- [description] (default: {True})

    Returns:
        [type] -- [description]
    """

    __author__ = 'Adam Bayliss'
    __contact__ = 'rabayliss@wisc.edu'
    __version__ = '3.0.0'
    __license__ = 'GPLv3'
    __help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
    __copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

    derived_suffixes = ["_Eval","_EZ"]
    # Adding error handling
    error_message = []
    # Potential inputs, patient, case, exam, beamset, protocol path, filename
    if target_map:
        for k, v in target_map.items():
            logcrit('Targets are {}:{}'.format(k, v))
    if run_status:
        status = UserInterface.ScriptStatus(
            steps=['Finding correct protocol',
                   'Matching Structure List',
                   'Getting target Doses',
                   'Adding Goals',
                   'Adding Standard Objectives'],
            docstring=__doc__,
            help=__help__)

    if not path_protocols:
        protocol_folder = r'../protocols'
        institution_folder = r'UW'
        path_protocols = os.path.join(os.path.dirname(__file__),
                                      protocol_folder,
                                      institution_folder)

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    if run_status:
        status.next_step(text='Determining correct treatment protocol ' +
                              'based on treatment planning order.', num=0)

    # TODO: there is some lack of logic here. If we move the elementree stuff to
    # 		dataframes, it would help reduce the overhead in messing with these
    # 		unsearchable elementrees
    if filename:
        logcrit('Protocol selected: {}'.format(filename))
        if not os.path.exists(os.path.join(path_protocols, filename)):
            error_message.append('Path {} not found. No goals could be added'
                                 .format(os.path.join(path_protocols, filename)))
            return error_message
        if protocol_name:
            tree = xml.etree.ElementTree.parse(os.path.join(path_protocols, filename))
            if tree.getroot().tag == 'protocol':
                name = tree.find('name').text
                if name == protocol_name:
                    protocol = tree.getroot()
        if order_name:
            for o in protocol.findall('order'):
                if o.find('name').text == order_name:
                    order = o
                    use_orders = True
                    break
    else:
        # Find the protocol the user wants to use through a dialog
        input_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Protocol'},
            title='Protocol Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(tpo.protocols.keys())},
            required=['i'])
        # Launch the dialog
        response = input_dialog.show()
        # Link root to selected protocol ElementTree
        logging.info("Protocol selected: {}".format(
            input_dialog.values['i']))
        # Store the protocol name and optional order name
        protocol_name = input_dialog.values['i']
        order_name = None
        order_list = []
        protocol = tpo.protocols[input_dialog.values['i']]
        for o in protocol.findall('order/name'):
            order_list.append(o.text)

        if len(order_list) >= 1:
            use_orders = True
            # Find the protocol the user wants to use.
            input_dialog = UserInterface.InputDialog(
                inputs={'i': 'Select Order'},
                title='Order Selection',
                datatype={'i': 'combo'},
                initial={'i': order_list[0]},
                options={'i': order_list},
                required=['i'])
            # Launch the dialog
            response = input_dialog.show()
            # Link root to selected protocol ElementTree
            logcrit(f"Treatment Planning Order selected: {input_dialog.values['i']}")
            # Update the order name

            # I believe this loop can be eliminated with we can use a different function
            # to match protocol.find('order') with input_dialog.values['i']
            for o in protocol.findall('order'):
                if o.find('name').text == input_dialog.values['i']:
                    order = o
                    logging.debug('Matching protocol ElementTag found for {}'.format(
                        input_dialog.values['i']))
                    break
            order_name = input_dialog.values['i']

        else:
            logging.debug('No orders in protocol')
            use_orders = False

    # Match the list of structures found in the objective protocols and protocols
    #
    # Find RS targets
    plan_targets = StructureOperations.find_targets(case=case)
    if run_status:
        status.next_step(text="Matching all structures to the current list.", num=1)
    protocol_targets = []
    missing_contours = []

    # Build second dialog
    target_inputs = {}
    target_initial = {}
    target_options = {}
    target_datatype = {}
    target_required = []
    i = 1
    # Lovely code, but had to break this loop up
    # for g, t in ((a, b) for a in root.findall('./goals/roi') for b in plan_targets):

    if use_orders:
        goal_locations = (protocol.findall('./goals/roi'), order.findall('./goals/roi'))
    else:
        goal_locations = (protocol.findall('./goals/roi'))
    # Look for required structs for a protocol
    required_locations = (order.findall('./required/roi'))
    logging.debug('Required {}'.format(required_locations))
    # Use the following loop to find the targets in protocol matching the names above
    # Find all protocol targets ignoring any derived targets
    derived_keywords = ['^.*_Eval.*?$', '^.*_EZ.*?$']
    derived_targets = []
    for s in goal_locations:
        for g in s:
            # Priorities should be even for targets and append unique elements only
            # into the protocol_targets list
            if int(g.find('priority').text) % 2 == 0:
                g_name = g.find('name').text
                for r in derived_keywords:
                    if re.search(r, g_name) and g_name not in derived_targets:
                        derived_targets.append(g_name)
                try:
                    d_name = g.find('dose').attrib['roi']
                except KeyError:
                    d_name = ""
                if g_name not in protocol_targets and g_name not in derived_targets:
                    protocol_targets.append(g_name)
                elif g_name not in protocol_targets and d_name and d_name not in protocol_targets:
                    protocol_targets.append(d_name)
        # Use the following loop to find the targets in protocol matching the names above
    i = 1
    for p in protocol_targets:
        k = str(i)
        # Python doesn't sort lists....
        k_name = k.zfill(2) + 'Aname_' + p
        k_dose = k.zfill(2) + 'Bdose_' + p
        target_inputs[k_name] = 'Match a plan target to ' + p
        target_options[k_name] = plan_targets
        target_datatype[k_name] = 'combo'
        target_required.append(k_name)
        target_inputs[k_dose] = 'Provide dose for protocol target: ' + p + ' Dose in cGy'
        target_required.append(k_dose)
        i += 1
        # Exact matches get an initial guess in the dropdown
        for t in plan_targets:
            if p == t:
                target_initial[k_name] = t

    # Warn the user they are missing organs at risk specified in the order
    rois = []  # List of contours in plan
    protocol_rois = []  # List of all the regions of interest specified in the protocol

    for r in case.PatientModel.RegionsOfInterest:
        rois.append(r.Name)
    # Record as missing any contours required but not in case
    if required_locations:
        for r in required_locations:
            r_name = r.find('name').text
            if r_name not in protocol_rois:
                protocol_rois.append(r_name)
            if not any(o == r_name for o in rois) and r_name not in missing_contours:
                missing_contours.append(r_name)
    # Launch the matching script here. Then check for any missing that remain. Supply function with rois and
    # protocol_rois
    if not filename:
        if missing_contours:
            mc_list = ',\n'.join(missing_contours)
            missing_message = 'Missing structures, continue script or cancel \n' + mc_list
            if run_status:
                status.next_step(text=missing_message, num=1)
            connect.await_user_input(missing_message)
            # Add a line here to check again for missing contours and write out the list
            for r in case.PatientModel.RegionsOfInterest:
                rois.append(r.Name)

            m_c = []
            found = False
            for m in missing_contours:
                # We don't want in, we need an exact match - for length too
                for r in rois:
                    found = False
                    if r == m:
                        found = True
                        break
                if not found:
                    if m not in m_c:
                        m_c.append(m)
            if not m_c:
                logging.debug('All structures in protocol accounted for')
            else:
                mc_list = ',\n'.join(m_c)
                missing_message = 'Missing structures remain: ' + mc_list
                logging.warning('Missing contours from this order: {}'.format(m_c))
        if run_status:
            status.next_step(text="Getting target doses from user.", num=2)
        target_dialog = UserInterface.InputDialog(
            inputs=target_inputs,
            title='Input Target Dose Levels',
            datatype=target_datatype,
            initial=target_initial,
            options=target_options,
            required=[])
        target_dialog.show()
        # Process inputs
        # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
        nominal_dose = 0
        translation_map = {}
        # TODO Add a dict element that is just key and dose
        #  seems like the next two loops could be combined, but
        #  since dict cycling isn't ordered I don't know how to create
        #  a blank element space
        for k, v in target_dialog.values.items():
            if len(v) > 0:
                i, p = k.split("_", 1)
                if p not in translation_map:
                    translation_map[p] = [None] * 2
                if 'name' in i:
                    # Key name will be the protocol target name
                    translation_map[p][0] = v

                if 'dose' in i:
                    # Append _dose to the key name
                    pd = p + '_dose'
                    # Not sure if this loop is still needed
                    translation_map[p][1] = (float(v) / 100.)

    # Process inputs
    # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
    nominal_dose = 0
    # TODO Add a dict element that is just key and dose
    #  seems like the next two loops could be combined, but
    #  since dict cycling isn't ordered I don't know how to create
    #  a blank element space
    if target_map:
        translation_map = target_map
        for k, v in target_map.items():
            logcrit('Targets are {}{}'.format(k, v))
    else:
        for k, v in translation_map.items():
            logcrit('Targets are {}{}'.format(k, v))

    if run_status:
        status.next_step(text="Adding goals.", num=3)
    # Iterate over goals in orders and protocols
    for s in order.findall('./goals/goalset'):
        logging.debug('Order has goalsets')
        logging.debug('Adding goalset {} to plan'.format(s.find('name').text))
        for g in tpo.goalsets[s.find('name').text].findall('roi'):
            Goals.add_goal(g, connect.get_current('Plan'))

    for seq in goal_locations:
        for g in seq:
            # try:
            # 1. Figure out if we need to change the goal ROI name
            p_n = g.find('name').text
            p_d = g.find('dose').text
            p_t = g.find('type').text
            try:
                p_rel = g.find('dose').attrib['roi']
            except KeyError:
                p_rel = ""
            # Handle derived rois that resulted from remapping to protocol
            suffixes = [ds for ds in derived_suffixes if ds in p_n]
            if len(suffixes) == 1:
                suffix = suffixes[0]
                p_parent = p_n.replace(suffix,"")
            elif len(suffixes) > 1:
                suffix = ""
                p_parent = ""
                logging.error(f'Too many derived matches for this goal structure name {p_n} unacceptable')
            else:
                suffix = ""
                p_parent = ""
            # Change the name for the roi goal if the user has matched it to a target
            if p_n in translation_map:
                # Change the roi name the goal uses to the matched value
                g.find('name').text = translation_map[p_n][0]
                logging.debug('Reassigned protocol target name:{} to {}'.format(
                    p_n, g.find('name').text))
            elif p_parent in translation_map:
                g.find('name').text = translation_map[p_parent][0] + suffix
                logging.debug('Reassigned derived protocol target name:{} to {}'.format(
                    p_n, g.find('name').text))


            # TODO: Exception catching in here for an unresolved reference
            # If the goal is relative change the name of the dose attribution
            # Change the dose to the user-specified level
            if "%" in g.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                p_r = g.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                logging.debug(
                    'ROI: {} has a relative goal of type: {} with a relative dose level: {}%'.format(
                        p_n, p_t, p_d))
                # Correct the relative dose to the user-specified dose levels for this structure
                if p_r in translation_map:
                    # Change the dose attribute to absolute
                    # TODO:: This may not be such a hot idea.
                    g.find('dose').attrib['units'] = "Gy"
                    g.find('dose').attrib['roi'] = translation_map[p_r][0]
                    goal_dose = float(translation_map[p_r][1]) * float(p_d) / 100
                    g.find('dose').text = str(goal_dose)
                    logging.debug('Reassigned protocol dose attribute name:' +
                                  '{} to {}, for dose:{}% to {} Gy'.format(
                                      p_r, g.find('dose').attrib['roi'], p_d, g.find('dose').text))
                else:
                    logging.warning('Unsuccessful match between relative dose goal for ROI: ' +
                                    '{}. '.format(p_r) +
                                    'The user did not match an existing roi to one required for this goal')
                    pass

            #  Knowledge-based goals:
            #  Call the knowledge_based_goal for the correct structure
            #  Use the returned dictionary to modify the ElementTree
            if 'know' in g.find('type').attrib:
                # TODO: Consider a new type for know-goals in the xml
                try:
                    p_r = g.find('dose').attrib['roi']
                except KeyError:
                    # If there is no relative dose attribute the correct structure is the
                    # the structure itself
                    p_r = g.find('name').text
                if g.find('volume') is not None:
                    vol = g.find('volume').text
                else:
                    vol = None
                # Look for a/b
                try:
                    alphabeta = float(g.find('dose').attrib['alphabeta'])
                    num_fx = float(beamset.FractionationPattern.NumberOfFractions)
                except KeyError:
                    alphabeta = None
                    num_fx = None

                know_goal = knowledge_based_goal(
                    structure_name=p_r,
                    goal_type=g.find('type').attrib['know'],
                    case=case,
                    exam=exam,
                    isodose=float(g.find('dose').text),
                    res_vol=vol,
                    num_fx=num_fx,
                    alphabeta=alphabeta)
                # use a dictionary for storing the return values
                try:
                    g.find('index').text = str(know_goal['index'])
                    logging.debug('Index changed for ROI {} to {}'.format(
                        g.find('name').text, g.find('index').text))
                except KeyError:
                    logging.debug('knowledge goals for {} had no index information'.format(
                        g.find('name').text))
                try:
                    g.find('dose').text = str(know_goal['dose'])
                    logging.debug('Dose changed for ROI {} to {}'.format(
                        g.find('name').text, g.find('dose').text))
                except KeyError:
                    logging.debug('knowledge goals for {} had no dose information'.format(
                        g.find('name').text))
                try:
                    g.find('volume').text = str(know_goal['volume'])
                    g.find('volume').attrib['units'] = str(know_goal['units'])
                    logging.debug('Index changed for ROI {} to {}'.format(
                        g.find('name').text, g.find('volume').text))
                except KeyError:
                    logging.debug('knowledge goals for {} had no volume information'.format(
                        g.find('name').text))

            # Regardless, add the goal now
            Goals.add_goal(g, connect.get_current('Plan'))

    if run_status:
        status.next_step(text="Adding Objectives.", num=4)
    objective_elements = select_objective_protocol(order_name=order_name,
                                                   protocol=protocol)
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    #
    obj_targets = []
    gen_obj_targets = [x for g in GENERIC_PLANNING_STRUCTURE_NAMES
                       for x in make_target_names(g, num_targets=100)]
    for r in rois:
        for g in gen_obj_targets:
            roi = target_match(g, r)
            if roi:
                if g not in translation_map:
                    translation_map[g] = [None] * 2
                translation_map[g][0] = roi
                obj_targets.append(roi)
    # TODO: Decide how we want the saved xml file to look. Do we want it a
    #  simple mapping+protocol? If so, the xml element file should really be unaltered
    #  we'd map an xml-input to objectives using the mapping, save the mapping and
    #  output the xml-result using the inverse mapping
    logging.debug('Translation map is {}'.format(translation_map))

    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_n = o.find('name').text
            #
            # Determine any beamset restrictions
            value = o.find('type').attrib.get('restrict_to_beamset')
            restrict_to_beamset = beamset.DicomPlanLabel if value == "True" else None
            # o_t = o.find('type').text
            o_d = o.find('dose').text
            if o_n in translation_map:
                s_roi = translation_map[o_n][0]
            else:
                s_roi = None
            logging.debug('{} has substitute {}'.format(o_n, s_roi))
            if "%" in o.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                o_r = o.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                # Correct the relative dose to the user-specified dose levels for this structure
                if o_r in translation_map:

                    s_dose = float(translation_map[o_r][1])  # * float(o_d) / 100
                    add_objective(o,
                                  exam=exam,
                                  case=case,
                                  plan=plan,
                                  beamset=beamset,
                                  s_roi=s_roi,
                                  s_dose=s_dose,
                                  s_weight=None,
                                  restrict_beamset=restrict_to_beamset,
                                  checking=True)
                else:
                    logging.debug(
                        'No match found protocol roi: {}, with a relative dose requiring protocol roi: {}'
                            .format(o_n, o_r))
                    s_dose = 0
                    pass
            else:
                s_dose = None
                add_objective(o,
                              exam=exam,
                              case=case,
                              plan=plan,
                              beamset=beamset,
                              s_roi=s_roi,
                              s_dose=s_dose,
                              s_weight=None,
                              restrict_beamset=restrict_to_beamset,
                              checking=True)
    return error_message
