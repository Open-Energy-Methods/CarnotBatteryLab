"""Case B ONLY: numerical convergence with measured Tout excluded from physics.

The physical boundary uses independently measured inlet-temperature profile
and EXHAUST velocity, with exhaust density from predicted outlet temperature
solved by a coupled fixed point each time interval. The resulting model is
still unqualified because pipe bore, gas properties and laboratory sensor
positions are not independently measured/verified. This is NOT a physical
validation and does not authorize any A/C/D calibration or claims.

The mesh acceptance values 1 K / 15 s were established in a prior study,
before this source-locked fine-grid run. No physical model parameters are fit.
"""
from __future__ import annotations
import argparse
import json
from math import sqrt,log2,isfinite
from pathlib import Path
from statistics import mean
from importlib.metadata import version

from run_case_B_no_target_leak import evaluate_case_B

MESHES=(32,64,128,256,512)
EXPERIMENT_SOURCE_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"
PAIRWISE_RMS_ACCEPTANCE_K=1.0
PAIRWISE_BREAKTHROUGH_ACCEPTANCE_S=15.0


def compare(a:dict,b:dict)->dict:
    if a["source_sha256"]!=b["source_sha256"] or (
        a["model_time_s"]!=b["model_time_s"]):
        raise ValueError("source or time arrays differ; invalid mesh comparison")
    if a["outlet_temperature_target_used_in_physics"] is not False or (
        b["outlet_temperature_target_used_in_physics"] is not False):
        raise ValueError("measured Tout forcing is prohibited in this study")
    err=[float(x-y) for x,y in zip(b["predicted_exhaust_C"][1:],
                                  a["predicted_exhaust_C"][1:])]
    if len(err)<10 or not all(isfinite(x) for x in err):
        raise ValueError("insufficient finite mesh comparison")
    ta=a["predicted_first_80C_s"]
    tb=b["predicted_first_80C_s"]
    return {
        "RMS_outlet_profile_difference_K":sqrt(mean(x*x for x in err)),
        "max_outlet_profile_difference_K":max(abs(x) for x in err),
        "first_80C_breakthrough_shift_s":None if ta is None or tb is None else tb-ta,
        "measured_outlet_enters_mass_flow":False,
    }


def assess(runs:dict[int,dict])->dict:
    if tuple(sorted(runs))!=MESHES:
        raise ValueError("required 32,64,128,256,512 grids not all present")
    pairs={}
    for n0,n1 in zip(MESHES,MESHES[1:]):
        pairs[f"{n0}_to_{n1}"]=compare(runs[n0],runs[n1])
    rms=[x["RMS_outlet_profile_difference_K"] for x in pairs.values()]
    crossing=[x["first_80C_breakthrough_shift_s"] for x in pairs.values()]
    full_crossings=all(c is not None and isfinite(c) for c in crossing)
    monotone_rms=all(x>y for x,y in zip(rms,rms[1:]))
    monotone_crossing=(full_crossings and
                       all(abs(x)>abs(y) for x,y in zip(crossing,crossing[1:])))
    meets=(monotone_rms and monotone_crossing and
           rms[-1]<=PAIRWISE_RMS_ACCEPTANCE_K and
           abs(crossing[-1])<=PAIRWISE_BREAKTHROUGH_ACCEPTANCE_S)
    orders=[log2(x/y) for x,y in zip(rms,rms[1:]) if x>0 and y>0]
    return {
        "pairwise":pairs,
        "observed_RMS_grid_orders":orders,
        "all_crossings_present":full_crossings,
        "monotone_outlet_RMS_improvement":monotone_rms,
        "monotone_breakthrough_improvement":monotone_crossing,
        "previously_declared_numerical_screening_limits":{
            "RMS_K":PAIRWISE_RMS_ACCEPTANCE_K,
            "breakthrough_shift_s":PAIRWISE_BREAKTHROUGH_ACCEPTANCE_S,
        },
        "provisional_spatial_screen_pass":bool(meets),
        "predictive_experimental_validation_pass":False,
        "model_hardware_qualified":False,
    }


def run(input_dir:Path)->dict:
    runs={}
    for n in MESHES:
        r=evaluate_case_B(input_dir,cells=n)
        if r["source_sha256"]!=EXPERIMENT_SOURCE_SHA:
            raise ValueError("measured Case B raw hash mismatch")
        if r["outlet_temperature_target_used_in_physics"] is not False:
            raise ValueError("target leakage detected in numerical solver")
        runs[n]=r
    refinement=assess(runs)
    return {
        "status":"CASE_B_TARGET_INDEPENDENT_EXHAUST_FORCING_SPATIAL_SCREEN_UNVALIDATED",
        "source_doi":"10.17632/j37x6ptpk2.1",
        "source_sha256":EXPERIMENT_SOURCE_SHA,
        "case":"B_only",
        "other_model_fitting_cases_not_read":["A","C","D"],
        "measured_Tout_excluded_from_physics":True,
        "still_not_independent_mass_flow_measurement":True,
        "source_exhaust_velocity_and_heater_inlet_are_measured_inputs":True,
        "pip_bore_ID_m_assumed":0.052,
        "numerical_dependencies":{"numpy":version("numpy"),"scipy":version("scipy")},
        "model_limitations":[
          "No measured exhaust diameter, corrected true mass flow or exhaust-tap pressure",
          "Modelled bed outlet is assumed equal to exhaust-pipe gas temperature",
          "Bed constant-density gas inventory while exhaust boundary uses ideal-gas density",
          "2022 rig geometry may differ from 2024 apparatus and slag cp(T) is unverified",
          "1-D gas/solid model omits radial gradients and horizontal buoyancy",
          "No independent full experimental predictive-validation acceptance",
        ],
        "runs":{
            str(n):{
                "cells":n,
                "time_s":runs[n]["model_time_s"],
                "model_exhaust_C":runs[n]["predicted_exhaust_C"],
                "measured_exhaust_C_for_evaluation_only":runs[n]["measured_exhaust_C_evaluation_only"],
                "observed_first_80C_s":runs[n]["measured_first_80C_s"],
                "model_first_80C_s":runs[n]["predicted_first_80C_s"],
                "RMSE_C_NOT_VALIDATION":runs[n]["rmse_C"],
                "MAE_C_NOT_VALIDATION":runs[n]["mae_C"],
                "max_relative_flow_fixed_point_residual":runs[n]["flow_implicit_convergence_max_rel"],
                "mean_flow_iterations":runs[n]["flow_implicit_mean_iterations"],
                "max_absolute_step_energy_residual_J":runs[n]["internal_energy_residual_max_absolute_J"],
            } for n in MESHES
        },
        "refinement":refinement,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_no_target_leak_512_mesh.json"))
    args=p.parse_args()
    result=run(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    for n in MESHES:
        a=result["runs"][str(n)]
        print("NO_TARGET_LEAK_FINE_MESH",
              f"N={n}",
              f"RMSE_C_NOT_VALIDATION={a['RMSE_C_NOT_VALIDATION']:.4f}",
              f"predicted_breakthrough_s={a['model_first_80C_s']}",
              f"flow_fp_max_rel={a['max_relative_flow_fixed_point_residual']:.3g}")
    for name,item in result["refinement"]["pairwise"].items():
        print("NO_TARGET_LEAK_REFINEMENT_PAIR",name,
              f"RMS_K={item['RMS_outlet_profile_difference_K']:.6f}",
              f"crossing_shift_s={item['first_80C_breakthrough_shift_s']}")
    print("NO_TARGET_LEAK_NUMERICAL_SCREEN_PASS",
          result["refinement"]["provisional_spatial_screen_pass"])
    print("EXPERIMENTAL_PREDICTIVE_VALIDATION_PASS False")


if __name__=="__main__":
    main()
