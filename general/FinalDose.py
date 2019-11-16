""" Final Dose

    1.0.4 Currently this simply is a wrapper for the rename_beams function. In future versions
        gantry angles, collimator angles, and couch angles may be slightly rounded to create
        an exact match to ARIA.

    1.0.5 Added rounding for jaw positions, MU, checks on overlap of external, dose grid,
        control point spacing, and sim fiducial point

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2019-09-05'

__version__ = '1.0.5'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2019-Nov-12'
__raystation__ = '8.0 SP B'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging
import sys
import connect
import BeamOperations
import PlanQualityAssuranceTests
import GeneralOperations
from GeneralOperations import logcrit as logcrit


class InvalidOperationException(Exception): pass


def main():
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')

    cps_test = False
    simfid_test = False
    external_test = False
    grid_test = False

    # EXTERNAL OVERLAP WITH COUCH OR SUPPORTS
    if external_test:
        external_error = False
        while external_error:
            error = PlanQualityAssuranceTests.external_overlap_test(patient, case, exam)
            if len(error) != 0:
                connect.await_user_input('Eliminate overlap of patient external with support structures')
            else:
                external_error = False

    # SIMFIDUCIAL TEST
    if simfid_test:
        fiducial_point = 'SimFiducials'
        fiducial_error = False
        while fiducial_error:
            error = PlanQualityAssuranceTests.simfiducial_test(case=case, exam=exam, poi=fiducial_point)
            if len(error) != 0:
                connect.await_user_input('Error in localization point: ' + '{}\n'.format(error))
            else:
                fiducial_error = False

    # GRID SIZE TEST
    if grid_test:
        fine_grid_names = ['_SBR_', '_SRS_']
        fine_grid_size = 0.1
        coarse_grid_names = ['_THI_', '_VMA_', '_3DC_', '_BST_', '_DCA_']
        coarse_grid_size = 0.2
        fine_grid_error = PlanQualityAssuranceTests.gridsize_test(beamset=beamset,
                                                                  plan_string=fine_grid_names,
                                                                  nominal_grid_size=fine_grid_size)
        coarse_grid_error = PlanQualityAssuranceTests.gridsize_test(beamset=beamset,
                                                                    plan_string=coarse_grid_names,
                                                                    nominal_grid_size=coarse_grid_size)
        if len(fine_grid_error) != 0:
            logging.warning('Dose grid check returned an error {}'.format(fine_grid_error))
            plan.SetDefaultDoseGrid(VoxelSize={'x': fine_grid_size, 'y': fine_grid_size, 'z': fine_grid_size})
            logging.info('Grid size was changed for SBRT-type plan')
        elif len(coarse_grid_error) != 0:
            logging.warning('Dose grid check returned an error {}'.format(coarse_grid_error))
            plan.SetDefaultDoseGrid(VoxelSize={'x': coarse_grid_size, 'y': coarse_grid_size, 'z': coarse_grid_size})
            logging.info('Grid size was changed for Normal-type plan')

    # CONTROL POINT SPACING TEST
    if cps_test:
        cps_error = PlanQualityAssuranceTests.cps_test(beamset, nominal_cps=2)
        if len(cps_error) != 0:
            sys.exit(cps_error)

    if 'Tomo' not in beamset.DeliveryTechnique:
        # Round jaws to nearest mm
        BeamOperations.round_jaws(beamset=beamset)
        # Rename the beams
        BeamOperations.rename_beams()
        # Round MU
        BeamOperations.round_mu(beamset)

    # Compute dose if need be
    # TODO: Better exception handling here.
    try:
        beamset.ComputeDose(
            ComputeBeamDoses=True,
            DoseAlgorithm="CCDose",
            ForceRecompute=False)
    except Exception:
        logging.info('Beamset {} did not need to be recomputed'.format(beamset.DicomPlanLabel))


    # Set the DSP for the plan
    BeamOperations.set_dsp(plan=plan, beam_set=beamset)
    logcrit('Final Dose Script Run Successfully')


if __name__ == '__main__':
    main()
