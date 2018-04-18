""" Create Mobius3D Simple Validation Plans
    
    This script creates a series of Mobius3D validation plans. See the wiki page for a 
    description of each plan and the plan/beamset/beam naming convention. Once each 
    beamset is completed, dose is computed and the plan is exported to the DICOM 
    destination.
    
    To run this script, you must first have a plan open that contains a homogeneous 
    phantom (see the associated script CreateReferenceCT.py, which creates a 
    homogeneous CT), external contour, and two heterogeneity contours named Box_1 and 
    Box_2 with at least one structure overridden to water. The script will change the
    density of the two boxes during execution, so any density overrides for the
    surrounding phantom should exclude these ROIs. The CT must be at least 60x40x60 cm
    in the LR/AP/SI dimensions.
    
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
__version__ = '1.1.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Mobius3D-QA'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import sys
import connect
import UserInterface
import logging
import time
import re
import math

# Define Varian EDWIN names
edw_list = ['EDW10IN', 'EDW15IN', 'EDW20IN', 'EDW25IN', 'EDW30IN', 'EDW45IN', 'EDW60IN']


def main():

    # Get current patient, case, and machine DB
    machine_db = connect.get_current('MachineDB')
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient to be loaded')
        sys.exit('This script requires a patient to be loaded')

    # Start script status
    status = UserInterface.ScriptStatus(steps=['Verify CT density table, external, and boxes are set',
                                               'Enter script runtime options'],
                                        docstring=__doc__,
                                        help=__help__)

    # Confirm a CT density table, boxes, and external contour was set
    status.next_step(text='Prior to execution, the script will make sure that a CT density table, External, ' +
                          'and Box_1/Box_2 contours are set for the current plan. Also, at least one contour must be ' +
                          'overridden to water.')
    time.sleep(1)

    examination = connect.get_current('Examination')
    if examination.EquipmentInfo.ImagingSystemReference is None:
        connect.await_user_input('The CT imaging system is not set. Set it now, then continue the script.')
        patient.Save()

    else:
        patient.Save()

    external = False
    bounds = [-30, 30, 0, 40, -30, 30]
    boxes = [False, False]
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            external = True
            b = case.PatientModel.StructureSets[examination.Name].RoiGeometries[r.Name].GetBoundingBox()
            bounds = [b[0].x, b[1].x, b[0].y, b[1].y, b[0].z, b[1].z]

        if r.Name == 'Box_1':
            boxes[0] = True

        if r.Name == 'Box_2':
            boxes[1] = True

    # If external was not set
    if not external:
        logging.debug('Executing PatientModel.CreateRoi for External')
        external = case.PatientModel.CreateRoi(Name='External',
                                               Color='Blue',
                                               Type='External',
                                               TissueName='',
                                               RbeCellTypeName=None,
                                               RoiMaterial=None)

        logging.debug('Executing CreateExternalGeometry for External')
        external.CreateExternalGeometry(Examination=examination, ThresholdLevel=None)
        for r in case.PatientModel.RegionsOfInterest:
            if r.Type == 'External':
                b = case.PatientModel.StructureSets[examination.Name].RoiGeometries[r.Name].GetBoundingBox()
                bounds = [b[0].x, b[1].x, b[0].y, b[1].y, b[0].z, b[1].z]
                break

    # Set isocenter to the center of the top plane of the external structure
    iso = [(bounds[1]+bounds[0])/2, -bounds[2], (bounds[5]+bounds[4])/2]

    # Search for water density override
    water = None
    try:
        for i in range(20):
            if case.PatientModel.Materials[i].Name == 'Water':
                water = case.PatientModel.Materials[i]
                break

    except Exception:
        logging.warning('A water density override was not found')

    # If Box_1 or Box_2 don't exist
    if not boxes[0]:
        logging.debug('Adding Box_1 contour')
        box = case.PatientModel.CreateRoi(Name='Box_1',
                                          Color='Red',
                                          Type='Organ',
                                          TissueName=None,
                                          RbeCellTypeName=None,
                                          RoiMaterial=None)
        box.CreateBoxGeometry(Size={'x': abs(bounds[1]-bounds[0])-1, 'y': 5, 'z': abs(bounds[5]-bounds[4])-1},
                              Examination=examination,
                              Center={'x': 0, 'y': 5, 'z': 0},
                              Representation='Voxels',
                              VoxelSize=None)
        if water is not None:
            box.SetRoiMaterial(Material=water)

    if not boxes[1]:
        logging.debug('Adding Box_2 contour')
        box = case.PatientModel.CreateRoi(Name='Box_2',
                                          Color='Orange',
                                          Type='Organ',
                                          TissueName=None,
                                          RbeCellTypeName=None,
                                          RoiMaterial=None)
        box.CreateBoxGeometry(Size={'x': abs(bounds[1]-bounds[0])-1, 'y': 5, 'z': abs(bounds[5]-bounds[4])-1},
                              Examination=examination,
                              Center={'x': 0, 'y': 15, 'z': 0},
                              Representation='Voxels',
                              VoxelSize=None)
        if water is not None:
            box.SetRoiMaterial(Material=water)

    logging.debug('Saving patient')
    time.sleep(1)
    patient.Save()

    # If a water density override was not set, do so now
    if water is None:
        connect.await_user_input('Either Box_1 or Box_2 must be overridden to water. Do so, then continue the script')
        patient.Save()
        try:
            for i in range(20):
                if case.PatientModel.Materials[i].Name == 'Water':
                    water = case.PatientModel.Materials[i]
                    break

        except Exception:
            logging.error('A water density override was still not found')
            status.finish('Script cancelled, a water density override is required')

    # Prompt user to enter runtime options
    machines = machine_db.QueryCommissionedMachineInfo(Filter={})
    machine_list = []
    for i, m in enumerate(machines):
        if m['IsCommissioned']:
            machine_list.append(m['Name'])

    time.sleep(1)
    status.next_step(text='Next, fill in the runtime options and click OK to continue.')
    time.sleep(1)
    inputs = UserInterface.InputDialog(inputs={'a': 'Select machines to create plans for:',
                                               'b': 'Enter MU for each beam:',
                                               'c': '6.1 Enter open field jaw sizes (cm):',
                                               'd': '6.3 Select EDWs:',
                                               'e': '6.4 Enter SDDs (cm):',
                                               'f': '6.5 Enter oblique angles (deg):',
                                               'g': '6.6 Enter density overrides (g/cc):',
                                               'h': '6.7 Enter circular field MLC sizes (cm):',
                                               'i': '6.8 Select custom MLC shapes:',
                                               'j': 'Dose grid resolution (mm):',
                                               'k': 'Runtime options:',
                                               'l': 'Mobius3D host name/IP address:',
                                               'm': 'Mobius3D DICOM port:',
                                               'n': 'Mobius3D DICOM AE title:',
                                               'o': 'Time delay between DICOM exports (sec):'},
                                       datatype={'a': 'check', 'd': 'check', 'i': 'check', 'k': 'check'},
                                       initial={'a': machine_list,
                                                'b': '100',
                                                'c': '2, 5, 10, 15, 20, 30, 40',
                                                'd': edw_list,
                                                'e': '70, 85, 100, 115, 130',
                                                'f': '0, 15, 30, 45, 60, 75',
                                                'g': '0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75',
                                                'h': '2, 5, 10, 15, 20, 30, 40',
                                                'i': ['C Shape', 'Fence', 'VMAT CP'],
                                                'j': '2',
                                                'k': ['Calculate plan', 'Export plan'],
                                                'l': 'mobius.uwhealth.wisc.edu',
                                                'm': '104',
                                                'n': 'MOBIUS3D',
                                                'o': '60'},
                                       options={'a': machine_list,
                                                'd': edw_list,
                                                'i': ['C Shape', 'Fence', 'VMAT CP'],
                                                'k': ['Calculate plan', 'Export plan']},
                                       required=['a', 'b', 'j'])

    # Parse responses
    response = inputs.show()
    if response == {}:
        status.finish('Script cancelled, inputs were not supplied')
        sys.exit('Script cancelled')

    else:
        status.update_text(text='Parsing inputs...')
        
    machines = response['a']
    mu = float(response['b'])
    jaws = map(float, response['c'].split(','))
    edws = response['d']
    ssds = map(float, response['e'].split(','))
    angles = map(float, response['f'].split(','))
    densities = map(float, response['g'].split(','))
    fields = map(float, response['h'].split(','))
    shapes = response['i']
    res = float(response['j'])/10
    if 'Calculate plan' in response['k']:
        calc = True

    else:
        calc = False
        logging.info('Calculation was disabled')

    host = response['l']
    port = int(response['m'])
    aet = response['n']
    try:
        delay = float(response['o'])

    except ValueError:
        delay = 0

    # Append script status step list with each machine/energy
    for m in machines:
        machine = machine_db.GetTreatmentMachine(machineName=m, lockMode=None)
        for q in machine.PhotonBeamQualities:
            status.add_step('Create {} {} MV plans'.format(m, int(q.NominalEnergy)))

    # Validate export options
    if calc and 'Export plan' in response['k'] and response['l'] != '' and response['m'] != '' and response['n'] != '':
        export = True

    else:
        logging.info('Export was disabled, or export parameters were not specified')
        export = False

    # Start timer
    tic = time.time()
    counter = 0

    # Loop through each machine
    for m in machines:

        # Store machine DB record
        machine = machine_db.GetTreatmentMachine(machineName=m, lockMode=None)

        # Store SAD
        sad = machine.Physics.SourceAxisDistance

        # Store leaf centers
        leafcen = machine.Physics.MlcPhysics.LeafCenterPositions

        # Loop through energies
        for q in machine.PhotonBeamQualities:

            # Store nominal energy
            e = int(q.NominalEnergy)
            counter += 1

            # Create 6.1 plan
            time.sleep(1)
            status.next_step(text='Creating, calculating, and exporting the 6.1 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.1 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.1 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.1 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            logging.debug('Saving patient prior to SetCurrent(), SetDefaultDoseGrid() calls')
            patient.Save()
            plan.SetCurrent()
            logging.debug('Setting default dose grid with {} cm resolution'.format(res))
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Loop through each field size
            for j in jaws:

                # Check if beamset exists
                info = plan.QueryBeamSetInfo(Filter={'Name': '{} x {}'.format(j, j)})
                if not info:

                    # Add beamset
                    logging.debug('Creating beamset for {} x {}'.format(j, j))
                    beamset = plan.AddNewBeamSet(Name='{} x {}'.format(j, j),
                                                 ExaminationName=case.Examinations[0].Name,
                                                 MachineName=m,
                                                 Modality='Photons',
                                                 TreatmentTechnique='Conformal',
                                                 PatientPosition='HeadFirstSupine',
                                                 NumberOfFractions=1,
                                                 CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False,
                                                 Comment='',
                                                 RbeModelReference=None,
                                                 EnableDynamicTrackingForVero=False)

                    # Add beam
                    logging.debug('Creating beam {} x {}'.format(j, j))
                    beam = beamset.CreatePhotonBeam(Energy=e,
                                                    IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                                   'NameOfIsocenterToRef': '',
                                                                   'Name': '{} x {}'.format(j, j),
                                                                   'Color': '98,184,234'},
                                                    Name='{} x {}'.format(j, j),
                                                    Description='',
                                                    GantryAngle=0,
                                                    CouchAngle=0,
                                                    CollimatorAngle=0)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=j,
                                                Height=j,
                                                CenterCoordinate={'x': 0, 'y': 0},
                                                MoveMLC=False,
                                                MoveAllMLCLeaves=False,
                                                MoveJaw=True,
                                                JawMargins={'x': 0, 'y': 0},
                                                DeleteWedge=False,
                                                PreventExtraLeafPairFromOpening=False)
                    beamset.Beams['{} x {}'.format(j, j)].BeamMU = mu

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for plan {} x {}'.format(j, j))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for plan {} x {}'.format(j, j))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='',
                                                       IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

            # Create 6.3 plan
            status.update_text(text='Creating, calculating, and exporting the 6.3 plans. For each plan, you will ' +
                                    'need to manually set the EDW, then click Continue on the script panel.')
            info = case.QueryPlanInfo(Filter={'Name': '6.3 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.3 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.3 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            logging.debug('Saving patient prior to SetCurrent(), SetDefaultDoseGrid() calls')
            patient.Save()
            plan.SetCurrent()
            logging.debug('Setting default dose grid with {} cm resolution'.format(res))
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Loop through each EDW
            for w in edws:

                # Check if beamset exists
                info = plan.QueryBeamSetInfo(Filter={'Name': w})
                if not info:

                    # Add beamset
                    logging.debug('Creating beamset for {}'.format(w))
                    beamset = plan.AddNewBeamSet(Name=re.sub('\D', '', w),
                                                 ExaminationName=case.Examinations[0].Name,
                                                 MachineName=m,
                                                 Modality='Photons',
                                                 TreatmentTechnique='Conformal',
                                                 PatientPosition='HeadFirstSupine',
                                                 NumberOfFractions=1,
                                                 CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False,
                                                 Comment='',
                                                 RbeModelReference=None,
                                                 EnableDynamicTrackingForVero=False)

                    # Add beam
                    logging.debug('Creating beam {}'.format(w))
                    beam = beamset.CreatePhotonBeam(Energy=e,
                                                    IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                                   'NameOfIsocenterToRef': '',
                                                                   'Name': '{}'.format(w),
                                                                   'Color': '98,184,234'},
                                                    Name=re.sub('\D', '', w),
                                                    Description='',
                                                    GantryAngle=0,
                                                    CouchAngle=0,
                                                    CollimatorAngle=90)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=40,
                                                Height=30,
                                                CenterCoordinate={'x': 0, 'y': -5},
                                                MoveMLC=False,
                                                MoveAllMLCLeaves=False,
                                                MoveJaw=True,
                                                JawMargins={'x': 0, 'y': 0},
                                                DeleteWedge=False,
                                                PreventExtraLeafPairFromOpening=False)
                    beamset.Beams[re.sub('\D', '', w)].BeamMU = mu

                    # Display prompt reminding user to set EDW angles
                    time.sleep(1)
                    logging.debug('Saving patient prior to SetCurrent() call')
                    patient.Save()
                    plan.SetCurrent()
                    beamset.SetCurrent()
                    connect.await_user_input('Manually set wedge to {}. Then continue.'.format(w))
                    patient.Save()
                    time.sleep(1)

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for plan {}'.format(w))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for plan {}'.format(w))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='',
                                                       IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

            # Create 6.4 plan
            status.update_text(text='Creating, calculating, and exporting the 6.4 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.4 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.4 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.4 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            patient.Save()
            plan.SetCurrent()
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Loop through each SSD
            for s in ssds:

                # Check if beamset exists
                info = plan.QueryBeamSetInfo(Filter={'Name': '{}'.format(s)})
                if not info:

                    # Add beamset
                    logging.debug('Creating beamset for {}'.format(s))
                    beamset = plan.AddNewBeamSet(Name='{}'.format(s),
                                                 ExaminationName=case.Examinations[0].Name,
                                                 MachineName=m,
                                                 Modality='Photons',
                                                 TreatmentTechnique='Conformal',
                                                 PatientPosition='HeadFirstSupine',
                                                 NumberOfFractions=1,
                                                 CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False,
                                                 Comment='',
                                                 RbeModelReference=None,
                                                 EnableDynamicTrackingForVero=False)

                    # Add beam
                    logging.debug('Creating beam {}'.format(s))
                    beam = beamset.CreatePhotonBeam(Energy=e,
                                                    IsocenterData={'Position': {'x': iso[0],
                                                                                'y': iso[1] + sad - s,
                                                                                'z': iso[2]},
                                                                   'NameOfIsocenterToRef': '',
                                                                   'Name': '{}'.format(s),
                                                                   'Color': '98,184,234'},
                                                    Name='{}'.format(s),
                                                    Description='',
                                                    GantryAngle=0,
                                                    CouchAngle=0,
                                                    CollimatorAngle=0)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=20,
                                                Height=20,
                                                CenterCoordinate={'x': 0, 'y': 0},
                                                MoveMLC=False,
                                                MoveAllMLCLeaves=False,
                                                MoveJaw=True,
                                                JawMargins={'x': 0, 'y': 0},
                                                DeleteWedge=False,
                                                PreventExtraLeafPairFromOpening=False)
                    beamset.Beams['{}'.format(s)].BeamMU = mu

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for plan {}'.format(s))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for plan {}'.format(s))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='', IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

            # Create 6.5 plan
            status.update_text(text='Creating, calculating, and exporting the 6.5 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.5 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.5 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.5 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            patient.Save()
            plan.SetCurrent()
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Loop through each gantry angle
            for a in angles:

                # Check if beamset exists
                info = plan.QueryBeamSetInfo(Filter={'Name': '{}'.format(a)})
                if not info:

                    # Add beamset
                    logging.debug('Creating beamset for {}'.format(a))
                    beamset = plan.AddNewBeamSet(Name='{}'.format(a),
                                                 ExaminationName=case.Examinations[0].Name,
                                                 MachineName=m,
                                                 Modality='Photons',
                                                 TreatmentTechnique='Conformal',
                                                 PatientPosition='HeadFirstSupine',
                                                 NumberOfFractions=1,
                                                 CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False,
                                                 Comment='',
                                                 RbeModelReference=None,
                                                 EnableDynamicTrackingForVero=False)

                    # Add beam
                    print 'Creating beam {}'.format(a)
                    beam = beamset.CreatePhotonBeam(Energy=e,
                                                    IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                                   'NameOfIsocenterToRef': '',
                                                                   'Name': '{}'.format(a),
                                                                   'Color': '98,184,234'},
                                                    Name='{}'.format(a),
                                                    Description='',
                                                    GantryAngle=a,
                                                    CouchAngle=0,
                                                    CollimatorAngle=0)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=10,
                                                Height=10,
                                                CenterCoordinate={'x': 0, 'y': 0},
                                                MoveMLC=False,
                                                MoveAllMLCLeaves=False,
                                                MoveJaw=True,
                                                JawMargins={'x': 0, 'y': 0},
                                                DeleteWedge=False,
                                                PreventExtraLeafPairFromOpening=False)
                    beamset.Beams['{}'.format(a)].BeamMU = mu

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for plan {}'.format(a))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for plan {}'.format(a))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='',
                                                       IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

            # Create 6.6 plan
            status.update_text(text='Creating, calculating, and exporting the 6.6 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.6 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.6 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.6 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            patient.Save()
            plan.SetCurrent()
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Add beamset
            logging.debug('Creating empty 6.6 beamset')
            info = plan.QueryBeamSetInfo(Filter={'Name': 'beam'})
            if not info:
                beamset = plan.AddNewBeamSet(Name='beam',
                                             ExaminationName=case.Examinations[0].Name,
                                             MachineName=m,
                                             Modality='Photons',
                                             TreatmentTechnique='Conformal',
                                             PatientPosition='HeadFirstSupine',
                                             NumberOfFractions=1,
                                             CreateSetupBeams=False,
                                             UseLocalizationPointAsSetupIsocenter=False,
                                             Comment='',
                                             RbeModelReference=None,
                                             EnableDynamicTrackingForVero=False)

                # Add beam
                logging.debug('Creating empty beam')
                beam = beamset.CreatePhotonBeam(Energy=e,
                                                IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                               'NameOfIsocenterToRef': '',
                                                               'Name': 'beam',
                                                               'Color': '98,184,234'},
                                                Name='beam',
                                                Description='',
                                                GantryAngle=0,
                                                CouchAngle=0,
                                                CollimatorAngle=0)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=10,
                                            Height=10,
                                            CenterCoordinate={'x': 0, 'y': 0},
                                            MoveMLC=False,
                                            MoveAllMLCLeaves=False,
                                            MoveJaw=True,
                                            JawMargins={'x': 0, 'y': 0},
                                            DeleteWedge=False,
                                            PreventExtraLeafPairFromOpening=False)
                beamset.Beams['beam'].BeamMU = mu

                # Loop through densities
                for d in densities:

                    # Check if material already exists
                    flag = True
                    idx = 0
                    i = 0
                    try:
                        for i in range(20):
                            if case.PatientModel.Materials[i].Name == 'Water_{}'.format(d):
                                flag = False
                                idx = i
                                break

                    except Exception:
                        idx = i

                    # Create material if it does not exist
                    if flag:
                        case.PatientModel.CreateMaterial(BaseOnMaterial=water,
                                                         Name='Water_{}'.format(d),
                                                         MassDensityOverride=d)

                    # Rename beamset and beam to density
                    beamset.DicomPlanLabel = '{} g/cc'.format(d)
                    beam.Name = '{} g/cc'.format(d)

                    # Update density for box 1 and box 2
                    case.PatientModel.RegionsOfInterest['Box_1'].SetRoiMaterial(
                        Material=case.PatientModel.Materials[idx])
                    case.PatientModel.RegionsOfInterest['Box_2'].SetRoiMaterial(
                        Material=case.PatientModel.Materials[idx])

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for {} g/cc'.format(d))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for {} g/cc'.format(d))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='',
                                                       IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

                # Set box densities back to water
                case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_1'] \
                    .OfRoi.SetRoiMaterial(Material=water)
                case.PatientModel.StructureSets[case.Examinations[0].Name].RoiGeometries['Box_2'] \
                    .OfRoi.SetRoiMaterial(Material=water)

            # Create 6.7 plan
            status.update_text(text='Creating, calculating, and exporting the 6.7 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.7 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.7 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.7 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            patient.Save()
            plan.SetCurrent()
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Loop through each field size
            for f in fields:

                # Check if beamset exists
                info = plan.QueryBeamSetInfo(Filter={'Name': '{} cm'.format(f)})
                if not info:

                    # Add beamset
                    logging.debug('Creating beamset for {} cm'.format(f))
                    beamset = plan.AddNewBeamSet(Name='{} cm'.format(f),
                                                 ExaminationName=case.Examinations[0].Name,
                                                 MachineName=m,
                                                 Modality='Photons',
                                                 TreatmentTechnique='Conformal',
                                                 PatientPosition='HeadFirstSupine',
                                                 NumberOfFractions=1,
                                                 CreateSetupBeams=False,
                                                 UseLocalizationPointAsSetupIsocenter=False,
                                                 Comment='',
                                                 RbeModelReference=None,
                                                 EnableDynamicTrackingForVero=False)

                    # Add beam
                    logging.debug('Creating beam {} cm'.format(f))
                    beam = beamset.CreatePhotonBeam(Energy=e,
                                                    IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                                   'NameOfIsocenterToRef': '',
                                                                   'Name': '{} cm'.format(f),
                                                                   'Color': '98,184,234'},
                                                    Name='{} cm'.format(f),
                                                    Description='',
                                                    GantryAngle=0,
                                                    CouchAngle=0,
                                                    CollimatorAngle=45)
                    beam.SetBolus(BolusName='')
                    beam.CreateRectangularField(Width=f,
                                                Height=f,
                                                CenterCoordinate={'x': 0, 'y': 0},
                                                MoveMLC=True,
                                                MoveAllMLCLeaves=False,
                                                MoveJaw=True,
                                                JawMargins={'x': 0, 'y': 0},
                                                DeleteWedge=False,
                                                PreventExtraLeafPairFromOpening=False)
                    beamset.Beams['{} cm'.format(f)].BeamMU = mu

                    # Create circular MLC pattern
                    leaves = beam.Segments[0].LeafPositions
                    for l in range(len(leaves[0])):
                        d = abs(leafcen[l])

                        if d >= f / 2:
                            leaves[0][l] = 0
                            leaves[1][l] = 0

                        else:
                            leaves[0][l] = -math.sqrt(max(pow(f / 2, 2) - math.pow(d, 2), f / 2 - 15))
                            leaves[1][l] = math.sqrt(max(pow(f / 2, 2) - math.pow(d, 2), f / 2 - 15))

                    beam.Segments[0].LeafPositions = leaves

                    # Calculate dose on beamset
                    if calc:
                        logging.debug('Calculating dose for plan {} cm'.format(f))
                        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                        time.sleep(1)
                        patient.Save()
                        time.sleep(1)

                    # Export beamset to the specified path
                    if export:
                        logging.debug('Exporting RT plan and beam dose for plan {} cm'.format(f))
                        try:
                            case.ScriptableDicomExport(Anonymize=True,
                                                       AnonymizedName='M3D {} {} MV'.format(m, e),
                                                       AnonymizedId='{0:0>4}'.format(counter),
                                                       AEHostname=host,
                                                       AEPort=port,
                                                       CallingAETitle='RayStation',
                                                       CalledAETitle=aet,
                                                       Examinations=[case.Examinations[0].Name],
                                                       RtStructureSetsReferencedFromBeamSets=
                                                       [beamset.BeamSetIdentifier()],
                                                       BeamSets=[beamset.BeamSetIdentifier()],
                                                       BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                       DicomFilter='',
                                                       IgnorePreConditionWarnings=True)

                        except Exception as error:
                            logging.warning(str(error))

                        # Pause execution
                        logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                        time.sleep(delay)

            # Create 6.8 plan
            status.update_text(text='Creating, calculating, and exporting the 6.8 plan...')
            info = case.QueryPlanInfo(Filter={'Name': '6.8 {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for 6.8 {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='6.8 {} {} MV'.format(m, e),
                                       PlannedBy='',
                                       Comment='',
                                       ExaminationName=case.Examinations[0].Name,
                                       AllowDuplicateNames=False)

            else:
                plan = case.LoadPlan(PlanInfo=info[0])

            # Set dose grid
            time.sleep(1)
            logging.debug('Saving patient prior to SetCurrent(), SetDefaultDoseGrid() calls')
            patient.Save()
            plan.SetCurrent()
            logging.debug('Setting default dose grid with {} cm resolution'.format(res))
            plan.SetDefaultDoseGrid(VoxelSize={'x': res, 'y': res, 'z': res})

            # Add C Shape beamset
            info = plan.QueryBeamSetInfo(Filter={'Name': 'C Shape'})
            if 'C Shape' in shapes and not info:
                logging.debug('Creating beamset for C Shape')
                beamset = plan.AddNewBeamSet(Name='C Shape',
                                             ExaminationName=case.Examinations[0].Name,
                                             MachineName=m,
                                             Modality='Photons',
                                             TreatmentTechnique='Conformal',
                                             PatientPosition='HeadFirstSupine',
                                             NumberOfFractions=1,
                                             CreateSetupBeams=False,
                                             UseLocalizationPointAsSetupIsocenter=False,
                                             Comment='',
                                             RbeModelReference=None,
                                             EnableDynamicTrackingForVero=False)

                # Add C Shape beam
                logging.debug('Creating beam C Shape')
                beam = beamset.CreatePhotonBeam(Energy=e,
                                                IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                               'NameOfIsocenterToRef': '',
                                                               'Name': 'C Shape',
                                                               'Color': '98,184,234'},
                                                Name='C Shape',
                                                Description='',
                                                GantryAngle=0,
                                                CouchAngle=0,
                                                CollimatorAngle=90)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=22,
                                            Height=22,
                                            CenterCoordinate={'x': 0, 'y': 0},
                                            MoveMLC=True,
                                            MoveAllMLCLeaves=True,
                                            MoveJaw=True,
                                            JawMargins={'x': 0, 'y': 0},
                                            DeleteWedge=False,
                                            PreventExtraLeafPairFromOpening=False)
                beamset.Beams['C Shape'].BeamMU = mu

                # Create C Shape MLC pattern using inner and outer radii below (in cm)
                outer = 9
                inner = 4
                leaves = beam.Segments[0].LeafPositions
                for l in range(len(leaves[0])):
                    d = abs(leafcen[l])

                    if d >= outer:
                        leaves[0][l] = 0
                        leaves[1][l] = 0

                    elif d >= inner:
                        leaves[0][l] = -math.sqrt(math.pow(outer, 2) - math.pow(d, 2))
                        leaves[1][l] = math.sqrt(math.pow(outer, 2) - math.pow(d, 2))

                    else:
                        leaves[0][l] = math.sqrt(pow(inner, 2) - math.pow(d, 2))
                        leaves[1][l] = math.sqrt(pow(outer, 2) - math.pow(d, 2))

                beam.Segments[0].LeafPositions = leaves

                # Calculate dose on beamset
                if calc:
                    logging.debug('Calculating dose for plan C Shape')
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    time.sleep(1)
                    patient.Save()
                    time.sleep(1)

                # Export beamset to the specified path
                if export:
                    logging.debug('Exporting RT plan and beam dose for plan C Shape')
                    try:
                        case.ScriptableDicomExport(Anonymize=True,
                                                   AnonymizedName='M3D {} {} MV'.format(m, e),
                                                   AnonymizedId='{0:0>4}'.format(counter),
                                                   AEHostname=host,
                                                   AEPort=port,
                                                   CallingAETitle='RayStation',
                                                   CalledAETitle=aet,
                                                   Examinations=[case.Examinations[0].Name],
                                                   RtStructureSetsReferencedFromBeamSets=
                                                   [beamset.BeamSetIdentifier()],
                                                   BeamSets=[beamset.BeamSetIdentifier()],
                                                   BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                   DicomFilter='',
                                                   IgnorePreConditionWarnings=True)

                    except Exception as error:
                        logging.warning(str(error))

                    # Pause execution
                    logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                    time.sleep(delay)

            # Add Fence beamset
            info = plan.QueryBeamSetInfo(Filter={'Name': 'Fence'})
            if 'Fence' in shapes and not info:
                logging.debug('Creating beamset for Fence')
                beamset = plan.AddNewBeamSet(Name='Fence',
                                             ExaminationName=case.Examinations[0].Name,
                                             MachineName=m,
                                             Modality='Photons',
                                             TreatmentTechnique='Conformal',
                                             PatientPosition='HeadFirstSupine',
                                             NumberOfFractions=1,
                                             CreateSetupBeams=False,
                                             UseLocalizationPointAsSetupIsocenter=False,
                                             Comment='',
                                             RbeModelReference=None,
                                             EnableDynamicTrackingForVero=False)

                # Add Fence beam
                logging.debug('Creating beam Fence')
                beam = beamset.CreatePhotonBeam(Energy=e,
                                                IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                               'NameOfIsocenterToRef': '',
                                                               'Name': 'Fence',
                                                               'Color': '98,184,234'},
                                                Name='Fence',
                                                Description='',
                                                GantryAngle=0,
                                                CouchAngle=0,
                                                CollimatorAngle=90)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=22,
                                            Height=22,
                                            CenterCoordinate={'x': 0, 'y': 0},
                                            MoveMLC=True,
                                            MoveAllMLCLeaves=True,
                                            MoveJaw=True,
                                            JawMargins={'x': 0, 'y': 0},
                                            DeleteWedge=False,
                                            PreventExtraLeafPairFromOpening=False)
                beamset.Beams['Fence'].BeamMU = mu

                # Create Fence MLC pattern using width and separation below (in cm)
                wid = 2
                sep = 4
                leaves = beam.Segments[0].LeafPositions
                for l in range(len(leaves[0])):
                    d = abs(leafcen[l])

                    if d % sep < wid / 2 or d % sep + wid / 2 > sep:
                        leaves[0][l] = -wid
                        leaves[1][l] = wid

                    else:
                        leaves[0][l] = -wid
                        leaves[1][l] = -wid

                beam.Segments[0].LeafPositions = leaves

                # Calculate dose on beamset
                if calc:
                    logging.debug('Calculating dose for plan Fence')
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    time.sleep(1)
                    patient.Save()
                    time.sleep(1)

                # Export beamset to the specified path
                if export:
                    logging.debug('Exporting RT plan and beam dose for plan Fence')
                    try:
                        case.ScriptableDicomExport(Anonymize=True,
                                                   AnonymizedName='M3D {} {} MV'.format(m, e),
                                                   AnonymizedId='{0:0>4}'.format(counter),
                                                   AEHostname=host,
                                                   AEPort=port,
                                                   CallingAETitle='RayStation',
                                                   CalledAETitle=aet,
                                                   Examinations=[case.Examinations[0].Name],
                                                   RtStructureSetsReferencedFromBeamSets=
                                                   [beamset.BeamSetIdentifier()],
                                                   BeamSets=[beamset.BeamSetIdentifier()],
                                                   BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                   DicomFilter='',
                                                   IgnorePreConditionWarnings=True)

                    except Exception as error:
                        logging.warning(str(error))

                    # Pause execution
                    logging.debug('Waiting {} seconds for Mobius3D to catch up'.format(delay))
                    time.sleep(delay)

            # Add VMAT CP beamset
            info = plan.QueryBeamSetInfo(Filter={'Name': 'VMAT CP'})
            if 'VMAT CP' in shapes and not info:
                logging.debug('Creating beamset for VMAT CP')
                beamset = plan.AddNewBeamSet(Name='VMAT CP',
                                             ExaminationName=case.Examinations[0].Name,
                                             MachineName=m,
                                             Modality='Photons',
                                             TreatmentTechnique='Conformal',
                                             PatientPosition='HeadFirstSupine',
                                             NumberOfFractions=1,
                                             CreateSetupBeams=False,
                                             UseLocalizationPointAsSetupIsocenter=False,
                                             Comment='',
                                             RbeModelReference=None,
                                             EnableDynamicTrackingForVero=False)

                # Add VMAT CP beam
                logging.debug('Creating beam VMAT CP')
                beam = beamset.CreatePhotonBeam(Energy=e,
                                                IsocenterData={'Position': {'x': iso[0], 'y': iso[1], 'z': iso[2]},
                                                               'NameOfIsocenterToRef': '',
                                                               'Name': 'VMAT CP',
                                                               'Color': '98,184,234'},
                                                Name='VMAT CP',
                                                Description='',
                                                GantryAngle=0,
                                                CouchAngle=0,
                                                CollimatorAngle=90)
                beam.SetBolus(BolusName='')
                beam.CreateRectangularField(Width=22,
                                            Height=22,
                                            CenterCoordinate={'x': 0, 'y': 0},
                                            MoveMLC=True,
                                            MoveAllMLCLeaves=True,
                                            MoveJaw=True,
                                            JawMargins={'x': 0, 'y': 0},
                                            DeleteWedge=False,
                                            PreventExtraLeafPairFromOpening=False)
                beamset.Beams['VMAT CP'].BeamMU = mu

                # Apply VMAT CP pattern
                stda = [-3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -0.95, -1.5, -1.74,
                        -2.15, -1.66, -1.13, -1.09, -1.35, -1.03, -0.59, -0.46, -0.44, -0.51, -0.56, -0.71, -0.53,
                        -0.43, -0.33, -0.21, 0.14, -0.25, -0.49, -0.88, -0.31, -0.26, -0.26, -0.47, -0.44, -0.44, -0.44,
                        -0.44, -0.44, -0.51, -2.82, -3.03, -2.11, -0.78, -0.51, -0.82, -3.03, -3.71, -3.71, -3.71,
                        -3.71, -3.71, -3.71, -3.71, -3.71, -3.71]
                stdb = [-3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -0.78, -0.81,
                        -0.81, -0.74, -0.66, 0.29, 0.33, 0.26, 0.26, 0.37, 0.43, 0.26, 0.26, 0.34, 0.28, -0.11, -0.08,
                        -0.01, 0.19, 0.44, 0.64, 0.9, 0.76, 0.86, 1.49, 1.21, 1.0, 0.31, 0.19, 0.19, 0.19, 0.26, 0.32,
                        2.57, 2.97, 3.09, 3.09, 2.94, 2.59, 2.2, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71, -3.71,
                        -3.71]
                stxa = [-3.71, -3.71, -3.71, -0.95, -1.5, -1.74, -2.15, -1.66, -1.13, -1.09, -1.35, -1.03, -0.59, -0.46,
                        -0.44, -0.44, -0.51, -0.51, -0.56, -0.59, -0.71, -0.71, -0.61, -0.53, -0.48, -0.43, -0.39,
                        -0.33, -0.31, -0.21, 0.14, 0.14, -0.25, -0.37, -0.49, -0.59, -0.9, -0.88, -0.39, -0.31, -0.26,
                        -0.26, -0.26, -0.31, -0.47, -0.53, -0.44, -0.44, -0.44, -0.44, -0.44, -0.51, -2.82, -3.03,
                        -2.11, -0.78, -0.51, -0.82, -3.12, -3.71]
                stxb = [-3.71, -3.71, -3.71, -0.78, -0.81, -0.81, -0.74, -0.66, 0.29, 0.33, 0.26, 0.26, 0.37, 0.43,
                        0.26, 0.26, 0.26, 0.26, 0.34, 0.34, 0.34, 0.28, -0.1, -0.11, -0.08, -0.06, -0.01, 0.04, 0.19,
                        0.26, 0.44, 0.56, 0.64, 0.72, 0.91, 0.9, 0.76, 0.76, 0.86, 0.99, 1.49, 1.51, 1.29, 1.21, 1.14,
                        1.00, 0.31, 0.19, 0.19, 0.19, 0.26, 0.32, 1.57, 1.97, 3.09, 3.09, 2.94, 2.59, 2.41, -3.71]

                leaves = beam.Segments[0].LeafPositions

                for l in range(len(leaves[0])):
                    if min(machine.Physics.MlcPhysics.LeafWidths) == 0.25:
                        leaves[0][l] = stxa[l]
                        leaves[1][l] = stxb[l]

                    elif min(machine.Physics.MlcPhysics.LeafWidths) == 0.5:
                        leaves[0][l] = stda[l]
                        leaves[1][l] = stdb[l]

                    else:
                        logging.warning('Unsupported MLC configuration for 6.8 test VMAT CP')

                beam.Segments[0].LeafPositions = leaves

                # Calculate dose on beamset
                if calc:
                    logging.debug('Calculating dose for plan VMAT CP')
                    beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                    time.sleep(1)
                    patient.Save()
                    time.sleep(1)

                # Export beamset to the specified path
                if export:
                    logging.debug('Exporting RT plan and beam dose for plan VMAT CP')
                    try:
                        case.ScriptableDicomExport(Anonymize=True,
                                                   AnonymizedName='M3D {} {} MV'.format(m, e),
                                                   AnonymizedId='{0:0>4}'.format(counter),
                                                   AEHostname=host,
                                                   AEPort=port,
                                                   CallingAETitle='RayStation',
                                                   CalledAETitle=aet,
                                                   Examinations=[case.Examinations[0].Name],
                                                   RtStructureSetsReferencedFromBeamSets=
                                                   [beamset.BeamSetIdentifier()],
                                                   BeamSets=[beamset.BeamSetIdentifier()],
                                                   BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
                                                   DicomFilter='',
                                                   IgnorePreConditionWarnings=True)

                    except Exception as error:
                        logging.warning(str(error))

    # Finish up
    time.sleep(1)
    patient.Save()
    time.sleep(1)
    logging.debug('Script completed successfully in {.3f} seconds'.format(time.time() - tic))
    status.finish('Script completed successfully')


if __name__ == '__main__':
    main()
