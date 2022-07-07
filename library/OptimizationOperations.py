""" Optimize Plan Functions

    Automatically optimize the current case, examination, plan, beamset using
    input optimization parameters

    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are
           passed to the function as an argument

    Example Usage:
    import optimize_plan from automated_plan_optimization
    optimization_inputs = {
        'initial_max_it': 40,
        'initial_int_it': 7,
        'second_max_it': 25,
        'second_int_it': 5,
        'vary_grid': True,
        'dose_dim1': 0.4,
        'dose_dim2': 0.3,
        'dose_dim3': 0.35,
        'dose_dim4': 0.2,
        'fluence_only': False,
        'reset_beams': True,
        'segment_weight': True,
        'reduce_oar': True,
        'n_iterations': 6}

    optimize_plan(patient=Patient,
                  case=case,
                  plan=plan,
                  beamset=beamset,
                  **optimization_inputs)

    Script Created by RAB Oct 2nd 2017
    Prerequisites:
        -   For reduce oar dose to work properly the user must use organ type correctly for
            targets

    Version history:
    1.0.0 Updated to use current beamset number for optimization,
            Validation efforts: ran this script for 30+ treatment plans.
            No errors beyond those encountered in typical optimization - abayliss
    1.0.1 Commented out the automatic jaw-limit restriction as this was required with
          jaw-tracking on but is no longer needed
    1.0.2 Turn off auto-scale prior to optimization -ugh
    2.0.0 Enhancements:
            Adds significant functionality including: variable dose grid definition,
            user interface, co-optimization capability, logging, status stepping,
            optimization time tracking, report of times, lots of error handling
          Error Corrections:
            Corrected error in reduce oar dose function call, which was effectively
            not performing the call at all.
          Future Enhancements:
            - [ ] Eliminate the hard coding of the dose grid changes in make_variable_grid_list
             and dynamically assign the grid based on the user's call
            - [ ] Add error catching for jaws being too large to autoset them for X1=-10 and X2=10
            - [ ] Add logging for voxel size
            - [ ] Add logging for functional decreases with each step - list of items
    2.0.1 Bug fix, if co-optimization is not used, the segment weight optimization fails. Put in logic
          to declare the variable cooptimization=False for non-cooptimized beamsets
    2.0.2 Bug fix, remind user that gantry 4 degrees cannot be changed without a reset.
          Inclusion of TomoTherapy Optimization methods
    2.0.3 Adding Jaw locking, including support for lock-to-jaw max for TrueBeamStX
    2.0.4 Added calls to BeamOperations for checking jaw limits. I wanted to avoid causing jaws to be set larger
          than allowed. Currently, the jaws will be the maximum X1, Y1 (least negative) and minimum X2, Y2
    2.0.5 Updated to RS 11
    2.0.6 Added check on existing dimension of dose grid. If current dimension is less than default
          don't reset


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
__date__ = '2022-Jun-27'
__version__ = '2.0.5'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = ''
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__credits__ = ['']

#

import logging
import connect
import UserInterface
import datetime
import sys
import os
import math
import pandas as pd
import numpy as np
import PlanOperations
import BeamOperations
from GeneralOperations import logcrit as logcrit


def iter_optimization_config_etree(etree):
    """Load the elements of the optimization_config tag into a dictionary

    Arguments:
        etree {[elementtree]} -- optimization_config tag

    Returns:
        oc_preferences -- a dictionary for reading into a dataframe
    """
    os_config = {'optimization_config': []}
    for o in etree.iter('optimization_config'):
        o_c = {}
        #
        # Optimization Configuration Name
        try:
            o_c["name"] = o.find("name").text
        except AttributeError:
            o_c["name"] = ""
        #
        # Description
        try:
            o_c["description"] = o.find("description").text
        except AttributeError:
            o_c["description"] = ""
        #
        # Initial iteration
        try:
            o_c["initial"] = o.find("initial").text
            o_c["initial_max_it"] = int(o.find("initial").attrib["max_it"])
            o_c["initial_int_it"] = int(o.find("initial").attrib["int_it"])
        except AttributeError:
            o_c["initial"] = ""
            o_c["initial_max_it"] = None
            o_c["initial_int_it"] = None
        #
        # Warmstart iteration
        try:
            o_c["warmstart"] = o.find("warmstart").text
            o_c["warmstart_max_it"] = int(o.find("warmstart").attrib["max_it"])
            o_c["warmstart_int_it"] = int(o.find("warmstart").attrib["int_it"])
            o_c["warmstart_n"] = int(o.find("warmstart").attrib["n"])
        except AttributeError:
            o_c["warmstart"] = ""
            o_c["warmstart_max_it"] = None
            o_c["warmstart_int_it"] = None
            o_c["warmstart_n"] = None
        #
        # Vary Dose Grid
        try:
            o_c["vary_grid"] = o.find("vary_grid").text
            if o_c["vary_grid"] == "True":
                o_c["vary_grid"] = True
                o_c["dose_dim1"] = float(o.find("vary_grid").attrib["dose_dim1"])
                o_c["dose_dim2"] = float(o.find("vary_grid").attrib["dose_dim2"])
                o_c["dose_dim3"] = float(o.find("vary_grid").attrib["dose_dim3"])
                o_c["dose_dim4"] = float(o.find("vary_grid").attrib["dose_dim4"])
            else:
                o_c["vary_grid"] = False
                o_c["dose_dim1"] = None
                o_c["dose_dim2"] = None
                o_c["dose_dim3"] = None
                o_c["dose_dim4"] = None
        except AttributeError:
            o_c["vary_grid"] = False
            o_c["dose_dim1"] = None
            o_c["dose_dim2"] = None
            o_c["dose_dim3"] = None
            o_c["dose_dim4"] = None
        #
        # Fluence Only
        try:
            o_c['fluence_only'] = o.find("fluence_only").text
            if o_c['fluence_only'] == "True":
                o_c['fluence_only'] = True
            else:
                o_c['fluence_only'] = False
        except AttributeError:
            o_c['fluence_only'] = False
        #
        # Reset Beams
        try:
            o_c['reset_beams'] = o.find("reset_beams").text
            if o_c['reset_beams'] == "True":
                o_c['reset_beams'] = True
            else:
                o_c['reset_beams'] = False
        except AttributeError:
            o_c['reset_beams'] = False
        #
        # Reduce Mod
        try:
            o_c['reduce_mod'] = o.find("reduce_mod").text
            if o_c['reduce_mod'] == "True":
                o_c['reduce_mod'] = True
                o_c['mod_target'] = float(o.find("reduce_mod").attrib["mod_target"])
            else:
                o_c['reduce_mod'] = False
                o_c['mod_target'] = False
        except AttributeError:
            o_c['reduce_mod'] = True
            o_c['mod_target'] = None
        #
        # Reduce OAR
        try:
            o_c['reduce_oar'] = o.find("reduce_oar").text
            if o_c['reduce_oar'] == "True":
                o_c['reduce_oar'] = True
            else:
                o_c['reduce_oar'] = False
        except AttributeError:
            o_c['reduce_oar'] = False
        #
        # Segment weight
        try:
            o_c['segment_weight'] = o.find("segment_weight").text
            if o_c['segment_weight'] == "True":
                o_c['segment_weight'] = True
            else:
                o_c['segment_weight'] = False
        except AttributeError:
            o_c['segment_weight'] = False
        #
        # Prompt for structure blocking/protection
        try:
            o_c['block_prompt'] = o.find("block_prompt").text
            if o_c['block_prompt'] == "True":
                o_c['block_prompt'] = True
            else:
                o_c['block_prompt'] = False
        except AttributeError:
            o_c['block_prompt'] = False
        #
        # Robustness optimization
        try:
            o_c['robust'] = o.find("robust").text
            if o_c['robust'] == "True":
                o_c['robust'] = True
                o_c['robust_sup'] = float(o.find("robust").attrib["sup"])
                o_c['robust_inf'] = float(o.find("robust").attrib["inf"])
                o_c['robust_ant'] = float(o.find("robust").attrib["ant"])
                o_c['robust_post'] = float(o.find("robust").attrib["post"])
                o_c['robust_right'] = float(o.find("robust").attrib["right"])
                o_c['robust_left'] = float(o.find("robust").attrib["left"])
            else:
                o_c['robust'] = False
                o_c['robust_sup'] = None
                o_c['robust_inf'] = None
                o_c['robust_ant'] = None
                o_c['robust_post'] = None
                o_c['robust_right'] = None
                o_c['robust_left'] = None
        except AttributeError:
            o_c['robust'] = False
            o_c['robust_sup'] = None
            o_c['robust_inf'] = None
            o_c['robust_ant'] = None
            o_c['robust_post'] = None
            o_c['robust_right'] = None
            o_c['robust_left'] = None
        # Append the resulting configuration to the dictionary
        os_config['optimization_config'].append(o_c)
    return os_config


def make_variable_grid_list(n_iterations, variable_dose_grid):
    """
    Function will determine, based on the input arguments, which iterations will result in a
    dose grid change.

    :param  n_iterations - number of total iterations to be run, from 1 to n_iterations
    :param  variable_dose_grid - a four element list with an iteration number
              at each iteration number a grid change should occur

    :returns change_grid  (list type)
                the index of the list is the iteration, and the value is the grid_size

    :Todo Get rid of the hard-coding of these dict elements at some point,
                Allow dynamic variation in the dose grid.
    """
    # n_iterations 1 to 4 are hard coded.
    if n_iterations == 1:
        change_grid = [variable_dose_grid['delta_grid'][3]]
    elif n_iterations == 2:
        change_grid = [variable_dose_grid['delta_grid'][0],
                       variable_dose_grid['delta_grid'][3]]
    elif n_iterations == 3:
        change_grid = [variable_dose_grid['delta_grid'][0],
                       variable_dose_grid['delta_grid'][2],
                       variable_dose_grid['delta_grid'][3]]
    elif n_iterations == 4:
        change_grid = [variable_dose_grid['delta_grid'][0],
                       variable_dose_grid['delta_grid'][1],
                       variable_dose_grid['delta_grid'][2],
                       variable_dose_grid['delta_grid'][3]]
    # if the number of iterations is > 4 then use the function specified grid_adjustment
    # iteration. Here we could easily put in support for a dynamic assignment.
    # change_grid will look like [0.5, 0, 0, 0.4, 0, 0.3, 0.2] where the optimize_plan
    # function will change the dose grid at each non-zero value
    else:
        change_grid = []
        for iteration in range(0, n_iterations):
            if iteration == variable_dose_grid['grid_adjustment_iteration'][0]:
                change_grid.append(variable_dose_grid['delta_grid'][0])
            elif iteration == variable_dose_grid['grid_adjustment_iteration'][1]:
                change_grid.append(variable_dose_grid['delta_grid'][1])
            elif iteration == variable_dose_grid['grid_adjustment_iteration'][2]:
                change_grid.append(variable_dose_grid['delta_grid'][2])
            elif iteration == variable_dose_grid['grid_adjustment_iteration'][3]:
                change_grid.append(variable_dose_grid['delta_grid'][3])
            else:
                change_grid.append(0)
    return change_grid


def approximate_lte(x, y):
    return np.all(x <= y) or np.all(np.isclose(x, y))

def select_rois_for_treat(plan, beamset, rois=None):
    """ For the beamset supplie set treat settings
    :param beamset: RS beamset or ForTreatmentSetup object
    :param rois: a list of strings of roi names
    :return roi_list: a list of rois that were set to allow Treat Margins for this beamset"""
    # Find the plan optimization for this beamset
    target_objectives = ['MinDose', 'UniformDose', 'TargetEud']
    function_types = ['CompositeDose']
    roi_list = []
    if rois is None:
        OptIndex = PlanOperations.find_optimization_index(plan=plan, beamset=beamset,
                                                          verbose_logging=False)
        plan_optimization = plan.PlanOptimizations[OptIndex]
        # Look for co-optimization - Treatment setup settings is an array if there is cooptimization
        if len(plan_optimization.OptimizationParameters.TreatmentSetupSettings) > 1:
            cooptimization = True
        else:
            cooptimization = False
            objective_beamset_name = None
        for o in plan_optimization.Objective.ConstituentFunctions:
            roi_name = o.ForRegionOfInterest.Name
            try:
                objective_function_type = o.DoseFunctionParameters.FunctionType
            except AttributeError:
                logging.debug(
                    'Objective type for roi {} is not associated with target and is ignored'.format(
                        roi_name) + ' from treat settings.')
                objective_function_type = None
            # Non-cooptimized objectives have no ForBeamSet object
            if cooptimization:
                try:
                    objective_beamset_name = o.OfDoseDistribution.ForBeamSet.DicomPlanLabel
                except AttributeError:
                    logging.debug(
                        'Objective for roi {} is not defined on a specific beamset'.format(
                            roi_name) + ' and is not included in treat settings.')
                    objective_beamset_name = None

            # If not cooptimization the roi is automatically in scope.
            # Otherwise match the beamset to which this objective is assigned to
            # the current beamset or label it out of scope.
            if not cooptimization or objective_beamset_name == beamset.DicomPlanLabel:
                roi_in_scope = True
            else:
                roi_in_scope = False

            if objective_function_type in target_objectives and \
                    roi_in_scope and \
                    roi_name not in roi_list:
                roi_list.append(roi_name)
        for r in roi_list:
            beamset.SelectToUseROIasTreatOrProtectForAllBeams(RoiName=r)
            logging.debug('Roi {} added to list for treat margins for beamset {}'.format(
                r, beamset.DicomPlanLabel))
    else:
        for r in rois:
            try:
                beamset.SelectToUseROIasTreatOrProtectForAllBeams(RoiName=r)
            except Exception as e:
                try:
                    if 'No ROI named' in e.Message:
                        logging.info(
                            'TreatProtect settings failed for roi {} since it does not exist'.format(
                                r))
                    else:
                        logging.exception(u'{}'.format(e.Message))
                        sys.exit(u'{}'.format(e.Message))
                except:
                    logging.exception(u'{}'.format(e.Message))
                    sys.exit(u'{}'.format(e.Message))
            if r not in roi_list:
                roi_list.append(r)
    return roi_list


def set_treat_margins(beam, rois, margins=None):
    """ Find the ROI's in this beamset that have a target type that are used in
        the optimization. Look at the plan name to define an aperature setting for
        the Treat Margins"""
    # TODO add functionality for single roi
    if margins is None:
        margins = {'Y1': 0.8, 'Y2': 0.8, 'X1': 0.8, 'X2': 0.8}

    for r in rois:
        logging.debug('{} treat margins used [X1, X2, Y1, Y2] = [{}, {}, {}, {}]'.format(
            r, margins['X1'], margins['X2'], margins['Y1'], margins['Y2']))
        try:
            beam.SetTreatAndProtectMarginsForBeam(TopMargin=margins['Y2'],
                                                  BottomMargin=margins['Y1'],
                                                  RightMargin=margins['X2'],
                                                  LeftMargin=margins['X1'],
                                                  Roi=r)
        except Exception as e:
            logging.exception(u'{}'.format(e.Message))
            sys.exit(u'{}'.format(e.Message))


def check_min_jaws(plan_opt, min_dim):
    """
    This function takes in the beamset, looks for field sizes that are less than a minimum
    resets the beams, and sets iteration count to back to zero
    :param beamset: current RS beamset
    :param min_dim: size of smallest desired aperture
    :return jaw_change: if a change was required return True, else False
    # This will not work with jaw tracking!!!

    """
    # If there are segments, check the jaw positions to see if they are less than min_dim

    # epsilon is a factor used to identify whether the jaws are likely to need adjustment
    # min_dimension * (1 + epsilon) will be used to lock jaws
    epsilon = 0.1
    jaw_change = False
    # n_mlc = 64
    # y_thick_inner = 0.25
    # y_thick_outer = 0.5
    for treatsettings in plan_opt.OptimizationParameters.TreatmentSetupSettings:
        for b in treatsettings.BeamSettings:
            logging.debug("Checking beam {} for jaw size limits".format(b.ForBeam.Name))
            # Search for the maximum leaf extend among all positions
            plan_is_optimized = False
            try:
                if b.ForBeam.DeliveryTechnique == 'SMLC':
                    if b.ForBeam.Segments:
                        plan_is_optimized = True
                elif b.ForBeam.DeliveryTechnique == 'DynamicArc':
                    if b.ForBeam.HasValidSegments:
                        plan_is_optimized = True
            except:
                logging.debug("Plan is not VMAT or SNS, behavior will not be clear for check")

            if plan_is_optimized:
                # Find the minimum jaw position, first set to the maximum
                min_x_aperture = 40
                min_y_aperture = 40
                for s in b.ForBeam.Segments:
                    # Find the minimum aperture in each beam
                    if s.JawPositions[1] - s.JawPositions[0] <= min_x_aperture:
                        min_x1 = s.JawPositions[0]
                        min_x2 = s.JawPositions[1]
                        min_x_aperture = min_x2 - min_x1
                    if s.JawPositions[3] - s.JawPositions[2] <= min_y_aperture:
                        min_y1 = s.JawPositions[2]
                        min_y2 = s.JawPositions[3]
                        min_y_aperture = min_y2 - min_y1

                # If the minimum size in x is smaller than min_dim, set the minimum to a proportion of min_dim
                # Use floor and ceil functions to ensure rounding to the nearest mm
                if min_x_aperture <= min_dim * (1 + epsilon):
                    logging.info(
                        'Minimum x-aperture is smaller than {} resetting beams'.format(min_dim))
                    logging.debug('x-aperture is X1={}, X2={}'.format(min_x1, min_x2))
                    x2 = (min_dim / (min_x2 - min_x1)) * min_x2
                    x1 = (min_dim / (min_x2 - min_x1)) * min_x1
                    logging.debug('x-aperture pre-flo/ceil X1={}, X2={}'.format(x1, x2))
                    x2 = math.ceil(10 * x2) / 10
                    x1 = math.floor(10 * x1) / 10
                    logging.debug('x-aperture is being set to X1={}, X2={}'.format(x1, x2))
                else:
                    x2 = s.JawPositions[1]
                    x1 = s.JawPositions[0]
                # If the minimum size in y is smaller than min_dim, set the minimum to a proportion of min_dim
                if min_y_aperture <= min_dim * (1 + epsilon):
                    logging.info(
                        'Minimum y-aperture is smaller than {} resetting beams'.format(min_dim))
                    logging.debug('y-aperture is Y1={}, Y2={}'.format(min_y1, min_y2))
                    y2 = (min_dim / (min_y2 - min_y1)) * min_y2
                    y1 = (min_dim / (min_y2 - min_y1)) * min_y1
                    logging.debug('y-aperture pre-flo/ceil Y1={}, Y2={}'.format(y1, y2))
                    y2 = math.ceil(10 * y2) / 10
                    y1 = math.floor(10 * y1) / 10
                    logging.debug('y-aperture is being set to Y1={}, Y2={}'.format(y1, y2))
                else:
                    y2 = s.JawPositions[3]
                    y1 = s.JawPositions[2]
                if min_x_aperture <= min_dim or min_y_aperture <= min_dim:
                    logging.info(
                        'Jaw size offset necessary on beam: {}, X = {}, Y = {}, with min dimension {}'
                            .format(b.ForBeam.Name, min_x_aperture, min_y_aperture, min_dim))
                    jaw_change = True
                    try:
                        # Uncomment to automatically set jaw limits
                        b.EditBeamOptimizationSettings(
                            JawMotion='Lock to limits',
                            LeftJaw=x1,
                            RightJaw=x2,
                            TopJaw=y1,
                            BottomJaw=y2,
                            SelectCollimatorAngle='False',
                            AllowBeamSplit='False',
                            OptimizationTypes=['SegmentOpt', 'SegmentMU'])
                    except:
                        logging.warning("Could not change beam settings to change jaw sizes")
                else:
                    logging.info(
                        'Jaw size offset unnecessary on beam:{}, X={}, Y={}, with min dimension={}'
                            .format(b.ForBeam.Name, min_x_aperture, min_y_aperture, min_dim))
            else:
                logging.debug("Beam {} is not optimized".format(b.ForBeam.Name))
    if jaw_change:
        plan_opt.ResetOptimization()
    return jaw_change


def reduce_oar_dose(plan_optimization):
    """
    Function will search the objective list and sort by target and oar generates
    then executes the reduce_oar command.

    :param plan_optimization:

    :return: true for successful execution, false for failure

    :todo:  -   identify oars by organ type to avoid accidentally using an incorrect type in
                reduce oars
            -   if Raystation support composite optimization + ReduceOARDose at some point
                the conditional should be removed
    """
    #
    # targets to be identified by their organ type and oars are assigned to everything else
    targets = []
    oars = []
    # Figure out if this plan is co-optimized and reject any ReduceOAR if it is
    # Do this by searching the objective functions for those that have a beamset
    # attribute
    composite_objectives = []
    for index, objective in enumerate(plan_optimization.Objective.ConstituentFunctions):
        if hasattr(objective.OfDoseDistribution, 'ForBeamSet'):
            composite_objectives.append(index)
    # If composite objectives are found warn the user
    if composite_objectives:
        connect.await_user_input("ReduceOAR with composite optimization is not supported " +
                                 "by RaySearch as of RS 11")
        logging.warning("reduce_oar_dose: " +
                        "RunReduceOARDoseOptimization not executed due to the presence of" +
                        "CompositeDose objectives")
        logging.debug("reduce_oar_dose: composite" +
                      "objectives found in iterations {}".format(composite_objectives))
        return False
    else:
        # Construct the currently-used targets and regions at risk as lists targets and oars
        # respectively
        logging.info("reduce_oar_dose: no composite" +
                     "objectives found, proceeding with ReduceOARDose")
        for objective in plan_optimization.Objective.ConstituentFunctions:
            objective_organ_type = objective.OfDoseGridRoi.OfRoiGeometry.OfRoi.OrganData.OrganType
            objective_roi_name = objective.OfDoseGridRoi.OfRoiGeometry.OfRoi.Name
            if objective_organ_type == 'Target':
                objective_is_target = True
            else:
                objective_is_target = False
            if objective_is_target:
                # Add only unique elements to targets
                if objective_roi_name not in targets:
                    targets.append(objective_roi_name)
            else:
                # Add only unique elements to oars
                if objective_roi_name not in oars:
                    oars.append(objective_roi_name)
        sorted_structure_message = "reduce_oar_dose: " + \
                                   "Reduce OAR dose executing with targets: " + ', '.join(targets)
        sorted_structure_message += " and oars: " + ', '.join(oars)
        logging.info(sorted_structure_message)

        try:
            test_success = plan_optimization.RunReduceOARDoseOptimization(
                UseVoxelBasedMimickingForTargets=False,
                UseVoxelBasedMimickingForOrgansAtRisk=False,
                OrgansAtRiskToImprove=oars,
                TargetsToMaintain=targets,
                OrgansAtRiskToMaintain=oars)
            return True
        except:
            return False


def add_robust_parameters(plan_optimization,
                          robust_superior,
                          robust_inferior,
                          robust_anterior,
                          robust_posterior,
                          robust_left,
                          robust_right,
                          robust_exams=[]):
    """
    Function adds a robust scenario for use with robust objectives
    only positional robustness currently supported

    :param plan_optimization: the RS TreatmentPlans:PlanOptimization Object
    :param robust_superior: superior distance [cm] over which to evaluate robustness
    :param robust_inferior: inferior distance [cm] over which to evaluate robustness
    :param robust_right: right distance [cm] over which to evaluate robustness
    :param robust_left: left distance [cm] over which to evaluate robustness
    :param robust_anterior: anterior distance [cm] over which to evaluate robustness
    :param robust_posterior: posterior distance [cm] over which to evaluate robustness
    :param robust_exams: a list of exams
    TODO: Support robustness on multiple images

    """
    #
    # Parse exam argument
    if robust_exams:
        exams = robust_exams
    else:
        exams = []
    #
    plan_optimization.OptimizationParameters.SaveRobustnessParameters(
        PositionUncertaintyAnterior=robust_anterior,
        PositionUncertaintyPosterior=robust_posterior,
        PositionUncertaintySuperior=robust_superior,
        PositionUncertaintyInferior=robust_inferior,
        PositionUncertaintyLeft=robust_left,
        PositionUncertaintyRight=robust_right,
        DensityUncertainty=0,
        PositionUncertaintySetting="Universal",
        IndependentLeftRight=True,
        IndependentAnteriorPosterior=True,
        IndependentSuperiorInferior=True,
        ComputeExactScenarioDoses=False,
        NamesOfNonPlanningExaminations=exams)
    if exams:
        logging.info('Robust optimization on used for beamset:{} on exams {}, with scenario'.format(
            plan_optimization.OptimizedBeamSets.DicomPlanLabel, exams) +
                     'Superior {s}, Inferior {i}, Posterior {p}, Anterior {a}, Right{r}, Left{l}'
                     .format(s=robust_superior,
                             i=robust_inferior,
                             a=robust_anterior,
                             p=robust_posterior,
                             r=robust_right,
                             l=robust_left))
    else:
        logging.info('Robust optimization on used for beamset:{}, with scenario'.format(
            plan_optimization.OptimizedBeamSets.DicomPlanLabel) +
                     'Superior {s}, Inferior {i}, Posterior {p}, Anterior {a}, Right{r}, Left{l}'
                     .format(s=robust_superior,
                             i=robust_inferior,
                             a=robust_anterior,
                             p=robust_posterior,
                             r=robust_right,
                             l=robust_left))


def optimization_report(fluence_only, vary_grid, reduce_oar, segment_weight, **report_inputs):
    """
    Output the conditions of the optimization to debug and inform the user through
    the return message

    :param fluence_only: logical based on fluence-only calculation
    :param vary_grid: logical based on varying dose grid during optimization
    :param reduce_oar: logical based on use reduce oar dose
    :param segment_weight: logical based on use segment weight optimization
    :param report_inputs: optional dictionary containing recorded times
    :return: on_screen_message: a string containing a status update

    :todo: add the functional values for each iteration
    """
    logging.info("optimization report: Post-optimization report:\n" +
                 " Desired steps were:")
    for step in report_inputs.get('status_steps'):
        logging.info('{}'.format(step))

    logging.info("optimization report: Optimization Time Information:")
    on_screen_message = 'Optimization Time information \n'
    # Output the total time for the script to run
    try:
        time_total_final = report_inputs.get('time_total_final')
        time_total_initial = report_inputs.get('time_total_initial')
        time_total = time_total_final - time_total_initial
        logging.info("Time: Optimization (seconds): {}".format(
            time_total.total_seconds()))
        # Update screen message
        on_screen_message += "Total time of the optimization was: {} s\n".format(
            time_total.total_seconds())
    except KeyError:
        logging.debug("No total time available")

    # If the user happened to let the fluence run to its termination output the optimization time
    if fluence_only:
        try:
            time_iteration_initial = report_inputs.get('time_iteration_initial')
            time_iteration_final = report_inputs.get('time_iteration_final')
            time_iteration_total = datetime.timedelta(0)
            for iteration, (initial, final) in enumerate(
                    zip(time_iteration_initial, time_iteration_final)):
                time_iteration_delta = final - initial
                time_iteration_total = time_iteration_total + time_iteration_delta
                logging.info("Time: Fluence-based optimization iteration {} (seconds): {}".format(
                    iteration, time_iteration_delta.total_seconds()))
                on_screen_message += "Iteration {}: Time Required {} s\n".format(
                    iteration + 1, time_iteration_delta.total_seconds())
        except KeyError:
            logging.debug("No fluence time list available")
    else:
        # Output the time required for each iteration and the total time spent in aperture-based optimization
        if report_inputs.get('maximum_iteration') != 0:
            try:
                time_iteration_initial = report_inputs.get('time_iteration_initial')
                time_iteration_final = report_inputs.get('time_iteration_final')
                time_iteration_total = datetime.timedelta(0)
                for iteration, (initial, final) in enumerate(
                        zip(time_iteration_initial, time_iteration_final)):
                    time_iteration_delta = final - initial
                    time_iteration_total = time_iteration_total + time_iteration_delta
                    logging.info(
                        "Time: Aperture-based optimization iteration {} (seconds): {}".format(
                            iteration, time_iteration_delta.total_seconds()))
                    on_screen_message += "Iteration {}: Time Required {} s\n".format(
                        iteration + 1, time_iteration_delta.total_seconds())
                logging.info("Time: Total Aperture-based optimization (seconds): {}".format(
                    time_iteration_total.total_seconds()))
                logcrit("Time: Total Aperture-based optimization (seconds): {}".format(
                    time_iteration_total.total_seconds()))
                on_screen_message += "Total time spent in aperture-based optimization was: {} s\n".format(
                    time_iteration_total.total_seconds())
            except KeyError:
                logging.debug("No Aperture-based iteration list available")
        # Output the time required for dose grid based changes
        if vary_grid:
            try:
                time_dose_grid = datetime.timedelta(0)
                time_dose_grid_initial = report_inputs.get('time_dose_grid_initial')
                time_dose_grid_final = report_inputs.get('time_dose_grid_final')
                for grid_change, (initial, final) in enumerate(
                        zip(time_dose_grid_initial, time_dose_grid_final)):
                    time_dose_grid_delta = final - initial
                    time_dose_grid = time_dose_grid + time_dose_grid_delta
                    logging.info("Time: Dose Grid change {} (seconds): {}".format(
                        grid_change, time_dose_grid_delta.total_seconds()))
                logging.info("Time: Dose Grid changes (seconds): {}".format(
                    time_dose_grid.total_seconds()))
                on_screen_message += "Total time of the dose grid changes was: {} s\n".format(
                    time_dose_grid.total_seconds())
            except KeyError:
                logging.debug("Dose grid time changes not available")
        # Output the time spent in segment weight based optimization
        if segment_weight:
            try:
                time_segment_weight_final = report_inputs.get('time_segment_weight_final')
                time_segment_weight_initial = report_inputs.get('time_segment_weight_initial')
                time_segment_weight = time_segment_weight_final - time_segment_weight_initial
                logging.info("Time: Segment Weight optimization (seconds): {}".format(
                    time_segment_weight.total_seconds()))
                on_screen_message += "Total time of segment weight only was: {} s\n".format(
                    time_segment_weight.total_seconds())
            except KeyError:
                logging.debug("No segment weight time available")
        # Output the time required for reduced oar dose calculation
        if reduce_oar:
            try:
                time_reduceoar_initial = report_inputs.get('time_reduceoar_initial')
                time_reduceoar_final = report_inputs.get('time_reduceoar_final')
                time_reduceoar = time_reduceoar_final - time_reduceoar_initial
                logging.info("Time: ReduceOarDose (seconds): {}".format(
                    time_reduceoar.total_seconds()))
                on_screen_message += "Total Time of Reduce OAR dose operation was: {} s\n".format(
                    time_reduceoar.total_seconds())
            except KeyError:
                logging.debug("No reduce OAR Dose time available")
    # Generate output - the onscreen message
    on_screen_message += 'Close this screen when complete'
    return on_screen_message


def parse_evaluation_function(progress_of_optimization, rtp_function, rf_i):
    # Take in a given objective from the optimizer and return the a dictionary
    # of the important features
    dfp_data = {}
    # Determine kind of objective we have
    RTPFunction = rtp_function
    composite = False
    dfo = False
    regular = False
    # Catch composites
    try:
        RTPFunction.FunctionType
        composite = True
    except AttributeError:
        composite = False
    # Catch dfo
    try:
        RTPFunction.DoseFunctionParameters.FunctionType
        regular = True
        dfo = False
    except AttributeError:
        regular = False
        dfo = True

    objective_values = progress_of_optimization.ObjectiveValues

    if composite:
        dfp_data['Roi'] = 'Composite'
        dfp_data['FunctionType'] = RTPFunction.FunctionType
        dfp_data['DoseLevel'] = None
        dfp_data['PercentVolume'] = None
        dfp_data['EudParameterA'] = None
        dfp_data['Weight'] = None
        dfp_data['HighDose'] = None
        dfp_data['LowDose'] = None
        dfp_data['Distance'] = None
        dfp_data['FinalValue'] = RTPFunction.FunctionValue.FunctionValue
    elif regular:
        dfp_data['Roi'] = RTPFunction.ForRegionOfInterest.Name
        dfp_data['FunctionType'] = RTPFunction.DoseFunctionParameters.FunctionType
        dfp_data['DoseLevel'] = RTPFunction.DoseFunctionParameters.DoseLevel
        if 'Eud' in RTPFunction.DoseFunctionParameters.FunctionType:
            dfp_data['PercentVolume'] = None
            dfp_data['EudParameterA'] = RTPFunction.DoseFunctionParameters.EudParameterA
        else:
            dfp_data['PercentVolume'] = RTPFunction.DoseFunctionParameters.PercentVolume
            dfp_data['EudParameterA'] = None
        dfp_data['Weight'] = RTPFunction.DoseFunctionParameters.Weight
        dfp_data['HighDose'] = None
        dfp_data['LowDose'] = None
        dfp_data['Distance'] = None
        dfp_data['FinalValue'] = RTPFunction.FunctionValue.FunctionValue
    elif dfo:
        dfp_data['Roi'] = RTPFunction.ForRegionOfInterest.Name
        dfp_data['FunctionType'] = 'DFO'
        dfp_data['DoseLevel'] = None
        dfp_data['PercentVolume'] = None
        dfp_data['EudParameterA'] = None
        dfp_data['Weight'] = RTPFunction.DoseFunctionParameters.Weight
        dfp_data['HighDose'] = RTPFunction.DoseFunctionParameters.HighDoseLevel
        dfp_data['LowDose'] = RTPFunction.DoseFunctionParameters.LowDoseLevel
        dfp_data['Distance'] = RTPFunction.DoseFunctionParameters.LowDoseDistance
        dfp_data['FinalValue'] = RTPFunction.FunctionValue.FunctionValue

    # Columns of iteration number for each function
    iterations = progress_of_optimization.Iterations
    its_list = []
    its_data = {}
    for i in iterations.tolist():
        its_list.append(int(i))
        its_data[int(i)] = progress_of_optimization.FunctionValues[int(i) - 1][rf_i]
    dfp_data.update(its_data)

    return dfp_data


def filename_iteration_output(iteration_number, beamset, patient, iteration_dir):
    # Construct the output filename string
    # Get the time
    now = datetime.datetime.now()
    dt_string = now.strftime("%m%d%Y_%H%M%S")
    #
    # Create patient specific string
    patient_string = patient.PatientID + "_" + beamset.DicomPlanLabel
    #
    # Join Strings
    filename = patient_string + "_" + dt_string
    #
    # Resolve dir
    try:
        if not os.path.isdir(iteration_dir):
            os.mkdir(iteration_dir)
    except Exception as e:
        sys.exit('{}'.format(e))
    return os.path.normpath('{}/{}.pkl'.format(iteration_dir, filename))


def output_iteration_data(poo, warmstart_number,
                          iteration_output_file,
                          beamset,
                          beam_params,
                          iteration_time):
    """
    poo: objective function object from RS
    warmstart_number: the iteration count
    """
    try:
        logging.debug('Beam params are {}'.format(beam_params))
        iterations = poo.Iterations
        objective_values = poo.ObjectiveValues
        rtp_functions = poo.ForRtpFunctions
        # Columns of Objective information
        cols = ['Roi', 'FunctionType', 'Weight', 'DoseLevel',
                'PercentVolume', 'EudA', 'HighDose', 'LowDose', 'Distance']
        #
        # Determine treatment technique
        if beamset.DeliveryTechnique == 'TomoHelical':
            cols = cols + ['time', 'rp', 'proj_time', 'total_travel', 'couch_speed', 'mod_factor']
            beam_dict = {'time': float(beam_params.iloc[0].time),
                         'proj_time': float(beam_params.iloc[0].proj_time),
                         'rp': float(beam_params.iloc[0].rp),
                         'total_travel': float(beam_params.iloc[0].total_travel),
                         'couch_speed': float(beam_params.iloc[0].couch_speed),
                         'mod_factor': float(beam_params.iloc[0].mod_factor),
                         'sinogram': beam_params.iloc[0].sinogram,
                         'WarmStart': int(warmstart_number),
                         'IterationTime': float(iteration_time.total_seconds()),
                         }
            for k, v in beam_dict.items():
                logging.debug('Adding the following to the output file {}, {}'.format(k, v))
        else:
            cols = cols + ['IterationTime']
            beam_dict = {'IterationTime': float(iteration_time.total_seconds())}
        # Columns of iteration number for each function
        its_list = []
        for i in iterations.tolist():
            its_list.append(int(i))
        cols = cols + iterations.tolist() + ['FinalValue']
        logging.debug('Headers are {}'.format(cols))
        df_1 = pd.DataFrame(columns=cols)
        objective_index = 0
        for rf in rtp_functions:
            row = parse_evaluation_function(poo, rf, rf_i=objective_index)
            row.update(beam_dict)
            df_1 = df_1.append(row, ignore_index=True)
            logging.debug('Made it through objective {}'.format(objective_index))
            objective_index += 1

        # Output
        df_1.to_pickle(iteration_output_file)
        # Read back in with df_2 = pd.read_pickle(iteration_output_file)
    except Exception as e:
        logging.debug('Error in setting output objective data {}'.format(e))
        sys.exit("{}".format(e))


def optimize_plan(patient, case, exam, plan, beamset, **optimization_inputs):
    """
    This function will optimize a plan
    :param patient: script requires a current patient
    :param case: a case is needed, though the variable is not used
    :param exam: an exam is needed to check the CT system
    :param plan: current plan
    :param beamset: current beamset, note composite optimization is supported
    :param optimization_inputs:
    TODO: Fill in all possible inputs
    :return: error
    """
    # For the supplied beamset compute the jaw-defined equivalent square
    try:
        patient.Save()
    except SystemError:
        return False, "No Patient loaded. Load patient case and plan."

    try:
        case.SetCurrent()
    except SystemError:
        return False, "No Case loaded. Load patient case and plan."

    try:
        plan.SetCurrent()
    except SystemError:
        return False, "No plan loaded. Load patient and plan."

    try:
        beamset.SetCurrent()
    except SystemError:
        return False, "No beamset loaded"

    if exam.EquipmentInfo.ImagingSystemReference:
        logging.debug('Examination has an assigned CT to density table')
    else:
        connect.await_user_input(
            'Set CT imaging system for this examination and continue the script')

    # TODO: Make this a beamset setting in the xml protocols
    small_field_names = ['_SRS_', '_SBR_', '_FSR_', '_LLL_', '_LUL_', '_RLL_', '_RML_', '_RUL_']
    large_field_names = ['TBI__FFS', 'TBI__HFS', 'HFS__TBI', 'FFS__TBI',
                         'TBI_FFS', 'TBI_HFS', 'HFS_TBI', 'FFS_TBI']
    # Choose the minimum field size in cm
    min_dim = 2
    # Parameters used for iteration number
    initial_maximum_iteration = optimization_inputs.get('initial_max_it', 60)
    initial_intermediate_iteration = optimization_inputs.get('initial_int_it', 10)
    second_maximum_iteration = optimization_inputs.get('second_max_it', 30)
    second_intermediate_iteration = optimization_inputs.get('second_int_it', 15)

    vary_grid = optimization_inputs.get('vary_grid', False)
    # Grid Sizes
    if vary_grid:
        dose_dim1 = optimization_inputs.get('dose_dim1', 0.5)
        dose_dim2 = optimization_inputs.get('dose_dim2', 0.4)
        dose_dim3 = optimization_inputs.get('dose_dim3', 0.3)
        dose_dim4 = optimization_inputs.get('dose_dim4', 0.2)

    maximum_iteration = optimization_inputs.get('n_iterations', 12)
    fluence_only = optimization_inputs.get('fluence_only', False)
    reset_beams = optimization_inputs.get('reset_beams', True)
    reduce_oar = optimization_inputs.get('reduce_oar', True)
    reduce_mod = optimization_inputs.get('reduce_mod', False)
    if reduce_mod:
        mod_target = optimization_inputs.get('mod_target', None)
    segment_weight = optimization_inputs.get('segment_weight', False)
    gantry_spacing = optimization_inputs.get('gantry_spacing', 2)
    close_status = optimization_inputs.get('close_status', False)
    # Check if a robustness scenario is to be used
    robust_optimization = optimization_inputs.get('robust', False)
    if robust_optimization:
        robust_superior = optimization_inputs.get('robust_sup', None)
        robust_inferior = optimization_inputs.get('robust_inf', None)
        robust_anterior = optimization_inputs.get('robust_ant', None)
        robust_posterior = optimization_inputs.get('robust_post', None)
        robust_right = optimization_inputs.get('robust_right', None)
        robust_left = optimization_inputs.get('robust_left', None)
    # Output of iteration during optimization specifications
    iteration_output_dir = optimization_inputs.get('output_data_dir', None)
    if iteration_output_dir:
        output_progress = True
    else:
        output_progress = False

    # Reporting
    report_inputs = {
        'initial_maximum_iteration': initial_maximum_iteration,
        'initial_intermediate_iteration': initial_intermediate_iteration,
        'second_maximum_iteration': second_maximum_iteration,
        'second_intermediate_iteration': second_intermediate_iteration,
        'maximum_iteration': maximum_iteration,
        'reset_beams': reset_beams,
        'gantry_spacing': gantry_spacing
    }
    if vary_grid:
        report_inputs['dose_dim1'] = dose_dim1
        report_inputs['dose_dim2'] = dose_dim2
        report_inputs['dose_dim3'] = dose_dim3
        report_inputs['dose_dim4'] = dose_dim4
        dose_dim_initial = dose_dim1
    elif any(a in beamset.DicomPlanLabel for a in large_field_names):
        dose_dim_initial = 0.4
    elif any(a in beamset.DicomPlanLabel for a in small_field_names):
        dose_dim_initial = 0.15
    else:
        dose_dim_initial = 0.2

    # Start the clock on the script at this time
    # Timing
    report_inputs['time_total_initial'] = datetime.datetime.now()

    if fluence_only:
        logging.info('Fluence only: {}'.format(fluence_only))
    else:
        if vary_grid:
            beamset.SetDefaultDoseGrid(
                VoxelSize={
                    'x': dose_dim1,
                    'y': dose_dim1,
                    'z': dose_dim1})
            variable_dose_grid = {
                'delta_grid': [dose_dim1,
                               dose_dim2,
                               dose_dim3,
                               dose_dim4],
                'grid_adjustment_iteration': [0,
                                              int(maximum_iteration / 2),
                                              int(3 * maximum_iteration / 4),
                                              int(maximum_iteration - 1)]}
            change_dose_grid = make_variable_grid_list(maximum_iteration, variable_dose_grid)

    save_at_complete = optimization_inputs.get('save', False)
    # Making the variable status script, arguably move to main()
    num_steps = 0
    status_dict = {0: 'Initialize optimization'}
    status_steps = [status_dict[num_steps]]
    if reset_beams:
        num_steps += 1
        status_dict[num_steps] = 'Reset Beams'
        status_steps.append(status_dict[num_steps])

    if fluence_only:
        num_steps += 1
        status_dict[num_steps] = 'Optimize Fluence Only'
        status_steps.append(status_dict[num_steps])
    else:
        for i in range(maximum_iteration):
            # Update message for changing the dose grids.
            if vary_grid:
                if change_dose_grid[i] != 0:
                    num_steps += 1
                    status_dict[num_steps] = 'Change dose grid to: {} cm'.format(change_dose_grid[i])
                    status_steps.append(status_dict[num_steps])
            if reduce_mod and i == maximum_iteration - 1:
                num_steps += 1
                status_dict[num_steps] = 'Reduce Modulation on Iteration: ' + str(i + 1)
                ith_step = status_dict[num_steps]
                reduce_mod_step = num_steps
            else:
                num_steps += 1
                status_dict[num_steps] = 'Complete Iteration:' + str(i + 1)
                ith_step = status_dict[num_steps]
            status_steps.append(ith_step)
        if segment_weight:
            num_steps += 1
            status_dict[num_steps] = 'Complete Segment weight optimization'
            status_steps.append(status_dict[num_steps])
        if reduce_oar:
            num_steps += 1
            status_dict[num_steps] = 'Reduce OAR Dose'
            status_steps.append(status_dict[num_steps])
    if save_at_complete:
        num_steps += 1
        status_dict[num_steps] = 'Save Patient'
        status_steps.append(status_dict[num_steps])

    num_steps += 1
    status_dict[num_steps] = 'Provide Optimization Report'
    status_steps.append(status_dict[num_steps])

    report_inputs['status_steps'] = status_steps

    logging.critical('{} automated optimization started with reset beams {}, {} warmstarts'.format(
        beamset.DicomPlanLabel, reset_beams, maximum_iteration
    ))

    # Change the status steps to indicate each iteration
    status = UserInterface.ScriptStatus(
        steps=status_steps,
        docstring=__doc__,
        help=__help__)

    status.next_step("Setting initialization variables")
    logging.info('Set some variables like Niterations, Nits={}'.format(maximum_iteration))
    # Variable definitions
    i = 0
    beamsinrange = True
    optimization_iteration = 0

    # SNS Properties
    maximum_segments_per_beam = 10  # type: int
    min_leaf_pairs = '2'  # type: str
    min_leaf_end_separation = '0.5'  # type: str
    allow_beam_split = False
    min_segment_area = '2'
    min_segment_mu = '2'

    if '_PRD_' in beamset.DicomPlanLabel:
        min_segment_area = '4'
        min_segment_mu = '6'
        logging.info('PRDR plan detected, setting minimum area to {} and minimum mu to {}'.format(
            min_segment_area, min_segment_mu))

    if any(a in beamset.DicomPlanLabel for a in small_field_names):
        margins = {'Y1': 0.15, 'Y2': 0.15, 'X1': 0.15, 'X2': 0.15}
    else:
        margins = {'Y1': 0.8, 'Y2': 0.8, 'X1': 0.8, 'X2': 0.8}

    # Find current Beamset Number and determine plan optimization
    rs_opt_key = PlanOperations.find_optimization_index(plan=plan, beamset=beamset,
                                                        verbose_logging=False)
    plan_optimization = plan.PlanOptimizations[rs_opt_key]
    plan_optimization_parameters = plan.PlanOptimizations[rs_opt_key].OptimizationParameters
    if robust_optimization:
        add_robust_parameters(plan_optimization=plan_optimization,
                              robust_superior=robust_superior,
                              robust_inferior=robust_inferior,
                              robust_anterior=robust_anterior,
                              robust_posterior=robust_posterior,
                              robust_right=robust_right,
                              robust_left=robust_left,
                              robust_exams=[])

    # Turn on important parameters
    plan_optimization_parameters.DoseCalculation.ComputeFinalDose = True

    # Turn off autoscale
    try:
        beamset.SetAutoScaleToPrimaryPrescription(AutoScale=False)
    except Exception as e:
        logging.debug('Failed to turn off autoscale: {}'.format(str(e)))

    # Set the Maximum iterations and segmentation iteration
    # to a high number for the initial run
    plan_optimization_parameters.Algorithm.OptimalityTolerance = 1e-14
    plan_optimization_parameters.Algorithm.MaxNumberOfIterations = initial_maximum_iteration
    plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = initial_intermediate_iteration

    # Try to Set the Gantry Spacing to 2 degrees
    # How many beams are there in this beamset
    # Set the control point spacing
    treatment_setup_settings = plan_optimization_parameters.TreatmentSetupSettings
    if len(treatment_setup_settings) > 1:
        cooptimization = True
        logging.debug('Plan is co-optimized with {} other plans'.format(
            len(plan_optimization_parameters.TreatmentSetupSettings)))
    else:
        cooptimization = False
        logging.debug('Plan is not co-optimized.')
    # Note: pretty worried about the hard-coded zero above. I don't know when it gets incremented
    # it is clear than when co-optimization occurs, we have more than one entry in here...

    # If not set yet, the dose grid needs setting.
    current_grid = beamset.GetDoseGrid()
    if current_grid:
        current_voxelsize = np.array([current_grid.VoxelSize.x,
                                      current_grid.VoxelSize.y,
                                      current_grid.VoxelSize.z])
        update_voxelsize = np.array([dose_dim_initial] * 3)
        if approximate_lte(current_voxelsize, update_voxelsize):
            logging.debug('Dose grid is {} <= {}. No grid changes'.format(current_grid.VoxelSize.x,
                                                                          dose_dim_initial))
        else:
            beamset.SetDefaultDoseGrid(
                VoxelSize={
                    'x': dose_dim_initial,
                    'y': dose_dim_initial,
                    'z': dose_dim_initial})
            plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
            logging.debug('Dose grid initialized with voxel size {}'.format(dose_dim_initial))
    else:
        beamset.SetDefaultDoseGrid(
            VoxelSize={
                'x': dose_dim_initial,
                'y': dose_dim_initial,
                'z': dose_dim_initial})
        plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
        logging.debug('Dose grid initialized with voxel size {}'.format(dose_dim_initial))
        patient.Save()

    # Reset
    if reset_beams:
        plan.PlanOptimizations[rs_opt_key].ResetOptimization()
        status.next_step("Resetting Optimization")

    if plan_optimization.Objective.FunctionValue is None:
        current_objective_function = 0
    else:
        current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
    logging.info('Current total objective function value at iteration {} is {}'.format(
        optimization_iteration, current_objective_function))

    if fluence_only:
        logging.info('User selected Fluence optimization Only')
        status.next_step('Running fluence-based optimization')

        # Fluence only is the quick and dirty way of dialing in all necessary elements for the calc
        plan_optimization_parameters.DoseCalculation.ComputeFinalDose = False
        plan_optimization_parameters.Algorithm.MaxNumberOfIterations = 500
        plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = 500
        # Start the clock for the fluence only optimization
        report_inputs.setdefault('time_iteration_initial', []).append(datetime.datetime.now())
        try:
            plan.PlanOptimizations[rs_opt_key].RunOptimization()
        except Exception as e:
            return False, 'Exception occurred during optimization: {}'.format(e)
        # Stop the clock
        report_inputs.setdefault('time_iteration_final', []).append(datetime.datetime.now())
        # Consider converting this to the report_inputs
        # Output current objective value
        if plan_optimization.Objective.FunctionValue is None:
            current_objective_function = 0
        else:
            current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
        logging.info('Current total objective function value at iteration {} is {}'.format(
            optimization_iteration, current_objective_function))
        reduce_oar_success = False
    else:
        logging.info('Full optimization')
        for ts in treatment_setup_settings:
            # Set properties of the beam optimization
            if ts.ForTreatmentSetup.DeliveryTechnique == 'TomoHelical':
                logging.debug('Tomo plan - control point spacing not set')
            elif ts.ForTreatmentSetup.DeliveryTechnique == 'SMLC':
                #
                # Execute treatment margin settings
                for beams in ts.BeamSettings:
                    mu = beams.ForBeam.BeamMU
                    if mu > 0:
                        logging.debug(
                            'This beamset is already optimized. Not applying treat settings to targets')
                    else:
                        treat_rois = select_rois_for_treat(plan, beamset=ts.ForTreatmentSetup, rois=None)
                        set_treat_margins(beam=beams.ForBeam, rois=treat_rois, margins=margins)
                #
                # Set beam splitting preferences
                for beams in ts.BeamSettings:
                    if mu > 0:
                        logging.debug(
                            'This beamset is already optimized beam-splitting preferences not applied')
                    else:
                        beams.AllowBeamSplit = allow_beam_split
                #
                # Set segment conversion properties
                mu = 0
                num_beams = 0
                for bs in ts.BeamSettings:
                    mu += bs.ForBeam.BeamMU
                    num_beams += 1
                if mu > 0:
                    logging.warning(
                        'This plan may not have typical SMLC optimization params enforced')
                else:
                    ts.SegmentConversion.MinSegmentArea = min_segment_area
                    ts.SegmentConversion.MinSegmentMUPerFraction = min_segment_mu
                    maximum_segments = num_beams * maximum_segments_per_beam
                    ts.SegmentConversion.MinNumberOfOpenLeafPairs = min_leaf_pairs
                    ts.SegmentConversion.MinLeafEndSeparation = min_leaf_end_separation
                    ts.SegmentConversion.MaxNumberOfSegments = str(maximum_segments)
                #
                # Set TrueBeamSTx jaw limits
                machine_ref = ts.ForTreatmentSetup.MachineReference.MachineName
                if machine_ref == 'TrueBeamSTx':
                    logging.info('Current Machine is {} setting max jaw limits'.format(machine_ref))

                    limit = [-20, 20, -10.8, 10.8]
                    for beams in ts.BeamSettings:
                        # Reference the beamset by the subobject in ForTreatmentSetup
                        success = BeamOperations.check_beam_limits(beams.ForBeam.Name,
                                                                   plan=plan,
                                                                   beamset=ts.ForTreatmentSetup,
                                                                   limit=limit,
                                                                   change=True,
                                                                   verbose_logging=True)
                        if not success:
                            # If there are MU then this field has already been optimized with the wrong jaw limits
                            # For Shame....
                            logging.debug(
                                'This beamset is already optimized with unconstrained jaws. Reset needed')
                            UserInterface.WarningBox(
                                'Restart Required: Attempt to limit TrueBeamSTx ' +
                                'jaws failed - check reset beams' +
                                ' on next attempt at this script')
                            status.finish('Restart required')
                            return False, 'Restart Required: Select reset beams on next run of script.'
            elif ts.ForTreatmentSetup.DeliveryTechnique == 'DynamicArc':
                #
                # Execute treatment margin settings
                for beams in ts.BeamSettings:
                    mu = beams.ForBeam.BeamMU
                    if mu > 0:
                        logging.debug('This beamset is already optimized.' +
                                      ' Not applying treat settings to Beam {}'.format(
                                          beams.ForBeam.Name))
                    else:
                        treat_rois = select_rois_for_treat(plan, beamset=ts.ForTreatmentSetup, rois=None)
                        set_treat_margins(beam=beams.ForBeam, rois=treat_rois, margins=margins)
                #
                # Check the control point spacing on arcs
                for beams in ts.BeamSettings:
                    mu = beams.ForBeam.BeamMU
                    if beams.ArcConversionPropertiesPerBeam is not None:
                        if beams.ArcConversionPropertiesPerBeam.FinalArcGantrySpacing > 2:
                            if mu > 0:
                                # If there are MU then this field has already been optimized with the wrong gantry
                                # spacing. For shame....
                                logging.info(
                                    'This beamset is already optimized with > 2 degrees.  Reset needed')
                                UserInterface.WarningBox(
                                    'Restart Required: Attempt to correct final gantry ' +
                                    'spacing failed - check reset beams' +
                                    ' on next attempt at this script')
                                status.finish('Restart required')
                                return False, 'Restart Required: Select reset beams on next run of script.'
                            else:
                                beams.ArcConversionPropertiesPerBeam.EditArcBasedBeamOptimizationSettings(
                                    FinalGantrySpacing=2)
                machine_ref = ts.ForTreatmentSetup.MachineReference.MachineName
                if machine_ref == 'TrueBeamSTx':
                    logging.info('Current Machine is {} setting max jaw limits'.format(machine_ref))
                    limit = [-20, 20, -10.8, 10.8]
                    for beams in ts.BeamSettings:
                        # Reference the beamset by the subobject in ForTreatmentSetup
                        success = BeamOperations.check_beam_limits(beams.ForBeam.Name,
                                                                   plan=plan,
                                                                   beamset=ts.ForTreatmentSetup,
                                                                   limit=limit,
                                                                   change=True,
                                                                   verbose_logging=True)
                        if not success:
                            # If there are MU then this field has already been optimized with the wrong jaw limits
                            # For Shame....
                            logging.debug(
                                'This beamset is already optimized with unconstrained jaws. Reset needed')
                            UserInterface.WarningBox(
                                'Restart Required: Attempt to limit TrueBeamSTx ' +
                                'jaws failed - check reset beams' +
                                ' on next attempt at this script')
                            status.finish('Restart required')
                            return False, 'Restart Required: Select reset beams on next run of script.'
        if output_progress:
            time_0 = datetime.datetime.now()
            time_1 = time_0

        while optimization_iteration != maximum_iteration:
            if plan_optimization.Objective.FunctionValue is None:
                previous_objective_function = 1e10
                logging.debug('This appears to be a cold start. Objective value set to {}'
                              .format(previous_objective_function))
            else:
                previous_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue

            # If the change_dose_grid list has a non-zero element change the dose grid
            if vary_grid:
                if change_dose_grid[optimization_iteration] != 0:
                    status.next_step(
                        'Variable dose grid used.  Dose grid now {} cm'.format(
                            change_dose_grid[optimization_iteration]))
                    logging.info(
                        'Running current value of change_dose_grid is {}'.format(change_dose_grid))
                    dose_dim = change_dose_grid[optimization_iteration]
                    # Start Clock on the dose grid change
                    report_inputs.setdefault('time_dose_grid_initial', []).append(
                        datetime.datetime.now())
                    beamset.SetDefaultDoseGrid(
                        VoxelSize={
                            'x': dose_dim,
                            'y': dose_dim,
                            'z': dose_dim})
                    plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
                    # Stop the clock for the dose grid change
                    report_inputs.setdefault('time_dose_grid_final', []).append(
                        datetime.datetime.now())
            #
            # If modulation reduction or time-reduction is required update the optimization settings
            if reduce_mod and optimization_iteration > 0:
                if ts.ForTreatmentSetup.DeliveryTechnique == 'TomoHelical':
                    tomo_params = BeamOperations.gather_tomo_beam_params(beamset)
                    logging.debug('Tomo params are {}'.format(tomo_params))
                    for b in ts.BeamSettings:
                        old_delivery_time = b.TomoPropertiesPerBeam.MaxDeliveryTime
                        mod_ratio = mod_target / tomo_params.mod_factor[0]
                        logging.debug('Delivery time currently {}'.format(old_delivery_time))
                        logging.debug('Current MF={}, Target={}'.format(tomo_params.mod_factor[0],
                                                                        mod_target))
                        if mod_ratio < 1.0:
                            new_delivery_time = old_delivery_time * mod_ratio * 0.9  # No convergence otherwise
                            settings = {'max_delivery_time': new_delivery_time}
                            BeamOperations.modify_tomo_beam_properties(settings, plan, beamset, b.ForBeam)
                            logging.info(
                                'Target mod factor exceeded ({} > {}):'.format(tomo_params.mod_factor[0], mod_target)
                                + 'Max delivery time updated from {} to {}'.format(old_delivery_time,
                                                                                   new_delivery_time))
                            if optimization_iteration == maximum_iteration - 1:
                                # We need to keep going until mod factor is under target
                                maximum_iteration += 1
                                logging.info('Last iteration reached and mod factor target not met.'
                                             + 'Extending max iterations by 1 to {}'.format(maximum_iteration))
                                status.next_step(text='Reducing Mod', num=reduce_mod_step)
                else:
                    logging.exception("Reduce mod not available for optimization on non helical plans")
            report_inputs.setdefault('time_iteration_initial', []).append(datetime.datetime.now())
            status.next_step(
                text='Running current iteration = {} of {}'.format(optimization_iteration + 1,
                                                                   maximum_iteration))
            logging.info(
                'Current iteration = {} of {}'.format(optimization_iteration + 1,
                                                      maximum_iteration))
            # Run the optimization
            try:
                time_0 = datetime.datetime.now()
                plan.PlanOptimizations[rs_opt_key].RunOptimization()
                time_1 = datetime.datetime.now()
            except Exception as e:
                try:
                    message = "".format(e.Message)
                    if "There is no feasible gantry period" in message:
                        logging.critical("No feasible gantry period found. Full message {}".format(message))
                    else:
                        return False, 'Exception occurred during optimization: {}'.format(e)
                except:
                    return False, 'Exception occurred during optimization: {}'.format(e)
            if output_progress:
                poo = plan_optimization.ProgressOfOptimization
                time_total = time_1 - time_0
                logging.info("Time: Optimization (seconds): {}".format(
                    time_total.total_seconds()))
                if ts.ForTreatmentSetup.DeliveryTechnique == 'TomoHelical':
                    beam_params = BeamOperations.gather_tomo_beam_params(beamset)
                else:
                    # TODO: Figure out what we want for VMAT
                    # Phys. Med. Biol. 60 (2015) 2587 - SAS 1 and 10
                    beam_params = {}
                iteration_output_file = filename_iteration_output(
                    iteration_number=optimization_iteration,
                    beamset=beamset,
                    patient=patient,
                    iteration_dir=iteration_output_dir,
                )
                output_iteration_data(poo=poo,  # No matter what you call it
                                      warmstart_number=optimization_iteration,
                                      iteration_output_file=iteration_output_file,
                                      beamset=beamset,
                                      beam_params=beam_params,
                                      iteration_time=time_total)

            # Stop the clock
            report_inputs.setdefault('time_iteration_final', []).append(datetime.datetime.now())
            optimization_iteration += 1
            logging.info("Optimization Number: {} completed".format(optimization_iteration))
            # Set the Maximum iterations and segmentation iteration to a lower number for the initial run
            plan_optimization_parameters.Algorithm.MaxNumberOfIterations = second_maximum_iteration
            plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = second_intermediate_iteration
            # Outputs for debug
            current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
            logging.info(
                'At iteration {} total objective function is {}, compared to previous {}'.format(
                    optimization_iteration,
                    current_objective_function,
                    previous_objective_function))
            if reduce_mod:
                if previous_objective_function < current_objective_function:
                    settings = {}
                    if old_delivery_time > 60.:
                        settings['max_delivery_time'] = 0.9 * old_delivery_time
                        BeamOperations.modify_tomo_beam_properties(settings, plan, beamset, b.ForBeam)
                        logging.info('Function value (Previous {} < Current {}). Reduced time from {} to  {}'.format(
                            previous_objective_function, current_objective_function,
                            old_delivery_time, settings['max_delivery_time']))
                else:
                    logging.info('Function value ({} > {}). Delivery time unchanged'.format(
                        previous_objective_function, current_objective_function))

            # Start the clock
            previous_objective_function = current_objective_function

        # Finish with a Reduce OAR Dose Optimization
        if segment_weight:
            if beamset.DeliveryTechnique == 'TomoHelical':
                status.next_step('TomoHelical Plan skipping Segment weight only optimization')
                logging.warning(
                    'Segment weight based optimization is not supported for TomoHelical')
                report_inputs['time_segment_weight_initial'] = datetime.datetime.now()
                report_inputs['time_segment_weight_final'] = datetime.datetime.now()
            else:
                status.next_step('Running Segment weight only optimization')
                report_inputs['time_segment_weight_initial'] = datetime.datetime.now()
                # Uncomment when segment-weight based co-optimization is supported
                # TODO: Checked in version 11B. Check in next version
                if cooptimization:
                    logging.warning("Co-optimized segment weight-based optimization is" +
                                    " not supported by RaySearch as of RS 11")
                    connect.await_user_input(
                        "Segment-weight optimization with composite optimization is not supported " +
                        "by RaySearch at this time")
                else:
                    for ts in treatment_setup_settings:
                        for beams in ts.BeamSettings:
                            if 'SegmentOpt' in beams.OptimizationTypes:
                                beams.EditBeamOptimizationSettings(
                                    OptimizationTypes=["SegmentMU"]
                                )
                    try:
                        plan.PlanOptimizations[rs_opt_key].RunOptimization()
                    except Exception as e:
                        return 'Exception occurred during optimization: {}'.format(e)
                    logging.info(
                        'Current total objective function value at iteration {} is {}'.format(
                            optimization_iteration,
                            plan_optimization.Objective.FunctionValue.FunctionValue))
                report_inputs['time_segment_weight_final'] = datetime.datetime.now()

        # Finish with a Reduce OAR Dose Optimization
        reduce_oar_success = False
        if reduce_oar:
            if beamset.DeliveryTechnique == 'TomoHelical':
                status.next_step('TomoHelical Plan skipping reduce oar dose optimization')
                logging.warning(
                    'Segment weight based optimization is not supported for TomoHelical')
                report_inputs['time_reduce_oar_initial'] = datetime.datetime.now()
                report_inputs['time_reduce_oar_final'] = datetime.datetime.now()
            else:
                status.next_step('Running ReduceOar Dose')
                report_inputs['time_reduceoar_initial'] = datetime.datetime.now()
                reduce_oar_success = reduce_oar_dose(plan_optimization=plan_optimization)
                report_inputs['time_reduceoar_final'] = datetime.datetime.now()
                if reduce_oar_success:
                    logging.info('ReduceOAR successfully completed')
                else:
                    logging.warning('ReduceOAR failed')
                logging.info('Current total objective function value at iteration {} is {}'.format(
                    optimization_iteration, plan_optimization.Objective.FunctionValue))

    report_inputs['time_total_final'] = datetime.datetime.now()
    if save_at_complete:
        try:
            patient.Save()
            status.next_step('Save Complete')
        except Exception as e:
            return False, 'Exception occurred during optimization: {}'.format(e)

    on_screen_message = optimization_report(
        fluence_only=fluence_only,
        vary_grid=vary_grid,
        reduce_oar=reduce_oar_success,
        segment_weight=segment_weight,
        **report_inputs)
    logging.critical('{} finished at {}'.format(beamset.DicomPlanLabel, datetime.datetime.now()))

    status.next_step('Optimization summary')
    if close_status:
        status.close()
    else:
        status.finish(on_screen_message)
    return True, on_screen_message
