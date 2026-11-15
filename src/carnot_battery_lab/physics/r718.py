"""Screening-level water-vapour R718 heat pump with finite heat exchangers.

NOT a compressor-manufacturer-qualified industrial design. Model limitations:
no refrigerant pressure losses, no compressor maps, no off-design, and an
externally cooled intercooler in the two-stage case. A simple expansion valve
(no liquid pump/flash recovery) closes the cycle. All assumptions are explicit.
SI units throughout. No frozen/assumed constant COP.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import math
from typing import Literal

from .finite_hx import HXCheck, InfeasibleHX, required_ua_counterflow


class InfeasibleCycle(ValueError):
    """Invalid property point, compressor envelope, or thermal boundary."""


@lru_cache(maxsize=1)
def _coolprop():
    try:
        import CoolProp
        from CoolProp.CoolProp import PropsSI
    except ImportError as exc:
        raise RuntimeError("R718 model requires pip install -e '.[physics]' (CoolProp)") from exc
    return PropsSI, CoolProp.__version__


@dataclass(frozen=True)
class WaterPoint:
    tag: str
    pressure_Pa: float
    temperature_K: float
    enthalpy_J_kg: float
    entropy_J_kgK: float


def _prop(output: str, k1: str, v1: float, k2: str, v2: float, backend: str) -> float:
    if backend not in ("HEOS::Water", "IF97::Water"):
        raise InfeasibleCycle("only HEOS::Water or IF97::Water supported")
    if not all(math.isfinite(x) for x in (v1,v2)):
        raise InfeasibleCycle("property input non-finite")
    f,_ = _coolprop()
    try:
        x = float(f(output,k1,v1,k2,v2,backend))
    except (ValueError,OverflowError) as exc:
        raise InfeasibleCycle(f"water property outside domain: {output}({k1},{k2})") from exc
    if not math.isfinite(x):
        raise InfeasibleCycle("water property returned non-finite result")
    return x


def _point(tag: str, pressure: float, *, backend: str,
           T: float | None=None, H: float | None=None, S: float | None=None,
           Q: int | None=None) -> WaterPoint:
    keys = [T is not None, H is not None, S is not None, Q is not None]
    if sum(keys) != 1 or pressure<=0:
        raise InfeasibleCycle("point must specify exactly one of T,H,S,Q and positive P")
    k,v = ("T",T) if T is not None else ("H",H) if H is not None else ("S",S) if S is not None else ("Q",Q)
    assert v is not None
    h=_prop("H","P",pressure,k,v,backend)
    s=_prop("S","P",pressure,k,v,backend)
    t=_prop("T","P",pressure,k,v,backend)
    return WaterPoint(tag,pressure,t,h,s)


@dataclass(frozen=True)
class R718Inputs:
    # All temperatures are Celsius in inputs, Kelvin internally.
    useful_process_heat_W: float = 1_000_000.0
    source_inlet_C: float = 80.0
    source_outlet_C: float = 70.0  # Illustrative ASSUMPTION absent from H-REF YAML
    process_return_C: float = 110.0
    process_supply_C: float = 150.0
    source_pinch_K: float = 5.0
    condenser_pinch_K: float = 5.0
    minimum_hx_approach_K: float = 5.0
    suction_superheat_K: float = 10.0
    intercool_superheat_K: float = 10.0
    intercool_sink_in_C: float = 60.0
    intercool_sink_out_C: float = 75.0
    isentropic_efficiency: float = 0.74  # illustrative, not map-qualified
    motor_efficiency: float = 0.95        # screening assumption
    max_stage_pressure_ratio: float = 5.0  # illustrative engineering screening guard
    max_discharge_C: float = 350.0        # illustrative engineering screening guard
    condenser_UA_W_K: float = 250_000.0
    source_UA_W_K: float = 250_000.0
    intercool_UA_W_K: float = 250_000.0
    source_cp_J_kgK: float = 4180.0
    process_cp_J_kgK: float = 4180.0
    intercool_cp_J_kgK: float = 4180.0
    arrangement: Literal["single","two_stage"] = "two_stage"
    backend: Literal["HEOS::Water","IF97::Water"] = "HEOS::Water"
    segments: int = 100

    def __post_init__(self):
        for name,value in vars(self).items():
            if isinstance(value,(float,int)) and not isinstance(value,bool) and not math.isfinite(value):
                raise InfeasibleCycle(f"non-finite {name}")
        if self.arrangement not in ("single","two_stage"):
            raise InfeasibleCycle("arrangement must be single or two_stage")
        if self.backend not in ("HEOS::Water","IF97::Water"):
            raise InfeasibleCycle("unrecognized property backend")
        if not (self.source_inlet_C>self.source_outlet_C>-273.15):
            raise InfeasibleCycle("source must enter hotter than it leaves")
        if not (self.process_supply_C>self.process_return_C):
            raise InfeasibleCycle("process supply must exceed process return")
        positives=("useful_process_heat_W","source_pinch_K","condenser_pinch_K",
            "minimum_hx_approach_K","suction_superheat_K","intercool_superheat_K",
            "condenser_UA_W_K","source_UA_W_K","intercool_UA_W_K",
            "source_cp_J_kgK","process_cp_J_kgK","intercool_cp_J_kgK",
            "max_stage_pressure_ratio")
        if any(getattr(self,name)<=0 for name in positives):
            raise InfeasibleCycle("positive duty, HX, heat capacity and pressure ratio required")
        if not (0<self.isentropic_efficiency<=1 and 0<self.motor_efficiency<=1):
            raise InfeasibleCycle("invalid isentropic or motor efficiency")
        if not (self.intercool_sink_out_C>self.intercool_sink_in_C):
            raise InfeasibleCycle("intercooler sink must warm")
        if isinstance(self.segments,bool) or not isinstance(self.segments,int) or self.segments<8:
            raise InfeasibleCycle("HX segments must be >=8")


@dataclass(frozen=True)
class R718Result:
    inputs: R718Inputs
    state_points: tuple[WaterPoint,...]
    low_pressure_Pa: float
    high_pressure_Pa: float
    stage_pressure_ratios: tuple[float,...]
    refrigerant_mass_flow_kg_s: float
    source_mass_flow_kg_s: float
    process_mass_flow_kg_s: float
    intercooler_sink_flow_kg_s: float
    Q_source_W: float
    Q_process_W: float
    Q_intercool_rejected_W: float
    W_compressor_shaft_W: float
    W_compressor_electric_W: float
    electric_motor_losses_W: float
    COP_heating_cycle: float
    COP_heating_electric: float
    first_law_residual_W: float
    compressor_entropy_generation_W_K: float
    condenser: HXCheck
    evaporator: HXCheck
    intercooler: HXCheck | None
    property_backend_version: str


def _compress(tag: str, inp: WaterPoint, p_out: float, design: R718Inputs) -> WaterPoint:
    ratio=p_out/inp.pressure_Pa
    if ratio<=1 or ratio>design.max_stage_pressure_ratio*(1+1e-12):
        raise InfeasibleCycle(f"stage pressure ratio {ratio:.3f} outside (1,{design.max_stage_pressure_ratio:g}]")
    hs=_prop("H","P",p_out,"S",inp.entropy_J_kgK,design.backend)
    hout=inp.enthalpy_J_kg+(hs-inp.enthalpy_J_kg)/design.isentropic_efficiency
    if hout<=inp.enthalpy_J_kg:
        raise InfeasibleCycle("compressor enthalpy rise must be positive")
    out=_point(tag,p_out,H=hout,backend=design.backend)
    if out.temperature_K>design.max_discharge_C+273.15:
        raise InfeasibleCycle(f"compressor discharge {out.temperature_K-273.15:.1f} C exceeds guard")
    if out.entropy_J_kgK+1e-4<inp.entropy_J_kgK:
        raise InfeasibleCycle("compressor violates entropy generation guard")
    return out


def solve_r718(design: R718Inputs) -> R718Result:
    """Steady cycle sized at actual condenser heat with finite source cooling.

    Evaporation is at (source outlet - pinch), NOT at (source inlet - pinch).
    The two-stage option rejects intercooler heat to separate coolant;
    rejected heat is not credited as useful process heat.
    """
    _,cpver=_coolprop()
    te=(design.source_outlet_C-design.source_pinch_K)+273.15
    tc=(design.process_supply_C+design.condenser_pinch_K)+273.15
    if te<=273.15 or tc>=647.096 or tc<=te:
        raise InfeasibleCycle("water phase, critical temperature or lift outside specified cycle")
    pe=_prop("P","T",te,"Q",1,design.backend)
    pc=_prop("P","T",tc,"Q",0,design.backend)
    state=[]
    suction=_point("suction",pe,T=te+design.suction_superheat_K,backend=design.backend)
    state.append(suction)
    if design.arrangement=="single":
        comp=_compress("discharge",suction,pc,design)
        state.append(comp)
        stage_ratios=(pc/pe,)
        shaft_J_kg=comp.enthalpy_J_kg-suction.enthalpy_J_kg
        intercool_J_kg=0.0
        intercool=None
    else:
        pm=math.sqrt(pe*pc)
        comp1=_compress("stage1_out",suction,pm,design)
        tmid=_prop("T","P",pm,"Q",1,design.backend)
        tin=tmid+design.intercool_superheat_K
        if tin>=comp1.temperature_K:
            raise InfeasibleCycle("no positive cooling potential at interstage")
        interm=_point("stage2_in",pm,T=tin,backend=design.backend)
        comp=_compress("discharge",interm,pc,design)
        state.extend((comp1,interm,comp))
        stage_ratios=(pm/pe,pc/pm)
        intercool_J_kg=comp1.enthalpy_J_kg-interm.enthalpy_J_kg
        if intercool_J_kg<=0:
            raise InfeasibleCycle("intercooler must reject heat")
        shaft_J_kg=(comp1.enthalpy_J_kg-suction.enthalpy_J_kg)+(comp.enthalpy_J_kg-interm.enthalpy_J_kg)
    liquid=_point("condenser_liquid",pc,Q=0,backend=design.backend)
    expansion=_point("after_throttle",pe,H=liquid.enthalpy_J_kg,backend=design.backend)
    state.extend((liquid,expansion))
    q_process_J_kg=comp.enthalpy_J_kg-liquid.enthalpy_J_kg
    q_source_J_kg=suction.enthalpy_J_kg-expansion.enthalpy_J_kg
    if min(q_process_J_kg,q_source_J_kg,shaft_J_kg)<=0:
        raise InfeasibleCycle("non-positive physically required cycle energy")
    m=design.useful_process_heat_W/q_process_J_kg
    qsource=m*q_source_J_kg
    qinter=m*intercool_J_kg
    wshaft=m*shaft_J_kg
    welectric=wshaft/design.motor_efficiency
    motor_loss=welectric-wshaft
    condenser=required_ua_counterflow(
        duty_W=design.useful_process_heat_W,
        hot_temperature_K=lambda x: _prop("T","P",pc,"H",comp.enthalpy_J_kg-x*q_process_J_kg,design.backend)
            if 0<x<1 else (comp.temperature_K if x==0 else liquid.temperature_K),
        cold_in_K=design.process_return_C+273.15,
        cold_out_K=design.process_supply_C+273.15,
        minimum_approach_K=design.minimum_hx_approach_K,
        installed_UA_W_per_K=design.condenser_UA_W_K,segments=design.segments)
    evaporator=required_ua_counterflow(
        duty_W=qsource,
        hot_temperature_K=lambda x: (design.source_inlet_C-(design.source_inlet_C-design.source_outlet_C)*x)+273.15,
        cold_in_K=te,cold_out_K=suction.temperature_K,
        cold_temperature_K=lambda x: _prop("T","P",pe,"H",suction.enthalpy_J_kg-x*q_source_J_kg,design.backend)
            if 0<x<1 else (suction.temperature_K if x==0 else expansion.temperature_K),
        minimum_approach_K=design.minimum_hx_approach_K,
        installed_UA_W_per_K=design.source_UA_W_K,segments=design.segments)
    flow_inter=0.0
    if design.arrangement=="two_stage":
        flow_inter=qinter/(design.intercool_cp_J_kgK*(design.intercool_sink_out_C-design.intercool_sink_in_C))
        intercool=required_ua_counterflow(
            duty_W=qinter,
            hot_temperature_K=lambda x: _prop("T","P",state[1].pressure_Pa,"H",state[1].enthalpy_J_kg-x*intercool_J_kg,design.backend)
                if 0<x<1 else (state[1].temperature_K if x==0 else state[2].temperature_K),
            cold_in_K=design.intercool_sink_in_C+273.15,
            cold_out_K=design.intercool_sink_out_C+273.15,
            minimum_approach_K=design.minimum_hx_approach_K,
            installed_UA_W_per_K=design.intercool_UA_W_K,segments=design.segments)
    ss=m*sum(max(0.0,b.entropy_J_kgK-a.entropy_J_kgK) for a,b in
        ([(suction,comp)] if design.arrangement=="single" else [(state[0],state[1]),(state[2],state[3])]))
    result=R718Result(design,tuple(state),pe,pc,stage_ratios,m,
        qsource/(design.source_cp_J_kgK*(design.source_inlet_C-design.source_outlet_C)),
        design.useful_process_heat_W/(design.process_cp_J_kgK*(design.process_supply_C-design.process_return_C)),
        flow_inter,qsource,design.useful_process_heat_W,qinter,wshaft,welectric,motor_loss,
        design.useful_process_heat_W/wshaft,design.useful_process_heat_W/welectric,
        qsource+wshaft-design.useful_process_heat_W-qinter,ss,
        condenser,evaporator,intercool,cpver)
    if abs(result.first_law_residual_W)>1e-7*result.Q_process_W:
        raise InfeasibleCycle("nonclosed full cycle energy ledger")
    return result
