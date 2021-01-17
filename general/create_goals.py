""" Create Clinical Goals and Objectives

    Add clinical goals and objectives in RayStation given user supplied inputs
    At this time, we are looking in the UW protocols directory for a
    list of approved protocols

    We may want to extend this main function to a simple function which would potentially
    take the path as an argument.

    Script will ask user for a protocol and potentially an order.  It will then find the
    doses that are to be used. If protocol defined doses exist and matches are found to
    target names it will load those first.

    Inputs::
        None at this time

    Dependencies::
        Note that protocols are assumed to have even priorities describing targets
    
    Validation Notes:
    Test Patient: MR# ZZUWQA_ScTest_05Jan2020, Name: Script_testing^Planning Structures Clinical Goals and Objectives
    -Anal_THI - sets clinical goals and objectives for AnoRectal-TPO

    TODO: Change the main to a callable function taking the protocol path as an input`
    TODO: Add goal loop for secondary - unspecified target goals
    :versions
    1.0.0 initial release supporting HN, Prostate, and lung (non-SBRT)
    1.0.1 supporting SBRT, brain, and knowledge-based goals for RTOG-SBRT Lung
    2.0.0 Adding the clinical objectives for IMRT
    2.1.0 Python 3.6 conversion and update to RS 10A SP1 and converted to use the
          new create_goals_and_objectives function

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '2.1.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import logging
import Objectives
import GeneralOperations


def main():

    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')
    ui = GeneralOperations.find_scope(level='ui')
    # TODO put in more sophisticated InvalidOperationException Catch here.
    try:
        ui.TitleBar.MenuItem['Plan Optimization'].Button_Plan_Optimization.Click()
    except:
        logging.debug('Unable to change viewing windows')

    error_message = Objectives.add_goals_and_objectives_from_protocol(
        case=case, plan=plan, beamset=beamset, exam=exam
    )
    if not error_message:
        logging.info('Clinical goals/objectives added successfully')
    else:
        output_message =''
        for e in error_message:
            output_message.append('{} '.format(e))
        logging.warning('Error adding clinical goals. {}'.format(output_message))



if __name__ == '__main__':
    main()
