import re
from collections import namedtuple
import numpy as np
from PlanReview.review_definitions import (
    PASS, ALERT, FAIL, TOMO_PREFERENCES,)

# Declare the named tuple for storing computed TomoTherapy parameters
TomoParams = namedtuple('TomoParams', ['gantry_period', 'time', 'couch_speed',
                                       'total_travel'])


# TOMOTHERAPY COMPUTATIONS
# Determine the TomoTherapy couch travel using the Y-offset of the first/last segment
def compute_couch_travel_helical(beam):
    # Take first and last segment, compute distance
    number_of_segments = len(beam.Segments)
    first_segment = beam.Segments[0]
    last_segment = beam.Segments[number_of_segments - 1]
    couch_travel = abs(last_segment.CouchYOffset - first_segment.CouchYOffset)
    return couch_travel


def compute_pitch_direct(beam):
    first_segment = beam.Segments[0]
    second_segment = beam.Segments[1]
    y_travel_per_projection = abs(second_segment.CouchYOffset - first_segment.CouchYOffset)
    pitch = round(y_travel_per_projection, 3)
    return pitch


def compute_couch_travel_direct(beam):
    # Take first and last segment, compute distance
    number_of_segments = len(beam.Segments)
    first_segment = beam.Segments[0]
    last_segment = beam.Segments[number_of_segments - 1]
    pitch = compute_pitch_direct(beam)
    couch_travel = pitch + abs(last_segment.CouchYOffset - first_segment.CouchYOffset)
    return couch_travel


def compute_tomo_params(beam):
    # Rs Beam object, return a named tuple
    number_segments = len(beam.Segments)
    # Total Time: Projection time x Number of Segments = Total Time
    time = beam.BeamMU * number_segments
    # Rotation period: Projection Time * 51
    if beam.DeliveryTechnique == "TomoHelical":
        gantry_period = beam.BeamMU * 51.
        total_travel = compute_couch_travel_helical(beam)
        # Couch Speed: Total Distance Traveled / Total Time
    else:
        total_travel = compute_couch_travel_direct(beam)
        gantry_period = None
    couch_speed = total_travel / time
    return TomoParams(gantry_period=gantry_period, time=time, couch_speed=couch_speed,
                      total_travel=total_travel)


def convert_couch_speed_to_mm(str_input):
    # Convert incoming str_input to a couch speed in mm/sec and return a string
    float_input = float(str_input)
    convert_input = float_input * 10  # cm-> mm
    return convert_input


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


# TODO: Need better plan classification, a tool that looks at dose per fraction
#       CT protocol, site, etc and tries to characterize the plan
# def get_treatment_details(rso):
#     """
#
#     :param rso:
#     :return:
#     """
#     TreatmentDetails = namedtuple('TreatmentDetails', ['body_site',
#                                                        'modality',
#                                                        'technique',
#                                                        'fractionation',
#                                                        'n_fx',
#                                                        'dose_per_fx'])
#
#     return TreatmentDetails(body_site=body_site,
#                             modality=modality,
#                             technique=technique,
#                             fractionation=plan_type,
#                             n_fx=number_of_fractions,
#                             dose_per_fx=dose_per_fraction)


def check_tomo_mod_factor(rso):
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
    site_found = None
    mod_high = None
    mod_low = None
    for site, prefs in TOMO_PREFERENCES.items():
        site_exp = "".join([v + '|' for v in prefs['ALIAS']])
        site_exp = site_exp[:len(site_exp) - 1]  # Drop the last pipe
        reg_site = re.compile(site_exp)
        if re.search(reg_site, rso.beamset.DicomPlanLabel):
            mod_high = float(prefs['MF_HIGH'])
            mod_low = float(prefs['MF_LOW'])
            site_found = site
            break

    # Check the current mod factors versus reported
    for b in rso.beamset.Beams:
        mod_factor = compute_mod_factor(beam=b)
        if not site_found:
            pass_result = ALERT
            message_str += f"No matching body site found for Beam {b.Name}" \
                           f" MF: {mod_factor:.2f}"
        elif mod_factor < mod_low:
            pass_result = ALERT
            message_str += f"Beam {b.Name} MF < {mod_low:.2f} " \
                           f"for site {site_found}"
        elif mod_factor > mod_high:
            if site_found == 'T3D':
                pass_result = FAIL
                message_str += f"Beam {b.Name} MF > {mod_high:.2f} " \
                               f"for site {site_found}. " \
                               f"Reoptimization REQUIRED"
            else:
                pass_result = ALERT
                message_str += f"Beam {b.Name} MF > {mod_high:.2f} " \
                               f"for site {site_found}"
        else:
            pass_result = PASS
            message_str += f"Beam {b.Name} MF ({mod_factor:.2f}) ideal " \
                           + "{:.2f} ≤ MF ≤ {:.2f}".format(mod_low, mod_high)
    return pass_result, message_str
