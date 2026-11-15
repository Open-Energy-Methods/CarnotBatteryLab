"""Experimental thermal/hydraulic comparisons with strict evidence gates.

Measured data are NEVER fabricated from model outputs. A numerical closeness
score alone does not yield an experimental validation PASS; matching geometry,
source boundary, sensor coordinates, uncertainties and withheld runs are
separate *mandatory* gates.

Default status: BLOCKED until independently provided experimental metadata.
"""
from __future__ import annotations
from dataclasses import dataclass
import bisect
import csv
import hashlib
import math
from pathlib import Path
from statistics import mean


class BenchmarkBlocked(ValueError):
    """Benchmark metadata, data or physical regime is incomplete."""


@dataclass(frozen=True)
class TimeSeries:
    elapsed_s: tuple[float,...]
    measured_C: tuple[float,...]
    source_sha256: str
    run_id: str
    sensor_id: str

    def __post_init__(self):
        if len(self.elapsed_s)!=len(self.measured_C) or len(self.elapsed_s)<3:
            raise BenchmarkBlocked("time and temperature series require >=3 matched measurements")
        if any(not math.isfinite(x) for x in (*self.elapsed_s,*self.measured_C)):
            raise BenchmarkBlocked("nonfinite raw time or temperature")
        if any(a>=b for a,b in zip(self.elapsed_s,self.elapsed_s[1:])):
            raise BenchmarkBlocked("time samples must strictly increase; never sort an unknown timestamp set")
        if not self.source_sha256 or not self.run_id or not self.sensor_id:
            raise BenchmarkBlocked("provenance, run and sensor IDs required")


def read_measured_csv(
    file: Path, *, header_row: int, time_column: str, sensor_column: str,
    time_unit: str, run_id: str, sensor_id: str, delimiter: str = ",",
) -> TimeSeries:
    """Parse *explicitly mapped* CSV columns. Never guess sensor geometry/units."""
    if time_unit not in ("seconds","minutes","hours"):
        raise BenchmarkBlocked("measurement time unit must be explicitly declared")
    if header_row<0 or not time_column or not sensor_column:
        raise BenchmarkBlocked("verified CSV schema mapping required")
    raw=file.read_bytes()
    if len(raw)>10_000_000 or not raw:
        raise BenchmarkBlocked("unsupported raw CSV size/empty file")
    try:
        text=raw.decode("utf-8-sig")
        rows=list(csv.reader(text.splitlines(),delimiter=delimiter))
    except (UnicodeError,csv.Error) as exc:
        raise BenchmarkBlocked("CSV cannot be parsed without an explicit compatible encoding") from exc
    if header_row>=len(rows):
        raise BenchmarkBlocked("header row not found")
    headers=rows[header_row]
    if headers.count(time_column)!=1 or headers.count(sensor_column)!=1:
        raise BenchmarkBlocked("CSV columns absent or ambiguous")
    ti=headers.index(time_column)
    si=headers.index(sensor_column)
    factor={"seconds":1.0,"minutes":60.0,"hours":3600.0}[time_unit]
    time=[]
    values=[]
    for n,row in enumerate(rows[header_row+1:],start=header_row+2):
        if not any(x.strip() for x in row):
            continue
        if max(ti,si)>=len(row):
            raise BenchmarkBlocked(f"missing sensor or time value at CSV line {n}")
        try:
            t=float(row[ti])*factor
            y=float(row[si])
        except ValueError as exc:
            raise BenchmarkBlocked(f"non-numeric measured value at CSV line {n}") from exc
        time.append(t)
        values.append(y)
    return TimeSeries(tuple(time),tuple(values),
        hashlib.sha256(raw).hexdigest(),run_id,sensor_id)


@dataclass(frozen=True)
class ExperimentalMapping:
    dataset_doi: str
    run_id: str
    sensor_id: str
    sensor_axial_position_m: float | None
    bed_geometry_source_ref: str | None
    mass_flow_source_ref: str | None
    measured_inlet_temperature_source_ref: str | None
    sensor_uncertainty_C: float | None
    held_out_from_calibration: bool
    is_same_flow_topology: bool

    def missing(self) -> tuple[str,...]:
        absent=[]
        for key in ("dataset_doi","run_id","sensor_id",
                    "bed_geometry_source_ref","mass_flow_source_ref",
                    "measured_inlet_temperature_source_ref"):
            if not getattr(self,key):
                absent.append(key)
        if self.sensor_axial_position_m is None or self.sensor_axial_position_m<0:
            absent.append("verified_sensor_axial_position_m")
        if self.sensor_uncertainty_C is None or self.sensor_uncertainty_C<=0:
            absent.append("sensor_uncertainty_C")
        if not self.held_out_from_calibration:
            absent.append("whole_run_not_used_in_calibration")
        if not self.is_same_flow_topology:
            absent.append("matching_axial_flow_topology")
        return tuple(absent)


@dataclass(frozen=True)
class Comparison:
    points: int
    rmse_C: float
    mae_C: float
    mean_bias_C: float
    maximum_absolute_error_C: float
    measured_run_id: str
    measured_sensor_id: str
    measured_file_sha256: str
    status: str
    blocked_reasons: tuple[str,...]


def compare_timeseries(
    measurements:TimeSeries,
    predicted_time_s:tuple[float,...],
    predicted_C:tuple[float,...],
    mapping:ExperimentalMapping,
    *,
    minimum_points:int=10,
) -> Comparison:
    if len(predicted_time_s)!=len(predicted_C) or len(predicted_time_s)<2:
        raise BenchmarkBlocked("predicted time series insufficient")
    if any(not math.isfinite(x) for x in (*predicted_time_s,*predicted_C)):
        raise BenchmarkBlocked("invalid prediction values")
    if any(a>=b for a,b in zip(predicted_time_s,predicted_time_s[1:])):
        raise BenchmarkBlocked("predicted times must be strictly increasing")
    if mapping.run_id!=measurements.run_id or mapping.sensor_id!=measurements.sensor_id:
        raise BenchmarkBlocked("cannot compare different run/sensor identity")
    # Linear time interpolation; do not extrapolate before/after prediction.
    errors=[]
    for t,ym in zip(measurements.elapsed_s,measurements.measured_C):
        if t<predicted_time_s[0] or t>predicted_time_s[-1]:
            continue
        i=bisect.bisect_right(predicted_time_s,t)-1
        if i==len(predicted_time_s)-1:
            yp=predicted_C[-1]
        else:
            frac=(t-predicted_time_s[i])/(predicted_time_s[i+1]-predicted_time_s[i])
            yp=predicted_C[i]+frac*(predicted_C[i+1]-predicted_C[i])
        errors.append(yp-ym)
    if len(errors)<minimum_points:
        raise BenchmarkBlocked("insufficient time-matched overlap for fair comparison")
    blocked=mapping.missing()
    # Even when all gates exist, require pre-registered acceptance against
    # sensor uncertainty; this function reports only comparison diagnostics.
    return Comparison(
        len(errors),math.sqrt(mean(e*e for e in errors)),
        mean(abs(e) for e in errors),mean(errors),max(abs(e) for e in errors),
        measurements.run_id,measurements.sensor_id,measurements.source_sha256,
        "BLOCKED_METADATA" if blocked else "COMPARED_NOT_VALIDATED",
        blocked,
    )


@dataclass(frozen=True)
class PressureDatum:
    mass_flow_kg_s: float
    measured_delta_p_Pa: float
    uncertainty_Pa: float
    temperature_C: float
    experiment_ref: str

    def __post_init__(self):
        if (not all(math.isfinite(v) for v in (self.mass_flow_kg_s,
              self.measured_delta_p_Pa,self.uncertainty_Pa,self.temperature_C))
            or self.mass_flow_kg_s<=0 or self.measured_delta_p_Pa<0
            or self.uncertainty_Pa<=0 or not self.experiment_ref):
            raise BenchmarkBlocked("measured pressure datum must have real uncertainty and experiment reference")


def compare_ergun_to_experiment(
    measurements:tuple[PressureDatum,...], *,
    diameter_m:float|None, length_m:float|None,
    particle_diameter_m:float|None, porosity:float|None,
    gas_density_kg_m3:float|None, gas_viscosity_Pa_s:float|None,
    pressure_taps_match_bed_only:bool,
    axial_flow:bool,
) -> dict:
    """Only compare Ergun where pressure taps measure an AXIAL bed, not radial duct loss."""
    if not axial_flow or not pressure_taps_match_bed_only:
        raise BenchmarkBlocked("axial Ergun model cannot validate a radial or duct-inclusive pressure trace")
    if not measurements:
        raise BenchmarkBlocked("no measured differential pressure")
    physical=(diameter_m,length_m,particle_diameter_m,porosity,gas_density_kg_m3,gas_viscosity_Pa_s)
    if any(x is None for x in physical):
        raise BenchmarkBlocked("bed geometry, flow properties and pressure tap positions unverified")
    from carnot_battery_lab.physics.packed_bed import PackedBedGeometry, ergun_pressure_drop_Pa
    assert all(x is not None for x in physical)
    bed=PackedBedGeometry(length_m,diameter_m,particle_diameter_m,porosity)
    errors=[]
    for d in measurements:
        u=d.mass_flow_kg_s/(gas_density_kg_m3*bed.cross_section_m2)
        pressure=ergun_pressure_drop_Pa(bed,u,gas_density_kg_m3,gas_viscosity_Pa_s)
        errors.append((pressure-d.measured_delta_p_Pa)/d.uncertainty_Pa)
    return {
        "status":"COMPARED_NOT_VALIDATED",
        "points":len(errors),
        "max_absolute_normalised_residual":max(abs(x) for x in errors),
        "rmse_in_units_of_measurement_uncertainty":math.sqrt(mean(x*x for x in errors)),
        "warning":"No fitted Ergun porosity or diameter; a geometry/pressure-tap source and independent holdout are still required",
    }
