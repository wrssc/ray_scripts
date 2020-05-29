""" Match and Generate Derived ROIs
Matches the current ROI list with TG-263 defined names, colors, and types
This script loads the TG-263 file as a pandas dataframe
Makes an ExternalClean object if it isn't already there
Looks for conflicting structure names that will be a problem when matching occurs


Version Notes:
0.0.0 

Script: Matches all plan rois with TG-263 based normal structures returning a sorted list of
the most likely matches based on: exact match, previously matched names (aliases) or levenshtein match

Known Issues: 

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
__date__ = '02-Feb-2020'

__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''

__raystation__ = '8.0.B'
__maintainer__ = 'Adam Bayliss'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = ''

import os
import sys
import logging
import random
import csv
## R: The only function you are using is ElementTree. I recommend:
##> import xml.etree.ElementTree as ET
## and then below
##> tree = ET.parse(file)
import xml
import pandas as pd
import re

# Local imports
import connect
## R: How does python know how to find these libraries? Is there another
## script that adds them to the path?
import BeamOperations
import Objectives
import Beams
import StructureOperations
import UserInterface

def main():
    ## R: StructureOperations is imported twice. I recommend moving all 
    ## imports outside of the function
    import StructureOperations
    from GeneralOperations import find_scope

    # Get current patient, case, exam, and plan
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    scope = find_scope()
    ## R: The plan variable is never used and can be safely omitted
    plan = scope['Plan']
    beamset = scope['BeamSet']
    # Open the 263 Dataframe
    ## R: PYTHON 3 NOTE: It is considered best practice in Python 3 to replace
    ## "os.path" with the pathlib library, which was added to the standard
    ## library for Python3. pathlib will improve the readability of this section:
    ##> from pathlib import Path
    ##> file = Path("..") / "protocols" / "TG-263.xml"
    ##> tree = ET.parse(file)
    ## *****
    ## R: This strikes me as a lot of code for loading a single file,
    ## even for os.path. Why is the loop needed?
    files = [[r"../protocols", r"", r"TG-263.xml"]]  # , [r"../protocols", r"UW", r""]]
    paths = []
    for i, f in enumerate(files):
        secondary_protocol_folder = f[0]
        institution_folder = f[1]
        paths.append(os.path.join(os.path.dirname(__file__),
                                  secondary_protocol_folder,
                                  institution_folder))
    tree = xml.etree.ElementTree.parse(os.path.join(paths[0], files[0][2]))
    rois_dict = StructureOperations.iter_standard_rois(tree)
    df_rois = pd.DataFrame(rois_dict["rois"])

    # Make ExternalClean
    external_name = 'ExternalClean'
    ## R: Style: The "ext_clean" is never used, so you could use the a 
    ## single underscore "_ = ". A single standalone underscore is sometimes
    ## used as a name to indicate that a variable is temporary or insignificant.
    ext_clean = StructureOperations.make_externalclean(patient=patient,
                                                       case=case,
                                                       examination=exam,
                                                       structure_name=external_name,
                                                       suffix=None,
                                                       delete=True)
    ## R: I am confused by the use of a while loop here.
    ## The while loop will only get executed once because the loop ends with
    ## "list_unfiltered = Flase". Seems like the while loop can be removed.
    list_unfiltered = True
    while list_unfiltered:
        plan_rois = StructureOperations.find_types(case=case)
        # filter the structure list
        filtered_plan_rois = []
        for r in plan_rois:
            # Filter the list to look for duplicates and exit out if undesirable features are found
            ## R: Will this function work if there are more than one case
            ## sensitive matches?
            found_case_sensitive_match = StructureOperations \
                .case_insensitive_structure_search(case=case, structure_name=r, roi_list=plan_rois)
            if found_case_sensitive_match is not None:
                logging.info('Two structures share the same name with different case:' +
                             '{} matches {}'.format(r, found_case_sensitive_match)
                             )
                user_message = 'Two structures share the same name with different case: ' + \
                               '{} matches {}. '.format(r, found_case_sensitive_match) + \
                               'Copy the geometry from the incorrect name to the correct ' + \
                               'structure and continue the script'
                connect.await_user_input(user_message)
                ## R: To be clear, using continue here will skip "filtered_plan_rois.append(r)"
                ## and move to the next contour in plan_rois. Is this intended?
                continue

            filtered_plan_rois.append(r)
        list_unfiltered = False

    ## R: In the control flow above, if there are structures that are a case-sensitive match,
    ## then the user manually unifies them into a single structure. When this happens,
    ## the contour "r" is never appended to filtered_plan_rois because of the continue statement.
    ## If the user decides to consolodate the duplicate contours into "r", then "r" will never end up in
    ## filtered_plan_rois when we reach the code below. Is that intended?
    results = StructureOperations.match_roi(patient=patient,
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
            if df_e.RGBColor.values[0] is not None:
                e_rgb = [int(x) for x in df_e.RGBColor.values[0]]
                msg = StructureOperations.change_roi_color(case=case, roi_name=e_name, rgb=e_rgb)
                if msg is not None:
                    logging.debug('{} could not change color. {}'.format(e_name, msg))
            # Set type and OrganType of matched structures
            if df_e.RTROIInterpretedType.values[0] is not None:
                e_type = df_e.RTROIInterpretedType.values[0]
                msg = StructureOperations.change_roi_type(case=case, roi_name=e_name,
                                                          roi_type=e_type)
                if msg is not None:
                    logging.debug('{} could not change type. {}'.format(e_name, msg))
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
                    logging.debug('{}: could not change type. {}'.format(roi, msg))
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
        # logging.debug('Exam {} has no Study Description'.format(exam.Name))
    try:
        protocol_name = exam_dicom_data['SeriesModule']['ProtocolName']
    except KeyError:
        protocol_name = 'None'
        # logging.debug('Exam {} has no Protocol Name'.format(exam.Name))
    try:
        series_description = exam_dicom_data['SeriesModule']['SeriesDescription']
    except KeyError:
        series_description = 'None'
        # logging.debug('Exam {} has no Series Description'.format(exam.Name))
    if beamset is not None:
        beamset_name = beamset.DicomPlanLabel
    else:
        beamset_name = 'None'

    # Output the resulting matches
    with open(os.path.normpath('{}/Matched_Structures.txt').format(log_directory),
              'a') as match_file:
        match_file.write('StudyDescription:{},'.format(study_description))
        match_file.write('ProtocolName:{},'.format(protocol_name))
        match_file.write('SeriesDescription:{},'.format(series_description))
        match_file.write('Beamset:{},'.format(beamset_name))
        i# match_file.write(',')
        i = 0
        for k, v in results.iteritems():
            # if i == len(results) - 1:
            #     match_file.write('{v}:{k}'.format(k=k, v=v))
            # else:
            match_file.write('{v}:{k},'.format(k=k, v=v))
            #i += 1
        match_file.write('\n')

    ## with open(os.path.normpath('{}/Matched_Structures.txt').format(log_directory)) as csvfile:
    ##     label_data = csv.DictReader(csvfile)
    ##     for row in label_data:
    ##         for k, v in row.iteritems():
    ##             logging.debug('Match {} to user input {}'.format(k, v))


if __name__ == '__main__':
    main()
