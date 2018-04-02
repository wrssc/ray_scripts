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
__date__ = '2018-04-02'

__version__ = '1.0.0'
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
local = r'\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\Geurts\ray_scripts'

# Specify subfolder to scan (to list all, leave blank)
module = r'general'

# Specify subfolder to be a library
library = r'library'

# Specify log file location (leave blank to not use logging)
logs = r'\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\Geurts\script_log.txt'

# Specify GitHub contents API
api = 'https://api.github.com/repos/mwgeurts/ray_scripts'

# Specify GitHub access token
token = '74dbb9edbefdafcabec66245c3d0d4b30ac7f0bb'

# If this is the primary script
if __name__ == "__main__":

    # Specify import statements
    import os
    import sys
    import wpf
    from System.Windows import Window, Thickness
    from System.Windows.Controls import Button, StackPanel

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
        r = requests.get(api+'/branches', \
            headers={'Authorization': 'token {}'.format(token)})
        list = r.json()
        
        # Start XAML content. As each branch is found, additional content will be appended
        window = Window()
        window.Width = 400
        window.Height = 500
        window.Title = 'Select a branch to run'
        stack = StackPanel()
        stack.Margin = Thickness(15)
        window.Content = stack
        
        # Define button action
        def DownloadBranch(self, e):
            window.DialogResult = True
            branch = self.Content
            
            # Get branch content
            try:
                if token != '':
                    r = requests.get(api+'/contents?ref='+branch, \
                        headers={'Authorization': 'token {}'.format(token)})
                else:
                    r = requests.get(api+'/contents?ref='+branch)
    
                list = r.json()
            except:
                error('Could not access GitHub repository')
                exit()

            # Clear directory
            if os.path.exists(local):
                try:
                    shutil.rmtree(local)
                except:
                    error('Could not delete local repository')
            os.mkdir(local)

            # Loop through folders in branch, creating folders and pulling content
            for l in list:
                if l.get('type'):
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
    
            # Loop through files in branch, downloading each
            for l in list:
                if l['type'] == u'file':
                    if l.get('download_url'):
                        print 'Downloading {}'.format(l['download_url'])
                        if os.path.exists(os.path.join(local, l['path'])):
                            os.remove(os.path.join(local, l['path']))
                        r = requests.get(l['download_url'])
                        open(os.path.join(local, l['path']), 'wb').write(r.content)
        
        # Loop through branches
        for l in list:
            button = Button()
            button.Content = l['name'].decode('utf-8')
            button.Margin = Thickness(5)
            button.Click += DownloadBranch
            stack.Children.Add(button)
            
        # Show branch selector dialog
        window.ShowDialog()

    # Initialize list of scripts
    paths = []
    scripts = []
    names = []
    tooltips = []
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
    window = Window()
    window.Width = 400
    window.Height = 500
    window.Title = 'Select a script to run'
    stack = StackPanel()
    stack.Margin = Thickness(15)
    window.Content = stack

    # Define button action
    def RunScript(self, e):
        window.DialogResult = True
        sys.path.append(local)
        if library != '':
            sys.path.append(os.path.join(local, library))
        sys.path.append(paths[names.index(self.Content)])
        try:
            logging.info('Executing {}.py'.format(scripts[names.index(self.Content)]))
            __import__(scripts[names.index(self.Content)])
        except Exception as e:
            logging.error('{}.py: {}'.format(scripts[names.index(self.Content)], str(e)))
            logging.shutdown()
            raise

    # List directory contents
    for name, tip in sorted(zip(names, tooltips)):
        button = Button()
        button.Content = name
        button.Margin = Thickness(5)
        button.ToolTip = tip
        button.Click += RunScript
        stack.Children.Add(button)
       
    # Open window  
    window.ShowDialog()
    logging.shutdown()