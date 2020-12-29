""" Automated Dry-Run

    This script accomplishes the following tasks:
    1. Looks through the target list and prompt user in the event it finds none
    2. Prompts the user to set fiducial simulation points
    2. Enter plan parameters through a dialog
    3. Makes a treatment plan for a dry-run
    4. Makes a copy of this plan to get around a bug in raystation
       that makes it such that until a new plan is created, the 
       patient's image data is not visible
    5. Has the user confirm isocenter placement
    Will prompt user for type of dry-run (breast or lung) and attempt to put beams at the center of a
    "gtv or ctv" target

    Validation Notes:
    Test Patient: MR# ZZUWQA_ScTest_29Dec2020, Name: Script_Testing^Automated Dry Run 
    Version Notes: 1.0.0 Original
    1.1.0 Update to python 3.6

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
__date__ = '29-Dec-2020'
__version__ = '1.1.0'
__status__ = 'Validation'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '10A.SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2020, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import connect
import logging
import UserInterface
import random
import sys


def main():
    # UW Inputs
    # If machines names change they need to be modified here:
    institution_inputs_machine_name = ['TrueBeamSTx', 'TrueBeam']
    institution_inputs_sites = ['Liver', 'Lung', 'Breast']
    institution_inputs_motion = ['MIBH', 'MEBH', 'Free-Breathing']
    status = UserInterface.ScriptStatus(
        steps=['SimFiducials point declaration',
               'Enter Plan Parameters',
               'Make plan for dry run',
               'Confirm iso placement'],
        docstring=__doc__,
        help=__help__)
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        patient_db = connect.get_current('PatientDB')
    except:
        UserInterface.WarningBox('This script requires a patient, case, and exam to be loaded')
        sys.exit('This script requires a patient, case, and exam to be loaded')

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['POI tools'].Select()
        ui.ToolPanel.TabItem['POIs'].Select()
    except:
        logging.debug("Could not click on the patient modeling window")
    # Capture the current list of ROI's to avoid saving over them in the future
    rois = case.PatientModel.StructureSets[examination.Name].RoiGeometries

    # Capture the current list of POI's to avoid a crash
    pois = case.PatientModel.PointsOfInterest

    # Find all targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.OrganData.OrganType == 'Target':
            plan_targets.append(r.Name)
    # Add user threat: empty target list.
    if not plan_targets:
        connect.await_user_input("The target list is empty." +
                                 " Please apply type PTV to the targets and continue.")
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == 'Target':
                plan_targets.append(r.Name)
    if not plan_targets:
        status.finish('Script cancelled, targets were not supplied')
        sys.exit('Script cancelled')
    # TODO: Add handling for empty targets or geometries

    # Look for the sim point, if not create a point
    sim_point_found = any(poi.Name == 'SimFiducials' for poi in pois)
    if sim_point_found:
        logging.warning("POI SimFiducials Exists")
        status.next_step(text="SimFiducials Point found, ensure that it is placed properly")
        connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')
    else:
        case.PatientModel.CreatePoi(Examination=examination,
                                    Point={'x': 0,
                                           'y': 0,
                                           'z': 0},
                                    VisualizationDiameter=1,
                                    Name="SimFiducials",
                                    Color="Green",
                                    Type="LocalizationPoint")
        status.next_step(text="SimFiducials POI created, ensure that it is placed properly")
        connect.await_user_input('Ensure Correct placement of the SimFiducials Point and continue script.')


        # Get some user data
    status.next_step(text="Complete plan information - check the TPO for doses " +
                          "and ARIA for the treatment machine")
    # This dialog grabs the relevant parameters to generate the dry run
    # For now, we'll hard code a few options until these inputs do something
    v1 = {'plan_name': 'DryRun', 'motion': 'NA in version 1', 'site': 'NA in version 1'}
    input_dialog = UserInterface.InputDialog(
        inputs={
            # 'input1_plan_name': 'Enter the Plan Name, typically DryRun',
            # 'input2_site': 'Select the Site',
            # 'input3_MMT': 'Motion Management Technique',
            'input4_choose_machine': 'Choose Treatment Machine',
            'input5_target': 'Select target for isocenter localization'
        },
        title='Dry Run Input',
        datatype={
            # 'input2_site': 'combo',
            # 'input3_MMT': 'combo',
            'input4_choose_machine': 'combo',
            'input5_target': 'combo'
        },
        initial={
            # 'input1_plan_name': 'DryRun',
        },
        options={
            # 'input2_site': institution_inputs_sites,
            # 'input3_MMT': institution_inputs_motion,
            'input4_choose_machine': institution_inputs_machine_name,
            'input5_target': plan_targets
        },
        required=[
            # 'input1_plan_name',
            # 'input2_site',
            # 'input3_MMT',
            'input4_choose_machine',
            'input5_target'])

    # Launch the dialog
    response =  input_dialog.show()
    # Close on cancel
    if response == {}:
        logging.info('dry_run cancelled by user')
        sys.exit('dry_run cancelled by user')
    else:
        logging.debug('User selected isocenter in target: {}'.format(
            input_dialog.values['input5_target']))

    # plan_name = input_dialog.values['input1_plan_name']
    # site = input_dialog.values['input2_site']
    # motion = input_dialog.values['input3_MMT']
    plan_name = v1['plan_name']
    site = v1['site']
    motion = v1['motion']

    plan_machine = input_dialog.values['input4_choose_machine']
    target = input_dialog.values['input5_target']

    logging.info('User selected plan name: {}'.format(plan_name))
    logging.info('User selected site name: {}'.format(site))
    logging.info('User selected motion technique: {}'.format(motion))
    logging.info('User selected machine: {}'.format(plan_machine))
    logging.info('User selected target for isocenter placement: {}'.format(target))

    status.next_step(text="Making plan.")

    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Plan design'].Button_Plan_design.Click()
    except:
        logging.debug("Could not click on the plan design window")

    plan_names = [plan_name, 'backup_delete']
    used_plan_names = []
    # RS 11?: plan_names = [plan_name]
    patient.Save()
    # RS 11?: eliminate for loop
    for p in plan_names:
        try:
            case.AddNewPlan(
                PlanName=p,
                PlannedBy="",
                Comment="",
                ExaminationName=examination.Name,
                AllowDuplicateNames=False)
            used_plan_names.append(p)
        except Exception:
            # Exception to deal with existing plan
            plan_name = p + str(random.randint(1, 999))
            case.AddNewPlan(
                PlanName=p,
                PlannedBy="",
                Comment="",
                ExaminationName=examination.Name,
                AllowDuplicateNames=False)
            used_plan_names.append(p)
        patient.Save()

        plan = case.TreatmentPlans[p]
        plan.SetCurrent()
        connect.get_current('Plan')

        plan.AddNewBeamSet(
            Name=p,
            ExaminationName=examination.Name,
            MachineName=plan_machine,
            Modality="Photons",
            TreatmentTechnique="Conformal",
            PatientPosition="HeadFirstSupine",
            NumberOfFractions=1,
            CreateSetupBeams=False,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment="",
            RbeModelReference=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[])

        beamset = plan.BeamSets[p]
        patient.Save()

        plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2,
                                           'y': 0.2,
                                           'z': 0.2})
        try:
            isocenter_position = case.PatientModel.StructureSets[examination.Name]. \
                RoiGeometries[target].GetCenterOfRoi()
        except Exception:
            logging.warning('Aborting, could not locate center of {}'.format(target))
            sys.exit

        target_center = {'x': isocenter_position.x,
                         'y': isocenter_position.y,
                         'z': isocenter_position.z}

        isocenter_parameters = beamset.CreateDefaultIsocenterData(Position=target_center)
        isocenter_parameters['Name'] = "iso_" + plan_name
        isocenter_parameters['NameOfIsocenterToRef'] = "iso_" + plan_name
        logging.info('Isocenter chosen based on center of {}. '.format(target) +
                     'Parameters are: x={}, y={}:, z={}, assigned to isocenter name{}'.format(
                         target_center['x'],
                         target_center['y'],
                         target_center['z'],
                         isocenter_parameters['Name']))

        beam_ener = [6, 6, 6]
        beam_names = ['1_AP_DryRun', '2_RLat_DryRun', '3_LLat_DryRun']
        beam_descrip = ['1 QA', '2 QA', '3 QA']
        beam_gant = [0, 270, 90]
        beam_col = [0, 0, 0]
        beam_couch = [0, 0, 0]

        for i, b in enumerate(beam_names):
            beamset.CreatePhotonBeam(BeamQualityId=beam_ener[i],
                                     IsocenterData=isocenter_parameters,
                                     Name=b,
                                     Description=beam_descrip[i],
                                     GantryAngle=beam_gant[i],
                                     CouchRotationAngle=beam_couch[i],
                                     CollimatorAngle=beam_col[i])
            beamset.PatientSetup.UseSetupBeams = True
        for beam in beamset.Beams:
            beam.BeamMU = 1
            beam.CreateRectangularField(
                Width=0.05,
                Height=0.05,
                CenterCoordinate={'x': -0.025, 'y': 0.005},
                MoveMLC=True, MoveAllMLCLeaves=False,
                MoveJaw=True,
                JawMargins={'x': 1, 'y': 1},
                DeleteWedge=False,
                PreventExtraLeafPairFromOpening=True)

    patient.Save()
    logging.debug('Load plan {}'.format(used_plan_names[0]))
    plan = case.TreatmentPlans[used_plan_names[0]]
    patient.Save()
    plan.SetCurrent()
    beamset = plan.BeamSets[used_plan_names[0]]
    patient.Save()
    beamset.SetCurrent()

    # Adding set up fields
    # HFS Setup
    # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
    set_up = {0: ['SetUp AP', 'SetUp AP', 0.0, '5'],
              1: ['SetUp RtLat', 'SetUp RtLat', 270.0, '5'],
              2: ['SetUp LtLat', 'SetUp LtLat', 90.0, '5'],
              3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
              }
    # Extract the angles
    angles = []
    for k, v in set_up.items():
        angles.append(v[2])
        logging.debug("v2={}".format(v[2]))

    beamset.UpdateSetupBeams(ResetSetupBeams=True,
                             SetupBeamsGantryAngles=angles)
    # Set the set-up parameter specifics
    for i, b in enumerate(beamset.PatientSetup.SetupBeams):
        b.Name = set_up[i][0]
        b.Description = set_up[i][1]
        b.GantryAngle = str(set_up[i][2])
        b.Segments[0].DoseRate = set_up[i][3]

    status.next_step(text="Confirm correct placement of isocenter and delete that pesky Backup Plan")

    status.finish(text="Delete that pesky Backup Plan, and close this dialog")


if __name__ == '__main__':
    main()
