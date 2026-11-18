"""Regenerate the M3.6 dynamic counterflow 1MW process-water thermal study.

All figures are hypotheses, not engineering equipment ratings. The gas
bed outlet is coupled to an independent transient water/metal HX and an
uninstalled return-gas cooler or heater; no true physical plant exists.
"""
from __future__ import annotations

import argparse,hashlib,json
from dataclasses import asdict,replace
from pathlib import Path

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.coupled_transient_process_loop import (
    CoupledHXTrial,simulate_coupled_transient_hx,
)
from carnot_battery_lab.physics.transient_liquid_hx import (
    TransientHXAssumptions,eos_interpolation_check,
)


def defined_cases():
    base=CoupledHXTrial()
    hx=TransientHXAssumptions()
    return {
      "cold_start_40kW_K":(base,hx),
      "10min_warmup_40kW_K":(
         replace(base,name="warmup_600s_40kW_K",
                 hx_warmup_duration_s=600.),hx),
      "10min_warmup_UA_10kW_K":(
         replace(base,name="undersized_UA_10kW_K",
                 hx_warmup_duration_s=600.),
         replace(hx,installed_overall_UA_W_K=10_000.)),
      "10min_warmup_UA_40kW_K_half_wall_capacity":(
         replace(base,name="half_metal_capacity",
                 hx_warmup_duration_s=600.),
         replace(hx,wall_total_heat_capacity_J_K=500_000.)),
      "10min_warmup_UA_40kW_K_low_liquid_pressure":(
         replace(base,name="undersized_process_pressure",
                 hx_warmup_duration_s=600.),
         replace(hx,assumed_liquid_inlet_absolute_pressure_Pa=400_000.)),
    }


def compact(x):
    d=x["coupled_discharge_HX_energy"]
    tr=x["sampled_thermocouple_like_model_trace_NOT_observations"]
    first_service=next(v for v in tr if not v["warmup_not_counted_for_process"])
    last=tr[-1]
    return {
      "trial":x["trial"]["name"],
      "model_only_full_process_duration_pass":x[
          "model_only_thermal_duty_possible"],
      "model_1MW_grade_prefix_min":d[
          "sampled_model_thermal_grade_prefix_s"]/60.,
      "first_unqualified_overall_step":d["first_failed_total_step_index"],
      "first_service_liquid_water_outlet_end_C":
          first_service["HX_water_outlet_end_C"],
      "last_process_liquid_water_outlet_end_C":
          last["HX_water_outlet_end_C"],
      "last_process_gas_bed_mean_in_C":
          last["bed_exit_gas_inlet_mean_C"],
      "total_water_stream_heat_from_HX_GJ_signed":
          d["HX_liquid_boundary_heating_J_SIGNED"]/1e9,
      "uninstalled_gas_return_cooler_thermal_GJ":
          d["gas_cooler_thermal_energy_required_J_uninstalled"]/1e9,
      "uninstalled_gas_return_reheater_thermal_GJ":
          d["gas_reheater_thermal_energy_required_J_uninstalled"]/1e9,
      "unmeasured_HX_aux_electricity_kWh":
          d["HX_gas_and_liquid_pump_electricity_J_uncalibrated"]/3.6e6,
      "max_entire_HX_bed_return_first_law_error_J":
          abs(d["bed_HX_gas_cooler_system_first_law_residual_J"]),
      "physical_industrial_service_qualified":False,
    }


def study(*,with_mesh_time_check:bool=True):
    bed=GasRockBed(cells=16)
    cases={}
    rows=[]
    for name,(trial,hx) in defined_cases().items():
        try:
            r=simulate_coupled_transient_hx(bed,trial,hx)
            cases[name]=r
            rows.append({"name":name,"status":"MODEL_RUN_COMPLETE",
                         **compact(r)})
        except ValueError as exc:
            if (name!="10min_warmup_UA_40kW_K_low_liquid_pressure" or
                not any(phrase in str(exc) for phrase in (
                    "insufficient for 150C liquid","cannot keep 150C water liquid"))):
                # Never misclassify an unrelated solver or programming failure
                # as successful physical rejection by the water EOS gate.
                raise
            cases[name]={
               "research_stage":"M3_6_FAIL_CLOSED_WATER_PHASE_OR_INLET",
               "status":"BLOCKED_NONLIQUID_150C_WATER_AT_ASSUMED_PRESSURE",
               "error_type":type(exc).__name__,
               "qualification":False,
               "whole_architecture_RTE":None,
            }
            rows.append({"name":name,
                         "status":"BLOCKED_NONLIQUID_150C_WATER_AT_ASSUMED_PRESSURE",
                         "physical_industrial_service_qualified":False})
    convergence=None
    if with_mesh_time_check:
        trial,hx=defined_cases()["10min_warmup_40kW_K"]
        grid={}
        for cells,dt in ((4,120.),(8,120.),(12,120.),(16,120.),
                         (8,60.),(12,60.)):
            t=replace(trial,transient_step_s=dt)
            h=replace(hx,cells=cells)
            r=simulate_coupled_transient_hx(bed,t,h)
            last=r["sampled_thermocouple_like_model_trace_NOT_observations"][-1]
            grid[f"hxN{cells}_dt{int(dt)}"]={
                "hx_spatial_cells":cells,
                "coupled_discharge_step_s":dt,
                "water_outlet_last_C":last["HX_water_outlet_end_C"],
                "process_prefix_s":r["coupled_discharge_HX_energy"][
                    "sampled_model_thermal_grade_prefix_s"],
                "model_only_full_duration_pass":r[
                    "model_only_thermal_duty_possible"],
                "combined_bed_HX_return_first_law_residual_J":r[
                    "coupled_discharge_HX_energy"][
                    "bed_HX_gas_cooler_system_first_law_residual_J"],
            }
        # Independently change packed-bed spatial resolution while holding
        # downstream HX mesh, time step, source and process service fixed.
        # Crucial because M3.5 still has measurable bed-grid effects.
        bed32=replace(bed,cells=32)
        r_bed32=simulate_coupled_transient_hx(
            bed32,replace(trial,transient_step_s=120.),
            replace(hx,cells=8))
        bed32_end=r_bed32[
            "sampled_thermocouple_like_model_trace_NOT_observations"][-1][
            "HX_water_outlet_end_C"]
        convergence={
          "grid":grid,
          "N8_to_N12_last_water_outlet_abs_difference_K":abs(
              grid["hxN8_dt120"]["water_outlet_last_C"]-
              grid["hxN12_dt120"]["water_outlet_last_C"]),
          "N12_to_N16_last_water_outlet_abs_difference_K":abs(
              grid["hxN12_dt120"]["water_outlet_last_C"]-
              grid["hxN16_dt120"]["water_outlet_last_C"]),
          "dt120_to_dt60_at_N8_last_water_outlet_abs_difference_K":abs(
              grid["hxN8_dt120"]["water_outlet_last_C"]-
              grid["hxN8_dt60"]["water_outlet_last_C"]),
          "dt120_to_dt60_at_N12_last_water_outlet_abs_difference_K":abs(
              grid["hxN12_dt120"]["water_outlet_last_C"]-
              grid["hxN12_dt60"]["water_outlet_last_C"]),
          "bed_grid_comparison":{
              "bedN16_HXN8_dt120_final_water_C":grid[
                  "hxN8_dt120"]["water_outlet_last_C"],
              "bedN32_HXN8_dt120_final_water_C":bed32_end,
              "bedN16_to_bedN32_final_water_difference_K":abs(
                  grid["hxN8_dt120"]["water_outlet_last_C"]-
                  bed32_end),
              "bedN32_model_full_hour_sampled_gate":
                  r_bed32["model_only_thermal_duty_possible"],
              "physical_equipment_validation":False,
          },
          "absolute_mesh_and_timestep_independence_not_yet_proven":True,
          "no_experimental_validation":True,
          "between_step_gas_inlet_history_not_resolved":True,
        }
    return {
      "research_status":"M3_6_TRANSIENT_GAS_PROCESS_WATER_AND_HX_METAL",
      "model_only_not_measured":True,
      "evidence_class":"HYPOTHETICAL_ELECTRIC_GAS_CHARGE_EXACT_1MW_PROCESS_REQUEST",
      "assumed_source":"220C electric-heater-gas, not 80C-source heat pump",
      "bed_properties":asdict(bed),
      "declared_cases":{k:{"trial":asdict(t),"HX_assumptions":asdict(h)}
                        for k,(t,h) in defined_cases().items()},
      "assumption_sha256":hashlib.sha256(json.dumps({
          "bed":asdict(bed),
          "trials":{k:{"trial":asdict(t),"HX":asdict(h)}
             for k,(t,h) in defined_cases().items()},
          },sort_keys=True).encode()).hexdigest(),
      "cases":cases,
      "summary_model_only":rows,
      "hx_discretization_and_timestep_sensitivity":convergence,
      "water_eos_interpolation":eos_interpolation_check(),
      "actual_1MW_qualified_case_count":0,
      "actual_gas_cooling_equipment_available":False,
      "actual_process_HX_installed_and_rated":False,
      "actual_water_pressure_measured":False,
      "manufacturer_R718_R600_compressor_map_available":False,
      "original_experimental_packed_bed_validation":False,
      "entire_architecture_RTE":None,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,
                   default=Path("results/m3_6_dynamic_110_150C_water_HX_study.json"))
    p.add_argument("--skip-convergence",action="store_true")
    a=p.parse_args()
    r=study(with_mesh_time_check=not a.skip_convergence)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    for row in r["summary_model_only"]:
        print("M3_6_MODEL_CASE",row)
    if r["hx_discretization_and_timestep_sensitivity"]:
        print("M3_6_MODEL_SPATIAL_TIME_CHECK",
              r["hx_discretization_and_timestep_sensitivity"])
    print("M3_6_INPUT_ASSUMPTIONS_SHA256",r["assumption_sha256"])
    print("M3_6_PHYSICAL_QUALIFIED_PROCESS_CASES=0")
    print("M3_6_PHYSICAL_ARCHITECTURE_RTE=None")


if __name__=="__main__":main()
