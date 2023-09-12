
def check_structure_exists(
        case, structure_name, roi_list=None,
        option="Check", exam=None):
    """
    Verify if a structure with the exact name specified exists or not
    :param case: Current RS case
    :param structure_name: the name of the structure to be confirmed
    :param roi_list: a list of available ROIs as RS RoiGeometries to check
                     against
    :param option: desired behavior
        Delete - deletes structure if found
        Check - simply returns true or false if found
        Wait - prompt user to create structure if not found
    :param exam: Current RS exam, if supplied the script deletes geometry only,
                 otherwise contour is deleted
    :return: Logical - True if structure is present in ROI List,
                       False otherwise
    """

    # If no roi_list is given, build it using all roi in the case
    if roi_list is None:
        roi_list = []
        for s in case.PatientModel.StructureSets:
            for r in s.RoiGeometries:
                if r not in roi_list:
                    roi_list.append(r)

    if any(roi.OfRoi.Name == structure_name for roi in roi_list):
        if exam is not None:
            structure_has_contours_on_exam = (
                case.PatientModel.StructureSets[exam.Name]
                    .RoiGeometries[structure_name]
                    .HasContours()
            )
        else:
            structure_has_contours_on_exam = False

        if option == "Delete":
            if structure_has_contours_on_exam:
                case.PatientModel.StructureSets[exam.Name].RoiGeometries[
                    structure_name
                ].DeleteGeometry()
                return False
            else:
                case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
                return True
        elif option == "Check":
            if exam is not None and structure_has_contours_on_exam:
                # logging.info("Structure {} has contours on exam {}".format(structure_name,
                # exam.Name))
                return True
            elif exam is not None:
                # logging.info("Structure {} has no contours on exam {}".format(structure_name,
                # exam.Name))
                return False
            else:
                # logging.info("Structure {} exists in this Case {}".format(structure_name,
                # case.Name))
                return True
        elif option == "Wait":
            if structure_has_contours_on_exam:
                # logging.info("Structure {} has contours on exam {}".format(structure_name,
                # exam.Name))
                return True
            else:
                connect.await_user_input("Create the structure {} and continue script."
                                         .format(structure_name))
    else:
        return False


def make_high_z(case, exam, desired_name):
    threshold = 3025  # Highest HU value on the scanner
    # Redraw the ExternalClean structure if necessary
    if check_structure_exists(
            case=case,
            structure_name=desired_name,
            exam=exam,
            option="Check"):
        roi_geom = case.PatientModel.StructureSets[exam.Name].RoiGeometries[
            desired_name]
    else:
        roi_geom = create_roi(
            case=case,
            examination=exam,
            roi_name=desired_name,
            delete_existing=False,
            suffix="",
        )
    if not roi_geom.HasContours():
        roi_geom.GrayLevelThreshold(Examination=exam,
                                    LowThreshold=int(0.9 * threshold),
                                    HighThreshold=threshold,
                                    PetUnit="",
                                    CbctUnit=None,
                                    BoundingBox=None)
