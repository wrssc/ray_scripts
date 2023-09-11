import re
from dateutil import parser
from typing import NamedTuple, Tuple, Optional

from PlanReview.review_definitions import PASS,FAIL


def match_date(date1, date2):
    p_date1 = p_date2 = None
    if date1:
        p_date1 = parser.parse(date1).date().strftime("%Y-%m-%d")
    if date2:
        p_date2 = parser.parse(date2).date().strftime("%Y-%m-%d")

    if p_date1 == p_date2:
        return True, p_date1, p_date2
    else:
        return False, p_date1, p_date2


def match_patient_name(name1, name2):
    # Case insensitive match on First and Last name (strip at ^)
    spl_1 = tuple(re.split(r'\^', name1))
    spl_2 = tuple(re.split(r'\^', name2))
    try:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE))\
           and bool(re.match(re.escape(spl_1[1]), re.escape(spl_2[1]), re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2
    except IndexError:
        if bool(re.match(r'^' + spl_1[0] + r'$', spl_2[0], re.IGNORECASE)):
            return True, name1, name2
        else:
            return False, name1, name2


def match_gender(gender1, gender2):
    # Match M/Male, F/Female, O/Other, Unknown/None
    if gender1:
        if 'Unknown' in gender1[0]:
            gender1 = None
        else:
            l1 = gender1[0]
    if gender2:
        l2 = gender2[0]
    if gender1 and gender2:
        if bool(re.match(l1, l2, re.IGNORECASE)):
            return True, gender1, gender2  # Genders Match
        else:
            return False, gender1, gender2  # Genders are different
    elif gender1:
        return False, gender1, gender2  # Genders are different
    elif gender2:
        return False, gender1, gender2  # Genders are different
    else:
        return False, gender1, gender2  # Genders not specified


def match_exactly(value1, value2):
    if value1 == value2:
        return True, value1, value2
    else:
        return False, value1, value2


def check_exam_data(rso: NamedTuple) -> Tuple[str, str]:
    """ Verify Examination DICOM Data
        Checks the RayStation plan information against the native CT DICOM header.

        Args:
            rso (ScriptObjects): Named tuple of ScriptObjects in Raystation containing [case,exam,plan,beamset,db].

        Returns:
            Tuple[str, str]: First element is the status (PASS/FAIL/ALERT),
                             Second element is the message string.

        Pseudocode:
            1. Extract 'do_physics_review' from kwargs
            2. Retrieve approval status from 'get_approval_info' function (to be implemented)
            3. Build the appropriate message string based on DICOM and RS data
            4. Determine the result (PASS/FAIL/ALERT)
            5. Return the result and message

        Test Patients:
            Pass: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: THI: Plan: Anal_THI
            Fail: Script_Testing^FinalDose: ZZUWQA_ScTest_06Jan2021: Case: VMAT: Plan: Pros_VMA
    """

    modality_tag = (0x0008, 0x0060)
    tags = {str(rso.patient.Name or ''): (0x0010, 0x0010, match_patient_name),
            str(rso.patient.PatientID or ''): (0x0010, 0x0020, match_exactly),
            str(rso.patient.Gender or ''): (0x0010, 0x0040, match_gender),
            str(rso.patient.DateOfBirth or ''): (0x0010, 0x0030, match_date)
            }
    get_rs_value = rso.exam.GetStoredDicomTagValueForVerification
    modality = list(get_rs_value(Group=modality_tag[0],
                                 Element=modality_tag[1]).values())[0]  # Get Modality
    message_str = "[DICOM vs RS]: "
    all_passing = True
    for k, v in tags.items():
        rs_tag = get_rs_value(Group=v[0], Element=v[1])
        for dicom_attr, dicom_val in rs_tag.items():
            match, rs, dcm = v[2](dicom_val, k)
            if match:
                message_str += "{}:[\u2713], ".format(dicom_attr)
            else:
                all_passing = False
                match_str = ' \u2260 '
                message_str += "{0}: [{1}:{2} {3} RS:{4}], " \
                    .format(dicom_attr, modality, dcm, match_str, rs)
    if all_passing:
        pass_result = PASS
    else:
        pass_result = FAIL
    return pass_result, message_str

