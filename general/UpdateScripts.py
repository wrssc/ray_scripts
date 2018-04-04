""" Refresh Production Scripts
    
    This script refreshes the local list of scripts from the online repository. This is 
    only applicable if a local variable was set in the version of ScriptSelector imported 
    into RayStation.
    
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

# Specify import statements
import requests
import os
import shutil
from logging import info, error
from ScriptSelector import api, token, local

# Specify branch to download
branch = 'master'

# Get branch content
try:
    if token != '':
        r = requests.get(api+'/contents?ref='+branch, headers={'Authorization': \
            'token {}'.format(token)})
    else:
        r = requests.get(api+'/contents?ref='+branch)
    
    list = r.json()
except:
    error('Could not access GitHub repository')
    exit()

# If local is empty, prompt user to select the location
if local == '':
    import clr
    clr.AddReference('System.Windows.Forms')
    from System.Windows.Forms import FolderBrowserDialog, DialogResult
    dialog = FolderBrowserDialog()
    dialog.Description = 'Select the local path to refresh:'
    if (dialog.ShowDialog() == DialogResult.OK):
        local = dialog.SelectedPath
    else:
        error('A local folder was not defined')
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
                    r = requests.get(api +'/contents' + l['path'] + '?ref='+branch, \
                        headers={'Authorization': 'token {}'.format(token)})
                else:
                    r = requests.get(api +'/contents' + l['path'] + '?ref='+branch)
                        
                sublist = r.json()
                for s in sublist:
                    list.append(s)
            
                if not os.path.exists(os.path.join(local, l['path'])):
                    os.mkdir(os.path.join(local, l['path']))

# Loop through files in branch, downloading each
for l in list:
    if l['type'] == u'file':
        if l.get('download_url'):
            info('Downloading {} to {}'.format(l['download_url'], \
                os.path.join(local, l['path'])))
            print 'Downloading {} to {}'.format(l['download_url'], \
                os.path.join(local, l['path']))
            if os.path.exists(os.path.join(local, l['path'])):
                os.remove(os.path.join(local, l['path']))
            r = requests.get(l['download_url'])
            open(os.path.join(local, l['path']), 'wb').write(r.content)