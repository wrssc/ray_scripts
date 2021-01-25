""" Automated Plan - Whole Brain

    Creates the structures required for the auto-whole brain block.

    This python script will generate a PTV_WB_xxxx that attempts to capture the whole brain
    contour to the C1 interface.  In the first iteration, this will simply generate the
    structures that will be used to populate the UW Template.  In future iterations we
    will be updating this script to load beam templates and create the actual plan.

    How To Use: After insertion of S-frame this script is run to generate the blocking
                structures for a whole brain plan

    TODO: Get rid of the second plan - it is only for correcting the GUI and can be dumped in
            RS8
    TODO: Add timing measurements to the planning process
    TODO: Eliminate S-frame use and extend dose grid based on BTV limits
    TODO: Add clinical goals

    Validation Notes:
    Test Patient: MR# ZZUWQA_ScTest_30Dec2020, Name: Script_Testing^Automated Plan - Whole Brain

    Version Notes: 1.0.0 Original
    1.0.1 Hot Fix to apparent error in version 7 (related to connect being used instead of a
            full import)
            Added functionality for making a plan, which TC is testing.
            Added automatic loading of couch along with a prompt to ask the user to move it.
    1.0.2 Added features after Dose reviewed the automatic generation of the plans.
          eliminated median dose prescription.  added 8.0 compliant language on the s-frame
    1.0.3 Added a secondary plan feature to correct the RS7 GUI bug that does not update the
            gui if the first plan is created with a script.
    1.0.4 Changed the export structure settings to reflect the new required method in RS 8.0a
            and up.
    1.0.5 Repaired local template structures to reflect S-Frame location
    1.1.0 Update to Python 3.6 and RS 10A SP1

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
__version__ = '1.0.5'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8B.SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import connect
import logging
import UserInterface
import random
import sys
import BeamOperations
import PlanOperations
import StructureOperations


def check_external(roi_list):
    if any(roi.OfRoi.Type == 'External' for roi in roi_list):
        logging.debug('External contour designated')
        return True
    else:
        logging.debug('No external contour designated')
        connect.await_user_input(
            'No External contour type designated. Give a contour an External type and continue script.')
        if any(roi.OfRoi.Type == 'External' for roi in roi_list):
            logging.debug('No external contour designated after prompt recommend exit')
            return False


def check_structure_exists(case, structure_name, roi_list, option):
    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if option == 'Delete':
            case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
            logging.warning("check_structure_exists: " +
                            structure_name + 'found - deleting and creating')
        elif option == 'Check':
            connect.await_user_input(
                'Contour {} Exists - Verify its accuracy and continue script'.format(
                    structure_name))
        return True
    else:
        logging.info('check_structure_exists: '
                     'Structure {} not found, and will be created'.format(structure_name))
        return False


def main():
    # Script will run through the following steps.  We have a logical inconsistency here with making a plan
    # this is likely an optional step
    status = UserInterface.ScriptStatus(
        steps=['SimFiducials point declaration',
               'Making the target',
               'Verify PTV_WB_xxxx coverage',
               'User Inputs Plan Information',
               'Regions at Risk Generation/Validation',
               'Support Structure Loading',
               'Target (BTV) Generation',
               'Plan Generation (Optional)'],
        docstring=__doc__,
        help=__help__)

    # UW Inputs
    # If machines names change they need to be modified here:
    institution_inputs_machine_name = ['TrueBeamSTx', 'TrueBeam']
    # The s-frame object currently belongs to an examination on rando named: "Supine Patient"
    # if that changes the s-frame load will fail
    institution_inputs_support_structures_examination = "Supine Patient"
    institution_inputs_support_structure_template = "UW Support"
    institution_inputs_source_roi_names = ['S-frame']
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        patient_db = connect.get_current('PatientDB')
    except:
        UserInterface.WarningBox('This script requires a patient, case, and exam to be loaded')
        sys.exit('This script requires a patient, case, and exam to be loaded')

    # Capture the current list of ROI's to avoid saving over them in the future
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries

    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest

    visible_structures = ['PTV_WB_xxxx', 'Lens_L', 'Lens_R']
    invisible_stuctures = [
        'Eye_L',
        'Eye_R',
        'External',
        'S-frame',
        'Avoid',
        'Avoid_Face',
        'Lens_R_PRV05',
        'Lens_L_PRV05',
        'BTV_Brain',
        'BTV_Flash_20',
        'BTV',
        'Brain']
    export_exclude_structs = [
        'Eye_L',
        'Eye_R',
        'Avoid',
        'Avoid_Face',
        'Lens_R_PRV05',
        'Lens_L_PRV05',
        'BTV_Brain',
        'BTV_Flash_20',
        'BTV']
    # Try navigating to the points tab
    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['POI tools'].Select()
        ui.ToolPanel.TabItem['POIs'].Select()
    except:
        logging.debug("Could not click on the patient modeling window")

    # Look for the sim point, if not create a point
    sim_point_found = any(poi.Name == 'SimFiducials' for poi in pois)
    if sim_point_found:
        logging.warning("POI SimFiducials Exists")
        status.next_step(text="SimFiducials Point found, ensure that it is placed properly")
        connect.await_user_input(
            'Ensure Correct placement of the SimFiducials Point and continue script.')
    else:
        poi_status = StructureOperations.create_poi(
            case=case, exam=examination, coords=[0., 0., 0.],
            name="SimFiducials",color="Green", rs_type='Localization_Point')
        # case.PatientModel.CreatePoi(Examination=examination,
        #                            Point={'x': 0,
        #                                   'y': 0,
        #                                   'z': 0},
        #                            Volume=0,
        #                            Name="SimFiducials",
        #                            Color="Green",
        #                            Type="LocalizationPoint")
        status.next_step(text="SimFiducials POI created, ensure that it is placed properly")
        connect.await_user_input(
            'Ensure Correct placement of the SimFiducials Point and continue script.')

    # Generate the target based on an MBS brain contour
    status.next_step(text="The PTV_WB_xxxx target is being generated")
    if not check_structure_exists(case=case, structure_name='PTV_WB_xxxx', roi_list=rois,
                                  option='Check'):
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Brain",
                      'RoiName': "PTV_WB_xxxx",
                      'RoiColor': "255, 255, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)

        case.PatientModel.AdaptMbsMeshes(Examination=examination,
                                         RoiNames=["PTV_WB_xxxx"],
                                         CustomStatistics=None,
                                         CustomSettings=None)

        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(
            Examination=examination,
            CustomStatistics=None,
            CustomSettings=[{'ShapeWeight': 0.5,
                             'TargetWeight': 0.7,
                             'MaxIterations': 70,
                             'OnlyRigidAdaptation': False,
                             'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].AdaptMbsMesh(
            Examination=examination,
            CustomStatistics=None,
            CustomSettings=[{'ShapeWeight': 0.5,
                             'TargetWeight': 0.5,
                             'MaxIterations': 50,
                             'OnlyRigidAdaptation': False,
                             'ConvergenceCheck': False}])
        status.next_step(text="The target was auto-generated based on the brain," +
                              " and the computer is not very smart. Check the PTV_WB_xxxx carefully")
    else:
        status.next_step(text="Existing target was used. Check the PTV_WB_xxxx carefully")

    case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].Type = "Ptv"

    case.PatientModel.RegionsOfInterest['PTV_WB_xxxx'].OrganData.OrganType = "Target"

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['ROI tools'].Select()
        ui.ToolPanel.TabItem['ROIs'].Select()
    except:
        logging.debug("Could not click on the patient modeling window")

    connect.await_user_input(
        'Ensure the PTV_WB_xxxx encompasses the brain and C1 and continue playing the script')

    # Get some user data
    status.next_step(text="Complete plan information - check the TPO for doses " +
                          "and ARIA for the treatment machine")
    # This dialog grabs the relevant parameters to generate the whole brain plan
    input_dialog = UserInterface.InputDialog(
        inputs={
            'input0_make_plan': 'Create the RayStation Plan',
            'input1_plan_name': 'Enter the Plan Name, typically Brai_3DC_R0A0',
            'input2_number_fractions': 'Enter the number of fractions',
            'input3_dose': 'Enter total dose in cGy',
            'input4_choose_machine': 'Choose Treatment Machine'
        },
        title='Whole Brain Plan Input',
        datatype={'input0_make_plan': 'check',
                  'input4_choose_machine': 'combo'
                  },
        initial={
            'input0_make_plan': ['Make Plan'],
            'input1_plan_name': 'Brai_3DC_R0A0',
        },
        options={'input0_make_plan': ['Make Plan'],
                 'input4_choose_machine': institution_inputs_machine_name,
                 },
        required=['input2_number_fractions',
                  'input3_dose',
                  'input4_choose_machine'])

    # Launch the dialog
    response = input_dialog.show()
    # Close on cancel
    if response == {}:
        logging.info('autoplan whole brain cancelled by user')
        sys.exit('autoplan whole brain cancelled by user')
    else:
        logging.debug('User selected {} for make plan'.format(
            input_dialog.values['input0_make_plan']))

    # Parse the outputs
    # User selected that they want a plan-stub made
    if 'Make Plan' in input_dialog.values['input0_make_plan']:
        make_plan = True
    else:
        make_plan = False
    plan_name = input_dialog.values['input1_plan_name']
    number_of_fractions = float(input_dialog.values['input2_number_fractions'])
    total_dose = float(input_dialog.values['input3_dose'])
    plan_machine = input_dialog.values['input4_choose_machine']

    ## patient.Save()

    # MBS generate the globes. Manually draw lenses
    status.next_step(text="Regions at risk will be created including Eyes, Lenses, and Brain.")
    brain_exists = check_structure_exists(case=case,
                                          structure_name='Brain',
                                          roi_list=rois,
                                          option='Check')
    if not brain_exists:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Brain",
                      'RoiName': "Brain",
                      'RoiColor': "255, 255, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Brain'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.0,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
    if any(roi.OfRoi.Name == 'Eye_L' for roi in rois):
        connect.await_user_input('Eye_L Contour Exists - Verify its accuracy and continue script')
    else:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Eye (Left)",
                      'RoiName': "Eye_L",
                      'RoiColor': "255, 128, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Eye_L'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 2.0,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['Eye_L'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.25,
                'TargetWeight': 0.75,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
    if any(roi.OfRoi.Name == 'Eye_R' for roi in rois):
        connect.await_user_input('Eye_R Contour Exists - Verify its accuracy and continue script')
    else:
        case.PatientModel.MBSAutoInitializer(
            MbsRois=[{'CaseType': "HeadNeck",
                      'ModelName': "Eye (Right)",
                      'RoiName': "Eye_R",
                      'RoiColor': "255, 128, 0"}],
            CreateNewRois=True,
            Examination=examination,
            UseAtlasBasedInitialization=True)
        case.PatientModel.RegionsOfInterest['Eye_R'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 2.0,
                'TargetWeight': 1,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])
        case.PatientModel.RegionsOfInterest['Eye_R'].AdaptMbsMesh(
            Examination=examination,
            CustomSettings=[{
                'ShapeWeight': 4.25,
                'TargetWeight': 1,
                'MaxIterations': 50,
                'OnlyRigidAdaptation': False,
                'ConvergenceCheck': False}])

    if not check_structure_exists(case=case, structure_name='Lens_L', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name='Lens_L',
                                    Color="Purple",
                                    Type="Organ",
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        connect.await_user_input('Draw the LEFT Lens then continue playing the script')

    if not check_structure_exists(case=case, structure_name='Lens_R', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name="Lens_R",
                                    Color="Purple",
                                    Type="Organ",
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        connect.await_user_input('Draw the RIGHT Lens then continue playing the script')

    if not check_structure_exists(case=case, structure_name='External', roi_list=rois,
                                  option='Check'):
        case.PatientModel.CreateRoi(Name="External",
                                    Color="Blue",
                                    Type="External",
                                    TissueName="",
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)
        case.PatientModel.RegionsOfInterest['External'].CreateExternalGeometry(
            Examination=examination,
            ThresholdLevel=-250)
    else:
        if not check_external(rois):
            logging.warning('No External-Type Contour designated-Restart'
                            ' script after choosing External-Type')
            sys.exit

    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Lens_L_PRV05'):
        logging.info('Lens_L_PRV05 not found, generating from expansion')

    case.PatientModel.CreateRoi(
        Name="Lens_L_PRV05",
        Color="255, 128, 0",
        Type="Avoidance",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].SetMarginExpression(
        SourceRoiName="Lens_L",
        MarginSettings={'Type': "Expand",
                        'Superior': 0.5,
                        'Inferior': 0.5,
                        'Anterior': 0.5,
                        'Posterior': 0.5,
                        'Right': 0.5,
                        'Left': 0.5})
    case.PatientModel.RegionsOfInterest['Lens_L_PRV05'].UpdateDerivedGeometry(
        Examination=examination, Algorithm="Auto")

    # The Lens_R prv will always be "remade"
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Lens_R_PRV05'):
        logging.info('Lens_R_PRV05 not found, generating from expansion')

    case.PatientModel.CreateRoi(
        Name="Lens_R_PRV05",
        Color="255, 128, 0",
        Type="Avoidance",
        TissueName=None,
        RbeCellTypeName=None,
        RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].SetMarginExpression(
        SourceRoiName="Lens_R",
        MarginSettings={'Type': "Expand",
                        'Superior': 0.5,
                        'Inferior': 0.5,
                        'Anterior': 0.5,
                        'Posterior': 0.5,
                        'Right': 0.5,
                        'Left': 0.5})
    case.PatientModel.RegionsOfInterest['Lens_R_PRV05'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='Avoid'):
        logging.info('Avoid not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="Avoid",
                                Color="255, 128, 128",
                                Type="Avoidance",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Avoid'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["Lens_L_PRV05",
                                        "Lens_R_PRV05"],
                     'MarginSettings': {
                         'Type': "Expand",
                         'Superior': 0,
                         'Inferior': 0,
                         'Anterior': 0,
                         'Posterior': 0,
                         'Right': 0,
                         'Left': 0}},
        ExpressionB={'Operation': "Union",
                     'SourceRoiNames': [],
                     'MarginSettings': {
                         'Type': "Expand",
                         'Superior': 0,
                         'Inferior': 0,
                         'Anterior': 0,
                         'Posterior': 0,
                         'Right': 0,
                         'Left': 0}},
        ResultOperation="None",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})
    case.PatientModel.RegionsOfInterest['Avoid'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # S - frame loading
    status.next_step(text="Roi contouring complete, loading patient immobilization.")
    # Load the S-frame into the current scan based on the structure template input above.
    # This operation is not supported in RS7, however, when we convert to RS8, this should work
    try:
        if check_structure_exists(case=case, roi_list=rois, option='Check',
                                  structure_name='S-frame'):
            logging.info('S-frame found, bugging user')
            connect.await_user_input(
                'S-frame present. ' +
                'Ensure placed correctly then continue script')
        else:
            support_template = patient_db.LoadTemplatePatientModel(
                templateName=institution_inputs_support_structure_template,
                lockMode='Read')

            case.PatientModel.CreateStructuresFromTemplate(
                SourceTemplate=support_template,
                SourceExaminationName=institution_inputs_support_structures_examination,
                SourceRoiNames=institution_inputs_source_roi_names,
                SourcePoiNames=[],
                AssociateStructuresByName=True,
                TargetExamination=examination,
                InitializationOption='AlignImageCenters'
            )
            connect.await_user_input(
                'S-frame automatically loaded. ' +
                'Ensure placed correctly then continue script')

        status.next_step(
            text='S-frame has been loaded. Ensure its alignment and continue the script.')
    except Exception:
        logging.warning('Support structure failed to load and was not found')
        status.next_step(text='S-frame failed to load and was not found. ' +
                              'Load manually and continue script.')
        connect.await_user_input(
            'S-frame failed to load and was not found. ' +
            'Ensure it is loaded and placed correctly then continue script')

    # Creating planning structures for treatment and protect
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='BTV_Brain'):
        logging.info('BTV_Brain not found, generating from expansion')

    status.next_step(text='Building planning structures')

    case.PatientModel.CreateRoi(Name="BTV_Brain", Color="128, 0, 64", Type="Ptv", TissueName=None,
                                RbeCellTypeName=None, RoiMaterial=None)

    case.PatientModel.RegionsOfInterest['BTV_Brain'].SetMarginExpression(
        SourceRoiName="PTV_WB_xxxx",
        MarginSettings={'Type': "Expand",
                        'Superior': 1,
                        'Inferior': 0.5,
                        'Anterior': 0.8,
                        'Posterior': 2,
                        'Right': 1,
                        'Left': 1})
    case.PatientModel.RegionsOfInterest['BTV_Brain'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # Avoid_Face - creates a block that will avoid treating the face
    # This contour extends down 10 cm from the brain itself.  Once this is subtracted
    # from the brain - this will leave only the face
    if not check_structure_exists(case=case,
                                  roi_list=rois,
                                  option='Delete',
                                  structure_name='Avoid_Face'):
        logging.info('Avoid_Face not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="Avoid_Face",
                                Color="255, 128, 128",
                                Type="Organ",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['Avoid_Face'].SetMarginExpression(
        SourceRoiName="PTV_WB_xxxx",
        MarginSettings={'Type': "Expand",
                        'Superior': 0,
                        'Inferior': 10,
                        'Anterior': 0,
                        'Posterior': 0,
                        'Right': 0,
                        'Left': 0})
    case.PatientModel.RegionsOfInterest['Avoid_Face'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # BTV_Flash_20: a 2 cm expansion for flash except in the directions the MD's wish to have no flash
    # Per MD's flashed dimensions are superior, anterior, and posterior
    if not check_structure_exists(case=case, roi_list=rois, option='Delete',
                                  structure_name='BTV_Flash_20'):
        logging.info('BTV_Flash_20 not found, generating from expansion')

    case.PatientModel.CreateRoi(Name="BTV_Flash_20",
                                Color="128, 0, 64",
                                Type="Ptv",
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)

    case.PatientModel.RegionsOfInterest['BTV_Flash_20'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["PTV_WB_xxxx"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 2,
                                        'Inferior': 0,
                                        'Anterior': 2,
                                        'Posterior': 2,
                                        'Right': 0,
                                        'Left': 0}},
        ExpressionB={'Operation': "Union",
                     'SourceRoiNames': ["Avoid_Face"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ResultOperation="Subtraction",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})

    case.PatientModel.RegionsOfInterest['BTV_Flash_20'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # BTV: the block target volume.  It consists of the BTV_Brain, BTV_Flash_20 with no additional structures
    # We are going to make the BTV as a fixture if we are making a plan so that we can autoset the dose grid
    if not check_structure_exists(case=case, roi_list=rois, option='Delete', structure_name='BTV'):
        logging.info('BTV not found, generating from expansion')

    if make_plan:
        btv_temporary_type = "Fixation"
    else:
        btv_temporary_type = "Ptv"

    case.PatientModel.CreateRoi(Name="BTV",
                                Color="Yellow",
                                Type=btv_temporary_type,
                                TissueName=None,
                                RbeCellTypeName=None,
                                RoiMaterial=None)
    case.PatientModel.RegionsOfInterest['BTV'].SetAlgebraExpression(
        ExpressionA={'Operation': "Union",
                     'SourceRoiNames': ["BTV_Brain",
                                        "BTV_Flash_20"],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ExpressionB={'Operation': "Intersection",
                     'SourceRoiNames': [],
                     'MarginSettings': {'Type': "Expand",
                                        'Superior': 0,
                                        'Inferior': 0,
                                        'Anterior': 0,
                                        'Posterior': 0,
                                        'Right': 0,
                                        'Left': 0}},
        ResultOperation="None",
        ResultMarginSettings={'Type': "Expand",
                              'Superior': 0,
                              'Inferior': 0,
                              'Anterior': 0,
                              'Posterior': 0,
                              'Right': 0,
                              'Left': 0})

    case.PatientModel.RegionsOfInterest['BTV'].UpdateDerivedGeometry(
        Examination=examination,
        Algorithm="Auto")

    # Change visibility of structures
    for s in visible_structures:
        try:
            patient.SetRoiVisibility(RoiName=s,
                                     IsVisible=True)
        except:
            logging.debug("Structure: {} was not found".format(s))

    for s in invisible_stuctures:
        try:
            patient.SetRoiVisibility(RoiName=s,
                                     IsVisible=False)
        except:
            logging.debug("Structure: {} was not found".format(s))
    # Exclude these from export
    case.PatientModel.ToggleExcludeFromExport(
        ExcludeFromExport=True,
        RegionOfInterests=export_exclude_structs,
        PointsOfInterests=[])

    if make_plan:
        try:
            ui = connect.get_current('ui')
            ui.TitleBar.MenuItem['Plan Design'].Button_Plan_Design.Click()
        except:
            logging.debug("Could not click on the plan Design MenuItem")

        plan_names = [plan_name, 'backup_r1a0']
        # RS 8: plan_names = [plan_name]
        patient.Save()
        # RS 8: eliminate for loop
        for p in plan_names:
            try:
                case.AddNewPlan(
                    PlanName=p,
                    PlannedBy="",
                    Comment="",
                    ExaminationName=examination.Name,
                    AllowDuplicateNames=False)
            except Exception:
                plan_name = p + str(random.randint(1, 999))
                case.AddNewPlan(
                    PlanName=p,
                    PlannedBy="",
                    Comment="",
                    ExaminationName=examination.Name,
                    AllowDuplicateNames=False)
            patient.Save()

            plan = case.TreatmentPlans[p]
            plan.SetCurrent()
            connect.get_current('Plan')
            # Creating a common call to a create beamset wrapper
            # will help the next time the function calls are changed
            # by RaySearch
            beamset_defs = BeamOperations.BeamSet()
            beamset_defs.rx_target = 'PTV_WB_xxxx'
            beamset_defs.number_of_fractions = number_of_fractions
            beamset_defs.total_dose = total_dose
            beamset_defs.machine = plan_machine
            beamset_defs.iso_target = 'PTV_WB_xxxx'
            beamset_defs.name = p
            beamset_defs.DicomName = p
            beamset_defs.modality = 'Photons'
            # Beamset elements derived from the protocol
            beamset_defs.technique = "Conformal"
            beamset_defs.protocol_name = "WBRT"

            beamset = BeamOperations.create_beamset(
                patient=patient,
                exam = examination,
                case=case,
                plan=plan,
                dialog=False,
                BeamSet=beamset_defs,
                create_setup_beams=False
            )

            patient.Save()

            beamset.AddDosePrescriptionToRoi(RoiName='PTV_WB_xxxx',
                                             DoseVolume=80,
                                             PrescriptionType='DoseAtVolume',
                                             DoseValue=total_dose,
                                             RelativePrescriptionLevel=1,
                                             AutoScaleDose=True)
            # Set the BTV type above to allow dose grid to cover
            case.PatientModel.RegionsOfInterest['BTV'].Type = 'Ptv'
            case.PatientModel.RegionsOfInterest['BTV'].OrganData.OrganType = 'Target'

            plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2,
                                               'y': 0.2,
                                               'z': 0.2})
            try:
                isocenter_position = case.PatientModel.StructureSets[examination.Name]. \
                    RoiGeometries['PTV_WB_xxxx'].GetCenterOfRoi()
            except Exception:
                logging.warning('Aborting, could not locate center of PTV_WB_xxxx')
                sys.exit
            ptv_wb_xxxx_center = {'x': isocenter_position.x,
                                  'y': isocenter_position.y,
                                  'z': isocenter_position.z}
            isocenter_parameters = beamset.CreateDefaultIsocenterData(Position=ptv_wb_xxxx_center)
            isocenter_parameters['Name'] = "iso_" + plan_name
            isocenter_parameters['NameOfIsocenterToRef'] = "iso_" + plan_name
            logging.info('Isocenter chosen based on center of PTV_WB_xxxx.' +
                         'Parameters are: x={}, y={}:, z={}, assigned to isocenter name{}'.format(
                             ptv_wb_xxxx_center['x'],
                             ptv_wb_xxxx_center['y'],
                             ptv_wb_xxxx_center['z'],
                             isocenter_parameters['Name']))

            beam_ener = [6, 6]
            beam_names = ['1_Brai_RLat', '2_Brai_LLat']
            beam_descrip = ['1 3DC: MLC Static Field', '2 3DC: MLC Static Field']
            beam_gant = [270, 90]
            beam_col = [0, 0]
            beam_couch = [0, 0]

            for i, b in enumerate(beam_names):
                beamset.CreatePhotonBeam(BeamQualityId=beam_ener[i],
                                     IsocenterData=isocenter_parameters,
                                     Name=b,
                                     Description=beam_descrip[i],
                                     GantryAngle=beam_gant[i],
                                     CouchRotationAngle=beam_couch[i],
                                     CollimatorAngle=beam_col[i])
            beamset.PatientSetup.UseSetupBeams = True
            # Set treat/protect and minimum MU
            for beam in beamset.Beams:
                beam.BeamMU = 1
                beam.SetTreatOrProtectRoi(RoiName='BTV')
                beam.SetTreatOrProtectRoi(RoiName='Avoid')

            beamset.TreatAndProtect(ShowProgress=True)
            # Compute the dose
            beamset.ComputeDose(
                ComputeBeamDoses=True,
                DoseAlgorithm="CCDose",
                ForceRecompute=True)

        # RS 8 delete next three lines
        plan_name_regex = '^' + plan_names[0] + '$'
        plan_information = case.QueryPlanInfo(Filter={'Name': plan_name_regex})
        case.LoadPlan(PlanInfo=plan_information[0])
        try:
            ui = connect.get_current('ui')
            ui.TitleBar.MenuItem['Plan Evaluation'].Button_Plan_Evaluation.Click()
        except:
            logging.debug("Could not click on the plan evaluation MenuItem")

    # Rename PTV per convention
    total_dose_string = str(int(total_dose))
    try:
        case.PatientModel.RegionsOfInterest[
            'PTV_WB_xxxx'].Name = 'PTV_WB_' + total_dose_string.zfill(4)
    except Exception as e:
        logging.debug('error reported {}'.format(e))
        logging.debug('cannot do name change')

    patient.Save()
    plan = case.TreatmentPlans[plan_name]
    plan.SetCurrent()
    connect.get_current('Plan')
    beamset = plan.BeamSets[plan_name]
    patient.Save()
    beamset.SetCurrent()
    connect.get_current('BeamSet')
    BeamOperations.rename_beams()
    # Set the DSP for the plan
    BeamOperations.set_dsp(plan=plan, beam_set=beamset)
    # Round MU
    # The Autoscale hides in the plan optimization hierarchy. Find the correct index.
    indx = PlanOperations.find_optimization_index(plan=plan, beamset=beamset, verbose_logging=False)
    plan.PlanOptimizations[indx].AutoScaleToPrescription = False
    BeamOperations.round_mu(beamset)
    # Round jaws to nearest mm
    logging.debug('Checking for jaw rounding')
    BeamOperations.round_jaws(beamset=beamset)


if __name__ == '__main__':
    main()
