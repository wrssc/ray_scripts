"""
Integration test runner for optimize_plan sweeps (named variants + grid sweeps).
Sample usage in Jupyter:


from testing.integration.optimize_plan_sweep import (
    run_optimize_plan_named_and_grid_sweeps
)

results = run_optimize_plan_named_and_grid_sweeps(
    include_baseline=True,
    include_named_variants=True,
    include_grid_sweep=True,
)

"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Tuple

import logging

from library.api.api_utils import find_scope
from library.OptimizationOperations import optimize_plan



def _normalize_inputs_for_technique(beamset: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Mirror the GUI policy for Tomo vs VMAT on a plain dict of optimize_plan kwargs."""
    out = dict(inputs)
    is_tomo = "Tomo" in getattr(beamset, "DeliveryTechnique", "")

    if is_tomo:
        # GUI behavior:
        # - disable VMAT-only post steps
        # - force treat settings on
        out["segment_weight"] = False
        out["reduce_oar"] = False
        out["use_treat_settings"] = True
        out["treat_margin"] = None
        # reduce_time allowed (keep whatever variant requested)
    else:
        # VMAT behavior:
        out["reduce_time"] = False
        # keep segment_weight/reduce_oar/use_treat_settings/treat_margin as provided by variant

    return out


def run_optimize_plan_named_and_grid_sweeps(
    *,
    include_baseline: bool = True,
    include_named_variants: bool = True,
    include_grid_sweep: bool = True,
) -> List[Dict[str, Any]]:
    """
    RayStation integration entrypoint (callable):
      - pulls current scope (patient/case/exam/plan/beamset/patient_db)
      - loads base + named variants + grid sweep from optimize_configs
      - runs optimize_plan(...) for each variant
      - returns structured results
    """
    # Scope (same pattern as automated_plan_optimization)
    patient = find_scope(level="Patient")
    case = find_scope(level="Case")
    exam = find_scope(level="Examination")
    plan = find_scope(level="Plan")
    beamset = find_scope(level="BeamSet")
    patient_db = find_scope(level="PatientDB")

    # Load sweep definitions
    from testing.optimization.fixtures.optimize_configs import base_config, named_variants, grid_sweep

    base_cfg = base_config(patient_db=patient_db)

    runs: List[Tuple[str, Any]] = []
    if include_baseline:
        runs.append(("baseline", base_cfg))
    if include_named_variants:
        runs.extend(named_variants(base_cfg))
    if include_grid_sweep:
        runs.extend(grid_sweep(base_cfg))

    results: List[Dict[str, Any]] = []

    for name, cfg in runs:
        # Convert dataclass -> dict kwargs
        d = cfg.__dict__.copy()

        # Convert treat_margin_cm -> treat_margin (cm)
        treat_margin_cm = d.pop("treat_margin_cm", None)
        d["treat_margin"] = treat_margin_cm

        # Apply technique constraints like the GUI
        d = _normalize_inputs_for_technique(beamset, d)

        # Ensure required context is present
        d["patient_db"] = patient_db

        status, message = optimize_plan(
            patient=patient,
            case=case,
            exam=exam,
            plan=plan,
            beamset=beamset,
            **d,
        )

        result = {
            "name": name,
            "status": bool(status),
            "message": message,
            "inputs": d,
        }
        results.append(result)

        if status:
            logging.info("OPT SWEEP [%s]: PASS - %s", name, message)
        else:
            logging.error("OPT SWEEP [%s]: FAIL - %s", name, message)

    return results
