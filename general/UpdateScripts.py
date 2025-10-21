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
__version__ = '1.2.0'
__license__ = 'GPLv3'
__help__ = 'https://github.com/wrssc/ray_scripts/wiki/Local-Repository-Setup'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'

# Specify import statements for global scope
import os


def main():

    # Specify import statements
    import requests
    import sys
    import importlib
    import shutil
    import logging
    import hashlib
    import UserInterface
    import time
    import tempfile

    # Retrieve variables from invoking function
    selector = importlib.import_module(os.path.basename(sys.modules['__main__'].__file__).split('.')[0])

    # Specify branch to download
    branch = 'master'
    logging.debug('user name {}'.format(os.getenv('username')))
    os.chdir(os.path.dirname(__file__))
    logging.debug('current directory is {}'.format(os.getcwd()))

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

    # Create temporary directory for download
    temp_dir = tempfile.mkdtemp(prefix='ray_scripts_update_')
    logging.info('Using temporary directory: {}'.format(temp_dir))

    # Loop through folders in branch, creating folders and pulling content
    for file_in_file_list in file_list:
        if file_in_file_list.get('type'):
            if file_in_file_list['type'] == u'dir':
                if selector.token != '':
                    r = requests.get(selector.api + '/contents' + file_in_file_list['path'] + '?ref=' + branch,
                                     headers={'Authorization': 'token {}'.format(selector.token)})
                else:
                    r = requests.get(selector.api + '/contents' + file_in_file_list['path'] + '?ref=' + branch)

                sublist = r.json()
                for s in sublist:
                    file_list.append(s)

                if not os.path.exists(os.path.join(temp_dir, file_in_file_list['path'])):
                    os.mkdir(os.path.join(temp_dir, file_in_file_list['path']))

    # Update progress bar text and length
    bar = UserInterface.ProgressBar('Downloading files', 'Update Progress', len(file_list) * 2)

    # Loop through files in branch, downloading each to temp directory
    for file_in_file_list in file_list:
        bar.update('Downloading {}'.format(file_in_file_list['path']))
        if file_in_file_list['type'] == u'file':
            if file_in_file_list.get('download_url'):
                logging.info('Downloading {} to {}'.format(file_in_file_list['download_url'],
                                                           os.path.join(temp_dir, file_in_file_list['path'])))
                if os.path.exists(os.path.join(temp_dir, file_in_file_list['path'])):
                    os.remove(os.path.join(temp_dir, file_in_file_list['path']))
                if selector.token != '':
                    r = requests.get(file_in_file_list['download_url'],
                                     headers={'Authorization': 'token {}'.format(selector.token)})
                else:
                    r = requests.get(file_in_file_list['download_url'])

                open(os.path.join(temp_dir, file_in_file_list['path']), 'wb').write(r.content)

    # Loop through files again, verifying in temp directory
    passed = True
    for file_in_file_list in file_list:
        bar.update('Verifying Hashes')
        if file_in_file_list['type'] == u'file':
            if file_in_file_list.get('download_url'):

                fh = open(os.path.join(temp_dir, file_in_file_list['path']), 'rb')
                content = fh.read()
                fh.close()
                sha = hashlib.sha1(bytearray('blob {}\0'.format(len(content)), 'utf8') + content).hexdigest()

                if file_in_file_list['sha'] == sha:
                    logging.info('Hash {} verified: {}'.format(file_in_file_list['path'], file_in_file_list['sha']))
                else:
                    logging.warning('Hash {} incorrect: {} != {}'.format(file_in_file_list['path'], file_in_file_list['sha'], sha))
                    passed = False

    # Close progress bar
    bar.close()

    if passed:
        # Create backup of existing directory if it exists
        backup_dir = None
        if os.path.exists(local):
            backup_dir = local + '_backup_' + time.strftime('%Y%m%d_%H%M%S')
            try:
                shutil.copytree(local, backup_dir)
                logging.info('Created backup at: {}'.format(backup_dir))
            except Exception as e:
                logging.warning('Failed to create backup: {}'.format(e))
                UserInterface.WarningBox('Failed to create backup of existing scripts. Proceed anyway?', 'Backup Warning')
                if not UserInterface.MessageBox('Continue without backup?', 'Confirm', 'YesNo') == 'Yes':
                    # Clean up temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return

        # Replace existing directory with temp directory
        try:
            if os.path.exists(local):
                shutil.rmtree(local, ignore_errors=True)
            shutil.move(temp_dir, local)
            logging.info('Successfully updated scripts directory: {}'.format(local))
            
            # Clean up backup if everything succeeded
            if backup_dir and os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
                logging.info('Removed backup directory: {}'.format(backup_dir))
            
            UserInterface.MessageBox('Script download and checksum verification successful', 'Success')
            
        except Exception as e:
            logging.error('Failed to replace existing directory: {}'.format(e))
            
            # Restore from backup if available
            if backup_dir and os.path.exists(backup_dir):
                try:
                    if os.path.exists(local):
                        shutil.rmtree(local, ignore_errors=True)
                    shutil.move(backup_dir, local)
                    logging.info('Restored from backup: {}'.format(backup_dir))
                    UserInterface.WarningBox('Update failed, restored from backup. No changes were made.', 'Update Failed')
                except Exception as restore_error:
                    logging.error('Failed to restore from backup: {}'.format(restore_error))
                    UserInterface.WarningBox('Update failed and backup restoration failed. Check logs for details.', 'Critical Error')
            else:
                UserInterface.WarningBox('Update failed. Check logs for details.', 'Update Failed')
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    else:
        # Clean up temp directory on verification failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        UserInterface.WarningBox('Scripts download, but verification failed. No changes were made.', 'Warning')


if __name__ == '__main__':
    main()
