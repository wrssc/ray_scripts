""" Treatment Planning Order Dialog Box

    This class displays a TPO input dialog to the user. See CreateTPO for more
    information. The following example illustrates how to use this function:

    import UserInterface
    tpo = UserInterface.TPODialog()
    tpo.load_protocols(os.path.join(os.path.dirname(__file__), '../../protocols/'))

    This program is free software: you can redistribute it and/or modify it under the
    terms of the GNU General Public License as published by the Free Software Foundation,
    either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT ANY
    WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
    PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with this
    program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Mark Geurts'
__contact__ = 'mark.w.geurts@gmail.com'
__version__ = '1.0.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Create-TPO'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import clr
import os
import xml.etree.ElementTree


class TPODialog:

    def __init__(self, title='TPO Dialog'):
        """tpo = UserInterface.TPODialog(protocols)"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize internal variables
        self.protocols = {}

        # Initialize form
        self.form = System.Windows.Forms.Form()
        self.form.AutoSize = True
        self.form.MaximumSize = System.Drawing.Size(800, System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
        self.form.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen
        self.form.Padding = System.Windows.Forms.Padding(0)
        self.form.Text = title
        self.form.AutoScroll = True
        self.form.BackColor = System.Drawing.Color.White
        self.form.TopMost = True

        # Add table layout
        self.table = System.Windows.Forms.TableLayoutPanel()
        self.table.ColumnCount = 1
        self.table.RowCount = 2
        self.table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.table.BackColor = System.Drawing.Color.White
        self.table.AutoSize = True
        self.form.Controls.Add(self.table)

        # Add columns
        self.columns = System.Windows.Forms.TableLayoutPanel()
        self.columns.ColumnCount = 2
        self.columns.RowCount = 1
        self.columns.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.columns.BackColor = System.Drawing.Color.White
        self.columns.AutoSize = True
        self.table.Controls.Add(self.columns)

        # Add left panel
        self.left = System.Windows.Forms.TableLayoutPanel()
        self.left.ColumnCount = 1
        self.left.RowCount = 1
        self.left.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.left.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.left.BackColor = System.Drawing.Color.White
        self.left.AutoSize = True
        self.columns.Controls.Add(self.left)

        # Add right panel
        self.right = System.Windows.Forms.TableLayoutPanel()
        self.right.ColumnCount = 1
        self.right.RowCount = 1
        self.right.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.right.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.right.BackColor = System.Drawing.Color.White
        self.right.AutoSize = True
        self.columns.Controls.Add(self.right)

        # Add bottom panel
        self.bottom = System.Windows.Forms.TableLayoutPanel()
        self.bottom.ColumnCount = 2
        self.bottom.RowCount = 1
        self.bottom.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.bottom.BackColor = System.Drawing.Color.White
        self.bottom.AutoSize = True
        self.table.Controls.Add(self.bottom)

        # Add left panel inputs
        self.institution_label = System.Windows.Forms.Label()
        self.institution_label.Text = 'Select institution:'
        self.institution_label.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width/2 - 50, 50)
        self.institution_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.institution_label)

        self.institution = System.Windows.Forms.ComboBox()
        self.institution.Height = 30
        self.institution.Width = self.form.MaximumSize.Width/2 - 50
        self.institution.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.institution_label)

        self.tpo_label = System.Windows.Forms.Label()
        self.tpo_label.Text = 'Select TPO template:'
        self.tpo_label.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width/2 - 50, 50)
        self.tpo_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.tpo_label)

        self.tpo = System.Windows.Forms.ComboBox()
        self.tpo.Height = 30
        self.tpo.Width = self.form.MaximumSize.Width / 2 - 50
        self.tpo.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.tpo)

        self.location_label = System.Windows.Forms.Label()
        self.location_label.Text = 'Select target laterality (if applicable):'
        self.location_label.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width / 2 - 50, 50)
        self.location_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.location_label)

        self.location = System.Windows.Forms.ComboBox()
        self.location.Height = 30
        self.location.Width = self.form.MaximumSize.Width / 2 - 50
        self.location.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.location)

        self.diagnosis_label = System.Windows.Forms.Label()
        self.diagnosis_label.Text = 'Enter diagnosis (or auto-fill from dropdown):'
        self.diagnosis_label.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width / 2 - 50, 50)
        self.diagnosis_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis_label)

        self.diagnosis_autofill = System.Windows.Forms.ComboBox()
        self.diagnosis_autofill.Height = 30
        self.diagnosis_autofill.Width = self.form.MaximumSize.Width / 2 - 50
        self.diagnosis_autofill.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis_autofill)

        self.diagnosis = System.Windows.Forms.TextBox()
        self.diagnosis.Height = 90
        self.diagnosis.Width = self.form.MaximumSize.Width - 50
        self.diagnosis.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis)

        self.diagnosis_label = System.Windows.Forms.Label()
        self.diagnosis_label.Text = 'Select TPO options:'
        self.diagnosis_label.MaximumSize = System.Drawing.Size(self.form.MaximumSize.Width / 2 - 50, 50)
        self.diagnosis_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis_label)



    def load_protocols(self, folder, overwrite=False):
        """tpo.load_protocols(folder)"""

        if overwrite:
            self.protocols = {}

        # Search protocol list, parsing each XML file for protocols
        for f in os.listdir(folder):
            if f.endswith('.xml'):
                tree = xml.etree.ElementTree.parse(os.path.join(folder, f))
                if tree.getroot().tag == 'protocol':
                    n = tree.findall('name')[0].text
                    if n in self.protocols:
                        self.protocols[n].extend(tree.getroot())
                    else:
                        self.protocols[n] = tree.getroot()


