"""Reproducible synthetic bidirectional packed-bed thermal cycle, not v1.0."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
from carnot_battery_lab.physics.reverse_flow_discharge import (
    CycleConditions,simulate_repeated_cycles)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,
                   default=Path("results/m3_synthetic_charge_reverse_discharge.json"))
    args=p.parse_args()
    bed=GasRockBed(
        geometry=PackedBedGeometry(.4,.158,.02,.39),
        cells=12,gas_density_kg_m3=1.,rock_density_kg_m3=3700.,
        rock_cp_J_kgK=1100.,ambient_K=303.15,wall_UA_W_K=.2,
        blower_efficiency=.7,
    )
    schedule=CycleConditions(charge_steps=30,discharge_steps=30,dt_s=30.)
    run=simulate_repeated_cycles(
        bed,BedState.uniform(bed,30.),
        conditions=schedule,cycles=3,
        cyclic_state_max_abs_K_threshold=.25)
    payload={
        "status":"SYNTHETIC_M3_CHARGE_REVERSE_DISCHARGE_NO_PHYSICAL_VALIDATION",
        "bed_hypothesis":asdict(bed),
        "cycle_hypothesis":asdict(schedule),
        "run":{key:val for key,val in run.items() if key!="final_state"},
        "final_state":asdict(run["final_state"]),
        "physical_validation_pass":False,
        "matched_useful_heat_service_qualification":False,
        "round_trip_efficiency_established":False,
        "compressor_or_heat_pump_coupling_included":False,
        "model_published_loss_correlations_are_not_instrument_calibrations":True,
        "limitations":[
            "No measured gas/slag properties or source-calibrated Ergun pressure losses",
            "No R718 or R600 heat-pump coupling, primary heat source, compressor electrical work",
            "No dynamically matched industrial process loop/heat exchanger",
            "Qualification checks process outlet start/mean/end samples, NOT continuous high-grade delivery",
            "No measured wall heat losses, valves, reverse-flow manifold mixing or 2-D buoyancy",
            "Cyclic closure is reported as a provisional numerical state screen, not experimental RTE",
        ]
    }
    original=json.dumps(
        {"bed":payload["bed_hypothesis"],"schedule":payload["cycle_hypothesis"]},
        sort_keys=True)
    payload["inputs_sha256"]=sha256(original.encode()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    for c in run["cycles"]:
        print("M3_CYCLE",c["cycle_number"],
              f"charge_J={c['charge_gas_thermal_input_J']:.4f}",
              f"qualified_heat_J={c['qualified_process_heat_J']:.4f}",
              f"end_state_max_K={c['max_start_end_temperature_difference_K']:.5f}",
              f"energy_residual_J={c['first_law_cycle_residual_J']:.6g}")
    print("M3_CYCLIC_SCREEN",run["nominal_cyclic_state_screen_pass"])
    print("M3_EXPERIMENTAL_VALIDATION_PASS=False; ELECTRIC_RTE_NOT_ESTABLISHED")


if __name__=="__main__":
    main()
