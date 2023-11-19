import PySimpleGUI as Sg
import library.DITTO.AriaRTPlanQR as AriaRTPlanQR
import library.DITTO.DicomIntegrityTool as DicomIntegrityTool


def run_dicom_integrity_tool_physics_review(tab_width: int, tab_height: int,
                                            beamset_name: str = None, use_progress_bar: bool = False):
    """
    Runs the DICOM Integrity Tool for Physics Review.

    This function orchestrates the process of comparing DICOM RT plans
    between Aria and RayStation systems. It optionally displays a progress bar
    and generates a GUI layout for the comparison results.

    Args:
        tab_width (int): The width of the tab for GUI layout.
        tab_height (int): The height of the tab for GUI layout.
        beamset_name (str, optional): Name of the beamset to be queried and compared.
        use_progress_bar (bool, optional): Flag to display progress bar during the operation.

    Returns:
        tuple: A tuple containing the GUI layout for the results and the DicomMatchTree object.
    """

    if use_progress_bar:
        from PlanReview.guis import display_progress_bar
        progress_window, progress_bar, progress_text = display_progress_bar(
            title_text='Dicom Integrity Tool', progress_bar_text='Running DITTO...')
        update_progress_bar(progress_bar, progress_window, progress_text, 1, 'Checking for DICOM data')
    else:
        progress_window, progress_bar, progress_text = None, None, None

    # Query Aria and RayStation for DICOM RT plans
    aria_file_location, rs_file_location, selected_rs = AriaRTPlanQR.aria_qr(beamset_name=beamset_name)

    # Update progress bar after querying
    if use_progress_bar:
        update_progress_bar(progress_bar, progress_window, progress_text, 50,
                            'Aria/RayStation Match found. Comparing...')

    # Check if DICOM data is available
    if aria_file_location is None and rs_file_location is None and selected_rs is None:
        if use_progress_bar:
            update_progress_bar(progress_bar, progress_window, progress_text, 99, 'Dicom Data Unavailable')
            progress_window.close()
        return None, None

    # Compare DICOM RT plans
    dicom_match_tree = DicomIntegrityTool.compare_dicomrt_plans(rs_file_location, aria_file_location)

    # Update progress bar after comparison
    if use_progress_bar:
        update_progress_bar(progress_bar, progress_window, progress_text, 99, 'Dicom Data Comparison Complete')

    # Prepare tree data for display
    treedata = dicom_match_tree.get_treedata()
    layout = create_gui_layout(treedata, beamset_name, tab_width, tab_height)

    # Finalize the progress bar if present
    if use_progress_bar:
        update_progress_bar(progress_bar, progress_window, progress_text, 100, '')
        progress_window.close()

    return layout, dicom_match_tree

def update_progress_bar(progress_bar, progress_window, progress_text, steps_performed, message):
    """
    Updates the progress bar with a new value and message.

    Args:
        progress_bar: The progress bar object.
        progress_window: The window containing the progress bar.
        progress_text: The text object displaying progress information.
        steps_performed (int): The current progress in percentage (0-100).
        message (str): The message to display on the progress bar.
    """
    progress_bar.update(current_count=int(steps_performed / 100))
    progress_text.update(message)


def create_gui_layout(treedata, beamset_name, tab_width, tab_height):
    """
    Creates the GUI layout for displaying DICOM RT Plan comparison results.

    Args:
        treedata: The tree data generated from the DICOM comparison.
        beamset_name (str): The name of the beamset.
        tab_width (int): The width of the tab for the GUI layout.
        tab_height (int): The height of the tab for the GUI layout.

    Returns:
        The generated GUI layout.
    """
    c0_width, c1_width, c2_width = 30, 25, 35
    n_rows = 32 if tab_width < 800 else 44
    file_label1 = "RayStation"
    file_label2 = "Aria"
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
    return layout





