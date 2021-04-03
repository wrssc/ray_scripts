""" UW Autoplanning

    Automatic generation of a plan
    -User selects autoplan type
    -Selects TPO (from supported list)
    Script:
    -Loads planning structures
    -Loads Beams
    -Loads clinical goals
    -Loads plan optimization templates
    -Runs an optimization script
    -Saves the plan for future comparisons
    Examination and Case must exist up front

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
__date__ = '2021-Mar-03'
__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Someone else'
__reviewed__ = 'YYYY-MM-DD'
__raystation__ = '10.0.0'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__credits__ = ['']

import sys
import os
import logging
# import xml.etree.ElementTree
# from collections import OrderedDict
import connect
import UserInterface
import GeneralOperations
from GeneralOperations import logcrit as logcrit
import StructureOperations
import Objectives
# import GeneralOperations
# import StructureOperations
# import BeamOperations
# from Objectives import add_goals_and_objectives_from_protocol
# from OptimizationOperations import optimize_plan, iter_optimization_config_etree
def target_dialog(case, protocol, order, use_orders=True):
    # Find RS targets
    plan_targets = StructureOperations.find_targets(case=case)
    protocol_targets = []
    missing_contours = []

    # Build second dialog
    target_inputs = {}
    target_initial = {}
    target_options = {}
    target_datatype = {}
    target_required = []
    i = 1
    if use_orders:
        goal_locations = (protocol.findall('./goals/roi'), order.findall('./goals/roi'))
    else:
        goal_locations = (protocol.findall('./goals/roi'))
    # Use the following loop to find the targets in protocol matching the names above
    for s in goal_locations:
        for g in s:
            g_name = g.find('name').text
            # Priorities should be even for targets and append unique elements only
            # into the protocol_targets list
            if int(g.find('priority').text) % 2 == 0 and g_name not in protocol_targets:
                protocol_targets.append(g_name)
                k = str(i)
                # Python doesn't sort lists....
                k_name = k.zfill(2) + 'Aname_' + g_name
                k_dose = k.zfill(2) + 'Bdose_' + g_name
                target_inputs[k_name] = 'Match a plan target to ' + g_name
                target_options[k_name] = plan_targets
                target_datatype[k_name] = 'combo'
                target_required.append(k_name)
                target_inputs[
                    k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                target_required.append(k_dose)
                i += 1
                # Exact matches get an initial guess in the dropdown
                for t in plan_targets:
                    if g_name == t:
                        target_initial[k_name] = t
    target_dialog = UserInterface.InputDialog(
        inputs=target_inputs,
        title='Input Target Dose Levels',
        datatype=target_datatype,
        initial=target_initial,
        options=target_options,
        required=[])
    print
    target_dialog.show()
    # Process inputs
    # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
    nominal_dose = 0
    translation_map = {}
    # TODO Add a dict element that is just key and dose
    #  seems like the next two loops could be combined, but
    #  since dict cycling isn't ordered I don't know how to create
    #  a blank element space
    for k, v in target_dialog.values.items():
        if len(v) > 0:
            i, p = k.split("_", 1)
            if p not in translation_map:
                translation_map[p] = [None] * 2
            if 'name' in i:
                # Key name will be the protocol target name
                translation_map[p][0] = v

            if 'dose' in i:
                # Append _dose to the key name
                pd = p + '_dose'
                # Not sure if this loop is still needed
                translation_map[p][1] = (float(v) / 100.)
    return translation_map




def main():
    #
    # Get current patient, case, exam
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    #
    # Select the TPO
    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    autoplan_folder = r'AutoPlans'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder, institution_folder, autoplan_folder)
    # Add a plan and beamset
    # Delete
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    # Find the protocol the user wants to use through a dialog
    protocol_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Protocol'},
            title='Protocol Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(tpo.protocols.keys())},
            required=['i'])
    # Launch the dialog
    response = protocol_dialog.show()
    # Link root to selected protocol ElementTree
    logging.info("Protocol selected: {}".format(protocol_dialog.values['i']))
    # Store the protocol name and optional order name
    protocol_name = protocol_dialog.values['i']
    protocol = tpo.protocols[protocol_name]
#    order_name = None
    orders = []
    for o in protocol.findall('order/name'):
        orders.append(o.text)

    # Find the protocol the user wants to use.
    selected_order = UserInterface.InputDialog(
        inputs={'i': 'Select Order'},
        title='Order Selection',
        datatype={'i': 'combo'},
        initial={'i': orders[0]},
        options={'i': orders},
        required=['i'])
    # Launch the dialog
    response = selected_order.show()
    # Link root to selected protocol ElementTree
    order_name = selected_order.values['i']
    logging.critical("Treatment Planning Order selected: {}".format(order_name))
    # Update the order name
    for o in protocol.findall('order'):
        if o.find('name').text == order_name:
            order = o
            logging.debug('Matching protocol ElementTag found for {}'.format(order_name))
            break
    # Prompt user for target map
    translation_map = target_dialog(case=case,protocol=protocol, order=order, use_orders=True)
    for k, v in translation_map.items():
            logging.debug('Targets are {}{}'.format(k, v))
    #
    # Available beamsets
    beamsets = []
    for b in protocol.findall('beamset/name'):
        beamsets.append(b)
    #
    technique='TomoHelical'
    # Available optimizations
    logging.debug('optimizations {}'.format(protocol.findall('optimization_config')))

    # opts = [o for o in protocol.findall('optimization_technique') if o.find('technique').text == technique]
    opts = []
    for o in protocol.findall('optimization_config'):
        if o.find('technique').text == technique:
            opts.append(o)
    logging.debug('available opts are {}'.format(opts))
    #



if __name__ == '__main__':
    main()