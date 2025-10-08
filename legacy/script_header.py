""" Script Title Goes Here

    A paragraph that describes what the script does. It will be displayed helper
    * Loads the ScriptStatus
    * Initializes a report for the script
    * Gets the current patient, case, patient database, and exam
    * User selects autoplan site
    * Selects a treatment planning order from supported list in protocols/UW/Autoplans
    * Prompts the user to set any overrides required for the plan

    Script:
    -Prompts user for protocol and order
    -Loads them from the autoplanning directory
    -Loads planning structures
    -Loads Beams
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons
    -Handle overrides
    Examination and Case must exist up front

    Testing mode:
    input_params is not None
    Bypasses user dialogs based on an input dictionary in input_params.
    Steps bypassed:


    TODO:
    -Return the result of each of the above steps as success or failure. Write result to
     log and to status
    -Output the objective value/plan params to a file for parsing
    -Add timing measurements
    TODO: Add a single pysimple gui for this whole program.
    TODO: Add SRS specific planning structure strategy


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
__date__ = '2021-Mar-03'
__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
__credits__ = ['']
__help__ = 'TODO: No Help'

# GUI here of invalidated code