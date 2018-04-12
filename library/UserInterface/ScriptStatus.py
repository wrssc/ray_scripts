""" Script Status GUI Widget

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
import math
import textwrap
import multiprocessing


def _ThreadRunner(object, name, summary, title, steps, help):

    return object._show_form(name, summary, title, steps, help)
    
class ScriptStatus:

    def __parse_docstring(self, docstring):
        """ internal docstring parser """

        lines = docstring.splitlines()
        name = lines.pop(0).strip(' " \n')
        lines.pop(0)  # Skip second line
        s = []
        for l in lines:
            if l.isspace():
                break
            s.append(l.strip())

        summary = ' '.join(s)
        return name, summary

    def _show_form(self, name, summary, title, steps, help):

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Define text wrap length
        wrap_length = 60

        # Initialize form
        self.__form = System.Windows.Forms.Form()
        self.__form.Width = 400
        self.__form.Height = min(20 * math.ceil(len(summary) / wrap_length) + 300, 800)
        self.__form.Padding = System.Windows.Forms.Padding(0)
        self.__form.Text = title
        self.__form.AutoScroll = True
        self.__form.BackColor = System.Drawing.Color.White
        self.__table = System.Windows.Forms.TableLayoutPanel()
        self.__table.ColumnCount = 1
        self.__table.RowCount = 1
        self.__table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.__table.Padding = System.Windows.Forms.Padding(0)
        self.__table.BackColor = System.Drawing.Color.White
        self.__table.AutoSize = True
        self.__form.Controls.Add(self.__table)

        # Add script name, summary
        if name is not None:
            self.__name = System.Windows.Forms.Label()
            self.__name.Text = name
            self.__name.Width = 345
            self.__name.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.__table.Controls.Add(self.__name)

        if summary is not None:
            self.__summary = System.Windows.Forms.Label()
            self.__summary.Text = '\n'.join(textwrap.wrap(summary, wrap_length))
            self.__summary.Width = 345
            self.__summary.Height = 15 * math.ceil(len(summary) / wrap_length)
            self.__summary.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.__table.Controls.Add(self.__summary)

        def read_only(s, _e):
            self.__steps.SelectedIndex = self.step

        self.step = 0

        # Add steps
        if steps is not None:
            self.__step_title = System.Windows.Forms.Label()
            self.__step_title.Text = 'Steps'
            self.__step_title.Width = 345
            self.__step_title.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.__table.Controls.Add(self.__step_title)

            self.__steps = System.Windows.Forms.ListBox()
            self.__steps.Width = 345
            self.__steps.Height = min(500, 30 * len(steps))
            self.__steps.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.__steps.MultiColumn = False
            self.__steps.Click += read_only
            for i in range(len(steps)):
                self.__steps.Items.Add('{}. {}'.format(i + 1, steps[i]))
            self.__steps.SelectedIndex = self.step
            self.__table.Controls.Add(self.__steps)

        self.__form.ShowDialog()
        self.__child_conn.close()

    def __init__(self, name=None, summary=None, title='Script Status', steps=None, docstring=None, help=None):
        """status = UserInterface.ScriptStatus(steps=['Step A', 'Step B'], docstring=__doc__, help=__help__)"""

        # If a docstring was provided, pull name and summary from there
        if docstring is not None:
            name, summary = self.__parse_docstring(docstring)

        # Launch separate thread
        self.__parent_conn, self.__child_conn = multiprocessing.Pipe()
        self.__process = multiprocessing.Process(target=_ThreadRunner, args=(self, name, summary, title, steps, help))
        self.__process.start()
        self.__process.join(1)

    def add_step(self, step):
        """status.add_step('Step C')"""

    def next_step(self, num=None, text=None):
        """status.next_step()"""

        if num is not None:
            self.step += 1
        else:
            self.step = num

        self.__steps.SelectedIndex = self.step
        self.__form.Update()

    def ask_input(self, inputs, initial=None, datatype=None, options=None, required=None):
        """status.ask_input({'a':'Enter a value for a:'})"""

    def __del__(self):
        """ScriptStatus class destructor"""
        self.__process.terminate()

    def close(self):
        """status.close()"""
        self.__del__()


if __name__ == '__main__':
    import time
    status = ScriptStatus(steps=['Step A', 'Step B'], docstring=__doc__, help=__help__)
    time.sleep(2)
    status.next_step()
    status.close()