import PySimpleGUI as sg
import sys
from pathlib import Path
import logging

ditto_path = Path(__file__).parent.parent / "library" / "DITTO"
sys.path.insert(1, str(ditto_path))
import AriaRTPlanQR
from library.DITTO.DicomIntegrityTool import compare_dicomrt_plans


def run_dicom_integrity_tool_physics_review():
    aria_file_location, rs_file_location, selected_rs = AriaRTPlanQR.aria_qr()
    logging.debug(f"Aria file location: {aria_file_location}")
    logging.debug(f"RayStation file location: {rs_file_location}")

    if aria_file_location is None and rs_file_location is None and selected_rs is None:
        return [
            [sg.Text('No DICOM Files found')],
        ]

    filename1 = rs_file_location
    filename2 = aria_file_location
    file_label1 = "RayStation"
    file_label2 = "Aria"
    dicom_match_tree = compare_dicomrt_plans(filename1, filename2)

    treedata = dicom_match_tree.get_treedata()

    layout = [
        [
            sg.Frame(
                title='DICOM RT Plan Comparison Result',
                layout=[
                    [
                        sg.Tree(
                            data=treedata,
                            headings=['Result', 'Comments', ],
                            auto_size_columns=False,
                            col0_width=50,
                            col_widths=[30, 60, ],
                            num_rows=30,
                            key='-TREE-',
                            show_expanded=False,
                            enable_events=True,
                            # expand_x=True,
                            # expand_y=True,

                        ),
                    ],
                    [
                        sg.Text(f'{file_label1} Value: '),
                        sg.Text('Value 1', key="-VALUE1-", size=(100, None)),
                    ],
                    [
                        sg.Text(f'{file_label2} Value: '),
                        sg.Text('Value 2', key="-VALUE2-", size=(100, None)),
                    ],
                    [
                        sg.Text(f'{file_label2} Debug Value: '),
                        sg.Text('Debug', key="-DEBUG-", size=(100, None)),
                    ],
                ],
            )
        ]
    ]

    return layout
