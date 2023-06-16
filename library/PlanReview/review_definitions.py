""" review_definitions.py
All functional assumptions made in deployment of the UW physics/dosimetry
check script

"""
import os

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
#
# CHECKBOXES are qa_tests that must be manually performed
CHECK_BOXES_PHYSICS_REVIEW = {
    'Plan Data': [
        {'key': 'plan_name_tpo',
         'test_name': 'Plan Name is consistent with TPO',
         'options': 'Yes,NA,No'},
        {'key': 'plan_approved_md',
         'test_name': 'Plan is approved by MD',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_beamset.check_beamset_approved'},
    ],
    'Preplanning Data': [
        {'key': 'ct_images_match',
         'test_name': 'CT images match RayStation Modality/Patient Name/MRN',
         'options': 'Yes,NA,No'},
        {'key': 'ct_images_number',
         'test_name': 'Number of CT images matches CT simulation document',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_examination.check_exam_date_and_slices'},
        {'key': 'ct_images_scan_datetime',
         'test_name': 'CT images Scan Date/Time matches CT simulation document',
         'options': 'Yes,NA,No',
         'replaced': 'qa_tests.test_examination.check_exam_date_and_slices'},
        {'key': 'ct_orientation',
         'test_name': 'CT orientation matches report',
         'options': 'Yes,NA,No'},
        {'key': 'immobilization_protocol',
         'test_name': 'Immobilization matches protocol and is reproducible',
         'options': 'Yes,NA,No'},
        {'key': 'no_artifacts',
         'test_name': 'No significant imaging artifacts present',
         'options': 'Yes,NA,No'},
        {'key': 'special_instructions',
         'test_name': 'Special instructions (FB, MIBH) are noted in treatment planning order',
         'options': 'Yes,NA,No'},
    ],
    'Patient Modeling': [
        {'key': 'md_approved_mim',
         'test_name': 'If contoured in MIM, MD approved session',
         'options' :'Yes,NA,No'},
        {'key': 'mim_statistics_match',
         'test_name': 'If contoured in MIM, Statistics/gross appearance matches RayStation',
         'options': 'Yes,NA,No'},
        {'key': 'mim_fusions',
         'test_name': 'Fusions in MIM are accurate',
         'options': 'Yes,NA,No'},
        {'key': 'mim_tpo_contours',
         'test_name': 'TPO listed contours are correctly interpolated',
         'options': 'Yes,NA,No'},
        {'key': 'mim_no_stray_voxels',
         'test_name': 'No stray voxels in the targets.',
         'options': 'Yes,NA,No'},
        {'key': 'mim_contour_extents',
         'test_name': 'Regions at risk near targets are contoured and sufficient for the plan',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_retracted',
         'test_name': 'PTV is retracted from skin at least 3mm',
         'options': 'Yes,NA,No'},
        {'key': 'density_overrides_contoured',
         'test_name': 'Density overrides are contoured',
         'options': 'Yes,NA,No'},
        {'key': 'density_overrides',
         'test_name': 'Density overrides Material assignment is appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'density_override_rois',
         'test_name': 'Density override ROIs do not overlap',
         'options': 'Yes,NA,No'},
        {'key': 'external_contour',
         'test_name': 'External contour is set correctly and does not include couch',
         'options': 'Yes,NA,No'},
        {'key': 'immobilization_devices',
         'test_name': 'Immobilization devices and couch added as structures are added correctly',
         'options': 'Yes,NA,No'},
        {'key': 'bolus_custom_devices',
         'test_name': 'Bolus and custom devices are physically and dosimetrically realistic',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'beam_names_correct',
         'test_name': 'Beam Names are correct',
         'options': 'Yes,NA,No'},
        {'key': 'beams_single_machine',
         'test_name': 'Beams are assigned to a single machine',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_placement',
         'test_name': 'Isocenter placement is appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'beams_not_through_mobile_objects',
         'test_name': 'Beams do not treat through mobile objects (arms, chin, legs)',
         'options': 'Yes,NA,No'},
        {'key': 'beam_apertures',
         'test_name': 'Beam Apertures are reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'matched_field_junctions',
         'test_name': 'Any matched field junctions are reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_prior_rt',
         'test_name': 'Overlap with prior RT is reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_resolution',
         'test_name': 'Dose grid Resolution is 2mm or less',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_coverage',
         'test_name': 'Dose Grid covers patient and support structures',
         'options': 'Yes,NA,No'},
        {'key': 'prescription',
         'test_name': 'Prescription matches TPO',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_volume',
         'test_name': 'Prescription is based on volume (preferred) or isodose line',
         'options': 'Yes,NA,No'},
    ],
    'Plan Evaluation': [
        {'key': 'dose_distribution',
         'test_name': 'Dose distribution looks reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'tpo_goals_constraints',
         'test_name': 'TPO goals and constraints are entered in clinical '
                      'goals and reasonably addressed',
         'options': 'Yes,NA,No'},
    ],
    'Mobius': [
        {'key': 'couch_removal_height',
         'test_name': 'Confirm couch removal height',
         'options': 'Yes,NA,No'},
        {'key': 'target_identification',
         'test_name': 'Target identification is correct',
         'options': 'Yes,NA,No'},
        {'key': 'structure_classification',
         'test_name': 'Classification of each structure is correct',
         'options': 'Yes,NA,No'},
        {'key': 'gamma_review',
         'test_name': 'Review gamma: 5%/3mm > 90%',
         'options': 'Yes,NA,No'},
        {'key': 'review_dose_acs',
         'test_name': 'Review dose in A, C, S',
         'options': 'Yes,NA,No'},
        {'key': 'beam_info_mobius',
         'test_name': 'Beam information in Mobius Clearance/deliverable are green',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_raystation_dose',
         'test_name': 'Mobius RayStation Dose difference is consistent with report',
         'options': 'Yes,NA,No'},
    ],

}
CHECK_BOXES_PHYSICS_REVIEW_3D = {
    'Plan Data': [
    ],
    'Preplanning Data': [
    ],
    'Patient Modeling': [
        {'key': 'sim_fiducials_alignment',
         'test_name': 'SimFiducials localization point alignment matches BBs,'
                      ' or AlignRT is noted in CT Sim',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'modality_energy',
         'test_name': 'Modality and Energy match TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_correct_isocenter',
         'test_name': 'Beams are assigned to the correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'btv_avoid_mlc',
         'test_name': 'BTV and AVOID are used to define MLC shapes',
         'options': 'Yes,NA,No'},
        {'key': 'wedges_placement',
         'test_name': 'Any wedges are intuitively placed',
         'options': 'Yes,NA,No'},
        {'key': 'beam_flash',
         'test_name': 'Beam Flash is present on breast or areas with potential'
                      ' out-of-field movement',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         'test_name': 'Beam MU is reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'beam_divergence',
         'test_name': 'Beam divergence is appropriate',
         'options': 'Yes,NA,No'},
    ],
    'Plan Evaluation': [
    ],
    'Mobius': [
    ]
}
CHECK_BOXES_PHYSICS_REVIEW_VMAT = {
    'Plan Settings': [
    ],
    'Preplanning Data': [
    ],
    'Patient Modeling': [
        {'key': 'sim_fiducials_alignment',
         'test_name': 'SimFiducials localization point alignment matches BBs,'
                      ' or AlignRT is noted in CT Sim',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_retracted',
         'test_name': 'PTV is retracted from skin at least 3mm',
         'options': 'Yes,NA,No'},
        {'key': 'prv_volumes',
         'test_name': 'PRV volumes are drawn for serial OARs',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'modality_energy',
         'test_name': 'Modality, Energy match TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_correct_isocenter',
         'test_name': 'Beams are assigned to the correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'arc_geometry',
         'test_name': 'Arc Geometry: Arcs match SmartArc Tolerance Tables',
         'options': 'Yes,NA,No'},
        {'key': 'collimator_angle',
         'test_name': 'Collimator angle differs on arcs',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_opening',
         'test_name': 'Jaw opening is sensible for target size',
         'options': 'Yes,NA,No'},
        {'key': 'arc_protect_blocking',
         'test_name': 'Arc protect or dosimetric Blocking is used to avoid'
                      ' low-reproducibility objects',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         'test_name': 'Beam MU is reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_prior_rt',
         'test_name': 'Overlap with prior RT is reviewed',
         'options': 'Yes,NA,No'},
        {'key': 'plan_setup',
         'test_name': 'Plan setup: Use of beam set dependency is appropriate'
                      ' (for previous dose '
                      'or multiple isocenter optimization)',
         'options': 'Yes,NA,No'},
    ],
    'Optimization': [
        {'key': 'objective_type',
         'test_name': 'Objective type is correct for targets/OAR',
         'options': 'Yes,NA,No'},
        {'key': 'optimization_settings',
         'test_name': 'Optimization settings: 2-degree gantry spacing',
         'options': 'Yes,NA,No'},
    ],
    'Plan Evaluation': [
    ],
    'Mobius': [
    ]
}

CHECK_BOXES_PHYSICS_REVIEW_ELECTRONS = {
    'Plan Design': [
        {'key': 'modality_energy_matches_tpo',
         'test_name': 'Modality, Energy matches TPO',
         'options': 'Yes,NA,No'},
        {'key': 'beams_assigned_correct_isocenter',
         'test_name': 'Beams assigned to correct isocenter',
         'options': 'Yes,NA,No'},
        {'key': 'beam_ssd_set_correctly',
         'test_name': 'Beam SSD set correctly 100 SSD for A6, 105 SSD otherwise',
         'options': 'Yes,NA,No'},
        {'key': 'beam_source_to_surface',
         'test_name': 'Beam source to surface should be to skin if no bolus,'
                      ' to surface if bolus',
         'options': 'Yes,NA,No'},
        {'key': 'beam_reasonably_en_face',
         'test_name': 'Beam is reasonably en face',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu_reasonable',
         'test_name': 'Beam MU reasonable',
         'options': 'Yes,NA,No'},
    ],
    'Electron Dose': [
        {'key': 'histories_per_cm2',
         'test_name': 'Number of histories ≥500K per cm2',
         'options': 'Yes,NA,No'},
    ],
    'Plan Settings': [],
    'Preplanning Data': [],
    'Patient Modeling': [
        {'key': 'sim_fiducials_alignment',
         'test_name': 'SimFiducials localization point alignment matches'
                      ' BBs, or AlignRT is noted '
                      'in CT Sim',
         'options': 'Yes,NA,No'},
    ],
    'Optimization': [],
    'Plan Evaluation': [],
    'Mobius': [],
}

CHECK_BOXES_PHYSICS_REVIEW_TOMO3D = {
    'Patient Modeling': [
        {'key': 'tomocouch_inserted_correctly',
         'test_name': 'TomoCouch is inserted correctly',
         'options': 'Yes,NA,No'},
        {'key': 'simfiducials_localization_alignment',
         'test_name': 'SimFiducials localization point alignment matches BBs',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'patient_shifts_no_collision',
         'test_name': 'Patient shifts will not lead to a collision',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_target_in_fov',
         'test_name': 'Patient shifts will place target in '
                      'MVCT Field of View (FOV)',
         'options': 'Yes,NA,No'},
        {'key': 'targets_separated_by_7_cm',
         'test_name': 'Targets separated by > 7 cm apart are treated'
                      ' with separate beamsets',
         'options': 'Yes,NA,No'},
        {'key': 'beam_modulation_factor',
         'test_name': 'Beam Modulation Factor < 2.2',
         'options': 'Yes,NA,No'},
        {'key': 'beam_field_width',
         'test_name': 'Beam Field Width is 5.05 cm',
         'options': 'Yes,NA,No'},
        {'key': 'beam_pitch',
         'test_name': 'Beam Pitch is 0.287',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_isocenter_lateral',
         'test_name': 'Treatment Isocenter lateral < 2 cm',
         'options': 'Yes,NA,No'},
    ],
    'Optimization': [
        {'key': 'optimization_on_targets_external',
         'test_name': 'Optimization on targets and External only',
         'options': 'Yes,NA,No'},
        {'key': 'protect_entry_exit_blocking',
         'test_name': 'Protect: "Entry" and "Entry/Exit" used to '
                      'block appropriate OARs',
         'options': 'Yes,NA,No'},
        {'key': 'fov_artifacts_addressed_blocked',
         'test_name': 'FOV artifacts are addressed or blocked',
         'options': 'Yes,NA,No'},
        {'key': 'low_reproducibility_anatomy_blocked',
         'test_name': 'Low reproducibility anatomy is blocked '
                      'with a margin of > 2 cm',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_mode_dynamic',
         'test_name': 'Jaw mode is Dynamic',
         'options': 'Yes,NA,No'},
    ],
    'Plan Evaluation': [
        {'key': 'plan_dvh_goals_identical',
         'test_name': 'Plan DVH and goals are identical to the _Auto plan',
         'options': 'Yes,NA,No'},
    ],
    'Transfer Plan': [
        {'key': 'transfer_plan_dose_distribution',
         'test_name': 'Transfer plan dose distribution and DVHs reviewed,'
                      ' match with Primary Plan',
         'options': 'Yes,NA,No'},
        {'key': 'transfer_plan_locked_approved',
         'test_name': 'Transfer plan is locked and approved by Dosimetry'
                      ' in RayStation',
         'options': 'Yes,NA,No'},
    ],
    'Plan Settings': [],
    'Preplanning Data': [],
    'Mobius': [],
}

CHECK_BOXES_PHYSICS_REVIEW_TOMO = {
    'Patient Modeling': [
        {'key': 'tomocouch_inserted_correctly',
         'test_name': 'TomoCouch is inserted correctly',
         'options': 'Yes,NA,No'},
        {'key': 'simfiducials_localization_alignment',
         'test_name': 'SimFiducials localization point alignment matches BBs',
         'options': 'Yes,NA,No'},
    ],
    'Transfer Plan': [
        {'key': 'transfer_plan_dose_distribution',
         'test_name': 'Transfer plan dose distribution and DVHs reviewed,'
                      ' match with Primary Plan',
         'options': 'Yes,NA,No'},
        {'key': 'transfer_plan_locked_approved',
         'test_name': 'Transfer plan is locked and approved by Dosimetry'
                      ' in RayStation',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'beamsets_assigned_same_machine',
         'test_name': 'Beamsets are assigned to the same machine',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_lateral_position',
         'test_name': 'Isocenter lateral position is <2 cm, '
                      'or a patient alert to break indexing is created',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_no_collision',
         'test_name': 'Patient shifts will not lead to a collision',
         'options': 'Yes,NA,No'},
        {'key': 'patient_shifts_target_in_fov',
         'test_name': 'Patient shifts place target in MVCT Field of View (FOV)',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time_less_than_600',
         'test_name': 'Treatment time is < 600 s '
                      'or explained in Dosimetry Safety Sheet',
         'options': 'Yes,NA,No'},
    ],
    'Optimization': [
        {'key': 'objective_type_correct',
         'test_name': 'Objective type is correct for targets/OAR',
         'options': 'Yes,NA,No'},
        {'key': 'protect_entry_exit_blocking',
         'test_name': 'Protect: "Entry" and "Entry/Exit" used'
                      ' to block appropriate OARs',
         'options': 'Yes,NA,No'},
        {'key': 'fov_artifacts_addressed_blocked',
         'test_name': 'FOV artifacts are addressed or blocked',
         'options': 'Yes,NA,No'},
        {'key': 'low_reproducibility_anatomy_blocked',
         'test_name': 'Low reproducibility anatomy is blocked'
                      ' with a margin of > 2 cm',
         'options': 'Yes,NA,No'},
        {'key': 'review_beams_eye_view',
         'test_name': 'Review Beam\'s eye view',
         'options': 'Yes,NA,No'},
    ],
    'Plan Evaluation': [],
    'Plan Settings': [],
    'Preplanning Data': [],
    'Mobius': [],
}

CHECK_BOXES = {
    'Plan Settings': [
        {'key': 'plan_name',
         'test_name': 'Plan Name consistent with TPO',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_placement',
         'test_name': 'Isocenter placement appropriate',
         'options': 'Yes,NA,No'},
        {'key': 'arcs_match',
         'test_name': 'Arcs match SmartArc Tolerance Tables',
         'options': 'Yes,NA,No'},
        {'key': 'collimator_angle',
         'test_name': 'Collimator angle differs on arcs',
         'options': 'Yes,NA,No'},
        {'key': 'jaw_opening',
         'test_name': 'Jaw opening sensible for target size',
         'options': 'Yes,NA,No'},
        {'key': 'blocking',
         'test_name': 'Blocking used to avoid low-reproducibility objects',
         'options': 'Yes,NA,No'},
        {'key': 'beam_mu',
         'test_name': 'Beam MU reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'beam_apertures',
         'test_name': 'Beam Apertures reasonable',
         'options': 'Yes,NA,No'},
        {'key': 'invivo_dosimetry',
         'test_name': 'Order generated for TLDs if needed',
         'options': 'Yes,NA,No'}
    ],
    'Simulation': [
        {'key': 'immobilization',
         'test_name': 'Immobilization matches protocol',
         'options': 'Yes,NA,No'},
        {'key': 'artifacts',
         'test_name': 'No significant artifacts present',
         'options': 'Yes,NA,No'},
    ],
    'Contouring': [
        {'key': 'contoured',
         'test_name': 'If contoured in MIM MD approved session',
         'options': 'Yes,NA,No'},
        {'key': 'statistics',
         'test_name': 'Statistics/gross appearance matches RayStation',
         'options': 'Yes,NA,No'},
        {'key': 'mim_fusion',
         'test_name': 'MIM Fusion Accurate',
         'options': 'Yes,NA,No'},
        {'key': 'stray_voxels',
         'test_name': 'No stray voxels in targets',
         'options': 'Yes,NA,No'},
        {'key': 'density_override',
         'test_name': 'Density overrides Material assignment appropriate',
         'options': 'Yes,NA,No'},
    ],
    'Dose Calculation': [
        {'key': 'ptv_skin',
         'test_name': 'PTV skin involvement confirmed',
         'options': 'Yes,NA,No'},
        {'key': 'bolus_custom',
         'test_name': 'Bolus and custom devices physically'
                      + ' and dosimetrically realistic',
         'options': 'Yes,NA,No'},
        {'key': 'overlap_reviewed',
         'test_name': 'Overlap with prior RT Reviewed',
         'options': 'Yes,NA,No'},
    ]
}
# SAFETY REVIEWS FOR DOSE
CHECK_BOXES_DOSE = {
    'Patient Data': [
        {'key': 'primary_image_set',
         'test_name': 'Correct image set used as primary',
         'options': 'Yes,NA,No'},
        {'key': 'patient_info',
         'test_name': 'Correct patient information (name, MRN, image #, orientation)',
         'options': 'Yes,NA,No'},
        {'key': 'ivdt_table',
         'test_name': 'Correct IVDT table used',
         'options': 'Yes,NA,No'},
        {'key': 'case_data',
         'test_name': 'Case data entered to match Course # in Aria, treatment site, MD',
         'options': 'Yes,NA,No'},
        {'key': 'slice_thickness',
         'test_name': 'Slice thickness appropriate for plan type',
         'options': 'Yes,NA,No'},
    ],
    'Patient Modeling': [
        {'key': 'approved_structure_set',
         'test_name': 'MD approved structure set',
         'options': 'Yes,NA,No'},
        {'key': 'contours_cleaned',
         'test_name': 'Contours interpolated and cleaned',
         'options': 'Yes,NA,No'},
        {'key': 'structure_template_loaded',
         'test_name': 'Structure Template Loaded: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'ptv_expansions',
         'test_name': 'PTV expansions per table',
         'options': 'Yes,NA,No'},
        {'key': 'sim_fiducial',
         'test_name': 'Sim Fiducial point set to match BB location',
         'options': 'Yes,NA,No'},
        {'key': 'ct_cutoff',
         'test_name': 'CT cutoff addressed',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'plan_beam_names',
         'test_name': 'Plan and beam set names match treatment site',
         'options': 'Yes,NA,No'},
        {'key': 'machine_correct',
         'test_name': 'Machine correct: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'dose_grid_resolution',
         'test_name': 'Dose grid resolution set to 0.2',
         'options': 'Yes,NA,No'},
        {'key': 'isodose_display',
         'test_name': 'Isodose line display set to Absolute values',
         'options': 'Yes,NA,No'},
        {'key': 'clinical_goals',
         'test_name': 'Clinical goals entered',
         'options': 'Yes,NA,No'},
        {'key': 'final_dose_calc_script',
         'test_name': 'Final Dose calculation script used',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_ELECTRON = {
    'Patient Data': [
    ],
    'Patient Modeling': [
        {'key': 'density_overrides',
         'test_name': 'Density overrides set appropriately and do not overlap external',
         'options': 'Yes,NA,No'},
        {'key': 'couch_structure',
         'test_name': 'TrueBeam couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'en_face_beam_angle',
         'test_name': 'En face beam angle used',
         'options': 'Yes,NA,No'},
        {'key': 'statistical_uncertainty',
         'test_name': 'Dose Statistical uncertainty < 1%',
         'options': 'Yes,NA,No'},
        {'key': 'ssd_cones',
         'test_name': 'SSD = 100 cm for 6x6 cone or 105 for all other cones, SSD to skin for no '
                      'bolus or to surface for bolus',
         'options': 'Yes,NA,No'},
        {'key': 'cutout_shape',
         'test_name': 'Cutout: Shape: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'cutout_name',
         'test_name': 'Cutout Name is accessory code',
         'options': 'Yes,NA,No'},
        {'key': 'bolus',
         'test_name': 'Bolus: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_based_volume',
         'test_name': 'Prescription based on volume',
         'options': 'Yes,NA,No'},
        {'key': 'printing_cutout',
         'test_name': 'Printing: cutout printed to correct scale factor of 1.00',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_water_phantom',
         'test_name': 'Mobius QuickCalc: Water phantom QA plan created',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_cutout_dimensions',
         'test_name': 'Mobius QuickCalc: Cutout dimensions correct',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_dmax_dose',
         'test_name': 'Mobius QuickCalc: Dmax dose entered into QuickCalc',
         'options': 'Yes,NA,No'},
        {'key': 'mobius_quickcalc_agreement',
         'test_name': 'Mobius QuickCalc: Agreement within 5%',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_TOMO = {
    'Patient Data Management': [
    ],
    'Patient Modeling': [
        {'key': 'generate_planning_structure_script',
         'test_name': 'Generate planning structure script used',
         'options': 'Yes,NA,No'},
        {'key': 'targets_retracted',
         'test_name': 'Targets retracted 3 mm from surface (PTV eval used)',
         'options': 'Yes,NA,No'},
        {'key': 'tomo_couch_structure',
         'test_name': 'Tomo couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'beam_added_no_collision',
         'test_name': 'Beam added with no collision via machine geometry',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_offsets',
         'test_name': 'Isocenter lateral offset < 3 cm and In/Out offset < 18 cm',
         'options': 'Yes,NA,No'}],
    'Plan Optimization': [
        {'key': 'clinical_goals_script',
         'test_name': 'Clinical goals script used and matches TPO template name',
         'options': 'Yes,NA,No'},
        {'key': 'dynamic_jaws',
         'test_name': 'Dynamic Jaws used on 2.5 and 5 cm plans',
         'options': 'Yes,NA,No'},
        {'key': 'field_width',
         'test_name': 'Field width < Target length',
         'options': 'Yes,NA,No'},
        {'key': 'pitch',
         'test_name': 'Pitch appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'modulation_factor',
         'test_name': 'Modulation factor appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time',
         'test_name': 'Treatment time appropriate for plan',
         'options': 'Yes,NA,No'},
        {'key': 'structures_blocked',
         'test_name': 'Structures are blocked per protocol if applicable',
         'options': 'Yes,NA,No'},
        {'key': 'plan_optimization_script',
         'test_name': 'Plan optimization script used',
         'options': 'Yes,NA,No'},
    ],
    'Adaptive Planning': [
        {'key': 'idms_adaptive',
         'test_name': 'iDMS Adaptive: treated fractions discontinued in new plan',
         'options': 'Yes,NA,No'},
    ]
}
CHECK_BOXES_DOSE_3D = {
    'Patient Data': [
    ],
    'Patient Modeling': [
        {'key': 'highz_artifacts',
         'test_name': 'High-Z artifacts & density overrides addressed: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'couch_structure',
         'test_name': 'TrueBeam couch structure present and set to correct height',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'btv_created',
         'test_name': 'BTV created and derived based on PTV',
         'options': 'Yes,NA,No'},
        {'key': 'beam_template_used',
         'test_name': 'Beam template used: Choose One ',
         'options': 'Yes,NA,No'},
        {'key': 'no_low_repro_objects',
         'test_name': 'Beam(s) do not pass through low-reproducibility objects (ie: head of '
                      'table)',
         'options': 'Yes,NA,No'},
        {'key': 'treat_protect',
         'test_name': 'Treat & Protect settings used',
         'options': 'Yes,NA,No'},
        {'key': 'prescription_type',
         'test_name': 'Prescription based on volume or isodose line',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_TOMO_3D = {
    'Patient Data Management': [
    ],
    'Patient Modeling': [
        {'key': 'highz_artifacts',
         'test_name': 'High-Z artifacts & density overrides addressed: Choose One',
         'options': 'Yes,NA,No'},
        {'key': 'tomo_couch_insertion',
         'test_name': 'Tomo Couch insertion height correct and no collisions with bore',
         'options': 'Yes,NA,No'},
        {'key': 'sim_fiducial_or_shifts',
         'test_name': 'Sim Fiducial point set to match BB location or Shifts Document',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'non_repro_tpo_structures_blocked',
         'test_name': 'Only non-reproducible and TPO-indicated structures blocked',
         'options': 'Yes,NA,No'},
    ],
    'Plan Optimization': [
        {'key': 'tpo_clinical_goals',
         'test_name': 'TPO Clinical Goals Entered',
         'options': 'Yes,NA,No'},
        {'key': 'auto_r0a0_plans',
         'test_name': 'Auto and R0A0 Plans are identical in Dose',
         'options': 'Yes,NA,No'},
        {'key': 'modulation_factor',
         'test_name': 'Modulation factor < 2.2',
         'options': 'Yes,NA,No'},
        {'key': 'bev_movie',
         'test_name': 'Beams Eye View Movie shows only target is treated',
         'options': 'Yes,NA,No'},
        {'key': 'treatment_time',
         'test_name': 'Treatment time appropriate for plan',
         'options': 'Yes,NA,No'},
    ],
    'Adaptive': [
        {'key': 'idms_adaptive',
         'test_name': 'iDMS Adaptive: treated fractions discontinued in new plan',
         'options': 'Yes,NA,No'},
    ]
}

CHECK_BOXES_DOSE_VMAT = {
    'Patient Data Management': [
    ],
    'Patient Modeling': [
        {'key': 'planning_structure_script',
         'test_name': 'Generate planning structure script used',
         'options': 'Yes,NA,No'},
    ],
    'Plan Design': [
        {'key': 'dose_grid_resolution_SBRT',
         'test_name': 'Dose grid resolution set to 0.2 (or 0.15 for SBRT)',
         'options': 'Yes,NA,No'},
        {'key': 'isocenter_lateral_offset',
         'test_name': 'Isocenter lateral offset < 5 cm for plans using full arcs',
         'options': 'Yes,NA,No'},
    ],
    'Plan Optimization': [
        {'key': 'clinical_goals_script_tpo',
         'test_name': 'Clinical goals script used and matches TPO template name',
         'options': 'Yes,NA,No'},
        {'key': 'treat_setting',
         'test_name': 'Treat setting used',
         'options': 'Yes,NA,No'},
        {'key': 'automated_plan_optimization',
         'test_name': 'Automated Plan Optimization script used',
         'options': 'Yes,NA,No'},
        {'key': 'beam_weights',
         'test_name': 'Beam weights > 5%',
         'options': 'Yes,NA,No'},
        {'key': 'couch_angle_rpm',
         'test_name': 'Couch angle < 45 degrees for RPM gating plans',
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
