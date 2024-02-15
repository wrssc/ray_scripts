from copy import deepcopy
from .DicomPairClasses import SequencePair, DicomTreePair, ElementPair
from .DicomPairClasses import Result
from .DicomPairTreeFunctions import create_dicom_tree_pair


def check_plan_names_match(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)
    CHECK_KEYS = ["RTPlanLabel", "RTPlanName"]

    copied_tree.tree_label = "Check Plan Names Match"
    copied_tree.remove_all_items_except(CHECK_KEYS)

    return copied_tree


def check_nominal_plan_dose(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)
    CHECK_KEYS = ["TargetPrescriptionDose"]

    copied_tree.tree_label = "Check Nominal Plan Dose"
    copied_tree.remove_all_items_except(["DoseReferenceSequence"])

    dr_sequence_list = copied_tree.get_element_from_key(
        "DoseReferenceSequence"
    ).sequence_list

    for dr in dr_sequence_list:
        # Prune extra items
        dr.remove_all_items_except(CHECK_KEYS)

    # This test will produce a failing result if the user defines multiple
    # prescriptions in RayStation, which is a feature in version 11B.
    # This code will check to see if there is one matching prescription and
    # zero mismatches. If so, it will assign the warning status.
    if not copied_tree.is_acceptable_match():
        count_match = 0
        count_mismatch = 0
        count_unique_1 = 0
        count_unique_2 = 0

        for dr in dr_sequence_list:
            element = dr.get_element_from_key("TargetPrescriptionDose")
            if element.is_acceptable_match():
                count_match += 1
            elif element.is_unique_to_dataset1():
                count_unique_1 += 1
            elif element.is_unique_to_dataset2():
                count_unique_2 += 1
            else:
                count_mismatch += 1

        summary_comment = (
            f"Matching Rx: {count_match}, "
            f"Unique Rx: {count_unique_1 + count_unique_2}, "
            f"Mismatching Rx: {count_mismatch}"
        )

        copied_tree.comment = summary_comment

        if (
            (count_match > 0)
            and (count_mismatch == 0)
            and (count_unique_1 > 0)
            and (count_unique_2 == 0)
        ):
            for dr in dr_sequence_list:
                element = dr.get_element_from_key("TargetPrescriptionDose")
                if element.is_unique_to_dataset1():
                    element.match_result = Result.ELEMENT_WARNING
                    element.comment = "Prescription is unique to RayStation"
            copied_tree.comment = (
                "There is at least one matching prescription, plus "
                "additional prescriptions that are unique to RayStation. "
            ) + copied_tree.comment
            copied_tree.update_match_result_recursive()

    return copied_tree


def check_number_of_plan_fractions(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)
    CHECK_KEYS = ["NumberOfFractionsPlanned"]

    copied_tree.tree_label = "Check Number of Plan Fractions"
    copied_tree.remove_all_items_except(["FractionGroupSequence"])

    sequence_list = copied_tree.get_element_from_key(
        "FractionGroupSequence"
    ).sequence_list

    for item in sequence_list:
        # Prune extra items
        item.remove_all_items_except(CHECK_KEYS)

    return copied_tree


def check_referenced_planning_image_uids(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)
    CHECK_KEYS = ["FrameOfReferenceUID", "StudyInstanceUID"]

    copied_tree.tree_label = "Check Referenced Planning Image UIDs"
    copied_tree.remove_all_items_except(CHECK_KEYS)

    return copied_tree


def check_structure_set_uids(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)
    CHECK_KEYS = ["ReferencedSOPClassUID", "ReferencedSOPInstanceUID"]

    copied_tree.tree_label = "Check Structure Set UIDs"
    copied_tree.remove_all_items_except(["ReferencedStructureSetSequence"])

    sequence_list = copied_tree.get_element_from_key(
        "ReferencedStructureSetSequence"
    ).sequence_list

    for item in sequence_list:
        # Prune extra items
        item.remove_all_items_except(CHECK_KEYS)

    # Add logic to handle exception
    if not copied_tree.is_acceptable_match():
        condition_1 = (
            sequence_list[0]
            .get_element_from_key("ReferencedSOPClassUID")
            .is_acceptable_match()
        )
        condition_2 = (
            sequence_list[0]
            .get_element_from_key("ReferencedSOPInstanceUID")
            .is_acceptable_match()
        )

        if condition_1 and not condition_2:
            comment = "ReferencedSOPInstanceUID does not match. This usually means the Structure Set was modified in Aria."
            copied_tree.comment = comment
            element = sequence_list[0].get_element_from_key("ReferencedSOPInstanceUID")
            element.match_result = Result.ELEMENT_WARNING
            element.comment = comment
            copied_tree.update_match_result_recursive()

    return copied_tree


def check_beam_parameter(dicom_match_tree, check_keys, check_label):
    copied_tree = deepcopy(dicom_match_tree)

    copied_tree.tree_label = check_label
    copied_tree.remove_all_items_except("BeamSequence")

    # Beam are isolated. Eliminate setup fields.
    beam_sequence_list = copied_tree.get_element_from_key("BeamSequence").sequence_list

    # Delete setup fields
    list_of_beams_to_delete = []
    for beam in beam_sequence_list:
        vp = beam.get_element_from_key("TreatmentDeliveryType").value_pair

        if (vp[0] != "TREATMENT") and (vp[1] != "TREATMENT"):
            list_of_beams_to_delete.append(beam)

    for beam in list_of_beams_to_delete:
        beam_sequence_list.remove(beam)

    # Prune items not in check keys
    for beam in beam_sequence_list:
        # Prune extra items
        beam.remove_all_items_except(check_keys)

    return copied_tree


def check_control_point_parameter(dicom_match_tree, check_keys, check_label):
    copied_tree = deepcopy(dicom_match_tree)

    copied_tree.tree_label = check_label
    copied_tree.remove_all_items_except("BeamSequence")

    # Beam are isolated. Eliminate setup fields.
    beam_sequence_list = copied_tree.get_element_from_key("BeamSequence").sequence_list

    # Delete setup fields
    list_of_beams_to_delete = []
    for beam in beam_sequence_list:
        vp = beam.get_element_from_key("TreatmentDeliveryType").value_pair

        if vp[1] != "TREATMENT":
            list_of_beams_to_delete.append(beam)

    for beam in list_of_beams_to_delete:
        beam_sequence_list.remove(beam)

    # Cycle though control points
    for beam in beam_sequence_list:
        # Prune all but ControlPointSequence
        beam.remove_all_items_except("ControlPointSequence")
        control_point_sequence_list = beam.get_element_from_key(
            "ControlPointSequence"
        ).sequence_list

        for cp in control_point_sequence_list:
            cp.remove_all_items_except(check_keys)

    return copied_tree


def check_dose_rate(dicom_match_tree):
    # Determine the three-letter designation in the middle of the plan
    plan_name_element = dicom_match_tree.get_element_from_key("RTPlanName")

    plan_type = "UNKNOWN"
    if plan_name_element.is_acceptable_match():
        plan_name = plan_name_element.value_pair[0]
        plan_name_parts = plan_name.split("_")
        if (len(plan_name_parts) == 3) and (len(plan_name_parts[1]) == 3):
            plan_type = plan_name_parts[1].upper()

    copied_tree = deepcopy(dicom_match_tree)

    copied_tree.tree_label = "Check Dose Rate"
    copied_tree.remove_all_items_except("BeamSequence")

    # Beam are isolated. Eliminate setup fields.
    beam_sequence_list = copied_tree.get_element_from_key("BeamSequence").sequence_list

    # Delete setup fields
    list_of_beams_to_delete = []
    for beam in beam_sequence_list:
        vp = beam.get_element_from_key("TreatmentDeliveryType").value_pair

        if vp[1] != "TREATMENT":
            list_of_beams_to_delete.append(beam)

    for beam in list_of_beams_to_delete:
        beam_sequence_list.remove(beam)

    # Determine the radiation type for this plan
    list_of_radiation_types = []
    for beam in beam_sequence_list:
        element = beam.get_element_from_key("RadiationType")
        list_of_radiation_types.append(element.value_pair[0])
        list_of_radiation_types.append(element.value_pair[1])

    radiation_type = "UNKNOWN"
    if all(rad_type == "ELECTRON" for rad_type in list_of_radiation_types):
        radiation_type = "ELECTRON"
    if all(rad_type == "PHOTON" for rad_type in list_of_radiation_types):
        radiation_type = "PHOTON"

    # Cycle though control points (collecting dose rates along the way)
    list_of_aria_dose_rates = []
    for beam in beam_sequence_list:
        # Prune all but ControlPointSequence
        beam.remove_all_items_except("ControlPointSequence")
        control_point_sequence_list = beam.get_element_from_key(
            "ControlPointSequence"
        ).sequence_list

        for cp in control_point_sequence_list:
            cp.remove_all_items_except("DoseRateSet")
            try:
                element = cp.get_element_from_key("DoseRateSet")
                list_of_aria_dose_rates.append(element.value_pair[1])
            except:
                pass

    copied_tree.prune_empty_trees_and_sequences()
    copied_tree.update_match_result_recursive()

    if not copied_tree.is_acceptable_match():
        # CASE 1: Plan is electrons and all dose rates are 1000 MU/min
        if (radiation_type == "ELECTRON") and all(
            rate == 1000 for rate in list_of_aria_dose_rates
        ):
            beam_sequence_list = copied_tree.get_element_from_key(
                "BeamSequence"
            ).sequence_list
            for beam in beam_sequence_list:
                control_point_sequence_list = beam.get_element_from_key(
                    "ControlPointSequence"
                ).sequence_list
                for cp in control_point_sequence_list:
                    element = cp.get_element_from_key("DoseRateSet")
                    element.match_result = Result.ELEMENT_WARNING
                    element.comment = "Aria Dose Rate = 1000 MU/min, and the plan is Electron Radiotherapy"
            copied_tree.comment = (
                "Aria Dose Rate = 1000 MU/min, and the plan is Electron Radiotherapy"
            )

        # CASE 2: Plan is PRD and all dose rates are 1000 MU/min
        if (plan_type == "PRD") and all(
            rate == 100 for rate in list_of_aria_dose_rates
        ):
            beam_sequence_list = copied_tree.get_element_from_key(
                "BeamSequence"
            ).sequence_list
            for beam in beam_sequence_list:
                control_point_sequence_list = beam.get_element_from_key(
                    "ControlPointSequence"
                ).sequence_list
                for cp in control_point_sequence_list:
                    element = cp.get_element_from_key("DoseRateSet")
                    element.match_result = Result.ELEMENT_WARNING
                    element.comment = (
                        "Aria Dose Rate = 100 MU/min, and the plan is PRDR"
                    )
            copied_tree.comment = "Aria Dose Rate = 100 MU/min, and the plan is PRDR"

    return copied_tree


def check_mu(dicom_match_tree):
    copied_tree = deepcopy(dicom_match_tree)

    # Get list of beams that are treatment fields:
    beam_sequence_list = copied_tree.get_element_from_key("BeamSequence").sequence_list

    list_of_treatment_beams = []
    for beam in beam_sequence_list:
        vp = beam.get_element_from_key("TreatmentDeliveryType").value_pair

        if vp[0] == "TREATMENT":
            list_of_treatment_beams.append(
                beam.get_element_from_key("BeamNumber").value_pair[0]
            )

        if vp[1] == "TREATMENT":
            list_of_treatment_beams.append(
                beam.get_element_from_key("BeamNumber").value_pair[1]
            )

    # Eliminate duplicates
    list_of_treatment_beams = list(set(list_of_treatment_beams))

    CHECK_KEYS = ["BeamMeterset"]

    copied_tree.tree_label = "Check Beam MU"
    copied_tree.remove_all_items_except("FractionGroupSequence")

    fg_sequence_list = copied_tree.get_element_from_key(
        "FractionGroupSequence"
    ).sequence_list

    # Delete setup fields
    for fg in fg_sequence_list:
        # Prune extra items
        fg.remove_all_items_except(["ReferencedBeamSequence"])
        beam_sequence_list = fg.get_element_from_key(
            "ReferencedBeamSequence"
        ).sequence_list

        list_of_beams_to_delete = []
        for beam in beam_sequence_list:
            vp = beam.get_element_from_key("ReferencedBeamNumber").value_pair
            if (vp[0] not in list_of_treatment_beams) and (
                vp[1] not in list_of_treatment_beams
            ):
                list_of_beams_to_delete.append(beam)

        for beam in list_of_beams_to_delete:
            beam_sequence_list.remove(beam)

        for beam in beam_sequence_list:
            beam.remove_all_items_except(CHECK_KEYS)

    return copied_tree


def check_electron_cutout_code(dicom_match_tree):
    """Verifies the electron cutout codes match between RayStation and Aria"""

    copied_tree = deepcopy(dicom_match_tree)

    copied_tree.tree_label = "Check Electron Cutout Code"
    copied_tree.remove_all_items_except("BeamSequence")

    # Beam are isolated. Eliminate setup fields.
    beam_sequence_list = copied_tree.get_element_from_key("BeamSequence").sequence_list

    # Delete setup fields
    list_of_beams_to_delete = []
    for beam in beam_sequence_list:
        vp = beam.get_element_from_key("TreatmentDeliveryType").value_pair

        if vp[1] != "TREATMENT":
            list_of_beams_to_delete.append(beam)

    for beam in list_of_beams_to_delete:
        beam_sequence_list.remove(beam)

    # Cycle though all beams again and isolate block sequence elements
    for beam in beam_sequence_list:
        # Prune all but BlockSequence
        beam.remove_all_items_except("BlockSequence")
        if len(beam.tree_list) > 0:
            block_sequence_list = beam.get_element_from_key(
                "BlockSequence"
            ).sequence_list

            for bs in block_sequence_list:
                bs.remove_all_items_except(["BlockName", "AccessoryCode"])

                value1 = bs.get_element_from_key("BlockName").value_pair[0]
                value2 = bs.get_element_from_key("AccessoryCode").value_pair[1]
                comment = "This is a synthesized data element in which the RayStation value is the DICOM Block Name and the Aria value is the DICOM Accessory Code"
                bs.tree_list.append(
                    ElementPair(
                        parent=bs,
                        attribute_name="Electron Block Code",
                        value_pair=[value1, value2],
                        comment=comment,
                        depth=bs.depth + 1,
                        process_func=None,
                        process_func_kwargs=None,
                        parent_key=bs.return_global_key,
                    )
                )
                bs.remove_all_items_except(["Electron Block Code"])

    return copied_tree


def run_aria_plan_transfer_checks(ds1, ds2):
    aptr_dicom_tree_pair = DicomTreePair(
        parent=None,
        tree_list=[],
        depth=0,
        parent_key="",
        tree_label="",
    )

    aptr_sequence_pair = SequencePair(
        parent=aptr_dicom_tree_pair,
        attribute_name="Aria Plan Transfer Review",
        sequence_list=[],
        comment="",
        depth=1,
        parent_key="",
    )

    aptr_dicom_tree_pair.tree_list = [aptr_sequence_pair]

    sequence_list = []

    dicom_match_tree = create_dicom_tree_pair(
        ds1=ds1,
        ds2=ds2,
        parent=aptr_sequence_pair,
        depth=2,
        parent_key=f">{aptr_sequence_pair.attribute_name}",
    )

    # Overall Plan
    sequence_list.append(check_plan_names_match(dicom_match_tree))
    sequence_list.append(check_nominal_plan_dose(dicom_match_tree))
    sequence_list.append(check_mu(dicom_match_tree))
    sequence_list.append(check_number_of_plan_fractions(dicom_match_tree))
    sequence_list.append(check_referenced_planning_image_uids(dicom_match_tree))
    sequence_list.append(check_structure_set_uids(dicom_match_tree))

    # Each Treatment Beam
    zipped_parameters = zip(
        [
            ["BeamName", "BeamNumber"],
            ["TreatmentMachineName"],
            ["NumberOfWedges", "WedgeSequence"],
            ["NumberOfControlPoints"],
            ["NumberOfBoli"],
            ["ReferencedBolusSequence"],
            ["ApplicatorSequence"],
            ["BlockSequence"],
        ],
        [
            "Check Beam Names",
            "Check Treatment Machine",
            "Check Wedge Beam Parameters",
            "Check Number of Control Points",
            "Check Number of Boli",
            "Check Bolus Referenced ROI Number",
            "Check Electron Applicator",
            "Check Electron Block",
        ],
    )

    for check_keys, check_label in zipped_parameters:
        sequence_list.append(
            check_beam_parameter(
                dicom_match_tree,
                check_keys=check_keys,
                check_label=check_label,
            )
        )

    # One last beam check
    sequence_list.append(check_electron_cutout_code(dicom_match_tree))

    # Each Control Point
    zipped_parameters = zip(
        [
            ["GantryAngle"],
            ["GantryRotationDirection"],
            ["BeamLimitingDeviceAngle"],
            ["PatientSupportAngle"],
            ["IsocenterPosition"],
            ["NominalBeamEnergy"],
            ["BeamLimitingDevicePositionSequence"],
            ["WedgePositionSequence"],
            ["CumulativeMetersetWeight"],
            ["SourceToSurfaceDistance"],
        ],
        [
            "Check Gantry Angles",
            "Check Gantry Rotation Direction",
            "Check Collimator Angles",
            "Check Table Angles",
            "Check Isocenter Position",
            "Check Beam Energy",
            "Check Jaws and MLCs",
            "Check Wedge Control Point Parameters",
            "Check Relative Meterset Weight for Each Control Point",
            "Check SSDs",
        ],
    )

    for check_keys, check_label in zipped_parameters:
        sequence_list.append(
            check_control_point_parameter(
                dicom_match_tree,
                check_keys=check_keys,
                check_label=check_label,
            )
        )

    # One last control point check
    sequence_list.append(check_dose_rate(dicom_match_tree))

    # Update sequence and check matching
    aptr_sequence_pair.sequence_list = sequence_list
    aptr_dicom_tree_pair.prune_empty_trees_and_sequences()
    aptr_dicom_tree_pair.update_match_result_recursive()

    return aptr_dicom_tree_pair
