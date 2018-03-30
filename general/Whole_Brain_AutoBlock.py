""" Whole Brain Autoblock
    Creates the structures required for the auto-whole brain block.
    
    This python script will generate a PTV_WB_xxxx that attempts to capture the whole brain
    block.  It loads, from the MBS, a brain structure that is modified by the user to 
    encompass the extent to which the physician wants inferior coverage.  Then, it looks 
    for existing Lens structures and asks the user to draw them.  


    How To Use: After insertion of S-frame this script is run to generate the blocking 
                structures for a whole brain plan.


    Validation Notes: 
    
    Version Notes: 1.0.0 Original
  
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
__date__ = '01-Feb-2018'
__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '6.0.0'
__maintainer__ = 'One maintainer'
__email__ =  'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = []


from connect import *

patient = get_current("Patient")
case = get_current("Case")
examination = get_current("Examination")

#
# retval_0 is an empty return value, I'm declaring it to avoid an implicit definition
retval_0 = False
#
# Capture the current list of ROI's to avoid saving over them in the future
rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries
#
# Capture the current list of POI's to avoid a crash
pois = case.PatientModel.PointsOfInterest
#
# Look for an existing localization point.  If it doesn't exist, create it
try:
   poi = pois._SimFiducials
except:
   retval_0 = case.PatientModel.CreatePoi(Examination=examination, 
              Point={ 'x': 0, 'y': 0, 'z': 0 },Volume=0 ,Name="SimFiducials",
              Color ="Green", Type="LocalizationPoint")
#
# If Brain exists as a contour, use it for defining the target
try: 
   retval_0 = rois._Brain
   retval_0 = case.PatientModel.CreateRoi(Name="PTV_WB_xxxx", Color="255, 128, 0", Type="Organ", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
   retval_0.SetMarginExpression(SourceRoiName="Brain", MarginSettings={ 
     'Type': "Expand", 'Superior': 0.0, 'Inferior': 0.0, 'Anterior': 0.0, 'Posterior': 0.0, 'Right': 0.0, 'Left': 0.0 })
   retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
# MBS-based loading of brain.  Note this creates a copy if it already exists.
except:
   case.PatientModel.MBSAutoInitializer(MbsRois=[{ 'CaseType': "HeadNeck", 
        'ModelName': "Brain", 'RoiName': "PTV_WB_xxxx", 'RoiColor': "255, 255, 0" }], 
        CreateNewRois=True, Examination=examination, UseAtlasBasedInitialization=True)
   case.PatientModel.AdaptMbsMeshes(Examination=examination, RoiNames=["PTV_WB_xxxx"],
        CustomStatistics=None, CustomSettings=None)
   #
   # Having briefly experimented, 200 iterations seems to get the main features of the 
   # brain volume correct
   case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(Examination=examination,
        CustomStatistics=None, CustomSettings=[{ 'ShapeWeight': 0.5, 'TargetWeight': 1,
        'MaxIterations': 200, 'OnlyRigidAdaptation': False, 'ConvergenceCheck': False }])
#
# Change some of the properties of the MBS-loaded target
with CompositeAction('Apply ROI changes (PTV_WB_xxxx)'):

  case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].Type = "Ptv"

  case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].OrganData.OrganType = "Target"

  # CompositeAction ends 

#
# The user should review the intended treatment volume.
await_user_input('Ensure the PTV_WB_xxxx encompasses the brain and C1 and continue playing the script')


case.PatientModel.MBSAutoInitializer(MbsRois=[{ 'CaseType': "HeadNeck", 'ModelName': 
     "Brain", 'RoiName': "Brain", 'RoiColor': "255, 255, 0" }, { 'CaseType': "HeadNeck", 
     'ModelName': "Eye (Left)", 'RoiName': "Globe_L", 'RoiColor': "255, 128, 0" }, 
     { 'CaseType': "HeadNeck", 'ModelName': "Eye (Right)", 'RoiName': "Globe_R", 
      'RoiColor': "255, 128, 0" }], CreateNewRois=True, Examination=examination, UseAtlasBasedInitialization=True)

case.PatientModel.AdaptMbsMeshes(Examination=examination, RoiNames=["Brain", "Globe_L", "Globe_R"],
     CustomStatistics=None, CustomSettings=None)

#
# Do not override existing contours of Lens
try: 
  a = rois._Lens_L
except:
  retval_0 = case.PatientModel.CreateRoi(Name="Lens_L", Color="Purple", Type="Organ", 
     TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
  # Prompt user to draw
  await_user_input('Draw the LEFT Lens then continue playing the script')

#
# Do not overwrite the contours of the right lens
try: 
  a = rois._Lens_R
except:
  retval_0 = case.PatientModel.CreateRoi(Name="Lens_R", Color="Purple", Type="Organ",
     TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
  # Prompt user to draw
  await_user_input('Draw the RIGHT Lens then continue playing the script')


#
# Check for an External contour, if not present, create one.
try: 
  a = rois._External
except:
    with CompositeAction('Create external (External)'):

      retval_0 = case.PatientModel.CreateRoi(Name="External", Color="Blue", Type="External", 
         TissueName="", RbeCellTypeName=None, RoiMaterial=None)

      retval_0.CreateExternalGeometry(Examination=examination, ThresholdLevel=-250)

      # CompositeAction ends 

#
# Generate lens PRV's if needed
with CompositeAction('Expand (Lens_L)'):
  try:
    a = rois._Lens_L_PRV05
  except:
    retval_0 = case.PatientModel.CreateRoi(Name="Lens_L_PRV05", Color="255, 128, 0", Type="Organ", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].ExcludeFromExport = True
    retval_0.SetMarginExpression(SourceRoiName="Lens_L", MarginSettings={ 'Type': "Expand", 'Superior': 0.5, 'Inferior': 0.5, 'Anterior': 0.5, 'Posterior': 0.5, 'Right': 0.5, 'Left': 0.5 })
    retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 


with CompositeAction('Expand (Lens_R)'):
  try:
    a = rois._Lens_R_PRV05
  except:
    retval_0 = case.PatientModel.CreateRoi(Name="Lens_R_PRV05", Color="255, 128, 0", Type="Organ", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

  case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].ExcludeFromExport = True

  retval_0.SetMarginExpression(SourceRoiName="Lens_R", MarginSettings={ 'Type': "Expand", 'Superior': 0.5, 'Inferior': 0.5, 'Anterior': 0.5, 'Posterior': 0.5, 'Right': 0.5, 'Left': 0.5 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 



with CompositeAction('ROI Algebra (Avoid)'):

  try:
    a = rois._Avoid
  except:
    retval_0 = case.PatientModel.CreateRoi(Name="Avoid", Color="255, 128, 128", Type="Organ", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

  case.PatientModel.RegionsOfInterest['Avoid'].ExcludeFromExport = True

#
# Generate the Avoid volume using the Lens PRV's
  retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["Lens_L_PRV05", "Lens_R_PRV05"], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ExpressionB={ 'Operation': "Union", 'SourceRoiNames': [], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ResultOperation="None", ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 

#
# Generate the block target volume for the brain using 1 cm S/L/R, 0.8 cm Anterior, and 0.5 cm Inferior

with CompositeAction('Expand (PTV_WB_xxxx)'):

  retval_0 = case.PatientModel.CreateRoi(Name="BTV_Brain", Color="128, 0, 64", Type="Ptv", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
  case.PatientModel.RegionsOfInterest['BTV_Brain'].ExcludeFromExport = True

  retval_0.SetMarginExpression(SourceRoiName="PTV_WB_xxxx", MarginSettings={ 'Type': "Expand", 'Superior': 1, 'Inferior': 0.5, 'Anterior': 0.8, 'Posterior': 2, 'Right': 1, 'Left': 1 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 


#
# Expand the target 10 cm inferiorly to create a face block which will be removed from the Flash volume
with CompositeAction('Expand (PTV_WB_xxxx)'):

  retval_0 = case.PatientModel.CreateRoi(Name="Avoid_Face", Color="255, 128, 128", Type="Organ", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)
  case.PatientModel.RegionsOfInterest['Avoid_Face'].ExcludeFromExport = True

  retval_0.SetMarginExpression(SourceRoiName="PTV_WB_xxxx", MarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 10, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 

#
# Generate a 2 cm flash volume ensuring the facial avoidance is used.

with CompositeAction('ROI Algebra (BTV_Flash_20)'):

  retval_0 = case.PatientModel.CreateRoi(Name="BTV_Flash_20", Color="128, 0, 64", Type="Ptv", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

  case.PatientModel.RegionsOfInterest['BTV_Flash_20'].ExcludeFromExport = True

  retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["PTV_WB_xxxx"], 'MarginSettings': { 'Type': "Expand", 'Superior': 2, 'Inferior': 0, 'Anterior': 2, 'Posterior': 2, 'Right': 0, 'Left': 0 } }, ExpressionB={ 'Operation': "Union", 'SourceRoiNames': ["Avoid_Face"], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ResultOperation="Subtraction", ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 

#
# The union of tbe BTV_Brain and BTV_Flash_20 is used for the BTV
with CompositeAction('ROI Algebra (BTV)'):

  retval_0 = case.PatientModel.CreateRoi(Name="BTV", Color="Yellow", Type="Ptv", TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

  case.PatientModel.RegionsOfInterest['BTV'].ExcludeFromExport = True

  retval_0.SetAlgebraExpression(ExpressionA={ 'Operation': "Union", 'SourceRoiNames': ["BTV_Brain", "BTV_Flash_20"], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ExpressionB={ 'Operation': "Intersection", 'SourceRoiNames': [], 'MarginSettings': { 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 } }, ResultOperation="None", ResultMarginSettings={ 'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0 })

  retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

  # CompositeAction ends 






