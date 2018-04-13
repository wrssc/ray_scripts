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
    results = InputDialog({'a': 'Enter a value: ', 'b': 'Select checkboxes:', 'c': 'Select combobox option:'},
                          datatype={'b': 'check', 'c': 'combo'},
                          initial={'a': '5', 'b': ['1'], 'c': 'C'},
                          options={'b': ['1', '2'], 'c': ['A', 'B', 'C']},
                          required=['a', 'b', 'c'])
    print results.show()

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


class InputDialog:

    def __init__(self, inputs, title='Input Dialog', initial=None, datatype=None, options=None, required=None, form=None):
        """input = UserInterface.InputDialog({'a':'Enter a value for a:'})"""

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

            # Link .NET assemblies
            clr.AddReference('System.Windows.Forms')
            clr.AddReference('System.Drawing')
            import System

            self.__form = System.Windows.Forms.Form()
            self.__form.Width = 400
            self.__form.Height = min(55 * len(inputs) + 100, 800)
            self.__form.Padding = System.Windows.Forms.Padding(0)
            self.__form.Text = title
            self.__form.AutoScroll = True
            self.__form.BackColor = System.Drawing.Color.White
            self.__form.TopMost = True

        else:
            self.__form = form

        # Add table layout
        self.__table = System.Windows.Forms.TableLayoutPanel()
        self.__table.ColumnCount = 1
        self.__table.RowCount = 1
        self.__table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.__table.Padding = System.Windows.Forms.Padding(0)
        self.__table.BackColor = System.Drawing.Color.White
        self.__table.AutoSize = True
        self.__form.Controls.Add(self.__table)

        # Initialize variables
        self.__labels = {}
        self.__inputs = {}
        self.values = {}

        # Add form inputs
        for i in sorted(inputs):

            # Label
            self.__labels[i] = System.Windows.Forms.Label()
            self.__labels[i].Text = inputs[i]
            self.__labels[i].Width = 345
            self.__labels[i].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.__table.Controls.Add(self.__labels[i])

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
                self.__inputs[i] = System.Windows.Forms.TextBox()
                self.__inputs[i].Height = 30
                self.__inputs[i].Width = 345
                if i in initial:
                    self.__inputs[i].Text = initial[i]

                self.__inputs[i].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self.__table.Controls.Add(self.__inputs[i])

            # Checkbox
            elif self.datatype[i] == 'check':
                self.__form.Height = min(self.__form.Height + 20 * (len(options[i]) - 1), 800)
                self.__inputs[i] = {}
                for o in self.options[i]:
                    self.__inputs[i][o] = System.Windows.Forms.CheckBox()
                    self.__inputs[i][o].Text = o
                    self.__inputs[i][o].Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
                    if i in initial and o in initial[i]:
                        self.__inputs[i][o].Checked = True

                    self.__table.Controls.Add(self.__inputs[i][o])

            # Combobox/dropdown menu
            elif self.datatype[i] == 'combo':
                self.__inputs[i] = System.Windows.Forms.ComboBox()
                self.__inputs[i].Height = 30
                self.__inputs[i].Width = 345
                self.__inputs[i].Items.AddRange(options[i])
                if i in initial and initial[i] in options[i]:
                    self.__inputs[i].SelectedItem = initial[i]

                self.__inputs[i].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self.__table.Controls.Add(self.__inputs[i])

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
                if self.datatype[r] == 'text' and self.__inputs[r].Text == '':
                    failed.append(r)

                elif self.datatype[r] == 'check':
                    n = 0
                    for x in self.__inputs[r]:
                        if self.__inputs[r][x].Checked:
                            n += 1

                    if n == 0:
                        failed.append(r)

                elif self.datatype[r] == 'combo' and self.__inputs[r].SelectedIndex == -1:
                    failed.append(r)

                # elif self.datatype[t] == 'list':

                # elif self.datatype[t] == 'radio':

                # elif self.datatype[t] == 'bool':

                else:
                    raise AttributeError('Invalid type: {}'.format(self.datatype[i]))

            # Continue if all required inputs exist
            if len(failed) == 0:
                self.__form.DialogResult = True
                self.status = True

            # Otherwise warn the user
            else:
                for f in failed:
                    self.__labels[f].ForeColor = System.Drawing.Color.Red

                System.Windows.Forms.MessageBox.Show('One or more required fields are missing', 'Required Fields',
                                                     System.Windows.Forms.MessageBoxButtons.OK,
                                                     System.Windows.Forms.MessageBoxIcon.Warning)
                self.status = False

        # Executes when cancel is pressed
        def cancel(_s, _e):
            self.__form.DialogResult = True
            self.status = False

        # OK/Cancel buttons
        self.__button_table = System.Windows.Forms.TableLayoutPanel()
        self.__button_table.ColumnCount = 2
        self.__button_table.RowCount = 1
        self.__button_table.Padding = System.Windows.Forms.Padding(0)
        self.__button_table.BackColor = System.Drawing.Color.White
        self.__button_table.AutoSize = True
        self.__button_table.Anchor = System.Windows.Forms.AnchorStyles.Right
        self.__table.Controls.Add(self.__button_table)

        self.__ok = System.Windows.Forms.Button()
        self.__ok.Text = 'OK'
        self.__ok.Height = 30
        self.__ok.Width = 50
        self.__ok.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.__ok.BackColor = System.Drawing.Color.LightGray
        self.__ok.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.__ok.Click += ok
        self.__button_table.Controls.Add(self.__ok)

        self.__cancel = System.Windows.Forms.Button()
        self.__cancel.Text = 'Cancel'
        self.__cancel.Height = 30
        self.__cancel.Width = 70
        self.__cancel.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.__cancel.BackColor = System.Drawing.Color.LightGray
        self.__cancel.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.__cancel.Click += cancel
        self.__button_table.Controls.Add(self.__cancel)

        # self.status stores the overall state of this object; True means the user provided
        # data, false means they didn't (Cancel or closed form) or that required data is missing
        self.status = False

    def show(self):
        """results = input.show()"""
        self.__form.ShowDialog()

        # Retrieve values and return as a dict
        if self.status:
            for t in self.__inputs:
                if self.datatype[t] == 'text':
                    self.values[t] = self.__inputs[t].Text

                elif self.datatype[t] == 'check':
                    self.values[t] = []
                    for o in self.__inputs[t]:
                        if self.__inputs[t][o].Checked:
                            self.values[t].append(o)

                elif self.datatype[t] == 'combo':
                    self.values[t] = self.__inputs[t].SelectedItem

                # elif self.datatype[t] == 'radio':

                # elif self.datatype[t] == 'bool':

                else:
                    raise AttributeError('Invalid type: {}'.format(self.datatype[t]))

            return self.values
        else:
            return {}

    def __del__(self):
        """InputDialog class destructor"""
        self.__form.Dispose()

