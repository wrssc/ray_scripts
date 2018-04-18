


import tempfile
import logging
import UserInterface
import os
import pydicom
import pynetdicom3
import shutil


# DICOM destinations dicts with names and details either as a dict of {host, aet, port} or a folder path
destinations = {'Mobius3D': {'host': 'mobius.uwhealth.wisc.edu', 'aet': 'MOBIUS3D', 'port': '104'},
                'Delta4':   {'path': r'\\aria.uwhealth.wisc.edu\echart\Delta4\DICOM'}}

# Machine filters are dicts of TPS models and a list of mapped machines
machine_filters = {'TrueBeam': ['TrueBeam2588', 'TrueBeam2871'],
                   'TrueBeamSTx': ['TrueBeam1358']}

# Energy filters are dicts of TPS energy and a list of mapped energy and fluence mode ID (leave blank for standard)
energy_filters = {7: [6, 'FFF'],
                  11: [10, 'FFF']}


def Send(case, destination, exam=None, beamset=None, beamdose=False, ignore_warnings=False, ignore_errors=False,
         anonymize=None, filter=None):

    # Attempt to filter machine and energy by default
    if filter is None:
        filter = ['machine', 'energy']

    # Create temporary folders to store original and modified exports
    original = tempfile.mkdtemp()
    modified = tempfile.mkdtemp()

    # Validate destination
    if destination not in destinations.keys():
        raise IndexError('The provided DICOM destination is not in the available list')

    # If multiple machine filters exist, prompt the user to select one
    new_machine = None
    if filter is not None and 'machine' in filter and beamset is not None:
        if beamset.MachineReference.MachineName in machine_filters.keys():
            if len(machine_filters[beamset.MachineReference.MachineName]) > 1:
                dialog = UserInterface.ButtonList(inputs=machine_filters[beamset.MachineReference.MachineName])
                new_machine = dialog.show()

            else:
                new_machine = machine_filters[beamset.MachineReference.MachineName][0]

    # Export data to original folder
    args = {'IgnorePreConditionWarnings': ignore_warnings, 'DicomFilter': ''}

    if exam is not None:
        args['Examinations'] = [exam]

    if beamset is not None:
        args['RtStructureSetsReferencedFromBeamSets'] = [beamset.BeamSetIdentifier()]
        args['BeamSets'] = [beamset.BeamSetIdentifier()]

        if beamdose:
            args['BeamDosesForBeamSets'] = [beamset.BeamSetIdentifier()]

    if anonymize is not None and hasattr(anonymize, 'name') and hasattr(anonymize, 'id'):
        args['Anonymize'] = True
        args['AnonymizedName'] = anonymize['name']
        args['AnonymizedId'] = anonymize['id']

    try:
        logging.debug('Executing ScriptableDicomExport() to path {}'.format(original))
        case.ScriptableDicomExport(**args)

    except Exception as error:
        if ignore_errors:
            logging.warning(str(error))

        else:
            raise

    # Load the DICOM files back in, applying filters
    edited = []
    for f in os.listdir(original):

        # Try to open as a DICOM file
        try:
            logging.debug('Reading file {}'.format(f))
            ds = pydicom.dcmread(os.path.join(import_path, s, f))

            # If this is a DICOM RT plan
            edits = 0
            if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':

                # If applying a machine filter
                if filter is not None and 'machine' in filter and new_machine is not None:
                    for b in ds.BeamSequence:
                        if b.TreatmentMachineName != new_machine:
                            edits += 1
                            b.TreatmentMachineName = new_machine

                # If applying an energy filter
                if filter is not None and 'energy' in filter and hasattr(b, 'ControlPointSequence'):
                    for c in b.ControlPointSequence:
                        if hasattr(c, 'NominalBeamEnergy') and c.NominalBeamEnergy in energy_filters.keys():
                            if c.NominalBeamEnergy != energy_filters[c.NominalBeamEnergy][0]:
                                edits += 1
                                c.NominalBeamEnergy = energy_filters[c.NominalBeamEnergy][0]

                            if not hasattr(b, 'FluenceModeID') or b.FluenceModeID != \
                                    energy_filters[c.NominalBeamEnergy][1]:
                                edits += 1
                                b.FluenceModeID = energy_filters[c.NominalBeamEnergy][1]
                                if energy_filters[c.NominalBeamEnergy][1] != '':
                                    edits += 1
                                    b.FluenceMode = 'NON_STANDARD'

            # If no edits are needed, copy the file to the modified directory
            if edits == 0:
                logging.debug('File {} does not require modification, and will be copied directly'.format(f))
                shutil.copy(os.path.join(original, f), modified)

            else:
                edited.append(f)
                logging.debug('File {} re-saved with {} edits'.format(f, edits)
                ds.save_as(os.path.join(modified, f))

        except pydicom.errors.InvalidDicomError:
            if ignore_errors:
                logging.warning('File {} could not be read during modification, skipping'.format(f))

            else:
                raise

    # If a DICOM SCP, send via pynetdicom3
    if hasattr(destinations[destination], 'host') and hasattr(destinations[destination], 'aet') and \
            hasattr(destinations[destination], 'port')

        ae = pynetdicom3.AE(scu_sop_class=pynetdicom3.StorageSOPClassList)
        logging.debug('Requesting Association with {}'.format(destinations[destination].host))
        assoc = ae.associate(destinations[destination]['host'], destinations[destination]['port'])

        if assoc.is_established:
            logging.debug('Association accepted by the peer')
            status = assoc.send_c_echo()
            if status:
                logging.debug('C-ECHO Response: 0x{0:04x}'.format(status.Status))

            for f in os.listdir(modified):

                try:
                    ds = pydicom.read_file('dcmfile')

                    # Validate changes against original file
                    if f in edited:
                        logging.debug('Reviewing edited file')








                    status = assoc.send_c_echo(ds)
                    logging.debug('{} C-STORE status: {}'.format(f, status))

                except pydicom.errors.InvalidDicomError:
                    if ignore_errors:
                        logging.warning('File {} could not be read during export, skipping'.format(f))

                    else:
                        raise

            assoc.release()

        elif assoc.is_rejected:
            raise IOError('Association to {} was rejected by the peer'.format(destinations[destination]['host']))

        elif assoc.is_aborted:
            raise IOError('Received A-ABORT from the peer during association to {}'.
                          format(destinations[destination]['host']))

    # Otherwise, if a folder destination, copy to remote path
    elif hasattr(destinations[destination], 'path'):
        for f in os.listdir(modified):
            logging.info('Exporting {} to {}'.format(f, destinations[destination]['path']))
            shutil.copy(os.path.join(modified, f), destinations[destination]['path'])


    # Delete temporary folders
    shutil.rmtree(original)
    shutil.rmtree(modified)