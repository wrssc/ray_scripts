import connect
import pydicom
from typing import List
import datetime


def get_referenced_sop_class_uids(dicom_filepath: str) -> List[str]:
    """
    Retrieve the 'Referenced SOP Class UID' values from the 'Referenced Instance Sequence'
    in a DICOM file using pydicom.

    The function assumes that the DICOM file contains a sequence named
    'ReferencedInstanceSequence' and that each item in this sequence includes the
    'ReferencedSOPClassUID' attribute.

    Args:
        dicom_filepath (str): Path to the DICOM file.

    Returns:
        List[str]: A list of 'Referenced SOP Class UID' values found in the sequence.
                   Returns an empty list if the sequence or the tag is not found.
    """
    ds = pydicom.dcmread(dicom_filepath)
    referenced_sop_class_uids = []

    # Check if the dataset contains the Referenced Instance Sequence.
    # Note: The exact name of the sequence may vary depending on the DICOM implementation.
    if 'ReferencedInstanceSequence' in ds:
        sequence = ds.ReferencedInstanceSequence
        for item in sequence:
            # Retrieve the Referenced SOP Class UID.
            sop_class_uid = item.get('ReferencedSOPClassUID', None)
            if sop_class_uid:
                referenced_sop_class_uids.append(sop_class_uid)
    else:
        print("Referenced Instance Sequence not found in the DICOM file.")

    return referenced_sop_class_uids


def get_acquisition_date(exam):
    """
    Retrieve the acquisition datetime from a DICOM exam.

    This function fetches the Acquisition Date (0008,0022) and Acquisition Time (0008,0032)
    from the exam object using the provided API. It then combines these strings (if both exist)
    and attempts to parse them into a datetime object. Supported formats include:
      - '%Y%m%d %H%M%S'         (e.g., '20240717 132424')
      - '%Y-%m-%d %H:%M:%S'      (e.g., '2024-07-17 13:24:24')
      - '%Y%m%d'                (if only the date is available)
      - '%Y-%m-%d'              (if only the date is available)

    Args:
        exam: An object representing the exam that must implement the method
              GetStoredDicomTagValueForVerification(Group, Element) which returns a dictionary
              with the DICOM tag's description and value.

    Returns:
        datetime.datetime: The parsed acquisition datetime if available and successfully parsed.
        None: If the acquisition date cannot be retrieved or parsed.
    """
    # Retrieve date and time from the DICOM tags.
    date_dict = exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0022)
    time_dict = exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0032)

    date_str = date_dict.get('Acquisition Date') if date_dict else None
    time_str = time_dict.get('Acquisition Time') if time_dict else None

    if not date_str:
        print(f"Could not retrieve acquisition date for exam {exam.Name}.")
        return None

    # Combine date and time strings if time is available.
    dt_str = date_str
    if time_str:
        dt_str = dt_str + ' ' + time_str

    # Define potential format strings depending on whether time is included.
    possible_formats = []
    if ' ' in dt_str:
        # Date and time are combined.
        possible_formats = ['%Y%m%d %H%M%S', '%Y-%m-%d %H:%M:%S']
    else:
        # Only date is present.
        possible_formats = ['%Y%m%d', '%Y-%m-%d']

    # Try parsing the datetime string with the possible formats.
    for fmt in possible_formats:
        try:
            acquisition_date = datetime.datetime.strptime(dt_str, fmt)
            return acquisition_date
        except ValueError:
            continue

    print(f"Could not parse acquisition date/time string '{dt_str}' for exam {exam.Name}.")
    return None


def get_acquisition_station(exam):
    # Retrieve the acquisition station from the DICOM exam.
    station_dict = exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x1010)
    if station_dict:
        return station_dict.get('Station Name', '').strip()
    return None


def exam_is_cbct(exam):
    """
    Determine if an exam is a cone-beam CT (CBCT) scan based on specific DICOM tag values.

    This function checks for the presence of known treatment units and manufacturers
    and looks for the "IGRT" indicator in the image comments to classify the exam as a CBCT.

    The following DICOM tags are used:
        - Station Name (Group 0x0008, Element 0x1010)
        - Manufacturer (Group 0x0008, Element 0x0070)
        - Image Comments (Group 0x0020, Element 0x4000)

    Args:
        exam: An object representing the exam. It must implement the method
              GetStoredDicomTagValueForVerification(Group, Element) which returns a dictionary
              of tag values or None if the tag is not present.

    Returns:
        bool: True if the exam is likely a CBCT scan, False otherwise.
    """
    # Define known identifiers.
    treatment_unit_list = ["TrueBeam", "Edge", "Halcyon"]
    manufacturer_list = ["Varian", "Elekta"]
    station_name = get_acquisition_station(exam)
    print(f"Exam {exam.Name} - Station Name: {station_name}")

    # Retrieve DICOM tag values for the exam.
    manufacturer_dict = exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0070)
    manufacturer_name = manufacturer_dict.get('Manufacturer', '').strip() if manufacturer_dict else ''
    try:
        image_comments_dict = exam.GetStoredDicomTagValueForVerification(Group=0x0020, Element=0x4000)
    except Exception as e:
        image_comments_dict = None

    image_comment = image_comments_dict.get('Image Comments', '').strip() if image_comments_dict else ''

    # For case-insensitive matching.
    station_name_lower = station_name.lower()
    manufacturer_name_lower = manufacturer_name.lower()
    image_comment_lower = image_comment.lower()

    # Check if any known treatment unit or manufacturer is present and if "IGRT" is in the image comment.
    is_treatment_unit = any(tu.lower() in station_name_lower for tu in treatment_unit_list)
    is_manufacturer = any(mn.lower() in manufacturer_name_lower for mn in manufacturer_list)
    has_igrt = "igrt" in image_comment_lower

    return is_treatment_unit and is_manufacturer and has_igrt


# TODO: Figure out how to match the frame of reference between the exam and the beamset
# def frame_of_reference_match(exam, beamset):
#     exam_frame_of_reference = exam.GetStoredDicomTagValueForVerification(Group=0x0020, Element=0x000D)
#     beamset_frame_of_reference = beamset.ModificationInfo.DicomUID
#     return exam_frame_of_reference == beamset_frame_of_reference
def sort_exams(exams):
    """
    Sort exams based on their acquisition date.

    Args:
        exams (list): A list of exam objects to be sorted.
    """
    # Sort the exams based on their acquisition date
    sorted_exams = sorted(exams, key=lambda x: get_acquisition_date(x))
    return sorted_exams


def rename_cbct_exam(exam, fx_number):
    """
    Rename CBCT exam to a standardized format based on its acquisition date.

    Args:
        exam (RS object): A list of exam objects to be renamed.
    """
    acquisition_date = get_acquisition_date(exam)
    if acquisition_date:
        # Zero-pad fraction number to 2 digits
        new_name = f"CBCT_{acquisition_date.strftime('%Y%m%d')}_{fx_number:02d}"
        print(f"Renaming exam {exam.Name} to {new_name}")
        if exam.Name != new_name:
            exam.Name = new_name
        return new_name
    else:
        print(f"Could not retrieve acquisition date for exam {exam.Name}. Cannot rename.")
        return None


def set_fx_number(exam, fx_number):
    exam.ImportFraction = fx_number


def set_imaging_system_reference(exam):
    station_name = get_acquisition_station(exam)

    if station_name:
        # TODO Get rid of this
        if station_name == "TrueBeam6198":
            station_name = "TrueBeam6696"
        try:
            exam.EquipmentInfo.SetImagingSystemReference(ImagingSystemName=station_name)
        except Exception as e:
            print(f"Error setting imaging system reference for exam {exam.Name}: {e}")


import tempfile


def create_temp_directory():
    """Create a temporary directory and return its path.
    """
    temp_dir = tempfile.mkdtemp()
    return temp_dir


def export_ct(rso, exam_name, directory, anon_name, anon_id):
    try:
        rso.case.ScriptableDicomExport(
            AnonymizationSettings={
                'Anonymize': True,
                'AnonymizedName': anon_name,
                'AnonymizedID': anon_id,
                'RetainDates': True,
                'RetainDeviceIdentity': True,
                'RetainInstitutionIdentity': True,
                'RetainUIDs': True,
                'RetainSafePrivateAttributes': True},
            ExportFolderPath=directory,
            Examinations=[exam_name],
            BeamSets=[],
            # BeamDosesForBeamSets=[],
            DicomFilter='',
            IgnorePreConditionWarnings=True)
        # rso.case.ScriptableDicomExport(Anonymize=True,
        #                            AnonymizedName='M3D {} {} MV'.format(m, e),
        #                            AnonymizedId='{0:0>4}'.format(counter),
        #                            AEHostname=host,
        #                            AEPort=port,
        #                            CallingAETitle='RayStation',
        #                            CalledAETitle=aet,
        #                            Examinations=[case.Examinations[0].Name],
        #                            RtStructureSetsReferencedFromBeamSets=
        #                            [beamset.BeamSetIdentifier()],
        #                            BeamSets=[beamset.BeamSetIdentifier()],
        #                            BeamSetDoseForBeamSets=[beamset.BeamSetIdentifier()],
        #                            DicomFilter='',
        #                            IgnorePreConditionWarnings=True)

    except Exception as error:
        print(f"Error exporting CT for exam {exam_name}: {error}")


def make_fov_roi(rso, fov_name):
    # If it is present, then try first to delete
    try:
        rso.case.PatientModel.RegionsOfInterest[fov_name].DeleteRoi()
    except Exception as e:
        print(f"Error deleting existing FOV ROI {fov_name}: {e}")
        fov_name = rso.case.PatientModel.GetUniqueRoiName(DesiredName=fov_name)
    # Check if the ROI already exists
    try:
        rso.case.PatientModel.CreateRoi(
            Name=fov_name,
            Color="192, 192, 192",
            Type='FieldOfView',
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        return fov_name
    except Exception as e:
        print(f"Error creating FOV ROI {fov_name}: {e}")
        return None


def create_fov_deformation_group(rso, group_name, target_exams, reference_exam, fov_focus_roi):
    # Create the deformation needed for the the cCBCT and vCBCT creation
    rso.case.PatientModel.CreateHybridDeformableRegistrationGroup(
         RegistrationGroupName=group_name,
         ReferenceExaminationName=reference_exam.Name,
         TargetExaminationNames=target_exams,
         ControllingRoiNames=[],
         ControllingPoiNames=[],
         FocusRoiNames=[fov_focus_roi],
         AlgorithmSettings=
         # Current settings from the Lim-FOV deformable registration defaults
         {
             'NumberOfResolutionLevels': 3,
             'InitialResolution': {'x': 0.5, 'y': 0.5, 'z': 0.5},
             'FinalResolution': {'x': 0.25, 'y': 0.25, 'z': 0.25},
             'InitialGaussianSmoothingSigma': 2.0,
             'FinalGaussianSmoothingSigma': 0.333,
             'InitialGridRegularizationWeight': 1500.0,
             'FinalGridRegularizationWeight': 1000.0,
             'ControllingRoiWeight': 0.5,
             'ControllingPoiWeight': 0.1,
             'MaxNumberOfIterationsPerResolutionLevel': 1000,
             'ImageSimilarityMeasure': "CorrelationCoefficient",
             'DeformationStrategy': "LimitedFieldOfView",
             'ConvergenceTolerance': 1e-5
         }
     )




def create_fov_geometry(rso, fov_name, exam_name):
    try:
        rso.case.PatientModel.RegionsOfInterest[fov_name].CreateFieldOfViewROI(
            ExaminationName=exam_name
        )
        return True
    except Exception as e:
        print(f"Error creating FOV geometry for {fov_name} with exam {exam_name}: {e}")
        return False


def create_cylinder_roi(rso, exam_name, center, length, radius):
    """
    Create a cylinder ROI based on the specified parameters.
    """
    # Delete the existing ROI if it exists
    try:
        existing_roi = rso.case.PatientModel.RegionsOfInterest["CylinderROI"]
        if existing_roi:
            rso.case.PatientModel.RegionsOfInterest["CylinderROI"].DeleteRoi()
    except Exception as e:
        print(f"Error deleting existing CylinderROI: {e}")
    try:
        roi = rso.case.PatientModel.CreateRoi(
            Name="CylinderROI",
            Color="192, 192, 192",
            Type='Control',
            TissueName=None,
            RbeCellTypeName=None,
            RoiMaterial=None,
        )
        roi.CreateCylinderGeometry(
            Radius=radius,
            Axis={"x": 0, "y": 0, "z": 1},
            Length=length,
            Examination=rso.case.Examinations[exam_name],
            Center=center,
            Representation='Voxels',
            VoxelSize=0.1,
        )
        return "CylinderROI"
    except Exception as e:
        print(f"Error creating cylinder ROI: {e}")
        return None


def make_fov_contraction(rso, exam_name, fov_name, cylinder_name):
    fov_roi = rso.case.PatientModel.RegionsOfInterest[fov_name]
    ExpressionA = {
        "Operation": "Union",
        "SourceRoiNames": [fov_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ExpressionB = {
        "Operation": "Union",
        "SourceRoiNames": [cylinder_name],
        "MarginSettings": {
            'Type': "Expand",
            'Superior': 0,
            'Inferior': 0,
            'Anterior': 0,
            'Posterior': 0,
            'Right': 0,
            'Left': 0,
        }
    }

    ResultMarginSettings = {
        'Type': "Expand",
        'Superior': 0,
        'Inferior': 0,
        'Anterior': 0,
        'Posterior': 0,
        'Right': 0,
        'Left': 0,
    }

    fov_roi.CreateAlgebraGeometry(
        Examination=rso.case.Examinations[exam_name],
        Algorithm="Auto",
        ExpressionA=ExpressionA,
        ExpressionB=ExpressionB,
        ResultOperation="Intersection",
        ResultMarginSettings=ResultMarginSettings,
    )


def contract_fov(rso, exam_name, fov_name, contraction_cm=1.5):
    """
    Contract the FOV ROI by a specified amount in mm.
    """
    # Get the bounding box of the FOV ROI
    roi_geometry = rso.case.PatientModel.StructureSets[exam_name].RoiGeometries[fov_name]
    bounding_box = roi_geometry.GetBoundingBox()
    center = roi_geometry.GetCenterOfRoi()
    print(f" Center of {fov_name}: {center}, with bounding box: {bounding_box}")
    length = bounding_box[1]['z'] - bounding_box[0]['z'] - contraction_cm * 2
    radius = (bounding_box[1]['x'] - bounding_box[0]['x']) / 2
    print(f"Bounding box for {fov_name}: {bounding_box}, center: {center}, length: {length}, radius: {radius}")
    # Create a cylinder roi
    cylinder_roi = create_cylinder_roi(rso, exam_name, center,
                                       length=length,
                                       radius=radius)
    make_fov_contraction(rso, exam_name, fov_name, cylinder_roi)

def match_for(rso, target_exam_name, reference_exam_name, registration_type="FOR"):
    """
    Match the frame of reference between two exams.
    """
    target_exam = rso.case.Examinations[target_exam_name]
    reference_exam = rso.case.Examinations[reference_exam_name]
    if registration_type == "FOR":
        for reg in rso.case.FrameOfReferenceRegistrations:
            if reg.FromFrameOfReference == target_exam.EquipmentInfo.FrameOfReference \
                    and reg.ToFrameOfReference == reference_exam.EquipmentInfo.FrameOfReference:
                return reg
    elif registration_type == "SS":
        for reg in rso.case.StructureRegistrations:
            if reg.FromExamination.Name == target_exam.Name and reg.ToExamination.Name == reference_exam.Name:
                return reg
    return None


def rename_fov_deformation(rso, target_exam_name, reference_exam_name, fx_number):
    registration = match_for(rso, reference_exam_name, target_exam_name, registration_type="SS")
    description = f"Deformation of {target_exam_name} to {reference_exam_name} for fraction {fx_number}"+\
    "Using a FOV-limited"
    if registration:
        registration.RenameStructureRegistration(
            NewName=f"FOV_Deformed_Fx{fx_number:02d}",
            Description=description)
    else:
        print(f"Could not find deformation for {target_exam_name} to {reference_exam_name}")



def rename_for_registration(rso, exam_name, fx_number, reference_exam_name):
    # First find the FOR matching the exam_name
    reference_exam = None
    target_exam = None
    for e in rso.case.Examinations:
        if e.Name == exam_name:
            target_exam = e
            break
    for e in rso.case.Examinations:
        if e.Name == reference_exam_name:
            reference_exam = e
            break
    if not target_exam:
        print(f"Could not find exam {exam_name}")
        return None
    if not reference_exam:
        print(f"Could not find exam {reference_exam_name}")
        return None
    # Search through the frame of reference registrations
    registration = match_for(rso, exam_name, reference_exam_name, registration_type="FOR")
    if registration:
        zero_fx = f"{fx_number:02d}"
        name = f"FOR_Fx{zero_fx}_{exam_name}_to_{reference_exam_name}"
        registration.RenameFrameOfReferenceRegistration(
            NewName=name,
            Description=f"Registration of {exam_name} to {reference_exam_name}"
                        f" for fraction {fx_number}"
        )
        return name
    return None



# def sort_cbct(rso, beamset_name):
def initialize_cbct(rso):
    case = rso.case
    plan = rso.plan
    beamset = rso.beamset
    exam = rso.exam
    cbct_exams = []
    for exam in rso.case.Examinations:
        if exam_is_cbct(exam):
            cbct_exams.append(exam)
    # Sort the exams based on acquisition date
    sorted_exams = sort_exams(cbct_exams)
    # Rename the exam to a standardized format
    renamed_exams = []
    for fx_number, exam in enumerate(sorted_exams, start=1):
        print(f"Processing exam {exam.Name} for fraction {fx_number}")
        with connect.CompositeAction("Initialization CBCT"):
            renamed_exams.append((rename_cbct_exam(exam, fx_number), fx_number, exam))
            # Set the imaging system reference for each exam
            set_imaging_system_reference(exam)
            # Set the fraction number for each exam
            set_fx_number(exam, fx_number)
    # Create the FOV ROI for exam
    fov_name = make_fov_roi(rso, f"FOV_m01cm")
    for renamed_exam, fx_number, exam in renamed_exams:
        with connect.CompositeAction("Create FOV ROI"):
            create_fov_geometry(rso, fov_name, renamed_exam)
            print(f"Creating FOV geometry for {renamed_exam}, fraction {fx_number}")
    # Rename the rigid registrations
    for renamed_exam, fx_number, exam in renamed_exams:
        print(f"Renaming registrations for {renamed_exam} for reference to {rso.exam.Name}")
        rename_for_registration(rso, renamed_exam, fx_number, 'TPCT')
    # Create the deformations
    create_fov_deformation_group(rso,
                                  "FOV_Deformation", [e[0] for e in renamed_exams],
                                  rso.case.Examinations['TPCT'], fov_name)
    # Rename the deformations
    for renamed_exam, fx_number, exam in renamed_exams:
        rename_fov_deformation(rso, renamed_exam, 'TPCT', fx_number)
    # Create the Corrected CBCTs
    # for cbct in sorted_exams:
    #     cbct_name = f"c{cbct.Name}"
    #     print(f"Creating Corrected CBCT for {cbct.Name} as {cbct_name}")
    #     with connect.CompositeAction("Create Corrected CBCT"):

     #        case.CreateNewCorrectedCbct(CorrectedCbctName=cbct_name,
     #                                    ReferenceExaminationName=rso.exam.Name,
     #                                    TargetExaminationName=cbct.Name,
     #                                    FovRoiName=fov_name,
     #                                    DeformableRegistrationName=None,
     #                                    CreateNewDeformableRegistration=True,
     #                                    CreateNewFieldOfView=False)
            # case.CreateNewVirtualCt(
            #     VirtualCtName=f"v{cbct.Name}",
            #     ReferenceExaminationName=rso.exam.Name,
            #     TargetExaminationName=cbct.Name,
            #     FovRoiName=fov_name,
            #     DeformableRegistrationName=deformable_reg_name,
            #     CreateNewDeformableRegistration=False,
            #     CreateNewFieldOfView=False
           #  )
    # TODO:
    #   Build a custom FOV which excludes the upper cm of the CBCT
    #   Rename the deformed registrations to dreg_FOV_CBCT_20240718_02
    #   Export the cCBCT, intialCT and dreg to a temp directory
    #   Perform analysis on cCBCT and dreg
    #   Create the virtual CBCTs (hopefully using the deformed registrations)
    #   Organ-based deformations
    #   Map Rois from the deformed registration to the virtual/corrected CBCT
    #   Dose accumulation

    # plan.InitializeDoseTrackingFromPlan(TreatmentDelivery=case.TreatmentDelivery,
    #                                     DoseAccumulationExamination=examination)

    # with CompositeAction('Apply image set properties'):

    #     case.Examinations['CT 1'].ImportFraction = 1

    #     case.Examinations['CT 1'].EquipmentInfo.SetImagingSystemReference(ImagingSystemName="TrueBeam6696")

    # retval_0 = case.CreateNewCorrectedCbct(CorrectedCbctName="Corrected CBCT 1", ReferenceExaminationName="TPCT",
    #                                        TargetExaminationName="CT 1", FovRoiName=None,
    #                                        DeformableRegistrationName=None, CreateNewDeformableRegistration=True,
    #                                        CreateNewFieldOfView=True)
