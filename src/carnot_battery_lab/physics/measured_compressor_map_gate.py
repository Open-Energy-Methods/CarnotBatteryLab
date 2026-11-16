"""M1.5 — independent compressor-map acceptance pre-screen, NEVER certification.

The numerical M1.4 demand is the query, not test evidence. A submitted map
must describe a *specific machine and stage*, its independently measured
suction operating coordinates, declared speed lines, measured shaft duty and
discharge temperature, rated limits, holdouts, uncertainties and provenance.

Interpolation is limited to the convex hull of stable FIT points at ONE
measured speed line. Two separate HOLDOUT measurements must predict measured
outputs without participating in interpolation. No cross-speed blending,
extrapolation, stitched stage maxima, automatic map authenticity judgment,
or extension from stage screening to system/hardware qualification.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isfinite
from pathlib import Path
import json
import re
from typing import Literal, Mapping, Sequence

from .compressor_envelope_requirements import CompressorStageDemand


COORDINATES = (
    "suction_pressure_Pa",
    "suction_temperature_C",
    "stage_pressure_ratio",
    "suction_volumetric_flow_m3_s",
)
OUTPUTS = (
    "refrigerant_mass_flow_kg_s",
    "shaft_power_W",
    "discharge_temperature_C",
)
ALLOWED_ORIGINS = (
    "SYNTHETIC_TEST_FIXTURE",
    "SUPPLIER_REPORTED_UNREVIEWED",
    "MEASURED_UNREVIEWED",
    "MEASURED_REVIEW_ASSERTED",
)


def _positive(value:float)->bool:
    return isinstance(value,(float,int)) and not isinstance(value,bool) and isfinite(value) and value>0


@dataclass(frozen=True)
class MapObservation:
    point_id: str
    role: Literal["fit","holdout"]
    speed_rpm: float
    suction_pressure_Pa: float
    suction_temperature_C: float
    stage_pressure_ratio: float
    suction_volumetric_flow_m3_s: float
    refrigerant_mass_flow_kg_s: float
    shaft_power_W: float
    discharge_temperature_C: float
    isentropic_efficiency: float
    stability_confirmed: bool
    flow_relative_standard_uncertainty: float
    shaft_relative_standard_uncertainty: float
    discharge_temperature_standard_uncertainty_K: float

    def __post_init__(self):
        if not self.point_id or self.role not in ("fit","holdout"):
            raise ValueError("map point requires unique ID and explicit fit/holdout role")
        for key in (
            "speed_rpm","suction_pressure_Pa","stage_pressure_ratio",
            "suction_volumetric_flow_m3_s","refrigerant_mass_flow_kg_s",
            "shaft_power_W","discharge_temperature_standard_uncertainty_K",
            "flow_relative_standard_uncertainty",
            "shaft_relative_standard_uncertainty",
        ):
            if not _positive(getattr(self,key)):
                raise ValueError(f"invalid positive measured field: {key}")
        if (not isfinite(self.suction_temperature_C) or
            not isfinite(self.discharge_temperature_C) or
            self.stage_pressure_ratio<=1 or
            not 0<self.isentropic_efficiency<=1 or
            self.stability_confirmed is not True or
            self.flow_relative_standard_uncertainty>0.25 or
            self.shaft_relative_standard_uncertainty>0.25):
            raise ValueError("invalid map point, uncertainty or stability")


@dataclass(frozen=True)
class RatedMapLimits:
    minimum_speed_rpm: float
    maximum_speed_rpm: float
    maximum_absolute_discharge_pressure_Pa: float
    maximum_stage_pressure_ratio: float
    maximum_discharge_temperature_C: float
    maximum_shaft_power_W: float

    def __post_init__(self):
        if (not all(_positive(getattr(self,key)) for key in (
            "minimum_speed_rpm","maximum_speed_rpm",
            "maximum_absolute_discharge_pressure_Pa",
            "maximum_stage_pressure_ratio","maximum_shaft_power_W"))
            or self.maximum_speed_rpm<self.minimum_speed_rpm
            or self.maximum_stage_pressure_ratio<=1
            or not isfinite(self.maximum_discharge_temperature_C)):
            raise ValueError("invalid or missing rated machine limits")


@dataclass(frozen=True)
class MapEvidence:
    evidence_class: str
    manufacturer_or_laboratory: str
    machine_id: str
    train_id: str
    topology_id: str
    stage: str
    refrigerant: str
    source_document_url: str | None
    source_document_sha256: str | None
    calibration_traceability_reference: str | None
    heldout_test_campaign_id: str | None
    independent_review_reference: str | None

    def __post_init__(self):
        if (self.evidence_class not in ALLOWED_ORIGINS or not all(
                (self.manufacturer_or_laboratory,self.machine_id,self.train_id,
                 self.topology_id,self.stage,self.refrigerant))):
            raise ValueError("invalid map evidence origin or machine identity")
        if self.evidence_class=="SYNTHETIC_TEST_FIXTURE":
            # Never permit a synthetic test fixture to masquerade as measured.
            return
        if (not self.source_document_url or
            not self.source_document_url.startswith("https://") or
            not self.source_document_sha256 or not re.fullmatch(
                "[0-9a-fA-F]{64}",self.source_document_sha256) or
            not self.calibration_traceability_reference or
            not self.heldout_test_campaign_id):
            raise ValueError("non-synthetic evidence lacks source, digest, calibration or independent campaign")
        if (self.evidence_class=="MEASURED_REVIEW_ASSERTED" and
            not self.independent_review_reference):
            raise ValueError("reviewed evidence needs a verifiable independent review reference")


@dataclass(frozen=True)
class MapThresholds:
    maximum_mass_flow_relative_error: float = 0.05
    maximum_shaft_power_relative_error: float = 0.05
    maximum_discharge_temperature_difference_K: float = 5.0
    maximum_holdout_normalized_error: float = 3.0

    def __post_init__(self):
        values=(
            self.maximum_mass_flow_relative_error,
            self.maximum_shaft_power_relative_error,
            self.maximum_discharge_temperature_difference_K,
            self.maximum_holdout_normalized_error,
        )
        if (not all(_positive(v) for v in values) or
            self.maximum_mass_flow_relative_error>0.2 or
            self.maximum_shaft_power_relative_error>0.2 or
            self.maximum_discharge_temperature_difference_K>20 or
            self.maximum_holdout_normalized_error>5):
            raise ValueError("unreasonable interpolation/holdout screening tolerances")


@dataclass(frozen=True)
class CompressorMap:
    evidence: MapEvidence
    rated_limits: RatedMapLimits
    points: tuple[MapObservation,...]

    def __post_init__(self):
        if len(self.points)<5:
            raise ValueError("map requires multipoint FIT and independent HOLDOUT measurements")
        ids=[x.point_id for x in self.points]
        if len(ids)!=len(set(ids)):
            raise ValueError("duplicate map point identifier")
        if len([x for x in self.points if x.role=="fit"])<3:
            raise ValueError("fewer than three independent map fitting points")
        if len([x for x in self.points if x.role=="holdout"])<2:
            raise ValueError("fewer than two independent holdout points")
        rated=self.rated_limits
        for x in self.points:
            if (not rated.minimum_speed_rpm<=x.speed_rpm<=rated.maximum_speed_rpm
                or x.stage_pressure_ratio>rated.maximum_stage_pressure_ratio
                or x.suction_pressure_Pa*x.stage_pressure_ratio>
                    rated.maximum_absolute_discharge_pressure_Pa
                or x.discharge_temperature_C>rated.maximum_discharge_temperature_C
                or x.shaft_power_W>rated.maximum_shaft_power_W):
                raise ValueError("measured point violates declared rated machine limits")


def map_from_dict(source:dict)->CompressorMap:
    if not isinstance(source,dict):
        raise ValueError("map must be a JSON object")
    return CompressorMap(
        evidence=MapEvidence(**source["evidence"]),
        rated_limits=RatedMapLimits(**source["rated_limits"]),
        points=tuple(MapObservation(**p) for p in source["points"]),
    )


def read_map_package(filename:str|Path)->tuple[CompressorMap,...]:
    """Explicit external input only; never fabricate maps from the M1.4 model."""
    data=json.loads(Path(filename).read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.get("schema")!="m1.5-measured-map-v1":
        raise ValueError("missing m1.5-measured-map-v1 schema")
    if not isinstance(data.get("maps"),list) or not data["maps"]:
        raise ValueError("map package has no measured/synthetic maps")
    maps=tuple(map_from_dict(m) for m in data["maps"])
    identities=[(m.evidence.train_id,m.evidence.stage) for m in maps]
    if len(identities)!=len(set(identities)):
        raise ValueError("multiple maps with same train and stage need explicit selection")
    return maps


def _coordinate_tuple(x)->tuple[float,...]:
    return tuple(float(getattr(x,k) if not isinstance(x,dict) else x[k])
                 for k in COORDINATES)


def _convex_weights_at_fixed_speed(
    query:Sequence[float], fit:Sequence[MapObservation],
)->list[float]|None:
    """Solve nonnegative barycentric feasibility, not unconstrained polynomial fit.

    Each coordinate is normalized by measured span, with fixed coordinates
    requiring near-exact equality. Strictly no extrapolation and no mixing
    across speeds; libscipy is imported only for nonempty map evaluations.
    """
    if len(fit)<3 or any(x.role!="fit" for x in fit):
        return None
    from scipy.optimize import linprog
    measurements=[_coordinate_tuple(p) for p in fit]
    aeq=[[1.0]*len(fit)]
    beq=[1.]
    for axis,q in enumerate(query):
        vals=[row[axis] for row in measurements]
        low,high=min(vals),max(vals)
        if high-low<=1e-12*max(1.,abs(low),abs(high)):
            if abs(q-low)>1e-9*max(1.,abs(low)):
                return None
            continue
        spread=high-low
        v=(q-low)/spread
        if v<-1e-8 or v>1+1e-8:
            return None
        aeq.append([(x-low)/spread for x in vals])
        beq.append(v)
    solution=linprog(
        [0.]*len(fit),A_eq=aeq,b_eq=beq,bounds=(0,None),
        method="highs")
    if not solution.success:
        return None
    weights=[float(x) for x in solution.x]
    if (any(x<-1e-8 for x in weights)
        or max(abs(sum(x*y for x,y in zip(weights,row))-v)
               for row,v in zip(aeq,beq))>1e-7):
        return None
    return weights


def _interpolate(fit:Sequence[MapObservation],weights:Sequence[float])->dict:
    return {key:sum(w*getattr(point,key) for point,w in zip(fit,weights))
            for key in OUTPUTS}


def validate_holdouts(m:CompressorMap, thresholds:MapThresholds)->dict:
    """HOLDOUT points must not appear among interpolated FIT samples."""
    rows=[]
    heldout=[x for x in m.points if x.role=="holdout"]
    for test in heldout:
        line=[x for x in m.points if x.role=="fit" and x.speed_rpm==test.speed_rpm]
        weights=_convex_weights_at_fixed_speed(_coordinate_tuple(test),line)
        if weights is None:
            rows.append({"point_id":test.point_id,"status":"HOLDOUT_OUTSIDE_FIT_SUPPORT"})
            continue
        predicted=_interpolate(line,weights)
        mass_error=abs(predicted["refrigerant_mass_flow_kg_s"]-test.refrigerant_mass_flow_kg_s)
        shaft_error=abs(predicted["shaft_power_W"]-test.shaft_power_W)
        discharge_error=abs(predicted["discharge_temperature_C"]-test.discharge_temperature_C)
        flow_limit=max(
            thresholds.maximum_mass_flow_relative_error*test.refrigerant_mass_flow_kg_s,
            thresholds.maximum_holdout_normalized_error*
                test.flow_relative_standard_uncertainty*test.refrigerant_mass_flow_kg_s)
        power_limit=max(
            thresholds.maximum_shaft_power_relative_error*test.shaft_power_W,
            thresholds.maximum_holdout_normalized_error*
                test.shaft_relative_standard_uncertainty*test.shaft_power_W)
        temperature_limit=max(
            thresholds.maximum_discharge_temperature_difference_K,
            thresholds.maximum_holdout_normalized_error*
                test.discharge_temperature_standard_uncertainty_K)
        ok=(mass_error<=flow_limit and shaft_error<=power_limit and
            discharge_error<=temperature_limit)
        rows.append({
            "point_id":test.point_id,
            "status":"HOLDOUT_RECONSTRUCTED_WITHIN_TOLERANCES"
                if ok else "HOLDOUT_PREDICTION_FAILED",
            "absolute_mass_flow_error_kg_s":mass_error,
            "absolute_shaft_power_error_W":shaft_error,
            "absolute_discharge_temperature_error_K":discharge_error,
            "test_not_used_for_fit":True,
        })
    valid=len(rows)>=2 and all(
        x["status"]=="HOLDOUT_RECONSTRUCTED_WITHIN_TOLERANCES" for x in rows)
    return {"passed":valid,"heldout_count":len(rows),"details":rows,
            "not_independent_evidence_of_source_authenticity":True}


def _rated_guard(demand:CompressorStageDemand, rated:RatedMapLimits,
                 speed:float)->str|None:
    if not rated.minimum_speed_rpm<=speed<=rated.maximum_speed_rpm:
        return "SPEED_OUTSIDE_MACHINE_RATING"
    if demand.discharge_pressure_Pa>rated.maximum_absolute_discharge_pressure_Pa:
        return "DISCHARGE_PRESSURE_ABOVE_MACHINE_RATING"
    if demand.stage_pressure_ratio>rated.maximum_stage_pressure_ratio:
        return "PRESSURE_RATIO_ABOVE_MACHINE_RATING"
    if demand.discharge_temperature_C>rated.maximum_discharge_temperature_C:
        return "MODEL_DISCHARGE_TEMPERATURE_ABOVE_MACHINE_RATING"
    if demand.shaft_power_W_idealized>rated.maximum_shaft_power_W:
        return "MODEL_SHAFT_POWER_ABOVE_MACHINE_RATING"
    return None


def screen_stage_demand(
    demand:CompressorStageDemand, maps:Sequence[CompressorMap], *,
    train_id:str, topology_id:str,
    thresholds:MapThresholds=MapThresholds(),
)->dict:
    """One full operating point; a speed-line fit does not certify controls."""
    candidates=[m for m in maps if (
        m.evidence.train_id==train_id and
        m.evidence.stage==demand.stage and
        m.evidence.refrigerant==demand.refrigerant and
        m.evidence.topology_id==topology_id)]
    if not candidates:
        return {"status":"NO_IDENTITY_AND_TOPOLOGY_MATCHED_MAP",
                "local_map_support":False,"hardware_qualified":False,
                "supported_speed_rpm":None}
    # read_map_package disallows ambiguous train/stage pairs.
    m=candidates[0]
    holdouts=validate_holdouts(m,thresholds)
    if not holdouts["passed"]:
        return {"status":"INDEPENDENT_HOLDOUT_VALIDATION_FAILED",
                "local_map_support":False,"hardware_qualified":False,
                "holdout_validation":holdouts,"supported_speed_rpm":None}
    statuses=[]
    for speed in sorted(set(p.speed_rpm for p in m.points if p.role=="fit")):
        guard=_rated_guard(demand,m.rated_limits,speed)
        if guard:
            statuses.append({"speed_rpm":speed,"status":guard})
            continue
        fit=[p for p in m.points if p.role=="fit" and p.speed_rpm==speed]
        weights=_convex_weights_at_fixed_speed(_coordinate_tuple(demand),fit)
        if weights is None:
            statuses.append({"speed_rpm":speed,"status":"OUTSIDE_FIXED_SPEED_MEASURED_CONVEX_HULL"})
            continue
        predicted=_interpolate(fit,weights)
        # Match the model's required capacity and assumed idealized shaft duty
        # against independently reported predictions with declared discrepancy
        # screening tolerances. This is NOT a rated motor curve or validation
        # of the assumed cycle's 0.74 isentropic efficiency.
        mdiff=abs(predicted["refrigerant_mass_flow_kg_s"]-
                  demand.refrigerant_mass_flow_kg_s)/demand.refrigerant_mass_flow_kg_s
        pdiff=abs(predicted["shaft_power_W"]-
                  demand.shaft_power_W_idealized)/demand.shaft_power_W_idealized
        tdiff=abs(predicted["discharge_temperature_C"]-
                  demand.discharge_temperature_C)
        if (predicted["shaft_power_W"]>m.rated_limits.maximum_shaft_power_W or
            predicted["discharge_temperature_C"]>
                m.rated_limits.maximum_discharge_temperature_C):
            status="INTERPOLATED_POINT_EXCEEDS_RATED_MACHINE_LIMIT"
        elif (mdiff>thresholds.maximum_mass_flow_relative_error or
              pdiff>thresholds.maximum_shaft_power_relative_error or
              tdiff>thresholds.maximum_discharge_temperature_difference_K):
            status="MAP_PREDICTION_DIFFERS_FROM_CYCLE_HYPOTHESIS"
        else:
            status="PROVISIONAL_NUMERICAL_INTERIOR_COVERAGE"
        statuses.append({
            "speed_rpm":speed,"status":status,
            "prediction":predicted,
            "relative_mass_flow_discrepancy":mdiff,
            "relative_shaft_power_discrepancy":pdiff,
            "absolute_discharge_temperature_discrepancy_K":tdiff,
            "fit_point_ids":[p.point_id for p in fit],
            "holdout_points_excluded_from_fit":True,
        })
    supported=next((p for p in statuses
                    if p["status"]=="PROVISIONAL_NUMERICAL_INTERIOR_COVERAGE"),None)
    provenance=m.evidence.evidence_class
    return {
        "status":("MODEL_COORDINATES_LOCALLY_SUPPORTED_BY_SYNTHETIC_MAP_ONLY"
                  if supported and provenance=="SYNTHETIC_TEST_FIXTURE"
                  else "PROVISIONAL_REVIEW_ASSERTED_MAP_COVERAGE_NOT_CERTIFICATION"
                  if supported and provenance=="MEASURED_REVIEW_ASSERTED"
                  else "PROVISIONAL_UNREVIEWED_MAP_COVERAGE_NOT_CERTIFICATION"
                  if supported else "NO_MAP_SUPPORTED_OPERATING_POINT"),
        "local_map_support":supported is not None,
        "supported_speed_rpm":supported["speed_rpm"] if supported else None,
        "map_evidence_class":provenance,
        "source_authenticity_independently_verified_by_software":False,
        "stage_model_cycle_efficiency_validated":False,
        "source_document_digest_verified_against_external_original":False,
        "hardware_qualified":False,
        "holdout_validation":holdouts,
        "speed_line_trials":statuses,
        "equipment_id":m.evidence.machine_id,
    }


def screen_compressor_train(
    stages:Sequence[CompressorStageDemand], maps:Sequence[CompressorMap], *,
    train_id:str,topology_id:str,
    thresholds:MapThresholds=MapThresholds(),
)->dict:
    if not stages:
        raise ValueError("no compressor demands supplied")
    if len({x.stage for x in stages})!=len(stages):
        raise ValueError("duplicate compressor stage in demand vector")
    records={d.stage:screen_stage_demand(d,maps,train_id=train_id,
                topology_id=topology_id,thresholds=thresholds) for d in stages}
    preliminary=all(v["local_map_support"] for v in records.values())
    return {
        "status":"MODEL_STAGE_MAP_SUPPORT_EXISTS_ONLY"
            if preliminary else "COMPRESSOR_MAP_EVIDENCE_OR_OPERATING_COVERAGE_MISSING",
        "model_stage_coordinates_supported":preliminary,
        "stage_results":records,
        "all_stage_speeds_coordinated_and_controllable":False,
        "rated_motor_and_gearbox_integration_qualified":False,
        "machine_hardware_qualified":False,
        "cycle_system_hardware_qualified":False,
    }


def screen_r718_charging_trajectory(
    trajectory:Mapping, maps:Sequence[CompressorMap], *,
    train_id:str="H_REF_R718_TWO_STAGE_INTERCOOLED",
    topology_id:str="R718_TWO_STAGE_WITH_EXTERNAL_INTERCOOLER",
    thresholds:MapThresholds=MapThresholds(),
)->dict:
    reports=[]
    for item in trajectory["points"]:
        demands=tuple(CompressorStageDemand(**x) for x in item["compressor_stages"])
        support=screen_compressor_train(demands,maps,train_id=train_id,
                    topology_id=topology_id,thresholds=thresholds)
        reports.append({
            "step":item["step"],"elapsed_s":item["elapsed_s"],
            "hot_gas_supply_C":item["hot_gas_supply_C"],
            "bed_return_C":item["bed_return_C"],
            **support,
        })
    full=bool(trajectory["charge_completed"] and reports and
              all(x["model_stage_coordinates_supported"] for x in reports))
    return {
        "status":"ALL_COMPLETED_POINTS_LOCALLY_SUPPORTED_NOT_HARDWARE_QUALIFIED"
            if full else "R718_CHARGE_ENVELOPE_NOT_ESTABLISHED",
        "requested_trajectory_complete":bool(trajectory["charge_completed"]),
        "charge_termination_reason":trajectory["charge_termination_reason"],
        "evaluated_steps":len(reports),
        "all_completed_steps_locally_supported":bool(reports and all(
            x["model_stage_coordinates_supported"] for x in reports)),
        "entire_requested_trajectory_locally_supported":full,
        "steps":reports,
        "between_step_speed_slew_and_transient_control_verified":False,
        "compressor_machine_hardware_qualified":False,
        "physical_process_heat_and_Carnot_battery_qualified":False,
    }
