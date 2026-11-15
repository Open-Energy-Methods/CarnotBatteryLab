"""Source-locked *numerical* packed-bed spatial convergence through 512 cells.

Replays ONLY original horizontal copper-slag Case B (Mendeley DOI
10.17632/j37x6ptpk2.1) using the previously documented 2022-rig geometry,
fixed 52mm *assumed* exhaust pipe bore, constant material parameters and the
historical observed-Tout-dependent mass-flow relation.

CAUTION: measured T_out enters the MASS FLOW forcing via source-paper Eq.(1),
hence this is legitimate numerical grid verification *for a fixed externally
specified forcing*, NOT an independent predictive model validation. No
model parameters are selected to reduce experimental error, and no A/C/D
physical runs are opened. A different predicted-Tout-boundary variant has
separate, non-grid-qualified scientific status.

All output points, time axes, original SHA-256 and input configuration are
archived. No fine-grid acceptance threshold is adjusted from results.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from statistics import mean
from math import sqrt,log2,isfinite
from dataclasses import asdict
from importlib.metadata import version

from exploratory_forward_horizontal_bed import exploratory_forward

DOI="10.17632/j37x6ptpk2.1"
FROZEN_SOURCE_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"
MESHES=(64,128,256,512)
RMS_GRID_TARGET_K=1.0
BREAKTHROUGH_GRID_TARGET_S=15.0


def _pair(coarse:dict,fine:dict)->dict:
    if coarse["source_sha256"]!=fine["source_sha256"]:
        raise ValueError("cannot compare different experimental sources")
    if coarse["time_s"]!=fine["time_s"]:
        raise ValueError("mesh comparisons require identical input samples/time axis")
    x=[float(b-a) for a,b in zip(coarse["model_Tout_C"],fine["model_Tout_C"])]
    if len(x)<10 or not all(isfinite(v) for v in x):
        raise ValueError("invalid finite temperature profiles")
    crossing_a=coarse["model_first_80C_outlet_crossing_s"]
    crossing_b=fine["model_first_80C_outlet_crossing_s"]
    if crossing_a is None or crossing_b is None:
        raise ValueError("breakthrough crossing missing on a mesh")
    return {
        "outlet_temperature_RMS_K":sqrt(mean(t*t for t in x[1:])),
        "outlet_temperature_max_absolute_K":max(abs(t) for t in x[1:]),
        "first_80C_crossing_shift_s":crossing_b-crossing_a,
        "zero_based_first_sample_excluded_from_RMS":True,
    }


def evaluate_fine_mesh_outputs(outputs:dict)->dict:
    if tuple(sorted(outputs))!=MESHES:
        raise ValueError("expected exactly 64, 128, 256 and 512 cells")
    pairs={}
    for a,b in zip(MESHES,MESHES[1:]):
        pairs[f"{a}_to_{b}"]=_pair(outputs[a],outputs[b])
    errors=[v["outlet_temperature_RMS_K"] for v in pairs.values()]
    shifts=[abs(v["first_80C_crossing_shift_s"]) for v in pairs.values()]
    orders=[log2(a/b) for a,b in zip(errors,errors[1:])]
    front_orders=[log2(a/b) for a,b in zip(shifts,shifts[1:])]
    monotone=all(a>b for a,b in zip(errors,errors[1:]))
    crossing_monotone=all(a>b for a,b in zip(shifts,shifts[1:]))
    meets=(errors[-1]<=RMS_GRID_TARGET_K
           and shifts[-1]<=BREAKTHROUGH_GRID_TARGET_S
           and monotone and crossing_monotone)
    return {
        "pairs":pairs,
        "observed_RMS_refinement_orders":orders,
        "observed_breakthrough_refinement_orders":front_orders,
        "outlet_RMS_monotone":monotone,
        "breakthrough_change_monotone":crossing_monotone,
        "previously_declared_screening_targets":{
            "pairwise_RMS_outlet_K":RMS_GRID_TARGET_K,
            "pairwise_first_80C_shift_s":BREAKTHROUGH_GRID_TARGET_S,
        },
        "provisional_numerical_increment_pass_at_512":bool(meets),
        "external_physical_validation_pass":False,
        "warning":"Single finest-grid pair below a provisional threshold is not a verified continuum solution, a certified numerical error bound, or experimental accuracy",
    }


def run(input_dir:Path)->dict:
    outputs={}
    for n in MESHES:
        r=exploratory_forward("B",input_dir=input_dir,cells=n)
        if r["source_sha256"]!=FROZEN_SOURCE_SHA:
            raise ValueError("source data checksum changed")
        outputs[n]=r
    summary=evaluate_fine_mesh_outputs(outputs)
    return {
        "status":"SOURCE_LOCKED_NUMERICAL_REFINEMENT_ONLY_NOT_PHYSICAL_VALIDATION",
        "doi":DOI,
        "source_case":"B_only",
        "source_sha256":FROZEN_SOURCE_SHA,
        "excluded_from_forward_fitting":["A","C","D"],
        "flow_target_leakage_warning":"Measured Tout enters gas-density and mass-flow forcing; not a blind experimental model comparison",
        "all_inputs_identical_except_spatial_cells":True,
        "solvers":{"scipy":version("scipy"),"numpy":version("numpy")},
        "physical_model_assumptions":{
            "gas_rock_nominal_geometry":"source-backed 2022 apparatus assumed identical to 2024",
            "pipe_inner_diameter_m_assumed_not_measured":0.052,
            "gas_and_rock_thermophysical_properties":"constant indicative, not measured batch",
            "wall_UA_W_K_assumed":0.5,
            "solid_axial_conductivity_W_mK":0,
            "source_exhaust_velocity_and_Tout_forcing":"original measured Case B only",
        },
        "runs":{
            str(n):{
                "cells":n,
                "model_tout_C":outputs[n]["model_Tout_C"],
                "measured_tout_C_for_comparison_only":outputs[n]["measured_Tout_C"],
                "time_s":outputs[n]["time_s"],
                "first_model_80C_crossing_s":outputs[n]["model_first_80C_outlet_crossing_s"],
                "first_measured_80C_crossing_s":outputs[n]["observed_first_80C_outlet_crossing_s"],
                "exploratory_RMSE_to_measured_C_NOT_VALIDATION":outputs[n]["rmse_C"],
                "exploratory_MAE_to_measured_C_NOT_VALIDATION":outputs[n]["mae_C"],
                "maximum_relative_energy_residual":outputs[n]["max_relative_step_energy_residual"],
            } for n in MESHES
        },
        "refinement_evidence":summary,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--output",type=Path,default=Path("results/external_horizontal_bed/case_B_fine_mesh_512.json"))
    args=p.parse_args()
    result=run(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    for n in MESHES:
        r=result["runs"][str(n)]
        print("FINE_GRID_CASE_B",
              f"N={n}",
              f"breakthrough_s={r['first_model_80C_crossing_s']:.4f}",
              f"experimental_RMSE_C_NOT_VALIDATION={r['exploratory_RMSE_to_measured_C_NOT_VALIDATION']:.4f}",
              f"relative_energy_residual={r['maximum_relative_energy_residual']:.3g}")
    for k,v in result["refinement_evidence"]["pairs"].items():
        print("FINE_GRID_PAIR",k,
              f"RMS_K={v['outlet_temperature_RMS_K']:.5f}",
              f"breakthrough_shift_s={v['first_80C_crossing_shift_s']:.5f}")
    print("NUMERICAL_INCREMENT_PROVISIONAL_PASS",
          result["refinement_evidence"]["provisional_numerical_increment_pass_at_512"])
    print("EXPERIMENTAL_MODEL_VALIDATION_PASS",False)


if __name__=="__main__":
    main()
