""" Set Treatment Jaws To Current

    Take the current jaw settings and set them to the current values.

    Version History:
    0.0.0 Development

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
__date__ = '2022-09-16'

__version__ = '0.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'

__reviewed__ = ''
__raystation__ = '11.B'
__maintainer__ = 'Adam Bayliss'

__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2022, University of Wisconsin Board of Regents'

import sys
import logging
import connect
import GeneralOperations
import BeamOperations
from PlanOperations import find_optimization_index


def main():
    plan = GeneralOperations.find_scope(level='Plan')
    beamset = GeneralOperations.find_scope(level='BeamSet')
    # Find the optimization index corresponding to this beamset
    opt_index = find_optimization_index(plan=plan, beamset=beamset)
    plan_optimization = plan.PlanOptimizations[opt_index]
    connect.await_user_input(
        'Note, beams will be reset. Cancel script if this is not intended')
    message = BeamOperations.lock_jaws_to_current(plan_optimization)
    log_message = message.split("\n")
    for l in log_message:
        logging.info(l)
    sys.exit("Treat settings changed!\n"
             + "{}".format(message))


if __name__ == '__main__':
    main()
