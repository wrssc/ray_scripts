""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""

def add_objective(function_type,
                  roi_name,
                  dose,
                  is_constraint,
                  restrict_all_beams,
                  restrict_beam,
                  robust,
                  restrict_beamset,
                  use_rbe,
                  volume=volume):
    """
    Add objective to RayStation
    :return:
    """

    with CompositeAction('Add Optimization Function'):
        retval_0 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="MinDose",
                                                                     RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None,
                                                                     IsRobust=False,
                                                                     RestrictToBeamSet=None,
                                                                     UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[0].DoseFunctionParameters.DoseLevel = 5000

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_1 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="MaxDose", RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[1].DoseFunctionParameters.DoseLevel = 5000

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_2 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="MinDvh", RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[2].DoseFunctionParameters.DoseLevel = 5000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[2].DoseFunctionParameters.PercentVolume = 30

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_3 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="UniformDose", RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[3].DoseFunctionParameters.DoseLevel = 5000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[3].DoseFunctionParameters.PercentVolume = 30

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_4 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="MinEud", RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[4].DoseFunctionParameters.DoseLevel = 5000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[4].DoseFunctionParameters.EudParameterA = 3

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_5 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="MaxEud", RoiName="PTV_p",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[5].DoseFunctionParameters.DoseLevel = 5000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[5].DoseFunctionParameters.EudParameterA = 3

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_6 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="TargetEud", RoiName="GTV",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[6].DoseFunctionParameters.DoseLevel = 5000

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_7 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="TargetEud", RoiName="GTV",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[7].DoseFunctionParameters.DoseLevel = 5000

        # CompositeAction ends

    with CompositeAction('Add Optimization Function'):
        retval_8 = plan.PlanOptimizations[0].AddOptimizationFunction(FunctionType="DoseFallOff", RoiName="GTV",
                                                                     IsConstraint=False,
                                                                     RestrictAllBeamsIndividually=False,
                                                                     RestrictToBeam=None, IsRobust=False,
                                                                     RestrictToBeamSet=None, UseRbeDose=False)

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[8].DoseFunctionParameters.HighDoseLevel = 6000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[8].DoseFunctionParameters.LowDoseLevel = 2000

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[8].DoseFunctionParameters.LowDoseDistance = 2

        plan.PlanOptimizations[0].Objective.ConstituentFunctions[
            8].DoseFunctionParameters.AdaptToTargetDoseLevels = True

        # CompositeAction ends

def load_objectives(protocol_file):
    """
    load objectives from an xml file
    :param protocol_file:
    :return:
    """

    # Script recorded 03 Dec 2018

    #   RayStation version: 7.0.0.19
    #   Selected patient: ...

    from connect import *

    plan = get_current("Plan")


