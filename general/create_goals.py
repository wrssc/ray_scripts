""" Create Clinical Goals

    Add clinical goals and objectives in RayStation given user supplied inputs
    At this time, we are looking in the UW protocols directory for a
    list of approved protocols

    We may want to extend this main function to a simple function which would potentially
    take the path as an argument.

    Script will ask user for a protocol and potentially an order.  It will then find the
    doses that are to be used. If protocol defined doses exist and matches are found to
    target names it will load those first.

    Inputs::
        None at this time

    Dependencies::
        Note that protocols are assumed to have even priorities describing targets

    TODO: Change the main to a callable function taking the protocol path as an input`
    TODO: Add goal loop for secondary - unspecified target goals
    :versions
    1.0.0 initial release supporting HN, Prostate, and lung (non-SBRT)
    1.0.1 supporting SBRT, brain, and knowledge-based goals for RTOG-SBRT Lung

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '1.0.1'
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


def rtog_sbrt_dgi(case, examination, target, flag, dose=None):
    """
    Function will return the RTOG lung 50% DGI for an input target structure name

    :inputs
        beamset: Name of current beamset
        target: name of current ROI
        flag: Flag to indicate the minor deviation criteria
    :return
        the value of the interpolated RTOG criteria is returned, index, or dose in Gy
    """
    prot_vol = [1.8, 3.8, 7.4, 13.2, 22, 34, 50, 70, 95, 126, 163]
    if flag == 'rtog_sbr_dgi_minor':
        index = [0.17, 0.18, 0.20, 0.21, 0.22, 0.23, 0.25, 0.29, 0.30, 0.32, 0.34]
        logging.debug('rtog_sbrt_dgi: Minor DGI selected.')
    elif flag == 'rtog_sbr_dgi_major':
        index = [0.13, 0.15, 0.17, 0.17, 0.18, 0.19, 0.20, 0.21, 0.23, 0.25, 0.27]
        logging.debug('rtog_sbrt_dgi: Major DGI selected.')
    elif flag == 'rtog_sbr_norm2_major':
        unscaled_index = [0.57, 0.57, 0.58, 0.58, 0.63, 0.68, 0.77, 0.86, 0.89, 0.91, 0.94]
        index = [i * dose for i in unscaled_index]
        logging.debug('rtog_sbrt_dgi: Major Normal_2cm selected.')
    elif flag == 'rtog_sbr_norm2_minor':
        index = [0.50, 0.50, 0.50, 0.50, 0.54, 0.58, 0.62, 0.66, 0.70, 0.73, 0.77]
        logging.debug('rtog_sbrt_dgi: Minor Normal_2cm selected.')
    else:
        logging.warning("rtog_sbrt_dgi: Unknown flag used in call. Returning zero")
        return 0.0

    try:
        t = case.PatientModel.StructureSets[examination.Name]. \
            RoiGeometries[target]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.warning('rtog_sbrt_dgi: {} has no contours, index undefined'.format(target))
    except:
        logging.warning('rtog_sbrt_dgi: Error getting volume for {}'.format(target))

    # fd = beamset.FractionDose
    # roi = fd.GetDoseGridRoi(RoiName=target)
    # vol = roi.RoiVolumeDistribution.TotalVolume
    # logging.debug('Type of roi {}'.format(type(roi)))
    if abs(vol) <= 1e-9:
        # Attempt to redefine dose grid
        logging.warning('rtog_sbrt_dgi: Volume is 0.0 for {}'.format(target))
    else:
        logging.debug('rtog_sbrt_dgi: Volume for {} is {}'.format(
            target, vol
        ))
    v = prot_vol[0]
    i = 0
    # Find first volume exceeding target volume or find the end of the list
    while v <= vol and i <= len(prot_vol):
        i += 1
        v = prot_vol[i]
    # Exceptions for target volumes exceeding or smaller than the minimum volume
    if i == 0:
        logging.warning('rtog_sbrt_dgi.py: Target volume < RTOG volume limits' +
                        '  returning lowest available index{}'.index[i])
        return index[i]
    elif i == len(prot_vol):
        logging.warning('rtog_sbrt_dgi.py: Target volume > RTOG volume limits' +
                        ' returning highest available index{}'.index[i])
        return index[i]
    # Interpolate on i and i - 1
    else:
        interp = index[i - 1] + (vol - prot_vol[i - 1]) * (
                (index[i] - index[i - 1]) / (prot_vol[i] - prot_vol[i - 1]))
        logging.info('rtog_sbrt_dgi: {} volume is {}, index = {}. '.format(
            target, vol, interp))
        logging.debug('Table searched lower bound on volume ' +
                      'interpolating volumes: ({}, {}) and index: ({}, {})'.format(
                          prot_vol[i - 1], prot_vol[i], index[i - 1], index[i]
                      ))
        return interp


# except AttributeError:
#    logging.warning('rtog_sbrt_dgi.py: Goal could not be loaded correctly since roi:' +
#                    ' {} is not contoured on this examination'.g.find('name').text)


def knowledge_based_goal(structure_name, goal_type, case, exam):
    """
    knowledge_based_goals will handle the knowledge based goals by goal type
    at this time the
    :param structure_name: structure to which goal should be applied
    :param goal_type: string flag for which the
    :param case: RS case object
    :param exam: RS examination object
    :return: know_analysis - dictionary containing the index to be changed
    """
    know_analysis = {}
    if goal_type in [
        'rtog_sbr_dgi_minor',
        'rtog_sbr_dgi_major']:
        know_analysis['index'] = rtog_sbrt_dgi(case=case,
                                               examination=exam,
                                               target=structure_name,
                                               flag=goal_type)
    elif goal_type in [
        'rtog_sbr_norm2_major',
        'rtog_sbr_norm2_minor']:
        know_analysis['dose'] = rtog_sbrt_dgi(case=case,
                                              examination=exam,
                                              target=structure_name,
                                              flag=goal_type)
    else:
        know_analysis['error'] = True
        logging.warning('knowledge_based_goal: Unsupported knowledge-based goal')

    return know_analysis


def main():
    """
    Function will take the optional input of the protocol file name
    :return:
    """
    filename = None
    status = UserInterface.ScriptStatus(
        steps=['Finding correct protocol',
               'Matching Structure List',
               'Getting target Doses',
               'Adding Goals'],
        docstring=__doc__,
        help=__help__)

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)

    # Get current patient, case, exam, and plan
    try:
        patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        exam = connect.get_current("Examination")
    except SystemError:
        raise IOError("No examination loaded. Load patient ct and plan.")

    try:
        plan = connect.get_current("Plan")
    except SystemError:
        raise IOError("No plan loaded. Load patient and plan.")

    # We may not need a beamset, depending on how volumes are handled
    try:
        beamset = connect.get_current("BeamSet")
    except SystemError:
        raise IOError("No beamset loaded. Load patient plan and beamset")

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    status.next_step(text="Determining correct treatment protocol" +
                          "based on treatment planning order.", num=0)

    # Eventually we may want to conver
    if filename:
        logging.info("Protocol selected: {}".format(
            filename))
        root = tpo.protocols[tpo.protocols[filename]]
    else:
        # Find the protocol the user wants to use.
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
        logging.info("Protocol selected: {}".format(
            input_dialog.values['input1']))
        order_list = []
        protocol = tpo.protocols[input_dialog.values['input1']]
        for o in protocol.findall('order/name'):
            order_list.append(o.text)

        if len(order_list) >= 1:
            use_orders = True
            # Find the protocol the user wants to use.
            input_dialog = UserInterface.InputDialog(
                inputs={'input1': 'Select Order'},
                title='Order Selection',
                datatype={'input1': 'combo'},
                initial={'input1': order_list[0]},
                options={'input1': order_list},
                required=['input1'])
            # Launch the dialog
            print input_dialog.show()
            # Link root to selected protocol ElementTree
            logging.info("Order selected: {}".format(
                input_dialog.values['input1']))
            for o in protocol.findall('order'):
                if o.find('name').text == input_dialog.values['input1']:
                    order = o
                    logging.debug('Matching protocol ElementTag found for {}'.format(
                        input_dialog.values['input1']))
                    break
        else:
            logging.debug('No orders in protocol')
            use_orders = False

        # Find RS targets
        plan_targets = []
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == 'Target':
                plan_targets.append(r.Name)

        status.next_step(text="Matching all structures to the current list.", num=1)
        # Add user threat: empty PTV list.
        if not plan_targets:
            connect.await_user_input("The target list is empty." +
                                     " Please apply type PTV to the targets and continue.")

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

        # Where the targets at?
        if use_orders:
            target_goal_level = order
        else:
            target_goal_level = protocol

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
                    final_inputs[k_name] = 'Match a plan target to ' + g_name
                    final_options[k_name] = plan_targets
                    final_datatype[k_name] = 'combo'
                    final_required.append(k_name)
                    final_inputs[k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                    final_required.append(k_dose)
                    i += 1
                    # Exact matches get an initial guess in the dropdown
                    for t in plan_targets:
                        if g_name == t:
                            final_initial[k_name] = t
                # Add a quick check if the contour exists in RS
                if int(g.find('priority').text) % 2:
                    if not any(r.Name == g_name for r in
                               case.PatientModel.RegionsOfInterest) and g_name not in missing_contours:
                        missing_contours.append(g_name)
        # Warn the user they are missing stuff
        if missing_contours:
            mc_list = ',\n'.join(missing_contours)
            missing_message = 'Missing structures, continue script or cancel \n' + mc_list
            status.next_step(text=missing_message, num=1)
            connect.await_user_input(missing_message)

        status.next_step(text="Getting target doses from user.", num=2)
        final_dialog = UserInterface.InputDialog(
            inputs=final_inputs,
            title='Input Clinical Goals',
            datatype=final_datatype,
            initial=final_initial,
            options=final_options,
            required=[])
        print final_dialog.show()

        # Process inputs
        # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
        protocol_match = {}
        nominal_name = ''
        nominal_dose = 0
        for k, v in final_dialog.values.iteritems():
            if len(v) > 0:
                i, p = k.split("_", 1)
                if 'name' in i:
                    # Key name will be the protocol target name
                    protocol_match[p] = v
                if 'dose' in i:
                    # Append _dose to the key name
                    pd = p + '_dose'
                    protocol_match[pd] = (float(v) / 100.)
                    if nominal_dose == 0:
                        # Set a nominal dose to the first matched pair
                        nominal_dose = protocol_match[pd]

        status.next_step(text="Adding goals.", num=3)
        # Take the relative dose limits and convert them to the user specified dose levels
        for seq in goal_locations:
            for g in seq:
                # If the key is a name key, change the ElementTree for the name
                try:
                    # 1. Figure out if we need to change the goal ROI name
                    p_n = g.find('name').text
                    p_d = g.find('dose').text
                    p_t = g.find('type').text
                    # Change the name for the roi goal if the user has matched it to a target
                    if p_n in protocol_match:
                        # Change the roi name the goal uses to the matched value
                        g.find('name').text = protocol_match[p_n]
                        logging.debug('Reassigned protocol target name:{} to {}'.format(
                            p_n, g.find('name').text))
                    else:
                        logging.debug('Protocol ROI: {}'.format(p_n) +
                                      ' was not matched to a target supplied by the user. ' +
                                      'expected if the ROI type is not a target')
                    # If the goal is relative change the name of the dose attribution
                    # Change the dose to the user-specified level
                    if "%" in g.find('dose').attrib['units']:
                        # Define the unmatched and unmodified protocol name and dose
                        p_r = g.find('dose').attrib['roi']
                        # See if the goal is on a matched target and change the % dose of the attributed ROI
                        # to match the user input target and dose level for that named structure
                        logging.debug('ROI: {} has a relative goal of type: {} has a relative dose level: {}'.format(
                           p_n, p_t, p_d))
                        # 2. Correct the relative dose to the user-specified dose levels for this structure
                        if p_r in protocol_match:
                            d_key = p_r + '_dose'
                            # Change the dose attribute to absolute
                            # TODO:: This may not be such a hot idea.
                            g.find('dose').attrib['units'] = "Gy"
                            g.find('dose').attrib['roi'] = protocol_match[p_r]
                            goal_dose = float(protocol_match[d_key]) * float(p_d) / 100
                            g.find('dose').text = str(goal_dose)
                            logging.debug('Reassigned protocol dose attribute name:' +
                                          '{} to {}, for dose:{} \% to {} Gy'.format(
                                           p_r, g.find('dose').attrib['roi'], p_d, g.find('dose').text))
                        else:
                            logging.warning('Unsuccessful match between relative dose goal for ROI: ' +
                                            '{}. '.format(p_r) +
                                            'The user did not match an existing roi to one required for this goal')
                            pass

                    #  Knowledge-based goals:
                    # 1. Call the knowledge_based_goal for the correct structure
                    # 2. Use the returned dictionary to modify the ElementTree
                    if 'know' in g.find('type').attrib:
                        know_goal = knowledge_based_goal(
                            structure_name=g.find('dose').attrib['roi'],
                            goal_type=g.find('type').attrib['know'],
                            case=case,
                            exam=exam)
                        # use a dictionary for storing the return values
                        try:
                            g.find('index').text = str(know_goal['index'])
                            logging.debug('Index changed for ROI {} to {}'.format(
                                g.find('name').text, g.find('index').text))
                        except KeyError:
                            logging.debug('knowledge goals for {} had no index information'.format(
                                g.find('name').text))
                        try:
                            g.find('dose').text = str(know_goal['dose'])
                            logging.debug('Dose changed for ROI {} to {}'.format(
                                g.find('name').text, g.find('dose').text))
                        except KeyError:
                            logging.debug('knowledge goals for {} had no index information'.format(
                                g.find('name').text))

                        # gotta send g, case, exam
                        # logging.debug('knowledge-based goal found {}'.format(
                        #     g.find('type').attrib['know']
                        # ))
                        # # Get the total volume of the goal's target from the dose-grid representation
                        # # Move this to a "knowledge-based" function in the utilities library
                        # if g.find('type').attrib['know'] == 'rtog_sbr_dgi_minor':
                        #     k = 'minor_dgi'
                        # elif g.find('type').attrib['know'] == 'rtog_sbr_dgi_major':
                        #     k = 'major_dgi'
                        # elif g.find('type').attrib['know'] == 'rtog_sbr_norm2_major':
                        #     k = 'major_2cm'
                        # elif g.find('type').attrib['know'] == 'rtog_sbr_norm2_minor':
                        #     k = 'minor_2cm'
                        # else:
                        #     logging.warning('Unsupported knowledge-based goal')
                        #     # Check on loop break here to get out of if only
                        #     break
                        # print
                        # print g.find('dose').attrib['roi']
                        # target = g.find('dose').attrib['roi']
                        # k_index = rtog_sbrt_dgi(case=case,
                        #                         examination=exam,
                        #                         target=target,
                        #                         flag=k)
                        # logging.debug('Index changed for ROI {} to {}'.format(
                        #     g.find('name').text, k_index
                        # ))
                        # g.find('index').text = str(k_index)

                except AttributeError:
                    logging.debug('Goal loaded which does not have dose attribute.')
                # Regardless, add the goal now
                Goals.add_goal(g, connect.get_current('Plan'))


if __name__ == '__main__':
    main()
