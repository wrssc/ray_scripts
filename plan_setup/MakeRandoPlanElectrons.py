""" Automatically Generate DICOM Export Test Plans

    You must have TPL_000 open for this to work as this iterates through all
    patient orientations

    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are
           passed to the function as an argument

    Example Usage:

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
__version__ = '1.0.2'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '7.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/xxxxx'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import connect

case = connect.get_current("Case")
plan_name = 'HFS_DICOM_Export'
beam_set_names = [
    "HFS_MeV_3DC_TB",
    "HFS_MV_VMA_TB",
    "HFS_MV_3DC_STx",
    "HFS_MV_VMA_STx",
    "HFS_MV_ConA_TB",
    "HFS_MV_ConA_TB",
]
machine_names = [
    "TrueBeam",
    "TrueBeam",
    "TrueBeamSTx",

]

case.AddNewPlan(PlanName=plan_name,
                PlannedBy="",
                Comment="Head First Supine Dicom Export Verification",
                ExaminationName="HFS",
                AllowDuplicateNames=False)
patient.Save()
plan = case.TreatmentPlans[plan_name]
plan.SetCurrent()
connect.get_current('Plan')

plan.SetDefaultDoseGrid(VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2})

plan.AddNewBeamSet(
    Name=beam_set_names[0],
    ExaminationName="HFS",
    MachineName="TrueBeam",
    Modality="Photons",
    TreatmentTechnique="Conformal",
    PatientPosition="HeadFirstSupine",
    NumberOfFractions=5,
    CreateSetupBeams=True,
    UseLocalizationPointAsSetupIsocenter=False,
    Comment="3D Validation plan for DICOM Export - TrueBeam",
    RbeModelReference=None,
    EnableDynamicTrackingForVero=False,
    NewDoseSpecificationPointNames=[],
    NewDoseSpecificationPoints=[],
    RespiratoryMotionCompensationTechnique="Disabled",
    RespiratorySignalSource="Disabled")

plan.AddNewBeamSet(Name="HFS_MeV_3DC_TB", ExaminationName="HFS", MachineName="TrueBeam_E",
                   Modality="Electrons", TreatmentTechnique="ApplicatorAndCutout",
                   PatientPosition="HeadFirstSupine", NumberOfFractions=5, CreateSetupBeams=True,
                   UseLocalizationPointAsSetupIsocenter=False,
                   Comment="3D validation plan for electrons", RbeModelReference=None,
                   EnableDynamicTrackingForVero=False, NewDoseSpecificationPointNames=[],
                   NewDoseSpecificationPoints=[], RespiratoryMotionCompensationTechnique="Disabled",
                   RespiratorySignalSource="Disabled")

plan.AddNewBeamSet(Name="HFS_MV_VMA_TB", ExaminationName="HFS", MachineName="TrueBeam",
                   Modality="Photons", TreatmentTechnique="VMAT", PatientPosition="HeadFirstSupine",
                   NumberOfFractions=5, CreateSetupBeams=True,
                   UseLocalizationPointAsSetupIsocenter=False,
                   Comment="VMAT Validation plan for DICOM Export - TrueBeam", RbeModelReference=None,
                   EnableDynamicTrackingForVero=False, NewDoseSpecificationPointNames=[],
                   NewDoseSpecificationPoints=[], RespiratoryMotionCompensationTechnique="Disabled",
                   RespiratorySignalSource="Disabled")

plan.AddNewBeamSet(Name="HFS_MV_3DC_STx", ExaminationName="HFS", MachineName="TrueBeamSTx",
                   Modality="Photons", TreatmentTechnique="Conformal", PatientPosition="HeadFirstSupine",
                   NumberOfFractions=5, CreateSetupBeams=True,
                   UseLocalizationPointAsSetupIsocenter=False,
                   Comment="3D Validation plan for DICOM Export - STx", RbeModelReference=None,
                   EnableDynamicTrackingForVero=False, NewDoseSpecificationPointNames=[],
                   NewDoseSpecificationPoints=[], RespiratoryMotionCompensationTechnique="Disabled",
                   RespiratorySignalSource="Disabled")

plan.AddNewBeamSet(Name="HFS_MV_VMA_STx", ExaminationName="HFS", MachineName="TrueBeamSTx",
                   Modality="Photons", TreatmentTechnique="VMAT", PatientPosition="HeadFirstSupine",
                   NumberOfFractions=5, CreateSetupBeams=True,
                   UseLocalizationPointAsSetupIsocenter=False,
                   Comment="3D Validation plan for DICOM Export - STx", RbeModelReference=None,
                   EnableDynamicTrackingForVero=False, NewDoseSpecificationPointNames=[],
                   NewDoseSpecificationPoints=[], RespiratoryMotionCompensationTechnique="Disabled",
                   RespiratorySignalSource="Disabled")

plan.AddNewBeamSet(Name="HFS_MV_ConA_TB", ExaminationName="HFS", MachineName="TrueBeam",
                   Modality="Photons", TreatmentTechnique="ConformalArc",
                   PatientPosition="HeadFirstSupine", NumberOfFractions=5, CreateSetupBeams=True,
                   UseLocalizationPointAsSetupIsocenter=False, Comment="", RbeModelReference=None,
                   EnableDynamicTrackingForVero=False, NewDoseSpecificationPointNames=[],
                   NewDoseSpecificationPoints=[], RespiratoryMotionCompensationTechnique="Disabled",
                   RespiratorySignalSource="Disabled")

retval_1.AddDosePrescriptionToRoi(RoiName="PTV1", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=2500,
                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

# Unscriptable Action 'Change context' Completed : SetContextToRadiationSetAction(...)

retval_2.AddDosePrescriptionToRoi(RoiName="PTV5_Surface", DoseVolume=95, PrescriptionType="DoseAtVolume",
                                  DoseValue=2500, RelativePrescriptionLevel=1, AutoScaleDose=True)

# Unscriptable Action 'Change context' Completed : SetContextToRadiationSetAction(...)

retval_3.AddDosePrescriptionToRoi(RoiName="PTV2", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=2500,
                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

# Unscriptable Action 'Change context' Completed : SetContextToRadiationSetAction(...)

retval_4.AddDosePrescriptionToRoi(RoiName="PTV3", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=2500,
                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

# Unscriptable Action 'Change context' Completed : SetContextToRadiationSetAction(...)

retval_5.AddDosePrescriptionToRoi(RoiName="PTV3", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=2500,
                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

retval_0.UpdateDependency(DependentBeamSetName="HFS_MV_ConA_TB", BackgroundBeamSetName="HFS_MV_3DC_TB",
                          DependencyUpdate="CreateDependency")

# Unscriptable Action 'Change context' Completed : SetContextToRadiationSetAction(...)

retval_6.AddDosePrescriptionToRoi(RoiName="PTV1", DoseVolume=95, PrescriptionType="DoseAtVolume", DoseValue=3750,
                                  RelativePrescriptionLevel=1, AutoScaleDose=True)

# CompositeAction ends


# Unscriptable Action 'Save' Completed : SaveAction(...)

with CompositeAction('Add beam (1_6MeV_06x06, Beam Set: HFS_MeV_3DC_TB)'):
    retval_7 = beam_set.CreateElectronBeam(ApplicatorName="Varian 6x6", Energy=6, InsertName="333",
                                           IsAddCutoutChecked=True, IsocenterData={
            'Position': {'x': -0.0968178451119894, 'y': -32.0682494405771, 'z': -0.465064539760374},
            'NameOfIsocenterToRef': "", 'Name': "HFS_MeV_3DC_TB 1", 'Color': "98, 184, 234"}, Name="1_6MeV_06x06",
                                           Description="", GantryAngle=0, CouchAngle=0, CollimatorAngle=0)

    retval_7.SetBolus(BolusName="Bolus")

    # Unscriptable Action 'Beam MU' Completed : DelegateSyncAction(...)

    # CompositeAction ends

# Unscriptable Action 'PTV5_Surface Checked' Completed : DelegateSyncAction(...)

with CompositeAction('Add beam (2_9MeV_10x10, Beam Set: HFS_MeV_3DC_TB)'):
    retval_8 = beam_set.CreateElectronBeam(ApplicatorName="Varian 10x10", Energy=9, InsertName="334",
                                           IsAddCutoutChecked=True, IsocenterData={
            'Position': {'x': -0.0968178451119894, 'y': -32.0682494405771, 'z': -0.465064539760374},
            'NameOfIsocenterToRef': "HFS_MeV_3DC_TB 1", 'Name': "HFS_MeV_3DC_TB 1", 'Color': "98, 184, 234"},
                                           Name="2_9MeV_10x10", Description="", GantryAngle=0, CouchAngle=0,
                                           CollimatorAngle=0)

    retval_8.SetBolus(BolusName="")

    # Unscriptable Action 'Beam MU' Completed : DelegateSyncAction(...)

    # CompositeAction ends

with CompositeAction('Bolus selected (Bolus, Beam: 2_9MeV_10x10, Beam Set: HFS_MeV_3DC_TB)'):
    retval_8.SetBolus(BolusName="Bolus")

    # CompositeAction ends

with CompositeAction('Add beam (3_12MeV_15x15, Beam Set: HFS_MeV_3DC_TB)'):
    retval_9 = beam_set.CreateElectronBeam(ApplicatorName="Varian 15x15", Energy=12, InsertName="335",
                                           IsAddCutoutChecked=True, IsocenterData={
            'Position': {'x': -0.0968178451119894, 'y': -32.0682494405771, 'z': -0.465064539760374},
            'NameOfIsocenterToRef': "HFS_MeV_3DC_TB 1", 'Name': "HFS_MeV_3DC_TB 1", 'Color': "98, 184, 234"},
                                           Name="3_12MeV_15x15", Description="", GantryAngle=0, CouchAngle=0,
                                           CollimatorAngle=0)

    retval_9.SetBolus(BolusName="Bolus")

    # Unscriptable Action 'Beam MU' Completed : DelegateSyncAction(...)

    # CompositeAction ends

with CompositeAction('Add beam (4_12MeV_20x20, Beam Set: HFS_MeV_3DC_TB)'):
    retval_10 = beam_set.CreateElectronBeam(ApplicatorName="Varian 20x20", Energy=12, InsertName="336",
                                            IsAddCutoutChecked=True, IsocenterData={
            'Position': {'x': -0.0968178451119894, 'y': -32.0682494405771, 'z': -0.465064539760374},
            'NameOfIsocenterToRef': "HFS_MeV_3DC_TB 1", 'Name': "HFS_MeV_3DC_TB 1", 'Color': "98, 184, 234"},
                                            Name="4_12MeV_20x20", Description="", GantryAngle=0, CouchAngle=0,
                                            CollimatorAngle=0)

    retval_10.SetBolus(BolusName="Bolus")

    # Unscriptable Action 'Beam MU' Completed : DelegateSyncAction(...)

    # CompositeAction ends

# Unscriptable Action 'Edit Beam (4_12MeV_20x20, Beam Set: HFS_MeV_3DC_TB)' Completed : EditElectronBeamAction(...)

with CompositeAction('Edit Beam (4_12MeV_20x20, Beam Set: HFS_MeV_3DC_TB)'):
    beam_set.Beams['4_12MeV_20x20'].Name = "4_15MeV_20x20"

    # CompositeAction ends

with CompositeAction('Add beam (5_15MeV_25x25, Beam Set: HFS_MeV_3DC_TB)'):
    retval_11 = beam_set.CreateElectronBeam(ApplicatorName="Varian 25x25", Energy=15, InsertName="337",
                                            IsAddCutoutChecked=True, IsocenterData={
            'Position': {'x': -0.0968178451119894, 'y': -32.0682494405771, 'z': -0.465064539760374},
            'NameOfIsocenterToRef': "HFS_MeV_3DC_TB 1", 'Name': "HFS_MeV_3DC_TB 1", 'Color': "98, 184, 234"},
                                            Name="5_15MeV_25x25", Description="", GantryAngle=0, CouchAngle=0,
                                            CollimatorAngle=0)

    retval_11.SetBolus(BolusName="Bolus")

    # Unscriptable Action 'Beam MU' Completed : DelegateSyncAction(...)

    # CompositeAction ends

# Unscriptable Action 'Edit SSD (1_6MeV_06x06, Beam Set: HFS_MeV_3DC_TB)' Completed : EditSSDAction(...)

# Unscriptable Action 'PTV5_Surface Checked' Completed : DelegateSyncAction(...)

# Unscriptable Action 'Setting 2 for PTV5_Surface' Completed : DelegateSyncAction(...)

# Unscriptable Action 'PTV5_Surface Checked' Completed : DelegateSyncAction(...)

# Unscriptable Action 'Setting 3 for PTV5_Surface' Completed : DelegateSyncAction(...)

# Unscriptable Action 'PTV5_Surface Checked' Completed : DelegateSyncAction(...)

# Unscriptable Action 'Setting 4 for PTV5_Surface' Completed : DelegateSyncAction(...)

# Unscriptable Action 'PTV5_Surface Checked' Completed : DelegateSyncAction(...)

# Unscriptable Action 'Setting 5 for PTV5_Surface' Completed : DelegateSyncAction(...)

with CompositeAction('Conform all'):
    retval_2.TreatAndProtect(ShowProgress=True)

    # CompositeAction ends
