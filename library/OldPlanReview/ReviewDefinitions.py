import os

# OUTPUT DIR
OUTPUT_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs"
ERROR_DIR = r"Q:\\RadOnc\RayStation\RayScripts\dev_logs\Errors\ReviewScript"
icon_dir = os.path.join(os.path.dirname(__file__), ".\Icons")
RED_CIRCLE = os.path.join(icon_dir, "Red_Circle_icon.png")
GREEN_CIRCLE = os.path.join(icon_dir, "Green_Circle_icon.png")
YELLOW_CIRCLE = os.path.join(icon_dir, "Yellow_Circle_icon.png")
BLUE_CIRCLE = os.path.join(icon_dir, "Blue_Circle_icon.png")
UW_HEALTH_LOGO = os.path.join(icon_dir, "UW_Health_Logo.png")
# RESULT STRINGS
PASS = "Pass"
FAIL = "Fail"
ALERT = "Alert"

# Level keys
LEVELS = {
    'PATIENT_KEY': "PATIENT_LEVEL",
    'EXAM_KEY': "EXAM_LEVEL",
    'PLAN_KEY': "PLAN_LEVEL",
    'BEAMSET_KEY': "BEAMSET_LEVEL",
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
# TODO: CHECKBOXES SHOULD BE BEAMSET DEPENDENT
CHECK_BOXES = {
    'Plan Settings': [
        {'key': 'plan_name', 'beam_type': None,
         'text': 'Plan Name consistent with TPO'},
        {'key': 'isocenter_placement', 'beam_type': None,
         'text': 'Isocenter placement appropriate'},
        {'key': 'arcs_match', 'beam_type': 'VMAT',
         'text': 'Arcs match SmartArc Tolerance Tables'},
        {'key': 'collimator_angle', 'beam_type': 'VMAT',
         'text': 'Collimator angle differs on arcs'},
        {'key': 'jaw_opening', 'beam_type': None,
         'text': 'Jaw opening sensible for target size'},
        {'key': 'blocking', 'beam_type': None,
         'text': 'Blocking used to avoid low-reproducibility objects'},
        {'key': 'beam_mu', 'beam_type': None,
         'text': 'Beam MU reasonable'},
        {'key': 'beam_apertures', 'beam_type': None,
         'text': 'Beam Apertures reasonable'},
    ],
    'Simulation': [
        {'key': 'immobilization', 'beam_type': None,
         'text': 'Immobilization matches protocol'},
        {'key': 'artifacts', 'beam_type': None,
         'text': 'No significant artifacts present'},
    ],
    'Contouring': [
        {'key': 'contoured', 'beam_type': None,
         'text': 'If contoured in MIM MD approved session'},
        {'key': 'statistics', 'beam_type': None,
         'text': 'Statistics/gross appearance matches RayStation'},
        {'key': 'mim_fusion', 'beam_type': None,
         'text': 'MIM Fusion Accurate'},
        {'key': 'stray_voxels', 'beam_type': None,
         'text': 'No stray voxels in targets'},
        {'key': 'density_override', 'beam_type': None,
         'text': 'Density overrides Material assignment appropriate'},
    ],
    'Dose Calculation': [
        {'key': 'ptv_skin', 'beam_type': None,
         'text': 'PTV skin involvement confirmed'},
        {'key': 'bolus_custom', 'beam_type': None,
         'text': 'Bolus and custom devices physically'
                 + ' and dosimetrically realistic'},
        {'key': 'overlap_reviewed', 'beam_type': None,
         'text': 'Overlap with prior RT Reviewed'},
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
