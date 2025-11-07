""" Load isodose and target visualization
    Loads some simple visual settings for targets and isodoses since this is not a sticky
    property of the RayStation (RS) software

    Version:
    1.0 Load targets as filled. Normalize isodose to prescription, and try to normalize to the
        maximum dose in External or External_Clean

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '29-Jul-2019'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8.b.SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import logging
import StructureOperations as so
from PlanReview.utils.review_api_versions import (get_prescription_dose_references,
                                                  get_acceptance_level_from_planning_goal)


def sort_and_map_to_colors(values):
    """
    Sorts a list of integers in descending order and maps them to predefined colors
    normalized by the maximum value in the list.

    Args:
        values (list): A list of up to five integers.

    Returns:
        dict: A dictionary with keys as normalized integers and values as colors.

    Raises:
        ValueError: If more than five integers are provided.
    """
    if len(values) > 13:
        raise ValueError("The list can contain up to 5 integers only.")

    # Define colors
    reference_colors = [
        so.define_sys_color([227, 26, 28]),  # BrewerRed
        so.define_sys_color([51, 160, 44]),  # BrewerDarkGreen
        so.define_sys_color([31, 120, 180]),  # BrewerDarkBlue
        so.define_sys_color([255, 127, 0]),  # BrewerOrange
        so.define_sys_color([106, 61, 154]),  # BrewerPurple
        so.define_sys_color([177, 89, 40]),  # BrewerBrown
        so.define_sys_color([255, 255, 51]),  # BrewerEsqueYellow
        so.define_sys_color([166, 206, 227]),  # BrewerLightBlue
        so.define_sys_color([178, 223, 138]),  # BrewerLightGreen
        so.define_sys_color([251, 154, 153]),  # BrewerLightRed
        so.define_sys_color([253, 191, 111]),  # BrewerLightOrange
        so.define_sys_color([202, 178, 214]),  # BrewerLightPurple
        so.define_sys_color([255, 255, 153]),  # BrewerLightYellow
    ]

    # Sort the list in descending order
    sorted_values = sorted(values, reverse=True)

    # Create the dictionary with normalized keys and color values
    color_mapping = {value: reference_colors[i] for i, value in enumerate(sorted_values)}

    return color_mapping


def isodose_reconfig(case, ref_doses, max_dose):
    """
    This function takes the current case, an optional max_dose
    :param case: ScriptObject of RS case
    :param ref_doses: The dose levels of interest in Gy
    :param max_dose: an optional argument that can designate the maximum dose within the plan
    :return:
    """
    # Find the maximum dose in the reference doses
    reference_dose = max(ref_doses)
    max_ratio = max_dose / reference_dose
    hottest_isodose = 98 * max_ratio  # 98% of ratio of max dose to reference dose
    # Halfway between reference and max dose
    hot_isodose = 100 * 0.5 * (1 + max_ratio)  # Halfway between reference and max dose

    target_dose_dict = sort_and_map_to_colors(ref_doses)

    rainbow_dose_levels = {
        hottest_isodose: so.define_sys_color([128, 20, 20]),  # BrewerDarkRed
        hot_isodose: so.define_sys_color([255, 0, 127]),  # BrewerPink
        100: so.define_sys_color([255, 0, 0]),  # Red
        95: so.define_sys_color([255, 128, 0]), # Orange
        90: so.define_sys_color([255, 255, 0]), # Yellow
        85: so.define_sys_color([127, 255, 0]), # Lime
        80: so.define_sys_color([0, 255, 0]), # Green
        70: so.define_sys_color([0, 255, 127]), # Teal
        60: so.define_sys_color([0, 255, 255]), # Aqua
        50: so.define_sys_color([0, 127, 255]), # Sky
        40: so.define_sys_color([0, 0, 255]), # Blue
        30: so.define_sys_color([127, 0, 255]), # Purple
        20: so.define_sys_color([255, 0, 255]), # Magenta
    }

    drop_range = 2  # The range in percentage of the reference dose to drop a rainbow dose
    dose_color_table = {}

    # Add target doses to dose_color_table
    for k, v in target_dose_dict.items():
        dose_color_table[100 * k / reference_dose] = v

    # Add rainbow doses to dose_color_table if they are not within drop_range of any target dose
    for k, v in rainbow_dose_levels.items():
        if all(abs(k - target) > drop_range for target in dose_color_table.keys()):
            dose_color_table[k] = v

    # Sort the dose_color_table in descending order
    dose_color_table = {key: dose_color_table[key] for key in sorted(dose_color_table.keys(), reverse=True)}

    case.CaseSettings.DoseColorMap.ColorTable = dose_color_table
    case.CaseSettings.DoseColorMap.PresentationType = 'Absolute'
    case.CaseSettings.DoseColorMap.ReferenceValue = reference_dose


def get_beamset_dose_at_point(beamset, point):
    """
    Determine the maximum dose at the specified point.
    Args:
        beamset: (ScriptObject): The beamset to check
        point: (dict): A dictionary with 'x', 'y', and 'z' keys representing the point to check
    Returns:
        (float): The maximum dose at the specified point in Gy
    """
    maximum_per_fraction_dose = beamset.FractionDose.InterpolateDoseInPoint(
        Point=point, PointFrameOfReference=beamset.FrameOfReference)
    number_of_fractions = beamset.FractionationPattern.NumberOfFractions
    return maximum_per_fraction_dose * number_of_fractions  # Gy


def find_max_dose_in_plan(beamset):
    max_dose_point = beamset.FractionDose.GetCoordinateOfMaxDose()
    if max_dose_point:
        max_dose = get_beamset_dose_at_point(beamset=beamset, point=max_dose_point)
    else:
        max_dose = None
    return max_dose


def goal_matches_priority(e, priority):
    if not priority:
        return True
    if int(e.PlanningGoal.Priority) == priority:
        return True
    else:
        return False


def parse_dose_from_goal(e):
    goal_type = e.PlanningGoal.Type
    if goal_type == 'DoseAtAbsoluteVolume':
        return int(e.PlanningGoal.AcceptanceLevel)
    elif goal_type == 'VolumeAtDose':
        return int(e.PlanningGoal.ParameterValue)
    elif goal_type == 'AverageDose':
        return int(e.PlanningGoal.AcceptanceLevel)
    else:
        k = logging.warning('unknown goal type {}'.format(goal_type))


def parse_coverage_from_goal(e, filters):
    result = False
    for f in filters:
        goal_acceptance_level = get_acceptance_level_from_planning_goal(e.PlanningGoal)
        if e.PlanningGoal.GoalCriteria == f[0] and goal_acceptance_level == f[1]:
            result = True
    return result


def find_goal_dose_levels(plan, priority, doses=None):
    # Find the dose levels used in the evaluation of the goals and return list of isodoses
    # priority is a list of priority levels. If present, then only return dose levels of
    # those groups.
    if doses is None:
        doses = []
    filters = [('AtLeast', 0.95), ('AtLeast', 0.98), ('AtLeast', 0.99), ('AtLeast', 1.0)]
    for e in plan.TreatmentCourse.EvaluationSetup.EvaluationFunctions:
        if goal_matches_priority(e, priority) and parse_coverage_from_goal(e, filters):
            d = parse_dose_from_goal(e)
            if d and d not in doses:
                doses.append(d)
    return sorted(doses)


def get_prescription_dose_levels(beamset):
    dose_levels = []
    prescription_dose_references = get_prescription_dose_references(beamset)
    try:
        for pdr in prescription_dose_references:
            dose_levels.append(pdr.DoseValue)
    except AttributeError:
        return dose_levels
    return dose_levels


def change_visualization_targets(rso):
    target_types = ['Ptv', 'Ctv', 'Gtv']
    for roi in rso.case.PatientModel.RegionsOfInterest:
        roi_representation = rso.case.PatientModel.RegionsOfInterest[roi.Name]
        if roi_representation.Type in target_types:
            roi_geom = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[roi_representation.Name]
            if roi_geom.HasContours():
                try:
                    roi_visualization_status = roi_representation.RoiVisualizationSettings.VisualizationMode2D()
                    trys = 0
                    while roi_visualization_status != 'Filled' and trys < 5:
                        rso.patient.Set2DvisualizationForRoi(RoiName=roi.Name,
                                                             Mode='filled')
                    if roi_visualization_status != 'Filled':
                        logging.warning(f'Could not change visualization for {roi.Name} after 5 tries')
                except Exception as ex:
                    logging.warning(f'Could not change visualization for {roi.Name} due to {ex}')
                    try:
                        roi.RoiVisualizationSettings.VisualizationMode2D('Filled')
                    except Exception as e:
                        logging.warning(f'Could not change visualization individual settings for {roi.Name} due to {e}')
                        continue


def change_visualization_isodose(rso):
    # Change the targets to filled in
    change_visualization_targets(rso)
    max_dose = find_max_dose_in_plan(beamset=rso.beamset)
    reference_doses = get_prescription_dose_levels(rso.beamset)
    reference_doses = find_goal_dose_levels(plan=rso.plan, priority=2, doses=reference_doses)

    isodose_reconfig(case=rso.case,
                     ref_doses=reference_doses,
                     max_dose=max_dose)
