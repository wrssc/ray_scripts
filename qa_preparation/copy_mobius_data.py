""" Copy approval data to clipboard

Copies data needed in the Mobius QA report to the clipboard.
Falls back to PySimpleGUI if PySide6 is missing.
"""

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2025-04-03'
__version__ = '0.0.2'
__status__ = 'Production'
__license__ = 'GPLv3'

import connect
import pyperclip
import logging
from datetime import datetime
from collections import OrderedDict
from typing import Optional
import sys

# Try PySide6 first; if unavailable, use PySimpleGUI
try:
    from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QTextEdit, QMessageBox
    from PySide6.QtCore import Qt, QTimer

    GUI_BACKEND = 'pyside'
except ImportError:
    GUI_BACKEND = 'pysimplegui'

    try:
        import PySimpleGUI as sg
    except ImportError:
        sg = None


def get_timestamp(beamset):
    """Return approval timestamp for a BeamSet or 'Not set.'."""
    if beamset.Review is None or str(beamset.Review.ApprovalStatus) != 'Approved':
        logging.info('QA is generated from unapproved plan or no review set.')
        return 'Not set.'
    time_stamp = str(beamset.Review.ReviewTime)
    date_object = datetime.strptime(time_stamp, '%m/%d/%Y %I:%M:%S %p')
    return str(date_object)


def get_beamset_uid(beamset):
    """Return the DICOM UID for the BeamSet."""
    return beamset.ModificationInfo.DicomUID


def build_clipboard_string(beamset):
    """
    Build a multi-line comment string from a BeamSet for the QA report.

    Args:
        beamset: RayStation BeamSet object

    Returns:
        str: Formatted comment with RSA timestamp and UID
    """
    dialog_dict = OrderedDict([
        ('RSA', get_timestamp(beamset)),
        ('UID', get_beamset_uid(beamset)),
    ])
    return '\n'.join(f"{k}: {v}" for k, v in dialog_dict.items()) + '\n'


def comment_to_clipboard(comment):
    """
    Copy the comment to the system clipboard.

    Args:
        comment (str): Text to copy
    """
    pyperclip.copy(comment)
    logging.debug("Comment copied to clipboard.")


def clipboard_gui_pyside(beamset):
    """
    Display a PySide6 GUI showing the comment and auto-closing after 4 seconds.

    Args:
        beamset: RayStation BeamSet object
    """

    class ClipboardWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Mobius data copied")
            self.setFixedSize(400, 120)

            # Build and copy comment
            try:
                comment = build_clipboard_string(beamset)
                comment_to_clipboard(comment)
            except Exception as e:
                comment = f"Error: {e}"

            # UI elements
            label = QLabel("✅ BeamSet message copied to clipboard:")
            label.setAlignment(Qt.AlignLeft)
            text_preview = QTextEdit()
            text_preview.setPlainText(comment)
            text_preview.setReadOnly(True)
            text_preview.setFocusPolicy(Qt.NoFocus)

            layout = QVBoxLayout(self)
            layout.addWidget(label)
            layout.addWidget(text_preview)

            # Auto-close
            QTimer.singleShot(4000, self.close)

    app = QApplication.instance() or QApplication(sys.argv)
    window = ClipboardWindow()
    window.show()
    app.exec()


def clipboard_gui_pysimplegui(beamset):
    """
    Display a PySimpleGUI window showing the comment and auto-closing after 4 seconds.

    Args:
        beamset: RayStation BeamSet object
    """
    if sg is None:
        logging.debug("PySimpleGUI is not installed; cannot show GUI.")
        return

    try:
        comment = build_clipboard_string(beamset)
        comment_to_clipboard(comment)
    except Exception as e:
        comment = f"Error: {e}"

    layout = [
        [sg.Text("✅ BeamSet message copied to clipboard:")],
        [sg.Multiline(comment, size=(60, 10), disabled=True, autoscroll=True)]
    ]
    window = sg.Window("Mobius data copied", layout, finalize=True)
    # Auto-close after 4000ms
    window.read(timeout=4000)
    window.close()


def clipboard_gui(beamset):
    """
    Wrapper to select the appropriate GUI backend.

    Args:
        beamset: RayStation BeamSet object
    """
    if GUI_BACKEND == 'pyside':
        clipboard_gui_pyside(beamset)
    elif GUI_BACKEND == 'pysimplegui':
        clipboard_gui_pysimplegui(beamset)
    else:
        # Fallback to console only
        comment = build_clipboard_string(beamset)
        comment_to_clipboard(comment)
        print(comment)


def main():
    """
    Main entry point: validates context and invokes clipboard GUI.
    Uses globals for RayStation objects.
    """
    app = None
    if GUI_BACKEND == 'pyside':
        # Create a type for parent to help linting
        parent: Optional[QWidget] = None
    # Validate RayStation context for Patient, Case, Plan, and BeamSet
    for obj_type in ('Patient', 'Case', 'Plan', 'BeamSet'):
        try:
            # Add the object to globals
            globals()[obj_type.lower()] = connect.get_current(obj_type)
        except Exception:
            # If GUI backend is PySide6, show QMessageBox; else print warning
            msg = f"This script requires a {obj_type} to be loaded"
            if GUI_BACKEND == 'pyside':
                app = QApplication.instance() or QApplication([])
                QMessageBox.warning(parent, "Warning", msg)
            else:
                print("Warning:", msg)

    # Finally, show the clipboard GUI
    try:
        clipboard_gui(globals()['beamset'])
    except NameError:
        # Handle case where BeamSet is not found
        if app:
            parent: Optional[QWidget] = None
            QMessageBox.warning(parent, "Warning", "BeamSet object not found; cannot build clipboard string.")

        else:
            print("Warning: BeamSet object not found; cannot build clipboard string.")
        logging.debug("BeamSet object not found; cannot build clipboard string.")


if __name__ == '__main__':
    main()
