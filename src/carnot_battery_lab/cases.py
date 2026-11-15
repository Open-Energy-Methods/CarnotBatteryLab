"""Validated, explicit industrial heat and power-to-power study contracts.

The fields represent boundary conditions, NOT a solved or validated plant. A
valid configuration is necessary but not sufficient for thermodynamic feasibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

import yaml


class CaseValidationError(ValueError):
    """An input violates a declared scientific study contract."""


@dataclass(frozen=True)
class StudyCase:
    case_id: str
    service: str
    load_MW_th: float | None
    source_inlet_C: float
    process_supply_C: float | None
    process_return_C: float | None
    ambient_C: float
    useful_storage_duration_h: float
    temporal_resolution_min: int
    configuration_status: str
    reference_only: bool
    notes: str

    def __post_init__(self) -> None:
        for k in ("source_inlet_C", "process_supply_C", "process_return_C", "ambient_C", "useful_storage_duration_h", "load_MW_th"):
            v = getattr(self, k)
            if v is not None and not math.isfinite(v):
                raise CaseValidationError(f"{k} must be finite")
        if self.service not in ("process_heat", "electricity_to_electricity"):
            raise CaseValidationError("service must be process_heat or electricity_to_electricity")
        if self.configuration_status not in ("illustrative", "feasibility_checked", "validated"):
            raise CaseValidationError("unsupported configuration_status")
        if self.reference_only is not True:
            raise CaseValidationError("example cases must explicitly be reference_only: true")
        if not self.case_id.strip():
            raise CaseValidationError("case_id is required")
        if not (-273.15 < self.ambient_C < 150):
            raise CaseValidationError("ambient_C must be a credible absolute temperature")
        if not (-273.15 < self.source_inlet_C < 1000):
            raise CaseValidationError("source_inlet_C outside admissible input bounds")
        if self.useful_storage_duration_h <= 0 or self.useful_storage_duration_h > 10000:
            raise CaseValidationError("useful_storage_duration_h must be positive and bounded")
        if self.temporal_resolution_min <= 0 or 1440 % self.temporal_resolution_min:
            raise CaseValidationError("temporal_resolution_min must divide 1440")
        if self.service == "process_heat":
            if self.load_MW_th is None or self.load_MW_th <= 0:
                raise CaseValidationError("process heat requires positive load_MW_th")
            if self.process_supply_C is None or self.process_return_C is None:
                raise CaseValidationError("process heat requires supply and return temperatures")
            if not (self.process_return_C < self.process_supply_C):
                raise CaseValidationError("process return must be cooler than process supply")
        else:
            if self.load_MW_th is not None or self.process_supply_C is not None or self.process_return_C is not None:
                raise CaseValidationError("electricity-to-electricity studies require a separate power-cycle service contract")

    @property
    def nominal_useful_storage_MWh_th(self) -> float | None:
        """Process-load × duration; not the required storage *inventory*."""
        if self.load_MW_th is None:
            return None
        return self.load_MW_th * self.useful_storage_duration_h


_ALLOWED = frozenset(StudyCase.__dataclass_fields__)
_REQUIRED = frozenset({"case_id", "service", "source_inlet_C", "ambient_C", "useful_storage_duration_h", "temporal_resolution_min", "configuration_status", "reference_only", "notes"})


def parse_study_case(data: dict[str, Any]) -> StudyCase:
    if not isinstance(data, dict):
        raise CaseValidationError("case must be a YAML mapping")
    unexpected = set(data) - _ALLOWED
    missing = _REQUIRED - set(data)
    if unexpected or missing:
        raise CaseValidationError(f"unexpected keys: {sorted(unexpected)}; missing keys: {sorted(missing)}")
    for key in ("load_MW_th", "source_inlet_C", "process_supply_C", "process_return_C", "ambient_C", "useful_storage_duration_h"):
        v = data.get(key)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise CaseValidationError(f"{key} must be numeric")
    if isinstance(data.get("temporal_resolution_min"), bool) or not isinstance(data.get("temporal_resolution_min"), int):
        raise CaseValidationError("temporal_resolution_min must be an integer")
    try:
        return StudyCase(**data)
    except TypeError as exc:
        raise CaseValidationError(str(exc)) from exc


def load_study_case(path: str | Path) -> StudyCase:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return parse_study_case(data)
