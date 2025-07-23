from typing import NamedTuple, Tuple
from PlanReview.review_definitions import PASS, FAIL, ALERT


def determine_prescription_type(prescription_dose_reference):
    """Determines the aria_prescription_filters type based on the aria_prescription_filters dose reference.

    Args:
        prescription_dose_reference (PrescriptionDoseReference): The aria_prescription_filters dose reference to check.

    Returns:
        str: The aria_prescription_filtersption_filters type.
    """
    if hasattr(prescription_dose_reference, 'OnStructure'):
        return 'Roi-based', prescription_dose_reference.OnStructure.Name
    elif hasattr(prescription_dose_reference, 'OnDoseSpecificationPoint') and \
            prescription_dose_reference.OnDoseSpecificationPoint is not None:
        return 'Dsp-based', prescription_dose_reference.OnDoseSpecificationPoint.Name
    elif hasattr(prescription_dose_reference, 'PrescriptionType') and \
            prescription_dose_reference.PrescriptionType == 'DoseAtPoint':
        return 'Site-based', 'Site Name'  # Placeholder for site name
    else:
        return 'Unknown', None


def extract_site_name(description):
    """Extracts the site name from the aria_prescription_filters description.

    Args:
        description (str): The aria_prescription_filters description string.

    Returns:
        str: The extracted site name or 'Unknown' if not found.
    """
    if ':' in description:
        return description.split(':')[0]
    else:
        return None


def check_prescription_description(rso: NamedTuple) -> Tuple[str, str]:
    """Check Prescription Dose Description
    Verifies that each aria_prescription_filters‐dose reference on the beamset has the correct
    Description as set by `set_prescription_description`.

    Args:
        rso (NamedTuple): ScriptObjects in RayStation containing
            [case, exam, plan, beamset, db]

    Returns:
        Tuple[str, str]:
            - First element is the status: PASS if all descriptions are correct,
              ALERT if there are aria_prescription_filters references with no OnStructure,
              FAIL if any description is set incorrectly.
            - Second element is a human‐readable message.
    """
    # Local status for unknown types

    beamset = rso.beamset
    beamset_name = beamset.DicomPlanLabel

    # Attempt to retrieve the dose references

    try:
        pdrs = beamset.Prescription.PrescriptionDoseReferences
    except AttributeError:
        return FAIL, f"No PrescriptionDoseReferences found on beamset {beamset_name}"

    correct = []
    incorrect = []
    unknown = []
    indx = 1
    for pdr in pdrs:

        # Case A: has an associated ROI, DSP or Site
        rx_type, rx_obj_name = determine_prescription_type(pdr)
        if rx_obj_name is not None:

            # expected_desc = f"{rx_obj_name}:{beamset_name}"
            expected_desc = f"{beamset_name}|D{indx}"
            actual_desc = getattr(pdr, "Description", None)

            if actual_desc == expected_desc:
                correct.append(f"{actual_desc}")
            else:
                incorrect.append((rx_obj_name, actual_desc, expected_desc))
        # Case B: unknown aria_prescription_filters type
        else:
            unknown.append(rx_type)
        indx += 1

    # Evaluate results
    if incorrect:
        msg = (
            "Incorrect aria_prescription_filters descriptions:"
            + "".join(
                f"\u2022 {roi}: got '{got}', expected '{exp}', "
                for roi, got, exp in incorrect
            )
        )
        return FAIL, msg

    if unknown:
        msg = (
            "Unknown aria_prescription_filters types (no OnStructure):"
            + "".join(f"\u2002 {ptype}" for ptype in unknown)
        )
        return ALERT, msg

    # All good
    msg = (
        f"All aria_prescription_filters descriptions correct for beamset {beamset_name}:"
        + "\u2022 " + " \u2022 ".join(correct)
    )
    return PASS, msg
