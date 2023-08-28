""" review_definitions.py
All functional assumptions made in deployment of the UW physics/dosimetry
check script

"""
import os
from PlanReview.utils.constants import KEY_OUT_TEST, KEY_OUT_DOMAIN_TYPE

# OUTPUT DIR
OUTPUT_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs"
ERROR_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs\Errors\ReviewScript"

protocol_folder = r'../../protocols'
institution_folder = r'UW'
PROTOCOL_DIR = os.path.join(os.path.dirname(__file__),
                            protocol_folder,
                            institution_folder)

icon_dir = os.path.join(os.path.dirname(__file__), "guis\\icons")
RED_CIRCLE = os.path.join(icon_dir, "red_circle_icon.png")
GREEN_CIRCLE = os.path.join(icon_dir, "green_circle_icon.png")
YELLOW_CIRCLE = os.path.join(icon_dir, "yellow_circle_icon.png")
BLUE_CIRCLE = os.path.join(icon_dir, "blue_circle_icon.png")
UW_HEALTH_LOGO = os.path.join(icon_dir, "UW_Health_Logo.png")
ICON_PRINT = os.path.join(icon_dir, "print_icon.png")
ICON_START = os.path.join(icon_dir, "start_icon.png")
ICON_CANCEL = os.path.join(icon_dir, "cancel_icon.png")
ICON_PAUSE = os.path.join(icon_dir, "pause_icon.png")
ICON_SAVE = os.path.join(icon_dir, "save_icon.png")
ICON_LOAD = os.path.join(icon_dir, "load_icon.png")
ICON_ERROR = os.path.join(icon_dir, "error_icon.png")
# RESULT STRINGS
PASS = "Pass"
FAIL = "Fail"
ALERT = "Alert"
NA = "Not Applicable"

# Level keys
LEVELS = {
    'PATIENT_KEY': "PATIENT_LEVEL",
    'EXAM_KEY': "EXAM_LEVEL",
    'PLAN_KEY': "PLAN_LEVEL",
    'BEAMSET_KEY': "BEAMSET_LEVEL",
    'SANDBOX_KEY': "SANDBOX_LEVEL",
    'RX_KEY': "RX_LEVEL",
    'LOG_KEY': "LOG_LEVEL"}
#
# FRONTPAGE PROMPTS
FRONT_TAB = [
    "NUMBER OF SLICES",
    "SCAN DATE",
    "CT ORIENTATION",
    "Special instructions–FB, MIBH…",
    "Energy specified"

]
REVIEW_LEVELS = {
                 'PREPLAN_DATA': 'Preplanning Data',
                 'PATIENT_MODEL': 'Patient Modeling',
                 'PLAN_DATA': 'Plan Data',
                 'PLAN_DESIGN': 'Plan Design',
                 'PLAN_EVAL': 'Plan Evaluation',
                 'OPTIMIZATION': 'Optimization',
                 'ADAPTIVE': 'Adaptive',
                 'MOBIUS': 'Mobius',
                 'SANDBOX': 'Sandbox'
                 }
#
# CHECKBOXES are qa_tests that must be manually performed
CHECK_BOXES_PHYSICS_REVIEW = {
    REVIEW_LEVELS['PLAN_DATA']: [
        {'key': 'plan_name_tpo',
         KEY_OUT_TEST: 'Plan Name is consistent with TPO',
         'options': 'Yes,NA,No'},
        {'key': 'plan_approved_md',
         KEY_OUT_TEST: 'Plan is approved by MD',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_beamset.check_beamset_approved'},
    ],
    REVIEW_LEVELS['PREPLAN_DATA']: [
        {'key': 'ct_images_match',
         KEY_OUT_TEST: 'CT images match RayStation Modality/Patient Name/MRN',
         'options': 'Yes,NA,No'},
        {'key': 'ct_images_number',
         KEY_OUT_TEST: 'Number of CT images matches CT simulation document',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_examination.check_exam_date_and_slices'},
        {'key': 'ct_images_scan_datetime',
         KEY_OUT_TEST: 'CT images Scan Date/Time matches CT simulation document',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_examination.check_exam_date_and_slices'},
        {'key': 'ct_orientation',
         KEY_OUT_TEST: 'CT orientation matches report',
         'options': 'Yes,NA,No'},
        {'key': 'immobilization_protocol',
         KEY_OUT_TEST: 'Immobilization matches protocol and is reproducible',
         'options': 'Yes,NA,No'},
        {'key': 'no_artifacts',
         KEY_OUT_TEST: 'No significant imaging artifacts present',
         'options': 'Yes,NA,No'},
        {'key': 'special_instructions',
         KEY_OUT_TEST: 'Special instructions (FB, MIBH) are noted in treatment planning order',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'md_approved_mim',
         KEY_OUT_TEST: 'If contoured in MIM, MD approved session',
         'options': 'Yes,NA,No'},
        {'key': 'mim_statistics_match',
         KEY_OUT_TEST: 'If contoured in MIM, Statistics/gross appearance matches RayStation',
         'options': 'Yes,NA,No'},
        {'key': 'mim_fusions',
         KEY_OUT_TEST: 'Fusions in MIM are accurate',
         'options': 'Yes,NA,No'},
        {'key': 'mim_tpo_contours',
         KEY_OUT_TEST: 'TPO listed contours are correctly interpolated',
         'options': 'Yes,NA,No'},
        {'key': 'mim_no_stray_voxels',
         KEY_OUT_TEST: 'No stray voxels in the targets.',
         'options': 'Yes,NA,No'},
        {'key': 'mim_contour_extents',
         KEY_OUT_TEST: 'Regions at risk near targets are contoured and sufficient for the plan',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_retracted',
         KEY_OUT_TEST: 'PTV is retracted from skin at least 3mm',
         'options': 'Yes,NA,No'},
        {'key': 'density_overrides_contoured',
         KEY_OUT_TEST: 'Density overrides are contoured',
         'options': 'Yes,NA,No'},
        {'key': 'density_overrides',
         KEY_OUT_TEST: 'Density overrides Material assignment is appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'density_override_rois',
         KEY_OUT_TEST: 'Density override ROIs do not overlap',
         'options': 'Yes,NA,No'},
        {'key': 'external_contour',
         KEY_OUT_TEST: 'External contour is set correctly and does not include couch',
         'options': 'Yes,NA,No'},
        {'key': 'immobilization_devices',
         KEY_OUT_TEST: 'Immobilization devices and couch added as structures are added correctly',
         'options': 'Yes,NA,No'},
        {'key': 'bolus_custom_devices',
         KEY_OUT_TEST: 'Bolus and custom devices are physically and dosimetrically realistic',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'beam_names_correct',
         KEY_OUT_TEST: 'Beam Names are correct',
         'options': 'Yes,NA,No'},
        {'key': 'beams_single_machine',
         KEY_OUT_TEST: 'Beams are assigned to a single machine',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_placement',
         KEY_OUT_TEST: 'Isocenter placement is appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'beams_not_through_mobile_objects',
         KEY_OUT_TEST: 'Beams do not treat through mobile objects (arms, chin, legs)',
         'options': 'Yes,NA,No'},
        {'key': 'beam_apertures',
         KEY_OUT_TEST: 'Beam Apertures are reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'matched_field_junctions',
         KEY_OUT_TEST: 'Any matched field junctions are reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_prior_rt',
         KEY_OUT_TEST: 'Overlap with prior RT is reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_resolution',
         KEY_OUT_TEST: 'Dose grid Resolution is 2mm or less',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_coverage',
         KEY_OUT_TEST: 'Dose Grid covers patient and support structures',
         'options': 'Yes,NA,No'},
        {'key': 'prescription',
         KEY_OUT_TEST: 'Prescription matches TPO',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_volume',
         KEY_OUT_TEST: 'Prescription is based on volume (preferred) or isodose line',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {'key': 'dose_distribution',
         KEY_OUT_TEST: 'Dose distribution looks reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'tpo_goals_constraints',
         KEY_OUT_TEST: 'TPO goals and constraints are entered in clinical '
                      'goals and reasonably addressed',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['MOBIUS']: [
        {'key': 'couch_removal_height',
         KEY_OUT_TEST: 'Confirm couch removal height',
         'options': 'Yes,NA,No'},
        {'key': 'target_identification',
         KEY_OUT_TEST: 'Target identification is correct',
         'options': 'Yes,NA,No'},
        {'key': 'structure_classification',
         KEY_OUT_TEST: 'Classification of each structure is correct',
         'options': 'Yes,NA,No'},
        {'key': 'gamma_review',
         KEY_OUT_TEST: 'Review gamma: 5%/3mm > 90%',
         'options': 'Yes,NA,No'},
        {'key': 'review_dose_acs',
         KEY_OUT_TEST: 'Review dose in A, C, S',
         'options': 'Yes,NA,No'},
        {'key': 'beam_info_mobius',
         KEY_OUT_TEST: 'Beam information in Mobius Clearance/deliverable are green',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_raystation_dose',
         KEY_OUT_TEST: 'Mobius RayStation Dose difference is consistent with report',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['SANDBOX']: [
        {'key': 'sandbox_tests',
         KEY_OUT_TEST: 'Did these experimental tests work for this case?',
         'options': 'Yes,NA,No'},
    ],

}
CHECK_BOXES_PHYSICS_REVIEW_3D = {
    REVIEW_LEVELS['PLAN_DATA']: [
    ],
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'sim_fiducials_alignment',
         KEY_OUT_TEST: 'SimFiducials localization point alignment matches BBs,'
                      ' or AlignRT is noted in CT Sim',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'modality_energy',
         KEY_OUT_TEST: 'Modality and Energy match TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_correct_isocenter',
         KEY_OUT_TEST: 'Beams are assigned to the correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'btv_avoid_mlc',
         KEY_OUT_TEST: 'BTV and AVOID are used to define MLC shapes',
         'options': 'Yes,NA,No'},
        {'key': 'wedges_placement',
         KEY_OUT_TEST: 'Any wedges are intuitively placed',
         'options': 'Yes,NA,No'},
        {'key': 'beam_flash',
         KEY_OUT_TEST: 'Beam Flash is present on breast or areas with potential'
                      ' out-of-field movement',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         KEY_OUT_TEST: 'Beam MU is reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'beam_divergence',
         KEY_OUT_TEST: 'Beam divergence is appropriate',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
    ],
    REVIEW_LEVELS['MOBIUS']: [
    ]
}
CHECK_BOXES_PHYSICS_REVIEW_VMAT = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'sim_fiducials_alignment',
         KEY_OUT_TEST: 'SimFiducials localization point alignment matches BBs,'
                      ' or AlignRT is noted in CT Sim',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_retracted',
         KEY_OUT_TEST: 'PTV is retracted from skin at least 3mm',
         'options': 'Yes,NA,No'},
        {'key': 'prv_volumes',
         KEY_OUT_TEST: 'PRV volumes are drawn for serial OARs',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'modality_energy',
         KEY_OUT_TEST: 'Modality, Energy match TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_correct_isocenter',
         KEY_OUT_TEST: 'Beams are assigned to the correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'arc_geometry',
         KEY_OUT_TEST: 'Arc Geometry: Arcs match SmartArc Tolerance Tables',
         'options': 'Yes,NA,No'},
        {'key': 'collimator_angle',
         KEY_OUT_TEST: 'Collimator angle differs on arcs',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_opening',
         KEY_OUT_TEST: 'Jaw opening is sensible for target size',
         'options': 'Yes,NA,No'},
        {'key': 'arc_protect_blocking',
         KEY_OUT_TEST: 'Arc protect or dosimetric Blocking is used to avoid'
                      ' low-reproducibility objects',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         KEY_OUT_TEST: 'Beam MU is reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_prior_rt',
         KEY_OUT_TEST: 'Overlap with prior RT is reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'plan_setup',
         KEY_OUT_TEST: 'Dependency settings of beam set appropriate'
                      ' (background/co-optimization)',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'objective_type',
         KEY_OUT_TEST: 'Objective type is correct for targets/OAR',
         'options': 'Yes,NA,No'},
        {'key': 'optimization_settings',
         KEY_OUT_TEST: 'Optimization settings: 2-degree gantry spacing',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
    ],
    REVIEW_LEVELS['MOBIUS']: [
    ]
}

CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS = {
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'modality_energy_matches_tpo',
         KEY_OUT_TEST: 'Modality, Energy matches TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_assigned_correct_isocenter',
         KEY_OUT_TEST: 'Beams assigned to correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'beam_ssd_set_correctly',
         KEY_OUT_TEST: 'Beam SSD set correctly 100 SSD for A6, 105 SSD otherwise',
         'options': 'Yes,NA,No'},
        {'key': 'beam_source_to_surface',
         KEY_OUT_TEST: 'Beam source to surface should be to skin if no bolus,'
                      ' to surface if bolus',
         'options': 'Yes,NA,No'},
        {'key': 'beam_reasonably_en_face',
         KEY_OUT_TEST: 'Beam is reasonably en face',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu_reasonable',
         KEY_OUT_TEST: 'Beam MU reasonable',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {'key': 'histories_per_cm2',
         KEY_OUT_TEST: 'Number of histories ≥500K per cm2',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'sim_fiducials_alignment',
         KEY_OUT_TEST: 'SimFiducials localization point alignment matches'
                      ' BBs, or AlignRT is noted '
                      'in CT Sim',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}

CHECK_BOXES_PHYSICS_REVIEW_TOMO3D = {
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'tomocouch_inserted_correctly',
         KEY_OUT_TEST: 'TomoCouch is inserted correctly',
         'options': 'Yes,NA,No'},
        {'key': 'simfiducials_localization_alignment',
         KEY_OUT_TEST: 'SimFiducials localization point alignment matches BBs',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'patient_shifts_no_collision',
         KEY_OUT_TEST: 'Patient shifts will not lead to a collision',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_target_in_fov',
         KEY_OUT_TEST: 'Patient shifts will place target in '
                      'MVCT Field of View (FOV)',
         'options': 'Yes,NA,No'},
        {'key': 'targets_separated_by_7_cm',
         KEY_OUT_TEST: 'Targets separated by > 7 cm apart are treated'
                      ' with separate beamsets',
         'options': 'Yes,NA,No'},
        {'key': 'beam_modulation_factor',
         KEY_OUT_TEST: 'Beam Modulation Factor < 2.2',
         'options': 'Yes,NA,No'},
        {'key': 'beam_field_width',
         KEY_OUT_TEST: 'Beam Field Width is 5.05 cm',
         'options': 'Yes,NA,No'},
        {'key': 'beam_pitch',
         KEY_OUT_TEST: 'Beam Pitch is 0.287',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_isocenter_lateral',
         KEY_OUT_TEST: 'Treatment Isocenter lateral < 2 cm',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'optimization_on_targets_external',
         KEY_OUT_TEST: 'Optimization on targets and External only',
         'options': 'Yes,NA,No'},
        {'key': 'protect_entry_exit_blocking',
         KEY_OUT_TEST: 'Protect: "Entry" and "Entry/Exit" used to '
                      'block appropriate OARs',
         'options': 'Yes,NA,No'},
        {'key': 'fov_artifacts_addressed_blocked',
         KEY_OUT_TEST: 'FOV artifacts are addressed or blocked',
         'options': 'Yes,NA,No'},
        {'key': 'low_reproducibility_anatomy_blocked',
         KEY_OUT_TEST: 'Low reproducibility anatomy is blocked '
                      'with a margin of > 2 cm',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_mode_dynamic',
         KEY_OUT_TEST: 'Jaw mode is Dynamic',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [
        {'key': 'plan_dvh_goals_identical',
         KEY_OUT_TEST: 'Plan DVH and goals are identical to the _Auto plan',
         'options': 'Yes,NA,No'},
    ],
    # 'Transfer Plan': [
    #     {'key': 'transfer_plan_dose_distribution',
    #      KEY_OUT_TEST: 'Transfer plan dose distribution and DVHs reviewed,'
    #                   ' match with Primary Plan',
    #      'options': 'Yes,NA,No'},
    #     {'key': 'transfer_plan_locked_approved',
    #      KEY_OUT_TEST: 'Transfer plan is locked and approved by Dosimetry'
    #                   ' in RayStation',
    #      'options': 'Yes,NA,No'},
    # ],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}

CHECK_BOXES_PHYSICS_REVIEW_TOMO = {
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'tomocouch_inserted_correctly',
         KEY_OUT_TEST: 'TomoCouch is inserted correctly',
         'options': 'Yes,NA,No'},
        {'key': 'simfiducials_localization_alignment',
         KEY_OUT_TEST: 'SimFiducials localization point alignment matches BBs',
         'options': 'Yes,NA,No'},
    ],
    # 'Transfer Plan': [
    #     {'key': 'transfer_plan_dose_distribution',
    #      KEY_OUT_TEST: 'Transfer plan dose distribution and DVHs reviewed,'
    #                   ' match with Primary Plan',
    #      'options': 'Yes,NA,No'},
    #     {'key': 'transfer_plan_locked_approved',
    #      KEY_OUT_TEST: 'Transfer plan is locked and approved by Dosimetry'
    #                   ' in RayStation',
    #      'options': 'Yes,NA,No'},
    # ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'beamsets_assigned_same_machine',
         KEY_OUT_TEST: 'Beamsets are assigned to the same machine',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_lateral_position',
         KEY_OUT_TEST: 'Isocenter lateral position is <2 cm, '
                      'or a patient alert to break indexing is created',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_no_collision',
         KEY_OUT_TEST: 'Patient shifts will not lead to a collision',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_target_in_fov',
         KEY_OUT_TEST: 'Patient shifts place target in MVCT Field of View (FOV)',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time_less_than_600',
         KEY_OUT_TEST: 'Treatment time is < 600 s '
                      'or explained in Dosimetry Safety Sheet',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'objective_type_correct',
         KEY_OUT_TEST: 'Objective type is correct for targets/OAR',
         'options': 'Yes,NA,No'},
        {'key': 'protect_entry_exit_blocking',
         KEY_OUT_TEST: 'Protect: "Entry" and "Entry/Exit" used'
                      ' to block appropriate OARs',
         'options': 'Yes,NA,No'},
        {'key': 'fov_artifacts_addressed_blocked',
         KEY_OUT_TEST: 'FOV artifacts are addressed or blocked',
         'options': 'Yes,NA,No'},
        {'key': 'low_reproducibility_anatomy_blocked',
         KEY_OUT_TEST: 'Low reproducibility anatomy is blocked'
                      ' with a margin of > 2 cm',
         'options': 'Yes,NA,No'},
        {'key': 'review_beams_eye_view',
         KEY_OUT_TEST: 'Review Beam\'s eye view',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_EVAL']: [],
    REVIEW_LEVELS['PREPLAN_DATA']: [],
    REVIEW_LEVELS['MOBIUS']: [],
}

CHECK_BOXES = {
    'Plan Settings': [
        {'key': 'plan_name',
         KEY_OUT_TEST: 'Plan Name consistent with TPO',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_placement',
         KEY_OUT_TEST: 'Isocenter placement appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'arcs_match',
         KEY_OUT_TEST: 'Arcs match SmartArc Tolerance Tables',
         'options': 'Yes,NA,No'},
        {'key': 'collimator_angle',
         KEY_OUT_TEST: 'Collimator angle differs on arcs',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_opening',
         KEY_OUT_TEST: 'Jaw opening sensible for target size',
         'options': 'Yes,NA,No'},
        {'key': 'blocking',
         KEY_OUT_TEST: 'Blocking used to avoid low-reproducibility objects',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         KEY_OUT_TEST: 'Beam MU reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'beam_apertures',
         KEY_OUT_TEST: 'Beam Apertures reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'invivo_dosimetry',
         KEY_OUT_TEST: 'Order generated for TLDs if needed',
         'options': 'Yes,NA,No'}
    ],
    REVIEW_LEVELS['PREPLAN_DATA']: [
        {'key': 'immobilization',
         KEY_OUT_TEST: 'Immobilization matches protocol',
         'options': 'Yes,NA,No'},
        {'key': 'artifacts',
         KEY_OUT_TEST: 'No significant artifacts present',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'contoured',
         KEY_OUT_TEST: 'If contoured in MIM MD approved session',
         'options': 'Yes,NA,No'},
        {'key': 'statistics',
         KEY_OUT_TEST: 'Statistics/gross appearance matches RayStation',
         'options': 'Yes,NA,No'},
        {'key': 'mim_fusion',
         KEY_OUT_TEST: 'MIM Fusion Accurate',
         'options': 'Yes,NA,No'},
        {'key': 'stray_voxels',
         KEY_OUT_TEST: 'No stray voxels in targets',
         'options': 'Yes,NA,No'},
        {'key': 'density_override',
         KEY_OUT_TEST: 'Density overrides Material assignment appropriate',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'ptv_skin',
         KEY_OUT_TEST: 'PTV skin involvement confirmed',
         'options': 'Yes,NA,No'},
        {'key': 'bolus_custom',
         KEY_OUT_TEST: 'Bolus and custom devices physically'
                      + ' and dosimetrically realistic',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_reviewed',
         KEY_OUT_TEST: 'Overlap with prior RT Reviewed',
         'options': 'Yes,NA,No'},
    ]
}
# SAFETY REVIEWS FOR DOSE
CHECK_BOXES_DOSE = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
        {'key': 'primary_image_set',
         KEY_OUT_TEST: 'Correct image set used as primary',
         'options': 'Yes,NA,No'},
        {'key': 'patient_info',
         KEY_OUT_TEST: 'Correct patient information (name, MRN, image #, orientation)',
         'options': 'Yes,NA,No'},
        {'key': 'ivdt_table',
         KEY_OUT_TEST: 'Correct IVDT table used',
         'options': 'Yes,NA,No'},
        {'key': 'case_data',
         KEY_OUT_TEST: 'Case data entered to match Course # in Aria, treatment site, MD',
         'options': 'Yes,NA,No'},
        {'key': 'slice_thickness',
         KEY_OUT_TEST: 'Slice thickness appropriate for plan type',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'approved_structure_set',
         KEY_OUT_TEST: 'MD approved structure set',
         'options': 'Yes,NA,No'},
        {'key': 'contours_cleaned',
         KEY_OUT_TEST: 'Contours interpolated and cleaned',
         'options': 'Yes,NA,No'},
        {'key': 'structure_template_loaded',
         KEY_OUT_TEST: 'Structure Template Loaded: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_expansions',
         KEY_OUT_TEST: 'PTV expansions per table',
         'options': 'Yes,NA,No'},
        {'key': 'sim_fiducial',
         KEY_OUT_TEST: 'Sim Fiducial point set to match BB location',
         'options': 'Yes,NA,No'},
        {'key': 'ct_cutoff',
         KEY_OUT_TEST: 'CT cutoff addressed',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'plan_beam_names',
         KEY_OUT_TEST: 'Plan and beam set names match treatment site',
         'options': 'Yes,NA,No'},
        {'key': 'machine_correct',
         KEY_OUT_TEST: 'Machine correct: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_resolution',
         KEY_OUT_TEST: 'Dose grid resolution set to 0.2',
         'options': 'Yes,NA,No'},
        {'key': 'isodose_display',
         KEY_OUT_TEST: 'Isodose line display set to Absolute values',
         'options': 'Yes,NA,No'},
        {'key': 'clinical_goals',
         KEY_OUT_TEST: 'Clinical goals entered',
         'options': 'Yes,NA,No'},
        {'key': 'final_dose_calc_script',
         KEY_OUT_TEST: 'Final Dose calculation script used',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_ELECTRON = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'density_overrides',
         KEY_OUT_TEST: 'Density overrides set appropriately and do not overlap external',
         'options': 'Yes,NA,No'},
        {'key': 'couch_structure',
         KEY_OUT_TEST: 'TrueBeam couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'en_face_beam_angle',
         KEY_OUT_TEST: 'En face beam angle used',
         'options': 'Yes,NA,No'},
        {'key': 'statistical_uncertainty',
         KEY_OUT_TEST: 'Dose Statistical uncertainty < 1%',
         'options': 'Yes,NA,No'},
        {'key': 'ssd_cones',
         KEY_OUT_TEST: 'SSD = 100 cm for 6x6 cone or 105 for all other cones, SSD to skin for no '
                      'bolus or to surface for bolus',
         'options': 'Yes,NA,No'},
        {'key': 'cutout_shape',
         KEY_OUT_TEST: 'Cutout: Shape: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'cutout_name',
         KEY_OUT_TEST: 'Cutout Name is accessory code',
         'options': 'Yes,NA,No'},
        {'key': 'bolus',
         KEY_OUT_TEST: 'Bolus: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_based_volume',
         KEY_OUT_TEST: 'Prescription based on volume',
         'options': 'Yes,NA,No'},
        {'key': 'printing_cutout',
         KEY_OUT_TEST: 'Printing: cutout printed to correct scale factor of 1.00',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_water_phantom',
         KEY_OUT_TEST: 'Mobius QuickCalc: Water phantom QA plan created',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_cutout_dimensions',
         KEY_OUT_TEST: 'Mobius QuickCalc: Cutout dimensions correct',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_dmax_dose',
         KEY_OUT_TEST: 'Mobius QuickCalc: Dmax dose entered into QuickCalc',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_agreement',
         KEY_OUT_TEST: 'Mobius QuickCalc: Agreement within 5%',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_TOMO = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'generate_planning_structure_script',
         KEY_OUT_TEST: 'Generate planning structure script used',
         'options': 'Yes,NA,No'},
        {'key': 'targets_retracted',
         KEY_OUT_TEST: 'Targets retracted 3 mm from surface (PTV eval used)',
         'options': 'Yes,NA,No'},
        {'key': 'tomo_couch_structure',
         KEY_OUT_TEST: 'Tomo couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'beam_added_no_collision',
         KEY_OUT_TEST: 'Beam added with no collision via machine geometry',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_offsets',
         KEY_OUT_TEST: 'Isocenter lateral offset < 3 cm and In/Out offset < 18 cm',
         'options': 'Yes,NA,No'}],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'clinical_goals_script',
         KEY_OUT_TEST: 'Clinical goals script used and matches TPO template name',
         'options': 'Yes,NA,No'},
        {'key': 'dynamic_jaws',
         KEY_OUT_TEST: 'Dynamic Jaws used on 2.5 and 5 cm plans',
         'options': 'Yes,NA,No'},
        {'key': 'field_width',
         KEY_OUT_TEST: 'Field width < Target length',
         'options': 'Yes,NA,No'},
        {'key': 'pitch',
         KEY_OUT_TEST: 'Pitch appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'modulation_factor',
         KEY_OUT_TEST: 'Modulation factor appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time',
         KEY_OUT_TEST: 'Treatment time appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'structures_blocked',
         KEY_OUT_TEST: 'Structures are blocked per protocol if applicable',
         'options': 'Yes,NA,No'},
        {'key': 'plan_optimization_script',
         KEY_OUT_TEST: 'Plan optimization script used',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['ADAPTIVE']: [
        {'key': 'idms_adaptive',
         KEY_OUT_TEST: 'iDMS Adaptive: treated fractions discontinued in new plan',
         'options': 'Yes,NA,No'},
    ]
}
CHECK_BOXES_DOSE_3D = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'highz_artifacts',
         KEY_OUT_TEST: 'High-Z artifacts & density overrides addressed: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'couch_structure',
         KEY_OUT_TEST: 'TrueBeam couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'btv_created',
         KEY_OUT_TEST: 'BTV created and derived based on PTV',
         'options': 'Yes,NA,No'},
        {'key': 'beam_template_used',
         KEY_OUT_TEST: 'Beam template used: Choose One ',
         'options': 'Yes,NA,No'},
        {'key': 'no_low_repro_objects',
         KEY_OUT_TEST: 'Beam(s) do not pass through low-reproducibility objects (ie: head of '
                      'table)',
         'options': 'Yes,NA,No'},
        {'key': 'treat_protect',
         KEY_OUT_TEST: 'Treat & Protect settings used',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_type',
         KEY_OUT_TEST: 'Prescription based on volume or isodose line',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_TOMO_3D = {
    REVIEW_LEVELS['PREPLAN_DATA']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'highz_artifacts',
         KEY_OUT_TEST: 'High-Z artifacts & density overrides addressed: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'tomo_couch_insertion',
         KEY_OUT_TEST: 'Tomo Couch insertion height correct and no collisions with bore',
         'options': 'Yes,NA,No'},
        {'key': 'sim_fiducial_or_shifts',
         KEY_OUT_TEST: 'Sim Fiducial point set to match BB location or Shifts Document',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'non_repro_tpo_structures_blocked',
         KEY_OUT_TEST: 'Only non-reproducible and TPO-indicated structures blocked',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'tpo_clinical_goals',
         KEY_OUT_TEST: 'TPO Clinical Goals Entered',
         'options': 'Yes,NA,No'},
        {'key': 'auto_r0a0_plans',
         KEY_OUT_TEST: 'Auto and R0A0 Plans are identical in Dose',
         'options': 'Yes,NA,No'},
        {'key': 'modulation_factor',
         KEY_OUT_TEST: 'Modulation factor < 2.2',
         'options': 'Yes,NA,No'},
        {'key': 'bev_movie',
         KEY_OUT_TEST: 'Beams Eye View Movie shows only target is treated',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time',
         KEY_OUT_TEST: 'Treatment time appropriate for plan',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['ADAPTIVE']: [
        {'key': 'idms_adaptive',
         KEY_OUT_TEST: 'iDMS Adaptive: treated fractions discontinued in new plan',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_VMAT = {
    REVIEW_LEVELS['PATIENT_MODEL']: [
    ],
    REVIEW_LEVELS['PATIENT_MODEL']: [
        {'key': 'planning_structure_script',
         KEY_OUT_TEST: 'Generate planning structure script used',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['PLAN_DESIGN']: [
        {'key': 'dose_grid_resolution_SBRT',
         KEY_OUT_TEST: 'Dose grid resolution set to 0.2 (or 0.15 for SBRT)',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_lateral_offset',
         KEY_OUT_TEST: 'Isocenter lateral offset < 5 cm for plans using full arcs',
         'options': 'Yes,NA,No'},
    ],
    REVIEW_LEVELS['OPTIMIZATION']: [
        {'key': 'clinical_goals_script_tpo',
         KEY_OUT_TEST: 'Clinical goals script used and matches TPO template name',
         'options': 'Yes,NA,No'},
        {'key': 'treat_setting',
         KEY_OUT_TEST: 'Treat setting used',
         'options': 'Yes,NA,No'},
        {'key': 'automated_plan_optimization',
         KEY_OUT_TEST: 'Automated Plan Optimization script used',
         'options': 'Yes,NA,No'},
        {'key': 'beam_weights',
         KEY_OUT_TEST: 'Beam weights > 5%',
         'options': 'Yes,NA,No'},
        {'key': 'couch_angle_rpm',
         KEY_OUT_TEST: 'Couch angle < 45 degrees for RPM gating plans',
         'options': 'Yes,NA,No'},
    ]
}

#
# LOG PARSING INFO
LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\logs"
DEV_LOG_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs"
KEEP_PHRASES = [("Critical", "CRITICAL"), ("Warnings", "WARNING"),
                ("Info", "INFO"), ("Debug", "DEBUG")]
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
DOSE_FRACTION_PAIRS = [(4, 2000), (5, 2000)]  # Often mixed up fractionations
#
# DOSE TOLERANCES
NO_FLY_DOSE = 100.  # cGy
PACEMAKER_DOSE = 200.  # cGy
#
# DOSE GRID PREFERENCES
DOSE_GRID_DEFAULT = 0.2  # 2 mm

PLAN_NAMES = {'LUNG_SBRT':
                  ['LUL', 'LLL', 'RUL', 'RML', 'RLL', 'LunR_SBR', 'LunL_SBR',
                   'LuLU_SBR', 'LuLL_SBR', 'LuRU_SBR', 'LuRM_SBR', 'LuRL_SBR'],
              'BREAST_SBRT':
                  ['BreR_SBR', 'BreL_SBR', ],
              'ABDOMEN_SBRT':
                  ['Abdo_SBR', 'LivR_SBR', 'Panc_SBR', ],
              'PELVIS_SBRT':
                  ['Pelv_SBR', 'HipR_SBR', 'HipL_SBR'],
              'BRAIN_FSRT':
                  ['Brai_SBR', 'Brai_FSR', 'PTV1_FSR', 'PTV2_FSR', 'PTV3_FSR', 'PTV4_FSR',
                   'PTV5_FSR'],
              'SPINE_SBRT':
                  ['SpiT_SBR', 'SpiC_SBR', 'SpiL_SBR'],
              'HEAD_NECK_SBRT':
                  ['NecB_SBR', 'NecR_SBR', 'NecL_SBR'],
              'SRS':
                  ['SRS'],
              'TBI':
                  ['TBI'],
              'VMAT':
                  ['VMA', '3CA'],
              'THI':
                  ['THI', 'T3D'],
              '3D':
                  '3CA'
              }

GRID_PREFERENCES = {
    'SBRT': {
        'PLAN_NAMES': PLAN_NAMES['LUNG_SBRT'] + PLAN_NAMES['BREAST_SBRT'] \
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
}
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
             'SUPPORTS': ['TomoCouch']
             }

TRUEBEAM_DATA = {'MACHINES': ['TrueBeam', 'TrueBeamSTx'],
                 'SUPPORTS': ['TrueBeamCouch', 'CivcoBaseShell_Cork', 'CivcoInclineShell_Wax',
                              'Sframe_F1_TBCouch_HN'],
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
             'ProneBreastBoard': 'Cartilage'}
# PLANNING PREFERENCES - CLINICAL
TOMO_PREFERENCES = {
    'ABDOMEN': {'ALIAS': ['Abdo_THI', 'Livr_THI', 'Panc_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.6},
    'BRAIN': {'ALIAS': ['Brai_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.6},
    'BREAST': {'ALIAS': ['BreL_THI', 'BreR_THI', 'ChwL_THI', 'ChwR_THI'], 'MF_HIGH': 2.8,
               'MF_LOW': 2.4},
    'CSI': {'ALIAS': ['CSI_THI'], 'MF_HIGH': 2.2, 'MF_LOW': 1.8},
    'EXTREMITY': {'ALIAS': ['ArmL_THI', 'ArmR_THI', 'LegL_THI', 'LegR_THI'], 'MF_HIGH': 2.4,
                  'MF_LOW': 2.0},
    'GYN': {'ALIAS': ['Vulv_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.8},
    'HN': {'ALIAS': ['NecB_THI', 'NecR_THI', 'NecL_THI'], 'MF_HIGH': 2.6, 'MF_LOW': 2.2},
    'LUNG-NO-SBRT': {'ALIAS': ['LunL_THI', 'LunR_THI', 'LunB_THI', 'Medi_THI'], 'MF_HIGH': 2.8,
                     'MF_LOW': 2.4},
    'LUNG-SBRT': {'ALIAS': PLAN_NAMES['LUNG_SBRT'], 'MF_HIGH': 1.4, 'MF_LOW': 1.2},
    'PELVIS': {'ALIAS': ['Pelv_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 1.8},
    'PROSTATE-LOW-RISK': {'ALIAS': ['Pros_THI'], 'MF_HIGH': 2.2, 'MF_LOW': 1.6},
    'PROSTATE-HIGH-RISK': {'ALIAS': ['ProN_THI', 'ProF_THI'], 'MF_HIGH': 2.4, 'MF_LOW': 2.0},
    'TOMO_3D': {'ALIAS': ['T3D'], 'MF_HIGH': 2.2, 'MF_LOW': 1.1},
}
