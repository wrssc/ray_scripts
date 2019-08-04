""" Final Dose

    Currently this simply is a wrapper for the rename_beams function. In future versions
    gantry angles, collimator angles, and couch angles may be slightly rounded to create
    an exact match to ARIA.

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

__version__ = '1.0.4'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2018-Sep-05'
__raystation__ = '7.0.0.19'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import BeamOperations
import connect


def main():
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    try:
        patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        exam = connect.get_current("Examination")
    except SystemError:
        raise IOError("No examination loaded. Load patient ct and plan.")

    try:
        plan = connect.get_current("Plan")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    BeamOperations.rename_beams()
    BeamOperations.set_dsp(plan=plan, beam_set=beamset)


if __name__ == '__main__':
    main()