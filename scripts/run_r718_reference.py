"""Emit a documented R718 feasibility screen, not a validated plant result."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from carnot_battery_lab.physics.r718 import R718Inputs,solve_r718


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("results/r718_h0_reference_screen.json"))
    args=parser.parse_args()
    design=R718Inputs()
    r=solve_r718(design)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    payload=asdict(r)
    payload["scientific_status"]="numerical_screen_unvalidated_compressor_and_cost"
    payload["limitations"]=["No manufacturer compressor map","Illustrative 5:1/stage ratio limit",
        "Fixed intermediate coolant, its pump not modelled","No refrigerant pressure drop",
        "No part-load or transient TES coupling","Fixed heat-transfer coefficient and UA input",
        "Screening input source outlet 70C not supplied by study case YAML"]
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"R718 two-stage COP_electric={r.COP_heating_electric:.4f}, ratio={r.stage_pressure_ratios}, source_out_C={design.source_outlet_C}")
    print(f"W_electric={r.W_compressor_electric_W:.0f} W, Q_source={r.Q_source_W:.0f} W, Q_intercool={r.Q_intercool_rejected_W:.0f} W")
    print(f"First law residual={r.first_law_residual_W:.5f} W, output={args.output}")


if __name__=="__main__":
    main()
