"""
tbi_definitions.py

This module contains constants and configuration values used throughout the TBI autoplanning workflow.
All values are project-specific and are used for protocol, plan, beamset, and ROI naming, as well as for geometric and dosimetric parameters.
"""

import math
import os

# Folder and path definitions for protocol and output locations
PROTOCOL_FOLDER = r'../../protocols'
INSTITUTION_FOLDER = r'UW'
AUTOPLAN_FOLDER = r'AutoPlans'
PATH_PROTOCOLS = os.path.join(os.path.dirname(__file__),
                              PROTOCOL_FOLDER, INSTITUTION_FOLDER, AUTOPLAN_FOLDER)
PATH_TO_OUTPUT = os.path.normpath(
    "Q:\\RadOnc\\RayStation\\RayScripts\\AutoPlanData")
DICOM_PATH = os.path.normpath('\\\\m-rayscon02587\\DicomImageStorage')

# Protocol and plan/beamset naming conventions
PROTOCOL_FILE_TOMO = "TomoTBI.xml"
PROTOCOL_NAME_TOMO = "UW Tomo TBI"
ORDER_NAME_FFS_TOMO = "TomoTBI_FFS"
ORDER_NAME_HFS_TOMO = "TomoTBI_HFS"
ORDER_NAME_HFS_KIDNEY_TOMO = "TomoTBI_Kidney_HFS"
BEAMSET_TEMPLATE_FFS_TOMO = "Tomo_TBI_FFS_FW50"
BEAMSET_TEMPLATE_HFS_TOMO = "Tomo_TBI_HFS_FW50"
TOMO_MACHINE = "HDA0488"
PROTOCOL_FILE_VMAT = "UW_VMAT_TBI.xml"
PROTOCOL_NAME_VMAT = "UW VMAT TBI"
BEAMSET_HFS_VMAT = "VMAT-HFS-TBI"
BEAMSET_FFS_VMAT = "VMAT-FFS-TBI"
VMAT_MACHINE = "TrueBeam"

# Order names for VMAT sub-plans
HFS_PELVIS_ORDER_NAME = 'VMAT_TBI_HFS_PELVIS_UPDATED'
HFS_PELVIS_KIDNEY_ORDER_NAME = 'VMAT_TBI_HFS_PELVIS_KIDNEY'
HFS_CHEST_ORDER_NAME = 'VMAT_TBI_HFS_CHEST_NOOBJ'
HFS_HEAD_ORDER_NAME = 'VMAT_TBI_HFS_HEAD_NOOBJ'
FFS_PELVIS_ORDER_NAME = 'VMAT_TBI_FFS_PELVIS_UPDATED'
FFS_LEGS_ORDER_NAME = 'VMAT_TBI_FFS_LEGS_NOOBJ'
FFS_FEET_ORDER_NAME = 'VMAT_TBI_FFS_FEET_NOOBJ'
ORDER_TARGET_NAME_FFS = "PTV_p_FFS"
ORDER_TARGET_NAME_HFS = "PTV_p_HFS"

# Default voxel size for dose grid (in cm)
DEFAULT_VOXEL_SIZE = {'x': 0.4, 'y': 0.4, 'z': 0.4}  # [cm]

# Plan and beamset names for Tomo and VMAT
HFS_TOMO_PLAN_NAME = "HFS__TBI_Tomo_Auto"
HFS_TOMO_BEAMSET_NAME = "HFS__TBI_Tomo"
FFS_TOMO_BEAMSET_NAME = "FFS__TBI_Tomo"
FFS_TOMO_PLAN_NAME = "FFS__TBI_Tomo_Auto"
TOMO_FFS_TRANSFER_NAME = "Tomo_FFS_Trnsfr"
FFS_PLACEHOLDER_NAME = "Empty plan"  # Default name assigned by RS upon plan import
HFS_VMAT_BEAMSET_NAME = "HFS__VMA"
HFS_VMAT_PLAN_NAME = HFS_VMAT_BEAMSET_NAME + "_Auto"
FFS_VMAT_BEAMSET_NAME = "FFS__VMA"
FFS_VMAT_PLAN_NAME = FFS_VMAT_BEAMSET_NAME + "_Auto"
VMAT_FFS_TRANSFER_NAME = "VMAT_FFS_Trnsfr"

# Geometric and dosimetric parameters for TBI planning
MIN_FFS_OVERLAP = 2  # Minimum Overlap [cm]
HFS_OVERLAP = 5  # Minimum Overlap [cm]
FW = 39  # 39 cm of MLC based field
CENTRAL_JUNCTION_WIDTH = 1.2 * 9  # [cm]
FFS_MAX_TREATMENT_LENGTH = 99  # TODO - A fudge - based junction placement on packing HFS
FFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past toes
FFS_SHIFT_BUFFER = 2  # [cm]
FFS_TREATMENT_LENGTH = (FFS_MAX_TREATMENT_LENGTH
                        - FFS_OVERSHOOT
                        - FFS_SHIFT_BUFFER
                        - CENTRAL_JUNCTION_WIDTH)
FFS_ISO_NUMBER = math.ceil(FFS_MAX_TREATMENT_LENGTH / (FW - MIN_FFS_OVERLAP))
HFS_MAX_TREATMENT_LENGTH = 114.5  # [cm]
HFS_SHIFT_BUFFER = 2  # [cm]
HFS_OVERSHOOT = 3  # cm - Distance of overshoot of beam past top of head
HFS_TREATMENT_LENGTH = (HFS_MAX_TREATMENT_LENGTH
                        + HFS_OVERSHOOT
                        + HFS_SHIFT_BUFFER
                        + CENTRAL_JUNCTION_WIDTH)

# POI and ROI naming conventions
JUNCTION_POINT = "junction"
HFS_POI = 'HFS_POI'
FFS_POI = 'FFS_POI'
EXTERNAL_SETUP = 'External_PRV10'
EXTERNAL_SETUP_EXP = 1.0  # cm expansion
EXTERNAL_NAME = "ExternalClean"
AVOID_HFS_NAME = "Avoid_HFS"
AVOID_FFS_NAME = "Avoid_FFS"
SKIN_AVOIDANCE = 'Avoid_Skin_PRV05'
SKIN_AVOIDANCE_CONTRACT = 0.5  # cm contraction
LUNG_AVOID_NAME = "Lungs_m07"
LUNG_AVOID_MARGIN = 0.7  # cm contraction
LUNGS = "Lungs"
LUNGS_EVAL_MARGIN = 1.0  # cm contraction for margin
LUNGS_EVAL_NAME = LUNGS + "_m10"
KIDNEYS = "Kidneys"
KIDNEY_AVOID_NAME = KIDNEYS + "_m05"
KIDNEY_AVOID_MARGIN = 0.5  # cm contraction
TARGET_FFS = "PTV_p_FFS"
TARGET_HFS = "PTV_p_HFS"
EVAL_SUFFIX = "_Eval"
JUNCTION_PREFIX_FFS = "ffs_junction_"
JUNCTION_PREFIX_HFS = "hfs_junction_"
HFS_TARGET_EVAL_NAME = TARGET_HFS + EVAL_SUFFIX
FFS_TARGET_EVAL_NAME = TARGET_FFS + EVAL_SUFFIX
HFS_TARGET_NAMES = [TARGET_HFS, HFS_TARGET_EVAL_NAME]
FFS_TARGET_NAMES = [TARGET_FFS, FFS_TARGET_EVAL_NAME]

# Model-based segmentation (MBS) ROI definitions
MBS_ROIS = {'Kidney_L': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Left)",
                         'RoiName': r"Kidney_L",
                         'RoiColor': "58, 251, 170"},
            'Kidney_R': {'CaseType': "Abdomen",
                         'ModelName': r"Kidney (Right)",
                         'RoiName': r"Kidney_R",
                         'RoiColor': "250, 57, 105"},
            'Lung_L': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Left)",
                       'RoiName': r"Lung_L",
                       'RoiColor': "253, 122, 9"},
            'Lung_R': {'CaseType': "Thorax",
                       'ModelName': r"Lung (Right)",
                       'RoiName': r"Lung_R",
                       'RoiColor': "54, 247, 223"}}

# Color palette for ROI display (RGB triplets)
COLORS = [[127, 0, 255],
          [0, 0, 255],
          [0, 127, 255],
          [0, 255, 255],
          [0, 255, 127],
          [0, 255, 0],
          [127, 255, 0],
          [255, 255, 0],
          [255, 127, 0],
          [255, 0, 0],
          [255, 0, 255]]

# =====================
# GUI Key Constants
# =====================
NFX_KEY = '-NFX-'
TOTAL_DOSE_KEY = '-TOTAL DOSE-'
VMAT_KEY = '-VMAT-'
TOMO_KEY = '-TOMO-'
KIDNEY_KEY = '-KIDNEY-'
NO_KIDNEY_KEY = '-NO KIDNEY-'
PAUSE_KEY = '-PAUSE-'
# Add more GUI keys as needed
