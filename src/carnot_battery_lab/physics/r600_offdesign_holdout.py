"""M1.7 off-design R600 measured-electric-efficiency validation.

An external OST n-butane experimental campaign provides 20 OBSERVED points,
but no manufacturer-qualified compressor map. The originally assumed model's
eta_is=0.74 is SHAFT efficiency; OST publishes OVERALL ELECTRIC eta_is.

The zero-fit reference is therefore eta_electric=0.74*0.95*0.98.
A second, explicitly EXPLORATORY 2-parameter log-pressure-ratio ridge
correction is trained only on condition-disjoint records, then evaluated on
pre-reserved experimental operating points. Neither fit nor successful
holdout supports extrapolation to H-REF machine operating conditions.

No assumptions about shaft rpm, flow, actual gas cooler, oil limits,
independent measured uncertainties or compressor hardware are introduced.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from math import isfinite, log, sqrt
from statistics import mean
from typing import Sequence
import csv
import io
import math

SOURCE_DOI="10.5281/zenodo.17599603"
SOURCE_MD5="680dd400cfb39b2fa0a1dd22a09c731f"
EXPERIMENTAL_CAMPAIGN="Experimental OST (Purdue 2024 Natural)"
REQUIRED_FIELDS=(
    "source","compressor","refrigerant","f_elec_Hz",
    "p_suc_bar","p_dis_bar","T_suc_C","eta_is","eta_vol",
)
REFERENCE_SHAFT_ISENTROPIC_EFFICIENCY=.74
REFERENCE_MOTOR_EFFICIENCY=.95
REFERENCE_INVERTER_EFFICIENCY=.98
REFERENCE_OVERALL_ELECTRIC_EFFICIENCY=(
    REFERENCE_SHAFT_ISENTROPIC_EFFICIENCY*
    REFERENCE_MOTOR_EFFICIENCY*REFERENCE_INVERTER_EFFICIENCY
)
RIDGE_LOG_PRESSURE_RATIO_PENALTY=.20
CONDITION_BIN_COUNT=5
SPLIT_SEED="CarnotBatteryLab-M1.7-v1-precommitted-condition-quintile"
REQUIRED_HOLDOUT_COUNT=4


@dataclass(frozen=True)
class MeasuredOffdesignPoint:
    compressor:str
    campaign:str
    suction_pressure_Pa:float
    discharge_pressure_Pa:float
    suction_temperature_C:float
    electrical_frequency_Hz:float
    overall_electric_isentropic_efficiency:float
    volumetric_efficiency:float

    def __post_init__(self):
        if self.campaign!=EXPERIMENTAL_CAMPAIGN or not self.compressor:
            raise ValueError("not an independently measured OST natural-fluid campaign")
        fields=(self.suction_pressure_Pa,self.discharge_pressure_Pa,
                self.electrical_frequency_Hz,
                self.overall_electric_isentropic_efficiency,self.volumetric_efficiency)
        if (not all(isfinite(x) and x>0 for x in fields)
            or self.discharge_pressure_Pa<=self.suction_pressure_Pa
            or not isfinite(self.suction_temperature_C)
            or self.overall_electric_isentropic_efficiency>1
            or self.volumetric_efficiency>1):
            raise ValueError("nonphysical measured compressor record")

    @property
    def pressure_ratio(self)->float:
        return self.discharge_pressure_Pa/self.suction_pressure_Pa

    @property
    def condition_key(self)->tuple:
        # Exact reported field resolution; replicates remain in one split,
        # never one fit / one test.
        return (self.compressor,self.campaign,self.suction_pressure_Pa,
                self.discharge_pressure_Pa,self.suction_temperature_C,
                self.electrical_frequency_Hz)

    @property
    def opaque_id(self)->str:
        return sha256(repr(self.condition_key).encode("utf-8")).hexdigest()[:16]


def parse_ost_pure_butane(raw:bytes, *,
                          expected_md5:str=SOURCE_MD5)->tuple[MeasuredOffdesignPoint,...]:
    """Pure n-butane only; neither simulated polynomial nor HC mixtures."""
    from hashlib import md5
    if md5(raw).hexdigest()!=expected_md5:
        raise ValueError("published source checksum mismatch")
    source=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not source.fieldnames or not set(REQUIRED_FIELDS).issubset(source.fieldnames):
        raise ValueError("published source column contract not matched")
    items=[]
    for row in source:
        origin=(row["source"] or "").strip()
        refrigerant=(row["refrigerant"] or "").strip().casefold()
        if not (origin==EXPERIMENTAL_CAMPAIGN and refrigerant=="butane"):
            continue
        try:
            items.append(MeasuredOffdesignPoint(
                compressor=row["compressor"].strip(),campaign=origin,
                suction_pressure_Pa=float(row["p_suc_bar"])*1e5,
                discharge_pressure_Pa=float(row["p_dis_bar"])*1e5,
                suction_temperature_C=float(row["T_suc_C"]),
                electrical_frequency_Hz=float(row["f_elec_Hz"]),
                overall_electric_isentropic_efficiency=float(row["eta_is"]),
                volumetric_efficiency=float(row["eta_vol"]),
            ))
        except (ValueError,TypeError,AttributeError) as exc:
            raise ValueError("malformed R600 observation; never drop it silently") from exc
    if not items:
        raise ValueError("no measured pure n-butane experimental observations")
    if len({x.compressor for x in items})!=1:
        raise ValueError("multiple OST compressor machines cannot be pooled")
    if len({x.electrical_frequency_Hz for x in items})!=1:
        raise ValueError("frequency variation requires a different grouped design")
    return tuple(items)


def reserve_operating_condition_groups(
    points:Sequence[MeasuredOffdesignPoint], *,
    bins:int=CONDITION_BIN_COUNT,
    seed:str=SPLIT_SEED,
)->tuple[tuple[MeasuredOffdesignPoint,...],tuple[MeasuredOffdesignPoint,...],dict]:
    """Unsupervised, deterministic and leakage-protected condition holdouts.

    Split decisions depend only on operating input conditions and immutable
    seed; observed efficiencies are NEVER consulted for split decisions.
    Replicate observations of a physical operating point stay in one group.
    One condition per pressure-ratio quantile bin is reserved first.
    """
    if not points or bins<2:
        raise ValueError("at least two pressure ratio bins required")
    groups={}
    for x in points:
        groups.setdefault(x.condition_key,[]).append(x)
    if len(groups)<bins*2:
        raise ValueError("too few unique independent operating conditions")
    keys=sorted(groups,key=lambda k:(
        log(groups[k][0].pressure_ratio),
        groups[k][0].suction_pressure_Pa,
        groups[k][0].suction_temperature_C,
        repr(k)))
    reserved=set()
    for b in range(bins):
        part=keys[(b*len(keys))//bins:((b+1)*len(keys))//bins]
        if len(part)<2:
            raise ValueError("insufficient separate conditions within quantile bin")
        pick=min(part,key=lambda k:sha256(
            (seed+"|"+repr(k)).encode("utf-8")).hexdigest())
        reserved.add(pick)
    train=tuple(y for key in keys if key not in reserved for y in groups[key])
    holdout=tuple(y for key in keys if key in reserved for y in groups[key])
    if len(train)<8 or len(holdout)<REQUIRED_HOLDOUT_COUNT:
        raise ValueError("insufficient fit or reserved points")
    if {x.condition_key for x in train}&{x.condition_key for x in holdout}:
        raise AssertionError("operating condition leakage")
    return train,holdout,{
        "seed":seed,"algorithm":"one_condition_group_per_log_pressure_ratio_quantile",
        "bin_count":bins,
        "uses_measured_efficiency_to_choose_holdout":False,
        "unique_operating_condition_count":len(groups),
        "train_observations":len(train),"holdout_observations":len(holdout),
        "train_unique_conditions":len({x.condition_key for x in train}),
        "holdout_unique_conditions":len({x.condition_key for x in holdout}),
        "train_opaque_condition_hashes":sorted({x.opaque_id for x in train}),
        "reserved_opaque_condition_hashes":sorted({x.opaque_id for x in holdout}),
        "same_original_experimental_campaign_no_independent_run_ID":True,
    }


@dataclass(frozen=True)
class PredeclaredRidge:
    variable:str
    training_mean_input_log_ratio:float
    training_mean_output:float
    slope:float
    regularization:float=RIDGE_LOG_PRESSURE_RATIO_PENALTY

    def predict(self,point:MeasuredOffdesignPoint)->float:
        return (self.training_mean_output+
                self.slope*(log(point.pressure_ratio)-
                            self.training_mean_input_log_ratio))


def fit_one_predictor(
    train:Sequence[MeasuredOffdesignPoint], *,
    variable:str,
)->PredeclaredRidge:
    if variable not in ("overall_electric_isentropic_efficiency",
                        "volumetric_efficiency"):
        raise ValueError("unsupported fit variable")
    if len(train)<8:
        raise ValueError("too few training points")
    x=[log(p.pressure_ratio) for p in train]
    y=[getattr(p,variable) for p in train]
    x0,y0=mean(x),mean(y)
    b=sum((a-x0)*(v-y0) for a,v in zip(x,y))/(
        sum((a-x0)**2 for a in x)+RIDGE_LOG_PRESSURE_RATIO_PENALTY)
    return PredeclaredRidge(variable,x0,y0,b)


def _metrics(actual:Sequence[float], predicted:Sequence[float])->dict:
    if not actual or len(actual)!=len(predicted) or any(
            not isfinite(x) for x in (*actual,*predicted)):
        raise ValueError("metric arrays must be nonempty, finite and equal length")
    errors=[p-y for p,y in zip(predicted,actual)]
    return {
        "N":len(actual),
        "MAE":sum(abs(x) for x in errors)/len(errors),
        "RMSE":sqrt(sum(x*x for x in errors)/len(errors)),
        "bias_prediction_minus_measurement":mean(errors),
        "maximum_absolute_error":max(abs(x) for x in errors),
    }


def _in_train_convex_hull(
    point:MeasuredOffdesignPoint,
    train:Sequence[MeasuredOffdesignPoint])->bool:
    """Three-dimensional measured INPUT-domain test; no fitted outputs used."""
    from scipy.optimize import linprog
    features=lambda p:(p.suction_pressure_Pa,p.suction_temperature_C,
                        log(p.pressure_ratio))
    vals=[features(x) for x in train]
    q=features(point)
    aeq=[[1.]*len(train)];beq=[1.]
    for axis in range(3):
        v=[x[axis] for x in vals]
        low,high=min(v),max(v)
        if high-low<=1e-12*max(1.,abs(low),abs(high)):
            if abs(q[axis]-low)>1e-8*max(1.,abs(low)):
                return False
            continue
        z=(q[axis]-low)/(high-low)
        if z<0 or z>1:
            return False
        aeq.append([(x-low)/(high-low) for x in v]);beq.append(z)
    optimum=linprog([0.]*len(train),A_eq=aeq,b_eq=beq,
                    bounds=(0,None),method="highs")
    return bool(optimum.success and all(w>=-1e-8 for w in optimum.x))


def eos_ideal_electrical_work_diagnostics(
    points:Sequence[MeasuredOffdesignPoint])->dict:
    """R600 EOS derived *specific* ideal and implied electric work.

    Source CSV has no measured compressor mass flow or shaft power.
    Implied electric work from measured overall eta is NOT an independently
    measured electric power or a performance validation of any compressor map.
    """
    from CoolProp.CoolProp import PropsSI
    spec=[]
    for p in points:
        inlet_H=float(PropsSI("H","P",p.suction_pressure_Pa,
                            "T",p.suction_temperature_C+273.15,"HEOS::n-Butane"))
        inlet_S=float(PropsSI("S","P",p.suction_pressure_Pa,
                            "T",p.suction_temperature_C+273.15,"HEOS::n-Butane"))
        out_H_ideal=float(PropsSI("H","P",p.discharge_pressure_Pa,
                                 "S",inlet_S,"HEOS::n-Butane"))
        h_iso=out_H_ideal-inlet_H
        if not isfinite(h_iso) or h_iso<=0:
            raise ValueError("unphysical measured R600 EOS isentropic work")
        spec.append({
            "h_iso_J_kg":h_iso,
            "electric_specific_work_implied_J_kg":
                h_iso/p.overall_electric_isentropic_efficiency,
            "electric_specific_work_model_hypothesis_J_kg":
                h_iso/REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
        })
    def bounds(key):
        return {"min":min(row[key] for row in spec),
                "max":max(row[key] for row in spec)}
    return {
        "EOS":"CoolProp HEOS::n-Butane",
        "points":len(spec),
        "isentropic_specific_enthalpy_J_kg":bounds("h_iso_J_kg"),
        "measured_eta_implied_not_measured_electric_work_J_kg":
            bounds("electric_specific_work_implied_J_kg"),
        "model_hypothesis_specific_electric_work_J_kg":
            bounds("electric_specific_work_model_hypothesis_J_kg"),
        "actual_measured_refrigerant_mass_flow":None,
        "actual_measured_electric_power":None,
        "actual_measured_shaft_power":None,
    }


def validate_reserved_offdesign(
    train:Sequence[MeasuredOffdesignPoint],
    holdout:Sequence[MeasuredOffdesignPoint],
    *,
    split:dict|None=None,
)->dict:
    if not train or not holdout:
        raise ValueError("empty training or reserved holdout")
    if {x.condition_key for x in train}&{x.condition_key for x in holdout}:
        raise ValueError("training/holdout leakage")
    eta_fit=fit_one_predictor(train,variable=
                             "overall_electric_isentropic_efficiency")
    vol_fit=fit_one_predictor(train,variable="volumetric_efficiency")
    actual_el=[x.overall_electric_isentropic_efficiency for x in holdout]
    actual_vol=[x.volumetric_efficiency for x in holdout]
    baseline_el=[REFERENCE_OVERALL_ELECTRIC_EFFICIENCY]*len(holdout)
    train_constant_el=[eta_fit.training_mean_output]*len(holdout)
    train_constant_vol=[vol_fit.training_mean_output]*len(holdout)
    fit_el=[eta_fit.predict(x) for x in holdout]
    fit_vol=[vol_fit.predict(x) for x in holdout]
    if any(not 0<y<=1 for y in (*fit_el,*fit_vol)):
        raise ValueError("unphysical test prediction; do not clip silently")
    in_domain=[_in_train_convex_hull(x,train) for x in holdout]
    def subset(values):
        return [v for v,inside in zip(values,in_domain) if inside]
    results={
        "electric_isentropic_efficiency":{
            "fixed_M1_4_reference":_metrics(actual_el,baseline_el),
            "train_only_constant":_metrics(actual_el,train_constant_el),
            "train_only_ridge_log_pressure_ratio":_metrics(actual_el,fit_el),
        },
        "volumetric_efficiency":{
            "train_only_constant":_metrics(actual_vol,train_constant_vol),
            "train_only_ridge_log_pressure_ratio":_metrics(actual_vol,fit_vol),
        },
    }
    in_domain_n=sum(in_domain)
    if in_domain_n:
        results["within_train_pressure_temperature_ratio_convex_hull"]={
            "N":in_domain_n,
            "electric_reference":_metrics(subset(actual_el),subset(baseline_el)),
            "electric_ridge":_metrics(subset(actual_el),subset(fit_el)),
            "volumetric_ridge":_metrics(subset(actual_vol),subset(fit_vol)),
        }
    return {
        "status":"OFFTARGET_RESERVED_EXPERIMENTAL_POINTS_SCORED_NOT_MACHINE_QUALIFIED",
        "model_reference_assumed_eta_shaft":REFERENCE_SHAFT_ISENTROPIC_EFFICIENCY,
        "model_reference_assumed_motor_efficiency":REFERENCE_MOTOR_EFFICIENCY,
        "model_reference_assumed_inverter_efficiency":REFERENCE_INVERTER_EFFICIENCY,
        "model_reference_overall_electric_eta":REFERENCE_OVERALL_ELECTRIC_EFFICIENCY,
        "models_train_only":{
            "overall_electric_eta":asdict(eta_fit),
            "volumetric_efficiency":asdict(vol_fit),
        },
        "metrics":results,
        "reserved_holdout_count":len(holdout),
        "reserved_holdout_within_training_convex_hull":in_domain_n,
        "reserved_holdout_outside_training_convex_hull":
            len(holdout)-in_domain_n,
        "convex_hull_support_check_uses_no_observed_efficiencies":True,
        "training_holdout_overlap":False,
        "independent_experimental_campaign_holdout":False,
        "point_measurement_uncertainty_available":False,
        "equipment_hardware_qualified":False,
        "matched_H_REF_80_70_to_110_150_qualified":False,
        "full_compressor_M1_5_map_validation":False,
        "model_hypothesis_can_be_falsified_only_for_offtarget_measured_points":True,
        "pass_fail_on_exact_target_hardware":None,
    }
