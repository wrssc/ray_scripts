""" Input Dialog GUI Widget

    The InputDialog() class constructor displays a form with input fields for the
    user to provide data to scripts. Multiple form inputs can be requested; the
    results are returned as a list. Optional input arguments also allow for custom
    input types (checkboxes, combo boxes), initial values, and required inputs. The
    results are returned as a dictionary with the same keys as defined in the text
    input argument. Note, the inputs are ordered vertically according to the SORTED
    keys, as dictionaries are randomly ordered in this version of python.
    The following example illustrates this class:

    import UserInterface
    dialog = UserInterface.InputDialog(inputs={'a': 'Enter a value: ',
                                               'b': 'Select checkboxes:',
                                               'c': 'Select combobox option:'},
                                       datatype={'b': 'check', 'c': 'combo'},
                                       initial={'a': '5', 'b': ['1'], 'c': 'C'},
                                       options={'b': ['1', '2'], 'c': ['A', 'B', 'C']},
                                       required=['a', 'b', 'c'])
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
__version__ = '1.0.1'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import clr


class InputDialog:

    def __init__(self, inputs, text='', title='Input Dialog', initial=None, datatype=None, options=None, required=None,
                 form=None):
        """dialog = UserInterface.InputDialog({'a':'Enter a value for a:'})"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize optional args
        if initial is None:
            initial = {}

        if datatype is None:
            self.datatype = {}
        else:
            self.datatype = datatype

        if options is None:
            self.options = {}
        else:
            self.options = options

        if required is None:
            self.required = []
        else:
            self.required = required

        if initial is None:
            initial = {}

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
            self.intro.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width - 55,
                                                         System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.intro.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.table.Controls.Add(self.intro)

        # Initialize variables
        self.labels = {}
        self.inputs = {}
        self.values = {}

        # Add form inputs
        for i in sorted(inputs):

            # Label
            self.labels[i] = System.Windows.Forms.Label()
            self.labels[i].Text = inputs[i]
            self.labels[i].MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width - 55,
                                                         System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.labels[i].AutoSize = True
            self.labels[i].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.table.Controls.Add(self.labels[i])

            # Validate data type
            if (i not in self.datatype and i not in self.options) or self.datatype[i] == 'text':
                self.datatype[i] = 'text'
            elif self.datatype[i] == 'check' and i in self.options:
                self.datatype[i] = 'check'
            elif self.datatype[i] == 'combo' and i in self.options:
                self.datatype[i] = 'combo'
            elif self.datatype[i] == 'radio' and i in self.options:
                self.datatype[i] = 'radio'
            elif self.datatype[i] == 'list' and i in self.options:
                self.datatype[i] = 'list'
            elif self.datatype[i] == 'bool':
                self.datatype[i] = 'bool'
            else:
                self.datatype[i] = 'unknown'

            # Textbox
            if self.datatype[i] == 'text':
                self.inputs[i] = System.Windows.Forms.TextBox()
                self.inputs[i].Height = 30
                self.inputs[i].Width = self.form.MaximumSize.Width - 55
                if i in initial:
                    self.inputs[i].Text = initial[i]

                self.inputs[i].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self.table.Controls.Add(self.inputs[i])

            # Checkbox
            elif self.datatype[i] == 'check':
                self.inputs[i] = {}
                for o in self.options[i]:
                    self.inputs[i][o] = System.Windows.Forms.CheckBox()
                    self.inputs[i][o].Text = o
                    self.inputs[i][o].Width = self.form.MaximumSize.Width - 70
                    self.inputs[i][o].Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
                    if i in initial and o in initial[i]:
                        self.inputs[i][o].Checked = True

                    self.table.Controls.Add(self.inputs[i][o])

            # Combobox/dropdown menu
            elif self.datatype[i] == 'combo':
                self.inputs[i] = System.Windows.Forms.ComboBox()
                self.inputs[i].Height = 30
                self.inputs[i].Width = self.form.MaximumSize.Width - 55
                self.inputs[i].Items.AddRange(options[i])
                if i in initial and initial[i] in options[i]:
                    self.inputs[i].SelectedItem = initial[i]

                self.inputs[i].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self.table.Controls.Add(self.inputs[i])

            # elif self.datatype[t] == 'list':

            # elif self.datatype[t] == 'radio':

            # elif self.datatype[t] == 'bool':

            else:
                raise AttributeError('Invalid type: {}'.format(datatype[i]))

        # Executes when OK is pressed
        def ok(_s, _e):

            # Validate required inputs
            failed = []
            for r in self.required:
                if self.datatype[r] == 'text' and self.inputs[r].Text == '':
                    failed.append(r)

                elif self.datatype[r] == 'check':
                    n = 0
                    for x in self.inputs[r]:
                        if self.inputs[r][x].Checked:
                            n += 1

                    if n == 0:
                        failed.append(r)

                elif self.datatype[r] == 'combo' and self.inputs[r].SelectedIndex == -1:
                    failed.append(r)

                # elif self.datatype[t] == 'list':

                # elif self.datatype[t] == 'radio':

                # elif self.datatype[t] == 'bool':

            # Continue if all required inputs exist
            if len(failed) == 0:
                self.form.DialogResult = True
                self.status = True

            # Otherwise warn the user
            else:
                for f in failed:
                    self.labels[f].ForeColor = System.Drawing.Color.Red

                System.Windows.Forms.MessageBox.Show('One or more required fields are missing', 'Required Fields',
                                                     System.Windows.Forms.MessageBoxButtons.OK,
                                                     System.Windows.Forms.MessageBoxIcon.Warning)
                self.status = False

        # Executes when cancel is pressed
        def cancel(_s, _e):
            self.form.DialogResult = True
            self.status = False

        # OK/Cancel buttons
        self.button_table = System.Windows.Forms.TableLayoutPanel()
        self.button_table.ColumnCount = 2
        self.button_table.RowCount = 1
        self.button_table.Padding = System.Windows.Forms.Padding(0)
        self.button_table.BackColor = System.Drawing.Color.White
        self.button_table.AutoSize = True
        self.button_table.Anchor = System.Windows.Forms.AnchorStyles.Right
        self.table.Controls.Add(self.button_table)

        self.ok = System.Windows.Forms.Button()
        self.ok.Text = 'OK'
        self.ok.Height = 30
        self.ok.Width = 50
        self.ok.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.ok.BackColor = System.Drawing.Color.LightGray
        self.ok.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.ok.Click += ok
        self.button_table.Controls.Add(self.ok)

        self.cancel = System.Windows.Forms.Button()
        self.cancel.Text = 'Cancel'
        self.cancel.Height = 30
        self.cancel.Width = 70
        self.cancel.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.cancel.BackColor = System.Drawing.Color.LightGray
        self.cancel.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.cancel.Click += cancel
        self.button_table.Controls.Add(self.cancel)

        # self.status stores the overall state of this object; True means the user provided
        # data, false means they didn't (Cancel or closed form) or that required data is missing
        self.status = False

    def show(self):
        """results = dialog.show()"""
        self.values = {}
        self.form.ShowDialog()

        # Retrieve values and return as a dict
        if self.status:
            for t in self.inputs:
                if self.datatype[t] == 'text':
                    self.values[t] = self.inputs[t].Text.encode('ascii', 'ignore')

                elif self.datatype[t] == 'check':
                    self.values[t] = []
                    for o in self.inputs[t]:
                        if self.inputs[t][o].Checked:
                            self.values[t].append(o.encode('ascii', 'ignore'))

                elif self.datatype[t] == 'combo':
                    if self.inputs[t].SelectedIndex >= 0:
                        self.values[t] = self.inputs[t].SelectedItem.encode('ascii', 'ignore')

                # elif self.datatype[t] == 'radio':

                # elif self.datatype[t] == 'bool':

                else:
                    raise AttributeError('Invalid type: {}'.format(self.datatype[t]))

            return self.values
        else:
            return {}

    def __del__(self):
        """InputDialog class destructor"""
        self.form.Dispose()

