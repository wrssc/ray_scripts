import numpy as np
import re
from DicomPairClasses import Result


def excuse_element_with_parent(element_pair, excused_parent, comment=""):
    """ Passes an expected mismatch/unique result when element has a specified parent 

    ----------
    PARAMETERS
    ----------
    element_pair : ElementPair
        The pair of DICOM elements being evaluated
    excused_parent : string, or list of string
        The name(s) of the DICOM sequence(s) that resulted in a mismatch or unique
        result to be excused as an expected mismatch or expected unique
    comment : string
        A comment, which may be passed into the element pair if desired

    -------
    RETURNS
    -------
    tup(Result, string)
        A result status, and a comment
    """

    # if parent is not a list, put it in a list
    if not isinstance(excused_parent, list):
        excused_parent_list = [excused_parent]
    else:
        excused_parent_list = excused_parent

    parent_name = element_pair.parent.parent.get_name()

    # Check to see if the element is excused.
    if parent_name in excused_parent_list:
        comment = f"{element_pair.attribute_name} is excused when it is in sequence {parent_name}"

        if element_pair.match_result == Result.ELEMENT_MISMATCH:
            return (Result.ELEMENT_EXPECTED_MISMATCH, comment)

        if element_pair.is_unique_to_dataset1():
            return (Result.ELEMENT_EXPECTED_UNIQUE_TO_1, comment)

        if element_pair.is_unique_to_dataset2():
            return (Result.ELEMENT_EXPECTED_UNIQUE_TO_2, comment)

    # If you get to this point, just return the match result
    return (element_pair.match_result, comment)


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
        vp1_formatted = tuple(re.split(r"\^", str(value_pair[0])))
        vp2_formatted = tuple(re.split(r"\^", str(value_pair[1])))
        try:
            if bool(
                re.match(
                    r"^" + vp1_formatted[0] + r"$", vp2_formatted[0], re.IGNORECASE
                )
            ) and bool(
                re.match(
                    re.escape(vp1_formatted[1]),
                    re.escape(vp2_formatted[1]),
                    re.IGNORECASE,
                )
            ):
                return (
                    Result.ELEMENT_ACCEPTABLE_NEAR_MATCH,
                    "Case insensitive name match",
                )
            else:
                return Result.ELEMENT_MISMATCH, "Mismatch declared on a name"
        except IndexError:
            if bool(
                re.match(
                    r"^" + vp1_formatted[0] + r"$", vp2_formatted[0], re.IGNORECASE
                )
            ):
                return (
                    Result.ELEMENT_ACCEPTABLE_NEAR_MATCH,
                    "Name match, but only one. Cher?",
                )
            else:
                return (
                    Result.ELEMENT_MISMATCH,
                    "Mismatch declared on a single name Cher != Drake",
                )
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
        return (
            Result.ELEMENT_MISMATCH,
            "Mismatch declared: At least one value is None.",
        )

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
            return assess_near_match(element_pair, comment="", tolerance_value=0.01)
        else:
            return return_expected_unique_to_raystation(
                element_pair,
                comment="SSD is unique to RayStation for ControlPoint index > 0",
            )

    # Ran out of special cases, return raw match result
    return (element_pair.match_result, comment)


def process_wedge_position_sequence(element_pair, comment=""):
    # Get name of parent
    parent_name = element_pair.parent.parent.parent.get_name()

    sequence_item_name, index = parent_name.split("=")
    if sequence_item_name == "ControlPointIndex":
        if index == "0":
            return (element_pair.match_result, comment)
        else:
            return return_expected_unique_to_raystation(
                element_pair,
                comment="Wedge position parameters are  unique to RayStation for ControlPoint index > 0",
            )

    # Ran out of special cases, return raw match result
    return (element_pair.match_result, comment)


def process_block_data(element_pair, comment=""):
    # ARIA connects the last and first point in an electron block whereaas RS drops it
    value_pair = element_pair.value_pair
    ds1_array = np.array(value_pair[0]).reshape(-1, 2)
    ds2_array = np.array(value_pair[1]).reshape(-1, 2)
    # Check if the last point is equal to the first in the ARIA block
    if np.array_equal(ds1_array, ds2_array):
        return Result.ELEMENT_MATCH, "Blocks identical"
    else:
        # If the last point is longer than the first pop it
        if np.isclose(ds1_array[0], ds1_array[-1]).all():
            ds1_pop = np.delete(ds1_array, (-1), axis=0)
            if np.array_equal(ds1_pop, ds2_array):
                return (
                    Result.ELEMENT_ACCEPTABLE_NEAR_MATCH,
                    "Blocks identical save the start/end connecting point",
                )
            elif np.isclose(ds1_pop, ds2_array).all():
                return Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, "Blocks within tolerance"
            else:
                return (
                    Result.ELEMENT_MISMATCH,
                    "Blocks do not match even without start/end connecting point",
                )
        else:
            return Result.ELEMENT_MISMATCH, "Blocks do not match"


def assess_block_points(element_pair, comment=""):
    # ARIA in a block: First point = Last point => Number of points is 1 greater than RS
    value_pair = element_pair.value_pair
    if int(value_pair[0]) == int(value_pair[1]) + 1:
        return (
            Result.ELEMENT_EXPECTED_MISMATCH,
            "Number of points match when start/end point is considered",
        )
    else:
        return Result.ELEMENT_MISMATCH, "Number of Points does not match"


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


def assess_tm_match(element_pair, comment=""):
    # RS is not using a valid TM format
    # TM Format: NEMA PS3.5 2013: HHMMSS.FFFFFF
    value_pair = element_pair.value_pair
    vp1_form = "{:.6f}".format(float(value_pair[0]))
    vp2_form = "{:.6f}".format(float(value_pair[1]))
    if vp1_form == vp2_form:
        return Result.ELEMENT_MATCH, "Value Representation TM Matched"
    else:
        vp1_form = "{:.0f}".format(float(value_pair[0]))
        vp2_form = "{:.0f}".format(float(value_pair[1]))
        if vp1_form == vp2_form:
            return Result.ELEMENT_ACCEPTABLE_NEAR_MATCH, "Time matched to 1.0 s"
        else:
            return (
                Result.ELEMENT_MISMATCH,
                "Mismatch declared on TM Value Representation",
            )


"""
ELEMENTS WITH COMPLEX BEHAVIOR
* SourceToSurfaceDistance
** Should match for ControlPointIndex=0
** Should be unique to RayStation for ControlPointIndex<1
* Manufacturer
** Should be a mismatch in root
** Should be unique to Aria in Beam
"""

UNIQUE_TO_RAYSTATION = {
    "GantryPitchAngle": (return_expected_unique_to_raystation, {}),
    "GantryPitchRotationDirection": (return_expected_unique_to_raystation, {}),
    "BolusID": (return_expected_unique_to_raystation, {}),
    "EffectiveWedgeAngle": (return_expected_unique_to_raystation, {}),
}

UNIQUE_TO_ARIA = {
    "SourceToBlockTrayDistance": (return_expected_unique_to_aria, {}),
    "AccessoryCode": (
        return_expected_unique_to_aria,
        {"comment": "AccessoryCode is set in RayStation by DicomExport.py"},
    ),
    "DoseRateSet": (
        return_expected_unique_to_aria,
        {"comment": "Dose Rate is set in Raystation by DicomExport.py"},
    ),
    "TableTopLateralPosition": (return_expected_unique_to_aria, {}),
    "TableTopLongitudinalPosition": (return_expected_unique_to_aria, {}),
    "TableTopVerticalPosition": (return_expected_unique_to_aria, {}),
    "DeviceSerialNumber": (return_expected_unique_to_aria, {}),
    "InstitutionName": (return_expected_unique_to_aria, {}),
    "InstitutionalDepartmentName": (return_expected_unique_to_aria, {}),
    "Manufacturer": (return_expected_unique_to_aria, {}),
    "ManufacturerModelName": (return_expected_unique_to_aria, {}),
    "ReferencedToleranceTableNumber": (return_expected_unique_to_aria, {}),
    "BeamLimitingDeviceAngleTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "GantryAngleTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "PatientSupportAngleTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "TableTopLateralPositionTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "TableTopLongitudinalPositionTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "TableTopVerticalPositionTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "ToleranceTableLabel": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "ToleranceTableNumber": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
    "BeamLimitingDevicePositionTolerance": (
        return_expected_unique_to_aria,
        {"comment": "Tolerance tables are unique to Aria"},
    ),
}

PROCESS_FUNCTION_DICT = {
    "PatientName": (assess_case_insensitive_match, {"comment": "Name"}),
    "ReferencedPatientSetupNumber": (
        return_expected_mismatch,
        {"comment": "Numerical value may be different due to field reordering"},
    ),
    "SoftwareVersions": (
        return_expected_mismatch,
        {"comment": "RayStation is not Aria"},
    ),
    "SourceToSurfaceDistance": (process_ssd, {}),
    "ReferencedWedgeNumber": (process_wedge_position_sequence, {}),
    "WedgePosition": (process_wedge_position_sequence, {}),
    "LeafJawPositions": (assess_near_match, {"tolerance_value": 0.01}),  # 0.01 mm
    "BeamDose": (assess_near_match, {"tolerance_value": 0.01}),  # 0.01 Gy
    "TreatmentMachineName": (process_treatment_machine_name, {}),
    "StudyTime": (assess_tm_match, {}),
    "SpecificCharacterSet": (
        return_expected_mismatch,
        {
            "comment": "Character encoding: ARIA uses Latin Alphabet, RayStation uses Unicode"
        },
    ),
    "BlockData": (process_block_data, {}),
    "BlockNumberOfPoints": (assess_block_points, {}),
    "BlockTrayID": (
        return_expected_mismatch,
        {"comment": "BlockTrayID is set in RayStation by DicomExport.py"},
    ),
    "ReferenceImageNumber": (
        excuse_element_with_parent,
        {"excused_parent": "ReferencedReferenceImageSequence"},
    ),
    "ReferencedSOPClassUID": (
        excuse_element_with_parent,
        {"excused_parent": "ReferencedReferenceImageSequence"},
    ),
    "ReferencedSOPInstanceUID": (
        excuse_element_with_parent,
        {"excused_parent": "ReferencedReferenceImageSequence"},
    ),
    "RTBeamLimitingDeviceType": (
        excuse_element_with_parent,
        {"excused_parent": "BeamLimitingDeviceToleranceSequence"},
    ),
}

PROCESS_FUNCTION_DICT = {
    **PROCESS_FUNCTION_DICT,
    **UNIQUE_TO_RAYSTATION,
    **UNIQUE_TO_ARIA,
}

