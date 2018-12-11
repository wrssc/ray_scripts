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
            if f.endswith('.xml'):
                tree = xml.etree.ElementTree.parse(os.path.join(folder, f))
    return tree


def add_objective(plan,
                  beamset,
                  function_type,
                  roi_name,
                  weight,
                  robust=False,
                  is_constraint=False,
                  dose=None,
                  volume=None,
                  eud_a=None,
                  restrict_beamset=None,
                  low_dose_dist=None,
                  high_dose=None,
                  low_dose=None,
                  adapt_dose=False,
                  ):
    """
    Add objective to RayStation
    :return:
    """

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
        logging.warning("optimize_plan: Beamset optimization for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")
    else:
        # Found our index.  We will use a shorthand for the remainder of the code
        plan_optimization = plan.PlanOptimizations[OptIndex]
        # plan_optimization_parameters = plan.PlanOptimizations[OptIndex].OptimizationParameters
        logging.info(
            'optimize_plan: Optimization found, proceeding with plan.PlanOptimization[{}] for beamset {}'.format(
                OptIndex, plan_optimization.OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            ))

    retval_0 = plan_optimization.AddOptimizationFunction(FunctionType=function_type,
                                                         RoiName=roi_name,
                                                         IsConstraint=is_constraint,
                                                         RestrictAllBeamsIndividually=False,
                                                         RestrictToBeam=None,
                                                         IsRobust=robust,
                                                         RestrictToBeamSet=restrict_beamset,
                                                         UseRbeDose=False)

    retval_0.DoseFunctionParameters.Weight=weight
    if dose:
        retval_0.DoseFunctionParameters.DoseLevel = dose
    if volume:
        retval_0.PercentVolume = volume
    if eud_a:
        retval_0.DoseFunctionParameters.EudParameterA = eud_a
    # It should be noted that the next 4 inputs should be combined into a "type" based argument for the
    # dose fall off type of optimization option.
    if high_dose:
        retval_0.DoseFunctionParameters.HighDoseLevel = high_dose
    if low_dose:
        retval_0.DoseFunctionParameters.LowDoseLevel = low_dose
    if low_dose_dist:
        retval_0.DoseFunctionParameters.LowDoseDistance = low_dose_dist
    if adapt_dose:
        retval_0.DoseFunctionParameters.AdaptToTargetDoseLevels = adapt_dose


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
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder,file)
    objs = select_objectives(filename=path_protocols)
    logging.debug("selected file {}".format(path_protocols))
    for o in objs.findall('objectiveset'):
        logging.debug("Objectiveset {} found".format(o.find('name').text))
    # obj = {'function_type': 'MinEud',
    #       'roi_name': 'PTV1',
    #       'constraint': False,
    #       'eud_a': 3,
    #       'dose': 50}
    # Types are:
    # MinDose: Dose, Weight
    # MaxDose: Dose, Weight
    # MinDvh: Dose, Weight, Volume
    # MaxDvh: Dose, Weight, Volume
    # UniformDose: Dose, Weight, % Volume=30?
    # MinEud: Dose, Weight, ParamA
    # MaxEud: Dose, Weight, ParamA
    # TargetEud: Dose, Weight, ParamA
    # DoseFallOff: HighDose, LowDose, LowDoseDistance, AdaptToTarget, ?RelativeLowDoseWeight=1
    # UniformityConstraint?
    add_objective(plan=plan,
                  beamset=beamset,
                  function_type='MinEud',
                  weight=10,
                  roi_name='PTV1',
                  eud_a=3,
                  dose=5000)


if __name__ == '__main__':
    main()
