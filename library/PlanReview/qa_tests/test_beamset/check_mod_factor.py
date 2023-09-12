import re
import numpy as np
from typing import NamedTuple, Tuple
from PlanReview.review_definitions import TOMO_PREFERENCES, ALERT, FAIL, PASS


def compute_mod_factor(beam: NamedTuple) -> float:
    """ Compute Modulation Factor
        Calculate the modulation factor based on the sinogram of a given beam.

        Args:
            beam (NamedTuple): TomoTherapy beam containing individual segments.

        Returns:
            mod_factor (float): The calculated modulation factor based
            on max(LOT)/Average of NonZero(LOT).

        Pseudocode:
        1. Read sinogram from beam segments.
        2. Convert sinogram to a numpy array.
        3. Filter out non-zero elements.
        4. Calculate modulation factor.
        5. Return modulation factor.

    """
    # Initialize sinogram list and segment counter
    sinogram = []
    number_segments = 0

    # Populate sinogram with leaf positions from beam segments
    for s in beam.Segments:
        number_segments += 1
        leaf_pos = [leaf_open for leaf_open in s.LeafOpenFraction]
        sinogram.append(leaf_pos)

    # Convert sinogram to a numpy array
    sino_array = np.array(sinogram)

    # Find non-zero elements
    non_zero = np.where(sino_array != 0)
    sino_non_zero = sino_array[non_zero]

    # Calculate modulation factor as max(LOT)/mean(LOT)
    mod_factor = np.max(sino_non_zero) / np.mean(sino_non_zero)

    return mod_factor


def check_mod_factor(rso: NamedTuple) -> Tuple[str, str]:
    """ Check Modulation Factor
            Verifies if the modulation factor of a given beam is within acceptable bounds.

            Args:
                rso (NamedTuple): ScriptObjects in RayStation containing
                                 [case ('RayStation Case Object'),
                                  exam ('RayStation Exam Object'),
                                  plan ('RayStation Plan Object'),
                                  beamset ('RayStation BeamSet Object'),
                                  db ('RayStation Database Object')]

            Returns:
                message (Tuple[str, str]): First element is the PASS/FAIL/ALERT status,
                                           Second element is the message string.

            Pseudocode:
            1. Search for a site match in TOMO_PREFERENCES
            2. Check mod factor for each beam
            2.a. Examples:
            * `TOMO_PREFERENCES` dictionary:
                {'ABDOMEN': {'ALIAS': ['Abdo_THI', 'Livr_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.6},
                 'BRAIN': {'ALIAS': ['Brai_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.6}, ...}

            * If a beamsets DicomPlanLabel matches an 'ALIAS' in the dictionary, it uses
              the corresponding 'MF_HIGH' and 'MF_LOW' values to evaluate the modulation factor.

            * For instance, if DicomPlanLabel is 'Abdo_THI', the function will check whether
              the modulation factor lies between 1.6 and 2.4 as per the 'ABDOMEN' entry.
            3. Return PASS/FAIL/ALERT status and message string

            Test Patients:
                Pass: Needed
                Fail: Needed
    """
    message_str = ""
    pass_result = None
    site_found = None
    mod_high = None
    mod_low = None
    for site, prefs in TOMO_PREFERENCES.items():
        site_exp = "".join([v + '|' for v in prefs['ALIAS']])
        site_exp = site_exp[:len(site_exp) - 1]  # Drop the last pipe
        reg_site = re.compile(site_exp)
        if re.search(reg_site, rso.beamset.DicomPlanLabel):
            mod_high = prefs['MF_HIGH']
            mod_low = prefs['MF_LOW']
            site_found = site
            break

    # Check the current mod factors versus reported
    for b in rso.beamset.Beams:
        mod_factor = compute_mod_factor(beam=b)
        if not site_found:
            pass_result = ALERT
            message_str += f"No matching body site found for Beam {b.Name} MF: {mod_factor:.2f}"
        elif mod_factor < mod_low:
            pass_result = ALERT
            message_str += f"Beam {b.Name} MF < {mod_low:.2f} for site {site_found}"
        elif mod_factor > mod_high:
            if site_found == 'T3D':
                pass_result = FAIL
                message_str += f"Beam {b.Name} MF > {mod_high:.2f} for site {site_found}. " \
                               f"Re-optimization REQUIRED"
            else:
                pass_result = ALERT
                message_str += f"Beam {b.Name} MF > {mod_high:.2f} for site {site_found}"
        else:
            pass_result = PASS
            message_str += f"Beam {b.Name} MF ({mod_factor:.2f}) ideal" \
                           f"{mod_low:.2f} ≤ MF ≤ {mod_high:.2f}"
    return pass_result, message_str
