"""Archive a reproducible, explicitly unvalidated charge-only R718/bed example."""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
from hashlib import sha256
import argparse
import json
import subprocess

from carnot_battery_lab.physics.r718 import R718Inputs
from carnot_battery_lab.physics.gas_rock_regenerator import GasRockBed,BedState
from carnot_battery_lab.physics.packed_bed import PackedBedGeometry
from carnot_battery_lab.physics.coupled_charge import ChargeControl,simulate_charge


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=Path("results/m2_charge_only_screen.json"))
    args=ap.parse_args()
    bed=GasRockBed(cells=16)
    control=ChargeControl(dt_s=180,number_of_steps=6)
    hp=R718Inputs()
    runs={}
    for initial_C in (90.0,95.0,105.0):
        r=simulate_charge(bed,BedState.uniform(bed,initial_C),hp,control)
        if not r.completed:
            raise RuntimeError(f"initial_C={initial_C}: {r.termination_reason}")
        runs[str(initial_C)]=asdict(r)
    # Compact-bed thermal-breakthrough stress: intentionally do not assume
    # indefinite compressor feasibility; preserve all states before a trip.
    compact=GasRockBed(geometry=PackedBedGeometry(1.5,3.5,0.045,0.4),
                       cells=16,wall_UA_W_K=50.0)
    compact_control=ChargeControl(dt_s=180.0,number_of_steps=20)
    stress=simulate_charge(compact,BedState.uniform(compact,95.0),hp,compact_control)
    try:
        gitsha=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    except (OSError,subprocess.CalledProcessError):
        gitsha="unavailable"
    payload={
        "scientific_status":"coupled_charge_screen_unvalidated_compressor",
        "mode":"charge_only_no_process_supply_no_electricity_return",
        "bed":asdict(bed),
        "control":asdict(control),
        "hp":asdict(hp),
        "git_sha":gitsha,
        "cases":runs,
        "compact_bed_breakthrough_stress":asdict(stress),
        "compact_bed_parameters":asdict(compact),
        "limitations":[
            "Published 2018/2020 compressor stages do not support requested 4.659:1 per-stage reference",
            "Constant density, cp, conductivity and fluid properties for bed; no compressible gas inertia",
            "Only one-way charging with prescribed HP condenser heat, not dynamic capacity map",
            "Auxiliary blower energy assumed removed to ambient, not recovered as bed heat",
            "No gas pipe pressure drops outside Ergun bed; no refrigerant pressure losses",
            "No charging/discharging cycle, source dispatch, qualified industrial heat or TES RTE",
            "No external model/experimental validation of coupled transient"
        ]
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    for key,run in runs.items():
        s=run["steps"]
        print(f"initial={key} C; steps={len(s)}; "
              f"grid first={s[0]['total_grid_electric_W']:.1f} W; "
              f"Qbed={run['cumulative_stored_energy_J']:.1f} J; "
              f"relative energy ledger error="
              f"{run['energy_ledger_residual_J']/run['cumulative_hp_heat_J']:.4g}")
    print(f"compact-stress completed={stress.completed}; steps={len(stress.steps)}; "
          f"last_reason={stress.termination_reason}")
    if stress.steps:
        print(f"compact-stress first-grid={stress.steps[0].total_grid_electric_W:.1f} W; "
              f"last-grid={stress.steps[-1].total_grid_electric_W:.1f} W")
    print(f"saved={args.output}")


if __name__=="__main__":
    main()
