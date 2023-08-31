from PlanReview.qa_tests.test_plan.check_plan_approved import check_plan_approved
from PlanReview.review_definitions import REVIEW_LEVELS


def get_plan_level_tests(rso, physics_review=True):
    if not rso.plan:
        return {}
    plan_checks_dict = {
        f"{REVIEW_LEVELS['PLAN_DATA']}::Plan approval status":
            (check_plan_approved, {"do_physics_review": physics_review}),
    }
    return plan_checks_dict
