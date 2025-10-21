import json
import datetime
from pathlib import Path
import pydicom

try:
    import FreeSimpleGUI as sg
except ImportError:
    import PySimpleGUI as sg
from DicomPairTreeFunctions import compare_dicomrt_plans
from AriaPlanTransferReviewChecks import run_aria_plan_transfer_checks


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
    filepath1,
    filepath2,
    file_label1="DICOM File 1",
    file_label2="DICOM File 2",
    diagnostic=False,
):
    import logging

    logging.debug(f"Running DIT for {filepath1} and {filepath2}")
    logging.debug(f"File labels: {file_label1} and {file_label2}")

    ds1 = pydicom.dcmread(filepath1, force=True)
    ds2 = pydicom.dcmread(filepath2, force=True)

    aptr_dicom_tree_pair = run_aria_plan_transfer_checks(ds1, ds2)

    aptr_treedata = aptr_dicom_tree_pair.get_treedata(show_matches=True)

    tab1_layout = [
        [
            sg.Tree(
                data=aptr_treedata,
                headings=[
                    "Result",
                    "Comments",
                ],
                auto_size_columns=False,
                col0_width=50,
                col_widths=[
                    30,
                    60,
                ],
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
    plan_names = dmt_dicom_match_tree.get_element_from_key("RTPlanLabel").value_pair
    if plan_names[0] == plan_names[1]:
        tab_title = plan_names[0]
    else:
        tab_title = f"RS: {plan_names[0]} vs. Aria: {plan_names[1]}"

    if diagnostic:

        dmt_dicom_match_tree = compare_dicomrt_plans(filepath1, filepath2)
        dmt_treedata = dmt_dicom_match_tree.get_treedata(show_matches=True)

        tab_diagnostic = [
            [
                sg.Tree(
                    data=dmt_treedata,
                    headings=[
                        "Result",
                        "Comments",
                    ],
                    auto_size_columns=False,
                    col0_width=50,
                    col_widths=[
                        30,
                        60,
                    ],
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

    if diagnostic:
        tabs = [sg.Tab(tab_title, tab1_layout), sg.Tab("Diagnostics", tab_diagnostic)]
    else:
        tabs = [
            sg.Tab(tab_title, tab1_layout),
        ]

    layout = [
        [
            sg.TabGroup(
                [tabs],
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

        if diagnostic:
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
                "RTPlanLabel"
            ).value_pair[0]
            report_failing_test_func(aptr_dicom_tree_pair, mrn=mrn, plan_name=plan_name)

    window.close()


if __name__ == "__main__":

    file_path = Path(
        r"U:\UWHealth\RadOnc\ShareAll\Users\DJacqmin\Clinical\DITTO\2024A Test Cases\BreL_BST_R0A0\2928874"
    )

    raystation_filename = r"RP Corrected.dcm"
    aria_filename = r"RP.2928874.BreL_BST_R0A0.dcm"

    file_path = Path(
        r"U:\UWHealth\RadOnc\ShareAll\Users\DJacqmin\Clinical\DITTO\2024A Test Cases\Shoulder"
    )

    raystation_filename = r"RP1.2.752.243.1.1.20250424174442129.4700.77820.dcm"
    aria_filename = r"RP.TPL_1310.ShoL_3DC_R0A0.dcm"

    run_dicom_integrity_tool(
        file_path / raystation_filename, file_path / aria_filename, diagnostic=True
    )
