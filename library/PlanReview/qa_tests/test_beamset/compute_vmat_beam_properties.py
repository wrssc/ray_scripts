import numpy as np
from PlanReview.utils import get_machine
from PlanReview.review_definitions import PASS, MCS_TOLERANCES


def closed_leaf_gaps(banks, min_gap_moving):
    threshold = 1e-6
    leaf_gaps = np.empty_like(banks, dtype=bool)
    leaf_gaps[:, 0, :] = abs(banks[:, 0, :] - banks[:, 1, :]) < \
                         (1 + threshold) * min_gap_moving
    leaf_gaps[:, 1, :] = leaf_gaps[:, 0, :]
    return leaf_gaps


def get_segment_number(beam):
    # Get total number of segments in the beam
    try:
        seg_num = 0
        # Find the number of leaves in the first segment to initialize the array
        for s in beam.Segments:
            seg_num += 1
    except:
        return None
    return seg_num


def get_relative_weight(beam):
    # Get each segment weight
    weights = []
    for s in beam.Segments:
        weights.append(s.RelativeWeight)
    return weights


def get_mlc_bank_array(beam):
    # Find the number of segments
    segment_number = get_segment_number(beam)
    if not segment_number:
        return None
    else:
        s0 = beam.Segments[0]
    #
    # Get the number of leaves
    num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])
    # Bank array declaration
    banks = np.empty((num_leaves_per_bank, 2, segment_number))
    # Combine the segments into a single ndarray of size:
    # number of MLCs x number of banks x number of segments
    s_i = 0
    for s in beam.Segments:
        # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
        banks[:, 0, s_i] = s.LeafPositions[0]  # np.dstack((banks, bank))
        banks[:, 1, s_i] = s.LeafPositions[1]
        s_i += 1
    return banks


def filter_banks(beam, banks):
    # MLCs x number of banks x number of segments
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Min gap
    min_gap_moving = current_machine.Physics.MlcPhysics.MinGapMoving
    # Find all closed leaf gaps and zero them
    closed = closed_leaf_gaps(banks, min_gap_moving)
    # Filtered banks is dimension [N_MLC,Bank Index, Control Points]
    filtered_banks = np.copy(banks)
    filtered_banks[closed] = np.nan
    return filtered_banks


def compute_mcs(beam, override_square=False):
    # Step and Shoot
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    #
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    # Absolute value since the relative difference between leaves on the same
    # bank is used
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    weighted_lsv = np.sum(lsv * segment_weights)
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperture_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperture_area / np.sum(beam_ciao)
    weighted_aav = np.sum(aav * segment_weights)
    #
    # MCS calc
    mcsv = np.sum(lsv * aav * segment_weights)
    return weighted_lsv, weighted_aav, mcsv


def compute_mcs_masi(beam, override_square=False):
    #
    # Get the beam mlc banks
    banks = get_mlc_bank_array(beam)
    weights = get_relative_weight(beam)
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    # Leaf Widths
    leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
    #
    # Segment weights
    segment_weights = np.array(weights)
    averaged_segment_weights = segment_weights[0:-1]  # Last control point is zero MU
    #
    # Filter the banks
    filtered_banks = filter_banks(beam, banks)
    #
    # Square field test
    if override_square:
        filtered_banks[:, 0, :] = np.nan
        filtered_banks[:, 1, :] = np.nan
        filtered_banks[32:38, 0, :] = -2.
        filtered_banks[32:38, 1, :] = 2.
    # Mask out the closed mlcs
    mask_banks = np.ma.masked_invalid(filtered_banks)
    #
    # Jm Number of active leaves in both banks in each control point
    jm = np.count_nonzero(mask_banks, axis=0) - 1.  # Subtract for n+1 leaf without next in mask
    # Max position
    pos_max = np.amax(mask_banks, axis=0) - np.amin(mask_banks, axis=0)  # Checked
    # Handle amax = amin (rectangles)
    if np.amax(mask_banks[:, 0, :]) == np.amin(mask_banks[:, 0, :]):
        pos_max[0, :] = np.amax(mask_banks[:, 0, :])
    if np.amax(mask_banks[:, 1, :]) == np.amin(mask_banks[:, 1, :]):
        pos_max[1, :] = np.amax(mask_banks[:, 1, :])
    # Absolute value of difference in single bank leaf movement
    pos_max = np.abs(pos_max)
    #
    # Difference in leaf positions for each segment on each bank
    banks_diff = np.abs(mask_banks[:-1, :, :] - mask_banks[1:, :, :])
    separated_lsv = np.divide(np.sum(pos_max - banks_diff, axis=0), (jm * pos_max))
    # Compute the leaf sequence variability
    lsv = separated_lsv[0, :] * separated_lsv[1, :]
    vmat_lsv = (lsv[:-1] + lsv[1:]) / 2.
    weighted_vmat_lsv = np.sum(vmat_lsv * segment_weights[:-1])
    #
    # AAV calculation
    apertures = mask_banks * leaf_widths[:, None, None]
    mlc_diff = apertures[:, 1, :] - apertures[:, 0, :]
    segment_aperature_area = np.sum(mlc_diff, axis=0)
    #
    # CIAO
    beam_ciao = np.amax(mlc_diff, axis=1)
    aav = segment_aperature_area / np.sum(beam_ciao)
    vmat_aav = (aav[:-1] + aav[1:]) / 2.
    weighted_vmat_aav = np.sum(vmat_aav * segment_weights[:-1])
    #
    # MCS calc
    mcsv = np.sum(vmat_lsv * vmat_aav * averaged_segment_weights)
    return weighted_vmat_lsv, weighted_vmat_aav, mcsv


def compute_vmat_beam_properties(rso):
    # Compute MCS and any other desired beam properties
    child_key = "Beamset Complexity"
    message_str = "[Beam Name: LSV, AAV, MCS] :: "
    tech = rso.beamset.DeliveryTechnique
    pass_result = PASS
    for b in rso.beamset.Beams:
        if tech == 'DynamicArc':
            lsv, aav, mcs = compute_mcs_masi(b)
        elif tech == 'SMLC':
            # TODO Review versus a non segmented case with big opening differences
            lsv, aav, mcs = compute_mcs(b)
        else:
            message_str = 'Error Unknown technique {}'.format(tech)
            break
        message_str += '[{}: '.format(b.Name)
        # TODO: Sort MCS by technique then replace with PASS/FAIL
        # LSV
        if lsv < MCS_TOLERANCES['LSV']['MEAN'] - 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(lsv)
        elif lsv > MCS_TOLERANCES['LSV']['MEAN'] + 2. * MCS_TOLERANCES['LSV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(lsv)
        else:
            message_str += '{:.3f},'.format(lsv)
        # AAV
        if aav < MCS_TOLERANCES['AAV']['MEAN'] - 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(aav)
        elif aav > MCS_TOLERANCES['AAV']['MEAN'] + 2. * MCS_TOLERANCES['AAV']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(aav)
        else:
            message_str += '{:.3f},'.format(aav)
        # MCS
        if mcs < MCS_TOLERANCES['MCS']['MEAN'] - 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} OVERMOD,'.format(mcs)
        elif mcs > MCS_TOLERANCES['MCS']['MEAN'] + 2. * MCS_TOLERANCES['MCS']['SIGMA']:
            ## pass_result = FAIL
            pass_result = None
            message_str += '{:.3f} UNDERMOD,'.format(mcs)
        else:
            message_str += '{:.3f}'.format(mcs)
        message_str += '],'
    return pass_result, message_str
