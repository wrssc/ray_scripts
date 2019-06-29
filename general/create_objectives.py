""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""
import os
import logging
import connect
import Objectives


def main():
    """
    This will have a rather extensive dialog to take the user through the process of selecting an objective
    set, then loading them. Right now, I'm going to pivot to autointegration in the clinical goals.
    TODO: Modify for appropriate inputs for prompting a user to fill in dose values and such for objectives
    -Likely we'll find all % references to targets and then ask user to fill in values
    -Will need extensive parsing of xml files for unresolved references
    TODO: Likely used as an afterthought.May want to ask to delete current objectives
    """
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current("Case")
        examination = connect.get_current("Examination")
        plan = connect.get_current("Plan")
        beamset = connect.get_current("BeamSet")
    except:
        logging.warning("patient, case and examination must be loaded")

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
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    # TODO: Need to integrate the following with some smart user prompting for
    #  missing dose and structure references such as the PTV_p's and 100%'s of whatever
    #  we'll need to store some kind of translate table so the xml-out script knows how to map
    #  these objectives, i.e. PTV_p -> PTV_3000_MD_++ then translate the result back out

    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
        for o in objectives:
            o_name = o.find('name').text
            o_type = o.find('type').text
            # TESTING ONLY - TODO ELIMINATE THIS NEXT LINE
            # This will need to be a user supplied dose level.
            if o.find('dose').attrib['units'] == '%':
                s_dose = '50'
            else:
                s_dose = None

            Objectives.add_objective(o,
                                     case=case,
                                     plan=plan,
                                     beamset=beamset,
                                     s_roi=None,
                                     #    s_roi='PTV_Eval_5000',
                                     s_dose=s_dose,
                                     s_weight=None,
                                     restrict_beamset=None)


if __name__ == '__main__':
    main()
