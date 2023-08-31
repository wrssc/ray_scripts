from dateutil import parser
import datetime
from PlanReview.review_definitions import *
from PlanReview.utils.constants import KEY_SIM_DATE, KEY_SLICES


def get_dicom_date_and_slices(rso):
    """
    Retrieve the DICOM date and slice count from the dataset.

    Args:
        rso: An object representing the dataset.

    Returns:
        tuple: A tuple containing the DICOM date as a string (e.g. '2021-08-15') and the slice count as an integer.
    """
    dcm_data = list(
        rso.exam.GetStoredDicomTagValueForVerification(
            Group=0x0008, Element=0x0021).values())
    if dcm_data:
        try:
            dcm_date = parser.parse(dcm_data[0])
        except TypeError:
            # Enabled for anonymized patient testing
            DEFAULT_DATE = datetime.datetime(datetime.MINYEAR, 1, 1)
            dcm_date = parser.parse(str(DEFAULT_DATE))
    else:
        dcm_date = None

    dcm_slices = len(rso.exam.Series[0].ImageStack.SlicePositions)

    return dcm_date.date().strftime("%Y-%m-%d"), dcm_slices


def match_date(date1, date2):
    """
    Compare two dates to see if they match.

    Args:
        date1 (str): The first date as a string (e.g. '2021-08-15').
        date2 (str): The second date as a string (e.g. '2021-08-15').

    Returns:
        tuple: A tuple containing a boolean indicating if the dates match, and the parsed dates as strings.
    """
    parsed_date1 = parsed_date2 = None
    if date1:
        parsed_date1 = parser.parse(date1).date().strftime("%Y-%m-%d")
    if date2:
        parsed_date2 = parser.parse(date2).date().strftime("%Y-%m-%d")

    if parsed_date1 == parsed_date2:
        return True, parsed_date1, parsed_date2
    else:
        return False, parsed_date1, parsed_date2


def check_exam_date_and_slices(rso, **kwargs):
    """
    Check if the exam date and slice count from the user match the DICOM data.

    Args:
        rso: An object representing the dataset.
        **kwargs: A dictionary containing the 'VALUES' key with user-entered data.

    Returns:
        tuple: A tuple containing the pass_result (PASS, FAIL, or ALERT) and a message_str describing the result.
    """
    values = kwargs.get('VALUES')
    exam_date_user = values[KEY_SIM_DATE]
    slices_user = int(values[KEY_SLICES])

    # Get DICOM date and slices from the dataset
    dicom_date, dicom_slices = get_dicom_date_and_slices(rso)

    # Check if the user-entered exam date matches the DICOM date
    date_match, parsed_date_user, _ = match_date(exam_date_user, dicom_date)
    if date_match:
        message_str = f"Exam {rso.exam.Name} date {dicom_date} matches user-entered date"
        pass_result_date = PASS
    else:
        if parsed_date_user is None:
            message_str = f"User did not enter a study date for exam: {rso.exam.Name}"
            pass_result_date = ALERT
        else:
            message_str = f"Exam {rso.exam.Name} date {dicom_date} does not match user-entered date {parsed_date_user}"
            pass_result_date = FAIL

    # Check if the user-entered slice count matches the DICOM slice count
    if slices_user:
        if dicom_slices == slices_user:
            message_str += f". Slice count {dicom_slices} matches user-entered count"
            pass_result_slices = PASS
        else:
            message_str += f". Slice count {dicom_slices} does not match user-entered count {slices_user}"
            pass_result_slices = FAIL
    else:
        message_str += f". User did not enter slice count for exam: {rso.exam.Name}"
        pass_result_slices = ALERT

    # Determine the overall pass_result
    pass_nomogram = {
        (PASS, PASS): PASS,
        (PASS, FAIL): FAIL,
        (FAIL, FAIL): FAIL,
        (FAIL, PASS): FAIL,
        (FAIL, ALERT): FAIL,
        (ALERT, FAIL): FAIL,
        (PASS, ALERT): ALERT,
        (ALERT, PASS): ALERT,
    }
    pass_result = pass_nomogram[(pass_result_date, pass_result_slices)]

    return pass_result, message_str
