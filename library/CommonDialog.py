""" Common Dialog controls for CPython

    The common dialog functions are Windows Presentation Foundation functions typically
    available in IronPython that are otherwise unavailable in CPython. These functions
    call IronPython as a subprocess, display the dialog box, and return the response.
    Current available functions include:

    path = folder_browser('Dialog Title')

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


# Specify import statements
import os
import tempfile
import subprocess

ipy = r'c:\Program Files (x86)\IronPython 2.7.1\ipy.exe'


def folder_browser(title='Folder Browser'):

    # Define code to run within IronPython
    code = """
# Specify import statements
import sys
import clr
clr.AddReference('System.Windows.Forms')
import System.Windows.Forms

# Create FolderBrowserDialog
dialog = System.Windows.Forms.FolderBrowserDialog()
dialog.Description = sys.argv[1]
dialog.ShowNewFolderButton = True

# Open dialog and wait for response
if dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK:
    print dialog.SelectedPath
    """

    # Open file handle to temp file and write code
    fh = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
    fh.write(code)
    fh.close()

    # Execute file
    path = subprocess.check_output('"{}" {} "{}"'.format(ipy,
                                                         os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                      fh.name), title)).strip()

    # Clean up and return
    os.unlink(fh.name)
    return path
