from typing import NamedTuple, Tuple
from PlanReview.review_definitions import (
    PASS, ALERT, FAIL)


def check_dicom_export_properties(beamset) -> Tuple[str, str]:
    """ Checks if the DicomExportProperties attribute is set in the beamset.

        Args:
            beamset: RayStation BeamSet Object

        Returns:
            pass_result, message_str (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                        Second element is the message string
    """
    beamset_name = beamset.DicomPlanLabel
    if not hasattr(beamset, 'DicomExportProperties'):
        return FAIL, f"Beamset: {beamset_name} does not have DicomExportProperties attribute."
    if not hasattr(beamset.DicomExportProperties, 'ExportedTreatmentMachineName'):
        return FAIL, f"Beamset {beamset_name} does not have ExportedTreatmentMachineName attribute."
    return PASS, ""


def check_machine_names(beamset) -> Tuple[str, str]:
    """ Checks if the MachineReference attribute is set in the beamset.

        Args:
            beamset: RayStation BeamSet Object

        Returns:
            pass_result, message_str (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                        Second element is the message string
    """
    beamset_name = beamset.DicomPlanLabel
    if not hasattr(beamset, 'MachineReference'):
        return FAIL, f"Beamset {beamset_name} does not have MachineReference attribute."
    if not hasattr(beamset.MachineReference, 'MachineName'):
        return FAIL, f"Beamset {beamset_name} does not have MachineName attribute."
    return PASS, ""


def check_machine_name(rso: NamedTuple) -> Tuple[str, str]:
    """ Checks to see if user has specified a machine alias

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                              [case ('RayStation Case Object'),
                               exam ('RayStation Exam Object'),
                               plan ('RayStation Plan Object'),
                               beamset ('RayStation BeamSet Object'),
                               db ('RayStation Database Object')]

        Returns:
            pass_result, message_str (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                        Second element is the message string

        Pseudocode:
        1. Check if the machine alias is set in the plan's metadata.
        2. If set, return PASS with a confirmation message.
        3. If not set, return FAIL with an error message.
    """
    from library.api.api_utils import get_machine
    result, message = check_dicom_export_properties(rso.beamset)
    if result != PASS:
        return result, message
    result, message = check_machine_names(rso.beamset)
    if result != PASS:
        return result, message

    beamset_name = rso.beamset.DicomPlanLabel

    # if not hasattr(rso.beamset, 'DicomExportProperties'):
    #     return FAIL, f"Beamset: {beamset_name} does not have DicomExportProperties attribute."
    # if not hasattr(rso.beamset.DicomExportProperties, 'ExportedTreatmentMachineName'):
    #     return FAIL, f"Beamset {beamset_name} does not have ExportedTreatmentMachineName attribute."
    # if not hasattr(rso.beamset, 'MachineReference'):
    #     return FAIL, f"Beamset {beamset_name} does not have MachineReference attribute."
    # if not hasattr(rso.beamset.MachineReference, 'MachineName'):
    #     return FAIL, f"Beamset {beamset_name} does not have MachineName attribute."
    # User-selected machine name
    selected_machine = rso.beamset.DicomExportProperties.ExportedTreatmentMachineName
    # Machine name from the beamset
    machine_name = rso.beamset.MachineReference.MachineName
    # Get the machine object using the machine name
    machine = get_machine(machine_name)
    if machine is None:
        return FAIL, f"Machine '{machine_name}' not found in the machine database."
    # Check attributes of the machine object
    if not hasattr(machine, 'NameAliases'):
        return FAIL, f"Machine '{machine_name}' does not have NameAliases attribute."
    possible_machines = machine.NameAliases
    # Cover the following cases.
    if not machine_name:
        return FAIL, "Machine name is not set in the beamset."
    # If there are no possible machines, then the machine configuration is incorrect.
    if not possible_machines:
        return FAIL, f"Machine '{machine_name}' has no aliases configured."
    # If the selected_machine is empty, then the user has not set an alias.
    if not selected_machine:
        return FAIL, f"Beamset '{beamset_name}' has no delivery system alias set. " \
                        f"Please set the 'ExportedTreatmentMachineName' in the DicomExportProperties."
    # If the selected_machine is not in the possible_machines, then the user has set an invalid alias.
    # (again perhaps impossible)
    if selected_machine not in possible_machines:
        return FAIL, f"Selected machine '{selected_machine}' " \
                     f"is not in the list of possible machines: {possible_machines}."
    return PASS, f"Machine name '{selected_machine}' is a valid alias for beamset '{beamset_name}', with " \
        f"machine '{machine_name}'."
