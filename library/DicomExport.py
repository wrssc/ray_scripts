""" DICOM Export Functions

    The DicomExport.send() function uses the RayStation ScriptableDicomExport()
    function, pydicom, and pynetdicom to export DICOM RT data to a temporary folder
    then modify the contents of the DICOM files, and finally to send the modified
    files to one or more destinations. In this manner, machine names and non-standard
    beam energies (FFF) can be corrected during export to the Record & Verify system.

    This function will read in two XML files during import: DicomDestinations.xml
    and DicomFilters.xml. They should contain DICOM destination and machine/energy
    filters, respectively. For information on their required formats, see the
    provided wiki link in __help__.

    Note that the addition of TomoTherapy Planning requires a slightly different call
    to ScriptableDicomExport() and the avoidance of attempts to create an AE Title-based
    association with RayGateway. RayGateway is not a standard DICOM destination. Rather
    it is used to give RayStation-generated DICOM plans the secret sauce they need to
    be interpretable by IDMS. As a result, in version 1.0.1 I am only adding RS-based export
    to the script. I do not have a filtering strategy as this time. - abayliss

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
    Version History:
    1.0.0 Original Release
    1.0.1 Update with TomoTherapy support for IDMS and RayGateway (without DICOM filtering)
    1.0.2 Added support for sending a TomoTherapy-based QA Plan with a filter for gantry period
    1.1.0 Changed to pynetdicom from pynetdicom3

    TODO:
        * Make sure logical tests are applied to filters to ensure suitability of each filter now
          that multiple beamsets are being exported.

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Mark Geurts and Adam Bayliss'
__contact__ = 'rabayliss@gmail.com'
__version__ = '1.1.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/DICOM-Export'
__copyright__ = 'Copyright (C) 2020, University of Wisconsin Board of Regents'

import os
import xml.etree.ElementTree
import time
import tempfile
import logging
import UserInterface
import pydicom
# import pynetdicom
from pynetdicom import AE
from pynetdicom.sop_class import RTPlanStorage, RTStructureSetStorage, CTImageStorage, RTDoseStorage, Verification
from pydicom.uid import ImplicitVRLittleEndian
from pydicom.dataset import Dataset
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


class InvalidOperationException(Exception):
    pass


def get_referenced_beam_name(rtplan: Dataset, ref_beam: Dataset) -> str:
    """Return the human‐readable BeamName for a ReferencedBeamSequence item,
    falling back to “Beam<Number>” if the name isn’t present.

    Args:
        rtplan (pydicom.dataset.Dataset): The RT Plan Dataset containing BeamSequence.
        ref_beam (pydicom.dataset.Dataset): One entry from
            ds.FractionGroupSequence[0].ReferencedBeamSequence.

    Returns:
        str: The matching BeamName from BeamSequence, or “Beam<Number>”.

    Raises:
        AttributeError: If ref_beam has no ReferencedBeamNumber.
    """
    # 1) get the beam number from the reference sequence
    if not hasattr(ref_beam, "ReferencedBeamNumber"):
        raise AttributeError("ReferencedBeamNumber missing on referenced beam entry")
    try:
        beam_num = int(ref_beam.ReferencedBeamNumber)
    except (ValueError, TypeError):
        return f"Beam{ref_beam.ReferencedBeamNumber}"

    # 2) build a lookup of full beams by number
    lookup = {
        beam.BeamNumber: beam
        for beam in getattr(rtplan, "BeamSequence", [])
        if hasattr(beam, "BeamNumber")
    }

    # 3) return the BeamName if available
    full_beam = lookup.get(beam_num)
    if full_beam and hasattr(full_beam, "BeamName"):
        return full_beam.BeamName

    # 4) fallback
    return f"Beam{beam_num}"


def send(case,
         destination,
         exam=None,
         beamset=None,
         ct=True,
         structures=True,
         plan=True,
         plan_dose=True,
         beam_dose=False,
         qa_plan=None,
         ignore_warnings=False,
         ignore_errors=False,
         bypass_export_check=False,
         rename=None,
         machine=None,
         table=None,
         pa_threshold=None,
         gantry_period=None,
         couch_speed=None,
         round_jaws=False,
         prescription=False,
         no_ref_point_location=False,
         block_accessory=False,
         block_tray_id=False,
         parent_plan=None,
         prdr_dr=False,
         rpm_gating=False,
         setup_beam_filter=True,
         electron_dose_rate_filter=True,
         fff_energy_filter=False,
         bar=True):
    """DicomExport.send(case=get_current('Case'), destination='MIM', exam=get_current('Examination'),
                        beamset=get_current('BeamSet'))"""

    # Start logging and timer
    logging.debug('Executing DICOM send() function, version {}'.format(__version__))
    tic = time.time()
    status = True

    # Re-cast string destination as list
    if isinstance(destination, str):
        destination = [destination]

    # Create temporary folders to store original and modified exports
    original = tempfile.mkdtemp()
    logging.debug('Temporary folder created for original files at {}'.format(original))
    modified = tempfile.mkdtemp()
    logging.debug('Temporary folder created for modified files at {}'.format(modified))

    # Validate destinations
    dest_list = destinations()
    for d in destination:
        if d not in dest_list:
            raise IndexError('The provided DICOM destination list is not valid')

        else:
            logging.debug('Provided destination {} was found'.format(d))
    # Load energy filters for selected machine
    if fff_energy_filter:
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

        # If the plan is a TomoTherapy plan, it will be sent to the RayGateway. However, if it is a QA plan, it cannot be sent
        # to the RayGateway via script as of version 8.0b SP2
        if 'RayGateway' in info['type']:
            if qa_plan:
                # TODO: QA RayGateway delete the sys exit when QA Plans are supported
                # sys.exit('RayGateway Export is not supported at this time')
                logging.debug('RayGateway to be used in {} to export QA plan, association unsupported.'
                              .format(info['host']))
                raygateway_args = info['aet']
                logging.debug('Incorrect argument sent RayGateWay Title: {}, should be {}'.format(raygateway_args, d))
            else:
                logging.debug('RayGateway to be used in {} to export patient plan, association unsupported.'
                              .format(info['host']))
                raygateway_args = info['aet']
        elif len({'host', 'aet', 'port'}.difference(info.keys())) == 0:
            raygateway_args = None
            # Open a DICOM AE requestor for RayStation at RayStation_SSCP
            #   Note that the local port is no longer required.
            ae = AE(ae_title=local_AET)
            # Add the requested context (Verification Service Object pair)
            ae.add_requested_context('1.2.840.10008.1.1')
            logging.debug('Requesting Association with {}'.format(info['host']))
            # Associate the requestor AE
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
        else:
            raygateway_args = None

    # Initialize ScriptableDicomExport() arguments
    args = {'IgnorePreConditionWarnings': ignore_warnings, 'DicomFilter': '', 'ExportFolderPath': original}

    # Append Examinations to export CT
    if ct and exam is not None:
        logging.debug('Examination {} selected for export'.format(exam.Name))
        args['Examinations'] = [exam.Name]

    # Append BeamSets to export RT plan
    if plan and beamset is not None:
        if type(beamset) == list:
            # If multiple beamsets are selected, append all of them
            args['BeamSets'] = [b.BeamSetIdentifier() for b in beamset]
            logging.debug('RT Plan {} selected for export'.format([beamset.BeamSetIdentifier() for beamset in beamset]))
        else:
            args['BeamSets'] = [beamset.BeamSetIdentifier()]
            logging.debug('RT Plan {} selected for export'.format(beamset.BeamSetIdentifier()))

    # Append beamset to export RTSS (if beamset is not present, export RTSS from exam)
    if structures:
        if beamset is not None:
            if type(beamset) == list:
                # If multiple beamsets are selected, append all of them
                args['RtStructureSetsReferencedFromBeamSets'] = [b.BeamSetIdentifier() for b in beamset]
            else:
                logging.debug('Plan structure set selected for export')
                args['RtStructureSetsReferencedFromBeamSets'] = [beamset.BeamSetIdentifier()]

        elif exam is not None:
            logging.debug('Exam structure set selected for export')
            args['RtStructureSetsForExaminations'] = [exam.Name]

    # Append PhysicalBeamDosesForBeamSets and/or PhysicalBeamSetDoseForBeamSets to export RT Dose
    if plan_dose and beamset is not None:
        if type(beamset) == list:
            # If multiple beamsets are selected, append all of them
            args['PhysicalBeamSetDoseForBeamSets'] = [b.BeamSetIdentifier() for b in beamset]
            logging.debug('Plan {} dose selected for export'.format([b.BeamSetIdentifier() for b in beamset]))
        else:
            logging.debug('Plan {} dose selected for export'.format(beamset.BeamSetIdentifier()))
            args['PhysicalBeamSetDoseForBeamSets'] = [beamset.BeamSetIdentifier()]

    if beam_dose and beamset is not None:
        if type(beamset) == list:
            # If multiple beamsets are selected, append all of them
            args['PhysicalBeamDosesForBeamSets'] = [b.BeamSetIdentifier() for b in beamset]
            logging.debug('Beam dose for plan {} selected for export'.format(
                [beamset.BeamSetIdentifier() for beamset in beamset]))
        else:
            logging.debug('Beam dose for plan {} selected for export'.format(beamset.BeamSetIdentifier()))
            args['PhysicalBeamDosesForBeamSets'] = [beamset.BeamSetIdentifier()]

    # Append anonymization parameters to re-identify patient
    if rename is not None and 'name' in rename and 'id' in rename:
        logging.debug('Patient re-named to {}, ID {} for export'.format(rename['name'], rename['id']))
        args['Anonymize'] = True
        args['AnonymizedName'] = rename['name']
        args['AnonymizedId'] = rename['id']

    # Export data to temp folder
    if isinstance(bar, UserInterface.ProgressBar):
        if raygateway_args is not None and len(destination) == 1:
            bar.update(text='Exporting DICOM files to RayGateway')

        else:
            bar.update(text='Exporting DICOM files to temporary folder')

    # Flag set for Tomo DQA
    if qa_plan is not None:
        if 'RayGateway' not in info['type']:  # and filters is not None and 'tomo_dqa' in filters:
            # DQA should be going to delta 4
            # Save to the file destination for filtering
            # TODO: resolve the RS phantom bug to allow the appropriate export of the
            #       phantom based plan.
            args = {'IgnorePreConditionWarnings': ignore_warnings,
                    'QaPlanIdentity': 'Patient',
                    'ExportFolderPath': original,
                    'ExportExamination': False,
                    'ExportExaminationStructureSet': False,
                    'ExportBeamSet': True,
                    'ExportBeamSetDose': True,
                    'ExportBeamSetBeamDose': True}

            qa_plan.ScriptableQADicomExport(**args)

        else:

            args = {'IgnorePreConditionWarnings': ignore_warnings,
                    'QaPlanIdentity': 'Phantom',
                    'TomoOriginalPlanOverride': beamset.BeamSetIdentifier(),
                    'RayGatewayTitle': raygateway_args,
                    'ExportFolderPath': '',
                    'ExportExamination': True,
                    'ExportExaminationStructureSet': True,
                    'ExportBeamSet': True,
                    'ExportBeamSetDose': True,
                    'ExportBeamSetBeamDose': False}

            qa_plan.ScriptableQADicomExport(**args)

    elif raygateway_args is not None and len(destination) == 1:
        if 'anonymize' in info and info['anonymize']:
            random_name = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
            random_id = ''.join(random.choice(string.digits) for _ in range(8))
            logging.debug('Export destination {} is anonymous, patient will be stored under name {} and ID {}'.
                          format(d, random_name, random_id))

        # If we are only sending to the Gateway, do the export and exit.
        logging.debug('Executing ScriptableDicomExport() to RayGateway {}'.format(raygateway_args))
        rg_args = args
        rg_args['RayGatewayTitle'] = raygateway_args
        del rg_args['ExportFolderPath']

        try:
            if parent_plan is None:
                try:
                    case.ScriptableDicomExport(**args)
                except Exception as error:
                    if hasattr(error, 'Message'):
                        # This is the error thrown when a plan is already in the iDMS
                        existing_plan_exception = "_{} already exist".format(beamset.DicomPlanLabel)
                        element_too_long = 'Element 3006,0050 is too long to be written in Explicit'
                        if existing_plan_exception in error.Message:
                            logging.debug('Parent plan likely in iDMS already. Error is {}'.format(error.Message))
                            logging.info('Parent Plan is already in IDMS {}'.format(beamset.DicomPlanLabel))
                            pass
                        else:
                            status = False
                            logging.error('DicomExport failed {}'.format(error))
                            UserInterface.MessageBox('DICOM export failed {}'.format(error), 'Export Fail')
                            raise
                    else:
                        status = False
                        logging.error('DicomExport failed {}'.format(error))
                        UserInterface.MessageBox('DICOM export failed {}'.format(error), 'Export Fail')
                        raise

                logging.info('DicomExport completed successfully in {:.3f} seconds'.format(time.time() - tic))
            else:
                try:
                    beamset.SendTransferredPlanToRayGateway(RayGatewayTitle='RAYGATEWAY',
                                                            PreviousBeamSet=parent_plan,
                                                            OriginalBeamSet=parent_plan,
                                                            IgnorePreConditionWarnings=ignore_warnings)
                except SystemError as e:
                    logging.exception('Error in exporting Parent {}: Transfer plan {}:{}'
                                      .format(parent_plan, beamset.DicomPlanLabel, e))
            if isinstance(bar, UserInterface.ProgressBar):
                bar.close()

            UserInterface.MessageBox('DICOM export was successful', 'Export Success')
        except Exception as error:
            if hasattr(error, 'message'):
                status = False
                logging.error('DicomExport failed {}'.format(error.message))
                UserInterface.MessageBox('DICOM export failed {}'.format(error.message), 'Export Fail')
                raise
            else:
                status = False
                logging.error('DicomExport failed {}'.format(error))
                UserInterface.MessageBox('DICOM export failed {}'.format(error), 'Export Fail')
                raise

        return status

    else:
        logging.debug('Executing ScriptableDicomExport() to path {}'.format(original))
        try:
            case.ScriptableDicomExport(**args)
        except Exception as error:
            if ignore_errors:
                logging.debug('type of error is {}'.format(type(error)))
                logging.warning(str(error))
                status = False
            else:
                logging.debug('type of error is {}'.format(type(error)))
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

                # 1) Setup fields
                # Apply setup Dose rate and nominal beam energy for setup fields
                if setup_beam_filter:
                    message = adjust_setup_field(ds=ds, expected=expected)
                    if message:
                        logging.debug(message)

                # 2) Machine filter
                if machine is not None:
                    message = apply_machine_filter(ds=ds, machine=machine, expected=expected)
                    logging.debug(message)

                # 3) PRDR filter
                if prdr_dr:
                    message = apply_prdr_filter(ds=ds, beamset=beamset, expected=expected)
                    if message:
                        logging.debug(message)

                # 4) Electron dose rate
                if electron_dose_rate_filter:
                    message = adjust_electron_dose_rate(ds=ds, expected=expected)
                    logging.debug(message)

                # 5) Block accessory filter
                if block_accessory:
                    message = apply_block_accessory_filter(ds=ds, expected=expected)
                    logging.debug(message)

                # 6) Block tray ID filter
                if block_tray_id:
                    message = apply_block_tray_id_filter(ds=ds, expected=expected)
                    logging.debug(message)

                # 7) Table position filter
                if table is not None:
                    message = apply_table_position_filter(ds=ds, expected=expected, table_position=table)
                    logging.debug(message)

                # 8) Round jaws filter
                if round_jaws:
                    message = apply_round_jaws_filter(ds=ds, expected=expected)
                    logging.debug(message)

                # 9) PA beam angle filter
                if pa_threshold:
                    message = apply_pa_beam_angle_filter(ds=ds, expected=expected, pa_threshold=pa_threshold)
                    logging.debug(message)

                # 10) Energy filter
                if energy_list:
                    message = apply_energy_filter(ds=ds, expected=expected, energy_list=energy_list)
                    logging.debug(message)

                # 11) Couch speed filter
                if couch_speed:
                    message = apply_couch_speed_filter(ds=ds, expected=expected, couch_speed=couch_speed)
                    logging.debug(message)

                # 12) Gantry period filter
                if gantry_period:
                    message = apply_gantry_period_filter(ds=ds, expected=expected, gantry_period=gantry_period)
                    logging.debug(message)

                # 13) Prescription and RPM gating (unchanged)
                if prescription:
                    message = old_apply_prescription_filter(ds=ds, beamset=beamset, expected=expected,
                                                            ref_point_location=no_ref_point_location)
                    if 'ERROR' in message:
                        raise InvalidOperationException(
                            'Prescription filter failed for {}: {}'.format(get_rt_plan_label(ds), message))
                    elif message:
                        logging.debug(f"Applied prescription filter to {get_rt_plan_label(ds)}: {message}")

                # 14) RPM gating filter
                if rpm_gating:
                    message = apply_rpm_gating_filter(ds=ds, expected=expected)
                    if message:
                        logging.debug(f"Applied RPM gating filter to {get_rt_plan_label(ds)}: {message}")

            # If no edits are needed, copy the file to the modified directory
            if expected.length() == 0:
                logging.debug(f'File {o} does not require modification, and will be copied directly')
                shutil.copy(os.path.join(original, o), modified)

            else:
                edited[o] = expected
                logging.debug(f'File {o} re-saved with {expected.length()} edits')
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
    for d in destination:
        info = destination_info(d)
        if 'anonymize' in info and info['anonymize']:
            random_name = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
            random_id = ''.join(random.choice(string.digits) for _ in range(8))
            logging.debug('Export destination {} is anonymous, patient will be stored under name {} and ID {}'.
                          format(d, random_name, random_id))

        # If an AE destination, establish pynetdicom association
        if 'RayGateway' in info['type'] and qa_plan is None:
            logging.debug('Multiple destinations, ScriptableDicomExport() to RayGateway {}'.format(raygateway_args))
            rg_args = args
            rg_args['RayGatewayTitle'] = raygateway_args
            del rg_args['ExportFolderPath']

            try:
                case.ScriptableDicomExport(**args)
                logging.info('Export to {} success'.format(info['aet']))

            except Exception as error:
                status = False
                if hasattr(error, 'message'):
                    logging.error('DicomExport failed {}'.format(error.message))
                    UserInterface.MessageBox('DICOM export failed {}'.format(error.message), 'Export Fail')

                else:
                    logging.error('DicomExport failed {}'.format(error))
                    UserInterface.MessageBox('DICOM export failed {}'.format(error), 'Export Fail')

                raise

            assoc = None

        elif len({'host', 'aet', 'port'}.difference(info)) == 0:
            # Establish an AE
            ae = AE(ae_title=local_AET)
            ae.add_requested_context(CTImageStorage, ImplicitVRLittleEndian)
            ae.add_requested_context(RTStructureSetStorage, ImplicitVRLittleEndian)
            ae.add_requested_context(RTPlanStorage, ImplicitVRLittleEndian)
            ae.add_requested_context(RTDoseStorage, ImplicitVRLittleEndian)
            ae.add_requested_context(Verification)
            # MIM and Delta4 appear to timeout on a setting called ARTIM
            ae.network_timeout = 600.
            assoc = ae.associate(info['host'], int(info['port']), ae_title=info['aet'])

        else:
            assoc = None

        i = 0
        total = len(os.listdir(modified))
        for m in os.listdir(modified):
            i += 1
            if isinstance(bar, UserInterface.ProgressBar):
                bar.update(text='Validating and Exporting Files to {} ({} of {})'.format(d, i, total))

            # send a message to the ae
            try:
                message = assoc.send_c_echo()
                logging.debug('Echo request returned {}'.format(message))
            except AttributeError:
                logging.debug('Selected destination does not have echo properties')
            try:
                logging.debug('Reading modified file {}'.format(os.path.join(modified, m)))
                ds = pydicom.dcmread(os.path.join(modified, m))

                # Validate changes against original file, recursively searching through sequences
                if m in edited and not bypass_export_check:
                    logging.debug('Validating edits against {}'.format(os.path.join(original, m)))
                    dso = pydicom.dcmread(os.path.join(original, m))
                    try:
                        # The Edits list should match the expected list generated above
                        if edited[m].matches(compare(ds, dso)):
                            logging.debug('File {} edits are consistent with expected'.format(m))

                        else:
                            logging.warning(f'File {m} edits are inconsistent with expected')
                            logging.warning(f'result: {edited[m].matches(compare(ds, dso))}')
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

                # If destination has a anonymize tag, remove personal info
                if 'anonymize' in info and info['anonymize']:
                    for t in personal_tags:
                        if hasattr(ds, t):
                            delattr(ds, t)

                    ds.PatientName = ''.join(random.choice(string.ascii_uppercase) for _ in range(8))
                    ds.PatientID = ''.join(random.choice(string.digits) for _ in range(8))
                    ds.PatientBirthdate = ''

                # Do not send to SCP for RayGateway
                if 'RAYGATEWAY' in info['type']:
                    logging.debug('{} is a RayGateway, skipping SCP'.format(info['host']))

                # Send to SCP via pynetdicom
                elif assoc is not None:
                    if assoc.is_established:
                        response = assoc.send_c_store(dataset=ds,
                                                      msg_id=1,
                                                      priority=0,
                                                      originator_aet=None,
                                                      originator_id=None)
                        logging.info('{0} → {1} C-STORE status: 0x{2:04x}'.format(m, d, response.Status))
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
                        logging.info('{} → {} copied'.format(m, os.path.join(info['path'], ds.PatientID)))

                    except IOError:
                        status = False
                        if ignore_errors:
                            logging.warning('{} → {} IOError'.format(m, os.path.join(info['path'], ds.PatientID)))

                        else:
                            if isinstance(bar, UserInterface.ProgressBar):
                                bar.close()

                            raise

            # If pydicom fails, stop export unless ignore_errors flag is set
            except pydicom.errors.InvalidDicomError as e:
                if ignore_errors:
                    logging.warning('File {} could not be read during modification, skipping'.format(m))
                    status = False

                else:
                    if isinstance(bar, UserInterface.ProgressBar):
                        bar.close()
                    logging.warning('File {} contains a dicom error {}'.format(m, e))

                    raise

        if assoc is not None:
            if assoc.is_established:
                assoc.release()

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
                if c.attrib['type'] != 'machine/energy':
                    continue
                if c.find('from/machine').text == beamset.Beams[b].MachineReference.MachineName:
                    for t in c.findall('to'):
                        if 'type' in c.attrib and c.attrib['type'] == 'machine/energy' and \
                                beamset.Beams[b].BeamQualityId.lower() == c.find('from/energy').text.lower() \
                                and c.find('from/energy').attrib['type'].lower() == beamset.Modality.lower():
                            beam_list[b].append(t.find('machine').text)

                        elif 'type' in c.attrib and c.attrib['type'] == 'machine':
                            beam_list[b].append(t.find('machine').text)

        if len(beam_list) > 0:
            sets = iter(map(set, beam_list))
            machine_list = next(sets)
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
                (beamset is None or c.find('from/machine').text == beamset.MachineReference.MachineName):
            for t in c.findall('to'):
                if machine is None or t.find('machine').text == machine and 'type' in \
                        t.find('energy').attrib and \
                        (beamset is None or t.find('energy').attrib['type'].lower() == beamset.Modality.lower()):
                    energy_list[c.find('from/energy').text] = t.find('energy').text

        # Otherwise, if only an energy filter
        elif 'type' in c.attrib and c.attrib['type'] == 'energy' and \
                (beamset is None or c.find('from/energy').attrib['type'].lower() == beamset.Modality.lower()):
            for t in c.findall('to'):
                energy_list[c.find('from/energy').text] = t.find('energy').text

    return energy_list


def adjust_setup_field(ds, expected):
    """
    Adjust the setup field dose rate and nominal beam energy for the given beam.
    Args:
        ds (pydicom.Dataset): the DICOM dataset containing the beam information
        expected: a list of expected changes to be made

    Returns:
        message string: logging message of adjustments
    """
    msg_parts = []
    message = ''
    for beam in ds.BeamSequence:
        dose_rate_updated = False
        nominal_energy_updated = False
        if hasattr(beam, 'TreatmentDeliveryType') and beam.TreatmentDeliveryType == 'SETUP':
            # Change the Meter rate and nominal beam energy
            # cps = beam.ControlPointSequence[0]
            for cp in beam.ControlPointSequence:
                if 'DoseRateSet' in cp and cp.DoseRateSet != 100:
                    cp.DoseRateSet = 100
                    expected.add(cp[0x300a0115], beam=beam, cp=cp)  # Dose Rate Set
                    dose_rate_updated = True
                elif 'DoseRateSet' not in cp:
                    cp.add_new(0x300a0115, 'DS', 100)
                    expected.add(cp[0x300a0115], beam=beam, cp=cp)  # Dose Rate Set
                    dose_rate_updated = True
                if 'NominalBeamEnergy' in cp and cp.NominalBeamEnergy != 6:
                    cp.NominalBeamEnergy = 6
                    expected.add(cp[0x300a0114], beam=beam, cp=cp)  # Nominal Beam Energy updated
                    nominal_energy_updated = True
            if dose_rate_updated or nominal_energy_updated:
                msg = f'Beam {beam.BeamName}: '
                if dose_rate_updated:
                    msg += 'Dose rate updated to 100 MU/min. '
                if nominal_energy_updated:
                    msg += 'Nominal beam energy updated to 6 MV.'
                msg_parts.append(msg)
    # Set the beam name at the front of the message string
    if msg_parts:
        message = '; '.join(msg_parts) + '.'
    return message


def apply_machine_filter(ds, machine, expected):
    """
    Apply a machine filter to all beams in the dataset.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        machine (str): the desired TreatmentMachineName
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if hasattr(beam, 'TreatmentMachineName') and beam.TreatmentMachineName != machine:
            beam.TreatmentMachineName = machine
            expected.add(beam[0x300a00b2], beam=beam)
            messages.append(f'Beam {beam.BeamName}: Machine filter applied: {machine}')
        else:
            messages.append(f'Beam {beam.BeamName}: Machine filter not applied: {machine}')
    return '; '.join(messages)


def get_table_offsets(to_machine, from_machine, device_name, immobilization_type):
    """
    Return alpha (vertical), beta (longitudinal), and gamma (lateral) offsets for a given from_machine, to_machine, device,
    and immobilization type from the machine/table_coordinates filter XML.
    In an HFS orientation, these offsets are applied as:
    VRT = alpha + isoY[cm]
    LNG = beta - isoZ[cm]
    LAT = gamma - isoX[cm]

    Args:
        to_machine (str): The name of the 'to' machine (e.g., 'TrueBeam1358').
        from_machine (str): The name of the 'from' machine (e.g., 'TrueBeamSTx').
        device_name (str): The name of the device used (e.g., 'QFix_Brain_TBCouch_F2andF3').
        immobilization_type (str): The immobilization approach/type (e.g., 'Frameless').

    Returns:
        tuple: (alpha, beta, gamma) as floats. If no match is found, returns (0.0, 0.0, 0.0).

    Raises:
        ValueError: If a matching filter element is found but lacks valid offsets.
    """
    # Iterate through all 'filter' nodes with type="machine/table_coordinates"
    for filter_node in filter_xml.findall("filter"):
        if filter_node.attrib.get('type') != 'machine/table_coordinates':
            continue  # Skip filters of other types
        # Check the <from> child
        from_node = filter_node.find('from')
        if from_node is None:
            continue

        from_machine_node = from_node.find('machine')
        if from_machine_node is None:
            continue

        # Does the 'from_machine' match?
        if from_machine_node.text != from_machine:
            continue

        # Check the <from>/immobilization/device entries
        immob_node = from_node.find('immobilization')
        if immob_node is None:
            continue

        # Gather <device> text inside <from>/immobilization>
        from_device = immob_node.find('device')
        if from_device is None:
            continue
        elif from_device.text != device_name:
            continue

        # Get the immobilization type
        from_immob_type = immob_node.find('immobilization_type')
        if from_immob_type is None:
            continue
        elif from_immob_type.text != immobilization_type:
            continue

        # Now, for each <to> under this <filter>, find a matching machine & device
        for to_node in filter_node.findall('to'):
            to_machine_node = to_node.find('machine')
            if to_machine_node is None:
                continue
            if to_machine_node.text != to_machine:
                continue

            # Check <to>/immobilization block
            to_immob_node = to_node.find('immobilization')
            if to_immob_node is None:
                continue

            # The <to> side has <device> and <immobilization_type> separately
            to_device_node = to_immob_node.find('device')
            to_type_node = to_immob_node.find('immobilization_type')

            if to_device_node is None or to_type_node is None:
                continue

            # Must match device_name and immobilization_type
            if to_device_node.text == device_name and to_type_node.text == immobilization_type:
                # Found a matching <to> entry; gather offsets from <offsets>
                offsets_node = to_node.find('offsets')
                if offsets_node is None:
                    logging.info(
                        f"No <offsets> found for to_machine={to_machine}, device={device_name},"
                        f" immob_type={immobilization_type}."
                    )
                    return 0.0, 0.0, 0.0

                alpha_node = offsets_node.find('alpha')
                beta_node = offsets_node.find('beta')
                gamma_node = offsets_node.find('gamma')

                # Validate offset tags
                if alpha_node is None or beta_node is None or gamma_node is None:
                    raise ValueError(
                        f"Missing alpha/beta/gamma in offsets for machine={to_machine}."
                    )

                try:
                    alpha_val = float(alpha_node.text)
                    beta_val = float(beta_node.text)
                    gamma_val = float(gamma_node.text)
                except ValueError as exc:
                    raise ValueError(
                        f"Failed to parse offsets as floats for machine={to_machine}."
                    ) from exc

                # Return as soon as we find the first matching entry
                return alpha_val, beta_val, gamma_val

    # If we reach here, no matching entry was found
    logging.info(
        f"No matching offsets found for from_machine={from_machine}, to_machine={to_machine}, "
        f"device={device_name}, immobilization_type={immobilization_type}."
    )
    return 0.0, 0.0, 0.0


def apply_prdr_filter(ds, beamset, expected):
    """
    Apply the PRDR filter across all photon beams in the dataset.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        beamset: RayStation beamset object (for DicomPlanLabel)
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    if type(beamset) is not list:
        beamset = [beamset]  # Ensure beamset is a list for iteration
    ill_named = []
    for b in beamset:
        if '_PRD_' not in b.DicomPlanLabel:
            ill_named.append(b.DicomPlanLabel)
    if ill_named:
        messages.append(f'Incorrect labeling of PRDR beamset, but applying PRDR filter to photon beams ' +
                        f'in beamset(s): {", ".join([ill for ill in ill_named])}')
    for beam in ds.BeamSequence:
        if getattr(beam, 'RadiationType', '') == 'PHOTON' and hasattr(beam, 'ControlPointSequence'):
            for cp in beam.ControlPointSequence:
                if 'DoseRateSet' in cp and cp.DoseRateSet != 100:
                    cp.DoseRateSet = 100
                    expected.add(cp[0x300a0115], beam=beam, cp=cp)
                elif 'DoseRateSet' not in cp:
                    cp.add_new(0x300a0115, 'DS', 100)
                    expected.add(cp[0x300a0115], beam=beam, cp=cp)
            messages.append(f'Beam {beam.BeamName}: PRDR dose rate set to 100 MU/min')
    return '; '.join(messages)


def apply_block_accessory_filter(ds, expected):
    """
    Add block accessory sequence to all electron beams that have a block.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if getattr(beam, 'RadiationType', '') == 'ELECTRON' and hasattr(beam, 'BlockSequence'):
            block_name = beam.BlockSequence[0].BlockName
            acc = pydicom.Dataset()
            acc.add_new(0x300A00F9, 'LO', block_name)
            acc.add_new(0x300A0423, 'CS', 'TRAY')
            acc.add_new(0x300A0424, 'IS', block_name)
            beam.add_new(0x300A0420, 'SQ', pydicom.Sequence([acc]))
            expected.add(beam[0x300A0420], beam=beam)
            messages.append(f'Beam {beam.BeamName}: added accessory for block "{block_name}"')
    return '; '.join(messages)


def apply_block_tray_id_filter(ds, expected):
    """
    Override BlockTrayID for all electron beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if getattr(beam, 'RadiationType', '') == 'ELECTRON' and hasattr(beam, 'BlockSequence'):
            bs0 = beam.BlockSequence[0]
            block_name = getattr(bs0, 'BlockName', None)
            tray = 'CustomFFDA'
            if not hasattr(bs0, 'AccessoryCode') or bs0.AccessoryCode != block_name:
                bs0.AccessoryCode = block_name
                expected.add(bs0[0x300A00F9], beam=beam)
            if not hasattr(bs0, 'BlockTrayID') or bs0.BlockTrayID != tray:
                bs0.BlockTrayID = tray
                expected.add(bs0[0x300A00F5], beam=beam)
            messages.append(f'Beam {beam.BeamName}: BlockTrayID set to "{tray}"')
    return '; '.join(messages)


def adjust_electron_dose_rate(ds, expected):
    """
    Adjust the dose rate for all electron beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if getattr(beam, 'RadiationType', '') == 'ELECTRON' and hasattr(beam, 'ControlPointSequence'):
            for cp in beam.ControlPointSequence:
                if 'DoseRateSet' in cp:
                    if cp.DoseRateSet != 1000:
                        cp.DoseRateSet = 1000
                        expected.add(cp[0x300a0115], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: Dose rate updated to 1000 MU/min')
                else:
                    cp.add_new(0x300a0115, 'DS', 1000)
                    expected.add(cp[0x300a0115], beam=beam, cp=cp)
                    messages.append(f'Beam {beam.BeamName}: Dose rate added as 1000 MU/min')
    return '; '.join(messages)


def apply_table_position_filter(ds, expected, table_position):
    """
    Apply table positions to all beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
        table_position (list): [Vert, Long, Lat]
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        for cp in getattr(beam, 'ControlPointSequence', []):
            changes = []
            if 'TableTopVerticalPosition' in cp and cp.TableTopVerticalPosition != table_position[0]:
                cp.TableTopVerticalPosition = table_position[0]
                expected.add(cp[0x300a012a], beam=beam, cp=cp)
                changes.append(f'Vert->{table_position[0]}')
            if 'TableTopLongitudinalPosition' in cp and cp.TableTopLongitudinalPosition != table_position[1]:
                cp.TableTopLongitudinalPosition = table_position[1]
                expected.add(cp[0x300a0129], beam=beam, cp=cp)
                changes.append(f'Long->{table_position[1]}')
            if 'TableTopLateralPosition' in cp and cp.TableTopLateralPosition != table_position[2]:
                cp.TableTopLateralPosition = table_position[2]
                expected.add(cp[0x300a0128], beam=beam, cp=cp)
                changes.append(f'Lat->{table_position[2]}')
            if changes:
                messages.append(f'Beam {beam.BeamName}: ' + ', '.join(changes))
    return '; '.join(messages)


def apply_round_jaws_filter(ds, expected):
    """
    Round jaw positions on all beams to nearest 0.1 cm.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        for cp in getattr(beam, 'ControlPointSequence', []):
            for p in getattr(cp, 'BeamLimitingDevicePositionSequence', []):
                if 'LeafJawPositions' in p and len(p.LeafJawPositions) == 2:
                    low, high = p.LeafJawPositions
                    new_low = math.floor(10 * low) / 10
                    new_high = math.ceil(10 * high) / 10
                    if (low, high) != (new_low, new_high):
                        p.LeafJawPositions = [new_low, new_high]
                        expected.add(p[0x300a011c], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: jaws rounded to [{new_low},{new_high}]')
    return '; '.join(messages)


def apply_pa_beam_angle_filter(ds, expected, pa_threshold):
    """
    Bump gantry to 180.010° for right‐PA beams above threshold.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
        pa_threshold (float): isocenter distance threshold
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if hasattr(beam, 'ControlPointSequence'):
            ok = True
            for cp in beam.ControlPointSequence:
                if (getattr(cp, 'GantryAngle', None) != 180 or
                        getattr(cp, 'GantryRotationDirection', None) != 'NONE' or
                        (hasattr(cp, 'IsocenterPosition') and cp.IsocenterPosition < pa_threshold)):
                    ok = False
                    break
            if ok:
                for cp in beam.ControlPointSequence:
                    cp.GantryAngle = 180.010
                    expected.add(cp[0x300a011e], beam=beam, cp=cp)
                messages.append(f'Beam {beam.BeamName}: Gantry bumped to 180.010°')
    return '; '.join(messages)


def apply_energy_filter(ds, expected, energy_list):
    """
    Map and enforce energy and fluence for all photon beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
        energy_list (dict): original→mapped energy strings
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        if getattr(beam, 'RadiationType', '') == 'PHOTON':
            for cp in getattr(beam, 'ControlPointSequence', []):
                if 'NominalBeamEnergy' in cp and cp.NominalBeamEnergy in energy_list:
                    mapped = energy_list[cp.NominalBeamEnergy]
                    e_val = float(re.sub(r'\D+', '', mapped))
                    mode_id = re.sub(r'\d+', '', mapped)
                    if cp.NominalBeamEnergy != e_val:
                        cp.NominalBeamEnergy = e_val
                        expected.add(cp[0x300a0114], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: Energy→{e_val}')
                    want_nonstd = bool(mode_id)
                    current_nonstd = getattr(beam, 'FluenceMode', '') == 'NON_STANDARD'
                    if want_nonstd and not current_nonstd:
                        beam.FluenceMode = 'NON_STANDARD'
                        expected.add(beam[0x30020051], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: FluenceMode→NON_STANDARD')
                    elif not want_nonstd and current_nonstd:
                        beam.FluenceMode = 'STANDARD'
                        expected.add(beam[0x30020051], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: FluenceMode→STANDARD')
                    if mode_id and getattr(beam, 'FluenceModeID', None) != mode_id:
                        beam.FluenceModeID = mode_id
                        expected.add(beam[0x30020052], beam=beam, cp=cp)
                        messages.append(f'Beam {beam.BeamName}: FluenceModeID→{mode_id}')
    return '; '.join(messages)


def apply_couch_speed_filter(ds, expected, couch_speed):
    """
    Add TomoTherapy QA couch speed to all beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
        couch_speed (dict): beamName→speed
    Returns:
        str: concatenated log messages
    """
    messages = []
    for beam in ds.BeamSequence:
        speed = couch_speed.get(beam.BeamName)
        if speed is not None:
            tag = pydicom.tag.Tag(0x300d, 0x1080)
            val = f"{round(speed, 6):.6f} "
            beam.add_new(tag, 'DS', val)
            expected.add(beam[tag], beam=beam)
            messages.append(f'Beam {beam.BeamName}: CouchSpeed→{val.strip()}')
    return '; '.join(messages)


def apply_gantry_period_filter(ds, expected, gantry_period):
    """
    Add TomoTherapy QA gantry period to all beams.
    Args:
        ds (pydicom.Dataset): the DICOM RTPlan dataset
        expected (_Edits): tracker for edits
        gantry_period (str|float): period value
    Returns:
        str: concatenated log messages
    """
    messages = []
    tag = pydicom.tag.Tag(0x300d, 0x1040)
    for beam in ds.BeamSequence:
        val = f"{gantry_period} "
        beam.add_new(tag, 'DS', val)
        expected.add(beam[tag], beam=beam)
        messages.append(f'Beam {beam.BeamName}: GantryPeriod→{val.strip()}')
    return '; '.join(messages)


def old_apply_prescription_filter(ds, beamset, expected, ref_point_location) -> str:
    """
    Build and insert the primary prescription reference point, and redistribute beam doses.
    Args:
        ds:                 full pydicom Dataset for the RTPlan
        beamset:            beamset object (to grab DicomPlanLabel & Prescription data)
        expected:           the _Edits tracker to record tag edits
        ref_point_location: bool, whether to insert coordinates or SITE
    Returns:
        msg (str): Summary message, or ''.
        TODO: Add Varian private tags for secondary prescription reference points.
    """
    msgs = []
    # If the beamset type is list, then we need to match the DicomPlanLabel attribute with the plan name
    # of the ds passed to this function
    ds_rt_plan_label = get_rt_plan_label(ds)
    if isinstance(beamset, list):
        beamset = next((b for b in beamset if b.DicomPlanLabel == ds_rt_plan_label), None)
    else:
        beamset = beamset
    if beamset is None:
        logging.warning(f'No matching beamset found for DicomPlanLabel: {ds_rt_plan_label} in beamset_list')
        return ''
    else:
        msgs.append(f'Rx Filter for {beamset.DicomPlanLabel}: ')
    # only proceed if prescription data exists
    presc = getattr(beamset.Prescription, 'PrimaryPrescriptionDoseReference', None)
    if (not presc or 'FractionGroupSequence' not in ds
            or len(ds.FractionGroupSequence[0].ReferencedBeamSequence) == 0):
        return ''
    # Create reference point for primary dose prescription in a se
    # Declare a new dataset for the Dose Reference Sequence
    ref = pydicom.Dataset()
    ref.add_new(0x300a0012, 'IS', 1)
    dose_ref_desc = str(beamset.DicomPlanLabel) + '.0'
    ref.add_new(0x300a0016, 'LO', dose_ref_desc)
    msgs.append(f"Set DoseReferenceDescription='{dose_ref_desc}'")

    # Add coordinates to the primary reference point
    if ref_point_location:
        ref.add_new(0x300a0014, 'CS', 'COORDINATES')
        msgs.append("Reference point has location, set DoseReferenceStructureType=COORDINATES")
        ref_beam_seq = ds.FractionGroupSequence[0].ReferencedBeamSequence[0]
        if 'BeamDoseSpecificationPoint' in ref_beam_seq:
            ref.add_new(0x300a0018, 'DS', ref_beam_seq.BeamDoseSpecificationPoint)
            msgs.append(
                f"BeamDoseSpecification point declared,  DoseReferencePointCoordinates={ref_beam_seq.BeamDoseSpecificationPoint}")
        else:
            ref.add_new(0x300a0018, 'DS', [0, 0, 0])
            msgs.append("No BeamDoseSpecificationPoint, set DoseReferencePointCoordinates=[0, 0, 0]")
    else:
        # If no reference_point location should be used, set the Rx type to site
        ref.add_new(0x300a0014, 'CS', 'SITE')
        msgs.append("Reference point has no location, set DoseReferenceStructureType=SITE")
        # Set the Varian internal tag designating the Target Volume in ARIA
        primary_dose_ref = beamset.Prescription.PrimaryPrescriptionDoseReference
        if hasattr(primary_dose_ref, 'OnStructure'):
            ref.add_new(0x32671000, 'UT', primary_dose_ref.OnStructure.Name)
            msgs.append(f"Primary reference is OnStructure Name={primary_dose_ref.OnStructure.Name}")
        # Address "Site"-based prescriptions
        elif hasattr(primary_dose_ref, 'Description'):
            ref.add_new(0x32671000, 'UT', primary_dose_ref.Description)
            msgs.append(f"Primary reference is Site-based Description={primary_dose_ref.Description}")
        else:
            msgs.append('ERROR: Unsupported prescription type for locationless reference point. Report to developer')

        expected.add(ref[0x32671000])
        # Add the private tag indicator
        ref.add_new(0x32670010, 'LO', 'UW Madison RayScripts 3267')
        msgs.append("Added private tag indicator, UW Madison RayScripts 3267")
        expected.add(ref[0x32670010])

    # Build Dose Reference UID
    series_uid = str(ds.SeriesInstanceUID).split('.', 4)
    prefix_uid = ""
    for i in range(4):
        prefix_uid += series_uid[i] + '.'
    dose_reference_uid = pydicom.uid.generate_uid(prefix=prefix_uid)
    ref.add_new(0x300a0013, 'UI', dose_reference_uid)
    msgs.append(f"Generated DoseReferenceUID={dose_reference_uid}")

    ref.add_new(0x300a0020, 'CS', 'TARGET')
    msgs.append("Set DoseReferenceType=TARGET")
    primary_prescription = beamset.Prescription.PrimaryPrescriptionDoseReference
    ref.add_new(0x300a0023, 'DS', primary_prescription.DoseValue / 100)
    msgs.append(f"Set DeliveryMaximumDose={primary_prescription.DoseValue / 100} in Gy")
    ref.add_new(0x300a002c, 'DS', primary_prescription.DoseValue / 100)
    msgs.append(f"Set OrganAtRiskMaximumDose={primary_prescription.DoseValue / 100} in Gy")

    if 'DoseReferenceSequence' not in ds:
        ds.add_new(0x300a0010, 'SQ', pydicom.Sequence([ref]))
        msgs.append("Added DoseReferenceSequence to RTPlan")
        expected.add(ds[0x300a0010])
    else:
        # Generate a DICOM UID for tracking the prescription to the same volume
        if 'DoseReferenceUID' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].DoseReferenceUID != \
                ref.DoseReferenceUID:
            msgs.append("Updating DoseReferenceUID")
            expected.add(ref[0x300a0013])

        if 'DoseReferenceStructureType' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].DoseReferenceStructureType != \
                ref.DoseReferenceStructureType:
            msgs.append("Updating DoseReferenceStructureType")
            expected.add(ref[0x300a0014])

        if 'DoseReferenceDescription' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].DoseReferenceDescription != ref.DoseReferenceDescription:
            msgs.append("Updating DoseReferenceDescription")
            expected.add(ref[0x300a0016])

        if ref_point_location:
            if 'DoseReferencePointCoordinates' not in ds.DoseReferenceSequence[0] or \
                    ds.DoseReferenceSequence[0].DoseReferencePointCoordinates != \
                    ref.DoseReferencePointCoordinates:
                msgs.append("Updating DoseReferencePointCoordinates")
                expected.add(ref[0x300a0018])

        if 'DoseReferenceType' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].DoseReferenceType != ref.DoseReferenceType:
            expected.add(ref[0x300a0020])

        if 'DeliveryMaximumDose' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].DeliveryMaximumDose != ref.DeliveryMaximumDose:
            expected.add(ref[0x300a0023])
            msgs.append("Updating DeliveryMaximumDose")

        if 'OrganAtRiskMaximumDose' not in ds.DoseReferenceSequence[0] or \
                ds.DoseReferenceSequence[0].OrganAtRiskMaximumDose != ref.OrganAtRiskMaximumDose:
            expected.add(ref[0x300a002c])
            msgs.append("Updating OrganAtRiskMaximumDose")

        ds.DoseReferenceSequence = pydicom.Sequence([ref])
        msgs.append("Updated existing DoseReferenceSequence in RTPlan")

    # Adjust beam doses to sum to primary dose point (if dose was not specified, evenly distribute it)
    total_dose = 0
    total_count = 0
    # Loop through the beams in the FractionGroupSequence
    for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
        beam_name = get_referenced_beam_name(ds, b)
        total_count += 1
        if hasattr(b, 'BeamDose'):
            total_dose += b.BeamDose
        if 'BeamDoseSpecificationPoint' not in b and ref_point_location:
            b.add_new(0x300a0082, 'DS', ref.DoseReferencePointCoordinates)
            expected.add(b[0x300a0082], beam=b)
            msgs.append(f'Beam {beam_name}: Added BeamDoseSpecificationPoint={ref.DoseReferencePointCoordinates}')
        elif 'BeamDoseSpecificationPoint' in b and not ref_point_location:
            # Following the varian private tag method of making beam points track to a
            # "<DoseReferenceUID>\00"
            # reference_beam_sequence_uid = str(dose_reference_uid) + r"\00"
            # Add in private tags indicating primary reference point UID
            # b.add_new(0x32491010,'UT',reference_beam_sequence_uid)
            # expected.add(b[0x32491010], beam=b)
            # Add the private tag indicator
            # b.add_new(0x32490010, 'LO', 'UW Madison RayScripts 3249')
            # expected.add(b[0x32490010])
            msgs.append(f'Beam {beam_name}: Deleting ref point location data.')
            if hasattr(b, 'BeamDoseSpecificationPoint'):
                del b[0x300a0082]  # Beam Dose Point Specification Coordinates
            if hasattr(b, 'BeamDosePointDepth'):
                del b[0x300a0088]  # Beam Dose Point Depth
            if hasattr(b, 'RadiologicalDepth'):
                del b[0x300a0089]  # Beam Dose Point Equivalent Depth
            if hasattr(b, 'BeamDoseType'):
                del b[0x300a0090]  # Beam Dose Type
    if total_dose == 0:
        for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
            beam_dose = ref.DeliveryMaximumDose / \
                        (total_count * ds.FractionGroupSequence[0].NumberOfFractionsPlanned)
            b.add_new(0x300a0084, 'DS', beam_dose)
            expected.add(b[0x300a0084], beam=b)
            msgs.append = f"Beam {beam_name}: Set BeamDose={beam_dose}"
    else:
        for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
            if hasattr(b, 'BeamDose'):
                max_beam_dose = b.BeamDose * ref.DeliveryMaximumDose / \
                                (total_dose * ds.FractionGroupSequence[0].NumberOfFractionsPlanned)
                if b.BeamDose != max_beam_dose:
                    b.BeamDose = max_beam_dose
                    expected.add(b[0x300a0084], beam=b)
                    msgs.append(f"Beam {beam_name}: Scaled BeamDose={max_beam_dose}")
    return '; '.join(msgs)


def apply_rpm_gating_filter(ds, expected) -> str:
    """
    Apply the RPM gating filter to the given dataset.
    Args:
        ds (FileDataset): The DICOM dataset to modify.
        expected (_Edits): The edits tracker to record tag edits.

    Returns:
        message (str): A summary message of the applied filter.
    """
    rpm_added = False
    for pss in ds.PatientSetupSequence:
        if not hasattr(pss, 'MotionSynchronizationSequence'):
            motn = pydicom.Dataset()
            motn.add_new(0x00189170, 'CS', 'GATING')
            motn.add_new(0x00189171, 'CS', 'EXTERNAL_MARKER')
            pss.add_new(0x300a0410, 'SQ', pydicom.Sequence([motn]))
            expected.add(pss[0x300a0410])
            rpm_added = True
    if rpm_added:
        return f'RPM gating filter applied to {len(ds.PatientSetupSequence)} PatientSetupSequence items.'
    return ''


def get_rt_plan_label(ds):
    """Extract the RT Plan Label from a pydicom Dataset.

    Args:
        ds (pydicom.Dataset): A DICOM dataset, typically read via pydicom.dcmread().

    Returns:
        str or None: The RT Plan Label (DICOM tag (300A,0002)), or None if not present.

    Raises:
        AttributeError: If `ds` is not a pydicom.Dataset.
    """
    # The RT Plan Label tag is (300A,0002)
    tag = (0x300A, 0x0002)
    element = ds.get(tag)
    return element.value if element is not None else None


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
        if d.find('name').text == destination:
            if 'type' in d.attrib:
                info['type'] = d.get('type')
            else:
                info['type'] = None
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

        tag = "0x{0:04x}{1:04x}".format(element.tag.group, element.tag.element)
        self.elements.append(element)
        self.tags.append(tag)
        if element.VR == 'SQ':
            string_value = 'SEQUENCE'

        else:
            string_value = str(element.value)

        if beam is not None and cp is not None:
            if 'BeamNumber' in beam:
                logging.debug('Element {} on beam {}, CP {} is now {}'.format(tag,
                                                                              beam.BeamNumber,
                                                                              cp.ControlPointIndex,
                                                                              string_value))
            elif 'ReferencedBeamNumber' in beam:
                logging.debug('Element {} on beam {}, CP {} is now {}'.format(tag,
                                                                              beam.ReferencedBeamNumber,
                                                                              cp.ControlPointIndex,
                                                                              string_value))
        elif beam is not None:
            if 'BeamNumber' in beam:
                logging.debug('Element {} on beam {} is now {}'.format(tag,
                                                                       beam.BeamNumber,
                                                                       string_value))
            elif 'ReferencedBeamNumber' in beam:
                logging.debug('Element {} on beam {} is now {}'.format(tag,
                                                                       beam.ReferencedBeamNumber,
                                                                       string_value))
        else:
            logging.debug('Element {} is now {}'.format(tag, string_value))

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
