""" DICOM Export Function

    The DicomExport.send() function uses the RayStation ScriptableDicomExport()
    function, pydicom, and pynetdicom3 to export DICOM RT plan data to a temporary
    folder, then modify the contents of the DICOM files, and finally to send the
    modified files to one or more destinations. In this manner, machine names and
    non-standard beam energies (FFF) can be configured in the system.

    Below is an example of how to call the send() function

    DicomExport.send(case=get_current('Case'),
                     destination='Transfer Folder',
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

# Parse destination and filters XML files
dest_xml = xml.etree.ElementTree.parse(os.path.join(os.path.dirname(__file__), 'DicomDestinations.xml'))
filter_xml = xml.etree.ElementTree.parse(os.path.join(os.path.dirname(__file__), 'DicomFilters.xml'))


def send(case,
         destination,
         exam=None,
         beamset=None,
         structures=True,
         plandose=True,
         beamdose=False,
         ignore_warnings=False,
         ignore_errors=False,
         anonymize=None,
         filters=None,
         machine=None,
         bar=True):
    """DicomExport.send(case=get_current('Case'), destination='MIM', exam=get_current('Examination'),
                        beamset=get_current('BeamSet'))"""

    # Start timer
    tic = time.time()
    status = True

    # Re-cast string destination as list
    if isinstance(destination, str):
        destination = [destination]

    # Filter machine and energy by default
    if filters is None:
        filters = ['machine', 'energy']

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

    # Establish connections with all SCP destinations
    if not bar:
        bar = UserInterface.ProgressBar(text='Establishing connection to DICOM destinations',
                                        title='Export Progress',
                                        marquee=True)

    for d in destination:
        info = destination_info(d)
        if len({'host', 'aet', 'port'}.difference(info.keys())) == 0:
            ae = pynetdicom3.AE(scu_sop_class=['1.2.840.10008.1.1'])
            logging.debug('Requesting Association with {}'.format(info['host']))
            assoc = ae.associate(info['host'], int(info['port']))

            # Throw errors unless C-ECHO responds
            if assoc.is_established:
                logging.debug('Association accepted by the peer')
                status = assoc.send_c_echo()
                assoc.release()
                logging.debug('C-ECHO Response: 0x{0:04x}'.format(status.Status))

            elif assoc.is_rejected and not ignore_errors:
                bar.close()
                raise IOError('Association to {} was rejected by the peer'.format(info['host']))

            elif assoc.is_aborted and not ignore_errors:
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
        if plandose:
            args['BeamSetDoseForBeamSets'] = [beamset.BeamSetIdentifier()]

        if beamdose:
            args['BeamDosesForBeamSets'] = [beamset.BeamSetIdentifier()]

    elif exam is not None and structures:
        args['RtStructureSetsForExaminations'] = [exam.Name]

    # Append anonymization parameters
    if anonymize is not None and hasattr(anonymize, 'name') and hasattr(anonymize, 'id'):
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
            edits = []
            if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                for b in ds.BeamSequence:

                    # If applying a machine filter
                    if machine is not None:
                        if b.TreatmentMachineName != machine:
                            logging.debug('Updating {} on beam {} to {}'.format(
                                str(b.data_element('TreatmentMachineName').tag), b.BeamNumber, machine))
                            b.TreatmentMachineName = machine
                            edits.append(str(b.data_element('TreatmentMachineName').tag))

                    # If applying an energy filter
                    if filters is not None and 'energy' in filters and hasattr(b, 'ControlPointSequence'):
                        for c in b.ControlPointSequence:
                            if hasattr(c, 'NominalBeamEnergy') and c.NominalBeamEnergy in energy_list.keys():
                                e = float(re.sub('\D+', '', energy_list[c.NominalBeamEnergy]))
                                m = re.sub('\d+', '', energy_list[c.NominalBeamEnergy])
                                if c.NominalBeamEnergy != e:
                                    logging.debug('Updating {} on beam {}, CP {} to {}'.format(str(
                                        c.data_element('NominalBeamEnergy').tag), b.BeamNumber, c.ControlPointIndex, e))
                                    c.NominalBeamEnergy = e
                                    edits.append(str(c.data_element('NominalBeamEnergy').tag))

                                # If a non-standard fluence, add mode ID and NON_STANDARD flag
                                if not hasattr(b, 'FluenceModeID') or b.FluenceModeID != m:
                                    logging.debug('Updating {} on beam {}, CP {} to {}'.format(
                                        str(b.data_element('FluenceModeID').tag), b.BeamNumber, c.ControlPointIndex, m))
                                    b.FluenceModeID = m
                                    edits.append(str(b.data_element('FluenceModeID').tag))
                                    if m != '':
                                        logging.debug('Updating {} on beam {}, CP {} to {}'.format(
                                            str(b.data_element('FluenceMode').tag), b.BeamNumber, c.ControlPointIndex,
                                            'NON_STANDARD'))
                                        b.FluenceMode = 'NON_STANDARD'
                                        edits.append(str(b.data_element('FluenceMode').tag))

            # If no edits are needed, copy the file to the modified directory
            if len(edits) == 0:
                logging.debug('File {} does not require modification, and will be copied directly'.format(o))
                shutil.copy(os.path.join(original, o), modified)

            else:
                edited[o] = edits
                logging.debug('File {} re-saved with {} edits'.format(o, len(edits)))
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
                edits = []
                for k0 in ds.keys():
                    if ds[k0].VR == 'SQ':
                        for i0 in range(len(ds[k0].value)):
                            for k1 in ds[k0].value[i0].keys():
                                if ds[k0].value[i0][k1].VR == 'SQ':
                                    for i1 in range(len(ds[k0].value[i0][k1].value)):
                                        for k2 in ds[k0].value[i0][k1].value[i1].keys():
                                            if ds[k0].value[i0][k1].value[i1][k2].VR == 'SQ':
                                                for i2 in range(len(ds[k0].value[i0][k1].value[i1][k2].value)):
                                                    for k3 in ds[k0].value[i0][k1].value[i1][k2].value[i2].keys():
                                                        if ds[k0].value[i0][k1].value[i1][k2].value[i2][k3].VR == 'SQ':
                                                            if not ignore_errors:
                                                                if isinstance(bar, UserInterface.ProgressBar):
                                                                    bar.close()

                                                                raise KeyError('Too many nested sequences')
                                                            else:
                                                                status = False

                                                        elif k3 not in dso[k0].value[i0][k1]. \
                                                                value[i1][k2].value[i2]:
                                                            edits.append(str(ds[k0].value[i0][k1].value[i1][k2].
                                                                             value[i2][k3].tag))

                                                        elif ds[k0].value[i0][k1].value[i1][k2].value[i2][k3].value != \
                                                                dso[k0].value[i0][k1].value[i1][k2]. \
                                                                        value[i2][k3].value:
                                                            edits.append(str(ds[k0].value[i0][k1].value[i1][k2].
                                                                             value[i2][k3].tag))

                                            elif k2 not in dso[k0].value[i0][k1].value[i1]:
                                                edits.append(str(ds[k0].value[i0][k1].value[i1][k2].tag))

                                            elif ds[k0].value[i0][k1].value[i1][k2].value != \
                                                    dso[k0].value[i0][k1].value[i1][k2].value:
                                                edits.append(str(ds[k0].value[i0][k1].value[i1][k2].tag))

                                elif k1 not in dso[k0].value[i0]:
                                    edits.append(str(ds[k0].value[i0][k1].tag))

                                elif ds[k0].value[i0][k1].value != dso[k0].value[i0][k1].value:
                                    edits.append(str(ds[k0].value[i0][k1].tag))

                    elif k0 not in dso:
                        edits.append(str(ds[k0].tag))

                    elif ds[k0].value != dso[k0].value:
                        edits.append(str(ds[k0].tag))

                # The edits list should match the expected list generated above
                if len(edits) == len(edited[m]) and edits.sort() == edited[m].sort():
                    logging.debug('File {} edits are consistent with expected'.format(m))

                else:
                    logging.error('Expected modification tags: ' + ', '.join(edited[m]))
                    logging.error('Observed modification tags: ' + ', '.join(edits))
                    status = False
                    if not ignore_errors:
                        if isinstance(bar, UserInterface.ProgressBar):
                            bar.close()

                        raise KeyError('DICOM Export modification inconsistency detected')

            # Send file
            for d in destination:
                info = destination_info(d)

                # Send to SCP via pynetdicom3
                if len({'host', 'aet', 'port'}.difference(info)) == 0:
                    ae = pynetdicom3.AE(scu_sop_class=pynetdicom3.StorageSOPClassList)
                    assoc = ae.associate(info['host'], int(info['port']))
                    if assoc.is_established:
                        status = assoc.send_c_store(dataset=ds,
                                                    msg_id=1,
                                                    priority=0,
                                                    originator_aet='RayStation',
                                                    originator_id=None)
                        assoc.release()
                        logging.info('{0} -> {1} C-STORE status: 0x{2:04x}'.format(m, d, status.Status))
                        if status.Status != 0:
                            status = False
                            if not ignore_errors:
                                if isinstance(bar, UserInterface.ProgressBar):
                                    bar.close()

                                raise IOError('C-STORE ERROR: 0x{2:04x}'.format(m, d, status.Status))

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

                    logging.info('Exporting {} to {}'.format(m, os.path.join(info['path'], ds.PatientID)))
                    shutil.copy(os.path.join(modified, m), os.path.join(info['path'], ds.PatientID))

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
    logging.debug('Deleting temporary folder {}'.format(original))
    shutil.rmtree(original)
    logging.debug('Deleting temporary folder {}'.format(modified))
    shutil.rmtree(modified)

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

    # Loop through each filter tag in the XML file
    for c in filter_xml.findall('filter'):

        # The FROM machine corresponds to the machine model
        m = c.findall('to/machine')[0].text

        # If the filter is both machine and energy, verify the al beam energies match
        if beamset is not None and 'type' in c.attrib and c.attrib['type'] == 'machine/energy' and \
                c.findall('from/machine')[0].text == beamset.MachineReference.MachineName:
            match = True
            e = float(c.findall('from/energy')[0].text)
            for b in beamset.Beams:
                if b.MachineReference.Energy != e:
                    match = False
                    break

            if match:
                machine_list.append(m)

        # Otherwise, if this is only a machine filter
        elif beamset is not None and 'type' in c.attrib and c.attrib['type'] == 'machine' and \
                c.findall('from/machine')[0].text == beamset.MachineReference.MachineName:
            machine_list.append(m)

        # If no machine is provided, return a full list
        elif beamset is None:
            machine_list.append(m)

    # Return a unique, sorted list
    return list(sorted(set(machine_list)))


def energies(beamset=None, machine=None):
    """energy_list = DicomExport.energies(beamset=get_current('BeamSet'), machine='TrueBeam')"""

    # The energy list is a key/value dictionary
    energy_list = {}

    # Loop through each filter
    for c in filter_xml.findall('filter'):

        # If the filter is a machine and energy filter, verify the machine matches
        if 'type' in c.attrib and c.attrib['type'] == 'machine/energy' and \
                c.findall('from/machine')[0] == beamset.MachineReference.MachineName:
            for t in c.findall('to'):
                if machine is None or t.findall('machine')[0] == machine:
                    energy_list[float(c.findall('from/energy')[0])] = t.findall('energy')[0].text

        # Otherwise, if only an energy filter
        elif 'type' in c.attrib and c.attrib['type'] == 'energy':
            for t in c.findall('to'):
                energy_list[float(c.findall('from/energy')[0])] = t.findall('energy')[0].text

    return energy_list


def destinations():
    """dest_list = DicomExport.destinations()"""

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
                info[e.tag] = e.text

    return info
