""" Automatically create and place the Civco incline board

This script accomplishes the following tasks:
1. Create and automatically place TrueBeam couch
2. Create and automatically place Civco incline board base
3. Create and automatically place Civco incline board body
    (with user-supplied angle)
4. Create and automatically place Civco wingboard (with user-supplied index)

This script was tested with:
* Patient: INCLINE BOARD
* MRN: 20210713
* Case: 5
* RayStation: Launcher
* Title: Sandbox

Version History:


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

__author__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__date__ = "2021-09-14"
__version__ = "0.0.1"
__status__ = "Development"
__deprecated__ = False
__reviewer__ = None
__reviewed__ = None
__raystation__ = "10A SP1"
__maintainer__ = "Dustin Jacqmin"
__contact__ = "djjacqmin_humanswillremovethis@wisc.edu"
__license__ = "GPLv3"
__help__ = None
__copyright__ = "Copyright (C) 2021, University of Wisconsin Board of Regents"

from connect import CompositeAction, get_current
import StructureOperations

def deploy_truebeam_couch(
    case,
    support_structure_template = "UW Support Structures",
    support_structures_examination = "CT 1",
    source_roi_names = ['Couch']
    ):
    """ Deploys the TrueBeam couch

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.
    support_structure_template: str
        The name of the support structure template in RayStation
        (default is "UW Support Structures")
    support_structures_examination: str
        The name of the examination associated with support_structure_template
        from which you will load the source ROIs (default is "CT 1")
    source_roi_names : list of str
        The names of the ROIs from support_structures_examination that you wish
        to load (default is ["Couch"]

    RETURNS
    -------
    None

    """

    # This script is designed to be used for HFS patients:
    examination = get_current("Examination")

    if exam.PatientPosition != "HFS":
        logging.error("Current exam in not in HFS position. Exiting script.")
        message = (
            "The script requires a patient in the head-first supine position. "
            "The currently selected exam is not HFS. Exiting script."
        )
        messagebox.showerror("Patient Orientation Error", message)
        exit()

    with CompositeAction("Drop TrueBeam Couch"):

        # Load the source template for the couch structure:
        try:
            support_template = patient_db.LoadTemplatePatientModel(
                templateName=support_structure_template,
                lockMode='Read'
            )
        except InvalidOperationException:
            logging.error(f"Could not load support_structure_template = {support_structure_template}. Exiting.")
            message = (
                "The script attempted to load a support_structure_template
                "called {support_structure_template}. This was not successful. "
                "Verify that a structure template with this name exists. "
                "Exiting script."
            )
            messagebox.showerror("Structure Template Error", message)
            exit()

        # Check for Couch already in plan

        # Add the TrueBeam Couch
        case.PatientModel.CreateStructuresFromTemplate(
            SourceTemplate=support_template,
            SourceExaminationName=support_structures_examination,
            SourceRoiNames=source_roi_names,
            SourcePoiNames=[],
            AssociateStructuresByName=True,
            TargetExamination=examination,
            InitializationOption='AlignImageCenters'
        )
        logging.info("Successfully dropped the TrueBeam Couch")

    with CompositeAction("Shift TrueBeam Couch"):

        COUCH_Y_SHIFT = 7

        couch = case.PatientModel.StructureSets[examination.Name].RoiGeometries["Couch"]

        top_of_couch = couch.GetBoundingBox()[0]["y"]
        TransformationMatrix = {'M11':1, 'M12':0, 'M13':0, 'M14':0,
                                'M21':0, 'M22':1, 'M23':0, 'M24':-(top_of_couch+COUCH_Y_SHIFT),
                                'M31':0, 'M32':0, 'M33':1, 'M34':0,
                                'M41':0, 'M42':0, 'M43':0, 'M44':1}
        couch.OfRoi.TransformROI3D(Examination=examination, TransformationMatrix=TransformationMatrix)

    with CompositeAction("Create Temporary ImageVolume ROI")
    

        # Create roi for shifted external
        ext_alignrt_su = case.PatientModel.CreateRoi(
            Name="Ext_AlignRT_SU",
            Color="Green",
            Type="Organ",
            TissueName="",
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        logging.info("Created Ext_AlignRT_SU")

        # Copy the external ROI into the shifted external:

        MarginSettings = {
            "Type": "Expand",
            "Superior": 0,
            "Inferior": 0,
            "Anterior": 0,
            "Posterior": 0,
            "Right": 0,
            "Left": 0,
        }
        ext_alignrt_su.SetMarginExpression(
            SourceRoiName=roi_external_name, MarginSettings=MarginSettings
        )
        ext_alignrt_su.UpdateDerivedGeometry(Examination=exam, Algorithm="Auto")

        logging.info("Copied {} into {}".format(roi_external_name, ext_alignrt_su.Name))

        # Finally, shift the contour. This shift direction will only work for HFP
        TransformationMatrix = {
            "M11": 1,
            "M12": 0,
            "M13": 0,
            "M14": 0,  # end row
            "M21": 0,
            "M22": 1,
            "M23": 0,
            "M24": -shift_size,  # end row
            "M31": 0,
            "M32": 0,
            "M33": 1,
            "M34": 0,  # end row
            "M41": 0,
            "M42": 0,
            "M43": 0,
            "M44": 1,  # end row
        }

        ext_alignrt_su.TransformROI3D(
            Examination=exam, TransformationMatrix=TransformationMatrix
        )
        logging.info(
            "Shifted {} anteriorly by {} cm".format(
                ext_alignrt_su.Name, str(shift_size)
            )
        )


def clean(case):
    """Undo all of the actions done by create_external_alignrt_su()

    PARAMETERS
    ----------
    case : ScriptObject
        A RayStation ScriptObject corresponding to the current case.

    RETURNS
    -------
    None

    """

    # Clean not developed at this time. If there is a problem with Ext_AlignRT_SU, it may be
    # manually deleted.
    pass


def main():
    """The main function for this file"""

    logging.debug("Beginning execution of DeployCivcoBoard.py in main()")
    case = get_current("Case")

    # Deploy the TrueBeam couch
    deploy_truebeam_couch(case)


if __name__ == "__main__":
    main()
