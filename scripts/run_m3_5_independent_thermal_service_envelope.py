"""Reproducible M3.5 source-independent 1MW liquid thermal-service scan.

All temperatures/flows, ideal resistance heater, pressure and rock
properties are UNCALIBRATED assumptions, not supplier equipment evidence.
No architecture ranking, measured validation, or system RTE is computed.
"""
from __future__ import annotations

import argparse,json,hashlib
from dataclasses import asdict,replace
from pathlib import Path

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.independent_thermal_envelope import (
    IndependentThermalCase,study_envelope,simulate_independent_case,
)


def declared_scenarios()->tuple[IndependentThermalCase,...]:
    default=dict(
        charge_mass_flow_kg_s=25.,
        discharge_mass_flow_kg_s=15.,
        discharge_duration_s=3600.,
        integration_step_s=600.,
        initial_bed_C=95.,
        discharge_return_gas_C=110.,
        heater_max_electric_W=4_500_000.,
        assumed_resistance_efficiency=1.,
    )
    return (
        IndependentThermalCase(
            name="low_grade_150C_8h",charge_hot_gas_C=150.,
            charge_duration_s=28800.,**default),
        IndependentThermalCase(
            name="source_hotflow_180C_4h",charge_hot_gas_C=180.,
            charge_duration_s=14400.,**default),
        IndependentThermalCase(
            name="short_220C_4min",charge_hot_gas_C=220.,
            charge_duration_s=240.,**default),
        IndependentThermalCase(
            name="charge_220C_2h",charge_hot_gas_C=220.,
            charge_duration_s=7200.,**default),
        IndependentThermalCase(
            name="charge_220C_4h",charge_hot_gas_C=220.,
            charge_duration_s=14400.,**default),
        IndependentThermalCase(
            name="charge_260C_4h",charge_hot_gas_C=260.,
            charge_duration_s=14400.,**default),
        IndependentThermalCase(
            name="charge_260C_8h",charge_hot_gas_C=260.,
            charge_duration_s=28800.,**default),
        IndependentThermalCase(
            name="charge_260C_8h_high_discharge_flow",
            charge_hot_gas_C=260.,charge_duration_s=28800.,
            **{**default,"discharge_mass_flow_kg_s":25.}),
        IndependentThermalCase(
            name="charge_260C_8h_2h_delivery",
            charge_hot_gas_C=260.,charge_duration_s=28800.,
            **{**default,"discharge_duration_s":7200.}),
    )


def compact_run_result(r:dict)->dict:
    c=r["case"]
    o={
      "name":c["name"],
      "charge_gas_temperature_C_assumed":c["charge_hot_gas_C"],
      "charge_duration_h_assumed":c["charge_duration_s"]/3600.,
      "discharge_flow_kg_s_assumed":c["discharge_mass_flow_kg_s"],
      "requested_process_duration_h":c["discharge_duration_s"]/3600.,
      "actual_industrial_service_qualified":False,
      "sampled_nominal_process_thermal_gate":r[
          "nominal_full_duty_discharge_duration_screened"],
      "model_sampled_thermal_duty_prefix_minutes":r[
          "screened_full_duty_prefix_duration_s"]/60.,
      "status":r["status"],
      "blocker":r.get("blocker"),
      "source_bound_gate":r[
          "optimistic_max_hot_gas_source_temperature_hx_gate_pass"],
    }
    if r["charge_model_executed"]:
        a=r["charging"]
        d=r["discharge"]
        o.update({
            "model_thermal_heat_from_assumed_charge_gas_GJ":
                a["total_model_heat_put_into_bed_from_source_gas_J"]/1e9,
            "model_ideal_heater_input_electricity_MWh_UNVALIDATED":
                a["model_charge_heater_electricity_J_not_real_plant"]/3.6e9,
            "model_charge_blower_MWh_Ergun_UNCALIBRATED":
                a["model_charge_blower_electricity_J_Ergun_uncalibrated"]/3.6e9,
            "max_model_charge_Ergun_dP_kPa_UNCALIBRATED":
                a["max_predicted_Ergun_charge_bed_pressure_drop_Pa_uncalibrated"]/1e3,
            "max_model_discharge_Ergun_dP_kPa_UNCALIBRATED":
                d["model_discharge_max_bed_pressure_drop_Pa_Ergun_uncalibrated"]/1e3,
            "max_required_ideal_HX_UA_W_K_if_some_steps_possible":
                d["maximum_required_counterflow_UA_W_K_across_eligible_steps"],
            "maximum_additional_thermal_gas_cooler_W_needed_if_some_steps_pass":
                d["max_interval_mean_additional_gas_cooler_thermal_W_if_1MW"],
            "model_storage_first_law_full_cycle_residual_J":
                d["combined_storage_first_law_residual_J"],
            "first_failed_discharge_interval":
                d["first_failed_step_number"],
        })
    return o


def grid_audit(bed:GasRockBed,reference:IndependentThermalCase)->dict:
    """M3.5 diagnostic convergence, not measured/mesh-independent accuracy.

    Compare axial spatial N16,32,64 and step sizes 600/300 sec on SAME
    220C/4h/1h case without changing any plant conditions. A discontinuous
    0/1 service gate is not interpreted as an error norm; raw outlet
    temperatures, charging heat and energy residual are also compared.
    """
    samples={}
    configs=((16,600.),(32,600.),(64,600.),(32,300.))
    for n,dt in configs:
        b=replace(bed,cells=n)
        c=replace(reference,integration_step_s=dt)
        x=simulate_independent_case(b,c)
        if not x["charge_model_executed"]:
            raise RuntimeError("convergence reference unexpectedly preblocked")
        first=x["discharge"]["sampled_intervals"][0]
        last=x["discharge"]["sampled_intervals"][-1]
        samples[f"n{n}_dt{int(dt)}"]={
            "cells":n,"time_step_s":dt,
            "model_nominal_full_duty_thermal_gate":x[
                "nominal_full_duty_discharge_duration_screened"],
            "model_screened_full_power_prefix_s":x[
                "screened_full_duty_prefix_duration_s"],
            "first_reverse_discharge_gas_outlet_time_mean_C":
                first["outlet_gas_sample_C"]["time_mean"],
            "last_reverse_discharge_gas_outlet_final_C":
                last["outlet_gas_sample_C"]["final"],
            "actual_charge_thermal_input_J":x["charging"][
                "total_model_heat_put_into_bed_from_source_gas_J"],
            "max_charge_predicted_dP_Pa_uncalibrated":x["charging"][
                "max_predicted_Ergun_charge_bed_pressure_drop_Pa_uncalibrated"],
            "combined_first_law_residual_J":x["discharge"][
                "combined_storage_first_law_residual_J"],
        }
    a=samples["n32_dt600"]
    b=samples["n64_dt600"]
    t=samples["n32_dt300"]
    return {
      "sampled_mesh_time_diagnostic":samples,
      "n32_to_n64_absolute_last_discharge_outlet_difference_K":
          abs(a["last_reverse_discharge_gas_outlet_final_C"]-
              b["last_reverse_discharge_gas_outlet_final_C"]),
      "n32_dt600_to_dt300_last_discharge_outlet_difference_K":
          abs(a["last_reverse_discharge_gas_outlet_final_C"]-
              t["last_reverse_discharge_gas_outlet_final_C"]),
      "mesh_or_timestep_approximation_validated_against_measurements":False,
      "numerical_independence_globally_proven":False,
      "numerical_guard_for_using_close_to_threshold_rankings":
          "NOT_PROVEN; inspect individual outlet and prefix changes",
    }



def charge_duration_threshold_mesh_study(
    bed:GasRockBed,reference:IndependentThermalCase)->dict:
    """Find a discrete, model-only charging-time bracket, not plant minimum.

    We use the 220C charge source and 15kg/s discharge baseline. Whole-run
    first/mean/final thermal gates are evaluated for 1h at N16/N32/N64.
    Search a frozen 10-minute charge-time grid from 10 minutes to 4 hours.
    All source temperature, pressure uncertainty, model calibration and
    continuous-between-samples limitations remain in force.
    """
    step_s=600.
    limit_steps=24
    entries={}
    for cells in (16,32,64):
        b=replace(bed,cells=cells)
        memo={}
        def at(k:int)->dict:
            if k not in memo:
                c=replace(reference,charge_duration_s=k*step_s,
                          integration_step_s=step_s)
                memo[k]=simulate_independent_case(b,c)
            return memo[k]
        if at(limit_steps)["nominal_full_duty_discharge_duration_screened"]:
            lo,hi=0,limit_steps
            while hi-lo>1:
                mid=(lo+hi)//2
                if at(mid)["nominal_full_duty_discharge_duration_screened"]:
                    hi=mid
                else:
                    lo=mid
            # Check the adjacent grid bracket (not a continuous guarantee).
            candidate=at(hi)
            preceding=at(lo) if lo else None
            assert candidate["nominal_full_duty_discharge_duration_screened"]
            assert preceding is None or not preceding[
                "nominal_full_duty_discharge_duration_screened"]
            entries[f"cells_{cells}"]={
                "first_passing_declared_charge_duration_s":hi*step_s,
                "last_failing_declared_charge_duration_s":(
                    lo*step_s if lo else None),
                "threshold_is_sampled_10min_grid_not_actual_optimum":True,
                "first_passing_case_model_ideal_heater_MWh":candidate[
                    "charging"]["model_charge_heater_electricity_J_not_real_plant"]/3.6e9,
                "first_passing_model_source_gas_heat_GJ":candidate[
                    "charging"]["total_model_heat_put_into_bed_from_source_gas_J"]/1e9,
                "first_passing_discharge_prefix_duration_s":candidate[
                    "screened_full_duty_prefix_duration_s"],
                "number_of_simulated_durations_binary_search":len(memo),
                "synthetic_source_and_HX_hardware_not_qualified":True,
            }
        else:
            entries[f"cells_{cells}"]={
                "status":"NO_FULL_HOUR_SAMPLED_THERMAL_PASS_FOR_CHARGE_UP_TO_4H",
                "tested_max_charge_duration_s":limit_steps*step_s,
                "threshold_is_sampled_10min_grid_not_actual_optimum":True,
                "number_of_simulated_durations_binary_search":len(memo),
                "synthetic_source_and_HX_hardware_not_qualified":True,
            }
    return {
        "hypothesis":"220C_gas_charge_25kg_s_110C_return_15kg_s_discharge_1h",
        "charge_duration_grid_resolution_s":step_s,
        "results_by_axial_mesh":entries,
        "case_ordering_assumed_monotone_for_this_reduced_linear_model":True,
        "geometric_mesh_dependence_inferred_from_three_N_values":True,
        "continuous_time_heat_delivery_guarantee":False,
        "true_minimum_physical_charging_duration_established":False,
        "all_results_model_only_not_experimental":True,
    }


def run(*,with_grid_audit:bool=True)->dict:
    bed=GasRockBed(cells=16)
    assumptions=declared_scenarios()
    data=study_envelope(bed,assumptions)
    data["input_assumptions_sha256"]=hashlib.sha256(
        json.dumps({"bed":asdict(bed),
                    "cases":[asdict(c) for c in assumptions]},
                   sort_keys=True).encode()).hexdigest()
    data["summary_rows_NOT_EMPIRICAL"]=[
        compact_run_result(x) for x in data["cases"].values()]
    if with_grid_audit:
        reference=next(x for x in assumptions if x.name=="charge_220C_4h")
        data["grid_convergence_diagnostic"]=grid_audit(bed,reference)
        data["charge_duration_threshold_mesh_diagnostic"]=(
            charge_duration_threshold_mesh_study(bed,reference))
    else:
        data["grid_convergence_diagnostic"]=None
        data["charge_duration_threshold_mesh_diagnostic"]=None
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(
        "results/m3_5_independent_gas_charge_liquid_service_envelope.json"))
    parser.add_argument("--skip-convergence",action="store_true")
    args=parser.parse_args()
    x=run(with_grid_audit=not args.skip_convergence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
    for row in x["summary_rows_NOT_EMPIRICAL"]:
        print("M3_5_CASE",row)
    if x["grid_convergence_diagnostic"]:
        print("M3_5_DIAGNOSTIC_MESH_TIMESTEP",
              x["grid_convergence_diagnostic"])
        print("M3_5_MODEL_ONLY_CHARGE_DURATION_THRESHOLD_MESH",
              x["charge_duration_threshold_mesh_diagnostic"])
    print("M3_5_ASSUMPTION_SHA256",x["input_assumptions_sha256"])
    print("M3_5_MODEL_ONLY_POSSIBLE_SAMPLED_CASES",
          x["model_only_possible_thermal_grade_cases"])
    print("M3_5_ACTUAL_PROCESS_DELIVERY_QUALIFIED_CASES=[]")
    print("M3_5_ACTUAL_COMPRESSOR_MAP_REQUIRED=False")
    print("M3_5_VALIDATED_ROUND_TRIP_EFFICIENCY=None")


if __name__=="__main__":
    main()
