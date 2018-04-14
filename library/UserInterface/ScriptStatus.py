""" Script Status GUI Widget

    ScriptStatus is a class that displays a UI to the user while scripts execute.
    Users can provide a list of steps that the script performs, and use the
    next_step() function to walk the user through the current step. The optional
    text argument allows additional (single or multi-line) text to be listed on
    the UI explaining what each step is doing. The finish() function will allow
    display a completion message and hold the parent script until the status
    window is closed (to exit immediately, use the close() function). To update
    the status text without progressing to the next step, call update_text()

    Note, the window will not display until the first next_step() call, which
    would correspond to the first step. The following example illustrates how to
    use this class.


    if __name__ == '__main__':
        import time
        import UserInterface

        status = UserInterface.ScriptStatus(steps=['Step A', 'Step B', 'Step C'],
                                            docstring=__doc__, help=__help__)

        status.next_step(text='Please wait while step A is running')
        time.sleep(2)
        status.next_step(text='Step B is now running')
        time.sleep(2)
        status.next_step(text='Step C is now running')
        time.sleep(2)
        status.finish(text='The script executed successfully')


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
import webbrowser
import logging


class ScriptStatus:

    def __init__(self, name=None, summary=None, title='Script Status', steps=None, docstring=None, help=None):
        """status = UserInterface.ScriptStatus(steps=['Step A', 'Step B'], docstring=__doc__, help=__help__)"""

        # If a docstring was provided, pull name and summary from there
        if docstring is not None:
            name, summary = _parse_docstring(docstring)

        # Store inputs and initialize step counter
        self.__args = {'name': name, 'summary': summary, 'title': title, 'steps': steps, 'help': help}
        self.current_step = -1

        # Initialize thread communication pathways
        self.__kill = multiprocessing.Event()
        self.__abort = multiprocessing.Event()
        self.__queue = multiprocessing.Queue()

        # Launch separate thread
        self.__process = multiprocessing.Process(target=_child_process,
                                                 args=(self.__args, self.__queue, self.__abort, self.__kill))

    def __del__(self):
        """ScriptStatus class destructor"""
        if self.__process.is_alive():
            self.__process.terminate()

    def next_step(self, text='', num=None):
        """status.next_step('new status')"""

        # If abort was pressed
        if self.__abort.is_set():

            # Link .NET assemblies
            clr.AddReference('System.Windows.Forms')
            clr.AddReference('System.Drawing')
            import System

            # Update child process
            logging.warning('ScriptStatus aborted after step {}'.format(self.current_step + 1))
            self.__queue.put([-2, 'The script was aborted after step {}'.format(self.current_step + 1)])

            # Display message box to stop parent thread
            System.Windows.Forms.MessageBox.Show('The script was aborted after step {}'.format(self.current_step + 1),
                                                 'Script Aborted', System.Windows.Forms.MessageBoxButtons.OK,
                                                 System.Windows.Forms.MessageBoxIcon.Warning)

            # Wait for child to be closed
            while not self.__kill.is_set():
                self.__process.join(0.1)

            exit()

        else:

            # Increment step
            if num is None:
                self.current_step += 1
            else:
                self.current_step = num

            self.current_step = min(self.current_step, len(self.__args['steps']) - 1)

            # Send step, what's next text to child process
            logging.info('ScriptStatus updated to step {}'.format(self.current_step + 1))
            self.__queue.put([self.current_step, text])

            # If the child is not yet started
            if not self.__process.is_alive():
                self.__process.start()
                self.__process.join(0.1)

    def add_step(self, text=''):
        """status.add_step('new step')"""
        self.__queue.put([-3, text])

    def update_text(self, text=''):
        """status.update_text('new text')"""
        self.__queue.put([self.current_step, text])

    def finish(self, text=''):

        logging.info('ScriptStatus finished at step {}'.format(self.current_step + 1))
        self.__queue.put([-2, text])
        while not self.__kill.is_set():
            self.__process.join(0.1)

        self.__process.terminate()

    def close(self):
        """status.close()"""
        logging.debug('ScriptStatus closed')
        if self.__process.is_alive():
            self.__process.terminate()

    def aborted(self):
        """bool = status.aborted()"""
        return self.__abort.is_set()


def _child_process(args, queue, aborted, kill):

    # Link .NET assemblies
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    import System

    current_step, status_text = queue.get()

    # Define text wrap length
    wrap_length = 60

    # Initialize form
    form = System.Windows.Forms.Form()
    form.Width = 400
    form.Height = min(800, 20 * math.ceil(len(args['summary']) / wrap_length) + 15 *
                      (status_text.count('\n') + 1) + 300 + max(50, min(500, 20 * len(args['steps']))))
    form.Padding = System.Windows.Forms.Padding(0)
    form.Text = args['title']
    form.AutoScroll = True
    form.BackColor = System.Drawing.Color.White
    form.TopMost = True
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
        name.Font = System.Drawing.Font(name.Font, name.Font.Style | System.Drawing.FontStyle.Bold)
        name.TextAlign = System.Drawing.ContentAlignment.TopCenter
        table.Controls.Add(name)

    if args['summary'] is not None:
        summary = System.Windows.Forms.Label()
        summary.Text = textwrap.fill(args['summary'], wrap_length)
        summary.Width = 345
        summary.Height = 20 * math.ceil(len(args['summary']) / wrap_length)
        summary.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        table.Controls.Add(summary)

    def read_only(_s, _e):
        steps.SelectedIndex = current_step

    # Add steps
    if args['steps'] is not None:
        step_title = System.Windows.Forms.Label()
        step_title.Text = 'Steps:'
        step_title.Width = 345
        step_title.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        step_title.Font = System.Drawing.Font(step_title.Font, step_title.Font.Style | System.Drawing.FontStyle.Bold)
        table.Controls.Add(step_title)

        steps = System.Windows.Forms.ListBox()
        steps.Width = 345
        steps.Height = max(50, min(500, 20 * len(args['steps'])))
        steps.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        steps.MultiColumn = False
        steps.Click += read_only
        for i in range(len(args['steps'])):
            steps.Items.Add('{}. {}'.format(i + 1, args['steps'][i]))

        steps.SelectedIndex = current_step
        table.Controls.Add(steps)

    # Add script status label
    status_label = System.Windows.Forms.Label()
    status_label.Text = 'Execution Status:'
    status_label.Width = 345
    status_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
    status_label.Font = System.Drawing.Font(status_label.Font, status_label.Font.Style | System.Drawing.FontStyle.Bold)
    table.Controls.Add(status_label)

    # Add script status
    status = System.Windows.Forms.Label()
    status.Text = status_text
    status.Width = 345
    status.Height = 15 * (status_text.count('\n') + 1) + 10
    status.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
    table.Controls.Add(status)

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
        webbrowser.open(args['help'], new=0, autoraise=True)

    # Executes when cancel is pressed
    def stop_script(_s, _e):
        if current_step >= 0:
            status.Text = 'The script will abort after this step...'
            aborted.set()

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

    if args['help'] is not None:
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
    form.SetDesktopLocation(System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Right - form.Width, 50)
    System.Windows.Forms.Application.DoEvents()

    while True:
        if not queue.empty():
            current_step, status_text = queue.get()

            # -3 indicates a step should be added
            if current_step == -3:
                args['steps'].append(status_text)
                steps.Items.Add('{}. {}'.format(len(args['steps']), status_text))
                current_step = steps.SelectedIndex

            else:
                status.Text = status_text
                status.Height = 15 * (status_text.count('\n') + 1) + 10
                form.Height = min(800, 20 * math.ceil(len(args['summary']) / wrap_length) + 15 *
                                  (status_text.count('\n') + 1) + 300 + max(50, min(500, 20 * len(args['steps']))))

            # -2 indicates script is done
            if current_step == -2:
                form.Visible = False
                bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
                bar.Minimum = 1
                bar.Value = 2
                bar.Maximum = 2
                abort.Text = 'Close'
                form.ShowDialog()

            # Otherwise assume this is a step index
            else:
                form.Visible = False
                if args['steps'] is not None:
                    steps.SelectedIndex = current_step

                bar.Style = System.Windows.Forms.ProgressBarStyle.Marquee
                form.Visible = True

        # Allow the UI time to catch up
        System.Windows.Forms.Application.DoEvents()


def _parse_docstring(docstring):
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

