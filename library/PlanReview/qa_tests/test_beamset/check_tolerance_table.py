from typing import NamedTuple, Optional, Tuple, Any

from OldPlanReview.ReviewDefinitions import TOMO_DATA
from PlanReview.review_definitions import PASS, FAIL, ALERT, GRID_PREFERENCES
from PlanReview.utils import get_machine
from PlanReview.utils.constants import (KEY_IMAGING_FREQ)


def tolerance_table_is_set(beamset: Any) -> bool:
    """ Check if the tolerance table is set for the given beamset."""
    return hasattr(beamset.PatientSetup.ToleranceTable, 'ToleranceTableLabel') and \
        beamset.PatientSetup.ToleranceTable.ToleranceTableLabel is not None


def get_beamset_tolerance_table(beamset: Any) -> Optional[str]:
    """ Retrieve the tolerance table for the given beamset."""
    try:
        return beamset.PatientSetup.ToleranceTable.ToleranceTableLabel
    except AttributeError:
        # If the attribute does not exist, return None
        return None



def check_tolerance_table(rso: NamedTuple, **kwargs: dict) -> Tuple[str, str]:
    """ Import the imaging frequency from values and check against the tolerance table.
    1) Check if the imaging frequency is specified in the input values.
    2) Check if the tolerance table is set for the beamset.
    3) Retrieve the tolerance table used in the beamset.
    4) Create a tolerance table guide from GRID_PREFERENCES in review_definitions.py.
    5) Check if the tolerance table label is in the tolerance table guide.
    6) Check if the imaging frequency is within the acceptable frequencies for the tolerance table.
    7) Return PASS if the imaging frequency is acceptable, otherwise return FAIL.

    Args:
        rso (NamedTuple): ScriptObjects in RayStation containing
                          [case ('RayStation Case Object'),
                           exam ('RayStation Exam Object'),
                           plan ('RayStation Plan Object'),
                           beamset ('RayStation BeamSet Object'),
                           db ('RayStation Database Object')]
        kwargs: Additional keyword arguments, including 'VALUES' which should contain the imaging frequency,
                stored under the key KEY_IMAGING_FREQ.
    Dependancies:
        - GRID_PREFERENCES: A dictionary containing tolerance table guides keyed by plan types, expects key
        'TOLERANCE_TABLE_GUIDE' to be present.
    Returns:
        Tuple[str, str]: First element is the status (PASS/FAIL/ALERT),
                         Second element is the message string.


    """
    values = kwargs.get('VALUES')
    imaging_frequency: Optional[str] = values.get(KEY_IMAGING_FREQ, None)

    if not imaging_frequency:
        return FAIL, "Imaging frequency is not specified in the input values."

    beam = rso.beamset.Beams[0]
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    if current_machine.Name in TOMO_DATA['MACHINES']:
        return PASS, "Tolerance table check is not applicable for Tomo machines."

    if not tolerance_table_is_set(rso.beamset):
        return FAIL, f"Tolerance table is not set for the beamset, {rso.beamset.DicomPlanLabel}."

    tolerance_table_label = get_beamset_tolerance_table(rso.beamset)
    if not tolerance_table_label:
        return FAIL, f"Tolerance table retrieval unsuccessful for beamset, {rso.beamset.DicomPlanLabel}."

    # Create a tolerance table guide from GRID_PREFERENCES
    tolerance_table_guide = {}
    for plan_type, preferences in GRID_PREFERENCES.items():
        # If the tolerance table guide is not already in tolerance table guide add it

        tolerance_tables = preferences.get('TOLERANCE_TABLE_GUIDE', {})
        for table, imaging_frequencies in tolerance_tables.items():
            if table not in tolerance_table_guide:
                tolerance_table_guide[table] = []
            if imaging_frequencies is not None:
                for im_fr in imaging_frequencies:
                    if im_fr not in tolerance_table_guide[table]:
                        tolerance_table_guide[table].append(im_fr)

    # Check if the tolerance table label is in the tolerance table guide
    if tolerance_table_label not in tolerance_table_guide.keys():
        return ALERT, f"Tolerance table '{tolerance_table_label}' is not recognized in the tolerance table guide."
    acceptable_frequencies = tolerance_table_guide[tolerance_table_label]
    # Check if the imaging frequency is within the acceptable frequencies
    if imaging_frequency in acceptable_frequencies:
        return PASS, f"Imaging frequency '{imaging_frequency}' is " \
                     f"acceptable for tolerance table '{tolerance_table_label}'."
    else:
        return FAIL, f"Imaging frequency '{imaging_frequency}' is NOT " \
                     f"acceptable for tolerance table '{tolerance_table_label}'."

