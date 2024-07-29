import pandas as pd
import numpy as np
import csv
import os
import logging
from typing import Tuple, NamedTuple, Optional, Any
from PlanReview.review_definitions import PASS, FAIL, ALERT, DATAFILE_TARGET_MATCH_STATISTICS
from PlanReview.utils.constants import KEY_BEAMSET_SELECT, KEY_BEAMSET_FRACTION_COUNT, \
    KEY_BEAMSET_TARGET_NAME, KEY_BEAMSET_DOSE

K_BEST = 'Best Match'
K_NO_MATCH = 'No Match'
K_EXACT = 'Exact Match'


def extract_gui_beamset_info(values, beamset_name):
    """
    Extracts beamset information from PySimpleGUI values using provided key definitions.

    This function processes the dictionary of values returned by the PySimpleGUI
    event loop to extract information about each beamset, including the selected
    beamset name, number of fractions, target names, and target doses. It also assigns
    a target number based on the dose.

    Args:
        values (dict): The dictionary of values returned by the PySimpleGUI event loop.
        beamset_name (str): The key name for the beamset name.

    Returns:
        dict: A dictionary where each key is a beamset index and its value is another
              dictionary with keys 'beamset_name', 'fractions', 'targets' where 'targets'
              is a list of dictionaries with keys 'name', 'dose', and 'target_number'.
    """
    beamset_info = {}

    for key, value in values.items():
        if KEY_BEAMSET_SELECT in key:
            beamset_index = key[1]
            beamset_info.setdefault(beamset_index, {'beamset_name': value, 'fractions': 0, 'targets': []})
        elif KEY_BEAMSET_FRACTION_COUNT in key:
            beamset_index = key[1]
            beamset_info[beamset_index]['fractions'] = value
        elif KEY_BEAMSET_TARGET_NAME in key:
            beamset_index, target_index = key[1], key[2]
            while len(beamset_info[beamset_index]['targets']) <= target_index:
                beamset_info[beamset_index]['targets'].append({'name': '', 'dose': 0, 'target_number': 0})
            beamset_info[beamset_index]['targets'][target_index]['name'] = value
        elif KEY_BEAMSET_DOSE in key:
            beamset_index, target_index = key[1], key[2]
            beamset_info[beamset_index]['targets'][target_index]['dose'] = value

    # Assign target numbers based on dose, sorted in descending order
    for beamset in beamset_info.values():
        targets_sorted_by_dose = sorted(beamset['targets'], key=lambda x: x['dose'], reverse=True)
        for i, target in enumerate(targets_sorted_by_dose, start=1):
            target['target_number'] = i

    # Return the beamset_info dictionary which matches the beamset_name
    for beamset_index, beamset_data in beamset_info.items():
        if beamset_data['beamset_name'] == beamset_name:
            return beamset_data
    beamset_data = None

    return beamset_data


def find_beamset_from_name(rso: NamedTuple, beamset_name: str) -> Optional[Any]:
    for beamset in rso.plan.BeamSets:
        if beamset.DicomPlanLabel == beamset_name:
            return beamset
    return None


def find_background_dependency(rso: NamedTuple, beamset_name: str) -> Optional[str]:
    """
    Find the background dependency for a given beamset.

    Args:
        rso (NamedTuple): The radiotherapy treatment plan.
        beamset_name (str): The name of the beamset.

    Returns:
        Optional[str]: The label of the background dependency, if found; otherwise, None.
    """
    for po in rso.plan.PlanOptimizations:
        for obs in po.OptimizedBeamSets:
            if obs.DicomPlanLabel == beamset_name and po.BackgroundDose is not None:
                return getattr(po.BackgroundDose.ForBeamSet, 'DicomPlanLabel', None)
    return None


def find_cooptimized_beamset(rso: NamedTuple, beamset_name: str) -> Optional[str]:
    """
    Find the co-optimized beamset for a given beamset.

    Args:
        rso (NamedTuple): The radiotherapy treatment plan.
        beamset_name (str): The name of the beamset.

    Returns:
        Optional[str]: The label of the co-optimized beamset, if found; otherwise, None.
    """
    po = find_optimization(rso, beamset_name)
    # If there is more than one beamset in this object, then there is a co-optimized beamset
    if len(po.OptimizedBeamSets) > 1:
        for obs in po.OptimizedBeamSets:
            if obs.DicomPlanLabel != beamset_name:
                return obs.DicomPlanLabel
    else:
        return None
    return None


def find_optimization(rso: NamedTuple, beamset_name: str) -> Optional[str]:
    """
    Find the optimization for a given beamset.

    Args:
        rso (NamedTuple): The radiotherapy treatment plan.
        beamset_name (str): The name of the beamset.

    Returns:
        Optional[str]: The label of the optimization, if found; otherwise, None.
    """
    for po in rso.plan.PlanOptimizations:
        for obs in po.OptimizedBeamSets:
            if obs.DicomPlanLabel == beamset_name:
                return po
    return None


def prescription_type_is_site(dose_ref):
    # Trap a site-based prescription
    if dose_ref.PrescriptionType == 'DoseAtPoint' and \
            not rx_contains_target(dose_ref):
        return True
    return False


def rx_contains_target(dose_ref):
    if doseref_attribute_test(dose_ref, 'OnStructure') is not None:
        return dose_ref.OnStructure.Name
    return None


def is_rx_primary(rso, beamset_name, contour_name):
    beamset = find_beamset_from_name(rso, beamset_name)
    if check_primary_rx_scriptobj(rso, beamset_name):
        # The Primary Rx is not empty.
        if contour_name:
            # The contour name is not empty.
            if beamset.Prescription.PrimaryPrescriptionDoseReference.OnStructure.Name == contour_name:
                return True
            else:
                return False
        else:
            return False  # No primary Rx possible when contour name is empty.
    else:
        return False


def check_primary_rx_scriptobj(rso, beamset_name):
    beamset = find_beamset_from_name(rso, beamset_name)
    primary_rx = beamset.Prescription.PrimaryPrescriptionDoseReference
    try:
        if primary_rx.OnStructure:
            return True
    except AttributeError:
        return False


def doseref_attribute_test(obj, attr_name):
    """
    Safely attempts to access an attribute of an object.

    Args:
        obj (object): The object to inspect.
        attr_name (str): The name of the attribute to access.

    Returns:
        The value of the attribute if it exists, None otherwise.
    """
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None


def find_rx_type(dose_ref):
    if prescription_type_is_site(dose_ref):
        return 'Site'
    else:
        return dose_ref.PrescriptionType


def extract_rx_data(rso, beamset_name):
    beamset = find_beamset_from_name(rso, beamset_name)
    rx_data = {'beamset_name': beamset_name,
               'raystation_fractions': doseref_attribute_test(beamset.FractionationPattern, 'NumberOfFractions')}
    rx = beamset.Prescription
    # Probably easiest to loop over the PrescriptionDoseReferences and append as we go.
    targets = []
    for dose_ref in rx.PrescriptionDoseReferences:
        rx_type = find_rx_type(dose_ref)
        n_fx = doseref_attribute_test(beamset.FractionationPattern, 'NumberOfFractions')
        raystation_target = rx_contains_target(dose_ref)
        raystation_primary_rx = is_rx_primary(rso, beamset_name, raystation_target)
        target_info = {
            'name': raystation_target,
            'dose': doseref_attribute_test(dose_ref, 'DoseValue') / 100,
            'rx_type': rx_type,
            'primary_rx': raystation_primary_rx,
            'dose_absolute_volume': doseref_attribute_test(dose_ref, 'DoseAbsoluteVolume'),
            'dose_relative_volume': doseref_attribute_test(dose_ref, 'DoseVolume'),
            'background_dependency': find_background_dependency(rso, beamset_name),
            'cooptimized_beamset': find_cooptimized_beamset(rso, beamset_name)
        }
        targets.append(target_info)
    rx_data['raystation_targets'] = targets
    return rx_data


def extract_raystation_beamset_info(rso, beamset_name):
    """
    Extracts beamset information from RayStation using API calls.

    Args:
        raystation_objects (dict): A dictionary containing RayStation objects,
                                   including 'rso' which is assumed to be the patient case object.
        beamset_name (str): The name of the beamset to extract information for.

    Returns:
        dict: A dictionary where each key is a beamset name and its value is a list of dictionaries
              with keys 'raystation_target', 'raystation_dose', and 'dose_absolute_volume'.
    """
    beamset = find_beamset_from_name(rso, beamset_name)
    if beamset:
        beamset_info = extract_rx_data(rso, beamset_name)
    else:
        beamset_info = {'beamset_name': beamset_name,
                        'raystation_fractions': 'N/A',
                        'raystation_targets': []}
    return beamset_info


def dict_to_dataframe(dictionary, dict_type):
    """
    Converts a nested dictionary to a pandas DataFrame where each target is a row.

    Args:
        dictionary (dict): The dictionary to convert.
        dict_type (str): A string indicating the type of dictionary ('gui' or 'raystation')
                         to tailor the processing accordingly.

    Returns:
        pandas.DataFrame: A DataFrame where each row represents a target.
    """
    records = []

    beamset_name = dictionary.get('beamset_name')
    fractions = dictionary.get('fractions') if dict_type == 'gui' else dictionary.get('raystation_fractions')
    targets = dictionary.get('targets') if dict_type == 'gui' else dictionary.get('raystation_targets')

    for target in targets:
        target_name = target.get('name')
        if not target_name:  # Skip the record if target_name is empty
            continue

        record = {
            'BeamsetName': beamset_name,
            'Fractions': fractions,
            'TargetName': target_name,
            'Dose': target.get('dose'),
            'MatchType': None,
            'RSTargetName': None,
            'RSTargetDose': None,
            'Score': 0,
            'DiceSimilarityCoefficient': 0,
            'Precision': 0,
            'Sensitivity': 0,
            'Specificity': 0,
            'PotentialMatches': []
        }
        if dict_type == 'raystation':
            record.update({
                'RxType': target.get('rx_type'),
                'PrimaryRx': target.get('primary_rx'),
                'DoseAbsoluteVolume': target.get('dose_absolute_volume'),
                'DoseRelativeVolume': target.get('dose_relative_volume'),
                'BackgroundDependency': target.get('background_dependency'),
                'CooptimizedBeamset': target.get('cooptimized_beamset')
            })
        records.append(record)

    return pd.DataFrame(records)


def test_fraction_match(df1, df2):
    """
    Tests if the number of fractions matches between two DataFrames for each beamset name, with very compact reporting.

    Args:
        df1 (pandas.DataFrame): The first DataFrame to compare, assumed to come from TPO.
        df2 (pandas.DataFrame): The second DataFrame to compare, assumed to come from RayStation.

    Returns:
        message (str): A message indicating the result of the comparison.
    """
    # Convert fractions to integers for consistent comparison
    df1['Fractions'] = df1['Fractions'].astype(int)
    df2['Fractions'] = df2['Fractions'].astype(int)

    # Use only unique beamset names from df1 for comparison
    unique_beamsets = set(df1['BeamsetName'])

    # Gather mismatches in a list
    mismatches = [
        (beamset, df1[df1['BeamsetName'] == beamset]['Fractions'].iloc[0],
         df2[df2['BeamsetName'] == beamset]['Fractions'].iloc[0])
        for beamset in unique_beamsets
        if df1[df1['BeamsetName'] == beamset]['Fractions'].iloc[0] !=
           df2[df2['BeamsetName'] == beamset]['Fractions'].iloc[0]
    ]

    # Construct and print the compact mismatch message
    if mismatches:
        mismatch_message = "Fraction mismatch: " + ", ".join(
            f"{beamset}: TPO:{fraction_df1} \u2260 RS:{fraction_df2} fractions" for beamset, fraction_df1, fraction_df2
            in mismatches
        )
    else:
        mismatch_message = f"Number of fractions match user-entered TPO values for beamset."

    return mismatch_message


def compare_target_names_and_doses(df1, df2):
    """
    Performs an initial comparison of beamsets between GUI (df1) and RayStation (df2) data to check
    for matching target names and doses. Updates df1 directly with match results.

    Args:
        df1 (pd.DataFrame): DataFrame representing GUI extracted data.
        df2 (pd.DataFrame): DataFrame representing RayStation extracted data.
    """
    for beamset_name in df1['BeamsetName'].unique():
        df1_beamset = df1[df1['BeamsetName'] == beamset_name]
        df2_beamset = df2[df2['BeamsetName'] == beamset_name]

        for index, row in df1_beamset.iterrows():
            target_name = row['TargetName']
            target_dose = float(row['Dose'])

            matching_target = df2_beamset[df2_beamset['TargetName'] == target_name]
            if not matching_target.empty:
                rs_dose = matching_target['Dose'].astype(float).iloc[0]
                rs_target_name = matching_target['TargetName'].iloc[0]
                if np.isclose(rs_dose, target_dose, atol=1e-8):
                    # Exact match
                    df1.loc[index, 'MatchType'] = K_EXACT
                    df1.loc[index, 'RSTargetDose'] = rs_dose
                    df1.loc[index, 'RSTargetName'] = rs_target_name
                else:
                    # Name match but dose mismatch
                    df1.loc[index, 'MatchType'] = 'Wrong Dose'
                    df1.loc[index, 'RSTargetDose'] = rs_dose
                    df1.loc[index, 'RSTargetName'] = rs_target_name
            else:
                # No match found
                df1.loc[index, 'MatchType'] = K_NO_MATCH


def determine_best_matches(df, criteria, thresholds):
    """
    Determines the best match for each GUI target based on customizable criteria and thresholds
    directly from a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing potential matches with their metrics.
        criteria (list of str): Metric names for determining the best match.
        thresholds (dict): Dictionary specifying the minimum threshold for each criterion.

    Returns:
        pd.DataFrame: DataFrame updated with the best match and its metrics.
    """
    import logging

    # Filter the DataFrame to include only rows that meet all the thresholds for each criterion
    criteria_filters = tuple(df[criterion] >= thresholds[criterion] for criterion in criteria)
    valid_matches = df[np.logical_and.reduce(criteria_filters)].copy()  # Make a copy to avoid SettingWithCopyWarning

    # If there are no valid matches left, prepare to return an unmodified DataFrame
    if valid_matches.empty:
        logging.debug(f"No valid matches found. Returning original DataFrame.")
        return df

    # Calculate the score for each valid match
    valid_matches['Score'] = valid_matches[criteria].mean(axis=1)

    # Sort and pick the best match based on the highest score
    best_matches = valid_matches.sort_values(by='Score', ascending=False).groupby('GUITarget').first().reset_index()
    logging.debug(f"Best matches:\n{best_matches}.")
    # Loop over best_matches and print out the scores
    for index, row in best_matches.iterrows():
        logging.debug(f"Best match for {row['GUITarget']}: {row['RSTarget']} with score {row['Score']}.")

    # Merge back to the original DataFrame to include the best match info
    result_df = df.merge(best_matches[['GUITarget', 'RSTarget', 'Score']], on='GUITarget', how='left',
                         suffixes=('', '_best'))

    return result_df


def parse_match_results(df):
    """
    Parses the best match results from a DataFrame to provide a concise message based on match types.

    Args:
        df (pandas.DataFrame): DataFrame containing best match results with metrics and scores.

    Returns:
        tuple: A tuple containing the result status and a single formatted message string.
    """

    grouped_messages = {
        K_EXACT: [],
        K_BEST: [],
        K_NO_MATCH: []
    }

    # Iterate through DataFrame rows
    for _, row in df.iterrows():
        gui_target = row['TargetName']
        rs_target = row.get('BestMatch')
        match_type = row['MatchType']

        if match_type == K_EXACT:
            grouped_messages[K_EXACT].append(gui_target)
        elif match_type == K_BEST:
            score = row.get('DiceSimilarityCoefficient', 0)  # Default to 0 if not available
            grouped_messages[K_BEST].append(f"{gui_target}\u21FE{rs_target} ({round(score,2):.2f})")
        elif match_type == K_NO_MATCH:
            grouped_messages[K_NO_MATCH].append(gui_target)

    # Format the single message string
    message_parts = []
    if grouped_messages[K_NO_MATCH]:
        message_parts.append("No match: " + ", ".join(grouped_messages[K_NO_MATCH]))
    if grouped_messages[K_BEST]:
        message_parts.append("Partial match (DSC): " + ", ".join(grouped_messages[K_BEST]))
    if grouped_messages[K_EXACT]:
        message_parts.append("Exact match: " + ", ".join(grouped_messages[K_EXACT]))

    if not message_parts:
        return FAIL, "Unknown error"

    result = PASS if K_NO_MATCH not in grouped_messages else PASS
    final_message = "; ".join(message_parts)

    return result, final_message


def write_matches_to_csv(rso, best_matches, output_csv_path):
    """
    Writes or appends best match results to a CSV file.

    Args:
        best_matches (dict): The best matches to write, including scores.
        output_csv_path (str): The path to the CSV file where results will be written or appended.
    """
    header = ['Beamset Name', 'GUI Target', 'Best RS Match', 'Score', 'Dice Similarity Coefficient',
              'Precision', 'Sensitivity', 'Specificity']
    mode = 'a' if os.path.exists(output_csv_path) else 'w'

    with open(output_csv_path, mode, newline='') as file:
        writer = csv.writer(file)
        if mode == 'w':
            writer.writerow(header)

        for gui_target, (rs_target, metrics, score) in best_matches.items():
            row = [rso.beamset.DicomPlanLabel, gui_target, rs_target, score, metrics['DiceSimilarityCoefficient'],
                   metrics['Precision'], metrics['Sensitivity'], metrics['Specificity']]
            writer.writerow(row)


def find_dose_equivalent_candidates(df1, df2, beamset_name):
    """
    For given unmatched targets in a beamset, finds dose-equivalent candidates in RayStation data.
    Updates the 'PotentialMatches' column in df1 with the list of candidate target names from RayStation.

    Args:
        df1 (pd.DataFrame): DataFrame representing GUI extracted data with a 'MatchType' column.
        df2 (pd.DataFrame): DataFrame representing RayStation extracted data.
        beamset_name (str): The name of the beamset to search within.
    """
    df1_beamset = df1[(df1['BeamsetName'] == beamset_name) & (df1['MatchType'] == K_NO_MATCH)]
    df2_beamset = df2[df2['BeamsetName'] == beamset_name]

    # Iterate over unmatched targets in df1
    for index, row in df1_beamset.iterrows():
        target_name = row['TargetName']
        target_dose = float(row['Dose'])

        # Find RayStation targets with a dose close to the unmatched target's dose
        matching_doses = df2_beamset[np.isclose(df2_beamset['Dose'].astype(float), target_dose, atol=1e-8)]

        # Update df1 with potential matches
        if not matching_doses.empty:
            df1.at[index, 'PotentialMatches'] = matching_doses['TargetName'].tolist()
        else:
            df1.at[index, 'PotentialMatches'] = []


def generate_mismatch_summary(df):
    """
    Generates a concise summary of mismatch details from a DataFrame, focusing on dose mismatches and using
    a compact format with Unicode characters for clarity.

    Args:
        df (pandas.DataFrame): DataFrame containing mismatch details, specifically 'target_name', 'dose',
         and 'matched_target_dose'.

    Returns:
        str: A brief summary of the mismatches, formatted with Unicode arrows and not equal sign,
             excluding 'Not found' cases.
    """
    # Filter DataFrame for 'Wrong Dose' type mismatches
    wrong_dose_df = df[df['MatchType'] == 'Wrong Dose']

    if wrong_dose_df.empty:
        return None

    # Create the summary message based on the wrong doses
    summary_parts = [f"{row['TargetName']}({round(float(row['Dose']))} \u21FE "
                     f"{round(float(row['RSTargetDose']))})"
                     for index, row in wrong_dose_df.iterrows()]

    summary_message = "Dose Mismatch! (TPO \u2260 RS) " + ', '.join(summary_parts)
    return summary_message


def update_best_matches_and_statistics(df_gui, ss):
    """
    Uses potential matches to update the GUI dataframe with the best match and updates the statistics.

    Args:
        df_gui (pd.DataFrame): DataFrame representing GUI extracted data with potential matches.
        df_rs (pd.DataFrame): DataFrame representing RayStation extracted data.
        ss (RayStationObject): Structure set object for accessing comparison methods.
    """
    criteria = ['DiceSimilarityCoefficient', 'Precision', 'Sensitivity', 'Specificity']
    thresholds = {
        'DiceSimilarityCoefficient': 0.7,
        'Precision': 0.5,
        'Sensitivity': 0.5,
        'Specificity': 0.7
    }

    # Iterate over the rows of the GUI dataframe
    for index, row in df_gui.iterrows():
        logging.debug(f"Processing row {index} with target {row['TargetName']}.")
        logging.debug(f"Potential matches: {row['PotentialMatches']}, with match type {row['MatchType']}.")
        if row['PotentialMatches'] and row['MatchType'] != K_EXACT:
            # Create a DataFrame to store comparison results
            match_stats = []

            # Get the reference target name and potential matches
            reference = row['TargetName']
            target_list = row['PotentialMatches']
            logging.debug(f"Reference target: {reference}, potential matches: {target_list}.")
            # Compute statistics for each potential match
            for target in target_list:
                # Assuming comp is a dictionary returned by a comparison method in RayStation
                comp = ss.ComparisonOfRoiGeometries(RoiA=reference, RoiB=target,
                                                    ComputeDistanceToAgreementMeasures=True)
                match_stats.append({
                    'GUITarget': reference,
                    'RSTarget': target,
                    'Score': None,  # Placeholder for the score
                    'DiceSimilarityCoefficient': comp['DiceSimilarityCoefficient'],
                    'Precision': comp['Precision'],
                    'Sensitivity': comp['Sensitivity'],
                    'Specificity': comp['Specificity']
                })
            logging.debug(f"Match statistics: {match_stats}.")

            # Convert match_stats to a DataFrame
            match_df = pd.DataFrame(match_stats)
            best_matches = determine_best_matches(match_df, criteria, thresholds)
            logging.debug(f"Best matches:\n{best_matches}.")
            df_gui.at[index, 'MatchType'] = K_NO_MATCH
            # If no match was found, there will not a Score_best column
            if 'Score_best' in best_matches.columns.to_list():
                # Update df_gui with the best match and corresponding statistics
                if best_matches['Score_best'].notnull().any():
                    best_match = best_matches.iloc[0]  # Assuming best_matches sorted descending by score
                    logging.debug(f"Best match found: {best_match['RSTarget_best']} with score {best_match['Score_best']}.")
                    df_gui.at[index, 'BestMatch'] = best_match['RSTarget_best']
                    df_gui.at[index, 'DiceSimilarityCoefficient'] = best_match['DiceSimilarityCoefficient']
                    df_gui.at[index, 'Precision'] = best_match['Precision']
                    df_gui.at[index, 'Sensitivity'] = best_match['Sensitivity']
                    df_gui.at[index, 'Specificity'] = best_match['Specificity']
                    df_gui.at[index, 'Score'] = best_match['Score_best']
                    df_gui.at[index, 'MatchType'] = K_BEST
        elif row['MatchType'] != K_EXACT:
            df_gui.at[index, 'MatchType'] = K_NO_MATCH


def match_fractions_to_preplan(rso: NamedTuple, **kwargs: Optional[str]) -> Tuple[str, str]:
    """ Match Fractions to Preplan
        Compares the number of fractions between the user-entered values and the DICOM dataset.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]
            **kwargs: Additional keyword arguments, options include:
                - VALUES (Optional[Dict[str, str]]): Dictionary containing user-entered values.

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                     Second element is the message string

        Pseudocode:
            1.  Extract fractions from the user-entered values
            2.  Get the number of fractions from the DICOM dataset
            3.  Compare Fractions: For each beamset, compare the number of fractions
                between GUI and RS. If they don't match, record the mismatch.
            4.  Determine the result (PASS/FAIL/ALERT)
            5.  Return the result and message

        Test Patients:
        """
    values = kwargs.get('VALUES')
    beamset_name = rso.beamset.DicomPlanLabel
    gui_beamset_info = extract_gui_beamset_info(values, beamset_name)
    if not gui_beamset_info:
        return FAIL, "Beamset not found in user-entered values."
    raystation_beamset_info = extract_raystation_beamset_info(rso, beamset_name)
    if not raystation_beamset_info:
        return FAIL, "Beamset not found in RayStation data."

    df_gui = dict_to_dataframe(gui_beamset_info, 'gui')
    df_rs = dict_to_dataframe(raystation_beamset_info, 'raystation')

    message = test_fraction_match(df_gui, df_rs)

    if 'mismatch' in message.lower():
        result = FAIL
    else:
        result = PASS

    return result, message


def match_rx_to_preplan(rso: NamedTuple, **kwargs: Optional[str]) -> Tuple[str, str]:
    """ Match Rx to Preplan
        Compares the user-entered prescription to the DICOM prescription.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]
            **kwargs: Additional keyword arguments, options include:
                - VALUES (Optional[Dict[str, str]]): Dictionary containing user-entered values.

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                     Second element is the message string

        Pseudocode:
            1.  Extract prescription from the user-entered values
            2.  Get the prescription from the RS beamset prescription
            3.  Compare Targets and Doses: For each target within a beamset,
                compare the target names and doses between GUI and RS.
                If there are mismatches:
                    4a. Return any mismatches with an incorrect dose as a FAIL, e.g. PTV_30 is indicated
                        to receive 30 Gy in the TPO but is prescribed 31 Gy in RS.
                    4b. Generate a list of RS targets that are prescribed the same dose as
                        the unmatched GUI targets.
                    4c. For each unmatched GUI target, check this list to find a target from RS
                        that might be a match based on dose equivalence.
                    4d. Check the Dice Similarity Coefficient, Precision, Sensitivity, and Specificity
                        to see if the dose-equivalent target is a match to the TPO target.
            5.  Determine the result:
                6a. PASS: all GUI-entered dose levels match in name and dose
                6b. ALERT: GUI-entered targets have a close match in dose to RS targets, i.e. there is a
                           target used in the RS plan that has the same dose as the GUI-entered target
                           and statistical metrics indicate a potential match between the two.
                6c. ALERT: No suitable match can be found for GUI-entered targets
            7.  Return the result and message

        Test Patients:

        Development patient: Script_Testing: MRN:ZZUWQA_ScTest_21Nov2022: multiple different kinds of prescription
        """
    values = kwargs.get('VALUES')
    # Declare beamset_name
    beamset_name = rso.beamset.DicomPlanLabel
    # Parse the prescription from RayStation
    raystation_beamset_info = extract_raystation_beamset_info(rso, beamset_name)
    # Parse the prescription from the GUI
    gui_beamset_info = extract_gui_beamset_info(values, beamset_name)
    # Convert the dictionaries to dataframes
    df_rs = dict_to_dataframe(raystation_beamset_info, 'raystation')
    df_gui = dict_to_dataframe(gui_beamset_info, 'gui')
    # Get the current structure set
    ss = rso.case.PatientModel.StructureSets[rso.exam.Name]

    # Compare the target names and doses
    compare_target_names_and_doses(df_gui, df_rs)

    # Analyze the results directly from the DataFrame
    # First check for mismatches in Dose: these are when the user-indicated dose
    # does not match the RS dose for the same target name.
    # if found, return, since those need to be fixed
    message_str = generate_mismatch_summary(df_gui)
    if message_str:
        result = FAIL
        return result, message_str
    # If there are no mismatches, check for unmatched targets
    logging.debug('Finding dose-equivalent candidates for unmatched targets.')
    find_dose_equivalent_candidates(df_gui, df_rs, beamset_name)
    # Determine the best matches based on contour similarity
    update_best_matches_and_statistics(df_gui, ss)
    # Parse the results to generate a message
    # write_matches_to_csv(rso, best_matches, "matches_summary.csv")
    result, message_str = parse_match_results(df_gui)
    # TODO: message_str is a dictionary here and needs to be reduced to a single string.
    # message_no_match = message_dict.get('No Match',"")
    # message_best = message_dict.get('Best Match',"")
    # message_exact = message_dict.get('Exact Match',"")
    # message_str = ""
    # if message_no_match:
    #     message_str = message_no_match + ": "
    # if message_best:
    #     message_str += message_best + ": "
    # if message_exact:
    #     message_str += message_exact
    logging.debug(f"***Message String:***\n{message_str}")
    return result, message_str
