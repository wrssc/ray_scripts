from .check_isocenter_clearance import check_isocenter_clearance
from .compute_vmat_beam_properties import compute_vmat_beam_properties
from PlanReview.review_definitions import REVIEW_LEVELS


def get_sandbox_level_tests(rso, physics_review=True):
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}

    sandbox_checks_dict = {
        f"{REVIEW_LEVELS['SANDBOX']}::Couch Zero Full Rotation Clearance Check":
            (check_isocenter_clearance, {}),
        f"{REVIEW_LEVELS['SANDBOX']}::Beamset Complexity":
            (compute_vmat_beam_properties, {})
    }
    return sandbox_checks_dict
