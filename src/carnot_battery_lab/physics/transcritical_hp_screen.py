"""M3.18: reference-bounded steady transcritical vapour-compression screen.

EOS: CoolProp HEOS. No compressor map, calibration, plant safety case or
experimental predictive accuracy is established. Preliminary ideal
single-stage valve, isentropic-efficiency correlation and heat exchangers
are separate from the dynamic TES solver.

Literature: Pfeiffer et al., 2026 IEA/HPC pre-experimental modelling;
Pfeiffer et al., 2026 Purdue IRACC paper 2177 measured 12 points
(only selected optimum-point performance reported in Table 3).
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
import math

PAPER_EVIDENCE={
    "IEA_2026":dict(kind="prediction_plus_equipment",source_in_C=90.,source_out_C=60.,
        sink_in_C=100.,sink_out_C=150.,predicted_mixture_R290_R601a_w=(.6,.4),
        predicted_mixture_COP=2.85,predicted_pure_R600a_COP=2.58,
        compressor="BITZER 2DME-7K",compressor_limit_discharge_C=160.,
        title="Transcritical high-temperature heat pump with hydrocarbon mixtures – experimental setup and model predictions",
        source="User-supplied IEA HPC 2026 PDF pp.1,3,6"),
    "PURDUE_2026":dict(kind="experimental_measured",source_in_C=100.,source_out_C=70.,
        sink_in_C=100.,sink_out_C=150.,frequency_Hz=60.,steady_state_points_count=12,
        optimum_pure_R600a=dict(heat_kW=12.9,heat_unc_kW=.34,COP=3.01,COP_unc=.29,
            overall_isentropic_efficiency=.601,pressure_ratio=4.16,
            discharge_C=153.6,discharge_P_kPa=4399.),
        optimum_mixture_R290_R601a_50_50=dict(heat_kW=17.3,heat_unc_kW=.4,
            COP=3.39,COP_unc=.28,overall_isentropic_efficiency=.638,
            pressure_ratio=3.97,discharge_C=162.4,discharge_P_kPa=4725.),
        source="User-supplied Purdue IRACC 2026 paper 2177 pp.4-6"),
}

@dataclass(frozen=True)
class ServiceEnvelope:
    source_in_C:float
    source_out_C:float
    sink_in_C:float
    sink_out_C:float
    target_heat_W:float=1e6
    water_pressure_Pa:float=2e6
    approach_min_K:float=5.
    suction_superheat_K:float=5.
    compressor_isentropic_efficiency:float=.65
    motor_efficiency:float=.95
    volumetric_efficiency_assumed:float=.75
    compressor_discharge_temperature_limit_C:float=160.
    compressor_pressure_limit_Pa:float=8e6
    def __post_init__(self):
        z=asdict(self)
        if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in z.values()):
            raise ValueError("invalid heat pump envelope")
        if not self.source_in_C>self.source_out_C or not self.sink_out_C>self.sink_in_C:
            raise ValueError("must have source cooling and sink heating")
        if self.source_out_C<=5 or self.sink_in_C<=0 or self.sink_out_C>=210:
            raise ValueError("source/sink outside selected pressurised-water screen")
        if min(self.target_heat_W,self.water_pressure_Pa,self.approach_min_K,
               self.suction_superheat_K,self.compressor_pressure_limit_Pa)<=0:
            raise ValueError("invalid heat pump inputs")
        if not 0<min(self.compressor_isentropic_efficiency,self.motor_efficiency,
                     self.volumetric_efficiency_assumed)<=max(
                     self.compressor_isentropic_efficiency,self.motor_efficiency,
                     self.volumetric_efficiency_assumed)<=1:
            raise ValueError("efficiency outside (0,1]")

def refrigerant_id(pure_or_mix):
    """Correct mass-to-mole conversion; CoolProp HEOS binary EOS NOT REFPROP."""
    from CoolProp.CoolProp import PropsSI
    if pure_or_mix=="R600a":return "HEOS::IsoButane",{"fluid":"R600a","mixture":False}
    if pure_or_mix=="R600":return "HEOS::n-Butane",{"fluid":"R600","mixture":False}
    if pure_or_mix in ("R290_R601a_60_40","R290_R601a_50_50"):
        w1=.6 if pure_or_mix.endswith("60_40") else .5
        m1=PropsSI("M","HEOS::Propane")
        m2=PropsSI("M","HEOS::Isopentane")
        x1=(w1/m1)/(w1/m1+(1-w1)/m2)
        return f"HEOS::Propane[{x1:.14g}]&Isopentane[{1-x1:.14g}]",dict(
            fluid=pure_or_mix,mixture=True,mass_fraction_propane=w1,
            mole_fraction_propane=x1,EOS="CoolProp HEOS, not REFPROP GERG-2008")
    raise ValueError("refrigerant not in preregistered experimental/scope list")

def thermal_interface_gate(sink_outlet_C,*,charge_gas_target_C=190.,
                            hot_end_approach_K=5.):
    """A nominal 150C process-water discharge target is NOT 190C gas charging."""
    if not all(math.isfinite(x) for x in (sink_outlet_C,charge_gas_target_C,hot_end_approach_K)) or hot_end_approach_K<=0:
        raise ValueError("invalid thermal interface")
    delta=sink_outlet_C-charge_gas_target_C-hot_end_approach_K
    return dict(heat_pump_sink_outlet_C=sink_outlet_C,
        TES_gas_charge_target_C=charge_gas_target_C,
        required_heat_pump_outlet_C=charge_gas_target_C+hot_end_approach_K,
        approach_margin_K=delta,thermally_compatible_without_booster=delta>=0,
        HX_equipment_sized=False)

def _temperature_on_water_enthalpy(P,h):
    from CoolProp.CoolProp import PropsSI
    return float(PropsSI("T","P",P,"H",h,"HEOS::Water"))

def cycle_at_point(e:ServiceEnvelope,fluid,lowP,highP,*,profile_segments=10):
    """One physically screened state-point calculation, no map inference.

    Raise ValueError for a physically invalid point; EOS errors are
    distinguished by the caller and do not turn into invented performance.
    """
    from CoolProp.CoolProp import PropsSI
    prop=lambda out,i1,x1,i2,x2:float(PropsSI(out,i1,x1,i2,x2,fluid))
    criticalP=float(PropsSI("PCRIT",fluid))
    if not lowP<criticalP<highP<=e.compressor_pressure_limit_Pa:
        raise ValueError("not transcritical at permitted pressure")
    Tdew=prop("T","P",lowP,"Q",1.)
    T1=Tdew+e.suction_superheat_K
    h1=prop("H","P",lowP,"T",T1)
    s1=prop("S","P",lowP,"T",T1)
    rho1=prop("D","P",lowP,"T",T1)
    h2s=prop("H","P",highP,"S",s1)
    h2=h1+(h2s-h1)/e.compressor_isentropic_efficiency
    T2=prop("T","P",highP,"H",h2)
    T3=e.sink_in_C+273.15+e.approach_min_K
    h3=prop("H","P",highP,"T",T3)
    # Isenthalpic valve. No receiver or flash-gas bypass in this screen.
    h4=h3
    qe=h1-h4;qh=h2-h3;w=h2-h1
    if min(qe,qh,w,rho1)<=0 or not all(math.isfinite(x) for x in (qe,qh,w,T2)):
        raise ValueError("nonphysical specific heat and compression")
    if T2-273.15>e.compressor_discharge_temperature_limit_C:
        raise ValueError("compressor discharge temperature rating exceeded")
    if T2<e.sink_out_C+273.15+e.approach_min_K-1e-5:
        raise ValueError("gas cooler hot-end pinch below assumed minimum")
    P=e.water_pressure_Pa
    hsw_in=float(PropsSI("H","T",e.sink_in_C+273.15,"P",P,"HEOS::Water"))
    hsw_out=float(PropsSI("H","T",e.sink_out_C+273.15,"P",P,"HEOS::Water"))
    hso_in=float(PropsSI("H","T",e.source_in_C+273.15,"P",P,"HEOS::Water"))
    hso_out=float(PropsSI("H","T",e.source_out_C+273.15,"P",P,"HEOS::Water"))
    if min(hsw_out-hsw_in,hso_in-hso_out)<=0:
        raise ValueError("invalid hot-water external loops")
    gc_min=float("inf");ev_min=float("inf")
    for k in range(profile_segments+1):
        f=k/profile_segments
        # Gas cooler hot->cold, counterflow water hot->cold.
        h_ref=h2-f*qh
        t_ref=prop("T","P",highP,"H",h_ref)
        t_water=_temperature_on_water_enthalpy(P,hsw_out-f*(hsw_out-hsw_in))
        gc_min=min(gc_min,t_ref-t_water)
        # Evaporator refrigerant cold->hot, heat source cold->hot.
        h_ref=h4+f*qe
        t_ref=prop("T","P",lowP,"H",h_ref)
        t_water=_temperature_on_water_enthalpy(P,hso_out+f*(hso_in-hso_out))
        ev_min=min(ev_min,t_water-t_ref)
    if min(gc_min,ev_min)<e.approach_min_K-1e-4:
        raise ValueError("local gas cooler/evaporator pinch violated")
    mref=e.target_heat_W/qh
    power_shaft=mref*w
    power_electric=power_shaft/e.motor_efficiency
    source_heat=mref*qe
    energy_residual=e.target_heat_W-source_heat-power_shaft
    if abs(energy_residual)>1e-7*e.target_heat_W:raise ValueError("heat-pump first law violated")
    suction_volume=mref/rho1
    pilot_disp_60Hz=9.2/3600.*60/50*e.volumetric_efficiency_assumed
    return dict(refrigerant=fluid,heating_W=e.target_heat_W,
        COP_compressor_electric=e.target_heat_W/power_electric,
        power_compressor_electric_W=power_electric,
        compressor_shaft_W=power_shaft,motor_loss_W=power_electric-power_shaft,
        source_heat_W=source_heat,process_water_flow_kg_s=e.target_heat_W/(hsw_out-hsw_in),
        required_source_water_flow_kg_s=source_heat/(hso_in-hso_out),
        refrigerant_mass_flow_kg_s=mref,suction_volume_flow_m3_s=suction_volume,
        equivalent_60Hz_pilot_displacement_count=suction_volume/pilot_disp_60Hz,
        pressure_low_Pa=lowP,pressure_high_Pa=highP,pressure_ratio=highP/lowP,
        discharge_temperature_C=T2-273.15,suction_temperature_C=T1-273.15,
        gas_cooler_min_approach_K=gc_min,evaporator_min_approach_K=ev_min,
        energy_residual_W=energy_residual,
        compressor_rating_margin_C=e.compressor_discharge_temperature_limit_C-(T2-273.15),
        compressor_map_measured=False,compressor_efficiency_assumed=True,
        pressure_loss_in_HX_modeled=False,mechanical_design_qualified=False)

def screen_envelope(e:ServiceEnvelope,refrigerant,*,low_dew_count=4,high_pressure_count=8):
    """Discover, not optimise, a reproducible low/high pressure grid."""
    from CoolProp.CoolProp import PropsSI
    fluid,meta=refrigerant_id(refrigerant)
    # Analytical impossibility: heat cannot flow across the hot-end pinch
    # when the allowed compressor discharge is colder than the required sink.
    # Check this BEFORE EOS searching; no compressor map can waive the limit.
    if e.sink_out_C+e.approach_min_K>e.compressor_discharge_temperature_limit_C:
        return dict(status="REJECTED_BY_HOT_END_RATING",fluid=meta,
            assumptions=asdict(e),attempts=0,accepted_points=0,
            rejections={"compressor_discharge_below_required_sink_hot_end":1},
            best=None,experimental_validation=False,
            thermodynamic_rating_gate_only=True)
    attempts=accepted=0
    failures={}
    selected=None
    try:
        critical=float(PropsSI("PCRIT",fluid))
    except Exception as exc:
        return dict(status="EOS_CRITICAL_POINT_UNAVAILABLE",fluid=meta,assumptions=asdict(e),
                    attempts=0,accepted_points=0,error=str(exc)[:300],best=None,
                    experimental_validation=False)
    low_dew_min=e.source_out_C-e.approach_min_K
    low_dew_max=min(e.source_in_C-e.suction_superheat_K-e.approach_min_K,low_dew_min+25.)
    for j in range(low_dew_count):
        dew=low_dew_min+(low_dew_max-low_dew_min)*j/max(1,low_dew_count-1)
        try:pl=float(PropsSI("P","T",dew+273.15,"Q",1.,fluid))
        except Exception as exc:
            failures["EOS_LOW_PRESSURE_FAILURE"]=failures.get("EOS_LOW_PRESSURE_FAILURE",0)+1
            continue
        for i in range(high_pressure_count):
            attempts+=1
            ph=critical*(1.02+(.48*i/max(1,high_pressure_count-1)))
            try:
                z=cycle_at_point(e,fluid,pl,ph)
            except ValueError as exc:
                key=str(exc);failures[key]=failures.get(key,0)+1
                continue
            except Exception:
                failures["EOS_STATE_UNAVAILABLE"]=failures.get("EOS_STATE_UNAVAILABLE",0)+1
                continue
            accepted+=1
            if selected is None or z["COP_compressor_electric"]>selected["COP_compressor_electric"]:
                selected=z
    return dict(status="SCREENED_EOS_FEASIBLE" if selected else "NO_FEASIBLE_CANDIDATE_ON_GRID",
        fluid=meta,assumptions=asdict(e),attempts=attempts,accepted_points=accepted,
        rejections=failures,best=selected,
        grid_search_not_global_optimisation=True,
        experimental_validation=False,
        compressor_speeds_measured=False)
