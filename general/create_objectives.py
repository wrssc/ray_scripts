""" Add objectives

    Contains functions required to load objectives from xml files
    add the objectives to RayStation. Contains functions for reassignment of an
    objective when the target name is not matched
"""
import sys
import os
import logging
import xml.etree.ElementTree
import connect
import Objectives



def main():
    """ Temp chunk of code to try to open an xml file"""
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
    ##file = 'planning_structs_conventional.xml'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file, folder=path_protocols)
    ## This one searches the whole directory
    ## tree = Objectives.select_objective_protocol()
    logging.debug("selected file {}".format(path_protocols))
    # Consider adding functionality for protocols, orders, etc...
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume
    for o in objective_elements:
        logging.debug('Returned the objectivesets: {}'.format(
            o.find('name').text))

    for objsets in objective_elements:
        #try:
        objectives = objsets.findall('./objectives/roi')
        # except:
        #    logging.debug("An issue exists with the list of elements from Objectives.py")
        ## objectives = objectiveset.findall('./objectives/roi')
        for o in objectives:
            o_name = o.find('name').text
            o_type = o.find('type').text
            # TESTING ONLY - TO DO ELIMINATE THIS NEXT LINE
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
    ##else:
    ##    logging.debug('Could not find objective set using tree = {}'.format(tree))


if __name__ == '__main__':
    main()
