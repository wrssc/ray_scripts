""" Create Electron QA Plan

    Creates a QA plan for an electron beam onto a water phantom in order to compare RayStation vs.
    Mobius MU.

    This script will create a QA plan in the Plan preparation workspace, using a 50cm cube water
    phantom. This phantom has POIs spaced every 1mm on the CAX.  The patient-specific cutout will
    be used but the couch and and gantry angles will be set to zero. The default SSD is 105cm so
    the user will need to manually edit the QA plan for a different SSD.  The dose grid resolution
    is 2.5mm and 500K histories will be used.

    Validation Notes: The script relies on the status of the QA phantom being verifiable as
                      read-only.Due to a programming error in RayStation 6.0 this status validation
                      fails when QA plans are generated as part of a python script.  Therefore,
                      unless the user has, without a script, validated the read-only status of the
                      plan by opening a "dummy" QA plan, the script will fail to execute.

    Version Notes: 1.0.0 Original
                   1.0.1 Added a relabeling of the plan to include the Beamset name to avoid
                         ambiguity when the "Mobius MU" plan name is taken.  Also changed the
                         active phantom to 50cmCube for the clinical institution.  Added
                         autorecompute and deleted incorrect plan recomputation syntax.
                   1.0.2 Added main function call, eliminated blanket connect import,
                         autoclick QA prep
                   1.1.0 Update to Rs 10A

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

__author__ = 'Jessie Huang-Vredevoogd'
__contact__ = 'jyhuang4@wisc.edu'
__date__ = '2021-01-17'
__version__ = '1.0.2'
__status__ = 'Production'
__deprecated__ = False
__reviewer__ = 'Adam Bayliss'
__reviewed__ = '2018-01-26'
__raystation__ = '10A SP1'
__maintainer__ = 'Huang-Vredevoogd and Bayliss'
__email__ = 'jyhuang4@wisc.edu'
__license__ = 'GPLv3'
__copyright__ = 'Copyright (C) 2021, University of Wisconsin Board of Regents'
__credits__ = []


def main():
    import connect
    import UserInterface
    import sys

    try:
        beam_set = connect.get_current("BeamSet")
    except Exception:
        UserInterface.WarningBox('This script requires a Beam Set to be loaded')
        sys.exit('This script requires a Beam Set to be loaded')

    QA_Plan_Name = beam_set.DicomPlanLabel + "QA"
    # Click magic
    ui = connect.get_current('ui')
    ui.TitleBar.MenuItem['QA preparation'].Button_QA_preparation.Click()

    try:
        beam_set.CreateQAPlan(
            PhantomName="50cm Cube_2",
            PhantomId="50cm Cube",
            QAPlanName=QA_Plan_Name,
            IsoCenter={'x': 0, 'y': -30, 'z': 25},
            DoseGrid={'x': 0.25, 'y': 0.25, 'z': 0.25},
            GantryAngle=0,
            CollimatorAngle=None,
            CouchAngle=0,
            ComputeDoseWhenPlanIsCreated=True,
            NumberOfMonteCarloHistories=500000)
    except Exception:
        UserInterface.WarningBox('QA Plan failed to create')
        sys.exit('QA Plan failed to create')


if __name__ == '__main__':
    main()





