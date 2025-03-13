""" review_definitions.py
All functional assumptions made in deployment of the UW physics/dosimetry
check script

Version History:
1.0: 2021/06/01: Initial version
1.1 30Aug2024: Added the Q-FIX immobilization device to the list of supports
               * See Test Patient:
                    ZZUWQA_ScriptTesting_QFix
                    MR: ZZUWQA_20240830_ScriptTesting_RAB

"""
import os
import sys
from PlanReview.utils.constants import (
    REPLACED, KEY_OUT_DESC, KEY_OUT_TEST, KEY_OUT_DOMAIN_TYPE, KEY_OUT_OPTIONS,
    KEY_AUTOMATED_TESTS, KEY_STATUS, KEY_REVIEW_TYPE, KEY_AUTOMATION,
    KEY_AUTO_REVIEW_DATE, KEY_OUT_CHECK_GROUP)

# The location of the log directory
log_dir = os.getenv('LOG_DIR')
#
# Reporting from the review script
# Main directory for the RayStation scripts
RAYSCRIPTS_DIR = r"Q:\\RadOnc\RayStation\RayScripts"
#
# Directories for patient-specific data
OUTPUT_DIR = os.path.join(RAYSCRIPTS_DIR, "logs")

# Directory which contains raw clinical data and is not to be uploaded to GitHub
PROTECTED_DIR = os.path.join(RAYSCRIPTS_DIR, "Protect")
# From ARIA User Admin in the ARIA Web Portal Export all users to a
# non-GitSync directory
STAFF_XML_PATH = os.path.join(PROTECTED_DIR, "VAUsersandGroupsExport_03Sep2024.xml")

# Data gathering directory for collecting data for the review script
DATA_GATHERING_DIR = os.path.join(RAYSCRIPTS_DIR, "Reports", "DataGathering")

# Dosimetry safety-sheets, if needed, would go here. Not currently used.
DOSIMETRY_OUTPUT_DIR = os.path.join(RAYSCRIPTS_DIR, "Reports", "DosimetrySafetySheets")

# Error reports for the review script
ERROR_DIR = os.path.join(RAYSCRIPTS_DIR, "Reports", "Error_Reports", "ReviewScript")

# Quality Improvement Reports
QI_REPORTS_DIR = os.path.join(RAYSCRIPTS_DIR, "Reports", "Quality_Improvement_Reports")
DATAFILE_EVENT_LIST = os.path.join(DATA_GATHERING_DIR, "Incident_Reports.csv")
# Revision Reports
REVISION_REPORTS_DIR = os.path.join(RAYSCRIPTS_DIR, "Reports", "Revision_Reports")
#
DATAFILE_TARGET_MATCH_STATISTICS = os.path.join(DATA_GATHERING_DIR, "TargetMatchStatistics.csv")

# From the same directory pull the data needed for emailing reports
LOCAL_RAYSCRIPTS_DATA = os.path.join(PROTECTED_DIR, "UW_Email_Preferences.xml")
sys.path.append(LOCAL_RAYSCRIPTS_DATA)


protocol_folder = r'../../protocols'
institution_folder = r'UW'
PROTOCOL_DIR = os.path.join(os.path.dirname(__file__),
                            protocol_folder,
                            institution_folder)
# region Icons
# Icon Section
icon_dir = os.path.join(os.path.dirname(__file__), "guis\\icons")
RED_CIRCLE = os.path.join(icon_dir, "red_circle_icon.png")
GREEN_CIRCLE = os.path.join(icon_dir, "green_circle_icon.png")
YELLOW_CIRCLE = os.path.join(icon_dir, "yellow_circle_icon.png")
BLUE_CIRCLE = os.path.join(icon_dir, "blue_circle_icon.png")
UW_HEALTH_LOGO = os.path.join(icon_dir, "UW_Health_Logo.png")
# ICONS 90 px horizontal
ICON_SMALL_PRINT = os.path.join(icon_dir, "print_icon_small.png")
ICON_SMALL_FINAL = os.path.join(icon_dir, "final_icon_small.png")
ICON_SMALL_START = os.path.join(icon_dir, "start_icon_small.png")
ICON_SMALL_CANCEL = os.path.join(icon_dir, "cancel_icon_small.png")
ICON_SMALL_PAUSE = os.path.join(icon_dir, "pause_icon_small.png")
ICON_SMALL_SAVE = os.path.join(icon_dir, "save_icon_small.png")
ICON_SMALL_LOAD = os.path.join(icon_dir, "load_icon_small.png")
ICON_SMALL_ERROR = os.path.join(icon_dir, "error_icon_small.png")
ICON_SMALL_SCALE_ISODOSE = os.path.join(icon_dir, "scale_icon_small.png")  # 90 px
ICON_SMALL_MATERIAL = os.path.join(icon_dir, "material_icon_small.png")
ICON_SMALL_WINDOW_LEVEL = os.path.join(icon_dir, "windowlevel_icon_small.png")
ICON_SMALL_SUBMIT = os.path.join(icon_dir, "submit_icon_small.png")

# ICONS 110 px horizontal
ICON_PRINT = os.path.join(icon_dir, "print_icon.png")
ICON_FINAL = os.path.join(icon_dir, "final_icon.png")
ICON_START = os.path.join(icon_dir, "start_icon.png")
ICON_CANCEL = os.path.join(icon_dir, "cancel_icon.png")
ICON_PAUSE = os.path.join(icon_dir, "pause_icon.png")
ICON_SAVE = os.path.join(icon_dir, "save_icon.png")
ICON_LOAD = os.path.join(icon_dir, "load_icon.png")
ICON_ERROR = os.path.join(icon_dir, "error_icon.png")
ICON_CHECKER = os.path.join(icon_dir, "checker_icon.png")
ICON_SCALE_ISODOSE = os.path.join(icon_dir, "scale_icon.png")
ICON_MATERIAL = os.path.join(icon_dir, "material_icon.png")
ICON_WINDOW_LEVEL = os.path.join(icon_dir, "windowlevel_icon.png")
ICON_SUBMIT = os.path.join(icon_dir, "submit_icon.png")
# endregion
# region Results
PASS = "Pass"
FAIL = "Fail"
ALERT = "Alert"
NA = "Not Applicable"
# endregion

# Level keys
DOMAIN_TYPE = {
    'PATIENT_KEY': "PATIENT_LEVEL",
    'EXAM_KEY': "EXAM_LEVEL",
    'PLAN_KEY': "PLAN_LEVEL",
    'BEAMSET_KEY': "BEAMSET_LEVEL",
    'SANDBOX_KEY': "SANDBOX_LEVEL",
    'RX_KEY': "RX_LEVEL",
    'LOG_KEY': "LOG_LEVEL"}
# FRONTPAGE PROMPTS
FRONT_TAB = [
    "NUMBER OF SLICES",
    "SCAN DATE",
    "CT ORIENTATION",
    "Special instructions–FB, MIBH…",
    "Energy specified"
]
REVIEW_LEVELS = {
    'PREPLAN_DATA': 'Preplan',
    'PATIENT_MODEL': 'Patient Modeling',
    'PLAN_DATA': 'Plan Data',
    'PLAN_DESIGN': 'Plan Design',
    'OPTIMIZATION': 'Optimization',
    'PLAN_EVAL': 'Plan Evaluation',
    'ADAPTIVE': 'Adaptive',
    'PRIOR_RT': 'Prior Radiotherapy',
    'IMPLANTED_DEVICE': 'Implanted Devices',
    'MOBIUS': 'Mobius',
    'SANDBOX': 'Sandbox',
}
REVIEW_TYPES = {"Physics", "Dosimetry"}

# CHECKBOXES are qa_tests that must be manually performed for physics review
CHECK_BOXES_PHYSICS_REVIEW = {
    KEY_REVIEW_TYPE: 'General Physics Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [
        {
            KEY_OUT_TEST: 'ct_images_match',
            KEY_OUT_DESC: 'CT images match RayStation Modality/Patient Name/MRN',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_exam_data'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sept2023'}
        },
        {
            KEY_OUT_TEST: 'ct_images_number',
            KEY_OUT_DESC: 'Number of CT images matches CT simulation document',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.compare_exam_data_to_preplan'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sept2023'}
        },
        {
            KEY_OUT_TEST: 'ct_images_scan_datetime',
            KEY_OUT_DESC: 'CT images Scan Date/Time matches CT simulation report',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.compare_exam_data_to_preplan',
                                      'qa_tests.text_examination.compare_exam_date', ],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        },
        {
            KEY_OUT_TEST: 'ct_orientation',
            KEY_OUT_DESC: 'CT orientation matches report',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_axial_orientation',
                                      'qa_tests.test_examination.compare_patient_orientation_to_preplan'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '02Oct2023'}},
        {
            KEY_OUT_TEST: 'immobilization_protocol',
            KEY_OUT_DESC: 'Immobilization matches protocol and is reproducible',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Simulation consistent with intended treatment '
                                          'and accurately incorporated into treatment plan',
                                  'KEY': 'sim_consistent_accurate'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},

        },
        {
            KEY_OUT_TEST: 'no_artifacts',
            KEY_OUT_DESC: 'No significant imaging artifacts present',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Simulation consistent with intended treatment '
                                          'and accurately incorporated into treatment plan',
                                  'KEY': 'sim_consistent_accurate'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'special_instructions',
            KEY_OUT_DESC: 'Special instructions (FB, MIBH) are noted in treatment planning order',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Simulation consistent with intended treatment '
                                          'and accurately incorporated into treatment plan',
                                  'KEY': 'sim_consistent_accurate'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'slice_thickness',
            KEY_OUT_DESC: 'Slice thickness appropriate for plan type',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_slice_thickness'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'md_approved_mim',
            KEY_OUT_DESC: 'If contoured in MIM, MD approved session',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Data in MIM is consistent with treatment plan:',
                                  'KEY': 'mim_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mim_fusions',
            KEY_OUT_DESC: 'Fusions in MIM are accurate',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Data in MIM is consistent with treatment plan:',
                                  'KEY': 'mim_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mim_statistics_match',
            KEY_OUT_DESC: 'If contoured in MIM, Statistics/gross appearance matches RayStation',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Data in MIM is consistent with treatment plan:',
                                  'KEY': 'mim_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'tpo_contours',
            KEY_OUT_DESC: 'TPO listed contours are correctly interpolated',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Anatomical and target contours appear correct:',
                                  'KEY': 'contours_correct'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_contour_gaps'],
                KEY_STATUS: 'Extended - check in place to look for contours with gaps',
                KEY_AUTO_REVIEW_DATE: '03Oct2023'},
        },
        {
            KEY_OUT_TEST: 'no_stray_voxels',
            KEY_OUT_DESC: 'No stray voxels in the targets.',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Anatomical and target contours appear correct:',
                                  'KEY': 'contours_correct'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'contour_extents',
            KEY_OUT_DESC: 'Regions at risk near targets are contoured and sufficient for the plan',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Anatomical and target contours appear correct:',
                                  'KEY': 'contours_correct'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'ptv_retracted',
            KEY_OUT_DESC: 'PTV is retracted from skin at least 3mm',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Contours influencing dose calculation are correct:',
                                  'KEY': 'dose_contours_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'density_overrides_contoured',
            KEY_OUT_DESC: 'Density overrides are contoured',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Contours influencing dose calculation are correct:',
                                  'KEY': 'dose_contours_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'density_overrides',
            KEY_OUT_DESC: 'Material assignment is appropriate',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_support_material'],
                KEY_STATUS: 'Enhanced - check takes place on common supports, but not all override scenarios',
                KEY_AUTO_REVIEW_DATE: 'Needs Review',
            },
        },
        {
            # TODO: Consider deleting this. RS does not allow this.
            KEY_OUT_TEST: 'density_override_rois',
            KEY_OUT_DESC: 'Density override ROIs do not overlap',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Contours influencing dose calculation are correct:',
                                  'KEY': 'dose_contours_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'external_contour',
            KEY_OUT_DESC: 'External contour is set correctly and does not include couch',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'immobilization_devices',
            KEY_OUT_DESC: 'Immobilization devices and couch added as structures are added correctly',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_couch_type',
                                      'qa_tests.test_examination.check_couch_extent'],
                KEY_STATUS: 'Needs Review',
                KEY_AUTO_REVIEW_DATE: 'NA'
            },
        },
        {
            KEY_OUT_TEST: 'bolus_custom_devices',
            KEY_OUT_DESC: 'Bolus and custom devices are physically and dosimetrically realistic',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Contours influencing dose calculation are correct:',
                                  'KEY': 'dose_contours_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_bolus_included'],
                KEY_STATUS: 'Needs Review',
                KEY_AUTO_REVIEW_DATE: 'NA'
            },
        },
    ],
    REVIEW_LEVELS['PLAN_DATA']: [
        {
            KEY_OUT_TEST: 'plan_name_tpo',
            KEY_OUT_DESC: 'Plan Name is consistent with TPO',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Plan level data consistent and approved',
                                  'KEY': 'plan_level_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'plan_approved_md',
            KEY_OUT_DESC: 'Plan is approved by MD',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Plan level data consistent and approved',
                                  'KEY': 'plan_level_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_beamset_approved',
                                      'qa_tests.text_plan.check_plan_approved'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '02Oct2023'}
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'beam_names_correct',
            KEY_OUT_DESC: 'Beam Names are correct',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'SOP followed in beam configuration:',
                                  'KEY': 'sop_for_beams'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beams_single_machine',
            KEY_OUT_DESC: 'Beams are assigned to a single machine',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'SOP followed in beam configuration:',
                                  'KEY': 'sop_for_beams'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'isocenter_placement',
            KEY_OUT_DESC: 'Isocenter placement is appropriate',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_common_isocenter'],
                KEY_STATUS: 'Needs Review',
                KEY_AUTO_REVIEW_DATE: 'NA'
            },
        },
        {
            KEY_OUT_TEST: 'beams_not_through_mobile_objects',
            KEY_OUT_DESC: 'Beams do not treat through mobile objects (arms, chin, legs)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_no_fly',
                                      'qa_tests.test_examination.check_image_extent'],
                KEY_STATUS: 'Enhanced-No Fly Volume Checked, '
                            '-Image extent versus target extent checked',
                KEY_AUTO_REVIEW_DATE: '01Sep2023'}
        },
        {
            KEY_OUT_TEST: 'beam_apertures',
            KEY_OUT_DESC: 'Beam Apertures are reasonable',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'matched_field_junctions',
            KEY_OUT_DESC: 'Any matched field junctions are reviewed',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'prescription',
            KEY_OUT_DESC: 'Prescription matches TPO',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': "Prescription correct and correctly resolved by dose grid:",
                                  'KEY': 'rx_and_grid_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_fraction_size'],
                KEY_STATUS: 'Enhanced: 5Gy x 4, and 1Gy x 8 transcription error reviewed',
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {
            KEY_OUT_TEST: 'prescription_volume',
            KEY_OUT_DESC: 'Prescription is based on volume (preferred) or isodose line',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': "Prescription correct and correctly resolved by dose grid:",
                                  'KEY': 'rx_and_grid_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'dose_grid_resolution',
            KEY_OUT_DESC: 'Dose grid Resolution is 2mm or less',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': "Prescription correct and correctly resolved by dose grid:",
                                  'KEY': 'rx_and_grid_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_dose_grid'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {
            KEY_OUT_TEST: 'dose_grid_coverage',
            KEY_OUT_DESC: 'Dose Grid covers patient and support structures',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': "Prescription correct and correctly resolved by dose grid:",
                                  'KEY': 'rx_and_grid_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },

    ],
    REVIEW_LEVELS['OPTIMIZATION']: [],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {
            KEY_OUT_TEST: 'dose_distribution',
            KEY_OUT_DESC: 'Dose distribution looks reasonable',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Dose distribution and clinical goals consistent with intended treatment:',
                                  'KEY': 'dose_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'tpo_goals_constraints',
            KEY_OUT_DESC: 'TPO goals and constraints are entered in clinical '
                          'goals and reasonably addressed',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Dose distribution and clinical goals consistent with intended treatment:',
                                  'KEY': 'dose_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['ADAPTIVE']: [],
    REVIEW_LEVELS['IMPLANTED_DEVICE']: [
        {
            KEY_OUT_TEST: 'imd_plan_review',
            KEY_OUT_DESC: 'Review treatment modality, dose to the device and '
                          'device distance to the nearest collimated field edge',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'imd_consult',
            KEY_OUT_DESC: 'Verify information entered in IMD Physics '
                          'Consult document is accurate',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'imd_supervised',
            KEY_OUT_DESC: 'Complete and sign the IMD Physics Consult document, '
                          'set the “Supervised By” field to attending MD.',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'imd_in_vivo',
            KEY_OUT_DESC: 'Determine if in vivo dosimetry measurement is required',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['PLAN_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },

    ],
    REVIEW_LEVELS['PRIOR_RT']: [
        {
            KEY_OUT_TEST: 'prior_rt_fusions',
            KEY_OUT_DESC: 'Review fusions done for prior RT (if not already done by a POD)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'prior_rt_dose',
            KEY_OUT_DESC: 'Review the dose accumulation, including TPO goals for prior RT',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'prior_rt_doc',
            KEY_OUT_DESC: 'Verify prior RT document is completed and attending MD in “Supervised by”',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['MOBIUS']: [
        {
            KEY_OUT_TEST: 'gamma_review',
            KEY_OUT_DESC: 'Review gamma: 5%/3mm > 90%',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': '2nd check calculation acceptable:',
                                  'KEY': 'mobius_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'review_dose_acs',
            KEY_OUT_DESC: 'Review dose in A, C, S',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': '2nd check calculation acceptable:',
                                  'KEY': 'mobius_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_info_mobius',
            KEY_OUT_DESC: 'Beam information in Mobius Clearance/deliverable are green',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': '2nd check calculation acceptable:',
                                  'KEY': 'mobius_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mobius_raystation_dose',
            KEY_OUT_DESC: 'Mobius RayStation Dose difference is consistent with report',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': '2nd check calculation acceptable:',
                                  'KEY': 'mobius_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        #
        # Removed September 2023 per Physics group
        # {
        #     KEY_OUT_TEST: 'couch_removal_height',
        #     KEY_OUT_DESC: 'Confirm couch removal height',
        #     KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
        #     KEY_OUT_OPTIONS: 'Yes,No',
        #     KEY_AUTOMATION: {},
        # },
        # {
        #     KEY_OUT_TEST: 'target_identification',
        #     KEY_OUT_DESC: 'Target identification is correct',
        #     KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
        #     KEY_OUT_OPTIONS: 'Yes,No',
        #     KEY_AUTOMATION: {},
        # },
        # {
        #     KEY_OUT_TEST: 'structure_classification',
        #     KEY_OUT_DESC: 'Classification of each structure is correct',
        #     KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
        #     KEY_OUT_OPTIONS: 'Yes,No',
        #     KEY_AUTOMATION: {},
        # },
    ],
    REVIEW_LEVELS['SANDBOX']: [
        {
            KEY_OUT_TEST: 'sandbox_tests',
            KEY_OUT_DESC: 'Did these experimental tests work for this case?',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['SANDBOX_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
}
CHECK_BOXES_PHYSICS_REVIEW_3D = {
    KEY_REVIEW_TYPE: '3D Conformal Physics Review',
    REVIEW_LEVELS['PLAN_DATA']: [],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'sim_fiducials_alignment',
            KEY_OUT_DESC: 'SimFiducials localization point alignment matches BBs,'
                          ' or AlignRT is noted in CT Sim',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_localization'],
                KEY_STATUS: 'Enhanced - Localization checked for existence but not correctness',
                KEY_AUTO_REVIEW_DATE: '02Oct2023'
            },
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'modality_energy',
            KEY_OUT_DESC: 'Modality and Energy match TPO',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beams_correct_isocenter',
            KEY_OUT_DESC: 'Beams are assigned to the correct isocenter',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'btv_avoid_mlc',
            KEY_OUT_DESC: 'BTV and AVOID are used to define MLC shapes',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'SOP followed in beam configuration:',
                                  'KEY': 'sop_for_beams'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'wedges_placement',
            KEY_OUT_DESC: 'Any wedges are intuitively placed',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_edw_field_size'],
                KEY_STATUS: 'Enhanced - EDW field size compliance checked',
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {
            KEY_OUT_TEST: 'beam_flash',
            KEY_OUT_DESC: 'Beam Flash is present on breast or areas with potential'
                          ' out-of-field movement',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_mu_reasonable',
            KEY_OUT_DESC: 'Beam MU is reasonable',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_edw_mu'],
                KEY_STATUS: 'Enhanced - EDW MU compliance checked',
                KEY_AUTO_REVIEW_DATE: '02Oct2023',
            },
        },
        {
            KEY_OUT_TEST: 'beam_divergence',
            KEY_OUT_DESC: 'Beam divergence is appropriate',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['MOBIUS']: []
}
CHECK_BOXES_PHYSICS_REVIEW_VMAT = {
    KEY_REVIEW_TYPE: 'VMAT Physics Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'sim_fiducials_alignment',
            KEY_OUT_DESC: 'SimFiducials localization point alignment matches BBs,'
                          ' or AlignRT is noted in CT Sim',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_localization'],
                KEY_STATUS: 'Enhanced - Localization checked for existence but not correctness',
                KEY_AUTO_REVIEW_DATE: '02Oct2023'
            },
        },
        # {
        #    KEY_OUT_TEST: 'ptv_retracted',
        #    KEY_OUT_DESC: 'PTV is retracted from skin at least 3mm',
        #    KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
        #    KEY_OUT_OPTIONS: 'Yes,No',
        #    KEY_AUTOMATION: {},
        # },
        {
            KEY_OUT_TEST: 'prv_volumes',
            KEY_OUT_DESC: 'PRV volumes are drawn for serial OARs',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_prv_status'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'modality_energy',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_DESC: 'Modality, Energy match TPO',
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beams_correct_isocenter',
            KEY_OUT_DESC: 'Beams are assigned to the correct isocenter',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'arc_geometry',
            KEY_OUT_DESC: 'Arc Geometry: Arcs match SmartArc Tolerance Tables',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'collimator_angle',
            KEY_OUT_DESC: 'Collimator angle differs on arcs',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'SOP followed in beam configuration:',
                                  'KEY': 'sop_for_beams'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'jaw_opening',
            KEY_OUT_DESC: 'Jaw opening is sensible for target size',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },

        {
            KEY_OUT_TEST: 'beam_mu_reasonable',
            KEY_OUT_DESC: 'Beam MU is reasonable',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        # Replaced on 03Oct2023 per Physics group by PRIOR_RT page
        # {
        #     KEY_OUT_TEST: 'overlap_prior_rt',
        #     KEY_OUT_DESC: 'Overlap with prior RT is reviewed',
        #     KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
        #     KEY_OUT_OPTIONS: 'Yes,No',
        #     KEY_AUTOMATION: {},
        # },
        {
            KEY_OUT_TEST: 'plan_setup',
            KEY_OUT_DESC: 'Dependency settings of beam set appropriate'
                          ' (background/co-optimization)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': "Prescription correct and correctly resolved by dose grid:",
                                  'KEY': 'rx_and_grid_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {
            KEY_OUT_TEST: 'objective_type',
            KEY_OUT_DESC: 'Objective type is correct for targets/OAR',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'VMAT-IMRT Optimization performed:',
                                  'KEY': 'vmat_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'arc_protect_blocking',
            KEY_OUT_DESC: 'Arc protect or dosimetric Blocking is used to avoid'
                          ' low-reproducibility objects',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'VMAT-IMRT Optimization performed:',
                                  'KEY': 'vmat_imrt_opt'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'optimization_settings',
            KEY_OUT_DESC: 'Optimization settings: 2-degree gantry spacing',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_control_point_spacing'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023',
            },
        },
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['MOBIUS']: []
}
CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS = {
    KEY_REVIEW_TYPE: 'Electron Physics Review',
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'modality_energy_matches_tpo',
            KEY_OUT_DESC: 'Modality, Energy matches TPO',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beams_assigned_correct_isocenter',
            KEY_OUT_DESC: 'Beams assigned to correct isocenter',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_ssd_set_correctly',
            KEY_OUT_DESC: 'Beam SSD set correctly 100 SSD for A6, 105 SSD otherwise',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_source_to_surface',
            KEY_OUT_DESC: 'Beam source to surface should be to skin if no bolus,'
                          ' to surface if bolus',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_reasonably_en_face',
            KEY_OUT_DESC: 'Beam is reasonably en face',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'cutout_representation',
            KEY_OUT_DESC: 'Physical cutout dimensions correct for 95 cm source-to-cutout distance',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam modifiers and collimation verified:',
                                  'KEY': 'modifiers_collimation_verified'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_mu_reasonable',
            KEY_OUT_DESC: 'Beam MU is reasonable',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Beam placement and characteristics are verified for accuracy and safety:',
                                  'KEY': 'beams_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {
            KEY_OUT_TEST: 'histories_per_cm2',
            KEY_OUT_DESC: 'Number of histories ≥500K per cm2',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Dose distribution and clinical goals consistent with intended treatment:',
                                  'KEY': 'dose_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'electron_wires',
            KEY_OUT_DESC: "Wire ROIs don't overlap external",
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Contours influencing dose calculation are correct:',
                                  'KEY': 'dose_contours_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'sim_fiducials_alignment',
            KEY_OUT_DESC: 'SimFiducials localization point alignment matches BBs,'
                          ' or AlignRT is noted in CT Sim',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_localization'],
                KEY_STATUS: 'Enhanced - Localization checked for existence but not correctness',
                KEY_AUTO_REVIEW_DATE: '02Oct2023'
            },
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}
CHECK_BOXES_PHYSICS_REVIEW_TOMO3D = {
    KEY_REVIEW_TYPE: '3D Conformal TomoTherapy Physics Review',
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'tomocouch_inserted_correctly',
            KEY_OUT_DESC: 'TomoCouch is inserted correctly',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'simfiducials_localization_alignment',
            KEY_OUT_DESC: 'SimFiducials localization point alignment matches BBs',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'patient_shifts_no_collision',
            KEY_OUT_DESC: 'Patient shifts will not lead to a collision',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'patient_shifts_target_in_fov',
            KEY_OUT_DESC: 'Patient shifts will place target in '
                          'MVCT Field of View (FOV)',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'targets_separated_by_7_cm',
            KEY_OUT_DESC: 'Targets separated by > 7 cm apart are treated'
                          ' with separate beamsets',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_modulation_factor',
            KEY_OUT_DESC: 'Beam Modulation Factor < 2.2',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Planning technique used:',
                                  'KEY': 'tomo_3d'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_mod_factor'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {

            KEY_OUT_TEST: 'beam_field_width',
            KEY_OUT_DESC: 'Beam Field Width is 5.05 cm',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Planning technique used:',
                                  'KEY': 'tomo_3d'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_pitch',
            KEY_OUT_DESC: 'Beam Pitch is 0.287',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Planning technique used:',
                                  'KEY': 'tomo_3d'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treatment_isocenter_lateral',
            KEY_OUT_DESC: 'Treatment Isocenter lateral < 2 cm',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_tomo_isocenter'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {
            KEY_OUT_TEST: 'optimization_on_targets_external',
            KEY_OUT_DESC: 'Optimization on targets and External only',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Optimization performed:',
                                  'KEY': 'tomo_3d_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'protect_entry_exit_blocking',
            KEY_OUT_DESC: 'Protect: "Entry" and "Entry/Exit" used to '
                          'block appropriate OARs',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Optimization performed:',
                                  'KEY': 'tomo_3d_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'fov_artifacts_addressed_blocked',
            KEY_OUT_DESC: 'FOV artifacts are addressed or blocked',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Optimization performed:',
                                  'KEY': 'tomo_3d_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_fov_overlap_external'],
                KEY_STATUS: 'Extended - automated test for FOV overlap with external or couch',
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        },
        {
            KEY_OUT_TEST: 'low_reproducibility_anatomy_blocked',
            KEY_OUT_DESC: 'Low reproducibility anatomy is blocked '
                          'with a margin of > 2 cm',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Optimization performed:',
                                  'KEY': 'tomo_3d_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'jaw_mode_dynamic',
            KEY_OUT_DESC: 'Jaw mode is Dynamic',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo3D Optimization performed:',
                                  'KEY': 'tomo_3d_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {
            KEY_OUT_TEST: 'plan_dvh_goals_identical',
            KEY_OUT_DESC: 'Plan DVH and goals are identical to the _Auto plan',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Dose distribution and clinical goals consistent with intended treatment:',
                                  'KEY': 'dose_ok'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    # 'Transfer Plan': [
    #     {
    #     KEY_OUT_TEST: 'transfer_plan_dose_distribution',
    #      KEY_OUT_DESC: 'Transfer plan dose distribution and DVHs reviewed,'
    #                   ' match with Primary Plan',
    #      KEY_OUT_OPTIONS: 'Yes,No',
    # KEY_AUTOMATION: {},
    # },
    #     {
    #     KEY_OUT_TEST: 'transfer_plan_locked_approved',
    #      KEY_OUT_DESC: 'Transfer plan is locked and approved by Dosimetry'
    #                   ' in RayStation',
    #      KEY_OUT_OPTIONS: 'Yes,No',
    # KEY_AUTOMATION: {},
    # },
    # ],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}
CHECK_BOXES_PHYSICS_REVIEW_TOMO = {
    KEY_REVIEW_TYPE: 'IMRT TomoTherapy Physics Review',
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'tomocouch_inserted_correctly',
            KEY_OUT_DESC: 'TomoCouch is inserted correctly',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'simfiducials_localization_alignment',
            KEY_OUT_DESC: 'SimFiducials localization point alignment matches BBs',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    # 'Transfer Plan': [
    #     {
    #
    #     KEY_OUT_TEST: 'transfer_plan_dose_distribution',
    #      KEY_OUT_DESC: 'Transfer plan dose distribution and DVHs reviewed,'
    #                   ' match with Primary Plan',
    #      KEY_OUT_OPTIONS: 'Yes,No',
    #      KEY_AUTOMATION: {},
    # },
    #     {
    #     KEY_OUT_TEST: 'transfer_plan_locked_approved',
    #      KEY_OUT_DESC: 'Transfer plan is locked and approved by Dosimetry'
    #                   ' in RayStation',
    #      KEY_OUT_OPTIONS: 'Yes,No',
    # KEY_AUTOMATION: {}      
    # },
    # ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'isocenter_lateral_position',
            KEY_OUT_DESC: 'Isocenter lateral position is <2 cm, '
                          'or a patient alert to break indexing is created',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_tomo_isocenter'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        },
        {
            KEY_OUT_TEST: 'patient_shifts_no_collision',
            KEY_OUT_DESC: 'Patient shifts will not lead to a collision',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'patient_shifts_target_in_fov',
            KEY_OUT_DESC: 'Patient shifts place target in MVCT Field of View (FOV)',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treatment_time_less_than_600',
            KEY_OUT_DESC: 'Treatment time is < 600 s '
                          'or explained in Dosimetry Safety Sheet',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'TomoTherapy-specific elements are verified:',
                                  'KEY': 'tomo_verified'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {
            KEY_OUT_TEST: 'objective_type_correct',
            KEY_OUT_DESC: 'Objective type is correct for targets/OAR',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'protect_entry_exit_blocking',
            KEY_OUT_DESC: 'Protect: "Entry" and "Entry/Exit" used'
                          ' to block appropriate OARs',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'fov_artifacts_addressed_blocked',
            KEY_OUT_DESC: 'FOV artifacts are addressed or blocked',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_fov_overlap_external'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        },
        {
            KEY_OUT_TEST: 'low_reproducibility_anatomy_blocked',
            KEY_OUT_DESC: 'Low reproducibility anatomy is blocked'
                          ' with a margin of > 2 cm',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'review_beams_eye_view',
            KEY_OUT_DESC: "Review Beam's eye view",
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}
# SAFETY REVIEWS FOR DOSE
CHECK_BOXES_DOSIMETRY_SAFETY = {
    KEY_REVIEW_TYPE: 'General Dosimetry Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [
        {
            KEY_OUT_TEST: 'primary_image_set',
            KEY_OUT_DESC: 'Correct image set used as primary',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'patient_info',
            KEY_OUT_DESC: 'Correct patient information (name, MRN, image #, orientation)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_exam_data'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sept2023'}
        },
        {
            KEY_OUT_TEST: 'ivdt_table',
            KEY_OUT_DESC: 'Correct IVDT table used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'case_data',
            KEY_OUT_DESC: 'Case data entered to match Course # in Aria, treatment site, MD',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'slice_thickness',
            KEY_OUT_DESC: 'Slice thickness appropriate for plan type',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_slice_thickness'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'approved_structure_set',
            KEY_OUT_DESC: 'MD approved structure set',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'contours_cleaned',
            KEY_OUT_DESC: 'Contours interpolated and cleaned',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'structure_template_loaded',
            KEY_OUT_DESC: 'Structure Template Loaded: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'ptv_expansions',
            KEY_OUT_DESC: 'PTV expansions per table',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'sim_fiducial',
            KEY_OUT_DESC: 'Sim Fiducial point set to match BB location',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_localization'],
                KEY_STATUS: 'Enhanced - Localization checked for existence but not correctness',
                KEY_AUTO_REVIEW_DATE: '02Oct2023'
            },
        },
        {
            KEY_OUT_TEST: 'ct_cutoff',
            KEY_OUT_DESC: 'CT cutoff addressed',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_fov_overlap_external',
                                      'qa_tests.test_examination.check_image_extent'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023',
            },
        },
    ],
    REVIEW_LEVELS['PLAN_DATA']: [
        {
            KEY_OUT_TEST: 'plan_name_tpo',
            KEY_OUT_DESC: 'Plan Name is consistent with TPO',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_CHECK_GROUP: {},
            # {'TEXT': 'Plan level data consistent and approved',
            #                  'KEY': 'plan_level_consistent'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'plan_beam_names',
            KEY_OUT_DESC: 'Plan and beam set names match treatment site',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'machine_correct',
            KEY_OUT_DESC: 'Machine correct: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'dose_grid_resolution',
            KEY_OUT_DESC: 'Dose grid resolution set to 0.2',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_dose_grid'],
                KEY_STATUS: 'Needs Review',
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {
            KEY_OUT_TEST: 'isodose_display',
            KEY_OUT_DESC: 'Isodose line display set to Absolute values',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'clinical_goals',
            KEY_OUT_DESC: 'Clinical goals entered',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'final_dose_calc_script',
            KEY_OUT_DESC: 'Final Dose calculation script used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['ADAPTIVE']: [],
    REVIEW_LEVELS['IMPLANTED_DEVICE']: [],
    REVIEW_LEVELS['PRIOR_RT']: [],
    REVIEW_LEVELS['MOBIUS']: [],
    REVIEW_LEVELS['SANDBOX']: [],
}
CHECK_BOXES_DOSIMETRY_SAFETY_3D = {
    KEY_REVIEW_TYPE: '3D Conformal Dosimetry Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'highz_artifacts',
            KEY_OUT_DESC: 'High-Z artifacts & density overrides addressed: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'couch_structure',
            KEY_OUT_DESC: 'TrueBeam couch structure present and set to correct height',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'btv_created',
            KEY_OUT_DESC: 'BTV created and derived based on PTV',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_template_used',
            KEY_OUT_DESC: 'Beam template used: Choose One ',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'no_low_repro_objects',
            KEY_OUT_DESC: 'Beam(s) do not pass through low-reproducibility objects (ie: head of '
                          'table)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treat_protect',
            KEY_OUT_DESC: 'Treat & Protect settings used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'prescription_type',
            KEY_OUT_DESC: 'Prescription based on volume or isodose line',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ]
}
CHECK_BOXES_DOSIMETRY_SAFETY_VMAT = {
    KEY_REVIEW_TYPE: 'VMAT Dosimetry Review',
    REVIEW_LEVELS['PATIENT_MODEL']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'planning_structure_script',
            KEY_OUT_DESC: 'Generate planning structure script used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'dose_grid_resolution_SBRT',
            KEY_OUT_DESC: 'Dose grid resolution set to 0.2 (or 0.15 for SBRT)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_dose_grid'],
                KEY_STATUS: 'Needs Review',
                KEY_AUTO_REVIEW_DATE: '01Sep2023',
            },
        },
        {
            KEY_OUT_TEST: 'isocenter_lateral_offset',
            KEY_OUT_DESC: 'Isocenter lateral offset < 5 cm for plans using full arcs',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {
            KEY_OUT_TEST: 'clinical_goals_script_tpo',
            KEY_OUT_DESC: 'Clinical goals script used and matches TPO template name',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treat_setting',
            KEY_OUT_DESC: 'Treat setting used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'automated_plan_optimization',
            KEY_OUT_DESC: 'Automated Plan Optimization script used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'beam_weights',
            KEY_OUT_DESC: 'Beam weights > 5%',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'couch_angle_rpm',
            KEY_OUT_DESC: 'Couch angle < 45 degrees for RPM gating plans',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ]
}
CHECK_BOXES_DOSIMETRY_SAFETY_ELECTRONS = {
    KEY_REVIEW_TYPE: 'Electron Dosimetry Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'density_overrides',
            KEY_OUT_DESC: 'Density overrides set appropriately and do not overlap external',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {

            KEY_OUT_TEST: 'couch_structure',
            KEY_OUT_DESC: 'TrueBeam couch structure present and set to correct height',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_CHECK_GROUP: {'TEXT': 'External geometry and support structures are correct:',
                                  'KEY': 'external_and_supports'},
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'en_face_beam_angle',
            KEY_OUT_DESC: 'En face beam angle used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'statistical_uncertainty',
            KEY_OUT_DESC: 'Dose Statistical uncertainty < 1%',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'ssd_cones',
            KEY_OUT_DESC: 'SSD = 100 cm for 6x6 cone or 105 for all other cones, SSD to skin for no '
                          'bolus or to surface for bolus',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'cutout_shape',
            KEY_OUT_DESC: 'Cutout: Shape: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'cutout_name',
            KEY_OUT_DESC: 'Cutout Name is accessory code',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'bolus',
            KEY_OUT_DESC: 'Bolus: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'prescription_based_volume',
            KEY_OUT_DESC: 'Prescription based on volume',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'printing_cutout',
            KEY_OUT_DESC: 'Printing: cutout printed to correct scale factor of 1.00',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mobius_quickcalc_water_phantom',
            KEY_OUT_DESC: 'Mobius QuickCalc: Water phantom QA plan created',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mobius_quickcalc_cutout_dimensions',
            KEY_OUT_DESC: 'Mobius QuickCalc: Cutout dimensions correct',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mobius_quickcalc_dmax_dose',
            KEY_OUT_DESC: 'Mobius QuickCalc: Dmax dose entered into QuickCalc',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'mobius_quickcalc_agreement',
            KEY_OUT_DESC: 'Mobius QuickCalc: Agreement within 5%',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ]
}
CHECK_BOXES_DOSIMETRY_SAFETY_TOMO = {
    KEY_REVIEW_TYPE: 'TomoTherapy Dosimetry Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'generate_planning_structure_script',
            KEY_OUT_DESC: 'Generate planning structure script used',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'targets_retracted',
            KEY_OUT_DESC: 'Targets retracted 3 mm from surface (PTV eval used)',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'tomo_couch_structure',
            KEY_OUT_DESC: 'Tomo couch structure present and set to correct height',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'beam_added_no_collision',
            KEY_OUT_DESC: 'Beam added with no collision via machine geometry',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'isocenter_offsets',
            KEY_OUT_DESC: 'Isocenter lateral offset < 3 cm and In/Out offset < 18 cm',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_beamset.check_tomo_isocenter'],
                KEY_STATUS: REPLACED,
                KEY_AUTO_REVIEW_DATE: '03Oct2023'}
        }],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {KEY_OUT_TEST: 'clinical_goals_script',
         KEY_OUT_DESC: 'Clinical goals script used and matches TPO template name',
         KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                               'KEY': 'tomo_imrt_opt'},
         KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
         KEY_OUT_OPTIONS: 'Yes,No',
         KEY_AUTOMATION: {},
         },
        {
            KEY_OUT_TEST: 'dynamic_jaws',
            KEY_OUT_DESC: 'Dynamic Jaws used on 2.5 and 5 cm plans',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'field_width',
            KEY_OUT_DESC: 'Field width < Target length',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'pitch',
            KEY_OUT_DESC: 'Pitch appropriate for plan',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'modulation_factor',
            KEY_OUT_DESC: 'Modulation factor appropriate for plan',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treatment_time',
            KEY_OUT_DESC: 'Treatment time appropriate for plan',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'structures_blocked',
            KEY_OUT_DESC: 'Structures are blocked per protocol if applicable',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'plan_optimization_script',
            KEY_OUT_DESC: 'Plan optimization script used',
            KEY_OUT_CHECK_GROUP: {'TEXT': 'Tomo Optimization correctly performed:',
                                  'KEY': 'tomo_imrt_opt'},
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['ADAPTIVE']: [
        {

            KEY_OUT_TEST: 'idms_adaptive',
            KEY_OUT_DESC: 'iDMS Adaptive: treated fractions discontinued in new plan',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ]
}
CHECK_BOXES_DOSIMETRY_SAFETY_TOMO3D = {
    KEY_REVIEW_TYPE: '3D Conformal TomoTherapy Dosimetry Review',
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {
            KEY_OUT_TEST: 'highz_artifacts',
            KEY_OUT_DESC: 'High-Z artifacts & density overrides addressed: Choose One',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'tomo_couch_insertion',
            KEY_OUT_DESC: 'Tomo Couch insertion height correct and no collisions with bore',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'sim_fiducial_or_shifts',
            KEY_OUT_DESC: 'Sim Fiducial point set to match BB location or Shifts Document',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['EXAM_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {
                KEY_AUTOMATED_TESTS: ['qa_tests.test_examination.check_localization'],
                KEY_STATUS: 'Enhanced - Localization checked for existence but not correctness',
                KEY_AUTO_REVIEW_DATE: '02Oct2023'
            },
        },
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {
            KEY_OUT_TEST: 'non_repro_tpo_structures_blocked',
            KEY_OUT_DESC: 'Only non-reproducible and TPO-indicated structures blocked',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {
            KEY_OUT_TEST: 'tpo_clinical_goals',
            KEY_OUT_DESC: 'TPO Clinical Goals Entered',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'auto_r0a0_plans',
            KEY_OUT_DESC: 'Auto and R0A0 Plans are identical in Dose',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'modulation_factor',
            KEY_OUT_DESC: 'Modulation factor < 2.2',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'bev_movie',
            KEY_OUT_DESC: 'Beams Eye View Movie shows only target is treated',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
        {
            KEY_OUT_TEST: 'treatment_time',
            KEY_OUT_DESC: 'Treatment time appropriate for plan',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ],
    REVIEW_LEVELS['ADAPTIVE']: [
        {
            KEY_OUT_TEST: 'idms_adaptive',
            KEY_OUT_DESC: 'iDMS Adaptive: treated fractions discontinued in new plan',
            KEY_OUT_DOMAIN_TYPE: DOMAIN_TYPE['BEAMSET_KEY'],
            KEY_OUT_OPTIONS: 'Yes,No',
            KEY_AUTOMATION: {},
        },
    ]
}

TECHNIQUE_MAP = {
    'TomoHelical': {
        "Physics": CHECK_BOXES_PHYSICS_REVIEW_TOMO,
        "Dosimetry": CHECK_BOXES_DOSIMETRY_SAFETY_TOMO,
    },
    'SMLC_Electrons': {
        "Physics": CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS,
        "Dosimetry": CHECK_BOXES_DOSIMETRY_SAFETY_ELECTRONS,
    },
    'DynamicArc': {
        "Physics": CHECK_BOXES_PHYSICS_REVIEW_VMAT,
        "Dosimetry": CHECK_BOXES_DOSIMETRY_SAFETY_VMAT,
    },
    'SMLC': {
        "Physics": CHECK_BOXES_PHYSICS_REVIEW_3D,
        "Dosimetry": CHECK_BOXES_DOSIMETRY_SAFETY_3D,
    },
    'T3D': {
        "Physics": CHECK_BOXES_PHYSICS_REVIEW_TOMO3D,
        "Dosimetry": CHECK_BOXES_DOSIMETRY_SAFETY_TOMO3D,
    }
}
# LOG PARSING INFO
LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\logs"
DEV_LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs"
KEEP_PHRASES = [("Critical", "CRITICAL"), ("Warnings", "WARNING"),
                ("Info", "INFO")]  # ("Debug", "DEBUG")]
#
# EXAM DEFAULTS
# TIME ELAPSED BETWEEN PLAN AND CT
DAYS_SINCE_SIM = 14
#
# CONTOURING DEFAULTS
BOLUS_NAMES = ["bolus"]
# def - check the front edges of the couch and suspended headboard
NO_FLY_NAME = "NoFlyZone_PRV"
PACEMAKER_NAME = "Pacemaker"
PACEMAKER_PRV_NAME = "Pacemaker_PRV50"
PACEMAKER_SEARCH_DISTANCE = 10.  # cm distance over which to look for the 2 Gy dose level
PACEMAKER_DISTANCE_TOLERANCE = 2.  # cm distance from which we want the 2 Gy line to be away from
# the pacer
SUPPORT_TOLERANCE = 2.0  # cm, the minimum distance between external and any support at isocenter
TRUEBEAM_MAX_DIAMETER = 80.0  # cm, the "pin" diameter of the TrueBeam
HDA_MAX_DIAMETER = 85.0  # cm, the cover diameter of the Tomo HDA
#
# PLANNING DEFAULTS
DOSE_FRACTION_PAIRS = [(4, 2000), (8, 800)]  # Often mixed up fractionations
#
# DOSE TOLERANCES
NO_FLY_DOSE = 100.  # cGy
PACEMAKER_DOSE = 200.  # cGy
#
# DOSE GRID PREFERENCES
DOSE_GRID_DEFAULT = 0.2  # 2 mm

# Supported patient orientations
PATIENT_ORIENTATIONS = {'HFS': 'Head First Supine',
                        'FFS': 'Feet First Supine',
                        'HFP': 'Head First Prone',
                        'FFP': 'Feet First Prone',
                        'HFDR': 'Head First Decubitus Right',
                        'FFDR': 'Feet First Decubitus Right',
                        'HFDL': 'Head First Decubitus Left',
                        'FFDL': 'Feet First Decubitus Left'}

PLAN_NAMES = {'LUNG_SBRT':
                  ['LUL', 'LLL', 'RUL', 'RML', 'RLL', 'LunR_SBR', 'LunL_SBR',
                   'LuLU_SBR', 'LuLL_SBR', 'LuRU_SBR', 'LuRM_SBR', 'LuRL_SBR',
                   ],
              'BREAST_SBRT':
                  ['BreR_SBR', 'BreL_SBR', ],
              'ABDOMEN_SBRT':
                  ['Abdo_SBR', 'LivR_SBR', 'Panc_SBR', 'AdrR_SBR', 'AdrL_SBR',
                   'KidR_SBR', 'KidL_SBR', 'Stom_SBR', 'Sple_SBR', 'Gall_SBR', ],
              'PELVIS_SBRT':
                  ['Pelv_SBR', 'HipR_SBR', 'HipL_SBR', 'Pros_SBR', 'Sacr_SBR'],
              'BRAIN_FSRT':
                  ['Brai_SBR', 'Brai_FSR', 'PTV1_FSR', 'PTV2_FSR', 'PTV3_FSR', 'PTV4_FSR',
                   'PTV5_FSR'],
              'SPINE_SBRT':
                  ['SpiT_SBR', 'SpiC_SBR', 'SpiL_SBR',
                   'SpC1_SBR', 'SpC2_SBR', 'SpC3_SBR', 'SpC4_SBR', 'SpC5_SBR', 'SpC6_SBR', 'SpC7_SBR',
                   'SpT1_SBR', 'SpT2_SBR', 'SpT3_SBR', 'SpT'],
              'HEAD_NECK_SBRT':
                  ['NecB_SBR', 'NecR_SBR', 'NecL_SBR', 'Neck_SBR',
                   'EyeR_SBR', 'EyeL_SBR'],
              'SRS':
                  ['SRS'],
              'TBI':
                  ['TBI'],
              'VMAT':
                  ['VMA'],
              'THI':
                  ['THI', 'T3D'],
              '3D':
                  ['3DC', '3CA', 'BST', 'Bst'],
              '2D':
                  ['2DC'],
              }

GRID_PREFERENCES = {
    'SBRT': {
        'PLAN_NAMES': PLAN_NAMES['LUNG_SBRT'] + PLAN_NAMES['BREAST_SBRT']
                      + PLAN_NAMES['ABDOMEN_SBRT'] + PLAN_NAMES['PELVIS_SBRT'],
        'DOSE_GRID': 0.15,  # 1.5 mm
        'FRACTION_SIZE_LIMIT': 801,  # cGy
        'SLICE_THICKNESS': 0.2,  # 2.0 mm
    },
    'SBRT_FINE': {
        'PLAN_NAMES': PLAN_NAMES['SPINE_SBRT'] + PLAN_NAMES['HEAD_NECK_SBRT'],
        'DOSE_GRID': 0.15,  # 1.5 mm
        'FRACTION_SIZE_LIMIT': 801,  # cGy
        'SLICE_THICKNESS': 0.1,  # 2.0 mm
    },
    'SRS': {
        'PLAN_NAMES': PLAN_NAMES['BRAIN_FSRT'] + PLAN_NAMES['SRS'],
        'DOSE_GRID': 0.1,  # 1.0 mm
        'FRACTION_SIZE_LIMIT': 1500,  # cGy
        'SLICE_THICKNESS': 0.1,  # 1.0 mm
    },
    'TBI': {
        'PLAN_NAMES': PLAN_NAMES['TBI'],
        'DOSE_GRID': 0.5,  # 5 mm
        'FRACTION_SIZE_LIMIT': None,  # Don't check
        'SLICE_THICKNESS': 0.4,  # 4 mm
    },
    'VMAT': {
        'PLAN_NAMES': PLAN_NAMES['VMAT'],
        'DOSE_GRID': 0.3,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.3,  # 3 mm
    },
    'THI': {
        'PLAN_NAMES': PLAN_NAMES['THI'],
        'DOSE_GRID': 0.3,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.3,  # 3 mm
    },
    '3D': {
        'PLAN_NAMES': PLAN_NAMES['3D'],
        'DOSE_GRID': 0.4,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.4,  # 4 mm
    },
    '2D': {
        'PLAN_NAMES': PLAN_NAMES['2D'],
        'DOSE_GRID': 0.4,  # 3 mm
        'FRACTION_SIZE_LIMIT': 800,  # cGy
        'SLICE_THICKNESS': 0.4,  # 4 mm
    },
}

#
# ELECTRON MONTE CARLO SETTINGS
# minimum number of e mc histories
ELECTRON_MC_MIN_HISTORIES = 1e6
# limit on the maximum uncertainty normalized to the maximum dose
ELECTRON_MC_UNCERTAINTY = 0.01
#
# FIELD OF VIEW SETTINGS
FIELD_OF_VIEW_PREFERENCES = {'NAME': 'FOV_Reconstructed',
                             'WALL_SUFFIX': '_Wall',
                             'CONTRACTION': 0.5,  # cm
                             'NAME_INTERSECTION': 'FOV_EXT_INTERSECT',
                             'SI_PTV_BUFFER': 2.0,  # cm
                             }

MCS_TOLERANCES = {'MCS': {'MEAN': 0.369,
                          'SIGMA': 0.152},
                  'LSV': {'MEAN': 0.694,
                          'SIGMA': 0.134},
                  'AAV': {'MEAN': 0.522,
                          'SIGMA': 0.188},
                  }

TOMO_DATA = {'MACHINES': ['HDA0488'],
             'PLAN_TR_SUFFIX': r'_Tr',
             'LATERAL_ISO_MARGIN': 2.,  # cm
             'SUPPORTS': ['TomoCouch', 'S-frame']
             }

TRUEBEAM_DATA = {'MACHINES': ['TrueBeam', 'TrueBeamSTx'],
                 'SUPPORTS': ['TrueBeamCouch', 'CivcoBaseShell_Cork', 'CivcoInclineShell_Wax',
                              'Sframe_F1_TBCouch_HN', 'Sframe_H2_TBCouch_Brain',
                              'ProneBreastBoard', 'QFix_Brain_TBCouch_H1andH2','QFix_H&N_TBCouch_F2andF3',
                              'Black Board External Final', 'Baseplate_Override_PMMA'],
                 'EDW_LIMITS': {'MU_LIMIT': 20.,
                                'Y2-OUT': 10.,  # Y2=OUT: -10 cm ≤ Y1 ≤ 10 cm
                                'Y1-IN': 10.,  # Y1=IN : -10 cm ≤ Y2 ≤ 10 cm
                                'Y-MIN': 4.,  # Y2 - Y1 ≥ 4 cm
                                'Y-MAX': 30.,  # Y2 - Y1 ≤ 30 cm
                                'X-MAX': 40.,  # X2 - X1 ≤ 40 cm
                                'X-MIN': 4.,  # X2 - X1 ≥ 4 cm
                                }}
# MATERIALS:
MATERIALS = {'TrueBeamCouch': 'Lung',
             'CivcoBaseShell_Cork': 'Cork',
             'CivcoInclineShell_Wax': 'Wax',
             'CivcoWingBoard_PMMA': 'PMMA',
             'Sframe_H2_TBCouch_Brain': 'Lung',
             'Sframe_F1_TBCouch_HN': 'Lung',
             'Sframe': 'Lung',
             'TomoCouch': 'Lung',
             'Baseplate_Override_PMMA': 'PMMA',
             'QFix_Brain_TBCouch_H1andH2': 'Lung',
             'QFix_H&N_TBCouch_F2andF3': 'Lung',
             'Black Board External Final': 'Lung',
             'ProneBreastBoard': 'Cartilage',
             'MT-T-45-S-CE221': 'PLA',
             'MT-T-45-M-CE221': 'PLA',
             'MT-T-45-L-CE221': 'PLA',
             }
# PLANNING PREFERENCES - CLINICAL
VMAT_PREFERENCES = {
    'SBRT': {
        'PLAN_NAMES': PLAN_NAMES['LUNG_SBRT'] + PLAN_NAMES['BREAST_SBRT']
                      + PLAN_NAMES['ABDOMEN_SBRT'] + PLAN_NAMES['PELVIS_SBRT'],
        'MOD_FACTOR_HIGH': 4,  # Sum of Beam MU / Rx in cGy
    },
    'SBRT_FINE': {
        'PLAN_NAMES': PLAN_NAMES['SPINE_SBRT'] + PLAN_NAMES['HEAD_NECK_SBRT'],
        'MOD_FACTOR_HIGH': 5,  # Sum of Beam MU / Rx in cGy
    },
    'SRS': {
        'PLAN_NAMES': PLAN_NAMES['BRAIN_FSRT'] + PLAN_NAMES['SRS'],
        'MOD_FACTOR_HIGH': 3,  # Sum of Beam MU / Rx in cGy
    },
    'TBI': {
        'PLAN_NAMES': PLAN_NAMES['TBI'],
        'MOD_FACTOR_HIGH': 6,  # Sum of Beam MU / Rx in cGy
    },
    'VMAT': {
        'PLAN_NAMES': PLAN_NAMES['VMAT'],
        'MOD_FACTOR_HIGH': 4,  # Sum of Beam MU / Rx in cGy
    },
    '3D': {
        'PLAN_NAMES': PLAN_NAMES['3D'],
        'MOD_FACTOR_HIGH': 3,  # Sum of Beam MU / Rx in cGy
    },
}
TOMO_PREFERENCES = {
    'ABDOMEN': {'ALIAS': ['Abdo_THI', 'Livr_THI', 'Panc_THI'],
                'MF_HIGH': 2.4, 'MF_LOW': 1.6},
    'BRAIN': {'ALIAS': ['Brai_THI'],
              'MF_HIGH': 2.4, 'MF_LOW': 1.6},
    'BREAST': {'ALIAS': ['BreL_THI', 'BreR_THI', 'ChwL_THI', 'ChwR_THI'],
               'MF_HIGH': 2.8, 'MF_LOW': 2.4},
    'CSI': {'ALIAS': ['CSI_THI'],
            'MF_HIGH': 2.2, 'MF_LOW': 1.8},
    'EXTREMITY': {'ALIAS': ['ArmL_THI', 'ArmR_THI', 'LegL_THI', 'LegR_THI'],
                  'MF_HIGH': 2.4, 'MF_LOW': 2.0},
    'GYN': {'ALIAS': ['Vulv_THI'],
            'MF_HIGH': 2.4, 'MF_LOW': 1.8},
    'HN': {'ALIAS': ['NecB_THI', 'NecR_THI', 'NecL_THI'],
           'MF_HIGH': 2.6, 'MF_LOW': 2.2},
    'LUNG-NO-SBRT': {'ALIAS': ['LunL_THI', 'LunR_THI', 'LunB_THI', 'Medi_THI'],
                     'MF_HIGH': 2.8, 'MF_LOW': 2.4},
    'LUNG-SBRT': {'ALIAS': PLAN_NAMES['LUNG_SBRT'],
                  'MF_HIGH': 1.4, 'MF_LOW': 1.2},
    'PELVIS': {'ALIAS': ['Pelv_THI', 'PelR_THI', 'PelL_THI', 'PelB_THI'],
               'MF_HIGH': 2.4, 'MF_LOW': 1.8},
    'PROSTATE-LOW-RISK': {'ALIAS': ['Pros_THI'], 'MF_HIGH': 2.2, 'MF_LOW': 1.6},
    'PROSTATE-HIGH-RISK': {'ALIAS': ['ProN_THI', 'ProF_THI'],
                           'MF_HIGH': 2.4, 'MF_LOW': 2.0},
    'TOMO_3D': {'ALIAS': ['T3D'],
                'MF_HIGH': 2.2, 'MF_LOW': 1.1},
}
# TECHNIQUE/MODALITY TYPES
TECHNIQUE_TYPES = {
    ('SMLC', 'Electrons'): ['Electron -- 2D', 'Electron -- 3D'],
    ('SMLC', 'Photons'): ['Static MLC -- 2D', 'Static NoMLC -- 2D', 'Static MLC -- 3D',
                          'Static NoMLC -- 3D', 'FiF MLC -- 3D', 'Static PRDR MLC -- 3D',
                          'SnS MLC -- IMRT', 'SnS PRDR MLC -- IMRT'],
    ('DynamicArc', 'Photons'): ['Conformal Arc -- 2D', 'Conformal Arc -- 3D', 'VMAT Arc -- IMRT'],
    ('TomoHelical', 'Photons'): ['TomoHelical -- IMRT', 'TomoHelical -- 3D Conformal'],
}
# PLAN/SITE CLASSIFICATION
SITE_CLASSIFICATION = {
    'Abdomen': {
        'beamset_aliases': ['Abd'],
        'site_aliases': ['Abdomen'],
        'Subsites': {
            'Liver': {
                'beamset_aliases': ['Liver', 'Livr'],
                'site_aliases': ['Liver', ],
            },
            'Pancreas': {
                'beamset_aliases': ['AbdR', 'AbdL', 'Abdo', 'Ab12', 'Ab13', 'Abd1', 'Abd2', 'Abd3', 'Panc'],
                'site_aliases': [],
            },
            'Misc': {
                'beamset_aliases': ['KidR', 'KidL', 'Kid', 'AdrR', 'AdrL', 'Sple'],
                'site_aliases': ['Kidney_Right', 'Rt Adrenal SBRT', 'Rt Adrenal Gland',
                                 'Adrenal_Left', 'Kidney SBRT'],
            },
        },
    },
    'Thorax': {
        'beamset_aliases': ['Bron', 'Ches', 'Hert'],
        'site_aliases': ['Thorax'],
        'Subsites': {
            'Esophagus': {
                'beamset_aliases': ['Esoph', 'EsoI', 'EsoS', 'Esop'],
                'site_aliases': ['Esophagus'],
                'Subsites': {},
            },
            'Lung': {
                'beamset_aliases': ['Lung', 'LunL', 'LunR', 'LunB', 'LuLU', 'LuLL',
                                    'LuRM', 'LuRI', 'LuRU', 'LuR1', 'LuRL', 'LuL1',
                                    'LuL2', 'LuRS', 'Medi'],
                'site_aliases': ['Lung', 'Bilateral Lungs', 'Lung_Bilateral',
                                 'Lung_Right Upper Lobe', 'Lung_Right', 'Bilateral Lung',
                                 'Bilat Lung', 'Lung_R', 'Lung_L', 'Lung_B', 'LunB', 'Lung SBRT',
                                 'LT lung sbrt', 'LuL'],
            },
            'Breast': {
                'beamset_aliases': ['BreL', 'BreR', 'ChwR', 'ChwL', 'AxiL', 'AxiR', 'ScvL', 'ScvR'],
                'site_aliases': [],
            },
            'Bone': {
                'beamset_aliases': ['RiL1', 'RiL2', 'RiL3', 'RiL4', 'RiL5', 'RiL6', 'RiL7', 'RiL8', 'RiL9',
                                    'RiL10', 'RiL11', 'RiL12', 'RibR', 'RibL', 'RiR1', 'RiR2', 'RiR3',
                                    'RiR4', 'RiR5', 'RiR6', 'RiR7', 'RiR8', 'RiR9', 'RiR10', 'RiR11', 'RiR12', ],
                'site_aliases': ['Scapula_Left', 'Scapula R', 'Scapula_Right', 'Lt Scapula', 'Rt Scapula',
                                 'Rib_Left', 'Ribs', 'Rib_R', 'Rib_Left', 'Scapula'],
            },
            'Thorax-Misc': {
                'beamset_aliases': ['Bron', 'Ches', 'Hert'],
                'site_aliases': [],
            },
        },
    },
    'Head and Neck': {
        'beamset_aliases': [],
        'site_aliases': [],
        'Subsites': {
            'HeadNeck-Left': {
                'beamset_aliases': ['NecL', 'ParL'],
                'site_aliases': ['Neck_Left'],
            },
            'HeadNeck-Right': {
                'beamset_aliases': ['NecR', 'ParR'],
                'site_aliases': ['Neck_Right'],
            },
            'HeadNeck-Bilateral': {
                'beamset_aliases': ['NecB', 'Naso'],
                'site_aliases': ['Neck_Bilateral'],
            },
            'HeadNeck-Misc': {
                'beamset_aliases': ['EyeL', 'EyeR', 'Nose', 'Skul', 'Neck',
                                    'Scal', 'TemR', 'TemL', 'NosL', 'CanL',
                                    'CanR', 'MndL', 'Face', 'HeaL', 'HeaR'],
                'site_aliases': ['Scalp', 'HN', 'Mandible', 'Paratracheal LN', 'Larynx'],
            },
        },
    },
    'Brain': {
        'beamset_aliases': ['Brai', 'Pitu', 'Bra1', 'Bra2', 'Bra3',
                            'Bra4', 'Bra5', 'Bra6', 'Bra7', 'Bra8', 'Bra9'],
        'site_aliases': ['Brain', 'FSRT Brain', 'Temporal'],
        'Subsites': {},
    },
    'Extremity': {
        'beamset_aliases': ['ShoL', 'LegL', 'LegR', 'FemR', 'FemL',
                            'HumL', 'HumR', 'FooL', 'FooR', 'HanR',
                            'HanL', 'ArmR', 'ArmL', 'HeeR', 'HeeL'],
        'site_aliases': ['Left Foot', 'Right Foot', 'Left Hand',
                         'Right Hand', 'Hand_L', 'Hand_R', 'L Forearm'],
        'Subsites': {},
    },
    'Pelvis': {
        'beamset_aliases': ['Pelv', 'PelB', 'PelL', 'PelR', 'PelI',
                            'PelS', 'Rect', 'Anus', 'Pel1', 'Pel2',
                            'PelN', 'GroR', 'GroL', 'PeLN', 'GluR', 'GluL'],
        'site_aliases': [],
        'Subsites': {
            'Bladder': {
                'beamset_aliases': ['Blad'],
                'site_aliases': ['Bladder'],
            },
            'Bone': {
                'beamset_aliases': ['IliL', 'IliR', 'IscR', 'IscL',
                                    'HipR', 'HipL', 'Sacr', 'AceR', 'AceL'],
                'site_aliases': [''],
            },
            'Prostate': {
                'beamset_aliases': ['Pros', ],
                'site_aliases': ['Prostate'],
            },
            'Prostate-Nodes': {
                'beamset_aliases': ['PrLN', 'PrFN', 'ProN'],
                'site_aliases': [],
            },
            'Prostate-Fossa': {
                'beamset_aliases': ['ProF'],
                'site_aliases': [],
            },
            'Rectum': {
                'beamset_aliases': ['Rect', 'Anus'],
                'site_aliases': ['Rectum'],
            },
            'Pelvis-Misc': {
                'beamset_aliases': ['Pelv', 'PelB', 'PelL', 'PelR', 'PelI',
                                    'PelS', 'Pel1', 'Pel2', 'PelN', 'GroR',
                                    'GroL', 'PeLN', 'GluR', 'GluL'],
                'site_aliases': [],
            },
        },
    },
    'Spine': {
        'beamset_aliases': ['SpiL', 'SpiT', 'SpiC', 'SpT8', 'SpC2',
                            'SpLS', 'SpCT', 'SpTL', 'SpC1', 'SpC3', 'SpC4',
                            'SpC5', 'SpC6', 'SpC7', 'Sp10', 'SpT1', 'SpT2',
                            'SpT3', 'SpT4', 'SpT5', 'SpT6', 'SpT7', 'SpT9',
                            'ST10', 'SpL1', 'SpL2', 'SpL3', 'SpL4', 'SpL5',
                            'SpT10', 'SpT11', 'SpT12'],
        'site_aliases': [],
        'Subsites': {},
    },
    'TotalBody': {
        'beamset_aliases': ['TBI'],
        'site_aliases': [],
        'Subsites': {},
    },
}
