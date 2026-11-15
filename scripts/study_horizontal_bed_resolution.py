"""Non-fitting numerical resolution and material/flow scenario study, Case B only.

Do not inspect/fit C,D reserved cases or reinterpret A as blind (A was
already evaluated in the previous exploratory development iteration).
This study deliberately never loads Case A, C or D. Use recorded source
Case B only to assess numerical error and uncertain input sensitivity.

Model-vs-experiment errors are not validity tests: forcing mdot depends on
observed Tout and assumed pipe ID, just as the source paper Eq(1).
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path

from exploratory_forward_horizontal_bed import exploratory_forward
from carnot_battery_lab.validation.flow_pressure_audit import sensitivity_scenarios


def differences(reference:dict, candidate:dict)->dict:
    if reference["source_sha256"]!=candidate["source_sha256"]:
        raise ValueError("cannot compare discretization on different raw experiments")
    if reference["time_s"]!=candidate["time_s"]:
        raise ValueError("time alignment changed during convergence study")
    errors=[a-b for a,b in zip(candidate["model_Tout_C"][1:],
                              reference["model_Tout_C"][1:])]
    return {
        "temperature_grid_RMS_difference_K":sqrt(sum(x*x for x in errors)/len(errors)),
        "temperature_grid_max_absolute_difference_K":max(abs(x) for x in errors),
        "model_80C_breakthrough_shift_s":(
            None if candidate["model_first_80C_outlet_crossing_s"] is None or
            reference["model_first_80C_outlet_crossing_s"] is None else
            candidate["model_first_80C_outlet_crossing_s"]-
            reference["model_first_80C_outlet_crossing_s"]),
    }


def study(input_dir:Path)->dict:
    profiles={}
    for name,parameters in (
        ("grid_08",{"cells":8}),
        ("grid_16",{"cells":16}),
        ("grid_32",{"cells":32}),
        ("dt_half",{"cells":16,"substeps_per_sample":2}),
        ("dt_quarter",{"cells":16,"substeps_per_sample":4}),
        ("bdf_strict",{"cells":16,"bdf_relative_tolerance":1e-9}),
        ("pipe_ID_045m",{"cells":16,"assumed_pipe_ID_m":.045}),
        ("pipe_ID_060m",{"cells":16,"assumed_pipe_ID_m":.060}),
        ("slag_cp_0800",{"cells":16,"assumed_rock_cp_J_kgK":800}),
        ("slag_cp_2300",{"cells":16,"assumed_rock_cp_J_kgK":2300}),
    ):
        run=exploratory_forward("B",input_dir=input_dir,**parameters)
        profiles[name]={
            "assumptions":parameters,
            "rmse_to_experiment_C_NOT_VALIDATION":run["rmse_C"],
            "mae_to_experiment_C_NOT_VALIDATION":run["mae_C"],
            "predicted_first_80C_s":run["model_first_80C_outlet_crossing_s"],
            "maximum_step_relative_energy_residual":run["max_relative_step_energy_residual"],
            "model_outlet_temperature_C":run["model_Tout_C"],
            "time_s":run["time_s"],
            "raw_experiment_sha256":run["source_sha256"],
        }
    baseline=profiles["grid_16"]
    ref={
        "source_sha256":baseline["raw_experiment_sha256"],
        "time_s":baseline["time_s"],
        "model_Tout_C":baseline["model_outlet_temperature_C"],
        "model_first_80C_outlet_crossing_s":baseline["predicted_first_80C_s"],
    }
    comparisons={}
    for name,run in profiles.items():
        cmp={
            "source_sha256":run["raw_experiment_sha256"],
            "time_s":run["time_s"],
            "model_Tout_C":run["model_outlet_temperature_C"],
            "model_first_80C_outlet_crossing_s":run["predicted_first_80C_s"],
        }
        comparisons[name]=differences(ref,cmp)
        del profiles[name]["model_outlet_temperature_C"]
        del profiles[name]["time_s"]
    sample=sensitivity_scenarios(Tout_C=100,velocity_m_s=5)
    return {
        "status":"CASE_B_ONLY_RESOLUTION_AND_UNCERTAINTY_SCREEN_NO_VALIDATION",
        "experiment":"10.17632/j37x6ptpk2.1/Case_B.csv",
        "frozen_data_hash":baseline["raw_experiment_sha256"],
        "unseen_evaluation_runs":["C","D"],
        "already_inspected_not_blind":"A",
        "calibration_runs":["B"],
        "source_backed_slag_cp_range_J_kgK":[800,2300],
        "nominal_pipe_ID_m":.052,
        "assumed_pipe_ID_scenarios_m":[.045,.052,.060],
        "flow_area_analytical_sensitivity":sample,
        "profiles":profiles,
        "outlet_differences_against_n16":comparisons,
        "requirements_before_claiming_numerical_convergence":[
            "actual three-level asymptotic numerical convergence in T_out(t)",
            "simulation time/step convergence demonstrated separately",
            "observed thermocline-front timing convergence with missing crossings rejected",
            "holdout C/D completely excluded from development/tuning",
        ],
        "measurement_dependency":"mass flow uses measured Tout; do NOT call this independent prediction",
        "pressure_calibration":"still blocked, native channel cannot be compared to Ergun Pa",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    ap.add_argument("--output",type=Path,default=Path("results/external_horizontal_bed/case_B_resolution_sensitivity.json"))
    args=ap.parse_args()
    result=study(args.input_dir)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    for key,profile in result["profiles"].items():
        delta=result["outlet_differences_against_n16"][key]
        print("RESOLUTION_CASE_B",key,
              f"RMSEexp={profile['rmse_to_experiment_C_NOT_VALIDATION']:.3f}",
              f"RMSagainst_n16={delta['temperature_grid_RMS_difference_K']:.4f}",
              f"first_80C={profile['predicted_first_80C_s']}")
    print("CASE_C_D_NOT_READ; STATUS=NUMERICAL_UNCERTAINTY_DIAGNOSTIC_NOT_PHYSICAL_VALIDATION")


if __name__=="__main__":
    main()
