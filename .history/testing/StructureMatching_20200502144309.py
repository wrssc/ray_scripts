""" Match Dialog
Matches the current ROI list with TG-263 defined names, colors, and types

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
import xml
import pandas as pd
import re

# Local imports
import connect
import BeamOperations
import Objectives
import Beams
import StructureOperations
import UserInterface


def test_select_element(patient, case, exam, plan, beamset):
    """Testing for the selection of elements from different levels in a protocol xml file"""
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWHeadNeck.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    # Test 1:L
    # Try to get a list of beamsets located in
    set_levels = ['beamset', 'order']
    set_type = [None, 'beamset']
    on_screen_message = 'TESTING of XML-element find'

    for i, sl in enumerate(set_levels):
        on_screen_message += 'Test find a list of beamsets in the {} protocol '.format(file)
        logging.debug('Using {} and {}'.format(sl, set_type[i]))
        available_beamsets = Beams.select_element(
            set_level=sl,
            set_type=set_type[i],
            set_elements='beam',
            filename=file,
            dialog=False,
            folder=path_protocols
        )
        logging.debug('Available beamsets include: {}'.format(available_beamsets))
        if not available_beamsets:
            on_screen_message += 'FAIL: Could not Find Beamset at protocol level'
        else:
            for bs in available_beamsets:
                on_screen_message += 'Beamset {} found \n'.format(bs)

    # Uncomment for a dialog
    order_name = None
    BeamSet = BeamOperations.beamset_dialog(case=case,
                                            filename=file,
                                            path=path_protocols,
                                            order_name=order_name)

    # new_beamset = BeamOperations.create_beamset(patient=patient,
    #                                             case=case,
    #                                             exam=exam,
    #                                             plan=plan,
    #                                             dialog=False,
    #                                             BeamSet=BeamSet)

    # beams = BeamOperations.load_beams_xml(filename=file,
    #                                       beamset_name=BeamSet.protocol_name,
    #                                       path=path_protocols)

    # Test an exact load of a specific beamset
    beamset_folder = r'beamsets'
    file = 'UWVMAT_Beamsets.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)

    # For debugging we can bypass the dialog by uncommenting the below lines
    BeamSet = BeamOperations.BeamSet()
    BeamSet.name = '2 Arc VMAT - HN Shoulder'
    BeamSet.DicomName = 'Test' + str(random.randint(1, 100))
    BeamSet.technique = 'VMAT'
    BeamSet.machine = 'TrueBeam'
    BeamSet.rx_target = 'PTV_7000'
    BeamSet.iso_target = 'PTV_7000'
    BeamSet.modality = 'Photons'
    BeamSet.total_dose = 7000.
    BeamSet.number_of_fractions = 33
    BeamSet.protocol_name = '2 Arc VMAT - HN Shoulder'

    new_beamset = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=BeamSet)

    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=BeamSet.protocol_name,
                                          path=path_protocols)

    # Test to load objectives
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWProstate.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    order_name = 'Prostate Only-Hypo [28Fx 7000cGy]'
    objective_elements = Beams.select_element(
        set_level='order',
        set_type=None,
        set_elements='objectives',
        set_level_name=order_name,
        filename=file,
        dialog=False,
        folder=path_protocols,
        verbose_logging=False)
    logging.debug('Objectives are {}'.format(objective_elements))

    plan_targets = StructureOperations.find_targets(case=case)
    translation_map = {plan_targets[0]: '1000'}
    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_n = o.find('name').text
            o_t = o.find('type').text
            o_d = o.find('dose').text
            if o_n in translation_map:
                s_roi = translation_map[o_n][0]
            else:
                s_roi = None

            if "%" in o.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                o_r = o.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                # Correct the relative dose to the user-specified dose levels for this structure
                if o_r in translation_map:

                    s_dose = float(translation_map[o_r][1])  # * float(o_d) / 100
                    Objectives.add_objective(o,
                                             exam=exam,
                                             case=case,
                                             plan=plan,
                                             beamset=beamset,
                                             s_roi=s_roi,
                                             s_dose=s_dose,
                                             s_weight=None,
                                             restrict_beamset=None,
                                             checking=True)
                else:
                    logging.debug(
                        'No match found protocol roi: {}, with a relative dose requiring protocol roi: {}'
                            .format(o_n, o_r))
                    s_dose = 0
                    pass
            else:
                s_dose = None
                Objectives.add_objective(o,
                                         exam=exam,
                                         case=case,
                                         plan=plan,
                                         beamset=beamset,
                                         s_roi=s_roi,
                                         s_dose=s_dose,
                                         s_weight=None,
                                         restrict_beamset=None,
                                         checking=True)

    # Test to activate the dialog and select in select_element function


def main():
    import StructureOperations
    from GeneralOperations import find_scope

    # Get current patient, case, exam, and plan
    patient = find_scope(level='Patient')
    case = find_scope(level='Case')
    exam = find_scope(level='Examination')
    scope = find_scope()
    plan = scope['Plan']
    beamset = scope['BeamSet']
    # Open the 263 Dataframe
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
    # if StructureOperations.check_structure_exists(
    #         case,
    #         external_name,
    # #         roi_list=None,
    #         option="Check",
    #         exam=exam
    # ):
    #     logging.info('An external {} was already defined on exam {}.'
    #                  .format(external_name, exam.Name) +
    #                  ' It was not redefined.'
    #                  )
    # else:
    ext_clean = StructureOperations.make_externalclean(case=case,
                                                           examination=exam,
                                                           structure_name=external_name,
                                                           suffix=None,
                                                           delete=True)
        #   df_rois=df_rois)

    list_unfiltered = True
    while list_unfiltered:
        plan_rois = StructureOperations.find_types(case=case)
        # filter the structure list
        filtered_plan_rois = []
        for r in plan_rois:
            # Filter the list to look for duplicates and exit out if undesirable features are found
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
                continue

            filtered_plan_rois.append(r)
        list_unfiltered = False

    results = StructureOperations.match_roi(patient=patient,
                                            examination=exam,
                                            case=case,
                                            plan_rois=filtered_plan_rois)
    # This is where we could  put in all of the color changing, type changing, and PRV definition
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
                if msg is None:
                    logging.debug('{} color changed to {}'.format(e_name, e_rgb))
                else:
                    logging.debug('{} could not change type. {}'.format(e_name, msg))
            # Set type and OrganType of matched structures
            if df_e.RTROIInterpretedType.values[0] is not None:
                e_type = df_e.RTROIInterpretedType.values[0]
                msg = StructureOperations.change_roi_type(case=case, roi_name=e_name,
                                                          roi_type=e_type)
                if msg is None:
                    logging.debug('{} type changed to {}'.format(e_name, e_type))
                else:
                    logging.debug('{} could not change type.'.format(e_name))
                    for m in msg:
                        logging.debug(m)
            # Create PRV's
            msg = StructureOperations.create_prv(patient=patient,
                                                 case=case,
                                                 examination=exam,
                                                 source_roi=e_name,
                                                 df_TG263=df_rois)
            if msg is not None:
                for m in msg:
                    logging.debug(m)
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
                if msg is None:
                    logging.debug('{}: type changed to {}'.format(roi, roi_type))
                else:
                    logging.debug('{}: could not change type.'.format(roi))
                    for m in msg:
                        logging.debug(m)
    patient_log_file_path = logging.getLoggerClass().root.handlers[0].baseFilename
    log_directory = patient_log_file_path.split(str(patient.PatientID))[0]

    exam_dicom_data = exam.GetAcquisitionDataFromDicom()
    try:
        study_description = exam_dicom_data['StudyModule']['StudyDescription']
    except KeyError:
        study_description = 'None'
        logging.debug('Exam {} has no Study Description'.format(exam.Name))
    try:
        protocol_name = exam_dicom_data['SeriesModule']['ProtocolName']
    except KeyError:
        protocol_name = 'None'
        logging.debug('Exam {} has no Protocol Name'.format(exam.Name))
    try:
        series_description = exam_dicom_data['SeriesModule']['SeriesDescription']
    except KeyError:
        series_description = 'None'
        logging.debug('Exam {} has no Series Description'.format(exam.Name))
    if beamset is not None:
        beamset_name = beamset.DicomPlanLabel
    else:
        beamset_name = 'None'

    with open(os.path.normpath('{}/Matched_Structures.txt').format(log_directory),
              'a') as match_file:
        match_file.write('StudyDescription:{},'.format(study_description))
        match_file.write('ProtocolName:{},'.format(protocol_name))
        match_file.write('SeriesDescription:{},'.format(series_description))
        match_file.write('Beamset:{},'.format(beamset_name))
        match_file.write('{{,')
        i = 0
        for k, v in results.iteritems():
            if i == len(results) - 1:
                match_file.write('{v}:{k}}}'.format(k=k, v=v))
            else:
                match_file.write('{v}:{k},'.format(k=k, v=v))
            i += 1
        match_file.write('\n')

    ## with open(os.path.normpath('{}/Matched_Structures.txt').format(log_directory)) as csvfile:
    ##     label_data = csv.DictReader(csvfile)
    ##     for row in label_data:
    ##         for k, v in row.iteritems():
    ##             logging.debug('Match {} to user input {}'.format(k, v))


if __name__ == '__main__':
    main()
