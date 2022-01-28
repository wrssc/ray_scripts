import numpy as np
from DicomPairClasses import Result


def return_expected_mismatch(value_pair, comment=""):
    return (Result.ELEMENT_EXPECTED_MISMATCH, comment)


def assess_near_match(value_pair, comment="", tolerance_value=0.01):

    # Make sure both are not None first
    if (value_pair[0] is None) or (value_pair[1] is None):
        return (Result.ELEMENT_MISMATCH, "Mismatch declared: At least one value is None.")

    ds1_array = np.array(value_pair[0])
    ds2_array = np.array(value_pair[1])
    if np.allclose(ds1_array, ds2_array, rtol=0.0, atol=tolerance_value):
        return (Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, comment)
    else:
        return (Result.ELEMENT_MISMATCH, comment)


PROCESS_FUNCTION_DICT = {
    "SoftwareVersions": (return_expected_mismatch, {"comment": "RayStation is not Aria"}),
    "LeafJawPositions": (assess_near_match, {"tolerance_value": 0.01}),  # 0.01 mm
    "TableTopLateralPosition": (return_expected_mismatch, {}),
    "TableTopLongitudinalPosition": (return_expected_mismatch, {}),
    "TableTopVerticalPosition": (return_expected_mismatch, {}),
}
