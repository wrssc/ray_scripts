""" Physics Review with Document

    """

import sys
from pathlib import Path

plan_review_path = Path(__file__).parent.parent / "library" / "PlanReview"
sys.path.insert(1, str(plan_review_path))
from PlanReview.physics_review import physics_review

physics_review(rso=None, do_physics_review=True)
