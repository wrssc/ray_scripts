from .check_beamset_approved import check_beamset_approved
from .check_transfer_approved import check_transfer_approved
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
from .beamset_review_tests import *


def get_beamset_level_tests(rso, physics_review=True):
    # Don't proceed if no beamset is defined
    if not rso.beamset:
        return {}

    beamset_checks_dict = {
        "Beamset approval status":
            (check_beamset_approved, {"do_physics_review": physics_review}),
        "Isocenter Position Identical":
            (check_common_isocenter, {"tolerance": 1e-15}),
        "Check Fractionation":
            (check_fraction_size, {}),
        "Couch Type Correct":
            (check_couch_type, {}),
        "Slice Thickness Comparison":
            (check_slice_thickness, {}),
        "Bolus Application":
            (check_bolus_included, {}),
        "No Fly Zone Dose Check":
            (check_no_fly, {}),
        "Check for pacemaker compliance":
            (check_pacemaker, {}),
        "Dose Grid Size Check":
            (check_dose_grid, {}),
        "Planning Risk Volume Assessment":
            (check_prv_status, {}),
        "Couch Zero Full Rotation Clearance Check":
            (check_isocenter_clearance, {}),
    }

    # Plan check for VMAT
    #
    technique = rso.beamset.DeliveryTechnique if rso.beamset else None
    if technique == 'DynamicArc':
        if rso.beamset.Beams[0].HasValidSegments:
            beamset_checks_dict["Control Point Spacing"] = (
                check_control_point_spacing,
                {'expected': 2.})
            beamset_checks_dict["Beamset Complexity"] = (
                compute_vmat_beam_properties, {})
    elif technique == 'SMLC':
        try:
            _ = rso.beamset.Beams[0].Segments[
                0]  # Determine if beams have segments
            beamset_checks_dict["Beamset Complexity"] = (
                compute_vmat_beam_properties, {})
            beamset_checks_dict["EDW MU Check"] = (
                check_edw_mu, {})
            beamset_checks_dict["EDW FieldSize Check"] = (
                check_edw_field_size, {})
        except Exception as e:
            pass
    elif 'Tomo' in technique:
        try:
            _ = rso.beamset.Beams[0].Segments[0]  # If beams have segments
            beamset_checks_dict["Isocenter Lateral Acceptable"] = (
                check_tomo_isocenter, {})
            beamset_checks_dict["Modulation Factor Acceptable"] = (
                check_mod_factor, {})
            beamset_checks_dict["Transfer BeamSet Approval Status"] = (
                check_transfer_approved, {})
        except Exception as e:
            pass
    return beamset_checks_dict
