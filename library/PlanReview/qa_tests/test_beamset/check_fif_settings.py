from typing import NamedTuple, Tuple
from PlanReview.review_definitions import PASS, FAIL, ALERT


def check_fif_settings(rso: NamedTuple) -> Tuple[str, str]:
    """ Check FIF Settings
        Checks if the 'UseFieldInField' setting is enabled for the beamset.

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
        1. Test whether this plan is Field-in-Field.
        2. If it is not, then return a PASS because the settings are not applicable.
        3. If it is, multiple checks are required:
            * Are all the segment sizes over 2 MU? Was that setting activated?
            * Is the combined segment weight from the most open segment over 70% (pass), over 65% (alert)?
            * Are these settings active:
                ** Use first segment in beam
                ** Is the number of subfields set to something like 3 (pass), (5 alert), >5 (fail)?
                ** Min segment MU per fraction > 4 MU (pass), >3 MU (alert), <= 3 MU (fail)
                ** In plan optimization is segment weight only optimization enabled?

        Test Patients:
            PASS: Script_Testing, Needed, e.g. #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
            FAIL: Script_Testing, Needed, e.g. #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
        """
    try:
        # Retrieve the 'UseFieldInField' setting from the beamset
        use_fif = rso.beamset.UseFieldInField

        # Check if 'UseFieldInField' is enabled
        if use_fif:
            pass_result = PASS
            message_str = f"Beamset: {rso.beamset.DicomPlanLabel} has Field-in-Field enabled."
        else:
            pass_result = FAIL
            message_str = f"Beamset: {rso.beamset.DicomPlanLabel} does not have Field-in-Field enabled."

    except Exception as e:
        # Handle exceptions and return ALERT status
        message_str = f"Unknown error in checking Field-in-Field settings: {e}"
        pass_result = ALERT

    return pass_result, message_str