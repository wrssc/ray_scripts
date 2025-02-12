""" Final Dosimetry Safety Review
    --version 1.0.3--Run basic plan integrity checks and parse the log file.

    """

import sys
from pathlib import Path
# This function is pointed to the PlanReview folder where the real magic happens
plan_review_path = Path(__file__).parent.parent / "library" / "PlanReview"
sys.path.insert(1, str(plan_review_path))
from PlanReview.physics_review import physics_review

# Similarly, point to the DITTO folder where more magic happens
ditto_path = Path(__file__).parent.parent / "library" / "DITTO"
sys.path.insert(1, str(ditto_path))

physics_review(do_physics_review=True, review_type='Dosimetry')
