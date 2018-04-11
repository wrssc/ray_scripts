""" Input Dialog GUI Widget

    The InputDialog() class constructor displays a form with input fields for the
    user to provide data to scripts. Multiple form inputs can be requested; the
    results are returned as a list. Optional input arguments also allow for custom
    input types (checkboxes, combo boxes), initial values, and required inputs. The
    results are returned as a dictionary with the same keys as defined in the text
    input argument. Note, the inputs are ordered vertically according to the SORTED
    keys, as dictionaries are stochastically referenced in this version of python.
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
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import clr


class InputDialog:

    def __getdatatype(self, t):
        """internal function to get data type"""
        if (t not in self.datatype and t not in self.options) or self.datatype[t] == 'text':
            return 'text'
        elif self.datatype[t] == 'check' and t in self.options:
            return 'check'
        elif self.datatype[t] == 'combo' and t in self.options:
            return 'combo'
        elif self.datatype[t] == 'radio' and t in self.options:
            return 'radio'
        elif self.datatype[t] == 'bool':
            return 'bool'
        else:
            return 'unknown'

    def __init__(self, text, title='Input Dialog', initial=None, datatype=None, options=None, required=None):
        """input = UserInterface.InputDialog('title', {'a':'Enter a value for a:'})"""

        # Initialize optional args
        if initial is None:
            initial = {}

        if datatype is None:
            datatype = {}

        if options is None:
            options = {}

        if required is None:
            required = []

        # Link .NET assemblies
        if initial is None:
            initial = {}
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize form
        self._form = System.Windows.Forms.Form()
        self._form.Width = 400
        self._form.Height = 55 * len(text) + 100
        self._form.Padding = System.Windows.Forms.Padding(0)
        self._form.Text = title
        self._form.AutoScroll = True
        self._form.BackColor = System.Drawing.Color.White
        self._table = System.Windows.Forms.TableLayoutPanel()
        self._table.ColumnCount = 1
        self._table.RowCount = 1
        self._table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self._table.Padding = System.Windows.Forms.Padding(0)
        self._table.BackColor = System.Drawing.Color.White
        self._table.AutoSize = True
        self._form.Controls.Add(self._table)

        # Store inputs and initialize variables
        self.datatype = datatype
        self.options = options
        self.required = required
        self._labels = {}
        self._inputs = {}
        self.values = {}

        # Add form inputs
        for t in sorted(text)

            # Label
            self._labels[t] = System.Windows.Forms.Label()
            self._labels[t].Text = text[t]
            self._labels[t].Width = 345
            self._labels[t].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self._table.Controls.Add(self._labels[t])

            # Textbox
            if self.__getdatatype(t) == 'text':
                self._inputs[t] = System.Windows.Forms.TextBox()
                self._inputs[t].Height = 30
                self._inputs[t].Width = 345
                if t in initial:
                    self._inputs[t].Text = initial[t]

                self._inputs[t].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self._table.Controls.Add(self._inputs[t])

            # Checkbox
            elif self.__getdatatype(t) == 'check':
                self._form.Height = self._form.Height + 20 * (len(options[t]) - 1)
                self._inputs[t] = {}
                for o in options[t]:
                    self._inputs[t][o] = System.Windows.Forms.CheckBox()
                    self._inputs[t][o].Text = o
                    self._inputs[t][o].Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
                    if t in initial and o in initial[t]:
                        self._inputs[t][o].Checked = True

                    self._table.Controls.Add(self._inputs[t][o])

            # Combobox/dropdown menu
            elif self.__getdatatype(t) == 'combo':
                self._inputs[t] = System.Windows.Forms.ComboBox()
                self._inputs[t].Height = 30
                self._inputs[t].Width = 345
                self._inputs[t].Items.AddRange(options[t])
                if t in initial and initial[t] in options[t]:
                    self._inputs[t].SelectedItem = initial[t]

                self._inputs[t].Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
                self._table.Controls.Add(self._inputs[t])

            # elif self.__getdatatype(t) == 'radio':

            # elif self.__getdatatype(t) == 'bool':

            else:
                raise AttributeError('Invalid type: {}'.format(datatype[t]))

        # Executes when OK is pressed
        def ok(_s, _e):

            # Check required inputs
            _failed = []
            for r in self.required:
                if self.__getdatatype(r) == 'text' and self._inputs[r].Text == '':
                    _failed.append(r)

                elif self.__getdatatype(r) == 'check':
                    n = 0
                    for x in self._inputs[r]:
                        if self._inputs[r][x].Checked:
                            n = n + 1

                    if n == 0:
                        _failed.append(r)

                elif self.__getdatatype(r) == 'combo' and self._inputs[r].SelectedIndex == -1:
                    _failed.append(r)

                # elif self.__getdatatype(t) == 'radio':

                # elif self.__getdatatype(t) == 'bool':

                else:
                    raise AttributeError('Invalid type: {}'.format(datatype[t]))

            # Continue if all required inputs exist
            if len(_failed) == 0:
                self._form.DialogResult = True
                self.status = True

            # Otherwise warn the user
            else:
                for f in _failed:
                    self._labels[f].ForeColor = System.Drawing.Color.Red

                System.Windows.Forms.MessageBox.Show('One or more required fields are missing', 'Required Fields',
                                                     System.Windows.Forms.MessageBoxButtons.OK,
                                                     System.Windows.Forms.MessageBoxIcon.Warning)
                self.status = False

        # Executes when cancel is pressed
        def cancel(_s, _e):
            self._form.DialogResult = True
            self.status = False

        # OK/Cancel buttons
        self._button_table = System.Windows.Forms.TableLayoutPanel()
        self._button_table.ColumnCount = 2
        self._button_table.RowCount = 1
        self._button_table.Padding = System.Windows.Forms.Padding(0)
        self._button_table.BackColor = System.Drawing.Color.White
        self._button_table.AutoSize = True
        self._button_table.Anchor = System.Windows.Forms.AnchorStyles.Right
        self._table.Controls.Add(self._button_table)

        self._ok = System.Windows.Forms.Button()
        self._ok.Text = 'OK'
        self._ok.Height = 30
        self._ok.Width = 50
        self._ok.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self._ok.BackColor = System.Drawing.Color.LightGray
        self._ok.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self._ok.Click += ok
        self._button_table.Controls.Add(self._ok)

        self._cancel = System.Windows.Forms.Button()
        self._cancel.Text = 'Cancel'
        self._cancel.Height = 30
        self._cancel.Width = 70
        self._cancel.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self._cancel.BackColor = System.Drawing.Color.LightGray
        self._cancel.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self._cancel.Click += cancel
        self._button_table.Controls.Add(self._cancel)

        self.status = False

    def show(self):
        """results = input.show()"""
        self._form.ShowDialog()

        if self.status:
            for t in self._inputs:
                if self.__getdatatype(t) == 'text':
                    self.values[t] = self._inputs[t].Text

                elif self.__getdatatype(t) == 'check':
                    self.values[t] = []
                    for o in self._inputs[t]:
                        if self._inputs[t][o].Checked:
                            self.values[t].append(o)

                elif self.__getdatatype(t) == 'combo':
                    self.values[t] = self._inputs[t].SelectedItem

                # elif self.__getdatatype(t) == 'radio':

                # elif self.__getdatatype(t) == 'bool':

                else:
                    raise AttributeError('Invalid type: {}'.format(self.datatype[t]))

            return self.values
        else:
            return {}

    def __del__(self):
        """InputDialog class destructor"""
        self._form.Dispose()

