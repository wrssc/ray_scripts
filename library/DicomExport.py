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
import sys
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
import shutil
import re
import math
import random
import string
from copy import deepcopy

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
         filters=None,
         machine=None,
         table=None,
         pa_threshold=None,
         gantry_period=None,
         couch_speed=None,
         round_jaws=False,
         prescription=False,
         ref_point_location=False,
         block_accessory=False,
         block_tray_id=False,
         parent_plan=None,
         prdr_dr=False,
         rpm_gating=False,
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

    # If multiple machine filter options exist, prompt the user to select one
    if machine is None and filters is not None and 'machine' in filters and beamset is not None:
        machine_list = machines(beamset)
        if len(machine_list) == 1:
            machine = machine_list[0]

        elif len(machine_list) > 1:
            dialog = UserInterface.ButtonList(inputs=machine_list, title='Select a machine to export as')
            machine = dialog.show()
            if machine is not None:
                logging.debug('User selected machine {} for RT plan export'.format(machine))

            else:
                raise IndexError('No machine was selected for RT plan export')

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
        logging.debug('RT Plan {} selected for export'.format(beamset.BeamSetIdentifier()))
        args['BeamSets'] = [beamset.BeamSetIdentifier()]
        # if prdr_dr and '_PRD_' in beamset.DicomPlanLabel:
        #     prdr_plan = True
        # else:
        #     prdr_plan = False

    # Append beamset to export RTSS (if beamset is not present, export RTSS from exam)
    if structures:
        if beamset is not None:
            logging.debug('Plan structure set selected for export')
            args['RtStructureSetsReferencedFromBeamSets'] = [beamset.BeamSetIdentifier()]

        elif exam is not None:
            logging.debug('Exam structure set selected for export')
            args['RtStructureSetsForExaminations'] = [exam.Name]

    # Append PhysicalBeamDosesForBeamSets and/or PhysicalBeamSetDoseForBeamSets to export RT Dose
    if plan_dose and beamset is not None:
        logging.debug('Plan {} dose selected for export'.format(beamset.BeamSetIdentifier()))
        args['PhysicalBeamSetDoseForBeamSets'] = [beamset.BeamSetIdentifier()]

    if beam_dose and beamset is not None:
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
                for b in ds.BeamSequence:

                    # If applying a machine filter
                    if machine is not None and 'TreatmentMachineName' in b and b.TreatmentMachineName != machine:
                        b.TreatmentMachineName = machine
                        expected.add(b[0x300a00b2], beam=b)

                    if 'TreatmentDeliveryType' in b and b.TreatmentDeliveryType == 'SETUP':
                        # Change Dose rate for set-up fields to 100 MU/min
                        for c in b.ControlPointSequence:
                            c.DoseRateSet = 100
                            expected.add(c[0x300a0115], beam=b, cp=c)
                            # Change the nominal beam energy
                            if 'NominalBeamEnergy' in c and c.NominalBeamEnergy != 6:
                                c.NominalBeamEnergy = 6
                                expected.add(c[0x300a0114], beam=b, cp=c)

                    # If plan is prdr then set the nominal dose rate to 100 MU/min
                    if prdr_dr and '_PRD_' in beamset.DicomPlanLabel and \
                            'RadiationType' in b and b.RadiationType == 'PHOTON' and \
                            'ControlPointSequence' in b:
                        for c in b.ControlPointSequence:
                            if 'DoseRateSet' in c and c.DoseRateSet != 100:
                                c.DoseRateSet = 100
                                expected.add(c[0x300a0115], beam=b, cp=c)

                    # Change Dose rate for electron fields to 1000 MU/min
                    if 'RadiationType' in b and b.RadiationType == 'ELECTRON' and 'ControlPointSequence' in b:
                        for c in b.ControlPointSequence:
                            c.DoseRateSet = 1000
                            expected.add(c[0x300a0115], beam=b, cp=c)

                        # The following lines add a new accessory for the electron block which is unnecessary in ARIA
                        # If converting electron block into accessory (note, accessory ID tags are currently hard coded
                        # if block_accessory and 'RadiationType' in b and b.RadiationType == 'ELECTRON' and \
                        #         'BlockSequence' in b and 'BlockName' in b.BlockSequence[0] and \
                        #         'GeneralAccessorySequence' not in b:

                        #     acc = pydicom.Dataset()
                        #     acc.add_new(0x300a00f9, 'LO', b.BlockSequence[0].BlockName)
                        #     if 'ApplicatorSequence' in b and 'ApplicatorID' in b.ApplicatorSequence and \
                        #             b.ApplicatorSequence.ApplicatorID == 'A6':
                        #         # acc.add_new(0x300a0421, 'SH', 'CustomFFDA6')
                        #         acc.add_new(0x300a0421, 'SH', 'CustomFFDA')
                        #
                        #     else:
                        #         acc.add_new(0x300a0421, 'SH', 'CustomFFDA')

                        #     acc.add_new(0x300a0423, 'CS', 'TRAY')
                        #     acc.add_new(0x300a0424, 'IS', b.BlockSequence[0].BlockName)
                        #     # acc.add_new(0x300a0424, 'IS', 1)
                        #     b.add_new(0x300a0420, 'SQ', pydicom.Sequence([acc]))
                        #     expected.add(b[0x300a0420])

                        # If overriding the block tray ID
                        if block_tray_id and 'RadiationType' in b and b.RadiationType == 'ELECTRON' and \
                                'BlockSequence' in b:

                            acc_code = b.BlockSequence[0].BlockName
                            if 'AccessoryCode' not in b.BlockSequence[0] or \
                                    b.BlockSequence[0].AccessoryCode != acc_code:
                                b.BlockSequence[0].AccessoryCode = acc_code
                                expected.add(b.BlockSequence[0][0x300a00f9], beam=b)

                            if 'ApplicatorSequence' in b and 'ApplicatorID' in b.ApplicatorSequence and \
                                    b.ApplicatorSequence.ApplicatorID == 'A6':
                                tray = 'CustomFFDA'

                            else:
                                tray = 'CustomFFDA'

                            if 'BlockTrayID' not in b.BlockSequence[0] or b.BlockSequence[0].BlockTrayID != tray:
                                b.BlockSequence[0].BlockTrayID = tray
                                expected.add(b.BlockSequence[0][0x300a00f5], beam=b)

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
                                            (p.LeafJawPositions[0] != math.floor(10 * p.LeafJawPositions[0]) / 10 or
                                             p.LeafJawPositions[1] != math.ceil(10 * p.LeafJawPositions[1]) / 10):
                                        p.LeafJawPositions[0] = math.floor(10 * p.LeafJawPositions[0]) / 10
                                        p.LeafJawPositions[1] = math.ceil(10 * p.LeafJawPositions[1]) / 10
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
                                    c.GantryAngle = 180.010
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

                    # If adding gantry period to TomoTherapy QA Plans
                    if couch_speed is not None:
                        # format and set tag to change
                        t1 = pydicom.tag.Tag('300d1080')
                        # find a tag match
                        for n in couch_speed.keys():
                            if n == b.BeamName:
                                speed = couch_speed[n]
                                break
                        if speed:
                            str_couch_speed = '{:.6f}'.format(round(speed,6))
                        else:
                            logging.warning('Unable to add couch speed for beam {}'.format(b.BeamName))

                        # Add some white-space to the end of gantry period
                        str_couch_speed = str_couch_speed + ' '

                        # add attribute to beam sequence
                        b.add_new(t1, 'DS', str_couch_speed)
                        expected.add(b[t1], beam=b)

                    # If adding gantry period to TomoTherapy QA Plans
                    if gantry_period is not None:
                        # format and set tag to change
                        t1 = pydicom.tag.Tag('300d1040')

                        # Add some white-space to the end of gantry period
                        str_gantry_period = gantry_period + ' '

                        # add attribute to beam sequence
                        b.add_new(t1, 'DS', gantry_period)
                        expected.add(b[t1], beam=b)

                # If adding reference points
                if prescription and beamset.Prescription.PrimaryPrescriptionDoseReference is not None and \
                        'FractionGroupSequence' in ds and len(ds.FractionGroupSequence[0].ReferencedBeamSequence) > 0:

                    # Create reference point for primary dose prescription
                    ref = pydicom.Dataset()
                    ref.add_new(0x300a0012, 'IS', 1)
                    # This is the "Dose Reference Description in ARIA"
                    # if hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference, 'OnStructure') and \
                    #         hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference.OnStructure, 'Name'):
                    #    ref.add_new(0x300a0016, 'LO', beamset.Prescription.PrimaryPrescriptionDoseReference.OnStructure.Name)
                    # elif hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference, 'OnDoseSpecificationPoint') and \
                    #         hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference.OnDoseSpecificationPoint, 'Name'):
                    #    ref.add_new(0x300a0016, 'LO',
                    #                beamset.Prescription.PrimaryPrescriptionDoseReference.OnDoseSpecificationPoint.Name)
                    # else:
                    #     ref.add_new(0x300a0014, 'LO', 'Target')
                    dose_ref_desc = str(beamset.DicomPlanLabel) + '.0'
                    ref.add_new(0x300a0016, 'LO', dose_ref_desc)

                    # Add coordinates to the primary reference point
                    if ref_point_location:
                        ref.add_new(0x300a0014, 'CS', 'COORDINATES')
                        if 'BeamDoseSpecificationPoint' in ds.FractionGroupSequence[0].ReferencedBeamSequence[0]:
                            ref.add_new(0x300a0018, 'DS',
                                        ds.FractionGroupSequence[0].ReferencedBeamSequence[0].BeamDoseSpecificationPoint)
                        else:
                            ref.add_new(0x300a0018, 'DS', [0, 0, 0])
                    else:
                        # If no reference_point location should be used, set the Rx type to site
                        ref.add_new(0x300a0014, 'CS', 'SITE')
                        # Set the Varian internal tag designating the Target Volume in ARIA
                        if hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference, 'OnStructure'):
                            ref.add_new(0x32671000, 'UT',
                                        beamset.Prescription.PrimaryPrescriptionDoseReference.OnStructure.Name)
                        # Address "Site"-based prescriptions
                        elif hasattr(beamset.Prescription.PrimaryPrescriptionDoseReference, 'Description'):
                            ref.add_new(0x32671000, 'UT',
                                        beamset.Prescription.PrimaryPrescriptionDoseReference.Description)
                        else:
                            sys.exit(
                                'Unsupported prescription type for locationless reference point. Report to developer')

                        expected.add(ref[0x32671000])
                        # Add the private tag indicator
                        ref.add_new(0x32670010, 'LO', 'UW Madison RayScripts 3267')
                        expected.add(ref[0x32670010])

                    # Build Dose Reference UID
                    series_uid = str(ds.SeriesInstanceUID).split('.', 4)
                    prefix_uid = ""
                    for i in range(4):
                        prefix_uid += series_uid[i] + '.'
                    dose_reference_uid = pydicom.uid.generate_uid(prefix=prefix_uid)
                    ref.add_new(0x300a0013, 'UI', dose_reference_uid)

                    ref.add_new(0x300a0020, 'CS', 'TARGET')
                    ref.add_new(0x300a0023, 'DS', beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue / 100)
                    ref.add_new(0x300a002c, 'DS', beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue / 100)

                    if 'DoseReferenceSequence' not in ds:
                        ds.add_new(0x300a0010, 'SQ', pydicom.Sequence([ref]))
                        expected.add(ds[0x300a0010])

                    else:
                        # Generate a DICOM UID for tracking the prescription to the same volume
                        if 'DoseReferenceUID' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceUID != \
                                ref.DoseReferenceUID:
                            expected.add(ref[0x300a0013])

                        if 'DoseReferenceStructureType' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceStructureType != \
                                ref.DoseReferenceStructureType:
                            expected.add(ref[0x300a0014])

                        if 'DoseReferenceDescription' not in ds.DoseReferenceSequence[0] or \
                                ds.DoseReferenceSequence[0].DoseReferenceDescription != ref.DoseReferenceDescription:
                            expected.add(ref[0x300a0016])

                        if ref_point_location:
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

                    # Adjust beam doses to sum to primary dose point (if dose was not specified, evenly distribute it)
                    total_dose = 0
                    total_count = 0
                    for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
                        total_count += 1
                        if hasattr(b, 'BeamDose'):
                            total_dose += b.BeamDose

                        if 'BeamDoseSpecificationPoint' not in b and ref_point_location:
                            logging.debug('Adding reference point location to b {}'.format(b.ReferencedBeamNumber))
                            b.add_new(0x300a0082, 'DS', ref.DoseReferencePointCoordinates)
                            expected.add(b[0x300a0082], beam=b)
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
                            logging.debug('Deleting ref point location from b {}'.format(b.ReferencedBeamNumber))
                            if hasattr(b,'BeamDoseSpecificationPoint'):
                                del b[0x300a0082] # Beam Dose Point Specification Coordinates
                            if hasattr(b,'BeamDosePointDepth'):
                                del b[0x300a0088] # Beam Dose Point Depth
                            if hasattr(b,'RadiologicalDepth'):
                                del b[0x300a0089] # Beam Dose Point Equivalent Depth
                            if hasattr(b,'BeamDoseType'):
                                del b[0x300a0090] # Beam Dose Type
                    if total_dose == 0:
                        for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
                            b.add_new(0x300a0084, 'DS', ref.DeliveryMaximumDose /
                                      (total_count * ds.FractionGroupSequence[0].NumberOfFractionsPlanned))
                            expected.add(b[0x300a0084], beam=b)

                    else:
                        for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
                            if hasattr(b, 'BeamDose') and b.BeamDose != b.BeamDose * ref.DeliveryMaximumDose / \
                                    (total_dose * ds.FractionGroupSequence[0].NumberOfFractionsPlanned):
                                b.BeamDose = b.BeamDose * ref.DeliveryMaximumDose / \
                                             (total_dose * ds.FractionGroupSequence[0].NumberOfFractionsPlanned)
                                expected.add(b[0x300a0084], beam=b)

                if rpm_gating:
                   for p in ds.PatientSetupSequence:
                       if 'MotionSynchronizationSequence' not in p:
                           motn = pydicom.Dataset()
                           motn.add_new(0x00189170,'CS','GATING')
                           motn.add_new(0x00189171,'CS','EXTERNAL_MARKER')
                           p.add_new(0x300a0410, 'SQ', pydicom.Sequence([motn]))
                           expected.add(p[0x300a0410])
                           logging.debug('Added gating params')

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
                if c.find('from/machine').text == beamset.Beams[b].MachineReference.MachineName:
                    # RayStation version 10A moves the MachineReference.Energy field to Null
                    # This is now a beamset property
                    # 8: Beam->MachineReference->Energy : float
                    # 10A: Beam->Beam->BeamQualityId: string
                    logging.debug('filter type {}'.format(c.attrib['type']))
                    logging.debug('matching filter energy:{}, RS {}'.format(c.find('from/energy').text.lower(),
                                                                            beamset.Beams[b].BeamQualityId).lower())
                    logging.debug('matching filter modality:{}, RS {}'.format(c.find('from/energy').attrib['type'].lower(),
                                                                        beamset.Modality.lower()))
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
