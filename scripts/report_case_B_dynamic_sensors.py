"""External Case-B-only dynamic mixed-contact TC scenario diagnostics.

Requires original source-locked forward states from study_case_B_sensor_phase_envelopes.
The simulated gas/solid fields are computed using measured Tin and velocity
and ASSUMED 52-mm bore, but NO post-initialisation measured TC or Tout.
The initial field does use source TC at t0 with assumed 50-mm offset.

Sensor positions, gas contact, and lag scenarios are frozen in source
code before any measurement comparison; NO minimisation/parameter fitting
is performed, and an all-scenarios min/max envelope is NOT a physical
measurement uncertainty interval or independent validation.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from statistics import mean

from carnot_battery_lab.validation.dynamic_thermocouples import (
    uncalibrated_scenario_envelope)

SOURCE_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def report(input_data:dict)->dict:
    if input_data.get("original_csv_sha256")!=SOURCE_SHA or (
        input_data.get("source_doi")!="10.17632/j37x6ptpk2.1"
    ) or input_data.get("phase_states_from_predicted_Tout_no_later_TC_target_input") is not True:
        raise ValueError("wrong source or target-leaking forward phase states")
    series=input_data["forward_phase_states"]
    if len(series)<10:
        raise ValueError("source has no substantive state series")
    times=[float(row["time_s"]) for row in series]
    gas=[tuple(float(v) for v in row["gas_K"]) for row in series]
    rock=[tuple(float(v) for v in row["solid_K"]) for row in series]
    envelope=uncalibrated_scenario_envelope(times,gas,rock)
    if tuple(times)!=envelope["time_s"]:
        raise ValueError("misaligned model time axis")
    observed=input_data["sensor_time_series"]  # excludes t0 used in initial state
    result={}
    for i in range(7):
        name=f"T{i+1}"
        obs=observed[name]
        if len(obs)!=len(times)-1:
            raise ValueError("sensor observation count differs from predicted mesh states")
        # First TC record is excluded because it reconstructed the initial state.
        y=[float(v["source_measured_TC_C"])+273.15 for v in obs]
        lo=list(envelope["low_K"][i][1:])
        hi=list(envelope["high_K"][i][1:])
        if any(float(v["time_s"])!=t for v,t in zip(obs,times[1:])):
            raise ValueError("source/simulated timestamps mismatched")
        distances=[max(a-m,m-b,0.) for m,a,b in zip(y,lo,hi)]
        if not all(math.isfinite(x) for x in distances):
            raise ValueError("non-finite sensor comparison")
        result[name]={
            "times_s":times[1:],
            "measured_C":[x-273.15 for x in y],
            "lower_hypothesis_extrema_C":[x-273.15 for x in lo],
            "upper_hypothesis_extrema_C":[x-273.15 for x in hi],
            "sample_count":len(y),
            "outside_model_scenario_extrema_fraction":sum(d>0 for d in distances)/len(distances),
            "mean_positive_outside_distance_C":mean(distances),
            "max_positive_outside_distance_C":max(distances),
        }
    return {
        "status":"M2_DYNAMIC_CONTACT_TC_SCENARIO_DIAGNOSTIC_NOT_VALIDATED",
        "source_sha256":SOURCE_SHA,
        "source_doi":"10.17632/j37x6ptpk2.1",
        "cells":input_data["cells"],
        "source_TC_t0_initialised_model":True,
        "observed_TC_t_gt_0_not_used_to_select_any_scenario":True,
        "shared_layout_hypotheses":envelope["scenarios"],
        "unknown_2024_sensor_layout_and_contact":True,
        "uncertainty_classification":"UNWEIGHTED_DETERMINISTIC_SCENARIOS_NOT_CALIBRATED_UNCERTAINTY",
        "sensor_comparisons":result,
        "numerical_sensor_operator_mesh_converged":False,
        "experimentally_validated":False,
        "no_model_or_sensor_parameters_fitted":True,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_TC_phase_position_diagnostic.json"))
    p.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_dynamic_TC_scenarios.json"))
    a=p.parse_args()
    out=report(json.loads(a.input.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    for name,r in out["sensor_comparisons"].items():
        print("DYNAMIC_TC_UNVALIDATED",name,
              f"outside_fraction={r['outside_model_scenario_extrema_fraction']:.4f}",
              f"max_C={r['max_positive_outside_distance_C']:.3f}")
    print("EXTERNAL_MODEL_VALIDATION_PASS=False")


if __name__=="__main__":
    main()
