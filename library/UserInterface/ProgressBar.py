""" Progress Bar GUI Widget

    The ProgressBar() class constructor displays a progress bar to the user and returns the
    class object. Calls to update(x) will update the progress bar value, where x is between
    0 and 1. The close() function will close the widget. The following example demonstrates
    this class:

    import UserInterface
    import time
    bar = UserInterface.ProgressBar('Progress Bar', 'Updating something', 10)
    for i in range(1, 10):
        bar.update()
        time.sleep(1)
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

# Import packages
import clr

class ProgressBar:

    def __init__(self, text='', title='Progress Bar', steps = 10):
        """bar = ProgressBar('text', 'title', steps)"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        self.form = System.Windows.Forms.Form()
        self.form.Width = 350
        self.form.Height = 140
        self.form.Text = title
        self.form.BackColor = System.Drawing.Color.White
        self.bar = System.Windows.Forms.ProgressBar()
        self.bar.Visible = True
        self.bar.Minimum = 1
        self.bar.Maximum = steps
        self.bar.Value = 1
        self.bar.Step = 1
        self.bar.Width = 300
        self.bar.Height = 30
        self.bar.Left = 15
        self.bar.Top = 15
        self.bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
        self.form.Controls.Add(self.bar)
        self.label = System.Windows.Forms.Label()
        self.label.Width = 300
        self.label.Height = self.label.PreferredHeight
        self.label.Left = 15
        self.label.Top = 60
        self.label.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        self.label.Text = text
        self.form.Controls.Add(self.label)
        self.form.Show()
        self.label.Update()

    def __del__(self):
        """ProgressBar class destructor"""
        self.form.Dispose()

    def update(self, text=''):
        """bar.update('new_text')"""
        self.bar.PerformStep()
        if text != '':
            self.label.Text = text
            self.label.Update()

    def close(self):
        """bar.close()"""
        self.form.Dispose()
