""" Whole Brain AutoBlock

    Creates the structures required for the auto-whole brain block.
    
    This python script will generate a PTV_WB_xxxx that attempts to capture the whole brain
    contour to the C1 interface.  In the first iteration, this will simply generate the 
    structures that will be used to populate the UW Template.  In future iterations we 
    will be updating this script to load beam templates and create the actual plan.   

    How To Use: After insertion of S-frame this script is run to generate the blocking 
                structures for a whole brain plan


    Validation Notes: 
    
    Version Notes: 1.0.0 Original
    1.0.1 Hot Fix to apparent error in version 7
  
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
__raystation__ = '7.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = []

import connect


def main():
    patient = connect.get_current("Patient")
    case = connect.get_current("Case")
    examination = connect.get_current("Examination")

    # Capture the current list of ROI's to avoid saving over them in the future
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries

    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest

    if 'SimFiducials' in pois:
        print 'Sim fiducial point found'
    else:
        case.PatientModel.CreatePoi(Examination=examination,
                                    Point={'x': 0,
                                           'y': 0,
                                           'z': 0},
                                    Volume=0,
                                    Name="SimFiducials",
                                    Color="Green",
                                    Type="LocalizationPoint")

    case.PatientModel.MBSAutoInitializer(
        MbsRois=[{'CaseType': "HeadNeck", 'ModelName': "Brain", 'RoiName': "PTV_WB_xxxx", 'RoiColor': "255, 255, 0"}],
        CreateNewRois=True, Examination=examination, UseAtlasBasedInitialization=True)

    case.PatientModel.AdaptMbsMeshes(Examination=examination, RoiNames=["PTV_WB_xxxx"], CustomStatistics=None,
                                     CustomSettings=None)

    case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(Examination=examination, CustomStatistics=None,
                                                                    CustomSettings=[
                                                                        {'ShapeWeight': 0.5, 'TargetWeight': 1,
                                                                         'MaxIterations': 200,
                                                                         'OnlyRigidAdaptation': False,
                                                                         'ConvergenceCheck': False}])

    with CompositeAction('Apply ROI changes (PTV_WB_xxxx)'):

        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].Type = "Ptv"

        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].OrganData.OrganType = "Target"

        # CompositeAction ends

    await_user_input('Ensure the PTV_WB_xxxx encompasses the brain and C1 and continue playing the script')

    case.PatientModel.MBSAutoInitializer(
        MbsRois=[{'CaseType': "HeadNeck", 'ModelName': "Brain", 'RoiName': "Brain", 'RoiColor': "255, 255, 0"},
                 {'CaseType': "HeadNeck", 'ModelName': "Eye (Left)", 'RoiName': "Globe_L", 'RoiColor': "255, 128, 0"},
                 {'CaseType': "HeadNeck", 'ModelName': "Eye (Right)", 'RoiName': "Globe_R", 'RoiColor': "255, 128, 0"}],
        CreateNewRois=True, Examination=examination, UseAtlasBasedInitialization=True)

    case.PatientModel.AdaptMbsMeshes(Examination=examination, RoiNames=["Brain", "Globe_L", "Globe_R"],
                                     CustomStatistics=None, CustomSettings=None)

    try:
        a = rois._Lens_L
    except:
        retval_0 = case.PatientModel.CreateRoi(Name="Lens_L", Color="Purple", Type="Organ", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)
        await_user_input('Draw the LEFT Lens then continue playing the script')

    try:
        a = rois._Lens_R
    except:
        retval_0 = case.PatientModel.CreateRoi(Name="Lens_R", Color="Purple", Type="Organ", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)
        await_user_input('Draw the RIGHT Lens then continue playing the script')

    with CompositeAction('Create external (External)'):

        retval_0 = case.PatientModel.CreateRoi(Name="External", Color="Blue", Type="External", TissueName="",
                                               RbeCellTypeName=None, RoiMaterial=None)

        retval_0.CreateExternalGeometry(Examination=examination, ThresholdLevel=-250)

        # CompositeAction ends

    with CompositeAction('Expand (Lens_L)'):
        try:
            a = rois._Lens_L_PRV05
        except:
            retval_0 = case.PatientModel.CreateRoi(Name="Lens_L_PRV05", Color="255, 128, 0", Type="Organ",
                                                   TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

        case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].ExcludeFromExport = True
        retval_0.SetMarginExpression(SourceRoiName="Lens_L",
                                     MarginSettings={'Type': "Expand", 'Superior': 0.5, 'Inferior': 0.5,
                                                     'Anterior': 0.5, 'Posterior': 0.5, 'Right': 0.5, 'Left': 0.5})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('Expand (Lens_R)'):
        try:
            a = rois._Lens_R_PRV05
        except:
            retval_0 = case.PatientModel.CreateRoi(Name="Lens_R_PRV05", Color="255, 128, 0", Type="Organ",
                                                   TissueName=None, RbeCellTypeName=None, RoiMaterial=None)

        case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].ExcludeFromExport = True

        retval_0.SetMarginExpression(SourceRoiName="Lens_R",
                                     MarginSettings={'Type': "Expand", 'Superior': 0.5, 'Inferior': 0.5,
                                                     'Anterior': 0.5, 'Posterior': 0.5, 'Right': 0.5, 'Left': 0.5})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('ROI Algebra (Avoid)'):

        try:
            a = rois._Avoid
        except:
            retval_0 = case.PatientModel.CreateRoi(Name="Avoid", Color="255, 128, 128", Type="Organ", TissueName=None,
                                                   RbeCellTypeName=None, RoiMaterial=None)

        case.PatientModel.RegionsOfInterest['Avoid'].ExcludeFromExport = True

        retval_0.SetAlgebraExpression(
            ExpressionA={'Operation': "Union", 'SourceRoiNames': ["Lens_L_PRV05", "Lens_R_PRV05"],
                         'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0,
                                            'Posterior': 0, 'Right': 0, 'Left': 0}},
            ExpressionB={'Operation': "Union", 'SourceRoiNames': [],
                         'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0,
                                            'Posterior': 0, 'Right': 0, 'Left': 0}}, ResultOperation="None",
            ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0,
                                  'Right': 0, 'Left': 0})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('Expand (PTV_WB_xxxx)'):

        retval_0 = case.PatientModel.CreateRoi(Name="BTV_Brain", Color="128, 0, 64", Type="Ptv", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)
        case.PatientModel.RegionsOfInterest['BTV_Brain'].ExcludeFromExport = True

        retval_0.SetMarginExpression(SourceRoiName="PTV_WB_xxxx",
                                     MarginSettings={'Type': "Expand", 'Superior': 1, 'Inferior': 0.5, 'Anterior': 0.8,
                                                     'Posterior': 2, 'Right': 1, 'Left': 1})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('Expand (PTV_WB_xxxx)'):

        retval_0 = case.PatientModel.CreateRoi(Name="Avoid_Face", Color="255, 128, 128", Type="Organ", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)
        case.PatientModel.RegionsOfInterest['Avoid_Face'].ExcludeFromExport = True

        retval_0.SetMarginExpression(SourceRoiName="PTV_WB_xxxx",
                                     MarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 10, 'Anterior': 0,
                                                     'Posterior': 0, 'Right': 0, 'Left': 0})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('ROI Algebra (BTV_Flash_20)'):

        retval_0 = case.PatientModel.CreateRoi(Name="BTV_Flash_20", Color="128, 0, 64", Type="Ptv", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)

        case.PatientModel.RegionsOfInterest['BTV_Flash_20'].ExcludeFromExport = True

        retval_0.SetAlgebraExpression(ExpressionA={'Operation': "Union", 'SourceRoiNames': ["PTV_WB_xxxx"],
                                                   'MarginSettings': {'Type': "Expand", 'Superior': 2, 'Inferior': 0,
                                                                      'Anterior': 2, 'Posterior': 2, 'Right': 0,
                                                                      'Left': 0}},
                                      ExpressionB={'Operation': "Union", 'SourceRoiNames': ["Avoid_Face"],
                                                   'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0,
                                                                      'Anterior': 0, 'Posterior': 0, 'Right': 0,
                                                                      'Left': 0}}, ResultOperation="Subtraction",
                                      ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0,
                                                            'Anterior': 0, 'Posterior': 0, 'Right': 0, 'Left': 0})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends

    with CompositeAction('ROI Algebra (BTV)'):

        retval_0 = case.PatientModel.CreateRoi(Name="BTV", Color="Yellow", Type="Ptv", TissueName=None,
                                               RbeCellTypeName=None, RoiMaterial=None)

        case.PatientModel.RegionsOfInterest['BTV'].ExcludeFromExport = True

        retval_0.SetAlgebraExpression(
            ExpressionA={'Operation': "Union", 'SourceRoiNames': ["BTV_Brain", "BTV_Flash_20"],
                         'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0,
                                            'Posterior': 0, 'Right': 0, 'Left': 0}},
            ExpressionB={'Operation': "Intersection", 'SourceRoiNames': [],
                         'MarginSettings': {'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0,
                                            'Posterior': 0, 'Right': 0, 'Left': 0}}, ResultOperation="None",
            ResultMarginSettings={'Type': "Expand", 'Superior': 0, 'Inferior': 0, 'Anterior': 0, 'Posterior': 0,
                                  'Right': 0, 'Left': 0})

        retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")

        # CompositeAction ends


if __name__ == '__main__':
    main()
