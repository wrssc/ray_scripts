""" Autoplanning Functions for MultiPatient and Autoloading

    Versions:
    01.00.00 Original submission

    Known Issues:

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
__date__ = '2021-06-23'

__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = '2018-Sep-05'
__raystation__ = '7.0.0.19'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import os
import xml.etree.ElementTree as Et
import re
import pandas
import logging
from collections import OrderedDict, namedtuple
from typing import NamedTuple, Union, Optional

import connect
import StructureOperations
import BeamOperations
import UserInterface
from OptimizationOperations import optimize_plan, iter_optimization_config_etree

sys.path.insert(1, os.path.join(os.path.dirname(__file__), r'../structure_definition'))
from AddSupportStructures import deploy_couch_model

InstitutionInputsSupportStructuresExamination = "Supine Patient"
InstitutionInputsSupportStructureTemplate = "UW Support"
COUCH_SOURCE_ROI_NAMES = {
    "TrueBeam": "TrueBeamCouch",
    "TomoTherapy": "TomoCouch"
}


def load_protocols(folder):
    """
    params: folder: the file folder containing xml files of autoplanning protocols
    return: protocols: a dictionary containing
                       <protocol_name>: [protocol_ElementTree,
                                         path+file_name]
    """
    protocols = {}
    # Search protocol list, parsing each XML file for protocols and goalsets
    for f in os.listdir(folder):
        if f.endswith('.xml'):
            tree = Et.parse(os.path.join(folder, f))
            if tree.getroot().tag == 'protocol':
                n = tree.find('name').text
                protocols[n] = [None, None]
                protocols[n][0] = tree.getroot()
                protocols[n][1] = f
    return protocols


def select_protocol(folder, protocol_name=None):
    """ Prompt the user for the protocol they would like to use
        param: folder: path to autoplanning files
        param: protocol_name: an optional argument to bypass the dialog
                             using the <name> protocol xml tag
        return:  (file_name, protocol_et):
               file_name: xml filename with merged path
               protocol_et: protocol elementree the user selected
    """
    protocols = load_protocols(folder=folder)
    if protocol_name:
        # Skip the dialog
        protocol_et = protocols[protocol_name][0]
        file_name = protocols[protocol_name][1]
        return file_name, protocol_et
    else:
        # Prompt user for desired protocol
        p_n = list(protocols.keys())
        #
        # Declare the dialog
        dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Protocol'},
            title='Protocol Selection',
            text='Choose a supported autoplan configuration',
            datatype={'i': 'combo'},
            initial={},
            options={'i': p_n},
            required=['i'])
        # Launch the dialog
        response = dialog.show()
        # Close on cancel
        if response == {}:
            logging.info('Autoload cancelled by user. Protocol not selected')
            sys.exit('Protocol not selected. Process cancelled.')
        # Link root to selected protocol ElementTree
        protocol_name = dialog.values['i']
        protocol_et = protocols[protocol_name][0]
        file_name = protocols[protocol_name][1]
        return file_name, protocol_et


def order_dict(protocol):
    # Return a dictionary of {'order name': order_element}
    orders = {}
    for o in protocol.findall('order'):
        orders[o.find('name').text] = o
    return orders


def find_order(protocol, order_name):
    # Look in a protocol elementtree and return an order name match
    # If more than one instance of the same order name is found,
    # or if no match is found, return none
    orders = order_dict(protocol)
    logging.debug("orders {}".format(orders))
    matched_orders = []
    for k, o in orders.items():
        if k == order_name:
            matched_orders.append(o)
    if len(matched_orders) == 1:
        return matched_orders[0]
    else:
        return None


def select_order(protocol, order_name=None):
    """
    Prompt user for the order they would like to use from the protocol
    ElementTree
    params: protocol: ElementTree object with protocol at its root
    params: bypass the dialog and return the order the user asked for
    returns: order: ElementTree object with order at root
    """
    #
    # If there is only one order in the protocol, then simply load it
    # also, if order name is set then find its match
    orders = order_dict(protocol)
    order_names = list(orders.keys())
    if order_name:
        return find_order(protocol, order_name=order_name)
    elif len(order_names) == 1:
        return orders[order_names[0]]
    else:
        # Launch a dialog for the user to select the order to review
        selected_order = UserInterface.InputDialog(
            inputs={'i': 'Select Order'},
            title='Autoplan order configuration',
            text='Choose the treatment planning order to be used',
            datatype={'i': 'combo'},
            initial={'i': order_names[0]},
            options={'i': order_names},
            required=['i'])
        # Launch the dialog
        response = selected_order.show()
        # Close on cancel
        if response == {}:
            logging.info('Autoload cancelled by user')
            sys.exit('Order not selected. Process cancelled.')
        # Link root to selected protocol ElementTree
        order_name = selected_order.values['i']
        # Update the order name
        order = orders[order_name]
        return order


def find_rx(order):
    # Take in the order ElementTree and return
    # rx: a named tuple with:
    # ( target: string: name of protocol target for beamset prescription,
    #   idl: float: isodose line expressed as a percentage,
    #   fx: int: number of fractions in prescription of order,
    #   dose: float: nominal plan dose in cGy)
    # Find prescription element
    Rx = namedtuple('Rx', ['target', 'idl', 'fx', 'dose', 'rois'])
    rx_elem = order.find('prescription')
    if rx_elem.find('fractions').text:
        num_fx = int(rx_elem.find('fractions').text)
    else:
        num_fx = None
    #
    # Find all <roi> in order rx
    order_targets = rx_elem.findall('roi')
    t = order_targets[0]
    # Set the nominal plan dose to the first roi found
    rx_target = t.find('name').text
    rx_volume = float(t.find('volume').text)
    rois = {}
    if t.find('dose').text:
        nominal_plan_dose = float(t.find('dose').text) * 100.  # Gy to cGy
        #
        # Ensure no other roi has a higher dose.
        for t in order_targets:
            td = float(t.find('dose').text) * 100.  # Gy to cGy
            rois[t.find('name').text] = td
            if td > nominal_plan_dose:
                nominal_plan_dose = td
                rx_target = t.find('name').text
                rx_volume = float(t.find('volume').text)
    else:
        nominal_plan_dose = None
    return Rx(target=rx_target, idl=rx_volume, fx=num_fx, dose=nominal_plan_dose, rois=rois)


def find_validation_status(order):
    """
    Find the validation status in the order.
    This module is designed to find the validation status of an order.
    If the validation status is found in the order, it extracts and returns
    the details in a dictionary format. If the validation status is not found,
    it sets default values and returns them.

    :param order: XML element containing the order information.
    :return: Dictionary containing the validation status details.
    """
    validation_element = order.find('validation')

    if validation_element:
        fields = ['validation_status', 'author', 'final_dose', 'copy_final_plan']
        values = {}

        for field in fields:
            element = validation_element.find(field)
            values[field] = element.text if element is not None else None
        status = True if values['validation_status'] == "True" else False
        author = values['author']
        final_dose = False if values['final_dose'] == "False" else True
        copy_final_plan = False if values['copy_final_plan'] == "False" else True
        validation_info = {
            'status': status,
            'author': author,
            'final_dose': final_dose,
            'copy_final_plan': copy_final_plan
        }
    else:
        validation_info = {
            'status': False,
            'author': None,
            'final_dose': True,
            'copy_final_plan': True
        }
    logging.debug(f"Validation Information: {validation_info}")
    return validation_info


def select_blocking(case):
    # TODO: Prompt user when blocking is supported in RayStation
    # Let the user pick the structures that should be available for blocking
    plan_rois = StructureOperations.find_organs_at_risk(case)
    inputs = {"Include": "Select Structures to Include in Block List"}
    datatype = {"Include": "check"}
    initial = {}
    options = {"Include": plan_rois}
    block_dialog = UserInterface.InputDialog(
        title='Block ROI Selection',
        inputs=inputs,
        datatype=datatype,
        initial=initial,
        options=options,
        required=[]
    )
    block_dialog.show()
    logging.debug('Blocking on {} selected'.format(block_dialog.values["Include"]))
    return block_dialog.values["Include"]


def place_fiducial(rso, poi_name):
    """
    Check to see if poi_name is found. If not, place the point and confirm its
    location with user.
    """
    try:
        ui = connect.get_current('ui')
        ui.TitleBar.MenuItem['Patient modeling'].Button_Patient_modeling.Click()
        ui.TabControl_ToolBar.TabItem['POI tools'].Select()
        ui.ToolPanel.TabItem['POIs'].Select()
    except Exception as e:
        logging.debug(f"Could not click on the patient modeling window {e}")

    poi = StructureOperations.find_localization_poi(case=rso.case)
    if poi:
        poi_name = poi.Name
        poi_has_coord = StructureOperations.has_coordinates_poi(case=rso.case,
                                                                exam=rso.exam,
                                                                poi=poi_name)
        if poi_has_coord:
            connect.await_user_input(
                'Ensure Correct placement of the {} Point and continue script.'.format(poi_name))
        else:
            connect.await_user_input(
                f'Localization point {poi_name} has no coordinates in this exam.'
                f' Place the point and continue the script.')

    else:
        StructureOperations.create_poi(case=rso.case,
                                       exam=rso.exam,
                                       coords=[0., 0., 0.],
                                       name=poi_name,
                                       color='Green',
                                       rs_type='LocalizationPoint')
        connect.await_user_input(
            f'Ensure Correct placement of the {poi_name} '
            f'Point and continue script.')


def query_patient_info(patient_id, first_name, last_name):
    db = connect.get_current("PatientDB")
    # Find the patient in the database
    patient_info = db.QueryPatientInfo(
        Filter={
            'FirstName': '^{0}$'.format(first_name),
            'LastName': '^{0}$'.format(last_name),
            'PatientID': '^{0}$'.format(patient_id)
        }
    )
    if len(patient_info) != 1:
        return None
    else:
        return patient_info[0]


def load_patient(patient_info):
    db = connect.get_current("PatientDB")
    patient = db.LoadPatient(PatientInfo=patient_info)
    return patient


def load_case(patient_info, case_name, patient=None):
    db = connect.get_current("PatientDB")
    if not patient:
        patient = load_patient(patient_info)
    cases = db.QueryCaseInfo(PatientInfo=patient_info)
    case_info = None
    if cases:
        for c in cases:
            if c['Name'] == case_name:
                case_info = c
                break
    if case_info:
        return patient.Cases[case_name]
    else:
        return None


def load_exam(case, exam_name):
    try:
        return case.Examinations[exam_name]
    except IndexError:
        return None


def load_plan(case, plan_name):
    try:
        info = case.QueryPlanInfo(Filter={'Name': plan_name})
    except Exception as e:
        logging.debug(f'Plan loading not possible: {e}')
        info = None
    if info:
        return case.TreatmentPlans[plan_name]
    else:
        return None


def load_beamset(plan, beamset_name):
    info = plan.QueryBeamsetInfo(Filter={'Name': beamset_name})
    if info:
        return plan.BeamSets[beamset_name]
    else:
        return None


def load_patient_data(patient_id, first_name, last_name, case_name, exam_name,
                      plan_name=None, beamset_name=None):
    """ Query's database for plan, case, and exam. Returns them as a dict. Saves patient if a
        new plan is created.

    Arguments:
        patient_id {string} -- Patient's ID in database
        first_name {string} -- Patient first name
        last_name {string} -- Patient Last Name
        case_name {string} -- RS case name
        exam_name {string} -- RS Exam Name
        plan_name {string} -- RS plan
        beamset_name {string} -- RS beamset

    Returns:
        dict -- {'Case': RS Case Object, 'Exam' RS Exam object,
                 'Plan': RS Plan Object - either existing or new}
    """
    # Initialize return variable
    patient_data = {'Error': [],
                    'Case': None,
                    'Patient': None,
                    'Exam': None,
                    'Plan': None,
                    'BeamSet': None}
    patient_info = query_patient_info(patient_id=patient_id, first_name=first_name,
                                      last_name=last_name)
    if patient_info:
        patient_data['Patient'] = load_patient(patient_info)
        patient = patient_data['Patient']
    else:
        patient_data['Error'] = [f'Patient {first_name} {last_name},'
                                 f' ID: {patient_id} not found']
        return patient_data

    # Load case
    # See if the case exists
    patient_data['Case'] = load_case(patient_info, case_name=case_name, patient=patient)
    if not patient_data['Case']:
        patient_data['Error'].append(f'Case {case_name} not found')
        return patient_data
    else:
        case = patient_data['Case']
    #
    # Load examination
    patient_data['Exam'] = load_exam(case=patient_data['Case'], exam_name=exam_name)
    if not patient_data['Exam']:
        patient_data['Error'].append(f'Exam {exam_name} not found')
        return patient_data
    else:
        exam = patient_data['Exam']
    #
    # Load the plan indicated
    # If the plan is found, cool. just make it current
    if plan_name:
        patient_data['Plan'] = load_plan(case=case, plan_name=plan_name)
        # TODO Move this to the main program as an option
        if not patient_data['Plan']:
            case.AddNewPlan(
                PlanName=plan_name,
                PlannedBy='H.A.L.',
                Comment='Diagnosis',
                ExaminationName=exam.Name,
                AllowDuplicateNames=False
            )
            patient_data['Plan'] = case.TreatmentPlans[plan_name]
        if beamset_name:
            patient_data['BeamSet'] = load_beamset(plan=patient_data['Plan'],
                                                   beamset_name=beamset_name)

    return patient_data


def set_overrides(rso):
    # Search the list of roi's. If any have form <>_Override_Tissue
    template_list = rso.db.GetTemplateMaterial()
    # Find materials needing Override
    override_rois = []
    for r in rso.case.PatientModel.RegionsOfInterest:
        pattern = re.compile("^.*_Override_.*$")
        if pattern.match(r.Name):
            override_rois.append(r.Name)
    logging.debug('Structures to override {}'.format(override_rois))
    rs_material = m = rs_m_match = None
    if override_rois:
        for o in override_rois:
            (name, status, material) = o.split("_")
            for m in template_list.Materials:
                # Generate Regex for material name
                rs_m_match = m.Name
                rs_m_match = rs_m_match.replace(" ", "")
                tissue_pattern = re.compile(r"^" + rs_m_match + r"$", re.IGNORECASE)
                if tissue_pattern.match(material):
                    rs_material = m
                    break
            try:
                rso.case.PatientModel.RegionsOfInterest[o].SetRoiMaterial(
                    Material=rs_material)
                logging.info(f"Override applied to {o} of {m.Name}: {m.MassDensity} g/cc")
            except Exception as e:
                logging.warning(f'{material} not found in material '
                                f'list using {rs_m_match}: {e}')


def fill_couch(case, exam, couch_roi_name):
    couch = case.PatientModel.StructureSets[exam.Name].RoiGeometries[couch_roi_name]
    image_bb = exam.Series[0].ImageStack.GetBoundingBox()
    extent_inf = image_bb[0]["z"]
    extent_sub = image_bb[1]["z"]

    # If inferior edge of couch is inside image boundary
    if couch.GetBoundingBox()[0]["z"] > extent_inf:
        # Extend couch until it exceeds image boundary
        # Note: A while loop is necessary because the maximum expansion is
        # 15 cm. This expansion may need to be repeated, hence the loop.
        while couch.GetBoundingBox()[0]["z"] > extent_inf:
            margin_settings = {
                'Type': "Expand",
                'Superior': 0,
                'Inferior': 15,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=exam,
                SourceRoiName=couch_roi_name,
                MarginSettings=margin_settings)

        # Perform a single contraction to match image boundaries
        contract_inf = extent_inf - couch.GetBoundingBox()[0]["z"]

        margin_settings = {
            'Type': "Contract",
            'Superior': 0,
            'Inferior': contract_inf,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
        }
        couch.OfRoi.CreateMarginGeometry(
            Examination=exam,
            SourceRoiName=couch_roi_name,
            MarginSettings=margin_settings
        )
    # If inferior edge of couch is outside image boundary
    elif couch.GetBoundingBox()[0]["z"] < extent_inf:
        # Contract couch until it is within image boundary
        while couch.GetBoundingBox()[0]["z"] < extent_inf:
            margin_settings = {
                'Type': "Contract",
                'Superior': 0,
                'Inferior': 15,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=exam,
                SourceRoiName=couch_roi_name,
                MarginSettings=margin_settings)

        # Perform a single expansion to match image boundaries
        expand_inf = couch.GetBoundingBox()[0]["z"] - extent_inf

        margin_settings = {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': expand_inf,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
        }
        couch.OfRoi.CreateMarginGeometry(
            Examination=exam,
            SourceRoiName=couch_roi_name,
            MarginSettings=margin_settings
        )
        logging.info(
            "Successfully matched the TrueBeam Couch to the inferior image boundary"
        )

    # If superior edge of couch is inside image boundary
    if couch.GetBoundingBox()[1]["z"] < extent_sub:
        # Extend couch until it exceeds image boundary
        while couch.GetBoundingBox()[1]["z"] < extent_sub:
            margin_settings = {
                'Type': "Expand",
                'Superior': 15,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=exam,
                SourceRoiName=couch_roi_name,
                MarginSettings=margin_settings
            )

        # Perform a single contraction to match image boundaries
        contract_sup = couch.GetBoundingBox()[1]["z"] - extent_sub

        margin_settings = {
            'Type': "Contract",
            'Superior': contract_sup,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
        }
        couch.OfRoi.CreateMarginGeometry(
            Examination=exam,
            SourceRoiName=couch_roi_name,
            MarginSettings=margin_settings
        )
    # If superior edge of couch is outside image boundary
    elif couch.GetBoundingBox()[1]["z"] > extent_sub:
        # Contract couch until it is within image boundary
        while couch.GetBoundingBox()[1]["z"] > extent_sub:
            margin_settings = {
                'Type': "Contract",
                'Superior': 15,
                'Inferior': 0,
                'Anterior': 0,
                'Posterior': 0,
                'Right': 0,
                'Left': 0
            }
            couch.OfRoi.CreateMarginGeometry(
                Examination=exam,
                SourceRoiName=couch_roi_name,
                MarginSettings=margin_settings
            )

        # Perform a single expansion to match image boundaries
        expand_sup = extent_sub - couch.GetBoundingBox()[1]["z"]

        margin_settings = {
            'Type': "Expand",
            'Superior': expand_sup,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0
        }
        couch.OfRoi.CreateMarginGeometry(
            Examination=exam,
            SourceRoiName=couch_roi_name,
            MarginSettings=margin_settings
        )

        logging.info(
            "Successfully matched the treatment couch to image extent."
        )


def load_supports(rso, supports, quiet=False):
    # Load the contours listed and have the user check.
    # rso: TODO fill in
    # supports: list of support structure names
    # template name: name of the RS template
    #
    # TODO: Move this to general operations and evaluate patient position
    rs_template = rso.db.LoadTemplatePatientModel(
        templateName=InstitutionInputsSupportStructureTemplate,
        lockMode='Read'
    )
    # Capture the current list of ROI's to avoid saving over them in the future
    rois = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    loaded = []
    for s in supports:
        # Check if s exists
        if StructureOperations.check_structure_exists(case=rso.case,
                                                      roi_list=rois,
                                                      option='Check',
                                                      structure_name=s):
            if rso.case.PatientModel.StructureSets[rso.exam.Name] \
                    .RoiGeometries[s].HasContours():
                loaded.append(s)

    # Compute the structures not yet named
    remain = list(set(supports) - set(loaded))
    logging.debug('Supports:{} were loaded. {} remain'.format(loaded, remain))
    couch = None
    for s in remain:
        if rso.exam.PatientPosition == 'HFS':
            if s == COUCH_SOURCE_ROI_NAMES['TrueBeam']:
                # Deploy the TrueBeam couch
                couch = deploy_couch_model(
                    rso.case,
                    support_structure_template=InstitutionInputsSupportStructureTemplate,
                    support_structures_examination=InstitutionInputsSupportStructuresExamination,
                    source_roi_names=[COUCH_SOURCE_ROI_NAMES['TrueBeam']]
                )
                break
            elif s == COUCH_SOURCE_ROI_NAMES['TomoTherapy']:
                couch = deploy_couch_model(
                    rso.case,
                    support_structure_template=InstitutionInputsSupportStructureTemplate,
                    support_structures_examination=InstitutionInputsSupportStructuresExamination,
                    source_roi_names=[COUCH_SOURCE_ROI_NAMES['TomoTherapy']]
                )
                break
        else:
            support_template = rso.db.LoadTemplatePatientModel(
                templateName=InstitutionInputsSupportStructureTemplate,
                lockMode='Read')
            if s == COUCH_SOURCE_ROI_NAMES['TrueBeam'] or \
                    s == COUCH_SOURCE_ROI_NAMES['TomoTherapy']:
                rso.case.PatientModel.CreateStructuresFromTemplate(
                    SourceTemplate=rs_template,
                    SourceExaminationName=InstitutionInputsSupportStructuresExamination,
                    SourceRoiNames=[s],
                    SourcePoiNames=[],
                    AssociateStructuresByName=True,
                    TargetExamination=rso.exam,
                    InitializationOption='AlignImageCenters'
                )
                fill_couch(case=rso.case, exam=rso.exam, couch_roi_name=s)
                couch = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries[s]
    if couch:
        remain.remove(couch.OfRoi.Name)
    if remain:
        _ = rso.db.LoadTemplatePatientModel(
            templateName=InstitutionInputsSupportStructureTemplate,
            lockMode='Read')

        rso.case.PatientModel.CreateStructuresFromTemplate(
            SourceTemplate=rs_template,
            SourceExaminationName=InstitutionInputsSupportStructuresExamination,
            SourceRoiNames=remain,
            SourcePoiNames=[],
            AssociateStructuresByName=True,
            TargetExamination=rso.exam,
            InitializationOption='AlignImageCenters'
        )
    if not quiet:
        connect.await_user_input(
            f'Ensure the supports {supports} are loaded correctly, '
            f'on exam {rso.exam.Name} and continue script')


def convert_translation_map(translation_map, unit):
    """
    Given a map of the form {RoiNameInProtocol: (RoiNameInPtPlan, Dose, Units('Gy' or 'cGy'))}
    convert it to the unit specified above
    return the translation map
    """
    tm = {}
    logging.debug('before conversion {}'.format(translation_map))
    gy = r'Gy'
    cgy = r'cGy'
    if unit != gy and unit != cgy:
        logging.warning('Unknown unit!')
        return None
    for k, v in translation_map.items():
        tm[k] = [None] * 3
        tm[k][0] = v[0]
        if unit == gy and v[2] == cgy:
            tm[k][1] = float(v[1]) / 100.
            tm[k][2] = gy
        elif unit == cgy and v[2] == gy:
            tm[k][1] = float(v[1]) * 100.
            tm[k][2] = cgy
        else:
            tm[k][1] = v[1]
            tm[k][2] = v[2]
    logging.debug('after conversion {}'.format(tm))
    return tm


def make_beamset(patient, case, exam, plan, beamset_defs):
    """Take current patient, case, exam, plan, and elements needed to
        create a RayStation beamset and add a beamset
        If the beamset name exists, add a number to the end and try again
        return the RayStation beamset script object
        """
    beamset_exists = True
    # If this beamset is found, then append 1-99 to the name and keep going
    i = 0
    new_bs_name = beamset_defs.name
    while beamset_exists:
        try:
            info = plan.QueryBeamSetInfo(Filter={'Name': '^{0}'.format(new_bs_name)})
            if info[0]['Name'] == new_bs_name:
                # Ensure the maximum DicomPlanLabel length of 16 chars is not exceeded
                if len(new_bs_name) > 14:
                    new_bs_name = beamset_defs.name[:14] + str(i).zfill(2)
                else:
                    new_bs_name = beamset_defs.name + str(i).zfill(2)
        except IndexError:
            beamset_exists = False
    # Beamset
    if beamset_defs.name != new_bs_name:
        logging.debug('Beamset {} exists! Replacing with {}'.format(beamset_defs.name, new_bs_name))
        beamset_defs.name = new_bs_name
    #
    rs_beam_set = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=beamset_defs,
                                                create_setup_beams=True)
    return rs_beam_set


def load_planning_structures(case, filename, path, workflow_name, translation_map):
    key_ps = 'planning_structure_config'
    wf = workflow_name
    # No planning structures needed
    if not wf:
        return 'NA'
    file = filename
    tree_pp = Et.parse(
        os.path.join(os.path.dirname(__file__), path, file))
    # Planning preferences loaded into dict
    dict_pp = StructureOperations \
        .iter_planning_structure_etree(tree_pp)
    # Planning preferences loaded dataframe
    df_pp = pandas.DataFrame(dict_pp[key_ps])
    # Slice for the planning structure set matching the input workflow
    df_wf = df_pp[df_pp.name == wf]

    pp = StructureOperations.PlanningStructurePreferences()
    pp.number_of_targets = int(df_wf.number_of_targets.values[0])
    if len(translation_map) < pp.number_of_targets:
        pp.number_of_targets = len(translation_map)
    pp.first_target_number = df_wf.first_target_number.values[0]
    uniform_structures = df_wf.uniform_structures.values[0]
    underdose_structures = df_wf.underdose_structures.values[0]
    try:
        inner_air_name = df_wf.inner_air_name.values[0]
    except AttributeError:
        inner_air_name = None

    if uniform_structures:
        uniform_filtered = StructureOperations.exists_roi(case=case,
                                                          rois=df_wf.uniform_structures.values[0],
                                                          return_exists=True)
        if uniform_filtered:
            pp.use_uniform_dose = True
            pp.uniform_properties['structures'] = uniform_filtered
            pp.uniform_properties['standoff'] = df_wf.uniform_standoff.values[0]
        else:
            pp.use_uniform_dose = False
    else:
        pp.use_uniform_dose = False
    dialog4_response = pp.uniform_properties

    if underdose_structures:
        under_filtered = StructureOperations.exists_roi(case=case,
                                                        rois=df_wf.underdose_structures.values[0],
                                                        return_exists=True)
        if under_filtered:
            pp.use_under_dose = True
            pp.under_dose_properties['structures'] = under_filtered
            pp.under_dose_properties['standoff'] = df_wf.underdose_standoff.values[0]
        else:
            pp.use_under_dose = False
    else:
        pp.use_under_dose = False
    dialog3_response = pp.under_dose_properties

    if inner_air_name:
        pp.use_inner_air = True
    else:
        pp.use_inner_air = False
    # TODO: move all references to dialog response to planning_prefs

    _ = {
        'number_of_targets': pp.number_of_targets,
        'generate_underdose': pp.use_under_dose,
        'generate_uniformdose': pp.use_uniform_dose,
        'generate_inner_air': pp.use_inner_air}
    dialog2_response = OrderedDict()
    logging.debug('translation map is {}'.format(translation_map))
    logging.debug('number of targets {}'.format(pp.number_of_targets))
    for k, v in translation_map.items():
        dialog2_response[v[0]] = v[1]
    # Skin-superficial
    dialog5_response = {}
    if df_wf.superficial_target_name.values[0]:
        dialog5_response['target_skin'] = True
    else:
        dialog5_response['target_skin'] = False
    # HD Ring
    if df_wf.ring_hd_name.values[0]:
        generate_ring_hd = True
        dialog5_response['ring_hd'] = generate_ring_hd
        dialog5_response['thick_hd_ring'] = df_wf.ring_hd_ExpA.values[0][0]
        dialog5_response['ring_standoff'] = df_wf.ring_hd_standoff.values[0]
    else:
        generate_ring_hd = False
        dialog5_response['ring_hd'] = generate_ring_hd
        dialog5_response['thick_hd_ring'] = None
        dialog5_response['ring_standoff'] = None
    # LD Ring
    if df_wf.ring_ld_name.values[0]:
        generate_ring_ld = True
        dialog5_response['ring_ld'] = generate_ring_ld
        dialog5_response['thick_ld_ring'] = df_wf.ring_ld_ExpA.values[0][0]
        dialog5_response['ring_standoff'] = df_wf.ring_hd_standoff.values[0]
    else:
        generate_ring_ld = False
        dialog5_response['ring_ld'] = generate_ring_ld
        dialog5_response['thick_ld_ring'] = None
    # Target rings
    if df_wf.ring_ts_name.values[0]:
        dialog5_response['target_rings'] = True
    else:
        dialog5_response['target_rings'] = False
    # OTV's
    if df_wf.otv_name.values[0]:
        dialog5_response['otv_standoff'] = df_wf.otv_standoff.values[0]
        generate_otvs = True
    else:
        dialog5_response['otv_standoff'] = None
        generate_otvs = False
    # Normal_1cm or Normal_2cm. If not declared, do not add.
    if df_wf.normal.values[0] == "Normal_2cm":
        generate_normal_2cm = True
        generate_normal_1cm = False
    elif df_wf.normal.values[0] == "Normal_1cm":
        generate_normal_1cm = True
        generate_normal_2cm = False
    else:
        generate_normal_2cm = False
        generate_normal_1cm = False
    # Skin evals
    if df_wf.skin_name.values[0]:
        generate_skin = True
        skin_contraction = df_wf.skin_ExpA.values[0][0]
    else:
        generate_skin = False
        skin_contraction = None
    StructureOperations.planning_structures(
        generate_ptvs=True,
        generate_ptv_evals=True,
        generate_otvs=generate_otvs,
        generate_skin=generate_skin,
        generate_inner_air=pp.use_inner_air,
        generate_field_of_view=True,
        generate_ring_hd=generate_ring_hd,
        generate_ring_ld=generate_ring_ld,
        generate_normal_1cm=generate_normal_1cm,
        generate_normal_2cm=generate_normal_2cm,
        generate_combined_ptv=True,
        skin_contraction=skin_contraction,
        run_status=False,
        planning_structure_selections=pp,
        dialog2_response=dialog2_response,
        dialog3_response=dialog3_response,
        dialog4_response=dialog4_response,
        dialog5_response=dialog5_response
    )
    success = 'True'
    return success


def load_configuration_optimize_beamset(
        filename: str, path: str, rso: NamedTuple, name: Optional[str] = None,
        technique: Optional[str] = None, output_data_dir: Optional[str] = None,
        bypass_user_prompts: bool = False, optimize: bool = True) -> Union[bool, str]:
    """Optimize the plan according to the specified configuration.

    Args:
        filename (str): Name of the protocol file being used.
        path (str): Path to the protocol.
        rso (NamedTuple): Tuple containing script objects for patient, case, etc.
        name (Optional[str]): Name from the beamset element.
        technique (Optional[str]): Technique from the beamset element.
        output_data_dir (Optional[str]): Directory for output data.
        bypass_user_prompts (bool): Flag to bypass user prompts. Default is False.
        optimize (bool): Flag to run optimization. Default is True.

    Returns:
        Union[bool, str]: True if plan optimized, error message if not.

    Pseudocode:
        1. Load the XML containing optimization configuration.
        2. Find the correct beamset type using name or technique.
        3. Extract the required optimization parameters.
        4. If user prompts are required, display the GUI for user inputs.
        5. Run the optimization if the optimize flag is True.
    """

    # XML target is a tag called optimization_config
    key_oc = 'optimization_config'
    tree_oc = Et.parse(
        os.path.join(os.path.dirname(__file__), path, filename))
    # Search the tree for the appropriate beamset type
    for o in tree_oc.findall('optimization_config'):
        if name:
            if o.find('name').text == name:
                t = o
                break
        elif technique:
            if o.find('technique').text == technique:
                t = o
                break
        else:
            logging.warning('Unknown optimization retrieval')
    logging.debug('Beamset type {}'.format(technique))
    logging.debug('Optimization with configuration {}'.format(t.find('name').text))
    wf = t.find('name').text
    # Optimization configurations loaded into dict
    dict_oc = iter_optimization_config_etree(tree_oc)
    # Optimization dict loaded to dataframe
    df_oc = pandas.DataFrame(dict_oc[key_oc])
    # Slice to match the input workflow
    df_wf = df_oc[df_oc.name == wf]
    # Retrieve arguments

    OptimizationParameters = {
        "initial_max_it": df_wf.initial_max_it.values[0],
        "initial_int_it": df_wf.initial_int_it.values[0],
        "second_max_it": df_wf.warmstart_max_it.values[0],
        "second_int_it": df_wf.warmstart_int_it.values[0],
        "vary_grid": df_wf.vary_grid.values[0],
        "dose_dim1": df_wf.dose_dim1.values[0],
        "dose_dim2": df_wf.dose_dim2.values[0],
        "dose_dim3": df_wf.dose_dim3.values[0],
        "dose_dim4": df_wf.dose_dim4.values[0],
        "n_iterations": df_wf.warmstart_n.values[0],
        'fluence_only': df_wf.fluence_only.values[0],
        'reset_beams': df_wf.reset_beams.values[0],
        'segment_weight': df_wf.segment_weight.values[0],
        'rescale_after_warmstart': df_wf.rescale_after_warmstart.values[0],
        'use_treat_settings': df_wf.use_treat_settings.values[0],
        'reduce_oar': df_wf.reduce_oar.values[0],
        'reduce_mod': df_wf.reduce_mod.values[0],
        'patient_db': rso.db,
        'mod_target': df_wf.mod_target.values[0],
        'block_prompt': df_wf.block_prompt.values[0],
        'robust': df_wf.robust.values[0],
        'robust_sup': df_wf.robust_sup.values[0],
        'robust_inf': df_wf.robust_inf.values[0],
        'robust_ant': df_wf.robust_ant.values[0],
        'robust_post': df_wf.robust_post.values[0],
        'robust_right': df_wf.robust_right.values[0],
        'robust_left': df_wf.robust_left.values[0],
        'position_uncertainty': df_wf.position_uncertainty.values[0],
        'output_data_dir': output_data_dir,
        "save": True,
        "close_status": True}
    #
    # Set any blocking via a user prompt
    block_prompt = df_wf.block_prompt.values[0]
    if block_prompt and not bypass_user_prompts:
        try:
            ui = connect.get_current('ui')
            ui.TitleBar.MenuItem['Plan optimization'].Button_Plan_optimization.Click()
            ui.TabControl_Modules.TabItem['Plan optimization'].Button_Plan_optimization.Click()
            ui.Workspace.TabControl['Objectives/constraints'].TabItem['Protect'].Select()
        except:
            logging.debug("Could not click on the patient protection window")
        connect.await_user_input(
            'Navigate to the Plan design page and set any blocking.')
    # Optimize the plan
    if optimize:
        optimization_report = optimize_plan(patient=rso.patient,
                                            case=rso.case,
                                            exam=rso.exam,
                                            plan=rso.plan,
                                            beamset=rso.beamset,
                                            **OptimizationParameters)
        return optimization_report
    else:
        return None

    """ try:
        optimization_report = optimize_plan(patient=rso.patient,
                        case=rso.case,
                        exam=rso.exam,
                        plan=rso.plan,
                        beamset=rso.beamset,
                        **OptimizationParameters)
        return optimization_report
    except Exception as e:
        return e
    """
