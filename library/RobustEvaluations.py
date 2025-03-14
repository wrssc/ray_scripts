#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Single-file script to:
  - Use the already-defined namedtuple 'rso' referencing a RayStation plan
  - Extract clinical goals and DVH data (nominal and robust) in a tidy (long) format
  - Export all planning data to a single JSON file (a complete "core dump")
    including placeholders for objectives and other optimization data.
  - Read the JSON back into Pandas DataFrames for analysis/plotting.

Author: You
"""

import connect
import os
import json
import numpy as np
import pandas as pd
import math
import datetime
from math import isclose, ceil, sqrt
from collections import namedtuple
import matplotlib.pyplot as plt
import seaborn
from cycler import cycler
import logging


###############################################################################
# (1) Basic utilities for fetching ROI lists
###############################################################################
def find_targets(case):
    """
    Return a list of target ROI names from the case.
    """
    target_rois = []
    for roi in case.PatientModel.RegionsOfInterest:
        if "PTV" in roi.Name.upper():
            target_rois.append(roi.Name)
    return list(set(target_rois))


def find_organs_at_risk(case):
    """
    Return a list of organ-at-risk (OAR) ROI names from the case.
    """
    oar_rois = []
    for roi in case.PatientModel.RegionsOfInterest:
        if "PTV" not in roi.Name.upper():
            oar_rois.append(roi.Name)
    return list(set(oar_rois))


def compute_individual_perturbed_doses(
        rso,
        max_shift_x,
        max_shift_y,
        max_shift_z,
        max_roll,
        max_yaw,
        max_pitch,
        density_perturbation
):
    """
    Compute perturbed doses by perturbing one parameter at a time (no mixed perturbations).
    For each parameter (x, y, z, roll, yaw, pitch) compute both positive (max) and negative (min)
    perturbations.

    Parameters:
      rso: RayStation object (namedtuple) with beamset, exam, etc.
      max_shift_x, max_shift_y, max_shift_z: maximum patient shift values (e.g., in cm)
      max_roll, max_yaw, max_pitch: maximum rotation angles (in degrees)
      density_perturbation: density perturbation factor (unitless)

    Returns:
      A dictionary mapping perturbation labels (e.g., "x_max", "yaw_min") to the perturbed dose results.
    """
    results = {}

    # Common parameters for ComputePerturbedDose
    common_params = {
        "DensityPerturbation": density_perturbation,
        "RotationPoint": {'x': 0, 'y': 0, 'z': 0},
        "OnlyOneDosePerImageSet": False,
        "AllowGridExpansion": False,
        "ExaminationNames": [rso.exam.Name],
        "FractionNumbers": [0],
        "ComputeBeamDoses": True
    }

    # Define perturbations in a dictionary:
    # For shifts, we supply a PatientShift dict; for rotations, we supply a single angle.
    perturbations = {
        "x": {"key": "PatientShift",
              "positive": {"x": max_shift_x, "y": 0, "z": 0},
              "negative": {"x": -max_shift_x, "y": 0, "z": 0}},
        "y": {"key": "PatientShift",
              "positive": {"x": 0, "y": max_shift_y, "z": 0},
              "negative": {"x": 0, "y": -max_shift_y, "z": 0}},
        "z": {"key": "PatientShift",
              "positive": {"x": 0, "y": 0, "z": max_shift_z},
              "negative": {"x": 0, "y": 0, "z": -max_shift_z}},
        "roll": {"key": "RollDegrees",
                 "positive": max_roll,
                 "negative": -max_roll},
        "yaw": {"key": "YawDegrees",
                "positive": max_yaw,
                "negative": -max_yaw},
        "pitch": {"key": "PitchDegrees",
                  "positive": max_pitch,
                  "negative": -max_pitch}
    }

    # Loop over each perturbation type and compute positive and negative cases.
    for param, details in perturbations.items():
        for sign, value in zip(["max", "min"], [details["positive"], details["negative"]]):
            # Set up the default parameters: no shift and no rotation.
            params = {
                "PatientShift": {'x': 0, 'y': 0, 'z': 0},
                "YawDegrees": 0,
                "PitchDegrees": 0,
                "RollDegrees": 0
            }
            # Update only the parameter we're perturbing.
            if details["key"] == "PatientShift":
                params["PatientShift"] = value
            else:
                params[details["key"]] = value

            # Merge common parameters with our specific ones.
            call_params = common_params.copy()
            call_params.update(params)

            # Call the RayStation API.
            results[f"{param}_{sign}"] = rso.beamset.ComputePerturbedDose(
                DensityPerturbation=call_params["DensityPerturbation"],
                PatientShift=call_params["PatientShift"],
                RotationPoint=call_params["RotationPoint"],
                YawDegrees=call_params["YawDegrees"],
                PitchDegrees=call_params["PitchDegrees"],
                RollDegrees=call_params["RollDegrees"],
                OnlyOneDosePerImageSet=call_params["OnlyOneDosePerImageSet"],
                AllowGridExpansion=call_params["AllowGridExpansion"],
                ExaminationNames=call_params["ExaminationNames"],
                FractionNumbers=call_params["FractionNumbers"],
                ComputeBeamDoses=call_params["ComputeBeamDoses"]
            )
    return results


###############################################################################
# (2) Tidy (long) data extraction functions
###############################################################################
def get_tidy_goals(rso):
    """
    Build a tidy list of nominal clinical goal observations.
    Each row (dict) includes patient, plan, beamset, scenario, ROI, and goal details.
    """
    tidy_goals = []
    plan = rso.plan
    scenario = "nominal"
    evaluation_functions = plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions
    for ef in evaluation_functions:
        row = {}
        row["patient"] = rso.patient.Name
        row["plan"] = rso.plan.Name
        row["PlanUID"] = rso.plan.UniqueId if rso.plan else None
        row["beamset"] = rso.beamset.DicomPlanLabel if rso.beamset else None
        row["BeamsetUID"] = rso.beamset.UniqueId if rso.beamset else None
        row["scenario"] = scenario
        row["roi"] = ef.ForRegionOfInterest.Name
        row["roi_type"] = ef.ForRegionOfInterest.Type
        row["acceptance_level"] = ef.PlanningGoal.AcceptanceLevel
        row["goal_criteria"] = ef.PlanningGoal.GoalCriteria
        row["parameter_value"] = ef.PlanningGoal.ParameterValue
        row["priority"] = ef.PlanningGoal.Priority
        row["type"] = ef.PlanningGoal.Type
        row["goal_value"] = ef.GetClinicalGoalValue()
        row["goal_evaluation"] = ef.EvaluateClinicalGoal()
        row["robustness"] = ef.UseRobustness
        # Build a human-readable goal string
        if row["type"] == 'VolumeAtDose':
            row[
                "goal_str"] = f"{row['roi']}:: V({float(row['parameter_value']) / 100:.2f}Gy) {row['goal_criteria']} {float(row['acceptance_level']) * 100:.2f}%"
        elif row["type"] == 'DoseAtVolume':
            row[
                "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}%) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
        elif row["type"] == 'DoseAtAbsoluteVolume':
            row[
                "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}cc) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
        else:
            row["goal_str"] = f"{row['roi']}:: UnknownGoalType"
        tidy_goals.append(row)
    return tidy_goals


def get_tidy_goal(rso, evaluation_goal, dose_on_exam, scenario):
    row = {
        "patient": rso.patient.Name,
        "plan": rso.plan.Name,
        "PlanUID": rso.plan.UniqueId if rso.plan else None,
        "beamset": rso.beamset.DicomPlanLabel if rso.beamset else None,
        "BeamsetUID": rso.beamset.UniqueId if rso.beamset else None,
        "scenario": scenario,
        "roi": evaluation_goal.ForRegionOfInterest.Name,
        "roi_type": evaluation_goal.ForRegionOfInterest.Type,
        "acceptance_level": evaluation_goal.PlanningGoal.AcceptanceLevel,
        "goal_criteria": evaluation_goal.PlanningGoal.GoalCriteria,
        "parameter_value": evaluation_goal.PlanningGoal.ParameterValue,
        "priority": evaluation_goal.PlanningGoal.Priority,
        "type": evaluation_goal.PlanningGoal.Type
    }
    try:
        row["goal_value"] = evaluation_goal.GetClinicalGoalValueForEvaluationDose(
            DoseDistribution=dose_on_exam,
            ScaleFractionDoseToBeamSet=True)
        row["goal_evaluation"] = evaluation_goal.EvaluateClinicalGoalForEvaluationDose(
            DoseDistribution=dose_on_exam,
            ScaleFractionDoseToBeamSet=True)
    except Exception as e:
        print(f"Error evaluating goal: {e}")
        row["goal_value"] = None
        row["goal_evaluation"] = None
    if row["goal_evaluation"] is None or row["goal_value"] is None:
        n_fx = dose_on_exam.ForBeamSet.FractionationPattern.NumberOfFractions

        # Get the goal manually
        if row["type"] == "VolumeAtDose":
            row["goal_value"] = dose_on_exam.GetRelativeVolumeAtDose(
                RoiName=row["roi"],
                DoseValues=[row['acceptance_level'] * 100 * n_fx],
            )[0]
            row["goal_evaluation"]
        elif row["type"] == "DoseAtVolume":
            row["goal_value"] = dose_on_exam.GetDoseAtRelativeVolume(
                RoiName=row["roi"],
                RelativeVolumes=[row['acceptance_level']],
            )[0]
        elif row["type"] == "DoseAtAbsoluteVolume":
            # We need to convert the acceptance level to a relative volume
            # by dividing by the total volume of the ROI.
            volume = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[row["roi"]].GetRoiVolume()
            row["goal_value"] = dose_on_exam.GetDoseAtRelativeVolume(
                RoiName=row["roi"],
                RelativeVolumes=[row['acceptance_level'] / volume],
            )[0]
        elif row["type"] == "AbsoluteVolumeAtDose":
            volume = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[row["roi"]].GetRoiVolume()
            row["goal_value"] = dose_on_exam.GetRelativeVolumeAtDose(
                RoiName=row["roi"],
                DoseValues=[row['acceptance_level'] * 100 / n_fx])[0]
        elif row["type"] == "AverageDose":
            row["goal_value"] = dose_on_exam.GetDoseStatistic(
                RoiName=row["roi"],
                DoseType="Average"
            ) * n_fx
        elif row["type"] == "ConformityIndex" or row["type"] == "HomogeneityIndex":
            # Have to compute it manually
            # Get the prescription dose
            # TODO
            row["goal_value"] = None
        else:
            logging.warning(f"Unknown goal type: {row['type']}")
        # Evaluate the goal
        if row["goal_value"] is not None:
            if row["goal_criteria"] == "AtMost":
                if row["goal_value"] <= row["acceptance_level"]:
                    row["goal_evaluation"] = True
                else:
                    row["goal_evaluation"] = False
            elif row["goal_criteria"] == "AtLeast":
                if row["goal_value"] >= row["acceptance_level"]:
                    row["goal_evaluation"] = True
                else:
                    row["goal_evaluation"] = False
            else:
                logging.warning(f"Unknown goal criteria: {row['goal_criteria']}")


    try:
        row["isocenter_shift"] = dose_on_exam.PerturbedDoseProperties.IsocenterShift
        row["xAxisRotationAngle"] = dose_on_exam.PerturbedDoseProperties.xAxisRotationAngle
        row["yAxisRotationAngle"] = dose_on_exam.PerturbedDoseProperties.yAxisRotationAngle
        row["zAxisRotationAngle"] = dose_on_exam.PerturbedDoseProperties.zAxisRotationAngle
    except Exception:
        row["isocenter_shift"] = None
        row["xAxisRotationAngle"] = None
        row["yAxisRotationAngle"] = None
        row["zAxisRotationAngle"] = None
    if row["type"] == 'VolumeAtDose':
        row[
            "goal_str"] = f"{row['roi']}:: V({float(row['parameter_value']) / 100:.2f}Gy) {row['goal_criteria']} {float(row['acceptance_level']) * 100:.2f}%"
    elif row["type"] == 'DoseAtVolume':
        row[
            "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}%) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
    elif row["type"] == 'DoseAtAbsoluteVolume':
        row[
            "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}cc) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
    else:
        row["goal_str"] = f"{row['roi']}:: UnknownGoalType"
    return row


def get_tidy_robust_goals(rso):
    """
    Build a tidy list of robust clinical goal observations.
    For each robust dose (from DoseOnExaminations) we call the robust evaluation methods
    and capture dose perturbation properties to generate a scenario label.
    """
    tidy_robust = []
    if not rso.case.TreatmentDelivery.FractionEvaluations \
            and not rso.case.TreatmentDelivery.RadiationSetScenarioGroups:
        return tidy_robust  # No robust evaluations available
    for radiation_set in rso.case.TreatmentDelivery.RadiationSetScenarioGroups:
        if not radiation_set.ReferencedRadiationSet.DicomPlanLabel == rso.beamset.DicomPlanLabel:
            continue
        # Each one of these is made for scenario such as a 1 cm uniform shift
        for discrete_scenario in radiation_set.DiscreteFractionDoseScenarios:
            if not discrete_scenario.DoseValues or \
                    not discrete_scenario.ForBeamSet.DicomPlanLabel == rso.beamset.DicomPlanLabel:
                continue
            for ef in rso.plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
                pert_props = discrete_scenario.PerturbedDoseProperties
                shift = pert_props.IsoCenterShift  # dict with x, y, z
                descriptor = f"scenario_robust_shift_x{shift.get('x', 0):.1f}_y{shift.get('y', 0):.1f}_z{shift.get('z', 0):.1f}"
                if pert_props.xAxisRotationAngle or pert_props.yAxisRotationAngle or pert_props.zAxisRotationAngle:
                    rot = f"_rot_{pert_props.xAxisRotationAngle:.1f}_{pert_props.yAxisRotationAngle:.1f}_{pert_props.zAxisRotationAngle:.1f}"
                else:
                    rot = "_rot_0.0_0.0_0.0"
                scenario = descriptor + rot
                row = get_tidy_goal(rso, ef, discrete_scenario, scenario)
                tidy_robust.append(row)

    for frac_eval in rso.case.TreatmentDelivery.FractionEvaluations:
        for dose_on_exam in frac_eval.DoseOnExaminations:
            if not dose_on_exam.OnExamination.Name == rso.exam.Name:
                continue
            for dose_eval in dose_on_exam.DoseEvaluations:
                if not dose_eval.ForBeamSet.DicomPlanLabel == rso.beamset.DicomPlanLabel or \
                        not dose_eval.DoseValues or not dose_eval.PerturbedDoseProperties:
                    continue
                pert_props = dose_eval.PerturbedDoseProperties
                shift = pert_props.IsoCenterShift  # dict with x, y, z
                descriptor = f"robust_shift_x{shift.get('x', 0):.1f}_y{shift.get('y', 0):.1f}_z{shift.get('z', 0):.1f}"
                rot = f"_rot_{pert_props.xAxisRotationAngle:.1f}_{pert_props.yAxisRotationAngle:.1f}_{pert_props.zAxisRotationAngle:.1f}"
                scenario = descriptor + rot
                for ef in rso.plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
                    row = get_tidy_goal(rso, ef, dose_eval, scenario)
                    # row = {"patient": rso.patient.Name, "plan": rso.plan.Name,
                    #        "PlanUID": rso.plan.UniqueId if rso.plan else None,
                    #        "beamset": rso.beamset.DicomPlanLabel if rso.beamset else None,
                    #        "BeamsetUID": rso.beamset.UniqueId if rso.beamset else None, "scenario": scenario,
                    #        "roi": ef.ForRegionOfInterest.Name, "roi_type": ef.ForRegionOfInterest.Type,
                    #        "acceptance_level": ef.PlanningGoal.AcceptanceLevel,
                    #        "goal_criteria": ef.PlanningGoal.GoalCriteria,
                    #        "parameter_value": ef.PlanningGoal.ParameterValue, "priority": ef.PlanningGoal.Priority,
                    #        "type": ef.PlanningGoal.Type}
                    # try:
                    #     row["goal_value"] = ef.GetClinicalGoalValueForEvaluationDose(
                    #         DoseDistribution=dose_on_exam,
                    #         ScaleFractionDoseToBeamSet=True)
                    #     row["goal_evaluation"] = ef.EvaluateClinicalGoalForEvaluationDose(
                    #         DoseDistribution=dose_on_exam,
                    #         ScaleFractionDoseToBeamSet=True)
                    # except Exception:
                    #     row["goal_value"] = None
                    #     row["goal_evaluation"] = None
                    # try:
                    #     row["isocenter_shift"] = dose_eval.PerturbedDoseProperties.IsocenterShift
                    #     row["xAxisRotationAngle"] = dose_eval.PerturbedDoseProperties.xAxisRotationAngle
                    #     row["yAxisRotationAngle"] = dose_eval.PerturbedDoseProperties.yAxisRotationAngle
                    #     row["zAxisRotationAngle"] = dose_eval.PerturbedDoseProperties.zAxisRotationAngle
                    # except Exception:
                    #     row["isocenter_shift"] = None
                    #     row["xAxisRotationAngle"] = None
                    #     row["yAxisRotationAngle"] = None
                    #     row["zAxisRotationAngle"] = None
                    # if row["type"] == 'VolumeAtDose':
                    #     row[
                    #         "goal_str"] = f"{row['roi']}:: V({float(row['parameter_value']) / 100:.2f}Gy) {row['goal_criteria']} {float(row['acceptance_level']) * 100:.2f}%"
                    # elif row["type"] == 'DoseAtVolume':
                    #     row[
                    #         "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}%) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
                    # elif row["type"] == 'DoseAtAbsoluteVolume':
                    #     row[
                    #         "goal_str"] = f"{row['roi']}:: D({float(row['parameter_value']) * 100:.2f}cc) {row['goal_criteria']} {float(row['acceptance_level']) / 100:.2f}Gy"
                    # else:
                    #     row["goal_str"] = f"{row['roi']}:: UnknownGoalType"
                    tidy_robust.append(row)
    return tidy_robust


def get_tidy_dvh(rso, precision=0.01):
    """
    Build a tidy list of nominal DVH data.
    Each row represents one dose-volume bin for one ROI.
    """
    tidy_dvh = []
    scenario = "nominal"
    roi_list = list(set(find_targets(rso.case) + find_organs_at_risk(rso.case)))
    for roi in roi_list:
        dvh_array = get_dvh(rso, roi, precision)
        for vals in dvh_array:
            row = {}
            row["patient"] = rso.patient.Name
            row["plan"] = rso.plan.Name
            row["PlanUID"] = rso.plan.UniqueId if rso.plan else None
            row["beamset"] = rso.beamset.DicomPlanLabel if rso.beamset else None
            row["BeamsetUID"] = rso.beamset.UniqueId if rso.beamset else None
            row["scenario"] = scenario
            row["roi"] = roi
            row["volume_fraction"] = vals[0]
            row["dose_Gy"] = vals[1]
            tidy_dvh.append(row)
    return tidy_dvh


def get_tidy_robust_dvh(rso, precision=0.01):
    """
    Build a tidy list of robust DVH data.
    For each robust evaluation dose, compute DVH data (here we use the same
    method as nominal as a placeholder) and label with the robust scenario.
    """
    tidy_robust_dvh = []
    if not hasattr(rso.case.TreatmentDelivery, "FractionEvaluations"):
        return tidy_robust_dvh
    for frac_eval in rso.case.TreatmentDelivery.FractionEvaluations:
        for dose_on_exam in frac_eval.DoseOnExaminations:
            try:
                dose_eval = dose_on_exam.DoseEvaluations[0]
                pert_props = dose_eval.PerturbedDoseProperties
                shift = pert_props.IsocenterShift
                descriptor = f"robust_shift_x{shift.get('x', 0):.1f}_y{shift.get('y', 0):.1f}_z{shift.get('z', 0):.1f}"
                rot = f"_rot_{pert_props.xAxisRotationAngle:.1f}_{pert_props.yAxisRotationAngle:.1f}_{pert_props.zAxisRotationAngle:.1f}"
                scenario = descriptor + rot
            except Exception:
                scenario = "robust_generic"
            roi_list = list(set(find_targets(rso.case) + find_organs_at_risk(rso.case)))
            for roi in roi_list:
                # As a placeholder, we call get_dvh() but override the scenario.
                dvh_array = get_dvh(rso, roi, precision)
                for vals in dvh_array:
                    row = {}
                    row["patient"] = rso.patient.Name
                    row["plan"] = rso.plan.Name
                    row["PlanUID"] = rso.plan.UniqueId if rso.plan else None
                    row["beamset"] = rso.beamset.DicomPlanLabel if rso.beamset else None
                    row["BeamsetUID"] = rso.beamset.UniqueId if rso.beamset else None
                    row["scenario"] = scenario
                    row["roi"] = roi
                    row["volume_fraction"] = vals[0]
                    row["dose_Gy"] = vals[1]
                    tidy_robust_dvh.append(row)
    return tidy_robust_dvh


###############################################################################
# (3) Export the data to a single JSON (core dump)
###############################################################################
def export_plan_data(rso, output_dir):
    """
    Extracts nominal goals, robust goals, DVH (nominal and robust),
    and placeholders for objectives and optimization data from rso.plan.
    All are exported to a single JSON file. The filename includes a timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    base_filename = f"{rso.patient.Name}_{rso.plan.Name}_{rso.beamset.DicomPlanLabel}_{timestamp}.json"
    output_json = os.path.join(output_dir, base_filename)

    data_dict = {
        "PatientName": rso.patient.Name,
        "PlanName": rso.plan.Name,
        "PlanUID": rso.plan.UniqueId if rso.plan else None,
        "BeamsetName": rso.beamset.DicomPlanLabel if rso.beamset else None,
        "BeamsetUID": rso.beamset.UniqueId if rso.beamset else None,
        "ExportTimestamp": timestamp,
        "goals": get_tidy_goals(rso),  # Nominal goals
        "robust_goals": get_tidy_robust_goals(rso),  # Robust goals (if any)
        "DVH": get_tidy_dvh(rso, precision=0.01),  # Nominal DVH data
        "robust_DVH": get_tidy_robust_dvh(rso, precision=0.01),  # Robust DVH data (placeholder)
        "objectives": [],  # Placeholder for objectives data during optimization
        "optimization_data": {}  # Placeholder for additional optimization details
    }

    with open(output_json, 'w') as fp:
        json.dump(data_dict, fp, indent=2)
    print(f"Exported plan data to {output_json}")


###############################################################################
# (4) Read the JSON back and create DataFrames for analysis/plotting
###############################################################################
def read_tidy_data(json_file):
    """
    Reads the JSON file and converts tidy lists into Pandas DataFrames.
    Returns DataFrames for nominal goals, robust goals, nominal DVH, robust DVH,
    and placeholders for objectives if needed.
    """
    with open(json_file, 'r') as fp:
        data = json.load(fp)

    df_goals = pd.DataFrame(data.get("goals", []))
    df_robust = pd.DataFrame(data.get("robust_goals", []))
    df_dvh = pd.DataFrame(data.get("DVH", []))
    df_robust_dvh = pd.DataFrame(data.get("robust_DVH", []))
    df_objectives = pd.DataFrame(data.get("objectives", []))  # may be empty

    print("\n=== Nominal Goals DataFrame ===")
    print(df_goals.head())
    print("\n=== Robust Goals DataFrame ===")
    print(df_robust.head())
    print("\n=== Nominal DVH DataFrame ===")
    print(df_dvh.head())
    print("\n=== Robust DVH DataFrame ===")
    print(df_robust_dvh.head())

    return df_goals, df_robust, df_dvh, df_robust_dvh, df_objectives


###############################################################################
# (5) Main function orchestrating the export and read-back demonstration
###############################################################################
def main():
    """
    Retrieves current patient/plan/beamset from RayStation,
    exports all planning data (goals, DVH, robust evaluations, etc.)
    into a single JSON file (a complete snapshot), and then reads
    the file back into DataFrames.
    """
    try:
        patient = connect.get_current("Patient")
    except:
        patient = None
    try:
        case = connect.get_current("Case")
    except:
        case = None
    try:
        plan = connect.get_current("Plan")
    except:
        plan = None
    try:
        beam_set = connect.get_current("BeamSet")
    except:
        beam_set = None
    try:
        examination = connect.get_current("Examination")
    except:
        examination = None
    try:
        machine_db = connect.get_current("MachineDB")
    except:
        machine_db = None
    try:
        patient_db = connect.get_current("PatientDB")
    except:
        patient_db = None
    try:
        ui = connect.get_current("ui")
    except:
        ui = None

    # Create a namedtuple for easy passing
    Pd = namedtuple('Pd', [
        'error', 'patient_db', 'machine_db', 'ui',
        'case', 'patient', 'exam', 'plan', 'beamset'
    ])
    rso = Pd(
        error=[],
        patient_db=patient_db,
        machine_db=machine_db,
        ui=ui,
        case=case,
        patient=patient,
        exam=examination,
        plan=plan,
        beamset=beam_set
    )

    # Define output directory and ensure it exists
    output_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(output_dir, exist_ok=True)

    # Export all planning data into one JSON file
    export_plan_data(rso, output_dir)

    # For demonstration, read the latest exported JSON file
    exported_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
    if exported_files:
        latest_file = os.path.join(output_dir, sorted(exported_files)[-1])
        print(f"\nReading data from {latest_file}")
        df_goals, df_robust, df_dvh, df_robust_dvh, df_objectives = read_tidy_data(latest_file)

    # (Optional) Further analysis or plotting can be done using the DataFrames.
    # For example, plotting nominal DVH curves:
    if not df_dvh.empty:
        for roi in df_dvh["roi"].unique():
            subset = df_dvh[df_dvh["roi"] == roi]
            plt.plot(subset["dose_Gy"], 1 - subset["volume_fraction"], label=roi)
        plt.xlabel("Dose (Gy)")
        plt.ylabel("1 - Volume Fraction")
        plt.title("Nominal DVH Curves")
        plt.legend()
        plt.show()


if __name__ == "__main__":
    main()
