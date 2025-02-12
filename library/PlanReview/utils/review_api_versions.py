import logging
from .review_dispatcher import APIDispatcher


dispatcher = APIDispatcher()  # Create an instance of the dispatcher


#
# Unique ID calls
def get_unique_id_beamset_v12(beamset):
    # Version 12 specific code
    return beamset.UniqueId


def get_unique_id_beamset_v15(beamset):
    # Version 15 specific code - use the DICOM UID
    return beamset.GetRadiationSetUuid()


def get_unique_id_plan_v12(plan):
    # Version 12 specific code
    return plan.UniqueId


def get_unique_id_plan_v15(plan):
    # Version 15 specific code - use the DICOM UID
    return plan.GetPlanUuid()


#
# Plan and Beamset Reviewer data
def get_plan_reviewer_name_v12(plan):
    # Version 12 specific code
    return plan.Review.ReviewerName


def get_plan_reviewer_name_v15(plan):
    # Version 15 specific code
    return plan.Review.ReviewerLoginName


def get_beamset_reviewer_name_v12(beamset):
    # Version 12 specific code
    return beamset.Review.ReviewerName


def get_beamset_reviewer_name_v15(beamset):
    # Version 15 specific code
    return beamset.Review.ReviewerLoginName


def get_prescription_dose_references_v15(beamset):
    # Version 15 specific code
    return beamset.Prescription.PrescriptionDoseReferences


def get_prescription_dose_references_v12(beamset):
    # Version 12 specific code
    return beamset.Prescription.PrescriptionDoseReferences


def get_number_of_emc_histories_v12(beamset):
    return beamset.FractionDose.DoseValues.AlgorithmProperties.MonteCarloHistoriesPerAreaFluence


def get_number_of_emc_histories_v15(beamset):
    return beamset.FractionDose.DoseValues.MCTotalNumberOfHistories


def ui_click_plan_optimization_v12(ui):
    try:
        ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()
    except Exception as e:
        logging.debug(f'Unable to change viewing windows: {e}')


def ui_click_plan_optimization_v15(ui):
    try:
        ui.TitleBar.MenuItem['Plan optimization'].Button_Plan_Optimization.Click()
    except Exception as e:
        logging.debug(f'Unable to change viewing windows: {e}')


def get_acceptance_level_from_planning_goal_v12(goal):
    return goal.AcceptanceLevel


def get_acceptance_level_from_planning_goal_v15(goal):
    return goal.PrimaryAcceptanceLevel


# REGISTER THESE FUNCTIONS WITH THE DISPATCHER
dispatcher.register('get_unique_id_beamset', 12, get_unique_id_beamset_v12)
dispatcher.register('get_unique_id_beamset', 15, get_unique_id_beamset_v15)

dispatcher.register('get_unique_id_plan', 12, get_unique_id_plan_v12)
dispatcher.register('get_unique_id_plan', 15, get_unique_id_plan_v15)

dispatcher.register('get_plan_reviewer_name', 12, get_plan_reviewer_name_v12)
dispatcher.register('get_plan_reviewer_name', 15, get_plan_reviewer_name_v15)

dispatcher.register('get_beamset_reviewer_name', 12, get_beamset_reviewer_name_v12)
dispatcher.register('get_beamset_reviewer_name', 15, get_beamset_reviewer_name_v15)

dispatcher.register('get_prescription_dose_references', 12, get_prescription_dose_references_v12)
dispatcher.register('get_prescription_dose_references', 15, get_prescription_dose_references_v15)

dispatcher.register('get_number_of_emc_histories', 12, get_number_of_emc_histories_v12)
dispatcher.register('get_number_of_emc_histories', 15, get_number_of_emc_histories_v15)

dispatcher.register('ui_click_plan_optimization', 12, ui_click_plan_optimization_v12)
dispatcher.register('ui_click_plan_optimization', 15, ui_click_plan_optimization_v15)

dispatcher.register('get_acceptance_level_from_planning_goal', 12, get_acceptance_level_from_planning_goal_v12)
dispatcher.register('get_acceptance_level_from_planning_goal', 15, get_acceptance_level_from_planning_goal_v15)


@dispatcher.dispatch('get_unique_id_beamset')
def get_unique_id_beamset(beamset):
    pass


@dispatcher.dispatch('get_unique_id_plan')
def get_unique_id_plan(plan):
    pass


@dispatcher.dispatch('get_plan_reviewer_name')
def get_plan_reviewer_name(plan):
    pass


@dispatcher.dispatch('get_beamset_reviewer_name')
def get_beamset_reviewer_name(beamset):
    pass


@dispatcher.dispatch('get_prescription_dose_references')
def get_prescription_dose_references(beamset):
    pass


@dispatcher.dispatch('get_number_of_emc_histories')
def get_number_of_emc_histories(beamset):
    pass


@dispatcher.dispatch('ui_click_plan_optimization')
def ui_click_plan_optimization(ui):
    pass


@dispatcher.dispatch('get_acceptance_level_from_planning_goal')
def get_acceptance_level_from_planning_goal(goal):
    pass
