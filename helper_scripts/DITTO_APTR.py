""" DICOM Integrity Tool - Aria Plan Transfer Review

"""

import sys
from pathlib import Path

ditto_path = Path(__file__).parent.parent / "library" / "DITTO"
sys.path.insert(1, str(ditto_path))
import DITTO.AriaRTPlanQR as AriaRTPlanQR
import DITTO.DicomIntegrityTool_APTR as DicomIntegrityTool_APTR
import logging


aria_file_location, rs_file_location, selected_rs = AriaRTPlanQR.aria_qr()

logging.debug(f"Aria file location: {aria_file_location}")
logging.debug(f"RayStation file location: {rs_file_location}")

DicomIntegrityTool_APTR.run_dicom_integrity_tool(
    rs_file_location,
    aria_file_location,
    file_label1="RayStation",
    file_label2="Aria",
)
