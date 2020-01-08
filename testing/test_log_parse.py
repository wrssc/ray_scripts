""" Test log parsing

"""
import UserInterface
import PlanQualityAssuranceTests
import connect
import logging
import os
import webbrowser
import GeneralOperations
from GeneralOperations import logcrit
import sys


def main():
    patient = GeneralOperations.find_scope(level='Patient')
    case = GeneralOperations.find_scope(level='Case')
    exam = GeneralOperations.find_scope(level='Examination')
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')
    #try:
    #    patient = connect.get_current('Patient')
    #    case = connect.get_current("Case")
    #    exam = connect.get_current("Examination")
    #    plan = connect.get_current("Plan")
    #    beamset = connect.get_current("Beamset")
    #except:
    #    logging.warning("patient, case and examination must be loaded")

    # Report Examination information
    # patient.Cases['Case 1'].Examinations['CT 1'].GetStoredDicomTagValueForVerification
    # series_number = exam.GetStoredDicomTagValueForVerification(Group=0x020, Element=0x011)
    # slice_thickness = exam.GetStoredDicomTagValueForVerification(Group=0x018,Element=0x050)
    # gantry_tilt = exam.GetStoredDicomTagValueForVerification(Group=0x018,Element=1120)
    # ct_info = {}

    grid_test = True
    simfid_test = True

    message = ''
    # SIMFIDUCIAL TEST
    if simfid_test:
        fiducial_point = 'SimFiducials'
        fiducial_error = False
        error = PlanQualityAssuranceTests.simfiducial_test(case=case, exam=exam, poi=fiducial_point)
        if error is None:
            message += 'Simfiducial point has coordinates'
        else:
            message += error



    if grid_test:
        fine_grid_names = ['_SBR_', '_SRS_']
        fine_grid_size = 0.1
        coarse_grid_names = ['_THI_', '_VMA_', '_3DC_', '_BST_', '_DCA_']
        coarse_grid_size = 0.2
        fine_grid_error = PlanQualityAssuranceTests.gridsize_test(beamset=beamset,
                                                                  plan_string=fine_grid_names,
                                                                  nominal_grid_size=fine_grid_size)
        coarse_grid_error = PlanQualityAssuranceTests.gridsize_test(beamset=beamset,
                                                                    plan_string=coarse_grid_names,
                                                                    nominal_grid_size=coarse_grid_size)
        if len(fine_grid_error) != 0:
            logging.warning('Dose grid check returned an error {}'.format(fine_grid_error))
            # plan.SetDefaultDoseGrid(VoxelSize={'x': fine_grid_size, 'y': fine_grid_size, 'z': fine_grid_size})
            logging.info('Grid size was changed for SBRT-type plan')
        elif len(coarse_grid_error) != 0:
            logging.warning('Dose grid check returned an error {}'.format(coarse_grid_error))
            # plan.SetDefaultDoseGrid(VoxelSize={'x': coarse_grid_size, 'y': coarse_grid_size, 'z': coarse_grid_size})
            logging.info('Grid size was changed for Normal-type plan')

    important = []
#    keep_phrases = ["CRITICAL", "WARNING"]
    keep_phrases = ["CRITICAL"]
    log_dir = r"Q:\\RadOnc\RayStation\RayScripts\logs"
    log_file = patient.PatientID + '.txt'
    infile = os.path.join(log_dir, patient.PatientID, log_file)

    with open(infile) as f:
        f = f.readlines()

    for line in f:
        for phrase in keep_phrases:
            if phrase in line:
                split = line.split("::")
                important.append(split)
                message += line + '\n'
                break
    dialog = UserInterface.RichTextBox(text=message)
    dialog.show()
    # webbrowser.open(infile)
    # connect.await_user_input('Check it out')



if __name__ == '__main__':
    main()
