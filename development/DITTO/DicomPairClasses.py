# DicomPairClasses.py

from enum import Flag
from colorama import Fore, Style
import PySimpleGUI as sg
from pathlib import Path

RED_CIRCLE = Path("development\\DITTO\\images\\red_circle_icon.png")
GREEN_CIRCLE = Path("development\\DITTO\\images\\green_circle_icon.png")
BLUE_CIRCLE = Path("development\\DITTO\\images\\blue_circle_icon.png")


class Result(Flag):
    ELEMENT_MATCH = 0
    ELEMENT_MISMATCH = 1
    ELEMENT_UNIQUE_TO_1 = 2
    ELEMENT_UNIQUE_TO_2 = 3
    ELEMENT_EXPECTED_MISMATCH = 4
    ELEMENT_ACCEPTABLE_NEAR_MATCH = 5
    ELEMENT_BOTH_NONE = 6

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
        Result.ELEMENT_BOTH_NONE,
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

    def get_valuepair_from_key(self, key):

        if key == self.attribute_name:
            return self.value_pair

        raise RuntimeError(
            f"'key' {key} does not match attribute name {self.attribute_name}"
        )

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
        if (self.value_pair[0] is None) and (self.value_pair[1] is None):
            self.match_result = Result.ELEMENT_BOTH_NONE
            return

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

    def get_valuepair_from_key(self, key):
        if key == self.attribute_name:
            return [f"Sequence {self.attribute_name} 1", f"Sequence {self.attribute_name} 2"]
        else:

            # Split the key apart
            key_parts = key.split(">")
            next_part = key_parts[0]

            print(key_parts, next_part)

            for item in self.sequence_list:
                if item.tree_label == next_part:
                    if len(key_parts) == 1:
                        return item.get_valuepair_from_key(next_part)
                    else:
                        return item.get_valuepair_from_key(">".join(key_parts[1:]))

            raise RuntimeError(
                f"get_valuepair_from_key could not find child with key {next_part}"
            )

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

    def get_valuepair_from_key(self, key):
        if key == self.tree_label:
            return [f"Tree {self.tree_label} 1", f"Tree {self.tree_label} 2"]
        else:

            # Split the key apart
            key_parts = key.split(">")
            next_part = key_parts[0]

            for item in self.tree_list:
                if item.attribute_name == next_part:
                    if len(key_parts) == 1:
                        # item is an attribute
                        return item.get_valuepair_from_key(next_part)

                    else:
                        return item.get_valuepair_from_key(">".join(key_parts[1:]))

            raise RuntimeError(
                f"get_valuepair_from_key could not find child with key {key_parts[0]}"
            )

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
