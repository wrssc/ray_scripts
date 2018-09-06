""" Generate Planning Structures

    Raystation script to make structures used for planning.
    Note:

    Inputs:

    Usage:


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
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import connect
import logging
import UserInterface


def MakeBooleanStructure(patient, case, examination, **kwargs):
    StructureName = kwargs.get("StructureName")
    ExcludeFromExport = kwargs.get("ExcludeFromExport")
    VisualizeStructure = kwargs.get("VisualizeStructure")
    StructColor = kwargs.get("StructColor")
    SourcesA = kwargs.get("SourcesA")
    MarginTypeA = kwargs.get("MarginTypeA")
    ExpA = kwargs.get("ExpA")
    OperationA = kwargs.get("OperationA")
    SourcesB = kwargs.get("SourcesB")
    MarginTypeB = kwargs.get("MarginTypeB")
    ExpB = kwargs.get("ExpB")
    OperationB = kwargs.get("OperationB")
    MarginTypeR = kwargs.get("MarginTypeR")
    ExpR = kwargs.get("ExpR")
    OperationResult = kwargs.get("OperationResult")
    StructType = kwargs.get("StructType")
    try:
        case.PatientModel.RegionsOfInterest[StructureName]
        logging.warning("Structure " + StructureName + " exists.  This will be overwritten in this examination")
    except:
        case.PatientModel.CreateRoi(Name=StructureName,
                                    Color=StructColor,
                                    Type=StructType,
                                    TissueName=None,
                                    RbeCellTypeName=None,
                                    RoiMaterial=None)

    case.PatientModel.RegionsOfInterest[StructureName].SetAlgebraExpression(
        ExpressionA={'Operation': OperationA, 'SourceRoiNames': SourcesA,
                     'MarginSettings': {'Type': MarginTypeA,
                                        'Superior': ExpA[0],
                                        'Inferior': ExpA[1],
                                        'Anterior': ExpA[2],
                                        'Posterior': ExpA[3],
                                        'Right': ExpA[4],
                                        'Left': ExpA[5]
                                        }},
        ExpressionB={'Operation': OperationB, 'SourceRoiNames': SourcesB,
                     'MarginSettings': {'Type': MarginTypeB,
                                        'Superior': ExpB[0],
                                        'Inferior': ExpB[0],
                                        'Anterior': ExpB[2],
                                        'Posterior': ExpB[3],
                                        'Right': ExpB[4],
                                        'Left': ExpB[5]}},
        ResultOperation=OperationResult,
        ResultMarginSettings={'Type': MarginTypeR,
                              'Superior': ExpR[0],
                              'Inferior': ExpR[1],
                              'Anterior': ExpR[2],
                              'Posterior': ExpR[3],
                              'Right': ExpR[4],
                              'Left': ExpR[5]})
    case.PatientModel.RegionsOfInterest[StructureName].ExcludeFromExport = ExcludeFromExport
    case.PatientModel.RegionsOfInterest[StructureName].UpdateDerivedGeometry(
        Examination=examination, Algorithm="Auto")


def main():
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
    except:
        logging.warning("Aww crap, No patient")

    # Underdosed Strucutures
    # Replace with a user prompt that suggests
    UnderStruct = ["Esophagus", "OpticNerve_L", "OpticNerve_R", "SpinalCord", "BrainStem"]
    # Uniform dose Structures
    # Replace with a user prompt that suggest
    UniformStruct = ["Mandible", "Lips", "ConstrMuscle", "Larynx"]

    # Commonly underdoses structures
    UnderStructureChoices = [
        'Aorta',
        'BrachialPlexus_L',
        'BrachialPlexus_L_PRV05',
        'BrachialPlexus_R',
        'BrachialPlexus_R_PRV05',
        'BrainStem',
        'CaudaEquina',
        'Chiasm',
        'Cochlea_L',
        'Cochlea_R',
        'Duodenum',
        'Esophagus',
        'SmallBowel',
        'Heart',
        'LargeBowel',
        'Lens_R',
        'Lens_L',
        'Rectum',
        'Genitalia',
        'Globe_L',
        'Globe_R',
        'Hippocampus_L',
        'Hippocampus_L_PRV05',
        'Hippocampus_R',
        'Hippocampus_R_PRV05',
        'IliacCrest_L',
        'IliacCrest_R',
        'PulmonaryTrunk',
        'SpinalCord',
        'SpinalCord_PRV02',
        'OpticNerve_L',
        'OpticNerve_R',
        'ProxBronchialTree',
        'Trachea',
        ]
    # Common uniformly dosed areas
    UniformStructureChoices = [
        'Aorta_PRV05'
        'BrainStem_PRV03',
        'Bladder',
        'CaudaEquina_PRV05',
        'Chiasm_PRV03',
        'Cochlea_L_PRV05',
        'Cochlea_R_PRV05',
        'ConstrMuscle',
        'Esophagus_PRV05',
        'Duodenum_PRV05',
        'Mandible',
        'LargeBowel',
        'Larynx',
        'Lens_L_PRV05',
        'Lens_R_PRV05',
        'Lips',
        'PeritonealCavity',
        'ProxBronchialTree_PRV05',
        'PulmonaryTrunk_PRV05',
        'OpticNerve_L_PRV03',
        'OpticNerve_R_PRV03',
        'Rectum',
        'SmallBowel',
        'SpinalCord_PRV05',
        'Stomach',
        'Trachea',
        'Vulva',
        ]

    # Find all the target names and generate the potential dropdown list for the cases
    # Use the above list for Uniform Structure Choices and Underdose choices, then
    # autoassign to the potential dropdowns
    if case is not None:
        TargetMatches = []
        UniformMatches = []
        UnderMatches = []
        AllOars = []
        for r in case.PatientModel.RegionsOfInterest:
            if r.Type == 'Ptv':
                TargetMatches.append(r.Name)
            if r.Type == 'Organ' or r.Type == 'Avoidance':
                AllOars.append(r.Name)
            if r.Name in UniformStructureChoices:
                UniformMatches.append(r.Name)
            if r.Name in UnderStructureChoices:
                UnderMatches.append(r.Name)
    StructureDialog = UserInterface.PSInputDialog(inputs={
                                               'A_PTV1': 'Select 1st Target Source',
                                               'A_PTV1Dose': 'Enter 1st Target Dose in cGy',
                                               'A_PTV2': 'Select 2nd Target Source',
                                               'A_PTV2Dose': 'Enter 2nd Target Dose in cGy',
                                               'A_PTV3': 'Select 3rd Target Source',
                                               'A_PTV3Dose': 'Enter 3rd Target Dose in cGy',
                                               'A_PTV4': 'Select 4th Target Source',
                                               'A_PTV4Dose': 'Enter 4th Target Dose in cGy',
                                               'A_PTV5': 'Select 5th Target Source',
                                               'A_PTV5Dose': 'Enter 5th Target Dose in cGy',
                                               'A_Under1': 'Select UnderDose Structures',
                                               'A_Under2': 'Select Unlisted UnderDose OAR',
                                               'A_Under3': 'Select Unlisted UnderDose OAR',
                                               'A_Uniform1': 'Select UniformDose Structures',
                                               'A_Uniform2': 'Select UniformDose OAR',
                                               'A_Uniform3': 'Select UniformDose OAR',
                                               'B_SkinContraction': 'Enter Skin Contraction in mm',
                                               'B_OTVStandoff': 'Enter Optimization Target Standoff in mm',
                                               'B_RingStandoff': 'Enter Ring Standoff in mm',
                                               'B_UnderStandoff': 'Enter Underdose Standoff in mm',
                                               'B_b': 'Select checkboxes:',
                                               'B_c': 'Select combobox option:'},
                                       datatype={'A_PTV1': 'combo',
                                                 'A_PTV2': 'combo',
                                                 'A_PTV3': 'combo',
                                                 'A_PTV4': 'combo',
                                                 'A_PTV5': 'combo',
                                                 'A_Uniform1': 'check',
                                                 'A_Uniform2': 'combo',
                                                 'A_Uniform3': 'combo',
                                                 'A_Under1': 'check',
                                                 'A_Under2': 'combo',
                                                 'A_Under3': 'combo', 
                                                 'B_b': 'check', 'B_c': 'combo'},
                                       initial={'A_PTV1': 'PTV1',
                                                'A_PTV1Dose': '0',
                                                'A_PTV2': 'PTV1',
                                                'A_PTV2Dose': '0',
                                                'A_PTV3': 'PTV1',
                                                'A_PTV3Dose': '0',
                                                'A_PTV4': 'PTV4',
                                                'A_PTV4Dose': '0',
                                                'A_PTV5': 'PTV5',
                                                'A_PTV5Dose': '0',
                                                'B_SkinContraction': '0.5',
                                                'B_OTVStandoff': '0.3',
                                                'B_RingStandoff': '0.2',
                                                'B_UnderStandoff': '0.4',
                                                'B_b': ['Target-Specific Rings'],
                                                'B_c': 'c'},
                                       options={'A_PTV1': TargetMatches,
                                                'A_PTV2': TargetMatches,
                                                'A_PTV3': TargetMatches,
                                                'A_PTV4': TargetMatches,
                                                'A_PTV5': TargetMatches,
                                                'A_Uniform1': UniformMatches,
                                                'A_Uniform2': AllOars,
                                                'A_Uniform3': AllOars,
                                                'A_Under1': UnderMatches,
                                                'A_Under2': AllOars,
                                                'A_Under3': AllOars,
                                                'B_b': UnderMatches,
                                                'B_c': UnderMatches},
                                       required=['A_PTV1', 'B_b', 'B_c'])
    ##
    # Stand off inputs
    # cm gap between higher dose targets (used for OTV volumes)
    OTVStandoff = 0.3
    # cm Expansion between targets and rings
    RingStandoff = 0.2
    ThickHDRing = 1.5
    ThickLDRing = 7.0
    # Compute UnderDose Standoff
    UnderDoseStandoff = 0.4
    print StructureDialog.show()
    # Find all the structures in the current case
    print "The resulting input values are PTV1(Name) {0}".format(StructureDialog.values['A_PTV1'])
    SkinContraction = StructureDialog.values['B_SkinContraction']

    # User-specified targets
    SourceList = ["PTV_72", "PTV_70", "PTV_64", "PTV_60", "PTV_54"]
    # List of PTVs to be used
    GeneratePTVs = True
    GeneratePTVEvals = True
    GenerateOTVs = True
    GenerateSkin = True
    GenerateInnerAir = True
    GenerateUnderDose = True
    GenerateUniformDose = True
    GenerateRingHD = True
    GenerateRingLD = True
    GenerateNormal_2cm = True
    GenerateTargetRings = True
    GenerateTargetSkin = True

    PTVPrefix = "PTV_"
    PTVEvalPrefix = "PTV_Eval_"
    OTVPrefix = "OTV_"
    for index, Target in enumerate(SourceList):
        NumMids = len(SourceList) - 2
        if index == 0:
            PTVName = PTVPrefix + "High"
            PTVList = [PTVName]
            PTVEvalName = PTVEvalPrefix + "High"
            PTVEvalList = [PTVEvalName]
            OTVName = OTVPrefix + "High"
            OTVList = [OTVName]
        elif index == len(SourceList) - 1:
            PTVName = PTVPrefix + "Low"
            PTVList.append(PTVName)
            PTVEvalName = PTVEvalPrefix + "Low"
            PTVEvalList.append(PTVEvalName)
            OTVName = OTVPrefix + "Low"
            OTVList.append(OTVName)
        else:
            MidTargetNumber = index - 1
            PTVName = PTVPrefix + "Mid" + str(MidTargetNumber)
            PTVList.append(PTVName)
            PTVEvalName = PTVEvalPrefix + "Mid" + str(MidTargetNumber)
            PTVEvalList.append(PTVEvalName)
            OTVName = OTVPrefix + "Mid" + str(MidTargetNumber)
            OTVList.append(OTVName)
    TargetColors = ["Red", "Green", "Blue", "Yellow", "Orange", "Purple"]
    # Contraction in cm to be used in the definition of the skin contour
    SkinContraction = 0.5
    ##
    # Stand off inputs
    # cm gap between higher dose targets (used for OTV volumes)
    OTVStandoff = 0.3
    # cm Expansion between targets and rings
    RingStandoff = 0.2
    ThickHDRing = 1.5
    ThickLDRing = 7.0
    # Compute UnderDose Standoff
    UnderDoseStandoff = 0.4
    ##
    # InnerAir Parameters
    # Upper Bound on the air volume to be removed from target coverage considerations
    InnerAirHU = -900



if __name__ == '__main__':
    main()
















