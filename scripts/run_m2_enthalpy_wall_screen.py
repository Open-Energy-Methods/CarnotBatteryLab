"""Reproducible M2.3 thermal-property/shell-inertia DEVELOPMENT screen.

Synthetic operating forcing only: no experimental source flow bore or wall
UA is claimed to be measured, no measured Case A/B/C/D TC fitted.
NIST N2/O2 Shomate cp(T) and h(T) form the gas energy basis.
Steel shell wall thickness source: Wolde et al. (2022), 7 mm nominal.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

from carnot_battery_lab.physics.enthalpy_wall_bed import (
    EnthalpyWallBed,EnthalpyWallState,advance_enthalpy_wall,energy_J)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/m2_variable_enthalpy_wall_screen.json"))
    args=p.parse_args()
    bed=EnthalpyWallBed(cells=8)
    state=EnthalpyWallState.uniform(bed,350.)
    initial=energy_J(bed,state)
    total_input=0.
    total_external_loss=0.
    steps=[]
    for k in range(4):
        result=advance_enthalpy_wall(
            bed,state,inlet_K=480.,mass_flow_kg_s=.020,dt_s=120.,
            relative_tolerance=1e-8)
        state=result.final_state
        total_input+=result.heat_from_inlet_gas_J
        total_external_loss+=result.heat_lost_to_ambient_J
        if abs(result.first_law_residual_J)>max(1.,abs(result.heat_from_inlet_gas_J))*1e-4:
            raise RuntimeError("synthetic variable enthalpy/wall heat balance failed")
        steps.append({
            "index":k+1,"bed_outlet_K":result.final_outlet_gas_K,
            "first_wall_K":state.wall_K[0],
            "fluid_gas_inlet_heat_J":result.heat_from_inlet_gas_J,
            "wall_ambient_loss_J":result.heat_lost_to_ambient_J,
            "internal_total_stored_J":result.stored_energy_change_J,
            "energy_residual_J":result.first_law_residual_J,
            "solver_function_evaluations":result.solver_nfev,
        })
    final=energy_J(bed,state)
    cumulative_residual=final-initial-total_input+total_external_loss
    if abs(cumulative_residual)>max(1.,abs(total_input))*1e-4:
        raise RuntimeError("full multi-step enthalpy/wall energy audit failed")
    settings=asdict(bed)
    result={
        "status":"SYNTHETIC_M2_VARIABLE_ENTHALPY_WALL_CONSERVATION_ONLY",
        "experimental_validation_pass":False,
        "sources":{
            "gas_NIST_species":"N2 https://webbook.nist.gov/cgi/cbook.cgi?Formula=N2&cTG=on ; O2 https://webbook.nist.gov/cgi/cbook.cgi?ID=C7782447&Type=JANAFG",
            "rig_steel_shell":"Wolde et al 2022 doi:10.59627/rbens.2022v13i2.395, nominal 7mm",
        },
        "settings":settings,
        "settings_sha256":sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest(),
        "environment":{"numpy":version("numpy"),"scipy":version("scipy")},
        "steps":steps,
        "initial_energy_J":initial,
        "final_energy_J":final,
        "external_gas_heating_J":total_input,
        "external_ambient_loss_J":total_external_loss,
        "multistep_energy_residual_J":cumulative_residual,
        "assumptions_not_lab_measured":[
            "N2/O2 molar mixture 79/21 ignores humid air, Ar and CO2",
            "gas sensible h(T) at fixed gas inventory not full compressible pressure model",
            "2024 slag density/cp(T) slope not independently calibrated",
            "shell steel 7mm cylindrical wall without end caps/pipe masses",
            "wall-solid and wall-to-ambient UAs are imposed unmeasured scenarios",
            "uniform initial field 350K, 480K inlet and 0.02kg/s gas synthetic",
            "no axial 2D buoyancy, no actual pneumatic pressure calibration",
        ],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(f"M2_VARIABLE_CP_SYNTHETIC_Q_J={total_input:.3f}",
          f"WALL_FINAL_K={state.wall_K[0]:.3f}",
          f"ENERGY_RESIDUAL_J={cumulative_residual:.6g}")
    print("M2_VARIABLE_CP_EXPERIMENTAL_VALIDATION_PASS=False")


if __name__=="__main__":
    main()
