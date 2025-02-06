""" Guided TbiPlanning
    Requires contours [External, Kidneys, Lungs] defined on HFS and FFS scans
    """

import sys
from pathlib import Path
# This function is pointed to the TBI folder where the real magic happens
auto_tbi_path = Path(__file__).parent.parent / "library" / "TbiPlanning"
sys.path.insert(1, str(auto_tbi_path))
from TbiPlanning.autoplan_tomo_vmat_tbi import tbi_gui

tbi_gui()
