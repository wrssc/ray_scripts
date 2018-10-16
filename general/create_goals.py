""" Create Clinical Goals

    Add clinical goals and objectives in RayStation given user supplied inputs
    At this time, we are looking in the UW_Approved protocols directory for a
    list of approved protocols

    We may want to extend this main function to a simple function which would potentially
    take the path as an argument.



    Inputs::

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

    # Replace this check with a check on the priorities
    targets = ['PTV', 'ITV', 'GTV']
    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    input_dialog = UserInterface.InputDialog(
        inputs={
            'input1': 'Select Protocol',
        },
        title='Initial Input Clinical Goals',
        datatype={'input1': 'combo'},
        initial={},
        options={'input1': list(tpo.protocols.keys())},
        required=['input1'])

    # Launch the dialog
    print input_dialog.show()
    # Link root to selected protocol ElementTree
    root = tpo.protocols[input_dialog.values['input1']]
    # Find RS targets
    plan_targets = []
    for r in case.PatientModel.RegionsOfInterest:
        if r.Type == 'Ptv':
            plan_targets.append(r.Name)
    # Use the following loop to find the targets in protocol matching the names above
    protocol_targets = []

    # Build second dialog
    final_inputs = {}
    final_initial = {}
    final_options = {}
    final_datatype = {}
    final_required = []
    i = 1
    #for g, t in ((a,b) for a in root.findall('./goals/roi') for b in plan_targets):
    for g in root.findall('./goals/roi'):
        # Ugh, gotta be a more pythonic way to do this loop
        # ? for g, t in ((a,b) for a in root.findall('./goals/roi') for b in targets)
        g_name = g.find('name').text
        # priority will be even if the goal is a target goal
        priority = g.find('priority').text
        print "priority = {}".format(priority)
        for t in plan_targets:
            # Look for an existing match to the target in the protocol_target list
            if g.find('priority').text % 2 and g_name not in protocol_targets:
                protocol_targets.append(g_name)
                k = str(i)
                # Python doesn't sort lists....
                k_name = k.zfill(2) + 'Aname_' + g_name
                final_inputs[k_name] = 'Match a plan target to ' + g_name
                final_options[k_name] = plan_targets
                final_datatype[k_name] = 'combo'
                final_required.append(k_name)
                kd = str(i)
                k_dose = kd.zfill(2) + 'Bdose_' + g_name
                final_inputs[k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                final_required.append(k_dose)
                i += 1
                # Exact matches get an initial guess in the dropdown
                if g_name == t:
                    final_initial[k_name] = t
                #elif g_name != t and any(g in g_name for g in targets):

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
