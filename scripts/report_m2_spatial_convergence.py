"""Derive transparent spatial-resolution report from source-locked Case B JSON."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from carnot_battery_lab.validation.numerical_convergence import evaluate_resolution


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_resolution_sensitivity.json"))
    parser.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_spatial_convergence_assessment.json"))
    args=parser.parse_args()
    raw=json.loads(args.input.read_text())
    result=evaluate_resolution(raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for name,value in zip(result["grid_pair_keys"],result["rms_change_K"]):
        print("CASE_B_REFINEMENT",name,f"outlet_RMS_K={value:.5f}")
    print("EMPIRICAL_OBSERVED_ORDERS",result["observed_order_from_outlet_RMS_doublings"])
    print("NUMERICAL_RESOLUTION_PASS",result["numerical_resolution_pass"])
    print("EXTERNAL_PREDICTIVE_VALIDATION_PASS",result["external_predictive_validation_pass"])


if __name__=="__main__":
    main()
