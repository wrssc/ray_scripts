""" Rename Beams In Current Beam Set

    Currently this simply is a wrapper for the rename_beams function. In future versions
    gantry angles, collimator angles, and couch angles may be slightly rounded to create
    an exact match to ARIA.

    Validation:
    10A: Test Patient: MR# ZZUWQA_ScTest_17Jan2021
                  Name: Script_Testing^RenameBeams
    11B: Test Patient: MR# ZZUWQA_ScTest_10Jun2022_11B_RenameBeams
                  Name: Script_Testing^RenameBeams

    

    Version History:
    1.0.4 Released
    1.1.0 Updated and validated in 10A SP1
    1.1.1 Updated and validated in 11B

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
__date__ = '2018-09-05'

__version__ = '1.1.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2022-Jun-27'
__raystation__ = '11B'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'

import BeamOperations


def main():
    BeamOperations.rename_beams()


if __name__ == '__main__':
    main()