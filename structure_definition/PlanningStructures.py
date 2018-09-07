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
        'Aorta_PRV05',
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
    TargetMatches = []
    UniformMatches = []
    UnderMatches = []
    AllOars = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'Ptv':
            TargetMatches.append(r.Name)
        if r.Name in UniformStructureChoices:
            UniformMatches.append(r.Name)
        if r.Name in UnderStructureChoices:
            UnderMatches.append(r.Name)
        if r.OrganData.OrganType == 'OrganAtRisk':
            AllOars.append(r.Name)
    # Using the Standard InputDialog
    # We want several calls.  The first will determine the target doses and
    # 1. Do you want Underdose, Uniform Dose, Target-specific rings
    # Based on those responses:
    # Approve underdose selections
    # Approve uniform dose selections
    InitialDialog = UserInterface.InputDialog(
        inputs={
            'PTV1': 'Select 1st Target Source',
            'PTV1Dose': 'Enter 1st Target Dose in cGy',
            'PTV2': 'Select 2nd Target Source',
            'PTV2Dose': 'Enter 2nd Target Dose in cGy',
            'PTV3': 'Select 3rd Target Source',
            'PTV3Dose': 'Enter 3rd Target Dose in cGy',
            'PTV4': 'Select 4th Target Source',
            'PTV4Dose': 'Enter 4th Target Dose in cGy',
            'PTV5': 'Select 5th Target Source',
            'PTV5Dose': 'Enter 5th Target Dose in cGy',
            'UnderDose': 'Priority 1 goals present: Use Underdosing',
            'UniformDose': 'Targets overlap sensitive structures: Use UniformDoses',
        },
        text='Target selection',
        title='Initial Screen',
        datatype={'PTV1': 'combo',
                  'PTV2': 'combo',
                  'PTV3': 'combo',
                  'PTV4': 'combo',
                  'PTV5': 'combo',
                  'UniformDose': 'check',
                  'UnderDose': 'check',
                  },
        initial={
                 'PTV1Dose': '0',
                 'PTV2Dose': '0',
                 'PTV3Dose': '0',
                 'PTV4Dose': '0',
                 'PTV5Dose': '0',
                 },
        options={'PTV1': TargetMatches,
                 'PTV2': TargetMatches,
                 'PTV3': TargetMatches,
                 'PTV4': TargetMatches,
                 'PTV5': TargetMatches,
                 'UniformDose': ['yes'],
                 'UnderDose': ['yes']
                 },
        required=['PTV1'])
    print InitialDialog.show()

    # Parse the output from InitialDialog
    SourceList = []
    source_doses = []
    if 'PTV1' in InitialDialog.values:
        SourceList.append(InitialDialog.values['PTV1'])
        source_doses.append(InitialDialog.values['PTV1Dose'])

    if 'PTV2' in InitialDialog.values:
        SourceList.append(InitialDialog.values['PTV2'])
        source_doses.append(InitialDialog.values['PTV2Dose'])

    if 'PTV3' in InitialDialog.values:
        SourceList.append(InitialDialog.values['PTV3'])
        source_doses.append(InitialDialog.values['PTV3Dose'])

    if 'PTV4' in InitialDialog.values:
        SourceList.append(InitialDialog.values['PTV4'])
        source_doses.append(InitialDialog.values['PTV4Dose'])

    if 'PTV5' in InitialDialog.values:
        SourceList.append(InitialDialog.values['PTV5'])
        source_doses.append(InitialDialog.values['PTV5Dose'])

    # User selected that Uniformdose is required
    if 'yes' in InitialDialog.values['UniformDose']:
        GenerateUniformDose = True
    else:
        GenerateUniformDose= False

    # User selected that Underdose is required

    if 'yes' in InitialDialog.values['UnderDose']:
        GenerateUnderDose = True
    else:
        GenerateUnderDose= False

    # Rephrase the next statement with logging
    print 'Proceeding with target list: [%s]' % ', '.join(map(str, SourceList))
    print 'Proceeding with target doses: [%s]' % ', '.join(map(str, source_doses))
    print 'User selected {} for UnderDose'.format(GenerateUnderDose)
    print 'User selected {} for UniformDose'.format(GenerateUniformDose)

    if GenerateUniformDose:
        uniform_dose_dialog = UserInterface.InputDialog(
            inputs={
            'Uniform1': 'Select UniformDose Structures',
            'Uniform2': 'Select UniformDose OAR',
            'Uniform3': 'Select UniformDose OAR',
            },
            datatype={
                      'Uniform1': 'check',
                      'Uniform2': 'combo',
                      'Uniform3': 'combo',
                     },
            initial={},
            options={
                     'Uniform1': UniformMatches,
                     'Uniform2': AllOars,
                     'Uniform3': AllOars},
            required=[])
        print uniform_dose_dialog.show()
        uniform_structures = []
        if uniform_dose_dialog.values['Uniform1'] is not None:
            uniform_structures.append(uniform_dose_dialog.values['Uniform1'])
        if uniform_dose_dialog.values['Uniform2'] is not None:
            uniform_structures.append(uniform_dose_dialog.values['Uniform2'])
        if uniform_dose_dialog.values['Uniform3'] is not None:
            uniform_structures.append(uniform_dose_dialog.values['Uniform3'])
        for structs in uniform_structures: print structs

    # StructureDialog = UserInterface.InputDialog(inputs={
    #                                            'PTV1': 'Select 1st Target Source',
    #                                            'PTV1Dose': 'Enter 1st Target Dose in cGy',
    #                                            'PTV2': 'Select 2nd Target Source',
    #                                            'PTV2Dose': 'Enter 2nd Target Dose in cGy',
    #                                            'PTV3': 'Select 3rd Target Source',
    #                                            'PTV3Dose': 'Enter 3rd Target Dose in cGy',
    #                                            'PTV4': 'Select 4th Target Source',
    #                                            'PTV4Dose': 'Enter 4th Target Dose in cGy',
    #                                            'PTV5': 'Select 5th Target Source',
    #                                            'PTV5Dose': 'Enter 5th Target Dose in cGy',
    #                                            'UnderDose': 'UnderDosing:',
    #                                            'Under2': 'Select Unlisted UnderDose OAR',
    #                                            'Under3': 'Select Unlisted UnderDose OAR',
    #                                            'Uniform1': 'Select UniformDose Structures',
    #                                            'Uniform2': 'Select UniformDose OAR',
    #                                            'Uniform3': 'Select UniformDose OAR',
    #                                            'SkinContraction': 'Enter Skin Contraction in mm',
    #                                            'OTVStandoff': 'Enter Optimization Target Standoff in mm',
    #                                            'RingStandoff': 'Enter Ring Standoff in mm',
    #                                            'UnderStandoff': 'Enter Underdose Standoff in mm',
    #                                            'b': 'Select checkboxes:',
    #                                            'c': 'Select combobox option:'},
    #                                    datatype={'PTV1': 'combo',
    #                                              'PTV2': 'combo',
    #                                              'PTV3': 'combo',
    #                                              'PTV4': 'combo',
    #                                              'PTV5': 'combo',
    #                                              'Uniform1': 'check',
    #                                              'Uniform2': 'combo',
    #                                              'Uniform3': 'combo',
    #                                              'UnderDose': 'check',
    #                                              'Under2': 'combo',
    #                                              'Under3': 'combo',
    #                                              'b': 'check', 'c': 'combo'},
    #                                    initial={'PTV1': 'PTV1',
    #                                             'PTV1Dose': '0',
    #                                             'PTV2': 'PTV1',
    #                                             'PTV2Dose': '0',
    #                                             'PTV3': 'PTV1',
    #                                             'PTV3Dose': '0',
    #                                             'PTV4': 'PTV4',
    #                                             'PTV4Dose': '0',
    #                                             'PTV5': 'PTV5',
    #                                             'PTV5Dose': '0',
    #                                             'SkinContraction': '0.5',
    #                                             'OTVStandoff': '0.3',
    #                                             'RingStandoff': '0.2',
    #                                             'UnderStandoff': '0.4',
    #                                             'b': ['Target-Specific Rings'],
    #                                             'c': 'c'},
    #                                    options={'PTV1': TargetMatches,
    #                                             'PTV2': TargetMatches,
    #                                             'PTV3': TargetMatches,
    #                                             'PTV4': TargetMatches,
    #                                             'PTV5': TargetMatches,
    #                                             'Uniform1': UniformMatches,
    #                                             'Uniform2': AllOars,
    #                                             'Uniform3': AllOars,
    #                                             'UnderDose': ['Priority 1 goals present: Use Underdosing'],
    #                                             'Under2': AllOars,
    #                                             'Under3': AllOars,
    #                                             'b': UnderMatches,
    #                                             'c': UnderMatches},
    #                                    required=['PTV1', 'b', 'c'])
    # Stand off inputs
    # cm gap between higher dose targets (used for OTV volumes)
    OTVStandoff = 0.3
    # cm Expansion between targets and rings
    RingStandoff = 0.2
    ThickHDRing = 1.5
    ThickLDRing = 7.0
    # Compute UnderDose Standoff
    UnderDoseStandoff = 0.4
    # Find all the structures in the current case
    print "The resulting input values are PTV1(Name) {0}".format(StructureDialog.values['PTV1'])
    # SkinContraction = StructureDialog.values['B_SkinContraction']

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
