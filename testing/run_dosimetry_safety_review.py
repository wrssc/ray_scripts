""" Dosimetry Safety Check with pdf
    --version 0.0.0--Run basic plan integrity checks and parse the log file.

    """

import sys
from pathlib import Path
# This function is pointed to the PlanReview folder where the real magic happens
plan_review_path = Path(__file__).parent.parent / "library" / "PlanReview"
sys.path.insert(1, str(plan_review_path))
from PlanReview.dosimetry_review import dosimetry_safety_check
dosimetry_safety_check()
