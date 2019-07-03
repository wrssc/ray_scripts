""" Create Clinical Goals and Objectives

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
    2.0.0 Adding the clinical objectives for IMRT

"""
__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__version__ = '2.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/CreateGoals'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

import sys
import os
import logging
import Objectives
import connect
import UserInterface
import Goals


def rtog_sbrt_dgi(case, examination, target, flag, isodose=None):
    """
    implementation of the RTOG limits for DGI and PITV modified to allow the
    use of the conformity index

    :param case: name of current case
    :param examination: current examination object
    :param target: roi to be used for evaluation of knowledge-based goal
    :param flag: type of goal to be used
    :param isodose: optional for inputing a relative dose value
    :return: a float that is the desired index or dose
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
        index = [i * float(isodose) for i in unscaled_index]
        logging.debug('rtog_sbrt_dgi: Major Normal_2cm selected. Index scaled by dose {}'.format(isodose))
    elif flag == 'rtog_sbr_norm2_minor':
        unscaled_index = [0.50, 0.50, 0.50, 0.50, 0.54, 0.58, 0.62, 0.66, 0.70, 0.73, 0.77]
        index = [i * float(isodose) for i in unscaled_index]
        logging.debug('rtog_sbrt_dgi: Minor Normal_2cm selected. Index scaled by dose {}'.format(isodose))
    else:
        logging.warning("rtog_sbrt_dgi: Unknown flag used in call. Returning zero")
        return 0.0

    vol = 0.0
    try:
        t = case.PatientModel.StructureSets[examination.Name]. \
            RoiGeometries[target]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.warning('rtog_sbrt_dgi: {} has no contours, index undefined'.format(target))
    except:
        logging.warning('rtog_sbrt_dgi: Error getting volume for {}, volume => 0.0'.format(target))

    # Compute density from the actual dose grid representation
    # fd = beamset.FractionDose
    # roi = fd.GetDoseGridRoi(RoiName=target)
    # vol = roi.RoiVolumeDistribution.TotalVolume
    # logging.debug('Type of roi {}'.format(type(roi)))
    if abs(vol) <= 1e-9:
        logging.warning('rtog_sbrt_dgi: Volume is 0.0 for {}'.format(target))
    else:
        logging.debug('rtog_sbrt_dgi: Volume for {} is {}'.format(
            target, vol))
    v = prot_vol[0]
    i = 0
    # Find first volume exceeding target volume or find the end of the list
    while v <= vol and i <= len(prot_vol)-1:
        i += 1
        v = prot_vol[i]
    # Exceptions for target volumes exceeding or smaller than the minimum volume
    if i == 0:
        logging.warning('rtog_sbrt_dgi.py: Target volume < RTOG volume limits' +
                        '  returning lowest available index{}'.format(index[i]))
        return index[i]
    elif i == len(prot_vol):
        logging.warning('rtog_sbrt_dgi.py: Target volume > RTOG volume limits' +
                        ' returning highest available index{}'.format(index[i]))
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


def residual_volume(structure_name, goal_volume, case, exam):
    """
    Used for finding the remaining volume in terms of the total.  Use for limits
    that must preserve a certain number of cc exposed below a limit
    :param structure_name: structure to evaluate the volume
    :param goal_volume: desired residual volume
    :param case: current case
    :param exam: current exam
    :return: the residual volume as a percentage of the total or zero if volume is undefined
    """
    vol = 0.0
    try:
        t = case.PatientModel.StructureSets[exam.Name]. \
            RoiGeometries[structure_name]
        if t.HasContours():
            vol = t.GetRoiVolume()
        else:
            logging.warning('residual_volume: {} has no contours, index undefined'.format(structure_name))
    except:
        logging.warning('residual_volume: Error getting volume for {}, volume => 0.0'.format(structure_name))

    if abs(vol) <= 1e-9:
        logging.warning('residual_volume: Volume is 0.0 for {}'.format(structure_name))
        return 0
    else:
        logging.debug('residual_volume: Volume for {} is {}'.format(
            structure_name, vol))
        residual_percentage = 100 * (vol - float(goal_volume)) / vol
        return residual_percentage


def conditional_overlap(structure_name, goal_volume, case, exam, comp_structure, isodose):
    """Evaluate the overlap between structure_name and comp_structure
    then modify goal volume and dose.
    If overlap return a dmax limit on a percentage of the comp_structure prescription dose
    If no overlap return an absolute dose limit on an absolute volume
    :param structure_name:
    :param goal_volume:
    :param case:
    :param exam:
    :param comp_structure:
    """
    # TODO: This module needs to be written to evaluate overlap and put a goal volume based on residual


def knowledge_based_goal(structure_name, goal_type, case, exam,
                         isodose=None,
                         res_vol=None,
                         comp_structure=None):
    """
    knowledge_based_goals will handle the knowledge based goals by goal type
    at this time the
    :param structure_name: structure to which goal should be applied
    :param goal_type: string flag for which the
    :param case: RS case object
    :param exam: RS examination object
    :param isodose: target dose level
    :param res_vol: target residual volume
    :param comp_structure: a comparison structure for conditional evaluation
    :return: know_analysis - dictionary containing the elements that need to be changed
    """
    know_analysis = {}
    if goal_type in ['rtog_sbr_dgi_minor', 'rtog_sbr_dgi_major']:
        know_analysis['index'] = rtog_sbrt_dgi(case=case,
                                               examination=exam,
                                               target=structure_name,
                                               flag=goal_type)
    elif goal_type in ['rtog_sbr_norm2_major', 'rtog_sbr_norm2_minor']:
        know_analysis['dose'] = rtog_sbrt_dgi(case=case,
                                              examination=exam,
                                              target=structure_name,
                                              flag=goal_type,
                                              isodose=isodose)
    elif goal_type in ['resid_vol']:
        know_analysis['volume'] = residual_volume(structure_name=structure_name,
                                                  goal_volume=res_vol,
                                                  case=case,
                                                  exam=exam)
        know_analysis['units'] = '%'
    elif goal_type in ['overlap']:
        know_analysis = conditional_overlap(structure_name=structure_name,
                                            goal_volume=res_volume,
                                            case=case,
                                            exam=exam,
                                            comp_structure=comp_structure,
                                            isodose=isodose)
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
               'Adding Goals',
               'Adding Standard Objectives'],
        docstring=__doc__,
        help=__help__)

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder)

    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
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
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(path_protocols)

    status.next_step(text="Determining correct treatment protocol" +
                          "based on treatment planning order.", num=0)

    # TODO: Set up a means of bypassing the dialogs
    #  Eventually we may want to convert to accepting a call from a filename
    #  Alternatively, this could all be set up as a function call
    if filename:
        logging.info("Protocol selected: {}".format(
            filename))
        root = tpo.protocols[tpo.protocols[filename]]
    else:
        # Find the protocol the user wants to use.
        input_dialog = UserInterface.InputDialog(
            inputs={'i': 'Select Protocol'},
            title='Protocol Selection',
            datatype={'i': 'combo'},
            initial={},
            options={'i': list(tpo.protocols.keys())},
            required=['i'])
        # Launch the dialog
        response = input_dialog.show()
        # Link root to selected protocol ElementTree
        logging.info("Protocol selected: {}".format(
            input_dialog.values['i']))
        # Store the protocol name and optional order name
        protocol_name = input_dialog.values['i']
        order_name = None
        order_list = []
        protocol = tpo.protocols[input_dialog.values['i']]
        for o in protocol.findall('order/name'):
            order_list.append(o.text)

        if len(order_list) >= 1:
            use_orders = True
            # Find the protocol the user wants to use.
            input_dialog = UserInterface.InputDialog(
                inputs={'i': 'Select Order'},
                title='Order Selection',
                datatype={'i': 'combo'},
                initial={'i': order_list[0]},
                options={'i': order_list},
                required=['i'])
            # Launch the dialog
            response = input_dialog.show()
            # Link root to selected protocol ElementTree
            logging.info("Order selected: {}".format(
                input_dialog.values['i']))
            # Update the order name

            # I believe this loop can be eliminated with we can use a different function
            # to match protocol.find('order') with input_dialog.values['i']
            for o in protocol.findall('order'):
                if o.find('name').text == input_dialog.values['i']:
                    order = o
                    logging.debug('Matching protocol ElementTag found for {}'.format(
                        input_dialog.values['i']))
                    break
            order_name = input_dialog.values['i']

        else:
            logging.debug('No orders in protocol')
            use_orders = False

        # Find RS targets
        plan_targets = []
        for r in case.PatientModel.RegionsOfInterest:
            if r.OrganData.OrganType == 'Target':
                plan_targets.append(r.Name)
        # Add user threat: empty PTV list.
        if not plan_targets:
            connect.await_user_input("The target list is empty." +
                                     " Please apply type PTV to the targets and continue.")
            for r in case.PatientModel.RegionsOfInterest:
                if r.OrganData.OrganType == 'Target':
                    plan_targets.append(r.Name)
        if not plan_targets:
            status.finish('Script cancelled, inputs were not supplied')
            sys.exit('Script cancelled')

        status.next_step(text="Matching all structures to the current list.", num=1)

        protocol_targets = []
        missing_contours = []

        # Build second dialog
        target_inputs = {}
        target_initial = {}
        target_options = {}
        target_datatype = {}
        target_required = []
        i = 1
        # Lovely code, but had to break this loop up
        # for g, t in ((a, b) for a in root.findall('./goals/roi') for b in plan_targets):

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
                    target_inputs[k_dose] = 'Provide dose for protocol target: ' + g_name + ' Dose in cGy'
                    target_required.append(k_dose)
                    i += 1
                    # Exact matches get an initial guess in the dropdown
                    for t in plan_targets:
                        if g_name == t:
                            target_initial[k_name] = t

        # Warn the user they are missing organs at risk specified in the order
        rois = []
        for r in case.PatientModel.RegionsOfInterest:
            # Maybe extend, can't remember
            rois.append(r.Name)
        for s in goal_locations:
            for g in s:
                g_name = g.find('name').text
                # Add a quick check if the contour exists in RS
                # This step is slow, we may want to gather all rois into a list and look for it
                if int(g.find('priority').text) % 2:
                    if not any(r == g_name for r in rois) and g_name not in missing_contours:
                        #       case.PatientModel.RegionsOfInterest) and g_name not in missing_contours:
                        missing_contours.append(g_name)

        if missing_contours:
            mc_list = ',\n'.join(missing_contours)
            missing_message = 'Missing structures, continue script or cancel \n' + mc_list
            status.next_step(text=missing_message, num=1)
            connect.await_user_input(missing_message)
            # Add a line here to check again for missing contours and write out the list
            for r in case.PatientModel.RegionsOfInterest:
                # Maybe extend, can't remember
                rois.append(r.Name)

            m_c = []
            found = False
            for m in missing_contours:
                # We don't want in, we need an exact match - for length too
                for r in rois:
                    found = False
                    if r == m:
                        found = True
                        break
                if not found:
                    if m not in m_c:
                        m_c.append(m)
            if not m_c:
                logging.debug('All structures in protocol accounted for')
            else:
                mc_list = ',\n'.join(m_c)
                missing_message = 'Missing structures remain \n' + mc_list
                logging.warning(missing_message)

        status.next_step(text="Getting target doses from user.", num=2)
        target_dialog = UserInterface.InputDialog(
            inputs=target_inputs,
            title='Input Target Dose Levels',
            datatype=target_datatype,
            initial=target_initial,
            options=target_options,
            required=[])
        print target_dialog.show()

        # Process inputs
        # Make a dict with key = name from elementTree : [ Name from ROIs, Dose in Gy]
        nominal_dose = 0
        translation_map = {}
        # TODO Add a dict element that is just key and dose
        #  seems like the next two loops could be combined, but
        #  since dict cycling isn't ordered I don't know how to create
        #  a blank element space
        for k, v in target_dialog.values.iteritems():
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
                    ## if nominal_dose == 0:
                    ##     # Set a nominal dose to the first matched pair

        status.next_step(text="Adding goals.", num=3)
        # Iterate over goals in orders and protocols
        for seq in goal_locations:
            for g in seq:
                # try:
                # 1. Figure out if we need to change the goal ROI name
                p_n = g.find('name').text
                p_d = g.find('dose').text
                p_t = g.find('type').text
                # Change the name for the roi goal if the user has matched it to a target
                if p_n in translation_map:
                    # Change the roi name the goal uses to the matched value
                    g.find('name').text = translation_map[p_n][0]

                    logging.debug('Reassigned protocol target name:{} to {}'.format(
                        p_n, g.find('name').text))
                # TODO: Exception catching in here for an unresolved reference
                # else:
                #    logging.debug('Protocol ROI: {}'.format(p_n) +
                #                  ' was not matched to a target supplied by the user. ' +
                #                 'expected if the ROI type is not a target')
                # If the goal is relative change the name of the dose attribution
                # Change the dose to the user-specified level
                if "%" in g.find('dose').attrib['units']:
                    # Define the unmatched and unmodified protocol name and dose
                    p_r = g.find('dose').attrib['roi']
                    # See if the goal is on a matched target and change the % dose of the attributed ROI
                    # to match the user input target and dose level for that named structure
                    logging.debug('ROI: {} has a relative goal of type: {} with a relative dose level: {}%'.format(
                        p_n, p_t, p_d))
                    # Correct the relative dose to the user-specified dose levels for this structure
                    if p_r in translation_map:
                        # Change the dose attribute to absolute
                        # TODO:: This may not be such a hot idea.
                        g.find('dose').attrib['units'] = "Gy"
                        g.find('dose').attrib['roi'] = translation_map[p_r][0]
                        goal_dose = float(translation_map[p_r][1]) * float(p_d) / 100
                        g.find('dose').text = str(goal_dose)
                        logging.debug('Reassigned protocol dose attribute name:' +
                                      '{} to {}, for dose:{}% to {} Gy'.format(
                                          p_r, g.find('dose').attrib['roi'], p_d, g.find('dose').text))
                    else:
                        logging.warning('Unsuccessful match between relative dose goal for ROI: ' +
                                        '{}. '.format(p_r) +
                                        'The user did not match an existing roi to one required for this goal')
                        pass

                #  Knowledge-based goals:
                #  Call the knowledge_based_goal for the correct structure
                #  Use the returned dictionary to modify the ElementTree
                if 'know' in g.find('type').attrib:
                    # TODO: Consider a new type for know-goals in the xml
                    try:
                        p_r = g.find('dose').attrib['roi']
                    except KeyError:
                        # If there is no relative dose attribute the correct structure is the
                        # the structure itself
                        p_r = g.find('name').text
                    if g.find('volume') is not None:
                        vol = g.find('volume').text
                    else:
                        vol = None
                    know_goal = knowledge_based_goal(
                        structure_name=p_r,
                        goal_type=g.find('type').attrib['know'],
                        case=case,
                        exam=exam,
                        isodose=g.find('dose').text,
                        res_vol=vol)
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
                        logging.debug('knowledge goals for {} had no dose information'.format(
                            g.find('name').text))
                    try:
                        g.find('volume').text = str(know_goal['volume'])
                        g.find('volume').attrib['units'] = str(know_goal['units'])
                        logging.debug('Index changed for ROI {} to {}'.format(
                            g.find('name').text, g.find('volume').text))
                    except KeyError:
                        logging.debug('knowledge goals for {} had no volume information'.format(
                            g.find('name').text))

                # except AttributeError:
                #    logging.debug('Goal loaded which does not have dose attribute.')
                # Regardless, add the goal now
                Goals.add_goal(g, connect.get_current('Plan'))

    status.next_step(text="Adding Objectives.", num=4)
    objective_elements = Objectives.select_objective_protocol(order_name=order_name,
                                                              protocol=protocol)
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    # TODO: Go back to planning structs and generate a mapping to be used for OTVs, etc
    #  but for now, we'll match to the closest suffix

    gen_obj_targets = ['OTV1_','sOTVu1_','OTV1_EZ_',
                   'OTV2_','sOTVu2_','OTV2_EZ_',
                   'OTV3_','sOTVu3_','OTV3_EZ_',
                   'OTV4_','sOTVu4_','OTV4_EZ_',
                   'OTV5_','sOTVu5_','OTV5_EZ_',
                   'sOTVu1','sOTVu2','sOTVu3',
                   'sOTVu4','sOTVu5',
                   'ring1_','ring2_','ring3_','ring4_','ring5_']
    obj_targets = []
    for r in rois:
        for g in gen_obj_targets:
            if g in r:
                if g not in translation_map:
                    translation_map[g] = [None] * 2
                translation_map[g][0] = r
                obj_targets.append(r)
                logging.debug('Added a target match {}'.format(r))
    # TODO: Decide how we want the saved xml file to look. Do we want it a
    #  simple mapping+protocol? If so, the xml element file should really be unaltered
    #  we'd map an xml-input to objectives using the mapping, save the mapping and
    #  output the xml-result using the inverse mapping

    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_n = o.find('name').text
            o_t = o.find('type').text
            o_d = o.find('dose').text
            if o_n in translation_map:
                s_roi = translation_map[o_n][0]
            else:
                s_roi = None

            if "%" in o.find('dose').attrib['units']:
                # Define the unmatched and unmodified protocol name and dose
                o_r = o.find('dose').attrib['roi']
                # See if the goal is on a matched target and change the % dose of the attributed ROI
                # to match the user input target and dose level for that named structure
                # Correct the relative dose to the user-specified dose levels for this structure
                if o_r in translation_map:
                    # TODO reconcile DFO with rest of modifications for elementrees
                    s_dose = float(translation_map[o_r][1])# * float(o_d) / 100
                    if o_t == 'DFO':
                        logging.debug('s_dose {}, tr {}, o_d {}, low {}'.format(
                            s_dose,translation_map[o_r][1],o_d,o.find('dose').attrib['low']
                        ))
                        s_dose = s_dose * float(o_d) / 100
                        o.find('dose').attrib['units'] = "Gy"
                        o.find('dose').attrib['low'] = float(translation_map[o_r][1]) *\
                                                       float(o.find('dose').attrib['low']) / 100
                    Objectives.add_objective(o,
                                             exam=exam,
                                             case=case,
                                             plan=plan,
                                             beamset=beamset,
                                             s_roi=s_roi,
                                             s_dose=s_dose,
                                             s_weight=None,
                                             restrict_beamset=None)
                else:
                    logging.debug('No match found for objective on ROI: {}'.format(o_r))
                    s_dose = 0
                    pass
            else:
                s_dose = None
                Objectives.add_objective(o,
                                         exam=exam,
                                         case=case,
                                         plan=plan,
                                         beamset=beamset,
                                         s_roi=s_roi,
                                         s_dose=s_dose,
                                         s_weight=None,
                                         restrict_beamset=None)




if __name__ == '__main__':
    main()
