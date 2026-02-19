import logging
from library.api.dispatcher import APIDispatcher

dispatcher = APIDispatcher()


def add_clinical_goal_v15(
        plan,
        roi_name,
        goal_criteria,
        goal_type,
        primary_acceptance_level,
        secondary_acceptance_level,
        parameter_value,
        is_comparative_goal,
        beamset_association,
        priority,
        associate_to_plan,
):
    logging.warning("Secondary acceptance level is not supported in < RS 2024 "
                    "Ignoring secondary acceptance level argument.")
    acceptance_level = primary_acceptance_level
    if parameter_value:

        plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi_name,
                                                         GoalCriteria=goal_criteria,
                                                         GoalType=goal_type,
                                                         AcceptanceLevel=acceptance_level,
                                                         ParameterValue=parameter_value,
                                                         IsComparativeGoal=is_comparative_goal,
                                                         BeamSet=beamset_association,
                                                         Priority=priority,
                                                         AssociateToPlan=associate_to_plan,
                                                         )

    else:
        plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi_name,
                                                         GoalCriteria=goal_criteria,
                                                         GoalType=goal_type,
                                                         AcceptanceLevel=acceptance_level,
                                                         IsComparativeGoal=is_comparative_goal,
                                                             BeamSet=beamset_association,
                                                            Priority=priority,
                                                            AssociateToPlan=associate_to_plan)
def add_clinical_goal_v17(
        plan,
        roi_name,
        goal_criteria,
        goal_type,
        primary_acceptance_level,
        secondary_acceptance_level,
        parameter_value,
        is_comparative_goal,
        beamset_association,
        priority,
        associate_to_plan,
):
    if parameter_value:
        plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi_name,
                                                         GoalCriteria=goal_criteria,
                                                         GoalType=goal_type,
                                                         PrimaryAcceptanceLevel=primary_acceptance_level,
                                                         SecondaryAcceptanceLevel=secondary_acceptance_level,
                                                         ParameterValue=parameter_value,
                                                         IsComparativeGoal=is_comparative_goal,
                                                         BeamSet=beamset_association,
                                                         Priority=priority,
                                                         AssociateToPlan=associate_to_plan,
                                                         )
    else:
        plan.TreatmentCourse.EvaluationSetup.AddClinicalGoal(RoiName=roi_name,
                                                         GoalCriteria=goal_criteria,
                                                         GoalType=goal_type,
                                                         PrimaryAcceptanceLevel=primary_acceptance_level,
                                                         SecondaryAcceptanceLevel=secondary_acceptance_level,
                                                         IsComparativeGoal=is_comparative_goal,
                                                             BeamSet=beamset_association,
                                                            Priority=priority,
                                                            AssociateToPlan=associate_to_plan)


dispatcher.register('add_clinical_goal', 12, add_clinical_goal_v15)
dispatcher.register('add_clinical_goal', 15, add_clinical_goal_v15)
dispatcher.register('add_clinical_goal', 17, add_clinical_goal_v17)


@dispatcher.dispatch('add_clinical_goal')
def add_clinical_goal(plan, roi_name, goal_criteria, goal_type,
                      primary_acceptance_level, secondary_acceptance_level,
                      parameter_value, is_comparative_goal, beamset_association,
                      priority, associate_to_plan):
    pass
