"""Real-fluid R718 --> state-dependent TES charging --> reverse gas discharge.

A NEGATIVE process-temperature service screen is a valid outcome. This is
NOT a real compressor-qualified HTHP, physical industrial HX or validated RTE.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
from carnot_battery_lab.physics.r718 import R718Inputs
from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge
from carnot_battery_lab.physics.sequential_hp_tes_service import (
    CandidateProcessGasService,handoff_coupled_charge_to_reverse_discharge)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,
                   default=Path("results/m3_r718_sequential_hp_tes_discharge_screen.json"))
    args=p.parse_args()
    bed=GasRockBed(cells=8)
    hp=R718Inputs()
    charging=ChargeControl(dt_s=120.,number_of_steps=2)
    original=BedState.uniform(bed,95.)
    r=simulate_charge(bed,original,hp,charging)
    services={
        "exploratory_gas_80C_to_110C":CandidateProcessGasService(
            process_return_K=353.15,required_supply_K=383.15,
            dt_s=60.,requested_steps=3),
        "proposed_industrial_110C_to_150C":CandidateProcessGasService(
            process_return_K=383.15,required_supply_K=423.15,
            dt_s=60.,requested_steps=3),
    }
    cases={name:handoff_coupled_charge_to_reverse_discharge(bed,r,service)
           for name,service in services.items()}
    payload={
        "status":"SEQUENTIAL_R718_THERMAL_TES_SERVICE_SCREEN_UNVALIDATED",
        "proposed_service_gas_not_real_process_water_loop":True,
        "R718_80C_heat_source_compressor_hardware_qualified":False,
        "R718_actual_heat_pump_map_available":False,
        "heat_pump_charge_is_storage_state_responsive":True,
        "charge_was_completed":r.completed,
        "charge_termination_reason":r.termination_reason,
        "charge_control":asdict(charging),
        "heat_pump_inputs":asdict(hp),
        "bed_hypothesis":asdict(bed),
        "original_initial_state":asdict(original),
        "post_charge_state":asdict(r.final_bed),
        "source_charge":asdict(r),
        "service_candidates":cases,
        "experimental_validation":False,
        "whole_system_round_trip_efficiency":None,
        "process_service_matched":False,
        "limitations":[
            "All compressor stage ratios remain unverified by manufacturer compressor maps",
            "R718 source is numerical, no experimentally qualified 80C-source machine",
            "Process and TES gas are modeled ideal constant-cp rather than actual industrial HX",
            "HP compressor/sink control and TES reverse discharge run sequentially not simultaneously",
            "No cyclic terminal state closure or dynamic process heat delivery guarantee",
            "Bed Ergun pressure/velocity/wall/slag materials not independently calibrated",
            "No validated electricity-to-heat RTE or matched-service architecture ranking",
        ],
    }
    provenance={"bed":payload["bed_hypothesis"],"hp":payload["heat_pump_inputs"],
                "control":payload["charge_control"],
                "services":{k:asdict(v) for k,v in services.items()}}
    payload["inputs_sha256"]=sha256(json.dumps(provenance,sort_keys=True).encode()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    print("R718_SEQUENTIAL_CHARGE_COMPLETED",r.completed)
    for name,a in cases.items():
        print("R718_TO_TES_REVERSE_GRADE",name,
              "status",a["status"],
              "qualified_J",a["qualified_process_heat_J"],
              "heat_signed_J",a.get("signed_discharge_heat_into_process_gas_J"),
              "first_law_residual_J",a.get("discharge_energy_residual_J"))
    print("R718_HARDWARE_QUALIFIED=False; PROCESS_MATCHED=False; RTE_ESTABLISHED=False")


if __name__=="__main__":
    main()
