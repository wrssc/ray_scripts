""" Treatment Planning Order Dialog Box

    This class displays a TPO input dialog to the user. See CreateTPO for more
    information. The following example illustrates how to use this function:

    import UserInterface
    tpo = UserInterface.TpoDialog()
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


class TpoDialog:

    def __init__(self, title='TPO Dialog'):
        """tpo = UserInterface.TPODialog(protocols)"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize internal variables
        self.protocols = {}
        self.status = True

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
        self.institution_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.institution_label)

        self.institution = System.Windows.Forms.ComboBox()
        self.institution.Height = 30
        self.institution.Width = self.form.MaximumSize.Width / 3 - 50
        self.institution.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.institution_label)

        self.tpo_label = System.Windows.Forms.Label()
        self.tpo_label.Text = 'Select TPO template:'
        self.tpo_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.tpo_label)

        self.tpo = System.Windows.Forms.ComboBox()
        self.tpo.Height = 30
        self.tpo.Width = self.form.MaximumSize.Width / 3 - 50
        self.tpo.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.tpo)

        self.location_label = System.Windows.Forms.Label()
        self.location_label.Text = 'Select target laterality (if applicable):'
        self.location_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.location_label)

        self.location = System.Windows.Forms.ComboBox()
        self.location.Height = 30
        self.location.Width = self.form.MaximumSize.Width / 3 - 50
        self.location.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.location)

        self.diagnosis_label = System.Windows.Forms.Label()
        self.diagnosis_label.Text = 'Enter diagnosis (or auto-fill from dropdown):'
        self.diagnosis_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis_label)

        self.diagnosis_autofill = System.Windows.Forms.ComboBox()
        self.diagnosis_autofill.Height = 30
        self.diagnosis_autofill.Width = self.form.MaximumSize.Width / 3 - 50
        self.diagnosis_autofill.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis_autofill)

        self.diagnosis = System.Windows.Forms.TextBox()
        self.diagnosis.Height = 90
        self.diagnosis.Width = self.form.MaximumSize.Width / 3 - 50
        self.diagnosis.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.diagnosis)

        self.options_label = System.Windows.Forms.Label()
        self.options_label.Text = 'Select other TPO options, as needed:'
        self.options_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.left.Controls.Add(self.options_label)

        self.previous_xrt = System.Windows.Forms.CheckBox()
        self.previous_xrt.Text = 'Previous radiation therapy'
        self.previous_xrt.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.previous_xrt)

        self.chemo = System.Windows.Forms.CheckBox()
        self.chemo.Text = 'Coordinate start with chemotherapy'
        self.chemo.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.chemo)

        self.pacemaker = System.Windows.Forms.CheckBox()
        self.pacemaker.Text = 'CEID/Pacemaker'
        self.pacemaker.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.pacemaker)

        self.weekly_qa = System.Windows.Forms.CheckBox()
        self.weekly_qa.Text = 'Weekly physics QA check'
        self.weekly_qa.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.weekly_qa.Checked = True
        self.left.Controls.Add(self.weekly_qa)

        self.verification = System.Windows.Forms.CheckBox()
        self.verification.Text = 'Verification simulation on first day of treatment'
        self.verification.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.verification.Checked = True
        self.left.Controls.Add(self.verification)

        self.accelerated = System.Windows.Forms.CheckBox()
        self.accelerated.Text = 'Accelerated planning requested'
        self.accelerated.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.left.Controls.Add(self.accelerated)

        # Add right panel placeholders
        self.right_table = System.Windows.Forms.TableLayoutPanel()
        self.right_table.ColumnCount = 2
        self.right_table.RowCount = 1
        self.right_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.right_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.right_table.BackColor = System.Drawing.Color.White
        self.right_table.AutoSize = True
        self.right.Controls.Add(self.right_table)

        self.fractions_label = System.Windows.Forms.Label()
        self.fractions_label.Text = 'Number of fractions:'
        self.fractions_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.fractions_label.Visible = False
        self.right_table.Controls.Add(self.fractions_label)

        self.fractions = System.Windows.Forms.TextBox()
        self.fractions.Height = 90
        self.fractions.Width = 100
        self.fractions.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.fractions.Visible = False
        self.right_table.Controls.Add(self.fractions)

        self.frequency_label = System.Windows.Forms.Label()
        self.frequency_label.Text = 'Treatment frequency:'
        self.frequency_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.frequency_label.Visible = False
        self.right_table.Controls.Add(self.frequency_label)

        self.frequency = System.Windows.Forms.ComboBox()
        self.frequency.Height = 30
        self.frequency.Width = 100
        self.frequency.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.frequency.Visible = False
        self.right_table.Controls.Add(self.frequency)

        self.modality_label = System.Windows.Forms.Label()
        self.modality_label.Text = 'Treatment modality:'
        self.modality_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.modality_label.Visible = False
        self.right_table.Controls.Add(self.modality_label)

        self.modality = System.Windows.Forms.ComboBox()
        self.modality.Height = 30
        self.modality.Width = 100
        self.modality.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.modality.Visible = False
        self.right_table.Controls.Add(self.modality)

        self.imaging_label = System.Windows.Forms.Label()
        self.imaging_label.Text = 'Image guidance:'
        self.imaging_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.imaging_label.Visible = False
        self.right_table.Controls.Add(self.imaging_label)

        self.imaging = System.Windows.Forms.ComboBox()
        self.imaging.Height = 30
        self.imaging.Width = 100
        self.imaging.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.imaging.Visible = False
        self.right_table.Controls.Add(self.imaging)

        self.motion_label = System.Windows.Forms.Label()
        self.motion_label.Text = 'Motion management:'
        self.motion_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.motion_label.Visible = False
        self.right_table.Controls.Add(self.motion_label)

        self.motion = System.Windows.Forms.ComboBox()
        self.motion.Height = 30
        self.motion.Width = 100
        self.motion.Margin = System.Windows.Forms.Padding(20, 0, 10, 0)
        self.motion.Visible = False
        self.right_table.Controls.Add(self.motion)

        # Initialize target table
        self.target_label = System.Windows.Forms.Label()
        self.target_label.Text = 'Select target structures:'
        self.target_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.target_label.Visible = False
        self.right.Controls.Add(self.target_label)

        self.target_table = System.Windows.Forms.TableLayoutPanel()
        self.target_table.ColumnCount = 3
        self.target_table.RowCount = 1
        self.target_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.target_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.target_table.BackColor = System.Drawing.Color.White
        self.target_table.AutoSize = True
        self.right.Controls.Add(self.target_table)

        self.target_name = System.Windows.Forms.Label()
        self.target_name.Text = 'Name'
        self.target_name.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.target_name.Visible = False
        self.target_table.Controls.Add(self.target_name)

        self.target_roi = System.Windows.Forms.Label()
        self.target_roi.Text = 'Structure'
        self.target_roi.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.target_roi.Visible = False
        self.target_table.Controls.Add(self.target_name)

        self.target_dose = System.Windows.Forms.Label()
        self.target_dose.Text = 'Dose'
        self.target_dose.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.target_dose.Visible = False
        self.target_table.Controls.Add(self.target_dose)

        # Initialize OAR table
        self.oar_label = System.Windows.Forms.Label()
        self.oar_label.Text = 'Select organ at risk structures:'
        self.oar_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.oar_label.Visible = False
        self.right.Controls.Add(self.oar_label)

        self.oar_table = System.Windows.Forms.TableLayoutPanel()
        self.oar_table.ColumnCount = 3
        self.oar_table.RowCount = 1
        self.oar_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.oar_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.oar_table.BackColor = System.Drawing.Color.White
        self.oar_table.AutoSize = True
        self.right.Controls.Add(self.oar_table)

        self.oar_name = System.Windows.Forms.Label()
        self.oar_name.Text = 'Name'
        self.oar_name.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.oar_name.Visible = False
        self.oar_table.Controls.Add(self.oar_name)

        self.oar_roi = System.Windows.Forms.Label()
        self.oar_roi.Text = 'Structure'
        self.oar_roi.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.oar_roi.Visible = False
        self.oar_table.Controls.Add(self.oar_roi)

        self.oar_dose = System.Windows.Forms.Label()
        self.oar_dose.Text = 'TPO Constraint'
        self.oar_dose.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.oar_dose.Visible = False
        self.oar_table.Controls.Add(self.oar_dose)

        # Add bottom panel inputs
        self.comments_label = System.Windows.Forms.Label()
        self.comments_label.Text = 'Comments (include description of previous radiation, justification for ' + \
                                   'accelerated planning, if applicable:'
        self.comments_label.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.comments_label.Visible = False
        self.bottom.Controls.Add(self.comments_label)

        self.button_table = System.Windows.Forms.TableLayoutPanel()
        self.button_table.ColumnCount = 1
        self.button_table.RowCount = 2
        self.button_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.button_table.BackColor = System.Drawing.Color.White
        self.button_table.AutoSize = True
        self.bottom.Controls.Add(self.button_table)

        def ok(_s, _e):
            self.form.DialogResult = True
            self.status = False

        def cancel(_s, _e):
            self.form.DialogResult = True
            self.status = False

        self.ok = System.Windows.Forms.Button()
        self.ok.Text = 'Continue'
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

        self.comments = System.Windows.Forms.TextBox()
        self.comments.Height = 200
        self.comments.Width = self.form.MaximumSize.Width / 3 - 50
        self.comments.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.bottom.Controls.Add(self.comments)




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

        # Populate institution list

        # Populate TPO template list

        # Populate diagnosis list

    #def select_tpo(self, tpo):

    #def select_institution(self, institution):

    #def select_diagnosis(self, diagnosis):



tpo = TpoDialog()
tpo.load_protocols(os.path.join(os.path.dirname(__file__), '../../protocols/'))

