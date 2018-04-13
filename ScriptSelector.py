""" Script Selector
    
    This script downloads a copy of the ray_scripts GitHub repository, then displays a 
    list to the user of each script present in the specified sub-folder. This script will
    then execute the script that the user selects. With this approach, this is the only 
    script that needs to be loaded into RayStation, while all of the actual scripts are 
    dynamically queried and run from this one. See the repository README and wiki for
    additional information. 
    
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
__version__ = '1.2.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Installation'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Import packages
import os
import sys
import clr
import socket
import getpass
import connect
import shutil
import logging
import importlib
import time

# Specify the location of a local repository containing all scripts (leave blank to 
# download a fresh copy each time)
local = r''

# Specify sub-folder to scan (to list all, leave blank)
module = r'general'

# Specify sub-folder to be a library
library = r'library'

# Specify log folder location (leave blank to not use logging)
logs = r''

# Specify GitHub access token
token = ''

# Specify GitHub contents API
api = 'https://api.github.com/repos/mwgeurts/ray_scripts'


# If this is the primary script
def main(m_local, m_module, m_library, m_logs, m_api, m_token):

    # Link .NET assemblies
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    import System

    try:
        patient = connect.get_current('Patient')
        pat_id = patient.PatientID
    except Exception:
        patient = False
        pat_id = 'NO_PATIENT'

    # Configure file logging
    logging.captureWarnings(True)
    if m_logs != '':
        logging.basicConfig(filename=os.path.normpath('{}/{}.txt'.format(m_logs, pat_id)),
                            level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', filemode='a',
                            format='%(asctime)s\t%(levelname)s\t%(filename)s: %(message)s')

    # Log system, RayStation, and patient info
    ui = connect.get_current('ui')
    logging.debug('*** Python {} ***'.format(sys.version))

    logging.debug('*** RayStation {} ***'.format(ui.GetApplicationVersion()))
    logging.debug('*** Server: {} ***'.format(socket.getfqdn()))
    logging.debug('*** User: {} ***'.format(getpass.getuser()))

    if pat_id != 'NO_PATIENT':
        logging.info('*** Patient: {}, {} ***'.format(pat_id, patient.Name))

    else:
        logging.info('*** Patient: NO_PATIENT ***')

    try:
        case = connect.get_current('Case')
        logging.info('*** Case: {} ***'.format(case.CaseName))

    except Exception:
        logging.info('*** Case: NO_CASE ***')

    try:
        plan = connect.get_current('Case')
        logging.info('*** Plan: {} ***'.format(plan.Name))

    except Exception:
        logging.info('*** Plan: NO_PLAN ***')

    try:
        beamset = connect.get_current('BeamSet')
        logging.info('*** Beamset: {} ***'.format(beamset.DicomPlanLabel))

    except Exception:
        logging.info('*** Beamset: NO_BEAMSET ***')

    # Create local scripts directory if one wasn't provided above
    if m_local == '':
        m_local = 'ray_scripts'

        # Get list of branches 
        import requests

        if m_token != '':
            r = requests.get(m_api + '/branches', headers={'Authorization': 'token {}'.format(m_token),
                                                           'Accept': 'application/vnd.github.v3+json'})
        else:
            r = requests.get(m_api + '/branches', headers={'Accept': 'application/vnd.github.v3+json'})
        branch_list = r.json()

        # Start XAML content. As each branch is found, additional content will be appended
        form = System.Windows.Forms.Form()
        form.Width = 400
        form.Height = 500
        form.Padding = System.Windows.Forms.Padding(0)
        form.Text = 'Select a branch to run'
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

        # Define button action
        def download_branch(self, _e):
            branch = self.Text.split(' ')[0]
            form.DialogResult = True

            if branch == '':
                return

            # Get branch content
            try:
                if m_token != '':
                    y = requests.get(m_api + '/contents?ref=' + branch,
                                     headers={'Authorization': 'token {}'.format(m_token),
                                              'Accept': 'application/vnd.github.v3+json'})
                else:
                    y = requests.get(m_api + '/contents?ref=' + branch,
                                     headers={'Accept': 'application/vnd.github.v3+json'})

                file_list = y.json()
            except requests.ConnectionError:
                logging.exception('Could not access GitHub repository')
                raise

            # Update progress bar length
            bar.Maximum = len(file_list)
            bar.Visible = True

            # Clear directory
            if os.path.exists(m_local):
                try:
                    shutil.rmtree(m_local)
                except OSError:
                    logging.error('Could not delete local repository')
            os.mkdir(m_local)

            # Loop through folders in branch, creating folders and pulling content
            for x in file_list:
                if x.get('type') and not x.get('submodule_git_url'):
                    if x['type'] == u'dir':
                        if x['name'] != u'.git':
                            if m_token != '':
                                y = requests.get(m_api + '/contents' + x['path'] + '?ref=' + branch,
                                                 headers={'Authorization': 'token {}'.format(m_token),
                                                          'Accept': 'application/vnd.github.v3+json'})
                            else:
                                y = requests.get(m_api + '/contents' + x['path'] + '?ref=' + branch,
                                                 headers={'Accept': 'application/vnd.github.v3+json'})

                            sublist = y.json()
                            for z in sublist:
                                file_list.append(z)

                            if not os.path.exists(os.path.join(m_local, x['path'])):
                                os.mkdir(os.path.join(m_local, x['path']))

            # Update progress bar length to full list
            bar.Value = 1
            bar.Maximum = len(file_list)

            # Loop through files in branch, downloading each
            for x in file_list:
                bar.PerformStep()
                System.Windows.Forms.Application.DoEvents()
                if x['type'] == u'file':
                    if x.get('download_url'):
                        logging.debug('Downloading {}'.format(x['download_url']))
                        if os.path.exists(os.path.join(m_local, x['path'])):
                            os.remove(os.path.join(m_local, x['path']))
                        if m_token != '':
                            y = requests.get(x['download_url'], headers={'Authorization':
                                                                         'token {}'.format(m_token),
                                                                         'Accept': 'application/vnd.github.v3+json'})
                        else:
                            y = requests.get(x['download_url'], headers={'Accept': 'application/vnd.github.v3+json'})

                        open(os.path.join(m_local, x['path']), 'wb').write(y.content)

            form.Dispose()

        # Loop through branches
        for l in branch_list:
            button = System.Windows.Forms.Button()
            button.Text = '{} ({})'.format(l['name'].decode('utf-8'), l['commit']['sha'][:7].decode('utf-8'))
            button.Height = 50
            button.Width = 345
            button.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
            button.BackColor = System.Drawing.Color.LightGray
            button.FlatStyle = System.Windows.Forms.FlatStyle.Flat
            button.Click += download_branch
            table.Controls.Add(button)

        # Add progress bar
        bar = System.Windows.Forms.ProgressBar()
        bar.Visible = False
        bar.Minimum = 1
        bar.Maximum = 1
        bar.Value = 1
        bar.Step = 1
        bar.Width = 345
        bar.Height = 30
        bar.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
        table.Controls.Add(bar)

        System.Windows.Forms.Application.EnableVisualStyles()
        form.ShowDialog()

    # Initialize list of scripts
    scripts = {}
    logging.debug('Scanning {} for scripts'.format(os.path.join(m_local, m_module)))
    for root, dirs, files in os.walk(os.path.join(m_local, m_module)):
        for f in files:
            if f.endswith('.py'):
                script = dict()
                script['path'] = root
                script['script'] = f.rstrip('.py')
                with open(os.path.join(root, f)) as fid:
                    c = fid.readlines()
                    script['name'] = c.pop(0).strip(' " \n')   # Assume first line contains name
                    c.pop(0)   # Skip second line
                    s = []
                    for l in c:
                        if l.isspace():
                            break
                        s.append(l.strip())

                    script['tooltip'] = '\n'.join(s)

                    for l in c:
                        if '__help__' in l:
                            script['help_link'] = l.split('=')[1].strip(' \'"')
                            break

                scripts[script['name']] = script

    # Start XAML content. As each script is found, additional content will be appended
    form = System.Windows.Forms.Form()
    form.Width = 400
    form.Height = 500
    form.Padding = System.Windows.Forms.Padding(0)
    form.Text = 'Select a script to run'
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

    # Define button action
    def run_script(self, _e):
        form.DialogResult = True
        form.Dispose()
        sys.path.append(m_local)
        if m_library != '':
            sys.path.append(os.path.join(m_local, m_library))
        sys.path.append(scripts[self.Text]['path'])
        tic = time.time()
        try:
            logging.info('Executing {}.py'.format(scripts[self.Text]['script']))
            code = importlib.import_module(scripts[self.Text]['script'])
            if hasattr(code, 'main') and callable(getattr(code, 'main')):
                code.main()

            if m_logs != '':
                with open(os.path.normpath('{}/ScriptSelector.txt').format(m_logs), 'a') as log_file:
                    log_file.write('{}\t{:.3f}\t{}\t{}.py\t{}'.format(time.strftime('%Y-%m-%d %H:%M:%S'),
                                                                      time.time() - tic, getpass.getuser(),
                                                                      scripts[self.Text]['script'], 'SUCCESS'))

        except Exception as e:
            logging.exception('{}.py: {}'.format(scripts[self.Text]['script'], str(e).splitlines()[0]))
            logging.shutdown()
            if m_logs != '':
                with open(os.path.normpath('{}/ScriptSelector.txt').format(m_logs), 'a') as log_file:
                    log_file.write('{}\t{:.3f}\t{}\t{}.py\t{}'.format(time.strftime('%Y-%m-%d %H:%M:%S'),
                                                                      time.time() - tic, getpass.getuser(),
                                                                      scripts[self.Text]['script'], 'ERROR'))

            raise

    # List directory contents
    for name in sorted(scripts.iterkeys()):
        button = System.Windows.Forms.Button()
        button.Text = name
        button.Height = 50
        button.Width = 345
        button.Margin = System.Windows.Forms.Padding(10, 10, 10, 0)
        button.BackColor = System.Drawing.Color.LightGray
        button.FlatStyle = System.Windows.Forms.FlatStyle.Flat
        button.Click += run_script
        table.Controls.Add(button)

        tooltip = System.Windows.Forms.ToolTip()
        tooltip.SetToolTip(button, scripts[name]['tooltip'])

    # Open window  
    form.ShowDialog()
    logging.shutdown()


if __name__ == '__main__':
    main(local, module, library, logs, api, token)
