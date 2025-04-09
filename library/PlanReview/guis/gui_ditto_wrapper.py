try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg
import pydicom
import sys
from pathlib import Path
# Similarly, point to the DITTO folder where more magic happens


def run_dicom_integrity_tool_physics_review(tab_width: int, tab_height: int,
                                            beamset_name: str = None, use_progress_bar: bool = False):
    ditto_path = Path(__file__).parent.parent / "library" / "DITTO"
    sys.path.insert(1, str(ditto_path))
    import DITTO.AriaRTPlanQR as AriaRTPlanQR
    import DITTO.DicomIntegrityTool_APTR as DicomIntegrityTool_APTR
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
        update_progress_bar(progress_bar, progress_text, 1, 'Checking for DICOM data')
    else:
        progress_window, progress_bar, progress_text = None, None, None

    # Query Aria and RayStation for DICOM RT plans
    aria_file_location, rs_file_location, selected_rs = AriaRTPlanQR.aria_qr(beamset_name=beamset_name)

    # Update progress bar after querying
    if use_progress_bar:
        update_progress_bar(progress_bar,  progress_text, 50,
                            'Aria/RayStation Match found. Comparing...')

    # Check if DICOM data is available
    if aria_file_location is None and rs_file_location is None and selected_rs is None:
        if use_progress_bar:
            update_progress_bar(progress_bar, progress_text, 99, 'Dicom Data Unavailable')
            progress_window.close()
        return None, None

    # Compare DICOM RT plans
    # Get ARIA and RAYSTATION Tree Pairs
    ds1 = pydicom.dcmread(rs_file_location, force=True)
    ds2 = pydicom.dcmread(aria_file_location, force=True)

    aptr_dicom_tree_pair = DicomIntegrityTool_APTR.run_aria_plan_transfer_checks(ds1, ds2)
    aptr_treedata = aptr_dicom_tree_pair.get_treedata(show_matches=True)

    # Update progress bar after comparison
    if use_progress_bar:
        update_progress_bar(progress_bar, progress_text, 99, 'Dicom Data Comparison Complete')

    # Prepare tree data for display
    # treedata = dicom_match_tree.get_treedata()
    layout = create_gui_layout(aptr_treedata, beamset_name, tab_width, tab_height)

    # Finalize the progress bar if present
    if use_progress_bar:
        update_progress_bar(progress_bar, progress_text, 100, '')
        progress_window.close()

    return layout, aptr_dicom_tree_pair


def update_progress_bar(progress_bar, progress_text, steps_performed, message):
    """
    Updates the progress bar with a new value and message.

    Args:
        progress_bar: The progress bar object.
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
                            key=f'-APTR_TREE_{beamset_name}',
                            show_expanded=False,
                            enable_events=True,

                        ),
                    ],
                    [
                        Sg.Text(f'{file_label1} Value: '),
                        Sg.Text('Value 1', key=f"-APTR_VALUE1_{beamset_name}", size=(100, None)),
                    ],
                    [
                        Sg.Text(f'{file_label2} Value: '),
                        Sg.Text('Value 2', key=f"-APTR_VALUE2_{beamset_name}", size=(100, None)),
                    ],
                    [
                        Sg.Text(f'{file_label2} Comment: '),
                        Sg.Text('Comment', key=f"-APTR_COMMENT_{beamset_name}", size=(100, None)),
                    ],
                ],
                size=(tab_width, tab_height),
            )
        ]
    ]
    return layout


def get_ditto_tab(tab_width, tab_height, beamsets):
    tab_list = []
    match_trees = {}
    count = 1
    for beamset in beamsets:
        ditto_layout, match_tree = run_dicom_integrity_tool_physics_review(
            tab_width=tab_width, tab_height=tab_height, beamset_name=beamset,
            use_progress_bar=True)
        if ditto_layout is None and match_tree is None:
            continue
        tab_ditto = Sg.Tab(f'DI: {count}', ditto_layout,
                           key='DITTO',
                           tooltip=f'Review and log DITTO results for {beamset}')
        tab_list.append(tab_ditto)
        match_trees[beamset] = match_tree
        count += 1
    return tab_list, match_trees


def on_ditto_element_click(window, values, event, beamsets, match_trees):
    # Extract the beamset name from the event key
    beamset_parts = event.split('_')
    beamset_name = '_'.join(beamset_parts[-3:])  # Join the last three parts to form the beamset name
    if beamset_name in beamsets:  # Check if the extracted name is in the list of beamsets
        tree_key = values[event][0]
        dicom_match_tree = match_trees[beamset_name]
        value1, value2 = dicom_match_tree.get_valuepair_from_key(tree_key[1:])
        element = dicom_match_tree.get_element_from_key(tree_key[1:])

        # Update the values in the window
        window[f"-APTR_VALUE1_{beamset_name}"].update(value1 if value1 is not None else "")
        window[f"-APTR_VALUE2_{beamset_name}"].update(value2 if value2 is not None else "")
        window[f"-APTR_COMMENT_{beamset_name}"].update(element.parent.get_name() if element.parent else "")
