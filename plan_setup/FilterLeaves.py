""" Fix Dynamic Leaf Gaps

    Loop through the beams in this beamset. Look for leaves that are closed more than
    the minimum leaf gap for the commissioned machine. Increment the gap until the 
    minimum leaf gap condition is met.

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.
    """

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '2020-01-29'

__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = ''
__raystation__ = '10.A'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'


import GeneralOperations
import BeamOperations
import logging


def main():
    beamset = GeneralOperations.find_scope(level='BeamSet')
    for b in beamset.Beams:
        error = BeamOperations.repair_leaf_gap(b)
        if error is not None:
            logging.debug(error)
        else:
            logging.debug('Beam {} filtered'.format(b.Name))

if __name__ == '__main__':
    main()