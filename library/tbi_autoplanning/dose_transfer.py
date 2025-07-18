import datetime
import logging
import math
import os
import shutil
import sys
import connect

try:
    import FreeSimpleGUI as Sg
except ImportError:
    import PySimpleGUI as Sg

from typing import Optional, List, Tuple
from .tbi_definitions import TOMO_FFS_TRANSFER_NAME, VMAT_FFS_TRANSFER_NAME, HFS_TOMO_PLAN_NAME, \
    HFS_VMAT_PLAN_NAME, FFS_PLACEHOLDER_NAME, DICOM_PATH, FFS_VMAT_PLAN_NAME
from .tbi_utils import Pd



def plan_transfer_successful(pd_hfs: Pd, pd_ffs: Pd, nfx: int) -> bool:
    """
    Check if the FFS plan has been successfully transferred to the HFS representation.
    Args:
        pd_hfs: Patient data for HFS (RayStation API object or Pd namedtuple).
        pd_ffs: Patient data for FFS (RayStation API object or Pd namedtuple).
        nfx: Number of fractions expected.
    Returns:
        bool: True if transfer is successful, False otherwise.
    """
    # Look through the existing plans in the HFS representation,
    # and check if the FFS plan has been transferred
    # Find the corresponding dose evaluation
    _, ffs_dose_evaluation = find_dose_evaluation(pd_ffs, pd_hfs)

    modality = pd_ffs.beamset.DeliveryTechnique
    hfs_transfer_name = TOMO_FFS_TRANSFER_NAME if modality == 'TomoHelical' else VMAT_FFS_TRANSFER_NAME
    hfs_plan_name = HFS_TOMO_PLAN_NAME if modality == 'TomoHelical' else HFS_VMAT_PLAN_NAME

    uid = None
    if ffs_dose_evaluation:
        uid = ffs_dose_evaluation.ModificationInfo.DicomUID
    for tp in pd_hfs.case.TreatmentPlans:
        if hfs_plan_name == tp.Name:
            for bs in tp.BeamSets:
                logging.debug(f'Checking beamset {bs.DicomPlanLabel} for {hfs_transfer_name}')
                if bs.DicomPlanLabel == hfs_transfer_name:
                    is_clinical = bs.IsApprovedToUseAsBackgroundDose()
                    is_scaled = bs.FractionationPattern.NumberOfFractions == nfx
                    logging.debug(f'Beamset {bs.DicomPlanLabel} is clinical: {is_clinical}, '
                                  f'is scaled: {is_scaled}')
                    logging.debug(f'Beamset {bs.DicomPlanLabel} comment: {bs.Comment}'
                                  f'UID: {uid}')
                    if uid:
                        if f'<FFS_UID>:{uid}' in bs.Comment and is_clinical and is_scaled:
                            return True
        elif FFS_PLACEHOLDER_NAME == tp.Name:
            for bs in tp.BeamSets:
                logging.debug(f'Checking beamset {bs.DicomPlanLabel} for {FFS_PLACEHOLDER_NAME}')
                if FFS_PLACEHOLDER_NAME == bs.DicomPlanLabel:
                    logging.debug(f'Beamset {bs.DicomPlanLabel} comment: {bs.Comment}'
                                  f'UID: {uid}')
                    if f'<FFS_UID>:{uid}' in bs.Comment:
                        return True
    return False


def find_dose_evaluation(pd_ffs: Pd, pd_hfs: Pd) -> Tuple[Optional[object], Optional[object]]:
    """
    Find the dose evaluation for the FFS plan on the HFS exam.
    Args:
        pd_ffs: Patient data for FFS.
        pd_hfs: Patient data for HFS.
    Returns:
        Tuple of (dose_on_examination, dose_evaluation) or (None, None) if not found.
    """
    fraction_evaluations = [f for f in pd_ffs.case.TreatmentDelivery.FractionEvaluations]
    ffs_dose_on_examination = None
    ffs_dose_evaluation = None
    for f in fraction_evaluations:
        for dose_exam in f.DoseOnExaminations:
            dose_eval = dose_exam.DoseEvaluations[0]
            if dose_eval.ForBeamSet.DicomPlanLabel == pd_ffs.beamset.DicomPlanLabel and \
                    dose_exam.OnExamination.Name == pd_hfs.exam.Name and \
                    dose_exam.OnExamination.PatientPosition == pd_hfs.exam.PatientPosition:
                ffs_dose_evaluation = dose_eval
                ffs_dose_on_examination = dose_exam
    return ffs_dose_on_examination, ffs_dose_evaluation


def get_available_evaluation_doses(case: object) -> List[dict]:
    """
    Get all available evaluation doses for a case.
    Args:
        case: RayStation case object.
    Returns:
        List of dictionaries with dose evaluation info.
    """
    evaluation_doses = []
    fraction_evaluations = [f for f in case.TreatmentDelivery.FractionEvaluations]
    for f in fraction_evaluations:
        for dose_exam in f.DoseOnExaminations:
            if len(dose_exam.DoseEvaluations) > 1:
                raise RuntimeError(f'More than one dose evaluation found for {dose_exam.OnExamination.Name}')
            dose_eval = dose_exam.DoseEvaluations[0]
            eval_dose = {'Origin Beamset': dose_eval.ForBeamSet.DicomPlanLabel,
                         'Destination Exam': dose_exam.OnExamination.Name,
                         'Destination Patient Position': dose_exam.OnExamination.PatientPosition,
                         'DICOM UID': dose_eval.ModificationInfo.DicomUID,
                         'Versioning Status': dose_eval.VersioningStatus.IsVersionSameAsCurrent,
                         'Dose Evaluation': dose_eval}
            evaluation_doses.append(eval_dose)
    return evaluation_doses


def get_evaluation_dose_values(origin_beamset: str, destination_exam: str, destination_patient_position: str, evaluation_doses: List[dict]) -> Optional[object]:
    """
    Retrieve dose values for a specific origin beamset and destination.
    Args:
        origin_beamset: Name of the origin beamset.
        destination_exam: Name of the destination exam.
        destination_patient_position: Patient position string.
        evaluation_doses: List of evaluation dose dicts.
    Returns:
        Dose data or None if not found.
    """
    for de in evaluation_doses:
        if de['Origin Beamset'] == origin_beamset and \
                de['Destination Exam'] == destination_exam and \
                de['Destination Patient Position'] == destination_patient_position:
            return de['Dose Evaluation'].DoseValues.DoseData
    return None


def rename_hfs_preplan(case: object, input_plan_name: str, input_beamset_name: str, output_plan_name: str, output_beamset_name: str) -> Optional[object]:
    """
    Rename a preplan and its beamset in the HFS case.
    Args:
        case: RayStation case object.
        input_plan_name: Current plan name.
        input_beamset_name: Current beamset name.
        output_plan_name: New plan name.
        output_beamset_name: New beamset name.
    Returns:
        The updated plan object, or None if not found.
    """
    # Check if the plan already exists
    for p in case.TreatmentPlans:
        if p.Name == input_plan_name:
            p.Name = output_plan_name
            break
    if not p:
        return None
    # Check if the beamset already exists
    for bs in p.BeamSets:
        if bs.DicomPlanLabel == input_beamset_name:
            bs.DicomPlanLabel = output_beamset_name
    # Verify the
    return case.TreatmentPlans[output_plan_name]


def export_background_dose(pd_ffs: Pd, pd_hfs: Pd) -> str:
    """
    Export background dose data by identifying and importing the correct dose series
    from the DICOM repository while ensuring no duplicate or incorrect doses are imported.
    Args:
        pd_ffs: Forward-facing patient data object.
        pd_hfs: Head-first supine patient data object.
    Returns:
        str: Error message if an issue occurs; otherwise, returns an empty string.
    """

    def convert_net_to_datetime(net_time):
        """Converts a NET time object to a Python datetime object."""
        return datetime.datetime(net_time.Year, net_time.Month, net_time.Day, net_time.Hour, net_time.Minute,
                                 net_time.Second)

    def find_patient_directory(repo_path, patient_id, expected_date):
        """
        Searches for a directory containing the given patient ID and expected date.
        """
        logging.debug(f'Searching for patient {patient_id} with expected date {expected_date} in {repo_path}')

        for root, dirs, _ in os.walk(repo_path):
            for directory in dirs:
                if patient_id in directory and expected_date in directory:
                    return os.path.join(root, directory)
        return None

    def check_datetime_match(dose_datetime, dicom_metadata):
        """
        Compares dose_datetime to DICOM metadata date and time, ignoring seconds.
        """
        try:
            year, month, day = int(dicom_metadata['SeriesDate'][:4]), int(dicom_metadata['SeriesDate'][4:6]), int(
                dicom_metadata['SeriesDate'][6:8])
            hour, minute = int(dicom_metadata['SeriesTime'][:2]), int(dicom_metadata['SeriesTime'][2:4])
        except (ValueError, KeyError, IndexError):
            return False

        series_datetime = datetime.datetime(year, month, day, hour, minute, 0)
        return dose_datetime.replace(second=0, microsecond=0) == series_datetime

    def get_series_to_import(pd, ffs_dose, ffs_eval, patient_data_path):
        """
        Retrieves the matching series for dose import.
        """
        dicom_elements_dict = {'study_instance_uid': (0x0020, 0x00d), 'patient_id': (0x0010, 0x0020)}
        series_or_instances = get_dicom_entries(dicom_elements_dict, ffs_dose.OnExamination)

        matching_patients = pd.db.QueryPatientsFromPath(Path=patient_data_path,
                                                        SearchCriterias={'PatientID': pd.patient.PatientID})
        if not matching_patients:
            raise RuntimeError(f'Patient not found in {patient_data_path}, export not performed')
        if len(matching_patients) > 1:
            raise RuntimeError(f'Multiple patients found in {patient_data_path}, export not performed')

        studies = pd.db.QueryStudiesFromPath(Path=patient_data_path, SearchCriterias=matching_patients[0])
        series = [s for study in studies for s in
                  pd.db.QuerySeriesFromPath(Path=patient_data_path, SearchCriterias=study)]

        mod_datetime = convert_net_to_datetime(ffs_eval.ModificationInfo.ModificationTime)

        return [entry for entry in series if (
                entry['StudyInstanceUID'] == series_or_instances['StudyInstanceUID'] and
                "Beam" not in entry['SeriesDescription'] and
                "Evaluation Fx Dose" in entry['SeriesDescription'] and
                check_datetime_match(mod_datetime, entry) and
                entry['Modality'] == 'RTDOSE'
        )]

    def remove_directory_contents_with_prompt(dir_path):
        """
        Prompts user before deleting all contents inside the given directory.
        """
        if not os.path.exists(dir_path):
            Sg.popup_error(f"The path {dir_path} does not exist.")
            return False

        layout = [
            [Sg.Text(f"Multiple exported dose files were found in:\n{dir_path}\nDo you want to remove all contents?")],
            [Sg.Button("Yes", key="-YES-"), Sg.Button("No", key="-NO-")]]
        window = Sg.Window("Confirm Deletion", layout, modal=True)

        while True:
            event, _ = window.read()
            if event in (Sg.WIN_CLOSED, "-NO-"):
                window.close()
                return False
            if event == "-YES-":
                window.close()
                break

        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

        Sg.popup("Contents removed successfully.")
        return True

    ffs_dose_on_examination, ffs_dose_evaluation = find_dose_evaluation(pd_ffs, pd_hfs)
    if not ffs_dose_on_examination:
        return f'No FFS Dose found for {pd_ffs.beamset.DicomPlanLabel} on {pd_hfs.exam.Name}'

    mod_date = convert_net_to_datetime(ffs_dose_evaluation.ModificationInfo.ModificationTime).strftime("%Y%m%d")
    today_str = datetime.date.today().strftime("%Y%m%d")
    # Prompt user to export the evaluation dose
    connect.await_user_input(f'Export to Target: PACS-RayStation\n '
                             f'Evaluation Fx Dose {FFS_VMAT_PLAN_NAME} (HFS)\n'
                             f'Make sure to deselect beam doses')

    patient_path = find_patient_directory(DICOM_PATH, pd_ffs.patient.PatientID, mod_date) or \
                   find_patient_directory(DICOM_PATH, pd_ffs.patient.PatientID, today_str)

    if not patient_path:
        return f'Patient directory not found in {DICOM_PATH}, export not performed'

    series_to_import = get_series_to_import(pd_ffs, ffs_dose_on_examination, ffs_dose_evaluation, patient_path)

    if len(series_to_import) > 1 and remove_directory_contents_with_prompt(patient_path):
        return f'Multiple exported dose files found. Please clear {patient_path} and restart export.'
    elif not series_to_import:
        return f'No dose export found in {patient_path} for {pd_ffs.beamset.DicomPlanLabel}, export not performed'

    warnings = pd_hfs.patient.ImportDataFromPath(
        Path=patient_path,
        CaseName=pd_hfs.case.CaseName,
        SeriesOrInstances=series_to_import,
    )

    if "A dummy plan has been created for an image set" not in warnings:
        return f'Import failed: {warnings}'

    empty_plan = pd_hfs.case.TreatmentPlans[FFS_PLACEHOLDER_NAME]
    empty_beamset = empty_plan.BeamSets[FFS_PLACEHOLDER_NAME]
    empty_beamset.Comment = f'{ffs_dose_evaluation.ForBeamSet.DicomPlanLabel}\n' \
                            f'{ffs_dose_evaluation.ForBeamSet.PatientPosition}\n' \
                            f'{ffs_dose_evaluation.ModificationInfo.ModificationTime}\n' \
                            f'<FFS_UID:{ffs_dose_evaluation.ModificationInfo.DicomUID}>'

    return ""


def get_dicom_entries(dicom_elements: dict, api_dicom_object: object) -> dict:
    """
    Fetch DICOM tag values for the given elements.
    Args:
        dicom_elements: Dict of DICOM tag tuples.
        api_dicom_object: RayStation DICOM object.
    Returns:
        Dict of DICOM tag values.
    """
    series_or_instances = {}
    for key, (group, element) in dicom_elements.items():
        dicom_entry = api_dicom_object.GetStoredDicomTagValueForVerification(
            Group=group, Element=element
        )
        if dicom_entry:  # Ensure dicom_entry is not None or empty
            series_or_instances.update(
                {"".join(name.split()): identifier for name, identifier in dicom_entry.items()}
            )
    return series_or_instances


def potential_transfer_plan_names(pd_ffs: Pd) -> List[str]:
    """
    Get possible plan names for transfer based on modality.
    Args:
        pd_ffs: Patient data for FFS.
    Returns:
        List of plan names.
    """
    modality = pd_ffs.beamset.DeliveryTechnique
    return [FFS_PLACEHOLDER_NAME, HFS_TOMO_PLAN_NAME] if modality == 'TomoHelical' \
        else [FFS_PLACEHOLDER_NAME, HFS_VMAT_PLAN_NAME]


def potential_transfer_beamset_names(pd_ffs: Pd) -> List[str]:
    """
    Get possible beamset names for transfer based on modality.
    Args:
        pd_ffs: Patient data for FFS.
    Returns:
        List of beamset names.
    """
    modality = pd_ffs.beamset.DeliveryTechnique
    return [FFS_PLACEHOLDER_NAME, TOMO_FFS_TRANSFER_NAME] if modality == 'TomoHelical' \
        else [FFS_PLACEHOLDER_NAME, VMAT_FFS_TRANSFER_NAME]


def check_empty_plans(pd_ffs: Pd, pd_hfs: Pd, exists: bool = True, unique: bool = True) -> None:
    """
    Check for empty plan containers in the HFS plan.
    Args:
        pd_ffs: Patient data for FFS.
        pd_hfs: Patient data for HFS.
        exists: Whether the plan should exist.
        unique: Whether only one should exist.
    Raises:
        RuntimeError if the check fails.
    """
    # Check for containers already existing in the hfs plan.
    empty_plans = []
    hfs_plan_names = potential_transfer_plan_names(pd_ffs)
    for tp in pd_hfs.case.TreatmentPlans:
        logging.debug(f'Looking in {tp.Name} for {hfs_plan_names}')
        if any([n in tp.Name for n in hfs_plan_names]):
            empty_plans.append(tp.Name)
    if exists:
        if len(empty_plans) == 0:
            raise RuntimeError(
                f'No {FFS_PLACEHOLDER_NAME} found in the HFS exam, run the export script first')
        elif len(empty_plans) > 1:
            raise RuntimeError(f'Multiple plans with name {hfs_plan_names} found in the HFS exam, delete all '
                               f'plans with plan name "{hfs_plan_names}" and re-export the FFS plan')
    else:
        if len(empty_plans) > 0:
            raise RuntimeError(f'{FFS_PLACEHOLDER_NAME} found in the HFS exam, delete all plans with'
                               f'plan name "{FFS_PLACEHOLDER_NAME}" and re-export the FFS plan')
    if unique and len(empty_plans) > 1:
        raise RuntimeError(
            f'Multiple plans with name {FFS_PLACEHOLDER_NAME} found in the HFS exam, delete all plans with'
            f'plan name "{FFS_PLACEHOLDER_NAME}" and re-export the FFS plan')


def calculate_ffs_on_hfs_logic(pd_ffs: Pd, pd_hfs: Pd, nfx: int, rx: int, make_vmat_plan: bool, make_tomo_plan: bool) -> Pd:
    """
    Helper to calculate FFS dose on HFS image, update dose grid, and compute dose.
    Args:
        pd_ffs: Patient data for FFS.
        pd_hfs: Patient data for HFS.
        nfx: Number of fractions.
        rx: Prescription dose.
        make_vmat_plan: Whether to make a VMAT plan.
        make_tomo_plan: Whether to make a Tomo plan.
    Returns:
        Updated pd_ffs object.
    """

    case = pd_ffs.case

    # If pd_ffs has no beamset, prompt user to pick from existing plans:
    if not pd_ffs.beamset:
        plans = [p.Name for p in case.TreatmentPlans]
        beamsets = [bs.DicomPlanLabel for p in case.TreatmentPlans for bs in p.BeamSets]
        ffs_plan, ffs_beamset = dose_calc_gui(case, plans, beamsets)
        pd_ffs = pd_ffs._replace(plan=ffs_plan, beamset=ffs_beamset)

    grid_updated = rescale_dose_grid_to_all_scans(pd_ffs)
    # If the dose grid changed, re-compute
    try:
        if grid_updated:
            pd_ffs.beamset.ComputeDose(ComputeBeamDoses=False, DoseAlgorithm='CCDose',
                                       ForceRecompute=False)
            pd_ffs.patient.Save()
    except Exception as e:
        logging.debug(f"During dose summation, dose computation failed: {e}")

    # Now compute dose on the HFS image
    hfs_scan_name = pd_hfs.exam.Name
    pd_ffs.beamset.ComputeDoseOnAdditionalSets(
        Examinations=[pd_hfs.exam],
    )

    # Must save to get the dose properly recognized in RayStation
    pd_ffs.patient.Save()

    # Return the updated PD if needed
    return pd_ffs


def rescale_dose_grid_to_all_scans(pdata: Pd) -> bool:
    """
    Rescale dose grid to cover all scans, updating if necessary.
    Args:
        pdata: Patient data object.
    Returns:
        bool: True if the grid was updated, False otherwise.
    """

    pm = pdata.case.PatientModel
    dg = pdata.beamset.GetDoseGrid()
    modality = pdata.beamset.DeliveryTechnique

    origin_frame_of_reference = pdata.beamset.FrameOfReference
    origin_exam_name = pdata.exam.Name

    logging.debug(f'Current dose grid corner: {dg.Corner}, '
                  f'Voxel size: {dg.VoxelSize}, '
                  f'Number of voxels: {dg.NrVoxels}')

    # Build initial bounding box from the current dose grid
    bb = [
        dg.Corner,
        {k: dg.Corner[k] + dg.VoxelSize[k] * dg.NrVoxels[k]
         for k in dg.Corner.keys()}
    ]
    logging.debug(f'Current dose grid bounding box: {bb}')

    # Types of ROIs to consider
    types = ['Ptv', 'Support', 'External']

    # Collect all structure sets and adjust bounding box as needed
    for s in pm.StructureSets:
        structure_frame_of_reference = s.OnExamination.EquipmentInfo.FrameOfReference
        transform_needed = (structure_frame_of_reference != origin_frame_of_reference)
        destination_name = s.OnExamination.Name if transform_needed else None

        if transform_needed:
            logging.debug(f'Need to transform from {origin_exam_name} to {destination_name}')

        for r in s.RoiGeometries:
            if r.OfRoi.Type in types:
                try:
                    bs = s.RoiGeometries[r.OfRoi.Name].GetBoundingBox()
                    # Transform bounding box if needed
                    bs_tr = ([
                                 pdata.case.TransformPointFromExaminationToExamination(
                                     FromExamination=destination_name,
                                     ToExamination=origin_exam_name,
                                     Point=b) for b in bs
                             ] if transform_needed else bs)
                    # Extend the bounding box if needed
                    for c, v in bs_tr[0].items():
                        if v < bb[0][c]:
                            logging.debug(f'Lower corner extended in {c} '
                                          f'from {bb[0][c]} to {v}')
                            bb[0][c] = v
                    for c, v in bs_tr[1].items():
                        if v > bb[1][c]:
                            logging.debug(f'Upper corner extended in {c} '
                                          f'from {bb[1][c]} to {v}')
                            bb[1][c] = v

                except Exception as e:
                    no_geom_set = "no geometry set for ROI"
                    if no_geom_set not in str(e):
                        logging.warning(f'Error in updating dose grid: {e}')

    # Prepare new grid specs
    vs = dg.VoxelSize
    span = {k: abs(bb[1][k] - bb[0][k]) for k in bb[1].keys()}
    logging.debug(f'New dose grid span after expansions: {span}')

    update_number_voxels = {
        k: math.ceil(v / vs[k]) for (k, v) in span.items()
    }

    # Check if we need to update dose grid
    needs_update = (
            update_number_voxels != dg.NrVoxels
            or bb[0] != dg.Corner
            or vs != dg.VoxelSize
    )

    logging.debug(f'Corner: {bb[0]}, '
                  f'Voxel size: {vs}, '
                  f'Number of voxels: {update_number_voxels}, '
                  f'Dose grid update needed: {needs_update}')

    # Update the dose grid if needed
    if needs_update:
        pdata.beamset.UpdateDoseGrid(
            Corner=bb[0],
            VoxelSize=vs,
            NumberOfVoxels=update_number_voxels
        )

    return needs_update


def dose_calc_gui(case: object, plans: List[str], beamsets: List[str]) -> Tuple[object, object]:
    """
    GUI for selecting FFS plan and beamset.
    Args:
        case: RayStation case object.
        plans: List of plan names.
        beamsets: List of beamset names.
    Returns:
        Tuple of (selected plan, selected beamset).
    """
    Sg.ChangeLookAndFeel('DarkPurple4')
    layout = [[Sg.Text("FFS Plan")],
              [Sg.Combo(plans, key="-FFS PLAN-",
                        default_value=plans[0],
                        size=(40, 1),
                        enable_events=True)],
              [Sg.Text("FFS Beamset")],
              [Sg.Combo(beamsets, key="-FFS BEAMSET-",
                        default_value=beamsets[0],
                        size=(40, 1),
                        enable_events=True)],
              [Sg.B('OK'), Sg.B('Cancel')]]
    window = Sg.Window("BEAMSET ASSIGNMENT",
                       layout)
    while True:
        event, values = window.read()
        if event == Sg.WIN_CLOSED or event == "Cancel":
            selections = None
            break
        elif event == "-FFS PLAN-":
            # Update beamset combo based on selected plan
            selected_plan_name = values['-FFS PLAN-']
            selected_plan = next((tp for tp in case.TreatmentPlans if tp.Name == selected_plan_name), None)
            logging.debug(f'Selected Plan: {selected_plan.Name}')
            if selected_plan:
                beamsets = [bs.DicomPlanLabel for bs in selected_plan.BeamSets]
                window['-FFS BEAMSET-'].update(values=beamsets, value=beamsets[0] if beamsets else '')
            else:
                window['-FFS BEAMSET-'].update(values=[], value='')
        elif event == "OK":
            selections = values
            break
    window.close()
    if selections == {}:
        sys.exit('Selection Script was cancelled')
    ffs_plan = None
    ffs_beamset = None

    for tp in case.TreatmentPlans:
        if tp.Name == selections['-FFS PLAN-']:
            ffs_plan = tp
            for bs in tp.BeamSets:
                if bs.DicomPlanLabel == selections['-FFS BEAMSET-']:
                    ffs_beamset = bs
                    break
    if not all([ffs_beamset, ffs_plan]):
        sys.exit('No FFS Beamsets defined')
    else:
        return ffs_plan, ffs_beamset
