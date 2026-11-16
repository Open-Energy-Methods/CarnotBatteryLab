"""Reproducible synthetic bidirectional packed-bed thermal cycle, not v1.0."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState,bed_energy_J
from carnot_battery_lab.physics.reverse_flow_discharge import (
    CycleConditions,simulate_repeated_cycles,advance_reverse_discharge)


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
    # A SEPARATE hypothetical uniformly preheated initial bed shows the
    # process-temperature cutoff can produce positive qualified delivery.
    # This state is NOT achieved by the short nominal cycling protocol
    # above and is NOT part of a cyclic round-trip performance claim.
    hot_initial=BedState.uniform(bed,110.)
    hot_state=hot_initial
    hot_start=bed_energy_J(bed,hot_state)
    hot_qualified_J=0.
    hot_signed_J=0.
    hot_wall_J=0.
    hot_fan_J=0.
    hot_exergy_J=0.
    hot_grade_intervals=0
    for _ in range(15):
        d=advance_reverse_discharge(
            bed,hot_state,return_gas_K=schedule.discharge_return_K,
            mass_flow_kg_s=schedule.mass_flow_kg_s,
            dt_s=schedule.dt_s,
            minimum_process_delivery_K=schedule.minimum_process_delivery_K,
            dead_state_K=schedule.dead_state_K)
        hot_state=d.final_state
        hot_qualified_J+=d.qualified_process_heat_J
        hot_signed_J+=d.signed_heat_to_process_gas_J
        hot_wall_J+=d.ambient_loss_J
        hot_fan_J+=d.fan_electric_J_model
        hot_exergy_J+=d.useful_heat_exergy_J
        hot_grade_intervals+=int(d.screen_passed_temperature_samples)
    hot_residual=bed_energy_J(bed,hot_state)-hot_start+hot_signed_J+hot_wall_J
    if hot_qualified_J<=0 or hot_grade_intervals==0 or abs(hot_residual)>1e-3:
        raise RuntimeError("separate preheated reverse discharge example failed")
    hot_case={
        "uniform_initial_bed_K_ASSUMED":383.15,
        "initial_bed_prehistory":"NOT_SIMULATED; no match to nominal 3-cycle initial state",
        "source":"synthetic preheated state; NOT laboratory qualification",
        "reverse_discharge_steps":15,
        "temperature_grade_K":schedule.minimum_process_delivery_K,
        "qualified_heat_J":hot_qualified_J,
        "signed_heat_to_gas_J":hot_signed_J,
        "process_flow_exergy_gain_J":hot_exergy_J,
        "model_Ergun_blower_electric_J_not_calibrated":hot_fan_J,
        "qualified_sampled_intervals":hot_grade_intervals,
        "wall_loss_J":hot_wall_J,
        "net_first_law_residual_J":hot_residual,
        "thermal_roundtrip_efficiency":None,
        "experimental_service_validation":False,
    }
    payload={
        "status":"SYNTHETIC_M3_CHARGE_REVERSE_DISCHARGE_NO_PHYSICAL_VALIDATION",
        "bed_hypothesis":asdict(bed),
        "cycle_hypothesis":asdict(schedule),
        "separate_preheated_bed_reverse_discharge":hot_case,
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
    print("M3_SEPARATE_PREHEATED_QUALIFIED_HEAT_J",f"{hot_qualified_J:.4f}",
          "GRADE_INTERVALS",hot_grade_intervals,
          "FIRST_LAW_RESIDUAL_J",f"{hot_residual:.6g}")
    print("M3_CYCLIC_SCREEN",run["nominal_cyclic_state_screen_pass"])
    print("M3_EXPERIMENTAL_VALIDATION_PASS=False; ELECTRIC_RTE_NOT_ESTABLISHED")


if __name__=="__main__":
    main()
