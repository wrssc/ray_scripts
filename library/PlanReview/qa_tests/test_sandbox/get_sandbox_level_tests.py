from .compute_vmat_beam_properties import compute_vmat_beam_properties
from .check_max_dose_point import check_max_dose_point
from PlanReview.qa_tests.test_beamset.compare_rx_to_preplan import match_rx_to_preplan
from PlanReview.review_definitions import REVIEW_LEVELS


def get_sandbox_level_tests(rso, physics_review=True, values=None):
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}

    sandbox_checks_dict = {

        f"{REVIEW_LEVELS['SANDBOX']}::Maximum Dose Inside Targets":
            (check_max_dose_point, {}),
        f"{REVIEW_LEVELS['SANDBOX']}::Beamset Complexity":
            (compute_vmat_beam_properties, {}),
    }
    if values:
        sandbox_checks_dict.update({
            f"{REVIEW_LEVELS['SANDBOX']}::Target Doses Match Treatment Planning Order":
                (match_rx_to_preplan, {'VALUES': values})
        })
    return sandbox_checks_dict
