""" Create Mobius3D DLG Optimization Plans
    
    This RayStation TPS script creates a series of DLG test plans on a
    homogeneous phantom for each machine and photon energy. Test plans consist
    of a 10x10 jaw defined field with a series of MLC leaf gaps and offsets,
    similar to the method applied by Yao and Farr (2015), "Determining the
    optimal dosimetric leaf gap setting for rounded leaf-end multileaf collimator
    systems by simple test fields", JACMP 16(4): 5321.
    
    To run this script, you must first have a plan open that contains a
    homogeneous phantom (see the associated script CreateReferenceCT.py, which
    creates a homogeneous CT) and external contour. The CT must be at least
    20x20x20 cm in the LR/AP/SI dimensions. The script will create one plan for
    each machine/energy, and one beamset for each MLC pattern. After calculating
    dose, the script will pause and prompt you to set the DLG offset in Mobius3D
    to a specified value, then (after resuming) export each plan and pause to
    prompt you to set the DLG offset to the next value. To get Mobius3D to save
    each DLG offset plan set in a different patient, you will need to manually
    change the patient ID between each offset iteration (this cannot be scripted
    in RayStation currently).
    
    Finally, after all plans calculate in Mobius3D, you can run RetrieveDLGplans.py to 
    download all TPS and Mobius3D dose volumes to a specified folder and CompareLeafGaps.m 
    to evaluate them in MATLAB.
    
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
from time import sleep, strftime

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

# Get current patient, case
patient = get_current('Patient')
case = get_current('Case')

# Store original patient name
name = patient.PatientName

# Loop through each beam
for m in machines:
    
    # Loop through each photon energy
    for e in photons:
        
        # Check if plan exists, and either create one or load it
        info = case.QueryPlanInfo(Filter={'Name':'DLG {} {}'.format(m, e)})
        if not info
            print 'Creating plan for DLG {} {}'.format(m, e)
            plan = case.AddNewPlan(PlanName='DLG {} {}'.format(m, e), PlannedBy='', \
                Comment='', ExaminationName=case.Examinations[0].Name, \
                AllowDuplicateNames=False)

        else
            plan = case.LoadPlan(PlanInfo=info[0])
            
        # Set dose grid
        plan.UpdateDoseGrid(Corner={'x': -10, 'y': -0.1, 'z': -10}, \
            VoxelSize={'x': 0.1, 'y': 0.1, 'z': 0.1}, \
            NumberOfVoxels={'x': 200, 'y': 201, 'z': 200})
       
        # Define leaf gaps, offsets, and M3D iterations
        gaps = [0.5, 1.0, 1.5, 2.0]
        offsets = [0, 0.25, 0.5]
        iters = [0, 1, 2, 3]

        # Loop through gaps
        for g in gaps:
            
            # Loop through offsets
            for o in offsets:
                
                # Check if beam set exists
                info = plan.QueryBeamSetInfo(Filter={'Name':'{}mm-{}mm'.format(g*10, o*10)})
                if not info
                
                    # Add beamset
                    print 'Creating beamset for {}mm-{}mm'.format(g*10, o*10)
                    beamset = plan.AddNewBeamSet(Name='{}mm-{}mm'.format(g*10, o*10), \
                        ExaminationName=case.Examinations[0].Name, \
                        MachineName=m, Modality='Photons', TreatmentTechnique='Conformal', \
                        PatientPosition='HeadFirstSupine', NumberOfFractions=1, \
                        CreateSetupBeams=False, UseLocalizationPointAsSetupIsocenter=False, \
                        Comment='', RbeModelReference=None, EnableDynamicTrackingForVero=False)

                    # Add beam
                    print 'Creating beam {}mm-{}mm'.format(g*10, o*10)
                    beam = beamset.CreatePhotonBeam(Energy=e, IsocenterData={ \
                        'Position': {'x': 0, 'y': 0, 'z': 0}, 'NameOfIsocenterToRef': '', \
                        'Name': '{}mm-{}mm'.format(g*10, o*10), 'Color': \
                        '98,184,234'}, Name='{}mm-{}mm'.format(g*10, o*10), \
                        Description='', GantryAngle=0, CouchAngle=0, CollimatorAngle=0)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=10, Height=10, CenterCoordinate={'x': \
                        0, 'y': 0}, MoveMLC=False, MoveAllMLCLeaves=True, MoveJaw=True, \
                        JawMargins={'x': 0, 'y': 0}, DeleteWedge=False, \
                        PreventExtraLeafPairFromOpening=False)
                    beamset.Beams['{}mm-{}mm'.format(g*10, o*10)].BeamMU=mu

                    # Update MLC leaves
                    leaves = beam.Segments[0].LeafPositions
                    for l in range(len(leaves[0])):
                        if leaves[0][l] != leaves[1][l]:
                            if l % 2 == 0:
                                leaves[0][l] = -g/2 - o
                                leaves[1][l] = g/2 - o
                            else:
                                leaves[0][l] = -g/2
                                leaves[1][l] = g/2

                    beam.Segments[0].LeafPositions = leaves
                    
                    # Calculate dose on beamset
                    if calc:
                        print 'Calculating dose'
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        patient.Save()
                        
        # Loop through offsets
        if export:
            for i in iters:

                # Change patient name
                patient.PatientName = 'DLG {} {} MV {} mm'.format(m, e, i)

                # Prompt user to set DLG offset
                await_user_input('Set {} {} MV DLG offset to {} mm and change patient ID'.format(m, e, i))

                # Loop through gaps
                for g in gaps:
                    
                    # Loop through offsets
                    for o in offsets:

                        # Query beamset
                        info = plan.QueryBeamSetInfo(Filter={'Name':'{}mm-{}mm'.format(g*10, o*10)})
                        if not info
                            print 'WARNING! Beamset {}mm-{}mm not found'.format(g*10, o*10)
                            
                        else

                            # Get current beamset
                            beamset = plan.LoadBeamSet(BeamSetInfo = info[0])

                            # Export beamset to the specified pathd
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
                            print 'Waiting 120 seconds for Mobius3D to catch up'
                            sleep(120)

# Restore original patient name
patient.PatientName = name

# Save patient
patient.Save()

print 'Done!'

