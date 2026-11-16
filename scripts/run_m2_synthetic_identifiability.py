"""Run deterministic model-only sensitivity; NO measured experimental fitting.

All values are synthetic hypothetical input perturbations, not uncertainty
distributions. The measured 2024 Case B/C/D data are not opened here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from carnot_battery_lab.validation.m2_synthetic_identifiability import (
    SyntheticInputs,synthetic_local_sensitivity,exact_reparameterisation_aliases,
    forward_synthetic)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path(
        "results/m2_synthetic_parameter_identifiability.json"))
    p.add_argument("--steps",type=int,default=24)
    p.add_argument("--cells",type=int,default=12)
    args=p.parse_args()
    baseline=SyntheticInputs()
    result=synthetic_local_sensitivity(baseline,steps=args.steps,cells=args.cells)
    aliases=exact_reparameterisation_aliases(baseline)
    if not aliases["same_D_squared_velocity_product"] or not aliases["same_rock_volumetric_heat_capacity"]:
        raise RuntimeError("analytic parameter alias invariant failed")
    nominal=forward_synthetic(baseline,steps=4,cells=8)
    flow_alias=forward_synthetic(
        SyntheticInputs(**aliases["pipe_diameter_and_velocity_scale_pair"]),
        steps=4,cells=8)
    rock_alias=forward_synthetic(
        SyntheticInputs(**aliases["rock_density_and_cp_pair"]),
        steps=4,cells=8)
    alias_deltas={
        "pipe_velocity_max_temperature_difference_K":
            max(abs(a-b) for a,b in zip(nominal["T_out_K"],flow_alias["T_out_K"])),
        "rock_density_cp_max_temperature_difference_K":
            max(abs(a-b) for a,b in zip(nominal["T_out_K"],rock_alias["T_out_K"])),
    }
    if max(alias_deltas.values())>1e-3:
        raise RuntimeError("claimed model-structural alias not demonstrated by forward model")
    result["analytic_aliases"]=aliases
    result["independent_synthetic_alias_numerical_errors"]=alias_deltas
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("SYNTHETIC_SENSITIVITY_RANK",result["rank_by_RMS_log_temperature_sensitivity"])
    print("RELATIVE_JACOBIAN_RANK",result["effective_SVD_rank_relative_1e_minus3"])
    print("STRUCTURAL_ALIAS_MAX_ERROR",alias_deltas)
    print("EXPERIMENTAL_VALIDATION_PASS=False; PARAMETER_FIT_PERFORMED=False")


if __name__=="__main__":
    main()
