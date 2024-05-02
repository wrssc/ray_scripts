""" General Operations
    GeneralOperations is a set of functions that operate on the patient and API level
    within RayStation.

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2024-04-22"

__version__ = "1.0.1"
__status__ = "Production"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"

__reviewed__ = ""
__raystation__ = "2024A"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__copyright__ = "Copyright (C) 2024, University of Wisconsin Board of Regents"

import logging
import connect
from api.api_utils import detect_api_version, find_scope


class InvalidDataException(Exception):
    pass


def logcrit(message):
    # Determine deepest scope
    current_scope = find_scope()
    level = ""

    # Construct the log message with '|' separator
    rs_version, rs_subversion = detect_api_version()
    if rs_version < 12:
        if current_scope["Case"] is not None:
            level += "Case: " + current_scope["Case"].CaseName + " | "
        if current_scope["Examination"] is not None:
            level += "Exam: " + current_scope["Examination"].Name + " | "
        if current_scope["Plan"] is not None:
            level += f"Plan: {current_scope['Plan'].Name} | PlanId: {current_scope['Plan'].UniqueId} | "
        if current_scope["BeamSet"] is not None:
            level += f"Beamset: {current_scope['BeamSet'].DicomPlanLabel} | BeamsetId: {current_scope['BeamSet'].UniqueId} | "
    elif rs_version > 12:
        if current_scope["Case"] is not None:
            level += "Case: " + current_scope["Case"].CaseName + " | "
        if current_scope["Examination"] is not None:
            level += "Exam: " + current_scope["Examination"].Name + " | "
        if current_scope["Plan"] is not None:
            level += f"Plan: {current_scope['Plan'].Name} | "
        if current_scope["BeamSet"] is not None:
            level += f"Beamset: {current_scope['BeamSet'].DicomPlanLabel} | "

    # Append the actual message to the log level information
    message = level + message

    # Log the message at critical level
    logging.critical(message)
