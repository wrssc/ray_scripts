"""Add Shoulder Blocking VMAT Beams
Script to add shoulder blocking using user driven info



Version Notes: 1.0.0 Original
1.0.1 Hot Fix to apparent error in version 7 (related to connect being used instead of a
full import)

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
__date__ = '01-Feb-2018'
__version__ = '1.0.0'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = ''
__reviewed__ = ''
__raystation__ = '8.0.B'
__maintainer__ = 'One maintainer'
__email__ = 'rabayliss@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2018, University of Wisconsin Board of Regents'
__help__ = 'https://github.com/mwgeurts/ray_scripts/wiki/Shoulder-Block'
__credits__ = []

import sys
import os
import logging
import connect
import UserInterface
import Beams
import PlanOperations


def main():
    # Get current patient, case, exam, and plan
    # note that the interpreter handles a missing plan as an Exception
    try:
        patient = connect.get_current("Patient")
    except SystemError:
        raise IOError("No Patient loaded. Load patient case and plan.")

    try:
        case = connect.get_current("Case")
    except SystemError:
        raise IOError("No Case loaded. Load patient case and plan.")

    try:
        exam = connect.get_current("Examination")
    except SystemError:
        raise IOError("No examination loaded. Load patient ct and plan.")

    try:
        plan = connect.get_current("Plan")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")

    try:
        beamset = connect.get_current("BeamSet")
    except Exception:
        raise IOError("No plan loaded. Load patient and plan.")
        sys.exit('This script requires a Beam Set to be loaded')

    # Script will run through the following steps.  We have a logical inconsistency here with making a plan
    # this is likely an optional step
    status = UserInterface.ScriptStatus(
        steps=['SimFiducials point declaration',
               'isocenter Declaration',
               'Left shoulder POI',
               'Right shoulder POI',
               'Add Beams'],
        docstring=__doc__,
        help=__help__)

    protocol_folder = r'../protocols'
    institution_folder = r'UW'
    beamset_folder = r'beamsets'
    file = 'UWVMAT_Beamsets.xml'
    path_protocols = os.path.join(os.path.dirname(__file__),
                                  protocol_folder,
                                  institution_folder, beamset_folder)
    beamset_name = '2 Arc VMAT'

    beam_elements = Beams.select_element(set_type='beamset',
                                         set_elements='beam',
                                         set_name=beamset_name,
                                         filename=file,
                                         folder=path_protocols)
    for et_beamsets in beam_elements:
        beams = et_beamsets.findall('./beam')
        for b in beams:
            b_n = b.find('name').text
            b_t = b.find('type').text
            beams = b.findall('./objectives/roi')
            logging.debug('Success {}'.format(b_n))

    try:

        plan.AddNewBeamSet(
            Name=p,
            ExaminationName=examination.Name,
            MachineName=plan_machine,
            Modality="Photons",
            TreatmentTechnique="Conformal",
            PatientPosition="HeadFirstSupine",
            NumberOfFractions=number_of_fractions,
            CreateSetupBeams=False,
            UseLocalizationPointAsSetupIsocenter=False,
            Comment="",
            RbeModelReference=None,
            EnableDynamicTrackingForVero=False,
            NewDoseSpecificationPointNames=[],
            NewDoseSpecificationPoints=[],
            RespiratoryMotionCompensationTechnique="Disabled",
            RespiratorySignalSource="Disabled")
        # copied_plan = case.CopyPlan(PlanName=plan.Name, NewPlanName='ShoulderBlock')
    except Exception:
        logging.warning('Unable to copy plan')
        sys.exit('Unable to copy plan')

    PlanOperations.check_localization(case=case, create=True, confirm=False)

    connect.set_current(copied_plan)

if __name__ == '__main__':
    main()
