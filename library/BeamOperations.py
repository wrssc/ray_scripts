""" Perform beam operations on Raystation plans
    
    rename_beams:
    Automatically label beams in Raystation according to UW Standard

    Determines the primary site of the Beam set by prompting the user
    The user identifies the site using the 4 letter pre-fix from the plan name
    If the user supplies more than 4 chars, the name is cropped
    The script will test the orientation of the patient and rename the beams accordingly
    If the beamset contains a couch kick the beams are named using the gXXCyy convention
    
    Versions: 
    01.00.00 Original submission
    01.00.01 PH reviewed, suggested eliminating an unused variable, changing integer
             floating point comparison, and embedding set-up beam creation as a 
             "try" to prevent a script failure if set-up beams were not selected
    01.00.02 PH Reviewed, correct FFP positioning issue.  Changed Beamset failure to 
             load to read the same as other IO-Faults
    01.00.03 RAB Modified for new naming convention on plans and to add support for the
             field descriptions to be used for billing.
    01.00.04 RAB Modified to include isocenter renaming.
    01.00.05 RAB Modified to automatically add the 4th set-up field and clean up creation
    01.00.06 RAB Modified to round the gantry and couch angle first then convert to integer

    Known Issues:

    Multi-isocenter treatment will be incorrect in the naming conventions for set up
    fields. The script will rename the first four fields regardless of which isocenter
    to which they belong.

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


import math
import numpy as np
import logging
import sys
import clr
import connect
import UserInterface
import StructureOperations

clr.AddReference('System')


class Beam(object):

    def __init__(self):
        self.name = None
        self.iso = {}
        self.startangle = None
        self.stopangle = None
        self.couchangle = None
        self.energy = None
        self.dsp = None

    def __eq__(self, other):
        return other and self.iso == other.iso and self.startangle \
               == other.startangle and self.stopangle == other.stopangle \
               and self.energy == other.energy and self.dsp == other.dsp \
               and self.couchangle == other.couchangle

    def __hash__(self):
        return hash((
            frozenset(self.iso.items()),
            self.startangle,
            self.stopangle,
            self.energy,
            self.dsp,
            self.couchangle,
        ))


class DSP(object):

    def __init__(self):
        self.name = None
        self.coords = {}

    def __eq__(self, other):
        return other and self.coords == other.coords

    def __hash__(self):
        return hash(frozenset(self.coords.items()))


# Return a patient position in the expected format for beamset definition
def patient_position_map(exam_position):
    if exam_position == 'HFP':
        return 'HeadFirstProne'
    elif exam_position == 'HFS':
        return 'HeadFirstSupine'
    elif exam_position == 'FFP':
        return 'FeetFirstProne'
    elif exam_position == 'FFS':
        return 'FeetFirstSupine'
    elif exam_position == 'HFDL':
        return 'HeadFirstDecubitusLeft'
    elif exam_position == 'HFDR':
        return 'HeadFirstDecubitusRight'
    elif exam_position == 'FFDL':
        return 'FeetFirstDecubitusLeft'
    elif exam_position == 'FFDR':
        return 'FeetFirstDecubitusRight'


def create_beamset(patient, case, exam, plan, dialog=True):
    """ Create a beamset by opening a dialog with user or loading from scratch
    :TODO Load the available machine inputs from xml file
    :TODO Test gating option
    """
    available_modality = ['Photons', 'Electrons']
    available_technique = ['Conformal', 'SMLC', 'VMAT', 'DMLC', 'ConformalArc', 'TomoHelical', 'TomoDirect']
    if dialog:
        targets = StructureOperations.find_targets(case=case)

        # TODO: Find out from RS why the DB query is broken
        # machine_db = connect.get_current('MachineDB')
        # machines = machine_db.QueryCommissionedMachineInfo(Filter={})
        # machine_list = []
        # for i, m in enumerate(machines):
        #     if m['IsCommissioned']:
        #         machine_list.append(m['Name'])
        machine_list = ['TrueBeam', 'TrueBeamSTx']

        input_dialog = UserInterface.InputDialog(
            inputs={
                '0': 'Choose the Rx target',
                '1': 'Enter the Beamset Name, typically <Site>_VMA_R0A0',
                '2': 'Enter the number of fractions',
                '3': 'Enter total dose in cGy',
                '4': 'Choose Treatment Machine',
                '5': 'Choose a Modality',
                '6': 'Choose a Technique',
                '7': 'Choose a Target for Isocenter Placement'
            },
            title='Beamset Inputs',
            datatype={
                '0': 'combo',
                '4': 'combo',
                '5': 'combo',
                '6': 'combo',
                '7': 'combo'
            },
            initial={
                '1': 'XXXX_VMA_R0A0',
            },
            options={
                '0': targets,
                '4': machine_list,
                '5': available_modality,
                '6': available_technique,
                '7': targets
            },
            required=['0',
                      '2',
                      '3',
                      '4',
                      '5',
                      '6',
                      '7'])

        # Launch the dialog
        response = input_dialog.show()
        if response == {}:
            sys.exit('Beamset loading was cancelled')

        # Parse the outputs
        # User selected that they want a plan-stub made
        rx_target = input_dialog.values['0']
        plan_name = input_dialog.values['1']
        number_of_fractions = float(input_dialog.values['2'])
        total_dose = float(input_dialog.values['3'])
        plan_machine = input_dialog.values['4']
        modality = input_dialog.values['5']
        technique = input_dialog.values['6']
        isocenter_target = input_dialog.values['7']

    try:

        plan.AddNewBeamSet(
            Name=plan_name,
            ExaminationName=exam.Name,
            MachineName=plan_machine,
            Modality=modality,
            TreatmentTechnique=technique,
            PatientPosition=patient_position_map(exam.PatientPosition),
            NumberOfFractions=number_of_fractions,
            CreateSetupBeams=True,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment="",
            RbeModelReference=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[],
            RespiratoryMotionCompensationTechnique="Disabled",
            RespiratorySignalSource="Disabled")

    except Exception:
        logging.warning('Unable to Add Beamset')
        sys.exit('Unable to Add Beamset')

    beamset = plan.BeamSets[plan_name]
    patient.Save()

    try:

        beamset.AddDosePrescriptionToRoi(RoiName=rx_target,
                                         DoseVolume=80,
                                         PrescriptionType='DoseAtVolume',
                                         DoseValue=total_dose,
                                         RelativePrescriptionLevel=1,
                                         AutoScaleDose=True)
    except Exception:
        logging.warning('Unable to set prescription')

    try:
        isocenter_position = case.PatientModel.StructureSets[exam.Name]. \
        RoiGeometries[isocenter_target].GetCenterOfRoi()
    except Exception:
        logging.warning('Aborting, could not locate center of {}'.format(isocenter_target))
        sys.exit('Failed to place isocenter')

    # Place isocenter
    # TODO Add a check on laterality at this point (if -7< x < 7 ) put out a warning
    ptv_center = {'x': isocenter_position.x,
                          'y': isocenter_position.y,
                          'z': isocenter_position.z}
    isocenter_parameters = beamset.CreateDefaultIsocenterData(Position=ptv_center)
    isocenter_parameters['Name'] = "iso_" + plan_name
    isocenter_parameters['NameOfIsocenterToRef'] = "iso_" + plan_name
    logging.info('Isocenter chosen based on center of {}.' +
                 'Parameters are: x={}, y={}:, z={}, assigned to isocenter name{}'.format(
                     isocenter_target,
                     ptv_center['x'],
                     ptv_center['y'],
                     ptv_center['z'],
                     isocenter_parameters['Name']))

    beamset.CreatePhotonBeam(Energy=6,
                             IsocenterData=isocenter_parameters,
                             Name='1_Brai_g270c355',
                             Description='1 3DC: MLC Static Field',
                             GantryAngle=270.0,
                             CouchAngle=355,
                             CollimatorAngle=0)

    beamset.CreatePhotonBeam(Energy=6,
                             IsocenterData=isocenter_parameters,
                             Name='2_Brai_g090c005',
                             Description='2 3DC: MLC Static Field',
                             GantryAngle=90,
                             CouchAngle=5,
                             CollimatorAngle=0)

    return beamset


def rename_beams():

    # These are the techniques associated with billing codes in the clinic
    # they will be imported
    available_techniques = [
        'Static MLC -- 2D',
        'Static NoMLC -- 2D',
        'Electron -- 2D',
        'Static MLC -- 3D',
        'Static NoMLC -- 3D',
        'Electron -- 3D',
        'FiF MLC -- 3D',
        'Static PRDR MLC -- 3D',
        'SnS MLC -- IMRT',
        'SnS PRDR MLC -- IMRT',
        'Conformal Arc -- 2D',
        'Conformal Arc -- 3D',
        'VMAT Arc -- IMRT',
        'Tomo Helical -- IMRT']
    supported_rs_techniques = [
        'SMLC',
        'DynamicArc',
        'TomoHelical']


    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        plan = connect.get_current('Plan')
        beamset = connect.get_current("BeamSet")

    except Exception:
        UserInterface.WarningBox('This script requires a Beam Set to be loaded')
        sys.exit('This script requires a Beam Set to be loaded')

    initial_sitename = beamset.DicomPlanLabel[:4]
    # Prompt the user for Site Name and Billing technique
    dialog = UserInterface.InputDialog(inputs={'Site': 'Enter a Site name, e.g. BreL',
                                               'Technique': 'Select Treatment Technique (Billing)'},
                                       datatype={'Technique': 'combo'},
                                       initial={'Technique': 'Select',
                                                'Site': initial_sitename},
                                       options={'Technique': available_techniques},
                                       required=['Site', 'Technique'])
    # Show the dialog
    print dialog.show()

    site_name = dialog.values['Site']
    input_technique = dialog.values['Technique']
    #
    # Electrons, 3D, and VMAT Arcs are all that are supported.  Reject plans that aren't
    technique = beamset.DeliveryTechnique
    #
    # Oddly enough, Electrons are DeliveryTechnique = 'SMLC'
    if technique not in supported_rs_techniques:
        logging.warning('Technique: {} unsupported in renaming script'.format(technique))
        raise IOError("Technique unsupported, manually name beams according to clinical convention.")

    # Tomo Helical naming
    if technique == 'TomoHelical':
        for b in beamset.Beams:
            beam_description = 'TomoHelical' + site_name
            b.Name = beam_description
            b.Description = input_technique
        return

    # While loop variable definitions
    beam_index = 0
    patient_position = beamset.PatientPosition
    # Turn on set-up fields
    beamset.PatientSetup.UseSetupBeams = True
    logging.debug('Renaming and adding set up fields to Beam Set with name {}, patient position {}, technique {}'.
                  format(beamset.DicomPlanLabel, beamset.PatientPosition, beamset.DeliveryTechnique))
    # Rename isocenters
    for b in beamset.Beams:
        iso_n = int(b.Isocenter.IsocenterNumber)
        b.Isocenter.Annotation.Name = 'Iso_' + beamset.DicomPlanLabel + '_' + str(iso_n + 1)
    #
    # HFS
    if patient_position == 'HeadFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                # 
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

    # Set-Up Fields
        # HFS Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp AP', 'SetUp AP', 0.0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 270.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFLDR
    elif patient_position == 'HeadFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

    # Set-Up Fields
        # HFLDR Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp LtLat', 'SetUp LtLat', 0.0, '5'],
                  1: ['SetUp AP', 'SetUp AP', 270.0, '5'],
                  2: ['SetUp PA', 'SetUp PA', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFLDL
    elif patient_position == 'HeadFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # HFLDL Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp PA', 'SetUp PA', 270.0, '5'],
                  2: ['SetUp AP', 'SetUp AP', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # HFP
    elif patient_position == 'HeadFirstProne':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')
        #
        # Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp PA', 'SetUp PA', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 90.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 270.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFS
    elif patient_position == 'FeetFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occured in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp AP', 'SetUp AP', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 90.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 270.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]

            # Address the Feet-first prone position
    # FFLDR
    elif patient_position == 'FeetFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # FFLDR Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp PA', 'SetUp PA', 270.0, '5'],
                  2: ['SetUp AP', 'SetUp AP', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFLDL
    elif patient_position == 'FeetFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'

                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                logging.warning('Error occurred in setting names of beams')
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')

        # Set-Up Fields
        # FFLDL Setup
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp RtLat', 'SetUp RtLat', 0.0, '5'],
                  1: ['SetUp AP', 'SetUp AP', 270.0, '5'],
                  2: ['SetUp PA', 'SetUp PA', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
            print "v2={}".format(v[2])

        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        # Set the set-up parameter specifics
        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    # FFP
    elif patient_position == 'FeetFirstProne':
        for b in beamset.Beams:
            standard_beam_name = 'Naming Error'
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchAngle), 1)
                gantry_angle_string = str(int(gantry_angle))
                couch_angle_string = str(int(couch_angle))
                #
                # Determine if the type is an Arc or SMLC
                # Name arcs as #_Arc_<Site>_<Direction>_<Couch>
                if technique == 'DynamicArc':
                    arc_direction = b.ArcRotationDirection
                    if arc_direction == 'Clockwise':
                        arc_direction_string = 'CW'
                    else:
                        arc_direction_string = 'CCW'

                    # Based on convention for billing, e.g. "1 CCW VMAT -- IMRT"
                    # set the beam_description
                    beam_description = (str(beam_index + 1) + ' ' + arc_direction_string +
                                        ' ' + input_technique)
                    if couch_angle == 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc')
                    else:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name + '_Arc'
                                              + '_c' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 'c' + couch_angle_string.zfill(3))
                    elif gantry_angle == 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180 < gantry_angle < 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RAO'
                    elif gantry_angle == 270:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 270 < gantry_angle < 360:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RPO'
                    elif gantry_angle == 0:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 0 < gantry_angle < 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LPO'
                    elif gantry_angle == 90:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 90 < gantry_angle < 180:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LAO'
                # Set the beamset names and description according to the convention above
                b.Name = standard_beam_name
                b.Description = beam_description
                beam_index += 1
            except Exception:
                UserInterface.WarningBox('Error occurred in setting names of beams')
                sys.exit('Error occurred in setting names of beams')
        # FFP: Set-Up fields
        # set_up: [ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
        set_up = {0: ['SetUp PA', 'SetUp PA', 0, '5'],
                  1: ['SetUp RtLat', 'SetUp RtLat', 270.0, '5'],
                  2: ['SetUp LtLat', 'SetUp LtLat', 90.0, '5'],
                  3: ['SetUp CBCT', 'SetUp CBCT', 0.0, '5']
                  }
        # Extract the angles
        angles = []
        for k, v in set_up.iteritems():
            angles.append(v[2])
        beamset.UpdateSetupBeams(ResetSetupBeams=True,
                                 SetupBeamsGantryAngles=angles)

        for i, b in enumerate(beamset.PatientSetup.SetupBeams):
            b.Name = set_up[i][0]
            b.Description = set_up[i][1]
            b.GantryAngle = str(set_up[i][2])
            b.Segments[0].DoseRate = set_up[i][3]
    else:
        raise IOError("Patient Orientation Unsupported.. Manual Beam Naming Required")


def find_dsp(plan, beam_set, dose_per_fraction=None, Beam=None):
    """
    :param plan: current plan
    :param beam_set: current beamset
    :param dose_per_fraction: dose value to find in cGy
    :param Beam: None sets beams to sum to Beamset fractional dose_value
                 <str_Beam> creates unique DSP for each beam for each beam's maximum
    :return: a list of [x, y, z] coordinates on the dose grid
    """
    # Get the MU weights of each beam
    tot = 0.
    for b in beam_set.Beams:
        tot += b.BeamMU

    if Beam is None:
        # Search the fractional dose grid
        # The dose grid is stored by RS as a numpy array
        pd = beam_set.FractionDose.DoseValues.DoseData
    else:
        # Find the right beam
        beam_found = False
        for b in beam_set.FractionDose.BeamDoses:
            if b.ForBeam.Name == Beam:
                pd = b.DoseValues.DoseData
                beam_found = True
        if not beam_found:
            print('No beam match for name provided')

    # The dose grid is stored [z: I/S, y: P/A, x: R/L]
    pd_np = pd.swapaxes(0, 2)

    if dose_per_fraction is None:
        rx = np.amax(pd_np)
    else:
        rx = dose_per_fraction

    logging.debug('rx = '.format(rx))

    xpos = None
    tolerance = 5.0e-2
    # beam_set = get_current('BeamSet')
    # plan = connect.get_current('Plan')

    xmax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.x
    ymax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.y
    xcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.x
    ycorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.y
    zcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.z
    xsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.x
    ysize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.y
    zsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.z

    if np.amax(pd_np) < rx:
        print 'max = ', str(max(pd))
        print 'target = ', str(rx)
        raise ValueError('max beam dose is too low')

    # rx_points = np.empty((0, 3), dtype=np.int)
    rx_points = np.argwhere(abs(rx - pd_np) <= tolerance)
    print("Shape of rx_points {}".format(rx_points.shape))

    # for (x, y, z), value in np.ndenumerate(pd_np):
    #    if rx - tolerance < value < rx + tolerance:
    #        rx_points = np.append(rx_points, np.array([[x, y, z]]), axis=0)
    #        print('dose = {}'.format(value))
    #        xpos = x * xsize + xcorner + xsize/2
    #        ypos = y * ysize + ycorner + ysize/2
    #        zpos = z * zsize + zcorner + zsize/2
    #        print 'corner = {0}, {1}, {2}'.format(xcorner,ycorner,zcorner)
    #        print 'x, y, z = {0}, {1}, {2}'.format(x * xsize, y * ysize, z * zsize)
    #        print 'x, y, z positions = {0}, {1}, {2}'.format(xpos,ypos,zpos)
    #        # return [xpos, ypos, zpos]
    # break

    matches = np.empty(np.size(rx_points, 0))

    for b in beam_set.FractionDose.BeamDoses:
        pd = np.array(b.DoseValues.DoseData)
        # The dose grid is stored [z: I/S, y: P/A, x: R/L]
        pd = pd.swapaxes(0, 2)
        # Numpy does evaluation of advanced indicies column wise:
        # pd[sheets, columns, rows]
        matches += abs(pd[rx_points[:, 0], rx_points[:, 1], rx_points[:, 2]] / rx -
            b.ForBeam.BeamMU / tot)

    min_i = np.argmin(matches)
    xpos = rx_points[min_i, 0] * xsize + xcorner + xsize / 2
    ypos = rx_points[min_i, 1] * ysize + ycorner + ysize / 2
    zpos = rx_points[min_i, 2] * zsize + zcorner + zsize / 2
    print 'x, y, z positions = {0}, {1}, {2}'.format(xpos, ypos, zpos)
    return [xpos, ypos, zpos]


def set_dsp(plan, beam_set):
    rx = beam_set.Prescription.PrimaryDosePrescription.DoseValue
    fractions = beam_set.FractionationPattern.NumberOfFractions
    if rx is None:
        raise ValueError('A Prescription must be set.')
    else:
        rx = rx / fractions

    dsp_pos = find_dsp(plan=plan, beam_set=beam_set, dose_per_fraction=rx)

    if dsp_pos:
        dsp_name = beam_set.DicomPlanLabel
        beam_set.CreateDoseSpecificationPoint(Name=dsp_name,
                                              Coordinates={'x': dsp_pos[0],
                                                           'y': dsp_pos[1],
                                                           'z': dsp_pos[2]})
    else:
        raise ValueError('No DSP was set, check execution details for clues.')

    # TODO: set this one up as an optional iteration for the case of multiple beams and multiple DSP's

    for i, beam in enumerate(beam_set.Beams):
        beam.SetDoseSpecificationPoint(Name=dsp_name)

    algorithm = beam_set.FractionDose.DoseValues.AlgorithmProperties.DoseAlgorithm
    # print "\n\nComputing Dose..."
    beam_set.ComputeDose(DoseAlgorithm=algorithm, ForceRecompute='TRUE')

