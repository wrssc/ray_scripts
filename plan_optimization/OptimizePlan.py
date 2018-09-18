""" Automated Plan Optimization
    
    Automatically optimize the current case, examination, plan, beamset using
    input optimization parameters
    
    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are 
           passed to the function as an argument

    Example Usage:
    import OptimizePlan from OptimizePlan 
    InitialMaximumIteration = 60
    InitialIntermediateIteration = 10
    SecondMaximumIteration = 30
    SecondIntermediateIteration = 15
    
    Create_Prvs(case, examination, **HNPRVs)
       

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
__date__ = '2018-Apr-10'
__version__ = '1.0.1'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '7.0.0'
__maintainer__ = 'One maintainer'
__email__ =  'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

# Script Created by RAB Oct 2nd 2017 
# Prerequisites:
# Final Dose should be selected
# 11/9/17 Updated to use current beamset number for optimization 
# 11/27/17 Validation efforts: ran this script for 30+ treatment plans.  No errors beyond those encountered in typical optimization - abayliss
# 11/29/17 Commented out the automatic jaw-limit restriction 
#          as this was required with jaw-tracking on but is no longer needed
# 11/29/17 Turn off auto-scale prior to optimization -ugh
# Added logging

# Fix the import all from connect.
import sys


def make_variable_grid_list(n_iterations, variable_dose_grid):
    # Function will determine, based on the input arguments, which iterations will result in a
    # dose grid change. The index of the list is the iteration, and the value is the grid_size
    # Usage:
    #
    #  variable_dose_grid = {
    #         'delta_grid': [0.4,
    #                        0.3,
    #                        0.25,
    #                        0.2],
    #         'grid_adjustment_iteration': [0,
    #                                       int(n_its / 2),
    #                                       int(3 * n_its / 4),
    #                                       int(n_its - 1)]}
    #
    # for index, grid_size in enumerate(change_grid):
    #     if grid_size != 0:
    #         print "Iteration:{}, change grid to {}".format(index+1,grid_size)
    #     else:
    #         print "Iteration:{}, No change to grid".format(index+1)
    #

    # Get rid of the hard-coding of these dict elements at some point
    change_grid = []
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
    else:
        for iteration in range(0, n_iterations - 1):
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

def OptimizePlan(patient, case, plan, beamset, **optimization_inputs):
    import logging
    import UserInterface


    #Parameters used for iteration number
    initial_maximum_iteration =  optimization_inputs.get('InitialMaxIt', 60)
    initial_intermediate_iteration = optimization_inputs.get('InitialIntIt', 10)
    second_maximum_iteration = optimization_inputs.get('SecondMaxIt', 30)
    second_intermediate_iteration = optimization_inputs.get('SecondIntIt', 15)

    vary_grid = optimization_inputs.get('vary_grid', False)
    # Grid Sizes
    dose_dim1 = optimization_inputs.get('dose_dim1', 0.5)
    dose_dim2 = optimization_inputs.get('dose_dim2', 0.4)
    dose_dim3 = optimization_inputs.get('dose_dim3', 0.3)
    dose_dim4 = optimization_inputs.get('dose_dim4', 0.2)
    maximum_iteration = optimization_inputs.get('NIterations', 12)
    svd_only = optimization_inputs.get('svd_only', False)
    gantry_spacing = optimization_inputs.get('gantry_spacing', 2)

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


    print 'initial_maximum_iteration TEST = '+str(initial_maximum_iteration)
    print 'initial_intermediate_iteration ='+str(initial_intermediate_iteration)
    print 'second_maximum_iteration ='+str(second_maximum_iteration)
    print 'second_intermediate_iteration = '+str(second_intermediate_iteration)
    print 'dose_dim1 ='+str(dose_dim1)
    print 'dose_dim2='+str(dose_dim2)
    print 'dose_dim3='+str(dose_dim3)
    print 'dose_dim4='+str(dose_dim4)
    print 'maximum_iteration=',str(maximum_iteration)

    # Making the variable status script, arguably move to main()
    status_steps = ['Initializing optimization']
    for i in range(maximum_iteration)
        ith_step = 'Executing Iteration:' + str(i+1)
        status_steps.append([ith_step])
    status_steps.append(['Reduce OAR Dose'])

    # Change the status steps to indicate each iteration
    status = UserInterface.ScriptStatus(
        steps=status_steps,
        docstring=__doc__,
        help=__help__)

    status.next_step(text='Setting optimization parameters, gantry spacing')
    logging.debug('Set some variables like Niterations, Nits={}'.format(maximum_iteration))
    # Maximum Jaw Sizes
    X1limit = -15
    X2limit = 15
    Y1limit = -19
    Y2limit = 19

    # Variable definitions
    i = 0
    beamsinrange = True
    num_beams = 0 
    OptIndex = 0 
    Optimization_Iteration = 0

    
    # Find current Beamset Number and determine plan optimization
    BeamSetName = beamset.DicomPlanLabel
    OptIndex = 0
    IndexNotFound = True
    # In RS, OptimizedBeamSets objects are keyed using the DicomPlanLabel, or Beam Set name.
    # Because the key to the OptimizedBeamSets presupposes the user knows the PlanOptimizations index
    # this while loop looks for the PlanOptimizations index needed below by searching for a key 
    # that matches the BeamSet DicomPlanLabel
    while IndexNotFound:
         try:
              OptName = plan.PlanOptimizations[OptIndex].OptimizedBeamSets[beamset.DicomPlanLabel].DicomPlanLabel
              IndexNotFound = False
         except SystemError:
              IndexNotFound = True
              OptIndex += 1
    # Found our index.  We will use a shorthand for the remainder of the code
    plan_optimization = plan.PlanOptimizations[OptIndex].OptimizationParameters


    #Turn on important parameters
    plan_optimization.DoseCalculation.ComputeFinalDose = True

    # Turn off autoscale
    plan.PlanOptimizations[OptIndex].AutoScaleToPrescription = False

    # Set the Maximum iterations and segmentation iteration
    # to a high number for the initial run
    plan_optimization.Algorithm.MaxNumberOfIterations = initial_maximum_iteration
    plan_optimization.DoseCalculation.IterationsInPreparationsPhase = initial_intermediate_iteration

    # Try to Set the Gantry Spacing to 2 degrees
    # How many beams are there in this beamset
    # Set the control point spacing
    treatment_setup_settings = plan_optimization.TreatmentSetupSettings[0]
    # Note: pretty worried about the hard-coded zero above. I don't know when it gets incremented
    for beams in treatment_setup_settings.BeamSettings:
        beams.ArcConversionPropertiesPerBeam.EditArcBasedBeamOptimizationSettings(FinalGantrySpacing=2)
    # while beamsinrange:
    #  try:
    #      plan.PlanOptimizations[OptIndex].OptimizationParameters.TreatmentSetupSettings[0].\
    #          BeamSettings[i].ArcConversionPropertiesPerBeam.EditArcBasedBeamOptimizationSettings(FinalGantrySpacing=2)
    ## Uncomment to automatically set jaw limits
    ##      plan.PlanOptimizations[OptIndex].OptimizationParameters.TreatmentSetupSettings[0].\
    ##          BeamSettings[i].EditBeamOptimizationSettings(
    ##                          JawMotion = "Use limits as max",
    ##                          LeftJaw = X1limit,
    ##                          RightJaw = X2limit,
    ##                          TopJaw = Y2limit,
    ##                          BottomJaw = Y1limit,
    ##                          OptimizationTypes=['SegmentOpt','SegmentMU'])
    #
    #      i += 1
    #      num_beams = i
    #
    #  except:
    #      beamsinrange = False

    # Reset
    plan.PlanOptimizations[OptIndex].ResetOptimization()


    if svd_only:
        # SVD only is the quick and dirty way of dialing in all necessary elements for the calc
        plan_optimization.Algorithm.MaxNumberOfIterations = 999
        plan_optimization.DoseCalculation.IterationsInPreparationsPhase = 999
        plan.PlanOptimizations[OptIndex].RunOptimization()

    else:
        while Optimization_Iteration != maximum_iteration:
             print 'Current iteration = {} of {}'.format(Optimization_Iteration,maximum_iteration)
             status.next_step(text='Iterating....')

             # If the change_dose_grid list has a non-zero element change the dose grid
             if change_dose_grid[Optimization_Iteration] != 0:
                 DoseDim = change_dose_grid[Optimization_Iteration]
                 with CompositeAction('Set default grid'):
                     retval_0 = plan.SetDefaultDoseGrid(
                         VoxelSize={
                             'x': DoseDim,
                             'y': DoseDim,
                             'z': DoseDim})
                     plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()

             plan.PlanOptimizations[OptIndex].RunOptimization()
             Optimization_Iteration += 1
             print "Optimization Number: {} completed".format(Optimization_Iteration)
             # Set the Maximum iterations and segmentation iteration to a lower number for the initial run
             plan_optimization.Algorithm.MaxNumberOfIterations = second_maximum_iteration
             plan_optimization.DoseCalculation.IterationsInPreparationsPhase = second_intermediate_iteration


    #Finish with a Reduce OAR Dose Optimization
    print "Running Reduce OAR Optimization"
    plan.PlanOptimizations[OptIndex].RunReduceOARDoseOptimization

def main():
    import connect
    import UserInterface

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

    # OPTIONS DIALOG
    #  Users will select use of:
    #
    # Maximum number of iterations for the first optimization
    optimization_dialog = UserInterface.InputDialog(
        title='Optimization Inputs',
        inputs={
            'input1_cold_max_iteration': 'Maximum number of iterations for initial optimization',
            'input2_cold_interm_iteration': 'Intermediate iteration for svd to aperture conversion',
            'input3_ws_max_iteration': 'Maximum iteration used in warm starts ',
            'input4_ws_interm_iteration': 'Intermediate iteration used in warm starts',
            'input5_vary_dose_grid': 'Start with large grid, and decrease gradually',
            'input6_svd_only': 'svd calculation only, for dialing in parameters',
            'input7_niterations': 'Number of Iterations'},
        datatype={
            'input5_vary_dose_grid': 'check'},
        initial={'input1_cold_max_iteration': '50',
                 'input2_cold_interm_iteration': '10',
                 'input3_ws_max_iteration': '35',
                 'input4_ws_interm_iteration': '5',
                 'input7_niterations': '4'},
        options={
            'input5_vary_dose_grid': ['Variable Dose Grid'],
            'input6_svd_only': ['svd calc']},
        required=[])
    print optimization_dialog.show()

    # DATA PARSING FOR THE OPTIMIZATION MENU
    # Determine if variable dose grid is selected
    try:
        if 'Variable Dose Grid' in optimization_dialog.values['input5_vary_dose_grid']:
            vary_dose_grid = True
        else:
            vary_dose_grid = False
    except KeyError:
        vary_dose_grid = False

    # SVD to DAO calc for cold start (first optimization)
    try:
        if 'svd calc' in optimization_dialog.values['input6_svd_only']:
            svd_only = True
        else:
            svd_only = False
    except KeyError:
        svd_only = False

    OptParams = {
    'InitialMaxIt' : int(optimization_dialog.values['input_cold_max_iteration']),
    'InitialIntIt' : int(optimization_dialog.values['input2_cold_interm_iteration']),
    'SecondMaxIt' : int(optimization_dialog.values['input3_ws_max_iteration']),
    'SecondIntIt' : int(optimization_dialog.values['input4_ws_interm_iteration']),
    'vary_grid': vary_dose_grid,
    'DoseDim1' : 0.45,
    'DoseDim2' : 0.35,
    'DoseDim3' : 0.35,
    'DoseDim4' : 0.22,
    'svd_only': svd_only
    'NIterations' : int(optimization_dialog.values['input7_n_iterations'])}
    OptimizePlan(Patient, case, plan, beamset, **OptParams)
#    OptimizePlan(Patient, case, plan, beamset)


if __name__=='__main__':
    main()




















