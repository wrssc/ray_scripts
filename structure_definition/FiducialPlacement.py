""" Fiducial Contouring

    0.0.0 Guides user through fiducial placement for prostate SBRT

    This program is free software: you can redistribute it and/or modify it under
    the terms of the GNU General Public License as published by the Free Software
    Foundation, either version 3 of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
    FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along with
    this program. If not, see <http://www.gnu.org/licenses/>.

    Review Comments
    I recommend including the test patient in the text above so that users can
    validate, if desired".

    """

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2019-09-05"

__version__ = "0.0.0"
__status__ = "Validation"
__deprecated__ = False
__reviewer__ = "Dustin Jacqmin"

__reviewed__ = "2020-JUL-11"
__raystation__ = "8.0 SP B"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__help__ = ""
__copyright__ = "Copyright (C) 2020, University of Wisconsin Board of Regents"

import logging
import sys
import connect

# import math
import UserInterface
from GeneralOperations import find_scope as find_scope
from GeneralOperations import logcrit as logcrit
import StructureOperations


# import clr
# clr.AddReference("System.Xml")
# import System


def main():
    # Get current patient, case, exam, and plan
    patient = find_scope(level="Patient")
    case = find_scope(level="Case")
    exam = find_scope(level="Examination")
    # Fiducial prefix to be used for naming rois and pois
    fiducial_prefix = "Fiducial"
    # Search distance for the size of the box around which to look for the fiducial
    search_distance = 0.35  # cm
    # Specifications of the seed
    seed_radius = 0.15
    """ Review Comments
    It was recently discovered that the fiducial size is 3 mm, not 5 mm. The
    seed_length may need to change, or perhaps 5 mm will render better on the
    TrueBeam. Something to consider.
    Response: The seed size going forward has been replaced with 5 mm 
    to match commissioned procedure.
    """
    seed_length = 0.5
    prv_radius = 0.2  # This is the search volume first attempted in the fiducial tracking procedure.
    # Launch a dialog for the number of fiducials
    dialog1 = UserInterface.InputDialog(
        inputs={"1": "Enter Number of Fiducials"},
        title="Fiducial Generation",
        datatype={},
        initial={"1": "0"},
        options={},
        required=["1"],
    )
    dialog1_response = dialog1.show()
    if dialog1_response == {}:
        sys.exit("Fiducial script cancelled")
    num_fiducials = int(dialog1_response["1"])
    # Loop to ensure an int response.
    while not isinstance(num_fiducials, int):
        dialog1_response = dialog1.show()
        if dialog1_response == {}:
            sys.exit("Fiducial script cancelled")
        try:
            num_fiducials = int(dialog1_response["1"])
        except:
            num_fiducials = None
    logging.debug("User selected {} fiducials".format(num_fiducials))
    # Find center of patient
    external_roi = StructureOperations.find_types(case=case, roi_type="External")
    if len(external_roi) != 1:
        sys.exit(
            "One and only one external-type object must be defined. {}".format(
                len(external_roi)
            )
        )
    else:
        external_name = external_roi[0]
        logging.debug("External contour is {}".format(external_name))
    # Place initial point at center of external initially
    external_center = (
        case.PatientModel.StructureSets[exam.Name]
        .RoiGeometries[external_name]
        .GetCenterOfRoi()
    )
    logging.debug(
        "Center of the external at x = {}, y = {}, z = {}".format(
            external_center.x, external_center.y, external_center.z,
        )
    )
    # Loop over the number of fiducials.
    # Prompt the user to place the fiducial using a point of interest
    # Search in this region for high-Z seeds, and autocontour.
    # Place the new centroid at this more accurate position.
    # Drop the cylindrical object and prompt the user to re-position it.
    for n in range(num_fiducials):
        point_name = fiducial_prefix + str(n + 1) + "_POI"
        case.PatientModel.CreatePoi(
            Examination=exam,
            Point={
                    "x": external_center.x,
                    "y": external_center.y,
                    "z": external_center.z,
                },
            Volume=0,
            Name=point_name,
            Color="Green",
            VisualizationDiameter=0.5,
            Type="Control",
        )
        # Initialize the fiducial_center to be at the same point as external_center
        fiducial_position = case.PatientModel.StructureSets[exam.Name] \
                            .RoiGeometries[external_name] \
                            .GetCenterOfRoi()
        # Check to make sure the user moved the poi
        while (fiducial_position == external_center):
            # Prompt the user to place the poi at the slice intersection
            connect.await_user_input(
                "Zoom in on fiducial {}.".format(n + 1)
                + " Place crosshairs {} at its geometric center.".format(point_name)
                + " Select 'Set to slice intersection '"
            )
            fiducial_position = case.PatientModel.StructureSets[exam.Name] \
                                .PoiGeometries[point_name].Point
        logging.debug(
            "Point placed at x = {}, y = {}, z = {}".format(
                fiducial_position.x, fiducial_position.y, fiducial_position.z
            )
        )
        # Delete POI
        case.PatientModel.PointsOfInterest[point_name].DeleteRoi()
        fiducial_name = fiducial_prefix + str(n + 1)
        fiducial_geom = StructureOperations.create_roi(
            case=case, examination=exam, roi_name=fiducial_name
        )
        # Now improve on the initial position with a bounding box
        x_min = fiducial_position.x - search_distance
        y_min = fiducial_position.y - search_distance
        z_min = fiducial_position.z - search_distance
        x_max = fiducial_position.x + search_distance
        y_max = fiducial_position.y + search_distance
        z_max = fiducial_position.z + search_distance
        bounding_box = {
            "MinCorner": {"x": x_min, "y": y_min, "z": z_min},
            "MaxCorner": {"x": x_max, "y": y_max, "z": z_max},
        }
        fiducial_geom.OfRoi.GrayLevelThreshold(
            Examination=exam,
            LowThreshold=500,
            HighThreshold=4000,
            PetUnit="",
            CbctUnit=None,
            BoundingBox=bounding_box,
        )
        # Grab the new Center
        fiducial_position = (
            case.PatientModel.StructureSets[exam.Name]
            .RoiGeometries[fiducial_name]
            .GetCenterOfRoi()
        )
        logging.debug(
            "GrayLevelAutocontour moved fiducial center to x = {}, y = {}, z = {}".format(
                fiducial_position.x, fiducial_position.y, fiducial_position.z
            )
        )
        # At this time, RS can only take a single direction for the axis alignment.
        # However, as a TODO: should use least squares to find transformation matrix
        # Also could solve for a rough axis as follows
        # Solve for a rough axis
        # b = case.PatientModel.StructureSets[exam.Name] \
        #             .RoiGeometries[fiducial_name].GetBoundingBox()
        # logging.debug('Bounding box is at x={}, y={}, z={}'
        #               .format(b[1].x,b[1].y,b[1].z))
        # mag = (
        #         (b[1].x - fiducial_position.x)**2
        #       + (b[1].y - fiducial_position.y)**2
        #       + (b[1].z - fiducial_position.z)**2
        #     )**0.5
        # x_hat = (b[1].x - fiducial_position.x) / mag
        # y_hat = (b[1].y - fiducial_position.y) / mag
        # z_hat = (b[1].z - fiducial_position.z) / mag
        # initial_axis = {'x': x_hat, 'y':y_hat, 'z': z_hat}
        # Initial axis: The unit vector describing the initial cylinder placement
        #   HFS: x~L/R, y~A/P,  z~S/I
        initial_axis = {"x": 0, "y": 0, "z": 1}
        logging.debug(
            "Coordinates of axis are {}, {}, {}".format(
                initial_axis["x"], initial_axis["y"], initial_axis["z"]
            )
        )
        # Place the seed
        fiducial_geom.OfRoi.CreateCylinderGeometry(
            Radius=seed_radius,
            Axis=initial_axis,
            Length=seed_length,
            Examination=exam,
            Center={
                "x": fiducial_position.x,
                "y": fiducial_position.y,
                "z": fiducial_position.z,
            },
            Representation="Voxels",
            VoxelSize=0.01,
        )
        msg = StructureOperations.change_to_263_color(case=case, roi_name=fiducial_name)
        if msg is not None:
            logging.debug(msg)
        # Prompt the user to manipulate the contour
        connect.await_user_input(
            "Use the 3D tools to rotate and translate the fiducial contour"
        )
        patient.SetRoiVisibility(RoiName=fiducial_name, IsVisible=False)
        # Acquire the new ROI center for placing the prv
        fiducial_position = (
            case.PatientModel.StructureSets[exam.Name]
            .RoiGeometries[fiducial_name]
            .GetCenterOfRoi()
        )
        prv_name = fiducial_prefix + str(n + 1) + "_PRV02"
        prv_geom = StructureOperations.create_roi(
            case=case, examination=exam, roi_name=prv_name
        )
        # Create the spherical prv volume
        prv_geom.OfRoi.CreateSphereGeometry(
            Radius=prv_radius,
            Examination=exam,
            Center={
                "x": fiducial_position.x,
                "y": fiducial_position.y,
                "z": fiducial_position.z,
            },
            Representation="Voxels",
            VoxelSize=0.01,
        )
        msg = StructureOperations.change_to_263_color(case=case, roi_name=prv_name)
        if msg is not None:
            logging.debug(msg)
    logcrit("Fiducial Contouring script ran successfully on {} fiducials".format(num_fiducials))



if __name__ == "__main__":
    main()
