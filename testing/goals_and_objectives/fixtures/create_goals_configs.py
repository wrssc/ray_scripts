from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CreateGoalsConfig:
    """
    Headless inputs for Objectives.add_goals_and_objectives_from_protocol.

    Notes:
    - filename is required for bypassing dialogs.
    - target_map format matches Objectives: {xml_target: [plan_roi_name, dose_Gy]}
    """
    path_protocols: str
    filename: str
    protocol_name: Optional[str] = None
    order_name: Optional[str] = None
    target_map: Optional[Dict[str, List[Any]]] = None  # [roi_name: str, dose_Gy: float]
    run_status: bool = False  # must be False for no status dialog


def base_config(*, path_protocols: str) -> CreateGoalsConfig:
    # Choose something sane as a default; override in named_variants/grid_sweep.
    return CreateGoalsConfig(
        path_protocols=path_protocols,
        filename="UWBrainCNS.xml",
        protocol_name="UW Brain/CNS",
        order_name=None,
        target_map=None,
        run_status=False,
    )


def named_variants(base: CreateGoalsConfig) -> List[Tuple[str, CreateGoalsConfig]]:
    """
    "Named variants" axis: different protocol files from protocols/UW directory.
    Each variant uses a different UW protocol file with appropriate settings.
    """
    return [
        ("uw_brain_cns", replace(base, filename="UWBrainCNS.xml", protocol_name="UW Brain/CNS")),
        ("uw_brain_sabr", replace(base, filename="UWBrainCNS_SABR.xml", protocol_name="UW Brain/CNS SABR")),
        ("uw_brain_srs", replace(base, filename="UWBrainCNS_SRS.xml", protocol_name="UW Brain/CNS SRS")),
        ("uw_breast", replace(base, filename="UWBreast.xml", protocol_name="UW Breast")),
        ("uw_breast_sbrt", replace(base, filename="UWBreastSBRT.xml", protocol_name="UW Breast SBRT")),
        ("uw_lung", replace(base, filename="UWLung.xml", protocol_name="UW Lung")),
        ("uw_lung_sbrt", replace(base, filename="UWLungSBRT.xml", protocol_name="UW Lung SBRT")),
        ("uw_prostate", replace(base, filename="UWProstate.xml", protocol_name="UW Prostate")),
        ("uw_prostate_sbrt", replace(base, filename="UWProstateSBRT.xml", protocol_name="UW Prostate SBRT")),
        ("uw_head_neck", replace(base, filename="UWHeadNeck.xml", protocol_name="UW Head & Neck")),
        ("uw_pelvis", replace(base, filename="UWPelvis.xml", protocol_name="UW Pelvis")),
        ("uw_abdomen", replace(base, filename="UWAbdomen.xml", protocol_name="UW Abdomen")),
        ("uw_abdomen_sbrt", replace(base, filename="UWAbdomen_SBRT.xml", protocol_name="UW Abdomen SBRT")),
        ("uw_spine_sbrt", replace(base, filename="UWSpineSBRT.xml", protocol_name="UW Spine SBRT")),
        ("uw_esophagus", replace(base, filename="UWEsophagus.xml", protocol_name="UW Esophagus")),
        ("uw_anorectal", replace(base, filename="UWAnorectal.xml", protocol_name="UW Anorectal")),
        ("uw_generic", replace(base, filename="UWGeneric.xml", protocol_name="UW Generic")),
    ]


def grid_sweep(base: CreateGoalsConfig) -> List[Tuple[str, CreateGoalsConfig]]:
    """
    "Grid sweep" axis for create_goals: systematic sweep over different UW protocol files
    with various order names and target map configurations.
    """
    return [
        ("brain_cns_standard", replace(base, filename="UWBrainCNS.xml", protocol_name="UW Brain/CNS")),
        ("brain_cns_with_order", replace(base, filename="UWBrainCNS.xml", protocol_name="UW Brain/CNS", order_name="Brain Standard")),
        ("breast_standard", replace(base, filename="UWBreast.xml", protocol_name="UW Breast")),
        ("breast_with_target_map", replace(
            base, 
            filename="UWBreast.xml", 
            protocol_name="UW Breast",
            target_map={
                "PTV": ["PTV_5040", 50.4],
                "CTV": ["CTV_5040", 50.4],
            }
        )),
        ("lung_standard", replace(base, filename="UWLung.xml", protocol_name="UW Lung")),
        ("lung_sbrt", replace(base, filename="UWLungSBRT.xml", protocol_name="UW Lung SBRT")),
        ("prostate_standard", replace(base, filename="UWProstate.xml", protocol_name="UW Prostate")),
        ("prostate_with_target_map", replace(
            base,
            filename="UWProstate.xml",
            protocol_name="UW Prostate",
            target_map={
                "PTV": ["PTV_7800", 78.0],
                "CTV": ["CTV_7800", 78.0],
            }
        )),
        ("generic_protocol", replace(base, filename="UWGeneric.xml", protocol_name="UW Generic")),
    ]
