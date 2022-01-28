# DicomPairClasses.py

from enum import Flag
from colorama import Fore, Style
import PySimpleGUI as sg
from pathlib import Path

RED_CIRCLE = b'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'
GREEN_CIRCLE = Path("development\\DITTO\\images\\green_circle.png")
BLUE_CIRCLE = Path("development\\DITTO\\images\\blue_circle.png")


class Result(Flag):
    ELEMENT_MATCH = 0
    ELEMENT_MISMATCH = 1
    ELEMENT_UNIQUE_TO_1 = 2
    ELEMENT_UNIQUE_TO_2 = 3
    ELEMENT_EXPECTED_MISMATCH = 4
    ELEMENT_ACCEPTABLE_NEAR_MATCH = 5

    SEQUENCE_MATCH = 10
    SEQUENCE_MISMATCH = 11
    SEQUENCE_UNIQUE_TO_1 = 12
    SEQUENCE_UNIQUE_TO_2 = 13
    SEQUENCE_EMPTY = 14

    DICOM_TREE_MATCH = 20
    DICOM_TREE_MISMATCH = 21
    DICOM_TREE_UNIQUE_TO_1 = 22
    DICOM_TREE_UNIQUE_TO_2 = 23

    SKIPPED = 99
    UNKNOWN = 100


class ElementPair():

    DEFAULT_ACCEPTABLE_RESULTS = [
        Result.ELEMENT_MATCH,
        Result.SEQUENCE_MATCH,
        Result.ELEMENT_EXPECTED_MISMATCH,
        Result.ELEMENT_ACCEPTABLE_NEAR_MATCH,
    ]

    def __init__(
        self,
        attribute_name,
        value_pair,
        comment="",
        depth=0,
        process_func=None,
        process_func_kwargs=None,
        parent_key="",
    ):
        self.attribute_name = attribute_name
        self.value_pair = value_pair
        self.comment = comment
        self.depth = depth
        self._process_func = process_func
        self._process_func_kwargs = process_func_kwargs
        self.parent_key = parent_key
        self._update_match_result()

    def update_process_func(self, process_func=None, process_func_kwargs=None):
        self._process_func = process_func
        self._process_func_kwargs = process_func_kwargs
        self._update_match_result()

    def is_acceptable_match(
        self,
        acceptable_results=DEFAULT_ACCEPTABLE_RESULTS
    ):
        return self.match_result in acceptable_results

    def is_pure_match(self):
        return self.match_result == Result.ELEMENT_MATCH

    def is_unique_to_dataset1(self):
        return self.match_result == Result.ELEMENT_UNIQUE_TO_1

    def is_unique_to_dataset2(self):
        return self.match_result == Result.ELEMENT_UNIQUE_TO_2

    def get_treedata(self, treedata=None):

        if treedata is None:
            treedata = sg.TreeData()

        return treedata

    def return_global_key(self):
        return f"{self.parent_key}>{self.attribute_name}"

    def _update_match_result(self):
        """
        Uses the value_pair and _process_func to update the match result and comment.
        """

        if self.value_pair[0] is None:
            self.match_result = Result.ELEMENT_UNIQUE_TO_2
            return
        if self.value_pair[1] is None:
            self.match_result = Result.ELEMENT_UNIQUE_TO_1
            return

        if self._process_func is None:
            if self.value_pair[0] == self.value_pair[1]:
                self.match_result = Result.ELEMENT_MATCH
            else:
                self.match_result = Result.ELEMENT_MISMATCH

        else:
            self.match_result, self.comment = self._process_func(
                self.value_pair,
                **self._process_func_kwargs
            )

    def __str__(self):
        depth_str = self.depth*"  "
        out_str = ""
        if self.is_unique_to_dataset1() or self.is_unique_to_dataset2():
            out_str += Fore.BLUE
        elif self.is_acceptable_match():
            out_str += Fore.GREEN
        else:
            out_str += Fore.RED

        out_str += (
            depth_str
            + f"ElementPair(attribute_name='{self.attribute_name}'"
            + f", result='{self.match_result}')"
        )

        out_str += Style.RESET_ALL

        return out_str


class SequencePair():

    DEFAULT_ACCEPTABLE_RESULTS = [
        Result.SEQUENCE_MATCH,
    ]

    def __init__(
        self,
        attribute_name,
        sequence_list,
        comment="",
        depth=0,
        parent_key="",
    ):
        self.attribute_name = attribute_name
        self.sequence_list = sequence_list
        self.comment = comment
        self.depth = depth
        self.parent_key = parent_key
        self.update_match_result()

    def update_match_result(self):
        """
        There are five possible match statuses:

        We will test them in the following order.
        SEQUENCE_EMPTY
            sequence_list has length zero
        SEQUENCE_UNIQUE_TO_1
            All items in sequence_list are unique to dataset 1
        SEQUENCE_UNIQUE_TO_2
            All items in sequence_list are unique to dataset 2
        SEQUENCE_MATCH
            All items in sequence_list are True on is_acceptable_match()
        SEQUENCE_MISMATCH
            Anything else
        """
        # Address the case for an empty sequence
        if len(self.sequence_list) == 0:
            self.match_result = Result.SEQUENCE_EMPTY
            return

        # The tree_list list is of ElementPair and SequencePair objects
        unique_1_list = [item.is_unique_to_dataset1() for item in self.sequence_list]
        unique_2_list = [item.is_unique_to_dataset2() for item in self.sequence_list]
        acceptable_match_list = [item.is_acceptable_match() for item in self.sequence_list]

        if all(unique_1_list):
            self.match_result = Result.SEQUENCE_UNIQUE_TO_1
        elif all(unique_2_list):
            self.match_result = Result.SEQUENCE_UNIQUE_TO_2
        elif all(acceptable_match_list):
            self.match_result = Result.SEQUENCE_MATCH
        else:
            self.match_result = Result.SEQUENCE_MISMATCH

    def is_acceptable_match(
        self,
        acceptable_results=DEFAULT_ACCEPTABLE_RESULTS
    ):
        return self.match_result in acceptable_results

    def is_pure_match(self):
        return self.match_result == Result.SEQUENCE_MATCH

    def is_unique_to_dataset1(self):
        return self.match_result == Result.SEQUENCE_UNIQUE_TO_1

    def is_unique_to_dataset2(self):
        return self.match_result == Result.SEQUENCE_UNIQUE_TO_2

    def get_treedata(self, treedata=None):

        if treedata is None:
            treedata = sg.TreeData()

        for item in self.sequence_list:

            if item.is_unique_to_dataset1() or item.is_unique_to_dataset2():
                icon = BLUE_CIRCLE
            elif item.is_acceptable_match():
                icon = GREEN_CIRCLE
            else:
                icon = RED_CIRCLE

            match_text = item.match_result.name

            treedata.Insert(
                parent=item.parent_key,
                key=item.return_global_key(),
                text=item.tree_label,
                values=[match_text, item.comment],
                icon=icon
            )
            item.get_treedata(treedata)

        return treedata

    def return_global_key(self):
        return f"{self.parent_key}>{self.attribute_name}"

    def __str__(self):
        depth_str = self.depth*"  "

        out_str = (
            depth_str
            + f"SequencePair(attribute_name='{self.attribute_name}'"
            + f", result='{self.match_result}')"
        )
        for item in self.sequence_list:
            out_str += f"\n{str(item)}"

        return out_str


class DicomTreePair():

    DEFAULT_ACCEPTABLE_RESULTS = [
        Result.DICOM_TREE_MATCH,
    ]

    def __init__(
        self,
        tree_list,
        comment="",
        depth=0,
        parent_key="",
        tree_label="",
    ):
        self.tree_list = tree_list
        self.comment = comment
        self.depth = depth
        self.tree_label = tree_label
        self.parent_key = parent_key
        self.update_match_result()

    def update_match_result(self):
        """
        There are four possible match statuses:

        We will test them in the following order.
        DICOM_TREE_UNIQUE_TO_1
            All items in tree_list are unique to dataset 1
        DICOM_TREE_UNIQUE_TO_2
            All items in tree_list are unique to dataset 2
        DICOM_TREE_MATCH
            All items in tree_list are True on is_acceptable_match()
        DICOM_TREE_MISMATCH
            Anything else
        """
        # The tree_list list is of ElementPair and SequencePair objects
        unique_1_list = [item.is_unique_to_dataset1() for item in self.tree_list]
        unique_2_list = [item.is_unique_to_dataset2() for item in self.tree_list]
        acceptable_match_list = [item.is_acceptable_match() for item in self.tree_list]

        if all(unique_1_list):
            self.match_result = Result.DICOM_TREE_UNIQUE_TO_1
        elif all(unique_2_list):
            self.match_result = Result.DICOM_TREE_UNIQUE_TO_2
        elif all(acceptable_match_list):
            self.match_result = Result.DICOM_TREE_MATCH
        else:
            self.match_result = Result.DICOM_TREE_MISMATCH

    def is_acceptable_match(
        self,
        acceptable_results=DEFAULT_ACCEPTABLE_RESULTS
    ):
        return self.match_result in acceptable_results

    def is_pure_match(self):
        return self.match_result == Result.DICOM_TREE_MATCH

    def is_unique_to_dataset1(self):
        return self.match_result == Result.DICOM_TREE_UNIQUE_TO_1

    def is_unique_to_dataset2(self):
        return self.match_result == Result.DICOM_TREE_UNIQUE_TO_2

    def return_global_key(self):
        if self.parent_key == "":
            return ""
        else:
            return f"{self.parent_key}>{self.tree_label}"

    def get_treedata(self, treedata=None):

        if treedata is None:
            treedata = sg.TreeData()

        for item in self.tree_list:

            if item.is_unique_to_dataset1() or item.is_unique_to_dataset2():
                icon = BLUE_CIRCLE
            elif item.is_acceptable_match():
                icon = GREEN_CIRCLE
            else:
                icon = RED_CIRCLE

            match_text = item.match_result.name

            treedata.Insert(
                parent=item.parent_key,
                key=item.return_global_key(),
                text=item.attribute_name,
                values=[match_text, item.comment],
                icon=icon
            )
            item.get_treedata(treedata)

        return treedata

    def __str__(self):
        depth_str = self.depth*"  "
        out_str = (
            depth_str
            + f"DicomTreePair(result='{self.match_result}'"
            + f", comment='{self.comment}')"
        )
        for item in self.tree_list:
            out_str += f"\n{str(item)}"

        return out_str
