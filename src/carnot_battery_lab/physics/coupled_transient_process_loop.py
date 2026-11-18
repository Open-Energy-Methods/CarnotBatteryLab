"""M3.6 coupled source-independent packed-bed -> transient HX -> gas return.

SOURCE heater hot gas is assumed: NOT a verified 80C waste-heat R718/R600
machine. Process liquid is a completely separate pressurised stream.
The outlet bed hot-gas step AVERAGE feeds the transient finite-volume HX
for the same 60s interval, preserving integrated gas input energy but NOT a
continuous exact inlet T(t). A return cooler/heater is a calculated thermal
load, NOT an installed component. No physical 1MW or RTE is qualified.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass,replace
from math import isfinite
from typing import Sequence

from .gas_rock_regenerator import GasRockBed,BedState,advance_bed,bed_energy_J
from .reverse_flow_discharge import advance_reverse_discharge
from .liquid_process_hx_gate import ProcessLiquidHXContract
from .independent_thermal_envelope import IndependentThermalCase,_steps,_hydraulic_re
from .transient_liquid_hx import (
    HXDynamicState,TransientHXAssumptions,advance_transient_hx,
    eos_interpolation_check,
)


@dataclass(frozen=True)
class CoupledHXTrial:
    name:str="baseline_assumed_40kW_K_start_cold"
    charge_gas_inlet_C:float=220.
    charge_flow_kg_s:float=25.
    charge_duration_s:float=7200.
    charge_step_s:float=600.
    discharge_gas_mass_flow_kg_s:float=15.
    process_duration_s:float=3600.
    transient_step_s:float=60.
    hx_warmup_duration_s:float=0.
    discharge_gas_return_C:float=110.
    initial_bed_C:float=95.
    heater_max_W:float=4_500_000.
    max_num_steps:int=240

    def __post_init__(self):
        if not isinstance(self.name,str) or not self.name:
            raise ValueError("case name required")
        for k in ("charge_flow_kg_s","charge_duration_s","charge_step_s",
                  "discharge_gas_mass_flow_kg_s","process_duration_s",
                  "transient_step_s","heater_max_W"):
            v=getattr(self,k)
            if isinstance(v,bool) or not isfinite(v) or v<=0:
                raise ValueError("invalid coupled trial positive parameter")
        if not isfinite(self.hx_warmup_duration_s) or self.hx_warmup_duration_s<0:
            raise ValueError("negative warmup")
        if any(not isfinite(v) or v<=-273.15 for v in (
            self.charge_gas_inlet_C,self.discharge_gas_return_C,self.initial_bed_C)):
            raise ValueError("invalid coupled temperatures")
        if self.charge_gas_inlet_C<=self.initial_bed_C:
            raise ValueError("source temperature too low for initial charging")
        for duration,step in ((self.process_duration_s+self.hx_warmup_duration_s,
                               self.transient_step_s),
                              (self.charge_duration_s,self.charge_step_s)):
            if duration/step>self.max_num_steps:
                raise ValueError("overlong reproducibility time grid")
        if (self.hx_warmup_duration_s/self.transient_step_s)%1>1e-8:
            raise ValueError("warmup must be multiple of HX step")
        if (self.process_duration_s/self.transient_step_s)%1>1e-8:
            raise ValueError("contract duration must be multiple of HX step")


def simulate_coupled_transient_hx(
    bed:GasRockBed,trial:CoupledHXTrial,
    hx:TransientHXAssumptions=TransientHXAssumptions(),*,
    requested_process:ProcessLiquidHXContract=ProcessLiquidHXContract(),
)->dict:
    if (requested_process.thermal_duty_W!=1e6 or
        requested_process.liquid_return_C!=110. or
        requested_process.liquid_supply_C!=150. or
        requested_process.liquid_absolute_pressure_Pa is not None or
        requested_process.installed_UA_W_K is not None):
        raise ValueError("contract is 1MW/110->150C; all real installed equipment unknown")
    if (trial.charge_gas_inlet_C<155. or
        not (15<=_hydraulic_re(bed,trial.charge_flow_kg_s)<=8500) or
        not (15<=_hydraulic_re(
            bed,trial.discharge_gas_mass_flow_kg_s)<=8500)):
        raise ValueError("source grade or Wakao Re unqualified")
    initial=BedState.uniform(bed,trial.initial_bed_C)
    state=initial
    target_gas_K=trial.charge_gas_inlet_C+273.15
    return_gas_K=trial.discharge_gas_return_C+273.15
    first_heater_W=(
        trial.charge_flow_kg_s*bed.gas_cp_J_kgK*
        (target_gas_K-state.fluid_temperature_K[-1]))
    if first_heater_W>trial.heater_max_W:
        raise ValueError("assumed electrical heater peak limit exceeded")
    initial_bed_J=bed_energy_J(bed,initial)
    charge_gas_heat=0.;charge_wall=0.;charge_blower=0.
    charge_dP=0.;max_charge_step_residual=0.
    for dt in _steps(trial.charge_duration_s,trial.charge_step_s):
        r=advance_bed(bed,state,inlet_K=target_gas_K,
                      mass_flow_kg_s=trial.charge_flow_kg_s,dt_s=dt)
        state=r.final_state
        charge_gas_heat+=r.heat_from_hot_gas_J
        charge_wall+=r.heat_loss_to_ambient_J
        charge_blower+=r.blower_electric_W*dt
        charge_dP=max(charge_dP,r.pressure_drop_Pa)
        max_charge_step_residual=max(max_charge_step_residual,
                                     abs(r.energy_residual_J))
    charged_bed_J=bed_energy_J(bed,state)
    charge_residual=charged_bed_J-initial_bed_J-charge_gas_heat+charge_wall
    if abs(charge_residual)>1e-5*max(1.,abs(charge_gas_heat)):
        raise RuntimeError("coupled dynamic HX initial source heat ledger inconsistent")
    pre_hx=HXDynamicState.initial(hx)
    s_hx=pre_hx
    water_flow=requested_process.process_liquid_mass_flow_kg_s
    water_inlet_K=requested_process.liquid_return_C+273.15
    minimum_grade_K=requested_process.liquid_supply_C+273.15
    bed_gas_heat=0.;bed_wall=0.;bed_blower=0.
    hx_gas_input_boundary=0.;hx_water_out=0.;hx_cooler=0.
    hx_conditioning_heater=0.;hx_pump_and_fan=0.
    gas_holdup=0.;liq_holdup=0.;wall_holdup=0.
    raw_errors=[]
    rows=[]
    prefix_s=0.;prefix_open=True;first_failed=None
    preheat_water_energy=0.
    delivered_nominal_qualified_J=0.  # ALWAYS 0, physical plant not validated
    warmup_intervals=int(round(trial.hx_warmup_duration_s/trial.transient_step_s))
    for i,dt in enumerate(_steps(
        trial.process_duration_s+trial.hx_warmup_duration_s,
        trial.transient_step_s)):
        step=advance_reverse_discharge(
            bed,state,return_gas_K=return_gas_K,
            mass_flow_kg_s=trial.discharge_gas_mass_flow_kg_s,
            dt_s=dt,minimum_process_delivery_K=minimum_grade_K)
        state=step.final_state
        hot_from_bed_mean_K=step.time_mean_outlet_K
        # Even the original packed-bed model may have time-varying output
        # WITHIN the step; only energy-matched mean is passed here.
        h=advance_transient_hx(
            hx,s_hx,gas_inlet_mean_K=hot_from_bed_mean_K,
            gas_flow_kg_s=trial.discharge_gas_mass_flow_kg_s,
            gas_cp_J_kgK=bed.gas_cp_J_kgK,
            gas_density_kg_m3=bed.gas_density_kg_m3,
            water_flow_kg_s=water_flow,
            water_inlet_K=water_inlet_K,dt_s=dt,
            required_water_supply_K=minimum_grade_K,
            minimum_local_gas_liquid_approach_K=
                requested_process.minimum_internal_approach_K)
        s_hx=h["state"]
        # Return gas thermal correction is derived using the HX actual
        # time-AVERAGED outlet enthalpy, not its end instantaneous state.
        mcp=trial.discharge_gas_mass_flow_kg_s*bed.gas_cp_J_kgK
        gas_out_mean=hot_from_bed_mean_K-h[
            "net_boundary_gas_heat_into_HX_J"]/(mcp*dt)
        conditioner_signed=mcp*dt*(gas_out_mean-return_gas_K)
        if conditioner_signed>=0:
            hx_cooler+=conditioner_signed
        else:
            hx_conditioning_heater+=-conditioner_signed
        gas_return_residual=(step.signed_heat_to_process_gas_J-
                             h["net_boundary_gas_heat_into_HX_J"]-
                             conditioner_signed)
        if abs(gas_return_residual)>1e-5*max(
            1.,abs(step.signed_heat_to_process_gas_J),
            abs(h["net_boundary_gas_heat_into_HX_J"])):
            raise RuntimeError("gas conditioner return-loop first-law failure")
        bed_gas_heat+=step.signed_heat_to_process_gas_J
        bed_wall+=step.ambient_loss_J
        bed_blower+=step.fan_electric_J_model
        hx_gas_input_boundary+=h["net_boundary_gas_heat_into_HX_J"]
        hx_water_out+=h["net_boundary_liquid_heat_from_HX_J"]
        hx_pump_and_fan+=dt*(h["assumed_hx_pressure_pump_audit"][
            "assumed_gas_hx_circulator_electric_W_uncalibrated"]+
            h["assumed_hx_pressure_pump_audit"][
            "assumed_liquid_hx_pump_electric_W_uncalibrated"])
        gas_holdup+=h["gas_holdup_change_J"]
        liq_holdup+=h["water_enthalpy_holdup_change_J"]
        wall_holdup+=h["wall_holdup_change_J"]
        raw_errors.append(max(abs(h[x]) for x in (
            "independent_gas_energy_residual_J",
            "independent_water_energy_residual_J",
            "independent_wall_energy_residual_J",
            "overall_HX_energy_residual_J")))
        is_warmup=i<warmup_intervals
        if is_warmup:
            preheat_water_energy+=h["net_boundary_liquid_heat_from_HX_J"]
        else:
            ok=h["model_nominal_water_supply_and_1MW_in_step"]
            if prefix_open and ok:
                prefix_s+=dt
            else:
                prefix_open=False
                if first_failed is None:first_failed=i+1
        rows.append({
          "time_end_s":(i+1)*dt,
          "warmup_not_counted_for_process":is_warmup,
          "bed_exit_gas_inlet_mean_C":hot_from_bed_mean_K-273.15,
          "HX_gas_outlet_time_average_C":gas_out_mean-273.15,
          "HX_water_outlet_start_C":h["water_outlet_start_K"]-273.15,
          "HX_water_outlet_end_C":h["water_outlet_end_K"]-273.15,
          "water_outlet_interval_mean_thermal_W":
              h["water_outlet_flow_average_heat_W"],
          "minimum_nodal_gas_minus_liquid_approach_K":
              h["minimum_gas_minus_water_local_nodal_difference_K"],
          "assumed_liquid_single_phase":h["assumed_hx_pressure_pump_audit"][
              "assumed_model_liquid_single_phase"],
          "sampled_model_exact_1MW_grade_screen":h[
              "model_nominal_water_supply_and_1MW_in_step"],
          "gas_return_cooler_thermal_J_if_positive":
              max(0.,conditioner_signed),
          "gas_return_reheater_thermal_J_if_negative":
              max(0.,-conditioner_signed),
          "gas_hx_bed_return_ledger_residual_J":gas_return_residual,
          "hx_water_boundary_heat_J":h["net_boundary_liquid_heat_from_HX_J"],
          "hx_total_first_law_residual_J":h["overall_HX_energy_residual_J"],
        })
    total_bed_end_J=bed_energy_J(bed,state)
    bed_discharge_residual=total_bed_end_J-charged_bed_J+bed_gas_heat+bed_wall
    # Do not confuse individually signed cooling and reheating: conditioner
    # net heat removal is Qcooler-Qreheater, NOT Qcooler+Qreheater.
    system_residual=(total_bed_end_J-charged_bed_J+
                     gas_holdup+liq_holdup+wall_holdup+
                     bed_wall+hx_water_out+hx_cooler-hx_conditioning_heater)
    scale=max(1.,abs(bed_gas_heat),abs(hx_water_out),
              abs(charged_bed_J-total_bed_end_J))
    if abs(bed_discharge_residual)>1e-5*scale or abs(system_residual)>1e-5*scale:
        raise RuntimeError("bed/HX/gas conditioner combined first-law failure")
    pass_one_hour=(abs(prefix_s-trial.process_duration_s)<1e-7)
    return {
      "research_stage":"M3_6_DYNAMIC_FINITE_VOLUME_GAS_TO_LIQUID_PROCESS_HX",
      "trial":asdict(trial),
      "assumed_packed_bed":asdict(bed),
      "assumed_HX_equipment_not_vendor_or_measured":asdict(hx),
      "original_1MW_liquid_contract": {
          "required_liquid_return_C":110.,
          "required_liquid_supply_C":150.,
          "required_thermal_W":1.e6,
          "derived_process_liquid_flow_kg_s":water_flow,
          "installed_HX_UA_or_liquid_pressure_measured":False,
      },
      "charging": {
          "model_charging_heat_J":charge_gas_heat,
          "assumed_ideal_resistance_heater_electricity_J":
              charge_gas_heat,
          "model_charge_blower_electricity_J":charge_blower,
          "charge_start_bed_energy_J":initial_bed_J,
          "charge_end_bed_energy_J":charged_bed_J,
          "charge_wall_loss_J":charge_wall,
          "charge_first_law_residual_J":charge_residual,
          "max_step_first_law_residual_J":max_charge_step_residual,
          "max_uncalibrated_bed_Ergun_pressure_drop_Pa":charge_dP,
      },
      "coupled_discharge_HX_energy": {
          "bed_integrated_heat_to_gas_J":bed_gas_heat,
          "bed_wall_loss_J":bed_wall,
          "bed_blower_electricity_J_Ergun_unvalidated":bed_blower,
          "HX_gas_boundary_energy_J":hx_gas_input_boundary,
          "HX_liquid_boundary_heating_J_SIGNED":hx_water_out,
          "warmup_liquid_energy_NOT_counted_as_process_J":
              preheat_water_energy,
          "gas_cooler_thermal_energy_required_J_uninstalled":hx_cooler,
          "gas_reheater_thermal_energy_required_J_uninstalled":
              hx_conditioning_heater,
          "HX_gas_and_liquid_pump_electricity_J_uncalibrated":
              hx_pump_and_fan,
          "HX_gas_holdup_change_J":gas_holdup,
          "HX_liquid_enthalpy_holdup_change_J":liq_holdup,
          "HX_wall_holdup_change_J":wall_holdup,
          "HX_max_single_step_phase_energy_error_J":max(raw_errors),
          "bed_discharge_first_law_residual_J":bed_discharge_residual,
          "bed_HX_gas_cooler_system_first_law_residual_J":system_residual,
          "sampled_model_grade_necessary_full_duration":pass_one_hour,
          "sampled_model_thermal_grade_prefix_s":prefix_s,
          "first_failed_total_step_index":first_failed,
          "sampled_true_continuous_grade_proven":False,
          "qualified_real_1MW_process_water_J":0.,
          "actual_installed_UA_and_water_pressure_known":False,
      },
      "sampled_thermocouple_like_model_trace_NOT_observations":rows,
      "water_EOS_direct_verification":eos_interpolation_check(
          pressure_Pa=hx.assumed_liquid_inlet_absolute_pressure_Pa),
      "model_only_thermal_duty_possible":pass_one_hour,
      "real_process_water_HX_qualified":False,
      "real_electric_charge_hardware_qualified":False,
      "coupled_external_80_to_70C_waste_heat_source_validated":False,
      "packed_bed_breakthrough_and_pressure_loss_validated":False,
      "source_gas_absolute_pressure_measured":False,
      "whole_architecture_RTE":None,
      "physical_energy_service_qualified":False,
    }
