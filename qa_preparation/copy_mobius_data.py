"""
Copy approval data to clipboard,

Copies data needed in the Mobius QA report to the clipboard.


Version:
    0.0.0 Testing
    0.0.1 Changed format of output message
    0.0.2 Debugging small changes in the 11 B interface and improving user dialogs
    1.0.0 Release post debug
    1.0.1 Minor changes:
            Delete 01 (UH) and 03 (EC) Add 06 (UH)
            Added a copy to clipboard button for the last dialog

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Adam Bayliss and Patrick Hill'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2025-04-03'
__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Sean Frigo'
__reviewed__ = ''
__raystation__ = '11B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2025, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import connect
import pyperclip
import logging
from datetime import datetime
from collections import OrderedDict
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit
)
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer
import sys


def get_timestamp(beamset):
    # Get the approval time-stamp for the parent beamset
    if beamset.Review is None:
        logging.info('No approval status set.')
        approval_time = 'Not set.'
        return approval_time
    else:
        if str(beamset.Review.ApprovalStatus) == 'Approved':
            time_stamp = str(beamset.Review.ReviewTime)
            date_object = datetime.strptime(time_stamp, '%m/%d/%Y %I:%M:%S %p')
            approval_time = str(date_object)
            return approval_time
        else:
            logging.info('QA is generated from unapproved plan')
            approval_time = 'Not set.'
            return approval_time


def get_beamset_uid(beamset):
    return beamset.ModificationInfo.DicomUID


def build_clipboard_string(beamset):
    # Build a comment to insert in the plan dialog and copy it to the clipboard
    dialog_dict = OrderedDict()
    dialog_dict['RSA'] = get_timestamp(beamset)
    dialog_dict['UID'] = get_beamset_uid(beamset)

    comment = ""
    for k, v in dialog_dict.items():
        comment += "{}: {}\n".format(k, v)
    return comment

def comment_to_clipboard(comment):
    """
    Copy the comment to the clipboard.
    """
    pyperclip.copy(comment)
    print("Comment copied to clipboard.")


def clipboard_gui(beamset):
    """
    PySide6 GUI to copy QA message to clipboard and show a short confirmation.
    """
    class ClipboardWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Mobius data copied")
            self.setFixedSize(400, 100)

            # Build message
            try:
                comment = build_clipboard_string(beamset)
                comment_to_clipboard(comment)
            except Exception as e:
                comment = f"Error: {e}"

            # Setup label and preview box
            self.label = QLabel("✅ BeamSet message copied to clipboard:")
            self.label.setAlignment(Qt.AlignLeft)

            self.text_preview = QTextEdit()
            self.text_preview.setPlainText(comment)
            self.text_preview.setReadOnly(True)
            self.text_preview.setFocusPolicy(Qt.NoFocus)

            layout = QVBoxLayout()
            layout.addWidget(self.label)
            layout.addWidget(self.text_preview)
            self.setLayout(layout)

            # Auto-close after 4 seconds
            QTimer.singleShot(4000, self.close)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = ClipboardWindow()
    window.show()
    app.exec()

def main():
    try:
        patient = connect.get_current('Patient')
        case = connect.get_current('Case')
    except Exception as e:
        app = QApplication.instance() or QApplication([])
        QMessageBox.warning(None, "Warning", "This script requires a patient to be loaded")

    try:
        plan = connect.get_current('Plan')
    except Exception:
        app = QApplication.instance() or QApplication([])
        QMessageBox.warning(None, "Warning", "This script requires a plan to be loaded")
    try:
        beamset = connect.get_current('BeamSet')
    except Exception:
        app = QApplication.instance() or QApplication([])
        QMessageBox.warning(None, "Warning", "This script requires a beamset to be loaded")

    

