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
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Local-Repository-Setup'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements for global scope
import os


def readonly_handler(func, path, execinfo):
    """ A function to handle windows file errors relating to directories being incorrectly
    assigned readonly status by windoze. Apparently this issue is to be resolved by python
    3.5 """
    os.chmod(path, 128) #or os.chmod(path, stat.S_IWRITE) from "stat" module
    func(path)

def main():

    # Specify import statements
    import requests
    import sys
    import importlib
    import shutil
    import logging
    import hashlib
    import UserInterface

    # Retrieve variables from invoking function
    selector = importlib.import_module(os.path.basename(sys.modules['__main__'].__file__).split('.')[0])

    # Specify branch to download
    branch = 'master'
    logging.debug('user name {}'.format(os.getenv('username')))

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
        browser = UserInterface.CommonDialog()
        local = browser.folder_browser('Select folder location for scripts:')
    else:
        local = selector.local

    # Clear directory
    if os.path.exists(local):
        if os.path.isfile(local):
            os.unlink(local)
        elif os.path.isdir(local):
            shutil.rmtree(local, onerror=readonly_handler)
            while True:
                try:
                    os.mkdir(local)
                    break
                except:
                    logging.debug('Dumb windows permission error')
                    continue
    else:
        os.mkdir(local)

    if os.path.exists(local):
        logging.info('Local directory is: {}'.format(local))
    else:
        logging.warning('Local directory failed to create: {}'.format(local))
        sys.exit('Exiting')


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
    bar = UserInterface.ProgressBar('Downloading files', 'Update Progress', len(file_list) * 2)

    # Loop through files in branch, downloading each
    for l in file_list:
        bar.update('Downloading {}'.format(l['path']))
        if l['type'] == u'file':
            if l.get('download_url'):
                logging.info('Downloading {} to {}'.format(l['download_url'],
                                                           os.path.join(local, l['path'])))
                if os.path.exists(os.path.join(local, l['path'])):
                    os.remove(os.path.join(local, l['path']))
                if selector.token != '':
                    r = requests.get(l['download_url'],
                                     headers={'Authorization': 'token {}'.format(selector.token)})
                else:
                    r = requests.get(l['download_url'])

                open(os.path.join(local, l['path']), 'wb').write(r.content)

    # Loop through files again, verifying
    passed = True
    for l in file_list:
        bar.update('Verifying Hashes')
        if l['type'] == u'file':
            if l.get('download_url'):

                fh = open(os.path.join(local, l['path']), 'rb')
                content = fh.read()
                fh.close()
                sha = hashlib.sha1(bytearray('blob {}\0'.format(len(content)), 'utf8') + content).hexdigest()

                if l['sha'] == sha:
                    logging.info('Hash {} verified: {}'.format(l['path'], l['sha']))
                else:
                    logging.warning('Hash {} incorrect: {} != {}'.format(l['path'], l['sha'], sha))
                    passed = False

    # Show success message
    bar.close()
    if passed:
        UserInterface.MessageBox('Script download and checksum verification successful', 'Success')
    else:
        UserInterface.WarningBox('Scripts download, but verification failed', 'Warning')


if __name__ == '__main__':
    main()
