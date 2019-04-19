""" Automated Plan Optimization
    
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
__date__ = '2018-Sep-27'
__version__ = '2.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '7.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']
#

import logging
import connect
import UserInterface
import datetime
import sys


def make_variable_grid_list(n_iterations, variable_dose_grid):
    """
    Function will determine, based on the input arguments, which iterations will result in a
    dose grid change.

    :param  n_iterations - number of total iterations to be run, from 1 to n_iterations
            variable_dose_grid - a four element list with an iteration number
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

    jaw_change = False
    for treatsettings in plan_opt.OptimizationParameters.TreatmentSetupSettings:
        for b in treatsettings.BeamSettings:
            logging.debug("Checking beam {} for jaw size limits".format(b.ForBeam.Name))
            if b.ForBeam.HasValidSegments:
                # Find the minimum jaw position
                min_x_aperture = 40
                min_y_aperture = 40;
                # Find the minimum aperture in each beam
                for s in b.ForBeam.Segments:
                    # Note: X2 = s.JawPositions[1], X1 = s.JawPositions[0],
                    #       Y2 = s.JawPositions[3], Y1 = s.JawPositions[2],
                    if s.JawPositions[1] - s.JawPositions[0] <= min_x_aperture:
                        min_x1 = s.JawPositions[0]
                        min_x2 = s.JawPositions[1]
                        min_x_aperture = min_x2 - min_x1
                    if s.JawPositions[3] - s.JawPositions[2] <= min_y_aperture:
                        min_y1 = s.JawPositions[2]
                        min_y2 = s.JawPositions[3]
                        min_y_aperture = min_y2 - min_y1
                # If the minimum size in x is smaller than min_dim, set the minimum to a proportion of min_dim
                if min_x_aperture <= min_dim:
                    logging.info('Minimum x-aperture is smaller than {} resetting beams'.format(min_dim))
                    x2 = min_dim * (min_x2 / (min_x2 - min_x1)) + min_x2
                    x1 = min_dim * (min_x1 / (min_x2 - min_x1)) + min_x1
                else:
                    x2 = s.JawPositions[1]
                    x1 = s.JawPositions[0]
                # If the minimum size in x is smaller than min_dim, set the minimum to a proportion of min_dim
                if min_y_aperture <= min_dim:
                    logging.info('Minimum y-aperture is smaller than {} resetting beams'.format(min_dim))
                    y2 = min_dim * (min_y2 / (min_y2 - min_y1)) + min_y2
                    y1 = min_dim * (min_y1 / (min_y2 - min_y1)) + min_y1
                else:
                    y2 = s.JawPositions[3]
                    y1 = s.JawPositions[2]
                if min_x_aperture <= min_dim or min_y_aperture <= min_dim:
                    logging.info('Jaw size offset necessary on beam: {}, X = {}, Y = {}, with min dimension {}'
                                 .format(b.ForBeam.Name,min_x_aperture,min_y_aperture,min_dim))
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
                    logging.info('Jaw size offset unnecessary on beam:{}, X={}, Y={}, with min dimension={}'
                                 .format(b.ForBeam.Name,min_x_aperture,min_y_aperture,min_dim))
            else:
                logging.debug("Beam {} does not have valid segments".format(b.ForBeam.Name))
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
                                 "by RaySearch at this time")
        logging.warning("automated_plan_optimization.py: reduce_oar_dose: " +
                        "RunReduceOARDoseOptimization not executed due to the presence of" +
                        "CompositeDose objectives")
        logging.debug("automated_plan_optimization.py: reduce_oar_dose: composite" +
                      "objectives found in iterations {}".format(composite_objectives))
        return False
    else:
        # Construct the currently-used targets and regions at risk as lists targets and oars
        # respectively
        logging.info("automated_plan_optimization.py: reduce_oar_dose: no composite" +
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
        sorted_structure_message = "automated_plan_optimization.py: reduce_oar_dose: " + \
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
            print test_success
            return True
        except:
            return False


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
    logging.info("automated_plan_optimization.py: optimization report: Post-optimization report:\n" +
                 " Desired steps were:")
    for step in report_inputs.get('status_steps'):
        logging.info('{}'.format(step))

    logging.info("automated_plan_optimization.py: optimization report: Optimization Time Information:")
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
            for iteration, (initial, final) in enumerate(zip(time_iteration_initial, time_iteration_final)):
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
                for iteration, (initial, final) in enumerate(zip(time_iteration_initial, time_iteration_final)):
                    time_iteration_delta = final - initial
                    time_iteration_total = time_iteration_total + time_iteration_delta
                    logging.info("Time: Aperture-based optimization iteration {} (seconds): {}".format(
                        iteration, time_iteration_delta.total_seconds()))
                    on_screen_message += "Iteration {}: Time Required {} s\n".format(
                        iteration + 1, time_iteration_delta.total_seconds())
                logging.info("Time: Total Aperture-based optimization (seconds): {}".format(
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
                for grid_change, (initial, final) in enumerate(zip(time_dose_grid_initial, time_dose_grid_final)):
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


def optimize_plan(patient, case, plan, beamset, **optimization_inputs):
    """
    This function will optimize a plan
    :param patient: script requires a current patient
    :param case: a case is needed, though the variable is not used
    :param plan: current plan
    :param beamset: current beamset, note composite optimization is supported
    :param optimization_inputs:
    :return:
    """
    # For the supplied beamset compute the jaw-defined equivalent square
    try:
        patient.Save()
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case.SetCurrent()
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        plan.SetCurrent()
    except SystemError:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset.SetCurrent()
    except SystemError:
        raise IOError("No beamset loaded")

    # Choose the minimum field size
    min_dim = 10
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
    small_target = optimization_inputs.get('small_target', True)
    reduce_oar = optimization_inputs.get('reduce_oar', True)
    segment_weight = optimization_inputs.get('segment_weight', False)
    gantry_spacing = optimization_inputs.get('gantry_spacing', 2)

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

    # Start the clock on the script at this time
    # Timing
    report_inputs['time_total_initial'] = datetime.datetime.now()

    if fluence_only:
        logging.info('optimize_plan: Fluence only: {}'.format(fluence_only))
    else:
        # If the dose grid is to be varied during optimization unload the grid parameters
        if vary_grid:
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

    # Making the variable status script, arguably move to main()
    status_steps = ['Initialize optimization']
    if reset_beams:
        status_steps.append('Reset Beams')

    if fluence_only:
        status_steps.append('Optimize Fluence Only')
    else:
        for i in range(maximum_iteration):
            # Update message for changing the dose grids.
            if vary_grid:
                if change_dose_grid[i] != 0:
                    status_steps.append('Change dose grid to: {} cm'.format(change_dose_grid[i]))
            ith_step = 'Complete Iteration:' + str(i + 1)
            status_steps.append(ith_step)
        if segment_weight:
            status_steps.append('Complete Segment weight optimization')
        if reduce_oar:
            status_steps.append('Reduce OAR Dose')
    status_steps.append('Provide Optimization Report')

    report_inputs['status_steps'] = status_steps

    # Change the status steps to indicate each iteration
    status = UserInterface.ScriptStatus(
        steps=status_steps,
        docstring=__doc__,
        help=__help__)

    status.next_step("Setting initialization variables")
    logging.info('optimize_plan: Set some variables like Niterations, Nits={}'.format(maximum_iteration))
    # Variable definitions
    i = 0
    beamsinrange = True
    num_beams = 0
    OptIndex = 0
    Optimization_Iteration = 0

    # Find current Beamset Number and determine plan optimization
    OptIndex = 0
    IndexNotFound = True
    # In RS, OptimizedBeamSets objects are keyed using the DicomPlanLabel, or Beam Set name.
    # Because the key to the OptimizedBeamSets presupposes the user knows the PlanOptimizations index
    # this while loop looks for the PlanOptimizations index needed below by searching for a key
    # that matches the BeamSet DicomPlanLabel
    # This can likely be replaced with a list comprehension
    while IndexNotFound:
        try:
            OptName = plan.PlanOptimizations[OptIndex].OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            IndexNotFound = False
        except Exception:
            IndexNotFound = True
            OptIndex += 1
    if IndexNotFound:
        logging.warning("optimize_plan: Beamset optimization for {} could not be found.".format(beamset.DicomPlanLabel))
        sys.exit("Could not find beamset optimization")
    else:
        # Found our index.  We will use a shorthand for the remainder of the code
        plan_optimization = plan.PlanOptimizations[OptIndex]
        plan_optimization_parameters = plan.PlanOptimizations[OptIndex].OptimizationParameters
        logging.info(
            'optimize_plan: Optimization found, proceeding with plan.PlanOptimization[{}] for beamset {}'.format(
                OptIndex, plan_optimization.OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
            ))

    # Turn on important parameters
    plan_optimization_parameters.DoseCalculation.ComputeFinalDose = True

    # Turn off autoscale
    plan.PlanOptimizations[OptIndex].AutoScaleToPrescription = False

    # Set the Maximum iterations and segmentation iteration
    # to a high number for the initial run
    plan_optimization_parameters.Algorithm.OptimalityTolerance = 1e-12
    plan_optimization_parameters.Algorithm.MaxNumberOfIterations = initial_maximum_iteration
    plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = initial_intermediate_iteration

    # Try to Set the Gantry Spacing to 2 degrees
    # How many beams are there in this beamset
    # Set the control point spacing
    treatment_setup_settings = plan_optimization_parameters.TreatmentSetupSettings
    if len(plan_optimization_parameters.TreatmentSetupSettings) > 1:
        cooptimization = True
        logging.debug('automated_plan_optimization: Plan is co-optimized with {} other plans'.format(
            len(plan_optimization_parameters.TreatmentSetupSettings)))
    else:
        cooptimization = False
        logging.debug('automated_plan_optimization: Plan is not co-optimized.')
    # Note: pretty worried about the hard-coded zero above. I don't know when it gets incremented
    # it is clear than when co-optimization occurs, we have more than one entry in here...

    # Reset
    if reset_beams:
        plan.PlanOptimizations[OptIndex].ResetOptimization()
        status.next_step("Resetting Optimization")

    if plan_optimization.Objective.FunctionValue is None:
        current_objective_function = 0
    else:
        current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
    logging.info('optimize_plan: Current total objective function value at iteration {} is {}'.format(
        Optimization_Iteration, current_objective_function))

    if fluence_only:
        logging.info('optimize_plan: User selected Fluence optimization Only')
        status.next_step('Running fluence-based optimization')

        # Fluence only is the quick and dirty way of dialing in all necessary elements for the calc
        plan_optimization_parameters.DoseCalculation.ComputeFinalDose = False
        plan_optimization_parameters.Algorithm.MaxNumberOfIterations = 500
        plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = 500
        # Start the clock for the fluence only optimization
        report_inputs.setdefault('time_iteration_initial', []).append(datetime.datetime.now())
        plan.PlanOptimizations[OptIndex].RunOptimization()
        # Stop the clock
        report_inputs.setdefault('time_iteration_final', []).append(datetime.datetime.now())
        # Consider converting this to the report_inputs
        # Output current objective value
        if plan_optimization.Objective.FunctionValue is None:
            current_objective_function = 0
        else:
            current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
        logging.info('optimize_plan: Current total objective function value at iteration {} is {}'.format(
            Optimization_Iteration, current_objective_function))
        reduce_oar_success = False
    else:
        logging.info('optimize_plan: Full optimization')
        for ts in treatment_setup_settings:
            # Set properties of the beam optimization
            for beams in ts.BeamSettings:
                mu = beams.ForBeam.BeamMU
                # Set the control point spacing for Arc Beams
                if beams.TomoPropertiesPerBeam is not None:
                    logging.debug('Tomo plan - control point spacing not set')
                elif beams.ArcConversionPropertiesPerBeam is not None:
                    if beams.ArcConversionPropertiesPerBeam.FinalArcGantrySpacing > 2:
                        if mu > 0:
                            # If there are MU then this field has already been optimized with the wrong gantry
                            # spacing. For shame....
                            logging.debug('This beamset is already optimized with > 2 degrees.  Reset needed')
                            UserInterface.WarningBox('Restart Required: Attempt to correct final gantry ' +
                                                     'spacing failed - check reset beams' +
                                                     ' on next attempt at this script')
                            sys.exit('Restart Required: Select reset beams on next run of script.')
                        else:
                            beams.ArcConversionPropertiesPerBeam.EditArcBasedBeamOptimizationSettings(
                                FinalGantrySpacing=2)
                    # Maximum Jaw Sizes should be limited for STx beams
                    # Determine the current machine
                    machine_ref = beamset.MachineReference.MachineName
                    if machine_ref == 'TrueBeamSTx':
                        logging.info('Current Machine is {} setting max jaw limits'.format(machine_ref))
                        x1limit = -20
                        x2limit = 20
                        y1limit = -10.9
                        y2limit = 10.9
                        if mu > 0:
                            # If there are MU then this field has already been optimized with the wrong jaw limits
                            # For Shame....
                            logging.debug('This beamset is already optimized with unconstrained jaws. Reset needed')
                            UserInterface.WarningBox('Restart Required: Attempt to limit TrueBeamSTx ' +
                                                     'jaws failed - check reset beams' +
                                                     ' on next attempt at this script')
                            sys.exit('Restart Required: Select reset beams on next run of script.')
                        else:
                            try:
                                # Uncomment to automatically set jaw limits
                                beams.EditBeamOptimizationSettings(
                                    JawMotion='Use limits as max',
                                    LeftJaw=x1limit,
                                    RightJaw=x2limit,
                                    TopJaw=y1limit,
                                    BottomJaw=y2limit,
                                    SelectCollimatorAngle='False',
                                    AllowBeamSplit='False',
                                    OptimizationTypes=['SegmentOpt', 'SegmentMU'])
                            except:
                                logging.debug('Failed to set limits for TrueBeamStx')

        while Optimization_Iteration != maximum_iteration:
            if small_target:
                restart = check_min_jaws(plan_optimization, min_dim)
                if restart:
                    Optimization_Iteration = 0;
            # Record the previous total objective function value
            if plan_optimization.Objective.FunctionValue is None:
                previous_objective_function = 0
            else:
                previous_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue

            status.next_step(
                text='Running current iteration = {} of {}'.format(Optimization_Iteration + 1, maximum_iteration))
            logging.info(
                'optimize_plan: Current iteration = {} of {}'.format(Optimization_Iteration + 1, maximum_iteration))
            #            status.next_step(text='Iterating....')
            # Check for small targets by evaluating the jaw size

            # If the change_dose_grid list has a non-zero element change the dose grid
            if vary_grid:
                if change_dose_grid[Optimization_Iteration] != 0:
                    status.next_step(
                        'Variable dose grid used.  Dose grid now {} cm'.format(
                            change_dose_grid[Optimization_Iteration]))
                    logging.info(
                        'optimize_plan: Running current value of change_dose_grid is {}'.format(change_dose_grid))
                    DoseDim = change_dose_grid[Optimization_Iteration]
                    # Start Clock on the dose grid change
                    report_inputs.setdefault('time_dose_grid_initial', []).append(datetime.datetime.now())
                    plan.SetDefaultDoseGrid(
                        VoxelSize={
                            'x': DoseDim,
                            'y': DoseDim,
                            'z': DoseDim})
                    plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
                    # Stop the clock for the dose grid change
                    report_inputs.setdefault('time_dose_grid_final', []).append(datetime.datetime.now())
            # Start the clock
            report_inputs.setdefault('time_iteration_initial', []).append(datetime.datetime.now())
            # Run the optimization
            plan.PlanOptimizations[OptIndex].RunOptimization()
            # Stop the clock
            report_inputs.setdefault('time_iteration_final', []).append(datetime.datetime.now())

            Optimization_Iteration += 1
            logging.info("optimize_plan: Optimization Number: {} completed".format(Optimization_Iteration))
            # Set the Maximum iterations and segmentation iteration to a lower number for the initial run
            plan_optimization_parameters.Algorithm.MaxNumberOfIterations = second_maximum_iteration
            plan_optimization_parameters.DoseCalculation.IterationsInPreparationsPhase = second_intermediate_iteration
            # Outputs for debug
            current_objective_function = plan_optimization.Objective.FunctionValue.FunctionValue
            logging.info(
                'optimize_plan: At iteration {} total objective function is {}, compared to previous {}'.format(
                    Optimization_Iteration,
                    current_objective_function,
                    previous_objective_function))
            previous_objective_function = current_objective_function

        # Finish with a Reduce OAR Dose Optimization
        if segment_weight:
            status.next_step('Running Segment weight only optimization')
            report_inputs['time_segment_weight_initial'] = datetime.datetime.now()
            # Uncomment when segment-weight based co-optimization is supported
            if cooptimization:
                logging.warning("Co-optimized segment weight-based optimization is" +
                                " not supported by RaySearch at this time.")
                connect.await_user_input("Segment-weight optimization with composite optimization is not supported " +
                                         "by RaySearch at this time")

            else:
                for ts in treatment_setup_settings:
                    for beams in ts.BeamSettings:
                        if 'SegmentOpt' in beams.OptimizationTypes:
                            beams.EditBeamOptimizationSettings(
                                OptimizationTypes=["SegmentMU"]
                            )
                plan.PlanOptimizations[OptIndex].RunOptimization()
                logging.info('optimize_plan: Current total objective function value at iteration {} is {}'.format(
                    Optimization_Iteration, plan_optimization.Objective.FunctionValue.FunctionValue))
            report_inputs['time_segment_weight_final'] = datetime.datetime.now()

        # Finish with a Reduce OAR Dose Optimization
        reduce_oar_success = False
        if reduce_oar:
            status.next_step('Running ReduceOar Dose')
            report_inputs['time_reduceoar_initial'] = datetime.datetime.now()
            reduce_oar_success = reduce_oar_dose(plan_optimization=plan_optimization)
            report_inputs['time_reduceoar_final'] = datetime.datetime.now()
            if reduce_oar_success:
                logging.info('optimize_plan: ReduceOAR successfully completed')
            else:
                logging.warning('optimize_plan: ReduceOAR failed')
            logging.info('optimize_plan: Current total objective function value at iteration {} is {}'.format(
                Optimization_Iteration, plan_optimization.Objective.FunctionValue))

    report_inputs['time_total_final'] = datetime.datetime.now()
    on_screen_message = optimization_report(
        fluence_only=fluence_only,
        vary_grid=vary_grid,
        reduce_oar=reduce_oar_success,
        segment_weight=segment_weight,
        **report_inputs)

    status.next_step('Optimization summary')
    status.finish(on_screen_message)


def main():
    try:
        Patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        plan = connect.get_current("Plan")
    except SystemError:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except SystemError:
        raise IOError("No beamset loaded")

    # OPTIMIZATION DIALOG
    #  Users will select use of:
    # Fluence only - no aperture conversion
    # Maximum number of iterations for the first optimization
    optimization_dialog = UserInterface.InputDialog(
        title='Optimization Inputs',
        inputs={
            'input01_fluence_only': 'Fluence calculation only, for dialing in parameters ' +
                                    'all other values in this window will be ignored',
            'input02_cold_start': 'Reset beams (cold start)',
            'input03_cold_max_iteration': 'Maximum number of iterations for initial optimization',
            'input04_cold_interm_iteration': 'Intermediate iteration for svd to aperture conversion',
            'input05_ws_max_iteration': 'Maximum iteration used in warm starts ',
            'input06_ws_interm_iteration': 'Intermediate iteration used in warm starts',
            'input07_vary_dose_grid': 'Start with large grid, and decrease gradually',
            'input08_n_iterations': 'Number of Iterations',
            'input09_segment_weight': 'Segment weight calculation',
            'input10_reduce_oar': 'Reduce OAR Dose',
            'input11_small_target': 'Target size < 3 cm'},
        datatype={
            'input07_vary_dose_grid': 'check',
            'input01_fluence_only': 'check',
            'input02_cold_start': 'check',
            'input09_segment_weight': 'check',
            'input10_reduce_oar': 'check',
            'input11_small_target': 'check'},
        initial={'input03_cold_max_iteration': '50',
                 'input04_cold_interm_iteration': '10',
                 'input05_ws_max_iteration': '35',
                 'input06_ws_interm_iteration': '5',
                 'input08_n_iterations': '4',
                 'input09_segment_weight': ['Perform Segment Weighted optimization'],
                 'input10_reduce_oar': ['Perform reduce OAR dose before completion'],
                 'input11_small_target': ['Target size < 3 cm - limit jaws']},
        options={
            'input01_fluence_only': ['Fluence calc'],
            'input02_cold_start': ['Reset Beams'],
            'input07_vary_dose_grid': ['Variable Dose Grid'],
            'input09_segment_weight': ['Perform Segment Weighted optimization'],
            'input10_reduce_oar': ['Perform reduce OAR dose before completion'],
            'input11_small_target': ['Target size < 3 cm - limit jaws']},
        required=[])
    print optimization_dialog.show()

    # DATA PARSING FOR THE OPTIMIZATION MENU
    # Determine if variable dose grid is selected
    try:
        if 'Variable Dose Grid' in optimization_dialog.values['input07_vary_dose_grid']:
            vary_dose_grid = True
        else:
            vary_dose_grid = False
    except KeyError:
        vary_dose_grid = False

    # SVD to DAO calc for cold start (first optimization)
    try:
        if 'Fluence calc' in optimization_dialog.values['input01_fluence_only']:
            fluence_only = True
        else:
            fluence_only = False
    except KeyError:
        fluence_only = False

    # Despite a calculated beam, reset and start over
    try:
        if 'Reset Beams' in optimization_dialog.values['input02_cold_start']:
            reset_beams = True
        else:
            reset_beams = False
    except KeyError:
        reset_beams = False

    # Perform a segment weight optimization after the aperature optimization
    try:
        if 'Perform Segment Weighted optimization' in optimization_dialog.values['input09_segment_weight']:
            segment_weight = True
        else:
            segment_weight = False
    except KeyError:
        segment_weight = False

    # Despite a calculated beam, reset and start over
    try:
        if 'Perform reduce OAR dose before completion' in optimization_dialog.values['input10_reduce_oar']:
            reduce_oar = True
        else:
            reduce_oar = False
    except KeyError:
        reduce_oar = False

    # Despite a calculated beam, reset and start over
    try:
        if 'Target size < 3 cm - limit jaws' in optimization_dialog.values['input11_small_target']:
            small_target = True
        else:
            small_target = False
    except KeyError:
        small_target = False
        #    try:
        #        if 'Perform Segment Weighted optimization' in optimization_dialog.values['input9_segment_weight']:
    optimization_inputs = {
        'initial_max_it': int(optimization_dialog.values['input03_cold_max_iteration']),
        'initial_int_it': int(optimization_dialog.values['input04_cold_interm_iteration']),
        'second_max_it': int(optimization_dialog.values['input05_ws_max_iteration']),
        'second_int_it': int(optimization_dialog.values['input06_ws_interm_iteration']),
        'vary_grid': vary_dose_grid,
        'dose_dim1': 0.5,
        'dose_dim2': 0.4,
        'dose_dim3': 0.3,
        'dose_dim4': 0.2,
        'fluence_only': fluence_only,
        'reset_beams': reset_beams,
        'segment_weight': segment_weight,
        'reduce_oar': reduce_oar,
        'small_target': small_target,
        'n_iterations': int(optimization_dialog.values['input08_n_iterations'])}

    optimize_plan(patient=Patient,
                  case=case,
                  plan=plan,
                  beamset=beamset,
                  **optimization_inputs)


if __name__ == '__main__':
    main()
