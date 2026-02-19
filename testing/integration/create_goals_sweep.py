"""
Integration test runner for create_goals sweeps (baseline + named variants + grid sweeps).

Sample usage in Jupyter:

from testing.integration.create_goals_sweep import run_create_goals_named_and_order_sweeps

results = run_create_goals_named_and_order_sweeps(
    path_protocols=r"\\path\\to\\protocols",
    include_baseline=True,
    include_named_variants=True,
    include_grid_sweep=True,
)

"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import logging

import GeneralOperations
import Objectives


def _normalize_inputs_for_wrapper(beamset: Any, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mirror the optimize_plan_sweep pattern: allow wrapper-level policy tweaks
    on a plain dict of Objectives kwargs, based on delivery technique if needed.

    Keep this minimal: create_goals is not technique-dependent today, but
    this gives you the same hook point as optimize_plan_sweep._normalize_inputs_for_technique.
    """
    out = dict(inputs)
    # Example placeholder if you later need technique-specific behavior:
    # is_tomo = "Tomo" in getattr(beamset, "DeliveryTechnique", "")
    return out


def run_create_goals_named_and_order_sweeps(
    *,
    path_protocols: str,
    include_baseline: bool = True,
    include_named_variants: bool = True,
    include_grid_sweep: bool = True,
) -> List[Dict[str, Any]]:
    """
    RayStation integration entrypoint (callable):
      - pulls current scope (patient/case/exam/plan/beamset/ui)
      - loads base + named variants + grid sweep from create_goals_configs
      - runs Objectives.add_goals_and_objectives_from_protocol(...) for each variant
      - returns structured results
    """
    # Scope (match create_goals.py wrapper style) :contentReference[oaicite:5]{index=5}
    patient = GeneralOperations.find_scope(level="Patient")
    case = GeneralOperations.find_scope(level="Case")
    exam = GeneralOperations.find_scope(level="Examination")
    plan = GeneralOperations.find_scope(level="Plan")
    beamset = GeneralOperations.find_scope(level="BeamSet")
    ui = GeneralOperations.find_scope(level="ui")

    # Attempt to bring the same UI tab forward (wrapper behavior) :contentReference[oaicite:6]{index=6}
    try:
        ui.TitleBar.MenuItem["Plan Optimization"].Button_Plan_Optimization.Click()
    except Exception:
        logging.debug("Unable to change viewing windows")

    # Load sweep definitions (mirrors optimize_plan_sweep imports) :contentReference[oaicite:7]{index=7}
    from testing.create_goals.fixtures.create_goals_configs import (
        base_config,
        named_variants,
        grid_sweep,
    )

    base_cfg = base_config(path_protocols=path_protocols)

    runs: List[Tuple[str, Any]] = []
    if include_baseline:
        runs.append(("baseline", base_cfg))
    if include_named_variants:
        runs.extend(named_variants(base_cfg))
    if include_grid_sweep:
        runs.extend(grid_sweep(base_cfg))

    results: List[Dict[str, Any]] = []

    for name, cfg in runs:
        # Convert dataclass -> dict kwargs (mirror optimize_plan_sweep) :contentReference[oaicite:8]{index=8}
        d = cfg.__dict__.copy()

        # Wrapper-level normalization hook
        d = _normalize_inputs_for_wrapper(beamset, d)

        # Required arguments for Objectives call
        # (patient is not used by Objectives.add_goals..., but keep scope pull consistent)
        error_message = Objectives.add_goals_and_objectives_from_protocol(
            case=case,
            plan=plan,
            beamset=beamset,
            exam=exam,
            **d,
        )

        ok = not error_message
        msg = "Clinical goals/objectives added successfully" if ok else "; ".join(str(e) for e in error_message)

        result = {
            "name": name,
            "status": bool(ok),
            "message": msg,
            "errors": list(error_message) if error_message else [],
            "inputs": d,
        }
        results.append(result)

        if ok:
            logging.info("GOALS SWEEP [%s]: PASS - %s", name, msg)
        else:
            logging.error("GOALS SWEEP [%s]: FAIL - %s", name, msg)

    return results
