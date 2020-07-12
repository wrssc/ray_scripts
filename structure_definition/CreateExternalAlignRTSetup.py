""" Create Shifted External for Prone Breast
This script accomplishes the following tasks:
1. Creates a copy of the external contour called External_Ant150
2. Shifts External_Ant150 anteriorly 150 mm

This script was tested with:
* Patient: ZZ_OSMS, Practice
* MRN: 20180717DJJ
* RayStation: Launcher 8B SP2 - Test (Development Server)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

__author__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__date__ = "2020-07-10"
__version__ = "0.1.0"
__status__ = "Development"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"
__reviewed__ = None
__raystation__ = "8.0 SP B"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2020, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current
import logging
import numpy as np


def create_external_alignrt_su(case, shift_size=150):
    """ Creates External_AlignRT_SU.

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    shift_size: float
        The shift size, in mm, in the anterior direction

    RETURNS
    -------
    None

    """


def clean(case):
    """Undo all of the actions done by create_external_fb()

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    pass


def main():
    """The main function for this file"""

    logging.debug("Beginning execution of CreateExternalAlignRTSetup.py in main()")
    case = get_current("Case")
    create_external_alignrt_su(case)


if __name__ == "__main__":
    main()
