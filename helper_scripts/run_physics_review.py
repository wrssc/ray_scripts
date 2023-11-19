""" Physics Review with Document
    --version 1.0.0--Run basic plan integrity checks and parse the log file.

    """

import sys
from pathlib import Path
# This function is pointed to the PlanReview folder where the real magic happens
plan_review_path = Path(__file__).parent.parent / "library" / "PlanReview"
sys.path.insert(1, str(plan_review_path))
from PlanReview.physics_review import physics_review
physics_review(rso=None, do_physics_review=True)
