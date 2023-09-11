import PySimpleGUI as sg
from collections import namedtuple
import logging
from PlanReview.review_definitions import FAIL, RED_CIRCLE, PASS, GREEN_CIRCLE
from PlanReview.review_definitions import YELLOW_CIRCLE, ALERT, BLUE_CIRCLE, DOMAIN_TYPE


def build_tree_element(parent_key: str, child_key: str, pass_result: str,
                       message_str: str) -> tuple:
    """
    Builds an element for insertion in a PySimpleGui tree.

    Args:
        parent_key (str): The key of the parent node.
        child_key (str): The key of the child node.
        pass_result (str): The result of the test, either "Pass", "Fail",
        "Alert", or "".
        message_str (str): The user message.

    Returns:
        A tuple containing two lists.
        Parent list contains the node for the node and child
        list is the sub_node. Each list contains the following elements:
        [key, value, text, pass/fail result, icon]
    """

    # Determine the appropriate icon based on the pass result
    if pass_result == FAIL:
        icon = RED_CIRCLE
    elif pass_result == PASS:
        icon = GREEN_CIRCLE
    elif pass_result == ALERT:
        icon = YELLOW_CIRCLE
    else:
        icon = BLUE_CIRCLE

    # Create the node for the parent
    parent_node = [parent_key, child_key, child_key, pass_result, icon]

    # Create the node for the child
    child = [child_key, parent_key + '.' + child_key, message_str,
             pass_result, icon]

    return parent_node, child


def parse_level_tests(level_tests):
    # Insert Level Nodes
    overall_status = PASS
    status_icon = GREEN_CIRCLE

    statuses = [level[3] for level in level_tests]
    if FAIL in statuses:
        overall_status = FAIL
        status_icon = RED_CIRCLE
    elif ALERT in statuses:
        overall_status = ALERT
        status_icon = YELLOW_CIRCLE

    return overall_status, status_icon


def insert_tests_return_fails(test_data, treedata, fails):
    """
    Inserts test data into PySimpleGUI.TreeData and returns a list of test
    failures.

    Args:
        test_data (list): A list of test data to be inserted into the tree.
        Each element should be
            a tuple in the format (test_name, test_key, test_description,
            test_result, test_icon).
        treedata (PySimpleGUI.TreeData): The PySimpleGUI TreeData object to
        insert the test data into.
        fails (list): An empty list that will be populated with any test
        failures.

    Returns:
        bool: True if test_data is not empty, False otherwise.
    """
    if test_data:
        for test in test_data:
            test_name, test_key, test_description, test_result, test_icon = test
            logging.debug(f'test_name: {test_name}, test_key: {test_key},'
                          f'test_description: {test_description}')
            treedata.Insert(test_name, test_key, test_description,
                            [test_result, ""], icon=test_icon)
            if (test_key == FAIL or test_key == ALERT) and test_result:
                fails.append(
                    f"TEST: {test_name}: {test_key}: {test_description}")
        return True
    else:
        return False


def load_rsos(rso, beamsets):
    # Make a list of raystation objects for each beamset return list
    # Initialize return variable
    Pd = namedtuple('Pd', [
        'error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    rsos = []
    for bs in rso.plan.BeamSets:
        if bs.DicomPlanLabel in beamsets:
            rsos.append(Pd(
                error=[], patient=rso.patient, case=rso.case, exam=rso.exam,
                db=rso.db, plan=rso.plan, beamset=bs))
    return rsos


def build_review_tree(rso, exam_level_tests, plan_level_tests,
                      beamset_levels, sandbox_level_tests, message_logs,
                      beamsets=[]):
    # beamset_levels is now a dict {dicomplanlabel: [beamset tests]}
    test_results = []  # Something is probably going to be broken on final dose
    # Tree Levels
    patient_key = (DOMAIN_TYPE['PATIENT_KEY'], f"Patient: {rso.patient.PatientID}")
    exam_key = (DOMAIN_TYPE['EXAM_KEY'], f"Exam: {rso.exam.Name}")
    plan_key = (DOMAIN_TYPE['PLAN_KEY'], f"Plan: {rso.plan.Name}")
    beamsets_key = {}
    all_bs_tests = []
    logging.debug(f'Beamset levels {beamset_levels.keys()}')
    if beamsets:
        rsos = load_rsos(rso, beamsets)
    else:
        rsos = [rso]
    for r in rsos:
        beamsets_key[r.beamset.DicomPlanLabel] = (
            DOMAIN_TYPE['BEAMSET_KEY'], f"Beam Set: {r.beamset.DicomPlanLabel}")
        all_bs_tests.append(beamset_levels[r.beamset.DicomPlanLabel])

    # beamset_key = (
    #     DOMAIN_TYPE['BEAMSET_KEY'], "Beam Set: " + rso.beamset.DicomPlanLabel)
    sandbox_key = (DOMAIN_TYPE['SANDBOX_KEY'], "Sandbox: ")
    rx_key = (DOMAIN_TYPE['RX_KEY'], "Prescription")
    log_key = (DOMAIN_TYPE['LOG_KEY'], "Logging")
    #
    tree_data = sg.TreeData()
    # TREE BUILDING
    #
    # Insert main (patient) node
    patient_level_pass, patient_icon = parse_level_tests(
        exam_level_tests + plan_level_tests + all_bs_tests)
    tree_data.Insert("", patient_key[0], patient_key[1], patient_level_pass,
                     icon=patient_icon)
    # Insert Exam Level Nodes
    exam_level_pass, exam_icon = parse_level_tests(exam_level_tests)
    tree_data.Insert(patient_key[0], exam_key[0], exam_key[1], exam_level_pass,
                     icon=exam_icon)
    insert_tests_return_fails(exam_level_tests, tree_data, test_results)
    # Insert Plan Level notes
    plan_level_pass, plan_icon = parse_level_tests(plan_level_tests)
    tree_data.Insert(patient_key[0], plan_key[0], plan_key[1], plan_level_pass,
                     icon=plan_icon)
    insert_tests_return_fails(plan_level_tests, tree_data, test_results)
    #
    # Insert Beamset Level Nodes
    for beamset_name, beamset_tests in beamset_levels.items():
        parent, child = beamsets_key[beamset_name]
        beamset_level_pass, beamset_icon = parse_level_tests(beamset_tests)
        tree_data.Insert(patient_key[0], parent, child,
                         beamset_level_pass, icon=beamset_icon)
        insert_tests_return_fails(beamset_tests, tree_data, test_results)
    #
    # Insert Sandbox Level Nodes
    sandbox_level_pass, sandbox_icon = parse_level_tests(sandbox_level_tests)
    tree_data.Insert(patient_key[0], sandbox_key[0], sandbox_key[1],
                     sandbox_level_pass, icon=sandbox_icon)
    insert_tests_return_fails(sandbox_level_tests, tree_data, test_results)
    #
    # Log Level
    tree_data.Insert(patient_key[0], log_key[0], log_key[1], "")
    if message_logs:
        for m in message_logs:
            tree_data.Insert(m[0], m[1], m[2], [
                m[3]])  # Note the list of the last entry. Can this be of use?
    return tree_data
