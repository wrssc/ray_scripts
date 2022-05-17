""" Display TomoTherapy Sinogram
    Use matplotlin to show the sinogram of the current TomoPlan
    Only works for TomoHelical.

    Version:
    0.0 Testing

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

__author__ = 'Adam Bayliss'
__contact__ = 'rabayliss@wisc.edu'
__date__ = '12-Dec-2021'
__version__ = '0.0.0'
__status__ = 'Testing'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '10.A'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import logging
import sys
import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
from collections import namedtuple
import connect
#import UserInterface
import BeamOperations
import GeneralOperations

def main():
    #
    # Initialize return variable
    PatientData = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    ptdat =PatientData(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = GeneralOperations.find_scope(level='Examination'),
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = GeneralOperations.find_scope(level='Plan'),
            beamset = GeneralOperations.find_scope(level='BeamSet'),
    )
    if ptdat.beamset.DeliveryTechnique == 'TomoHelical':
        beam_params = BeamOperations.gather_tomo_beam_params(ptdat.beamset)
    else:
        sys.exit('Unable to show a sinogram for this kind of plan')
    sino_i = beam_params.loc[0].sinogram * beam_params.loc[0].proj_time *1000. #ms per s
    num_proj_i = beam_params.iloc[0].sinogram.shape[0]
    num_mlc_i = beam_params.iloc[0].sinogram.shape[1]
    extent_i = [0, num_mlc_i, 0 , num_proj_i]
    plt.style.use('grayscale')
    plt.imshow(1-sino_i, interpolation='none',extent=extent_i)
    plt.show()

if __name__ == '__main__':
    main()
