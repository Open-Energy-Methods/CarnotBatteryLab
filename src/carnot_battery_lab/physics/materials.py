"""Temperature feasibility guards: not a fluid property database.

No material temperature limit is established by the value of an unrelated
engineering study. The chosen nominal operating window is a conservative
screen on one mixture, with provenance and explicit conditions.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class SaltWindow:
    material_id: str
    min_bulk_temp_C: float
    max_bulk_temp_C: float
    provenance: str

    def __post_init__(self) -> None:
        if not self.material_id or not self.provenance:
            raise ValueError("salt window requires material identification and source")
        if not all(map(math.isfinite, (self.min_bulk_temp_C,self.max_bulk_temp_C))):
            raise ValueError("salt temperatures must be finite")
        if self.min_bulk_temp_C >= self.max_bulk_temp_C:
            raise ValueError("invalid temperature window")


# THIS IS A SCREEN, NOT A PLANT SPECIFICATION: Source says the mixture melts
# around 220 C; 260 C is an illustrative conservative OPERATING floor and
# must be reviewed for freezing margin, transient wall T and impurities.
SOLAR_SALT_SCREEN = SaltWindow(
    material_id="solar-salt-60NaNO3-40KNO3",
    min_bulk_temp_C=260.0,
    max_bulk_temp_C=565.0,
    provenance="L09 Solar Two NREL 2000 + L14 Molten Salt Storage for Power Generation",
)


def check_bulk_temperature_window(cold_C: float, hot_C: float, window: SaltWindow) -> tuple[bool, str]:
    if not math.isfinite(cold_C) or not math.isfinite(hot_C):
        raise ValueError("temperature must be finite")
    if cold_C >= hot_C:
        return False, "cold bulk temperature must be below hot bulk temperature"
    if cold_C < window.min_bulk_temp_C:
        return False, f"cold bulk salt below screening limit ({window.min_bulk_temp_C} C): freeze risk"
    if hot_C > window.max_bulk_temp_C:
        return False, f"hot bulk salt exceeds declared screening ceiling ({window.max_bulk_temp_C} C)"
    return True, "Within provisional bulk temperature screen only; full thermal/mechanical checks pending"
