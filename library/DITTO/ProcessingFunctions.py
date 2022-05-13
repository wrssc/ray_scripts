import numpy as np
import re
from DicomPairClasses import Result


def assess_case_insensitive_match(element_pair, comment=""):
    value_pair = element_pair.value_pair
    # Exact match, got lucky
    if value_pair[0] == value_pair[1]:
        return Result.ELEMENT_MATCH, "Perfect Match"

    # Make sure both are not None first
    if (value_pair[0] is None) or (value_pair[1] is None):
        return Result.ELEMENT_MISMATCH, "Mismatch declared: At least one value is None."

    if comment == "Name":
        # Case-insensitive match on First and Last name (strip at ^)
        vp1_formatted = tuple(re.split(r'\^', str(value_pair[0])))
        vp2_formatted = tuple(re.split(r'\^', str(value_pair[1])))
        try:
            if bool(re.match(r'^' + vp1_formatted[0] + r'$', vp2_formatted[0], re.IGNORECASE)) and \
                    bool(re.match(re.escape(vp1_formatted[1]), re.escape(vp2_formatted[1]), re.IGNORECASE)):
                return Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, "Case insensitive name match"
            else:
                return Result.ELEMENT_MISMATCH, "Mismatch declared on a name"
        except IndexError:
            if bool(re.match(r'^' + vp1_formatted[0] + r'$', vp2_formatted[0], re.IGNORECASE)):
                return Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, "Name match, but only one. Cher?"
            else:
                return Result.ELEMENT_MISMATCH, "Mismatch declared on a single name Cher != Drake"
    else:
        vp1_formatted = str(value_pair[0]).casefold()
        vp2_formatted = str(value_pair[1]).casefold()
        if vp1_formatted == vp2_formatted:
            return Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, "Case insensitive match"
        else:
            return Result.ELEMENT_MISMATCH, "Mismatch declared in any case."


def return_expected_mismatch(element_pair, comment=""):
    if element_pair.match_result == Result.ELEMENT_MISMATCH:
        return (Result.ELEMENT_EXPECTED_MISMATCH, comment)
    else:
        return (element_pair.match_result, comment)


def return_expected_unique_to_raystation(element_pair, comment=""):
    # Verify that the first item is unique.
    if element_pair.is_unique_to_dataset1():
        return (Result.ELEMENT_EXPECTED_UNIQUE_TO_1, comment)

    # The item was not unique to dataset 2. Surprise! Return raw match result.
    comment = "Expected unique to RayStation, but it is not."
    return (element_pair.match_result, comment)


def return_expected_unique_to_aria(element_pair, comment=""):
    # Verify that the second item is unique.
    if element_pair.is_unique_to_dataset2():
        return (Result.ELEMENT_EXPECTED_UNIQUE_TO_2, comment)

    # The item was not unique to dataset 2. Surprise! Return raw match result.
    comment = "Expected unique to Aria, but it is not."
    return (element_pair.match_result, comment)


def assess_near_match(element_pair, comment="", tolerance_value=0.01):
    # Check the case for trivial equality
    value_pair = element_pair.value_pair
    if value_pair[0] == value_pair[1]:
        return (Result.ELEMENT_MATCH, "Perfect match")

    # Make sure both are not None first
    if (value_pair[0] is None) or (value_pair[1] is None):
        return (Result.ELEMENT_MISMATCH, "Mismatch declared: At least one value is None.")

    ds1_array = np.array(value_pair[0])
    ds2_array = np.array(value_pair[1])
    if np.allclose(ds1_array, ds2_array, rtol=0.0, atol=tolerance_value):
        return (Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, comment)
    else:
        return (Result.ELEMENT_MISMATCH, comment)


def process_ssd(element_pair, comment=""):
    # Get name of parent
    parent_name = element_pair.parent.get_name()

    sequence_item_name, index = parent_name.split("=")
    if sequence_item_name == "ControlPointIndex":
        if index == "0":
            return assess_near_match(
                element_pair,
                comment="",
                tolerance_value=0.01
            )
        else:
            return return_expected_unique_to_raystation(
                element_pair,
                comment="SSD is unique to RayStation for ControlPoint index > 0"
            )

    # Ran out of special cases, return raw match result
    return (element_pair.match_result, comment)


def process_treatment_machine_name(element_pair, comment=""):
    ray_machine, aria_machine = element_pair.value_pair

    TRUEBEAM_M120 = ["TrueBeam2588", "TrueBeam2871", "TrueBeam3744"]
    TRUEBEAM_STX = ["TrueBeam1358"]

    if (ray_machine == "TrueBeam") and (aria_machine in TRUEBEAM_M120):
        comment = f"Aria {aria_machine} corresponds to RayStation {ray_machine}"
        return (Result.ELEMENT_MATCH, comment)
    elif (ray_machine == "TrueBeamSTx") and (aria_machine in TRUEBEAM_STX):
        comment = f"Aria {aria_machine} corresponds to RayStation {ray_machine}"
        return (Result.ELEMENT_MATCH, comment)

    # Ran out of special cases, return raw match result
    return (element_pair.match_result, comment)


"""
ELEMENTS WITH COMPLEX BEHAVIOR
* SourceToSurfaceDistance
** Should match for ControlPointIndex=0
** Should be unique to RayStation for ControlPointIndex<1
* Manufacturer
** Should be a mismatch in root
** Should be unique to aria in Beam
"""

PROCESS_FUNCTION_DICT = {
    "PatientName": (assess_case_insensitive_match, {"comment": "Name"}),
    "BolusID": (return_expected_unique_to_raystation, {}),
    "DeviceSerialNumber": (return_expected_unique_to_aria, {}),
    "InstitutionName": (return_expected_unique_to_aria, {}),
    "InstitutionalDepartmentName": (return_expected_unique_to_aria, {}),
    "Manufacturer": (return_expected_unique_to_aria, {}),
    "ManufacturerModelName": (return_expected_unique_to_aria, {}),
    "ReferencedToleranceTableNumber": (return_expected_unique_to_aria, {}),
    "ReferencedPatientSetupNumber": (
        return_expected_mismatch, {"comment": "Numerical value may be different due to field reordering"}),
    "SoftwareVersions": (return_expected_mismatch, {"comment": "RayStation is not Aria"}),
    "SourceToSurfaceDistance": (process_ssd, {}),
    "LeafJawPositions": (assess_near_match, {"tolerance_value": 0.01}),  # 0.01 mm
    "TableTopLateralPosition": (return_expected_unique_to_aria, {}),
    "TableTopLongitudinalPosition": (return_expected_unique_to_aria, {}),
    "TableTopVerticalPosition": (return_expected_unique_to_aria, {}),
    "TreatmentMachineName": (process_treatment_machine_name, {}),
}
