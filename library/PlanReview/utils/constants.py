# KEYS TO DEFINE WHICH CHECKBOXES TO INCLUDE
REPLACED = 'Replaced'

# KEYS TO BE USED IN OUTPUT
KEY_SIMULATION_DATA = '-SIMULATION_DATA-'
KEY_SITE_SELECT = '-SITE_SELECT-'
KEY_PROTOCOL_SELECT = '-PROTOCOL_SELECT-'
KEY_ORDER_SELECT = '-ORDER_SELECT-'
KEY_SIM_DATE = '-SIMULATION_DATE-'  # Key for the preplan tab simulation date
KEY_SLICES = '-SCAN_SLICES-'  # Key for the preplan tab scan slices
KEY_TX_INST_SET = '-TREATMENT_INSTRUCTIONS-'
KEY_TX_INST = '-INSTRUCTION-'
KEY_IMAGING_FREQ = '-IMAGING_FREQUENCY-'
KEY_TREAT_FREQ = '-TREATMENT_FREQUENCY-'
KEY_FRACTIONS = '-N_FRACTIONS-'
KEY_BEAMSET = '-BEAMSET-'
KEY_BEAMSET_SELECT = '-BEAMSET_SELECT-'
KEY_CHECK = '-CHECK-'
KEY_USER_COMMENT = '-USER_COMMENT-'
KEY_IMD = '-IMPLANTED_MEDICAL_DEVICE-'
KEY_PRIOR_RT = '-PRIOR_RADIOTHERAPY-'
KEY_TESTS = '-TESTS-'
KEY_HEADER = '-HEADER-'
KEY_QA = '-QA_FORM-'
#
# All Text keys will just add 'TEXT-' to the input key. e.g. '-INSTRUCTION-TEXT'
KEY_RADIO = '-RADIO-'
KEY_COMBO = '-COMBO-'
KEY_INPUT_TEXT = '-INPUT_TEXT-'
KEY_CHECKBOX = '-CHECKBOX-'
KEY_BEAMSET_COUNT = KEY_BEAMSET + '-COUNT-'
KEY_BEAMSET_DOSE = KEY_BEAMSET + '-DOSE-'
KEY_BEAMSET_FRACTION_DOSE = KEY_BEAMSET + '-FRACTION_DOSE-'
KEY_BEAMSET_TARGET_NAME = KEY_BEAMSET + '-TARGET_NAME'
KEY_BEAMSET_TARGET_COUNT = KEY_BEAMSET + '-TARGET_COUNT-'
KEY_BEAMSET_FRACTION_COUNT = KEY_BEAMSET + KEY_FRACTIONS
KEY_SIDE_PANEL = '-SIDE_PANEL-'

#
# These probably won't be used outside this program
KEY_T = '-TEXT-'
KEY_D = '-DEFAULT-'
KEY_O = '-OPTIONS-'
KEY_F = '-FRAME-'

#
# Output Keys
KEY_AUTO_FAIL = '-AUTOMATED_FAILED_TESTS-'
KEY_AUTO_PASS = '-AUTOMATED_PASSING_TESTS-'
KEY_OUT_MESSAGE = '-MESSAGE-'
KEY_AUTOMATED_TESTS = '-AUTOMATED_TESTS-'
KEY_STATUS = '-STATUS-'
KEY_AUTO_REVIEW_DATE = '-AUTOMATION_REVIEW_DATE-'
KEY_REVIEW_TYPE = '-REVIEW_TYPE-'
KEY_AUTOMATION = '-AUTOMATION_INFORMATION-'
KEY_OUT_COMMENT = '-COMMENT-'
KEY_PROCEED_REVISE = "-PROCEED_REVISE-"
KEY_DOSE = "-DOSE-"
KEY_QI_INFO = "-QI_ISSUE-"  # Used in the side panel to display any quality improvement suggestions
KEY_REVISION_INFO = "-REASON_FOR_REVISION-"  # Used in the side panel to display the reason for revision
#
# Used in the side panel for Dosimetry review
KEY_REVISION_NUMBER = f'{KEY_DOSE}-REVISION_NUMBER-'  # Used in the side panel to display the number of revisions
KEY_DOSE_REVISION = f'{KEY_DOSE}-REVISION-'  # Used in the side panel to display the dose revision
KEY_DOSE_REVISION_INFO = f'{KEY_DOSE}-REVISION_INFO-'  # Used in the side panel to display the reason for revision
KEY_DOSE_QI = f'{KEY_DOSE}-QI-'  # Used in the side panel to display any dose quality improvement suggestions
KEY_DOSE_QI_INFO = f'{KEY_DOSE}-QI_INFO-'  # Used in the side panel to display any dose quality improvement suggestions
#
KEY_OUT_ICON = '-ICON-'
KEY_OUT_TEST = '-TEST_NAME-'
KEY_OUT_DESC = '-TEST_DESC-'
KEY_OUT_OPTIONS = '-TEST_OPTIONS-'
KEY_OUT_TAB = '-REVIEW_TAB-'
KEY_OUT_RESULT = '-RESULT-'
KEY_OUT_TEST_SOURCE = '-TEST_SOURCE-'
SOURCE_USER = 'Human Test'
SOURCE_AUTO = 'Automated Test'
KEY_OUT_DOMAIN_TYPE = '-DOMAIN_TYPE-'
KEY_OUT_DOMAIN_NAME = '-DOMAIN_NAME-'
KEY_OUT_CHECK_GROUP = '-CHECK_GROUP-'
KEY_PATIENT_ORIENTATION = '-PATIENT_ORIENTATION-'
KEY_DOSE_SITE = KEY_DOSE + '-SITE-'
KEY_DOSE_BILL = KEY_DOSE + '-BILL-'
#
# QA FORM KEYS
KEY_QA_FORM = '-QA_FORM-'
QA_FORM_AUTO = [
    {'KEY': 'report_date', 'TEXT': 'Date of Report'},
    {'KEY': 'patient_name', 'TEXT': 'Patient Name'},
    {'KEY': 'mr_num', 'TEXT': 'MR Number'},
    {'KEY': 'attending_physician', 'TEXT': 'Attending Physician'},
    {'KEY': 'where_in_proc_discovered',
     'TEXT': 'Where in the process was the event discovered?'},
    {'KEY': 'anatomical_site', 'TEXT': 'What anatomical site is being treated?',
     'OPTIONS': ['H&N', 'Brain', 'Thorax', 'Breast', 'Abdomen',
                 'GYN', 'GU', 'Skin', 'Extremities', 'GI', 'Pelvis',
                 'Other (Please specify)']
     },
    {'KEY': 'other_anatom_type_text', 'TEXT': 'Specify other site'},
    {'KEY': 'pertinent_treatment_technique',
     'TEXT': 'Treatment Technique Pertinent to Event',
     'OPTIONS': ['2D', '3D', 'IMRT/VMAT']},
    {'KEY': 'occurrence_time', 'TEXT': 'Time (nearest hour)'},
    {'KEY': 'am', 'TEXT': 'AM'},
    {'KEY': 'pm', 'TEXT': 'PM'},
    {'KEY': 'synopsis', 'TEXT': 'Brief Label/Synopsis'},
]
QA_FORM_MANUAL = [
    {'KEY': 'occurrence_choice', 'TEXT': 'Date of Occurrence',
     'OPTIONS': ['Simulation Date', 'Plan Date']},
    {'KEY': 'treatment_location', 'TEXT': 'Location',
     'OPTIONS': ['N/A', 'Room A', 'Room B', 'Room C', 'Room D', 'View Ray',
                 'East Clinic', 'HDR', 'CT', 'Johnson Creek']},
    {'KEY': 'where_in_proc_occured', 'TEXT': 'Where in the process did the event occur?',
     'OPTIONS': ['Pre-planning Imaging and Simulation', 'Treatment planning']},
    {'KEY': 'extent_of_issue', 'TEXT': 'Extent of issue',
     'OPTIONS': ['Near-miss', 'Reached the patient (Attending MD notified)',
                 'Reached the patient/Possible dosimetric implications (Attending MD notified)',
                 'Unsafe condition', 'Operational/Process Improvement']},
    {'KEY': 'description', 'TEXT': 'Describe the discrepancy below.'},
]

#
# Error messages
FAILED_AUTOMATED_TEST = "Fail: Comment Needed"
