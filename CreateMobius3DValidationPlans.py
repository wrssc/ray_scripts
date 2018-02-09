""" Create Mobius3D Simple Validation Plans
    
    This script creates a series of Mobius3D validation plans. See the Mobius3D
    Commissioning Report for a description of each plan and the plan/beamset/beam
    naming convention. Once each beamset is completed, dose is computed and the
    plan is exported to the DICOM destination.
    
    To run this script, you must first have a plan open that contains a
    homogeneous phantom (see the associated script CreateReferenceCT.py, which
    creates a homogeneous CT) external contour, and two heterogeneity contours named 
    Box_1 and Box_2. The script will change the density of the two boxes during execution,
    so any density overrides for the surrounding phantom should exclude these ROIs. The CT 
    must be at least 60x40x60 cm in the LR/AP/SI dimensions. 
    
    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__date__ = '2018-01-16'

__version__ = '1.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'N/A'

__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.1.1.2'
__maintainer__ = 'Mark Geurts'

__email__ =  'mark.w.geurts@gmail.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements
from connect import *
from time import sleep

from math import sqrt, pow

# Define calcs and export flags (set to True to calculate dose and export)
calc = True
export = True

# Define list of machines
machines = ['TrueBeam', 'TrueBeamSTx']

# Define list of energies for each machine
photons = [6, 10, 15]

# Define number of MU within each field
mu = 100

# Define the Mobius3D server details
host = 'mobius.uwhealth.wisc.edu'
port = 104
aet = 'MOBIUS3D'

# Define standard MLC leaf center distance from isocenter, in cm
leafcen = [-19.5, -18.5, -17.5, -16.5, -15.5, -14.5, -13.5, -12.5, -11.5, -10.5, \
           -9.75, -9.25, -8.75, -8.25, -7.75, -7.25, -6.75, -6.25, -5.75, -5.25, \
           -4.75, -4.25, -3.75, -3.25, -2.75, -2.25, -1.75, -1.25, -0.75, -0.25, \
           0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25, 4.75, \
           5.25, 5.75, 6.25, 6.75, 7.25, 7.75, 8.25, 8.75, 9.25, 9.75, \
           10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5]

# Define STx leaf center distances
leafcenstx = [-10.75, -10.25, -9.75, -9.25, -8.75, -8.25, -7.75, -7.25, -6.75, -6.25, \
              -5.75, -5.25, -4.75, -4.25, -3.875, -3.625, -3.375, -3.125, -2.875, -2.625, \
              -2.375, -2.125, -1.875, -1.625, -3.375, -1.125, -0.875, -0.625, -0.375, -0.125, \
              0.125, 0.375, 0.625, 0.875, 1.125, 1.375, 1.625, 1.875, 2.125, 2.375, \
              2.625, 2.875, 3.125, 3.375, 3.625, 3.875, 4.25, 4.75, 5.25, 5.75, \
              6.25, 6.75, 7.25, 7.75, 8.25, 8.75, 9.25, 9.75, 10.25, 10.75]

# Get current patient, case
patient = get_current('Patient')
case = get_current('Case')

# Store original patient name and ID
name = patient.PatientName

# Loop through each beam
for m in machines:
    
    # Loop through each photon energy
    for e in photons:
        
        # Change name and prompt user to change patient ID in prep for export
        if export:
            patient.PatientName = 'M3D {} {} MV'.format(m, e)
            await_user_input('Change patient ID')
    
        # Create 6.1 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.1 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.1 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.1 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
    
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})
        
        # Define field sizes
        jaws = [2, 5, 10, 15, 20, 30, 40]
        
        # Loop through each field size
        for j in jaws:
        
            # Check if beamset exists
            info = plan.QueryBeamSetInfo(Filter={'Name':'{} x {}'.format(j, j)})
            if not info:
        
                # Add beamset
                print 'Creating beamset for {} x {}'.format(j, j)
                beamset = plan.AddNewBeamSet(Name='{} x {}'.format(j, j), \
                    ExaminationName=case.Examinations[0].Name, \
                    MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                    PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                    CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                    Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)
        
                # Add beam
                print 'Creating beam {} x {}'.format(j, j)
                beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                    'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                    'Name': '{} x {}'.format(j, j), 'Color': \
                    '98,184,234'}, Name='{} x {}'.format(j, j), \
                    Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=0)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=j, Height=j, CenterCoordinate={'x': \
                    0, 'y': 0}, MoveMLC=False, MoveAllMLCLeaves=False, MoveJaw=True, \
                    JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                    PreventExtraLeafPairFromOpening=False)
                beamset.Beams['{} x {}'.format(j, j)].BeamMU=mu
            
                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()
        
                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                           CallingAETitle='RayStation', CalledAETitle=aet, \
                           Examinations=[case.Examinations[0].Name], \
                           RtStructureSetsReferencedFromBeamSets = \
                           [beamset.BeamSetIdentifier()], \
                           BeamSets=[beamset.BeamSetIdentifier()], \
                           BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                           DicomFilter='', IgnorePreConditionWarnings=True)
                
                    except SystemError as error:
                        print str(error)
            
                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)
        
        # Create 6.3 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.3 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.3 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.3 {} {}'.format(m, e), PlannedBy='', \
            Comment='', ExaminationName=case.Examinations[0].Name, \
            AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
    
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})
        
        # Define EDWs
        edws = [10, 15, 20, 25, 30, 45, 60]
        
        # Loop through each EDW
        for w in edws:
        
            # Check if beamset exists
            info = plan.QueryBeamSetInfo(Filter={'Name':'{}'.format(w)})
            if not info:
            
                # Add beamset
                print 'Creating beamset for EDW{}OUT'.format(w)
                beamset = plan.AddNewBeamSet(Name='{}'.format(w), \
                    ExaminationName=case.Examinations[0].Name, \
                    MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                    PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                    CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                    Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)
            
                # Add beam
                print 'Creating beam {}'.format(w)
                beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                    'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                    'Name': '{}'.format(w), 'Color': '98,184,234'}, Name='{}'.format(w), \
                    Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=90)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=40, Height=30, CenterCoordinate={'x': \
                    0, 'y': -5}, MoveMLC=False, MoveAllMLCLeaves=False, MoveJaw=True, \
                    JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                    PreventExtraLeafPairFromOpening=False)
                beamset.Beams['{}'.format(w)].BeamMU=mu
            
                # Display prompt reminding user to set EDW angles
                patient.Save()
                plan.SetCurrent()
                beamset.SetCurrent()
                await_user_input('Manually set wedge to EDW{}IN. Then continue.'.format(w))
                patient.Save()
            
                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()
            
                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                           CallingAETitle='RayStation', CalledAETitle=aet, \
                           Examinations=[case.Examinations[0].Name], \
                           RtStructureSetsReferencedFromBeamSets = \
                           [beamset.BeamSetIdentifier()], \
                           BeamSets=[beamset.BeamSetIdentifier()], \
                           BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                           DicomFilter='', IgnorePreConditionWarnings=True)

                    except SystemError as error:
                        print str(error)

                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)
        
        # Create 6.4 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.4 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.4 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.4 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
    
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})
        
        # Define SSDs
        ssds = [70, 85, 100, 115, 130]
        
        # Loop through each SSD
        for s in ssds:
        
            # Check if beamset exists
            info = plan.QueryBeamSetInfo(Filter={'Name':'{}'.format(s)})
            if not info:
            
                # Add beamset
                print 'Creating beamset for {}'.format(s)
                beamset = plan.AddNewBeamSet(Name='{}'.format(s), \
                    ExaminationName=case.Examinations[0].Name, \
                    MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                    PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                    CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                    Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)
            
                # Add beam
                print 'Creating beam {}'.format(s)
                beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                    'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                    'Name': '{}'.format(s), 'Color': '98,184,234'}, Name='{}'.format(s), \
                    Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=0)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=20, Height=20, CenterCoordinate={'x': \
                    0, 'y': 0}, MoveMLC=False, MoveAllMLCLeaves=False, MoveJaw=True, \
                    JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                    PreventExtraLeafPairFromOpening=False)
                beamset.Beams['{}'.format(s)].BeamMU=mu
            
                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()
            
                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                           CallingAETitle='RayStation', CalledAETitle=aet, \
                           Examinations=[case.Examinations[0].Name], \
                           RtStructureSetsReferencedFromBeamSets = \
                           [beamset.BeamSetIdentifier()], \
                           BeamSets=[beamset.BeamSetIdentifier()], \
                           BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                           DicomFilter='', IgnorePreConditionWarnings=True)

                    except SystemError as error:
                        print str(error)

                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)
        
        # Create 6.5 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.5 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.5 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.5 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
            
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})
        
        # Define angles
        angles = [0, 15, 30, 45, 60, 75]
        
        # Loop through each gantry angle
        for a in angles:
        
            # Check if beamset exists
            info = plan.QueryBeamSetInfo(Filter={'Name':'{}'.format(a)})
            if not info:
        
                # Add beamset
                print 'Creating beamset for {}'.format(a)
                beamset = plan.AddNewBeamSet(Name='{}'.format(a), \
                    ExaminationName=case.Examinations[0].Name, \
                    MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                    PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                    CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                    Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)
            
                # Add beam
                print 'Creating beam {}'.format(a)
                beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                    'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                    'Name': '{}'.format(a), 'Color': '98,184,234'}, Name='{}'.format(a), \
                    Description='', GantryAngle=a, CouchAngle=0, CollimatorAngle=0)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=10, Height=10, CenterCoordinate={'x': \
                    0, 'y': 0}, MoveMLC=False, MoveAllMLCLeaves=False, MoveJaw=True, \
                    JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                    PreventExtraLeafPairFromOpening=False)
                beamset.Beams['{}'.format(a)].BeamMU=mu
            
                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()
            
                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                           CallingAETitle='RayStation', CalledAETitle=aet, \
                           Examinations=[case.Examinations[0].Name], \
                           RtStructureSetsReferencedFromBeamSets = \
                           [beamset.BeamSetIdentifier()], \
                           BeamSets=[beamset.BeamSetIdentifier()], \
                           BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                           DicomFilter='', IgnorePreConditionWarnings=True)

                    except SystemError as error:
                        print str(error)

                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)

        # Create 6.6 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.6 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.6 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.6 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
            
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})
        
        # Define densities
        densities = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75]
        
        # Add beamset
        print 'Creating empty beamset'
        info = plan.QueryBeamSetInfo(Filter={'Name':'beam'})
        if not info:
            beamset = plan.AddNewBeamSet(Name='beam', \
                ExaminationName=case.Examinations[0].Name, \
                MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)
                
            # Add beam
            print 'Creating empty beam'
            beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                'Name': 'beam', 'Color': '98,184,234'}, Name='beam', \
                Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=0)
            beam.SetBolus(BolusName='')
            beam.CreateRectangularField(Width=10, Height=10, CenterCoordinate={'x': \
                0, 'y': 0}, MoveMLC=False, MoveAllMLCLeaves=False, MoveJaw=True, \
                JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                PreventExtraLeafPairFromOpening=False)
            beamset.Beams['beam'].BeamMU=mu
        
            # Loop through densities
            for d in densities:
        
                # Check if material already exists
                flag = True
                idx = 0
                try:
                    for i in range(0, 20):
                        if case.PatientModel.Materials[i].Name == 'Water':
                            water = case.PatientModel.Materials[i]
        
                        if case.PatientModel.Materials[i].Name == 'Water_{}'.format(d):
                            flag = False
                            idx = i
                            break
        
                except ValueError:
                    idx = i
        
                # Create material if it does not exist
                if flag:
                    case.PatientModel.CreateMaterial(BaseOnMaterial=water, \
                        Name='Water_{}'.format(d), MassDensityOverride=d)
        
                # Rename beamset and beam to density
                beamset.DicomPlanLabel = '{} g/cc'.format(d)
                beam.Name = '{} g/cc'.format(d)
        
                # Update density for box 1 and box 2
                case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_1'].OfRoi.SetRoiMaterial(\
                    Material=case.PatientModel.Materials[idx])
                case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_2'].OfRoi.SetRoiMaterial(\
                    Material=case.PatientModel.Materials[idx])
        
                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()
        
                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                           CallingAETitle='RayStation', CalledAETitle=aet, \
                           Examinations=[case.Examinations[0].Name], \
                           RtStructureSetsReferencedFromBeamSets = \
                           [beamset.BeamSetIdentifier()], \
                           BeamSets=[beamset.BeamSetIdentifier()], \
                           BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                           DicomFilter='', IgnorePreConditionWarnings=True)

                    except SystemError as error:
                        print str(error)
                
                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)    
        
            # Set box densities back to water
            case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_1'].OfRoi.SetRoiMaterial(\
                Material=water)
            case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_2'].OfRoi.SetRoiMaterial(\
                Material=water)
        
        # Create 6.7 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.7 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.7 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.7 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
            
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})

        # Define field sizes, in cm
        fields = [2, 5, 10, 15, 20, 30, 40]

        # Loop through each field size
        for f in fields:
            
            # Check if beamset exists
            info = plan.QueryBeamSetInfo(Filter={'Name':'{} cm'.format(f)})
            if not info:
            
                # Add beamset
                print 'Creating beamset for {} cm'.format(f)
                beamset = plan.AddNewBeamSet(Name='{} cm'.format(f), \
                    ExaminationName=case.Examinations[0].Name, \
                    MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                    PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                    CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                    Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)

                # Add beam
                print 'Creating beam {} cm'.format(f)
                beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                    'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                    'Name': '{} cm'.format(f), 'Color': \
                    '98,184,234'}, Name='{} cm'.format(f), \
                    Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=45)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=f, Height=f, CenterCoordinate={'x': \
                    0, 'y': 0}, MoveMLC=True, MoveAllMLCLeaves=False, MoveJaw=True, \
                    JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                    PreventExtraLeafPairFromOpening=False)
                beamset.Beams['{} cm'.format(f)].BeamMU=mu

                # Create circular MLC pattern
                leaves = beam.Segments[0].LeafPositions
                for l in range(len(leaves[0])):
                    if 'STx' in m:
                        d = abs(leafcenstx[l])
                
                    else:
                        d = abs(leafcen[l])
                
                    if d >= f/2:
                        leaves[0][l] = 0
                        leaves[1][l] = 0
                
                    else:
                        leaves[0][l] = -sqrt(max(pow(f/2,2) - pow(d,2), f/2 - 15))
                        leaves[1][l] = sqrt(max(pow(f/2,2) - pow(d,2), f/2 - 15))
            
                beam.Segments[0].LeafPositions = leaves

                # Calculate dose on beamset
                if calc:
                    print 'Calculating dose'
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    patient.Save()

                # Export beamset to the specified path
                if export:
                    print 'Exporting RT plan and beam dose'
                    try:
                        case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                            CallingAETitle='RayStation', CalledAETitle=aet, \
                            Examinations=[case.Examinations[0].Name], \
                            RtStructureSetsReferencedFromBeamSets = \
                            [beamset.BeamSetIdentifier()], \
                            BeamSets=[beamset.BeamSetIdentifier()], \
                            BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                            DicomFilter='', IgnorePreConditionWarnings=True)
                
                    except SystemError as error:
                        print str(error)

                    # Pause execution
                    print 'Waiting 60 seconds for Mobius3D to catch up'
                    sleep(60)

        # Create 6.8 plan
        info = case.QueryPlanInfo(Filter={'Name':'6.8 {} {}'.format(m, e)})
        if not info:
            print 'Creating plan for 6.8 {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='6.8 {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else:
            plan = case.LoadPlan(PlanInfo=info[0])
            
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -30, 'y': -0.2, 'z': -30}, \
            VoxelSize={'x': 0.2, 'y': 0.2, 'z': 0.2}, \
            NumberOfVoxels={'x': 300, 'y': 201, 'z': 300})

        # Add C Shape beamset
        info = plan.QueryBeamSetInfo(Filter={'Name':'C Shape'})
        if not info:
            print 'Creating beamset for C Shape'
            beamset = plan.AddNewBeamSet(Name='C Shape', \
                ExaminationName=case.Examinations[0].Name, \
                MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)

            # Add C Shape beam
            print 'Creating beam C Shape'
            beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                'Name': 'C Shape', 'Color': '98,184,234'}, Name='C Shape', \
                Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=90)
            beam.SetBolus(BolusName='')
            beam.CreateRectangularField(Width=22, Height=22, CenterCoordinate={'x': \
                0, 'y': 0}, MoveMLC=True, MoveAllMLCLeaves=True, MoveJaw=True, \
                JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                PreventExtraLeafPairFromOpening=False)
            beamset.Beams['C Shape'].BeamMU=mu

            # Create C Shape MLC pattern using inner and outer radii below (in cm)
            outer = 9
            inner = 4
            leaves = beam.Segments[0].LeafPositions
            for l in range(len(leaves[0])):
                if 'STx' in m:
                    d = abs(leafcenstx[l])

                else:
                    d = abs(leafcen[l])
        
                if d >= outer:
                    leaves[0][l] = 0
                    leaves[1][l] = 0

                elif d >= inner:
                    leaves[0][l] = -sqrt(pow(outer,2) - pow(d,2))
                    leaves[1][l] = sqrt(pow(outer,2) - pow(d,2))

                else:
                    leaves[0][l] = sqrt(pow(inner,2) - pow(d,2))
                    leaves[1][l] = sqrt(pow(outer,2) - pow(d,2))

            beam.Segments[0].LeafPositions = leaves

            # Calculate dose on beamset
            if calc:
                print 'Calculating dose'
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                patient.Save()

            # Export beamset to the specified path
            if export:
                print 'Exporting RT plan and beam dose'
                try:
                    case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                        CallingAETitle='RayStation', CalledAETitle=aet, \
                        Examinations=[case.Examinations[0].Name], \
                        RtStructureSetsReferencedFromBeamSets = \
                        [beamset.BeamSetIdentifier()], \
                        BeamSets=[beamset.BeamSetIdentifier()], \
                        BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                        DicomFilter='', IgnorePreConditionWarnings=True)
                
                except SystemError as error:
                    print str(error)
            
                # Pause execution
                print 'Waiting 60 seconds for Mobius3D to catch up'
                sleep(60)

        # Add Fence beamset
        info = plan.QueryBeamSetInfo(Filter={'Name':'Fence'})
        if not info:
            print 'Creating beamset for Fence'
            beamset = plan.AddNewBeamSet(Name='Fence', \
            ExaminationName=case.Examinations[0].Name, \
            MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
            PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
            CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
            Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)

            # Add Fence beam
            print 'Creating beam Fence'
            beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                'Name': 'Fence', 'Color': '98,184,234'}, Name='Fence', \
                Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=90)
            beam.SetBolus(BolusName='')
            beam.CreateRectangularField(Width=22, Height=22, CenterCoordinate={'x': \
                0, 'y': 0}, MoveMLC=True, MoveAllMLCLeaves=True, MoveJaw=True, \
                JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                PreventExtraLeafPairFromOpening=False)
            beamset.Beams['Fence'].BeamMU=mu

            # Create Fence MLC pattern using width and separation below (in cm)
            wid = 2
            sep = 4
            leaves = beam.Segments[0].LeafPositions
            for l in range(len(leaves[0])):
                if 'STx' in m:
                    d = abs(leafcenstx[l])

                else:
                    d = abs(leafcen[l])

                if d % sep < wid/2 or d % sep + wid/2 > sep:
                    leaves[0][l] = -wid
                    leaves[1][l] = wid

                else:
                    leaves[0][l] = -wid
                    leaves[1][l] = -wid

            beam.Segments[0].LeafPositions = leaves

            # Calculate dose on beamset
            if calc:
                print 'Calculating dose'
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                patient.Save()

            # Export beamset to the specified path
            if export:
                print 'Exporting RT plan and beam dose'
                try:
                    case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                        CallingAETitle='RayStation', CalledAETitle=aet, \
                        Examinations=[case.Examinations[0].Name], \
                        RtStructureSetsReferencedFromBeamSets = \
                        [beamset.BeamSetIdentifier()], \
                        BeamSets=[beamset.BeamSetIdentifier()], \
                        BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                        DicomFilter='', IgnorePreConditionWarnings=True)

                except SystemError as error:
                    print str(error)

                # Pause execution
                print 'Waiting 60 seconds for Mobius3D to catch up'
                sleep(60)

        # Add VMAT CP beamset
        info = plan.QueryBeamSetInfo(Filter={'Name':'VMAT CP'})
        if not info:
            print 'Creating beamset for VMAT CP'
            beamset = plan.AddNewBeamSet(Name='VMAT CP', \
                ExaminationName=case.Examinations[0].Name, \
                MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)

            # Add VMAT CP beam
            print 'Creating beam VMAT CP'
            beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                'Name': 'VMAT CP', 'Color': '98,184,234'}, Name='VMAT CP', \
                Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=90)
            beam.SetBolus(BolusName='')
            beam.CreateRectangularField(Width=22, Height=22, CenterCoordinate={'x': \
                0, 'y': 0}, MoveMLC=True, MoveAllMLCLeaves=True, MoveJaw=True, \
                JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                PreventExtraLeafPairFromOpening=False)
            beamset.Beams['VMAT CP'].BeamMU=mu

            # Apply VMAT CP pattern
            stda = [-3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, \
                    -3.71, -0.95, -1.5, -1.74, -2.15, -1.66, -1.13, -1.09, -1.35, -1.03, \
                    -0.59, -0.46, -0.44, -0.51, -0.56, -0.71, -0.53, -0.43, -0.33, -0.21, \
                    0.14, -0.25, -0.49, -0.88, -0.31, -0.26, -0.26, -0.47, -0.44, -0.44, \
                    -0.44, -0.44, -0.44, -0.51, -2.82, -3.03, -2.11, -0.78, -0.51, -0.82, \
                    -3.03, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71]
            stdb = [-3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, \
                    -3.71, -0.78, -0.81, -0.81, -0.74, -0.66, 0.29, 0.33, 0.26, 0.26, \
                    0.37, 0.43, 0.26, 0.26, 0.34, 0.28, -0.11, -0.08, -0.01, 0.19, \
                    0.44, 0.64, 0.9, 0.76, 0.86, 1.49, 1.21, 1.0, 0.31, 0.19, \
                    0.19, 0.19, 0.26, 0.32, 2.57, 2.97, 3.09, 3.09, 2.94, 2.59, \
                    2.2, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71]
            stxa = [-3.71, -3.71, -3.71, -0.95, -1.5, -1.74, -2.15, -1.66, -1.13, -1.09, \
                    -1.35, -1.03, -0.59, -0.46, -0.44, -0.44, -0.51, -0.51, -0.56, -0.59, \
                    -0.71, -0.71, -0.61, -0.53, -0.48, -0.43, -0.39, -0.33, -0.31, -0.21, \
                    0.14, 0.14, -0.25, -0.37, -0.49, -0.59, -0.9, -0.88, -0.39, -0.31, \
                    -0.26, -0.26, -0.26, -0.31, -0.47, -0.53, -0.44, -0.44, -0.44, -0.44, \
                    -0.44, -0.51, -2.82, -3.03, -2.11, -0.78, -0.51, -0.82, -3.12, -3.71]
            stxb = [-3.71, -3.71, -3.71, -0.78, -0.81, -0.81, -0.74, -0.66, 0.29, 0.33, \
                    0.26, 0.26, 0.37, 0.43, 0.26, 0.26, 0.26, 0.26, 0.34, 0.34, \
                    0.34, 0.28, -0.1, -0.11, -0.08, -0.06, -0.01, 0.04, 0.19, 0.26, \
                    0.44, 0.56, 0.64, 0.72, 0.91, 0.9, 0.76, 0.76, 0.86, 0.99, \
                    1.49, 1.51, 1.29, 1.21, 1.14, 1.00, 0.31, 0.19, 0.19, 0.19, \
                    0.26, 0.32, 1.57, 1.97, 3.09, 3.09, 2.94, 2.59, 2.41, -3.71]

            leaves = beam.Segments[0].LeafPositions

            for l in range(len(leaves[0])):
                if 'STx' in m:
                    leaves[0][l] = stxa[l]
                    leaves[1][l] = stxb[l]

                else:
                    leaves[0][l] = stda[l]
                    leaves[1][l] = stdb[l]

            beam.Segments[0].LeafPositions = leaves

            # Calculate dose on beamset
            if calc:
                print 'Calculating dose'
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                patient.Save()

            # Export beamset to the specified path
            if export:
                print 'Exporting RT plan and beam dose'
                try:
                    case.ScriptableDicomExport(AEHostname=host, AEPort=port, \
                        CallingAETitle='RayStation', CalledAETitle=aet, \
                        Examinations=[case.Examinations[0].Name], \
                        RtStructureSetsReferencedFromBeamSets = \
                        [beamset.BeamSetIdentifier()], \
                        BeamSets=[beamset.BeamSetIdentifier()], \
                        BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()], \
                        DicomFilter='', IgnorePreConditionWarnings=True)

                except SystemError as error:
                    print str(error)

# Restore original patient name
patient.PatientName = name

# Save patient
patient.Save()

print 'Done!'

