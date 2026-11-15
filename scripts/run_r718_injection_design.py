"""Emit source-comparable R718 liquid-injection design point evidence."""
import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from importlib.metadata import version
import argparse
from carnot_battery_lab.physics.r718_injection_reference import (
    InjectionDesignInputs, solve_injection_design)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/r718_injection_design_reference.json"))
    args=p.parse_args()
    r=solve_injection_design()
    data=asdict(r)
    data["external_design_point_source"]="doi:10.18462/iir.gl.2018.1367 Table 1, Fig 2"
    data["licence"]="Publication rights remain with authors/IIR; no third-party PDF or figure redistributed"
    data["2018_reported_nominal_stage2_mdot_kg_s"]=0.222
    data["stage2_mass_flow_relative_error"]=(r.m_stage2_kg_s/0.222-1)
    data["stage1_volume_flow_relative_error"]=(r.volume_flow_stage1_m3_h/1231-1)
    data["stage2_volume_flow_relative_error"]=(r.volume_flow_stage2_m3_h/468-1)
    data["backend_version"]=version("CoolProp")
    data["input_sha256"]=sha256(json.dumps(asdict(r.inputs),sort_keys=True).encode()).hexdigest()
    data["claim_limits"]=[
        "Nominal compressor designs are not measured performance maps",
        "No pressure loss or actual stage speed/flow surge/choke map",
        "Stage-two injection mass predicted by the assumed mixing state",
        "Source 120 C inlet is an illustrative added boundary, not 80 C reference",
        "Liquid injection hardware, pressure drops, heat transfer and droplet separation not modelled",
        "Finite HX installed UA hypothetical, not geometry-derived",
        "No source/process pumping, part-load or storage coupling",
        "Thermodynamic match is not engineering certification"
    ]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"published design p ratios={r.p_ratios}; predicted stage2 mass={r.m_stage2_kg_s:.6f} vs 0.222 kg/s")
    print(f"nominal volume flows calculated={r.volume_flow_stage1_m3_h:.1f}, {r.volume_flow_stage2_m3_h:.1f} m3/h vs 1231,468")
    print(f"source T={r.source_in_C:.1f}->{r.source_out_C:.2f} C; sink={r.inputs.sink_in_C}->{r.inputs.sink_out_C} C")
    print(f"Qcond={r.Q_condenser_W:.1f} W; COP_gear_motor_inverter_only={r.COP_grid_no_pumps:.4f}")
    print(f"mass/mixing residual={r.injection_mixing_residual_W:.5g} W; energy residual={r.first_law_residual_W:.5g} W")


if __name__=="__main__":
    main()
