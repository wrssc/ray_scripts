from PlanReview.review_definitions import PASS, FAIL, ELECTRON_MC_MIN_HISTORIES, ELECTRON_MC_UNCERTAINTY
from PlanReview.utils.review_api_versions import get_number_of_emc_histories


def emc_calc_params(beamset):
    """
    For each beam, go through the beam doses, and return the statistical uncertainty and the
    MC histories used in beam dose. Return the maximum uncertainty and minimum MC histories.
    :param beamset: RS beamset
    :return: NormUnc (the maximum normalized uncertainty) and number of histories used in calc
    """
    max_uncertainty = 0
    # Return electron monte carlo computational parameters
    for bd in beamset.FractionDose.BeamDoses:
        max_uncertainty = max(max_uncertainty, bd.DoseValues.RelativeStatisticalUncertainty)
    min_histories = get_number_of_emc_histories(beamset)

    return {'NormUnc': max_uncertainty, 'MinHist': min_histories}


def check_emc_statistics(rso):
    """
    Checks the electron monte carlo accuracy to ensure statistical limit is met
    :param rso: RS object
    :return: result, message: where message is the message to be displayed in the review, and
    result is the pass/fail status.
    """
    eval_current_emc = emc_calc_params(rso.beamset)
    if eval_current_emc['MinHist'] < ELECTRON_MC_MIN_HISTORIES \
            or eval_current_emc['NormUnc'] > ELECTRON_MC_UNCERTAINTY:
        stat_limit_hist = int(
            eval_current_emc['MinHist']
            * (eval_current_emc['NormUnc'] / ELECTRON_MC_UNCERTAINTY) ** 2.)
        recommended_histories = max(ELECTRON_MC_MIN_HISTORIES, stat_limit_hist)
        message = f"EMC uncertainty: {round(100 * eval_current_emc['NormUnc'])}% "
        f"recommend increasing histories from {eval_current_emc['MinHist']} "
        f"to {recommended_histories}"
        result = FAIL
    else:
        message = f'Clinically-acceptable EMC uncertainty: {round( 100 * eval_current_emc["NormUnc"])} ' \
                  f'and histories {eval_current_emc["MinHist"]}'
        result = PASS

    return result, message
