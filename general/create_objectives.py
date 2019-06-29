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
    order_name = 'GBM Brain 6000cGy in 30Fx [Single-Phase Stupp]'
    path_protocols = os.path.join(os.path.dirname(__file__), protocol_folder, institution_folder)
    objective_elements = Objectives.select_objective_protocol(filename=file,
                                                              folder=path_protocols,
                                                              order_name=order_name)
    ## This one searches the whole directory
    ## file = 'planning_structs_conventional.xml'
    ## objective_elements = Objectives.select_objective_protocol()
    ## TODO: specify the objective directory for a generic objectiveset file
    logging.debug("selected file {}".format(path_protocols))
    # Parse each type in a separate function
    # Add matching elements
    # Add objective function should know whether something is absolute or relative for dose and volume

    for objsets in objective_elements:
        objectives = objsets.findall('./objectives/roi')
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

if __name__ == '__main__':
    main()
