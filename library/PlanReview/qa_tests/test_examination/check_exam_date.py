from typing import NamedTuple, Tuple, Optional
from dateutil import parser
import datetime
from PlanReview.review_definitions import DAYS_SINCE_SIM, PASS, FAIL, ALERT
from PlanReview.utils import get_approval_info


def check_exam_date(rso: NamedTuple) -> Tuple[str, str]:
    """ Check Exam Date
        Check if the examination date occurred within the tolerance set by DAYS_SINCE_SIM.
        First, it checks for a RayStation approval date, then the last saved by, and
        if not found, the current time is used.

        Args:
            rso (NamedTuple): ScriptObjects in RayStation containing
                             [case ('RayStation Case Object'),
                              exam ('RayStation Exam Object'),
                              plan ('RayStation Plan Object'),
                              beamset ('RayStation BeamSet Object'),
                              db ('RayStation Database Object')]

        Returns:
            result, message_string (Tuple[str, str]): First element is the status (PASS/FAIL/ALERT),
                                                      Second element is the message string

        Pseudocode:
        1. Extract DICOM data from 'rso'
        2. Retrieve the approval status from 'get_approval_info' function
        3. Parse or determine the DICOM date and current time
        4. Calculate the elapsed days between DICOM date and current time
        5. Determine the result (PASS/FAIL/ALERT) based on elapsed days and tolerance
        6. Build and return the result and message string

        Test Patients:
            Pass: ZZ_RayStation^CT_Artifact, 20210408SPF, Case 1: TB_HFS_ArtFilt: Lsha_3DC_R0A0 (all but Gender)
            Fail: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022, ChwL: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    tolerance: int = DAYS_SINCE_SIM  # Days since simulation
    dcm_data: list = list(
        rso.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020).values())
    approval_status = get_approval_info(rso.plan, rso.beamset)

    if dcm_data:
        try:
            dcm_date: datetime.datetime = parser.parse(dcm_data[0])
        except TypeError:
            DEFAULT_DATE: datetime.datetime = datetime.datetime(datetime.MINYEAR, 1, 1)
            dcm_date = parser.parse(str(DEFAULT_DATE))

        if approval_status.beamset_approved:
            current_time: datetime.datetime = parser.parse(str(rso.beamset.Review.ReviewTime))
        else:
            try:
                # Use last saved date if plan not approved
                current_time: datetime.datetime = parser.parse(
                    str(rso.beamset.ModificationInfo.ModificationTime))
            except AttributeError:
                current_time: datetime.datetime = datetime.datetime.now()

        elapsed_days: int = (current_time - dcm_date).days

        if elapsed_days <= tolerance:
            message_str: str = "Exam {} acquired {} within {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days,
                        current_time.date())
            pass_result: str = PASS
        else:
            message_str: str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days,
                        current_time.date())
            pass_result: str = FAIL
    else:
        message_str: str = "Exam {} has no apparent study date!".format(rso.exam.Name)
        pass_result: str = ALERT
    return pass_result, message_str

