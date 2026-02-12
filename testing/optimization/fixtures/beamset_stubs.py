from __future__ import annotations
from dataclasses import dataclass


@dataclass
class BeamSetStub:
    DeliveryTechnique: str
    DicomPlanLabel: str = "TEST"


def make_vmat_beamset(label: str = "VMAT_TEST") -> BeamSetStub:
    # Anything that does NOT contain "Tomo" will be treated as VMAT by your runner.
    return BeamSetStub(DeliveryTechnique="VMAT", DicomPlanLabel=label)


def make_tomo_beamset(label: str = "TOMO_TEST") -> BeamSetStub:
    # Your normalization checks: "Tomo" in DeliveryTechnique
    return BeamSetStub(DeliveryTechnique="TomoHelical", DicomPlanLabel=label)
