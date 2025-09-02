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
    1.2.0 Adding parse on RayGateway error handling, implemented new function-based handling of filters

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
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'

import os
import xml.etree.ElementTree as ET
import time
import tempfile
import logging
import traceback
import pydicom
import shutil
import math
import random
import string
import re
import UserInterface
import pprint
import numpy as np
from pynetdicom import AE
from pynetdicom.sop_class import RTPlanStorage, RTStructureSetStorage, CTImageStorage, RTDoseStorage, Verification
from pydicom.tag import Tag
from pydicom.uid import ImplicitVRLittleEndian
from pydicom.dataset import Dataset
from pydicom.errors import InvalidDicomError
from collections import OrderedDict
from typing import List, Pattern, Any, Optional, Tuple, Sequence, Dict
from decimal import Decimal, ROUND_HALF_UP, getcontext, ROUND_HALF_EVEN
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Callable, Any, Dict

# @dataclass(frozen=True)
# class FilterSpec:
#     name:      str
#     fn:        Callable[..., str]   # returns a message; may be no-op
#     predicate: Callable[[Dict[str, Any]], bool]

# Parse destination and filters XML files
dest_xml = ET.parse(os.path.join(os.path.dirname(__file__), 'DicomDestinations.xml'))
filter_xml = ET.parse(os.path.join(os.path.dirname(__file__), 'DicomFilters.xml'))

# local_AET defines the AE title that will be used by the script when communicating with the destination
local_AET = 'RAYSTATION_SSCP'
local_port = 105

# Define personal_tags (for anonymization)
personal_tags = ['PatientName', 'PatientID', 'OtherPatientIDs', 'OtherPatientIDsSequence', 'PatientBirthDate']

# ---------- regexes ----------
STATUS = re.compile(r"Error status code.*?\((\d{3})\)\s*([^\n]+)", re.I)
SERVER = re.compile(r"Server message:\s*(.+?)(?:$|\n)", re.I | re.S)
MESSAGE = re.compile(r"Message:\s*(.+?)(?:$|\n)", re.I | re.S)
EXCEPTION = re.compile(
    r"\b([A-Z][A-Za-z0-9_.]*Exception):\s*(.+?)(?=$|\n| ---)"
)

# ----------- identical run-on chunks like “… ) ---> … ) ---> …” --------------
BACKTRACK = re.compile(r"(?:\s+--->\s+)+")


class InvalidOperationException(Exception):
    pass


# ----- RT Plan Export Filter Class --------------------------------
# @dataclass(frozen=True)
# class FilterSpec:
#     name: str
#     fn: Callable[..., str]  # returns a message; may be no-op
#     predicate: Callable[[Dict[str, Any]], bool]

INDEX_REFERENCED_ROI_NUMBER = Tag(0x30060084)


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
        traceback.print_exc()
        logging.error("An error occurred: " +
                      "Referenced BeamNumber is missing on referenced beam entry" +
                      f"\nTraceback:\n {traceback.format_exc()}"
                      )
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


def get_referenced_beam_attribute(rtplan: Dataset, ref_beam: Dataset, attr: str) -> Any:
    """Return the value of a specified attribute from a ReferencedBeamSequence item.

    Args:
        rtplan (pydicom.dataset.Dataset): The RT Plan Dataset containing BeamSequence.
        ref_beam (pydicom.dataset.Dataset): One entry from
            ds.FractionGroupSequence[0].ReferencedBeamSequence.
        attr (str): The attribute name to retrieve from the referenced beam.

    Returns:
        Any: The value of the specified attribute, or None if not found.

    Raises:
        AttributeError: If ref_beam has no ReferencedBeamNumber.
    """
    if not hasattr(ref_beam, "ReferencedBeamNumber"):
        traceback.print_exc()
        logging.error(f"An error occurred while attempting to retrieve attr {attr}: " +
                      "Referenced BeamNumber is missing on referenced beam entry" +
                      f"\nTraceback:\n {traceback.format_exc()}"
                      )
        raise AttributeError(
            f"ReferencedBeamNumber missing on referenced beam entry for attribute {attr}"
        )

    beam_num = int(ref_beam.ReferencedBeamNumber)
    full_beams = getattr(rtplan, "BeamSequence", [])

    for beam in full_beams:
        if hasattr(beam, "BeamNumber") and beam.BeamNumber == beam_num:
            return getattr(beam, attr, None)

    return None


def export_beamset_rtplan(case, exam, beamset):
    """Export the specified beamset to a temporary directory and return the RT Plan as a pydicom Dataset.

    This function uses RayStation’s ScriptableDicomExport API to export only the RT Plan
    for the given beamset. It then scans the export folder for the DICOM file whose
    SOP Class UID matches RTPlanStorage, reads it with pydicom, and returns it.

    Args:
        case (object): RayStation Case object (e.g., from get_current('Case')).
        exam (object): RayStation Examination object (e.g., from get_current('Examination')).
        beamset (object): RayStation BeamSet object (e.g., from get_current('BeamSet')).

    Returns:
        pydicom.dataset.FileDataset: The RT Plan dataset read from the exported DICOM file.

    Raises:
        FileNotFoundError: If no RT Plan file is found in the export directory.
        Exception: Propagates any exceptions raised by the export call.
    """
    # Create a temporary directory for export
    export_dir = tempfile.mkdtemp(prefix='rtplan_export_')
    try:
        # Perform the export: only RT Plan (no CT, no structures, no dose)
        case.ScriptableDicomExport(
            ExportFolderPath=export_dir,
            # Examinations=[],
            BeamSets=[beamset.BeamSetIdentifier()],
            IgnorePreConditionWarnings=True,
        )

        # Scan for the RT Plan DICOM file
        for fname in os.listdir(export_dir):
            fpath = os.path.join(export_dir, fname)
            try:
                ds = pydicom.dcmread(fpath)
            except pydicom.errors.InvalidDicomError:
                continue
            # Identify the RT Plan by its SOP Class UID
            if ds.file_meta.MediaStorageSOPClassUID == RTPlanStorage:
                return ds

        # If we reach here, no RT Plan was found
        raise FileNotFoundError(f'No RT Plan file found in {export_dir}')

    finally:
        # Clean up the temporary directory
        shutil.rmtree(export_dir, ignore_errors=True)


def load_rtplan(filepath: str) -> pydicom.dataset.FileDataset:
    """Load an RT Plan DICOM file from disk and return the pydicom Dataset.

    This function reads a DICOM file at the given path, verifies that it
    contains an RT Plan (SOP Class UID == RTPlanStorage), and returns the
    corresponding pydicom FileDataset.

    Args:
        filepath (str): Full path to the DICOM file to load.

    Returns:
        pydicom.dataset.FileDataset: The RT Plan dataset.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        InvalidDicomError: If the file cannot be parsed as a DICOM file.
        ValueError: If the file is not an RT Plan (wrong SOP Class UID).
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"No such file: '{filepath}'")

    try:
        ds = pydicom.dcmread(filepath)
    except InvalidDicomError as e:
        raise InvalidDicomError(f"Failed to read DICOM file '{filepath}': {e}")

    sop_class = ds.file_meta.get('MediaStorageSOPClassUID', None)
    if sop_class != RTPlanStorage:
        raise ValueError(
            f"File '{filepath}' is not an RT Plan (SOP Class UID {sop_class})"
        )

    return ds


# -------- tighter canonicalisation ------------------------------------------
def _canon(s: str) -> str:
    """
    Return a *finger-print* good enough for “same meaning” tests:

        • lower-case
        • '_' treated as space
        • strip all remaining non-alnum
        • collapse duplicate tokens while *preserving order*
    """
    s = s.casefold().replace("_", " ")
    # keep only letters+digits+space
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    tokens: list[str] = []
    seen: set[str] = set()
    for tok in s.split():
        if tok not in seen:
            seen.add(tok)
            tokens.append(tok)
    return " ".join(tokens)


def _squash_backtrack(text: str) -> str:
    """
    Remove *verbatim* duplicates created by AggregateException back-tracking.
    Example input (line-breaks added):

        Foo bar ---> Foo bar ---> Foo bar

    becomes:

        Foo bar
    """
    parts = BACKTRACK.split(text)
    if len(parts) <= 1:
        return text
    # first part is always kept; keep only parts that change canon()
    out: list[str] = [parts[0]]
    last_fingerprint = _canon(parts[0])
    for seg in parts[1:]:
        fp = _canon(seg)
        if fp != last_fingerprint:
            out.append(seg)
            last_fingerprint = fp
    return " ---> ".join(out)


# ---------- prefer-shortest & parenthetical-echo unchanged -------------------
def _prefer_shortest(items: list[str]) -> list[str]:
    chosen: list[str] = []
    for text in items:
        fp = _canon(text)
        if any(fp == _canon(c) and len(text) > len(c) for c in chosen):
            continue
        chosen = [c for c in chosen if not (fp == _canon(c) and len(c) > len(text))]
        chosen.append(text)
    return chosen


def _drop_parenthetical_echo(s: str) -> str:
    m = re.search(r"\s*\((.*?)\)\s*$", s)
    if m and _canon(m.group(1)) == _canon(s[: m.start()].strip()):
        return s[: m.start()].rstrip()
    return s


# ---------------- revised _uniq: one fast pass -------------------------------
def _uniq(rx: Pattern[str], text: str) -> list[str]:
    out: OrderedDict[str, str] = OrderedDict()
    for m in rx.finditer(text):
        raw = m.group(1).strip()
        fp = _canon(raw)
        out.setdefault(fp, raw)  # first-seen wording wins
    return list(out.values())


# ---------------------------- main one-liner maker ---------------------------
def summarize(log: str) -> str:
    """Condense a raw RayGateway exception into one sentence."""
    log = _squash_backtrack(log)

    parts: list[str] = []

    if m := STATUS.search(log):
        parts.append(f"HTTP {m[1]} {m[2].strip()}")

    if s := SERVER.search(log):
        parts.append(s[1].strip())

    if msgs := _uniq(MESSAGE, log):
        msgs = _prefer_shortest(msgs)  # enable idea 2 if desired
        msgs = [_drop_parenthetical_echo(x) for x in msgs]  # idea 3
        parts.append(" | ".join(msgs))
    # Fallback: still nothing? grab the first meaningful line
    if not parts:
        first = next((ln.strip() for ln in log.splitlines() if ln.strip()), "")
        msgs = _drop_parenthetical_echo(first)
        parts.append(msgs)

    return " – ".join(parts)


def handle_raygateway_error(error: Exception, beamset_name: str) -> dict:
    """Handle errors from RayGateway export, parsing the error message and logging it.
    """
    if isinstance(error, Exception):
        if hasattr(error, 'message'):
            error = error.message
        else:
            error = str(error)

    # TODO: eliminate debug
    logging.debug(f'Handling RayGateway error: {error}')
    parsed_error = summarize(error)
    # This is the error thrown when a plan is already in the iDMS
    existing_plan_exception = f"_{beamset_name} already exist"
    element_too_long = 'Element 3006,0050 is too long to be written in Explicit'
    if existing_plan_exception in error:
        return {'continue': True, 'message': f'Parent Plan is already in IDMS {beamset_name}'
                                             f': {parsed_error}'}
    elif element_too_long in error:
        return {'continue': False, 'message': f"An ROI in the {beamset_name} exceeds the maximum tolerable "
                                              f"length for DICOM export. Simplify ROIs with _npts>2500"}
    else:
        logging.error(f'DicomExport failed {parsed_error}')
        return {'continue': False, 'message': f'DICOM export failed {parsed_error}'}


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
         aria_compatibility_mode=False,
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
    # Load energy filters for the selected machine
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
                    raygateway_response = handle_raygateway_error(error, beamset.DicomPlanLabel)
                    if raygateway_response['continue']:
                        logging.debug(raygateway_response['message'])
                        pass
                    else:
                        logging.error(raygateway_response['message'])
                        UserInterface.MessageBox(raygateway_response['message'], 'Export Fail')
                        status = False
                        raise
                logging.info('DicomExport completed successfully in {:.3f} seconds'.format(time.time() - tic))
            else:
                try:
                    beamset.SendTransferredPlanToRayGateway(RayGatewayTitle='RAYGATEWAY',
                                                            PreviousBeamSet=parent_plan,
                                                            OriginalBeamSet=parent_plan,
                                                            IgnorePreConditionWarnings=ignore_warnings)
                except Exception as e:
                    raygateway_response = handle_raygateway_error(e, beamset.DicomPlanLabel)
                    if raygateway_response['continue']:
                        logging.debug(raygateway_response['message'])
                        pass
                    else:
                        logging.error(raygateway_response['message'])
                        UserInterface.MessageBox(raygateway_response['message'], 'Export Fail')
                        status = False
                        raise
            if isinstance(bar, UserInterface.ProgressBar):
                bar.close()

            UserInterface.MessageBox('DICOM export was successful', 'Export Success')
        except Exception as error:
            raygateway_response = handle_raygateway_error(error, beamset.DicomPlanLabel)
            if raygateway_response['continue']:
                logging.debug(raygateway_response['message'])
                pass
            else:
                logging.error(raygateway_response['message'])
                if isinstance(bar, UserInterface.ProgressBar):
                    bar.close()
                UserInterface.MessageBox(raygateway_response['message'], 'Export Fail')
                status = False
            if isinstance(bar, UserInterface.ProgressBar):
                bar.close()

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
            ds = pydicom.dcmread(os.path.join(original, o))

            # If this is a DICOM RT plan
            expected = _Edits()
            # ARIA -specific export
            ds_aria = None
            expected_aria = None
            if ds.file_meta.MediaStorageSOPClassUID == '1.2.840.10008.5.1.4.1.1.481.5':
                rt_plan_msg = f'RTPLAN: {(get_rt_plan_label(ds))}'
                logging.debug(f'Processing {rt_plan_msg}')

                # 1) Setup fields
                # Apply setup Dose rate and nominal beam energy for setup fields
                if setup_beam_filter:
                    message = adjust_setup_field(ds=ds, expected=expected)
                    if message:
                        logging.debug(f"\t{rt_plan_msg}: {message}")

                # 2) Machine filter
                if machine is not None:
                    message = apply_machine_filter(ds=ds, machine=machine, expected=expected)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 3) PRDR filter
                if prdr_dr:
                    message = apply_prdr_filter(ds=ds, beamset=beamset, expected=expected)
                    if message:
                        logging.debug(f"\t{rt_plan_msg}: {message}")

                # 4) Electron dose rate
                if electron_dose_rate_filter:
                    message = adjust_electron_dose_rate(ds=ds, expected=expected)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 5) Block accessory filter
                if block_accessory:
                    message = apply_block_accessory_filter(ds=ds, expected=expected)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 6) Block tray ID filter
                if block_tray_id:
                    message = apply_block_tray_id_filter(ds=ds, expected=expected)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 7) Table position filter
                if table is not None:
                    message = apply_table_position_filter(ds=ds, expected=expected, table_position=table)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 8) Round jaws filter
                if round_jaws:
                    message = apply_round_jaws_filter(ds=ds, expected=expected)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 9) PA beam angle filter
                if pa_threshold:
                    message = apply_pa_beam_angle_filter(ds=ds, expected=expected, pa_threshold=pa_threshold)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 10) Energy filter
                if energy_list:
                    message = apply_energy_filter(ds=ds, expected=expected, energy_list=energy_list)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 11) Couch speed filter
                if couch_speed:
                    message = apply_couch_speed_filter(ds=ds, expected=expected, couch_speed=couch_speed)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 12) Gantry period filter
                if gantry_period:
                    message = apply_gantry_period_filter(ds=ds, expected=expected, gantry_period=gantry_period)
                    logging.debug(f"\t{rt_plan_msg}: {message}")

                # 13) RPM gating filter
                if rpm_gating:
                    message = apply_rpm_gating_filter(ds=ds, expected=expected)
                    if message:
                        logging.debug(f"\t{rt_plan_msg}: {message}")

                # 14) Prescription filter for ARIA - Must be last filter applied!
                if aria_compatibility_mode:
                    # Create a copy for ARIA specific export
                    ds_aria = deepcopy(ds)
                    expected_aria = deepcopy(expected)
                    message = apply_prescription_filter_aria(
                        ds=ds_aria, beamset=beamset, expected=expected_aria)
                    if 'ERROR' in message:
                        raise InvalidOperationException(
                            'Prescription filter failed for {}: {}'.format(get_rt_plan_label(ds_aria), message))
                    elif message:
                        logging.debug(f"\t{rt_plan_msg}: {message}")

            # If no edits are needed, copy the file to the modified directory
            if expected.length() == 0:
                shutil.copy(os.path.join(original, o), modified)
            else:
                edited[o] = expected
                logging.debug(f'File {o} re-saved with {expected.length()} edits')
                ds.save_as(os.path.join(modified, o))
            # Check for the ARIA copy and save it if it exists
            # Check for the ARIA copy and save it if it exists
            if ds_aria is not None:
                if expected_aria and expected_aria.length() > 0:
                    aria_name = o.replace('.dcm', '_aria.dcm')
                    logging.debug(f'File {o} ARIA copy re-saved with {expected_aria.length()} edits')
                    ds_aria.save_as(os.path.join(modified, aria_name))
                    # register expected edits so validation can run on the ARIA file
                    edited[aria_name] = expected_aria

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

        selected_files = select_modified_files_for_destination(modified, info, aria_compatibility_mode)
        i = 0
        total = len(selected_files)
        for fpath in selected_files:
            m = os.path.basename(fpath)
            if isinstance(bar, UserInterface.ProgressBar):
                bar.update(text=f'Validating and Exporting Files to {d} ({i + 1} of {total})')
            i += 1

            # send a message to the ae
            try:
                message = assoc.send_c_echo()
                logging.debug('Echo request returned {}'.format(message))
            except AttributeError:
                logging.debug('Selected destination does not have echo properties')
            try:
                logging.debug('Reading modified file {}'.format(fpath))
                ds = pydicom.dcmread(fpath)

                # Validate changes against original file, recursively searching through sequences
                if m in edited and not bypass_export_check:
                    logging.debug('Validating edits against {}'.format(
                        os.path.join(original, m if not m.endswith('_aria.dcm') else m.replace('_aria', ''))
                    ))
                    dso_name = m[:-9] + '.dcm' if m.endswith('_aria.dcm') else m
                    dso = pydicom.dcmread(os.path.join(original, dso_name))
                    try:
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


def is_aria_destination(info: dict) -> bool:
    # Don’t conflate with RayGateway (handled elsewhere)
    blob = f"{info.get('type', '')}|{info.get('aet', '')}|{info.get('name', '')}|{info.get('host', '')}".casefold()
    return ('aria' in blob or 'varian' in blob) and 'raygateway' not in blob


def select_modified_files_for_destination(modified_dir: str,
                                          info: dict,
                                          aria_compatibility_mode: bool) -> List[str]:
    """
    Selects modified files for a specified destination directory, filtering DICOM files based on their
    SOP Class UID and compatibility mode.

    This function processes a directory of modified files, determines files of interest based on their
    file names and DICOM metadata, and returns a list of selected file paths. The selection can vary
    depending on whether ARIA compatibility mode is enabled and if the destination is associated with
    ARIA.

    ARIA compatibility mode is intended to ensure that if both a base RT Plan and an ARIA-specific
    RT Plan exist for the same SOP Instance UID, only the ARIA-specific version is selected for export.
    For ARIA Destinations, RT Dose files are excluded when ARIA compatibility mode is active.

    Args:
        modified_dir (str): The directory containing modified files to process.
        info (dict): Metadata about the destination or relevant context.
        aria_compatibility_mode (bool): A flag indicating whether to enable ARIA-specific compatibility.

    Returns:
        List[str]: A list of selected file paths based on the input directory and filtering criteria.
    """
    plans_by_uid: dict[str, dict[str, str]] = {}
    non_plans: List[str] = []
    # Indication that we want the ARIA-specific version of the plan if it exists, exclude the dose
    # because the destination is ARIA and the filter is active
    want_aria = aria_compatibility_mode and is_aria_destination(info)

    for m in os.listdir(modified_dir):
        fpath = os.path.join(modified_dir, m)
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=True, force=True)
        except InvalidDicomError:
            continue

        if ds.SOPClassUID == RTPlanStorage:
            uid = str(ds.SOPInstanceUID)
            bucket = plans_by_uid.setdefault(uid, {})
            if m.endswith('_aria.dcm'):
                bucket['aria'] = fpath
            else:
                bucket['base'] = fpath
        else:
            if ds.SOPClassUID == RTDoseStorage and want_aria:
                # If we want ARIA plans, exclude non-plans
                continue
            non_plans.append(fpath)

    selected = list(non_plans)

    for uid, paths in plans_by_uid.items():
        if want_aria and 'aria' in paths:
            selected.append(paths['aria'])
        elif 'base' in paths:
            selected.append(paths['base'])
        else:
            # Fallback (shouldn’t happen): if only aria exists and we want aria, take it
            if want_aria and 'aria' in paths:
                selected.append(paths['aria'])

    return selected


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


# def apply_primary_dose_reference_sequence(
#         ds: pydicom.Dataset,
#         beamset: Any,
#         expected: Any,
#         insert_reference_coords: bool
# ) -> str:
#     """
#     Build or update the RTPlan DoseReferenceSequence for the primary aria_compatibility_mode.
#
#     This wraps the internal helper `_build_primary_dose_reference`, which:
#       - Creates a new item in DoseReferenceSequence (300A,0010).
#       - Sets DoseReferenceNumber (300A,0012), Description (300A,0016),
#         StructureType (300A,0014 = COORDINATES or SITE), and
#         DoseReferencePointCoordinates (300A,0018) if coordinate mode.
#       - Generates a DoseReferenceUID (300A,0013) under the RTPlan’s SeriesInstanceUID prefix.
#       - Sets DoseReferenceType (300A,0020 = TARGET), DeliveryMaximumDose (300A,0023),
#         and OrganAtRiskMaximumDose (300A,002C).
#       - For SITE mode, writes Varian private tags (3267,1000… / 3267,0010…).
#
#     Args:
#         ds: Full pydicom Dataset for the RTPlan.
#         beamset: RayStation BeamSet (or list thereof) containing DicomPlanLabel
#                  and Prescription.PrimaryPrescriptionDoseReference.
#         expected: Edits tracker to record modified DICOM elements.
#         insert_reference_coords: If True, use COORDINATES mode; if False, SITE mode.
#
#     Returns:
#         A semicolon-delimited summary of all operations performed.
#     """
#     # Delegate to the helper and join its log messages
#     msgs: List[str] = _build_dose_reference_sequence(
#         ds,
#         beamset,
#         expected,
#         insert_reference_coords
#     )
#     return "; ".join(msgs)
#

# def _build_dose_reference_sequence(
#         ds: pydicom.Dataset,
#         beamset: Any,
#         expected: Any,
#         ref_point_location: bool
# ) -> List[str]:
#     """Create or update the DoseReferenceSequence with primary aria_compatibility_mode details.
#
#     DICOM tags used:
#       - (300A,0010) DoseReferenceSequence (SQ)
#       - (300A,0012) DoseReferenceNumber (IS) - 1 for primary and 2, 3, etc. for subsequent -> Check only
#       - (300A,0014) DoseReferenceStructureType (CS): COORDINATES for primary and SITE for secondary -> Check only
#       - (300A,0016) DoseReferenceDescription (LO) -> TODO: This seems to be wonky in RS and appears off in ARIA
#       - (300A,0018) DoseReferencePointCoordinates (DS) - Must be Kept if Primary -> Check only
#       - (300A,0013) DoseReferenceUID (UI) -> TODO
#       - (300A,0020) DoseReferenceType (CS): TARGET -> Check only
#       - (300A,0023) DeliveryMaximumDose (DS)
#       - (300A,0026) Target Prescription Dose (DS) - TODO: Needs to be exactly set to RS Values - Coming over with rounding errors
#       - (300A,002C) OrganAtRiskMaximumDose (DS)
#       - Private tags for Varian/UF: (3267,1000…), (3267,0010…)
#
#     Args:
#         ds: Full RTPlan pydicom Dataset.
#         beamset: Selected BeamSet with Prescription info.
#         expected: _Edits tracker for recording modified tags.
#         ref_point_location: True for coordinate refs, False for SITE‐based refs.
#
#     Returns:
#         List of operation messages for logging.
#     """
#     msgs: List[str] = []
#     seq0 = ds.FractionGroupSequence[0].ReferencedBeamSequence[0]
#
#     # Create a new DoseReference item
#     ref = pydicom.Dataset()
#     ref.add_new(0x300A0012, 'IS', 1)  # DoseReferenceNumber
#
#     # Description uses PlanLabel + ".0"
#     desc = f"{beamset.DicomPlanLabel}.0"
#     ref.add_new(0x300A0016, 'LO', desc)  # DoseReferenceDescription
#     msgs.append(f"Set DoseReferenceDescription='{desc}'")
#
#     # StructureType: COORDINATES or SITE
#     if ref_point_location:
#         ref.add_new(0x300A0014, 'CS', 'COORDINATES')  # DoseReferenceStructureType
#         coords = getattr(seq0, 'BeamDoseSpecificationPoint', [0, 0, 0])
#         ref.add_new(0x300A0018, 'DS', coords)  # DoseReferencePointCoordinates
#         msgs.append(f"Coordinates mode: set DoseReferencePointCoordinates={coords}")
#     else:
#         ref.add_new(0x300A0014, 'CS', 'SITE')  # DoseReferenceStructureType
#         # OnStructure.Name or Description for SITE refs
#         prim = beamset.Prescription.PrimaryPrescriptionDoseReference
#         if hasattr(prim, 'OnStructure'):
#             site_val = prim.OnStructure.Name
#         else:
#             site_val = getattr(prim, 'Description', 'UNKNOWN')
#         # Varian private tag for structure name
#         ref.add_new(0x32671000, 'UT', site_val)
#         expected.add(ref[0x32671000])
#         ref.add_new(0x32670010, 'LO', 'UW Madison RayScripts 3267')
#         expected.add(ref[0x32670010])
#         msgs.append(f"SITE mode: set private tag OnStructure/Description='{site_val}'")
#
#     # Generate a new DoseReferenceUID under the same SeriesInstanceUID prefix
#     prefix = '.'.join(str(ds.SeriesInstanceUID).split('.')[:4]) + '.'
#     uid = pydicom.uid.generate_uid(prefix=prefix)
#     ref.add_new(0x300A0013, 'UI', uid)  # DoseReferenceUID
#     msgs.append(f"Generated DoseReferenceUID={uid}")
#
#     # Target type and dose values (Gy)
#     ref.add_new(0x300A0020, 'CS', 'TARGET')  # DoseReferenceType
#     max_dose = beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue / 100
#     ref.add_new(0x300A0023, 'DS', max_dose)  # DeliveryMaximumDose
#     ref.add_new(0x300A002C, 'DS', max_dose)  # OrganAtRiskMaximumDose
#     msgs.append(f"Set maximum dose = {max_dose} Gy")
#
#     # Insert or update the sequence on the RTPlan
#     if 'DoseReferenceSequence' not in ds:
#         ds.add_new(0x300A0010, 'SQ', pydicom.Sequence([ref]))
#         expected.add(ds[0x300A0010])
#         msgs.append("Added new DoseReferenceSequence to RTPlan")
#     else:
#         ds.DoseReferenceSequence = pydicom.Sequence([ref])
#         msgs.append("Replaced existing DoseReferenceSequence in RTPlan")
#
#     return msgs
#

# def apply_beam_dose_specification_filter(
#         ds: pydicom.Dataset,
#         expected: Any,
#         apply_beam_spec_point: bool
# ) -> str:
#     """
#     Add or remove per-beam BeamDoseSpecificationPoint entries based on flag.
#
#     This wraps the internal helper `_adjust_beam_dose_spec_and_distribution`, which:
#       - Iterates each beam in FractionGroupSequence[0].ReferencedBeamSequence.
#       - If `apply_beam_spec_point` is True, reads the RTPlan’s DoseReferencePointCoordinates
#         and writes them to each beam’s BeamDoseSpecificationPoint (300A,0082).
#       - If False, removes any existing BeamDoseSpecificationPoint (300A,0082),
#         BeamDosePointDepth (300A,0088), RadiologicalDepth (300A,0089),
#         and BeamDoseType (300A,0090).
#       - Scales or uniformly distributes BeamDose (300A,0084) to match the primary aria_compatibility_mode.
#
#     Args:
#         ds: Full pydicom Dataset for the RTPlan.
#         expected: Edits tracker to record modified DICOM elements.
#         apply_beam_spec_point: If True, add spec points; if False, strip them.
#
#     Returns:
#         A semicolon-delimited summary of all operations performed.
#     """
#     msgs: List[str] = _adjust_beam_dose_spec_and_distribution(
#         ds,
#         expected,
#         apply_beam_spec_point
#     )
#     return "; ".join(msgs)


# def _adjust_beam_dose_spec_and_distribution(
#         ds: pydicom.Dataset,
#         expected: Any,
#         ref_point_location: bool
# ) -> List[str]:
#     """Adjust each beam’s specification point and scale or distribute beam doses.
#
#     DICOM tags used:
#       - (300A,0082) BeamDoseSpecificationPoint (DS)
#       - (300A,0084) BeamDose (DS)
#       - Optional removal of: (300A,0088) BeamDosePointDepth, (300A,0089) RadiologicalDepth,
#         (300A,0090) BeamDoseType
#       - Private tags commented for future use: (3249,1010...), (3249,0010...)
#
#     Args:
#         ds: Full RTPlan pydicom Dataset.
#         expected: _Edits tracker for recording modified tags.
#         ref_point_location: True to add coords, False to remove existing coords.
#
#     Returns:
#         List of operation messages for logging.
#     """
#     msgs: List[str] = []
#     frac = ds.FractionGroupSequence[0]
#     beams = frac.ReferencedBeamSequence
#     total_dose = sum(getattr(b, 'BeamDose', 0) for b in beams if hasattr(b, 'BeamDose'))
#     count = len(beams)
#     # Add or remove BeamDoseSpecificationPoint per beam
#     for b in beams:
#         name = get_referenced_beam_name(ds, b)
#         if ref_point_location:
#             coords = ds.DoseReferenceSequence[0].DoseReferencePointCoordinates
#             b.add_new(0x300A0082, 'DS', coords)  # BeamDoseSpecificationPoint
#             expected.add(b[0x300A0082], beam=b)
#             msgs.append(f"Beam '{name}': set BeamDoseSpecificationPoint={coords}")
#         else:
#             # remove location-based tags if present
#             for tag in (0x300A0082, 0x300A0088, 0x300A0089, 0x300A0090):
#                 if hasattr(b, tag):
#                     del b[tag]
#             msgs.append(f"Beam '{name}': cleared specification point tags")
#
#     # If no explicit beam doses, distribute evenly
#     if total_dose == 0:
#         uniform = ds.DoseReferenceSequence[0].DeliveryMaximumDose \
#                   / (count * frac.NumberOfFractionsPlanned)
#         for b in beams:
#             b.add_new(0x300A0084, 'DS', uniform)  # BeamDose
#             expected.add(b[0x300A0084], beam=b)
#             msgs.append(f"Beam '{get_referenced_beam_name(ds, b)}': assigned uniform dose={uniform}")
#     else:
#         # Scale existing BeamDose to match new total aria_compatibility_mode
#         for b in beams:
#             if hasattr(b, 'BeamDose'):
#                 scaled = b.BeamDose * ds.DoseReferenceSequence[0].DeliveryMaximumDose \
#                          / (total_dose * frac.NumberOfFractionsPlanned)
#                 if b.BeamDose != scaled:
#                     b.BeamDose = scaled
#                     expected.add(b[0x300A0084], beam=b)
#                     msgs.append(f"Beam '{get_referenced_beam_name(ds, b)}': scaled dose={scaled}")
#
#     return msgs


# def quantize_beam_doses_to_total(
#         beam_doses: List[float],
#         total_dose: float,
#         decimals: int = 3
# ) -> List[float]:
#     """
#     Given an initial set of beam doses (which may be unnormalized weights or raw dose values),
#     compute a new set of beam doses that exactly sum to `total_dose` when each value is
#     rounded to `decimals` decimal places.
#
#     Steps:
#       1. Normalize the input `beam_doses` so their sum is 1.0 (weights).
#       2. Multiply each weight by `total_dose` to get the raw target dose for each beam.
#       3. Quantize each raw dose to the specified number of decimal places using
#          ROUND_HALF_UP.
#       4. Compute the residual error (total_dose minus sum of quantized doses).
#       5. Add the residual error to the beam with the largest original weight to
#          ensure the final list sums exactly to `total_dose`.
#
#     Args:
#         beam_doses: List of initial beam dose values or relative weights.
#         total_dose: Desired total dose (same units as beam_doses).
#         decimals: Number of decimal places for the DICOM DS string (e.g. 3).
#
#     Returns:
#         A new list of beam doses (floats) whose rounded sum equals `total_dose`.
#     """
#     # Convert to Decimal for accurate rounding
#     D = Decimal
#     total_d = D(str(total_dose))
#     # Compute sum of inputs and derive normalized weights
#     sum_input = sum(beam_doses)
#     if sum_input == 0:
#         raise ValueError("Sum of beam_doses must be non-zero")
#     weights = [D(str(b)) / D(str(sum_input)) for b in beam_doses]
#
#     # Raw target doses
#     raw = [(w * total_d) for w in weights]
#     # Quantize each to the specified precision
#     quantized = [
#         r.quantize(D(f'1.{"0" * decimals}'), rounding=ROUND_HALF_UP)
#         for r in raw
#     ]
#
#     # Compute and absorb rounding error
#     error = total_d - sum(quantized)
#     # Find the index with largest weight
#     max_idx = max(range(len(weights)), key=lambda i: weights[i])
#     quantized[max_idx] = quantized[max_idx] + error
#
#     # Convert back to floats
#     return [float(q) for q in quantized]


def format_dose_value(val: Decimal, max_chars: int = 16, decimals: int = 10, strip=False) -> str:
    """
    Format a Decimal for DICOM DS with fixed decimal precision and optional trailing zeros,
    preserving exact float interpretation for ARIA.

    Args:
        val (Decimal): Value to format
        max_chars (int): DICOM DS max string length (16 default)
        decimals (int): Number of decimal places to preserve
        strip (bool): If True, strip trailing zeros; if False, preserve them

    Returns:
        str: Formatted string preserving trailing zeros
    """
    if strip:
        # Strip trailing zeros if requested
        s = f"{val:.{decimals}f}".rstrip('0').rstrip('.')
    else:
        s = f"{val:.{decimals}f}"  # Do NOT strip trailing zeros
    if len(s) > max_chars:
        # fallback to rounded form with fewer decimals
        s = f"{val:.8f}"
    if len(s) > max_chars:
        s = f"{val:.6f}"
    return s[:max_chars]


# ----- Build Filters --------------------------------
# FILTER_CATALOG : tuple[FilterSpec, ...] = (
#     #1) Setup fields
#     #   Apply setup Dose rate and nominal beam energy for setup fields
#     FilterSpec(
#         name='setup_beam_filter',
#         fn=adjust_setup_field,
#         predicate=lambda c: c['setup_beam_filter']
#     ),
#     #2) Machine filter
#     FilterSpec(
#         name='machine_filter',
#         fn=apply_machine_filter,
#
#    )
# )


def find_beamset_by_label(beamsets, ds):
    """
    Find a matching BeamSet by DicomPlanLabel in the provided list of beamsets.

    Args:
        beamsets: List of BeamSet objects.
        ds: pydicom Dataset containing the RTPlan with DicomPlanLabel.

    Returns:
        The matching BeamSet object or None if not found.
    """
    ds_rt_plan_label = get_rt_plan_label(ds)
    if isinstance(beamsets, list):
        beamset = next((b for b in beamsets if b.DicomPlanLabel == ds_rt_plan_label), None)
    else:
        beamset = beamsets
    if beamset is None:
        logging.warning(f'No matching beamset found for DicomPlanLabel: {ds_rt_plan_label} in beamset_list')
        return None
    return beamset


# from typing import List, Tuple, Optional
# import xml.etree.ElementTree as ET

def generate_extended_va_xml(
        dose_refs: List[Tuple[str, Optional[str], Optional[str]]],
        beams: Optional[List[Tuple[int, int]]] = None,
        tolerance_table: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Generate compact ExtendedVAPlanInterface XML string with no newlines or extra spacing.

    Args:
        dose_refs: List of tuples (ref_num, daily_limit, session_limit).
        beams: Optional list of tuples (ReferencedBeamNumber, FieldOrder).
        tolerance_table: Optional list of (field_name, value) pairs.

    Returns:
        str: XML string suitable for writing to DICOM tag (no newlines).
    """
    root = ET.Element("ExtendedVAPlanInterface", Version="1")

    # Beams
    beams_elem = ET.SubElement(root, "Beams")
    if beams:
        for num, order in beams:
            beam = ET.SubElement(beams_elem, "Beam")
            ET.SubElement(beam, "ReferencedBeamNumber").text = str(num)
            ext = ET.SubElement(beam, "BeamExtension")
            ET.SubElement(ext, "FieldOrder").text = str(order)
            ET.SubElement(ext, "GantryRtnExtendedStart").text = "false"
            ET.SubElement(ext, "GantryRtnExtendedStop").text = "false"

    # ToleranceTables
    tables_elem = ET.SubElement(root, "ToleranceTables")
    if tolerance_table:
        table = ET.SubElement(tables_elem, "ToleranceTable")
        ET.SubElement(table, "ReferencedToleranceTableNumber").text = "1"
        ext = ET.SubElement(table, "ToleranceTableExtension")
        for field, val in tolerance_table:
            ET.SubElement(ext, field).text = val

    # DoseReferences
    dose_elem = ET.SubElement(root, "DoseReferences")
    for number, daily, session in dose_refs:
        dr = ET.SubElement(dose_elem, "DoseReference")
        ET.SubElement(dr, "ReferencedDoseReferenceNumber").text = str(number)
        ext = ET.SubElement(dr, "DoseReferenceExtension")
        if daily is not None:
            ET.SubElement(ext, "DailyDoseLimit").text = str(daily)
        if session is not None:
            ET.SubElement(ext, "SessionDoseLimit").text = str(session)

    # Generate compact XML string
    xml_str = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        short_empty_elements=False
    ).decode("utf-8")
    xml_str = xml_str.replace("\n", "").replace("\r", "").replace("\t", "").strip()
    return xml_str


def find_prescription_index_of_dicom_dose_reference(dose_reference_sequence, beamset) -> int:
    def _check_inputs():
        if not hasattr(dose_reference_sequence, 'DoseReferenceNumber'):
            raise ValueError("dose_reference_sequence must have DoseReferenceNumber attribute")
        if not hasattr(beamset, 'Prescription'):
            raise ValueError("beamset must have a Prescription attribute")
        if not hasattr(dose_reference_sequence, 'DoseReferenceDescription'):
            raise ValueError(
                f'DoseReferenceDescription is empty for DoseReferenceNumber '
                f'{dose_reference_sequence.DoseReferenceNumber}. '
                'Cannot find matching info, it is likely the Final Dose script '
                'was not run before this one. Please run the Final Dose script first or disable '
                'filters and manually set reference point data.'
            )

    _check_inputs()
    index_drs = dose_reference_sequence.DoseReferenceNumber
    # If index_drs == 1 -> this is a primary prescription
    prescription_dose_references = beamset.Prescription.PrescriptionDoseReferences
    # Make a dictionary of the conditions to match
    drs_conditions = {'DESCRIPTION': dose_reference_sequence.DoseReferenceDescription,
                      'TARGET_DOSE': Decimal(str(dose_reference_sequence.TargetPrescriptionDose)),
                      'UID': dose_reference_sequence.DoseReferenceUID,
                      'ROI_NUMBER': dose_reference_sequence.ReferencedROINumber
                      if hasattr(dose_reference_sequence, 'ReferencedROINumber') else None
                      }
    # Loop over all the prescription entries and check the matching values
    for pdr in prescription_dose_references:
        logging.debug(f"Checking prescription dose reference: {pdr.Description} "
                      f"with index {prescription_dose_references.IndexOf(pdr)} for matches to these conditions "
                      f"on the dose reference sequence: "
                      f"{drs_conditions}")
        pdr_conditions = {
            'DESCRIPTION': pdr.Description,
            'TARGET_DOSE': Decimal(str(pdr.DoseValue)) / Decimal('100'),  # Convert to Gy
            'UID': pdr.DoseReferenceIdentifier.UID,
            'ROI_NUMBER': pdr.OnStructure.RoiNumber if hasattr(pdr, 'OnStructure')
                                                       and hasattr(pdr.OnStructure, 'RoiNumber') else None
        }
        # Let's check key by key
        for key in drs_conditions:
            if key not in pdr_conditions:
                logging.debug(f"Key '{key}' not found in prescription dose reference conditions.")
                continue
            if drs_conditions[key] != pdr_conditions[key]:
                logging.debug(f"Condition mismatch for key '{key}': "
                              f"{drs_conditions[key]} != {pdr_conditions[key]}")
                break
        if all(drs_conditions[k] == pdr_conditions[k] for k in drs_conditions):
            logging.debug(f"Found matching prescription dose reference: {pdr.Description} "
                          f"with index {prescription_dose_references.IndexOf(pdr)}")
            return prescription_dose_references.IndexOf(pdr)
    logging.error(f'The aria_compatibility_mode description is set to an unexpected value. '
                  f'It is {dose_reference_sequence.DoseReferenceDescription}, and would expect it was:'
                  f' {beamset.DicomPlanLabel}|D1...n '
                  f'Unable to find matching aria_compatibility_mode for DoseReferenceSequence:'
                  f' {dose_reference_sequence.DoseReferenceDescription}, likely due to missing Final Dose script ')
    raise ValueError(
        f'The aria_compatibility_mode description is set to an unexpected value.\n'
        f'It is {dose_reference_sequence.DoseReferenceDescription}, and would expect it was: '
        f'{beamset.DicomPlanLabel}|D1...n\n'
        f'Please run the Final Dose script first or disable filters and manually set reference point data '
        f'in ARIA.'
    )


def add_dose_reference_extension_tag(ds: Dataset, beamsets, expected) -> str:
    """
    Adds the Varian VISION 3253 private dose reference extension tag to a DICOM dataset.

    Args:
        ds (Dataset): The RT Plan DICOM dataset to modify.
        beamsets: RayStation beamsets object to extract dose references from.
        expected: A set-like container to track added tags (used downstream for filtering/export).
    """

    def get_dose_references(ds, matched_beamset) -> List[Tuple[str, Optional[str], Optional[str]]]:
        """Extract dose references from the beamset."""
        # Need to be careful here. The order of the beamset prescriptions is totally arbitrary, based on user input.
        # We can match the inDex=1 and primary prescription reliably, but need to search for the correct rx to match
        # the reference sequence bas
        dose_references = []
        # Loop over the ds DoseReferenceSequence instead
        for drs in ds.DoseReferenceSequence:
            # Find the matching beamset prescription for this index
            prescription_index = find_prescription_index_of_dicom_dose_reference(drs, matched_beamset)
            prescription_dose_reference = matched_beamset.Prescription.PrescriptionDoseReferences[prescription_index]
            number_of_fractions = Decimal(str(ds.FractionGroupSequence[0].NumberOfFractionsPlanned))
            total_dose_gy = Decimal(str(prescription_dose_reference.DoseValue)) / Decimal('100')  # Convert to Gy
            daily_limit = format_dose_value(total_dose_gy / number_of_fractions, strip=True)
            session_limit = format_dose_value(total_dose_gy / number_of_fractions, strip=True)
            dose_references.append((drs.DoseReferenceNumber, daily_limit, session_limit))
        return dose_references

    # Register private creator
    private_creator_tag = Tag(0x3253, 0x0010)
    private_creator_value = "Varian Medical Systems VISION 3253"
    ds.add_new(private_creator_tag, 'LO', private_creator_value)
    expected.add(ds[private_creator_tag])

    # Get the referenced beamset
    beamset = find_beamset_by_label(beamsets, ds)
    # Get dose references
    dose_refs = get_dose_references(ds, beamset)

    # Generate XML using full interface generator (only dose refs in this context)
    xml_string = generate_extended_va_xml(
        dose_refs=dose_refs,
        beams=None,
        tolerance_table=None
    )

    # Store XML in private tag (3253,1000)
    # Encode the xml string as bytes
    xml_encode = xml_string.encode('utf-8')
    private_data_tag = Tag(0x3253, 0x1000)
    ds.add_new(private_data_tag, 'UN', xml_encode)
    expected.add(ds[private_data_tag])
    ds.add_new(Tag(0x3253, 0x1002), 'UN', b'ExtendedIF')
    expected.add(ds[Tag(0x3253, 0x1002)])
    # ds.add_new(Tag(0x3253, 0x1001), 'UN', b'2858')
    # expected.add(ds[Tag(0x3253, 0x1001)])


def get_rs_prescription(beamset):
    """Get the primary aria_compatibility_mode dose reference from the beamset."""
    if hasattr(beamset.Prescription, 'PrimaryPrescriptionDoseReference'):
        return beamset.Prescription.PrimaryPrescriptionDoseReference
    else:
        logging.warning('No primary aria_compatibility_mode dose reference found in beamset.')
        return False


# def scale_reference_point_doses_to_prescription(current_beamset, dcm_rt_plan, decimal_precision=3,
#                                                 expected=None):
#     desired_decimals = decimal_precision
#     precision_scale = Decimal('10') ** desired_decimals  # e.g. Decimal('100')
#     quantum = Decimal('1.' + '0' * desired_decimals)  # e.g. Decimal('1.00')
#
#     primary_rx = get_rs_prescription(current_beamset)
#     n_fractions = Decimal(str(dcm_rt_plan.FractionGroupSequence[0].NumberOfFractionsPlanned))
#     primary_rx_dose = Decimal(str(primary_rx.DoseValue)) / Decimal('100')  # Convert to Gy
#     primary_fractional_dose = primary_rx_dose / n_fractions
#
#     doses = []
#     beam_sequences = []
#     for beam_sequence in dcm_rt_plan.FractionGroupSequence[0].ReferencedBeamSequence:
#         if hasattr(beam_sequence, 'BeamDose'):
#             doses.append(Decimal(str(beam_sequence.BeamDose)))
#             beam_sequences.append(beam_sequence)
#
#     scale = primary_fractional_dose / sum(doses)
#     print(f'Current dose sum is {sum(doses)}')
#     q_scaled_doses = []
#     remainders = []
#     # Logic for quantized dose adjustment with remainders
#     for d in doses:
#         quant_dose = (d * scale).quantize(Decimal(quantum), rounding=ROUND_HALF_UP)
#         q_scaled_doses.append(quant_dose)
#         remainders.append(d * scale - quant_dose)
#     integer_target = int((primary_fractional_dose * precision_scale).to_integral_value(rounding=ROUND_HALF_UP))
#     int_scaled_doses = [int((sd * precision_scale).to_integral_value(rounding=ROUND_HALF_UP)) for sd in
#                         q_scaled_doses]
#     K = int(integer_target - sum(int_scaled_doses))
#     # 1) Pair each remainder with its beam index
#     pairs = list(enumerate(remainders))
#     #    -> [(0, rho_0), (1, rho_1), ..., (n-1, rho_{n-1})]
#     # 2) Sort descending if K>0 (or ascending if K<0)
#     pairs.sort(key=lambda x: x[1], reverse=(K > 0))
#     # 3) Apply ±1 quantum to the top |K| beams, i.e. those with the largest remainders
#     for idx, _ in pairs[:abs(K)]:
#         int_scaled_doses[idx] += 1 if K > 0 else -1
#     # 4) Convert back to decimal doses
#     adjusted_values = [u / Decimal(precision_scale) for u in int_scaled_doses]
#     post_float_error = float(primary_fractional_dose) - sum([float(i) for i in adjusted_values])
#
#     # 5) Update the BeamDose values in the beam sequences
#     for beam_sequence, adjusted_value, dose in zip(beam_sequences, adjusted_values, doses):
#         # Update the BeamDose value in the beam sequence
#         beam_sequence.BeamDose = format_dose_value(adjusted_value)
#         # Log the changes in dose values
#         ref_beam_name = get_referenced_beam_attribute(dcm_rt_plan, beam_sequence, 'BeamName')
#         print(
#             f"Adjusted BeamDose for {ref_beam_name} from {dose:.{decimal_precision}f} to "
#             f"{adjusted_value:.{decimal_precision}f} Gy, %diff = "
#             f"{((adjusted_value - dose) / dose * 100):.12f}%")
#         if expected is not None:
#             expected.add(beam_sequence[0x300A0084], beam=beam_sequence)
#     print(
#         f'Sum of Adjusted: {sum(adjusted_values):.{decimal_precision}f}, with residual error = {post_float_error:.2e}')
#

def apply_prescription_filter_aria(ds, beamset, expected) -> str:
    """
    Build and insert the primary aria_compatibility_mode reference point, and redistribute beam doses, pretty much
    just for ARIA. This is because, to get the reference point doses to add correctly, we need to modify
    the beam dose specification points (making them locationless). Obviously, Mobius doesn't like that
    ARIA sets the dose to the primary reference point using the values in (300A,0084) BeamDose, so those have to
    add up to exactly the primary aria_compatibility_mode dose for the other dose levels to be correct.
    DICOM tags used:
    - (300A,0010) DoseReferenceSequence (SQ)
    - (300A,0012) DoseReferenceNumber (IS) - 1 for primary and 2, 3, etc. for subsequent -> Check only
    - (300A,0014) DoseReferenceStructureType (CS): COORDINATES for primary and SITE for secondary -> Check only
    - (300A,0016) DoseReferenceDescription (LO) -> TODO: This seems to be wonky in RS and appears off in ARIA
    - (300A,0018) DoseReferencePointCoordinates (DS) - Must be Kept if Primary -> Check only
    - (300A,0013) DoseReferenceUID (UI) -> TODO
    - (300A,0020) DoseReferenceType (CS): TARGET -> Check only
    - (300A,0023) DeliveryMaximumDose (DS) ?
    - (300A,0026) Target Prescription Dose (DS) - TODO: Needs to be exactly set to RS Values - Coming over with rounding errors
    - (300A,002C) OrganAtRiskMaximumDose (DS)
    - (300A, 0082) BeamDoseSpecificationPoint (DS) -
    - Private tags for Varian/UF: (3267,1000…), (3267,0010…)

    Args:
        ds:                 full pydicom Dataset for the RTPlan
        beamset:            beamset object (to grab DicomPlanLabel & Prescription data)
        expected:           the _Edits tracker to record tag edits
        ref_point_location: bool, whether to insert coordinates or SITE
    Returns:
        msg (str): Summary message, or ''.
    """

    def _determine_prescription_type(primary_dose_reference):
        """Determine the type of aria_compatibility_mode based on the beamset."""
        # Check for a primary dose reference object in RS
        if hasattr(primary_dose_reference, 'OnStructure'):
            return 'STRUCTURE'
        elif hasattr(primary_dose_reference, 'Description'):
            return 'SITE'
        else:
            return 'UNKNOWN'

    def _fraction_group_sequence_valid(ds):
        """Check if the FractionGroupSequence exists and has referenced beams."""
        if 'FractionGroupSequence' not in ds:
            logging.warning('No FractionGroupSequence found in RTPlan.')
            return False
        if len(ds.FractionGroupSequence[0].ReferencedBeamSequence) == 0:
            logging.warning('No ReferencedBeamSequence found in FractionGroupSequence.')
            return False
        return True

    def _find_rx_reference(beamset, dose_reference_sequence):
        logging.debug(f'Finding matching aria_compatibility_mode for dose reference: '
                      f'{beamset.DicomPlanLabel}')
        prescription_index = find_prescription_index_of_dicom_dose_reference(dose_reference_sequence, beamset)
        return beamset.Prescription.PrescriptionDoseReferences[prescription_index]

    def _add_private_dose_reference_identifier(item, description_str: str, expected):
        creator_tag = Tag(index_private_creator)
        data_tag = Tag(index_private_data)
        # Encode the description string as bytes
        description_str = description_str.encode('utf-8')
        if creator_tag in item:
            item[creator_tag].value = "Varian Medical Systems VISION 3267"
        else:
            item.add_new(creator_tag, 'LO', "Varian Medical Systems VISION 3267")
            expected.add(item[creator_tag])
        if data_tag in item:
            item[data_tag].value = description_str
        else:
            item.add_new(data_tag, 'UN', description_str)
            expected.add(item[data_tag])

    def _mu_scaled_beam_doses(mu: List[Decimal],
                              rx_primary: Decimal,
                              n_fractions: Decimal,
                              decimals: int = 8
                              ) -> Tuple[List[Decimal], Decimal]:
        """
        Compute MU-weighted BeamDose values and apply a K-remainder
        redistribution so the rounded triplet sums exactly to the
        prescription per fraction.

        Args
        ----
        mu : list of MU values, one per beam (setup beams already removed)
        rx_primary : prescription per fraction for the primary point [Gy]
        n_fractions : number of fractions planned
        decimals : number of decimal places allowed (Varian = 3)

        Returns
        -------
        doses : list of adjusted BeamDose values [Gy] (length = len(mu))
        rx_primary : returned unchanged for convenience
        """
        precision_scale = Decimal(10) ** decimals  # e.g. 1000
        quantum = Decimal(f"1e-{decimals}")  # e.g. 0.001
        primary_fractional_dose = rx_primary / n_fractions
        print(f'Input primary dose: {rx_primary} Gy, MU: {mu}, n_fractions: {n_fractions}'
              f'with primary fractional dose: {primary_fractional_dose} Gy')

        sum_total_mu = sum(mu)
        # --- raw MU-weighted dose before rounding ----------------------------
        unscaled = [primary_fractional_dose * m / sum_total_mu for m in mu]

        # --- first pass: round to grid ---------------------------------------
        q_doses = [d.quantize(quantum, ROUND_HALF_UP) for d in unscaled]

        # --- remainder pass (K-remainder, identical to Varian’s ±0.001 loop) --
        int_target = int((primary_fractional_dose * precision_scale).to_integral_value(ROUND_HALF_UP))
        int_doses = [int((d * precision_scale).to_integral_value(ROUND_HALF_UP)) for d in q_doses]
        K = int_target - sum(int_doses)  # number of quanta we still need

        if K:  # distribute the leftover quanta
            # sort indices by size of remainder *before* the first rounding
            remainders = [u - q for u, q in zip(unscaled, q_doses)]
            order = sorted(range(len(mu)),
                           key=lambda r_index: remainders[r_index],
                           reverse=(K > 0))
            for k_index in order[:abs(K)]:
                int_doses[k_index] += 1 if K > 0 else -1

        scaled_doses = [Decimal(u) / precision_scale for u in int_doses]
        logging.debug(f'Output doses: {scaled_doses}, with total dose: {sum(scaled_doses)},'
                      f' and residual error: {primary_fractional_dose - sum(scaled_doses)}')
        return scaled_doses, rx_primary

    def beams_have_dose(dcm_rt_plan):
        """Check if any beams in the DICOM RTPlan have a BeamDose value."""
        return any(hasattr(beam, 'BeamDose') for beam in dcm_rt_plan.FractionGroupSequence[0].ReferencedBeamSequence)

    msgs = []
    # TODO: move all tags to top so we can see which ones get used
    index_ref_point_desc = 0x300a0016
    index_dose_del_max_dose = 0x300a0023
    index_target_prescription_dose = 0x300a0026
    index_target_maximum_dose = 0x300a0027
    index_beam_dose_per_beam = 0x300a0084
    index_private_creator = 0x32670010  # Private creator tag for Varian VISION 3267
    index_private_data = 0x32671000  # Private data tag for Varian VISION 3267
    getcontext().prec = 28  # high enough to avoid rounding issues

    # If the beamset type is list, then we need to match the DicomPlanLabel attribute with the plan name
    # of the ds passed to this function
    if isinstance(beamset, list):
        logging.debug(f'Applying aria_compatibility_mode filter to beamsets: {[b.DicomPlanLabel for b in beamset]}')
    else:
        logging.debug(f'Applying aria_compatibility_mode filter to beamset: {beamset.DicomPlanLabel}')
    beamset = find_beamset_by_label(beamset, ds)
    logging.debug(f'Found beamset: {beamset.DicomPlanLabel} to match with DicomPlanLabel: {get_rt_plan_label(ds)}')
    msgs.append(f'Rx Filter for {beamset.DicomPlanLabel}: ')
    # only proceed if aria_compatibility_mode data exists
    # Check the ds for FractionGroupSequence and ReferencedBeamSequence
    if not _fraction_group_sequence_valid(ds):
        return ''
    # Fetch the aria_compatibility_mode object
    primary_dose_ref = get_rs_prescription(beamset)
    if type(primary_dose_ref) is bool:
        return ''
    number_of_fractions = Decimal(str(ds.FractionGroupSequence[0].NumberOfFractionsPlanned))

    for drs in ds.DoseReferenceSequence:
        deliv_tag = Tag(index_dose_del_max_dose)
        targ_tag = Tag(index_target_maximum_dose)
        rx_tag = Tag(index_target_prescription_dose)
        rs_prescription = _find_rx_reference(beamset, drs)
        dose_ref_num = Tag(0x300A0012)  # DoseReferenceNumber
        # ARIA rounds to 3 decimals then adjusts weights by 0.001 to reduce rounding error
        # maximum expected error is 0.0005 Gy * n fractions
        if drs.get(dose_ref_num, None) is not None and drs.DoseReferenceNumber == 1:
            # If this is the primary dose reference, do not set tolerance
            tol_factor = Decimal('0')
        else:
            tol_factor = Decimal('0') + Decimal('0.0005')  # 0.0005 x beam number
        rx_str = drs.get(rx_tag, None)
        if rx_str is None:
            rx_dose = Decimal(str(rs_prescription.DoseValue)) / Decimal('100')  # Convert to Gy
        else:
            rx_dose = Decimal(str(rx_str.value))  # Already in Gy
        new_val = format_dose_value(rx_dose, strip=False)
        new_tol = format_dose_value(rx_dose + tol_factor * number_of_fractions, strip=False)

        # Target Prescription Dose
        if rx_tag in drs:
            # overwrite the existing element’s value
            drs[rx_tag].value = new_val
        else:
            # create it from scratch (VR “DS” for Decimal String)
            drs.add_new(rx_tag, 'DS', new_val)
            expected.add(drs[rx_tag])

        # DeliveryMaximumDose
        if deliv_tag in drs:
            # overwrite the existing element’s value
            drs[deliv_tag].value = new_val
        else:
            # create it from scratch (VR “DS” for Decimal String)
            drs.add_new(deliv_tag, 'DS', new_val)
            expected.add(drs[deliv_tag])

        # TargetMaximumDose
        if targ_tag in drs:
            drs[targ_tag].value = new_tol
        else:
            drs.add_new(targ_tag, 'DS', new_tol)
            expected.add(drs[targ_tag])
        # Insert private reference tags for the Daily and Session Dose reference limits
        # Retreive the reference point name from the beamset
        ref_point_desc = drs.get(index_ref_point_desc, None)
        if ref_point_desc is None:
            # If the reference point description is not set, use the beamset DicomPlanLabel
            traceback.print_exc()
            logging.error(f"An error occurred while attempting to retrieve a DoseReferenceDescription "
                          f"for beamset {beamset.DicomPlanLabel}. "
                          f"\n Traceback:\n {traceback.format_exc()}")
            raise ValueError(
                f'Beam {beamset.DicomPlanLabel}: DoseReferenceDescription not found, '
                f'cannot proceed with dose adjustment.'
            )
        else:
            _add_private_dose_reference_identifier(drs, ref_point_desc.value, expected)

    # Adjust beam doses to sum to primary dose point (if dose was not specified, evenly distribute it)
    total_dose = Decimal('0.0')
    total_count = Decimal('0.0')
    total_mu = Decimal('0.0')

    # Loop through the beams in the FractionGroupSequence
    for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
        beam_name = get_referenced_beam_name(ds, b)
        tdt = get_referenced_beam_attribute(ds, b, 'TreatmentDeliveryType')
        if tdt == "SETUP" or tdt is None:
            logging.debug(f"{beam_name} is a setup beam skipping")
            continue
        total_count += Decimal('1')
        if hasattr(b, 'BeamDose'):
            total_dose += Decimal(str(b.BeamDose))
        if hasattr(b, 'BeamMeterset'):
            total_mu += Decimal(str(b.BeamMeterset))
    primary_dose = Decimal(str(primary_dose_ref.DoseValue)) / Decimal('100')  # Convert to Gy
    # Rescale the primary dose

    # Normalize by beam MU
    # if beams_have_dose(ds):
    # scale_reference_point_doses_to_prescription(current_beamset=beamset,
    #                                              dcm_rt_plan=ds, expected=expected,
    #                                              decimal_precision=3)
    if total_mu >= 0:
        mu_values = []
        ref_beams = []
        for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
            if get_referenced_beam_attribute(ds, b, 'TreatmentDeliveryType') == "SETUP":
                continue
            mu_values.append(Decimal(str(b.BeamMeterset)))
            ref_beams.append(b)
        doses, _ = _mu_scaled_beam_doses(mu_values,
                                         primary_dose,
                                         number_of_fractions,
                                         decimals=8)

        for b, dose in zip(ref_beams, doses):
            # write exactly three decimals
            b.add_new(index_beam_dose_per_beam, 'DS', f"{dose:.8f}")
            expected.add(b[index_beam_dose_per_beam], beam=b)
        # for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
        #     beam_name = get_referenced_beam_name(ds, b)
        #     tdt = get_referenced_beam_attribute(ds, b, 'TreatmentDeliveryType')
        #     if tdt == "SETUP" or tdt is None:
        #         logging.debug(f"{beam_name} is a setup beam skipping")
        #         continue
        #     mu = Decimal(str(b.BeamMeterset))
        #     max_beam_dose = primary_dose * mu / (total_mu * number_of_fractions)
        #     # Ensure the max_beam_dose is formatted correctly
        #     # Set the precision of max_beam_dose to 10 digits to avoid rounding issues
        #     max_beam_dose = format_dose_value(max_beam_dose, strip=False)
        #     #
        #     b.add_new(index_beam_dose_per_beam, 'DS', max_beam_dose)
        #     expected.add(b[index_beam_dose_per_beam], beam=b)
        #     msgs.append(f"Beam {beam_name}: Set BeamDose={max_beam_dose} for MU={mu}, "
        #                 f"TotalMU={total_mu}, NumberOfFractions={number_of_fractions}")
    # elif total_count == 0:
    #     for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
    #         beam_name = get_referenced_beam_name(ds, b)
    #         tdt = get_referenced_beam_attribute(ds, b, 'TreatmentDeliveryType')
    #         if tdt == "SETUP" or tdt is None:
    #             logging.debug(f"{beam_name} is a setup beam skipping")
    #             continue
    #         # Calculate the beam dose per fraction
    #         beam_dose = primary_dose / (total_count * number_of_fractions)
    #         # Ensure the beam_dose is formatted correctly
    #         beam_dose = format_dose_value(beam_dose, strip=False)
    #         b.add_new(index_beam_dose_per_beam, 'DS', beam_dose)
    #         expected.add(b[index_beam_dose_per_beam], beam=b)
    #         msgs.append(f"Beam {beam_name}: Set BeamDose={beam_dose} for {total_count}, "
    #                     f"NumberOfFractions={number_of_fractions}")
    # else:
    #     for b in ds.FractionGroupSequence[0].ReferencedBeamSequence:
    #         # Let's get the correct Beam Dose and fudge it so that it exactly adds to the primary dose
    #         beam_name = get_referenced_beam_name(ds, b)
    #
    #         total_count = Decimal(str(total_count))
    #         beam_dose = primary_dose / (total_count * number_of_fractions)
    #         # Ensure the beam_dose is formatted correctly
    #         beam_dose = format_dose_value(beam_dose, strip=False)
    #         b.add_new(index_beam_dose_per_beam, 'DS', beam_dose)
    #         expected.add(b[index_beam_dose_per_beam], beam=b)
    #         msgs.append = f"Beam {beam_name}: Set BeamDose={beam_dose}"

    add_dose_reference_extension_tag(ds, beamset, expected)
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
