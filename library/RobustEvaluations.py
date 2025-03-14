#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Single-file script to:
  - Use the already-defined namedtuple 'rso' referencing a RayStation plan
  - Extract clinical goals and DVH data
  - Write to JSON
  - Read from JSON
  - Perform box-stem style plotting of clinical goals

Author: You
"""

import connect
import os
import json
import numpy
import pandas as pd
import copy
import math
from math import isclose, ceil
from collections import namedtuple
import matplotlib.pyplot as plt
# If you prefer not to rely on seaborn for styling, remove it:
import seaborn
from cycler import cycler


###############################################################################
# (1) Basic stubs or utilities for fetching structure lists
###############################################################################
def find_targets(case):
    """
    Stub: Return a list of target ROI names in 'case'.
    In real usage, you might parse specific naming conventions or
    parse the 'Type' of each ROI to guess 'Ptv' or 'Gtv'.
    """
    target_rois = []
    for roi in case.PatientModel.RegionsOfInterest:
        # Example heuristic for a target:
        if "PTV" in roi.Name.upper():
            target_rois.append(roi.Name)
    return list(set(target_rois))


def find_organs_at_risk(case):
    """
    Stub: Return a list of OAR ROI names in 'case'.
    In real usage, you might parse 'Type' or naming conventions
    to guess: 'BODY', 'Bladder', 'Rectum', etc.
    """
    oar_rois = []
    for roi in case.PatientModel.RegionsOfInterest:
        # Example heuristic for OAR:
        if "PTV" not in roi.Name.upper():
            oar_rois.append(roi.Name)
    return list(set(oar_rois))


###############################################################################
# (2) Functions to extract clinical goals and DVH from rso.plan
###############################################################################
def get_clinical_goal(rso, roi_name=None):
    """
    Return all clinical goals from rso.plan, optionally filtering by roi_name.
    Returns a dict-of-dicts keyed by index:
      { 0: {'roi':..., 'acceptance_level':..., ... }, 1: {...}, etc. }
    """
    clinical_goal = {}
    plan = rso.plan
    evaluation_functions = plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions
    i_g = 0
    for ef in evaluation_functions:
        if (roi_name is None) or (roi_name == ef.ForRegionOfInterest.Name):
            cgoal = {}
            cgoal['roi'] = ef.ForRegionOfInterest.Name
            cgoal['roi_type'] = ef.ForRegionOfInterest.Type
            cgoal['acceptance_level'] = ef.PlanningGoal.AcceptanceLevel
            cgoal['goal_criteria'] = ef.PlanningGoal.GoalCriteria
            cgoal['parameter_value'] = ef.PlanningGoal.ParameterValue
            cgoal['priority'] = ef.PlanningGoal.Priority
            cgoal['type'] = ef.PlanningGoal.Type
            cgoal['goal_value'] = ef.GetClinicalGoalValue()
            cgoal['goal_evaluation'] = ef.EvaluateClinicalGoal()
            cgoal['robustness'] = ef.UseRobustness
            clinical_goal[i_g] = cgoal
            i_g += 1
    return clinical_goal


def get_dvh(rso, roi_name, precision=0.01):
    """
    Returns a 2D numpy array of [volume_fraction, dose_at_that_volume].
      volume_fraction: from 0 -> 1.0  (in steps of 'precision')
      dose_at_that_volume: dose [Gray]
    """
    plan_dose = rso.plan.TreatmentCourse.TotalDose
    number_dvh_points = int(1. / precision) + 1
    vols = [precision * x for x in range(number_dvh_points)]
    dose_values = plan_dose.GetDoseAtRelativeVolumes(RoiName=roi_name, RelativeVolumes=vols)
    dose_array = numpy.column_stack([vols, dose_values])
    return dose_array


###############################################################################
# (3) Export the data to JSON
###############################################################################
def export_plan_data(rso, output_json):
    """
    Extracts clinical goals + DVHs for each target/OAR in the 'rso.plan',
    writes them to a JSON file 'output_json'.
    """
    data_dict = {'PatientName': rso.patient.Name, 'PlanName': rso.plan.Name,
                 'PlanUID': rso.plan.UniqueId if rso.plan else None,
                 'BeamsetName': rso.beamset.DicomPlanLabel if rso.beamset else None,
                 'BeamsetUID': rso.beamset.UniqueId if rso.beamset else None,
                 'goals': get_clinical_goal(rso, roi_name=None)}

    # Gather goals

    # For demonstration, gather targets/OARs
    tars = find_targets(rso.case)
    oars = find_organs_at_risk(rso.case)
    # Store each ROI DVH
    data_dict['DVH'] = {}
    for t in tars + oars:
        dvh_array = get_dvh(rso, t, precision=0.01)
        data_dict['DVH'][t] = dvh_array.tolist()

    # Write to JSON
    with open(output_json, 'w') as fp:
        json.dump(data_dict, fp, indent=2)
    print(f"Exported plan data to {output_json}")


###############################################################################
# (4) Read the JSON data back in and produce DataFrames + box-stem style plots
###############################################################################
#
# You provided a large block of code that compares multiple “patients/plans.”
# For a single plan or a single comparison scenario, you can adapt that code.
# Below is a condensed version that:
#  - loads the JSON
#  - turns the goals into a DataFrame
#  - demonstrates a simple DVH plot
#  - includes your box-stem “Goal” class for more advanced comparisons
#

def empty_copy(obj):
    class Empty(obj.__class__):
        def __init__(self):
            pass

    newcopy = Empty()
    newcopy.__class__ = obj.__class__
    return newcopy


class Goal:
    """
    Your existing 'Goal' class, condensed a bit for brevity.
    This version sets self.goal_str in the constructor
    and can store the 'goal_value' for display/plots.
    """

    def __init__(self, initial=None):
        tr_dict = {
            'AtLeast': '≥',
            'AtMost': '≤',
            'DoseAtVolume': 'D',
            'VolumeAtDose': 'V',
            'DoseAtAbsoluteVolume': 'D'
        }
        if initial is None:
            self.roi = numpy.nan
            self.parameter_value = numpy.nan
            self.goal_criteria = numpy.nan
            self.priority = numpy.nan
            self.goal_value = numpy.nan
            self.roi_type = numpy.nan
            self.type = numpy.nan
            self.acceptance_level = numpy.nan
            self.goal_evaluation = numpy.nan
            self.goal_str = numpy.nan
        else:
            self.roi = initial['roi']
            self.parameter_value = initial['parameter_value']
            self.goal_criteria = initial['goal_criteria']
            self.priority = initial['priority']
            self.goal_value = initial['goal_value']
            self.roi_type = initial['roi_type']
            self.type = initial['type']
            self.acceptance_level = initial['acceptance_level']
            self.goal_evaluation = initial['goal_evaluation']
            self.goal_str = None
            # Build a readable string
            if self.type == 'VolumeAtDose':
                val = f"{float(self.acceptance_level) * 100:.2f}%"
                par = f"{float(self.parameter_value) / 100:.2f}Gy"
                self.goal_str = f"{self.roi}:: V({par}) {tr_dict[self.goal_criteria]} {val}"
            elif self.type == 'DoseAtVolume':
                val = f"{float(self.acceptance_level) / 100:.2f}Gy"
                par = f"{float(self.parameter_value) * 100:.2f}%"
                self.goal_str = f"{self.roi}:: D({par}) {tr_dict[self.goal_criteria]} {val}"
            elif self.type == 'DoseAtAbsoluteVolume':
                val = f"{float(self.acceptance_level) / 100:.2f}Gy"
                par = f"{float(self.parameter_value) * 100:.2f}cc"
                self.goal_str = f"{self.roi}:: D({par}) {tr_dict[self.goal_criteria]} {val}"
            else:
                # Fallback
                self.goal_str = f"{self.roi}:: UnknownGoalType"

    def __eq__(self, other):
        return (
                other and
                self.roi == other.roi and
                isclose(self.parameter_value, other.parameter_value, abs_tol=1e-3) and
                self.goal_criteria == other.goal_criteria and
                self.priority == other.priority and
                self.roi_type == other.roi_type and
                self.type == other.type and
                isclose(self.acceptance_level, other.acceptance_level, abs_tol=1e-3)
        )

    def __copy__(self):
        new_copy = empty_copy(self)
        new_copy.roi = self.roi
        new_copy.parameter_value = self.parameter_value
        new_copy.goal_criteria = self.goal_criteria
        new_copy.priority = self.priority
        new_copy.goal_value = numpy.nan
        new_copy.roi_type = self.roi_type
        new_copy.type = self.type
        new_copy.acceptance_level = self.acceptance_level
        new_copy.goal_evaluation = numpy.nan
        new_copy.goal_str = self.goal_str
        return new_copy

    def getall(self):
        """
        Return a dict of all fields.
        """
        return {
            'roi': self.roi,
            'parameter_value': self.parameter_value,
            'goal_criteria': self.goal_criteria,
            'priority': self.priority,
            'goal_value': self.goal_value,
            'roi_type': self.roi_type,
            'type': self.type,
            'acceptance_level': self.acceptance_level,
            'goal_evaluation': self.goal_evaluation,
            'goal_str': self.goal_str
        }


# Utility function if you want to compare sets of goals:
def different_goals(check, ref):
    """
    Return a list of goals in 'check' that are not matched in 'ref'.
    """
    unmatched = []
    for ckkey, ckval in check.items():
        matched = False
        for rfkey, rfval in ref.items():
            if ckval == rfval:
                matched = True
                break
        if not matched:
            unmatched.append(ckval)
    return unmatched


###############################################################################
def read_and_compare_goals(json_file):
    """
    Example function:
      - read the single JSON with plan data
      - parse goals into a dictionary
      - convert them into your 'Goal' objects
      - create a DataFrame
      - do a simple demonstration of box-plotting or direct printing
    """
    with open(json_file, 'r') as fp:
        data_dict = json.load(fp)

    # Build a dictionary of Goal objects indexed by an integer
    goal_dict = {}
    for idx_str, gdict in data_dict['goals'].items():
        idx_int = int(idx_str)
        goal_dict[idx_int] = Goal(gdict)

    # Convert these to a DataFrame:
    # Each goal gets a row; columns are the fields in 'Goal.getall()'
    df_goals = pd.DataFrame.from_dict({idx: g.getall() for idx, g in goal_dict.items()},
                                      orient='index')
    df_goals.sort_index(inplace=True)

    print("\n=== Clinical Goals from JSON ===")
    print(df_goals)

    # Simple box plot example of 'goal_value' vs. 'acceptance_level' (normalized)
    # We'll do it with a single plan, so you might not have multiple to compare.
    # But to demonstrate, let's treat each row as a "sample" for a boxplot:
    val_array = df_goals['goal_value'].values
    normed_array = df_goals['goal_value'] / df_goals['acceptance_level']

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    # left subplot: absolute goal_value
    axes[0].boxplot(val_array, showmeans=True)
    axes[0].set_title("Goal Values (absolute)")
    axes[0].grid(True)

    # right subplot: normalized
    axes[1].boxplot(normed_array, showmeans=True)
    axes[1].set_title("Goal Values / Acceptance Level")
    axes[1].axhline(y=1.0, color='r', linestyle='--')  # reference line
    axes[1].grid(True)

    plt.suptitle("Clinical Goals for Plan: " + data_dict['PlanName'])
    plt.show()

    # Return the df if you want to do more with it
    return df_goals
