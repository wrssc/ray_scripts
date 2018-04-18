""" Create Mobius3D DLG Optimization Plans
    
    This RayStation TPS script creates a series of DLG test plans on a
    homogeneous phantom for each machine and photon energy. Test plans consist
    of a 10x10 jaw defined field with a series of MLC leaf gaps and offsets,
    similar to the method applied by Yao and Farr (2015), "Determining the
    optimal dosimetric leaf gap setting for rounded leaf-end multileaf collimator
    systems by simple test fields", JACMP 16(4): 5321.
    
    To run this script, you must first have a plan open that contains a
    homogeneous phantom (see the associated script CreateReferenceCT.py, which
    creates a homogeneous CT) and external contour. The CT should be at least
    20x20x20 cm in the LR/AP/SI dimensions. The script will create one plan for
    each machine/energy, and one beamset for each MLC pattern. After calculating
    dose, the script will pause and prompt you to set the DLG offset in Mobius3D
    to a specified value, then (after resuming) export each plan and pause to
    prompt you to set the DLG offset to the next value.
    
    Finally, after all plans calculate in Mobius3D, you can run
    DownloadPlanCheckFiles.py in https://github.com/mwgeurts/mobius_scripts to
    download all TPS and Mobius3D dose volumes to a specified folder and then
    CompareLeafGaps.m (contact the author) to evaluate them in MATLAB.
    
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
    status = UserInterface.ScriptStatus(steps=['Verify CT density table and external are set',
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
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'External':
            external = True
            b = case.PatientModel.StructureSets[examination.Name].RoiGeometries[r.Name].GetBoundingBox()
            bounds = [b[0].x, b[1].x, b[0].y, b[1].y, b[0].z, b[1].z]

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
    iso = [(bounds[0] + bounds[1]) / 2, -bounds[2], (bounds[4] + bounds[5]) / 2]

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
                                               'c': 'Enter leaf gaps (cm):',
                                               'd': 'Enter leaf offsets (cm):',
                                               'e': 'Enter DLG offset iterations (cm):',
                                               'j': 'Dose grid resolution (mm):',
                                               'k': 'Runtime options:',
                                               'l': 'Mobius3D host name/IP address:',
                                               'm': 'Mobius3D DICOM port:',
                                               'n': 'Mobius3D DICOM AE title:',
                                               'o': 'Time delay between DICOM exports (sec):'},
                                       datatype={'a': 'check', 'k': 'check'},
                                       initial={'a': machine_list,
                                                'b': '100',
                                                'c': '0.5, 1.0, 1.5, 2.0',
                                                'd': '0, 0.25, 0.5',
                                                'e': '0.0, 0.1, 0.2, 0.3',
                                                'j': '1.0',
                                                'k': ['Calculate plan', 'Export plan'],
                                                'l': 'mobius.uwhealth.wisc.edu',
                                                'm': '104',
                                                'n': 'MOBIUS3D',
                                                'o': '60'},
                                       options={'a': machine_list,
                                                'k': ['Calculate plan', 'Export plan']},
                                       required=['a', 'b', 'c', 'd', 'e', 'j'])

    # Parse responses
    response = inputs.show()
    if response == {}:
        status.finish('Script cancelled, inputs were not supplied')
        sys.exit('Script cancelled')

    else:
        status.update_text(text='Parsing inputs...')

    machines = response['a']
    mu = float(response['b'])
    gaps = map(float, response['c'].split(','))
    offsets = map(float, response['d'].split(','))
    iters = map(float, response['e'].split(','))
    res = float(response['j']) / 10
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
    counter = 1000

    # Loop through each machine
    for m in machines:

        # Store machine DB record
        machine = machine_db.GetTreatmentMachine(machineName=m, lockMode=None)

        # Loop through energies
        for q in machine.PhotonBeamQualities:

            # Store nominal energy
            e = int(q.NominalEnergy)

            # Create 6.1 plan
            time.sleep(1)
            status.next_step(text='Creating, calculating, and exporting each DLG plan. For each DLG Offset iteration ' +
                                  'entered earlier, the script will pause and you will be prompted to update the DLG ' +
                                  'offset in Mobius3D. The script will then re-export the same plan list, thereby ' +
                                  'creating copies of the same plans with different DLG offsets applied.')
            info = case.QueryPlanInfo(Filter={'Name': 'DLG {} {} MV'.format(m, e)})
            if not info:
                logging.debug('Creating plan for DLG {} {} MV'.format(m, e))
                plan = case.AddNewPlan(PlanName='DLG {} {} MV'.format(m, e),
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

            # Loop through gaps
            for g in gaps:

                # Loop through offsets
                for o in offsets:

                    # Check if beam set exists
                    info = plan.QueryBeamSetInfo(Filter={'Name': '{}mm-{}mm'.format(g * 10, o * 10)})
                    if not info:

                        # Add beamset
                        logging.debug('Creating beamset for plan {}mm-{}mm'.format(g * 10, o * 10))
                        beamset = plan.AddNewBeamSet(Name='{}mm-{}mm'.format(g * 10, o * 10),
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
                        logging.debug('Creating beam {}mm-{}mm'.format(g * 10, o * 10))
                        beam = beamset.CreatePhotonBeam(Energy=e,
                                                        IsocenterData={'Position': {'x': iso[0],
                                                                                    'y': iso[1],
                                                                                    'z': iso[2]},
                                                                       'NameOfIsocenterToRef': '',
                                                                       'Name': '{}mm-{}mm'.format(g * 10, o * 10),
                                                                       'Color': '98,184,234'},
                                                        Name='{}mm-{}mm'.format(g * 10, o * 10),
                                                        Description='',
                                                        GantryAngle=0,
                                                        CouchAngle=0,
                                                        CollimatorAngle=0)
                        beam.SetBolus(BolusName='')
                        beam.CreateRectangularField(Width=10,
                                                    Height=10,
                                                    CenterCoordinate={'x': 0, 'y': 0},
                                                    MoveMLC=False,
                                                    MoveAllMLCLeaves=True,
                                                    MoveJaw=True,
                                                    JawMargins={'x': 0, 'y': 0},
                                                    DeleteWedge=False,
                                                    PreventExtraLeafPairFromOpening=False)
                        beamset.Beams['{}mm-{}mm'.format(g * 10, o * 10)].BeamMU = mu

                        # Update MLC leaves
                        leaves = beam.Segments[0].LeafPositions
                        for l in range(len(leaves[0])):
                            if leaves[0][l] != leaves[1][l]:
                                if l % 2 == 0:
                                    leaves[0][l] = -g / 2 - o
                                    leaves[1][l] = g / 2 - o
                                else:
                                    leaves[0][l] = -g / 2
                                    leaves[1][l] = g / 2

                        beam.Segments[0].LeafPositions = leaves

                        # Calculate dose on beamset
                        if calc:
                            logging.debug('Calculating dose for plan {}mm-{}mm'.format(g * 10, o * 10))
                            beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm='CCDose')
                            time.sleep(1)
                            patient.Save()
                            time.sleep(1)

            # Loop through DLG offset iterations
            if export:
                for i in iters:

                    # Prompt user to set DLG offset
                    counter += 1
                    logging.debug('Prompting user to update {} {} MV DLG offset to {} mm'.format(m, e, i))
                    connect.await_user_input('Set Mobius3D {} {} MV DLG offset to {} mm, and set dose calculation ' +
                                             'resolution to {} mm'.format(m, e, i, res))

                    # Loop through gaps
                    for g in gaps:

                        # Loop through offsets
                        for o in offsets:

                            # Query beamset, then export and load
                            info = plan.QueryBeamSetInfo(Filter={'Name': '{}mm-{}mm'.format(g * 10, o * 10)})
                            if not info:
                                logging.warning('Beamset {}mm-{}mm not found!'.format(g * 10, o * 10))

                            else:
                                beamset = plan.LoadBeamSet(BeamSetInfo=info[0])

                                logging.debug(
                                    'Exporting RT plan and beam dose for plan {}mm-{}mm'.format(g * 10, o * 10))
                                try:
                                    case.ScriptableDicomExport(Anonymize=True,
                                                               AnonymizedName='DLG {} {} MV {} mm'.format(m, e, i),
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

    # Finish up
    time.sleep(1)
    patient.Save()
    time.sleep(1)
    logging.debug('Script completed successfully in {.3f} seconds'.format(time.time() - tic))
    status.finish('Script completed successfully')


if __name__ == '__main__':
    main()
