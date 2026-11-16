"""One-way interval diagnostic for sheathed Type-K thermocouples.

Source: Wolde et al., 2022, Revista Brasileira de Energia Solar 13(2),
pp. 165-173, Methods 2.1, page 166, DOI 10.59627/rbens.2022v13i2.395:
7 Type-K sheaths contact BOTH rock particles and surrounding gas;
50 mm axial spacing. Their absolute first-sensor offset and instrument
time constant are NOT independently verified in the 2024 data.

This produces a very permissive instantaneous, phase-and-position
*model extrema envelope* across every physically possible common offset
x0 in [0, L-(N-1)*spacing]. It is NOT a calibrated measurement-uncertainty
interval or a sensor-response/phase model. It deliberately does NOT infer
the gas/rock mixing coefficient or choose an offset to fit observations.
Observed values outside the envelope are only flagged for investigation,
not a physical-model validation failure (sensor lag, location mismatch).

This code does NOT use observations to set physics parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


class UnqualifiedSensorEvidence(ValueError):
    pass


@dataclass(frozen=True)
class SensorLayoutEvidence:
    bed_length_m:float=0.400
    number_of_sensors:int=7
    published_spacing_m:float=0.050
    exact_initial_offset_m:float|None=None
    sheath_contacts_gas_and_solid:bool=True
    instrument_time_constant_s:float|None=None
    source_ref:str="Wolde et al. 2022, Methods 2.1, p.166"

    def __post_init__(self):
        if (not math.isfinite(self.bed_length_m) or self.bed_length_m<=0 or
            not math.isfinite(self.published_spacing_m) or self.published_spacing_m<=0 or
            not isinstance(self.number_of_sensors,int) or
            isinstance(self.number_of_sensors,bool) or self.number_of_sensors<2):
            raise UnqualifiedSensorEvidence("invalid sensor-spacing geometry")
        if (self.number_of_sensors-1)*self.published_spacing_m>self.bed_length_m+1e-10:
            raise UnqualifiedSensorEvidence("sensors do not fit in the stated bed")
        if self.exact_initial_offset_m is not None and (
            not math.isfinite(self.exact_initial_offset_m) or
            not 0<=self.exact_initial_offset_m<=self.maximum_initial_offset_m):
            raise UnqualifiedSensorEvidence("invalid independently specified first-sensor offset")
        if not self.sheath_contacts_gas_and_solid:
            raise UnqualifiedSensorEvidence("source states sheaths contact both phases")
        if self.instrument_time_constant_s is not None and (
            not math.isfinite(self.instrument_time_constant_s) or
            self.instrument_time_constant_s<=0):
            raise UnqualifiedSensorEvidence("invalid sensor time constant")

    @property
    def maximum_initial_offset_m(self)->float:
        return self.bed_length_m-(self.number_of_sensors-1)*self.published_spacing_m

    def axial_possible_interval_m(self, sensor_index:int)->tuple[float,float]:
        if not isinstance(sensor_index,int) or isinstance(sensor_index,bool) or not (
                0<=sensor_index<self.number_of_sensors):
            raise UnqualifiedSensorEvidence("sensor_index is 0-based and must be within reported 7 probes")
        base=sensor_index*self.published_spacing_m
        return (
            base+(self.exact_initial_offset_m if self.exact_initial_offset_m is not None else 0.),
            base+(self.exact_initial_offset_m if self.exact_initial_offset_m is not None
                  else self.maximum_initial_offset_m),
        )


@dataclass(frozen=True)
class PhasePositionEnvelope:
    sensor_label:str
    axial_possible_m:tuple[float,float]
    lower_model_temperature_C:float
    upper_model_temperature_C:float
    sampled_cell_indices:tuple[int,...]
    status:str="UNQUALIFIED_INSTANTANEOUS_PHASE_POSITION_EXTREMA"


def sensor_phase_position_envelope(
    gas_C:Sequence[float],solid_C:Sequence[float],
    sensor_index:int,layout:SensorLayoutEvidence=SensorLayoutEvidence()
)->PhasePositionEnvelope:
    if len(gas_C)!=len(solid_C) or len(gas_C)<2:
        raise ValueError("gas/rock temperatures must share >=2 finite-volume cells")
    if not all(math.isfinite(t) for t in (*gas_C,*solid_C)):
        raise ValueError("nonfinite model thermal state")
    lo,hi=layout.axial_possible_interval_m(sensor_index)
    dz=layout.bed_length_m/len(gas_C)
    # Finite volume model states are cell averages. The allowed probe
    # segment intersects every cell in the interval. Including cells at
    # exact boundary intersections is deliberately conservative.
    i0=max(0,min(len(gas_C)-1,int(math.floor(lo/dz))))
    i1=max(i0,min(len(gas_C)-1,int(math.floor(hi/dz))))
    touched=tuple(range(i0,i1+1))
    values=[gas_C[i] for i in touched]+[solid_C[i] for i in touched]
    return PhasePositionEnvelope(
        sensor_label=f"T{sensor_index+1}",
        axial_possible_m=(lo,hi),
        lower_model_temperature_C=min(values),
        upper_model_temperature_C=max(values),
        sampled_cell_indices=touched,
    )


def envelope_exceedance_C(measured_C:float,envelope:PhasePositionEnvelope)->float:
    """Nonnegative outside-band distance, NOT observation uncertainty."""
    if not math.isfinite(measured_C):
        raise ValueError("measured thermocouple value must be finite")
    return max(envelope.lower_model_temperature_C-measured_C,
               measured_C-envelope.upper_model_temperature_C,0.)


def diagnostic_summary(samples:Sequence[tuple[float,PhasePositionEnvelope]])->dict:
    """Expose raw out-of-extrema diagnostics; never return a validation PASS."""
    if not samples:
        raise ValueError("at least one source measurement and predicted envelope required")
    if any(x.sensor_label!=samples[0][1].sensor_label for _,x in samples):
        raise ValueError("cannot aggregate different thermocouples")
    exceeds=[envelope_exceedance_C(y,e) for y,e in samples]
    return {
        "sensor":samples[0][1].sensor_label,
        "comparisons":len(exceeds),
        "outside_model_extrema_count":sum(x>0 for x in exceeds),
        "outside_model_extrema_fraction":sum(x>0 for x in exceeds)/len(exceeds),
        "mean_outside_distance_C":sum(exceeds)/len(exceeds),
        "maximum_outside_distance_C":max(exceeds),
        "not_a_measurement_uncertainty_interval":True,
        "measurement_phase": "UNKNOWN_MIXED_ROCK_GAS_SHEATH",
        "sensor_time_constant":"UNKNOWN",
        "scientific_status":"ONE_WAY_EXPLORATORY_DIAGNOSTIC_NOT_MODEL_VALIDATION",
    }
