"""M2.1 measured packed-bed thermal breakthrough + pressure-loss evidence gate.

Prevents model-to-self comparisons and serial-sample data leakage:
- Experimental run = group unit, not time row or TC channel
- Thermocouple locations/pressure taps/flow measurement provenance are
  required *before* time-aligned model comparisons
- Entire holdout run must be excluded from calibration and geometry/thermal
  tuning. Neither in-domain prediction nor material properties are assumed.
- Experimental pressure-loss must be compared to predicted packed-bed Ergun
  *with explicit clean-bed pressure tap correction* and measured viscosity/rho;
  uncorrected external pipe/fittings loss is not bed-only ground truth.

No raw source has yet passed this admission schema. All artificial fixtures
used by unit tests are explicitly synthetic and never produce a VALIDATED claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, sqrt
from statistics import mean
from typing import Sequence
import json

from .packed_bed import PackedBedGeometry, ergun_pressure_drop_Pa

ALLOWED_EVIDENCE=("SYNTHETIC_UNIT_TEST",
                  "ORIGINAL_LAB_MEASURED_UNREVIEWED",
                  "ORIGINAL_LAB_MEASURED_REVIEWED")
MIN_INDEPENDENT_RUNS=4
MIN_TRAIN_RUNS=2
MIN_HOLDOUT_RUNS=2


def _real(v:float)->bool:
    return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v)


@dataclass(frozen=True)
class MeasuredBedRun:
    dataset_doi:str
    run_id:str
    apparatus_id:str
    evidence_class:str
    source_sha256:str
    source_field_and_unit_map_id:str
    temperature_calibration_ref:str
    pressure_calibration_ref:str
    flow_calibration_ref:str
    bed_geometry:PackedBedGeometry
    # Both inputs actually measured for this specific run.
    mass_flow_kg_s:float
    gas_density_kg_m3:float
    gas_dynamic_viscosity_Pa_s:float
    initial_temperature_K:float
    thermal_inlet_temperature_K:float
    reported_pressure_drop_tap_to_tap_Pa:float
    independently_measured_pipe_fittings_pressure_drop_Pa:float|None
    differential_pressure_sensor_standard_uncertainty_Pa:float
    # Independent original timestamps and physical installed thermocouple
    # locations, not fitted detection times or arbitrary pixel digitization.
    time_s:tuple[float,...]
    axial_sensor_positions_m:tuple[float,...]
    observed_fluid_temperature_K_by_sensor:tuple[tuple[float,...],...]
    thermal_sensor_standard_uncertainty_K:float
    stable_flow_confirmed:bool

    def __post_init__(self):
        strings=(self.dataset_doi,self.run_id,self.apparatus_id,
                 self.source_field_and_unit_map_id,self.temperature_calibration_ref,
                 self.pressure_calibration_ref,self.flow_calibration_ref)
        if not all(isinstance(x,str) and x.strip() for x in strings):
            raise ValueError("missing original apparatus, sensor unit or calibration provenance")
        if (not isinstance(self.source_sha256,str) or
            len(self.source_sha256)!=64 or
            any(ch not in "0123456789abcdef" for ch in self.source_sha256)):
            raise ValueError("exact original measurement source sha256 required")
        if self.evidence_class not in ALLOWED_EVIDENCE:
            raise ValueError("invalid original experimental evidence class")
        for k in ("mass_flow_kg_s","gas_density_kg_m3",
                  "gas_dynamic_viscosity_Pa_s","initial_temperature_K",
                  "thermal_inlet_temperature_K",
                  "differential_pressure_sensor_standard_uncertainty_Pa",
                  "thermal_sensor_standard_uncertainty_K"):
            v=getattr(self,k)
            if not _real(v) or v<=0:
                raise ValueError(f"invalid physical original field {k}")
        if (not _real(self.reported_pressure_drop_tap_to_tap_Pa) or
            self.reported_pressure_drop_tap_to_tap_Pa<0 or
            self.independently_measured_pipe_fittings_pressure_drop_Pa is not None
            and (not _real(self.independently_measured_pipe_fittings_pressure_drop_Pa)
                 or self.independently_measured_pipe_fittings_pressure_drop_Pa<0)):
            raise ValueError("invalid source pressure or independent pipe-loss field")
        if self.stable_flow_confirmed is not True:
            raise ValueError("unstable experiment is not a steady pressure-loss validation")
        if len(self.time_s)<3 or not all(_real(x) and x>=0 for x in self.time_s):
            raise ValueError("source experiment requires measured nonnegative elapsed timestamps")
        if any(b<=a for a,b in zip(self.time_s,self.time_s[1:])):
            raise ValueError("source timestamps must be strictly increasing, not merged/duplicated")
        if (not self.axial_sensor_positions_m or
            len(self.axial_sensor_positions_m)!=len(
                self.observed_fluid_temperature_K_by_sensor)):
            raise ValueError("temperature TC position/series count mismatch")
        if len(set(self.axial_sensor_positions_m))!=len(self.axial_sensor_positions_m):
            raise ValueError("two sensors have identical positions")
        for x,row in zip(self.axial_sensor_positions_m,
                         self.observed_fluid_temperature_K_by_sensor):
            if not _real(x) or not 0<=x<=self.bed_geometry.length_m:
                raise ValueError("physical sensor position outside measured bed")
            if len(row)!=len(self.time_s) or any(
                not _real(y) or y<=0 for y in row):
                raise ValueError("sensor temperature series has missing/nonphysical values")

    @property
    def group_key(self)->tuple[str,str,str]:
        return self.dataset_doi,self.apparatus_id,self.run_id

    @property
    def input_signature(self)->tuple[float,...]:
        # By construction, does not use heldout observed outlet history or dP.
        g=self.bed_geometry
        return (self.mass_flow_kg_s,self.initial_temperature_K,
                self.thermal_inlet_temperature_K,g.length_m,g.diameter_m,
                g.particle_diameter_m,g.porosity)


def fixed_run_holdout_protocol(runs:Sequence[MeasuredBedRun],*
                               reserved_run_ids:Sequence[str],
                               expected_evidence:str=
                                 "ORIGINAL_LAB_MEASURED_UNREVIEWED")->dict:
    if len(runs)<MIN_INDEPENDENT_RUNS:
        raise ValueError("too few independent experiment run groups")
    if len({x.group_key for x in runs})!=len(runs):
        raise ValueError("same run split or duplicated as independent records")
    if len({(x.dataset_doi,x.apparatus_id) for x in runs})!=1:
        raise ValueError("never pool different apparatus/dataset physics for validation")
    if any(x.evidence_class!=expected_evidence for x in runs):
        raise ValueError("wrong experiment evidence class; synthetic tests cannot qualify")
    ids={x.run_id for x in runs}
    if len(set(reserved_run_ids))!=len(reserved_run_ids) or not set(
        reserved_run_ids).issubset(ids):
        raise ValueError("duplicate, missing or unknown heldout run ID")
    held=[x for x in runs if x.run_id in reserved_run_ids]
    train=[x for x in runs if x.run_id not in reserved_run_ids]
    if len(train)<MIN_TRAIN_RUNS or len(held)<MIN_HOLDOUT_RUNS:
        raise ValueError("requires independent train and heldout entire experiments")
    if set(x.group_key for x in train)&set(x.group_key for x in held):
        raise ValueError("thermocouple/time/sample leakage between fit and holdout")
    if any(x.independently_measured_pipe_fittings_pressure_drop_Pa is None
           for x in held):
        pressure_supported=False
    else:
        pressure_supported=True
    # Multidimensional *input*-support cannot be established merely by
    # independent minima/maxima: a nonnegative barycentric hull is required.
    same_run_geometry=all(x.bed_geometry==runs[0].bed_geometry for x in runs)
    return {
        "original_source_doi":runs[0].dataset_doi,
        "original_apparatus_id":runs[0].apparatus_id,
        "training_entire_run_ids":[x.run_id for x in train],
        "reserved_entire_run_ids":[x.run_id for x in held],
        "training_run_count":len(train),
        "reserved_run_count":len(held),
        "simulated_observation_count_used_as_independent_experiment":0,
        "source_measurement_sha256s":{
            x.run_id:x.source_sha256 for x in runs},
        "source_sensor_units_and_calibration_explicit":True,
        "bed_geometry_identical_across_runs":same_run_geometry,
        "experimental_tap_to_tap_pressure_loss_independently_correctable":
            pressure_supported,
        "time_aligned_thermal_history_validation_executed":False,
        "source_temperature_and_pressure_holdout_predictions_accepted":False,
        "fully_independent_experimental_campaign":False,
        "exact_H_REF_bed_or_machine_qualified":False,
    }


def pressure_loss_no_fit_score(
    measured:MeasuredBedRun, *,
    originally_measured_pipe_loss_correction_required:bool=True)->dict:
    """No empirical Ergun coefficient fitted to this measurement."""
    if (measured.evidence_class=="SYNTHETIC_UNIT_TEST"):
        # Test fixtures may exercise formulas but never return empirical pass.
        evidence="SYNTHETIC_UNIT_TEST_NOT_EXPERIMENTAL_VALIDATION"
    else:
        evidence="ORIGINAL_MEASURED_RUN_BED_ONLY_MODEL_DIAGNOSTIC"
    correction=measured.independently_measured_pipe_fittings_pressure_drop_Pa
    if originally_measured_pipe_loss_correction_required and correction is None:
        return {"status":"BLOCKED_UNMEASURED_EXTERNAL_PIPING_LOSS",
                "source_run_id":measured.run_id,
                "model_error_Pa":None,"validation_passed":False}
    bed_measured=(
        measured.reported_pressure_drop_tap_to_tap_Pa-(correction or 0.))
    if bed_measured<0:
        return {"status":"BLOCKED_SOURCE_CORRECTION_EXCEEDS_TOTAL_TAP_LOSS",
                "source_run_id":measured.run_id,
                "model_error_Pa":None,"validation_passed":False}
    superficial=(measured.mass_flow_kg_s/
                 (measured.gas_density_kg_m3*measured.bed_geometry.cross_section_m2))
    predicted=ergun_pressure_drop_Pa(
        measured.bed_geometry,superficial,measured.gas_density_kg_m3,
        measured.gas_dynamic_viscosity_Pa_s)
    return {
        "status":"NO_FIT_PHYSICAL_ERGUN_DIAGNOSTIC",
        "evidence_class":evidence,
        "source_run_id":measured.run_id,
        "measured_bed_only_dP_Pa":bed_measured,
        "predicted_ergun_dP_Pa":predicted,
        "predicted_minus_measured_dP_Pa":predicted-bed_measured,
        "normalized_absolute_pressure_error_by_sensor_standard_uncertainty":
            abs(predicted-bed_measured)/
                measured.differential_pressure_sensor_standard_uncertainty_Pa,
        "independently_measured_piping_correction_Pa":correction,
        "temperature_histories_not_part_of_pressure_diagnostic":True,
        "validation_passed":False,
        "exact_H_REF_hydraulic_loss_validated":False,
    }


def score_independent_holdout_thermal_history(
    run:MeasuredBedRun,*,predicted_temperature_K_by_sensor:Sequence[Sequence[float]],
    training_run_ids:Sequence[str],reserved_run_ids:Sequence[str])->dict:
    """Time- and axial-TC-aligned prediction; no resampling or fit allowed.

    Predictor must have been generated with the source-measured inlet history,
    initial bed state, proper geometry/materials and NOT the withheld outputs.
    The function cannot attest how a caller fitted these predictions; therefore
    its output explicitly never constitutes independent source validation.
    """
    if (run.run_id not in reserved_run_ids or
        run.run_id in training_run_ids or
        set(training_run_ids)&set(reserved_run_ids)):
        raise ValueError("heldout run was used for training or was not reserved")
    if len(predicted_temperature_K_by_sensor)!=len(
        run.observed_fluid_temperature_K_by_sensor):
        raise ValueError("predicted thermocouple positions mismatch")
    results=[]
    for original,predicted,pos in zip(
        run.observed_fluid_temperature_K_by_sensor,
        predicted_temperature_K_by_sensor,run.axial_sensor_positions_m):
        if len(predicted)!=len(run.time_s) or any(
            not _real(v) or v<=0 for v in predicted):
            raise ValueError("predicted temperatures must align with original timestamps")
        errors=[p-a for p,a in zip(predicted,original)]
        results.append({
          "axial_thermocouple_position_m":pos,
          "N_correlated_temporal_samples_not_independent":len(errors),
          "MAE_K":mean(abs(x) for x in errors),
          "RMSE_K":sqrt(mean(x*x for x in errors)),
          "bias_K":mean(errors),
          "max_abs_error_K":max(abs(x) for x in errors),
        })
    return {
        "status":"POINTWISE_THERMAL_HISTORY_DIAGNOSTIC_ONLY",
        "source_run_id":run.run_id,
        "per_position_error":results,
        "total_correlated_timeseries_values":len(run.time_s)*len(results),
        "separate_heldout_run_in_prediction_call":True,
        "predictor_generation_blind_to_holdout_not_independently_proven":True,
        "measured_sensor_uncertainty_K":run.thermal_sensor_standard_uncertainty_K,
        "experimental_validation_certified":False,
    }
