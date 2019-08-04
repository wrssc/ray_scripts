""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""
import sys
import os
import logging
import xml.etree.ElementTree
import UserInterface
import StructureOperations


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
            opts.OptimizedBeamSets[beamset.DicomPlanLabel]
            indices.append(OptIndex)
        except:
            pass
    # Ensure we have a unique match or exit
    if len(indices) == 1:
        # Found our index.  We will use a shorthand for the remainder of the code
        OptIndex = indices[0]
        plan_optimization = plan.PlanOptimizations[OptIndex]
    elif len(indices) == 0:
        logging.warning("Beamset optimization for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")
    elif len(indices) > 1:
        logging.warning("Beamset has multiple optimizations, cannot proceed")
        sys.exit("Multiple beamset optimizations found in current plan.Cannot proceed")
    return OptIndex


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
            logging.debug('Order: {} has no objectives. Protocol objectives being used'.format(order_name))
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
            logging.info('Objective list to be loaded {}'.format(
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
            o_t = o.find('type').text
            o_d = o.find('dose').text
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

    if checking:
        roi_check = all(StructureOperations.check_roi(case=case, exam=exam, rois=roi))

        if not roi_check:
            logging.warning("Objective skipped for protocol ROI: {} since plan roi {} has no contours".format(
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
            logging.warning('Unsupported robustness type {}'.format(obj.find('type').attrib['robust']))
    else:
        robust = False

    OptIndex = find_optimization_index(plan=plan, beamset=beamset)
    plan_optimization = plan.PlanOptimizations[OptIndex]

    # Add the objective
    # try:

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
                  "{}, type {}, dose {}, weight {}, for beamset {} with restriction: {}".format(
                      roi, function_type, dose, weight, beamset.DicomPlanLabel, restrict_beamset))

# except:
#     logging.debug("Failed to add objective for ROI:" +
#                   " {}, type {}, dose {}, weight {}, for beamset {}".format(
#                       roi, function_type, dose, weight, restrict_beamset))
