""" Compare Contours
    Compare two contours selected by the user and return the
    Dice Coefficient, Precision, Sensitivity, Specificity, Mean DTA, Max DTA

    Version:
    0.0 Compares two contours using the RayStation method Test
    1.0 Release

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
__date__ = '04-Jun-2021'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '10.A'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = ''
__credits__ = []

import logging
import sys
from collections import namedtuple
import connect
import UserInterface
import StructureOperations
import GeneralOperations




def main():
    #
    # Initialize return variable
    Pd = namedtuple('Pd', ['error','db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    # Get current patient, case, exam
    pd = Pd(error = [],
            patient = GeneralOperations.find_scope(level='Patient'),
            case = GeneralOperations.find_scope(level='Case'),
            exam = GeneralOperations.find_scope(level='Examination'),
            db = GeneralOperations.find_scope(level='PatientDB'),
            plan = None,
            beamset = None)
    defined_rois = []
    for r in pd.case.PatientModel.RegionsOfInterest:
        defined_rois.append(r.Name)
    rois_1 = defined_rois.copy()
    rois_2 = defined_rois.copy()

    # Declare the dialog
    dialog = UserInterface.InputDialog(
        inputs={'1': 'Select Roi 1', '2':'Select Roi 2'},
        title='Roi Compare',
        datatype={'1': 'combo', '2':'combo'},
        initial={},
        options={'1': rois_1, '2':rois_2},
        required=[])
    # Launch the dialog
    response = dialog.show()
    # Close on cancel
    if response == {}:
        logging.info('Autoload cancelled by user. Protocol not selected')
        sys.exit('Protocol not selected. Process cancelled.')
    stats = StructureOperations.compute_comparison_statistics(
        patient = pd.patient,
        case = pd.case,
        exam = pd.exam,
        rois_a = [dialog.values['1']],
        rois_b = [dialog.values['2']],
        compute_distances = True
    )
    user_message = ""
    for k, v in stats.items():
        user_message += "{} : {}\n".format(k,v)
    user_message += "{}".format("""\n
    DiceSimilarityCoefficient: | ROIA intersect ROIB | / | ROIA | + | ROIB |\n
    Precision: ROIA intersect ROIB | / | ROIA union ROIB |\n
    Sensitivity: 1 - | ROIB not ROIA | / | ROIA |\n
    Specificity: | ROIA intersect ROIB | / | ROIA |\n
    MeanDistanceToAgreement: Mean distance to agreement computed
      from average of minimum voxel distances\n
    MaxDistanceToAgreement: Maximum of minimum distances\n
      between voxels (Hausdorff)""")
    UserInterface.MessageBox(user_message)

if __name__ == '__main__':
    main()
