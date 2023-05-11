from pathlib import Path
from xml.dom.minidom import Element
import pydicom
import PySimpleGUI as sg
from DicomPairClasses import ElementPair, SequencePair, DicomTreePair, Result
from ProcessingFunctions import PROCESS_FUNCTION_DICT
from copy import deepcopy
import json
import datetime

ATTRIBUTE_MATCH_DICT = {
    "BeamSequence": "BeamNumber",
    "BeamLimitingDeviceSequence": "RTBeamLimitingDeviceType",
    "ControlPointSequence": "ControlPointIndex",
    "BeamLimitingDevicePositionSequence": "RTBeamLimitingDeviceType",
    "ReferencedDoseReferenceSequence": "ReferencedDoseReferenceNumber",
    "PrimaryFluenceModeSequence": "FluenceMode",
    "ReferencedBolusSequence": "ReferencedROINumber",
    "DoseReferenceSequence": "DoseReferenceNumber",
    "FractionGroupSequence": "FractionGroupNumber",
    "ReferencedBeamSequence": "ReferencedBeamNumber",
    "PatientSetupSequence": "PatientSetupNumber",
    "ReferencedStructureSetSequence": "ReferencedSOPClassUID",  # ClassID??
    "ToleranceTableSequence": "ToleranceTableNumber",
    "BeamLimitingDeviceToleranceSequence": "RTBeamLimitingDeviceType",
    "BlockSequence": "BlockNumber",
    "ApplicatorSequence": "ApplicatorType",
    "ApplicatorGeometrySequence": "ApplicatorOpening",
    "ReferencedReferenceImageSequence": "ReferenceImageNumber",
    "WedgeSequence": "WedgeNumber",
    "WedgePositionSequence": "ReferencedWedgeNumber",  # contrived,
    "PlannedVerificationImageSequence": "XRayImageReceptorAngle",  # contrived, one of a kind
}
# Need to add Applicator Sequence, Block Sequence, ReferencedReferenceImageSequence, PlannedVerificationImageSequence


def create_dicom_tree_pair(ds1, ds2, parent, depth=0, parent_key="", tree_label=""):

    dicom_tree_pair = DicomTreePair(
        parent=parent,
        tree_list=[],
        depth=depth,
        parent_key=parent_key,
        tree_label=tree_label,
    )

    tree_list = []

    if parent_key == "":
        childs_parent_key = ""
    else:
        childs_parent_key = f"{parent_key}>{tree_label}"

    # Loop over all keywords in the first DICOM file
    for ds1_keyword in ds1.dir():

        if ds1_keyword in PROCESS_FUNCTION_DICT:
            process_func, kwargs = PROCESS_FUNCTION_DICT[ds1_keyword]
        else:
            process_func, kwargs = None, None

        # CASE 1: The item is not a Sequence
        if ds1[ds1_keyword].VR != "SQ":

            if ds1_keyword not in ds2.dir():
                value_pair = (ds1[ds1_keyword].value, None)
            else:
                value_pair = (ds1[ds1_keyword].value, ds2[ds1_keyword].value)

            tree_list.append(
                ElementPair(
                    parent=dicom_tree_pair,
                    attribute_name=ds1_keyword,
                    value_pair=value_pair,
                    comment="",
                    depth=depth + 1,
                    process_func=process_func,
                    process_func_kwargs=kwargs,
                    parent_key=childs_parent_key,
                )
            )

            continue

        # CASE 2: The item is a sequence

        # CASE 2a: Sequence ds1_keyword is not in our match sequence dictionary
        # In order to match items in a sequences, we must know which data element
        # to use for matching. Check ATTRIBUTE_MATCH_DICT to see if one is specified.
        # If not, skip it.
        if ds1_keyword not in ATTRIBUTE_MATCH_DICT.keys():

            tree_list.append(
                SequencePair(
                    parent=dicom_tree_pair,
                    attribute_name=ds1_keyword,
                    sequence_list=[],
                    comment=(
                        "Sequence was skipped because the attribute "
                        "was not found in ATTRIBUTE_MATCH_DICT"
                    ),
                    depth=depth + 1,
                    parent_key=childs_parent_key,
                )
            )

            continue

        # CASE 2b: Sequence ds1_keyword is unique to dataset 1
        # If a sequence is unique to one dataset, we could choose to do one of two thing:
        # 1. Stop searching, and simply document the finding
        # 2. Enter the sequence and declare everything below to be unique as well
        # We will do the latter, as the details of the unique item may be of importance
        # and we want to preserve that information for analysis.
        match_keyword = ATTRIBUTE_MATCH_DICT[ds1_keyword]
        if ds1_keyword not in ds2.dir():

            sequence_pair = SequencePair(
                parent=dicom_tree_pair,
                attribute_name=ds1_keyword,
                sequence_list=[],
                comment="Sequence is unique to the first dataset.",
                depth=depth + 1,
                parent_key=childs_parent_key,
            )

            sequence_list = []
            for item1 in ds1[ds1_keyword]:

                label = f"{match_keyword}={item1[match_keyword].value}"

                sequence_list.append(
                    create_dicom_tree_pair(
                        item1,
                        pydicom.Dataset(),
                        parent=sequence_pair,
                        depth=depth + 2,
                        parent_key=f"{childs_parent_key}>{ds1_keyword}",
                        tree_label=label,
                    )
                )

            sequence_pair.sequence_list = sequence_list
            sequence_pair.update_match_result()

            tree_list.append(sequence_pair)
            continue

        # CASE 2c: Sequence ds1_keyword has a match in ds2

        # Loop over items in the sequence, matching one at a time
        # If a match is found, we will recursively send it into create_dicom_pair_dictionary()
        match_keyword = ATTRIBUTE_MATCH_DICT[ds1_keyword]

        sequence_pair = SequencePair(
            parent=dicom_tree_pair,
            attribute_name=ds1_keyword,
            sequence_list=[],
            comment="",
            depth=depth + 1,
            parent_key=childs_parent_key,
        )

        sequence_list = []
        # This is the slowest way to find matches, but it works.
        # O(N) = N^2. Could probably get O(N) = 2N.
        for item1 in ds1[ds1_keyword]:
            found = False
            label = f"{match_keyword}={item1[match_keyword].value}"
            for item2 in ds2[ds1_keyword]:
                if item1[match_keyword].value == item2[match_keyword].value:
                    # We found a match. Send each element tree into comparison
                    found = True
                    sequence_list.append(
                        create_dicom_tree_pair(
                            ds1=item1,
                            ds2=item2,
                            parent=sequence_pair,
                            depth=depth + 2,
                            parent_key=f"{childs_parent_key}>{ds1_keyword}",
                            tree_label=label,
                        )
                    )

            if not found:
                # If we don't find a match, then this sequence item is unique
                # We will pair it with blank dataset, which will result in
                # all child elements being declared unique.
                sequence_list.append(
                    create_dicom_tree_pair(
                        ds1=item1,
                        ds2=pydicom.Dataset(),
                        parent=sequence_pair,
                        depth=depth + 2,
                        parent_key=f"{childs_parent_key}>{ds1_keyword}",
                        tree_label=label,
                    )
                )

        # Repeat with ds2 as the search focus, to find unique items in ds2
        for item2 in ds2[ds1_keyword]:
            found = False
            label = f"{match_keyword}={item2[match_keyword].value}"
            for item1 in ds1[ds1_keyword]:
                if item1[match_keyword].value == item2[match_keyword].value:
                    # We found a match.
                    found = True

            if not found:
                # Unique to dataset 2
                sequence_list.append(
                    create_dicom_tree_pair(
                        ds1=pydicom.Dataset(),
                        ds2=item2,
                        parent=sequence_pair,
                        depth=depth + 2,
                        parent_key=f"{childs_parent_key}>{ds1_keyword}",
                        tree_label=label,
                    )
                )

        sequence_pair.sequence_list = sequence_list
        sequence_pair.update_match_result()

        tree_list.append(sequence_pair)

    # Loop over all keywords in the second DICOM file to capture items unique to dataset 2
    for ds2_keyword in ds2.dir():
        if ds2_keyword in PROCESS_FUNCTION_DICT:
            process_func, kwargs = PROCESS_FUNCTION_DICT[ds2_keyword]
        else:
            process_func, kwargs = None, None

        if ds2[ds2_keyword].VR != "SQ":

            # Address Unique attributes in ds2
            if ds2_keyword not in ds1.dir():
                value_pair = (None, ds2[ds2_keyword].value)

                tree_list.append(
                    ElementPair(
                        parent=dicom_tree_pair,
                        attribute_name=ds2_keyword,
                        value_pair=value_pair,
                        comment="",
                        depth=depth + 1,
                        process_func=process_func,
                        process_func_kwargs=kwargs,
                        parent_key=childs_parent_key,
                    )
                )

            continue

        # CASE 2a: Sequence ds2_keyword is not in our match sequence dictionary
        if (ds2_keyword not in ATTRIBUTE_MATCH_DICT.keys()) and (
            ds2_keyword not in ds1.dir()
        ):

            sequence_pair = SequencePair(
                parent=dicom_tree_pair,
                attribute_name=ds2_keyword,
                sequence_list=[],
                comment=(
                    "Sequence was skipped because the attribute "
                    "was not found in ATTRIBUTE_MATCH_DICT"
                ),
                depth=depth + 1,
                parent_key=childs_parent_key,
            )

            tree_list.append(sequence_pair)

            continue

        # CASE 2b: Sequence ds2_keyword is unique to dataset 2

        if ds2_keyword not in ds1.dir():
            match_keyword = ATTRIBUTE_MATCH_DICT[ds2_keyword]

            sequence_pair = SequencePair(
                parent=dicom_tree_pair,
                attribute_name=ds2_keyword,
                sequence_list=[],
                comment="Sequence is unique to the second dataset.",
                depth=depth + 1,
                parent_key=childs_parent_key,
            )
            sequence_list = []

            for item2 in ds2[ds2_keyword]:

                label = f"{match_keyword}={item2[match_keyword].value}"

                sequence_list.append(
                    create_dicom_tree_pair(
                        ds1=pydicom.Dataset(),
                        ds2=item2,
                        parent=sequence_pair,
                        depth=depth + 2,
                        parent_key=f"{childs_parent_key}>{ds2_keyword}",
                        tree_label=label,
                    )
                )

            sequence_pair.sequence_list = sequence_list
            sequence_pair.update_match_result()

            tree_list.append(sequence_pair)
            continue

    # Update Tree
    dicom_tree_pair.tree_list = tree_list
    dicom_tree_pair.update_match_result()

    return dicom_tree_pair


def compare_dicomrt_plans(filepath1, filepath2):
    """ Compares two DICOM-RT Plan files

    PARAMETERS
    ----------
    filepath1: Path or string
        The path and filename to the first DICOM-RT plan file
    filepath2: Path or string
        The path and filename to the second DICOM-RT plan filepip
    """

    ds1 = pydicom.dcmread(filepath1, force=True)
    ds2 = pydicom.dcmread(filepath2, force=True)

    dicom_pair_tree = create_dicom_tree_pair(ds1=ds1, ds2=ds2, parent=None)

    # print_pair_tree_results(dicom_pair_tree)

    return dicom_pair_tree


def report_failing_test_func(aptr_dicom_tree_pair, mrn="0000000", plan_name="Plan"):

    failing_results = []
    list_of_checks = aptr_dicom_tree_pair.get_element_from_key(
        "Aria Plan Transfer Review"
    ).sequence_list
    for check in list_of_checks:
        if not check.is_acceptable_match():
            failing_results.append(check.tree_label)

    failing_results_string = "\n".join(failing_results)
    layout = [
        [sg.Text(f"Failing Tests: {failing_results_string}")],
        [sg.Text("Please add additional clinical context in the box below.")],
        [sg.Multiline(s=(45, 3), key="-MULTILINE-")],
        [sg.Button("Report")],
    ]

    window = sg.Window("Report Failing Test", layout)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Exit":
            break

        if event == "Report":
            report_dict = {
                "id": mrn,
                "plan name": plan_name,
                "failing results": failing_results,
                "context": values["-MULTILINE-"],
            }
            json_object = json.dumps(report_dict, indent=4)

            root = Path(
                r"U:\UWHealth\RadOnc\ShareAll\Users\DJacqmin\RayStation\DITTO_logs"
            )
            filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{mrn}_{plan_name}.json"
            with open(root / filename, "w") as file:
                file.write(json_object)
            break

    window.close()


def run_dicom_integrity_tool(
    filepath1, filepath2, file_label1="DICOM File 1", file_label2="DICOM File 2",
):

    ds1 = pydicom.dcmread(filepath1, force=True)
    ds2 = pydicom.dcmread(filepath2, force=True)

    # Start APTR
    aptr_dicom_tree_pair = DicomTreePair(
        parent=None, tree_list=[], depth=0, parent_key="", tree_label="",
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

            comment = (
                f"Matching Rx: {count_match}, "
                f"Unique Rx: {count_unique_1 + count_unique_2}, "
                f"Mismatching Rx: {count_mismatch}"
            )

            copied_tree.comment = comment

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
                element = sequence_list[0].get_element_from_key(
                    "ReferencedSOPInstanceUID"
                )
                element.match_result = Result.ELEMENT_WARNING
                element.comment = comment
                copied_tree.update_match_result_recursive()

        return copied_tree

    def check_beam_parameter(dicom_match_tree, check_keys, check_label):

        copied_tree = deepcopy(dicom_match_tree)

        copied_tree.tree_label = check_label
        copied_tree.remove_all_items_except("BeamSequence")

        # Beam are isolated. Eliminate setup fields.
        beam_sequence_list = copied_tree.get_element_from_key(
            "BeamSequence"
        ).sequence_list

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
        beam_sequence_list = copied_tree.get_element_from_key(
            "BeamSequence"
        ).sequence_list

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

    def check_mu(dicom_match_tree):

        copied_tree = deepcopy(dicom_match_tree)

        # Get list of beams that are treatment fields:
        beam_sequence_list = copied_tree.get_element_from_key(
            "BeamSequence"
        ).sequence_list

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

    # Run Tests
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
            "Check Bolus Name and Referenced ROI Number",
            "Check Electron Applicator",
            "Check Electron Block",
        ],
    )

    for check_keys, check_label in zipped_parameters:
        sequence_list.append(
            check_beam_parameter(
                dicom_match_tree, check_keys=check_keys, check_label=check_label,
            )
        )

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
            ["DoseRateSet"],
            ["CumulativeMetersetWeight"],
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
            "Check Dose Rate",
            "Check Relative Meterset Weight for each Control Point",
        ],
    )

    for check_keys, check_label in zipped_parameters:
        sequence_list.append(
            check_control_point_parameter(
                dicom_match_tree, check_keys=check_keys, check_label=check_label,
            )
        )

    # Update sequence and check matching
    aptr_sequence_pair.sequence_list = sequence_list
    aptr_dicom_tree_pair.prune_empty_trees_and_sequences()
    aptr_dicom_tree_pair.update_match_result_recursive()

    aptr_treedata = aptr_dicom_tree_pair.get_treedata(show_matches=True)

    tab1_layout = [
        [
            sg.Tree(
                data=aptr_treedata,
                headings=["Result", "Comments",],
                auto_size_columns=False,
                col0_width=50,
                col_widths=[30, 60,],
                num_rows=30,
                key="-APTR_TREE-",
                show_expanded=False,
                enable_events=True,
                # expand_x=True,
                # expand_y=True,
            ),
            # sg.Checkbox(
            #   "Show matches", default=True, enable_events=True, key="-MATCHES-"
            # ),
        ],
        [
            sg.Text(f"{file_label1} Value: "),
            sg.Text("Value 1", key="-APTR_VALUE1-", size=(100, None)),
        ],
        [
            sg.Text(f"{file_label2} Value: "),
            sg.Text("Value 2", key="-APTR_VALUE2-", size=(100, None)),
        ],
        [
            sg.Text(f"{file_label2} Comment: "),
            sg.Text("Comment", key="-APTR_COMMENT-", size=(100, None)),
        ],
    ]

    dmt_dicom_match_tree = compare_dicomrt_plans(filepath1, filepath2)
    dmt_treedata = dmt_dicom_match_tree.get_treedata(show_matches=True)

    tab2_layout = [
        [
            sg.Tree(
                data=dmt_treedata,
                headings=["Result", "Comments",],
                auto_size_columns=False,
                col0_width=50,
                col_widths=[30, 60,],
                num_rows=30,
                key="-DMT_TREE-",
                show_expanded=False,
                enable_events=True,
                # expand_x=True,
                # expand_y=True,
            ),
        ],
        [
            sg.Text(f"{file_label1} Value: "),
            sg.Text("Value 1", key="-DMT_VALUE1-", size=(100, None)),
        ],
        [
            sg.Text(f"{file_label2} Value: "),
            sg.Text("Value 2", key="-DMT_VALUE2-", size=(100, None)),
        ],
        [
            sg.Text(f"{file_label2} Debug Value: "),
            sg.Text("Debug", key="-DMT_DEBUG-", size=(100, None)),
        ],
    ]

    layout = [
        [
            sg.TabGroup(
                [
                    [
                        sg.Tab("Aria Plan Transfer Review", tab1_layout, tooltip="tip"),
                        sg.Tab("DICOM Comparison Tree", tab2_layout),
                    ]
                ],
                tooltip="TIP2",
            )
        ],
        [sg.Button("Report Failing Test")],
    ]

    window = sg.Window("Dicom Integrity Tool", layout, resizable=True)

    while True:  # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break

        if event in "-APTR_TREE-":

            tree_key = values["-APTR_TREE-"][0]

            if ">" in tree_key:

                value1, value2 = aptr_dicom_tree_pair.get_valuepair_from_key(
                    tree_key[1:]
                )
                element = aptr_dicom_tree_pair.get_element_from_key(tree_key[1:])

                if value1 is None:
                    value1 = ""

                if value2 is None:
                    value2 = ""

                if element.parent is None:
                    name = ""
                else:
                    name = element.parent.get_name()

                window["-APTR_VALUE1-"].update(value1)
                window["-APTR_VALUE2-"].update(value2)
                window["-APTR_COMMENT-"].update(element.comment)

        if event in "-DMT_TREE-":

            tree_key = values["-DMT_TREE-"][0]

            if ">" in tree_key:

                value1, value2 = dmt_dicom_match_tree.get_valuepair_from_key(
                    tree_key[1:]
                )
                element = dmt_dicom_match_tree.get_element_from_key(tree_key[1:])

                if value1 is None:
                    value1 = ""

                if value2 is None:
                    value2 = ""

                if element.parent is None:
                    name = ""
                else:
                    name = element.parent.get_name()

                window["-DMT_VALUE1-"].update(value1)
                window["-DMT_VALUE2-"].update(value2)

            window["-DMT_DEBUG-"].update(tree_key)

        if event == "Report Failing Test":
            mrn = dmt_dicom_match_tree.get_element_from_key("PatientID").value_pair[0]
            plan_name = dmt_dicom_match_tree.get_element_from_key(
                "RTPlanName"
            ).value_pair[0]
            report_failing_test_func(aptr_dicom_tree_pair, mrn=mrn, plan_name=plan_name)

    window.close()


if __name__ == "__main__":

    # VMAT w/ and w/o bolus plans
    file_path = Path(
        r"U:\UWHealth\RadOnc\ShareAll\Users\ZEL\DICOM_Compare_Files\3164588"
    )
    # raystation_filename = r"RP1.2.752.243.1.1.20220110105336812.2000.10016.dcm"
    # aria_filename = r"Bol_ARIA1.2.246.352.71.5.137378053967.332155.20220111111326.dcm"
    # aria_filename = r"NoB_ARIA1.2.246.352.71.5.137378053967.332249.20220111111326.dcm"

    # EDW Plan
    file_path = Path(
        r"U:\UWHealth\RadOnc\ShareAll\Users\DJacqmin\RayStation\DICOMs\Plan_EDW"
    )
    """
    raystation_filename = r"RP1.2.752.243.1.1.20220628154229160.2400.53002.dcm"
    aria_filename = r"RP.3596693.ArmL_2DC_R0A0.dcm"
    """

    # Prostate Plan
    file_path = Path(
        r"U:\UWHealth\RadOnc\ShareAll\Users\DJacqmin\RayStation\DICOMs\Plan_Prostate"
    )

    raystation_filename = r"RP1.2.752.243.1.1.20230321151237111.2000.28646.dcm"
    aria_filename = r"RP.0783795.Pros_SBR_R1A0.dcm"

    run_dicom_integrity_tool(file_path / raystation_filename, file_path / aria_filename)
