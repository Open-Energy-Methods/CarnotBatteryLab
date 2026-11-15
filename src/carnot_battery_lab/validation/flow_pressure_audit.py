"""Source-constrained horizontal-bed flow/pressure calibration audit.

Wolde et al. 2022 (doi:10.59627/rbens.2022v13i2.395), Eq. (1):
mdot = rho(T_out) * A_exhaust * v_exhaust.
The pipe INTERNAL diameter is not documented with the 2024 dataset and
its DP channel does not specify electrical-to-Pa scaling or baseline.
All diameter/pressure-temperature ranges in this file are explicitly
SENSITIVITY SCENARIOS, not confidence intervals or calibrated instruments.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from math import pi,sqrt,isfinite
from statistics import median
from typing import Sequence

R_AIR=287.05


class EvidenceMissing(ValueError):
    """Physical measurement cannot be resolved from the supplied evidence."""


@dataclass(frozen=True)
class ExhaustScenario:
    # These are deliberately NOT certified pipe specifications.
    pipe_inner_diameter_m:float
    static_pressure_Pa:float=101325.
    exhaust_temperature_C:float=100.
    measured_velocity_m_s:float=5.

    def __post_init__(self):
        values=(self.pipe_inner_diameter_m,self.static_pressure_Pa,
                self.exhaust_temperature_C,self.measured_velocity_m_s)
        if not all(isfinite(v) for v in values):
            raise ValueError("all flow inputs must be finite")
        if (self.pipe_inner_diameter_m<=0 or self.static_pressure_Pa<=0
            or self.exhaust_temperature_C<=-273.15 or self.measured_velocity_m_s<0):
            raise ValueError("invalid positive density/area/velocity")

    @property
    def exhaust_density_kg_m3(self)->float:
        return self.static_pressure_Pa/(R_AIR*(self.exhaust_temperature_C+273.15))

    @property
    def mass_flow_kg_s(self)->float:
        return (self.exhaust_density_kg_m3*
                pi*self.pipe_inner_diameter_m**2/4*self.measured_velocity_m_s)


def sensitivity_scenarios(*, Tout_C:float, velocity_m_s:float,
                          diameters_m:tuple[float,...]=(.045,.052,.060)) ->dict:
    """Pipe diameter/pressure uncertainty is NOT a calibrated m_dot."""
    if len(diameters_m)<2 or tuple(sorted(set(diameters_m)))!=diameters_m:
        raise ValueError("provide >=2 increasing distinct diameter scenarios")
    rows=[]
    for d in diameters_m:
        s=ExhaustScenario(d,exhaust_temperature_C=Tout_C,
                          measured_velocity_m_s=velocity_m_s)
        rows.append({**asdict(s),"mass_flow_kg_s":s.mass_flow_kg_s,
                     "density_kg_m3":s.exhaust_density_kg_m3})
    flow_ratio=rows[-1]["mass_flow_kg_s"]/rows[0]["mass_flow_kg_s"] if velocity_m_s>0 else None
    return {
        "source_equation":"Wolde et al 2022 Eq1, measured exhaust Tout and velocity",
        "diameters_are_assumptions_NOT_measurement":True,
        "diameter_scenarios":rows,
        "relative_mdot_D_sensitivity":"d ln(m_dot)/d ln(D) = 2",
        "max_over_min_mdot":flow_ratio,
        "measurement_dependency":"T_out is a modelling target and also used to infer inlet mass flow",
        "validation_status":"NOT_INDEPENDENT",
    }


@dataclass(frozen=True)
class PressureCalibration:
    channel_name:str
    pressure_unit_to_Pa:float|None=None
    offset_in_native_units:float|None=None
    calibration_source_reference:str|None=None
    taps_span_only_bed:bool|None=None
    pipe_minor_loss_correction_Pa:float|None=None
    pressure_uncertainty_Pa:float|None=None

    def missing(self)->tuple[str,...]:
        misses=[]
        if (self.pressure_unit_to_Pa is None or
            not isfinite(self.pressure_unit_to_Pa) or self.pressure_unit_to_Pa<=0):
            misses.append("verified_unit_conversion_to_Pa")
        if (self.offset_in_native_units is None or
            not isfinite(self.offset_in_native_units)):
            misses.append("verified_zero_offset")
        if not self.calibration_source_reference:
            misses.append("transducer_calibration_source")
        if self.taps_span_only_bed is None:
            misses.append("verified_pressure_tap_boundaries")
        if (self.taps_span_only_bed is False and
            self.pipe_minor_loss_correction_Pa is None):
            misses.append("independently_measured_pipe_fitting_loss")
        if (self.pressure_uncertainty_Pa is None or
            not isfinite(self.pressure_uncertainty_Pa) or
            self.pressure_uncertainty_Pa<=0):
            misses.append("pressure_uncertainty_Pa")
        return tuple(misses)


def convert_pressure_channel(native:Sequence[float],
                             calibration:PressureCalibration
                            )->tuple[float,...]:
    """Fail CLOSED: never infer kPa from channel magnitudes alone."""
    missing=calibration.missing()
    if missing:
        raise EvidenceMissing("pressure unit/calibration incomplete: "+", ".join(missing))
    if not all(isfinite(x) for x in native):
        raise EvidenceMissing("raw channel contains non-finite readings")
    assert calibration.pressure_unit_to_Pa is not None
    assert calibration.offset_in_native_units is not None
    # Tap boundary includes pipe losses if not bed-only; require correction.
    correction=(calibration.pipe_minor_loss_correction_Pa or 0.)
    pressures=tuple((v-calibration.offset_in_native_units)*
                     calibration.pressure_unit_to_Pa-correction for v in native)
    return pressures


def native_pressure_diagnostics(
    native_pressure:Sequence[float],velocity_m_s:Sequence[float]
)->dict:
    if len(native_pressure)!=len(velocity_m_s) or len(native_pressure)<4:
        raise ValueError("measurement arrays not aligned")
    if any(not isfinite(v) for v in (*native_pressure,*velocity_m_s)):
        raise ValueError("nonfinite measured channel")
    if any(v<0 for v in velocity_m_s):
        raise ValueError("negative measured exhaust velocity requires flow-direction record")
    positives=[p for p in native_pressure if p>0]
    return {
        "reading_count":len(native_pressure),
        "pressure_channel_unit":"UNKNOWN",
        "pressure_channel_min_native":min(native_pressure),
        "pressure_channel_median_native":median(native_pressure),
        "pressure_channel_max_native":max(native_pressure),
        "nonpositive_pressure_readings":len(native_pressure)-len(positives),
        "velocity_median_m_s":median(velocity_m_s),
        "cannot_compare_with_Ergun_Pa":True,
        "reason":"no verified transducer scale/offset and bed-only tap correction",
    }
