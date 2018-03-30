""" AutoPlan_HN_Curative
    
    Automatic generation of a curative Head and Neck Plan.  
    -Loads planning structures
    -Loads Beams (or templates)
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons

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
__date__ = '2018-Mar-28'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '6.0.0'
__maintainer__ = 'One maintainer'
__email__ =  'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

from connect import *

from CreatePrvs import CreatePrvs

# Execute the PRV Creation
# Note the numbers below are uniform expansions in cm
case = get_current("Case")
examination = get_current("Examination")
HNPRVs = {
    "BrainStem"        : 0.3, 
    "BrachialPlexus_R" : 0.5,
    "BrachialPlexus_L" : 0.5,
    "Chiasm"           : 0.3,
    "Cochlea_R"        : 0.5,
    "Cochlea_L"        : 0.5,
    "Esophagus"        : 0.5,
    "Lens_R"           : 0.5,
    "Lens_L"           : 0.5,
    "OpticNerve_R"     : 0.3,
    "OpticNerve_L"     : 0.3,
    "SpinalCord"       : 0.5
         }

CreatePrvs(case, examination, **HNPRVs)
# Prompt the user for the target doses
