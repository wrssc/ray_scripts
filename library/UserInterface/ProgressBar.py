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
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
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

        self.__form = System.Windows.Forms.Form()
        self.__form.Width = 350
        self.__form.Height = 140
        self.__form.Text = title
        self.__form.BackColor = System.Drawing.Color.White

        self.__bar = System.Windows.Forms.ProgressBar()
        self.__bar.Visible = True
        self.__bar.Minimum = 1
        self.__bar.Maximum = steps
        self.__bar.Value = 1
        self.__bar.Step = 1
        self.__bar.Width = 300
        self.__bar.Height = 30
        self.__bar.Left = 15
        self.__bar.Top = 15
        self.__bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
        self.__form.Controls.Add(self.__bar)

        self.__label = System.Windows.Forms.Label()
        self.__label.Width = 300
        self.__label.Height = self.__label.PreferredHeight
        self.__label.Left = 15
        self.__label.Top = 60
        self.__label.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        self.__label.Text = text
        self.__form.Controls.Add(self.__label)

        System.Windows.Forms.Application.EnableVisualStyles()
        self.__form.Show()
        self.__label.Update()

    def __del__(self):
        """ProgressBar class destructor"""
        self.__form.Dispose()

    def update(self, text=''):
        """bar.update('new_text')"""
        if self.__bar.Value == self.__bar.Maximum:
            self.__bar.Maximum += 1
        self.__bar.PerformStep()
        if text != '':
            self.__label.Text = text
            self.__label.Update()

    def close(self):
        """bar.close()"""
        self.__form.Dispose()
