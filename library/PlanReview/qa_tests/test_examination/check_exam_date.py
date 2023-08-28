from dateutil import parser
import datetime
from PlanReview.review_definitions import DAYS_SINCE_SIM, PASS,FAIL, ALERT
from PlanReview.utils import get_approval_info


def check_exam_date(rso):
    """
    Check if examination date occurred within tolerance set by DAYS_SINCE_SIM
    First it checks for a RayStation approval date, then we'll use the last saved by,
    if not we'll use right now!

    Args:
        rso: (namedtuple): Named tuple of ScriptObjects
    Returns:
        (Pass/Fail/Alert, Message to Display)
    Test Patient:
        Pass (all but Gender): ZZ_RayStation^CT_Artifact, 20210408SPF
              Case 1: TB_HFS_ArtFilt: Lsha_3DC_R0A0
        Fail: Script_Testing^Plan_Review, #ZZUWQA_ScTest_01May2022:
              ChwL: Bolus_Roi_Check_Fail: ChwL_VMA_R0A0
    """
    tolerance = DAYS_SINCE_SIM  # Days since simulation
    dcm_data = list(
        rso.exam.GetStoredDicomTagValueForVerification(Group=0x0008, Element=0x0020).values())
    approval_status = get_approval_info(rso.plan, rso.beamset)
    if dcm_data:
        try:
            dcm_date = parser.parse(dcm_data[0])
        except TypeError:
            DEFAULT_DATE = datetime.datetime(datetime.MINYEAR, 1, 1)
            dcm_date = parser.parse(str(DEFAULT_DATE))
        #
        if approval_status.beamset_approved:
            current_time = parser.parse(str(rso.beamset.Review.ReviewTime))
        else:
            try:
                # Use last saved date if plan not approved
                current_time = parser.parse(str(rso.beamset.ModificationInfo.ModificationTime))
            except AttributeError:
                current_time = datetime.datetime.now()

        elapsed_days = (current_time - dcm_date).days

        if elapsed_days <= tolerance:
            message_str = "Exam {} acquired {} within {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days,
                        current_time.date())
            pass_result = PASS
        else:
            message_str = "Exam {} acquired {} GREATER THAN {} days ({} days) of Plan Date {}" \
                .format(rso.exam.Name, dcm_date.date(), tolerance, elapsed_days,
                        current_time.date())
            pass_result = FAIL
    else:
        message_str = "Exam {} has no apparent study date!".format(rso.exam.Name)
        pass_result = ALERT
    return pass_result, message_str
