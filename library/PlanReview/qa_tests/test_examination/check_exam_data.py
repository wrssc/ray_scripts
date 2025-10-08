import re
from dateutil import parser
from typing import NamedTuple, Tuple
import unicodedata
from pydicom.valuerep import PersonName
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


def _norm(s: str) -> str:
    # Case-insensitive, preserve spaces/hyphens, trim padding per DICOM rules
    # Dedupes Unicode characters (e.g. full-width vs half-width), combining marks,
    # case folding, and trims leading/trailing whitespace
    return unicodedata.normalize("NFKC", s.strip()).casefold()


def _split_alpha(pn: PersonName) -> Tuple[str, str, str]:
    """
    Extract Alphabetic group only:
    Family^Given^Middle^(Prefix)^(Suffix)
    """
    # PersonName defaults to the first (= alphabetic) group.
    last   = pn.family_name or ""
    first  = pn.given_name or ""
    middle = pn.middle_name or ""
    return last, first, middle

def match_patient_name(
    name1: str,
    name2: str,
    require_middle: bool = False,
) -> Tuple[bool, str, str]:
    """
    Compare DICOM PN values using pydicom parsing.

    Args:
      name1: PN string (e.g., 'Last^First^Middle=...').
      name2: PN string.
      require_middle: If True, middle must match when present; else ignored.

    Returns:
      (match, original_name1, original_name2)
    """
    # Use pydicom to parse PersonName (PN) values.
    # Compare only the alphabetic group (first of up to 3 groups).
    # Ignore name suffixes (e.g., Jr, III) and prefixes (e.g., Dr, Mr).
    # Ignore case, leading/trailing whitespace, Unicode variants.
    # Ignore differences in middle name/initial unless require_middle is True.
    pn1 = PersonName(name1)
    pn2 = PersonName(name2)

    # Split into components.
    l1, f1, m1 = _split_alpha(pn1)
    l2, f2, m2 = _split_alpha(pn2)

    # Compare last and first names.
    same_last  = _norm(l1) == _norm(l2)
    same_first = _norm(f1) == _norm(f2)

    if not (same_last and same_first):
        return False, name1, name2

    if require_middle:
        return (_norm(m1) == _norm(m2)), name1, name2

    # Accept even if one middle is missing or differs.
    return True, name1, name2


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

