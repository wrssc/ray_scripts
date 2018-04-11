""" Common Dialog UI Widgets

    The CommonDialog class contains Windows Presentation Foundation functions typically
    available in IronPython that are otherwise unavailable in CPython. Class functions
    call IronPython as a subprocess, display the dialog box, and return the response.
    The following example shows how to use the functions in this class:

    import UserInterface
    common = UserInterface.CommonDialog()
    path = common.folder_browser('Select a folder containing CT files:')
    filename = common.open_file('Select a file to open:')
    filename = common.save_file('Choose where to save a file:')

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
import logging


class CommonDialog:

    # Class constructor
    def __init__(self, ipy=r'c:\Program Files (x86)\IronPython 2.7.1\ipy.exe'):
        """common = CommonDialog('c:\optional path to IronPython\ipy.exe')"""

        # Store input
        self.ipy = ipy

        # Verify IronPython exists
        if not os.path.isfile(self.ipy):
            logging.error('No such file or directory: {}'.format(self.ipy))
            raise OSError(2, 'No such file or directory', self.ipy)

        # Create folder_browser script
        self.folder_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
        self.folder_script.write("""
# Import modules and assemblies
import sys
import clr
clr.AddReference('System.Windows.Forms')
import System

# Create FolderBrowserDialog
dialog = System.Windows.Forms.FolderBrowserDialog()
dialog.Description = sys.argv[1]
dialog.ShowNewFolderButton = True

# Open dialog and wait for response
if dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK:
    print dialog.SelectedPath
""")
        self.folder_script.close()

        # Create open_file script
        self.openfile_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
        self.openfile_script.write("""
# Import modules and assemblies
import sys
import clr
import os
clr.AddReference('System.Windows.Forms')
import System

# Create OpenFileDialog
dialog = System.Windows.Forms.OpenFileDialog()
dialog.Title = sys.argv[1]
dialog.Filter = sys.argv[2]
dialog.InitialDirectory = os.path.expanduser('~/Documents')
dialog.RestoreDirectory = False
if sys.argv[3] == 'True':
    dialog.Multiselect = True
else:
    dialog.Multiselect = False

# Open dialog and wait for response
if dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK:
    if dialog.Multiselect:
        for f in dialog.FileNames:
            print os.path.join(os.getcwd(), f)
    else:
        print os.path.join(os.getcwd(), dialog.FileName)
""")
        self.openfile_script.close()

        # Create save_file script
        self.savefile_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
        self.savefile_script.write("""
# Import modules and assemblies
import sys
import clr
import os
clr.AddReference('System.Windows.Forms')
import System

# Create OpenFileDialog
dialog = System.Windows.Forms.SaveFileDialog()
dialog.Title = sys.argv[1]
dialog.Filter = sys.argv[2]
dialog.InitialDirectory = os.path.expanduser('~/Documents')
dialog.RestoreDirectory = False
dialog.Multiselect = False

# Open dialog and wait for response
if dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK:
    print os.path.join(os.getcwd(), dialog.FileName)
""")
        self.openfile_script.close()

    # folder_browser function
    def folder_browser(self, title='Folder Browser'):
        """path = common.folder_browser(title='title')"""
        return subprocess.check_output('"{}" {} "{}"'.format(self.ipy, self.folder_script.name, title)).strip()

    # open_file function
    def open_file(self, title='File Browser', filters='All Files (*.*)|*.*', multi=False):
        """file = common.open_file(title='title', filters='filter', multi=False)"""
        return subprocess.check_output('"{}" {} "{}" "{}" "{}"'.format(self.ipy, self.openfile_script.name, title,
                                                                       filters, multi)).strip()

    # save_file function
    def save_file(self, title='Save File', filters='All Files (*.*)|*.*'):
        """file = common.save_file(title='title', filters='filter', multi=False)"""
        return subprocess.check_output('"{}" {} "{}" "{}"'.format(self.ipy, self.savefile_script.name, title,
                                                                  filters)).strip()

    # Class destructor
    def __del__(self):
        os.unlink(self.folder_script.name)
        os.unlink(self.openfile_script.name)
