from pathlib import Path
import pydicom
import PySimpleGUI as sg
from DicomPairClasses import ElementPair, SequencePair, DicomTreePair
from ProcessingFunctions import PROCESS_FUNCTION_DICT

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
    "ReferencedStructureSetSequence": "ReferencedSOPInstanceUID",
    "ToleranceTableSequence": "ToleranceTableNumber",
    "BeamLimitingDeviceToleranceSequence": "RTBeamLimitingDeviceType"
}


def create_dicom_tree_pair(ds1, ds2, depth=0, parent=None, parent_key="", tree_label=""):

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
                    depth=depth+1,
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
                    depth=depth+1,
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
                depth=depth+1,
                parent_key=childs_parent_key
            )

            sequence_list = []
            for item1 in ds1[ds1_keyword]:

                label = f"{match_keyword}={item1[match_keyword].value}"

                sequence_list.append(
                    create_dicom_tree_pair(
                        item1,
                        pydicom.Dataset(),
                        parent=sequence_pair,
                        depth=depth+2,
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
            depth=depth+1,
            parent_key=childs_parent_key
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
                            item1,
                            item2,
                            parent=sequence_pair,
                            depth=depth+2,
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
                        item1,
                        pydicom.Dataset(),
                        parent=sequence_pair,
                        depth=depth+2,
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
                        pydicom.Dataset(),
                        item2,
                        parent=sequence_pair,
                        depth=depth+2,
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
                        depth=depth+1,
                        process_func=process_func,
                        process_func_kwargs=kwargs,
                        parent_key=childs_parent_key,
                    )
                )

            continue

        # CASE 2a: Sequence ds2_keyword is not in our match sequence dictionary
        if (ds2_keyword not in ATTRIBUTE_MATCH_DICT.keys()) and (ds2_keyword not in ds1.dir()):

            tree_list.append(
                SequencePair(
                    parent=dicom_tree_pair,
                    attribute_name=ds2_keyword,
                    sequence_list=[],
                    comment=(
                        "Sequence was skipped because the attribute "
                        "was not found in ATTRIBUTE_MATCH_DICT"
                    ),
                    depth=depth+1,
                    parent_key=childs_parent_key
                )
            )

            continue

        # CASE 2b: Sequence ds2_keyword is unique to dataset 2

        if ds2_keyword not in ds1.dir():
            match_keyword = ATTRIBUTE_MATCH_DICT[ds2_keyword]

            sequence_list = []
            for item2 in ds2[ds2_keyword]:
                label = f"{match_keyword}={item2[match_keyword].value}"
                sequence_list.append(
                    create_dicom_tree_pair(
                        pydicom.Dataset(),
                        item2,
                        depth=depth+2,
                        parent_key=f"{childs_parent_key}>{ds2_keyword}",
                        tree_label=label,
                    )
                )

            tree_list.append(
                SequencePair(
                    parent=dicom_tree_pair,
                    attribute_name=ds2_keyword,
                    sequence_list=sequence_list,
                    comment="Sequence is unique to the second dataset.",
                    depth=depth+1,
                    parent_key=childs_parent_key
                )
            )
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

    dicom_pair_tree = create_dicom_tree_pair(ds1, ds2)

    # print_pair_tree_results(dicom_pair_tree)

    return dicom_pair_tree


def run_dicom_integrity_tool(
    filename1,
    filename2,
    file_label1="DICOM File 1",
    file_label2="DICOM File 2",
):

    dicom_match_tree = compare_dicomrt_plans(filename1, filename2)

    treedata = dicom_match_tree.get_treedata()

    layout = [
        [
            sg.Tree(
                data=treedata,
                headings=['Result','Comments', ],
                auto_size_columns=True,
                num_rows=20,
                col0_width=40,
                key='-TREE-',
                show_expanded=False,
                enable_events=True,
                #expand_x=True,
                #expand_y=True,
            ),
        ],
        [
            sg.Text(f'{file_label1} Value: '),
            sg.Text('Value 1', key="-VALUE1-"),
        ],
        [
            sg.Text(f'{file_label2} Value: '),
            sg.Text('Value 2', key="-VALUE2-"),
        ],
        [
            sg.Text(f'{file_label2} Debug Value: '),
            sg.Text('Debug', key="-DEBUG-"),
        ],
    ]

    window = sg.Window('Tree Element Test', layout, resizable=True)

    while True:     # Event Loop
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Cancel'):
            break

        tree_key = values["-TREE-"][0]

        value1, value2 = dicom_match_tree.get_valuepair_from_key(tree_key[1:])

        if value1 is None:
            value1 = ""

        if value2 is None:
            value2 = ""

        window["-VALUE1-"].update(value1)
        window["-VALUE2-"].update(value2)

    window.close()

if __name__ == "__main__":

    file_path = Path(r"U:\UWHealth\RadOnc\ShareAll\Users\ZEL\DICOM_Compare_Files\3164588")
    raystation_filename = r"RP1.2.752.243.1.1.20220110105336812.2000.10016.dcm"
    aria_filename = r"Bol_ARIA1.2.246.352.71.5.137378053967.332155.20220111111326.dcm"
    aria_filename = r"NoB_ARIA1.2.246.352.71.5.137378053967.332249.20220111111326.dcm"

    run_dicom_integrity_tool(file_path / raystation_filename, file_path / aria_filename)
