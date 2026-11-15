"""Natural-fluid R600 transcritical *thermodynamic screening*, NOT vendor qualification.

R600 reference evidence (different experimental operating boundaries):
Verdnik & Rieberer 2022, doi:10.1016/j.ijrefrig.2022.05.010:
one-stage suction-gas-cooled piston compressor, IHX, high-side pressure
optimisation, experimental source inlet 40-60 C, sink outlets 110-160 C.
Reported example 60 C source / 160 C sink, COP 3.1, 24.2 kW.

This simple cycle intentionally omits the apparatus IHX, compressor map,
speed constraints, discharge limits, pressurised circuit pump losses and
geometry-derived UA. It MUST NOT be claimed to reproduce hardware COP or
be manufacturer qualified at 80/70C waste source and 110/150C process.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import math
from CoolProp.CoolProp import PropsSI, get_global_param_string
from .finite_hx import HXCheck,required_ua_counterflow,InfeasibleHX


class InfeasibleR600(ValueError):
    pass


@dataclass(frozen=True)
class R600ScreenInputs:
    source_inlet_C:float=80.
    source_outlet_C:float=70.
    process_return_C:float=110.
    process_supply_C:float=150.
    process_heat_W:float=1_000_000.
    evaporator_pinch_K:float=5.
    gas_cooler_pinch_K:float=5.
    suction_superheat_K:float=10.
    evaporator_UA_W_K:float=250_000.
    gas_cooler_UA_W_K:float=250_000.
    isentropic_efficiency:float=.74  # hypothesis, NOT published map at 80 C
    motor_efficiency:float=.95
    inverter_efficiency:float=.98
    source_cp_J_kgK:float=4180.
    process_cp_J_kgK:float=4180.
    available_source_flow_kg_s:float=25.
    available_process_flow_kg_s:float=10.
    high_pressure_Pa:float=4_500_000.
    gas_cooler_exit_C:float=115.  # installed HX assumed 5 K cold-end approach
    segments:int=100
    fluid:str="HEOS::n-Butane"

    def __post_init__(self):
        values=[v for v in vars(self).values() if isinstance(v,(float,int))
                and not isinstance(v,bool)]
        if not all(math.isfinite(v) for v in values):
            raise InfeasibleR600("nonfinite cycle inputs")
        if self.process_heat_W<=0 or self.source_inlet_C<=self.source_outlet_C:
            raise InfeasibleR600("no source heat or useful output")
        if self.process_supply_C<=self.process_return_C:
            raise InfeasibleR600("process heating temperature order invalid")
        if self.evaporator_pinch_K<=0:
            raise InfeasibleR600("invalid evaporator approach")
        if self.gas_cooler_pinch_K<=0 or self.suction_superheat_K<=0:
            raise InfeasibleR600("invalid superheat/approach")
        if not all(0<x<=1 for x in (self.isentropic_efficiency,
                                  self.motor_efficiency,self.inverter_efficiency)):
            raise InfeasibleR600("invalid assumed efficiencies")
        if min(self.evaporator_UA_W_K,self.gas_cooler_UA_W_K,
               self.available_source_flow_kg_s,self.available_process_flow_kg_s,
               self.source_cp_J_kgK,self.process_cp_J_kgK)>0:
            pass
        else:
            raise InfeasibleR600("positive flow caps/cp/UA required")
        if isinstance(self.segments,bool) or self.segments<8:
            raise InfeasibleR600("segments must be >=8")


@dataclass(frozen=True)
class R600ScreenResult:
    inputs:R600ScreenInputs
    evaporating_C:float
    critical_temperature_C:float
    critical_pressure_Pa:float
    evaporator_pressure_Pa:float
    high_side_pressure_Pa:float
    pressure_ratio:float
    suction_C:float
    discharge_C:float
    mass_flow_kg_s:float
    Q_process_W:float
    Q_source_W:float
    W_shaft_W:float
    W_compressor_electric_W:float
    COP_compressor_electric:float
    source_flow_kg_s:float
    process_flow_kg_s:float
    heat_balance_residual_W:float
    evaporator_HX:HXCheck
    gas_cooler_HX:HXCheck
    scientific_status:str="thermodynamically_feasible_screener_NO_compressor_map_NO_hardware_qualification"


def solve_r600_screen(case:R600ScreenInputs=R600ScreenInputs())->R600ScreenResult:
    b=case.fluid
    prop=lambda output,k1,x1,k2,x2:float(PropsSI(output,k1,x1,k2,x2,b))
    tcrit=float(PropsSI("Tcrit",b))
    pcrit=float(PropsSI("pcrit",b))
    if case.high_pressure_Pa<=pcrit:
        raise InfeasibleR600("high side must exceed R600 critical pressure in transcritical screen")
    evap_C=case.source_outlet_C-case.evaporator_pinch_K
    if evap_C+case.suction_superheat_K>case.source_inlet_C-case.evaporator_pinch_K+1e-10:
        raise InfeasibleR600("source hot-end suction superheat pinch infeasible")
    evap_T=evap_C+273.15
    pe=float(PropsSI("P","T",evap_T,"Q",1,b))
    if case.high_pressure_Pa<=pe:
        raise InfeasibleR600("compression pressure ordering invalid")
    t1=evap_T+case.suction_superheat_K
    h1=prop("H","P",pe,"T",t1)
    s1=prop("S","P",pe,"T",t1)
    h2s=prop("H","P",case.high_pressure_Pa,"S",s1)
    h2=h1+(h2s-h1)/case.isentropic_efficiency
    t2=prop("T","P",case.high_pressure_Pa,"H",h2)
    t3=case.gas_cooler_exit_C+273.15
    h3=prop("H","P",case.high_pressure_Pa,"T",t3)
    h4=h3  # isenthalpic expansion, no pressure loss assumptions
    if h2<=h3 or h1<=h4:
        raise InfeasibleR600("nonpositive gas cooler or evaporator heat")
    m=case.process_heat_W/(h2-h3)
    qsource=m*(h1-h4)
    wshaft=m*(h2-h1)
    we=wshaft/(case.motor_efficiency*case.inverter_efficiency)
    msource=qsource/(case.source_cp_J_kgK*
                     (case.source_inlet_C-case.source_outlet_C))
    mprocess=case.process_heat_W/(case.process_cp_J_kgK*
                     (case.process_supply_C-case.process_return_C))
    if msource>case.available_source_flow_kg_s:
        raise InfeasibleR600("source mass flow cap exceeded")
    if mprocess>case.available_process_flow_kg_s:
        raise InfeasibleR600("process mass flow cap exceeded")
    check_source=required_ua_counterflow(
        duty_W=qsource,
        hot_temperature_K=lambda x:case.source_inlet_C+273.15-
            (case.source_inlet_C-case.source_outlet_C)*x,
        cold_in_K=prop("T","P",pe,"H",h4),
        cold_out_K=t1,
        cold_temperature_K=lambda x:(
            t1 if x==0 else prop("T","P",pe,"H",h4) if x==1
            else prop("T","P",pe,"H",h1-(h1-h4)*x)),
        minimum_approach_K=case.evaporator_pinch_K,
        installed_UA_W_per_K=case.evaporator_UA_W_K,
        segments=case.segments)
    check_cooler=required_ua_counterflow(
        duty_W=case.process_heat_W,
        hot_temperature_K=lambda x:(
            t2 if x==0 else t3 if x==1
            else prop("T","P",case.high_pressure_Pa,"H",h2-(h2-h3)*x)),
        cold_in_K=case.process_return_C+273.15,
        cold_out_K=case.process_supply_C+273.15,
        minimum_approach_K=case.gas_cooler_pinch_K,
        installed_UA_W_per_K=case.gas_cooler_UA_W_K,
        segments=case.segments)
    resid=qsource+wshaft-case.process_heat_W
    if abs(resid)>1e-8*case.process_heat_W:
        raise InfeasibleR600("first law failure")
    return R600ScreenResult(
        case,evap_C,tcrit-273.15,pcrit,pe,case.high_pressure_Pa,
        case.high_pressure_Pa/pe,t1-273.15,t2-273.15,m,
        case.process_heat_W,qsource,wshaft,we,case.process_heat_W/we,
        msource,mprocess,resid,check_source,check_cooler)


def scan_transcritical_high_side(
    base:R600ScreenInputs=R600ScreenInputs(),
    high_pressures_Pa:tuple[float,...]=(4.0e6,4.5e6,5.0e6,5.5e6,6.0e6)
) -> dict:
    if len(high_pressures_Pa)<2 or any(not math.isfinite(p) or p<=0 for p in high_pressures_Pa):
        raise ValueError("high-side scan requires >=2 positive pressures")
    points=[]
    for p in high_pressures_Pa:
        from dataclasses import replace
        trial=replace(base,high_pressure_Pa=p)
        try:
            r=solve_r600_screen(trial)
            points.append({
                "pressure_Pa":p,"status":"FINITE_HX_THERMODYNAMIC_SCREEN_PASS",
                "COP_compressor_electric":r.COP_compressor_electric,
                "pressure_ratio":r.pressure_ratio,
                "discharge_C":r.discharge_C,
                "required_gas_cooler_UA_W_K":r.gas_cooler_HX.required_UA_W_per_K,
                "requires_hardware_map":True,
            })
        except (InfeasibleR600,InfeasibleHX,ValueError) as exc:
            points.append({"pressure_Pa":p,
                           "status":"INFEASIBLE_SCREEN",
                           "reason":str(exc)[:180]})
    candidates=[v for v in points if v["status"]=="FINITE_HX_THERMODYNAMIC_SCREEN_PASS"]
    return {
        "points":points,
        "screening_best_pressure_Pa":(
            max(candidates,key=lambda v:v["COP_compressor_electric"])["pressure_Pa"]
            if candidates else None),
        "hardware_qualified":False,
        "measured_80C_150C_refrigerant_map":False,
        "model_limits":[
            "No real compressor map, speed, discharge-temperature guards or verified IHX",
            "High-side pressure sweep is not manufacturer rated operation",
            "No source/process pumps, gas cooler geometry, source pressure drop, TES dynamics",
            "No verified match to R600 experiment at 80C source / 150C process",
        ],
    }
