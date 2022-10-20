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
    01.00.07 RAB Modified to handle errors produced in setting a DSP where no primary Rx is defines

    Known Issues:

    Multi-isocenter treatment will be incorrect in the naming conventions for set up
    fields. The script will rename the first four fields regardless of which isocenter
    to which they belong.
    TODO Consider making the input argument to the jaw checking the mlc_properties class
        Move the mlc properties class to a globally accessible class?

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
import pandas as pd
import math
import logging
import sys
import clr
import connect
import UserInterface
import StructureOperations
import PlanOperations
import GeneralOperations
import Beams
import datetime

clr.AddReference('System')


class Beam(object):

    def __init__(self):
        self.number = None
        self.technique = None
        self.name = None
        self.energy = None
        self.gantry_start_angle = None
        self.gantry_stop_angle = None
        self.rotation_dir = None
        self.collimator_angle = None
        self.iso = {}
        self.couch_angle = None
        self.jaw_limits = {}
        self.field_width = None
        self.pitch = None
        self.jaw_mode = None
        self.back_jaw_position = None
        self.front_jaw_position = None
        self.max_gantry_period = None
        self.max_delivery_time = None
        self.max_delivery_time_factor = None
        self.dsp = None

    def __eq__(self, other):
        return other and \
               self.iso == other.iso \
               and self.gantry_start_angle == other.gantry_start_angle \
               and self.gantry_stop_angle == other.gantry_stop_angle \
               and self.energy == other.energy \
               and self.dsp == other.dsp \
               and self.couch_angle == other.couch_angle \
               and self.collimator_angle == other.collimator_angle \
               and self.rotation_dir == other.rotation_dir \
               and self.technique == other.technique \
               and self.field_width == other.field_width \
               and self.pitch == other.pitch \
               and self.jaw_mode == other.jaw_mode \
               and self.back_jaw_position == other.back_jaw_position \
               and self.front_jaw_position == other.front_jaw_position \
               and self.max_delivery_time == other.max_delivery_time \
               and self.max_delivery_time_factor == other.max_delivery_time_factor \
               and self.max_gantry_period == other.max_gantry_period

    def __hash__(self):
        return hash((
            frozenset(self.iso.items()),
            self.gantry_start_angle,
            self.gantry_stop_angle,
            self.energy,
            self.dsp,
            self.couch_angle,
        ))


class BeamSet(object):

    def __init__(self):
        self.name = None
        self.DicomName = None
        self.description = None
        self.iso = {}
        self.number_of_fractions = None
        self.total_dose = None
        self.machine = None
        self.modality = None
        self.technique = None
        self.rx_target = None
        self.rx_volume = None
        self.iso_target = None
        self.support_roi = None
        self.protocol_name = None
        self.origin_file = None
        self.origin_folder = None

    def __eq__(self, other):
        return other and self.iso == other.iso and self.number_of_fractions \
               == other.number_of_fractions and self.total_dose == other.total_dose \
               and self.machine == other.machine and self.modality == other.modality \
               and self.technique == other.technique and self.rx_target == other.rx_target \
               and self.rx_volume == other.rx_volume and self.support_roi == other.support_roi

    def __hash__(self):
        return hash((
            frozenset(self.iso.items()),
            self.number_of_fractions,
            self.total_dose,
            self.machine,
            self.modality,
            self.technique,
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


def beamset_dialog(case, filename=None, path=None, order_name=None):
    """
    Ask user for information required to load a beamset including the desired protocol beamset to load.

    :param case: current case from RS
    :param folder: folder name of the location of the protocol files
    :param filename: filename housing the order
    :param order_name: optional specification of the order to use
    :return: dialog_beamset: an object of type BeamSet with values set by the user dialog
    """
    # Define an empty BeamSet object that will be the returned object
    dialog_beamset = BeamSet()
    # TODO: Uncomment in version 9 to load the available machine inputs from current commissioned list
    machine_db = connect.get_current('MachineDB')
    # try:
    #    machines = machine_db.QueryCommissionedMachineInfo(Filter={'IsLinac': True})
    #    machine_list = []
    #    for i, m in enumerate(machines):
    #        if m['IsCommissioned']:
    #            machine_list.append(m['Name'])
    # except:
    #    logging.debug('Unable to find machine list still...')
    machine_list = ['TrueBeam', 'TrueBeamSTx', 'HDA0477', 'HDA0488']
    # TODO Test gating option
    # TODO Load all available beamsets found in a file
    available_modality = ['Photons', 'Electrons']
    available_technique = ['Conformal', 'SMLC', 'VMAT', 'DMLC', 'ConformalArc', 'TomoHelical', 'TomoDirect']
    # machine_list = ['TrueBeam', 'TrueBeamSTx']

    # Open the user supplied filename located at folder and return a list of available beamsets
    # Should be able to eliminate this if after the modifications to select_element are complete
    if filename is not None:
        dialog_beamset.origin_file = filename
        dialog_beamset.origin_folder = path
        logging.debug('looking in {} at {} for a {}'.format(filename, path, 'beamset'))
        available_beamsets = Beams.select_element(
            set_level='beamset',
            set_type=None,
            set_elements='beam',
            filename=filename,
            dialog=False,
            folder=path,
            verbose_logging=False)

    targets = StructureOperations.find_targets(case=case)

    dialog = UserInterface.InputDialog(
        inputs={
            '0': 'Choose the Rx target',
            '1': 'Enter the Beamset Name, typically <Site>_VMA_R0A0',
            '2': 'Enter the number of fractions',
            '3': 'Enter total dose in cGy',
            '4': 'Choose Treatment Machine',
            '6': 'Choose a Technique',
            '7': 'Choose a Target for Isocenter Placement',
            '8': 'Choose a Beamset to load'
        },
        title='Beamset Inputs',
        datatype={
            '0': 'combo',
            '4': 'combo',
            '6': 'combo',
            '7': 'combo',
            '8': 'combo'
        },
        initial={
            '1': 'XXXX_VMA_R0A0',
            '4': 'VMAT',
            '8': available_beamsets[0]
        },
        options={
            '0': targets,
            '4': machine_list,
            '6': available_technique,
            '7': targets,
            '8': available_beamsets
        },
        required=['0',
                  '2',
                  '3',
                  '4',
                  '6',
                  '7',
                  '8'])

    # Launch the dialog
    response = dialog.show()
    if response == {}:
        sys.exit('Beamset loading was cancelled')

    dialog_beamset.rx_target = dialog.values['0']
    dialog_beamset.name = dialog.values['1']
    dialog_beamset.DicomName = dialog.values['1']
    dialog_beamset.number_of_fractions = float(dialog.values['2'])
    dialog_beamset.total_dose = float(dialog.values['3'])
    dialog_beamset.machine = dialog.values['4']
    dialog_beamset.modality = 'Photons'
    dialog_beamset.technique = dialog.values['6']
    dialog_beamset.iso_target = dialog.values['7']
    dialog_beamset.protocol_name = dialog.values['8']

    return dialog_beamset


def find_isocenter_parameters(case, exam, beamset, iso_target=None,
                              iso_poi=None,
                              existing_iso=None,
                              lateral_zero=False):
    """Function to return the dict object needed for isocenter placement from the center of a supplied
    name of a structure"""

    if iso_target:
        try:
            isocenter_position = case.PatientModel.StructureSets[exam.Name]. \
                RoiGeometries[iso_target].GetCenterOfRoi()
        except Exception:
            logging.warning('Aborting, could not locate center of {}'.format(iso_target))
            sys.exit('Failed to place isocenter')
    elif iso_poi:
        try:
            isocenter_position = case.PatientModel.StructureSets[exam.Name]. \
                PoiGeometries[iso_poi].Point
        except Exception:
            logging.warning('Aborting, could not locate center of {}'.format(iso_poi))
            sys.exit('Failed to place isocenter at Point {}'.format(iso_poi))
    elif existing_iso:
        beamsets = [bs for p in case.TreatmentPlans for bs in p.BeamSets]
        for bs in beamsets:
            try:
                for b in bs.Beams:
                    if b.Isocenter.Annotation.Name == existing_iso:
                        isocenter_position = b.Isocenter.Position
                        break
            except:
                pass

    # Place isocenter
    # TODO Add a check on laterality at this point (if -7< x < 7 ) put out a warning
    if lateral_zero:
        ptv_center = {'x': 0.,
                      'y': isocenter_position.y,
                      'z': isocenter_position.z}
    else:
        ptv_center = {'x': isocenter_position.x,
                      'y': isocenter_position.y,
                      'z': isocenter_position.z}
    isocenter_parameters = beamset.CreateDefaultIsocenterData(Position=ptv_center)
    isocenter_parameters['Name'] = "iso_" + beamset.DicomPlanLabel
    isocenter_parameters['NameOfIsocenterToRef'] = "iso_" + beamset.DicomPlanLabel
    logging.info('Isocenter chosen based on center of {}.'.format(iso_target) +
                 'Parameters are: x={}, y={}:, z={}, assigned to isocenter name{}'.format(
                     ptv_center['x'],
                     ptv_center['y'],
                     ptv_center['z'],
                     isocenter_parameters['Name']))

    return isocenter_parameters


def create_beamset(patient, case, exam, plan,
                   BeamSet=None,
                   dialog=True,
                   filename=None,
                   path=None,
                   order_name=None,
                   create_setup_beams=True,
                   rename_existing=False):
    """ Create a beamset by opening a dialog with user or loading from scratch
    Currently relies on finding out information via a dialog. I would like it to optionally take the elements
    from the BeamSet class and return the result

    Running as a dialog:
    BeamOperations.create_beamset(patient=patient, case=case, exam=exam, plan=plan, dialog=True)

    Running using the BeamSet class

       """
    if dialog:
        b = beamset_dialog(case=case, filename=filename, path=path, order_name=order_name)
    elif BeamSet is not None:
        b = BeamSet
    else:
        logging.warning('Cannot load beamset due to incorrect argument list')

    # Evaluate for an existing beamset. If rename_existing, add a suffix, otherwise fail
    info = plan.QueryBeamSetInfo(Filter={'Name': '^{0}'.format(b.DicomName)})
    if not info:
        beamset_exists = False
    else:
        if not rename_existing:
            logging.debug('Beamset {} exists and cannot be renamed'.format(b.DicomName))
            return None
        else:
            beamset_exists = True
            # If this beamset is found, then append 1-99 to the name and keep going
            i = 0
            new_bs_name = b.DicomName
            while beamset_exists:
                try:
                    info = plan.QueryBeamSetInfo(Filter={'Name': '^{0}'.format(new_bs_name)})
                    if info[0]['Name'] == new_bs_name:
                        # Ensure the maximum DicomPlanLabel length of 16 chars is not exceeded
                        if len(new_bs_name) > 14:
                            new_bs_name = b.DicomName[:14] + str(i).zfill(2)
                        else:
                            new_bs_name = b.DicomName + str(i).zfill(2)
                        i += 1
                except IndexError:
                    beamset_exists = False
            # Replace input beamset_defs name with update
            if b.DicomName != new_bs_name:
                logging.debug('Beamset {} exists! Replacing with {}'.format(b.DicomName, new_bs_name))
                b.DicomName = new_bs_name

    # TODO: Eliminate exception upon transition to 11
    try:
        plan.AddNewBeamSet(
            Name=b.DicomName,
            ExaminationName=exam.Name,
            MachineName=b.machine,
            Modality=b.modality,
            TreatmentTechnique=b.technique,
            PatientPosition=patient_position_map(exam.PatientPosition),
            NumberOfFractions=b.number_of_fractions,
            CreateSetupBeams=create_setup_beams,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment="",
            RbeModelReference=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[],
            MotionSynchronizationTechniqueSettings=None)
    except:
        plan.AddNewBeamSet(
            Name=b.DicomName,
            ExaminationName=exam.Name,
            MachineName=b.machine,
            Modality=b.modality,
            TreatmentTechnique=b.technique,
            PatientPosition=patient_position_map(exam.PatientPosition),
            NumberOfFractions=b.number_of_fractions,
            CreateSetupBeams=create_setup_beams,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment="",
            RbeModelName=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[],
            MotionSynchronizationTechniqueSettings=None,
            ToleranceTableLabel=None)

    beamset = plan.BeamSets[b.DicomName]
    patient.Save()
    # TODO: Delete upper level try in RS 11
    try:
        # RS 10
        beamset.AddDosePrescriptionToRoi(RoiName=b.rx_target,
                                         DoseVolume=b.rx_volume,
                                         PrescriptionType='DoseAtVolume',
                                         DoseValue=b.total_dose,
                                         RelativePrescriptionLevel=1,
                                         AutoScaleDose=True)
    except AttributeError:
        # RS 11
        try:
            beamset.AddRoiPrescriptionDoseReference(RoiName=b.rx_target,
                                                    DoseVolume=b.rx_volume,
                                                    PrescriptionType='DoseAtVolume',
                                                    DoseValue=b.total_dose,
                                                    RelativePrescriptionLevel=1)
            # TODO Must deal separately with scale to dose
            # beamset.ScaleToPrimaryPrescriptionDoseReference
        except:
            logging.warning('Unable to set prescription')
    return beamset


def place_beams_in_beamset(iso, beamset, beams):
    """
    Put beams in place based on a list of Beam objects
    :param iso: isocenter data dictionary
    :param beamset: beamset to which to add beams
    :param beams: list of Beam objects
    :return:
    """
    if beamset.DeliveryTechnique == "DynamicArc":
        for b in beams:
            logging.info(('Loading Beam {}. Type {}, Name {}, Energy {}, StartAngle {}, StopAngle {}, ' +
                          'RotationDirection {}, CollimatorAngle {}, CouchAngle {} ').format(
                b.number, b.technique, b.name,
                b.energy, b.gantry_start_angle,
                b.gantry_stop_angle, b.rotation_dir,
                b.collimator_angle, b.couch_angle))

            beamset.CreateArcBeam(ArcStopGantryAngle=b.gantry_stop_angle,
                                  ArcRotationDirection=b.rotation_dir,
                                  BeamQualityId=b.energy,
                                  IsocenterData=iso,
                                  Name=b.name,
                                  Description=b.name,
                                  GantryAngle=b.gantry_start_angle,
                                  CouchRotationAngle=b.couch_angle,
                                  CollimatorAngle=b.collimator_angle)

    elif beamset.DeliveryTechnique == "SMLC":
        for b in beams:
            logging.info(('Loading Beam {}. Type {}, Name {}, Energy {}, Gantry Angle {}, Couch Angle {}, ' +
                          'CollimatorAngle {},').format(
                b.number, b.technique, b.name,
                b.energy, b.gantry_start_angle, b.couch_angle,
                b.collimator_angle))

            beamset.CreatePhotonBeam(BeamQualityId=b.energy,
                                     IsocenterData=iso,
                                     Name=b.name,
                                     Description=b.name,
                                     GantryAngle=b.gantry_start_angle,
                                     CouchRotationAngle=b.couch_angle,
                                     CollimatorAngle=b.collimator_angle)


def place_tomo_beam_in_beamset(plan, iso, beamset, beam):
    """
    Put beams in place based on a list of Beam objects
    :param iso: isocenter data dictionary
    :param beamset: beamset to which to add beams
    :param beams: list of Beam objects
    :return:
    """
    verbose_logging = True
    logging.info(('Loading Beam {}. Type {}, Name {}, Energy {}, ' +
                  'Field Width {}, Pitch {}').format(
        beam.number, beam.technique, beam.name,
        beam.energy, beam.field_width, beam.pitch))

    beamset.CreatePhotonBeam(Name=beam.name,
                             BeamQualityId=beam.energy,
                             IsocenterData=iso,
                             Description=beam.name,
                             )
    opt_index = PlanOperations.find_optimization_index(plan=plan,
                                                       beamset=beamset,
                                                       verbose_logging=False)
    plan_optimization_parameters = plan.PlanOptimizations[opt_index].OptimizationParameters
    for tss in plan_optimization_parameters.TreatmentSetupSettings:
        if tss.ForTreatmentSetup.DicomPlanLabel == beamset.DicomPlanLabel:
            ts_settings = tss
            if verbose_logging:
                logging.debug('TreatmentSetupSettings:{} matches Beamset:{} looking for beam {}'.format(
                    tss.ForTreatmentSetup.DicomPlanLabel, beamset.DicomPlanLabel, beam.name))
            for bs in ts_settings.BeamSettings:
                if bs.ForBeam.Name == beam.name:
                    beam_found = True
                    current_beam_settings = bs
                    break
                else:
                    continue
        else:
            continue

    if ts_settings is None:
        logging.exception('No treatment set up settings could be found for beamset {}'.format(
            beamset.DicomPlanLabel) + 'Contact script administrator')

    if not beam_found:
        logging.warning('Beam {} not found in beam list from {}'.format(
            beam.name, beamset.DicomPlanLabel))
        sys.exit('Could not find a beam match for setting aperture limits')

    if ts_settings is not None and current_beam_settings is not None:
        current_beam_settings.TomoPropertiesPerBeam.EditTomoBasedBeamOptimizationSettings(
            JawMode=beam.jaw_mode,
            PitchTomoHelical=beam.pitch,
            # PitchTomoDirect=,
            BackJawPosition=beam.back_jaw_position,
            FrontJawPosition=beam.front_jaw_position,
            MaxDeliveryTime=beam.max_delivery_time,
            MaxGantryPeriod=beam.max_gantry_period,
            MaxDeliveryTimeFactor=beam.max_delivery_time_factor)
    beamset.Beams[0].BeamQualityId = beam.energy


def place_tomodirect_beams_in_beamset(plan, iso, beamset, beams):
    """
    Put beams in place based on a list of Beam objects
    :param iso: isocenter data dictionary
    :param beamset: beamset to which to add beams
    :param beams: list of Beam objects
    :return:
    """
    verbose_logging = False
    for b in beams:
        logging.info(('Loading Beam {}. Type {}, Name {}, Energy {}, ' +
                      'Gantry Angle {}, Field Width {}, Pitch {}').format(
            b.number, b.technique, b.name,
            b.energy, b.gantry_start_angle, b.field_width, b.pitch))

        beamset.CreatePhotonBeam(Name=b.name,
                                 BeamQualityId=b.energy,
                                 IsocenterData=iso,
                                 Description=b.name,
                                 GantryAngle=b.gantry_start_angle,
                                 )
        opt_index = PlanOperations.find_optimization_index(plan=plan,
                                                           beamset=beamset,
                                                           verbose_logging=False)
        plan_optimization_parameters = plan.PlanOptimizations[opt_index].OptimizationParameters
        for tss in plan_optimization_parameters.TreatmentSetupSettings:
            if tss.ForTreatmentSetup.DicomPlanLabel == beamset.DicomPlanLabel:
                ts_settings = tss
                if verbose_logging:
                    logging.debug('TreatmentSetupSettings:{} matches Beamset:{} looking for beam {}'.format(
                        tss.ForTreatmentSetup.DicomPlanLabel, beamset.DicomPlanLabel, b.name))
                for bs in ts_settings.BeamSettings:
                    if bs.ForBeam.Name == b.name:
                        beam_found = True
                        current_beam_settings = bs
                        break
                    else:
                        continue
            else:
                continue
        if ts_settings is None:
            logging.exception('No treatment set up settings could be found for beamset {}'.format(
                beamset.DicomPlanLabel) + 'Contact script administrator')

        if not beam_found:
            logging.warning('Beam {} not found in beam list from {}'.format(
                b.name, beamset.DicomPlanLabel))
            sys.exit('Could not find a beam match for setting aperture limits')

        if ts_settings is not None and current_beam_settings is not None:
            current_beam_settings.TomoPropertiesPerBeam.EditTomoBasedBeamOptimizationSettings(
                JawMode=b.jaw_mode,
                # PitchTomoHelical=beam.pitch,
                PitchTomoDirect=b.pitch,
                BackJawPosition=b.back_jaw_position,
                FrontJawPosition=b.front_jaw_position,
                MaxDeliveryTime=b.max_delivery_time,
                MaxGantryPeriod=b.max_gantry_period,
                MaxDeliveryTimeFactor=b.max_delivery_time_factor)


def modify_tomo_beam_properties(settings, plan, beamset, beam):
    # Allow modification of a single tomotherapy optimization setting
    # settings: Dict: {'back_jaw_position': Float,
    #                  'front_jaw_position': Float,
    #                  'jaw_mode' : Dynamic/Static
    #                  'max_delivery_time': Float
    #                  'max_delivery_time_factor' : Float
    #                  'max_gantry_period' : Float
    #                  'pitch_tomo_direct' : Float
    #                  'pitch_tomo_helical': Float
    #                        '}
    for o in plan.PlanOptimizations:
        for t in o.OptimizationParameters.TreatmentSetupSettings:
            if t.ForTreatmentSetup.DicomPlanLabel == beamset.DicomPlanLabel:
                for bs in t.BeamSettings:
                    if bs.ForBeam.Name == beam.Name:
                        if 'jaw_mode' in settings.keys():
                            jaw_mode = settings['jaw_mode']
                        else:
                            jaw_mode = bs.TomoPropertiesPerBeam.JawMode
                        if 'pitch_tomo_direct' in settings.keys():
                            pitch_tomo_direct = settings['pitch_tomo_direct']
                        else:
                            pitch_tomo_direct = bs.TomoPropertiesPerBeam.PitchTomoDirect
                        if 'pitch_tomo_helical' in settings.keys():
                            pitch_tomo_helical = settings['pitch_tomo_helical']
                        else:
                            pitch_tomo_helical = bs.TomoPropertiesPerBeam.PitchTomoHelical
                        if 'back_jaw_position' in settings.keys():
                            back_jaw_position = settings['back_jaw_position']
                        else:
                            back_jaw_position = bs.TomoPropertiesPerBeam.BackJawPosition
                        if 'front_jaw_position' in settings.keys():
                            front_jaw_position = settings['front_jaw_position']
                        else:
                            front_jaw_position = bs.TomoPropertiesPerBeam.FrontJawPosition
                        if 'max_delivery_time' in settings.keys():
                            max_delivery_time = settings['max_delivery_time']
                        else:
                            max_delivery_time = bs.TomoPropertiesPerBeam.MaxDeliveryTime
                        if 'max_gantry_period' in settings.keys():
                            max_gantry_period = settings['max_gantry_period']
                        else:
                            max_gantry_period = bs.TomoPropertiesPerBeam.MaxGantryPeriod
                        if 'max_delivery_time_factor' in settings.keys():
                            max_delivery_time_factor = settings['max_delivery_time_factor']
                        else:
                            max_delivery_time_factor = bs.TomoPropertiesPerBeam.MaxDeliveryTimeFactor
                        try:
                            bs.TomoPropertiesPerBeam.EditTomoBasedBeamOptimizationSettings(
                                JawMode=jaw_mode,
                                PitchTomoHelical=pitch_tomo_helical,
                                PitchTomoDirect=pitch_tomo_direct,
                                BackJawPosition=back_jaw_position,
                                FrontJawPosition=front_jaw_position,
                                MaxDeliveryTime=max_delivery_time,
                                MaxGantryPeriod=max_gantry_period,
                                MaxDeliveryTimeFactor=max_delivery_time_factor)
                        except Exception as e:
                            try:
                                if 'No changes to save' in e.Message:
                                    logging.info('No changes to save in modifying tomo beam properties')
                                    pass
                                else:
                                    logging.exception(u'{}'.format(e.Message))
                                    sys.exit(u'{}'.format(e.Message))
                            except:
                                logging.exception("EXCEPTION OF Unknown Type")
                                sys.exit(u'{}'.format(e))


def gather_tomo_beam_params(beamset):
    # Compute time, rotation period, couch speed, pitch
    #   mod factor
    for b in beamset.Beams:
        number_segments = 0
        total_travel = 0
        max_lot = 0
        sinogram = []
        for s in b.Segments:
            number_segments += 1
            leaf_pos = []
            for l in s.LeafOpenFraction:
                leaf_pos.append(l)
            sinogram.append(leaf_pos)
        # Projection time in Rs is just MU
        proj_time = b.BeamMU
        # Total Time: Projection time x Number of Segments = Total Time
        time = b.BeamMU * number_segments
        # Rotation period: Projection Time * 51
        rp = b.BeamMU * 51.
        # Couch Speed: Total Distance Traveled / Total Time
        total_travel = b.Segments[number_segments - 1].CouchYOffset \
                       - b.Segments[0].CouchYOffset
        couch_speed = total_travel / time
        # Pitch: Distance traveled in rotation / field width

        # Convert sinogram to numpy array
        sino_array = np.array(sinogram)
        # Find non-zero elements
        non_zero = np.where(sino_array != 0)
        sino_non_zero = sino_array[non_zero]
        # Mod Factor = Average / Max LOT
        mod_factor = np.max(sino_non_zero) / np.mean(sino_non_zero)
        # Declare the tomo dataframe
        dtypes = np.dtype([
            ('time', float),  # Total time of plan [s]
            ('proj_time', float),  # Time of each projection [s]
            ('total_travel', float),  # Couch travel [cm]
            ('couch_speed', float),  # Speed of couch [cm/s]
            ('sinogram', object),  # List of leaf openings
            ('mod_factor', float)  # Max/Ave_Nonzero
        ])
        data = np.empty(0, dtype=dtypes)
        df = pd.DataFrame(data)
        # Return a dataframe for json output
        df.at[0, 'time'] = time
        df.at[0, 'proj_time'] = proj_time
        df.at[0, 'rp'] = rp
        df.at[0, 'total_travel'] = total_travel
        df.at[0, 'couch_speed'] = couch_speed
        df.at[0, 'sinogram'] = sino_array
        df.at[0, 'mod_factor'] = mod_factor
    return df


def check_pa(plan, beam):
    """Determine if any fields are pa, and return true if the gantry is unlikely to clear from
    a determined direction
    :param beam: RS beam object
    :return None if test passed, suggested gantry angle if failed"""
    delivery_techiques = ['SMLC']
    linac_clearance = 35.0
    if beam.GantryAngle != 180 or beam.DeliveryTechnique not in delivery_techiques:
        return None
    else:
        lateral_iso = beam.Isocenter.Position.x
        grid = plan.GetDoseGrid()
        lower_corner = grid.Corner
        lc_x = lower_corner.x
        lc_y = lower_corner.y
        lc_z = lower_corner.z

        uc_x = lc_x + grid.VoxelSize.x * grid.NrVoxels.x
        uc_y = lc_y + grid.VoxelSize.y * grid.NrVoxels.y
        uc_z = lc_z + grid.VoxelSize.z * grid.NrVoxels.z
        # Find the distance of the corners of the dose grid from isocenter
        corners = np.empty([8, 3])
        sq_diff = np.zeros([8, 2])
        # The dose grid corners are going to need to be converted to patient coordinates for this to work...
        # start at lower left and raster up
        corners[0, :] = [lc_x, lc_y, lc_z]
        corners[1, :] = [uc_x, lc_y, lc_z]
        corners[2, :] = [lc_x, lc_y, uc_z]
        corners[3, :] = [uc_x, lc_y, uc_z]
        corners[4, :] = [lc_x, uc_y, lc_z]
        corners[5, :] = [uc_x, uc_y, lc_z]
        corners[6, :] = [lc_x, uc_y, uc_z]
        corners[7, :] = [uc_x, uc_y, uc_z]
        logging.debug('Corners is \n {}'.format(corners))
        # np_list = corners.tolist()
        # np_out = '\n'.join('{}'.format(row) for row in np_list)
        # logging.debug('Corner is \n{}'.format(np_out))
        # Evaluate the distance of each corner
        sq_diff[:, 0] = beam.Isocenter.Position.x - corners[:, 0]
        sq_diff[:, 1] = beam.Isocenter.Position.z - corners[:, 2]
        sq_diff = np.square(sq_diff)
        logging.debug('sq_diff is \n {}'.format(sq_diff))
        dist = np.sum(sq_diff, axis=1)
        logging.debug('dist is \n {}'.format(dist))
        max_corner = np.argmax(dist)
        logging.debug('Maximum distance is to corner {} at position (x, y, z): ({}, {}, {})'.format(
            max_corner, corners[max_corner, 0], corners[max_corner, 1], corners[max_corner, 2]))
        if max_corner % 2 == 0:
            # Lower (negative) corner, clearance issue is on HFS's left, recommend using beam down the right
            return 180.1
        else:
            # Upper (positive) corner, clearance issue is on HFS's right, recommend using beam down the left
            return 179.9

        # Find the corner farthest from iso


def rename_isocenter(plan, beamset):
    # Look for all isocenters used in the plan and build a set
    beamset_isocenters = set([str(b.Isocenter.Annotation.Name) for bs in plan.BeamSets for b in bs.Beams])
    # Find an unused isocenter name
    iso_name_found = False
    iso_count = 0
    while not iso_name_found:
        iso_name = 'Iso_' + beamset.DicomPlanLabel + '_' + str(iso_count)
        if iso_name in beamset_isocenters:
            iso_count += 1
        else:
            iso_name_found = True
    for b in beamset.Beams:
        b.Isocenter.Annotation.Name = iso_name


# def check_clearance(beamset):
#     """Currently looking only at PA fields for whether the pa function should be flipped
#     return: dict: {Beam.Name: 'PA_Check': {'No_Collision':True, 'Change_Gantry': 180.1}}"""
#     beam_status = {}
#     for b in beamset.Beams:
#         rec_gantry_angle = check_pa(beam=b)
#         if rec_gantry_angle is not None:
#             logging.debug('Beam {} potential gantry clearance issue. Recommend changing gantry angle from {} to {}'
#                           .format(b.Name, b.GantryAngle, rec_gantry_angle))
#             if b.Name not in beam_status:
#                 beam_status[b.Name] = {'PA_Check':}
#             beam_status[b.Name] = ['PA_Clear']


def validate_setup_fields(beamset):
    """For the current beamset check all SSD's and return a list of any beams with infinite SSD's.
    :param beamset: RS beamset object
    :return invalid_gantry_angles: a list of gantry angles of invalid set-up fields
    """
    invalid_gantry_angles = []
    for setup_beam in beamset.PatientSetup.SetupBeams:
        if setup_beam.GetSSD() != float('inf'):
            logging.debug('Valid SSD {} detected on setup beam with gantry angle {}'.format(
                setup_beam.GetSSD(), setup_beam.GantryAngle))
        else:
            logging.debug('Invalid SSD {} detected on setup beam with gantry angle {}'.format(
                setup_beam.GetSSD(), setup_beam.GantryAngle))
            invalid_gantry_angles.append(float(setup_beam.GantryAngle))
    return invalid_gantry_angles


def update_set_up(beamset, set_up):
    """Update the setup fields after checking their validity
    :param: beamset: RS beamset object
    :param: set_up: Dict: [i][ Set-Up Field Name, Set-Up Field Description, Gantry Angle, Dose Rate]
    """
    # Extract the angles
    angles = []
    for k, v in set_up.items():
        angles.append(v[2])
    # Initialize the Setup Beams
    beamset.UpdateSetupBeams(ResetSetupBeams=True, SetupBeamsGantryAngles=angles)
    # Test for valid set-up fields
    invalid_setup_field = validate_setup_fields(beamset=beamset)
    if len(invalid_setup_field) > 0:
        # Pop the invalid beam angles
        angles = []
        for k in list(set_up):
            if any(set_up[k][2] == ga for ga in invalid_setup_field):
                set_up.pop(k)
            else:
                angles.append(set_up[k][2])
        # Update the setup beams with the valid angles
        beamset.UpdateSetupBeams(ResetSetupBeams=True, SetupBeamsGantryAngles=angles)
    # Set the set-up parameter specifics
    i = 0
    for k in set_up:
        beamset.PatientSetup.SetupBeams[i].Name = set_up[k][0]
        beamset.PatientSetup.SetupBeams[i].Description = set_up[k][1]
        beamset.PatientSetup.SetupBeams[i].GantryAngle = str(set_up[k][2])
        beamset.PatientSetup.SetupBeams[i].Segments[0].DoseRate = set_up[k][3]
        i += 1


def rename_beams(site_name=None, input_technique=None):
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

    #
    # Electrons, 3D, and VMAT Arcs are all that are supported.  Reject plans that aren't
    technique = beamset.DeliveryTechnique
    #
    # Oddly enough, Electrons are DeliveryTechnique = 'SMLC'
    if technique not in supported_rs_techniques:
        logging.warning('Technique: {} unsupported in renaming script'.format(technique))
        raise IOError("Technique unsupported, manually name beams according to clinical convention.")
    # These are the techniques associated with billing codes in the clinic
    # they will be imported
    # Separate the billing list by technique
    if technique == 'SMLC':
        if beamset.Modality == 'Electrons':
            available_techniques = [
                'Electron -- 2D',
                'Electron -- 3D']
        else:
            available_techniques = [
                'Static MLC -- 2D',
                'Static NoMLC -- 2D',
                'Static MLC -- 3D',
                'Static NoMLC -- 3D',
                'FiF MLC -- 3D',
                'Static PRDR MLC -- 3D',
                'SnS MLC -- IMRT',
                'SnS PRDR MLC -- IMRT']
    elif technique == 'DynamicArc':
        available_techniques = [
            'Conformal Arc -- 2D',
            'Conformal Arc -- 3D',
            'VMAT Arc -- IMRT']
    elif technique == 'TomoHelical':
        available_techniques = [
            'TomoHelical -- IMRT',
            'TomoHelical -- 3D Conformal']

    initial_sitename = beamset.DicomPlanLabel[:4]
    if not site_name and not input_technique:
        # Prompt the user for Site Name and Billing technique
        dialog = UserInterface.InputDialog(inputs={'Site': 'Enter a Site name, e.g. BreL',
                                                   'Technique': 'Select Treatment Technique (Billing)'},
                                           datatype={'Technique': 'combo'},
                                           initial={'Technique': 'Select',
                                                    'Site': initial_sitename},
                                           options={'Technique': available_techniques},
                                           required=['Site', 'Technique'])
        # Show the dialog
        response = dialog.show()
        if response == {}:
            logging.info('Beam rename cancelled by user')
            sys.exit('Beam rename cancelled')

        site_name = dialog.values['Site']
        input_technique = dialog.values['Technique']

    # Tomo Helical naming
    if technique == 'TomoHelical':
        for b in beamset.Beams:
            beam_description = 'TomoHelical_' + site_name
            b.Name = beam_description
            b.Description = input_technique
        return

    # While loop variable definitions
    beam_index = 0
    patient_position = beamset.PatientPosition
    # Turn on set-up fields
    beamset.PatientSetup.UseSetupBeams = True
    logging.debug(
        'Renaming and adding set up fields to Beam Set with name {}, patdelivery_time_factor {}, technique {}'.
            format(beamset.DicomPlanLabel, beamset.PatientPosition, beamset.DeliveryTechnique))
    # Rename isocenters
    rename_isocenter(plan, beamset)
    #
    # HFS
    if patient_position == 'HeadFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)

    # HFLDR
    elif patient_position == 'HeadFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    # HFLDL
    elif patient_position == 'HeadFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    # HFP
    elif patient_position == 'HeadFirstProne':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    # FFS
    elif patient_position == 'FeetFirstSupine':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_PA'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)

        # Address the Feet-first prone position
    # FFLDR
    elif patient_position == 'FeetFirstDecubitusRight':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_RLAT'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    # FFLDL
    elif patient_position == 'FeetFirstDecubitusLeft':
        standard_beam_name = 'Naming Error'
        for b in beamset.Beams:
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_LLAT'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    # FFP
    elif patient_position == 'FeetFirstProne':
        for b in beamset.Beams:
            standard_beam_name = 'Naming Error'
            try:
                gantry_angle = round(float(b.GantryAngle), 1)
                couch_angle = round(float(b.CouchRotationAngle), 1)
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
                                              + '_t' + couch_angle_string.zfill(3))
                else:
                    # Based on convention for billing, e.g. "1 SnS PRDR MLC -- IMRT"
                    # set the beam_description
                    beam_description = str(beam_index + 1) + ' ' + input_technique
                    if couch_angle != 0:
                        standard_beam_name = (str(beam_index + 1) + '_' + site_name
                                              + '_g' + gantry_angle_string.zfill(3)
                                              + 't' + couch_angle_string.zfill(3))
                    elif 179.8 < gantry_angle < 180.2:
                        standard_beam_name = str(beam_index + 1) + '_' + site_name + '_AP'
                    elif 180.2 < gantry_angle < 270:
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
                    elif 90 < gantry_angle < 179.8:
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
        update_set_up(beamset=beamset, set_up=set_up)
    else:
        raise IOError("Patient Orientation Unsupported.. Manual Beam Naming Required")


class mlc_properties:
    """
    Class of mlc_properties:
    using an RS beam object a number of parameters of the MLC bank, and the specific segments are evaluated

    has_segments: determines whether segments have been defined for this field (electron fields don't have segments)
    beam: the original beam RS object- arguable as to whether another copy of this is needed
    max_tip: if the beam has an MLC, this will determine the maximum position the MLC can extend from the CAX
    num_leaves_per_bank: the number of MLC leaves in a bank

    banks: a numpy array of MLC segment positions

    """

    # Initialize with a RS beam object
    def __init__(self, beam):
        self.beam = beam  # A Raystation beam object that has segments
        try:
            s0 = self.beam.Segments[0]
            self.has_segments = True
        except:
            self.has_segments = False

        if self.has_segments:
            current_machine_name = self.beam.MachineReference.MachineName
            current_machine = GeneralOperations.get_machine(current_machine_name)
            # If the plan is imported then the MlcPhysics methods will not be defined
            try:
                mlc_physics = current_machine.Physics.MlcPhysics
            except AttributeError:
                mlc_physics = None

            # TODO: This variable changed in 10. Find it
            if mlc_physics:
                # Maximum motion of a leaf on its own side of the origin
                self.max_tip = mlc_physics.MaxTipDifference
                # Maximum leaf out of carriage distance [cm]
                self.max_leaf_carriage = mlc_physics.Carriage.MaxLeafOutOfCarriageDistance
                # Grab the leaf centers and widths
                self.leaf_centers = current_machine.Physics.MlcPhysics.UpperLayer.LeafCenterPositions
                self.leaf_widths = current_machine.Physics.MlcPhysics.UpperLayer.LeafWidths
                # Grab the distance behind the x-jaw a dynamic leaf is supposed to be placed
                self.leaf_jaw_overlap = current_machine.Physics.MlcPhysics.LeafJawOverlap
                # Grab the minimum gap allowed for a dynamic leaf
                self.min_gap_moving = current_machine.Physics.MlcPhysics.MinGapMoving
            else:
                self.max_tip = None
                self.max_leaf_carriage = 15  # Plug a guess in here
                self.leaf_centers = None
                self.leaf_widths = None
                self.leaf_jaw_overlap = None
                self.min_gap_moving = 0.05  # Guess in here

            # Compute the number of leaves in the bank based on the first segment
            self.num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])

            #
            # Set up a numpy array that will be a combine segments
            # into a single ndarray of size:
            # MLC leaf number x number of banks x number of segments
            self.banks = np.column_stack((s0.LeafPositions[0], s0.LeafPositions[1]))
            self.number_segments = len(beam.Segments)
            if self.number_segments > 1:
                for cp in range(1, self.number_segments):
                    # for s in beam.Segments:
                    s = beam.Segments[cp]
                    # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
                    bank = np.column_stack((s.LeafPositions[0], s.LeafPositions[1]))
                    self.banks = np.dstack((self.banks, bank))
                # Determine if leaves are in retracted position
                if np.all(self.banks[:, 0, :] <= - self.max_leaf_carriage):
                    x1_bank_retracted = True
                else:
                    x1_bank_retracted = False
                if np.all(self.banks[:, 1, :] >= self.max_leaf_carriage):
                    x2_bank_retracted = True
                else:
                    x2_bank_retracted = False
            else:
                # Determine if leaves are in retracted position
                if np.all(self.banks[:, 0] <= - self.max_leaf_carriage):
                    x1_bank_retracted = True
                else:
                    x1_bank_retracted = False
                if np.all(self.banks[:, 1] >= self.max_leaf_carriage):
                    x2_bank_retracted = True
                else:
                    x2_bank_retracted = False

            if x1_bank_retracted and x2_bank_retracted:
                self.mlc_retracted = True
            else:
                self.mlc_retracted = False

    # MLC methods:
    def stationary_leaf_gaps(self):
        threshold = 1e-6
        # Find the MLC gaps that are closed (set to the minimum moving leaf opening) and return them
        # If stationary_only is True, return only leaf gaps that are closed to minimum and do not move in the next
        # control point
        # closed leaf gaps: [# MLC, # Banks, #Control points]
        if not self.has_segments:
            return None
        leaf_gaps = np.empty_like(self.banks, dtype=bool)
        # Solve only for gaps that do not move in the next control point
        number_of_control_points = leaf_gaps.shape[2]
        for cp in range(number_of_control_points):
            for l in range(leaf_gaps.shape[0]):
                # Only flag leaves that have a difference in position equal to the minimum moving leaf gap
                diff = abs(self.banks[l, 0, cp] - self.banks[l, 1, cp])
                # If the leaf is defined as non-dynamic (0, 0) then ignore it.
                if self.banks[l, 0, cp] == 0 and self.banks[l, 1, cp] == 0:
                    ignore_leaf_pair = True
                elif diff > (1 + threshold) * self.min_gap_moving:
                    ignore_leaf_pair = True
                else:
                    ignore_leaf_pair = False
                #
                if ignore_leaf_pair:
                    leaf_gaps[l, :, cp] = False
                else:
                    #
                    # Check if the leaf gap is a "closed leaf gap" that is not moving in adjacent control points
                    # See if leaf pair moves from one iteration to the next
                    #
                    # First control point only evaluate ahead two control points for changes
                    if cp == 0:
                        x1_diff_0 = abs(self.banks[l, 0, cp + 1] - self.banks[l, 0, cp])
                        x1_diff_1 = abs(self.banks[l, 0, cp + 2] - self.banks[l, 0, cp + 1])
                        x2_diff_0 = abs(self.banks[l, 1, cp + 1] - self.banks[l, 1, cp])
                        x2_diff_1 = abs(self.banks[l, 1, cp + 2] - self.banks[l, 1, cp + 1])
                    # Last control point only evaluate last two control points for changes
                    elif cp == number_of_control_points - 1:
                        x1_diff_0 = abs(self.banks[l, 0, cp] - self.banks[l, 0, cp - 1])
                        x1_diff_1 = abs(self.banks[l, 0, cp - 1] - self.banks[l, 0, cp - 2])
                        x2_diff_0 = abs(self.banks[l, 1, cp] - self.banks[l, 1, cp - 1])
                        x2_diff_1 = abs(self.banks[l, 1, cp - 1] - self.banks[l, 1, cp - 2])
                    else:
                        # Check if the previous closed leaf pair was in a different position
                        x1_diff_0 = abs(self.banks[l, 0, cp] - self.banks[l, 0, cp - 1])
                        x1_diff_1 = abs(self.banks[l, 0, cp + 1] - self.banks[l, 0, cp])
                        x2_diff_0 = abs(self.banks[l, 1, cp] - self.banks[l, 1, cp - 1])
                        x2_diff_1 = abs(self.banks[l, 1, cp + 1] - self.banks[l, 1, cp])
                    x1_diff = [x1_diff_0, x1_diff_1]
                    x2_diff = [x2_diff_0, x2_diff_1]
                    # Evaluate each control point difference to see if it is less than the threshold for equivalence
                    if all(x1 <= threshold for x1 in x1_diff) and all(x2 <= threshold for x2 in x2_diff):
                        leaf_gaps[l, :, cp] = True
                    else:
                        leaf_gaps[l, :, cp] = False

        return leaf_gaps

    def closed_leaf_gaps(self):
        threshold = 1e-6
        if not self.has_segments:
            return None
        leaf_gaps = np.empty_like(self.banks, dtype=bool)
        leaf_gaps[:, 0, :] = abs(self.banks[:, 0, :] - self.banks[:, 1, :]) < \
                             (1 + threshold) * self.min_gap_moving
        leaf_gaps[:, 1, :] = leaf_gaps[:, 0, :]
        return leaf_gaps

    def max_opening(self):
        # Find the maximum open top and bottom leaf and maximum opening in x1 and x2 directions ignoring
        # MLC's that are set to the minimum leaf opening
        # Determine if a leaf pair separation exceeds the minimum leaf separation if not zero
        # the gap
        filtered_banks = np.copy(self.banks)
        closed_gap = self.closed_leaf_gaps()
        filtered_banks[closed_gap] = 0
        # Along all control points solve for the most open mlc position on bank x1 and bank x2
        if self.number_segments > 1:
            min_x1_bank = np.amin(filtered_banks[:, 0, :], axis=1)
            max_x2_bank = np.amax(filtered_banks[:, 1, :], axis=1)
        else:
            # If there is only one control point then just give back the bank data
            min_x1_bank = filtered_banks[:, 0]
            max_x2_bank = filtered_banks[:, 1]
        max_open_x1 = np.amin(min_x1_bank)
        right_leaf_number = np.argmin(max_open_x1)
        max_open_x2 = np.amax(max_x2_bank)
        left_leaf_number = np.argmin(max_open_x2)
        # Solve for the index of the first nonzero element in min_x1_bank and the last non-zero element
        top_leaf_number = np.max(np.argwhere(min_x1_bank))
        bottom_leaf_number = np.min(np.argwhere(min_x1_bank))
        max_open_y1 = self.leaf_centers[bottom_leaf_number] - 0.5 * self.leaf_widths[bottom_leaf_number]
        max_open_y2 = self.leaf_centers[top_leaf_number] + 0.5 * self.leaf_widths[top_leaf_number]
        return {'max_open_x1': max_open_x1, 'max_right_leaf': right_leaf_number,
                'max_open_x2': max_open_x2, 'max_left_leaf': left_leaf_number,
                'max_open_y1': max_open_y1, 'max_bottom_leaf': bottom_leaf_number,
                'max_open_y2': max_open_y2, 'max_top_leaf': top_leaf_number}

    def ciao(self):
        # Determine the maximum of any leaf position for all segments
        # completely irradiated area outline
        # return a numpy array of maximum (most open) leaf position over all control points
        if self.has_segments:
            ciao_array = np.empty(shape=(self.num_leaves_per_bank, 2))
            if self.number_segments > 1:
                ciao_array[:, 0] = np.amin(self.banks[:, 0, :], axis=1)
                ciao_array[:, 1] = np.amax(self.banks[:, 1, :], axis=1)
            else:
                ciao_array[:, 0] = self.banks[:, 0]
                ciao_array[:, 1] = self.banks[:, 1]
            return ciao_array
        else:
            return None

    def max_travel(self):
        # For all segments: determine the maximum distance each leaf is from the jaw (carriage)
        # return a numpy array of maximum (most open) leaf position over all control points
        if self.has_segments:
            max_travel_array = np.empty(shape=(self.num_leaves_per_bank, 2))
            if self.number_segments > 1:
                max_travel_array[:, 0] = np.amax(self.banks[:, 0, :], axis=1)
                max_travel_array[:, 1] = np.amin(self.banks[:, 1, :], axis=1)
            else:
                # If there is only one control point then just give back the bank data
                max_travel_array[:, 0] = self.banks[:, 0]
                max_travel_array[:, 1] = self.banks[:, 1]
            return max_travel_array
        else:
            return None


def maximum_beam_leaf_extent(beam):
    """
    :param beam: RayStation beam object
    :return: numpy array of maximum (most open) leaf position over all control points
    """
    try:
        # Find the number of leaves in the first segment to initialize the array
        s0 = beam.Segments[0]
    except:
        logging.debug('Beam {} does not have segments for a ciao.'.format(beam.Name))
        return None

    num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])
    banks = np.column_stack((s0.LeafPositions[0], s0.LeafPositions[1]))
    # Combine the segments into a single ndarray of size:
    # number of MLCs x number of banks x number of segments
    for s in beam.Segments:
        # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
        bank = np.column_stack((s.LeafPositions[0], s.LeafPositions[1]))
        banks = np.dstack((banks, bank))

    # Determine the maximum of any leaf position for all segments
    # completely irradiated area outline
    ciao = np.empty(shape=(num_leaves_per_bank, 2))
    ciao[:, 0] = np.amin(banks[:, 0, :], axis=1)
    ciao[:, 1] = np.amax(banks[:, 1, :], axis=1)
    return ciao


def maximum_leaf_carriage_extent(beam):
    """
    Find the leaf that is farthest from the current jaw position
    :param beam: RayStation beam object
    :return: numpy array of maximum (most open) leaf position over all control points
    """
    try:
        # Find the number of leaves in the first segment to initialize the array
        s0 = beam.Segments[0]
    except:
        logging.debug('Beam {} does not have segments for a ciao.'.format(beam.Name))
        return None
    t_init = datetime.datetime.now()
    num_leaves_per_bank = int(s0.LeafPositions[0].shape[0])
    banks = np.column_stack((s0.LeafPositions[0], s0.LeafPositions[1]))
    # Combine the segments into a single ndarray of size:
    # number of MLCs x number of banks x number of segments
    for s in beam.Segments:
        # Take the bank positions on X1-bank, and X2 Bank and put them in column 0, 1 respectively
        bank = np.column_stack((s.LeafPositions[0], s.LeafPositions[1]))
        banks = np.dstack((banks, bank))

    # Determine the maximum travel of any leaf on the bank
    max_travel = np.empty(shape=(num_leaves_per_bank, 2))
    max_travel[:, 0] = np.amax(banks[:, 0, :], axis=1)
    max_travel[:, 1] = np.amin(banks[:, 1, :], axis=1)
    # Stop the clock
    t_fine = datetime.datetime.now()
    delta = t_fine - t_init
    logging.debug('Max Carriage Operation required {} seconds'.format(delta.total_seconds()))
    return max_travel


def repair_leaf_gap(beam):
    """ Find all of the closed leaves. Repair the leaf gap rounding problem so that the leaves are spaced
        by exactly the minimum leaf gap. Return success.
    """
    # Adjustment factor is the factor to increment each leaf position by until the
    # gap condition is met
    increment = 1.e-6

    # Determine the mlc properties of the beam
    beam_mlc = mlc_properties(beam)

    # Find the closed leaves
    closed_leaves = beam_mlc.stationary_leaf_gaps()

    # Store the initial position as a check.  Delete after validated
    initial_beam_mlc = np.copy(beam_mlc.banks)

    # Loop over the leaves
    for i in range(beam_mlc.banks.shape[0]):
        # Loop over control points
        for j in range(beam_mlc.banks.shape[2]):
            # If this is part of the closed leaf range, then make sure the gap is greater than or
            # equal to the machine commissioned gap
            # if np.all(closed_leaves[i, 0, j]):
            gap = abs(beam_mlc.banks[i, 0, j] - beam_mlc.banks[i, 1, j])
            logging.debug('Bank0[{},{}] {}, Bank1 [{},{}] {}: gap {}'.format(
                i, j, beam_mlc.banks[i, 0, j], i, j, beam_mlc.banks[i, 1, j],
                gap))
            if gap < increment:
                beam_mlc.banks[i, 0, j] = 0.
                beam_mlc.banks[i, 1, j] = (1. + increment) * beam_mlc.min_gap_moving
                logging.debug('Zero leaf gap, moved to {}, {}'.format(
                    beam_mlc.banks[i, 0, j], beam_mlc.banks[i, 1, j]))
            elif gap < beam_mlc.min_gap_moving:
                while gap < beam_mlc.min_gap_moving:
                    beam_mlc.banks[i, 0, j] = (1. + increment) * beam_mlc.banks[i, 0, j]
                    beam_mlc.banks[i, 1, j] = (1. + increment) * beam_mlc.banks[i, 1, j]
                    gap = abs(beam_mlc.banks[i, 0, j] - beam_mlc.banks[i, 1, j])
                    logging.debug('Rounded leaf gap moved to bank0 {}, bank1 {}'.format(
                        beam_mlc.banks[i, 0, j], beam_mlc.banks[i, 1, j]))
                logging.debug(
                    'Beam {}, leaf pair {}, control point {}: Dynamic closed pair '
                    .format(beam.Name, j + 1, i + 1) +
                    'should be moved from {} to {}'
                    .format(initial_beam_mlc[i, 0, j], beam_mlc.banks[i, 0, j]))
    if np.all(np.equal(initial_beam_mlc, beam_mlc.banks)):
        logging.debug('Beam {} Filtered and initial arrays are equal. No filtering applied'.format(beam.Name))
    else:
        # Set the leaf positions to the np array (one-by-one...ugh)
        for cp in range(len(beam.Segments)):
            lp = beam.Segments[cp].LeafPositions
            for l in range(len(lp[0])):
                lp[0][l] = beam_mlc.banks[l, 0, cp]
                lp[1][l] = beam_mlc.banks[l, 1, cp]
            beam.Segments[cp].LeafPositions = lp
    return None


def filter_leaves(beam):
    """ Examine all leaves that are currently set to be at a minimum leaf gap. If those leaves
        are not moving from control point to control point, then place them such that they will
        be behind the jaw once the set-back is in place. Note that the actual calculation here is
        to place the leaf-pair at: Original Gap position + 0.8 mm + RS Minimum Leaf Jaw Overlap
        :param beam: A beam class object
        :return error: A string documenting success or failure"""
    s0 = beam.Segments[0]
    a = s0.JawPositions[1] - s0.JawPositions[0]
    b = s0.JawPositions[3] - s0.JawPositions[2]
    equivalent_square_field_size = 2 * a * b / (a + b)
    if equivalent_square_field_size < 3.:
        # TODO: Reenable for small field sizes or use offset
        mlc_filter = True
        mlc_filter = False
    else:
        mlc_filter = False

    if not mlc_filter:
        error = "MLC filtering unnecessary, field size is larger than 3 cm^2"
        return error
    # For some bizzare reason, the __init__ method of beam does not pull the data from
    # the MLC MachineReference physics. So we are searching for the machine directly here.
    beam_mlc = mlc_properties(beam)

    if beam_mlc.mlc_retracted:
        error = "MLC filtering failed. MLC retracted"
        return error
    if not beam_mlc.has_segments:
        error = "MLC filtering failed. No segments"
        return error
    # Find the first and last leaf that is not covered by the jaw if the jaw was set exactly to the leaf boundaries
    # The indexing on the MLC goes from 0, (at the x1) jaw to the maximum at the y1 jaw
    max_open = beam_mlc.max_opening()
    x1_jaw = max_open['max_open_x1']
    x2_jaw = max_open['max_open_x2']
    # Leaves that are outside the y-jaw positions and outside left and right jaw positions are moved to
    # the RS endorsed distance behind the jaws
    offset = beam_mlc.leaf_jaw_overlap + 0.8
    # Find the leaves needing adjustment
    closed_leaves = beam_mlc.stationary_leaf_gaps()
    # Store the initial position of the leaves to see if filtering will be necessary
    initial_beam_mlc = np.copy(beam_mlc.banks)
    # Loop over leaves
    for i in range(beam_mlc.banks.shape[0]):
        # Loop over control points
        for j in range(beam_mlc.banks.shape[2]):
            # If this is part of the closed leaf range, then evaluate which jaw it is closest to.
            if np.all(closed_leaves[i, 0, j]):
                x1_diff = abs(beam_mlc.banks[i, 0, j] - x1_jaw)
                x2_diff = abs(beam_mlc.banks[i, 0, j] - x2_jaw)
                if x1_diff <= x2_diff:
                    # This leaf should close behind the x1_jaw
                    beam_mlc.banks[i, 0, j] = x1_jaw - offset - beam_mlc.min_gap_moving
                    beam_mlc.banks[i, 1, j] = x1_jaw - offset
                    logging.debug(
                        'Beam {}, leaf pair {}, control point {}: Dynamic closed pair '
                        .format(beam.Name, j + 1, i + 1) +
                        'should be moved from {} to {}'
                        .format(initial_beam_mlc[i, 1, j], beam_mlc.banks[i, 1, j]))
                elif x1_diff > x2_diff:
                    # This leaf should close behind the x1_jaw
                    beam_mlc.banks[i, 0, j] = x2_jaw + offset
                    beam_mlc.banks[i, 1, j] = x2_jaw + offset + beam_mlc.min_gap_moving
                    logging.debug(
                        'Beam {}, leaf pair {}, control point {}: Dynamic closed pair '
                        .format(beam.Name, j + 1, i + 1) +
                        'should be moved from {} to {}'
                        .format(initial_beam_mlc[i, 0, j], beam_mlc.banks[i, 0, j]))

    if np.all(np.equal(initial_beam_mlc, beam_mlc.banks)):
        logging.debug('Beam {} Filtered and initial arrays are equal. No filtering applied'.format(beam.Name))
    else:
        # Set the leaf positions to the np array (one-by-one...ugh)
        for cp in range(len(beam.Segments)):
            lp = beam.Segments[cp].LeafPositions
            for l in range(len(lp[0])):
                lp[0][l] = beam_mlc.banks[l, 0, cp]
                lp[1][l] = beam_mlc.banks[l, 1, cp]
            beam.Segments[cp].LeafPositions = lp
        error = None
        return error


def check_mlc_jaw_positions(jaw_positions, mlc_positions):
    """
    Check the incoming jaw positions against machine constraints
    :param jaw_positions: {'X1': l_jaw, 'X2': r_jaw, 'Y1': t_jaw, 'Y2': b_jaw}
    :param mlc_data: mlc_positions class object
    :return: error

    Sample code:
    # For a current beamset called 'beamset'
    for b in beamset.Beams
        mlc_positions = mlc_properties(b)
        jaw_positions = {
            'X1': b.Segments[0].JawPositions[0],
            'X2': b.Segments[0].JawPositions[1],
            'Y1': b.Segments[0].JawPositions[2],
            'Y2': b.Segments[0].JawPositions[3]}
        error = check_mlc_jaw_positions(jaw_positions, mlc_positions)

    """

    # Maximum a single leaf can extend from the carriage (jaw)
    maximum_leaf_out_of_carriage = mlc_positions.max_leaf_carriage
    error = ''
    # if ciao is not None:
    #     ciao = maximum_leaf_carriage_extent(beam=beam)
    max_travel = mlc_positions.max_travel()
    # Find the maximally extended MLC in each bank
    max_x1_bank = np.amax(max_travel[:, 0], axis=0)
    min_x2_bank = np.amin(max_travel[:, 1], axis=0)

    # delta's are the maximum extent of the MLC leaves away from the jaw for this segment
    if max_travel is not None and not mlc_positions.mlc_retracted:
        delta_x1 = jaw_positions['X1'] - max_x1_bank
        delta_x2 = jaw_positions['X2'] - min_x2_bank
    else:
        # The beam has no segments, jaws only. Set these variables to something that does not influence calc
        # i.e. return no violation
        delta_x1 = delta_x2 = 0

    if abs(delta_x1) >= maximum_leaf_out_of_carriage:
        error = 'Maximum leaf limit violated for X1. '
    if abs(delta_x2) > maximum_leaf_out_of_carriage:
        error += 'Maximum leaf limit violated for X2'
    if error:
        logging.debug('MLC Out of Carriage limit reached with proposed jaw positions: ' +
                      'Maximum A MLC = {}, X1 = {}: '.format(abs(delta_x1), jaw_positions['X1']) +
                      'Maximum B MLC = {}, X2 = {}'.format(abs(delta_x2), jaw_positions['X2']))
    return error


def lock_jaws(plan, beamset, beam_name, limits):
    """

    Args:
        plan: pl:w
        an from RS
        beamset: beamset from RS
        beam_name: beam name str
        limits: {
            'x1': flt, Right Jaw
            'x2': flt, Left Jaw
            'y1': flt, Bottom Jaw,
            'y2': flt, Top Jaw
            'lock': T/F, Jah Rule Mon}

    Returns:
    message (str) result
    """
    # Find the optimization index corresponding to this beamset
    opt_index = PlanOperations.find_optimization_index(plan=plan,
                                                       beamset=beamset)
    if limits['lock']:
        jaw_rule_mon = 'Lock to limits'
    else:
        jaw_rule_mon = 'Use limits as max'
    plan_opt = plan.PlanOptimizations[opt_index].OptimizationParameters
    for ts in plan_opt.TreatmentSetupSettings:
        # If StX overwrite to leaf extent in y
        machine_ref = ts.ForTreatmentSetup.MachineReference.MachineName
        if machine_ref == 'TrueBeamSTx':
            limits['y1'] = -10.8
            limits['y2'] = 10.8
        for b in ts.BeamSettings:
            if b.ForBeam.Name == beam_name:
                try:
                    # Uncomment to automatically set jaw limits
                    b.EditBeamOptimizationSettings(
                        JawMotion=jaw_rule_mon,
                        LeftJaw=limits['x1'],
                        RightJaw=limits['x2'],
                        TopJaw=limits['y1'],
                        BottomJaw=limits['y2'],
                        SelectCollimatorAngle='False',
                        AllowBeamSplit='False',
                        OptimizationTypes=['SegmentOpt', 'SegmentMU'])
                    message += f"Beam {beam_name} locked to " \
                               + "[{x1},{x2},{y1},{y2}]".format(
                        x1=limits['x1'],
                        x2=limits['x2'],
                        y1=limits['y1'],
                        y2=limits['y2'])
                except:
                    message = "Could not change beam settings to change jaw sizes"
                break
    return message


def lock_jaws_to_current(plan_opt):
    """
    Acquire the current jaw positions and use them to lock the beams.
    Args:
        plan_opt:

    Returns:

    """
    jaw_positions = {}
    message = ""
    for treatsettings in plan_opt.OptimizationParameters.TreatmentSetupSettings:
        for b in treatsettings.BeamSettings:
            s0 = b.ForBeam.Segments[0]
            jaw_positions[b.ForBeam.Name] = {
                'x1': math.ceil(10 * s0.JawPositions[0]) / 10,
                'x2': math.floor(10 * s0.JawPositions[1]) / 10,
                'y1': math.ceil(10 * s0.JawPositions[2]) / 10,
                'y2': math.floor(10 * s0.JawPositions[3]) / 10}

    plan_opt.ResetOptimization()
    for treatsettings in plan_opt.OptimizationParameters.TreatmentSetupSettings:
        for b in treatsettings.BeamSettings:
            b_name = b.ForBeam.Name
            try:
                # Uncomment to automatically set jaw limits
                b.EditBeamOptimizationSettings(
                    JawMotion='Lock to limits',
                    LeftJaw=jaw_positions[b_name]['x1'],
                    RightJaw=jaw_positions[b_name]['x2'],
                    TopJaw=jaw_positions[b_name]['y1'],
                    BottomJaw=jaw_positions[b_name]['y2'],
                    SelectCollimatorAngle='False',
                    AllowBeamSplit='False',
                    OptimizationTypes=['SegmentOpt', 'SegmentMU'])
                message += f"Beam {b_name} locked to " \
                           + "[{x1},{x2},{y1},{y2}]\n".format(
                    x1=jaw_positions[b_name]['x1'],
                    x2=jaw_positions[b_name]['x2'],
                    y1=jaw_positions[b_name]['y1'],
                    y2=jaw_positions[b_name]['y2'])
            except:
                message = "Could not change beam settings to change jaw sizes"
    return message


def check_y_jaw_positions(jaw_positions, beam):
    """
    Make sure setting the jaw positions to the proposed limits does not open past available MLC or
    past jaw overtravel limits
    :param jaw_positions:
    :param beam: RS beam object
    :return: error, if error is None, then no error is detected
    """

    error = ''
    current_machine_name = beam.MachineReference.MachineName
    machine_db = connect.get_current('MachineDB')
    current_machine = machine_db.GetTreatmentMachine(machineName=current_machine_name,
                                                     lockMode=None)
    # Maximum jaw overtravel (minimum) position
    min_y2_jaw_limit = current_machine.Physics.JawPhysics.MinBottomJawPos
    min_y1_jaw_limit = - min_y2_jaw_limit

    if beam.DeliveryTechnique == 'TomoHelical':
        error = 'Tomotherapy helical jaw checking is not supported.'
        return error

    # Make sure beam has control points
    try:
        s0 = beam.Segments[0]
    except AttributeError:
        logging.debug('beam: {} is a jaw-only field, without segments'.format(beam.Name))
        return error

    # Maximum MLC defined positions: Leaf Center + 0.2 Leaf_Width this ensures at least a full millimeter
    # of cushion for jaw inaccuracies on a 5 mm leaf and 2 mm on a 1 cm leaf
    current_mlc_physics = current_machine.Physics.MlcPhysics
    max_y1_jaw_limit = current_mlc_physics.UpperLayer.LeafCenterPositions[0] - \
                       0.2 * current_mlc_physics.UpperLayer.LeafWidths[0]
    n_leaves = len(current_mlc_physics.UpperLayer.LeafCenterPositions)
    max_y2_jaw_limit = current_mlc_physics.UpperLayer.LeafCenterPositions[n_leaves - 1] + \
                       0.2 * current_mlc_physics.UpperLayer.LeafWidths[n_leaves - 1]

    # Check jaws
    if jaw_positions['Y1'] > min_y1_jaw_limit:
        error += 'Beam {}: Y1 jaw overtravel will be violated at Y1 = {}'.format(
            beam.Name, jaw_positions['Y1'])
    if jaw_positions['Y1'] < max_y1_jaw_limit:
        error += 'Beam {}: Y1 jaw position exceeds MLC-delineated boundary at Y1 = {}'.format(
            beam.Name, jaw_positions['Y1'])
    if jaw_positions['Y2'] < min_y2_jaw_limit:
        error += 'Beam {}: Y2 jaw overtravel will be violated at Y2 = {}'.format(
            beam.Name, jaw_positions['Y2'])
    if jaw_positions['Y2'] > max_y2_jaw_limit:
        error += 'Beam {}: Y2 jaw position exceeds MLC-delineated boundary at Y2 = {}'.format(
            beam.Name, jaw_positions['Y2'])

    return error


def rounded_jaw_positions(beam):
    """
    compute the jaw positions that will satisfy machine constraints and:
    -For small fields:
        Use jaw setbacks of 0.8 mm (X) and 0.2 mm (Y)
        *This will allow the full MLC leaf end to be defining the field
        *Avoid fields being defined by less accurate jaw positions in Y
        * mlc_filtering should be applied before this step to eliminate incorrect dynamic leaves
    -For non-small fields:
        Try to round the jaws to the nearest open millimeter. If this would open the bank past
        the MLC-defined region, leave a leaf too far from the carriage, or cause a jaw overtravel
        then round the jaws closed.
    :param beam: RS beam
    :return: {X1=l_jaw (left), X2=r_jaw (right), Y1=t_jaw (top), Y2=b_jaw (bottom)}
    """
    jaw_positions = {}

    s0 = beam.Segments[0]
    # Find the result of setting the jaws open
    round_open_l_jaw = math.floor(10 * s0.JawPositions[0]) / 10
    round_open_r_jaw = math.ceil(10 * s0.JawPositions[1]) / 10
    round_open_t_jaw = math.floor(10 * s0.JawPositions[2]) / 10
    round_open_b_jaw = math.ceil(10 * s0.JawPositions[3]) / 10
    # Compute closed jaw positions
    round_closed_l_jaw = math.ceil(10 * s0.JawPositions[0]) / 10
    round_closed_r_jaw = math.floor(10 * s0.JawPositions[1]) / 10
    round_closed_t_jaw = math.ceil(10 * s0.JawPositions[2]) / 10
    round_closed_b_jaw = math.floor(10 * s0.JawPositions[3]) / 10

    # Potential options
    use_jaw_offset = False
    use_round_open = False
    use_round_closed = False
    # Check for the equivalent square area, and do not use jaw offsets if the limit is larger than 3 cm^2
    # get the ciao for this beam
    a = s0.JawPositions[1] - s0.JawPositions[0]
    b = s0.JawPositions[3] - s0.JawPositions[2]
    equivalent_square_field_size = 2 * a * b / (a + b)
    if equivalent_square_field_size < 3.:
        use_jaw_offset = True
        # TODO: Use Jaw Offset is not working correctly in 11B. Disabled for now.
    else:
        use_round_open = True
    # For some bizzare reason, the __init__ method of beam does not pull the data from
    # the MLC MachineReference physics. So we are searching for the machine directly here.
    current_machine = GeneralOperations.get_machine(machine_name=beam.MachineReference.MachineName)
    # Maximum jaw overtravel (minimum) position
    current_mlc_physics = current_machine.Physics.MlcPhysics

    # If the target is small, try to use jaw offsets.
    beam_mlc = mlc_properties(beam)
    if use_jaw_offset:
        x_jaw_offset = 0.8
        y_jaw_offset = 0.2
        # Initialize the mlc_properties class
        # If we can't compute a ciao, or the MLC is retracted, just use open settings.
        if beam_mlc.mlc_retracted or not beam_mlc.has_segments:
            if beam_mlc.mlc_retracted:
                logging.debug('MLC is retracted. Proceeding with jaw-only field settings')
            use_round_open = True
            use_jaw_offset = False
        else:
            # Now find the maximum Top and Bottom MLC positions
            # Raystation starts moving leaves to the midplane, so we want to find the first open, and
            # last open MLC leaf pair.
            # compute leaf difference
            max_open = beam_mlc.max_opening()
            [max_open_x1, max_open_x2, max_open_y1, max_open_y2] = max_open['max_open_x1'], max_open['max_open_x2'], \
                                                                   max_open['max_open_y1'], max_open['max_open_y2']
            x1_jaw_standoff = math.floor(10 * (max_open_x1 - x_jaw_offset)) / 10
            x2_jaw_standoff = math.ceil(10 * (max_open_x2 + x_jaw_offset)) / 10
            y1_jaw_standoff = math.floor(10 * (max_open_y1 - y_jaw_offset)) / 10
            y2_jaw_standoff = math.ceil(10 * (max_open_y2 + y_jaw_offset)) / 10
    else:
        logging.debug('Beam {}: X1:{}, X2:{}, Y1:{}, Y2:{}; Calculated Eq Square Field {}'.format(
            beam.Name, s0.JawPositions[0], s0.JawPositions[1], s0.JawPositions[2], s0.JawPositions[3],
            equivalent_square_field_size
        ))
    # Check jaws
    # Try to use Jaw Standoff jaw offsets first. Then, if that violates a machine constraint
    # Try to set the jaws based on rounding open, if that still violates the machine constraints
    # Round the jaws closed.
    if use_jaw_offset:
        jaw_positions['Y1'] = y1_jaw_standoff
        jaw_positions['Y2'] = y2_jaw_standoff
        jaw_positions['X1'] = x1_jaw_standoff
        jaw_positions['X2'] = x2_jaw_standoff
        error_y_msg = check_y_jaw_positions(jaw_positions, beam)
        error_x_msg = check_mlc_jaw_positions(jaw_positions, beam_mlc)
        if error_x_msg or error_y_msg:
            # Default then to round open
            use_round_open = True
        else:
            logging.debug('Beam: {}: Equivalent Sq. Field Size is {}, Jaw Standoff offsets used'.format(
                beam.Name, equivalent_square_field_size))
    if use_round_open:
        jaw_positions['Y1'] = round_open_t_jaw
        jaw_positions['Y2'] = round_open_b_jaw
        jaw_positions['X1'] = round_open_l_jaw
        jaw_positions['X2'] = round_open_r_jaw
        error_y_msg = check_y_jaw_positions(jaw_positions, beam)
        error_x_msg = check_mlc_jaw_positions(jaw_positions, beam_mlc)
        if error_y_msg or error_x_msg:
            # Default then to rounding both jaws closed
            use_round_closed = True
            if error_y_msg:
                logging.debug('Beam {} Y-Jaws: could not be rounded open, error {}'.format(beam.Name, error_y_msg))
            if error_x_msg:
                logging.debug('Beam {} X-Jaws: could not be rounded open, error {}'.format(beam.Name, error_x_msg))
    if use_round_closed:
        jaw_positions['Y1'] = round_closed_t_jaw
        jaw_positions['Y2'] = round_closed_b_jaw
        jaw_positions['X1'] = round_closed_l_jaw
        jaw_positions['X2'] = round_closed_r_jaw
        error_y_msg = check_y_jaw_positions(jaw_positions, beam)
        error_x_msg = check_mlc_jaw_positions(jaw_positions, beam_mlc)
        if error_y_msg:
            logging.debug('Beam {} Y-Jaws: could not be rounded, error {}'.format(beam.Name, error_y_msg))
        if error_x_msg:
            logging.debug('Beam {} X-Jaws: could not be rounded, error {}'.format(beam.Name, error_x_msg))
    return jaw_positions


def jaws_rounded(beam):
    """
    Checks a beam to see if it has been rounded.
    Note, we presume only the first segment needs to be checked.
    :param beam: RS beam scriptable object
    :return: True if jaws are already rounded. False otherwise.
    """
    rounded = True

    s0 = beam.Segments[0]
    j0 = rounded_jaw_positions(beam)
    if (s0.JawPositions[0] != j0['X1'] or
            s0.JawPositions[1] != j0['X2'] or
            s0.JawPositions[2] != j0['Y1'] or
            s0.JawPositions[3] != j0['Y2']):
        rounded = False

    return rounded


def round_jaws(beamset):
    """
    Rounds the jaws.
    For each beam, the first segment is examined for appropriate rounding.
    Rounding is by default, to round open. However, if insufficient MLC travel is available, the X jaws will be
    rounded closed.
    Open: X1/Y1 will be rounded down to nearest mm, X2/Y2 rounded up
    Closed: X2/Y1 will be rounded down to nearest mm, X1/Y2 rounded up
        note X1=l_jaw (left), X2=r_jaw (right), Y1=t_jaw (top), Y2=b_jaw (bottom)
    :param beamset: RS beamset
    :return: success: boolean indicating adjustments were successful
    """
    for b in beamset.Beams:
        error = filter_leaves(b)
        if error is not None:
            logging.debug(error)
        else:
            logging.debug('Beam {} filtered'.format(b.Name))

        if not jaws_rounded(beam=b):
            s0 = b.Segments[0]
            init_positions = [s0.JawPositions[0], s0.JawPositions[1], s0.JawPositions[2], s0.JawPositions[3]]
            j0 = rounded_jaw_positions(b)
            for s in b.Segments:
                s.JawPositions = [j0['X1'], j0['X2'], j0['Y1'], j0['Y2']]
            GeneralOperations.logcrit('Beam {}: jaw positions changed '.format(b.Name) +
                                      '<X1: {0:.2f}->{1:.2f}>, '.format(init_positions[0], s.JawPositions[0]) +
                                      '<X2: {0:.2f}->{1:.2f}>, '.format(init_positions[1], s.JawPositions[1]) +
                                      '<Y1: {0:.2f}->{1:.2f}>, '.format(init_positions[2], s.JawPositions[2]) +
                                      '<Y2: {0:.2f}->{1:.2f}>'.format(init_positions[3], s.JawPositions[3]))
        else:
            GeneralOperations.logcrit('Beam {}: jaw positions do not need rounding.'.format(b.Name))
    success = True
    return success


def mu_rounded(beam):
    """
    Compute the monitor units for the raystation beam to the nearest MU using the Round_Half_Up strategy
    :param beam:
    :return: a rounded float of the beam MU
    """
    from decimal import Decimal, ROUND_HALF_UP

    init_mu = beam.BeamMU
    dec_mu = Decimal(init_mu).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
    return float(dec_mu)


def mu_is_rounded(beam):
    """
    Determine if supplied beam has MU rounded to nearest whole MU
    :param beam: raystation beam object
    :return:
    """
    tolerance = 1e-6
    rounded = True
    init_mu = beam.BeamMU
    rounded_mu = mu_rounded(beam)
    if abs(init_mu - rounded_mu) > tolerance:
        rounded = False

    return rounded


def round_mu(beamset):
    """
    Rounds to the nearest MU
    :param beamset:
    :return: success: logical
    """
    if 'Tomo' in beamset.DeliveryTechnique:
        logging.debug('Round MU is not a good idea on a Tomo plan.')
        success = False
        return success

    for b in beamset.Beams:
        if mu_is_rounded(b):
            GeneralOperations.logcrit('Beam {} already has rounded MU {}'.format(b.Name, b.BeamMU))
        else:
            mu_i = b.BeamMU
            b.BeamMU = mu_rounded(b)
            GeneralOperations.logcrit('Beam {0} MU changed from {1:.2f} to {2}'.format(b.Name, mu_i, b.BeamMU))
    return True


def exists_dsp(beamset, dsps):
    """See if rois is in the list"""
    if type(dsps) is not list:
        dsps = [dsps]

    defined_dsps = []
    for p in beamset.DoseSpecificationPoints:
        defined_dsps.append(p.Name)

    dsp_exists = []

    for p in dsps:
        i = 0
        exact_match = False
        if p in defined_dsps:
            while i < len(defined_dsps):
                if p == defined_dsps[i]:
                    exact_match = True
                i += 1
            if exact_match:
                dsp_exists.append(True)
            else:
                dsp_exists.append(False)
        else:
            dsp_exists.append(False)

    return dsp_exists


def dsp_matches_rx(beamset, dsp):
    """

    :param beamset: raystation beamset
    :param dsp: Dose specification point name (string)
    :param rx_dose: prescription dose
    :return: True if total dose match
    """
    tolerance = 0.001
    number_of_fractions = beamset.FractionationPattern.NumberOfFractions
    rx_dose = beamset.Prescription.PrimaryPrescriptionDoseReference.DoseValue / number_of_fractions
    if exists_dsp(beamset, dsps=dsp):
        total_dose = 0
        for bd in beamset.FractionDose.BeamDoses:
            if bd.UserSetBeamDoseSpecificationPoint.Name == dsp:
                if bd.DoseAtPoint.DoseValue is not None:
                    total_dose += bd.DoseAtPoint.DoseValue
                else:
                    return False
        if abs(total_dose - rx_dose) > tolerance:
            logging.debug('Dose specification point {} does not match fractional rx dose {}'.format(
                dsp, rx_dose))
            return False
        else:
            return True
    else:
        logging.warning('Dsp point {} does not exist'.format(dsp))


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

    logging.debug('rx = {}'.format(rx))

    xpos = None
    tolerance = 1e-4

    xmax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.x
    ymax = plan.TreatmentCourse.TotalDose.InDoseGrid.NrVoxels.y
    xcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.x
    ycorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.y
    zcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.z
    xsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.x
    ysize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.y
    zsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.z

    if np.amax(pd_np) < rx:
        logging.debug('max = {}'.format(np.amax(pd_np)))
        logging.debug('target = {}'.format(rx))
        raise ValueError('Max beam dose is too low. Cannot find a DSP. Max Dose in Beamset is {}, for Rx {}'.format(
            np.amax(pd_np), rx))

    rx_points = np.array([])
    while rx_points.size == 0:
        t_init = tolerance
        rx_points = np.argwhere(abs(rx - pd_np) <= tolerance)
        tolerance = t_init * 1.1
    logging.info('Tolerance used for rx agreement was +/- {} Gy'.format(t_init))

    matches = np.empty(np.size(rx_points, 0))

    for b in beam_set.FractionDose.BeamDoses:
        pd = np.array(b.DoseValues.DoseData)
        # The dose grid is stored [z: I/S, y: P/A, x: R/L], so swap x and z
        pd = pd.swapaxes(0, 2)
        # Numpy does evaluation of advanced indices column wise:
        # rso[sheets, columns, rows]
        # Calculation organizes points by the MU contributed by each beam. The point
        # which has the closest dose from each beam to the MU used by the beam will be used
        # below
        matches += abs(pd[rx_points[:, 0], rx_points[:, 1], rx_points[:, 2]] / rx -
                       b.ForBeam.BeamMU / tot)

    min_i = np.argmin(matches)
    xpos = rx_points[min_i, 0] * xsize + xcorner + xsize / 2
    ypos = rx_points[min_i, 1] * ysize + ycorner + ysize / 2
    zpos = rx_points[min_i, 2] * zsize + zcorner + zsize / 2

    return [xpos, ypos, zpos]


def find_dsp_centroid(plan, beam_set, percent_max=None):
    """
    Find the centroid of points at or above 98% or percent_max of the maximum dose in the grid
    :param plan: current plan
    :param beam_set: current beamset
    :param percent_max: percentage of maximum dose, above which points will be included
    :return: a list of [x, y, z] coordinates on the dose grid
    """
    # Get the MU weights of each beam
    tot = 0.
    for b in beam_set.Beams:
        tot += b.BeamMU

    # Search the fractional dose grid
    # The dose grid is stored by RS as a numpy array
    pd = beam_set.FractionDose.DoseValues.DoseData

    # The dose grid is stored [z: I/S, y: P/A, x: R/L]
    pd = pd.swapaxes(0, 2)

    if percent_max is None:
        rx = np.amax(pd) * 98. / 100.
    else:
        rx = np.amax(pd) * percent_max / 100.

    tolerance = 1e-2

    xcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.x
    ycorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.y
    zcorner = plan.TreatmentCourse.TotalDose.InDoseGrid.Corner.z
    xsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.x
    ysize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.y
    zsize = plan.TreatmentCourse.TotalDose.InDoseGrid.VoxelSize.z

    rx_points = np.array([])
    # Find the an array of points with dose > rx
    # if there are no points with this dose, look for points with a lower percentage
    t = 1
    while rx_points.size == 0:
        t_init = t
        rx_points = np.argwhere(pd >= rx * t)
        t = t_init - tolerance
    logging.info('Tolerance used for the supplied dose {} agreement was > {} Gy'.format(rx, rx * t_init))

    logging.debug('Finding centroid of matching dose points')
    length = rx_points.shape[0]  # total number of points
    n_x_pos = rx_points[:, 0] * xsize + xcorner + xsize / 2  # points in RS coordinates
    n_y_pos = rx_points[:, 1] * ysize + ycorner + ysize / 2
    n_z_pos = rx_points[:, 2] * zsize + zcorner + zsize / 2
    xpos = np.sum(n_x_pos) / length  # average position
    ypos = np.sum(n_y_pos) / length
    zpos = np.sum(n_z_pos) / length

    return [xpos, ypos, zpos]


def set_dsp(plan, beam_set, percent_rx=100., method='MU'):
    """
    Set a dose specification point using the current beamset prescription.
    :param plan: RS plan object
    :param beam_set: Rs beam_set object
    :param percent_rx: The percentage of the prescription value to use in calculating the desired
        DSP dose, e.g. 100% of Rx is the prescription dose exactly.
    :param method: the method to use in selecting the DSP point to use
        MU chooses the DSP that most closely matches the MU_Beam/MU_TOTAL
        Centroid chooses the point that is in the centroid of all DSP points
    :return:
    """
    try:
        rx = beam_set.Prescription.PrimaryPrescriptionDoseReference.DoseValue * percent_rx / 100.
    except AttributeError:
        logging.debug('Beamset does not have a prescription')
        raise ValueError('A prescription must be set')

    fractions = beam_set.FractionationPattern.NumberOfFractions
    if rx is None:
        raise ValueError('A Prescription must be set.')
    else:
        rx = rx / fractions

    # Look for an existing suitable already assigned DSP
    try:
        existing_dsp = beam_set.FractionDose.BeamDoses[0].UserSetBeamDoseSpecificationPoint.Name
        logging.debug('Found existing DSP {} for this beamset {}'.format(
            existing_dsp, beam_set.DicomPlanLabel))
        if dsp_matches_rx(beamset=beam_set, dsp=existing_dsp):
            logging.debug('Existing DSP {} satisfies prescription for this beamset {}'.format(
                existing_dsp, beam_set.DicomPlanLabel))
            return True
    except AttributeError:
        logging.debug('No dsp in current beamset {}'.format(beam_set.DicomPlanLabel))

    if method == 'MU':
        dsp_pos = find_dsp(plan=plan, beam_set=beam_set, dose_per_fraction=rx)
    elif method == 'Centroid':
        dsp_pos = find_dsp_centroid(plan=plan, beam_set=beam_set, percent_max=98)

    if dsp_pos:
        i = 0
        dsp_name = beam_set.DicomPlanLabel

        while any(exists_dsp(beamset=beam_set, dsps=dsp_name)):
            i += 1
            dsp_name = beam_set.DicomPlanLabel + '_' + str(i)

        beam_set.CreateDoseSpecificationPoint(Name=dsp_name,
                                              Coordinates={'x': dsp_pos[0],
                                                           'y': dsp_pos[1],
                                                           'z': dsp_pos[2]})
    else:
        raise ValueError('No DSP was set, check execution details for clues.')

    # TODO: set this one up as an optional iteration for the case of multiple beams and multiple DSP's

    for i, beam in enumerate(beam_set.Beams):
        beam.SetDoseSpecificationPoint(Name=dsp_name)

    # algorithm = beam_set.FractionDose.DoseValues.AlgorithmProperties.DoseAlgorithm
    # print "\n\nComputing Dose..."
    # beam_set.ComputeDose(DoseAlgorithm=algorithm, ForceRecompute='TRUE')


def load_beams_xml(filename, beamset_name, path):
    """Load a beamset from the file located in the path in the filename:
    :param filename: The name of the xml file housing the beamset to be loaded
    :param beamset_name: name of the beamset (element) to load
    :param path: path to the xml file
    :return beams: a list of objects of type Beam"""

    beam_elements = Beams.select_element(set_level='beamset',
                                         set_type=None,
                                         set_elements='beam',
                                         set_level_name=beamset_name,
                                         filename=filename,
                                         folder=path, verbose_logging=True)

    beams = []
    for et_beamsets in beam_elements:
        beam_nodes = et_beamsets.findall('./beam')
        for b in beam_nodes:
            beam = Beam()
            beam.number = int(b.find('BeamNumber').text)
            beam.name = str(b.find('Name').text)
            beam.technique = str(b.find('DeliveryTechnique').text)
            beam.energy = str(b.find('Energy').text)

            if b.find('GantryAngle') is None:
                beam.gantry_start_angle = None
            else:
                beam.gantry_start_angle = float(b.find('GantryAngle').text)

            if b.find('GantryStopAngle') is None:
                beam.gantry_stop_angle = None
            else:
                beam.gantry_stop_angle = float(b.find('GantryStopAngle').text)

            if b.find('ArcRotationDirection') is None:
                beam.rotation_dir = None
            else:
                beam.rotation_dir = str(b.find('ArcRotationDirection').text)

            if b.find('CollimatorAngle') is None:
                beam.collimator_angle = None
            else:
                beam.collimator_angle = float(b.find('CollimatorAngle').text)

            if b.find('CouchAngle') is None:
                beam.couch_angle = None
            else:
                beam.couch_angle = float(b.find('CouchAngle').text)

            try:
                use_jaw_limits = b.find("JawLimits").text
                if use_jaw_limits == "True":
                    beam.jaw_limits = {
                        'x1': float(b.find("JawLimits").attrib["x1"]),
                        'x2': float(b.find("JawLimits").attrib["x2"]),
                        'y1': float(b.find("JawLimits").attrib["y1"]),
                        'y2': float(b.find("JawLimits").attrib["y2"]), }
                    if b.find("JawLimits").attrib["lock"] == "True":
                        beam.jaw_limits['lock'] = True
                    else:
                        beam.jaw_limits['lock'] = False
                else:
                    beam.jaw_limits = {}
            except AttributeError:
                beam.jaw_limits = {}

            try:
                if b.find('FieldWidth') is None:
                    beam.field_width = None
                else:
                    beam.field_width = float(b.find('FieldWidth').text)
            except AttributeError:
                beam.field_width = None

            try:
                if b.find('Pitch') is None:
                    beam.pitch = None
                else:
                    beam.pitch = float(b.find('Pitch').text)
            except AttributeError:
                beam.pitch = None

            try:
                if b.find('JawMode') is None:
                    beam.jaw_mode = None
                else:
                    beam.jaw_mode = b.find('JawMode').text
            except AttributeError:
                beam.jaw_mode = None

            try:
                if b.find('BackJawPosition') is None:
                    beam.back_jaw_position = None
                else:
                    beam.back_jaw_position = float(b.find('BackJawPosition').text)
            except AttributeError:
                beam.back_jaw_position = None

            try:
                if b.find('FrontJawPosition') is None:
                    beam.front_jaw_position = None
                else:
                    beam.front_jaw_position = float(b.find('FrontJawPosition').text)
            except AttributeError:
                beam.front_jaw_position = None

            try:
                if b.find('MaxDeliveryTime') is None:
                    beam.max_delivery_time = None
                else:
                    beam.max_delivery_time = float(b.find('MaxDeliveryTime').text)
            except AttributeError:
                beam.max_delivery_time = None

            try:
                if b.find('MaxGantryPeriod') is None:
                    beam.max_gantry_period is None
                else:
                    beam.max_gantry_period = float(b.find('MaxGantryPeriod').text)
            except AttributeError:
                beam.max_gantry_period is None

            try:
                if b.find('MaxDeliveryTimeFactor') is None:
                    beam.max_delivery_time_factor is None
                else:
                    beam.max_delivery_time_factor = float(b.find('MaxDeliveryTimeFactor').text)
            except AttributeError:
                beam.max_delivery_time_factor is None

            beams.append(beam)
    return beams


def check_beam_limits(beam_name, plan, beamset, limit, change=False, verbose_logging=True):
    """
    Check the current locked limit on the beams and modify the optimization limit
    :param beam_name: name of beam to be modified
    :param plan: current plan
    :param beamset: current beamset
    :param limit: list of four limit [x1, x2, y1, y2]
    :param change: change the beam limit True/False
    :param verbose_logging: turn on (True) or off (False) extensive debugging messages
    :return: success: True if limits changed or limit is satisfied by current beam limits
    """
    # Find the optimization index corresponding to this beamset
    opt_index = PlanOperations.find_optimization_index(plan=plan,
                                                       beamset=beamset,
                                                       verbose_logging=verbose_logging)
    plan_optimization_parameters = plan.PlanOptimizations[opt_index].OptimizationParameters
    ts_settings = None
    beam_found = False
    for tss in plan_optimization_parameters.TreatmentSetupSettings:
        if tss.ForTreatmentSetup.DicomPlanLabel == beamset.DicomPlanLabel:
            ts_settings = tss
            if verbose_logging:
                logging.debug('TreatmentSetupSettings:{} matches Beamset:{} looking for beam {}'.format(
                    tss.ForTreatmentSetup.DicomPlanLabel, beamset.DicomPlanLabel, beam_name))
            for bs in ts_settings.BeamSettings:
                if bs.ForBeam.Name == beam_name:
                    beam_found = True
                    current_beam = bs
                    break
                else:
                    continue
        else:
            continue

    if ts_settings is None:
        logging.exception('No treatment set up settings could be found for beamset {}'.format(
            beamset.DicomPlanLabel) + 'Contact script administrator')

    if not beam_found:
        logging.warning('Beam {} not found in beam list from {}'.format(
            beam_name, beamset.DicomPlanLabel))
        sys.exit('Could not find a beam match for setting aperture limits')

    # Check for existing aperture limit
    try:
        current_limits = current_beam.BeamApertureLimit
        if current_limits != 'NoLimit':
            existing_limits = [current_beam.ForBeam.InitialJawPositions[0],
                               current_beam.ForBeam.InitialJawPositions[1],
                               current_beam.ForBeam.InitialJawPositions[2],
                               current_beam.ForBeam.InitialJawPositions[3]]
            if verbose_logging:
                logging.debug(('aperture limits found on beam {} of initial jaw positions: x1 = {}, ' +
                               'x2 = {}, y1 = {}, y2 = {}')
                              .format(beam_name, existing_limits[0], existing_limits[1],
                                      existing_limits[2], existing_limits[3]))
        else:
            existing_limits = [None] * 4
            if verbose_logging:
                logging.debug('No limits currently exist on beam {}'.format(beam_name))

    except AttributeError:
        logging.debug('no existing aperture limits on beam {}'.format(beam_name))
        current_limits = None
        existing_limits = [None] * 4

    if current_limits == 'NoLimit':
        modified_limit = limit
        limits_met = False
        if verbose_logging:
            logging.info(('No jaw limits found on Beam {}: Jaw limits should be '
                          'x1 = {}, x2 = {}, y1 = {}, y2 = {}')
                         .format(beam_name,
                                 modified_limit[0],
                                 modified_limit[1],
                                 modified_limit[2],
                                 modified_limit[3]))

    else:
        x1 = existing_limits[0]
        x2 = existing_limits[1]
        y1 = existing_limits[2]
        y2 = existing_limits[3]
        if all([limit[0] <= x1, limit[1] >= x2, limit[2] <= y1, limit[3] >= y2]):
            limits_met = True
        else:
            limits_met = False
            modified_limit = [max(x1, limit[0]),
                              min(x2, limit[1]),
                              max(y1, limit[2]),
                              min(y2, limit[3])]
            if verbose_logging:
                logging.info(('Jaw limits found on Beam {}: Jaw limits should be changed '
                              'x1: {} => {}, x2: {} => {}, y1: {} => {}, y2: {} => {}')
                             .format(beam_name,
                                     limit[0], modified_limit[0],
                                     limit[1], modified_limit[1],
                                     limit[2], modified_limit[2],
                                     limit[3], modified_limit[3]))

    if not limits_met:
        if current_beam.ForBeam.BeamMU > 0:
            if verbose_logging:
                logging.debug('Beam has MU. Changing jaw limit with an optimized beam is not possible without reset')
            return False
        if change:
            current_beam.EditBeamOptimizationSettings(
                JawMotion='Use limits as max',
                LeftJaw=modified_limit[0],
                RightJaw=modified_limit[1],
                TopJaw=modified_limit[2],
                BottomJaw=modified_limit[3],
                SelectCollimatorAngle='False',
                AllowBeamSplit='False',
                OptimizationTypes=['SegmentOpt', 'SegmentMU'])
            logging.info('Beam {}: Changed jaw limits x1: {} => {}, x2: {} = {}, y1: {} => {}, y2: {} => {}'
                         .format(beam_name,
                                 existing_limits[0], current_beam.ForBeam.InitialJawPositions[0],
                                 existing_limits[1], current_beam.ForBeam.InitialJawPositions[1],
                                 existing_limits[2], current_beam.ForBeam.InitialJawPositions[2],
                                 existing_limits[3], current_beam.ForBeam.InitialJawPositions[3]))
            return True
        else:
            logging.info(('Aperture check shows that limit on {} are not current. Limits should be '
                          'x1 = {}, x2 = {}, y1 = {}, y2 = {}').format(beam_name,
                                                                       modified_limit[0],
                                                                       modified_limit[1],
                                                                       modified_limit[2],
                                                                       modified_limit[3]))
            return False
    else:
        logging.debug('Limits met, no changes in aperture needed')
        return True


def emc_calc_params(beamset):
    """
    For each beam, go through the beam doses, and return the statistical uncertainty and the
    MC histories used in beam beam dose. Return the maximum uncertainty and minimum MC histories.
    :param beamset: RS beamset
    :return: NormUnc (the maximum normalized uncertainty) and number of histories used in calc
    """
    max_uncertainty = 0
    min_histories = 1e10
    # Return electron monte carlo computational parameters
    for bd in beamset.FractionDose.BeamDoses:
        max_uncertainty = max(max_uncertainty, bd.DoseValues.RelativeStatisticalUncertainty)
        min_histories = min(min_histories, bd.DoseValues.AlgorithmProperties.MonteCarloHistoriesPerAreaFluence)

    return {'NormUnc': max_uncertainty, 'MinHist': min_histories}


class EmcTest:
    # Class used in output of the EMC test, where bool will be T/F depending on clinical uncertainties met
    # and hist will return the number of suggested histories if the calculation of dose needs to be rerun
    def __init__(self):
        self.bool = True
        self.hist = None


def check_emc(beamset, stat_limit=0.01, histories=5e5):
    """
    Checks the electron monte carlo accuracy to ensure statistical limit is met
    :param beamset: RS beamset
    :param stat_limit: limit on the maximum uncertainty normalized to the maximum dose
    :param histories: number of e mc histories
    :return: EmcTest: True if meeting both standard clinical goals, otherwise a new recommended number of histories
    """
    eval_current_emc = emc_calc_params(beamset)
    if eval_current_emc['MinHist'] < histories or eval_current_emc['NormUnc'] > stat_limit:
        EmcTest.bool = False
        stat_limit_hist = int(eval_current_emc['MinHist'] * (eval_current_emc['NormUnc'] / stat_limit) ** 2.)
        EmcTest.hist = max(histories, stat_limit_hist)
        logging.info('Electron MC check showed an uncertainty of {} recommend increasing histories from {} to {}'
                     .format(eval_current_emc['NormUnc'], eval_current_emc['MinHist'], EmcTest.hist))
    else:
        EmcTest.bool = True
        logging.info('Electron MC check showed clinically-acceptable uncertainty {} and histories {}'
                     .format(eval_current_emc['NormUnc'], eval_current_emc['MinHist']))

    return EmcTest
