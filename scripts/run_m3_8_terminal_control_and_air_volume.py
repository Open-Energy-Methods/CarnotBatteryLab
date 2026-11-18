"""M3.8 controlled-service experiment with independent real-air CV verification."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from dataclasses import asdict
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed
from carnot_battery_lab.physics.transient_liquid_hx import TransientHXAssumptions
from carnot_battery_lab.physics.coupled_transient_process_loop import CoupledHXTrial,simulate_coupled_transient_hx
from carnot_battery_lab.physics.process_gas_bypass_control import GasBypassControllerAssumptions
from carnot_battery_lab.physics.real_air_control_volume import AirVolumeState,advance_air_volume
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.real_air_bed_prototype import RealAirBedAssumptions,run_real_air_bed


def study():
    results={}
    # Hard predeclared hypotheses; compare temporal controller update at
    # SAME valve rate per second, then separate mesh and charge duration.
    cases=(
      ("mean60_reference",16,8,60.,7200.,"interval_mean_duty"),
      ("terminal60",16,8,60.,7200.,"terminal_temperature"),
      ("terminal30",16,8,30.,7200.,"terminal_temperature"),
      ("terminal10",16,8,10.,7200.,"terminal_temperature"),
      ("terminal30_refined",32,12,30.,7200.,"terminal_temperature"),
      ("terminal30_4h",16,8,30.,14400.,"terminal_temperature"),
    )
    for name,nb,nh,dt,charge,objective in cases:
        trial=CoupledHXTrial(name=name,charge_duration_s=charge,
               hx_warmup_duration_s=600.,process_duration_s=3600.,
               transient_step_s=dt,max_num_steps=500)
        cfg=GasBypassControllerAssumptions(startup_full_flow_seconds=120.,
               objective=objective,maximum_fraction_rate_per_s=.4/60.)
        sim=simulate_coupled_transient_hx(GasRockBed(cells=nb),trial,
               TransientHXAssumptions(cells=nh),gas_bypass_controller=cfg)
        rows=[r for r in sim["sampled_thermocouple_like_model_trace_NOT_observations"]
                if not r["warmup_not_counted_for_process"]]
        d=sim["coupled_discharge_HX_energy"]
        controls=[r["assumed_model_predictive_gas_bypass_control"] for r in rows]
        summary={
          "case":name,"bed_cells":nb,"hx_cells":nh,"control_update_s":dt,
          "charge_hours":charge/3600.,"objective":objective,
          "consecutive_passing_service_minutes":d["sampled_model_thermal_grade_prefix_s"]/60.,
          "passing_total_service_minutes":sum(c["model_only_interval_exact_150C_control"] for c in controls)*dt/60.,
          "model_all_service_intervals_pass":sim["model_only_thermal_duty_possible"],
          "min_water_node_C":min(c["min_nodal_process_water_C"] for c in controls),
          "max_water_node_C":max(c["max_nodal_process_water_C"] for c in controls),
          "max_abs_mean_duty_error_W":max(abs(c["mean_control_duty_error_W"]) for c in controls),
          "max_abs_valve_mass_residual_kg_s":max(abs(c["mass_balance_residual_kg_s"]) for c in controls),
          "final_water_C":rows[-1]["HX_water_outlet_end_C"],
          "uninstalled_return_cooler_thermal_GJ":d["gas_cooler_thermal_energy_required_J_uninstalled"]/1e9,
          "combined_first_law_residual_J":d["bed_HX_gas_cooler_system_first_law_residual_J"],
          "physical_service_qualified":False,
        }
        results[name]={"summary":summary,"simulation":sim}
        print("M3_8_CASE",json.dumps(summary),flush=True)
    s=AirVolumeState.from_TP(1.,383.15,250000.)
    cells={
      "sealed_heating":advance_air_volume(s,duration_s=10.,heat_into_gas_W=5000.),
      "open_heated_inflow":advance_air_volume(s,duration_s=2.,
           inlet_mass_flow_kg_s=.10,outlet_mass_flow_kg_s=.05,inlet_T_K=450.),
    }
    for k,v in cells.items():
        print("M3_8_REAL_AIR_CELL",k,json.dumps(v),flush=True)
    # A separate pressure-driven lab-scale prototype, not the 1MW geometry.
    g=PackedBedGeometry(length_m=.5,diameter_m=.3,
                         particle_diameter_m=.01,porosity=.4)
    prototypes={}
    for n in (2,4,8):
        a=RealAirBedAssumptions(g,cells=n)
        p=run_real_air_bed(a,duration_s=10.)
        prototypes[str(n)]={"assumptions":asdict(a),"result":p}
        print("M3_8_PRESSURE_DRIVEN_BED",json.dumps({
            "cells":n,"outlet_gas_K":p["final_gas_states"][-1]["T"],
            "final_exit_mass_flow_kg_s":p["final_signed_face_mass_flow_kg_s"][-1],
            "mass_residual_kg":p["mass_first_law_residual_kg"],
            "energy_residual_J":p["energy_first_law_residual_J"],
            "max_interstitial_Mach":p["maximum_accepted_node_interstitial_Mach"],
        }),flush=True)
    return {
      "research_stage":"M3_8_TERMINAL_CONTROL_AND_REAL_AIR_VOLUME_PRIMITIVE",
      "original_contract":"1MW_110_to_150C_water", "results":results,
      "real_air_control_volume_tests":cells,
      "standalone_pressure_driven_real_air_bed_prototypes":prototypes,
      "prototype_heat_transfer_coefficient_not_measured":True,
      "fully_coupled_variable_property_bed_HX_implemented":False,
      "original_weber_dataset_raw_measurements_available":False,
      "experimental_validation_completed":False,
      "actual_controller_rated_and_installed":False,
      "actual_process_water_delivery_qualified":False,
      "Carnot_battery_RTE":None,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/m3_8_control_and_real_air.json"))
    a=p.parse_args()
    x=study()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
