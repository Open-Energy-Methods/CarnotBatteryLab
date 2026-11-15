"""Published R718 compressor-point evidence and explicit non-transferability.

The 2018 points are NOMINAL DESIGNS, NOT measured compressor maps.
The 2020 maxima are observed on a DIFFERENT two-stage test rig.
This module compares the present screening hardware requirements against
those evidence points, without fitting or inventing a speed/surge map.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .r718 import R718Result, _prop


@dataclass(frozen=True)
class PublishedImpeller:
    label: str
    p_in_Pa: float
    t_in_K: float
    mass_flow_kg_s: float
    volume_flow_m3_h: float
    pressure_ratio: float
    eta_is: float
    source: str

    def property_check(self, backend: str = "HEOS::Water") -> dict[str, float]:
        """Compare independently reported *nominal* volume and mass flows to EOS density."""
        rho = _prop("D", "P", self.p_in_Pa, "T", self.t_in_K, backend)
        expected_vdot = self.mass_flow_kg_s / rho * 3600.0
        return {
            "eos_density_kg_m3": rho,
            "reported_volume_flow_m3_h": self.volume_flow_m3_h,
            "eos_volume_flow_m3_h": expected_vdot,
            "relative_volume_flow_difference": (
                expected_vdot / self.volume_flow_m3_h - 1.0
            ),
        }


DESIGN_2018 = (
    PublishedImpeller(
        "Zuehlsdorf2018_stage1_design", 100000.0, 110.0 + 273.15,
        0.196, 1231.0, 3.2, 0.74,
        "doi:10.18462/iir.gl.2018.1367 Table 1; expected, not tested at these states",
    ),
    PublishedImpeller(
        "Zuehlsdorf2018_stage2_design", 320000.0, 145.0 + 273.15,
        0.222, 468.0, 2.0, 0.74,
        "doi:10.18462/iir.gl.2018.1367 Table 1; expected, not tested at these states",
    ),
)

# SINTEF 2020: separate rig, observed maximum stage ratios and peak
# efficiencies from DOI 10.18462/iir.gl.2020.1019 (abstract).
# Peak eta and maximum ratio are not necessarily simultaneous conditions.
MEASURED_2020_MAX_STAGE_RATIOS = (2.4, 2.0)
MEASURED_2020_PEAK_STAGE_ETA_IS = (0.67, 0.77)


def compare_required_stage_ratios(
    result: R718Result, *, reference: str = "design_2018"
) -> dict[str, object]:
    """Conservative *hardware comparison*, not a general physical infeasibility proof."""
    if len(result.stage_pressure_ratios) != 2:
        raise ValueError("two-stage R718 result required")
    if reference == "design_2018":
        caps = tuple(x.pressure_ratio for x in DESIGN_2018)
        kind = "nominal_design_points"
    elif reference == "measured_2020":
        caps = MEASURED_2020_MAX_STAGE_RATIOS
        kind = "reported_stage_maxima_not_simultaneous_map"
    else:
        raise ValueError("unknown published hardware reference")
    actual = tuple(float(x) for x in result.stage_pressure_ratios)
    return {
        "reference": reference,
        "reference_type": kind,
        "requested_stage_ratios": actual,
        "reference_stage_ratios": caps,
        "stage_ratio_exceeded": tuple(a > b + 1e-10 for a, b in zip(actual, caps)),
        "product_ratio_required": math.prod(actual),
        "product_ratio_reference": math.prod(caps),
        "fits_reference_ratio_caps": all(a <= b for a, b in zip(actual, caps)),
        "disclaimer": (
            "Comparative check only: actual inlet pressure, gas flow, temperature, "
            "shaft speed, choke and surge domain differ. No complete measured "
            "compressor map was available, and no universal R718 infeasibility "
            "conclusion follows from exceeding these individual references."
        ),
    }
