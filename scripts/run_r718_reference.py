"""R718 screening result with study-contract and assumption-file provenance."""
from __future__ import annotations
import argparse
from dataclasses import asdict, fields
import hashlib
import json
from pathlib import Path
import yaml

from carnot_battery_lab.physics.r718 import R718Inputs,solve_r718
from carnot_battery_lab.provenance import build_input_manifest
from carnot_battery_lab.cases import load_study_case

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',type=Path,default=ROOT/'cases/reference_industrial_heat_150C.yaml')
    parser.add_argument('--screen-params',type=Path,default=ROOT/'cases/r718_h0_screen_parameters.yaml')
    parser.add_argument('--output',type=Path,default=ROOT/'results/r718_h0_reference_screen.json')
    args=parser.parse_args()
    study=load_study_case(args.case)
    config_raw=args.screen_params.read_bytes()
    config=yaml.safe_load(config_raw)
    allowed={f.name for f in fields(R718Inputs)}
    if not isinstance(config,dict) or set(config)-allowed:
        raise ValueError('screening input contains unsupported properties')
    design=R718Inputs(**config)
    if study.service!='process_heat' or any([
        design.useful_process_heat_W!=study.load_MW_th*1e6,
        design.source_inlet_C!=study.source_inlet_C,
        design.process_return_C!=study.process_return_C,
        design.process_supply_C!=study.process_supply_C,
    ]):
        raise ValueError('screening design must preserve reference study contract')
    r=solve_r718(design)
    manifest=build_input_manifest(args.case,ROOT)
    payload=asdict(r)
    payload['study_manifest']=manifest
    payload['model_assumption_file']=str(args.screen_params.name)
    payload['model_assumptions_sha256']=hashlib.sha256(config_raw).hexdigest()
    payload['scientific_status']='numerical_screen_unvalidated_compressor_and_cost'
    payload['limitations']=[
        'No manufacturer compressor map; 5:1 per-stage assumed',
        'External intercooler coolant pump not modelled',
        'No refrigerant pressure drop or plant source/process pumps',
        'No part-load, startup or transient TES coupling',
        'UA installed independently of HX geometry and pressure losses',
        'Source outlet 70 C assumed, not present in study reference case',
    ]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'R718 two-stage COP_electric={r.COP_heating_electric:.4f}, ratio={r.stage_pressure_ratios}')
    print(f'W_electric={r.W_compressor_electric_W:.0f} W, Q_source={r.Q_source_W:.0f} W, Q_intercool={r.Q_intercool_rejected_W:.0f} W')
    print(f'First law residual={r.first_law_residual_W:.5f} W, output={args.output}')


if __name__=='__main__':
    main()
