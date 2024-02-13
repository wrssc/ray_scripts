import json
import datetime
from pathlib import Path
import pydicom
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
):
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
        tab_title = f'RS: {plan_names[0]} vs. Aria: {plan_names[1]}'

    layout = [
        [
            sg.TabGroup(
                [
                    [
                        sg.Tab(tab_title, tab1_layout),
                    ]
                ],
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

        if event == "Report Failing Test":
            mrn = dmt_dicom_match_tree.get_element_from_key("PatientID").value_pair[0]
            plan_name = dmt_dicom_match_tree.get_element_from_key(
                "RTPlanLabel"
            ).value_pair[0]
            report_failing_test_func(aptr_dicom_tree_pair, mrn=mrn, plan_name=plan_name)

    window.close()
