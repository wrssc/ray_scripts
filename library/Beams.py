""" Add Beams

    Contains functions required to load objectives from xml files
    add the beams to RayStation.
"""
import sys
import os
import logging
import xml.etree.ElementTree
import UserInterface
import StructureOperations
import connect


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

        machines = connect.machine_db.QueryCommissionedMachineInfo(Filter={})
        machine_list = []
        for i, m in enumerate(machines):
            if m['IsCommissioned']:
                machine_list.append(m['Name'])

        input_dialog = UserInterface.InputDialog(
            inputs={
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
                '4': 'combo',
                '5': 'combo',
                '6': 'combo',
                '7': 'combo'
            },
            initial={
                '1': 'XXXX_VMA_R0A0',
            },
            options={
                '4': machine_list,
                '5': available_modality,
                '6': available_technique,
                '7': targets
            },
            required=['2',
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

        beamset.AddDosePrescriptionToRoi(RoiName='PTV_WB_xxxx',
                                         DoseVolume=80,
                                         PrescriptionType='DoseAtVolume',
                                         DoseValue=total_dose,
                                         RelativePrescriptionLevel=1,
                                         AutoScaleDose=True)
    except Exception:
        logging.warning('Unable to set prescription')

    return beamset


def select_element(set_type, set_elements, folder=None, filename=None, set_name=None, order_name=None, protocol=None):
    """
    Function to select the correct element from an xml file

    set_type is the xml tag of the structure to find. Accepted: objectiveset, beamset
    set_elements are the leaves within the set_type (i.e. beams or objectives
    User will supply a folder, in which case, they will need to select from all files found
    a filename, in which case they select from all sets found
    a set_name which returns the exact element-tree match for that set.



    :param filename: os joined protocol name, used to directly open a file
    :param folder: folder from os to search within and prompt user to select appropriate protocol
    :param order_name: the name of order level element from xml file
    :param protocol: ElementTree-Element of the objectiveset you want

    :return: et_list: elementtree list of elements with objectives and/or objectivesets

    Usage:
    USE CASE 1:
    ## User knows the file the order is housed in but wants to select the order
    # Prompt user to select an order out of a specific file (UWBrainCNS.xml) located in
    # ../protocols/UW
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file, folder=path_protocols)

    USE CASE 2:
    ## User knows the exact order that needs to be loaded. Return only the selected order and
    ## any objectivesets in the protocol
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    file = 'UWBrainCNS.xml'
    order_name = 'GBM Brain 6000cGy in 30Fx [Single-Phase Stupp]'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file,
                                                              folder=path_protocols,
                                                              order_name=order_name)
    USE CASE 3:
    ## User will select a default objectiveset from the standard objectives directory
    objective_elements = Objectives.select_objective_protocol()

    USE CASE 4:
    ## User supplies ordername and protocol element:
    objective_elements = Objectives.select_objective_protocol(order_name=order_name,
                                                              protocol=protocol)
    :TODO add an optional arguement for finding an objectiveset or beamset exact match.

    """
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    objectives_folder = r'objectives'

    et_level = './' + set_type
    et_element = './' + set_elements
    et_list = []
    sets = {}

    # First search the file list to be searched depending on the supplied information
    # output a list of files that are to be scanned
    if filename is not None:
        # User directly supplied the filename of the protocol or file containing the set
        path_to_sets = folder
        if set_name is not None:
            if folder is None:
                path_to_sets = os.path.join(os.path.dirname(__file__),
                                            protocol_folder,
                                            institution_folder)

            if filename.endswith('.xml'):
                # Parse the xml file
                tree = xml.etree.ElementTree.parse(os.path.join(path_to_sets, filename))
                logging.debug('tree root is {}'.format(tree.getroot().tag))
                # Search first for a top level set
                sets = tree.findall(et_level)
                logging.debug('sets is {}'.format(sets))
                for s in sets:
                    logging.debug('set name is {}'.format(set_name))
                    if s.find('name').text == set_name:
                        et_list.append(s)
                        return et_list
        else:
            file_list = [filename]


    elif folder and not filename:
        # User wants to select the protocol or objectiveset from a list of xml files
        path_to_sets = os.path.join(os.path.dirname(__file__),
                                    protocol_folder,
                                    institution_folder)
        file_list = os.listdir(path_to_sets)
    else:
        # If no information was supplied look in the objectives folder
        path_to_sets = os.path.join(os.path.dirname(__file__),
                                    protocol_folder,
                                    institution_folder,
                                    objectives_folder)
        file_list = os.listdir(path_to_sets)

    # Return variable. A list of ET Elements
    if protocol is not None:
        # Search first for a top level objectiveset
        # Find the objectivesets:
        # These get loaded for protocols regardless of orders
        protocol_set = protocol.findall(et_level)
        for p in protocol_set:
            et_list.append(p)
        orders = protocol.findall('./order')
        # Search the orders to find those with objectives and return the candidates
        # for the selectable objectives
        for o in orders:
            elements = o.findall(et_element)
            if elements:
                n = o.find('name').text
                sets[n] = o
            else:
                logging.debug('No objects of type {} found in {}'.format(set_type, o.find('name').text))
    else:
        for f in file_list:
            if f.endswith('.xml'):
                # Parse the xml file
                tree = xml.etree.ElementTree.parse(os.path.join(path_to_sets, f))
                # Search first for a top level set
                if tree.getroot().tag == set_type:
                    n = tree.find('name').text
                    if n in sets:
                        # objective_sets[n].extend(tree.getroot())
                        logging.debug("Set {} already in list".format(n))
                    else:
                        sets[n] = tree
                        et_list.append(tree)
                elif tree.getroot().tag == 'protocol':
                    # Find the sets
                    # These get loaded for protocols regardless of orders
                    protocol_set = tree.findall(et_level)
                    for p in protocol_set:
                        et_list.append(p)
                    orders = tree.findall('./order')
                    # Search the orders to find those with objectives and return the candidates
                    # for the selectable objectives
                    for o in orders:
                        elements = o.findall(et_element)
                        if elements:
                            n = o.find('name').text
                            sets[n] = o
                        else:
                            logging.debug('No elements of type {} found in {}'.format(set_elements,
                                                                                      o.find('name').text))

    # Augment the list to include all xml files found with an "objectiveset" tag in name
    if order_name is not None:
        try:
            selected_order = sets[order_name]
        except KeyError:
            # This order doesn't appear to match one that has objectives in it
            # Pass an empty entry
            logging.debug('Order: {} has no {}. Protocol {} being used'.format(order_name, set_elements, set_elements))
            selected_order = None
    else:
        input_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Objective Set'},
            title='Objective Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(sets.keys())},
            required=['i'])
        response = input_dialog.show()
        # Close on cancel
        if response == {}:
            logging.info('create_objective cancelled by user')
            sys.exit('create_objective cancelled by user')
        else:
            logging.debug('User selected order: {} for objectives'.format(
                input_dialog.values['i']))
            selected_order = sets[input_dialog.values['i']]
    # Add the order to the returned list
    if selected_order is not None:
        et_list.append(selected_order)

    if et_list is not None:
        for e in et_list:
            logging.info('Objective list to be loaded {}'.format(
                e.find('name').text))
    else:
        logging.warning('objective files were not found')

    return et_list
