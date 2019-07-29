""" Modify Tomo DQA Plan

    Prompts user for Gantry Period for running a TomoDQA

    Version:
    1.0 Load targets as filled. Normalize isodose to prescription, and try to normalize to the
        maximum dose in External or External_Clean

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later
    version.
    
    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss and Patrick Hill'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '29-Jul-2019'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8b.SP2'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/User-Interface'
__credits__ = []

import connect
import logging
import UserInterface

import os
import pydicom
from pydicom.tag import Tag


def main():
    # extract dicom file and gantry period from directory files
    input_dialog = UserInterface.InputDialog(
        inputs={'1': 'Enter Gantry Period'},
        title='Gantry Period',
        datatype={},
        initial={},
        options={},
        required=['1'])
    # Launch the dialog
    response = input_dialog.show()
    # Link root to selected protocol ElementTree
    logging.info("User input the following Gantry Period: {}".format(
        input_dialog.values['1']))
    # Store the protocol name and optional order name
    gantry_period = input_dialog.values['1']

    filepath = 'W:\\rsconvert\\'
    hlist = os.listdir(filepath)
    flist = filter(lambda x: '.dcm' in x, hlist)
    filename = flist[0]
    GPlist = filter(lambda x: '.txt' in x, hlist)
    # GPval = GPlist[0][3:8]+' '

    GPval = gantry_period + ' '

    # format and set tag to change
    t1 = Tag('300d1040')

    # read file
    ds = pydicom.read_file(filepath+filename)

    # add attribute to beam sequence
    ds.BeamSequence[0].add_new(t1, 'UN', GPval)

    # output file
    ds.save_as(filepath+'new_'+filename, write_like_original=True)


if __name__ == '__main__':
    main()


