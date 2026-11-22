"""M3.19 matched-service, temperature-approach-driven charging alternatives.

This screens *necessary* heat-transfer conditions. An upper-bound
postprocessing allocation is not a coupled compressor/TES simulation.
All inputs in SI, all reported savings CONDITIONAL on source/pinch/HP
capacity and compressor-map/hardware qualification.
"""
from __future__ import annotations
import math

def direct_hp_gate(charge_target_C,hot_end_approach_K=5.,
                   hp_compressor_discharge_limit_C=160.,
                   charger_hot_loop_outlet_C=150.):
    vals=(charge_target_C,hot_end_approach_K,hp_compressor_discharge_limit_C,charger_hot_loop_outlet_C)
    if not all(math.isfinite(x) for x in vals) or hot_end_approach_K<=0:
        raise ValueError("invalid temperature boundaries")
    required_loop_C=charge_target_C+hot_end_approach_K
    # Additional 5 K refrigerant-to-water pinch: compressor discharge
    # must be hotter than water output for physical heat transfer.
    required_compressor_C=required_loop_C+hot_end_approach_K
    return dict(charge_gas_target_C=charge_target_C,
        required_hot_water_outlet_C=required_loop_C,
        required_compressor_discharge_C=required_compressor_C,
        water_temperature_suffices=charger_hot_loop_outlet_C>=required_loop_C,
        discharge_rating_suffices=hp_compressor_discharge_limit_C>=required_compressor_C,
        directly_compatible=charger_hot_loop_outlet_C>=required_loop_C and hp_compressor_discharge_limit_C>=required_compressor_C,
        compressor_performance_map_qualified=False,heat_exchanger_sized=False)

def bounded_hp_preheat(charge_stage,*,gas_enthalpy,gas_hp_supply_C=150.,
                       hot_end_approach_K=5.,hypothetical_hp_COP=2.302054578653484,
                       resistance_efficiency=.95,max_ledger_disagreement=.04):
    """Integrate optimistic 150C-to-gas preheat before an electric boost.

    Model trajectory and actual heater heat remain fixed. Allows at most
    min(original heat input, m*(h(145C)-h(Treturn))), never reuses heat,
    and assumes zero added pressure loss, no HX inventory, perfectly
    controlled split and constant hypothetical HP COP. Gives *a bound*,
    NOT proved savings or physical heat-pump/TES matching.
    """
    if not callable(gas_enthalpy):raise ValueError("gas enthalpy EOS required")
    v=(gas_hp_supply_C,hot_end_approach_K,hypothetical_hp_COP,resistance_efficiency,max_ledger_disagreement)
    if not all(math.isfinite(x) for x in v) or hot_end_approach_K<=0 or hypothetical_hp_COP<=1 or not 0<resistance_efficiency<=1 or not 0<max_ledger_disagreement<1:
        raise ValueError("invalid hypothetical heat-pump assumptions")
    rows=charge_stage["phase_trace"]
    if rows is None or len(rows)<2:raise ValueError("charge trace unavailable")
    max_gas_K=gas_hp_supply_C+273.15-hot_end_approach_K
    vals=[]
    for row in rows:
        try:t=float(row["time_s"]);q=float(row["heater_to_gas_W"]);m=float(row["gas_flow_kg_s"]);tret=float(row["return_gas_K"])
        except (KeyError,TypeError) as exc:raise ValueError("missing charge-trace state") from exc
        if not all(math.isfinite(x) for x in (t,q,m,tret)) or q<0 or m<0 or tret<=0:
            raise ValueError("invalid thermodynamic charge-trace state")
        if tret>=max_gas_K:pre=0.
        else:
            hot_h=float(gas_enthalpy(max_gas_K))
            return_h=float(gas_enthalpy(tret))
            if not all(math.isfinite(x) for x in (hot_h,return_h)) or hot_h<=return_h:
                raise ValueError("nonphysical air-heating EOS")
            pre=min(q,m*(hot_h-return_h))
        vals.append((t,q,pre))
    if abs(vals[0][0])>1e-8 or abs(vals[-1][0]-charge_stage["duration_s"])>1e-7:
        raise ValueError("charge trace not phase-aligned")
    Epre=Eorig_trace=0.
    for a,b in zip(vals[:-1],vals[1:]):
        dt=b[0]-a[0]
        if dt<=0:raise ValueError("nonmonotonic trace")
        Eorig_trace+=dt*(a[1]+b[1])/2
        Epre+=dt*(a[2]+b[2])/2
    actual=float(charge_stage["heater_thermal_to_gas_J"])
    if actual<0 or abs(Eorig_trace-actual)>max(10.,max_ledger_disagreement*actual):
        raise ValueError("10s charge trace does not reproduce thermal energy ledger")
    # Upper bound is capped at original integrated heater heat:
    Epre=min(Epre,actual)
    Ebooster_thermal=actual-Epre
    Eboost_electric=Ebooster_thermal/resistance_efficiency
    Ehp_electric=Epre/hypothetical_hp_COP
    orig_electric=float(charge_stage["heater_electric_J"])
    if abs(orig_electric-actual/resistance_efficiency)>max(10.,1e-5*orig_electric):
        raise ValueError("base electric heater ledger disagrees with efficiency")
    return dict(
        thermal_heater_baseline_J=actual,
        baseline_electric_heater_J=orig_electric,
        upper_bound_HP_contribution_J=Epre,
        upper_bound_HP_fraction=Epre/actual if actual>0 else 0.,
        lower_bound_electric_booster_J=Eboost_electric,
        hypothetical_HP_compressor_electric_J=Ehp_electric,
        hypothetical_combined_electric_J=Eboost_electric+Ehp_electric,
        conditional_upper_bound_electric_saving_J=orig_electric-Eboost_electric-Ehp_electric,
        hypothetical_source_heat_J=Epre*(1.-1./hypothetical_hp_COP),
        sampling_ledger_relative_difference=abs(Eorig_trace-actual)/max(1.,actual),
        hp_peak_heat_W=max(z[2] for z in vals),
        required_gas_preheat_temperature_C=max_gas_K-273.15,
        hp_outlet_C=gas_hp_supply_C,
        COP_assumed_for_80C_source=hypothetical_hp_COP,
        no_HX_pinch_profile_or_pressure_drop_computed=True,
        first_law_internal_substitution_only=True,
        physically_qualified_saving=False,
        dynamic_HP_TES_coupling_validated=False)
