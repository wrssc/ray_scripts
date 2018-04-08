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
__version__ = '1.1.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Local-Repository-Setup'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


def main():

    # Specify import statements
    import requests
    import os
    import sys
    import importlib
    import shutil
    import logging
    import clr
    import hashlib

    clr.AddReference('System.Windows.Forms')
    import System.Windows.Forms

    clr.AddReference('System.Drawing')
    import System.Drawing

    # Retrieve variables from invoking function
    selector = importlib.import_module(os.path.basename(sys.modules['__main__'].__file__).split('.')[0])

    # Specify branch to download
    branch = 'master'

    # Get branch content
    try:
        if selector.token != '':
            r = requests.get(selector.api + '/contents?ref=' + branch,
                             headers={'Authorization': 'token {}'.format(selector.token)})
        else:
            r = requests.get(selector.api + '/contents?ref=' + branch)

        file_list = r.json()

    except requests.ConnectionError:
        logging.exception('Could not access GitHub repository')
        raise

    # If local is empty, prompt user to select the location
    if selector.local == '':
        import subprocess
        ipy = r'c:\Program Files (x86)\IronPython 2.7.1\ipy.exe'
        s = 'Select folder to export CT to:'
        local = subprocess.check_output('"{}" {} "{}"'.format(ipy,
                                                              os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                           '..\library\FolderBrowser.py'), s)).strip()
    else:
        local = selector.local

    # Display progress bar
    form = System.Windows.Forms.Form()
    form.Width = 350
    form.Height = 100
    form.Text = 'Downloading folder structure'
    bar = System.Windows.Forms.ProgressBar()
    bar.Visible = True
    bar.Minimum = 1
    bar.Maximum = 100
    bar.Value = 1
    bar.Step = 1
    bar.Width = 300
    bar.Height = 50
    bar.Margin = System.Windows.Forms.Padding(25, 25, 25, 25)
    bar.Style = System.Windows.Forms.ProgressBarStyle.Continuous
    form.Controls.Add(bar)
    form.ShowDialog()

    # Clear directory
    if os.path.exists(local):
        shutil.rmtree(local, ignore_errors=True)
    else:
        os.mkdir(local)

    # Loop through folders in branch, creating folders and pulling content
    for l in file_list:
        if l.get('type'):
            if l['type'] == u'dir':
                if selector.token != '':
                    r = requests.get(selector.api + '/contents' + l['path'] + '?ref=' + branch,
                                     headers={'Authorization': 'token {}'.format(selector.token)})
                else:
                    r = requests.get(selector.api + '/contents' + l['path'] + '?ref=' + branch)

                sublist = r.json()
                for s in sublist:
                    file_list.append(s)

                if not os.path.exists(os.path.join(local, l['path'])):
                    os.mkdir(os.path.join(local, l['path']))

    # Update progress bar text and length
    form.Text = 'Downloading files'
    bar.Maximum = len(file_list) * 2

    # Loop through files in branch, downloading each
    for l in file_list:
        bar.PerformStep()
        if l['type'] == u'file':
            if l.get('download_url'):
                if os.path.basename(l['path'].decode('utf-8')) != os.path.basename(__file__):
                    logging.info('Downloading {} to {}'.format(l['download_url'],
                                                               os.path.join(local, l['path'])))
                    print 'Downloading {} to {}'.format(l['download_url'],
                                                        os.path.join(local, l['path']))
                    if os.path.exists(os.path.join(local, l['path'])):
                        os.remove(os.path.join(local, l['path']))
                    if selector.token != '':
                        r = requests.get(l['download_url'],
                                         headers={'Authorization': 'token {}'.format(selector.token)})
                    else:
                        r = requests.get(l['download_url'])

                    open(os.path.join(local, l['path']), 'wb').write(r.content)

    # Update progress bar text and length
    form.Text = 'Verifying Hashes'

    # Loop through files again, verifying
    for l in file_list:
        bar.PerformStep()
        if l['type'] == u'file':
            sha1sum = hashlib.sha1()
            with open(os.path.join(local, l['path']), 'rb') as source:
                block = source.read(2 ** 16)
                while len(block) != 0:
                    sha1sum.update(block)
                    block = source.read(2 ** 16)

            if l['sha'] == sha1sum.hexdigest():
                logging.info('Hash {} verified: {}'.format(l['path'], l['sha']))
                print 'Hash {} verified: {}'.format(l['path'], l['sha'])
            else:
                logging.warning('Hash {} incorrect: {} != {}'.format(l['path'], l['sha'], sha1sum.hexdigest()))
                print 'Hash {} incorrect: {} != {}'.format(l['path'], l['sha'], sha1sum.hexdigest())

    # Close form
    form.DialogResult = True


if __name__ == '__main__':
    main()
