""" Script Selector
    
    This script scans the subfolders in this repository and displays a list of each script
    found in a given subfolder to the user. This script will then execute the script that 
    the user selects. With this approach, this is the only script that needs to be loaded 
    into RayStation, while all of the actual scripts are dynamically queried and run from 
    this one.
    
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
__date__ = '2018-04-02'

__version__ = '1.0.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'N/A'

__reviewed__ = 'YYYY-MM-DD'
__maintainer__ = 'Mark Geurts'

__email__ =  'mark.w.geurts@gmail.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements
import os
import sys
import wpf
from System.Windows import Window, Thickness
from System.Windows.Controls import Button, StackPanel

# Specify the location of the repository containing all scripts
repo = r'\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\Geurts\ray_scripts'

# Specify subfolder to scan (to list all, leave blank)
module = r''

"""
# Specify flag indicating whether or not to refresh the repository (git pull) prior to 
# scanning the repository
refresh = False

# Refresh Git repository
if refresh:
"""

# Initialize list of scripts
paths = []
scripts = []
names = []
tooltips = []
for root, dirs, files in os.walk(os.path.join(repo, module)):
    for file in files:
        if file.endswith('.py'):
            print 'Found {}'.format(os.path.join(root, file))
            paths.append(root)
            scripts.append(file.rstrip('.py'))
            f = open(os.path.join(root, file))
            c = f.readlines()
            names.append(c.pop(0).strip(' " \n'))
            c.pop(0)
            s = []
            for l in c:
                if l.isspace():
                    break
                s.append(l.strip())
            f.close()  
            tooltips.append('\n'.join(s))

# Start XAML content. As each script is found, additional content will be appended
window = Window()
window.Width = 400
window.Height = 500
window.Title = 'Select a script to run'
stack = StackPanel()
stack.Margin = Thickness(15)
window.Content = stack

# Define button action
def RunScript(self, e):
    print '{} selected, executing {}'.format(self.Content, \
        scripts[names.index(self.Content)])
    window.DialogResult = True
    sys.path.append(paths[names.index(self.Content)])
    __import__(scripts[names.index(self.Content)])

# List directory contents
for name, tip in zip(names, tooltips):
    button = Button()
    button.Content = name
    button.Margin = Thickness(5)
    button.ToolTip = tip
    button.Click += RunScript
    stack.Children.Add(button)
       
# Open window  
window.ShowDialog()