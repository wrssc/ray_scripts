""" Guided tbi_autoplanning
    Requires contours [External, Kidneys, Lungs] defined on HFS and FFS scans
    """

import sys
from pathlib import Path
# This function is pointed to the TBI folder where the real magic happens
auto_tbi_path = Path(__file__).parent.parent / "library" / "tbi_autoplanning"
sys.path.insert(1, str(auto_tbi_path))
from tbi_autoplanning.autoplan_tomo_vmat_tbi import tbi_gui

tbi_gui()
