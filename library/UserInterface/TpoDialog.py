""" Treatment Planning Order Dialog Box

    This class displays a TPO input dialog to the user. See CreateTPO for more
    information. The following example illustrates how to use this function:

    import connect
    import UserInterface
    tpo = UserInterface.TpoDialog()
    tpo.load_protocols(os.path.join(os.path.dirname(__file__), '../../protocols/'))
    tpo.show(connect.get_current('Case'), connect.get_current('Examination'))

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
import logging
import xml.etree.ElementTree

icd = '../../protocols/icd10cm_codes_2018.txt'


class TpoDialog:

    def __init__(self, title='TPO Dialog', match_threshold=0.6, num_rx=3):
        """tpo = UserInterface.TPODialog(protocols)"""

        # Link .NET assemblies
        clr.AddReference('System.Windows.Forms')
        clr.AddReference('System.Drawing')
        import System

        # Initialize internal variables
        self.protocols = {}
        self.status = False
        self.institution_list = []
        self.protocol_list = []
        self.order_list = []
        self.targets = {}
        self.oars = {}
        self.structures = []
        self.match_threshold = match_threshold
        self.num_rx = num_rx
        self.fraction_groups = 1
        self.values = {}
        self.suggested = '--------- above are suggested ---------'

        # Load CMS ICD file
        self.diagnosis_list = {}
        with open(os.path.join(os.path.dirname(__file__), icd), 'r') as f:
            for l in f:
                s = l.split(' ', 1)
                if len(s) == 2 and s[1] != '' and (s[0].startswith('C') or s[0].startswith('D')):
                    if len(s[0]) > 3:
                        self.diagnosis_list[s[0]] = '{}.{} {}'.format(s[0][0:3], s[0][3:], s[1])
                    else:
                        self.diagnosis_list[s[0]] = '{} {}'.format(s[0], s[1])

        # Initialize form
        self.form = System.Windows.Forms.Form()
        self.form.AutoSize = True
        self.form.MaximumSize = System.Drawing.Size(850, System.Windows.Forms.Screen.PrimaryScreen.WorkingArea.Bottom)
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
        self.bottom.RowCount = 2
        self.bottom.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.bottom.BackColor = System.Drawing.Color.White
        self.bottom.AutoSize = True
        self.table.Controls.Add(self.bottom)

        def update_left(s, e):

            # If an institution was changed
            if s.Name == 'institution':
                logging.debug('Institution set to {}'.format(s.SelectedItem))

            # Otherwise, if a protocol was changed
            elif s.Name == 'protocol' and s.SelectedItem in self.protocols:
                logging.debug('Protocol set to {}'.format(s.SelectedItem))

                # Update diagnosis list
                diagnoses = []
                for d in self.protocols[s.SelectedItem].findall('diagnoses/icd'):
                    if d.text in self.diagnosis_list.keys():
                        diagnoses.append(self.diagnosis_list[d.text])

                if len(diagnoses) > 0:
                    diagnoses = list(set(diagnoses))
                    diagnoses.sort()
                    if self.diagnosis.Items.Count > 0:
                        self.diagnosis.Items.Clear()

                    sorted_list = self.diagnosis_list.values()
                    sorted_list.sort()
                    self.diagnosis.Items.AddRange(diagnoses + [self.suggested] + sorted_list)
                    if len(diagnoses) == 1:
                        self.diagnosis.SelectedItem = diagnoses[0]

                # Update order list
                orders = []
                for o in self.protocols[s.SelectedItem].findall('order/name'):
                    orders.append(o.text)

                if len(orders) > 0:
                    orders = list(set(orders))
                    orders.sort()
                    if self.order.Items.Count > 0:
                        self.order.Items.Clear()

                    self.order.Items.AddRange(orders)
                    if len(orders) == 1:
                        self.order.SelectedItem = orders[0]

            # Otherwise, if an order was changed
            elif s.Name == 'order' and s.SelectedItem in self.order_list:
                logging.debug('Order set to {}'.format(s.SelectedItem))
                update_right(s, e)

        def update_right(_s, _e):
            if self.protocol.SelectedItem in self.protocols.keys() and self.order.SelectedItem in self.order_list:
                logging.debug('Updating order inputs based on order template')

                # Store protocol, order element trees
                protocol = self.protocols[self.protocol.SelectedItem]
                order = None
                for o in protocol.findall('order'):
                    if o.find('name').text == self.order.SelectedItem:
                        order = o
                        logging.debug('Matching protocol ElementTag found for {}'.format(self.order.SelectedItem))
                        break

                # Update fractionation
                self.form.SuspendLayout()
                self.right_table.Hide()
                self.prescription_label.Visible = True
                logging.debug('Updating fractionation value(s)')
                if order is not None and order.find('prescription/fractions') is not None:
                    self.fractions_label.Visible = True
                    c = 0
                    for p in order.findall('prescription'):
                        self.fractions[c].Visible = True
                        self.fractions[c].Text = p.find('fractions').text
                        c += 1

                    for n in range(c, self.num_rx):
                        self.fractions[n].Visible = False
                        self.fractions[n].SelectedItem = ''

                    self.right_table.ColumnCount = c + 1
                    self.fraction_groups = c + 1

                elif protocol.find('prescription/fractions') is not None:
                    self.fractions_label.Visible = True
                    c = 0
                    for p in protocol.findall('prescription'):
                        self.fractions[c].Visible = True
                        self.fractions[c].Text = p.find('fractions').text
                        c += 1

                    for n in range(c, self.num_rx):
                        self.fractions[n].Visible = False
                        self.fractions[n].SelectedItem = ''

                    self.right_table.ColumnCount = c + 1
                    self.fraction_groups = c + 1

                else:
                    self.fractions_label.Visible = False
                    self.fraction_groups = 0
                    for n in range(self.num_rx):
                        self.fractions[n].Visible = False
                        self.fractions[n].SelectedItem = ''

                # Update treatment frequency
                logging.debug('Updating treatment frequency list')
                if order is not None and order.find('prescription/frequency') is not None:
                    self.frequency_label.Visible = True
                    c = 0
                    for p in order.findall('prescription'):
                        self.frequency[c].Visible = True
                        frequency_list = []
                        for f in p.findall('frequency'):
                            frequency_list.append(f.text)
                            if 'default' in f.attrib and f.attrib['default'].lower() == 'true':
                                self.frequency[c].SelectedItem = f.text

                        frequency_list.sort()
                        if self.frequency[c].Items.Count > 0:
                            self.frequency[c].Items.Clear()

                        self.frequency[c].Items.AddRange(frequency_list)
                        if len(frequency_list) == 1:
                            self.frequency[c].SelectedItem = frequency_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.frequency[n].Visible = False
                        self.frequency[n].SelectedItem = ''

                elif protocol.find('prescription/frequency') is not None:
                    self.frequency_label.Visible = True
                    c = 0
                    for p in protocol.findall('prescription'):
                        self.frequency[c].Visible = True
                        frequency_list = []
                        for f in p.findall('frequency'):
                            frequency_list.append(f.text)
                            if 'default' in f.attrib and f.attrib['default'].lower() == 'true':
                                self.frequency[c].SelectedItem = f.text

                        frequency_list.sort()
                        if self.frequency[c].Items.Count > 0:
                            self.frequency[c].Items.Clear()

                        self.frequency[c].Items.AddRange(frequency_list)
                        if len(frequency_list) == 1:
                            self.frequency[c].SelectedItem = frequency_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.technique[n].Visible = False
                        self.technique[n].SelectedItem = ''

                else:
                    self.frequency_label.Visible = False
                    for n in range(self.num_rx):
                        self.frequency[n].Visible = False
                        self.frequency[n].SelectedItem = ''

                # Update treatment technique
                logging.debug('Updating treatment technique list')
                if order is not None and order.find('prescription/technique') is not None:
                    self.technique_label.Visible = True
                    c = 0
                    for p in order.findall('prescription'):
                        self.technique[c].Visible = True
                        technique_list = []
                        for t in p.findall('technique'):
                            technique_list.append(t.text)
                            if 'default' in t.attrib and t.attrib['default'].lower() == 'true':
                                self.technique[c].SelectedItem = t.text

                        technique_list.sort()
                        if self.technique[c].Items.Count > 0:
                            self.technique[c].Items.Clear()

                        self.technique[c].Items.AddRange(technique_list)
                        if len(technique_list) == 1:
                            self.technique[c].SelectedItem = technique_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.technique[n].Visible = False
                        self.technique[n].SelectedItem = ''

                elif protocol.find('prescription/technique') is not None:
                    self.technique_label.Visible = True
                    c = 0
                    for p in protocol.findall('prescription'):
                        self.technique[c].Visible = True
                        technique_list = []
                        for t in p.findall('technique'):
                            technique_list.append(t.text)
                            if 'default' in t.attrib and t.attrib['default'].lower() == 'true':
                                self.technique[c].SelectedItem = t.text

                        technique_list.sort()
                        if self.technique[c].Items.Count > 0:
                            self.technique[c].Items.Clear()

                        self.technique[c].Items.AddRange(technique_list)
                        if len(technique_list) == 1:
                            self.technique[c].SelectedItem = technique_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.technique[n].Visible = False
                        self.technique[n].SelectedItem = ''

                else:
                    self.technique_label.Visible = False
                    for n in range(self.num_rx):
                        self.technique[n].Visible = False
                        self.technique[n].SelectedItem = ''

                # Update imaging
                logging.debug('Updating imaging list')
                if order is not None and order.find('prescription/imaging') is not None:
                    self.imaging_label.Visible = True
                    c = 0
                    for p in order.findall('prescription'):
                        self.imaging[c].Visible = True
                        imaging_list = []
                        for i in p.findall('imaging'):
                            imaging_list.append(i.text)
                            if 'default' in i.attrib and i.attrib['default'].lower() == 'true':
                                self.imaging[c].SelectedItem = i.text

                        imaging_list.sort()
                        if self.imaging[c].Items.Count > 0:
                            self.imaging[c].Items.Clear()

                        self.imaging[c].Items.AddRange(imaging_list)
                        if len(imaging_list) == 1:
                            self.imaging[c].SelectedItem = imaging_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.imaging[n].Visible = False
                        self.imaging[n].SelectedItem = ''

                elif protocol.find('prescription/imaging') is not None:
                    self.imaging_label.Visible = True
                    c = 0
                    for p in protocol.findall('prescription'):
                        self.imaging[c].Visible = True
                        imaging_list = []
                        for i in p.findall('imaging'):
                            imaging_list.append(i.text)
                            if 'default' in i.attrib and i.attrib['default'].lower() == 'true':
                                self.imaging[c].SelectedItem = i.text

                        imaging_list.sort()
                        if self.imaging[c].Items.Count > 0:
                            self.imaging[c].Items.Clear()

                        self.imaging[c].Items.AddRange(imaging_list)
                        if len(imaging_list) == 1:
                            self.imaging[c].SelectedItem = imaging_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.imaging[n].Visible = False
                        self.imaging[n].SelectedItem = ''

                else:
                    self.imaging_label.Visible = False
                    for n in range(self.num_rx):
                        self.imaging[n].Visible = False
                        self.imaging[n].SelectedItem = ''

                # Update motion
                logging.debug('Updating motion list')
                if order is not None and order.find('prescription/motion') is not None:
                    self.motion_label.Visible = True
                    c = 0
                    for p in order.findall('prescription'):
                        self.motion[c].Visible = True
                        motion_list = []
                        for f in p.findall('motion'):
                            motion_list.append(f.text)
                            if 'default' in f.attrib and f.attrib['default'].lower() == 'true':
                                self.motion[c].SelectedItem = f.text

                        motion_list.sort()
                        if self.motion[c].Items.Count > 0:
                            self.motion[c].Items.Clear()

                        self.motion[c].Items.AddRange(motion_list)
                        if len(motion_list) == 1:
                            self.motion[c].SelectedItem = motion_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.motion[n].Visible = False
                        self.motion[n].SelectedItem = ''

                elif protocol.find('prescription/motion') is not None:
                    self.motion_label.Visible = True
                    c = 0
                    for p in protocol.findall('prescription'):
                        self.motion[c].Visible = True
                        motion_list = []
                        for f in p.findall('motion'):
                            motion_list.append(f.text)
                            if 'default' in f.attrib and f.attrib['default'].lower() == 'true':
                                self.motion[c].SelectedItem = f.text

                        motion_list.sort()
                        if self.motion[c].Items.Count > 0:
                            self.motion[c].Items.Clear()
                            
                        self.motion[c].Items.AddRange(motion_list)
                        if len(motion_list) == 1:
                            self.motion[c].SelectedItem = motion_list[0]

                        c += 1

                    for n in range(c, self.num_rx):
                        self.motion[n].Visible = False
                        self.motion[n].SelectedItem = ''

                else:
                    self.motion_label.Visible = False
                    for n in range(self.num_rx):
                        self.motion[n].Visible = False
                        self.motion[n].SelectedItem = ''

                # Update target dose table
                logging.debug('Updating target dose table')
                self.targets = {}
                for r in protocol.findall('prescription/roi'):
                    if r.find('name').text in self.targets:
                        self.targets[r.find('name').text]['element'].append(r)

                    else:
                        self.targets[r.find('name').text] = {'element': [r]}

                for r in order.findall('prescription/roi'):
                    if r.find('name').text in self.targets:
                        self.targets[r.find('name').text]['element'].append(r)

                    else:
                        self.targets[r.find('name').text] = {'element': [r]}

                if len(self.targets) > 0:
                    self.target_label.Visible = True
                    self.target_table.Controls.Clear()
                    self.target_table.RowStyles.Clear()

                    self.target_name = System.Windows.Forms.Label()
                    self.target_name.Text = 'Use'
                    self.target_name.AutoSize = True
                    self.target_name.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
                    self.target_table.Controls.Add(self.target_name)

                    self.target_roi = System.Windows.Forms.Label()
                    self.target_roi.Text = 'Structure'
                    self.target_roi.AutoSize = True
                    self.target_roi.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                    self.target_table.Controls.Add(self.target_roi)

                    self.target_dose = System.Windows.Forms.Label()
                    self.target_dose.Text = 'Dose (Gy)'
                    self.target_dose.AutoSize = True
                    self.target_dose.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                    self.target_table.Controls.Add(self.target_dose)

                    for t in sorted(self.targets.iterkeys()):
                        self.targets[t]['name'] = System.Windows.Forms.CheckBox()
                        self.targets[t]['name'].Checked = True
                        self.targets[t]['name'].Width = 150
                        self.targets[t]['name'].Text = t
                        self.targets[t]['name'].Margin = System.Windows.Forms.Padding(5, 8, 10, 0)
                        self.target_table.Controls.Add(self.targets[t]['name'])

                        self.targets[t]['structure'] = System.Windows.Forms.ComboBox()
                        self.targets[t]['structure'].Width = 150
                        self.targets[t]['structure'].Margin = System.Windows.Forms.Padding(10, 8, 10, 0)
                        self.targets[t]['structure'].Items.AddRange(self.structures)
                        self.target_table.Controls.Add(self.targets[t]['structure'])
                        m, d = self.__levenshtein_match(t, self.structures)
                        if m is not None and d < len(t) * self.match_threshold:
                            self.targets[t]['structure'].SelectedItem = m

                        self.targets[t]['dosetable'] = System.Windows.Forms.TableLayoutPanel()
                        self.targets[t]['dosetable'].ColumnCount = len(self.targets[t]['element'])
                        self.targets[t]['dosetable'].RowCount = 1
                        self.targets[t]['dosetable'].Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
                        self.targets[t]['dosetable'].BackColor = System.Drawing.Color.White
                        self.targets[t]['dosetable'].AutoSize = True
                        self.target_table.Controls.Add(self.targets[t]['dosetable'])

                        self.targets[t]['dose'] = []
                        for n in range(len(self.targets[t]['element'])):
                            self.targets[t]['dose'].append(System.Windows.Forms.TextBox())
                            self.targets[t]['dose'][n].Text = self.targets[t]['element'][n].find('dose').text
                            self.targets[t]['dose'][n].AccessibleDescription = \
                                self.targets[t]['element'][n].find('volume').text
                            self.targets[t]['dose'][n].Width = 50
                            self.targets[t]['dose'][n].Margin = System.Windows.Forms.Padding(10, 5, 10, 0)
                            self.targets[t]['dosetable'].Controls.Add(self.targets[t]['dose'][n])

                else:
                    self.target_label.Visible = False
                    self.target_table.Controls.Clear()
                    self.target_table.RowStyles.Clear()

                # Update OAR constraint table
                logging.debug('Updating OAR table')
                self.oars = {}
                for r in protocol.findall('goals/roi'):
                    if r.find('name').text not in self.targets:
                        if r.find('name').text in self.oars:
                            self.oars[r.find('name').text]['element'].append(r)

                        else:
                            self.oars[r.find('name').text] = {'element': [r]}

                for r in order.findall('goals/roi'):
                    if r.find('name').text not in self.targets:
                        if r.find('name').text in self.oars:
                            self.oars[r.find('name').text]['element'].append(r)

                        else:
                            self.oars[r.find('name').text] = {'element': [r]}

                if len(self.oars) > 0:
                    self.oar_label.Visible = True
                    self.oar_table.Controls.Clear()
                    self.oar_table.RowStyles.Clear()

                    self.oar_name = System.Windows.Forms.Label()
                    self.oar_name.Text = 'Use'
                    self.oar_name.AutoSize = True
                    self.oar_name.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
                    self.oar_table.Controls.Add(self.oar_name)

                    self.oar_name = System.Windows.Forms.Label()
                    self.oar_name.Text = 'Structure'
                    self.oar_name.AutoSize = True
                    self.oar_name.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                    self.oar_table.Controls.Add(self.oar_name)

                    self.oar_goal = System.Windows.Forms.Label()
                    self.oar_goal.Text = 'Goal'
                    self.oar_goal.AutoSize = True
                    self.oar_goal.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                    self.oar_table.Controls.Add(self.oar_goal)

                    for o in sorted(self.oars.iterkeys()):
                        self.oars[o]['name'] = System.Windows.Forms.CheckBox()
                        self.oars[o]['name'].Checked = True
                        self.oars[o]['name'].Width = 150
                        self.oars[o]['name'].Text = o
                        self.oars[o]['name'].Margin = System.Windows.Forms.Padding(5, 8, 10, 0)
                        self.oar_table.Controls.Add(self.oars[o]['name'])

                        self.oars[o]['structure'] = System.Windows.Forms.ComboBox()
                        self.oars[o]['structure'].Width = 150
                        self.oars[o]['structure'].Margin = System.Windows.Forms.Padding(10, 8, 10, 0)
                        self.oars[o]['structure'].Items.AddRange(self.structures)
                        self.oar_table.Controls.Add(self.oars[o]['structure'])
                        m, d = self.__levenshtein_match(o, self.structures)
                        if m is not None and d < len(o) * self.match_threshold:
                            self.oars[o]['structure'].SelectedItem = m

                        goals = []
                        for g in self.oars[o]['element']:
                            left = ''
                            symbol = ''
                            right = ''
                            if g.find('type').text == 'DX':
                                left = 'D{}{}'.format(g.find('volume').text, g.find('volume').attrib['units'])
                                if 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'le':
                                    symbol = '<='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'lt':
                                    symbol = '<'

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'ge':
                                    symbol = '>='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'gt':
                                    symbol = '>'

                                if 'units' in g.find('dose').attrib and g.find('dose').attrib['units'] == '%':
                                    right = '{}%'.format(g.find('dose').text)

                                else:
                                    right = '{} Gy'.format(g.find('dose').text)

                            elif g.find('type').text == 'VX':
                                left = 'V{}'.format(g.find('dose').text)
                                if 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'le':
                                    symbol = '<='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'lt':
                                    symbol = '<'

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'ge':
                                    symbol = '>='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'gt':
                                    symbol = '>'

                                right = '{}{}'.format(g.find('volume').text, g.find('volume').attrib['units'])

                            elif g.find('type').text == 'Max':
                                left = 'Max'
                                if 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'le':
                                    symbol = '<='

                                else:
                                    symbol = '<'

                                if 'units' in g.find('dose').attrib and g.find('dose').attrib['units'] == '%':
                                    right = '{}%'.format(g.find('dose').text)

                                else:
                                    right = '{} Gy'.format(g.find('dose').text)

                            elif g.find('type').text == 'Min':
                                left = 'Min'
                                if 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'ge':
                                    symbol = '>='

                                else:
                                    symbol = '>'

                                if 'units' in g.find('dose').attrib and g.find('dose').attrib['units'] == '%':
                                    right = '{}%'.format(g.find('dose').text)

                                else:
                                    right = '{} Gy'.format(g.find('dose').text)

                            elif g.find('type').text == 'Mean':
                                left = 'Mean'
                                if 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'le':
                                    symbol = '<='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'lt':
                                    symbol = '<'

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'ge':
                                    symbol = '>='

                                elif 'dir' in g.find('type').attrib and g.find('type').attrib['dir'] == 'gt':
                                    symbol = '>'

                                if 'units' in g.find('dose').attrib and g.find('dose').attrib['units'] == '%':
                                    right = '{}%'.format(g.find('dose').text)

                                else:
                                    right = '{} Gy'.format(g.find('dose').text)

                            if left != '':
                                goals.append('{} {} {}'.format(left, symbol, right))

                        self.oars[o]['goal'] = System.Windows.Forms.Label()
                        self.oars[o]['goal'].Text = '\n'.join(goals)
                        self.oars[o]['goal'].AutoSize = True
                        self.oars[o]['goal'].Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
                        self.oar_table.Controls.Add(self.oars[o]['goal'])

                else:
                    self.oar_table.Visible = False
                    self.oar_table.Controls.Clear()
                    self.oar_table.RowStyles.Clear()

                self.form.ResumeLayout()
                self.right_table.Show()

            else:
                self.prescription_label.Visible = False
                self.fractions_label.Visible = False
                self.fractions.Visible = False
                self.frequency_label.Visible = False
                self.frequency.Visible = False
                self.technique_label.Visible = False
                self.technique.Visible = False
                self.imaging_label.Visible = False
                self.imaging.Visible = False
                self.motion_label.Visible = False
                self.motion.Visible = False
                self.target_label.Visible = False
                self.target_table.Controls.Clear()
                self.target_table.RowStyles.Clear()

        # Add left panel inputs
        self.institution_label = System.Windows.Forms.Label()
        self.institution_label.Text = 'Select institution:'
        self.institution_label.AutoSize = True
        self.institution_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.institution_label)

        self.institution = System.Windows.Forms.ComboBox()
        self.institution.Name = 'institution'
        self.institution.Width = self.form.MaximumSize.Width / 3 - 50
        self.institution.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.institution.SelectedIndexChanged += update_left
        self.left.Controls.Add(self.institution)

        self.protocol_label = System.Windows.Forms.Label()
        self.protocol_label.Text = 'Select protocol:'
        self.protocol_label.AutoSize = True
        self.protocol_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.protocol_label)

        self.protocol = System.Windows.Forms.ComboBox()
        self.protocol.Name = 'protocol'
        self.protocol.Width = self.form.MaximumSize.Width / 3 - 50
        self.protocol.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.protocol.SelectedIndexChanged += update_left
        self.left.Controls.Add(self.protocol)

        self.order_label = System.Windows.Forms.Label()
        self.order_label.Text = 'Select planning order:'
        self.order_label.AutoSize = True
        self.order_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.order_label)

        self.order = System.Windows.Forms.ComboBox()
        self.order.Name = 'order'
        self.order.Width = self.form.MaximumSize.Width / 3 - 50
        self.order.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.order.SelectedIndexChanged += update_left
        self.left.Controls.Add(self.order)

        self.diagnosis_label = System.Windows.Forms.Label()
        self.diagnosis_label.Text = 'Select diagnosis:'
        self.diagnosis_label.AutoSize = True
        self.diagnosis_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.diagnosis_label)

        self.diagnosis = System.Windows.Forms.ComboBox()
        self.diagnosis.Width = self.form.MaximumSize.Width / 3 - 50
        self.diagnosis.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        sorted_diagnoses = self.diagnosis_list.values()
        sorted_diagnoses.sort()
        self.diagnosis.Items.AddRange(sorted_diagnoses)
        self.left.Controls.Add(self.diagnosis)

        self.options_label = System.Windows.Forms.Label()
        self.options_label.Text = 'Select other TPO options, as needed:'
        self.options_label.AutoSize = True
        self.options_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.options_label)

        self.previous_xrt = System.Windows.Forms.CheckBox()
        self.previous_xrt.Text = 'Previous radiation therapy'
        self.previous_xrt.AutoSize = True
        self.previous_xrt.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.previous_xrt)

        self.chemo = System.Windows.Forms.CheckBox()
        self.chemo.Text = 'Coordinate start with chemotherapy'
        self.chemo.AutoSize = True
        self.chemo.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.chemo)

        self.pacemaker = System.Windows.Forms.CheckBox()
        self.pacemaker.Text = 'CEID/Pacemaker'
        self.pacemaker.AutoSize = True
        self.pacemaker.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.pacemaker)

        self.weekly_qa = System.Windows.Forms.CheckBox()
        self.weekly_qa.Text = 'Weekly physics QA check'
        self.weekly_qa.AutoSize = True
        self.weekly_qa.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.weekly_qa.Checked = True
        self.weekly_qa.Visible = False
        self.left.Controls.Add(self.weekly_qa)

        self.verification = System.Windows.Forms.CheckBox()
        self.verification.Text = 'Verification simulation on first day of treatment'
        self.verification.AutoSize = True
        self.verification.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.verification.Checked = True
        self.verification.Visible = False
        self.left.Controls.Add(self.verification)

        self.accelerated = System.Windows.Forms.CheckBox()
        self.accelerated.Text = 'Accelerated planning requested'
        self.accelerated.AutoSize = True
        self.accelerated.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.left.Controls.Add(self.accelerated)

        # Add right panel placeholders
        self.prescription_label = System.Windows.Forms.Label()
        self.prescription_label.Text = 'Prescription Details'
        self.prescription_label.AutoSize = True
        self.prescription_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.prescription_label.Font = System.Drawing.Font(self.prescription_label.Font,
                                                           self.prescription_label.Font.Style |
                                                           System.Drawing.FontStyle.Bold)
        self.prescription_label.Visible = False
        self.right.Controls.Add(self.prescription_label)

        self.right_table = System.Windows.Forms.TableLayoutPanel()
        self.right_table.ColumnCount = 1 + self.num_rx
        self.right_table.RowCount = 5
        self.right_table.GrowStyle = System.Windows.Forms.TableLayoutPanelGrowStyle.AddRows
        self.right_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.right_table.BackColor = System.Drawing.Color.White
        self.right_table.AutoSize = True
        self.right.Controls.Add(self.right_table)

        self.fractions_label = System.Windows.Forms.Label()
        self.fractions_label.Text = 'Number of fractions:'
        self.fractions_label.Width = 180
        self.fractions_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.fractions_label.Visible = False
        self.right_table.Controls.Add(self.fractions_label)

        self.fractions = []
        for n in range(self.num_rx):
            self.fractions.append(System.Windows.Forms.TextBox())
            self.fractions[n].Width = 50
            self.fractions[n].Margin = System.Windows.Forms.Padding(0, 8, 10, 0)
            self.fractions[n].Visible = False
            self.right_table.Controls.Add(self.fractions[n])

        self.frequency_label = System.Windows.Forms.Label()
        self.frequency_label.Text = 'Treatment frequency:'
        self.frequency_label.AutoSize = True
        self.frequency_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.frequency_label.Visible = False
        self.right_table.Controls.Add(self.frequency_label)

        self.frequency = []
        for n in range(self.num_rx):
            self.frequency.append(System.Windows.Forms.ComboBox())
            self.frequency[n].Width = 150
            self.frequency[n].Margin = System.Windows.Forms.Padding(0, 8, 10, 0)
            self.frequency[n].Visible = False
            self.right_table.Controls.Add(self.frequency[n])

        self.technique_label = System.Windows.Forms.Label()
        self.technique_label.Text = 'Treatment technique:'
        self.technique_label.AutoSize = True
        self.technique_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.technique_label.Visible = False
        self.right_table.Controls.Add(self.technique_label)

        self.technique = []
        for n in range(self.num_rx):
            self.technique.append(System.Windows.Forms.ComboBox())
            self.technique[n].Width = 150
            self.technique[n].Margin = System.Windows.Forms.Padding(0, 8, 10, 0)
            self.technique[n].Visible = False
            self.right_table.Controls.Add(self.technique[n])

        self.imaging_label = System.Windows.Forms.Label()
        self.imaging_label.Text = 'Image guidance:'
        self.imaging_label.AutoSize = True
        self.imaging_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.imaging_label.Visible = False
        self.right_table.Controls.Add(self.imaging_label)

        self.imaging = []
        for n in range(self.num_rx):
            self.imaging.append(System.Windows.Forms.ComboBox())
            self.imaging[n].Width = 150
            self.imaging[n].Margin = System.Windows.Forms.Padding(0, 8, 10, 0)
            self.imaging[n].Visible = False
            self.right_table.Controls.Add(self.imaging[n])

        self.motion_label = System.Windows.Forms.Label()
        self.motion_label.Text = 'Motion management:'
        self.motion_label.AutoSize = True
        self.motion_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.motion_label.Visible = False
        self.right_table.Controls.Add(self.motion_label)

        self.motion = []
        for n in range(self.num_rx):
            self.motion.append(System.Windows.Forms.ComboBox())
            self.motion[n].Width = 150
            self.motion[n].Margin = System.Windows.Forms.Padding(0, 8, 10, 0)
            self.motion[n].Visible = False
            self.right_table.Controls.Add(self.motion[n])

        # Initialize target table
        self.target_label = System.Windows.Forms.Label()
        self.target_label.Text = 'Target Dose Levels'
        self.target_label.AutoSize = True
        self.target_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.target_label.Font = System.Drawing.Font(self.target_label.Font,
                                                     self.target_label.Font.Style | System.Drawing.FontStyle.Bold)
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

        # Initialize OAR table
        self.oar_label = System.Windows.Forms.Label()
        self.oar_label.Text = 'Organ at Risk Goals'
        self.oar_label.AutoSize = True
        self.oar_label.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.oar_label.Font = System.Drawing.Font(self.oar_label.Font,
                                                  self.oar_label.Font.Style | System.Drawing.FontStyle.Bold)
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

        # Add bottom panel inputs
        self.comments_label = System.Windows.Forms.Label()
        self.comments_label.Text = 'Comments: (include description of previous radiation, justification for ' + \
                                   'accelerated planning, if applicable)'
        self.comments_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.comments_label.AutoSize = True
        self.bottom.Controls.Add(self.comments_label)

        self.button_label = System.Windows.Forms.Label()
        self.button_label.Text = ''
        self.button_label.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        self.bottom.Controls.Add(self.button_label)

        self.comments = System.Windows.Forms.TextBox()
        self.comments.Height = 100
        self.comments.Width = self.form.MaximumSize.Width - 200
        self.comments.Multiline = True
        self.comments.Margin = System.Windows.Forms.Padding(10, 0, 10, 0)
        self.bottom.Controls.Add(self.comments)

        self.button_table = System.Windows.Forms.TableLayoutPanel()
        self.button_table.ColumnCount = 1
        self.button_table.RowCount = 2
        self.button_table.Padding = System.Windows.Forms.Padding(0, 0, 0, 0)
        self.button_table.BackColor = System.Drawing.Color.White
        self.button_table.AutoSize = True
        self.bottom.Controls.Add(self.button_table)

        def ok(_s, _e):

            # Verify dropdown inputs are provided
            missing = []
            if self.institution.SelectedItem == '' or self.institution.SelectedItem is None:
                missing.append('institution')
                self.institution_label.ForeColor = System.Drawing.Color.Red

            else:
                self.institution_label.ForeColor = System.Drawing.Color.Black

            if self.protocol.SelectedItem == '' or self.protocol.SelectedItem is None:
                missing.append('protocol')
                self.protocol_label.ForeColor = System.Drawing.Color.Red

            else:
                self.protocol_label.ForeColor = System.Drawing.Color.Black

            if self.order.SelectedItem == '' or self.order.SelectedItem is None:
                missing.append('planning order')
                self.order_label.ForeColor = System.Drawing.Color.Red

            else:
                self.order_label.ForeColor = System.Drawing.Color.Black

            if self.diagnosis.SelectedItem == '' or self.diagnosis.SelectedItem is None:
                missing.append('diagnosis')
                self.diagnosis_label.ForeColor = System.Drawing.Color.Red

            else:
                self.diagnosis_label.ForeColor = System.Drawing.Color.Black

            for n in range(self.fraction_groups):
                if self.fractions[n].Visible and self.fractions[n].Text == '':
                    missing.append('fractions')
                    self.fractions_label.ForeColor = System.Drawing.Color.Red

                else:
                    self.fractions_label.ForeColor = System.Drawing.Color.Black

                if self.frequency[n].Visible and (self.frequency[n].SelectedItem == '' or
                                                  self.frequency[n].SelectedItem is None):
                    missing.append('frequency')
                    self.frequency_label.ForeColor = System.Drawing.Color.Red

                else:
                    self.frequency_label.ForeColor = System.Drawing.Color.Black

                if self.technique[n].Visible and (self.technique[n].SelectedItem == '' or
                                                 self.technique[n].SelectedItem is None):
                    missing.append('technique')
                    self.technique_label.ForeColor = System.Drawing.Color.Red

                else:
                    self.technique_label.ForeColor = System.Drawing.Color.Black

                if self.imaging[n].Visible and (self.imaging[n].SelectedItem == '' or
                                                self.imaging[n].SelectedItem is None):
                    missing.append('imaging')
                    self.imaging_label.ForeColor = System.Drawing.Color.Red

                else:
                    self.imaging_label.ForeColor = System.Drawing.Color.Black

                if self.motion[n].Visible and (self.motion[n].SelectedItem == '' or
                                               self.motion[n].SelectedItem is None):
                    missing.append('frequency')
                    self.motion_label.ForeColor = System.Drawing.Color.Red

                else:
                    self.motion_label.ForeColor = System.Drawing.Color.Black

            if len(missing) > 0:
                missing = list(set(missing))
                self.status = False
                System.Windows.Forms.MessageBox.Show('The following inputs are required: ' + ', '.join(missing),
                                                     'Required Fields',
                                                     System.Windows.Forms.MessageBoxButtons.OK,
                                                     System.Windows.Forms.MessageBoxIcon.Warning)

            # Otherwise, verify structures are specified
            else:
                missing = []
                for t in self.targets.values():
                    if t['name'].Checked and (t['structure'].SelectedItem == '' or t['structure'].SelectedItem is None):
                        missing.append(t['name'].Text)
                        t['name'].ForeColor = System.Drawing.Color.Red

                    else:
                        t['name'].ForeColor = System.Drawing.Color.Black

                for o in self.oars.values():
                    if o['name'].Checked and (o['structure'].SelectedItem == '' or o['structure'].SelectedItem is None):
                        missing.append(o['name'].Text)
                        o['name'].ForeColor = System.Drawing.Color.Red

                    else:
                        o['name'].ForeColor = System.Drawing.Color.Black

                if len(missing) > 0:
                    self.status = False
                    System.Windows.Forms.MessageBox.Show('The following targets or OARs are not matched to existing ' +
                                                         'structures: ' + ', '.join(missing) + '. Either match them ' +
                                                         'or uncheck the structures to not constrain them during ' +
                                                         'planning.', 'Unmatched Structures',
                                                         System.Windows.Forms.MessageBoxButtons.OK,
                                                         System.Windows.Forms.MessageBoxIcon.Warning)

                else:
                    self.status = True
                    self.form.DialogResult = True

        def cancel(_s, _e):
            self.form.DialogResult = True
            self.status = False

        self.ok = System.Windows.Forms.Button()
        self.ok.Text = 'Continue'
        self.ok.Height = 30
        self.ok.Width = 90
        self.ok.Margin = System.Windows.Forms.Padding(0, 0, 10, 0)
        self.ok.BackColor = System.Drawing.Color.LightGray
        self.ok.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.ok.Click += ok
        self.button_table.Controls.Add(self.ok)

        self.cancel = System.Windows.Forms.Button()
        self.cancel.Text = 'Cancel'
        self.cancel.Height = 30
        self.cancel.Width = 90
        self.cancel.Margin = System.Windows.Forms.Padding(0, 10, 10, 0)
        self.cancel.BackColor = System.Drawing.Color.LightGray
        self.cancel.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        self.cancel.Click += cancel
        self.button_table.Controls.Add(self.cancel)

    def show(self, case=None, exam=None):
        """results = tpo.show()"""

        # Attempt to match institution, TPO based on exam protocol
        institutions = []
        protocols = []
        if exam is not None:
            for key, value in self.protocols.items():
                for c in value.findall('ct/protocol'):
                    if c.text == exam.GetProtocolName():
                        protocols.append(key)
                        if 'institution' in c.attrib:
                            institutions.append(c.attrib['institution'])

            institutions = list(set(institutions))
            institutions.sort()
            protocols = list(set(protocols))
            protocols.sort()
            if len(institutions) > 0:
                if self.institution.Items.Count > 0:
                    self.institution.Items.Clear()

                self.institution.Items.AddRange(institutions + [self.suggested] + self.institution_list)
                if len(institutions) == 1:
                    self.institution.SelectedItem = institutions[0]

            if len(protocols) > 0:
                if self.protocol.Items.Count > 0:
                    self.protocol.Items.Clear()

                self.protocol.Items.AddRange(protocols + [self.suggested] + self.protocol_list)
                if len(protocols) == 1:
                    self.protocol.SelectedItem = protocols[0]

        # Attempt to match order based on structure set
        if case is not None:
            self.structures = []
            for r in case.PatientModel.RegionsOfInterest:
                self.structures.append(r.Name)

            #
            # TODO: attempt to match structure set to order
            #

        # Display form
        self.form.ShowDialog()

        # Parse responses
        if self.status:
            self.values['institution'] = self.institution.SelectedItem
            self.values['protocol'] = self.protocol.SelectedItem
            self.values['order'] = self.order.SelectedItem
            self.values['diagnosis'] = self.diagnosis.SelectedItem.split(' ', 1)
            self.values['options'] = {}
            self.values['options'][self.previous_xrt.Text] = self.previous_xrt.Checked
            self.values['options'][self.chemo.Text] = self.chemo.Checked
            self.values['options'][self.pacemaker.Text] = self.pacemaker.Checked
            self.values['options'][self.weekly_qa.Text] = self.weekly_qa.Checked
            self.values['options'][self.verification.Text] = self.verification.Checked
            self.values['options'][self.accelerated.Text] = self.accelerated.Checked
            self.values['options'][self.previous_xrt.Text] = self.previous_xrt.Checked
            self.values['comments'] = self.comments.Text
            self.values['fractions'] = []
            self.values['frequency'] = []
            self.values['technique'] = []
            self.values['imaging'] = []
            self.values['motion'] = []
            for n in range(self.fraction_groups):
                try:
                    self.values['fractions'].append(int(self.fractions[n].Text))
                    self.values['frequency'].append(self.frequency[n].SelectedItem)
                    self.values['technique'].append(self.technique[n].SelectedItem)
                    self.values['imaging'].append(self.imaging[n].SelectedItem)
                    self.values['motion'].append(self.motion[n].SelectedItem)

                except ValueError:
                    logging.debug('Ignored fraction group {} as fraction value {} is invalid'.
                                  format(n, self.fractions[n].Text))

            self.values['structures'] = {}
            self.values['xml'] = self.protocols[self.protocol.SelectedItem]
            self.values['targets'] = {}
            for t in self.targets.values():
                self.values['targets'][t['name'].Text] = {'use': t['name'].Checked,
                                                          'structure': t['structure'].SelectedItem,
                                                          'volume': [],
                                                          'dose': []}
                for n in range(len(t['element'])):
                    self.values['targets'][t['name'].Text]['dose'].append(float(t['dose'][n].Text))
                    if t['dose'][n].AccessibleDescription != '':
                        self.values['targets'][t['name'].Text]['volume'].append(
                            float(t['dose'][n].AccessibleDescription))

                    else:
                        self.values['targets'][t['name'].Text]['volume'].append(95)

                if t['structure'].SelectedItem != '':
                    self.values['structures'][t['structure'].SelectedItem] = t['name'].Text

            self.values['oars'] = {}
            for o in self.oars.values():
                self.values['oars'][o['name'].Text] = {'use': o['name'].Checked,
                                                       'structure': o['structure'].SelectedItem}

                if o['structure'].SelectedItem != '':
                    self.values['structures'][o['structure'].SelectedItem] = o['name'].Text

            return self.values

        else:
            return {}

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
        self.institution_list = []
        for p in self.protocols.values():
            for i in p.findall('institutions/institution'):
                self.institution_list.append(i.text)

        if len(self.institution_list) > 0:
            self.institution_list = list(set(self.institution_list))
            self.institution_list.sort()
            if self.institution.Items.Count > 0:
                self.institution.Items.Clear()

            self.institution.Items.AddRange(self.institution_list)

        # Populate protocol list
        self.protocol_list = self.protocols.keys()
        if len(self.protocol_list) > 0:
            self.protocol_list.sort()
            if self.protocol.Items.Count > 0:
                self.protocol.Items.Clear()

            self.protocol.Items.AddRange(self.protocol_list)

        # Populate order list
        self.order_list = []
        for p in self.protocols.values():
            for o in p.findall('order/name'):
                self.order_list.append(o.text)

        if len(self.order_list) > 0:
            self.order_list = list(set(self.order_list))
            self.order_list.sort()
            if self.order.Items.Count > 0:
                self.order.Items.Clear()

            self.order.Items.AddRange(self.order_list)

    def select_protocol(self, protocol):
        """tpo.select_protocol('Protocol Name')"""
        if protocol in self.protocol_list:
            self.protocol.SelectedItem = protocol

    def select_order(self, order):
        """tpo.select_order('Order Name')"""
        if order in self.order_list:
            self.order.SelectedItem = order

    def __levenshtein_match(self, item, arr):
        """[match,dist]=__levenshtein_match(item,arr)"""

        # Initialize return args
        dist = max(len(item), min(map(len, arr)))
        match = None

        # Loop through array of options
        for a in arr:
            v0 = range(len(a) + 1) + [0]
            v1 = [0] * len(v0)
            for b in range(len(item)):
                v1[0] = b + 1
                for c in range(len(a)):
                    if item[b].lower() == a[c].lower():
                        v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c])

                    else:
                        v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c] + 1)

                v0, v1 = v1, v0

            if v0[len(a)] < dist:
                dist = v0[len(a)]
                match = a

        return match, dist
