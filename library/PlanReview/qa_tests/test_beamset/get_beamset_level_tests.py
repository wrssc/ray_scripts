import logging
from .check_beamset_approved import check_beamset_approved
from .check_control_point_spacing import check_control_point_spacing
from .check_couch_type import check_couch_type
from .check_edw_mu import check_edw_mu
from .check_emc_statistics import check_emc_statistics
from .check_edw_field_size import check_edw_field_size
from .check_slice_thickness import check_slice_thickness
from .check_prv_status import check_prv_status
from .check_common_isocenter import check_common_isocenter
from .check_bolus_included import check_bolus_included
from .check_dose_grid import check_dose_grid
# from PlanReview.qa_tests.test_sandbox.compute_vmat_beam_properties import compute_vmat_beam_properties
from .check_isocenter_clearance import check_isocenter_clearance
from .check_tomo_isocenter import check_tomo_isocenter
from .check_mod_factor import check_mod_factor
from .check_fraction_size import check_fraction_size
from .check_no_fly import check_no_fly
from .check_pacemaker import check_pacemaker
from .parse_beamset_selection import parse_beamset_selection
from .compare_rx_to_preplan import match_fractions_to_preplan
from .compare_rx_to_preplan import match_rx_to_preplan
from .check_prescription_description import check_prescription_description
from PlanReview.review_definitions import REVIEW_LEVELS
from PlanReview.qa_tests.analyze_logs import retrieve_logs


def get_beamset_level_tests(rso, physics_review=True, log_messages=None, values=None,
                            roi_voxel_representations=None):
    if log_messages is None:
        log_messages = retrieve_logs(rso)
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}
    if roi_voxel_representations is None:
        rois_checked=None
        rois_to_delete=None
    else:
        rois_checked = roi_voxel_representations['rois_checked']
        rois_to_delete = roi_voxel_representations['rois_to_delete']

    beamset_checks_dict = {
        f"{REVIEW_LEVELS['PLAN_DATA']}::Beamset approval status":
            (check_beamset_approved, {"do_physics_review": physics_review}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset Template Selection":
            (parse_beamset_selection, {"LOG_MESSAGES": log_messages}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Isocenter Position Identical":
            (check_common_isocenter, {"tolerance": 1e-15}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Check Fractionation":
            (check_fraction_size, {}),
        f"{REVIEW_LEVELS['PATIENT_MODEL']}::Couch Type Correct":
            (check_couch_type, {}),
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Clearance Check":
            (check_isocenter_clearance,
             {'rois_checked': rois_checked, 'rois_to_delete': rois_to_delete}),
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
        f"{REVIEW_LEVELS['PLAN_DESIGN']}::Prescription description (Aria) reference point":
            (check_prescription_description, {}),
    }
    if values:
        beamset_checks_dict.update({
            f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset fractionation vs TPO":
                (match_fractions_to_preplan, {'VALUES': values}),
            f"{REVIEW_LEVELS['PLAN_DESIGN']}::Target Doses Match Treatment Planning Order":
                (match_rx_to_preplan, {'VALUES': values}),
                })

    # Plan check for VMAT
    #
    technique = rso.beamset.DeliveryTechnique if rso.beamset else None
    if technique == 'DynamicArc':
        try:
            if rso.beamset.Beams[0].HasValidSegments:
                beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Control Point Spacing"] = (
                    check_control_point_spacing, {'expected': 2.})
                # TODO: Add after more testing
                #     beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset Complexity"] = (
                #     compute_vmat_beam_properties, {})
                beamset_checks_dict[f"{REVIEW_LEVELS['OPTIMIZATION']}::Planning Risk Volume Assessment"] = \
                    (check_prv_status, {})
        except Exception as e:
            if 'Index was out of range. Must be non-negative ' in str(e):
                pass
    elif technique == 'SMLC':
        if rso.beamset.Modality == 'Electrons':
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Electron MC Statistics"] = (
                check_emc_statistics, {})
        else:
            try:
                _ = rso.beamset.Beams[0].Segments[0]  # Determine if beams have segments
                # TODO: Add after more testing
                #     beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Beamset Complexity"] = (
                #     compute_vmat_beam_properties, {})
                beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::EDW MU Check"] = (
                    check_edw_mu, {})
                beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::EDW FieldSize Check"] = (
                    check_edw_field_size, {})
            except Exception as e:
                logging.warning(f'Error observed during SMLC-specific checks {e}')
                pass
    elif 'Tomo' in technique:
        try:
            _ = rso.beamset.Beams[0].Segments[0]  # If beams have segments
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Isocenter Lateral Acceptable"] = (
                check_tomo_isocenter, {})
            beamset_checks_dict[f"{REVIEW_LEVELS['PLAN_DESIGN']}::Modulation Factor Acceptable"] = (
                check_mod_factor, {})
            beamset_checks_dict[f"{REVIEW_LEVELS['OPTIMIZATION']}::Planning Risk Volume Assessment"] = \
                check_prv_status, {}
        except Exception as e:
            logging.warning(f'Error observed during Tomo-specific checks {e}')
            pass
    return beamset_checks_dict
