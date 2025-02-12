import logging
import datetime
from collections import OrderedDict
from PlanReview.review_definitions import DOMAIN_TYPE, FAIL
from PlanReview.qa_tests.test_examination import get_exam_level_tests
from PlanReview.qa_tests.test_plan import get_plan_level_tests
from PlanReview.qa_tests.test_beamset import get_beamset_level_tests
from PlanReview.qa_tests.test_sandbox import get_sandbox_level_tests
from PlanReview.qa_tests.test_plan import parse_order_selection
from PlanReview.qa_tests.analyze_logs import retrieve_logs
from PlanReview.utils import get_user_name
from PlanReview.utils.email_results import save_report, email_report


def parse_time_log(time_log, time0, time1, test_name):
    time_diff = time1 - time0
    time_log[test_name] = time_diff.total_seconds()
    return time_log


def update_progress_bar(progress_bar, progress_text, tests_performed, progress_total, message_text):
    if progress_bar is not None and progress_text is not None:
        progress_bar.update(
            current_count=int(100 * tests_performed / progress_total))
        progress_text.update(message_text)
        progress_bar.UpdateBar(tests_performed)


def log_time_log(time_log):

    # Sort the time_log by duration
    sorted_time_log = OrderedDict(sorted(time_log.items(), key=lambda item: item[1], reverse=True))

    # Determine the maximum length of test names for alignment
    max_test_name_length = max(len(test_name) for test_name in sorted_time_log)

    # Log each test and its duration in a formatted way
    logging.info(f"{'Test Name':<{max_test_name_length}} | Duration (s)")
    logging.info("-" * (max_test_name_length + 15))
    for test_name, duration in sorted_time_log.items():
        logging.info(f"{test_name:<{max_test_name_length}} | {duration:.2f}")


def execute_test(rso, test_name, test_function, kwargs, time_log):
    logging.debug(f'Executing test {test_name}')
    time_0 = datetime.datetime.now()
    try:
        pass_result, message = test_function(rso=rso, **kwargs)
    except Exception as e:
        message = f"Error: {str(e)}"
        # Send an error report email and return a failure
        # Save and email the report
        user_name = get_user_name()
        file_path = save_report(
            report_type='error_report',
            patient_id=rso.patient.PatientID,
            beamset_name=rso.beamset.DicomPlanLabel,
            user_name=user_name,
            report_text=f"Automated report: error occurred while executing the test: {test_name}\n\n{str(e)}"
        )
        email_report(file_path, 'error_report', source='script')
        pass_result = FAIL
    time_log = parse_time_log(time_log, time_0, datetime.datetime.now(), test_function.__name__)
    return pass_result, message, time_log


def perform_automated_checks(rso, do_physics_review,
                             display_progress, values, beamsets=[]):
    """
        Builds and returns a review tree for a radiotherapy treatment plan
        using PySimpleGUI.

        Args:
            rso: The radiotherapy structure object.
            do_physics_review: A boolean value indicating whether to perform physics review.
            display_progress: A boolean value indicating whether to display a progress bar.
            values: A dictionary containing the values of the GUI.
            beamsets: A list of beamsets to be checked

        Returns:
            A tuple containing the tree data and tree children.
    """
    from PlanReview.guis import (
        build_tree_element, build_review_tree, display_progress_bar, load_rsos)
    # Show progress bar
    if display_progress:
        progress_window, progress_bar, progress_text = display_progress_bar()
    else:
        progress_window = None
        progress_bar = None
        progress_text = None
    time_log = {}

    # Tree Levels (move these to tree building)
    patient_key = (DOMAIN_TYPE['PATIENT_KEY'], "Patient: " + rso.patient.PatientID)
    exam_key = (DOMAIN_TYPE['EXAM_KEY'], "Exam: " + rso.exam.Name)
    plan_key = (DOMAIN_TYPE['PLAN_KEY'], "Plan: " + rso.plan.Name)
    # If multiple beamsets are flagged find objects for all of them
    if beamsets:
        rsos = load_rsos(rso, beamsets)
    else:
        rsos = [rso]
    sandbox_key = (DOMAIN_TYPE['SANDBOX_KEY'], "Sandbox: ")
    rx_key = (DOMAIN_TYPE['RX_KEY'], "Prescription")
    #

    tree_children = []

    # Parse logs
    time_0 = datetime.datetime.now()
    message_logs = retrieve_logs(rso)
    time_log = parse_time_log(time_log, time_0,
                              datetime.datetime.now(), 'parse_logs')

    # Gather Patient Level Checks
    patient_checks_dict = get_exam_level_tests(rso, values)
    # Gather Plan Level Checks
    plan_checks_dict = get_plan_level_tests(rso, do_physics_review)
    # Gather BeamSet Level Checks
    beamset_checks = {
        r.beamset.DicomPlanLabel: get_beamset_level_tests(
            r, do_physics_review, message_logs,
            values=values)
        for r in rsos}
    # Gather SandBox Level Checks
    sandbox_checks_dict = get_sandbox_level_tests(rso, do_physics_review)

    progress_total = len(patient_checks_dict.keys()) \
                     + len(plan_checks_dict.keys()) \
                     + sum([len(v) for v in beamset_checks.values()]) + 1
    tests_performed = 1
    update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                        'Running Exam Tests...')
    # Execute qa_tests
    exam_level_tests = []
    for key, p_func in patient_checks_dict.items():
        update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                            f'Exam Test: {key}...')
        pass_result, message, time_log = execute_test(rso, key, p_func[0], p_func[1], time_log)
        # logging.debug(f'Executing test {key}')
        # time_0 = datetime.datetime.now()
        # pass_result, message = p_func[0](rso=rso, **p_func[1])
        # time_log = parse_time_log(time_log, time_0, datetime.datetime.now(), key)
        node, child = build_tree_element(parent_key=exam_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        exam_level_tests.extend([node, child])
        exam_children = [DOMAIN_TYPE['EXAM_KEY'], rso.exam.Name]
        exam_children.extend(child)
        tree_children.append(exam_children)
        tests_performed += 1
    update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                        'Running Plan Tests...')
    # Execute Plan Level Checks
    plan_level_tests = []
    # Parse the log file for the treatment planning order selected.
    dialog_key = 'Treatment Planning Order Selection'
    tpo_dialog = parse_order_selection(
        beamset_name=rso.beamset.DicomPlanLabel,
        messages=message_logs,
        dialog_key=dialog_key)
    node, child = build_tree_element(parent_key=plan_key[0],
                                     child_key=dialog_key,
                                     pass_result=tpo_dialog[dialog_key][0],
                                     message_str=tpo_dialog[dialog_key][1])
    plan_level_tests.extend([node, child])
    for k, v in tpo_dialog.items():
        if k != dialog_key and all(v):
            node, child = build_tree_element(parent_key=dialog_key,
                                             child_key=k,
                                             pass_result=v[0],
                                             message_str=v[1])
            plan_level_tests.extend([node, child])
            plan_children = [DOMAIN_TYPE['PLAN_KEY'], rso.plan.Name]
            plan_children.extend(child)
            tree_children.append(plan_children)
    # FINISH PLAN LEVEL CHECKS DEFINED IN plan_checks_dict
    for key, pl_func in plan_checks_dict.items():
        update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                            f'Plan Test: {key}')
        pass_result, message, time_log = execute_test(rso, key, pl_func[0], pl_func[1], time_log)
        # time_0 = datetime.datetime.now()
        # pass_result, message = pl_func[0](rso=rso, **pl_func[1])
        # time_log = parse_time_log(time_log, time_0, datetime.datetime.now(), key)
        node, child = build_tree_element(parent_key=plan_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        plan_level_tests.extend([node, child])
        plan_children = [DOMAIN_TYPE['PLAN_KEY'], rso.plan.Name]
        plan_children.extend(child)
        tree_children.append(plan_children)
    update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                        'Running BeamSet Tests...')

    #
    # BEAMSET LEVEL CHECKS
    beamset_levels = {}
    for r in rsos:
        beamset_level_tests = []
        bs_name = r.beamset.DicomPlanLabel
        update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                            f'Testing BeamSet: {bs_name}...')
        for key, b_func in beamset_checks[bs_name].items():
            update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                                f'BeamSet Test: {key}')
            pass_result, message, time_log = execute_test(r, key, b_func[0], b_func[1], time_log)
            # time_0 = datetime.datetime.now()
            # pass_result, message = b_func[0](rso=r, **b_func[1])
            # time_log = parse_time_log(time_log, time_0, datetime.datetime.now(), key)
            node, child = build_tree_element(
                parent_key=DOMAIN_TYPE['BEAMSET_KEY'],
                child_key=key, pass_result=pass_result, message_str=message)
            beamset_level_tests.extend([node, child])
            beamset_children = [DOMAIN_TYPE['BEAMSET_KEY'], bs_name]
            beamset_children.extend(child)
            tree_children.append(beamset_children)
            tests_performed += 1
        beamset_levels[bs_name] = beamset_level_tests
    #
    update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                        'Running Sandbox Tests...')
    #
    # SANDBOX LEVEL CHECKS
    sandbox_level_tests = []
    for key, s_func in sandbox_checks_dict.items():
        update_progress_bar(progress_bar, progress_text, tests_performed, progress_total,
                            f'Sandbox Test: {key}')
        pass_result, message, time_log = execute_test(rso, key, s_func[0], s_func[1], time_log)
        # time_0 = datetime.datetime.now()
        # pass_result, message = s_func[0](rso=rso, **s_func[1])
        # time_log = parse_time_log(time_log, time_0, datetime.datetime.now(), key)
        node, child = build_tree_element(parent_key=sandbox_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        sandbox_level_tests.extend([node, child])
        sandbox_children = [DOMAIN_TYPE['SANDBOX_KEY'], 'SANDBOX']
        sandbox_children.extend(child)
        tree_children.append(sandbox_children)

    tree_data = build_review_tree(rso, exam_level_tests,
                                  plan_level_tests,
                                  beamset_levels,
                                  sandbox_level_tests,
                                  message_logs,
                                  beamsets=beamsets)
    log_time_log(time_log)

    if display_progress:
        progress_window.close()
    return tree_data, tree_children
