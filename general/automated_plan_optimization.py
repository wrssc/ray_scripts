""" Automated Plan Optimization
    
    Automatically optimize the current case, examination, plan, beamset using
    input optimization parameters
    
    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are 
           passed to the function as an argument

    Example Usage:
    import optimize_plan from automated_plan_optimization
    optimization_inputs = {
        'initial_max_it': 40,
        'initial_int_it': 7,
        'second_max_it': 25,
        'second_int_it': 5,
        'vary_grid': True,
        'dose_dim1': 0.4,
        'dose_dim2': 0.3,
        'dose_dim3': 0.35,
        'dose_dim4': 0.2,
        'fluence_only': False,
        'reset_beams': True,
        'segment_weight': True,
        'reduce_oar': True,
        'n_iterations': 6}

    optimize_plan(patient=Patient,
                  case=case,
                  plan=plan,
                  beamset=beamset,
                  **optimization_inputs)

    Script Created by RAB 12Dec2019
    Prerequisites:

    Validation Notes:
    Test Patient: MR# ZZUWQA_ScTest_30Dec2020, 
                  Name: Script_Testing^Automated Plan – Whole Brain
    TomoTherapy, VMAT (seg weight, reduce OAR, variable dose grid)
    Version history:
    1.0.0 Moved Most functions to the OptimizeOperations library
    1.1.0 Updated to RayStation Version 10A SP1


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2021-Jan-05'
__version__ = '1.1.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10A.SP1'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__help__ = None
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
__credits__ = ['']
#

import logging

import connect
import UserInterface
import OptimizationOperations


def main():
    try:
        Patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        exam = connect.get_current("Examination")
    except SystemError:
        raise IOError("No Examination loaded. Load patient case and plan.")
    
    try:
        plan = connect.get_current("Plan")
    except SystemError:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except SystemError:
        raise IOError("No beamset loaded")

    # OPTIMIZATION DIALOG
    #  Users will select use of:
    # Fluence only - no aperture conversion
    # Maximum number of iterations for the first optimization
    optimization_dialog = UserInterface.InputDialog(
        title='Optimization Inputs',
        inputs={
            'input01_fluence_only': 'Fluence calculation only, for dialing in parameters ' +
                                    'all other values in this window will be ignored',
            'input02_cold_start': 'Reset beams (cold start)',
            'input03_cold_max_iteration': 'Maximum number of iterations for initial optimization',
            'input04_cold_interm_iteration': 'Intermediate iteration for svd to aperture conversion',
            'input05_ws_max_iteration': 'Maximum iteration used in warm starts ',
            'input06_ws_interm_iteration': 'Intermediate iteration used in warm starts',
            'input07_vary_dose_grid': 'Start with large grid, and decrease gradually',
            'input08_n_iterations': 'Number of Iterations',
            'input09_segment_weight': 'Segment weight calculation',
            'input10_reduce_oar': 'Reduce OAR Dose',
            # Small Target
            # 'input11_small_target': 'Target size < 3 cm'
        },
        datatype={
            'input07_vary_dose_grid': 'check',
            'input01_fluence_only': 'check',
            'input02_cold_start': 'check',
            'input09_segment_weight': 'check',
            'input10_reduce_oar': 'check',
            # 'input11_small_target': 'check'
        },
        initial={'input03_cold_max_iteration': '50',
                 'input04_cold_interm_iteration': '10',
                 'input05_ws_max_iteration': '35',
                 'input06_ws_interm_iteration': '5',
                 'input08_n_iterations': '4',
                 'input09_segment_weight': ['Perform Segment Weighted optimization'],
                 'input10_reduce_oar': ['Perform reduce OAR dose before completion'],
                 # Small Target
                 # 'input11_small_target': ['Target size < 3 cm - limit jaws']
                 },
        options={
            'input01_fluence_only': ['Fluence calc'],
            'input02_cold_start': ['Reset Beams'],
            'input07_vary_dose_grid': ['Variable Dose Grid'],
            'input09_segment_weight': ['Perform Segment Weighted optimization'],
            'input10_reduce_oar': ['Perform reduce OAR dose before completion'],
            # Small Target
            # 'input11_small_target': ['Target size < 3 cm - limit jaws']
        },
        required=[])
    optimization_dialog.show()

    # DATA PARSING FOR THE OPTIMIZATION MENU
    # Determine if variable dose grid is selected
    try:
        if 'Variable Dose Grid' in optimization_dialog.values['input07_vary_dose_grid']:
            vary_dose_grid = True
        else:
            vary_dose_grid = False
    except KeyError:
        vary_dose_grid = False

    # SVD to DAO calc for cold start (first optimization)
    try:
        if 'Fluence calc' in optimization_dialog.values['input01_fluence_only']:
            fluence_only = True
        else:
            fluence_only = False
    except KeyError:
        fluence_only = False

    # Despite a calculated beam, reset and start over
    try:
        if 'Reset Beams' in optimization_dialog.values['input02_cold_start']:
            reset_beams = True
        else:
            reset_beams = False
    except KeyError:
        reset_beams = False

    # Perform a segment weight optimization after the aperture optimization
    try:
        if 'Perform Segment Weighted optimization' in optimization_dialog.values['input09_segment_weight']:
            segment_weight = True
        else:
            segment_weight = False
    except KeyError:
        segment_weight = False

    # Despite a calculated beam, reset and start over
    try:
        if 'Perform reduce OAR dose before completion' in optimization_dialog.values['input10_reduce_oar']:
            reduce_oar = True
        else:
            reduce_oar = False
    except KeyError:
        reduce_oar = False
    # Despite a calculated beam, reset and start over
    # Small Target
    # try:
    #     if 'Target size < 3 cm - limit jaws' in optimization_dialog.values['input11_small_target']:
    #         small_target = True
    #     else:
    #         small_target = False
    # except KeyError:
    #     small_target = False
    optimization_inputs = {
        'initial_max_it': int(optimization_dialog.values['input03_cold_max_iteration']),
        'initial_int_it': int(optimization_dialog.values['input04_cold_interm_iteration']),
        'second_max_it': int(optimization_dialog.values['input05_ws_max_iteration']),
        'second_int_it': int(optimization_dialog.values['input06_ws_interm_iteration']),
        'vary_grid': vary_dose_grid,
        'dose_dim1': 0.5,
        'dose_dim2': 0.4,
        'dose_dim3': 0.3,
        'dose_dim4': 0.2,
        'fluence_only': fluence_only,
        'reset_beams': reset_beams,
        'segment_weight': segment_weight,
        'reduce_oar': reduce_oar,
        'save': True,
        # Small Target
        # 'small_target': small_target,
        'n_iterations': int(optimization_dialog.values['input08_n_iterations'])}

    OptimizationOperations.optimize_plan(patient=Patient,
                                         case=case,
                                         exam=exam,
                                         plan=plan,
                                         beamset=beamset,
                                         **optimization_inputs)


if __name__ == '__main__':
    main()
