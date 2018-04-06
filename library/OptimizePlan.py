""" OptimizePlan
    
    Automatically optimizize the current case, examination, plan, beamset using
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
__date__ = '2018-Apr-06'
__version__ = '1.0.0'
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

from connect import *
import sys

def OptimizePlan(patient, case, plan, beamset, **OptParams):
    #Parameters used for iteration number
    InitialMaximumIteration =  OptParams.get(InitialMaxIt, 60)
    InitialIntermediateIteration = OptParams.get(InitialIntIt, 10)
    SecondMaximumIteration = OptParams.get(SecondMaxIt, 30)
    SecondIntermediateIteration = OptParams.get(SecondIntIt, 15)
    
    # Grid Sizes
    DoseDim1 = OptParams.get(DoseDim1 , 0.5)
    DoseDim2 = OptParams.get(DoseDim2 , 0.4)
    DoseDim3 = OptParams.get(DoseDim3 , 0.3)
    DoseDim4 = OptParams.get(DoseDim4 , 0.2)
    Maximum_Iteration = OptParams.get(NIterations , 12)

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

    try:
         Patient = get_current("Patient")
    except SystemError:
         raise IOError("No Patient loaded. Load patient case and plan.")

    try:
         case = get_current("Case")
    except SystemError:
         raise IOError("No Case loaded. Load patient case and plan.")

    try:
         plan = get_current("Plan")
    except SystemError:
         raise IOError("No plan loaded. Load patient and plan.")

    try: 
         beamset = get_current("BeamSet")
    except SystemError:
         raise IOError("No beamset loaded")

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

    #Turn on important parameters
    plan.PlanOptimizations[OptIndex].OptimizationParameters.DoseCalculation.ComputeFinalDose = True

    # Turn off autoscale
    plan.PlanOptimizations[OptIndex].AutoScaleToPrescription = False

    # Set the Maximum iterations and segmentation iteration
    # to a high number for the initial run
    plan.PlanOptimizations[OptIndex].OptimizationParameters.Algorithm.MaxNumberOfIterations = InitialMaximumIteration
    plan.PlanOptimizations[OptIndex].OptimizationParameters.DoseCalculation.IterationsInPreparationsPhase = InitialIntermediateIteration

    # Try to Set the Gantry Spacing to 2 degrees
    # How many beams are there in this beamset

    while beamsinrange:
      try:
          plan.PlanOptimizations[OptIndex].OptimizationParameters.TreatmentSetupSettings[0].\
              BeamSettings[i].ArcConversionPropertiesPerBeam.EditArcBasedBeamOptimizationSettings(FinalGantrySpacing=2)
    ## Uncomment to automatically set jaw limits
    ##      plan.PlanOptimizations[OptIndex].OptimizationParameters.TreatmentSetupSettings[0].\
    ##          BeamSettings[i].EditBeamOptimizationSettings(
    ##                          JawMotion = "Use limits as max",
    ##                          LeftJaw = X1limit,
    ##                          RightJaw = X2limit,
    ##                          TopJaw = Y2limit,
    ##                          BottomJaw = Y1limit,
    ##                          OptimizationTypes=['SegmentOpt','SegmentMU'])
      
          i += 1
          num_beams = i
     
      except:
          beamsinrange = False


    while Optimization_Iteration != Maximum_Iteration:
         UpdateMessage = 'Current iteration = '+str(Optimization_Iteration)+' of '+ str(Maximum_Iteration)
         print UpdateMessage
         # MessageBox.Show(UpdateMessage)
         if Optimization_Iteration == 2:
         # Change Dose Grid size
            DoseDim = DoseDim1
            with CompositeAction('Set default grid'):
              retval_0 = plan.SetDefaultDoseGrid(VoxelSize={ 'x': DoseDim, 'y': DoseDim, 'z': DoseDim })
              plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
         # CompositeAction ends 
           # Set the Maximum iterations and segmentation iterattion to a lower number for the initial run
            plan.PlanOptimizations[OptIndex].OptimizationParameters.Algorithm.MaxNumberOfIterations = SecondMaximumIteration
            plan.PlanOptimizations[OptIndex].OptimizationParameters.DoseCalculation.IterationsInPreparationsPhase = SecondIntermediateIteration
         elif Optimization_Iteration == 4:
         # Change Dose Grid size
            DoseDim = DoseDim2
            with CompositeAction('Set default grid'):
              retval_0 = plan.SetDefaultDoseGrid(VoxelSize={ 'x': DoseDim, 'y': DoseDim, 'z': DoseDim })
              plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
         # CompositeAction ends 
         elif Optimization_Iteration == 6:
         # Change Dose Grid size
            DoseDim = DoseDim3
            with CompositeAction('Set default grid'):
              retval_0 = plan.SetDefaultDoseGrid(VoxelSize={ 'x': DoseDim, 'y': DoseDim, 'z': DoseDim })
              plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
         # CompositeAction ends 
         elif Optimization_Iteration == 10:
         # Change Dose Grid size
            DoseDim = DoseDim4
            with CompositeAction('Set default grid'):
              retval_0 = plan.SetDefaultDoseGrid(VoxelSize={ 'x': DoseDim, 'y': DoseDim, 'z': DoseDim })
              plan.TreatmentCourse.TotalDose.UpdateDoseGridStructures()
         # CompositeAction ends 
         print("Optimization Number: " + str(Optimization_Iteration))
         plan.PlanOptimizations[OptIndex].RunOptimization()
         Optimization_Iteration += 1

    #Finish with a Reduce OAR Dose Optimization
    print("Running Reduce OAR Optimization" )
    plan.PlanOptimizations[OptIndex].RunReduceOARDoseOptimization




