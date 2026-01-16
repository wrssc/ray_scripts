# regression_testing/rs_context_loader.py

"""Loads RayStation context for regression tests.

Provides manifest-driven context loading:

- generation tests: load patient + set current case + exam (plan/beamset created by script)
- context tests: load patient + set current case + plan + beamset + exam

Retains existing selection-based helper for older workflows.
"""

from __future__ import annotations

from collections import namedtuple
from typing import Any, Dict, Optional, Sequence, Tuple

from library.api.api_rs import import_raystation_api

rs = import_raystation_api()


def query_by_mrn(patient_db: Any, mrn: str, use_index: bool = False):
    return patient_db.QueryPatientInfo(
        Filter={"PatientID": mrn},
        UseIndexService=use_index,
    )


def _get_case_by_name(patient: Any, case_name: str):
    for case in getattr(patient, "Cases", []):
        name = getattr(case, "CaseName", None) or getattr(case, "Name", "")
        if name == case_name:
            return case
    return None


def _get_plan_by_name(case: Any, plan_name: str):
    for plan in getattr(case, "TreatmentPlans", []):
        if getattr(plan, "Name", "") == plan_name:
            return plan
    return None


def _get_beamset_by_label_or_name(plan: Any, beamset_label_or_name: str):
    for bs in getattr(plan, "BeamSets", []):
        label = getattr(bs, "DicomPlanLabel", None) or ""
        name = getattr(bs, "Name", "") or ""
        if beamset_label_or_name in (label, name):
            return bs
    return None


def _get_exam_by_name(case: Any, exam_name: str):
    for exam in getattr(case, "Examinations", []):
        if getattr(exam, "Name", "") == exam_name:
            return exam
    return None


def set_case_plan_beamset(case: Any, plan: Any, beamset: Any) -> None:
    if case:
        case.SetCurrent()
    if plan:
        plan.SetCurrent()
    if beamset:
        beamset.SetCurrent()


def _choose_exam_name(case: Any, beamset: Any) -> str:
    """Pick an exam name likely to exist.

    Preference:
      1) Beamset planning exam (if available)
      2) Current examination if it belongs to this case
      3) First exam in case
    """
    for attr in ("PlanningExamination", "Examination", "OnExamination"):
        try:
            ex = getattr(beamset, attr, None)
            if ex is not None and getattr(ex, "Name", ""):
                return ex.Name
        except Exception:
            pass

    try:
        cur = rs.get_current("Examination")
        if cur is not None and _get_exam_by_name(case, cur.Name) is not None:
            return cur.Name
    except Exception:
        pass

    exams = list(getattr(case, "Examinations", []))
    if not exams:
        raise ValueError("Case has no examinations.")
    return exams[0].Name


def init_rso(patient, case, examination, patient_db, machine_db, ui, plan, beamset):
    Pd = namedtuple("Pd", ["error", "patient_db", "machine_db", "ui", "case", "patient", "exam", "plan", "beamset"])
    return Pd(
        error=[],
        patient=patient,
        case=case,
        exam=examination,
        patient_db=patient_db,
        machine_db=machine_db,
        ui=ui,
        plan=plan,
        beamset=beamset,
    )


def reload_raystation_objects():
    try:
        reload_patient = rs.get_current("Patient")
    except Exception as e:
        raise ValueError("Reload of patient fails") from e

    try:
        reload_case = rs.get_current("Case")
    except Exception as e:
        raise ValueError("Reload of case fails") from e

    # Plan/BeamSet may not exist for generation tests before script runs
    try:
        reload_plan = rs.get_current("Plan")
    except Exception:
        reload_plan = None

    try:
        reload_beamset = rs.get_current("BeamSet")
    except Exception:
        reload_beamset = None

    try:
        reload_examination = rs.get_current("Examination")
    except Exception as e:
        raise ValueError("Reload of exam fails") from e

    try:
        reload_machine_db = rs.get_current("MachineDB")
    except Exception:
        reload_machine_db = None

    try:
        reload_patient_db = rs.get_current("PatientDB")
    except Exception:
        reload_patient_db = None

    try:
        reload_ui = rs.get_current("ui")
    except Exception:
        reload_ui = None

    return init_rso(
        reload_patient,
        reload_case,
        reload_examination,
        reload_patient_db,
        reload_machine_db,
        reload_ui,
        reload_plan,
        reload_beamset,
    )


def _require_str(d: Dict[str, Any], key: str, *, where: str) -> str:
    v = d.get(key, "")
    s = str(v).strip()
    if not s:
        raise ValueError(f"Missing required {where}.{key}")
    return s


def _maybe_str(d: Dict[str, Any], key: str) -> str:
    v = d.get(key, "")
    return str(v).strip()


def load_patient_from_manifest(patient_db: Any, test_patient: Dict[str, Any]) -> Any:
    """Load patient by manifest test_patient.patient_id (PatientID).

    Args:
        patient_db: RayStation PatientDB object.
        test_patient: Manifest 'test_patient' dict.

    Returns:
        Patient object.

    Raises:
        ValueError: if patient not found.
    """
    patient_id = _require_str(test_patient, "patient_id", where="test_patient")
    pts = query_by_mrn(patient_db, patient_id, use_index=True)
    if len(pts) == 0:
        raise ValueError(f"PatientID not found in patient_db: {patient_id!r}")
    patient_db.LoadPatient(PatientInfo=pts[0], AllowPatientUpgrade=True)
    return rs.get_current("Patient")


def set_current_from_manifest_test(spec: Dict[str, Any], patient_db: Any):
    """Load patient and set RayStation current objects from a manifest test spec.

    Modes:
      - generation/generator/execution:
          requires test_patient: patient_id, case_name, exam_name
          sets current: Patient, Case, Examination
          does NOT require plan/beamset to exist
      - context/context_execution/validation:
          requires test_patient: patient_id, case_name, plan_name, beamset_name
          sets current: Patient, Case, Plan, BeamSet, Examination

    Args:
        spec: One element from manifest["tests"].
        patient_db: RayStation PatientDB.

    Returns:
        rso (namedtuple) from reload_raystation_objects().

    Raises:
        ValueError: if required objects are missing.
    """
    test_type = str(spec.get("test_type", "")).strip().lower()
    test_patient = spec.get("test_patient", None)
    if not isinstance(test_patient, dict):
        raise ValueError("spec.test_patient must be a dict")

    patient = load_patient_from_manifest(patient_db, test_patient)

    case_name = _require_str(test_patient, "case_name", where="test_patient")
    case = _get_case_by_name(patient, case_name)
    if case is None:
        raise ValueError(f"Case not found: {case_name!r}")

    # Always set current case
    try:
        case.SetCurrent()
    except Exception:
        pass

    is_generation = test_type in ("generation", "generator", "execution")

    if is_generation:
        exam_name = _require_str(test_patient, "exam_name", where="test_patient")
        exam = _get_exam_by_name(case, exam_name)
        if exam is None:
            raise ValueError(f"Examination not found in case: {exam_name!r}")

        try:
            rs.set_current("Examination", exam)
        except Exception:
            pass

        return reload_raystation_objects()

    # Context-based
    plan_name = _require_str(test_patient, "plan_name", where="test_patient")
    beamset_name = _require_str(test_patient, "beamset_name", where="test_patient")

    plan = _get_plan_by_name(case, plan_name)
    if plan is None:
        raise ValueError(f"Plan not found: {plan_name!r} (Case {case_name!r})")

    beamset = _get_beamset_by_label_or_name(plan, beamset_name)
    if beamset is None:
        raise ValueError(f"Beamset not found: {beamset_name!r} (Plan {plan_name!r}, Case {case_name!r})")

    exam_name = _maybe_str(test_patient, "exam_name") or _choose_exam_name(case, beamset)
    exam = _get_exam_by_name(case, exam_name)
    if exam is None:
        raise ValueError(f"Examination not found in case: {exam_name!r}")

    set_case_plan_beamset(case, plan, beamset)

    try:
        rs.set_current("Examination", exam)
    except Exception:
        pass

    return reload_raystation_objects()


# Backwards-compatible function (selection dict) retained
def set_current_patient_from_selection(mrn: str, patient_db: Any, selection: Dict[str, Any]):
    """Load MRN and set Case/Plan/Beamset/Examination from selection dict."""
    mrn = str(mrn).strip()
    if not mrn:
        raise ValueError("mrn is empty")

    pts = query_by_mrn(patient_db, mrn, use_index=True)
    if len(pts) == 0:
        rs.await_user_input(f"Data missing {mrn} must be sent from MIM")
        pts = query_by_mrn(patient_db, mrn, use_index=True)
    if len(pts) == 0:
        raise ValueError(f"MRN not found in patient_db: {mrn}")

    patient_db.LoadPatient(PatientInfo=pts[0], AllowPatientUpgrade=True)
    patient = rs.get_current("Patient")

    case_name = str(selection.get("case_name", "")).strip()
    plan_name = str(selection.get("plan_name", "")).strip()
    beamset_name = str(selection.get("beamset_name", "")).strip()

    if not (case_name and plan_name and beamset_name):
        raise ValueError(f"Selection dict missing required keys for MRN {mrn}: {selection}")

    case = _get_case_by_name(patient, case_name)
    if case is None:
        raise ValueError(f"Case not found: {case_name!r}")

    plan = _get_plan_by_name(case, plan_name)
    if plan is None:
        raise ValueError(f"Plan not found: {plan_name!r} (Case {case_name!r})")

    beamset = _get_beamset_by_label_or_name(plan, beamset_name)
    if beamset is None:
        raise ValueError(f"Beamset not found: {beamset_name!r} (Plan {plan_name!r}, Case {case_name!r})")

    exam_name = _choose_exam_name(case, beamset)
    exam = _get_exam_by_name(case, exam_name)
    if exam is None:
        raise ValueError(f"Examination not found in case: {exam_name!r}")

    set_case_plan_beamset(case, plan, beamset)

    try:
        rs.set_current("Examination", exam)
    except Exception:
        pass

    rso = reload_raystation_objects()

    try:
        rso_exam_name = getattr(getattr(rso, "exam", None), "Name", None)
        if rso_exam_name and rso_exam_name != exam_name:
            print(f"WARNING: rso exam is {rso_exam_name!r} but expected {exam_name!r}")
    except Exception:
        pass

    return rso
