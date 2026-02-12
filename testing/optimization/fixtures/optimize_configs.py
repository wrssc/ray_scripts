from __future__ import annotations
from dataclasses import replace
from typing import Any, Dict, Iterable, List, Tuple

from testing.optimization.runners.optimize_plan_runner import OptimizePlanConfig


def base_config(patient_db: Any) -> OptimizePlanConfig:
    return OptimizePlanConfig(
        patient_db=patient_db,
        fluence_only=False,
        reset_beams=True,
        n_iterations=4,
        initial_max_it=50,
        initial_int_it=10,
        second_max_it=35,
        second_int_it=5,
        vary_grid=False,
        segment_weight=False,
        reduce_oar=False,
        use_treat_settings=False,
        treat_margin_cm=None,
        close_status=True,
        save=True,
    )


def named_variants(base: OptimizePlanConfig) -> List[Tuple[str, OptimizePlanConfig]]:
    return [
        ("warm_start", replace(base, reset_beams=False)),
        ("vary_grid", replace(base, vary_grid=True)),
        ("seg_weight", replace(base, segment_weight=True)),
        ("reduce_oar", replace(base, reduce_oar=True, n_iterations=2)),
        ("treat_default", replace(base, use_treat_settings=True, treat_margin_cm=None)),
        ("treat_custom_0p25cm", replace(base, use_treat_settings=True, treat_margin_cm=0.25)),
        ("fluence_only", replace(base, fluence_only=True)),
    ]


def grid_sweep(base: OptimizePlanConfig) -> List[Tuple[str, OptimizePlanConfig]]:
    dims = [
        ("grid_0p5_0p4_0p3_0p2", replace(base, vary_grid=True, dose_dim1=0.5, dose_dim2=0.4, dose_dim3=0.3, dose_dim4=0.2)),
        ("grid_0p4_0p3_0p35_0p2", replace(base, vary_grid=True, dose_dim1=0.4, dose_dim2=0.3, dose_dim3=0.35, dose_dim4=0.2)),
    ]
    return dims
