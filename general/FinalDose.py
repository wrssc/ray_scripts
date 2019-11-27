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
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging
import sys
import connect
import UserInterface
import BeamOperations
import PlanOperations
import PlanQualityAssuranceTests
import GeneralOperations
from GeneralOperations import logcrit as logcrit
import StructureOperations
import clr
clr.AddReference("System.Xml")
import System


class MyException(Exception):
    pass


def main():
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')
    ui = GeneralOperations.find_scope(level='ui')
    ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()

    # Institution specific plan names and dose grid settings
    fine_grid_names = ['_SBR_']
    fine_grid_size = 0.15
    coarse_grid_names = ['_THI_', '_VMA_', '_3DC_', '_BST_', '_DCA_']
    coarse_grid_size = 0.2
    # Set up the workflow steps.
    steps = []
    if 'Tomo' not in beamset.DeliveryTechnique and beamset.Modality != 'Electrons':
        steps.append('Rename Beams')
        steps.append('Check for external structure integrity')
        steps.append('Check SimFiducials have coordinates')
        steps.append('Check the dose grid size')
        steps.append('Check for control Point Spacing')
        steps.append('Compute Dose if neccessary')
        steps.append('Set DSP')
        steps.append('Round Jaws')
        steps.append('Round MU')
        steps.append('Recompute Dose')
        rename_beams = True
        cps_test = True
        simfid_test = True
        external_test = True
        grid_test = True
        tomo_couch_test = False

    if 'Tomo' in beamset.DeliveryTechnique:
        steps.append('Rename Beams')
        steps.append('Check for external structure integrity')
        steps.append('Check Tomo Couch position relative to isocenter')
        steps.append('Check SimFiducials have coordinates')
        steps.append('Check the dose grid size')
        steps.append('Compute Dose if neccessary')
        steps.append('Set DSP')
        rename_beams = True
        simfid_test = True
        external_test = True
        grid_test = True
        cps_test = False
        tomo_couch_test = True

    if beamset.Modality == 'Electrons':
        steps.append('Rename Beams')
        steps.append('Check for external structure integrity')
        steps.append('Check SimFiducials have coordinates')
        steps.append('Check the dose grid size')
        steps.append('Compute Dose if neccessary')
        steps.append('Set DSP')
        rename_beams = True
        simfid_test = True
        external_test = True
        grid_test = True
        cps_test = False
        tomo_couch_test = False

    status = UserInterface.ScriptStatus(steps=steps,
                                        docstring=__doc__,
                                        help=__help__)
    status.next_step('Checking beam names')

    if rename_beams:
        # Rename the beams
        BeamOperations.rename_beams()
        status.next_step('Renamed Beams, checking external integrity')

    # EXTERNAL OVERLAP WITH COUCH OR SUPPORTS
    if external_test:
        external_error = False
        while external_error:
            error = PlanQualityAssuranceTests.external_overlap_test(patient, case, exam)
            if len(error) != 0:
                connect.await_user_input('Eliminate overlap of patient external with support structures')
            else:
                external_error = False
        status.next_step('Reviewed external')

    # TOMO COUCH TEST
    if tomo_couch_test:
        tomo_couch_error = False
        couch_name = 'TomoCouch'
        couch = PlanQualityAssuranceTests.tomo_couch_check(case=case,
                                                           exam=exam,
                                                           beamset=beamset,
                                                           tomo_couch_name=couch_name,
                                                           limit=2.0,
                                                           shift=True)
        if not couch.valid:
            tomo_couch_error = True
            connect.await_user_input(couch.error)
            if not couch.valid:
                x_shift = couch.calculated_lateral_shift()
                logging.info('Moving {} by {}'.format(couch_name, x_shift))
                StructureOperations.translate_roi(case=case,
                                              exam=exam,
                                              roi=couch_name,
                                              shifts={'x': x_shift, 'y': 0, 'z': 0})
            plan.SetDefaultDoseGrid(
                VoxelSize={'x': coarse_grid_size,'y': coarse_grid_size, 'z': coarse_grid_size})
        else:
            tomo_couch_error = False
        status.next_step('TomoTherapy couch checked for correct lateral positioning')


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
        status.next_step('Reviewed SimFiducials')

    # GRID SIZE TEST
    if grid_test:
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
        status.next_step('Reviewed Dose Grid')

    # CONTROL POINT SPACING TEST
    if cps_test:
        cps_error = PlanQualityAssuranceTests.cps_test(beamset, nominal_cps=2)
        if len(cps_error) != 0:
            sys.exit(cps_error)
        status.next_step('Reviewed Control Point Spacing, computing dose if neccessary')

    if beamset.Modality == 'Photons':
        dose_algorithm = 'CCDose'
        if 'Tomo' in beamset.DeliveryTechnique:
            # TODO: Better exception handling here.
            try:
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=False)
                status.next_step('Recomputed Dose, finding DSP')
            except Exception:
                status.next_step('Dose recomputation unneccessary, finding DSP')
                logging.info('Beamset {} did not need to be recomputed'.format(beamset.DicomPlanLabel))
            # Set the DSP for the plan and recompute dose to force an update of the DSP
            BeamOperations.set_dsp(plan=plan, beam_set=beamset)
            beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=True)
            status.next_step('DSP set. Script complete')
        else:
            # TODO: Better exception handling here.
            try:
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=False)
                status.next_step('Recomputed Dose, finding DSP')
            except Exception as e:
                logging.debug('exception produced was {}. type{}'.format(e,type(e)))
                status.next_step('Dose re-computation unnecessary, finding DSP')
                logging.info('Beamset {} did not need to be recomputed'.format(beamset.DicomPlanLabel))

            # Set the DSP for the plan
            BeamOperations.set_dsp(plan=plan, beam_set=beamset)
            status.next_step('DSP set. Rounding jaws')

            # Round jaws to nearest mm
            logging.debug('Checking for jaw rounding')
            BeamOperations.round_jaws(beamset=beamset)

            # Round MU
            status.next_step('Jaws Rounded. Rounding MU')
            # The Autoscale hides in the plan optimization hierarchy. Find the correct index.
            indx = PlanOperations.find_optimization_index(plan=plan, beamset=beamset, verbose_logging=False)
            plan.PlanOptimizations[indx].AutoScaleToPrescription = False
            BeamOperations.round_mu(beamset)

            # Recompute dose
            status.next_step('Recomputing Dose')
            # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
            try:
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=True)
            except Exception as e:
                logging.debug(' error type is {}, with e = {}'.format(type(e), e))
            status.next_step('Script Complete')

    if beamset.Modality == 'Electrons':
        dose_algorithm = 'ElectronMonteCarlo'
        # TODO: Better exception handling here.
        try:
            # Try a quick run
            if not beamset.FractionDose.DoseValues.IsClinical:
                beamset.AccurateDoseAlgorithm.MonteCarloHistoriesPerAreaFluence = 10000
                status.next_step('Computing dose with small number of histories')
                beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=False)
        except Exception:
            status.next_step('Dose was clinical, no need for recompute')
            logging.info('Beamset {} did not need to be recomputed'.format(beamset.DicomPlanLabel))
        # Set the DSP and TODO: add rx surface
        BeamOperations.set_dsp(plan=plan, beam_set=beamset, percent_rx=98., method='Centroid')
        status.next_step('DSP set, checking statistics')
        mc_histories = 500000
        # Make sure electron monte carlo statistical uncertainty is clinical
        emc_result = BeamOperations.check_emc(beamset, stat_limit=0.005, histories=mc_histories)
        # If the test returns an insufficient uncertainty, change the number of histories
        if emc_result.bool is False:
            beamset.AccurateDoseAlgorithm.MonteCarloHistoriesPerAreaFluence = emc_result.hist
        # Autoscale must be turned off to round the MU.
        # Round MU
        indx = PlanOperations.find_optimization_index(plan=plan, beamset=beamset, verbose_logging=False)
        plan.PlanOptimizations[indx].AutoScaleToPrescription = False
        BeamOperations.round_mu(beamset)
        status.next_step('Rounded MU, recomputing doses')
        # Compute Dose with new DSP, and recommended history settings (mainly to force a DSP update)
        beamset.ComputeDose(ComputeBeamDoses=True, DoseAlgorithm=dose_algorithm, ForceRecompute=True)
        status.next_step('Script Complete')


    logcrit('Final Dose Script Run Successfully')


if __name__ == '__main__':
    main()
