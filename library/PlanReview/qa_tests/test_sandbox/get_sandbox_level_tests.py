from .check_isocenter_clearance import check_isocenter_clearance


def get_sandbox_level_tests(rso, physics_review=True):
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}

    sandbox_checks_dict = {
        "Couch Zero Full Rotation Clearance Check":
            (check_isocenter_clearance, {}),
    }
    return sandbox_checks_dict
