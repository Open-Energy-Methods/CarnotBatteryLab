"""Reproduce independent M3.9 open pressure-connected bed/HX cases.

Small, hypothetical preheated bed numerical prototype; not industrial
service, not a real charging cycle, no qualified RTE.
"""
import argparse,json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.open_real_air_water_train import (
    OpenAirWaterTrain,run_open_air_water_train,
)


def study():
    base=OpenAirWaterTrain()
    cases={
      "coarse_2_2":replace(base,bed_cells=2,hx_cells=2),
      "baseline_4_4":base,
      "refined_8_8":replace(base,bed_cells=8,hx_cells=8),
      "higher_hx_resistance":replace(base,hx_total_minor_K=40.),
      "lower_pressure_head":replace(base,inlet_gas_P_Pa=250050.,
                                   outlet_reservoir_P_Pa=249950.),
      "cold_bed_control":replace(base,initial_bed_solid_K=383.15),
      "lower_water_hx_UA":replace(base,hx_overall_UA_W_K=30.),
    }
    results={}
    for k,v in cases.items():
        r=run_open_air_water_train(v,duration_s=60.)
        summary={key:r[key] for key in (
            "water_outlet_final_C","water_mean_thermal_duty_W",
            "bed_HX_shared_interface_mass_kg","whole_train_energy_residual_J",
            "whole_train_mass_residual_kg","bed_energy_residual_J",
            "HX_energy_residual_J","maximum_interstitial_or_HX_Mach_at_accepted_nodes")}
        summary["final_gas_exit_mass_flow_kg_s"]=r["gas_face_mass_flow_kg_s"][-1]
        results[k]={"summary":summary,"result":r}
        print("M3_9_CASE",k,json.dumps(summary),flush=True)
    return {
        "research_stage":"M3_9_OPEN_PRESSURE_CONNECTED_BED_HX",
        "numerical_prototype_not_industrial_service":True,
        "results":results,
        "gas_closed_circulation_loop_implemented":False,
        "actual_charging_energy_and_cycle_not_modeled":True,
        "experimental_validation":False,
        "industrial_1MW_qualified":False,
        "Carnot_battery_RTE":None,
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/m3_9_open_air_water_train.json"))
    a=p.parse_args()
    x=study()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n")
