"""M3.7 *hypothetical* gas-bypass valve for exactly the original 1MW process water.

A physically mass-conserving HOT GAS BYPASS is upstream of the separate gas
heat exchanger: hot gas m_total is split into (f*m_total) through HX and
((1-f)*m_total) around it, then remixed before an *uninstalled* conditioner
that restores the specified 110 C bed return. Process WATER m_dot is unchanged
and is derived from original 110->150 C HEOS::Water enthalpy.

An ideal predictive, per-interval constant valve fraction is selected from
modelled mean water enthalpy duty. This is not a commissioned controller,
not a continuous temperature guarantee, and not an installed bypass/valve.
Failures cannot silently alter the contracted 1MW or give free hot inventory.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any
from .transient_liquid_hx import HXDynamicState,TransientHXAssumptions,advance_transient_hx


@dataclass(frozen=True)
class GasBypassControllerAssumptions:
    minimum_hx_gas_fraction:float=.10
    maximum_fraction_step_change:float=.40
    interval_mean_duty_target_W:float=1_000_000.
    permitted_interval_mean_duty_error_W:float=1_500.
    permitted_nodal_water_outlet_error_K:float=.5
    maximum_bisection_steps:int=13
    startup_full_flow_seconds:float=0.

    def __post_init__(self):
        props=(self.minimum_hx_gas_fraction,
               self.maximum_fraction_step_change,
               self.interval_mean_duty_target_W,
               self.permitted_interval_mean_duty_error_W,
               self.permitted_nodal_water_outlet_error_K)
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or
               not isfinite(x) or x<=0 for x in props):
            raise ValueError("invalid assumed gas bypass controller")
        if not self.minimum_hx_gas_fraction<1:
            raise ValueError("minimum through-HX gas fraction must be less than 1")
        if self.maximum_fraction_step_change>1:
            raise ValueError("actuator fraction slew > 1 in one interval")
        if not isinstance(self.maximum_bisection_steps,int) or not 2<=self.maximum_bisection_steps<=30:
            raise ValueError("invalid bisection budget")
        if (isinstance(self.startup_full_flow_seconds,bool)
            or not isinstance(self.startup_full_flow_seconds,(int,float))
            or not isfinite(self.startup_full_flow_seconds)
            or self.startup_full_flow_seconds<0):
            raise ValueError("invalid nonnegative full-flow startup period")


def advance_hx_with_predictive_gas_bypass(
    settings:GasBypassControllerAssumptions,
    hx:TransientHXAssumptions,state:HXDynamicState,*,
    hot_gas_inlet_mean_K:float,gas_total_mass_flow_kg_s:float,
    gas_cp_J_kgK:float,gas_density_kg_m3:float,
    water_mass_flow_kg_s:float,water_inlet_K:float,dt_s:float,
    previous_gas_through_fraction:float=1.,
    required_supply_K:float=423.15,
    elapsed_discharge_time_s:float=0.,
)->dict:
    if not (isfinite(previous_gas_through_fraction) and
            settings.minimum_hx_gas_fraction<=previous_gas_through_fraction<=1):
        raise ValueError("invalid previous gas bypass command")
    if abs(settings.interval_mean_duty_target_W-1e6)>1e-9 or abs(required_supply_K-423.15)>1e-9:
        raise ValueError("M3.7 controller cannot change exact original 1MW/150C contract")

    base={"a":hx,"state":state,"gas_inlet_mean_K":hot_gas_inlet_mean_K,
          "gas_cp_J_kgK":gas_cp_J_kgK,
          "gas_density_kg_m3":gas_density_kg_m3,
          "water_flow_kg_s":water_mass_flow_kg_s,
          "water_inlet_K":water_inlet_K,"dt_s":dt_s,
          "required_water_supply_K":required_supply_K}
    trials={}
    def test(fraction:float):
        k=round(fraction,14)
        if k not in trials:
            trials[k]=advance_transient_hx(
                **base,gas_flow_kg_s=gas_total_mass_flow_kg_s*fraction)
        return trials[k]

    if not isinstance(elapsed_discharge_time_s,(int,float)) or (
        not isfinite(elapsed_discharge_time_s) or elapsed_discharge_time_s<0):
        raise ValueError("nonnegative elapsed discharge time required")
    startup_hold=elapsed_discharge_time_s<settings.startup_full_flow_seconds
    if startup_hold:
        full=test(1.)
        achieved=full["water_outlet_flow_average_heat_W"]
        min_kelvin=full[
            "minimum_water_outlet_temperature_K_at_numerical_solver_nodes"]
        max_kelvin=full[
            "maximum_water_outlet_temperature_K_at_numerical_solver_nodes"]
        return {
          "model_only_gas_bypass_control_status":
              "STARTUP_FULL_HOT_GAS_FLOW_NO_PROCESS_CREDIT",
          "hx_step":full,
          "requested_through_hx_gas_fraction":1.,
          "selected_through_hx_gas_fraction":1.,
          "model_gas_bypass_fraction":0.,
          "through_hx_gas_mass_flow_kg_s":gas_total_mass_flow_kg_s,
          "bypassed_gas_mass_flow_kg_s":0.,
          "gas_mass_balance_residual_kg_s":0.,
          "valve_slew_rate_limited":False,
          "sampled_gas_fraction_to_duty_monotone":None,
          "trial_q_at_min_fraction_W":None,
          "trial_q_at_full_fraction_W":achieved,
          "interval_water_enthalpy_heating_W":achieved,
          "interval_mean_thermal_duty_error_W":(
              achieved-settings.interval_mean_duty_target_W),
          "within_mean_heat_control_tolerance":False,
          "min_accepted_node_water_outlet_C":min_kelvin-273.15,
          "max_accepted_node_water_outlet_C":max_kelvin-273.15,
          "all_accepted_nodes_within_hypothetical_water_setpoint_band":False,
          "model_only_interval_nominal_150C_control_gate":False,
          "number_of_ODE_trial_solves_including_monotonicity":1,
          "real_valve_and_control_equipment_qualified":False,
          "true_continuous_150C_control_certified":False,
          "actual_1MW_process_water_delivered_qualified":False,
        }
    minimum=settings.minimum_hx_gas_fraction
    # Monotonicity isn't a consequence of the finite-time three-inventory HX
    # model in every possible state. Independently sample the entire valve
    # range before trusting a binary search.
    fractions=[minimum+(1-minimum)*i/4 for i in range(5)]
    values=[test(f)["water_outlet_flow_average_heat_W"] for f in fractions]
    monotone=all(b>=a-1e-6*settings.interval_mean_duty_target_W
                 for a,b in zip(values,values[1:]))
    target=settings.interval_mean_duty_target_W
    if not monotone:
        requested=1.
        status="NONMONOTONE_DYNAMIC_HX_DUTY_VS_GAS_FRACTION"
    elif values[-1]<target:
        requested=1.
        status="INSUFFICIENT_THERMAL_DUTY_AT_FULL_HX_GAS_FLOW"
    elif values[0]>target:
        requested=minimum
        status="MINIMUM_HX_GAS_FLOW_STILL_OVERDELIVERS"
    else:
        low=minimum
        high=1.
        for _ in range(settings.maximum_bisection_steps):
            mid=(low+high)/2.
            value=test(mid)["water_outlet_flow_average_heat_W"]
            if value<target:low=mid
            else:high=mid
        requested=(low+high)/2.
        status="MODEL_BISECTION_REQUEST_WITHIN_THERMAL_BRACKET"

    # Valve slew constraint may prevent following the target, even in a
    # static feasible thermal envelope. Do not discard actuator dynamics.
    lower=max(minimum,previous_gas_through_fraction-
              settings.maximum_fraction_step_change)
    upper=min(1.,previous_gas_through_fraction+
              settings.maximum_fraction_step_change)
    selected=min(max(requested,lower),upper)
    actuator_limited=abs(selected-requested)>1e-12
    result=test(selected)
    achieved=result["water_outlet_flow_average_heat_W"]
    # Original process water is UNBYPASSED. Exactly the same water flow goes
    # through the HX, so interval mean water duty is its actual enthalpy flow.
    deviation=achieved-target
    min_kelvin=result[
        "minimum_water_outlet_temperature_K_at_numerical_solver_nodes"]
    max_kelvin=result["maximum_water_outlet_temperature_K_at_numerical_solver_nodes"]
    # The water mass flow was derived using h(110C)->h(150C), so the
    # instantaneous 150C setpoint should NOT be inferred from mean enthalpy
    # alone. Explicitly require all accepted nodal 150 +/- stated band.
    node_within_band=(min_kelvin>=required_supply_K-
                      settings.permitted_nodal_water_outlet_error_K
                      and max_kelvin<=required_supply_K+
                      settings.permitted_nodal_water_outlet_error_K)
    mean_on_target=abs(deviation)<=settings.permitted_interval_mean_duty_error_W
    result_ok=(bool(mean_on_target and node_within_band and not actuator_limited
                    and monotone and result["assumed_hx_pressure_pump_audit"][
                        "assumed_model_liquid_single_phase"]
                    and result["minimum_gas_minus_water_local_nodal_difference_K"]>=5.))
    return {
      "model_only_gas_bypass_control_status":status,
      "hx_step":result,
      "requested_through_hx_gas_fraction":requested,
      "selected_through_hx_gas_fraction":selected,
      "model_gas_bypass_fraction":1.-selected,
      "through_hx_gas_mass_flow_kg_s":selected*gas_total_mass_flow_kg_s,
      "bypassed_gas_mass_flow_kg_s":(1.-selected)*gas_total_mass_flow_kg_s,
      "gas_mass_balance_residual_kg_s":(
         selected*gas_total_mass_flow_kg_s+
         (1.-selected)*gas_total_mass_flow_kg_s-gas_total_mass_flow_kg_s),
      "valve_slew_rate_limited":actuator_limited,
      "sampled_gas_fraction_to_duty_monotone":monotone,
      "trial_q_at_min_fraction_W":values[0],
      "trial_q_at_full_fraction_W":values[-1],
      "interval_water_enthalpy_heating_W":achieved,
      "interval_mean_thermal_duty_error_W":deviation,
      "within_mean_heat_control_tolerance":bool(mean_on_target),
      "min_accepted_node_water_outlet_C":min_kelvin-273.15,
      "max_accepted_node_water_outlet_C":max_kelvin-273.15,
      "all_accepted_nodes_within_hypothetical_water_setpoint_band":node_within_band,
      "model_only_interval_nominal_150C_control_gate":result_ok,
      "number_of_ODE_trial_solves_including_monotonicity":len(trials),
      "real_valve_and_control_equipment_qualified":False,
      "true_continuous_150C_control_certified":False,
      "actual_1MW_process_water_delivered_qualified":False,
    }
