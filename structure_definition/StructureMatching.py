""" Match and Generate Derived ROIs
Matches the current ROI list with TG-263 defined names, colors, and types
This script loads the TG-263 file as a pandas dataframe
Makes an ExternalClean object if it isn't already there
Looks for conflicting structure names that will be a problem when matching occurs


Version History:
1.0.0 Production
1.0.1 RS 11B Update
1.0.2 Added SRS option for color scheme choices

Script: Matches all plan rois with TG-263 based normal structures returning a sorted list of
the most likely matches based on: exact match, previously matched names (aliases) or levenshtein match

Known Issues: 

Validation Notes:
    Test Patient: MR# ZZUWQA_ScTest_09Jun2022_MatchStructures
                  NAME: Script_Testing^MatchStructuresPRVs
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

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '27-Jun-2022'

__version__ = '1.0.1'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''

__raystation__ = '11B'
__maintainer__ = 'Adam Bayliss'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'
__help__ = ''

import os
from pathlib import Path
import logging
import xml.etree.ElementTree as Et
import pandas as pd
import re

# Local imports
import connect
import StructureOperations
from GeneralOperations import find_scope


def custom_color(roi_name, template):
    logging.debug(f'Change color called for {roi_name} with template {template}')
    if template == 'SRS MultiTarget':
        if roi_name.startswith('PTV') or roi_name.startswith('GTV'):
            number = roi_name[3:]  # Extract the number from ROI name (assuming it follows the pattern PTV* or GTV*)
            try:
                number = int(number)
                color_index = number % 10  # Get the color index based on the number (1 to 10)
                srs_colors = {
                    1: [255, 0, 0],
                    2: [255, 128, 0],
                    3: [255, 255, 0],
                    4: [128, 255, 0],
                    5: [0, 255, 128],
                    6: [0, 255, 255],
                    7: [0, 128, 255],
                    8: [0, 0, 255],
                    9: [128, 0, 255],
                    10: [255, 0, 255]
                }
                return srs_colors[color_index]
            except ValueError:
                pass
    return None  # Return None if the conditions are not met or there is an error


def main():
    # Get current patient, case, exam, and plan
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    scope = find_scope()
    beamset = scope['BeamSet']
    # Open the 263 Dataframe
    files = [[r"../protocols", r"", r"TG-263.xml"]]
    paths = []

    for i, f in enumerate(files):
        secondary_protocol_folder = f[0]
        institution_folder = f[1]
        path = Path(__file__).resolve().parent / secondary_protocol_folder / institution_folder
        paths.append(path)

    tree = Et.parse(paths[0] / files[0][2])
    rois_dict = StructureOperations.iter_standard_rois(tree)
    # Open the xml file as a dataframe
    df_rois = pd.DataFrame(rois_dict["rois"])

    # Make ExternalClean
    external_name = 'ExternalClean'
    _ = StructureOperations.make_externalclean(patient=patient,
                                               case=case,
                                               examination=exam,
                                               structure_name=external_name,
                                               suffix=None,
                                               delete=False)
    plan_rois = StructureOperations.find_types(case=case)
    # filter the structure list
    filtered_plan_rois = []
    for r in plan_rois:
        # Filter the list to look for duplicates and exit out if undesirable features are found
        found_case_sensitive_match = StructureOperations \
            .case_insensitive_structure_search(case=case, structure_name=r, roi_list=plan_rois)
        while found_case_sensitive_match:
            logging.info('Two structures share the same name with different case:' +
                         '{} matches {}'.format(r, found_case_sensitive_match)
                         )
            user_message = 'At least two structures share the same name with different case: ' + \
                           '{} matches {}. '.format(r, found_case_sensitive_match) + \
                           'Copy the geometry from the incorrect name to the correct ' + \
                           'structure and continue the script'
            connect.await_user_input(user_message)
        filtered_plan_rois.append(r)

    results, color_scheme = StructureOperations.match_roi(patient=patient,
                                            examination=exam,
                                            case=case,
                                            plan_rois=filtered_plan_rois)
    #
    # Redefine all of the plan rois
    all_rois = StructureOperations.find_types(case=case)
    for roi in all_rois:
        df_e = df_rois[df_rois.name == roi]
        if len(df_e) > 1:
            logging.warning('Too many matching {}. That makes me a sad panda. :('.format(roi))
        elif df_e.empty:
            logging.debug('{} was not found in the protocol list'.format(roi))
        else:
            e_name = df_e.name.values[0]
            logging.debug('roi {} was matched to dataframe element {}'.format(
                roi, e_name
            ))
            # Set color of matched structures
            color = custom_color(roi,color_scheme)
            if color:
                msg = StructureOperations.change_roi_color(case=case, roi_name=e_name, rgb=color)
                if msg is not None:
                    logging.debug(f'{e_name} could not change color. {msg}')
            elif df_e.RGBColor.values[0] is not None:
                e_rgb = [int(x) for x in df_e.RGBColor.values[0]]
                msg = StructureOperations.change_roi_color(case=case, roi_name=e_name, rgb=e_rgb)
                if msg is not None:
                    logging.debug(f'{e_name} could not change color. {msg}')
            # Set type and OrganType of matched structures
            if df_e.RTROIInterpretedType.values[0] is not None:
                e_type = df_e.RTROIInterpretedType.values[0]
                msg = StructureOperations.change_roi_type(case=case, roi_name=e_name,
                                                          roi_type=e_type)
                if msg is not None:
                    logging.debug(f'{e_name} could not change type. {msg}')
            # Create PRV's
            msg = StructureOperations.create_prv(patient=patient,
                                                 case=case,
                                                 examination=exam,
                                                 source_roi=e_name,
                                                 df_TG263=df_rois)
            if msg is not None:
                logging.debug(msg)
        # Basic target handling
        target_filters = {}
        # PTV rules
        target_filters['Ptv'] = re.compile(r'^PTV', re.IGNORECASE)
        # GTV rules
        target_filters['Gtv'] = re.compile(r'^GTV', re.IGNORECASE)
        # CTV rules
        target_filters['Ctv'] = re.compile(r'^CTV', re.IGNORECASE)
        for roi_type, re_test in target_filters.items():
            if re.match(re_test, roi):
                msg = StructureOperations.change_roi_type(case=case, roi_name=roi,
                                                          roi_type=roi_type)
                if msg is not None:
                    logging.debug(f'{roi}: could not change type. {msg}')
    msg = StructureOperations.create_derived(patient=patient,
                                             case=case,
                                             examination=exam,
                                             roi=None,
                                             df_rois=df_rois,
                                             roi_list=None)
    if msg is not None:
        logging.debug(msg)
    # :TODO: Uncomment when RaySearch allows a sort to roi list.
    # StructureOperations.renumber_roi(case=case)
    patient_log_file_path = logging.getLoggerClass().root.handlers[0].baseFilename
    log_directory = patient_log_file_path.split(str(patient.PatientID))[0]

    exam_dicom_data = exam.GetAcquisitionDataFromDicom()
    try:
        study_description = exam_dicom_data['StudyModule']['StudyDescription']
    except KeyError:
        study_description = 'None'
    try:
        protocol_name = exam_dicom_data['SeriesModule']['ProtocolName']
    except KeyError:
        protocol_name = 'None'
    try:
        series_description = exam_dicom_data['SeriesModule']['SeriesDescription']
    except KeyError:
        series_description = 'None'
    if beamset is not None:
        beamset_name = beamset.DicomPlanLabel
    else:
        beamset_name = 'None'

    # Output the resulting matches
    with open(os.path.normpath('{}/Matched_Structures.txt').format(log_directory),
              'a') as match_file:
        match_file.write(f'StudyDescription:{study_description},')
        match_file.write(f'ProtocolName:{protocol_name},')
        match_file.write(f'SeriesDescription:{series_description},')
        match_file.write(f'Beamset:{beamset_name},')
        i = 0
        for k, v in results.items():
            match_file.write(f'{v}:{k},')
        match_file.write('\n')



if __name__ == '__main__':
    main()
