""" Progress Bar GUI Widget

    The ProgressBar() class constructor displays a progress bar to the user and returns the
    class object. Calls to update(x) will update the progress bar value, where x is between
    0 and 1. The close() function will close the widget. The following example demonstrates
    this class:

    import ProgressBar
    bar = ProgressBar.ProgressBar('Progress Bar', 'Updating something')
    for i in range(1, 10):
        bar.update(i/10)
    bar.close()

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
import clr
clr.AddReference('System.Windows.Forms')
import System.Windows.Forms
clr.AddReference('System.Drawing')
import System.Drawing


class ProgressBar:

    def __init__(self, title='Progress Bar', text=''):
        """bar = ProgressBar.ProgressBar(title, text)"""

        self.form = System.Windows.Forms.Form()
        self.form.Width = 350
        self.form.Height = 200
        self.form.Text = title
        self.bar = System.Windows.Forms.ProgressBar()
        self.bar.Visible = True
        self.bar.Minimum = 0
        self.bar.Maximum = 1
        self.bar.Value = 0
        self.bar.Width = 300
        self.bar.Height = 30
        self.bar.Left = 15
        self.bar.Top = 15
        self.bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
        self.form.Controls.Add(self.bar)
        self.label = System.Windows.Forms.Label
        self.label.Width = 300
        self.label.Height = 30
        self.label.Left = 15
        self.label.Top = 30
        self.label.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        self.label.Text = text
        self.form.Controls.Add(self.label)
        self.form.Show()

    def update(self, value, text=''):
        """bar.update(0.5, new_text)"""
        self.bar.Value = value
        if text != '':
            self.label.Text = text

    def close(self):
        """bar.close()"""
        self.form.DialogResult = True
