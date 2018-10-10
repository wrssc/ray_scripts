""" CreatePrvs.py
    
    This script will create all PRV's for the structure names that are passed to 
    it.  The argument to the function call herein defined as CreatePrvs takes the 
    form of a dict object with an expansion parameter specified in centimeters.  
    
    Scope: Requires RayStation "Case" and "Examination" to be loaded.  They are 
           passed to the function as an argument

    Example Usage:
    import CreatePrvs
    HNPRVs = {"BrainStem":0.3,"BrachialPlexus_R":0.5}
    Create_Prvs(case, examination, **HNPRVs)
       

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
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import connect
import sys
import logging
import xml.etree.Elementtree


def CreatePrvs(case, examination, check_all, **kwargs):
    Colors = {
        "BrainStem": "127, 255, 212",
        "BrachialPlexus_R": "255,   0, 255",
        "BrachialPlexus_L": "255,   0, 255",
        "BronchialTree_R": "162, 205,  90",
        "BronchialTree_L": "162, 205,  90",
        "CaudaEquina": "  0, 100,   0",
        "Chiasm": "34,  139,  34",
        "Cochlea_R": "173, 216, 230",
        "Cochlea_L": "173, 216, 230",
        "Duodenum": "  0, 100,   0",
        "Esophagus": " 70,  30, 180",
        "Kidney_R": "138,  43, 226",
        "Kidney_L": "138,  43, 226",
        "Lens_R": "205, 133,   0",
        "Lens_L": "205, 133,   0",
        "OpticNerve_R": "250, 128, 114",
        "OpticNerve_L": "250, 128, 114",
        "SpinalCord": "  0, 100,   0"
    }

    if check_all:
        protocol_folder = r'../../protocols/UW_Approved'
        file_name = 'UW_prvs_and_logical.xml'

        tree = xml.etree.ElementTree.parse(os.path.join(protocol_folder, file_name))
        for s in tree.findall('//planning_structures/derived_roi'):
            print 'Adding derived struct'
            print s
    else:
        for key in kwargs:
            # dict key is the source name from the function call
            SourceName = str(key)
            # Expansion (in cm) is the value from the input dict
            Exp = kwargs[key]
            # Make a string out of the Exp (noting we are looking for "0.3"
            StrExp = str(Exp)
            # Format the PRV name, note that I have assumed a mm number here
            # for example, Exp = 0.3 -> '03'
            PRVName = SourceName + '_PRV' + StrExp.replace('.', '')
            # If one isn't found, I am not sure what this error message will do below in the colors list
            Color = Colors.get(SourceName, "Error no matching structure found in the Color list for PRVs")
            # All PRV's hardcoded as type avoidance
            Type = "Avoidance"
            # Define a uniform expansion dictionary for the SetMarginExpression function
            ExpDict = {'Type': "Expand", 'Superior': Exp, 'Inferior': Exp, 'Anterior': Exp, 'Posterior': Exp, 'Right': Exp,
                       'Left': Exp}
            try:
                if case.PatientModel.RegionsOfInterest[SourceName]:
                    # Look to see if this structure exists.  If so delete it and update to derived
                    try:
                        case.PatientModel.RegionsOfInterest[PRVName]
                        retval_0 = case.PatientModel.RegionsOfInterest[PRVName].DeleteRoi()
                        retval_0 = case.PatientModel.CreateRoi(Name=PRVName, Color=Color, Type=Type, TissueName=None,
                                                               RbeCellTypeName=None, RoiMaterial=None)
                    except:
                        retval_0 = case.PatientModel.CreateRoi(Name=PRVName, Color=Color, Type=Type, TissueName=None,
                                                               RbeCellTypeName=None, RoiMaterial=None)
                    # Expand the PRV from the source and update the geometry
                    retval_0.SetMarginExpression(SourceRoiName=SourceName, MarginSettings=ExpDict)
                    retval_0.UpdateDerivedGeometry(Examination=examination, Algorithm="Auto")
            except:
                logging.warning(
                    "No PRV Generated for Structure: " + SourceName +
                    ".  It was not found in the Regions of Interest list.")
