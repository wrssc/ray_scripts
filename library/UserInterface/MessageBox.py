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
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/User-Interface'
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
        """box = UserInterface.QuestionBox('text', 'title')"""

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

class RichTextBox:


    def __init__(self, text, title='RT Box', form=None):

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        import System

        """box = UserInterface.MessageBox('text', 'title')"""
        if form is None:
            self.form = System.Windows.Forms.Form()
            self.form.AutoSize = True
            self.form.MaximumSize = System.Drawing.Size(1200,
                                                        System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.form.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
            self.form.Padding = System.Windows.Forms.Padding(0)
            self.form.Text = title
            self.form.AutoScroll = True
            self.form.BackColor = System.Drawing.Color.White
            self.form.TopMost = True

            # Add table layout
            self.outer_table = System.Windows.Forms.TableLayoutPanel()
            self.outer_table.ColumnCount = 1
            self.outer_table.RowCount = 1
            self.outer_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
            self.outer_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 10)
            self.outer_table.BackColor = System.Drawing.Color.White
            self.outer_table.AutoSize = True
            self.form.Controls.Add(self.outer_table)

            # Add intro text
            if text != '':

                self.intro = System.Windows.Forms.Label()
                self.intro.Text = text
                self.intro.AutoSize = True
                self.intro.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width - 55,
                                                             System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
                self.intro.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                self.outer_table.Controls.Add(self.intro)

        else:
            self.form = form

    def show(self):
        """results = dialog.show()"""
        self.values = {}
        self.form.ShowDialog()




