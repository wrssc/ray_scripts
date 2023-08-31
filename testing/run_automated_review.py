""" Automated Review Only

    """

import sys
from pathlib import Path

plan_review_path = Path(__file__).parent.parent / "library" / "PlanReview"
sys.path.insert(1, str(plan_review_path))
from PlanReview.automated_review import automated_tests

automated_tests()
