import re
from typing import Dict, List, Set, Any, Tuple
from dataclasses import dataclass, field
from PlanReview.review_definitions import BOLUS_NAMES, PASS, FAIL, ALERT
from PlanReview.utils import get_roi_list, match_roi_name


@dataclass
class BolusState:
# Raw RS objects
    plan: Any
    beamset: Any
    case: Any
    exam: Any

    # Beam-level info
    beams: List[Any] = field(default_factory=list)
    beam_bolus_map: Dict[Any, str] = field(default_factory=dict)
    iso_groups: Dict[str, List[Any]] = field(default_factory=dict)
    bolus_used_this_beamset: bool = False

    # ROI-level info
    bolus_rois: List[Any] = field(default_factory=list)
    valid_bolus_rois: List[Any] = field(default_factory=list)
    invalid_bolus_rois: List[Any] = field(default_factory=list)

    # Usage across beamsets
    bolus_usage_by_beamset: Dict[str, Set[str]] = field(default_factory=dict)
    all_applied_bolus_names: Set[str] = field(default_factory=set)
    bolus_used_anywhere: bool = False

    # Per-ROI usage in the entire plan
    roi_used_anywhere: Dict[str, bool] = field(default_factory=dict)


def applied_bolus_names(beamset: Any) -> Set[str]:
    """ Return list of bolus names applied to beams in the beamset """
    applied_boli = set([beam_has_bolus_applied(b) for b in beamset.Beams])
    return applied_boli

def find_bolus_types(case: Any, roi_list: List[Any]) -> List[str]:
    bolus_types = []
    for roi_name in roi_list:
        roi = case.PatientModel.RegionsOfInterest[roi_name]
        if roi.Type == "Bolus":
            bolus_types.append(roi.Name)
    return bolus_types

def name_matches_bolus_pattern(name: str) -> bool:
    # Case insensitive match
    pattern1 = r"^Bolus_\d+mm_\d+x\d+$"  # e.g., Bolus_5mm_20x20
    pattern2 = r"^Bolus_custom$"          # e.g., Bolus_custom
    if re.match(pattern1, name, re.IGNORECASE) or re.match(pattern2, name, re.IGNORECASE):
        return True
    return False


# def find_unapplied_boli(plan: Any, beamset: Any, bolus_names: List[str]) -> Dict:
#     applied_boli = applied_bolus_names(beamset)
#     # Check if there are structures named as bolus but not applied to any beams
#     unused_boli = []
#     correctly_applied_boli = []
#     for b in bolus_names:
#         if b not in applied_boli:
#             unused_boli.append(b)
#         else:
#             correctly_applied_boli.append(b)
#     # Check to see if the unused bolus is applied in other beamsets
#     never_used_boli = []
#     for bolus_name in unused_boli:
#         plan_bolus_usage = []
#         for bs in plan.BeamSets:
#             bs_boli = applied_bolus_names(bs)
#             if bolus_name in bs_boli:
#                 plan_bolus_usage.append(bs.DicomPlanLabel)
#         if not plan_bolus_usage:
#             never_used_boli.append(bolus_name)
#     return {'applied_boli': applied_boli, 'unused_boli': unused_boli, 'never_used_boli': never_used_boli}
#
#
# def beams_with_bolus_applied(beamset: Any) -> Dict:
#     beams_with_bolus = {}
#     for beam in beamset.Beams:
#         beams_with_bolus[beam.Name] = beam_has_bolus_applied(beam)
#     return beams_with_bolus
#

def beam_has_bolus_applied(beam):
    if hasattr(beam, 'Boli') and len(beam.Boli)>0:
        return beam.Boli[0].Name
    return None


def gather_bolus_state(case: Any, plan: Any, beamset: Any, exam: Any)-> BolusState:
    """ Gather all relevant bolus state information for the given plan and beamset """
    state = BolusState(plan=plan, beamset=beamset, case=case, exam=exam)

    # Beam-level info
    state.beams = list(beamset.Beams)
    state.beam_bolus_map = {b.Name: beam_has_bolus_applied(b) for b in state.beams}
    state.bolus_used_this_beamset = any(bolus_name is not None for bolus_name in state.beam_bolus_map.values())

    # Group beams by isocenter
    for beam in state.beams:
        iso_name = beam.Isocenter.Annotation.Name
        state.iso_groups.setdefault(iso_name, []).append(beam)

    # ROI-level info
    roi_list = get_roi_list(case, exam_name=None)
    bolus_names = match_roi_name(roi_names=BOLUS_NAMES, roi_list=roi_list,
                                 mode="contains", case_sensitive=False)
    # Append any ROIs with type 'Bolus'
    bolus_types = [name for name in find_bolus_types(case, roi_list) if name not in bolus_names]
    bolus_names.extend(bolus_types)
    # Append any ROIs that are used as bolus in any beamset
    # for bs in plan.BeamSets:
    #    bs_boli = applied_bolus_names(bs)
    #    for bolus_name in bs_boli:
    #        if bolus_name and bolus_name not in bolus_names:
    #            bolus_names.append(bolus_name)
    bs_boli = applied_bolus_names(state.beamset)
    bs_boli = [b for b in bs_boli if b is not None]
    bolus_names.extend([name for name in bs_boli if name and name not in bolus_names])
    # Store bolus ROIs
    state.bolus_rois = bolus_names
    # Check naming validity
    for roi_name in bolus_names:
        if name_matches_bolus_pattern(roi_name):
            if roi_name not in state.valid_bolus_rois:
                state.valid_bolus_rois.append(roi_name)
        else:
            state.invalid_bolus_rois.append(roi_name)
    # Evaluate plan level bolus usage
    for bs in state.plan.BeamSets:
        bs_name = str(bs.DicomPlanLabel)
        bs_boli = applied_bolus_names(bs)
        bs_boli = {b for b in bs_boli if b is not None}
        state.bolus_usage_by_beamset[bs_name] = bs_boli
        state.all_applied_bolus_names = state.all_applied_bolus_names.union(bs_boli)

    state.bolus_used_anywhere = bool(state.all_applied_bolus_names)

    # Per-ROI usage in the entire plan
    for roi_name in state.bolus_rois:
        state.roi_used_anywhere[roi_name] = roi_name in state.all_applied_bolus_names

    return state


def find_beams_missing_bolus(beamset: Any) -> Dict[str, Dict[str, List[str]]]:
    """
    Directly check bolus consistency per isocenter:

    Rule:
        If ANY beam in an isocenter has bolus, then ALL beams in that isocenter
        must have bolus.

    Returns:
        {
            beamset_label: {
                isocenter_name: [beam_missing_bolus, ...],
                ...
            },
            ...
        }
        Empty dict = no issues.
    """
    issues: Dict[str, Dict[str, List[str]]] = {}

    bs_label = beamset.DicomPlanLabel

    # Group beams by isocenter
    iso_groups: Dict[str, List[Any]] = {}
    for beam in beamset.Beams:
        iso_groups.setdefault(beam.Isocenter.Annotation.Name, []).append(beam)

    # Evaluate each isocenter group
    for iso_name, beams in iso_groups.items():
        # Bolus names: [None, "Bolus10mm", ...]
        bolus_list = [beam_has_bolus_applied(b) for b in beams]

        # If no bolus at all -> no problem
        if all(b is None for b in bolus_list):
            continue

        # Some have bolus, some do not -> problem
        missing = [
            beam.Name
            for beam, bol in zip(beams, bolus_list)
            if bol is None
        ]

        if missing:
            issues.setdefault(bs_label, {})[iso_name] = missing

    return issues


def check_isocenter_consistency(state: BolusState) -> Tuple[List[str], List[str]]:
    """Return (fail_issues, alert_issues) related to isocenter consistency"""
    fail_issues: List[str] = []
    alert_issues: List[str] = []
    bs_label = str(state.beamset.DicomPlanLabel)
    # Look for mixed bolus usage
    missing_by_iso = find_beams_missing_bolus(state.beamset)
    if missing_by_iso and bs_label in missing_by_iso:
        for iso_name, beams in missing_by_iso[bs_label].items():
            alert_issues.append(
                f"Mixed bolus usage in isocenter '{iso_name}': beams missing bolus: {beams}"
            )
    # Look for mixed bolus names within isocenters
    for iso_name, iso_beams in state.iso_groups.items():
        bolus_names_in_iso = {
            state.beam_bolus_map[b.Name]
            for b in iso_beams
            if state.beam_bolus_map.get(b.Name) is not None
        }
        if len(bolus_names_in_iso) > 1:
            alert_issues.append(
                f"In beamset {bs_label}, isocenter {iso_name} uses multiple bolus rois "
                f"{sorted(bolus_names_in_iso)}; aria alert needed or use a single bolus per isocenter."
            )
    return fail_issues, alert_issues


def check_bolus_naming(state: BolusState) -> Tuple[List[str], List[str]]:
    """Return (fail_issues, alert_issues) for bolus naming correctness."""
    fail_issues: List[str] = []
    alert_issues: List[str] = []

    for roi_name in state.invalid_bolus_rois:
        used_anywhere = state.roi_used_anywhere.get(roi_name, False)
        if used_anywhere:
            # Misnamed but used -> ALERT
            alert_issues.append(
                f"Bolus ROI '{roi_name}' is used but does not follow naming convention "
                f"(Bolus_<thickness>mm_<width>x<height> or Bolus_custom); rename for RTT clarity."
            )
        else:
            # Misnamed and unused -> FAIL
            fail_issues.append(
                f"Bolus-related ROI '{roi_name}' is not used in any beamset and does not "
                f"follow naming convention; delete this unused contour."
            )

    return fail_issues, alert_issues


def check_bolus_usage_hygiene(state: BolusState) -> Tuple[List[str], List[str]]:
    """Return (fail_issues, alert_issues) for plan-wide bolus usage hygiene."""
    fail_issues: List[str] = []
    alert_issues: List[str] = []

    plan_name = str(state.plan.Name)

    # Validly named bolus ROIs that are never used anywhere => FAIL
    for roi_name in state.valid_bolus_rois:
        used_anywhere = state.roi_used_anywhere.get(roi_name, False)
        if not used_anywhere:
            fail_issues.append(
                f"Validly named bolus ROI '{roi_name}' is not applied to any beam in plan "
                f"'{plan_name}'; it should be deleted."
            )

    # Misnamed, unused ROIs already handled as FAIL in check_bolus_naming.
    # Multiple-ROI-with-some-unused is also implicitly covered by the loop above.

    return fail_issues, alert_issues

def aggregate_bolus_issues(
    state: BolusState,
    fail_issues: List[str],
    alert_issues: List[str],
) -> Tuple[str, str]:
    """
    Decide final PASS/ALERT/FAIL and construct the message.

    Returns:
        (status, message)
    """
    if fail_issues:
        status = FAIL
        message = " ; ".join(fail_issues + alert_issues)
        return status, message

    if alert_issues:
        status = ALERT
        message = "; ".join(alert_issues)
        return status, message

    # PASS cases
    bs_label = str(state.beamset.DicomPlanLabel)
    plan_name = str(state.plan.Name)

    if not state.bolus_rois and not state.bolus_used_anywhere:
        message = (
            f"PASS: No bolus ROIs and no bolus usage found in plan '{plan_name}'."
        )
    elif state.bolus_used_this_beamset:
        message = (
            f"PASS: Bolus usage in beamset {bs_label} is consistent across all "
            f"isocenters and follows naming and usage conventions."
        )
    else:
        # No bolus in this beamset, but bolus may be used correctly in other beamsets
        message = (
            f"PASS: No bolus used in beamset {bs_label}; any bolus in plan "
            f"'{plan_name}' is applied correctly in other beamsets and passes "
            f"naming/usage checks."
        )

    return PASS, message


def check_bolus_included(rso):

    """ Check Bolus Included
    Checks if the given bolus is applied to any beam in the beamset.

    Args:
        rso (Union[NamedTuple, dict]): ScriptObjects in Raystation containing [case,exam,plan,beamset,db]

    Returns:
        Tuple[str, str]: First element is the status (PASS/FAIL),
                         Second element is the message string

        Bolus Validation Rule Set
    =========================

    This check enforces correct usage, naming, and cleanliness of bolus ROI
    structures within a RayStation plan. The logic operates at the beamset level
    but inspects plan-wide bolus usage as needed to determine whether a bolus ROI
    is properly applied or should have been deleted.

    Severity Hierarchy:
        FAIL > ALERT > PASS
    All issues are aggregated; the highest-severity issue determines the final
    result. Messages are one-line summaries that include enough detail for
    correction.

    Definitions:
        - “Bolus used in beamset” means at least one beam in the current beamset
          has a non-empty Boli[] list.
        - “Bolus applied in isocenter” means bolus is applied to a beam whose
          isocenter label matches the grouping of interest.
        - A valid bolus ROI name (case-insensitive) must match:
              Bolus_<thickness>mm_<width>x<height>
          or:
              Bolus_custom
        - Any ROI whose name contains “bolus” or whose ROI Type is “Bolus”
          is subject to naming and usage validation.

    PASS Conditions (all must be met):
        1. If no bolus is used in this beamset:
             a. No bolus-related ROI exists anywhere in the plan; OR
             b. Bolus is correctly used in at least one other beamset.
           (Beamsets are independent: bolus for Beamset B does not create
            requirements for Beamset A.)
        2. If bolus is used in this beamset:
             a. Within each isocenter, bolus must be applied to all beams
                (all-or-none per isocenter).
             b. Within each isocenter, all beams must use the SAME bolus name.
        3. No bolus ROI (validly named or not) is allowed to be unused across the
           entire plan. All bolus ROIs must be applied somewhere.
        4. No naming violations for any bolus ROI that is used.
        5. No ALERT or FAIL conditions encountered.

    ALERT Conditions:
        (These do not invalidate the plan but indicate RTT workflow risk.)
        1. Mixed bolus usage within an isocenter:
             - At least one beam has bolus and at least one does not.
        2. Mixed bolus types within an isocenter:
             - e.g., Bolus_5mm_20x20 on Beam 1; Bolus_10mm_20x20 on Beam 2.
        3. Naming errors for bolus ROIs that ARE used:
             - Any bolus-related ROI that does not match the strict naming rules
               but is applied to at least one beam produces an ALERT.
        (All ALERT conditions allow other beamsets to pass independently.)

    FAIL Conditions:
        (These are plan-quality errors requiring correction.)
        1. A bolus ROI exists in the plan but is never applied to any beam in the
           entire plan (validly named or not). It should have been deleted.
        2. A bolus ROI contains “bolus” in the name, or has ROI Type “Bolus”, but:
             - does not follow naming rules AND
             - is not applied anywhere in the plan.
        3. Multiple bolus ROIs exist and any of them are unused.
             - All bolus-related structures must either be used or removed.
        4. Any unused bolus-related structure, regardless of naming correctness,
           produces a FAIL.
        (Failure conditions do not depend on isocenter grouping; they are global.)

    Multiple-Issue Handling:
        - Identify all issues across naming, usage, and consistency.
        - Severity of final result follows FAIL > ALERT > PASS.
        - Returned message aggregates all issues into concise one-line summaries.

    This rule set implements a strict interpretation of bolus cleanliness, naming
    standards, intra-isocenter consistency, and plan-wide usage hygiene, consistent
    with RTT workflow expectations and clinical best practices.


    Test Patients:
        Pass: Name: Script_Testing^Plan_Review,MRN: #ZZUWQA_ScTest_01May2022,Case: ChwL, Bolus_Roi_Check_Pass: ChwL_VMA_R1A0
        Fail: Name: Script_Testing^Plan_Review,MRN: #ZZUWQA_ScTest_01May2022,Case: ChwL, Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    state = gather_bolus_state(
        case=rso.case,
        plan=rso.plan,
        beamset=rso.beamset,
        exam=rso.exam,
    )

    fail_issues: List[str] = []
    alert_issues: List[str] = []

    # 1) Isocenter-level consistency (ALERT only)
    f, a = check_isocenter_consistency(state)
    fail_issues.extend(f)
    alert_issues.extend(a)

    # 2) Naming rules (ALERT or FAIL)
    f, a = check_bolus_naming(state)
    fail_issues.extend(f)
    alert_issues.extend(a)

    # 3) Usage hygiene (FAIL only)
    f, a = check_bolus_usage_hygiene(state)
    fail_issues.extend(f)
    alert_issues.extend(a)

    # 4) Aggregate to final status + message
    return aggregate_bolus_issues(state, fail_issues, alert_issues)
