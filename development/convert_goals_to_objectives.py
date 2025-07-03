import pandas as pd
from typing import Optional, Dict, Any
from connect import get_current
import logging
# TODO:
#      - ensure all goals types are working. Currently average dose is getting set to max
#      - need a generic set of goals for targets that may not have a clinical goal or a reasonabl
#        guess for things like rings, sOTVu etc.
#      - add regular plan optimization objectives
#      - create a dialog  to select copy to mco or to run mco optimization or to copy goals to regular optimization
#


def evaluation_functions_to_dataframe(plan) -> pd.DataFrame:
    """Return a DataFrame summarizing every EvaluationFunction in *plan*.

    Each row corresponds to a single clinical goal (EvaluationFunction).
    Columns capture the most commonly inspected parameters for audit,
    scripting, and dashboard work.

    Parameters
    ----------
    plan :
        The RayStation `Plan` object, typically obtained via
        ``connect.get_current('Plan')``.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with one row per EvaluationFunction and the columns

        * roi                - Name of the ROI the goal applies to
        * goal_type          - PlanningGoal.Type (e.g., VolumeAtDose)
        * goal_criteria      - PlanningGoal.GoalCriteria
        * parameter_value    - PlanningGoal.ParameterValue (float or None)
        * acceptance_level   - PlanningGoal.AcceptanceLevel
        * priority           - PlanningGoal.Priority
        * tolerance          - PlanningGoal.Tolerance
        * is_comparative     - PlanningGoal.IsComparativeGoal
        * reject_on_fail     - PlanningGoal.RejectPlanOnFail
        * tag                - EvaluationFunction.Tag
        * use_beam_specific  - EvaluationFunction.UseBeamSpecificForAllBeams
        * use_robustness     - EvaluationFunction.UseRobustness
    """
    records: list[Dict[str, Any]] = []

    for func in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
        goal = func.PlanningGoal  # convenience handle
        roi_name: Optional[str] = None
        try:
            roi_name = func.ForRegionOfInterest.Name
        except Exception as e:
            # Some goals (e.g., target coverage) reference dose grids instead
            pass

        records.append(
            {
                "roi": roi_name,
                "goal_type": goal.Type,
                "goal_criteria": goal.GoalCriteria,
                "parameter_value": getattr(goal, "ParameterValue", None),
                "acceptance_level": goal.AcceptanceLevel,
                "priority": goal.Priority,
                "tolerance": goal.Tolerance,
                "is_comparative": goal.IsComparativeGoal,
                "reject_on_fail": goal.RejectPlanOnFail,
                "tag": func.Tag,
                "use_beam_specific": func.UseBeamSpecificForAllBeams,
                "use_robustness": func.UseRobustness,
            }
        )

    return pd.DataFrame.from_records(records)


# Low-level helpers
def _find_optimization_index(plan, beamset) -> int:
    """
    Return the index of the PlanOptimization that owns *beamset*.
    """
    matches = [
        idx
        for idx, po in enumerate(plan.PlanOptimizations)
        if beamset in po.OptimizedBeamSets       # <- use the object, not the label
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"{beamset.DicomPlanLabel}: expected exactly one matching "
            f"PlanOptimization, found {len(matches)}"
        )
    return matches[0]


def _ensure_mco(po) -> None:
    """Create the MCO object if it does not yet exist."""
    try:
        _ = po.Mco.TemplateOptimizationProblem  # access triggers AttributeError if absent
    except AttributeError:
        po.CreateMco()
        print("Created new MCO template")
    else:
        print("MCO template already present")


def _goal_to_mco_function(row):
    """Translate a clinical goal into (FunctionType, parameter-dict)."""
    t = row["goal_type"]
    crit = row["goal_criteria"]

    if t in ("VolumeAtDose", "AbsoluteVolumeAtDose"):
        ftype = "MaxDvh" if crit == "AtMost" else "MinDvh"
        params = {
            "PercentVolume": row["acceptance_level"] * 100
            if t == "VolumeAtDose"
            else row["acceptance_level"],  # cc
            "DoseLevel": row["parameter_value"],  # cGy
        }
    elif t in ("DoseAtVolume", "DoseAtAbsoluteVolume"):
        ftype = "MaxDose" if crit == "AtMost" else "MinDose"
        params = {
            "DoseLevel": row["acceptance_level"]  # cGy
        }
    elif t == "AverageDose":
        ftype = "MaxDose" if crit == "AtMost" else "MinDose"
        params = {"DoseLevel": row["acceptance_level"]}
    elif t == "ConformityIndex":
        ftype = "UniformityConstraint"
        params = {}  # RayStation handles CI internally; no extra fields
    elif t == "HomogeneityIndex":
        ftype = "UniformityConstraint"
        params = {}
    else:
        raise NotImplementedError(f"No MCO mapping for goal type {t!s}")

    return ftype, params


def push_goals_to_mco(
    df: pd.DataFrame,
    plan=None,
    beamset=None,
) -> None:
    """
    Convert clinical goals in *df* into MCO optimization functions.

    Priority 1-2     -> constraints (hard limits)
    Priority >= 3     -> objectives (soft limits)

    Parameters
    ----------
    df : pandas.DataFrame
        Output of ``evaluation_functions_to_dataframe``.
    plan :
        RayStation ``Plan`` object.  Defaults to the current plan.
    beamset :
        The beamset you want to optimise against.  Defaults to the
        *current* beamset in the UI.

    Notes
    -----
    * Runs inside the RayStation scripting environment.
    * Dose units are assumed to be cGy (RayStation's internal unit).
    * Unhandled goal types raise ``NotImplementedError`` - add mappings
      in ``_goal_to_mco_function`` as needed.
    """
    plan = plan or get_current("Plan")
    beamset = beamset or get_current("BeamSet")

    opt_idx = _find_optimization_index(plan, beamset)
    po = plan.PlanOptimizations[opt_idx]

    _ensure_mco(po)
    tmpl = po.Mco.TemplateOptimizationProblem

    for _, row in df.iterrows():
        try:
            ftype, params = _goal_to_mco_function(row)
        except NotImplementedError as exc:
            logging.warning(str(exc))
            continue

        is_constraint = row["priority"] in (1, 2)

        mco_fun = tmpl.AddOptimizationFunction(
            FunctionType=ftype,
            RoiName=row["roi"],
            IsConstraint=is_constraint,
            RestrictAllBeamsIndividually=False,
            RestrictToBeam=None,
            IsRobust=row["use_robustness"],
            RestrictToBeamSet=None,
            UseRbeDose=False,
        )

        # Populate dose-specific parameters
        dparams = mco_fun.DoseFunctionParameters
        for key, val in params.items():
            setattr(dparams, key, val)

        print(
            f"Added MCO {'constraint' if is_constraint else 'objective'} "
            f"({ftype}) on {row['roi']} - priority {row['priority']}"
        )

# def initialize_mco(plan_optimization, )
#
# from connect import get_current
# plan = get_current('Plan')
# df = evaluation_functions_to_dataframe(plan)
# df.to_csv(r'U:\Physics\Reports\evaluation_functions.csv', index=False)