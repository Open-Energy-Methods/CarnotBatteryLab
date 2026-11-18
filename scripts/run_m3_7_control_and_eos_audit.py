"""M3.7 precise process water valve control and gas EOS sensitivity audit.

Source-independent 220C heater-only hypothetical charge, original 1MW liquid.
Strictly no actual heat-pump compressor, installed water HX, bypass actuator,
gas pressure, packed bed measurement or electrical RTE qualification.
"""
from __future__ import annotations
import argparse,hashlib,json
from dataclasses import asdict,replace
from pathlib import Path

from carnot_battery_lab.physics.air_eos_sensitivity import (
    air_gas_loop_property_sensitivity,
)
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.transient_liquid_hx import (
    TransientHXAssumptions,
)
from carnot_battery_lab.physics.coupled_transient_process_loop import (
    CoupledHXTrial,simulate_coupled_transient_hx,
)
from carnot_battery_lab.physics.process_gas_bypass_control import (
    GasBypassControllerAssumptions,
)


def _summarize_case(r):
    rows=r["sampled_thermocouple_like_model_trace_NOT_observations"]
    process=[x for x in rows if not x["warmup_not_counted_for_process"]]
    control=r["model_only_hypothetical_gas_bypass_control"]
    return {
      "model_sampled_1MW_150C_controller_full_service_gate":
          r["model_only_thermal_duty_possible"],
      "process_minutes_requested":r["trial"]["process_duration_s"]/60.,
      "model_controlled_enthalpy_and_water_temperature_band_prefix_min":
          r["coupled_discharge_HX_energy"][
              "sampled_model_thermal_grade_prefix_s"]/60.,
      "first_failed_overall_step":
          r["coupled_discharge_HX_energy"]["first_failed_total_step_index"],
      "process_last_water_temperature_C":
          process[-1]["HX_water_outlet_end_C"],
      "process_min_accepted_node_water_C":
          min(x["HX_water_outlet_minimum_accepted_node_C"]
              for x in process),
      "process_max_interval_mean_duty_abs_error_W":
          max(abs(x["water_outlet_interval_mean_thermal_W"]-1e6)
              for x in process),
      "model_thermal_return_cooler_J_uninstalled":
          r["coupled_discharge_HX_energy"][
              "gas_cooler_thermal_energy_required_J_uninstalled"],
      "model_bed_HX_cooler_first_law_residual_J":r[
          "coupled_discharge_HX_energy"][
              "bed_HX_gas_cooler_system_first_law_residual_J"],
      "number_of_controlled_steps_within_band":control[
          "steps_with_nodal_150C_band_and_mean_1MW"],
      "number_of_controlled_steps_failing_band":control[
          "steps_outside_control_band_or_limited"],
      "real_valve_or_industrial_heat_certified":False,
    }


def _mesh_grid(*,rapid:bool):
    bed=GasRockBed(cells=16)
    hx=TransientHXAssumptions(cells=8)
    trial=CoupledHXTrial(
        name="numerical_ref_2h_charge_10min_warmup_1h_delivery",
        hx_warmup_duration_s=600.,process_duration_s=600. if rapid else 3600.,
        transient_step_s=60.)
    # Re-run spatial and coupling changes separately; all physical boundary
    # inputs, water EOS and HX equipment assumptions remain identical.
    configs=(
        (16,8,60.),(16,12,60.),(16,16,60.),
        (32,8,60.),(64,8,60.),
        (16,8,30.),(32,12,60.),
    ) if not rapid else (
        (16,8,60.),(16,12,60.),(32,8,60.))
    result={}
    for nbed,nhx,dt in configs:
        newbed=replace(bed,cells=nbed)
        newhx=replace(hx,cells=nhx)
        newtrial=replace(trial,transient_step_s=dt)
        r=simulate_coupled_transient_hx(newbed,newtrial,newhx)
        final=r["sampled_thermocouple_like_model_trace_NOT_observations"][-1]
        result[f"bed{nbed}_hx{nhx}_dt{int(dt)}"]={
            "bed_cells":nbed,"HX_cells":nhx,
            "coupling_step_s":dt,
            "final_water_outlet_C":final["HX_water_outlet_end_C"],
            "model_full_process_sampled_pass":r[
                "model_only_thermal_duty_possible"],
            "combined_energy_residual_J":r[
                "coupled_discharge_HX_energy"][
                    "bed_HX_gas_cooler_system_first_law_residual_J"],
        }
    def diff(a,b):
        return abs(result[a]["final_water_outlet_C"]-
                   result[b]["final_water_outlet_C"])
    detailed=({
       "HX_N8_to_N12_K":diff("bed16_hx8_dt60","bed16_hx12_dt60"),
       "HX_N12_to_N16_K":diff("bed16_hx12_dt60","bed16_hx16_dt60"),
       "bed_N16_to_N32_K":diff("bed16_hx8_dt60","bed32_hx8_dt60"),
       "bed_N32_to_N64_K":diff("bed32_hx8_dt60","bed64_hx8_dt60"),
       "dt60_to_dt30_K":diff("bed16_hx8_dt60","bed16_hx8_dt30"),
       "bed32_HX12_mixed_grid_reference":result["bed32_hx12_dt60"],
    } if not rapid else {})
    return {
        "numerical_results_same_physical_hypothesis":result,
        "separate_finite_volume_sensitivity_deltas":detailed,
        "original_contract_not_changed":True,
        "experimentally_confirmed_mesh_independence":False,
        "actual_continuous_temperature_trace_validated":False,
        "numerical_design_threshold_and_mesh_robustness_not_established":True,
    }


def study(*,rapid=False):
    control=GasBypassControllerAssumptions()
    hx=TransientHXAssumptions(cells=8)
    bed=GasRockBed(cells=16)
    baseline=CoupledHXTrial(
        name="M3_7_hypothetical_bypass_150C_controller",
        hx_warmup_duration_s=600.,
        process_duration_s=600. if rapid else 3600.,
        transient_step_s=60.)
    controlled=simulate_coupled_transient_hx(
        bed,baseline,hx,gas_bypass_controller=control)
    result={
      "research_stage":"M3_7_CONTROL_EOS_DIAGNOSTIC_AND_CONVERGENCE",
      "original_thermal_contract":"1MW_exact_enthalpy_water_110_to_150C",
      "heat_source":"assumed_220C_electric_hot_gas_not_real_80C_waste_heat_pump",
      "model_control_assumptions":asdict(control),
      "model_coupled_trial":asdict(baseline),
      "model_installed_HX_is_only_assumed":asdict(hx),
      "model_1MW_150C_process_control":{
        "model_result":controlled,
        "summary":_summarize_case(controlled),
      },
      "gas_thermophysical_EOS_variation_NOT_coupled":
          air_gas_loop_property_sensitivity(bed),
      "gas_bed_HX_constant_cp_density_model_still_requires_EOS_refactor":True,
      "numerical_mesh_coupling_and_time_sensitivity":
          _mesh_grid(rapid=rapid),
      "original_M2_2_independent_experimental_holdout_available":False,
      "published_Mendeley_Weber_data_Doi":"10.17632/3pp86gdvh4.2",
      "original_source_download_and_thermocouple_validation_NOT_done":True,
      "real_control_hardware_and_valve_ratings_known":False,
      "actual_installed_water_HX_UA_known":False,
      "actual_gas_pressure_known":False,
      "manufacturer_R718_R600_compressor_qualified":False,
      "validated_process_liquid_delivery_J":0.,
      "Carnot_battery_RTE":None,
    }
    result["assumption_sha256"]=hashlib.sha256(json.dumps({
       "bed":asdict(bed),"hx":asdict(hx),
       "trial":asdict(baseline),"control":asdict(control),
    },sort_keys=True).encode()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path(
        "results/m3_7_bypass_control_air_EOS_and_convergence.json"))
    p.add_argument("--rapid",action="store_true")
    a=p.parse_args()
    x=study(rapid=a.rapid)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
    print("M3_7_IDEAL_GAS_BYPASS_CONTROL",
          x["model_1MW_150C_process_control"]["summary"])
    rr=x["model_1MW_150C_process_control"]["model_result"][
        "sampled_thermocouple_like_model_trace_NOT_observations"]
    for phase in ("warmup","process"):
        selected=[q for q in rr if q["warmup_not_counted_for_process"]==
                  (phase=="warmup")]
        for idx in sorted(set([0,1,2,len(selected)//2,len(selected)-2,len(selected)-1])):
            if 0<=idx<len(selected):
                item=selected[idx]
                print("M3_7_CONTROLLER_TRAJECTORY",phase,idx,{
                    "time_end_s":item["time_end_s"],
                    "water_end_C":item["HX_water_outlet_end_C"],
                    "water_interval_mean_W":item["water_outlet_interval_mean_thermal_W"],
                    "control":item["assumed_model_predictive_gas_bypass_control"]})
    states=x["gas_thermophysical_EOS_variation_NOT_coupled"][
        "pressure_scenarios"][1]["pointwise_states"]
    print("M3_7_AIR_EOS_REFERENCE_250KPA",
          {temp:{
            key:states[temp][key] for key in (
              "cp_J_kgK","density_kg_m3",
              "eos_air_enthalpy_rise_above_110C_J_kg",
              "original_constant_cp_enthalpy_rise_above_110C_J_kg")}
            for temp in ("110.0","220.0","260.0")})
    print("M3_7_INDEPENDENT_BED_HX_MESH_DIAGNOSTIC",
          x["numerical_mesh_coupling_and_time_sensitivity"][
             "separate_finite_volume_sensitivity_deltas"])
    print("M3_7_REAL_GAS_EOS_DIAGNOSTIC_CASES",
          len(x["gas_thermophysical_EOS_variation_NOT_coupled"][
              "pressure_scenarios"]))
    print("M3_7_REAL_PROCESS_1MW_SERVICE_VALIDATED=False")
    print("M3_7_MATCHED_ARCHITECTURE_RTE=None")


if __name__=="__main__":main()
