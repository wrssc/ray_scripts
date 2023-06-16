from PlanReview.review_definitions import LEVELS
from PlanReview.qa_tests.test_examination import get_exam_level_tests
from PlanReview.qa_tests.test_plan import get_plan_level_tests
from PlanReview.qa_tests.test_beamset import get_beamset_level_tests
from PlanReview.qa_tests.test_sandbox import get_sandbox_level_tests
from PlanReview.qa_tests.test_beamset import parse_beamset_selection
from PlanReview.qa_tests.test_plan import parse_order_selection
from PlanReview.qa_tests.analyze_logs import retrieve_logs
from PlanReview.guis import build_tree_element, build_review_tree


def perform_automated_checks(rso, do_physics_review,
                             progress_bar, values, beamsets=None):
    """
        Builds and returns a review tree for a radiotherapy treatment plan
        using PySimpleGUI.

        Args:
            rso: The radiotherapy structure object.
            do_physics_review: A boolean value indicating whether to
            perform physics review.

        Returns:
            A tuple containing the tree data and tree children.
    """

    # Tree Levels (move these to tree building)
    patient_key = (LEVELS['PATIENT_KEY'], "Patient: " + rso.patient.PatientID)
    exam_key = (LEVELS['EXAM_KEY'], "Exam: " + rso.exam.Name)
    plan_key = (LEVELS['PLAN_KEY'], "Plan: " + rso.plan.Name)
    # TODO: Here we need to take the beamsets and extend them for each
    #       beamset in beamsets
    if beamsets:
        beamsets_key = [(
            LEVELS['BEAMSET_KEY'], "Beam Set: " + rso.beamset.DicomPlanLabel)]
    else:
        beamsets_key = [(
            LEVELS['BEAMSET_KEY'], "Beam Set: " + rso.beamset.DicomPlanLabel)]
    sandbox_key = (LEVELS['SANDBOX_KEY'], "Sandbox: ")
    rx_key = (LEVELS['RX_KEY'], "Prescription")
    log_key = (LEVELS['LOG_KEY'], "Logging")
    #

    tree_children = []

    """
    Gather Patient Level Checks
    """
    patient_checks_dict = get_exam_level_tests(rso,values)
    """
    Gather Plan Level Checks
    """
    plan_checks_dict = get_plan_level_tests(rso, do_physics_review)
    """
    Gather BeamSet Level Checks
    """
    beamset_checks_dict = get_beamset_level_tests(rso, do_physics_review)
    """
    Gather SandBox Level Checks
    """
    sandbox_checks_dict = get_sandbox_level_tests(rso, do_physics_review)

    progress_total = len(patient_checks_dict.keys()) \
                     + len(plan_checks_dict.keys()) \
                     + len(beamset_checks_dict.keys()) + 1
    """
    Parse logs
    """
    message_logs = retrieve_logs(rso, log_key)
    tests_performed = 1
    if progress_bar is not None:
        progress_bar.update(
            current_count=int(100 * tests_performed / progress_total))


    # Execute qa_tests
    exam_level_tests = []
    for key, p_func in patient_checks_dict.items():
        pass_result, message = p_func[0](rso=rso, **p_func[1])
        node, child = build_tree_element(parent_key=exam_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        exam_level_tests.extend([node, child])
        tree_children.append(child)
        tests_performed += 1
        if progress_bar is not None:
            progress_bar.update(
                current_count=int(100 * tests_performed/progress_total))

    """
    Execute Plan Level Checks
    """
    # Plan LevelChecks
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
            tree_children.append(child)
    # FINISH PLAN LEVEL CHECKS DEFINED IN plan_checks_dict
    for key, pl_func in plan_checks_dict.items():
        pass_result, message = pl_func[0](rso=rso, **pl_func[1])
        node, child = build_tree_element(parent_key=plan_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        plan_level_tests.extend([node, child])
        tree_children.append(child)
        if progress_bar is not None:
            progress_bar.update(
                current_count=int(100 * tests_performed/progress_total))

    #
    # BEAMSET LEVEL CHECKS
    beamset_level_tests = []

    #
    # Run dialog parse
    dialog_key = 'Beamset Template Selection'
    beamset_dialog = parse_beamset_selection(
        beamset_name=rso.beamset.DicomPlanLabel,
        messages=message_logs)
    node, child = build_tree_element(parent_key=beamsets_key[0][0],
                                     child_key=dialog_key,
                                     pass_result=beamset_dialog[dialog_key][0],
                                     message_str=beamset_dialog[dialog_key][1])
    beamset_level_tests.extend([node, child])
    for k, v in beamset_dialog.items():
        if k != dialog_key and all(v):
            node, child = build_tree_element(parent_key=dialog_key,
                                             child_key=k,
                                             pass_result=v[0],
                                             message_str=v[1])
            beamset_level_tests.extend([node, child])
            tree_children.append(child)

    # Run others
    for key, b_func in beamset_checks_dict.items():
        pass_result, message = b_func[0](rso=rso, **b_func[1])
        node, child = build_tree_element(parent_key=beamsets_key[0][0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        beamset_level_tests.extend([node, child])
        tree_children.append(child)
        if progress_bar is not None:
            progress_bar.update(
                current_count=int(100 * tests_performed/progress_total))

    #
    # SANDBOX LEVEL CHECKS
    sandbox_level_tests = []
    for key, s_func in sandbox_checks_dict.items():
        pass_result, message = s_func[0](rso=rso, **s_func[1])
        node, child = build_tree_element(parent_key=sandbox_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        sandbox_level_tests.extend([node, child])
        tree_children.append(child)

    tree_data = build_review_tree(rso, exam_level_tests,
                                  plan_level_tests,
                                  beamset_level_tests,
                                  sandbox_level_tests,
                                  message_logs)
    return tree_data, tree_children
