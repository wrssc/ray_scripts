""" List Match Table GUI Widget

    The MatchDialog() class constructor displays a form allowing the user to match
    each item in a list of input strings to a list of options. The form will display a
    table with inputs in the left column and a dropdown list containing options in the
    right column. Initial values for each match can be provided via an initial dict.
    If not provided, the class will set the initial value to the item in options with
    the smallest Levenshtein distance. Exact matching and regular expressions are also
    supported, both for inputs or options. All matching is case-insensitive. The
    following examples illustrate how to use this function.

    import UserInterface
    dialog = UserInterface.MatchDialog(inputs=['bladder', 'rect', 'pros_MD'],
                                       options=['Bladder', 'Rectum', 'Prostate', 'External']
                                       text='Match the following list of template contours on the left to a ' +
                                            'corresponding user provided contour on the right:')

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
import re


class MatchDialog:

    def __init__(self, inputs, options, text='', title='Match Values', initial=None, form=None, method='Levenshtein',
                 regexp=None, threshold = 0.6):
        """dialog = UserInterface.MatchDialog(['a', 'b', 'c'], ['d', 'e', 'f'])"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize variables
        self.labels = {}
        self.inputs = {}
        self.values = {}
        self.options = options

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
        self.outer_table = System.Windows.Forms.TableLayoutPanel()
        self.outer_table.ColumnCount = 1
        self.outer_table.RowCount = 1
        self.outer_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.outer_table.Padding = System.Windows.Forms.Padding(0)
        self.outer_table.BackColor = System.Drawing.Color.White
        self.outer_table.AutoSize = True
        self.form.Controls.Add(self.outer_table)

        # Add intro text
        if text != '':

            self.intro = System.Windows.Forms.Label()
            self.intro.Text = text
            self.intro.AutoSize = True
            self.intro.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width - 50,
                                                         System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
            self.intro.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.outer_table.Controls.Add(self.intro)

        # Add list table
        self.list_table = System.Windows.Forms.TableLayoutPanel()
        self.list_table.ColumnCount = 2
        self.list_table.RowCount = len(inputs)
        self.list_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.list_table.Padding = System.Windows.Forms.Padding(0)
        self.list_table.BackColor = System.Drawing.Color.White
        self.list_table.AutoSize = True
        self.outer_table.Controls.Add(self.list_table)

        # Loop through inputs, listing each with a dropdown of options
        for i in inputs:

            self.labels[i] = System.Windows.Forms.Label()
            self.labels[i].Text = i
            self.labels[i].AutoSize = True
            self.labels[i].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.list_table.Controls.Add(self.labels[i])

            self.inputs[i] = System.Windows.Forms.ComboBox()
            self.inputs[i].Height = 30
            self.inputs[i].AutoSize = True
            self.inputs[i].Items.AddRange(self.options)

            if initial is not None and i in initial and initial[i] in options:
                self.inputs[i].SelectedItem = initial[i]

            elif method.lower() == 'exact':
                for o in self.options:
                    if i.lower() == o.lower():
                        self.inputs[i].SelectedItem = o
                        break

            elif method.lower() == 'levenshtein':
                m, d = _levenshtein_match(i, self.options)
                if m is not None and d < len(i) * threshold:
                    self.inputs[i].SelectedItem = m

            elif method.lower() == 'regexp':
                for o in self.options:
                    if o in regexp and re.search(regexp[o], i, flags=re.IGNORECASE) is not None:
                        self.inputs[i].SelectedItem = o
                        break

                    elif i in regexp and re.search(regexp[i], o, flags=re.IGNORECASE) is not None:
                        self.inputs[i].SelectedItem = o
                        break

            self.inputs[i].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            self.list_table.Controls.Add(self.inputs[i])

        # Executes when OK is pressed
        def ok(_s, _e):
            self.form.DialogResult = True
            self.status = True

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
        self.outer_table.Controls.Add(self.button_table)

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
        """matches = dialog.show()"""

        self.values = {}
        self.form.ShowDialog()

        # Retrieve values and return as a dict
        if self.status:
            for t in self.inputs:
                if self.inputs[t].SelectedIndex >= 0:
                    self.values[t] = self.inputs[t].SelectedItem.encode('ascii', 'ignore')

            return self.values
        else:
            return {}

    def __del__(self):
        """MatchDialog class destructor"""
        self.form.Dispose()


def _levenshtein_match(item, arr):
    """[match,dist]=_match(item,arr)"""

    # Initialize return args
    dist = max(len(item), min(map(len, arr)))
    match = None

    # Loop through array of options
    for a in arr:

        # Initialize index vectors
        v0 = range(len(a)+1) + [0]
        v1 = [0] * len(v0)

        for b in range(len(item)):
            v1[0] = b + 1

            for c in range(len(a)):

                # min(deletion, insertion, substitution)
                if item[b].lower() == a[c].lower():
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c])

                else:
                    v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c] + 1)

            v0, v1 = v1, v0

        if v0[len(a)] < dist:
            dist = v0[len(a)]
            match = a

    return match, dist
