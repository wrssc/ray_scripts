""" Load Beamset from Template


    Versions:
    01.00.00 Original submission

    Known Issues:

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by the
    Free Software Foundation, either version 3 of the License, or (at your
    option) any later version.

    This program is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License along
    with this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2022-09-21"

__version__ = "0.1.0"
__status__ = "Production"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"

__reviewed__ = ""
__raystation__ = "11"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__help__ = ""
__copyright__ = "Copyright (C) 2022, University of Wisconsin Board of Regents"

import logging
import xml
import sys
import BeamOperations
import PlanOperations
from os import path, listdir
from collections import namedtuple
from GeneralOperations import get_all_commissioned, find_scope, get_machine, logcrit
from StructureOperations import find_types
import PySimpleGUI as sg

PROTOCOL_FOLDER = r'../protocols'
INSTITUTION_FOLDER = r'UW'
BEAMSET_FOLDER = r'beamset_templates'
PATH_BEAMSETS = path.join(path.dirname(__file__),
                          PROTOCOL_FOLDER, INSTITUTION_FOLDER, BEAMSET_FOLDER)


def load_beamsets(beamset_type, beamset_modality):
    """
    params: folder: the file folder containing xml files of autoplanning protocols
    return: protocols: a dictionary containing
                       <protocol_name>: [protocol_ElementTree,
                                         path+file_name]
    """
    beamsets = {}
    # Search file list for xml files containing templates
    logging.debug('Looking for beamset types {}'.format(beamset_type))
    for f in listdir(PATH_BEAMSETS):
        if f.endswith('.xml'):
            tree = xml.etree.ElementTree.parse(path.join(PATH_BEAMSETS, f))
            if tree.getroot().tag == 'templates':
                if beamset_type in [t.text for t in tree.findall('type')] \
                        and beamset_modality in tree.find('modality').text:
                    for bs in tree.findall('beamset'):
                        n = str(bs.find('name').text)
                        beamsets[n] = [None, None]
                        beamsets[n][0] = bs
                        beamsets[n][1] = f
    return beamsets


def find_beamset_element(beamsets, beamset_name):
    beamset_et = beamsets[beamset_name][0]
    file_name = beamsets[beamset_name][1]
    return beamset_et, file_name


# TODO: add a check for existing isocenters
def get_pois(pd):
    found_poi = [p.Name for p in pd.case.PatientModel.PointsOfInterest]
    return found_poi


def get_qualities(pd):
    # Get photon beam qualities
    machine = get_machine(pd.beamset.MachineReference.MachineName)
    qualities = []
    try:
        pbb = machine.PhotonBeamQualities
    except AttributeError:
        logging.debug('No nominal energy attribute for beamset {}'.format(pd.beamset.DicomPlanLabel))
        return qualities
    for q in pbb:
        q_str = "{:.0f}".format(q.NominalEnergy)
        if q.FluenceMode:
            q_str += r' ' + q.FluenceMode
        qualities.append(q_str)
    return qualities


def get_isos(pd):
    isos = {}
    beamsets = [bs for tp in pd.case.TreatmentPlans for bs in tp.BeamSets]
    for bs in beamsets:
        for b in bs.Beams:
            if bs.DicomPlanLabel not in isos.keys():
                iso_name = bs.DicomPlanLabel + ':' + b.Isocenter.Annotation.Name
                isos[iso_name] = {'-Beamset Name-': bs.DicomPlanLabel, '-Iso Name-': b.Isocenter.Annotation.Name}
    return isos


def set_frame_visibility(window, visible_frame, frames_list):
    invisible = [f for f in frames_list if f != visible_frame]
    for i in invisible:
        window[i].update(visible=False)
    window[visible_frame].update(visible=True)


def select_checkboxes(window, select_box, box_list):
    unchecked = [c for c in box_list if c != select_box]
    for c in unchecked:
        window[c].update(False)
    window[select_box].update(True)


def update_options(window, combo_key, combo_options, combos_list):
    # Update combo boxes with list in combos_list for combo_key,
    # all others set to None
    empty_combos = [c for c in combos_list if c != combo_key]
    for e in empty_combos:
        window.Element(e).update(values=[])
        window[e].update('')
    window.Element(combo_key).update(values=combo_options)


def get_beamset_gui(pd, beamset_list, target_list, iso_list, poi_list, energy_list=None):
    beamset_selection_values = None
    dialog_name = 'Beamset Template Selection'
    frames = ['-FRAME ISO TARGET-', '-FRAME ISO EXISTING-', '-FRAME ISO POI-']
    check_boxes = ['-USE TARGET LIST-', '-USE ISO LIST-', '-USE POI LIST-']
    combos = ['-ISO TARGET-', '-ISO EXISTING-', '-ISO POI-']
    sg.ChangeLookAndFeel('DarkPurple4')
    if energy_list:
        energy_visible = True
    else:
        energy_visible = False

    top = [
        [
            sg.Text(
                dialog_name,
                size=(90, 1),
                justification='center',
                font=("Helvetica", 16),
                relief=sg.RELIEF_RIDGE
            ),
        ],
        [
            sg.Text(
                f'Please select the beamset template for  "{pd.beamset.DicomPlanLabel}"'
            )
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Combo(
                            beamset_list,
                            default_value=None,
                            size=(30, 1),
                            key="-BEAMSET TEMPLATE-"
                        )
                    ],
                ],
                title='Template Selection',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a beamset to load',
            ),
        ],
        [
            sg.Text(
                f'Please select and energy for  "{pd.beamset.DicomPlanLabel}"',
                visible=energy_visible
            )
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Combo(
                            energy_list,
                            default_value=None,
                            size=(10, 1),
                            key="-ENERGY-",
                        )
                    ],
                ],
                title='Energy Selection',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select an energy for the beams',
                visible=energy_visible
            ),
        ],
    ]
    col1 = [
        [
            sg.Checkbox(
                'Place Isocenter in a Target ROI',
                enable_events=True,
                key=check_boxes[0]
            ),
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Text('PTV Target ROIs'),
                        sg.Combo(
                            target_list,
                            readonly=True,
                            default_value=None,
                            key=combos[0],
                            size=(30, 1)
                        )
                    ],
                ],
                title='Isocenter Placement',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a target in which to place isocenter',
                visible=False,
                key=frames[0],
            ),
        ],
    ]
    col2 = [
        [
            sg.Checkbox(
                'Place Isocenter in an existing Isocenter',
                enable_events=True,
                key=check_boxes[1])
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Text('Existing Isocenters'),
                        sg.Combo(
                            iso_list,
                            readonly=True,
                            default_value=None,
                            key=combos[1],
                            size=(30, 1)
                        )
                    ],
                ],
                title='Isocenter Placement',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select a existing isocenter in which to place isocenter',
                visible=False,
                key=frames[1],
            ),
        ],

    ]
    col3 = [
        [
            sg.Checkbox(
                'Place Isocenter in an existing POI',
                enable_events=True,
                key=check_boxes[2]
            ),
        ],
        [
            sg.Frame(
                layout=[
                    [
                        sg.Text('Existing POIs'),
                        sg.Combo(
                            poi_list,
                            readonly=True,
                            default_value=None,
                            key=combos[2],
                            size=(30, 1)
                        )
                    ],
                ],
                title='Isocenter Placement',
                relief=sg.RELIEF_SUNKEN,
                tooltip='Select an existing POI in which to place isocenter',
                visible=False,
                key=frames[2],
            ),
        ],

    ]

    bottom = [
        [
            sg.Submit(tooltip='Click to submit this window'),
            sg.Cancel()
        ]
    ]
    layout = [[sg.Column(top)], [sg.Column(col1), sg.Column(col2), sg.Column(col3)], [sg.Column(bottom)]]

    window = sg.Window(
        'Beam Template Selection',
        layout,
        default_element_size=(40, 1),
        grab_anywhere=False
    )

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Cancel":
            beamset_selection_values = None
            break
        elif event == "Submit":
            beamset_selection_values = values
            break
        elif event.startswith(check_boxes[0]):
            update_options(window, combos[0], target_list, combos)
            select_checkboxes(window, check_boxes[0], check_boxes)
            set_frame_visibility(window, frames[0], frames)
        elif event.startswith(check_boxes[1]):
            update_options(window, combos[1], iso_list, combos)
            select_checkboxes(window, check_boxes[1], check_boxes)
            set_frame_visibility(window, frames[1], frames)
        elif event.startswith(check_boxes[2]):
            update_options(window, combos[2], poi_list, combos)
            select_checkboxes(window, check_boxes[2], check_boxes)
            set_frame_visibility(window, frames[2], frames)
    window.close()

    return beamset_selection_values


def beamset_dialog(pd):
    # Narrow the options list by technique
    beamset_type = pd.beamset.DeliveryTechnique
    beamset_modality = pd.beamset.Modality
    if 'Tomo' in beamset_type:
        tomo_plan = True
    else:
        tomo_plan = False
    # Initialize available beamsets which will be a dropdown selection
    beamsets = load_beamsets(beamset_type, beamset_modality)
    if not beamsets:
        sys.exit('No available templates for Beamset type:{}, Modality:{}'
                 .format(beamset_type, beamset_modality))
    beamset_list = [b for b in beamsets.keys()]

    energy_list = get_qualities(pd)
    # Get machine list
    # if tomo_plan:
    #     machines = get_all_commissioned(machine_type='Tomo')
    # else:
    #     machines = get_all_commissioned(machine_type='VMAT')
    #     machine = get_machine(pd.beamset.MachineReference.MachineName)
    #     pbb = machine.PhotonBeamQualities
    #     energy_list = []
    #     for q in pbb:
    #         q_str = q.DosimetricEnergy
    #         if q.FluenceMode:
    #             q_str += r' ' + q.FluenceMode
    #         energy_list.append(q_str)
    #
    # inputs = {'bs': 'Select Beamset', 'e': 'Select Energy'}
    # datatype = {'bs': 'combo', 'e': 'combo'}
    # initial = {'bs': beamset_list[0], 'e': energy_list[0]}
    # options = {'bs': beamset_list, 'e': energy_list}
    # required = ['bs', 'e']
    #
    # Determine isocenter positioning
    #
    # Get all targets
    # TODO check if targets have coords on this exam
    target_list = find_types(pd.case, roi_type='Ptv')
    if not target_list:
        sys.exit('No ROIs of type PTV found in this case')
    # Get all existing isocenters
    isos = get_isos(pd)
    iso_list = list(isos.keys())
    # Get all pois
    # TODO Check poi has coords on this exam
    poi_list = get_pois(pd)
    bob = get_beamset_gui(pd, beamset_list, target_list, iso_list, poi_list, energy_list)
    # Close on cancel
    if not bob:
        logging.info('Autoload cancelled by user. Beamset data not selected')
        sys.exit('Beamset data not selected. Process cancelled.')
    if bob['-ISO EXISTING-']:
        iso_target = {'ISO_0': isos[bob['-ISO EXISTING-']]['-Iso Name-']}
    else:
        iso_target = {'ISO_0': None}

    iso_target['ROI'] = bob['-ISO TARGET-']
    iso_target['POI'] = bob['-ISO POI-']
    # Parse responses
    beamset_name = bob['-BEAMSET TEMPLATE-']
    beamset_et, filename = find_beamset_element(beamsets,
                                                bob['-BEAMSET TEMPLATE-'])
    energy = bob['-ENERGY-']

    dialog_name = 'Beamset Template Selection'
    logcrit('Dialog:{}, '.format(dialog_name)
            + 'TemplateName:{}, '.format(beamset_et.find('name').text)
            + 'Iso:{}, '.format(iso_target)
            + 'Energy:{}'.format(energy))
    return beamset_name, filename, iso_target, energy


def main():
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error=[],
            patient=find_scope(level='Patient'),
            case=find_scope(level='Case'),
            exam=find_scope(level='Examination'),
            db=find_scope(level='PatientDB'),
            plan=find_scope(level='Plan'),
            beamset=find_scope(level='BeamSet'))
    if not pd.beamset:
        sys.exit('A Beamset must be loaded to proceed')
    #
    # Move the patient, not the couch, due to limited range
    current_technique = pd.beamset.DeliveryTechnique
    if 'Tomo' in current_technique:
        lateral_zero = True
        logging.info('Tomo plan selected, lateral will be set to zero')
    else:
        lateral_zero = False

    beamset_name, filename, iso, energy = beamset_dialog(pd)

    beams = BeamOperations.load_beams_xml(filename=filename,
                                          beamset_name=beamset_name,
                                          path=PATH_BEAMSETS)
    # Place isocenter
    try:
        iso_params = BeamOperations.find_isocenter_parameters(
            case=pd.case,
            exam=pd.exam,
            beamset=pd.beamset,
            iso_target=iso['ROI'],
            iso_poi=iso['POI'],
            existing_iso=iso['ISO_0'],
            lateral_zero=lateral_zero)
    except Exception:
        logging.warning(
            'Aborting, could not locate center of {}'.format(iso))
        sys.exit('Failed to place isocenter')

    # Parse Tomo versus VMAT
    if current_technique == 'TomoHelical':
        beam = beams[0]
        BeamOperations.place_tomo_beam_in_beamset(plan=pd.plan, iso=iso_params,
                                                  beamset=pd.beamset, beam=beam)
    elif current_technique == 'DynamicArc' or current_technique == 'SMLC':
        BeamOperations.place_beams_in_beamset(iso=iso_params,
                                              beamset=pd.beamset,
                                              beams=beams)
        for b in beams:
            if b.jaw_limits:
                result = BeamOperations.lock_jaws(plan=pd.plan,
                                                  beamset=pd.beamset,
                                                  beam_name=b.name,
                                                  limits=b.jaw_limits)
                logging.info(result)

        for b in pd.beamset.Beams:
            b.BeamQualityId = energy
    else:
        now_u_dunit = 'Unsupported beamset technique {}'.format(beams[0].technique)
        logging.debug('Unsupported beamset technique {}'.format(beams[0].technique))
        sys.exit(now_u_dunit)


if __name__ == '__main__':
    main()
