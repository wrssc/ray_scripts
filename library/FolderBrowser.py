""" Folder Browser IronPython Plugin
    
    This plugin is called within IronPython and opens a folder browser dialog box. The 
    selected path is returned upon successful completion. The following code demonstrates 
    how this plugin is executed from within another script (running in CPython). Note, 
    this is a good old fashioned hack until I can figure out how to get CommonDialog 
    elements running in CPython.
    
    ipy = r'c:\Program Files (x86)\IronPython 2.7.1\ipy.exe'
    str = 'Select folder to export CT to:'
    import subprocess
    path = subprocess.check_output('"{}" ..\library\FolderBrowser.py "{}"'.format(ipy, str))
    
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
