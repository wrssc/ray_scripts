""" DICOM Export Functions

    The DicomExport.send() function uses the RayStation ScriptableDicomExport()
    function, pydicom, and pynetdicom3 to export DICOM RT data to a temporary folder
    then modify the contents of the DICOM files, and finally to send the modified
    files to one or more destinations. In this manner, machine names and non-standard
    beam energies (FFF) can be corrected during export to the Record & Verify system.

    This function will read in two XML files during import: DicomDestinations.xml
    and DicomFilters.xml. They should contain DICOM destination and machine/energy
    filters, respectively. For information on their required formats, see the
    provided wiki link in __help__.

    Below is an example of how to call the send() function. There are multiple
    additional input arguments that can be added to further filter the DICOM files,
    such as anonymization, overriding table positions, rounding jaws, or setting
    block IDs. For a full description of how to use these settings, see the provided
    wiki link in __help__.

    # Get a list of configured DICOM destinations
    d = DicomExport.destinations()

    # Send the currently loaded plan to the first destination
    DicomExport.send(case=get_current('Case'),
                     destination=d[0],
                     exam=get_current('Examination'),
                     beamset=get_current('BeamSet'),
                     filters=['machine', 'energy'],
                     ignore_warnings=True)

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
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/DICOM-Export'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import os
import xml.etree.ElementTree
import time
import tempfile
import logging
import UserInterface
import pydicom
import pynetdicom3
import shutil
import re
import math
import random
import string

# Parse destination and filters XML files
dest_xml = xml.etree.ElementTree.parse(os.path.join(os.path.dirname(__file__), 'DicomDestinations.xml'))
filter_xml = xml.etree.ElementTree.parse(os.path.join(os.path.dirname(__file__), 'DicomFilters.xml'))

# local_AET defines the AE title that will be used by the script when communicating with the destination
local_AET = 'RAYSTATION_SSCP'
local_port = 105

# Define personal_tags (for anonymization)
personal_tags = ['PatientName', 'PatientID', 'OtherPatientIDs', 'OtherPatientIDsSequence', 'PatientBirthDate']


def send(case,
         destination,
         exam=None,
         beamset=None,
         structures=True,
         plan_dose=True,
         beam_dose=False,
         ignore_warnings=False,
         ignore_errors=False,
         anonymize=None,
         filters=None,
         machine=None,
         table=None,
         pa_threshold=None,
         prescription=False,
         round_jaws=False,
         block_accessory=False,
         bar=True):
    """DicomExport.send(case=get_current('Case'), destination='MIM', exam=get_current('Examination'),
                        beamset=get_current('BeamSet'))"""

    # Start timer
    tic = time.time()
    status = True

    # Re-cast string destination as list
    if isinstance(destination, str):
        destination = [destination]

    # Create temporary folders to store original and modified exports
    original = tempfile.mkdtemp()
    modified = tempfile.mkdtemp()

    # Validate destinations
    dest_list = destinations()
    for d in destination:
        if d not in dest_list:
            raise IndexError('The provided DICOM destination is not in the available list')

    # If multiple machine filter options exist, prompt the user to select one
    if machine is None and filters is not None and 'machine' in filters and beamset is not None:
        machine_list = machines(beamset)
        if len(machine_list) == 1:
            machine = machine_list[0]

        elif len(machine_list) > 1:
            dialog = UserInterface.ButtonList(inputs=machine_list, title='Select a machine to export as')
            machine = dialog.show()

    # Load energy filters for selected machine
    if filters is not None and 'energy' in filters and beamset is not None:
        energy_list = energies(beamset, machine)
    else:
        energy_list = None

    # Establish connections with all SCP destinations
    if bar:
        bar = UserInterface.ProgressBar(text='Establishing connection to DICOM destinations',
                                        title='Export Progress',
                                        marquee=True)

    for d in destination:
        info = destination_info(d)
        if len({'host', 'aet', 'port'}.difference(info.keys())) == 0:
            ae = pynetdicom3.AE(scu_sop_class=['1.2.840.10008.1.1'],
                                ae_title=local_AET,
                                port=local_port)
            logging.debug('Requesting Association with {}'.format(info['host']))
            assoc = ae.associate(info['host'], int(info['port']), ae_title=info['aet'])

            # Throw errors unless C-ECHO responds
            if assoc.is_established:
                logging.debug('Association accepted by the peer')
                response = assoc.send_c_echo()
                assoc.release()
                logging.debug('C-ECHO Response: 0x{0:04x}'.format(response.Status))

            elif assoc.is_rejected and not ignore_errors:
                if isinstance(bar, UserInterface.ProgressBar):
                    bar.close()

                raise IOError('Association to {} was rejected by the peer'.format(info['host']))

            elif assoc.is_aborted and not ignore_errors:
                if isinstance(bar, UserInterface.ProgressBar):
                    bar.close()

                raise IOError('Received A-ABORT from the peer during association to {}'.format(info['host']))

            else:
                status = False

    # Initialize ScriptableDicomExport() arguments
    args = {'IgnorePreConditionWarnings': ignore_warnings, 'DicomFilter': '', 'ExportFolderPath': original}

    # Append exam to export CT
    if exam is not None:
        args['Examinations'] = [exam.Name]

    # Append beamset to export RTSS and Dose (if beamset is not present, export RTSS from exam)
    if beamset is not None:
        if structures:
            args['RtStructureSetsReferencedFromBeamSets'] = [beamset.BeamSetIdentifier()]

        args['BeamSets'] = [beamset.BeamSetIdentifier()]
        if plan_dose:
            args['BeamSetDoseForBeamSets'] = [beamset.BeamSetIdentifier()]

        if beam_dose:
            args['BeamDosesForBeamSets'] = [beamset.BeamSetIdentifier()]

    elif exam is not None and structures:
        args['RtStructureSetsForExaminations'] = [exam.Name]

    # Append anonymization parameters
    if anonymize is not None and 'name' in anonymize and 'id' in anonymize:
        args['Anonymize'] = True
        args['AnonymizedName'] = anonymize['name']
        args['AnonymizedId'] = anonymize['id']

    # Export data to temp folder
    if isinstance(bar, UserInterface.ProgressBar):
        bar.update(text='Exporting DICOM files to temporary folder')

    try:
        logging.debug('Executing ScriptableDicomExport() to path {}'.format(original))
        case.ScriptableDicomExport(**args)

    except Exception as error:
        if ignore_errors:
            logging.warning(str(error))
            status = False

        else:
            if isinstance(bar, UserInterface.ProgressBar):
                bar.close()

            raise

    # Load the DICOM files back in, applying filters
    edited = {}
    if isinstance(bar, UserInterface.ProgressBar):
        bar.update(text='Applying filters')

    for o in os.listdir(original):

        # Try to open as a DICOM file
        try:
            logging.debug('Reading original file {}'.format(o))
            ds = pydicom.dcmread(os.path.join(original, o))

            # If this is a DICOM RT plan
            expected = _Edits()
            if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                for b in ds.BeamSequence:

                    # If applying a machine filter
                    if machine is not None and 'TreatmentMachineName' in b and b.TreatmentMachineName != machine:
                        b.TreatmentMachineName = machine
                        expected.add(b[0x300a00b2], beam=b)

                    # If converting electron block into accessory (note, accessory ID tags are currently hard coded
                    if block_accessory and 'RadiationType' in b and b.RadiationType == 'ELECTRON' and \
                            'BlockSequence' in b and 'BlockName' in b.BlockSequence[0] and \
                            'GeneralAccessorySequence' not in b:

                        acc = pydicom.Dataset()
                        acc.add_new(0x300a00f9, 'LO', b.BlockSequence[0].BlockName)
                        if 'ApplicatorSequence' in b and 'ApplicatorID' in b.ApplicatorSequence and \
                                b.ApplicatorSequence.ApplicatorID == 'A6':
                            acc.add_new(0x300a0421, 'SH', 'CustomFFDA6')

                        else:
                            acc.add_new(0x300a0421, 'SH', 'CustomFFDA')

                        acc.add_new(0x300a0423, 'CS', 'TRAY')
                        acc.add_new(0x300a0424, 'IS', 1)
                        b.add_new(0x300a0420, 'SQ', pydicom.Sequence([acc]))
                        expected.add(b[0x300a0420])

                    # If updating table position
                    if table is not None and 'ControlPointSequence' in b:
                        for c in b.ControlPointSequence:
                            if 'TableTopLateralPosition' in c and c.TableTopLateralPosition != table[0]:
                                c.TableTopLateralPosition = table[0]
                                expected.add(c[0x300a012a], beam=b, cp=c)

                            if 'TableTopLongitudinalPosition' in c and \
                                    c.TableTopLongitudinalPosition != table[1]:
                                c.TableTopLongitudinalPosition = table[1]
                                expected.add(c[0x300a0129], beam=b, cp=c)

                            if 'TableTopVerticalPosition' in c and c.TableTopVerticalPosition != table[2]:
                                c.TableTopVerticalPosition = table[2]
                                expected.add(c[0x300a0128], beam=b, cp=c)

                    # If rounding jaws
                    if round_jaws and 'ControlPointSequence' in b:
                        for c in b.ControlPointSequence:
                            if hasattr(c, 'BeamLimitingDevicePositionSequence'):
                                for p in c.BeamLimitingDevicePositionSequence:
                                    if 'LeafJawPositions' in p and len(p.LeafJawPositions) == 2 and \
                                            (p.LeafJawPositions[0] != math.floor(p.LeafJawPositions[0]) or
                                             p.LeafJawPositions[1] != math.ceil(p.LeafJawPositions[1])):
                                        p.LeafJawPositions[0] = math.floor(p.LeafJawPositions[0])
                                        p.LeafJawPositions[1] = math.ceil(p.LeafJawPositions[1])
                                        expected.add(p[0x300a011c], beam=b, cp=c)

                    # If adjusting PA beam angle for right sided targets
                    if pa_threshold is not None:
                        right_pa = True
                        for c in b.ControlPointSequence:
                            if 'GantryAngle' not in c or c.GantryAngle != 180 or \
                                    'GantryRotationDirection' not in c or c.GantryRotationDirection != 'NONE' or \
                                    ('IsocenterPosition' in c and c.IsocenterPosition < pa_threshold):
                                right_pa = False
                                break

                        if right_pa:
                            for c in b.ControlPointSequence:
                                if 'GantryAngle' in c:
                                    c.GantryAngle = 180.1
                                    expected.add(c[0x300a011e], beam=b, cp=c)

                    # If applying an energy filter (note only photon are supported)
                    if energy_list is not None and 'ControlPointSequence' in b:
                        for c in b.ControlPointSequence:
                            if 'NominalBeamEnergy' in c and c.NominalBeamEnergy in energy_list.keys() and \
                                    'RadiationType' in b and b.RadiationType == 'PHOTON':
                                e = float(re.sub('\D+', '', energy_list[c.NominalBeamEnergy]))
                                m = re.sub('\d+', '', energy_list[c.NominalBeamEnergy])
                                if c.NominalBeamEnergy != e:
                                    c.NominalBeamEnergy = e
                                    expected.add(c[0x300a0114], beam=b, cp=c)

                                # If a non-standard fluence, add mode ID and NON_STANDARD flag
                                if 'FluenceMode' not in b or (b.FluenceMode != 'NON_STANDARD' and m != '') or \
                                        (b.FluenceMode != 'STANDARD' and m == ''):

                                    if m != '':
                                        b.FluenceMode = 'NON_STANDARD'

                                    else:
                                        b.FluenceMode = 'STANDARD'

                                    expected.add(b[0x30020051], beam=b, cp=c)

                                if m != '' and ('FluenceModeID' not in b or b.FluenceModeID != m):
                                    b.FluenceModeID = m
                                    expected.add(b[0x30020052], beam=b, cp=c)

                # If adding reference points
                if prescription and beamset.Prescription.PrimaryDosePrescription is not None and \
                        'FractionGroupSequence' in ds and len(ds.FractionGroupSequence[0].ReferencedBeamSequence) > 0:

                    # Create reference point for primary dose prescription
                    ref = pydicom.Dataset()
                    ref.add_new(0x300a0012, 'IS', 1)
                    ref.add_new(0x300a0014, 'CS', 'COORDINATES')
                    if hasattr(beamset.Prescription.PrimaryDosePrescription.OnStructure, 'Name'):
                        ref.add_new(0x300a0016, 'LO', beamset.Prescription.PrimaryDosePrescription.OnStructure.Name)

                    else:
                        ref.add_new(0x300a0016, 'LO', 'PTV')

                    if 'BeamDoseSpecificationPoint' in ds.FractionGroupSequence[0].ReferencedBeamSequence[0]:
                        ref.add_new(0x300a0018, 'DS',
                                    ds.FractionGroupSequence[0].ReferencedBeamSequence[0].BeamDoseSpecificationPoint)

                    else:
                        ref.add_new(0x300a0018, 'DS', [0, 0, 0])

                    ref.add_new(0x300a0020, 'CS', 'ORGAN_AT_RISK')
                    ref.add_new(0x300a0023, 'DS', beamset.Prescription.PrimaryDosePrescription.DoseValue / 100)
                    ref.add_new(0x300a002c, 'DS', beamset.Prescription.PrimaryDosePrescription.DoseValue / 100)

                    if 'DoseReferenceSequence' not in ds:
                        ds.add_new(0x300a0010, 'SQ', pydicom.Sequence([ref]))
                        expected.add(ds[0x300a0010])

                    else:
                        if 'DoseReferenceStructureType' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceStructureType != \
                                ref.DoseReferenceStructureType:
                            expected.add(ref[0x300a0014])

                        if 'DoseReferenceDescription' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceDescription != ref.DoseReferenceDescription:
                            expected.add(ref[0x300a0016])

                        if 'DoseReferencePointCoordinates' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferencePointCoordinates != \
                                ref.DoseReferencePointCoordinates:
                            expected.add(ref[0x300a0018])

                        if 'DoseReferenceType' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceType != ref.DoseReferenceType:
                            expected.add(ref[0x300a0020])

                        if 'DeliveryMaximumDose' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DeliveryMaximumDose != ref.DeliveryMaximumDose:
                            expected.add(ref[0x300a0023])

                        if 'OrganAtRiskMaximumDose' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].OrganAtRiskMaximumDose != ref.OrganAtRiskMaximumDose:
                            expected.add(ref[0x300a002c])

                        ds.DoseReferenceSequence = pydicom.Sequence([ref])

                    # Adjust beam doses to sum to primary dose point
                    total_dose = 0
                    for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
                        if hasattr(b, 'BeamDose'):
                            total_dose += b.BeamDose

                    for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
                        if hasattr(b, 'BeamDose') and b.BeamDose != b.BeamDose * ref.DeliveryMaximumDose / \
                                (total_dose * ds.FractionGroupSequence[0].NumberOfFractionsPlanned):
                            b.BeamDose = b.BeamDose * ref.DeliveryMaximumDose / \
                                         (total_dose * ds.FractionGroupSequence[0].NumberOfFractionsPlanned)
                            expected.add(b[0x300a0084], beam=b)

            # If no edits are needed, copy the file to the modified directory
            if expected.length() == 0:
                logging.debug('File {} does not require modification, and will be copied directly'.format(o))
                shutil.copy(os.path.join(original, o), modified)

            else:
                edited[o] = expected
                logging.debug('File {} re-saved with {} edits'.format(o, expected.length()))
                ds.save_as(os.path.join(modified, o))

        # If pydicom fails, stop export unless ignore_errors flag is set
        except pydicom.errors.InvalidDicomError:
            if ignore_errors:
                logging.warning('File {} could not be read during modification, skipping'.format(o))
                status = False

            else:
                if isinstance(bar, UserInterface.ProgressBar):
                    bar.close()

                raise

    # Generate random names/ID
    random_name = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
    random_id = ''.join(random.choice(string.digits) for _ in range(8))

    # Validate and/or send each file
    i = 0
    total = len(os.listdir(modified))
    for m in os.listdir(modified):
        i += 1
        if isinstance(bar, UserInterface.ProgressBar):
            bar.update(text='Validating and Exporting Files ({} of {})'.format(i, total))

        try:
            logging.debug('Reading modified file {}'.format(os.path.join(modified, m)))
            ds = pydicom.dcmread(os.path.join(modified, m))

            # Validate changes against original file, recursively searching through sequences
            if m in edited:
                logging.debug('Validating edits against {}'.format(os.path.join(original, m)))
                dso = pydicom.dcmread(os.path.join(original, m))

                try:
                    # The Edits list should match the expected list generated above
                    if edited[m].matches(compare(ds, dso)):
                        logging.debug('File {} edits are consistent with expected'.format(m))

                    else:
                        status = False
                        if not ignore_errors:
                            if isinstance(bar, UserInterface.ProgressBar):
                                bar.close()

                            raise KeyError('DICOM Export modification inconsistency detected')

                except KeyError:
                    if ignore_errors:
                        logging.warning('DICOM validation encountered too many nested sequences')
                        status = False

                    else:
                        if isinstance(bar, UserInterface.ProgressBar):
                            bar.close()

                        raise

            # Send file
            for d in destination:
                info = destination_info(d)

                # If destination has a anonymize tag, remove personal info
                phi = {}
                if 'anonymize' in info and info['anonymize']:
                    for t in personal_tags:
                        if hasattr(ds, t):
                            phi[t] = getattr(ds, t)
                            delattr(ds, t)

                    ds.PatientName = random_name
                    ds.PatientID = random_id
                    ds.PatientBirthdate = ''

                # Send to SCP via pynetdicom3
                if len({'host', 'aet', 'port'}.difference(info)) == 0:
                    ae = pynetdicom3.AE(scu_sop_class=['1.2.840.10008.5.1.4.1.1.481.5',
                                                       '1.2.840.10008.5.1.4.1.1.481.3',
                                                       '1.2.840.10008.5.1.4.1.1.481.2',
                                                       '1.2.840.10008.5.1.4.1.1.2'],
                                        ae_title=local_AET,
                                        port=local_port,
                                        transfer_syntax=['1.2.840.10008.1.2'])

                    assoc = ae.associate(info['host'], int(info['port']), ae_title=info['aet'])
                    if assoc.is_established:
                        response = assoc.send_c_store(dataset=ds,
                                                      msg_id=1,
                                                      priority=0,
                                                      originator_aet=None,
                                                      originator_id=None)
                        assoc.release()
                        logging.info('{0} -> {1} C-STORE status: 0x{2:04x}'.format(m, d, response.Status))
                        if response.Status != 0:
                            status = False
                            if not ignore_errors:
                                if isinstance(bar, UserInterface.ProgressBar):
                                    bar.close()

                                raise IOError('C-STORE ERROR: 0x{2:04x}'.format(m, d, response.Status))

                    elif assoc.is_rejected and not ignore_errors:
                        if isinstance(bar, UserInterface.ProgressBar):
                            bar.close()

                        raise IOError('Association to {} was rejected by the peer'.format(info['host']))

                    elif assoc.is_aborted and not ignore_errors:
                        if isinstance(bar, UserInterface.ProgressBar):
                            bar.close()

                        raise IOError('Received A-ABORT from the peer during association to {}'.format(info['host']))

                    else:
                        status = False

                # Send to folder based on PatientID via file copy
                elif 'path' in info:
                    if not os.path.exists(os.path.join(info['path'], ds.PatientID)):
                        os.mkdir(os.path.join(info['path'], ds.PatientID))

                    try:
                        shutil.copy(os.path.join(modified, m), os.path.join(info['path'], ds.PatientID))
                        logging.info('{} -> {} copied'.format(m, os.path.join(info['path'], ds.PatientID)))

                    except IOError:
                        status = False
                        if ignore_errors:
                            logging.warning('{} -> {} IOError'.format(m, os.path.join(info['path'], ds.PatientID)))

                        else:
                            if isinstance(bar, UserInterface.ProgressBar):
                                bar.close()

                            raise

                # If destination had a anonymize tag, set values back
                for k, v in phi.items():
                    setattr(ds, k, v)

        # If pydicom fails, stop export unless ignore_errors flag is set
        except pydicom.errors.InvalidDicomError:
            if ignore_errors:
                logging.warning('File {} could not be read during modification, skipping'.format(m))
                status = False

            else:
                if isinstance(bar, UserInterface.ProgressBar):
                    bar.close()

                raise

    # Delete temporary folders
    try:
        logging.debug('Deleting temporary folder {}'.format(original))
        shutil.rmtree(original)
        logging.debug('Deleting temporary folder {}'.format(modified))
        shutil.rmtree(modified)
    except IOError:
        logging.warning('One or more temporary folders could not be removed')

    # Finish up
    if isinstance(bar, UserInterface.ProgressBar):
        bar.close()

    if status:
        logging.info('DicomExport completed successfully in {:.3f} seconds'.format(time.time() - tic))
        UserInterface.MessageBox('DICOM export was successful', 'Export Success')

    else:
        logging.warning('DicomExport completed with errors in {:.3f} seconds'.format(time.time() - tic))
        UserInterface.WarningBox('DICOM export finished but with errors', 'Export Warning')

    return status


def machines(beamset=None):
    """machine_list = DicomExport.machines(beamset=get_current('BeamSet'))"""

    machine_list = []

    # If a beamset is provided, search through each beam and store a list of matching to machines
    if beamset is not None:
        beam_list = []
        for b in range(len(beamset.Beams)):
            beam_list.append([])
            for c in filter_xml.findall('filter'):
                if c.findall('from/machine')[0].text == beamset.Beams[b].MachineReference.MachineName:
                    for t in c.findall('to'):
                        if 'type' in c.attrib and c.attrib['type'] == 'machine/energy' and \
                                beamset.Beams[b].MachineReference.Energy == float(c.findall('from/energy')[0].text) \
                                and c.findall('from/energy')[0].attrib['type'].lower() == beamset.Modality.lower():
                            beam_list[b].append(t.findall('machine')[0].text)

                        elif 'type' in c.attrib and c.attrib['type'] == 'machine':
                            beam_list[b].append(t.findall('machine')[0].text)

        sets = iter(map(set, beam_list))
        machine_list = sets.next()
        for s in sets:
            machine_list = machine_list.intersection(s)

        return list(sorted(machine_list))

    # Otherwise just return a list of all to machines
    else:
        for m in filter_xml.findall('filter/to/machine'):
            machine_list.append(m.text)

        return list(sorted(set(machine_list)))


def energies(beamset=None, machine=None):
    """energy_list = DicomExport.energies(beamset=get_current('BeamSet'), machine='TrueBeam')"""

    # The energy list is a key/value dictionary
    energy_list = {}

    # Loop through each filter
    for c in filter_xml.findall('filter'):

        # If the filter is a machine and energy filter, verify the machine matches
        if 'type' in c.attrib and c.attrib['type'] == 'machine/energy' and \
                (beamset is None or c.findall('from/machine')[0].text == beamset.MachineReference.MachineName):
            for t in c.findall('to'):
                if machine is None or t.findall('machine')[0].text == machine and 'type' in \
                        t.findall('energy')[0].attrib and \
                        (beamset is None or t.findall('energy')[0].attrib['type'].lower() == beamset.Modality.lower()):
                    energy_list[float(c.findall('from/energy')[0].text)] = t.findall('energy')[0].text

        # Otherwise, if only an energy filter
        elif 'type' in c.attrib and c.attrib['type'] == 'energy' and \
                (beamset is None or c.findall('from/energy')[0].attrib['type'].lower() == beamset.Modality.lower()):
            for t in c.findall('to'):
                energy_list[float(c.findall('from/energy')[0].text)] = t.findall('energy')[0].text

    return energy_list


def destinations():
    """destination_list = DicomExport.destinations()"""

    # Return a list of all DICOM destinations
    dest_list = []
    for d in dest_xml.findall('destination/name'):
        dest_list.append(d.text)

    return sorted(dest_list)


def destination_info(destination):
    """info = DicomExport.destination_info('MIM')"""

    # Return a dictionary of DICOM destination parameters
    info = {}
    for d in dest_xml.findall('destination'):
        if d.findall('name')[0].text == destination:
            for e in d.findall('*'):
                if 'type' in e.attrib and e.attrib['type'] == 'text':
                    info[e.tag] = e.text
                elif 'type' in e.attrib and e.attrib['type'] == 'int':
                    info[e.tag] = int(e.text)
                elif 'type' in e.attrib and e.attrib['type'] == 'float':
                    info[e.tag] = float(e.text)
                elif 'type' in e.attrib and e.attrib['type'] == 'bool':
                    info[e.tag] = e.text.lower() == 'true'
                else:
                    info[e.tag] = e.text

    return info


def compare(ds, dso):
    """edits = DicomExport.compare(dataset1, dataset2)"""

    edits = _Edits()
    for k0 in ds.keys():
        if k0 not in dso:
            edits.add(ds[k0])

        elif ds[k0].VR == 'SQ':
            for i0 in range(len(ds[k0].value)):
                for k1 in ds[k0].value[i0].keys():
                    if k1 not in dso[k0].value[i0]:
                        edits.add(ds[k0].value[i0][k1])

                    elif ds[k0].value[i0][k1].VR == 'SQ':
                        for i1 in range(len(ds[k0].value[i0][k1].value)):
                            for k2 in ds[k0].value[i0][k1].value[i1].keys():
                                if k2 not in dso[k0].value[i0][k1].value[i1]:
                                    edits.add(ds[k0].value[i0][k1].value[i1][k2])

                                elif ds[k0].value[i0][k1].value[i1][k2].VR == 'SQ':
                                    for i2 in range(len(ds[k0].value[i0][k1].value[i1][k2].value)):
                                        for k3 in ds[k0].value[i0][k1].value[i1][k2].value[i2].keys():
                                            if k3 not in dso[k0].value[i0][k1]. \
                                                    value[i1][k2].value[i2]:
                                                edits.add(ds[k0].value[i0][k1].value[i1][k2].value[i2][k3])

                                            elif ds[k0].value[i0][k1].value[i1][k2].value[i2][k3].VR == 'SQ':
                                                raise KeyError('Unsupported number of nested sequences')

                                            elif ds[k0].value[i0][k1].value[i1][k2].value[i2][k3].value != \
                                                    dso[k0].value[i0][k1].value[i1][k2].value[i2][k3].value:
                                                edits.add(ds[k0].value[i0][k1].value[i1][k2].value[i2][k3])

                                elif ds[k0].value[i0][k1].value[i1][k2].value != \
                                        dso[k0].value[i0][k1].value[i1][k2].value:
                                    edits.add(ds[k0].value[i0][k1].value[i1][k2])

                    elif ds[k0].value[i0][k1].value != dso[k0].value[i0][k1].value:
                        edits.add(ds[k0].value[i0][k1])

        elif ds[k0].value != dso[k0].value:
            edits.add(ds[k0])

    return edits


class _Edits:
    """_Edits is an internal class that is used by DicomExport.send() to keep track of DICOM tag edits"""

    def __init__(self):
        """edits = _Edits()"""
        self.elements = []
        self.tags = []

    def add(self, element, beam=None, cp=None):
        """edits.add(ds.TagName)"""

        self.elements.append(element)
        self.tags.append("0x{0:04x}{1:04x}".format(element.tag.group, element.tag.element))
        if beam is not None and cp is not None:
            if 'BeamNumber' in beam:
                logging.debug('Element {} on beam {}, CP {} is now {}'.format(self.tags[-1],
                                                                              beam.BeamNumber,
                                                                              cp.ControlPointIndex,
                                                                              element.value))
            elif 'ReferencedBeamNumber' in beam:
                logging.debug('Element {} on beam {}, CP {} is now {}'.format(self.tags[-1],
                                                                              beam.ReferencedBeamNumber,
                                                                              cp.ControlPointIndex,
                                                                              element.value))
        elif beam is not None:
            if 'BeamNumber' in beam:
                logging.debug('Element {} on beam {} is now {}'.format(self.tags[-1],
                                                                       beam.BeamNumber,
                                                                       element.value))
            elif 'ReferencedBeamNumber' in beam:
                logging.debug('Element {} on beam {} is now {}'.format(self.tags[-1],
                                                                       beam.ReferencedBeamNumber,
                                                                       element.value))
        else:
            logging.debug('Element {} is now {}'.format(self.tags[-1], element.value))

    def length(self):
        return len(self.elements)

    def matches(self, edits):
        """boolean = edits.matches(other_edits)"""

        self.tags.sort()
        edits.tags.sort()
        if len(self.tags) == len(edits.tags) and self.tags == edits.tags:
            return True
        else:
            logging.warning('Expected modification tags: ' + ', '.join(self.tags))
            logging.warning('Observed modification tags: ' + ', '.join(edits.tags))
            return False
