from PlanReview.review_definitions import DOMAIN_TYPE
from PlanReview.qa_tests.test_examination import get_exam_level_tests
from PlanReview.qa_tests.test_plan import get_plan_level_tests
from PlanReview.qa_tests.test_beamset import get_beamset_level_tests
from PlanReview.qa_tests.test_sandbox import get_sandbox_level_tests
from PlanReview.qa_tests.test_beamset import parse_beamset_selection
from PlanReview.qa_tests.test_plan import parse_order_selection
from PlanReview.qa_tests.analyze_logs import retrieve_logs
from PlanReview.guis import build_tree_element, build_review_tree, \
    display_progress_bar, load_rsos


def perform_automated_checks(rso, do_physics_review,
                             display_progress, values, beamsets=[]):
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
    # Show progress bar
    if display_progress:
        progress_window, progress_bar = display_progress_bar()
    else:
        progress_bar = None
        progress_window = None

    # Tree Levels (move these to tree building)
    patient_key = (DOMAIN_TYPE['PATIENT_KEY'], "Patient: " + rso.patient.PatientID)
    exam_key = (DOMAIN_TYPE['EXAM_KEY'], "Exam: " + rso.exam.Name)
    plan_key = (DOMAIN_TYPE['PLAN_KEY'], "Plan: " + rso.plan.Name)
    #
    # If multiple beamsets are flagged find objects for all of them
    if beamsets:
        rsos = load_rsos(rso, beamsets)
    else:
        rsos = [rso]
    sandbox_key = (DOMAIN_TYPE['SANDBOX_KEY'], "Sandbox: ")
    rx_key = (DOMAIN_TYPE['RX_KEY'], "Prescription")
    log_key = (DOMAIN_TYPE['LOG_KEY'], "Logging")
    #

    tree_children = []

    """
    Gather Patient Level Checks
    """
    patient_checks_dict = get_exam_level_tests(rso, values)
    """
    Gather Plan Level Checks
    """
    plan_checks_dict = get_plan_level_tests(rso, do_physics_review)
    """
    Gather BeamSet Level Checks
    """
    beamset_checks = {
        r.beamset.DicomPlanLabel: get_beamset_level_tests(r, do_physics_review)
        for r in rsos}
    """
    Gather SandBox Level Checks
    """
    sandbox_checks_dict = get_sandbox_level_tests(rso, do_physics_review)

    progress_total = len(patient_checks_dict.keys()) \
                     + len(plan_checks_dict.keys()) \
                     + sum([len(v) for v in beamset_checks.values()]) + 1
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
        exam_children = [DOMAIN_TYPE['EXAM_KEY'], rso.exam.Name]
        exam_children.extend(child)
        tree_children.append(exam_children)
        tests_performed += 1
        if progress_bar is not None:
            progress_bar.update(
                current_count=int(100 * tests_performed / progress_total))

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
            plan_children = [DOMAIN_TYPE['PLAN_KEY'], rso.plan.Name]
            plan_children.extend(child)
            tree_children.append(plan_children)
    # FINISH PLAN LEVEL CHECKS DEFINED IN plan_checks_dict
    for key, pl_func in plan_checks_dict.items():
        pass_result, message = pl_func[0](rso=rso, **pl_func[1])
        node, child = build_tree_element(parent_key=plan_key[0],
                                         child_key=key,
                                         pass_result=pass_result,
                                         message_str=message)
        plan_level_tests.extend([node, child])
        plan_children = [DOMAIN_TYPE['PLAN_KEY'], rso.plan.Name]
        plan_children.extend(child)
        tree_children.append(plan_children)
        if progress_bar is not None:
            progress_bar.update(
                current_count=int(100 * tests_performed / progress_total))

    #
    # BEAMSET LEVEL CHECKS
    beamset_levels = {}
    for r in rsos:

        beamset_level_tests = []
        #
        # Run dialog parse
        bs_name = r.beamset.DicomPlanLabel
        dialog_key = 'Beamset Template Selection'
        beamset_dialog = parse_beamset_selection(
            beamset_name=bs_name, messages=message_logs)
        node, child = build_tree_element(
            parent_key=DOMAIN_TYPE['BEAMSET_KEY'],
            child_key=dialog_key, pass_result=beamset_dialog[dialog_key][0],
            message_str=beamset_dialog[dialog_key][1])
        beamset_level_tests.extend([node, child])
        for k, v in beamset_dialog.items():
            if k != dialog_key and all(v):
                node, child = build_tree_element(parent_key=dialog_key,
                                                 child_key=k,
                                                 pass_result=v[0],
                                                 message_str=v[1])
                beamset_level_tests.extend([node, child])
                beamset_children = [DOMAIN_TYPE['BEAMSET_KEY'], bs_name]
                beamset_children.extend(child)
                tree_children.append(beamset_children)

        # Run others
        for key, b_func in beamset_checks[bs_name].items():
            pass_result, message = b_func[0](rso=r, **b_func[1])
            node, child = build_tree_element(
                parent_key=DOMAIN_TYPE['BEAMSET_KEY'],
                child_key=key, pass_result=pass_result, message_str=message)
            beamset_level_tests.extend([node, child])
            beamset_children = [DOMAIN_TYPE['BEAMSET_KEY'], bs_name]
            beamset_children.extend(child)
            tree_children.append(beamset_children)
            if progress_bar is not None:
                progress_bar.update(
                    current_count=int(100 * tests_performed / progress_total))
        beamset_levels[bs_name] = beamset_level_tests

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
        sandbox_children = [DOMAIN_TYPE['SANDBOX_KEY'], 'SANDBOX']
        sandbox_children.extend(child)
        tree_children.append(sandbox_children)

    tree_data = build_review_tree(rso, exam_level_tests,
                                  plan_level_tests,
                                  beamset_levels,
                                  sandbox_level_tests,
                                  message_logs,
                                  beamsets=beamsets)

    if display_progress:
        progress_window.close()
    return tree_data, tree_children
