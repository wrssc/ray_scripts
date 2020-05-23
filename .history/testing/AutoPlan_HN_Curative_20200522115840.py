""" Auto Load Plan
    
    Automatic generation of a curative Head and Neck Plan.  
    -Load the patient and case
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
__version__ = '1.0.1'
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

import sys
import os
import csv
import logging

import GeneralOperations
import StructureOperations
import BeamOperations
import UserInterface


def main():
    # Prompt the user to open a file
    browser = UserInterface.CommonDialog()
    filecsv = browser.open_file('Select a plan list file', 'CSV Files (*.csv)|*.csv')
    if filecsv != '':
        with open(filecsv, 'r') as f:
            r = csv.reader(f, delimiter=',')
            r.next()  # Skip header
            rows = [Row(*l) for l in r]
    #
    # Create the output file
    path = os.path.dirname(filecsv)
    output_filename = os.path.join(path, filecsv.replace(".csv","_output.txt"))
    output_file = open(output_filename, "a+")
    output_message = "PatientID" + "\tPlan Name" + "\tBeamSet Name" + "\tStatus\n"
    output_file.write(output_message)
    output_file.close()
    
    
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    # plan = GeneralOperations.find_scope(level='Plan')
    # Get in here and grab a patient specific csv
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = ''
    file = 'UWGeneric.xml'
    protocol_beamset = 'Tomo3D-FW5'
    beamset_file = 'UWGeneric.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    # Targets and dose
    target_1 = 'PTV_60'
    target_1_dose = 6000
    # target_2 = 'PTV_60'
    # target_2_dose = 6000
    # target_3 = 'PTV_54'
    # target_3_dose = 5400
    rx_target = target_1
    beamset_name = 'Tmplt_20Feb2020'
    number_fractions = 30
    machine = 'HDA0488'
    iso_target = 'All_PTVs'
    #
    planning_struct = True
    if planning_struct:
        # Define planning structures
        planning_prefs= StructureOperations.planning_structure_preferences()
        planning_prefs.number_of_targets = 1
        planning_prefs.use_uniform_dose = True
        planning_prefs.use_under_dose = False
        planning_prefs.use_inner_air = False

        dialog1_response = {'number_of_targets': 1,
                         'generate_underdose': False,
                         'generate_uniformdose': True,
                         'generate_inner_air': False}
        targets_dose = {target_1: target_1_dose}
        dialog2_response = targets_dose
        # dialog1_response = {'number_of_targets': 2,
        #                     'generate_underdose': False,
        #                     'generate_uniformdose': True,
        #                     'generate_inner_air': False}
        # targets_dose = {target_1: target_1_dose, target_2: target_2_dose, target_3: target_3_dose}
        # dialog2_response = targets_dose
        # dialog1_response = None
        # dialog2_response = None
        dialog3_response = {'structures': ['Bone_Mandible', 'Larynx', 'Esophagus'],
                            'standoff': 0.4}
        dialog4_response = {'structures': ['Bone_Mandible', 'Larynx', 'Esophagus'],
                            'standoff': 0.4}
        dialog5_response = {'target_skin': False,
                            'ring_hd': True,
                            'target_rings': True,
                            'thick_hd_ring': 2,
                            'thick_ld_ring': 5,
                            'ring_standoff': 0.2,
                            'otv_standoff': 0.4}
        StructureOperations.planning_structures(
            generate_ptvs=True,
            generate_ptv_evals=True,
            generate_otvs=True,
            generate_skin=True,
            generate_inner_air=True,
            generate_field_of_view=True,
            generate_ring_hd=True,
            generate_ring_ld=True,
            generate_normal_2cm=True,
            generate_combined_ptv=True,
            skin_contraction=0.3,
            run_status=False,
            planning_structure_selections=planning_prefs,
            dialog2_response=dialog2_response,
            dialog3_response=dialog3_response,
            dialog4_response=dialog4_response,
            dialog5_response=dialog5_response
        )

    # Dependancies: All_PTVs
    iso_target_exists = StructureOperations.check_structure_exists(
        case=case, structure_name=iso_target, option='Wait', exam=exam)
    if not iso_target_exists:
        logging.debug('{} does not exist. It must be defined to make this script work'.format(iso_target))
        sys.exit('{} is a required structure'.format(iso_target))

    # TODO: Add a plan based on the xml
    # Go grab the beamset called protocol_beamset
    # This step is likely not neccessary, just know exact beamset name from protocol
    available_beamsets = BeamOperations.Beams.select_element(
        set_level='beamset',
        set_type=None,
        set_elements='beam',
        filename=beamset_file,
        set_level_name=protocol_beamset,
        dialog=False,
        folder=path_protocols,
        verbose_logging=False)

    # TODO: Retrieve these definitions from the planning protocol.
    beamset_defs = BeamOperations.BeamSet()
    beamset_defs.rx_target = rx_target
    beamset_defs.name = beamset_name
    beamset_defs.DicomName = beamset_name
    beamset_defs.number_of_fractions = number_fractions
    beamset_defs.total_dose = target_1_dose
    beamset_defs.machine = machine
    beamset_defs.modality = 'Photons'
    beamset_defs.technique = 'TomoHelical'
    beamset_defs.iso_target = iso_target
    beamset_defs.protocol_name = available_beamsets

    order_name = None
    # par_beam_set = BeamOperations.beamset_dialog(case=case,
    #                                              filename=file,
    #                                              path=path_protocols,
    #                                              order_name=order_name)

    rs_beam_set = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=beamset_defs,
                                                create_setup_beams=False)

    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=protocol_beamset,
                                          path=path_protocols)
    if len(beams) > 1:
        logging.warning('Invalid tomo beamset in {}, more than one Tomo beam found.'.format(beamset_defs.name))
    else:
        beam = beams[0]

    # Place isocenter
    try:
        beamset_defs.iso = BeamOperations.find_isocenter_parameters(
            case=case,
            exam=exam,
            beamset=rs_beam_set,
            iso_target=beamset_defs.iso_target,
            lateral_zero=True)

    except Exception:
        logging.warning('Aborting, could not locate center of {}'.format(beamset_defs.iso_target))
        sys.exit('Failed to place isocenter')

    BeamOperations.place_tomo_beam_in_beamset(plan=plan, iso=beamset_defs.iso, beamset=rs_beam_set, beam=beam)

    patient.Save()
    rs_beam_set.SetCurrent()
    sys.exit('Done')

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
    # For debugging we can bypass the dialog by uncommenting the below lines
    order_name = None
    par_beam_set = BeamOperations.beamset_dialog(case=case,
                                                 filename=file,
                                                 path=path_protocols,
                                                 order_name=order_name)

    rs_beam_set = BeamOperations.create_beamset(patient=patient,
                                                case=case,
                                                exam=exam,
                                                plan=plan,
                                                dialog=False,
                                                BeamSet=par_beam_set,
                                                create_setup_beams=False)

    beams = BeamOperations.load_beams_xml(filename=file,
                                          beamset_name=par_beam_set.protocol_name,
                                          path=path_protocols)

    # Now add in clinical goals and objectives
    add_goals_and_structures_from_protocol(patient=patient, case=case, plan=plan, beamset=rs_beam_set, exam=exam,
                                           filename=None, path_protocols=None, run_status=False)




if __name__ == '__main__':
    main()
