""" Generate Planning Structures

    This script is designed to help you make planning structures.  Prior to starting you should determine:
    All structures to be treated, and their doses
    All structures with priority 1 goals (they are going to be selected for UnderDose)
    All structures where hot-spots are undesirable but underdosing is not desired.  They will be placed in
    the UniformDose ROI.


    Raystation script to make structures used for planning.

    Note:
    Using the Standard InputDialog
    We have several calls
    The first will determine the target doses and whether we are uniform or underdosing
         Based on those responses:
         Select and Approve underdose selections
         Select and Approve uniform dose selections
    The second non-optional call prompts the user to use:
        -Target-specific rings
        -Specify desired standoffs in the rings closest to the target

    Inputs:
        None, though eventually the common uniform and underdose should be dumped into xml files
        and stored in protocols

    Usage:

    Version History:
    1.0.1: Hot fix to repair inconsistency when underdose is not used but uniform dose is.
    1.0.2: Adding "inner air" as an optional feature
    1.0.3 Hot fix to repair error in definition of sOTVu: Currently taking union of PTV and
            not_OTV - should be intersection.
    1.0.4 Bug fix for upgrade to RS 8 - replaced the toggling of the exclude from export with
            the required method.
    1.0.4b Save the user mapping for this structure set as an xml file to be loaded by create_goals
    1.0.5 Exclude InnerAir and FOV from Export, add IGRT Alignment Structure
    1.0.6 Added the Normal_1cm structure to the list


    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""
from pickle import FALSE

# from typing import List, Any

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.0.5'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import StructureOperations


def main():
    StructureOperations.planning_structures()


if __name__ == '__main__':
    main()
