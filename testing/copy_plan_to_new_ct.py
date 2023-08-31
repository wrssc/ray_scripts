""" Copy plan to new CT
This attached script is provided as a tool and not as a RaySearch endorsed script for
clinical use.  The use of this script in its whole or in part is done so
without any guarantees of accuracy or expected outcomes. Please verify all results. Further,
per the Raystation Instructions for Use, ALL scripts MUST be verified by the user prior to
clinical use.

Copy Plan to New CT or Merge Beamsets 3.0.10

It can copy a proton(version 10+ only) or photon or electron plan from one CT to another.  It will not copy wedges.
It does support VMAT and RayStation Versions 4.7 and 5, 6, 7, 8, 9, 10, 11A & 11B.  You must ensure that there are no merged
beams in a 3D-CRT plan. This will no longer compute the final plan.
"""
import sys
import clr
import platform

from connect import *

##### RayWindow selection #####
ui = get_current('ui')
_version = ui.GetApplicationVersion().split('.')
version = int(_version[0]) if int(_version[1]) != 99 else int(_version[0]) + 1
subversion = int(_version[1])
print('version: {}.{}'.format(version,subversion))
if version >= 11:
    print ('RayStation 11A and forward requires CPython')
    assert platform.python_implementation() == "CPython"
    from pathlib import Path
    window_class = RayWindow
    clr.AddReference('ScriptClient')
else:
    print ('This script prior to RayStation 11A requires IronPython')
    assert platform.python_implementation() == "IronPython"
    import wpf
    from System.Windows import Window
    window_class = Window
    clr.AddReference('ScriptClient.dll')



clr.AddReference('System')
clr.AddReference("System.Xml")
clr.AddReference("System.Windows.Forms")
import System

from random import choice
from string import ascii_uppercase
from System.Windows import *
from System.Collections.ObjectModel import ObservableCollection
from System.Windows.Controls import ComboBox, ComboBoxItem
from System.IO import StringReader
from System.Xml import XmlReader
from System.Windows.Forms import MessageBox




class MyWindow(window_class):

    def __init__(self):
        xaml = \
            """
<Window
       xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
       xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" x:Name="CopyPlanWindow"
       Title="Copy Plan To New CT" Height="371" Width="235">
    <Grid>

        <TabControl HorizontalAlignment="Left" Height="336" Margin="0,2,0,0" VerticalAlignment="Top" Width="292">
            <TabItem Header="Copy Plan to New CT">
                <Grid Background="#FFE5E5E5" Margin="0,0,64,0">
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="173*"/>
                        <ColumnDefinition Width="49*"/>
                    </Grid.ColumnDefinitions>
                    <TextBox x:Name="NewPlanNameTextBox" HorizontalAlignment="Left" Height="23" Margin="20,110,0,0" TextWrapping="Wrap" VerticalAlignment="Top" Width="187" TextChanged="TextBox_TextChanged" Grid.ColumnSpan="2"/>
                    <Label x:Name="PlanNameLbl" Content="New Plan Name" HorizontalAlignment="Left" Margin="20,79,0,0" VerticalAlignment="Top" Width="110"/>
                    <ListBox x:Name="NewDatasetListBox" HorizontalAlignment="Left" Height="90" Margin="20,169,0,0" VerticalAlignment="Top" Width="187" SelectionChanged="TextBox_TextChanged" Grid.ColumnSpan="2"/>
                    <Label x:Name="DatasetLbl" Content="New Dataset" HorizontalAlignment="Left" Margin="20,138,0,0" VerticalAlignment="Top" Width="110"/>
                    <Button x:Name="SubmitButton" Content="Submit" HorizontalAlignment="Left" Margin="36,272,0,0" VerticalAlignment="Top" Width="75" Click="SubmitButton_Click" IsEnabled="False"/>
                    <Button x:Name="CancelButton" Content="Cancel" HorizontalAlignment="Left" Margin="116,272,0,0" VerticalAlignment="Top" Width="75" Click="CancelButton_Click" Grid.ColumnSpan="2"/>
                    <ComboBox x:Name="p2cCB" HorizontalAlignment="Left" Margin="20,52,0,0" VerticalAlignment="Top" Width="187" Grid.ColumnSpan="2"/>
                    <Label Content="Plan to Copy" HorizontalAlignment="Left" Margin="20,21,0,0" VerticalAlignment="Top" Width="91"/>
                </Grid>
            </TabItem>
            <TabItem Header="Copy Beam Set">
                <Grid Background="#FFE5E5E5" Margin="0,0,64,0">
                    <ComboBox x:Name="p2c2CB" HorizontalAlignment="Left" Margin="20,110,0,0" VerticalAlignment="Top" Width="187" MouseLeave="p2c2CB_MouseLeave" />
                    <Label x:Name="BeamSetLbl" Content="Plan to Copy To" HorizontalAlignment="Left" Margin="20,79,0,0" VerticalAlignment="Top" Width="110"/>
                    <ListBox x:Name="bsLB" HorizontalAlignment="Left" Height="90" Margin="20,169,0,0" VerticalAlignment="Top" Width="187" SelectionChanged="bsLB_SelectionChanged" SelectionMode="Multiple"  Grid.ColumnSpan="2"/>
                    <Label x:Name="DatasetLbl2" Content="BeamSet(s) to Copy" HorizontalAlignment="Left" Margin="20,138,0,0" VerticalAlignment="Top" Width="110"/>
                    <Button x:Name="SubmitButton2" Content="Submit" HorizontalAlignment="Left" Margin="36,272,0,0" VerticalAlignment="Top" Width="75" Click="SubmitButton2_Click"  IsEnabled="False"/>
                    <Button x:Name="CancelButton2" Content="Cancel" HorizontalAlignment="Left" Margin="116,272,0,0" VerticalAlignment="Top" Width="75" Click="CancelButton_Click"/>
                    <ComboBox x:Name="p2cfCB" HorizontalAlignment="Left" Margin="20,52,0,0" VerticalAlignment="Top" Width="187" MouseLeave="p2cfCB_MouseLeave"/>
                    <Label Content="Plan to Copy From" HorizontalAlignment="Left" Margin="20,21,0,0" VerticalAlignment="Top" Width="187"/>
                </Grid>
            </TabItem>
        </TabControl>
    </Grid>
</Window>
"""
        xr = XmlReader.Create(StringReader(xaml))
        if version >= 11:
            self.LoadComponent(xaml)  # 11A w/RayWindow
        else:
            wpf.LoadComponent(self, xr) # up to 10B
        self.populateDatasetList()
        self.mode = ""

    def SubmitButton_Click(self, sender, e):
        self.mode = 'copy'
        self.DialogResult = True

    def CancelButton_Click(self, sender, e):
        self.DialogResult = False

    def TextBox_TextChanged(self, sender, e):
        self.shouldEnableSubmit1()

    def p2cCB_MouseLeave(self, sender, e):
        self.shouldEnableSubmit1()

    def p2c2CB_MouseLeave(self, sender, e):
        self.shouldEnableSubmit2()

    def p2cfCB_MouseLeave(self, sender, e):
        if self.p2cfCB.Text != '':
            bsns = [b.DicomPlanLabel for b in root.TreatmentPlans[self.p2cfCB.Text].BeamSets]
            self.bsLB.Items.Clear()
            for bsn in sorted(bsns):
                self.bsLB.Items.Add(bsn)
        self.shouldEnableSubmit2()

    def bsLB_SelectionChanged(self, sender, e):
        self.shouldEnableSubmit2()

    def SubmitButton2_Click(self, sender, e):
        self.mode = 'merge'
        self.DialogResult = True

    def shouldEnableSubmit1(self):
        if (self.NewPlanNameTextBox.Text != ''
                and self.NewDatasetListBox.SelectedItem != None
                and self.p2cCB.Text != ''):
            self.SubmitButton.IsEnabled = True

        else:
            self.SubmitButton.IsEnabled = False

    def shouldEnableSubmit2(self):
        if (self.p2c2CB.Text != ''
                and self.bsLB.SelectedItem != None
                and self.p2cfCB.Text != ''):
            self.SubmitButton2.IsEnabled = True

        else:
            self.SubmitButton2.IsEnabled = False


    def populateDatasetList(self):
        p2ccollection = ObservableCollection[ComboBoxItemClass]()
        p2c2collection = ObservableCollection[ComboBoxItemClass]()
        p2cfcollection = ObservableCollection[ComboBoxItemClass]()
        for p in root.TreatmentPlans:
            p2ccollection.Add(ComboBoxItemClass(p.Name))
            p2c2collection.Add(ComboBoxItemClass(p.Name))
            p2cfcollection.Add(ComboBoxItemClass(p.Name))
        self.p2cCB.ItemsSource = p2ccollection
        self.p2c2CB.ItemsSource = p2c2collection
        self.p2cfCB.ItemsSource = p2cfcollection
        exams = [exam.Name for exam in root.Examinations]
        for e in sorted(exams):
            self.NewDatasetListBox.Items.Add(e)


class ComboBoxItemClass(ComboBoxItem):
    def __init__(self,name):
        self.Content = name
        self.FontSize = 10


def TreatmentTechnique(bs):
    TT = '?'
    if bs.Modality == 'Photons':
        if bs.PlanGenerationTechnique == 'Imrt':
            if bs.DeliveryTechnique == 'SMLC':
                TT = 'SMLC'
            if bs.DeliveryTechnique == 'DynamicArc':
                TT = 'VMAT'
            if bs.DeliveryTechnique == 'DMLC':
                TT = 'DMLC'
            if bs.DeliveryTechnique == 'Arc': # RS6
                TT = 'VMAT'

        if bs.PlanGenerationTechnique == 'Conformal':
            if bs.DeliveryTechnique == 'SMLC':
                TT = 'Conformal'
            if bs.DeliveryTechnique == 'Arc':
                TT = 'Conformal Arc'
            if bs.DeliveryTechnique == 'DynamicArc':
                TT = 'VMAT'

    if bs.Modality == 'Electrons':
        if bs.PlanGenerationTechnique == 'Conformal':
            if bs.DeliveryTechnique == 'SMLC':
                TT = 'ApplicatorAndCutout'
    if version > 9:
        if bs.Modality == 'Protons':
            if bs.PlanGenerationTechnique == 'Imrt':
                if bs.DeliveryTechnique == 'PencilBeamScanning':
                    TT = 'ProtonPencilBeamScanning'
    return TT


def createControlPoints(dose):
    # we need to run a dummy optimization to create control points
    po = replan.PlanOptimizations[poIndex]

    # remove an roi named 'dummyPTV' if it exists
    try:
        roi = root.PatientModel.RegionsOfInterest['dummyPTV']
        roi.DeleteRoi()
    except:
        pass

    # create OUR dummyPTV roi
    with CompositeAction('Create dummy'):
        dummy = root.PatientModel.CreateRoi(Name='dummyPTV', Color='Red'
                , Type='Ptv', TissueName=None, RoiMaterial=None)

        dummy.CreateSphereGeometry(Radius=2,
                                   Examination=examination[0],
                                   Center=isocenter)

    # remove any existing optimization objectives
    if po.Objective != None:
        for f in po.Objective.ConstituentFunctions:
            f.DeleteFunction()

    # add OUR optimization objectives
    with CompositeAction('Add objective'):
        function = po.AddOptimizationFunction(
            FunctionType='UniformDose',
            RoiName='dummyPTV',
            IsConstraint=False,
            RestrictAllBeamsIndividually=False,
            RestrictToBeam=None,
            IsRobust=False,
            RestrictToBeamSet=None,
            )

        function.DoseFunctionParameters.DoseLevel = dose
        function.DoseFunctionParameters.Weight = 90

    # set the arc spacing and create teh segments
    with CompositeAction('Dummy optimization'):
        po.OptimizationParameters.Algorithm.MaxNumberOfIterations = 2
        po.OptimizationParameters.DoseCalculation.IterationsInPreparationsPhase = \
            1
        for (i, bs) in \
            enumerate(originalPlan.PlanOptimizations[opoIndex].OptimizationParameters.TreatmentSetupSettings[0].BeamSettings):
            replan.PlanOptimizations[poIndex].OptimizationParameters.TreatmentSetupSettings[0].BeamSettings[i].ArcConversionPropertiesPerBeam.FinalArcGantrySpacing = \
                bs.ArcConversionPropertiesPerBeam.FinalArcGantrySpacing
        po.RunOptimization()


def add_energy_layer(b,el,i,newBeamSet,plan,bsName):

    global beamIsos
    global isoData

    # let's try to minimize the creation of duplicate isocenters
    lock.acquire()
    if b.Name not in beamIsos:
        beamIsos.append(b.Name)
        isoData = newBeamSet.CreateDefaultIsocenterData(
            Position=b.Position
        )


    bName = "{0}_{1}".format(str(i), str(el.Energy))
    newBeamSet.CreatePBSIonBeam(
        SnoutId=b.SnoutId,
        SpotTuneId=spotTuneId,
        RangeShifter="{:0.2f}".format(el.Energy),
        IsocenterData=isoData,
        Name=bName,
        GantryAngle=b.GantryAngle,
        CouchAngle=b.CouchAngle,
        CollimatorAngle=b.CollimatorAngle
    )

    newBeam = plan.BeamSets[bsName].Beams[bName]

    newBeamSet.Beams[bName].EditSnoutPosition(
        SnoutPosition=b.SnoutPosition
    )
    # if there is a block, let's create it
    if b.Block is not None:
        blockName = "{0}_Block".format(bName)
        newBeam.AddOrEditIonBlock(
            BlockName=blockName,
            MaterialName=b.Block.MaterialName,
            Thickness=b.Block.Thickness,
            MillingToolDiameter=b.Block.MillingToolDiameter
        )

        newBeam.Blocks[blockName].Contour = b.Block.Contour

    # lets add the spots

    xPos = [sp[0] for sp in el.SpotPositions]
    yPos = [sp[1] for sp in el.SpotPositions]
    weights = [sw / sum(el.SpotWeights) for sw in el.SpotWeights]

    newBeam.AddEnergyLayerWithSpots(
        Energy=staticEnergy,
        SpotPositionsX=xPos,
        SpotPositionsY=yPos,
        SpotWeights=weights
    )

    newBeam.BeamMU = b.Mu * sum(el.SpotWeights)
    newBeam.Segments[0].Spots.Weights = weights
    newBeam.Segments[0].RelativeWeight = 1.0
    lock.release()


def get_energy_layers(segs):
    """
    Given the segments of a beam, create a list of energy layer objects
    :param segs: all segments (energy layer) for a beam
    :return: [list] of energy layer objects
    """
    layers = []
    for s in segs:
        el = EnergyLayer()
        el.Energy = s.NominalEnergy
        el.SpotPositions = [(p.x, p.y) for p in s.Spots.Positions]
        el.SpotWeights = [w for w in s.Spots.Weights]
        el.RelativeWeight = s.RelativeWeight
        layers.append(el)
    return layers


def getPlanName(pn):
    """
    Function to return unique plan name
    :param pn: current plan name
    :return: unique plan name
    """
    i = 0
    npn = pn[:]
    while len([p.Name for p in root.TreatmentPlans if p.Name == npn]):
        suffix = '_{}'.format(i)
        trim_length = 16 - len(suffix)
        npn = pn[:trim_length] + suffix
        i += 1
    return npn


def getBeamSetName(bsn):
    """
    Function to return unique plan name
    :param pn: current plan name
    :return: unique plan name
    """
    i = 0
    nbsn = bsn[:]
    while len([bs.DicomPlanLabel for bs in replan.BeamSets if bs.DicomPlanLabel == nbsn]):
        suffix = '_{}'.format(i)
        trim_length = 16 - len(suffix)
        nbsn = bsn[:trim_length] + suffix
        i += 1
    return nbsn


def add_pbs_beam(b,el,i,newBeamSet,plan,bsName):

    global beamIsos
    global isoData

    # let's try to minimize the creation of duplicate isocenters
    lock.acquire()
    if b.Name not in beamIsos:
        beamIsos.append(b.Name)
        isoData = newBeamSet.CreateDefaultIsocenterData(
            Position=b.Position
        )


    bName = "{0}_{1}".format(str(i), str(el.Energy))
    newBeamSet.CreatePBSIonBeam(
        SnoutId=b.SnoutId,
        SpotTuneId=spotTuneId,
        RangeShifter="{:0.2f}".format(el.Energy),
        IsocenterData=isoData,
        Name=bName,
        GantryAngle=b.GantryAngle,
        CouchAngle=b.CouchAngle,
        CollimatorAngle=b.CollimatorAngle
    )

    newBeam = plan.BeamSets[bsName].Beams[bName]

    newBeamSet.Beams[bName].EditSnoutPosition(
        SnoutPosition=b.SnoutPosition
    )
    # if there is a block, let's create it
    if b.Block is not None:
        blockName = "{0}_Block".format(bName)
        newBeam.AddOrEditIonBlock(
            BlockName=blockName,
            MaterialName=b.Block.MaterialName,
            Thickness=b.Block.Thickness,
            MillingToolDiameter=b.Block.MillingToolDiameter
        )

        newBeam.Blocks[blockName].Contour = b.Block.Contour

    # lets add the spots

    xPos = [sp[0] for sp in el.SpotPositions]
    yPos = [sp[1] for sp in el.SpotPositions]
    weights = [sw / sum(el.SpotWeights) for sw in el.SpotWeights]

    newBeam.AddEnergyLayerWithSpots(
        Energy=staticEnergy,
        SpotPositionsX=xPos,
        SpotPositionsY=yPos,
        SpotWeights=weights
    )

    newBeam.BeamMU = b.Mu * sum(el.SpotWeights)
    newBeam.Segments[0].Spots.Weights = weights
    newBeam.Segments[0].RelativeWeight = 1.0
    lock.release()


class Objective(object):

    def __init__(self):
        self.FunctionType = None
        self.RoiName = None
        self.IsConstraint = False
        self.RestrictAllBeamsIndividually = None
        self.IsRobust = None
        self.RestrictToBeamSet = False
        self.UseRbeDose = False
        self.DoseLevel = None
        self.HighDoseLevel = None
        self.LowDoseLevel = None
        self.AdaptToTargetDoseLevels = False
        self.LowDoseDistance = None
        self.PercentVolume = None
        self.Weight = None
        self.EudParameterA = None
        self.PercentStdDeviation = None


class Beam(object):

    def __init__(self):
        self.Name = None
        self.Position = {}
        self.GantryAngle = None
        self.CollimatorAngle = None
        self.CouchRotationAngle = None
        self.CouchPitchAngle = None
        self.CouchRollAngle = None
        self.SnoutId = None
        self.SpotTuneId = None
        self.RangeShifter = None
        self.SnoutPosition = None
        self.Block = None
        self.EnergyLayers = None
        self.Mu = None


class EnergyLayer(object):

    def __init__(self):
        self.Energy = None
        self.SpotPositions = []
        self.SpotWeights = []
        self.RelativeWeight = None


class Block(object):

    def __init__(self):
        self.BlockName = None
        self.MaterialName = None
        self.Thickness = None
        self.MillingToolDiameter = None
        self.Contour = []


class Robustness(object):

    def __init__(self):
        self.PositionUncertaintyAnterior = None
        self.PositionUncertaintyPosterior = None
        self.PositionUncertaintySuperior = None
        self.PositionUncertaintyInferior = None
        self.PositionUncertaintyLeft = None
        self.PositionUncertaintyRight = None
        self.DensityUncertainty = None
        self.PositionUncertaintySetting = None
        self.IndependentLeftRight = None
        self.IndependentAnteriorPosterior = None
        self.IndependentSuperiorInferior = None
        self.NumberOfDiscretizationPoints = None
        self.IndependentBeams = None
        self.ComputeExactScenarioDoses = None
        self.NamesOfNonPlanningExaminations = []


class Beamset(object):

    def __init__(self):
        self.Name = None
        self.Number = None
        self.ExaminationName = None
        self.MachineName = None
        self.TreatmentTechnique = None
        self.PatientPosition = None
        self.NumberOfFractions = None
        self.Rx = None
        self.CreateSetupBeams = False
        self.UseLocalizationPointAsSetupIsocenter = False
        self.UseUserSelectedIsocenterSetupIsocenter = False # this should be added for 11B (12.0)
        self.Beams = []
        self.Objectives = []
        self.IsSFO = None
        self.IsRobust = None
        self.Robustness = None
        self.OptimizationParameters = None


class OptimizationParameters(object):

    def __init__(self):
        self.NumberOfIterationsBeforeSpotWeightBounding = 0
        self.SpotWeightLimits = {}
        self.SpotWeightLimitsMargin = None


class Rx(object):

    def __init__(self):
        self.RoiName = None
        self.PrescriptionType = None
        self.DoseVolume = None
        self.DoseValue = None
        self.RelativePrescriptionLevel = None
        self.AutoScaleDose = False

# -----------------------
# OBSERVE: The script would probably generate the wrong isocenter if patient is not HFS.
# -----------------------
def main():
    # Check if a patient is loaded
    try:
        machine_db = get_current('MachineDB')
        patient = get_current('Patient')
        ui = get_current('ui')
        _version = ui.GetApplicationVersion().split('.')
        version = int(_version[0]) if int(_version[1]) != 99 else int(_version[0]) + 1
        subversion = int(_version[1])
    except:
        raise IOError('You must load a patient first')

    poIndex = 0
    opoIndex = 0

    #check the version of RayStation
    if version > 4:
        root = get_current('Case')
    else:
        root = get_current('Patient')

    dialog = MyWindow()
    dialog.ShowDialog()

    reg = None

    if dialog.DialogResult:
        # Are we copying or merging?
        if dialog.mode == 'copy':
            originalPlan = root.TreatmentPlans[dialog.p2cCB.Text]
            replanCTName = dialog.NewDatasetListBox.SelectedItem
            replanName = dialog.NewPlanNameTextBox.Text

            examination = [e for e in root.Examinations if e.Name == replanCTName]
            originalPlanCTName = \
                originalPlan.BeamSets[0].GetPlanningExamination().Name

            # Does a registration exist? We will use this to maintain copy vs merge state
            reg = root.GetTransformForExaminations(
                FromExamination=originalPlanCTName,
                ToExamination=replanCTName
            )
            if version >= 11:
                # if reg == None:
                if reg.all() == None:
                    print ('********************')
                    print ('Registration missing')
                    print ('********************')
                    import sys

                    sys.exit()
            else:
                if reg == None:
                    print ('********************')
                    print ('Registration missing')
                    print ('********************')
                    import sys

                    sys.exit()

            # if a plan with the same name exists, rename the new plan to include 5 random characters
            replanName = getPlanName(replanName)

            # lets create the copy plan
            replan = root.AddNewPlan(PlanName=replanName, PlannedBy='', Comment='',
                                     ExaminationName=replanCTName,
                                     AllowDuplicateNames=False)
            # if version >= 10 and subversion == 1 or version >= 11:
            #     pass # needs to be done per beamset in these versions
            if not (version >= 10 and subversion == 1 or version >= 11):
                dg = originalPlan.GetDoseGrid()
                # patient.Cases[0].TreatmentPlans[0].BeamSets[0].FractionDose.InDoseGrid
                replan.SetDefaultDoseGrid(
                    VoxelSize={
                        'x': dg.VoxelSize.x,
                        'y': dg.VoxelSize.y,
                        'z': dg.VoxelSize.z
                    }
                )

            beamSets = originalPlan.BeamSets

        # if not copy then must be merge
        else:
            originalPlan = root.TreatmentPlans[dialog.p2cfCB.Text]
            beamSets = [originalPlan.BeamSets[item] for item in dialog.bsLB.SelectedItems]
            replan = root.TreatmentPlans[dialog.p2c2CB.Text]
            if version >= 10 and subversion == 1 or version >= 11:
                # originalPlan.TreatmentCourse.TreatmentFractions[0].BeamSet.FractionDose.OnDensity.FromExamination.Name
                replanCTName = originalPlan.TreatmentCourse.TotalDose.WeightedDoseReferences[0].DoseDistribution.OnDensity.FromExamination.Name
            else:
            # if not (version >= 10 and subversion == 1 or version >= 11):
                replanCTName = originalPlan.TreatmentCourse.TotalDose.OnDensity.FromExamination.Name
            examination = [e for e in root.Examinations if e.Name == replanCTName]
            inrange = True
            i = 0
            while inrange:
                try:
                    replan.PlanOptimizations[i]
                    i += 1
                    poIndex = i
                except:
                    inrange = False
            for (i,_po) in enumerate(originalPlan.PlanOptimizations):
                try:
                    if _po.OptimizedBeamSets[0].DicomPlanLabel == beamSets[0].DicomPlanLabel:
                        opoIndex = i
                except:
                    pass

    # user probably canceled so lets exit
    else:
        sys.exit()

    for bs in beamSets:
        if version >= 11:
            rx = bs.Prescription.PrimaryPrescriptionDoseReference
        else:
            rx = bs.FractionDose.ForBeamSet.Prescription.PrimaryDosePrescription
        name = bs.DicomPlanLabel
        machineName = bs.MachineReference.MachineName
        try:
            machine = machine_db.GetTreatmentMachine(machineName = machineName)
        except:
            machine = machine_db.GetTreatmentMachine(machineName=machineName,lockMode='Read')
        modality = bs.Modality
        patientPosition = bs.PatientPosition
        fractions = bs.FractionationPattern.NumberOfFractions
        TT = TreatmentTechnique(bs)
        if 'conformal' in TT.lower():
            for beam in bs.Beams:
                if beam.Segments.Count > 1:
                    print ('********************')
                    print ('Please unmerge any merged beams before running this script')
                    print ('********************')
                    MessageBox.Show('Please unmerge any merged beams before running this script')
                    exit(0)

        # if the beamset name exists we will add 5 random characters to maintain uniquesness
        # for bscheck in replan.BeamSets:
        #     if bs.DicomPlanLabel == bscheck.DicomPlanLabel:
        #         name += ''.join(choice(ascii_uppercase) for i in range(5))
        #         break
        name = getBeamSetName(bs.DicomPlanLabel)
        # lets create the beamset
        NBSargs = {'Name': name,
                                'ExaminationName': replanCTName,
                                'MachineName': machineName,
                                'Modality': modality,
                                'TreatmentTechnique': TT,
                                'PatientPosition': patientPosition,
                                'NumberOfFractions': fractions,
                                'CreateSetupBeams': False,
                                'Comment': ''}
        if version >= 10 and subversion == 1 or version >= 11:
            NBSargs['RbeModelName'] = None
            NBSargs['EnableDynamicTrackingForVero'] = False
            NBSargs['NewDoseSpecificationPointNames'] = []
            NBSargs['NewDoseSpecificationPoints'] = []
            NBSargs['MotionSynchronizationTechniqueSettings'] = {'DisplayName': None,
                                                      'MotionSynchronizationSettings': None,
                                                      'RespiratoryIntervalTime': None,
                                                      'RespiratoryPhaseGatingDutyCycleTimePercentage': None,
                                                      'MotionSynchronizationTechniqueType': 'Undefined'},
            NBSargs['Custom'] = ''
        if version >= 10 and subversion == 1: # 3.0.9
            NBSargs['MotionSynchronizationTechniqueSettings'] = { 'DisplayName': None,
                                                                   'MotionSynchronizationSettings': None,
                                                                   'RespiratoryIntervalTime': None,
                                                                   'RespiratoryPhaseGatingDutyCycleTimePercentage': None
                                                                  }
            NBSargs['Custom'] = None
        if version >= 11:
            NBSargs['MotionSynchronizationTechniqueSettings'] = \
                                                     {'DisplayName': None, 'MotionSynchronizationSettings': None,
                                                      'RespiratoryIntervalTime': None,
                                                      'RespiratoryPhaseGatingDutyCycleTimePercentage': None,
                                                      'MotionSynchronizationTechniqueType': "Undefined"}
            NBSargs['ToleranceTableLabel'] = None


        rpbs = replan.AddNewBeamSet(**NBSargs)
        # define dose grid if not done at plan level prior (>=10B)
        if version >= 10 and subversion == 1 or version >= 11:
            dg = bs.GetDoseGrid()
            rpbs.SetDefaultDoseGrid(
                VoxelSize={
                    'x': dg.VoxelSize.x,
                    'y': dg.VoxelSize.y,
                    'z': dg.VoxelSize.z
                }
            )

        if modality == 'Electrons':
            for beam in bs.Beams:
                has_cutout = True
                CEBargs = {
                    'Name': beam.Name,
                    'GantryAngle': beam.GantryAngle,
                    'ApplicatorName': beam.Applicator.ElectronApplicatorName,
                }
                try:
                    CEBargs['InsertName'] = beam.Applicator.Insert.Name
                    CEBargs['IsAddCutoutChecked'] = True

                except:
                    CEBargs['IsAddCutoutChecked'] = False
                    has_cutout = False

                if version > 8:
                    CEBargs['BeamQualityId'] = beam.BeamQualityId
                    CEBargs['CouchPitchAngle'] = beam.CouchPitchAngle
                    CEBargs['CouchRollAngle'] = beam.CouchRollAngle
                    try:
                        CEBargs['CouchRotationAngle'] = beam.CouchRotationAngle
                    except:
                        CEBargs['CouchAngle'] = beam.CouchAngle
                else:
                    CEBargs['Energy'] = beam.MachineReference.Energy
                    CEBargs['CouchAngle'] = beam.CouchAngle

                if version > 4:
                    iso = beam.Isocenter.Position
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CEBargs['IsocenterData'] = bs.CreateDefaultIsocenterData(Position=isocenter)

                else:
                    iso = beam.PatientToBeamMapping.IsocenterPoint
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CEBargs['Isocenter'] = isocenter

                newBeam = rpbs.CreateElectronBeam(**CEBargs)
                if has_cutout:
                    contour = [{'x':c.x, 'y':c.y} for c in beam.Applicator.Insert.Contour]
                    newBeam.Applicator.Insert.Contour = contour
                newBeam.BeamMU = beam.BeamMU

        # not an electron, is it protons?
        elif TT == 'ProtonPencilBeamScanning':
            beamSet = Beamset()
            beams = []
            beamIsos = []
            objectives = []
            is_robust = False
            rx = Rx()
            optimization_parameters = OptimizationParameters()

            beamSet.Name = rpbs.DicomPlanLabel
            beamSet.Number = rpbs.Number
            beamSet.ExaminationName = rpbs.GetPlanningExamination().Name
            beamSet.MachineName = rpbs.MachineReference.MachineName
            beamSet.TreatmentTechnique = "ProtonPencilBeamScanning"
            beamSet.PatientPosition = rpbs.PatientPosition
            beamSet.NumberOfFractions = rpbs.FractionationPattern.NumberOfFractions
            beamSet.CreateSetupBeams = rpbs.PatientSetup.UseSetupBeams
            if version >= 12: # boolean flags for setup change in 11B
                if patient.Cases[0].TreatmentPlans[2].BeamSets[0].PatientSetup.IsocenterType == 'LocalizationPoint':
                    beamSet.UseLocalizationPointAsSetupIsocenter = True
                    beamSet.UseUserSelectedIsocenterSetupIsocenter = False
                elif patient.Cases[0].TreatmentPlans[2].BeamSets[0].PatientSetup.IsocenterType == 'TreatmentIsocenter':
                    beamSet.UseLocalizationPointAsSetupIsocenter = False
                    beamSet.UseUserSelectedIsocenterSetupIsocenter = True
                else: # by default it is false false?
                    beamSet.UseLocalizationPointAsSetupIsocenter = False
                    beamSet.UseUserSelectedIsocenterSetupIsocenter = False
            else:
                beamSet.UseLocalizationPointAsSetupIsocenter = bs.PatientSetup.UseLocalizationPointAsSetupIsocenter
            beamSet.IsRobust = False

            # let's build our beam objects and make logical checks on the beams
            for b in bs.Beams:
                # if b.RangeShifterId is not None:
                #     raise IOError(
                #         "The use of RangeShifters in the initialization plan is not permitted.")
                if b.Segments.Count == 0:
                    raise IOError("Not all beams have energy layers.")

                beam = Beam()

                beam.Name = b.Name
                beam.Position = {
                    'x': b.Isocenter.Position.x,
                    'y': b.Isocenter.Position.y,
                    'z': b.Isocenter.Position.z
                }
                beam.GantryAngle = b.GantryAngle
                beam.CollimatorAngle = b.InitialCollimatorAngle
                beam.CouchRotationAngle = b.CouchRotationAngle
                beam.CouchPitchAngle = b.CouchPitchAngle
                beam.CouchRollAngle = b.CouchRollAngle
                beam.SnoutId = b.SnoutId
                beam.SnoutPosition = b.SnoutPosition
                beam.SpotTuneId = b.Segments[0].Spots.SpotTuneId
                beam.EnergyLayers = get_energy_layers(b.Segments)
                beam.Mu = b.BeamMU
                if b.RangeShifterId is not None:
                    beam.RangeShifter = [
                        rs.Name for rs in machine.RangeShifters
                        if rs.RangeShifterId == b.RangeShifterId
                        ][0]

                # if the beam has a block, let's make a block object to add to the
                # beam
                if b.Blocks.Count != 0:
                    block = Block()
                    block.BlockName = "{0}_Block".format(b.Name)
                    block.MaterialName = b.Blocks[0].Material.Name
                    block.MillingToolDiameter = b.Blocks[0].MillingToolDiameter
                    block.Thickness = b.Blocks[0].Thickness
                    block.Contour = [
                        {
                            'x': c.x,
                            'y': c.y
                        }
                        for c in b.Blocks[0].Contour
                        ]

                    beam.Block = block

                # let's add this beam to the list of beams for this beamset
                beams.append(beam)

            beamSet.Beams = beams

            # let's get the index of the PlanOptimization
            for pbsPoIndex, po in enumerate(originalPlan.PlanOptimizations):
                if po.OptimizedBeamSets[0].DicomPlanLabel == bs.DicomPlanLabel:
                    bsNumber = pbsPoIndex

            swl = originalPlan.PlanOptimizations[bsNumber].OptimizationParameters.PencilBeamScanningProperties.SpotWeightLimits
            optimization_parameters.SpotWeightLimits = {'x': swl.x, 'y': swl.y}
            optimization_parameters.SpotWeightLimitsMargin = \
                originalPlan.PlanOptimizations[bsNumber].OptimizationParameters.PencilBeamScanningProperties.SpotWeightLimitsMargin

            beamSet.OptimizationParameters = optimization_parameters

            # if there are non-constraint objectives, let's build our objective
            if originalPlan.PlanOptimizations[bsNumber].Objective.ConstituentFunctions.Count > 0:
                for i, ob in enumerate(originalPlan.PlanOptimizations[bsNumber].Objective.ConstituentFunctions):
                    objective = Objective()
                    try:
                        objective.FunctionType = ob.DoseFunctionParameters.FunctionType
                        objective.DoseLevel = ob.DoseFunctionParameters.DoseLevel
                        objective.PercentVolume = ob.DoseFunctionParameters.PercentVolume
                    except:
                        if hasattr(ob.DoseFunctionParameters, 'AdaptToTargetDoseLevels'):
                            objective.FunctionType = "DoseFallOff"
                            objective.AdaptToTargetDoseLevels = ob.DoseFunctionParameters.AdaptToTargetDoseLevels
                            objective.HighDoseLevel = ob.DoseFunctionParameters.HighDoseLevel
                            objective.LowDoseLevel = ob.DoseFunctionParameters.LowDoseLevel
                            objective.LowDoseDistance = ob.DoseFunctionParameters.LowDoseDistance
                        elif hasattr(ob.DoseFunctionParameters, 'PercentStdDeviation'):
                            objective.FunctionType = "UniformityConstraint"
                            objective.PercentStdDeviation = ob.DoseFunctionParameters.PercentStdDeviation
                        else:
                            objective.FunctionType = ob.DoseFunctionParameters.FunctionType
                            objective.DoseLevel = ob.DoseFunctionParameters.DoseLevel
                            objective.EudParameterA = ob.DoseFunctionParameters.EudParameterA
                    objective.RoiName = ob.ForRegionOfInterest.Name
                    objective.RestrictAllBeamsIndividually = False
                    objective.IsConstraint = False
                    objective.IsRobust = ob.UseRobustness
                    objective.Weight = ob.DoseFunctionParameters.Weight
                    if objective.IsRobust:
                        is_robust = True


                    objectives.append(objective)

            else:
                i = 0

            # if there are constraint objectives, let's build our objective objects
            # and make logical checks
            if originalPlan.PlanOptimizations[bsNumber].Constraints.Count > 0:
                for j, ob in enumerate(originalPlan.PlanOptimizations[bsNumber].Constraints):
                    objective = Objective()
                    try:
                        objective.FunctionType = ob.DoseFunctionParameters.FunctionType
                        objective.DoseLevel = ob.DoseFunctionParameters.DoseLevel
                        objective.PercentVolume = ob.DoseFunctionParameters.PercentVolume
                    except:
                        if hasattr(ob.DoseFunctionParameters, 'AdaptToTargetDoseLevels'):
                            objective.FunctionType = "DoseFallOff"
                            objective.AdaptToTargetDoseLevels = ob.DoseFunctionParameters.AdaptToTargetDoseLevels
                            objective.HighDoseLevel = ob.DoseFunctionParameters.HighDoseLevel
                            objective.LowDoseLevel = ob.DoseFunctionParameters.LowDoseLevel
                            objective.LowDoseDistance = ob.DoseFunctionParameters.LowDoseDistance
                        elif hasattr(ob.DoseFunctionParameters, 'PercentStdDeviation'):
                            objective.FunctionType = "UniformityConstraint"
                            objective.PercentStdDeviation = ob.DoseFunctionParameters.PercentStdDeviation
                        else:
                            objective.FunctionType = ob.DoseFunctionParameters.FunctionType
                            objective.DoseLevel = ob.DoseFunctionParameters.DoseLevel
                            objective.EudParameterA = ob.DoseFunctionParameters.EudParameterA
                    objective.RoiName = ob.ForRegionOfInterest.Name
                    objective.IsConstraint = True
                    objective.IsRobust = ob.UseRobustness
                    if objective.IsRobust:
                        is_robust = True
                    objective.Weight = ob.DoseFunctionParameters.Weight
                    objective.RestrictAllBeamsIndividually = False

                objectives.append(objective)

            # let's add the objective objects to our beamset object
            beamSet.Objectives = objectives

            # if the plan is robust, we need to copy the robust optimization
            # parameters
            if is_robust:
                rp = originalPlan.PlanOptimizations[
                    bsNumber].OptimizationParameters.RobustnessParameters
                robustness = Robustness()
                robustness.PositionUncertaintyAnterior = rp.PositionUncertaintyParameters.PositionUncertaintyAnterior
                robustness.PositionUncertaintyInferior = rp.PositionUncertaintyParameters.PositionUncertaintyInferior
                robustness.PositionUncertaintyPosterior = rp.PositionUncertaintyParameters.PositionUncertaintyPosterior
                robustness.PositionUncertaintySuperior = rp.PositionUncertaintyParameters.PositionUncertaintySuperior
                robustness.PositionUncertaintyLeft = rp.PositionUncertaintyParameters.PositionUncertaintyLeft
                robustness.PositionUncertaintyRight = rp.PositionUncertaintyParameters.PositionUncertaintyRight
                robustness.PositionUncertaintySetting = rp.PositionUncertaintyParameters.PositionUncertaintySetting
                robustness.IndependentLeftRight = rp.PositionUncertaintyParameters.IndependentLeftRight
                robustness.IndependentAnteriorPosterior = rp.PositionUncertaintyParameters.IndependentAnteriorPosterior
                robustness.IndependentSuperiorInferior = rp.PositionUncertaintyParameters.IndependentSuperiorInferior
                robustness.DensityUncertainty = rp.DensityUncertaintyParameters.DensityUncertainty
                robustness.NumberOfDiscretizationPoints = rp.DensityUncertaintyParameters.NumberOfDiscretizationPoints
                robustness.ComputeExactScenarioDoses = rp.RobustComputationSettings.ComputeExactScenarioDoses
                robustness.NamesOfNonPlanningExaminations = [e.Name for e in rp.PatientGeometryUncertaintyParameters.Examinations]

                # let's add the robustness object to the beamset object
                beamSet.Robustness = robustness
                beamSet.IsRobust = True

            newBeamSet = rpbs

            # let's add the beams
            for b in beamSet.Beams:

                if b.Name not in beamIsos:
                    beamIsos.append(b.Name)
                    isocenter = b.Position
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x': iso.x,
                            'y': iso.y,
                            'z': iso.z
                        }
                    isoData = newBeamSet.CreateDefaultIsocenterData(
                        Position=isocenter
                    )

                newBeam = newBeamSet.CreatePBSIonBeam(
                    SnoutId=b.SnoutId,
                    SpotTuneId=b.SpotTuneId,
                    RangeShifter=b.RangeShifter,
                    IsocenterData=isoData,
                    Name=b.Name,
                    GantryAngle=b.GantryAngle,
                    CouchRotationAngle=b.CouchRotationAngle,
                    CouchPitchAngle=b.CouchPitchAngle,
                    CouchRollAngle=b.CouchRollAngle,
                    CollimatorAngle=b.CollimatorAngle
                )

                newBeam.EditSnoutPosition(
                    SnoutPosition=b.SnoutPosition
                )

                # if there is a block, let's create it
                if b.Block is not None:
                    blockName = "{0}_Block".format(b.Name)
                    newBeam.AddOrEditIonBlock(
                        BlockName=blockName,
                        MaterialName=b.Block.MaterialName,
                        Thickness=b.Block.Thickness,
                        MillingToolDiameter=b.Block.MillingToolDiameter
                    )

                    newBeam.Blocks[blockName].Contour = b.Block.Contour

                # lets add the spots
                for el in b.EnergyLayers:
                    xPos = [sp[0] for sp in el.SpotPositions]
                    yPos = [sp[1] for sp in el.SpotPositions]
                    # weights = [sw / sum(el.SpotWeights) for sw in el.SpotWeights]

                    newBeam.AddEnergyLayerWithSpots(
                        Energy=el.Energy,
                        SpotPositionsX=xPos,
                        SpotPositionsY=yPos,
                        SpotWeights=el.SpotWeights
                    )

                    newBeam.Segments[newBeam.Segments.Count-1].RelativeWeight = el.RelativeWeight

                newBeam.BeamMU = b.Mu

            # let's add the objectives
            for poIndex, po in enumerate(replan.PlanOptimizations):
                if po.OptimizedBeamSets[0].DicomPlanLabel == beamSet.Name:
                    print ("poIndex = " + str(poIndex))
                    bsNumber = poIndex
            iO = 0
            iC = 0
            for ob in beamSet.Objectives:
                ft = "TargetEud" if ob.FunctionType == "UniformEud" else ob.FunctionType
                replan.PlanOptimizations[bsNumber].AddOptimizationFunction(
                    FunctionType=ft,
                    RoiName=ob.RoiName,
                    IsConstraint=ob.IsConstraint,
                    RestrictAllBeamsIndividually=ob.RestrictAllBeamsIndividually,
                    IsRobust=ob.IsRobust
                )

                if ob.IsConstraint:
                    dFP = replan.PlanOptimizations[bsNumber].Constraints[iC].DoseFunctionParameters
                    iC += 1
                else:
                    dFP = replan.PlanOptimizations[bsNumber].Objective.ConstituentFunctions[iO].DoseFunctionParameters
                    iO += 1

                if ob.FunctionType == "DoseFallOff":
                    dFP.HighDoseLevel = ob.HighDoseLevel
                    dFP.LowDoseLevel = ob.LowDoseLevel
                    dFP.LowDoseDistance = ob.LowDoseDistance
                    dFP.AdaptToTargetDoseLevels = ob.AdaptToTargetDoseLevels
                    dFP.Weight = ob.Weight
                elif ob.FunctionType in ["UniformEud", "MaxEud", "MinEud"]:
                    dFP.DoseLevel = ob.DoseLevel
                    dFP.EudParameterA = ob.EudParameterA
                    dFP.Weight = ob.Weight
                elif ob.FunctionType == "UniformityConstraint":
                    dFP.PercentStdDeviation = ob.PercentStdDeviation
                    dFP.Weight = ob.Weight
                else:
                    dFP.DoseLevel = ob.DoseLevel
                    dFP.PercentVolume = ob.PercentVolume
                    dFP.Weight = ob.Weight

            replan.PlanOptimizations[
                bsNumber
            ].OptimizationParameters.PencilBeamScanningProperties.NumberOfIterationsBeforeSpotWeightBounding = \
                beamSet.OptimizationParameters.NumberOfIterationsBeforeSpotWeightBounding

            replan.PlanOptimizations[
                bsNumber
            ].OptimizationParameters.PencilBeamScanningProperties.SpotWeightLimits = \
                beamSet.OptimizationParameters.SpotWeightLimits

            replan.PlanOptimizations[
                bsNumber
            ].OptimizationParameters.PencilBeamScanningProperties.SpotWeightLimitsMargin = \
                beamSet.OptimizationParameters.SpotWeightLimitsMargin

            # let's check and add as appropriate the robustness parameters
            if beamSet.Robustness is not None:
                print ("Adding Robust Parameters")
                replan.PlanOptimizations[bsNumber].OptimizationParameters.SaveRobustnessParameters(
                    PositionUncertaintyAnterior=beamSet.Robustness.PositionUncertaintyAnterior,
                    PositionUncertaintyPosterior=beamSet.Robustness.PositionUncertaintyPosterior,
                    PositionUncertaintySuperior=beamSet.Robustness.PositionUncertaintySuperior,
                    PositionUncertaintyInferior=beamSet.Robustness.PositionUncertaintyInferior,
                    PositionUncertaintyLeft=beamSet.Robustness.PositionUncertaintyLeft,
                    PositionUncertaintyRight=beamSet.Robustness.PositionUncertaintyRight,
                    IndependentLeftRight=beamSet.Robustness.IndependentLeftRight,
                    IndependentAnteriorPosterior=beamSet.Robustness.IndependentAnteriorPosterior,
                    IndependentSuperiorInferior=beamSet.Robustness.IndependentSuperiorInferior,
                    DensityUncertainty=beamSet.Robustness.DensityUncertainty,
                    ComputeExactScenarioDoses=beamSet.Robustness.ComputeExactScenarioDoses,
                    NamesOfNonPlanningExaminations=beamSet.Robustness.NamesOfNonPlanningExaminations
                )

        # not an electron plan is it also not a VMAT?
        elif TT != 'VMAT':
            for beam in bs.Beams:
                CPBargs = {
                    'Name': beam.Name,
                    'GantryAngle': beam.GantryAngle,
                    'CollimatorAngle': beam.InitialCollimatorAngle,
                    }

                if version > 4:
                    iso = beam.Isocenter.Position
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CPBargs['IsocenterData'] = bs.CreateDefaultIsocenterData(Position=isocenter)

                else:
                    iso = beam.PatientToBeamMapping.IsocenterPoint
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CPBargs['Isocenter'] = isocenter

                if version > 8:
                    CPBargs['BeamQualityId'] = beam.BeamQualityId
                    CPBargs['CouchPitchAngle'] = beam.CouchPitchAngle
                    CPBargs['CouchRollAngle'] = beam.CouchRollAngle
                    try:
                        CPBargs['CouchRotationAngle'] = beam.CouchRotationAngle
                    except:
                        CPBargs['CouchAngle'] = beam.CouchAngle
                else:
                    CPBargs['Energy'] = beam.MachineReference.Energy
                    CPBargs['CouchAngle'] = beam.CouchAngle

                newBeam = rpbs.CreatePhotonBeam(**CPBargs)
                for (i, s) in enumerate(beam.Segments):
                    newBeam.CreateRectangularField()
                    newBeam.Segments[i].LeafPositions = s.LeafPositions
                    newBeam.Segments[i].JawPositions = s.JawPositions
                    newBeam.BeamMU = beam.BeamMU
                    newBeam.Segments[i].RelativeWeight = s.RelativeWeight

        # must be a VMAT
        else:
            for beam in bs.Beams:
                CABargs = {
                    'ArcStopGantryAngle': beam.ArcStopGantryAngle,
                    'ArcRotationDirection': beam.ArcRotationDirection,
                    'Name': beam.Name,
                    'GantryAngle': beam.GantryAngle,
                    'CollimatorAngle': beam.InitialCollimatorAngle,
                    }
                if version > 4:
                    iso = beam.Isocenter.Position
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CABargs['IsocenterData'] = bs.CreateDefaultIsocenterData(Position=isocenter)

                else:
                    iso = beam.PatientToBeamMapping.IsocenterPoint
                    isocenter = {
                        'x':iso.x,
                        'y':iso.y,
                        'z':iso.z
                    }

                    # check if copy or merge
                    if reg is not None:
                        iso = root.TransformPointFromExaminationToExamination(
                            FromExamination=originalPlanCTName,
                            ToExamination=replanCTName,
                            Point=isocenter
                        )
                        isocenter = {
                            'x':iso.x,
                            'y':iso.y,
                            'z':iso.z
                        }
                    CABargs['Isocenter'] = isocenter
                if version > 8:
                    CABargs['BeamQualityId'] = beam.BeamQualityId
                    CABargs['CouchPitchAngle'] = beam.CouchPitchAngle
                    CABargs['CouchRollAngle'] = beam.CouchRollAngle
                    try:
                        CABargs['CouchRotationAngle'] = beam.CouchRotationAngle
                    except:
                        CABargs['CouchAngle'] = beam.CouchAngle
                else:
                    CABargs['Energy'] = beam.MachineReference.Energy
                    CABargs['CouchAngle'] = beam.CouchAngle

                newBeam = rpbs.CreateArcBeam(**CABargs)

            # we cannot create controlpoints directly
            createControlPoints(rx.DoseValue)
            poIndex += 1

            # lets copy the old segments to the new segments
            for (i, beam) in enumerate(bs.Beams):
                rpbs.Beams[i].BeamMU = beam.BeamMU

                for (j, s) in enumerate(beam.Segments):
                    rpbs.Beams[i].Segments[j].LeafPositions = \
                        s.LeafPositions
                    rpbs.Beams[i].Segments[j].JawPositions = s.JawPositions
                    rpbs.Beams[i].Segments[j].DoseRate = s.DoseRate
                    rpbs.Beams[i].Segments[j].RelativeWeight = \
                        s.RelativeWeight

    # lets compute the beams
    # for bs in replan.BeamSets:
    #     if bs.Modality != 'Electrons':
    #         if bs.Beams.Count != 0:
    #             bs.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose', ForceRecompute=True)
    #     else:
    #         print ('Electron BeamSet - set histories, prescription and compute')

    patient.Save()


if __name__ == '__main__':
    main()

