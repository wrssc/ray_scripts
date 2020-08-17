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

    TODO: Change the main to a callable function taking the protocol path as an input`
    TODO: Add goal loop for secondary - unspecified target goals
    :versions
    1.0.0 initial release supporting HN, Prostate, and lung (non-SBRT)
    1.0.1 supporting SBRT, brain, and knowledge-based goals for RTOG-SBRT Lung
    2.0.0 Adding the clinical objectives for IMRT

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '2.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import Objectives


def main():
    Objectives.add_goals_and_structures_from_protocol()



if __name__ == '__main__':
    main()
