""" Find a dose reference point within the dose grid
This attached script is provided as a tool and not as a RaySearch endorsed script for
clinical use.  The use of this script in its whole or in part is done so
without any guarantees of accuracy or expected outcomes. Please verify all results. Further,
per the Raystation Instructions for Use, ALL scripts MUST be verified by the user prior to
clinical use.

DSP Auto-Creation v 1.3



*Dependency: numpy

This script will add a DSP such that the doses for all beams will sum to the RX dose.
"""

import clr
import math
import numpy as np
import connect
import logging

clr.AddReference('System')


def find_dsp(plan, beam_set, dose_per_fraction=None, Beam=None):
    """
    :param plan: current plan
    :param beam_set: current beamset
    :param dose_per_fraction: dose value to find in cGy
    :param Beam: None sets beams to sum to Beamset fractional dose_value
                 <str_Beam> creates unique DSP for each beam for each beam's maximum
    :return: a list of [x, y, z] coordinates on the dose grid
    """
    # Get the MU weights of each beam
    tot = 0.
    for b in beam_set.Beams:
        tot += b.BeamMU

    if Beam is None:
        # Search the fractional dose grid
        # The dose grid is stored by RS as a numpy array
        pd = beam_set.FractionDose.DoseValues.DoseData
    else:
        # Find the right beam
        beam_found = False
        for b in beam_set.FractionDose.BeamDoses:
            if b.ForBeam.Name == Beam:
                pd = b.DoseValues.DoseData
                beam_found = True
        if not beam_found:
            print('No beam match for name provided')

    # The dose grid is stored [z: I/S, y: P/A, x: R/L]
    pd_np = pd.swapaxes(0, 2)

    if dose_per_fraction is None:
        rx = np.amax(pd_np)
    else:
        rx = dose_per_fraction

    logging.debug('rx = '.format(rx))

    xpos = None
    tolerance = 5.0e-2
    # beam_set = get_current('BeamSet')
    # plan = connect.get_current('Plan')

    xmax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.x
    ymax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.y
    xcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.x
    ycorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.y
    zcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.z
    xsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.x
    ysize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.y
    zsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.z

    if np.amax(pd_np) < rx:
        print 'max = ', str(max(pd))
        print 'target = ', str(rx)
        raise ValueError('max beam dose is too low')

    # rx_points = np.empty((0, 3), dtype=np.int)
    rx_points = np.argwhere(abs(rx - pd_np) <= tolerance)
    print("Shape of rx_points {}".format(rx_points.shape))

    # for (x, y, z), value in np.ndenumerate(pd_np):
    #    if rx - tolerance < value < rx + tolerance:
    #        rx_points = np.append(rx_points, np.array([[x, y, z]]), axis=0)
    #        print('dose = {}'.format(value))
    #        xpos = x * xsize + xcorner + xsize/2
    #        ypos = y * ysize + ycorner + ysize/2
    #        zpos = z * zsize + zcorner + zsize/2
    #        print 'corner = {0}, {1}, {2}'.format(xcorner,ycorner,zcorner)
    #        print 'x, y, z = {0}, {1}, {2}'.format(x * xsize, y * ysize, z * zsize)
    #        print 'x, y, z positions = {0}, {1}, {2}'.format(xpos,ypos,zpos)
    #        # return [xpos, ypos, zpos]
    # break

    matches = np.empty(np.size(rx_points, 0))

    for b in beam_set.FractionDose.BeamDoses:
        pd = np.array(b.DoseValues.DoseData)
        # The dose grid is stored [z: I/S, y: P/A, x: R/L]
        pd = pd.swapaxes(0, 2)
        # Numpy does evaluation of advanced indicies column wise:
        # pd[sheets, columns, rows]
        matches += abs(pd[rx_points[:, 0], rx_points[:, 1], rx_points[:, 2]] / rx -
            b.ForBeam.BeamMU / tot)

    min_i = np.argmin(matches)
    xpos = rx_points[min_i, 0] * xsize + xcorner + xsize / 2
    ypos = rx_points[min_i, 1] * ysize + ycorner + ysize / 2
    zpos = rx_points[min_i, 2] * zsize + zcorner + zsize / 2
    print 'x, y, z positions = {0}, {1}, {2}'.format(xpos, ypos, zpos)
    return [xpos, ypos, zpos]


def set_dsp(plan, beam_set):
    rx = beam_set.Prescription.PrimaryDosePrescription.DoseValue
    fractions = beam_set.FractionationPattern.NumberOfFractions
    if rx is None:
        raise ValueError('A Prescription must be set.')
    else:
        rx = rx / fractions

    dsp_pos = find_dsp(plan=plan, beam_set=beam_set, dose_per_fraction=rx)

    if dsp_pos:
        dsp_name = beam_set.DicomPlanLabel
        beam_set.CreateDoseSpecificationPoint(Name=dsp_name,
                                              Coordinates={'x': dsp_pos[0],
                                                           'y': dsp_pos[1],
                                                           'z': dsp_pos[2]})
    else:
        raise ValueError('No DSP was set, check execution details for clues.')

    # TODO: set this one up as an optional iteration for the case of multiple beams and multiple DSP's

    for i, beam in enumerate(beam_set.Beams):
        beam.SetDoseSpecificationPoint(Name=dsp_name)

    algorithm = beam_set.FractionDose.DoseValues.AlgorithmProperties.DoseAlgorithm
    # print "\n\nComputing Dose..."
    beam_set.ComputeDose(DoseAlgorithm=algorithm, ForceRecompute='TRUE')


def main():
    beam_set = connect.get_current('BeamSet')
    plan = connect.get_current('Plan')
    set_dsp(plan=plan, beam_set=beam_set)


if __name__ == '__main__':
    main()

