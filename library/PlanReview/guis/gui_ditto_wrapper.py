import PySimpleGUI as Sg
import library.DITTO.AriaRTPlanQR as AriaRTPlanQR
import library.DITTO.DicomIntegrityTool as DicomIntegrityTool


def run_dicom_integrity_tool_physics_review(tab_width, tab_height, beamset_name=None, progress_bar=False):
    from PlanReview.guis import display_progress_bar
    if progress_bar:
        progress_window, progress_bar, progress_text = display_progress_bar(
            title_text='Dicom Integrity Tool', progress_bar_text='Running DITTO...')
        steps_performed = 1
        progress_bar.update(current_count=int(steps_performed/100))
        progress_text.update('Checking for DICOM data')
    else:
        progress_window = None
        progress_bar = None
        progress_text = None

    aria_file_location, rs_file_location, selected_rs = AriaRTPlanQR.aria_qr(
        beamset_name=beamset_name)
    if progress_bar:
        steps_performed = 50
        progress_bar.update(current_count=int(steps_performed/100))
        progress_text.update('Aria/RayStation Match found. Comparing...')

    if aria_file_location is None and rs_file_location is None and selected_rs is None:
        if progress_bar:
            steps_performed = 99
            progress_bar.update(current_count=int(steps_performed/100))
            progress_text.update('Dicom Data Unavailable')
            progress_window.close()
        return None, None

    filename1 = rs_file_location
    filename2 = aria_file_location
    file_label1 = "RayStation"
    file_label2 = "Aria"
    dicom_match_tree = DicomIntegrityTool.compare_dicomrt_plans(filename1, filename2)
    if progress_bar:
        steps_performed = 99
        progress_bar.update(current_count=int(steps_performed/100))
        progress_text.update('Dicom Data Comparison Complete')

    treedata = dicom_match_tree.get_treedata()
    c0_width = 30
    c1_width = 25
    c2_width = 35
    n_rows = 32 if tab_width < 800 else 44

    layout = [
        [
            Sg.Frame(
                title=f'DICOM RT Plan Comparison Result: {beamset_name}',
                layout=[
                    [
                        Sg.Tree(
                            data=treedata,
                            headings=['Result', 'Comments', ],
                            auto_size_columns=False,
                            col0_width=c0_width,
                            col_widths=[c1_width, c2_width, ],
                            num_rows=n_rows,
                            key=f'-DITTO_TREE_{beamset_name}',
                            show_expanded=False,
                            enable_events=True,

                        ),
                    ],
                    [
                        Sg.Text(f'{file_label1} Value: '),
                        Sg.Text('Value 1', key=f"-DITTO_TREE_VALUE1_{beamset_name}", size=(100, None)),
                    ],
                    [
                        Sg.Text(f'{file_label2} Value: '),
                        Sg.Text('Value 2', key=f"-DITTO_TREE_VALUE2_{beamset_name}", size=(100, None)),
                    ],
                    [
                        Sg.Text(f'{file_label2} Debug Value: '),
                        Sg.Text('Debug', key=f"-DITTO_TREE_DEBUG_{beamset_name}", size=(100, None)),
                    ],
                ],
                size=(tab_width, tab_height),
            )
        ]
    ]

    if progress_bar:
        steps_performed = 100
        progress_bar.update(current_count=int(steps_performed/100))
        progress_window.close()
    return layout,dicom_match_tree
