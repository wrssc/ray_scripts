import logging
from .check_beamset_approved import check_beamset_approved
from .check_control_point_spacing import check_control_point_spacing
from .check_couch_type import check_couch_type
from .check_edw_mu import check_edw_mu
from .check_edw_field_size import check_edw_field_size
from .check_slice_thickness import check_slice_thickness
from .check_prv_status import check_prv_status
from .check_common_isocenter import check_common_isocenter
from .check_bolus_included import check_bolus_included
from .check_dose_grid import check_dose_grid
from .compute_vmat_beam_properties import compute_vmat_beam_properties
from .check_tomo_isocenter import check_tomo_isocenter
from .check_mod_factor import check_mod_factor
from .check_fraction_size import check_fraction_size
from .check_no_fly import check_no_fly
from .check_pacemaker import check_pacemaker
from PlanReview.review_definitions import REVIEW_LEVELS


def get_beamset_level_tests(rso, physics_review=True):
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}

    beamset_checks_dict = {
        f"{REVIEW_LEVELS['PLAN_DATA']}::Beamset approval status":
            (check_beamset_approved, {"do_physics_review": physics_review}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Isocenter Position Identical":
            (check_common_isocenter, {"tolerance": 1e-15}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Check Fractionation":
            (check_fraction_size, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Couch Type Correct":
            (check_couch_type, {}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Slice Thickness Comparison":
            (check_slice_thickness, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Bolus Application":
            (check_bolus_included, {}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::No Fly Zone Dose Check":
            (check_no_fly, {}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Check for pacemaker compliance":
            (check_pacemaker, {}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Dose Grid Size Check":
            (check_dose_grid, {}),
        f"{REVIEW_LEVELS['OPTIMIZATION']}::Planning Risk Volume Assessment":
            (check_prv_status, {}),
    }

    # Plan check for VMAT
    #
    technique = rso.beamset.DeliveryTechnique if rso.beamset else None
    if technique == 'DynamicArc':
        if rso.beamset.Beams[0].HasValidSegments:
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Control Point Spacing"] = (
                check_control_point_spacing,
                {'expected': 2.})
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset Complexity"] = (
                compute_vmat_beam_properties, {})
    elif technique == 'SMLC':
        try:
            _ = rso.beamset.Beams[0].Segments[
                0]  # Determine if beams have segments
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset Complexity"] = (
                compute_vmat_beam_properties, {})
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::EDW MU Check"] = (
                check_edw_mu, {})
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::EDW FieldSize Check"] = (
                check_edw_field_size, {})
        except Exception as e:
            pass
    elif 'Tomo' in technique:
        try:
            _ = rso.beamset.Beams[0].Segments[0]  # If beams have segments
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Isocenter Lateral Acceptable"] = (
                check_tomo_isocenter, {})
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Modulation Factor Acceptable"] = (
                check_mod_factor, {})
        except Exception as e:
            logging.warning(f'Error observed during tomo specific checks {e}')
            pass
    return beamset_checks_dict
