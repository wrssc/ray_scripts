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
import connect


def select_objectives(folder=None, filename=None):
    """

    :param filename: os joined protocol name
    :param folder: folder from os to search within
    :return: tree: elementtree from xml file
    """
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


# def add_goal(goal, plan, roi=None, targets=None, exam=None, case=None):

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
        if obj.find('volume').attrib["units"] == "cc":
            try:
                t = case.PatientModel.StructureSets[exam.Name]. \
                    RoiGeometries[s_roi]
                if t.HasContours():
                    roi_vol = t.GetRoiVolume()
                    volume = float(obj.find('volume').text) / roi_vol
                    obj.find('volume').text = str(volume)
                    obj.find('volume').attrib["units"] = "%"
                else:
                    logging.warning('add_objective: {} has no contours, index undefined'.format(s_roi))
            except:
                logging.warning('add_objective: Error getting volume for {}, volume => 0.0'.format(s_roi))
        elif obj.find('volume').attrib["units"] == "%":
            volume = float(obj.find('volume').text)
    # Modify the dose tag if relative
    if s_dose:
        logging.debug('add_objective: ROI: {} Protocol dose {} {} substituted with {} Gy'.format(
            obj.find('name').text, obj.find('dose').text, obj.find('dose').attrib["units"], s_dose))
        if obj.find('dose').attrib["units"] == "%":
            obj.find('dose').attrib["units"] = "Gy"
            obj.find('dose').text = s_dose
            dose = float(s_dose) * 100
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

    # Find current Beamset Number and determine plan optimization
    OptIndex = 0
    IndexNotFound = True
    # In RS, OptimizedBeamSets objects are keyed using the DicomPlanLabel, or Beam Set name.
    # Because the key to the OptimizedBeamSets presupposes the user knows the PlanOptimizations index
    # this while loop looks for the PlanOptimizations index needed below by searching for a key
    # that matches the BeamSet DicomPlanLabel
    # This can likely be replaced with a list comprehension
    while IndexNotFound:
        try:
            OptName = plan.PlanOptimizations[OptIndex].OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            IndexNotFound = False
        except Exception:
            IndexNotFound = True
            OptIndex += 1
    if IndexNotFound:
        logging.warning(" Beamset optimization for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")
    else:
        # Found our index.  We will use a shorthand for the remainder of the code
        plan_optimization = plan.PlanOptimizations[OptIndex]
        # plan_optimization_parameters = plan.PlanOptimizations[OptIndex].OptimizationParameters
        logging.info(
            'optimization found, proceeding with plan.PlanOptimization[{}] for beamset {}'.format(
                OptIndex, plan_optimization.OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            ))

    retval_0 = plan_optimization.AddOptimizationFunction(FunctionType=function_type,
                                                         RoiName=roi,
                                                         IsConstraint=constraint,
                                                         RestrictAllBeamsIndividually=False,
                                                         RestrictToBeam=None,
                                                         IsRobust=robust,
                                                         RestrictToBeamSet=restrict_beamset,
                                                         UseRbeDose=False)
    try:
        retval_0 = plan_optimization.AddOptimizationFunction(FunctionType=function_type,
                                                             RoiName=roi,
                                                             IsConstraint=constraint,
                                                             RestrictAllBeamsIndividually=False,
                                                             RestrictToBeam=None,
                                                             IsRobust=robust,
                                                             RestrictToBeamSet=restrict_beamset,
                                                             UseRbeDose=False)
        retval_0.DoseFunctionParameters.Weight = weight
        retval_0.DoseFunctionParameters.DoseLevel = dose
        if volume:
            retval_0.PercentVolume = volume
        if 'Eud' in function_type:
            retval_0.DoseFunctionParameters.EudParameterA = eud_a
        # Dose fall off type of optimization option.
        if function_type == 'DoseFallOff':
            retval_0.DoseFunctionParameters.HighDoseLevel = high_dose
            retval_0.DoseFunctionParameters.LowDoseLevel = low_dose
            retval_0.DoseFunctionParameters.LowDoseDistance = low_dose_dist
            retval_0.DoseFunctionParameters.AdaptToTargetDoseLevels = adapt_dose
        logging.debug("add_objective: Added objective for ROI:" +
                      "{}, type {}, dose {}, weight {}, for beamset {}".format(
                          roi, function_type, dose, weight, restrict_beamset))
    except:
        logging.debug("add_objective: Failed to add objective for ROI:" +
                      " {}, type {}, dose {}, weight {}, for beamset {}".format(
                          roi, function_type, dose, weight, restrict_beamset))


def main():
    """ Temp chunk of code to try to open an xml file"""
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        plan = connect.get_current("Plan")
        beamset = connect.get_current("BeamSet")
    except:
        logging.warning("patient, case and examination must be loaded")

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'planning_structs_conventional.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder, file)
    tree = select_objectives(filename=path_protocols)
    logging.debug("selected file {}".format(path_protocols))
    # TODO::
    # Extend this for multiple objective sets found within a file
    # Consider adding functionality for protocols, orders, etc...
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    if tree.getroot().tag == 'objectiveset':
        logging.debug("parsing xml: {}".format(file))
        n = tree.find('name').text
        logging.debug('Found protocol {} in {}'.format(n, file))
        objectiveset = tree.getroot()
        objectives = objectiveset.findall('./objectives/roi')
        for o in objectives:
            o_name = o.find('name').text
            o_type = o.find('type').text
            logging.debug("objective: {} found with type {}".format(o_name, o_type))
            # TESTING ONLY - TO DO ELIMINATE THIS NEXT LINE
            if o.find('dose').attrib['units'] == '%':
                s_dose = '50'
            else:
                s_dose = None

            add_objective(o,
                          case=case,
                          plan=plan,
                          beamset=beamset,
                          s_roi=None,
                          s_dose=s_dose,
                          s_weight=None,
                          restrict_beamset=None)
    else:
        logging.debug('Could not find objective set using tree = {}'.format(tree))
    # for o in objs.findall('objectiveset'):
    #    logging.debug("Objectiveset {} found".format(o.find('name').text))
    # obj = {'function_type': 'MinEud',
    #       'roi_name': 'PTV1',
    #       'constraint': False,
    #       'eud_a': 3,
    #       'dose': 50}

    # add_objective(plan=plan,
    #              beamset=beamset,
    #              function_type='MinEud',
    #              weight=10,
    #              roi_name='PTV1',
    #              eud_a=3,
    #              dose=5000)


if __name__ == '__main__':
    main()
