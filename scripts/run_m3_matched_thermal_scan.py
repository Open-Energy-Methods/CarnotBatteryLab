"""M3.2 reproducible restricted thermal schedule scan. No physical qualification.

The original proposed gas proxy is 110C return to 150C delivery, 1 MW.
This is NOT a demonstration of a liquid process heat exchanger.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
from carnot_battery_lab.physics.r718 import R718Inputs
from carnot_battery_lab.physics.coupled_charge import ChargeControl
from carnot_battery_lab.physics.sequential_hp_tes_service import (
    CandidateProcessGasService,
)
from carnot_battery_lab.physics.matched_thermal_service import (
    MatchedThermalProtocol,scan_matched_thermal_schedules,
)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,
        default=Path("results/m3_matched_cycle_gas_service_screen.json"))
    args=parser.parse_args()
    bed=GasRockBed(cells=8)
    initial=BedState.uniform(bed,95.)
    hp=R718Inputs()
    charging=ChargeControl(dt_s=120.,number_of_steps=2)
    target=CandidateProcessGasService(
        process_return_K=383.15,required_supply_K=423.15,
        reverse_mass_flow_kg_s=25.,dt_s=60.,requested_steps=2)
    protocol=MatchedThermalProtocol(
        charge_step_counts=(2,4,8,16,32),discharge_step_counts=(2,),
        repeat_cycles=3,nominal_process_duty_W=1_000_000.,
        terminal_max_abs_difference_K=.25)
    screening=scan_matched_thermal_schedules(
        bed,initial,hp,charging,target,protocol)
    input_data={
        "bed":asdict(bed),
        "initial":asdict(initial),
        "hp":asdict(hp),
        "charging":asdict(charging),
        "target":asdict(target),
        "protocol":asdict(protocol),
    }
    report={
        "status":"M3_2_NUMERICAL_GAS_SERVICE_CYCLIC_SCREEN_UNQUALIFIED",
        "inputs":input_data,
        "input_sha256":sha256(
            json.dumps(input_data,sort_keys=True).encode()).hexdigest(),
        "results":screening,
        "industrial_liquid_process_heat_exchanger_modelled":False,
        "80C_source_compressor_envelope_verified":False,
        "experimental_thermocline_or_pressure_validation":False,
        "thermal_round_trip_efficiency":None,
        "electricity_round_trip_efficiency":None,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("M3_2_REPRODUCIBLE_GAS_SCREEN",screening["status"])
    for key,value in screening["candidates"].items():
        good=[row for row in value["cycles"]
              if row["status"]=="NUMERICAL_CYCLE_COMPLETED"]
        first=good[0] if good else None
        blocked=next((row for row in value["cycles"]
                      if row["status"]!="NUMERICAL_CYCLE_COMPLETED"),None)
        print(key,value["status"],"completed_cycles",len(good),
              "model_only_thermal_match",value["model_only_matched_gas_thermal_screen"],
              "first_post_charge_process_outlet_C",
              round(first["first_discharge_outlet_before_flow_K"]-273.15,3)
                  if first else None,
              "first_initial_grade_deficit_K",
              round(first["initial_outlet_temperature_deficit_K"],3)
                  if first else None,
              "first_terminal_field_error_K",
              round(first["max_terminal_field_difference_K"],3)
                  if first else None,
              "first_charge_compressor_ratio_guard",
              round(first["max_nominal_R718_stage_pressure_ratio_across_charge"],3)
                  if first else None,
              "blocked_cycle",blocked["cycle"] if blocked else None,
              "charging_termination_reason",
              blocked.get("termination_reason") if blocked else None)
    print("HARDWARE_QUALIFIED=False; PHYSICAL_VALIDATION=False; RTE=None")


if __name__=="__main__":
    main()
