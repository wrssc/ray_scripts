""" Button List GUI Widget

    The ButtonList() class constructor displays a vertical list of buttons based on
    the provided inputs list. The show() command will display the form and return
    the selected value, or None if the form was cancelled.

    import UserInterface
    dialog = UserInterface.ButtonList(inputs=['a', 'b'])
    print dialog.show()

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

# Import packages
import clr


class ButtonList:

    def __init__(self, inputs, text='', title='Select a Button', form=None):
        """dialog = UserInterface.ButtonList(['a', 'b'])"""
        
        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize variable
        self.value = None

        # Initialize form (if provided, use existing)
        if form is None:
            self.form = System.Windows.Forms.Form()
            self.form.AutoSize = True
            self.form.MaximumSize = System.Drawing.Size(400,
                                                        System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.form.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
            self.form.Padding = System.Windows.Forms.Padding(0)
            self.form.Text = title
            self.form.AutoScroll = True
            self.form.BackColor = System.Drawing.Color.White
            self.form.TopMost = True

        else:
            self.form = form

        # Add table layout
        self.table = System.Windows.Forms.TableLayoutPanel()
        self.table.ColumnCount = 1
        self.table.RowCount = 1
        self.table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.table.Padding = System.Windows.Forms.Padding(0, 0, 0, 10)
        self.table.BackColor = System.Drawing.Color.White
        self.table.AutoSize = True
        self.form.Controls.Add(self.table)

        # Add intro text
        if text != '':
            self.intro = System.Windows.Forms.Label()
            self.intro.Text = text
            self.intro.AutoSize = True
            self.intro.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width - 50,
                                                         System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.intro.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.table.Controls.Add(self.intro)

        # Executes when OK is pressed
        def go(s, _e):
            self.value = s.Text
            self.form.DialogResult = True
            self.status = True

        # Loop through inputs
        for i in inputs:
            self.buttons[i] = System.Windows.Forms.Button()
            self.buttons[i].Text = i
            self.buttons[i].Height = 50
            self.buttons[i].Width = form.MaximumSize.Width - 50
            self.buttons[i].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.buttons[i].BackColor = System.Drawing.Color.LightGray
            self.buttons[i].FlatStyle = System.Windows.Forms.FlatStyle.Flat
            self.buttons[i].Click += go
            self.table.Controls.Add(self.buttons[i])
        
    def show(self):
        """results = dialog.show()"""
        self.value = None
        self.form.ShowDialog()
        return self.value

    def __del__(self):
        """ButtonList class destructor"""
        self.form.Dispose()
