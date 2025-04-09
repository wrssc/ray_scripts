# Define a function to extract the number from the string using a regex
import logging
from collections import namedtuple
import connect

import library.GeneralOperations as GeneralOperations
from library.StructureOperations import make_externalclean, check_roi
from library.api.api_case import get_rigid_registrations
# from .autoplan_tomo_vmat_tbi import verify_registration_approval

from .tbi_definitions import EXTERNAL_NAME, HFS_VMAT_PLAN_NAME, HFS_VMAT_BEAMSET_NAME, \
    FFS_VMAT_PLAN_NAME, FFS_VMAT_BEAMSET_NAME, HFS_TOMO_PLAN_NAME, HFS_TOMO_BEAMSET_NAME, FFS_TOMO_PLAN_NAME, \
    FFS_TOMO_BEAMSET_NAME


def register_images(pd_hfs, pd_ffs, hfs_scan_name, ffs_scan_name, testing):
    if not testing:
        # Make external clean on both
        ext_clean = make_externalclean(
            patient=pd_hfs.patient,
            case=pd_hfs.case,
            examination=pd_hfs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )
        # If this breaks on a clean scan, we will want to see if this exam has contours
        ext_clean = make_externalclean(
            patient=pd_ffs.patient,
            case=pd_ffs.case,
            examination=pd_ffs.exam,
            structure_name=EXTERNAL_NAME,
            suffix=None,
            delete=False,
        )

    # TODO: Review - this isn't catching correctly. approved is False
    approved = verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=False,
            InitializeImages=True,
            FocusRoisNames=[],
            RegistrationName=None)

        # Refine on bones
        pd_ffs.case.ComputeGrayLevelBasedRigidRegistration(
            FloatingExaminationName=hfs_scan_name,
            ReferenceExaminationName=ffs_scan_name,
            UseOnlyTranslations=False,
            HighWeightOnBones=True,
            InitializeImages=False,
            FocusRoisNames=[],
            RegistrationName=None)
    else:
        logging.info(f'Approved registration found between {pd_ffs.exam.Name} and {pd_hfs.exam.Name}.')


def update_plan_and_beamset(pd, beamset_name, plan_name=None):
    # Update the plan and beamset for the given patient data
    case = pd.case
    if not plan_name:
        plan = [p for p in case.TreatmentPlans if any(bs.DicomPlanLabel == beamset_name for bs in p.BeamSets)]
        plan = plan[0]
        beamset = [bs for bs in plan.BeamSets if bs.DicomPlanLabel == beamset_name][0]
    else:
        plan = [p for p in case.TreatmentPlans if p.Name == plan_name]
        plan = plan[0]
        beamset = [bs for bs in plan.BeamSets if bs.DicomPlanLabel == beamset_name][0]
    if not plan or not beamset:
        raise RuntimeError(f'Plan with beamset {beamset_name} not found')
    pd = pd._replace(plan=plan, beamset=beamset)
    return pd


def set_current_plan_beamset(pd):
    """ Set the current plan and beamset for the given patient data """
    if pd.plan and pd.beamset:
        pd.patient.Save()
        pd.plan.SetCurrent()
        pd.beamset.SetCurrent()


def reset_primary_secondary(exam1, exam2):
    # Resets exam 1 as primary and exam2 as secondary
    exam1.SetPrimary()
    exam2.SetSecondary()


def initialize_patient_data(hfs_exam, ffs_exam, vmat=False, tomo=False):
    # Initialize patient data structures
    Pd = namedtuple('Pd', ['error', 'db', 'case', 'patient', 'exam', 'plan', 'beamset'])
    case = GeneralOperations.find_scope(level='Case')
    hfs_plan = None
    hfs_beamset = None
    ffs_plan = None
    ffs_beamset = None
    if vmat:
        hfs_plan_name = HFS_VMAT_PLAN_NAME
        hfs_beamset_name = HFS_VMAT_BEAMSET_NAME
        ffs_plan_name = FFS_VMAT_PLAN_NAME
        ffs_beamset_name = FFS_VMAT_BEAMSET_NAME
    if tomo:
        hfs_plan_name = HFS_TOMO_PLAN_NAME
        hfs_beamset_name = HFS_TOMO_BEAMSET_NAME
        ffs_plan_name = FFS_TOMO_PLAN_NAME
        ffs_beamset_name = FFS_TOMO_BEAMSET_NAME
    if tomo or vmat:
        try:
            ffs_plan = case.TreatmentPlans[ffs_plan_name]
            ffs_beamset = ffs_plan.BeamSets[ffs_beamset_name]
        except Exception as e:
            logging.info(f'Could not find FFS plan {ffs_plan_name} in {case.CaseName}: {e}')
        try:
            hfs_plan = case.TreatmentPlans[hfs_plan_name]
            hfs_beamset = hfs_plan.BeamSets[hfs_beamset_name]
        except Exception as e:
            logging.info(f'Could not find HFS plan {hfs_plan_name} in {case.CaseName}: {e}')

    pd_hfs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=hfs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=hfs_plan,
                beamset=hfs_beamset)

    pd_ffs = Pd(error=[],
                patient=GeneralOperations.find_scope(level='Patient'),
                case=GeneralOperations.find_scope(level='Case'),
                exam=ffs_exam,
                db=GeneralOperations.find_scope(level='PatientDB'),
                plan=ffs_plan,
                beamset=ffs_beamset)

    return pd_hfs, pd_ffs


def rename_exams(case):
    hfs_scan_name = ""
    hfs_exam = None
    ffs_scan_name = ""
    ffs_exam = None
    num_exams = 0
    for e in case.Examinations:
        if e.PatientPosition == 'HFS':
            hfs_exam = e
            e.Name = 'HFS'
            hfs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))

        elif e.PatientPosition == 'FFS':
            ffs_exam = e
            e.Name = 'FFS'
            ffs_scan_name = e.Name
            logging.info('Scan {} is patient orientation {}'.format(e.Name, e.PatientPosition))
        else:
            raise RuntimeError('unknown exam orientation')
        num_exams += 1
    if not hfs_scan_name or not hfs_exam:
        raise RuntimeError('Could not find an HFS examination')
    if not ffs_scan_name or not ffs_exam:
        raise RuntimeError('Could not find an FFS examination')
    if not all([hfs_scan_name, ffs_scan_name]):
        raise RuntimeError('This script requires a head first and feet first scan')
    if num_exams > 2:
        raise RuntimeError('This script assumes two exams. One in the HFS '
                           'position and the other in FFS position. '
                           f'The number of exams in this case is {num_exams} '
                           f'and could lead to ambiguity. Exiting')
    return hfs_scan_name, hfs_exam, ffs_scan_name, ffs_exam


def determine_prefix(exam):
    # Return HFS or FFS depending on exam orientation
    if exam.PatientPosition == 'HFS':
        return 'hfs'
    elif exam.PatientPosition == 'FFS':
        return 'ffs'


def check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    approved = False
    # Look through registration objects
    registrations = get_rigid_registrations(pd_ffs.case)
    for r in registrations:
        try:
            _ = r.RegistrationSource
        except AttributeError:
            logging.debug('No approved registrations found')
            approved = False
            break
        if r.RegistrationSource.FromExamination.Name == ffs_scan_name \
                and r.RegistrationSource.ToExamination.Name == hfs_scan_name \
                and r.Review:
            try:
                if r.Review.ApprovalStatus == 'Approved':
                    approved = True
            except AttributeError:
                approved = False
            break
    return approved


def verify_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name):
    # Check for existing registration, if approved return approved
    # Otherwise look for existing registrations and if they are not approved
    # prompt user to approve them or to allow them to be overwritten
    registrations = False
    # Look through registration objects
    approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)

    if not approved:
        for s in pd_ffs.case.StructureRegistrations:
            if s.FromExamination.Name == hfs_scan_name \
                    and s.ToExamination.Name == ffs_scan_name:
                registrations = True
                if s.Review:
                    try:
                        if s.Review.ApprovalStatus == 'Approved':
                            approved = True
                    except AttributeError:
                        approved = False
                break
    if approved:
        return approved
    else:
        if registrations:
            connect.await_user_input('An existing FFS to HFS registration has been'
                                     ' found.\n Approve it to avoid an overwrite')
            approved = check_registration_approval(pd_ffs, ffs_scan_name, hfs_scan_name)
    return approved


def get_center(rs_obj, roi_name):
    # Given a structure name, depending on the patient orientation
    # solve for the most inferior extent of the roi and return that coordinate
    #
    # Check for an empty contour
    [roi_check] = check_roi(rs_obj.case, rs_obj.exam, rois=roi_name)
    if not roi_check:
        return None
    bb_roi = rs_obj.case.PatientModel.StructureSets[rs_obj.exam.Name] \
        .RoiGeometries[roi_name].GetBoundingBox()
    c = {'x': bb_roi[0].x + (bb_roi[1].x - bb_roi[0].x) / 2,
         'y': bb_roi[0].y + (bb_roi[1].y - bb_roi[0].y) / 2,
         'z': bb_roi[0].z + (bb_roi[1].z - bb_roi[0].z) / 2}
    return c
