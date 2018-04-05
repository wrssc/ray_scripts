""" Script Selector
    
    This script downloads a copy of the ray_scripts GitHub repository, then displays a 
    list to the user of each script present in the specified subfolder. This script will 
    then execute the script that the user selects. With this approach, this is the only 
    script that needs to be loaded into RayStation, while all of the actual scripts are 
    dynamically queried and run from this one.
    
    If you do not wish to download a fresh copy of the repository each time, you can also 
    specify a local folder via the local path below. In a
    
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
__date__ = '2018-04-04'

__version__ = '1.1.0'
__status__ = 'Development'
__deprecated__ = False
__reviewer__ = 'N/A'

__reviewed__ = 'YYYY-MM-DD'
__maintainer__ = 'Mark Geurts'

__email__ =  'mark.w.geurts@gmail.com'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify the location of a local repository containing all scripts (leave blank to 
# download a fresh copy each time)
local = r''

# Specify subfolder to scan (to list all, leave blank)
module = r'general'

# Specify subfolder to be a library
library = r'library'

# Specify log file location (leave blank to not use logging)
logs = r''

# Specify GitHub contents API
api = 'https://api.github.com/repos/mwgeurts/ray_scripts'

# Specify GitHub access token
token = ''

# If this is the primary script
if __name__ == "__main__":

    # Specify import statements
    import os
    import sys
    import clr
    import shutil
    clr.AddReference('System.Windows.Forms')
    from System.Windows.Forms import Form, Button, Padding, FlatStyle, TableLayoutPanel, \
        TableLayoutPanelGrowStyle, ToolTip, ProgressBar, ProgressBarStyle
    clr.AddReference('System.Drawing')
    from System.Drawing import Color

    # Start logging
    if logs != '':
        import logging
        logging.basicConfig(filename=logs, level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S', \
            format='%(asctime)s\t%(levelname)s\t%(filename)s: %(message)s', mode='a')

    # Create local scripts directory if one wasn't provided above
    if local == '':
        local = 'ray_scripts'
           
        # Get list of branches 
        import requests
        if token != '':
            r = requests.get(api+'/branches', \
                headers={'Authorization': 'token {}'.format(token)})
        else:
            r = requests.get(api+'/branches')
        list = r.json()
        
        # Start XAML content. As each branch is found, additional content will be appended
        form = Form()
        form.Width = 400
        form.Height = 500
        form.Padding = Padding(0)
        form.Text = 'Select a branch to run'
        form.AutoScroll = True
        form.BackColor = Color.White
        table = TableLayoutPanel()
        table.ColumnCount = 1
        table.RowCount = 1
        table.GrowStyle = TableLayoutPanelGrowStyle.AddRows
        table.Padding = Padding(0)
        table.BackColor = Color.White
        table.AutoSize = True
        form.Controls.Add(table)
        
        # Define button action
        def DownloadBranch(self, e):
            branch = self.Text
            form.DialogResult = True

            # Get branch content
            try:
                if token != '':
                    r = requests.get(api+'/contents?ref='+branch, \
                        headers={'Authorization': 'token {}'.format(token)})
                else:
                    r = requests.get(api+'/contents?ref='+branch)
    
                list = r.json()
            except:
                if logs != '':
                    logging.error('Could not access GitHub repository')
                else:
                    print 'Could not access GitHub repository'
                exit()

            # Update progress bar length
            bar.Maximum = len(list);
            bar.Visible = True;

            # Clear directory
            if os.path.exists(local):
                try:
                    shutil.rmtree(local)
                except:
                    if logs != '':
                        logging.error('Could not delete local repository')
                    else:
                        print 'Could not delete local repository'
            os.mkdir(local)

            # Loop through folders in branch, creating folders and pulling content
            for l in list:
                if l.get('type') and not l.get('submodule_git_url'):
                    if l['type'] == u'dir':
                        if l['name'] != u'.git':
                            if token != '':
                                r = requests.get(api +'/contents' + l['path'] + \
                                    '?ref='+branch, headers={'Authorization': \
                                    'token {}'.format(token)})
                            else:
                                r = requests.get(api +'/contents' + l['path'] + \
                                '?ref='+branch)
                        
                            sublist = r.json()
                            for s in sublist:
                                list.append(s)
            
                            if not os.path.exists(os.path.join(local, l['path'])):
                                os.mkdir(os.path.join(local, l['path']))
    
            # Update progress bar length to full list
            bar.Value = 1
            bar.Maximum = len(list)
    
            # Loop through files in branch, downloading each
            for l in list:
                bar.PerformStep();
                if l['type'] == u'file':
                    if l.get('download_url'):
                        print 'Downloading {}'.format(l['download_url'])
                        if os.path.exists(os.path.join(local, l['path'])):
                            os.remove(os.path.join(local, l['path']))
                        if token != '':
                            r = requests.get(l['download_url'], headers={'Authorization': \
                                'token {}'.format(token)})
                        else:
                            r = requests.get(l['download_url'])
                            
                        open(os.path.join(local, l['path']), 'wb').write(r.content)
        
            form.Dispose()

        # Loop through branches
        for l in list:
            button = Button()
            button.Text = l['name'].decode('utf-8')
            button.Height = 50
            button.Width = 345
            button.Margin = Padding(10, 10, 10, 0)
            button.BackColor = Color.LightGray
            button.FlatStyle = FlatStyle.Flat
            button.Click += DownloadBranch
            table.Controls.Add(button)
        
        # Add progress bar
        bar = ProgressBar()
        bar.Visible = False
        bar.Minimum = 1
        bar.Maximum = 1
        bar.Value = 1
        bar.Step = 1
        bar.Width = 345
        bar.Height = 30
        bar.Margin = Padding(10, 10, 10, 0)
        bar.Style = ProgressBarStyle.Continuous
        table.Controls.Add(bar)

        form.ShowDialog()

    # Initialize list of scripts
    paths = []
    scripts = []
    names = []
    tooltips = []
    print 'Scanning {} for scripts'.format(os.path.join(local, module))
    for root, dirs, files in os.walk(os.path.join(local, module)):
        for file in files:
            if file.endswith('.py'):
                paths.append(root)
                scripts.append(file.rstrip('.py'))
                f = open(os.path.join(root, file))
                c = f.readlines()
                names.append(c.pop(0).strip(' " \n'))
                c.pop(0)
                s = []
                for l in c:
                    if l.isspace():
                        break
                    s.append(l.strip())
                f.close()  
                tooltips.append('\n'.join(s))

    # Start XAML content. As each script is found, additional content will be appended
    form = Form()
    form.Width = 400
    form.Height = 500
    form.Padding = Padding(0)
    form.Text = 'Select a script to run'
    form.AutoScroll = True
    form.BackColor = Color.White
    table = TableLayoutPanel()
    table.ColumnCount = 1
    table.RowCount = 1
    table.GrowStyle = TableLayoutPanelGrowStyle.AddRows
    table.Padding = Padding(0)
    table.BackColor = Color.White
    table.AutoSize = True
    form.Controls.Add(table)

    # Define button action
    def RunScript(self, e):
        form.DialogResult = True
        script = names.index(self.Text)
        form.Dispose()
        sys.path.append(local)
        if library != '':
            sys.path.append(os.path.join(local, library))
        sys.path.append(paths[script])
        try:
            print 'Executing {}.py'.format(scripts[script])
            if logs != '':
                logging.info('Executing {}.py'.format(scripts[script]))

            __import__(scripts[script])
        except Exception as e:
            if logs != '':
                logging.error('{}.py: {}'.format(scripts[script], str(e)))
                logging.shutdown()

            raise

    # List directory contents
    for name, tip in sorted(zip(names, tooltips)):
        button = Button()
        button.Text = name
        button.Height = 50
        button.Width = 345
        button.Margin = Padding(10, 10, 10, 0)
        button.BackColor = Color.LightGray
        button.FlatStyle = FlatStyle.Flat;
        button.Click += RunScript
        table.Controls.Add(button)
        
        tooltip = ToolTip()
        tooltip.SetToolTip(button, tip);
       
    # Open window  
    form.ShowDialog()
    if logs != '':
        logging.shutdown()
