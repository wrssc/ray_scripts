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


def _ChildProcess(args, queue, kill):

    # Link .NET assemblies
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    import System

    current_step = queue.get()

    # Define text wrap length
    wrap_length = 60

    # Initialize form
    form = System.Windows.Forms.Form()
    form.Width = 400
    form.Height = min(20 * math.ceil(len(args['summary']) / wrap_length) + 300, 800)
    form.Padding = System.Windows.Forms.Padding(0)
    form.Text = args['title']
    form.AutoScroll = True
    form.BackColor = System.Drawing.Color.White
    table = System.Windows.Forms.TableLayoutPanel()
    table.ColumnCount = 1
    table.RowCount = 1
    table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
    table.Padding = System.Windows.Forms.Padding(0)
    table.BackColor = System.Drawing.Color.White
    table.AutoSize = True
    form.Controls.Add(table)

    # Add script name, summary
    if args['name'] is not None:
        name = System.Windows.Forms.Label()
        name.Text = args['name']
        name.Width = 345
        name.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        table.Controls.Add(name)

    if args['summary'] is not None:
        summary = System.Windows.Forms.Label()
        summary.Text = '\n'.join(textwrap.wrap(args['summary'], wrap_length))
        summary.Width = 345
        summary.Height = 15 * math.ceil(len(args['summary']) / wrap_length)
        summary.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        table.Controls.Add(summary)

    def read_only(_s, _e):
        steps.SelectedIndex = current_step

    # Add steps
    if args['steps'] is not None:
        step_title = System.Windows.Forms.Label()
        step_title.Text = 'Steps'
        step_title.Width = 345
        step_title.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        table.Controls.Add(step_title)

        steps = System.Windows.Forms.ListBox()
        steps.Width = 345
        steps.Height = min(500, 30 * len(args['steps']))
        steps.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        steps.MultiColumn = False
        steps.Click += read_only
        for i in range(len(args['steps'])):
            steps.Items.Add('{}. {}'.format(i + 1, args['steps'][i]))

        steps.SelectedIndex = current_step
        table.Controls.Add(steps)

    # Add progress bar
    bar = System.Windows.Forms.ProgressBar()
    bar.Visible = True
    bar.Width = 345
    bar.Height = 30
    bar.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
    bar.Style = System.Windows.Forms.ProgressBarStyle.Marquee
    bar.MarqueeAnimationSpeed = 50
    table.Controls.Add(bar)

    # Executes when OK is pressed
    def launch_help(_s, _e):
        print 'TODO: launch help'

    # Executes when cancel is pressed
    def stop_script(_s, _e):
        if q >= 0:
            print 'TODO: abort and revert state'

        form.DialogResult = True
        kill.set()

    # OK/Cancel buttons
    button_table = System.Windows.Forms.TableLayoutPanel()
    button_table.ColumnCount = 2
    button_table.RowCount = 1
    button_table.Padding = System.Windows.Forms.Padding(0)
    button_table.BackColor = System.Drawing.Color.White
    button_table.AutoSize = True
    button_table.Anchor = System.Windows.Forms.AnchorStyles.Right
    table.Controls.Add(button_table)

    help = System.Windows.Forms.Button()
    help.Text = 'Help'
    help.Height = 30
    help.Width = 70
    help.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
    help.BackColor = System.Drawing.Color.LightGray
    help.FlatStyle = System.Windows.Forms.FlatStyle.Flat
    help.Click += launch_help
    button_table.Controls.Add(help)

    abort = System.Windows.Forms.Button()
    abort.Text = 'Abort'
    abort.Height = 30
    abort.Width = 70
    abort.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
    abort.BackColor = System.Drawing.Color.LightGray
    abort.FlatStyle = System.Windows.Forms.FlatStyle.Flat
    abort.Click += stop_script
    button_table.Controls.Add(abort)

    # Display form
    System.Windows.Forms.Application.EnableVisualStyles()
    form.Update()
    form.Show()

    while True:
        if not queue.empty():
            q = queue.get()

            # -1 indicates script is done
            if q == -1:
                form.Visible = False
                bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
                bar.Minimum = 1
                bar.Value = 10
                bar.Maximum = 10
                abort.Text = 'Close'
                form.ShowDialog()


            # queue is step index
            elif q >= 0:
                current_step = q
                steps.SelectedIndex = current_step


        System.Windows.Forms.Application.DoEvents()

    
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

    def __init__(self, name=None, summary=None, title='Script Status', steps=None, docstring=None, help=None):
        """status = UserInterface.ScriptStatus(steps=['Step A', 'Step B'], docstring=__doc__, help=__help__)"""

        # If a docstring was provided, pull name and summary from there
        if docstring is not None:
            name, summary = self.__parse_docstring(docstring)

        # Store inputs and initialize step counter
        self.args = {'name': name, 'summary': summary, 'title': title, 'steps': steps, 'help': help}
        self.current_step = 0

        # Launch separate thread
        self.__kill = multiprocessing.Event()
        self.__queue = multiprocessing.Queue()
        self.__queue.put(0)
        self.__parent_conn, self.__child_conn = multiprocessing.Pipe()
        self.__process = multiprocessing.Process(target=_ChildProcess,
                                                 args=(self.args, self.__queue, self.__kill))
        self.__process.start()
        self.__process.join(1)

    def next_step(self, num=None, text=None):
        """status.next_step()"""

        if num is None:
            self.current_step += 1
        else:
            self.current_step = num

        self.__queue.put(min(self.current_step, len(self.args['steps'])))

    def finish(self, text=None):

        self.__queue.put(-1)
        while not self.__kill.is_set():
            self.__process.join(1)

        self.__process.terminate()

    def add_step(self, step):
        """status.add_step('Step C')"""


    def ask_input(self, inputs, initial=None, datatype=None, options=None, required=None):
        """status.ask_input({'a':'Enter a value for a:'})"""


    def __del__(self):
        """ScriptStatus class destructor"""
        self.__process.terminate()

    def close(self):
        """status.close()"""
        self.__del__()

'''
if __name__ == '__main__':
    import time
    status = ScriptStatus(steps=['Step A', 'Step B', 'Step C'], docstring=__doc__, help=__help__)
    time.sleep(2)
    status.next_step()
    time.sleep(2)
    status.next_step()
    time.sleep(2)
    status.finish()
'''

