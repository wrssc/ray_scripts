""" MessageBox GUI Widget

    The MessageBox() class constructor displays a message box to the user, and pauses
    execution until OK is pressed. The following example illustrates how to use this
    class:

    import UserInterface
    box = UserInterface.MessageBox('You successfully launched a MessageBox', 'Success')

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
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements
import clr

class MessageBox:

    def __init__(self, text, title='Message Box'):
        """box = UserInterface.MessageBox('text', 'title')"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        import System

        System.Windows.Forms.MessageBox.Show(text, title, System.Windows.Forms.MessageBoxButtons.OK)

class WarningBox:

    def __init__(self, text, title='Warning'):
        """box = UserInterface.WarningBox('text', 'title')"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        import System

        System.Windows.Forms.MessageBox.Show(text, title, System.Windows.Forms.MessageBoxButtons.OK,
                                             System.Windows.Forms.MessageBoxIcon.Warning)

class QuestionBox:

    def __init__(self, text, title='Question'):
        """box = UserInterface.MessageBox('text', 'title')"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        import System

        r = System.Windows.Forms.MessageBox.Show(text, title, System.Windows.Forms.MessageBoxButtons.YesNo,
                                                      System.Windows.Forms.MessageBoxIcon.Question)

        if r == System.Windows.Forms.DialogResult.Yes:
            self.yes = True
            self.no = False

        else:
            self.yes = False
            self.no = True
