"""Generate machine-readable M1 scientific-audit comparisons (not a validated HP)."""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse
import json

from carnot_battery_lab.physics.r718 import R718Inputs, solve_r718
from carnot_battery_lab.physics.auxiliary_hydraulics import add_liquid_auxiliaries
from carnot_battery_lab.physics.compressor_evidence import (
    DESIGN_2018, compare_required_stage_ratios)
from carnot_battery_lab.physics.hx_convergence import hx_resolution_study


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=Path("results/m1_reference_evidence.json"))
    args=ap.parse_args()
    r=solve_r718(R718Inputs())
    reference={
        "nominal_2018": [dict(asdict(x),**x.property_check()) for x in DESIGN_2018],
        "comparison_2018": compare_required_stage_ratios(r,reference="design_2018"),
        "comparison_measured_2020": compare_required_stage_ratios(
            r,reference="measured_2020"),
        "fluid_hydraulics": {
            key:([asdict(x) for x in value] if key=="circuits" else value)
            for key,value in add_liquid_auxiliaries(r).items()
        },
        "hx_quadrature_convergence": [asdict(x) for x in hx_resolution_study(r.inputs)],
        "screen_COP_electric_without_aux": r.COP_heating_electric,
        "screen_stage_ratios": r.stage_pressure_ratios,
        "screen_first_law_residual_W": r.first_law_residual_W,
        "scientific_status": "screening_model_plus_independent_design_point_checks",
        "external_reference_ids": [
            "doi:10.18462/iir.gl.2018.1367 Table 1 design point",
            "doi:10.18462/iir.gl.2020.1019 abstract measured stage maxima",
        ],
        "limitations": [
            "Published impeller design and measured maxima come from distinct rigs",
            "Nominal stage1 and stage2 reference mass flows are not equal",
            "No actual interpolated compressor map, surge/choke or speed envelope",
            "Current 5:1-stage case exceeds reported 2018 and 2020 stage ratios",
            "Hydraulic pipe dimensions and gear/motor/inverter efficiency assumed",
            "No refrigerant-side pressure loss or plant transient modelling",
            "IF97/HEOS consistency and first-law closure are not external plant validation",
        ]
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(reference,indent=2,sort_keys=True)+"\n")
    print(f"saved: {args.output}")
    print(f"screen illustrative compressor-only COP={r.COP_heating_electric:.4f}")
    print(f"ratio exceeds published 2018 design: {reference['comparison_2018']['stage_ratio_exceeded']}")
    print(f"ratio exceeds 2020 measured stage maxima: {reference['comparison_measured_2020']['stage_ratio_exceeded']}")
    print(f"liquid-auxiliary COP={reference['fluid_hydraulics']['COP_grid_with_liquid_auxiliaries']:.4f}")
    print(f"last HX relative change={reference['hx_quadrature_convergence'][-1]['worst_relative_change_from_previous']:.5g}")


if __name__=="__main__":
    main()
