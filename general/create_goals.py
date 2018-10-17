""" Create Clinical Goals

    Add clinical goals and objectives in RayStation given user supplied inputs
    At this time, we are looking in the UW protocols directory for a
    list of approved protocols

    We may want to extend this main function to a simple function which would potentially
    take the path as an argument.

    Inputs::
        None at this time

    Dependencies::
        Note that protocols are assumed to have even priorities describing targets

    TODO: Change the main to a callable function taking the protocol path as an input`
    TODO: Add goal loop for secondary - unspecified target goals

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import os
import logging
import datetime
import connect
import UserInterface
import Goals


def main():
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)

    # Get current patient, case, exam, and plan
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
        exam = connect.get_current('Examination')
        plan = connect.get_current('Plan')
        patient.Save()

    except Exception:
        UserInterface.WarningBox('This script requires a patient and plan to be loaded')
        sys.exit('This script requires a patient and plan to be loaded')

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    input_dialog = UserInterface.InputDialog(
        inputs={'input1': 'Select Protocol'},
        title='Protocol Selection',
        datatype={'input1': 'combo'},
        initial={},
        options={'input1': list(tpo.protocols.keys())},
        required=['input1'])

    # Launch the dialog
    print input_dialog.show()
    # Link root to selected protocol ElementTree
    logging.info("create_goals.py: protocol selected: {}".format(
        input_dialog.values['input1']))
    root = tpo.protocols[input_dialog.values['input1']]
    # Find RS targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'Ptv':
            plan_targets.append(r.Name)

    # Add user threat: empty PTV list.
    connect.await_user_input("The target list is empty. Please apply type PTV to the targets and continue.")

    protocol_targets = []
    missing_contours = []

    # Build second dialog
    final_inputs = {}
    final_initial = {}
    final_options = {}
    final_datatype = {}
    final_required = []
    i = 1
    # Lovely code, but had to break this loop up
    # for g, t in ((a, b) for a in root.findall('./goals/roi') for b in plan_targets):

    # Use the following loop to find the targets in protocol matching the names above
    for g in root.findall('./goals/roi'):
        g_name = g.find('name').text
        for t in plan_targets:
            # Priorities should be even for targets and append unique elements only
            # into the protocol_targets list
            if int(g.find('priority').text) % 2 == 0 and g_name not in protocol_targets:
                protocol_targets.append(g_name)
                k = str(i)
                # Python doesn't sort lists....
                k_name = k.zfill(2) + 'Aname_' + g_name
                k_dose = k.zfill(2) + 'Bdose_' + g_name
                final_inputs[k_name] = 'Match a plan target to ' + g_name
                final_options[k_name] = plan_targets
                final_datatype[k_name] = 'combo'
                final_required.append(k_name)
                final_inputs[k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                final_required.append(k_dose)
                i += 1
                # Exact matches get an initial guess in the dropdown
                if g_name == t:
                    final_initial[k_name] = t
        # Add a quick check if the contour exists in RS
        if int(g.find('priority').text) % 2:
            if not any(r.Name == g_name for r in
                       case.PatientModel.RegionsOfInterest) and g_name not in missing_contours:
                missing_contours.append(g_name)
    # Warn the user they are missing stuff
    if missing_contours:
        missing_message = 'Missing structures, continue script or cancel \n'.join(missing_contours)
        connect.await_user_input(missing_message)

    final_dialog = UserInterface.InputDialog(
        inputs=final_inputs,
        title='Input Clinical Goals',
        datatype=final_datatype,
        initial=final_initial,
        options=final_options,
        required=final_required)
    print final_dialog.show()

    # Process inputs
    # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
    protocol_match = {}
    for k, v in final_dialog.values.iteritems():
        i, p = k.split("_", 1)
        if 'name' in i:
            # Key name will be the protocol target name
            protocol_match[p] = v
        if 'dose' in i:
            # Append _dose to the key name
            pd = p + '_dose'
            protocol_match[pd] = (float(v) / 100.)

    # Take the relative dose limits and convert them to the user specified dose levels
    for g in root.findall('./goals/roi'):
        # If the key is a name key, change the ElementTree for the name
        if g.find('name').text in protocol_match and "%" in g.find('dose').attrib['units']:
            name_key = g.find('name').text
            dose_key = g.find('name').text + '_dose'
            logging.debug('Reassigned protocol name from {} to {}, for dose {} Gy'.format(
                g.find('name').text, protocol_match[name_key],
                protocol_match[dose_key]))
            g.find('name').text = protocol_match[name_key]
            g.find('dose').attrib = "Gy"
            g.find('dose').text = protocol_match[dose_key]
        # Regardless, add the goal now
        logging.debug('create_goals.py: Adding goal ' + Goals.print_goal(g, 'xml'))
        Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()
