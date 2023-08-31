from PlanReview.review_definitions import TOMO_DATA, TRUEBEAM_DATA, FAIL, \
    PASS, ALERT
from PlanReview.utils.get_machine import get_machine


def check_couch_type(rso):
    # Abbreviate geometries
    rg = rso.case.PatientModel.StructureSets[rso.exam.Name].RoiGeometries
    roi_list = [r.OfRoi.Name for r in rg]
    beam = rso.beamset.Beams[0]
    current_machine = get_machine(machine_name=beam.MachineReference.MachineName)
    wrong_supports = []
    correct_supports = []
    if current_machine.Name in TRUEBEAM_DATA['MACHINES']:
        wrong_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
    elif current_machine.Name in TOMO_DATA['MACHINES']:
        wrong_supports = [s for s in TRUEBEAM_DATA['SUPPORTS'] if s in roi_list]
        correct_supports = [s for s in TOMO_DATA['SUPPORTS'] if s in roi_list]
    if wrong_supports:
        message_str = 'Support Structure(s) {} are INCORRECT for  machine {}'.format(
            wrong_supports, current_machine.Name)
        pass_result = FAIL
    elif correct_supports:
        message_str = 'Support Structure(s) {} are correct for machine {}'.format(
            correct_supports, current_machine.Name)
        pass_result = PASS
    else:
        message_str = 'No couch structure found'
        pass_result = ALERT
    # Prepare output
    return pass_result, message_str
