"""R718 liquid-injection two-stage design-point reproduction (2018 source).

This is a **published DESIGN-point-aligned** thermodynamic cycle, not an
independently validated compressor map or an experimentally qualified plant.

Reference:
Zühlsdorf et al. (2018) DOI 10.18462/iir.gl.2018.1367, Table 1 and Fig 2
Impeller 1: P1=1.0 bar, T1=110 C, m1=0.196 kg/s, PR1=3.2, eta=0.74
Impeller 2: P3=3.2 bar, T3=145 C, m3=0.222 kg/s, PR2=2.0, eta=0.74
The 0.222 kg/s is INDEPENDENT nominal design data, not used to fit injection.

Figure 2: saturated condenser liquid is throttled into an intermediate
pressure de-superheater; its COMPLETE evaporation is verified by superheated
stage-two inlet state and exact mass/enthalpy mixing. Condenser liquid also
throttles to the evaporator. Separate source/sink HX UA and pinch are checked.

This reference is NOT the original 80 C waste-source / 150 C H-REF case:
120 C source inlet is an explicit illustrative added assumption to maintain
real source-side pinch with 110 C first-stage compressor suction.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from .r718 import _prop, _point, WaterPoint, InfeasibleCycle
from .finite_hx import HXCheck, required_ua_counterflow


@dataclass(frozen=True)
class InjectionDesignInputs:
    p_stage1_in_Pa: float = 100_000.0
    p_stage2_in_Pa: float = 320_000.0
    p_condenser_Pa: float = 640_000.0
    T_stage1_in_C: float = 110.0
    T_stage2_in_C: float = 145.0
    m_stage1_kg_s: float = 0.196
    eta_stage1: float = 0.74
    eta_stage2: float = 0.74
    source_in_C: float = 120.0      # assumed for finite source HX, not published
    source_pinch_K: float = 5.0
    sink_in_C: float = 110.0
    sink_out_C: float = 150.0
    sink_pinch_K: float = 5.0
    source_UA_W_K: float = 100_000.0  # hypothetical installed UA, not design
    sink_UA_W_K: float = 100_000.0
    source_cp_J_kgK: float = 4180.0
    sink_cp_J_kgK: float = 4180.0
    eta_motor: float = 0.95
    eta_inverter: float = 0.98
    eta_gear: float = 0.95
    max_stage_discharge_C: float = 350.0  # illustrative, not manufacturer limit
    segments: int = 100
    backend: str = "HEOS::Water"

    def __post_init__(self):
        for name, value in vars(self).items():
            if isinstance(value,(float,int)) and not isinstance(value,bool) and not math.isfinite(value):
                raise ValueError(f"nonfinite {name}")
        if not (0<self.p_stage1_in_Pa<self.p_stage2_in_Pa<self.p_condenser_Pa):
            raise ValueError("stage pressures must be increasing and positive")
        if self.m_stage1_kg_s<=0 or self.source_cp_J_kgK<=0 or self.sink_cp_J_kgK<=0:
            raise ValueError("positive flow and heat capacity required")
        if not all(0<v<=1 for v in (
            self.eta_stage1,self.eta_stage2,self.eta_motor,self.eta_inverter,self.eta_gear)):
            raise ValueError("efficiencies must lie in (0,1]")
        if not all(v>0 for v in (
            self.source_pinch_K,self.sink_pinch_K,self.source_UA_W_K,self.sink_UA_W_K)):
            raise ValueError("positive HX approaches/UA required")
        if not self.sink_out_C>self.sink_in_C or not self.T_stage1_in_C>0:
            raise ValueError("invalid process or inlet temperatures")
        if isinstance(self.segments,bool) or not isinstance(self.segments,int) or self.segments<8:
            raise ValueError("segments >= 8 required")


@dataclass(frozen=True)
class InjectionDesignResult:
    inputs: InjectionDesignInputs
    stage1_suction: WaterPoint
    stage1_discharge: WaterPoint
    stage2_suction: WaterPoint
    stage2_discharge: WaterPoint
    liquid_condenser: WaterPoint
    throttle_evaporator: WaterPoint
    injection_liquid_throttled: WaterPoint
    m_stage1_kg_s: float
    m_injection_kg_s: float
    m_stage2_kg_s: float
    volume_flow_stage1_m3_h: float
    volume_flow_stage2_m3_h: float
    p_ratios: tuple[float,float]
    Q_evaporator_W: float
    Q_condenser_W: float
    W_shaft_W: float
    W_grid_no_pumps_W: float
    COP_grid_no_pumps: float
    first_law_residual_W: float
    injection_mixing_residual_W: float
    source_HX: HXCheck
    sink_HX: HXCheck
    source_in_C: float
    source_out_C: float
    source_flow_kg_s: float
    sink_flow_kg_s: float
    published_stage2_flow_kg_s: float = 0.222
    published_stage1_volume_m3_h: float = 1231.0
    published_stage2_volume_m3_h: float = 468.0
    status: str = "published_design_point_thermodynamics_not_measured_compressor_map"


def solve_injection_design(case:InjectionDesignInputs=InjectionDesignInputs()
                           ) -> InjectionDesignResult:
    b=case.backend
    p1,p2,pc=case.p_stage1_in_Pa,case.p_stage2_in_Pa,case.p_condenser_Pa
    s1=_point("stage1_suction",p1,T=case.T_stage1_in_C+273.15,backend=b)
    sat1=_prop("T","P",p1,"Q",1,b)
    sat2=_prop("T","P",p2,"Q",1,b)
    satc=_prop("T","P",pc,"Q",0,b)
    if s1.temperature_K<=sat1+5:
        raise InfeasibleCycle("stage-one suction superheat <=5 K")
    s3=_point("stage2_suction",p2,T=case.T_stage2_in_C+273.15,backend=b)
    if s3.temperature_K<=sat2+5:
        raise InfeasibleCycle("stage-two suction superheat <=5 K")
    h2s=_prop("H","P",p2,"S",s1.entropy_J_kgK,b)
    s2=_point("stage1_discharge",p2,
              H=s1.enthalpy_J_kg+(h2s-s1.enthalpy_J_kg)/case.eta_stage1,backend=b)
    if s2.temperature_K<=s3.temperature_K or s2.temperature_K>case.max_stage_discharge_C+273.15:
        raise InfeasibleCycle("intercooling or stage-one discharge infeasible")
    h4s=_prop("H","P",pc,"S",s3.entropy_J_kgK,b)
    s4=_point("stage2_discharge",pc,
              H=s3.enthalpy_J_kg+(h4s-s3.enthalpy_J_kg)/case.eta_stage2,backend=b)
    if s4.temperature_K>case.max_stage_discharge_C+273.15:
        raise InfeasibleCycle("stage-two discharge exceeds assumed guard")
    liq=_point("condenser_liquid",pc,Q=0,backend=b)
    throttled=_point("throttle_evaporator",p1,H=liq.enthalpy_J_kg,backend=b)
    inj=_point("injection_liquid_after_throttle",p2,H=liq.enthalpy_J_kg,backend=b)
    # m1*h2 + m_inj*h_liq = (m1+m_inj)*h3, solve for m_inj
    m1=case.m_stage1_kg_s
    denom=s3.enthalpy_J_kg-inj.enthalpy_J_kg
    if denom<=0:
        raise InfeasibleCycle("injection fluid has insufficient cooling potential")
    mi=m1*(s2.enthalpy_J_kg-s3.enthalpy_J_kg)/denom
    if mi<=0:
        raise InfeasibleCycle("injection mass must be strictly positive")
    m3=m1+mi
    q_source=m1*(s1.enthalpy_J_kg-throttled.enthalpy_J_kg)
    q_cond=m3*(s4.enthalpy_J_kg-liq.enthalpy_J_kg)
    wshaft=m1*(s2.enthalpy_J_kg-s1.enthalpy_J_kg)+m3*(s4.enthalpy_J_kg-s3.enthalpy_J_kg)
    if min(q_source,q_cond,wshaft)<=0:
        raise InfeasibleCycle("nonpositive source, heat or compressor work")
    el=wshaft/(case.eta_motor*case.eta_inverter*case.eta_gear)
    source_out_C=sat1-273.15+case.source_pinch_K
    if source_out_C>=case.source_in_C:
        raise InfeasibleCycle("source heat transfer approach impossible")
    # Verify local hot-source vs refrigerant temperature to avoid the old
    # source-inlet-only false feasibility problem.
    evaporator=required_ua_counterflow(
        duty_W=q_source,
        hot_temperature_K=lambda x: (case.source_in_C-(case.source_in_C-source_out_C)*x)+273.15,
        cold_in_K=sat1,cold_out_K=s1.temperature_K,
        cold_temperature_K=lambda x:
            _prop("T","P",p1,"H",s1.enthalpy_J_kg-x*(s1.enthalpy_J_kg-throttled.enthalpy_J_kg),b)
            if 0<x<1 else (s1.temperature_K if x==0 else throttled.temperature_K),
        minimum_approach_K=case.source_pinch_K,
        installed_UA_W_per_K=case.source_UA_W_K,segments=case.segments)
    condenser=required_ua_counterflow(
        duty_W=q_cond,
        hot_temperature_K=lambda x:
            _prop("T","P",pc,"H",s4.enthalpy_J_kg-x*(s4.enthalpy_J_kg-liq.enthalpy_J_kg),b)
            if 0<x<1 else (s4.temperature_K if x==0 else liq.temperature_K),
        cold_in_K=case.sink_in_C+273.15,cold_out_K=case.sink_out_C+273.15,
        minimum_approach_K=case.sink_pinch_K,
        installed_UA_W_per_K=case.sink_UA_W_K,segments=case.segments)
    rho1=_prop("D","P",p1,"T",s1.temperature_K,b)
    rho3=_prop("D","P",p2,"T",s3.temperature_K,b)
    err_energy=q_source+wshaft-q_cond
    err_mix=m1*s2.enthalpy_J_kg+mi*inj.enthalpy_J_kg-m3*s3.enthalpy_J_kg
    if abs(err_energy)>1e-7*q_cond or abs(err_mix)>1e-7*q_cond:
        raise InfeasibleCycle("nonclosed injection and full-cycle energy balance")
    return InjectionDesignResult(
        case,s1,s2,s3,s4,liq,throttled,inj,m1,mi,m3,
        3600*m1/rho1,3600*m3/rho3,(p2/p1,pc/p2),
        q_source,q_cond,wshaft,el,q_cond/el,err_energy,err_mix,
        evaporator,condenser,case.source_in_C,source_out_C,
        q_source/(case.source_cp_J_kgK*(case.source_in_C-source_out_C)),
        q_cond/(case.sink_cp_J_kgK*(case.sink_out_C-case.sink_in_C)))
