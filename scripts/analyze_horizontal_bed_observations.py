"""Published 2024 horizontal-bed MEASURED observables, no model fitting.

CC BY 4.0 data DOI 10.17632/j37x6ptpk2.1; columns/time units follow its
README. Four cases A-D contain measured temperatures, air exhaust velocity,
and differential-pressure channel. The README does NOT specify pressure
units, so this analysis NEVER treats the channel as Pa without independent
instrumentation metadata.

Use case A only as pre-registered OUT-OF-SAMPLE physical benchmark, in line
with the 2025 companion paper's held-out experiment. No model parameters
are calibrated to A. This produces observed thresholds, not predictions.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import mean,median

DOI="10.17632/j37x6ptpk2.1"
EXPECTED={
  "A":"35558300d7d5ef7a2ccf5c039fb8f566fbcc97b8ff6ffc181af6ba567769a0e9",
  "B":"5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab",
  "C":"5bfab2554b44ec5d1b5ce1e5aecd94074c35e126f7c7ed427aa9282777b454f9",
  "D":"b6db5d44e050d0cac259db42368cea421b88cfc51a9747586e47b5c20d27493f",
}
TEMP_FIELDS=["$T_{in}$","$T_{out}$"]+[f"$T_{i}$" for i in range(1,8)]


def load_case(directory:Path,case_id:str)->dict:
    if case_id not in EXPECTED:
        raise ValueError("unknown case")
    path=directory/f"Case_{case_id}.csv"
    raw=path.read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED[case_id]:
        raise ValueError(f"case {case_id} raw data modified: {sha}")
    rows=list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    if len(rows)<50:
        raise ValueError("unexpectedly short experimental series")
    expected_fields={"Time exp.","Velocity",r"$\Delta P$",r"$T_{0}$",*TEMP_FIELDS}
    if not expected_fields.issubset(set(rows[0].keys())):
        raise ValueError(f"source measurement columns changed: {set(rows[0].keys())}")
    samples=[]
    for i,row in enumerate(rows):
        vals={}
        for field in expected_fields:
            try:
                vals[field]=float(row[field])
            except (ValueError,TypeError) as exc:
                raise ValueError(f"case {case_id} row {i}: bad measurement {field}") from exc
            if not math.isfinite(vals[field]):
                raise ValueError("nonfinite measured value")
        samples.append(vals)
    times=[r["Time exp."] for r in samples]
    if any(t2<=t1 for t1,t2 in zip(times,times[1:])):
        raise ValueError("measurement timestamps must be monotonic")
    return {"rows":samples,"sha256":sha,"case":case_id}


def first_threshold_time(records:list[dict],field:str,threshold_C:float)->float|None:
    """First rising crossing only; avoids assuming field/sensor position."""
    for prev,cur in zip(records,records[1:]):
        y1,y2=prev[field],cur[field]
        if y1<threshold_C<=y2:
            t1,t2=prev["Time exp."],cur["Time exp."]
            if y2==y1:
                return float(t2)
            return t1+(threshold_C-y1)*(t2-t1)/(y2-y1)
    return None


def summarize_case(case:dict)->dict:
    rows=case["rows"]
    times=[r["Time exp."] for r in rows]
    res={
        "case":case["case"],"source_sha256":case["sha256"],
        "time_start_s":times[0],"time_end_s":times[-1],
        "number_of_observations":len(rows),
        "sampling_median_s":median(t2-t1 for t1,t2 in zip(times,times[1:])),
        "sensor_temperature_summary_C":{},
        "pressure_channel":{
            "units":"UNKNOWN_FROM_SOURCE_README",
            "min":min(r[r"$\Delta P$"] for r in rows),
            "median":median(r[r"$\Delta P$"] for r in rows),
            "max":max(r[r"$\Delta P$"] for r in rows),
            "note":"Instrument channel cannot be converted to Pa absent independent sensor documentation/pressure tap definition",
        },
        "exhaust_velocity_m_s":{
            "min":min(r["Velocity"] for r in rows),
            "median":median(r["Velocity"] for r in rows),
            "max":max(r["Velocity"] for r in rows),
        },
        "scientific_status":"EXPERIMENTAL_OBSERVATION_NOT_MODEL_VALIDATION",
    }
    for field in TEMP_FIELDS:
        data=[r[field] for r in rows]
        res["sensor_temperature_summary_C"][field]={
           "initial":data[0],"final":data[-1],
           "maximum":max(data),"minimum":min(data),
           "first_rising_crossing_80C_s":first_threshold_time(rows,field,80.0),
           "first_rising_crossing_120C_s":first_threshold_time(rows,field,120.0),
        }
    return res


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",type=Path,default=Path("results/external_horizontal_bed"))
    p.add_argument("--output",type=Path,default=Path("results/external_horizontal_bed/measured_observations.json"))
    args=p.parse_args()
    cases={case:load_case(args.input_dir,case) for case in EXPECTED}
    summary={
        "dataset_doi":DOI,
        "original_data_class":"MEASURED",
        "data_license":"CC BY 4.0",
        "source_readme":"30-second sampling, temperatures C, velocity m/s, source differential-pressure units unstated",
        "holdout_case":"A",
        "candidate_training_cases":["B","C","D"],
        "comparisons":{cid:summarize_case(c) for cid,c in cases.items()},
        "physical_validation_status":"NOT_RUN",
        "blockers":[
            "independently verified bed diameter/length/porosity and rock particle size",
            "sensor axial coordinates and real exhaust-pipe cross-sectional area",
            "differential-pressure sensor units, zero and tap locations",
            "out-of-sample forward simulation with measured transient inlet and mass flow",
            "three-level space/time convergence and uncertainty-aware model/data comparison",
        ],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    for cid,v in summary["comparisons"].items():
        outlet=v["sensor_temperature_summary_C"]["$T_{out}$"]
        print(f"MEASURED_CASE={cid} n={v['number_of_observations']} "
              f"max_outlet_C={outlet['maximum']:.2f} "
              f"first_80C_s={outlet['first_rising_crossing_80C_s']} "
              f"pressure_native_med={v['pressure_channel']['median']:.4g} "
              f"vel_m_s_med={v['exhaust_velocity_m_s']['median']:.4g}")
    print("status=MEASURED_ONLY_NOT_VALIDATION; pressure unit unverified")


if __name__=="__main__":
    main()
