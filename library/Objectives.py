""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""
import sys
import os
import logging
import datetime
import xml.etree.ElementTree
import UserInterface
import connect


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


def select_objective_protocol(folder=None, filename=None):
    """
    :param filename: os joined protocol name
    :param folder: folder from os to search within
    :return: tree: elementtree from xml file

    Prompt user to select the objective xml file they want to use
    :return: tree: Elementtree with user-selected objectives loaded
    TODO:: Make the folder-based and filename based elements work
    """
    if filename:
        filelist = [filename]
        path_objectives = folder
    elif folder and not filename:
        path_objectives = os.path.join(os.path.dirname(__file__),
                                       protocol_folder,
                                       institution_folder)
        filelist = os.listdir(path_objectives)
    else:
        protocol_folder = r'../protocols'
        institution_folder = r'UW'
        # os join autoresolves the path
        path_objectives = os.path.join(os.path.dirname(__file__),
                                       protocol_folder,
                                       institution_folder)
        filelist = os.listdir(path_objectives)

    objective_sets = {}
    for f in filelist:
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(os.path.join(path_objectives, f))
            logging.debug('Searching tree: {}'.format(tree.getroot().tag))
            # Search first for a top level objectiveset
            if tree.getroot().tag == 'objectiveset':
                n = tree.find('name').text
                logging.debug('Found objectiveset {} in {}'.format(n, f))
                # Debugging fun
                if n in objective_sets:
                    # objective_sets[n].extend(tree.getroot())
                    logging.debug("Objective set {} already in list".format(n))
                else:
                    objective_sets[n] = tree
            elif tree.getroot().tag == 'protocol':
                protocol = tree.getroot()
                # Find the objectivesets:
                # These get loaded for protocols regardless of orders
                protocol_obj_set = protocol.findall('./objectiveset')
                logging.debug("protocol_obj_set is {}".format(type(protocol_obj_set)))
                #logging.debug("all elements: {}".format(protocol_obj_set.attrib("name")))
                #logging.debug("Found objective set {} in {}".format(
                #    protocol_obj_set.get("name"), protocol.get("name")
                # ))

                for p in protocol_obj_set:
                    logging.debug("Type of p is {}".format(p.get("name")))
                orders = protocol.findall('./order')
                # Search the orders to find those with objectives and return the candidates
                # for the selectable objectives
                for o in orders:
                    # TODO: replace this next line with findall objectives
                    objectives = o.findall('./objectives')
                    # Force user to select from the orders with separate objectives
                    if objectives:
                        logging.debug("Found some orders {} with objectives".format(
                            o.find('name').text))
                        n = o.find('name').text
                        objective_sets[n] = o
                    logging.debug("Found some orders {}".format(o.find('name').text))
            else:
                logging.debug("Could not find anything useful in file {}".format(f))


    # Augment the list to include all xml files found with an "objectiveset" tag in name
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
   ##     status.finish('User cancelled create objective creation.')
        sys.exit('create_objective cancelled by user')
    for k in input_dialog.values:
        logging.debug('This is key {} value {}'.format(k,input_dialog.values[k]))

    # logging.debug('user selected {}').format(input_dialog.values['i'])
    # tree = objective_sets[input_dialog.values['i']]
    # Rename this thing
    logging.debug("In function: os {} has type {}".format(input_dialog.values['i'],
                 type(objective_sets[input_dialog.values['i']])))
    logging.debug("In function: pos has type {}".format(
                 type(protocol_obj_set)))
    tree = [objective_sets[input_dialog.values['i']],protocol_obj_set]
    # tree = Objectives.select_objectives(input_dialog.values['i'])
    return tree

def select_objectives(folder=None, filename=None):
    """

    :param filename: os joined protocol name
    :param folder: folder from os to search within
    :return: tree: elementtree from xml file
    """
    # This function can likely be deleted
    if filename:
        tree = xml.etree.ElementTree.parse(filename)
    elif folder:
        # Search protocol list, parsing each XML file for protocols and goalsets
        logging.debug('Searching folder {} for protocols, goal sets'.format(folder))
        for f in os.listdir(folder):
            # This guy should prompt the user to find the appropriate file
            if f.endswith('.xml'):
                tree = xml.etree.ElementTree.parse(os.path.join(folder, f))
    return tree


def add_objective(obj, case, plan, beamset,
                  s_roi=None, s_dose=None,
                  s_weight=None, restrict_beamset=None):
    """
    adds an objective function to the optimization in RayStation after
    :param obj: child (roi-tag) of an ElementTree - consider mak
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
        logging.debug("Objective is added for protocol ROI: {} using plan ROI: {}".format(
            obj.find('name').text, s_roi))
        roi = s_roi
        obj.find('name').text = roi
    else:
        roi = obj.find('name').text
    #
    # Deal with relative or absolute volumes, modify the volume tag
    # (RayStation only allows relative volume roi's
    # :TODO: Check how to find existence of a tag in elementtree
    if obj.find('volume') is None:
        volume = None
    else:
        # If the user specified an absolute volume convert this into %
        if obj.find('volume').attrib["units"] == "cc":
            try:
                t = case.PatientModel.StructureSets[exam.Name]. \
                    RoiGeometries[s_roi]
                if t.HasContours():
                    roi_vol = t.GetRoiVolume()
                    volume = int(float(obj.find('volume').text) / roi_vol)
                    logging.debug('ROI: {} Protocol volume {} substituted with {}'.format(
                        obj.find('name').text, obj.find('volume').text, volume))
                    obj.find('volume').text = str(volume)
                    obj.find('volume').attrib["units"] = "%"
                else:
                    logging.warning('add_objective: {} has no contours, index undefined'.format(s_roi))
            except:
                logging.warning('add_objective: Error getting volume for {}, volume => 0.0'.format(s_roi))
        elif obj.find('volume').attrib["units"] == "%":
            volume = int(obj.find('volume').text)
    # Modify the dose tag if relative
    if s_dose:
        logging.debug('add_objective: ROI: {} Protocol dose {} {} substituted with {} Gy'.format(
            obj.find('name').text, obj.find('dose').text, obj.find('dose').attrib["units"], s_dose))
        if obj.find('dose').attrib["units"] == "%":
            obj.find('dose').attrib["units"] = "Gy"
            # Change the element to the substitute dose times the percentage of the reference
            obj.find('dose').text = float(s_dose) * float(obj.find('dose').text) / 100
            dose = float(obj.find('dose').text) * 100
        else:
            obj.find('dose').text = float(s_dose) * 100
    else:
        dose = float(obj.find('dose').text) * 100
    #
    # Read the weight variable
    if s_weight:
        logging.debug('add_objective: ROI: {} Protocol weight {} substituted with {}'.format(
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
        logging.debug('add_objective: Unsupported function type for ROI: {} with type: {}'.format(
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
            logging.warning('add_objective: Unsupported constraint specification {}'.format(
                obj.find('type').attrib['constraint']))
    if 'adapt' in obj.find('type').attrib:
        if obj.find('type').attrib['adapt'] == 'True':
            adapt_dose = True
        elif obj.find('type').attrib['adapt'] == 'False':
            adapt_dose = False
        else:
            logging.warning('add_objective: Unsupported type for attribute {}'.format(
                obj.find('type').attrib['adapt']))
    if obj.find('type').text == 'DFO':
        if obj.find('dose').attrib['units'] == "%":
            high_dose = 100 * float(s_dose) * float(obj.find('dose').text) / 100
            low_dose = 100 * float(s_dose) * float(obj.find('dose').attrib['low']) / 100
        elif obj.find('dose').attrib['units'] == "Gy":
            high_dose = 100 * float(obj.find('dose').text)
            low_dose = 100 * float(obj.find('dose').attrib['low'])
        else:
            logging.warning('add_objective: Unsupported doses for Dose Fall Off')
        if 'dist' in obj.find('type').attrib:
            low_dose_dist = float(obj.find('type').attrib['dist'])
        else:
            logging.warning('add_objective: Unknown low dose distance for Dose Fall Off')
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

    # UniformDose: Dose, Weight, % Volume=30?
    # UniformityConstraint?

    OptIndex = find_optimization_index(plan=plan,beamset=beamset)
    plan_optimization = plan.PlanOptimizations[OptIndex]

    # Add the objective
    try:
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
    except:
        logging.debug("Failed to add objective for ROI:" +
                      " {}, type {}, dose {}, weight {}, for beamset {}".format(
                          roi, function_type, dose, weight, restrict_beamset))
