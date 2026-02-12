from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from typing import Optional, Any, Dict, Iterable, List, Tuple
import logging


@dataclass(frozen=True)
class OptimizePlanConfig:
    """All optimization inputs represented in the GUI (plus a couple required by optimize_plan)."""

    # Required context for optimize_plan inputs
    patient_db: Any

    # Iteration controls
    n_iterations: int = 4
    initial_max_it: int = 50
    initial_int_it: int = 10
    second_max_it: int = 35
    second_int_it: int = 5

    # Strategy toggles
    fluence_only: bool = True
    reset_beams: bool = False
    vary_grid: bool = False

    # Post-optimization toggles (VMAT)
    segment_weight: bool = False
    reduce_oar: bool = False

    # Post-optimization toggles (Tomo)
    reduce_time: bool = False

    # Treatment settings (VMAT)
    use_treat_settings: bool = False
    treat_margin_cm: Optional[float] = None  # None means "default" if use_treat_settings is True

    # Dose grid params (present in dict defaults; used if optimize_plan uses them)
    dose_dim1: float = 0.5
    dose_dim2: float = 0.4
    dose_dim3: float = 0.3
    dose_dim4: float = 0.2

    # Disable the forced open status screen
    close_status: bool = True

    # Save results after optimization
    save: bool = True


def _normalize_for_delivery_technique(cfg: OptimizePlanConfig, beamset: Any) -> OptimizePlanConfig:
    """Apply the same behavioral constraints as GUI imposes for Tomo vs VMAT."""
    is_tomo = "Tomo" in getattr(beamset, "DeliveryTechnique", "")

    if is_tomo:
        # GUI behavior: Tomo disables some VMAT-only options and forces treat settings
        return replace(
            cfg,
            segment_weight=False,
            reduce_oar=False,
            use_treat_settings=True,
            treat_margin_cm=None,  # not used in Tomo GUI path
        )
    else:
        # VMAT: reduce_time not applicable
        return replace(cfg, reduce_time=False)


def _as_optimize_plan_kwargs(cfg: OptimizePlanConfig) -> Dict[str, Any]:
    """Convert config -> optimize_plan kwargs names used by your script."""
    d = asdict(cfg)

    # store as treat_margin_cm in the config for clarity and convert to treat_margin.
    treat_margin_cm = d.pop("treat_margin_cm")
    d["treat_margin"] = treat_margin_cm

    return d


def run_optimize_plan(
    *,
    patient: Any,
    case: Any,
    exam: Any,
    plan: Any,
    beamset: Any,
    base: OptimizePlanConfig,
    override: Optional[OptimizePlanConfig] = None,
    optimize_plan_func=None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Run one optimization using a base config plus an optional override config.

    Returns:
        (status, message, final_kwargs)
    """
    if optimize_plan_func is None:
        from library.OptimizationOperations import optimize_plan as optimize_plan_func

    cfg = override if override is not None else base
    cfg = _normalize_for_delivery_technique(cfg, beamset)
    kwargs = _as_optimize_plan_kwargs(cfg)

    status, message = optimize_plan_func(
        patient=patient,
        case=case,
        exam=exam,
        plan=plan,
        beamset=beamset,
        **kwargs,
    )
    return status, message, kwargs


def run_optimize_sweep(
    *,
    patient: Any,
    case: Any,
    exam: Any,
    plan: Any,
    beamset: Any,
    base: OptimizePlanConfig,
    variants: Iterable[OptimizePlanConfig],
    optimize_plan_func=None,
) -> List[Tuple[bool, str, Dict[str, Any]]]:
    """
    Run multiple optimizations back-to-back with different configs.

    Returns a list of (status, message, final_kwargs) for each run.
    """
    results: List[Tuple[bool, str, Dict[str, Any]]] = []
    for cfg in variants:
        logging.info(f'Executing optimization with config: {cfg}')
        status, message, final_kwargs = run_optimize_plan(
            patient=patient,
            case=case,
            exam=exam,
            plan=plan,
            beamset=beamset,
            base=base,
            override=cfg,
            optimize_plan_func=optimize_plan_func,
        )
        logging.info(f'Finished optimization with config: {cfg}')
        results.append((status, message, final_kwargs))
    return results
