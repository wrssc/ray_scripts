import re
import numpy as np
from PlanReview.review_definitions import TOMO_PREFERENCES, ALERT, FAIL, PASS


def compute_mod_factor(beam):
    """
    Read the sinogram in from individual segments in the tomo beam, and output the mod
    factor based on max(LOT)/Average of NonZero(LOT)
    :param beam:
    :return:
    """
    sinogram = []
    number_segments = 0
    for s in beam.Segments:
        number_segments += 1
        leaf_pos = []
        for l in s.LeafOpenFraction:
            leaf_pos.append(l)
        sinogram.append(leaf_pos)
    # Convert sinogram to numpy array
    sino_array = np.array(sinogram)
    # Find non-zero elements
    non_zero = np.where(sino_array != 0)
    sino_non_zero = sino_array[non_zero]
    # Mod Factor = Average / Max LOT
    mod_factor = np.max(sino_non_zero) / np.mean(sino_non_zero)
    return mod_factor


def check_mod_factor(rso):
    """

    Args:
        rso:

    Returns:
    message (list str): [Pass_Status, Message String]

    Test Patient:
        TODO: PASS: Script_Testing, #ZZUWQA_ScTest_13May2022, ChwR_3DC_R0A0
        TODO: FAIL: Script_Testing, #ZZUWQA_ScTest_13May2022b, Esop_VMA_R1A0
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
                               f"Reoptimization REQUIRED"
            else:
                pass_result = ALERT
                message_str += f"Beam {b.Name} MF > {mod_high:.2f} for site {site_found}"
        else:
            pass_result = PASS
            message_str += f"Beam {b.Name} MF ({mod_factor:.2f}) ideal"\
                    "{mod_low:.2f} ≤ MF ≤ {mod_high:.2f}"
    return pass_result, message_str
