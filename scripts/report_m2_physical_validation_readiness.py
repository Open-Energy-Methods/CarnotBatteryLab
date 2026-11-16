"""External physical-validation readiness independent from mesh convergence.

Consumes BOTH real Case B 512-cell studies from the dedicated CI workflow:
- literature-inspired source target-informed exhaust flow;
- model-predicted-Tout implicit exhaust flow with no target leakage.

Neither can certify experimental validity without measured pipe bore,
pressure transducer scale/taps/uncertainty and verified sensor/material data.
This module NEVER fabricates calibration or extrapolates to other runs.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import json

SOURCE_DOI="10.17632/j37x6ptpk2.1"
CASE_B_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def assess(historic:dict,independent:dict)->dict:
    for name,payload in (("historical",historic),("predicted-exhaust",independent)):
        if payload.get("source_sha256")!=CASE_B_SHA:
            raise ValueError(f"{name} original Case B checksum mismatch")
    if independent.get("source_doi")!=SOURCE_DOI or independent.get("case")!="B_only":
        raise ValueError("wrong independent-source DOI/run")
    if historic.get("doi")!=SOURCE_DOI or historic.get("source_case")!="B_only":
        raise ValueError("wrong historical-source run")
    if independent.get("measured_Tout_excluded_from_physics") is not True:
        raise ValueError("measured temperature leaked into independent forward forcing")
    if not historic.get("flow_target_leakage_warning"):
        raise ValueError("historical mass-flow evidence not clearly classified")
    independent_grid=independent["refinement"]
    historic_grid=historic["refinement_evidence"]
    if not isinstance(independent_grid.get("provisional_spatial_screen_pass"),bool) or not isinstance(
        historic_grid.get("provisional_numerical_increment_pass_at_512"),bool):
        raise ValueError("source-locked numerical pass/fail reports absent")
    if independent_grid.get("predictive_experimental_validation_pass") is not False or (
        historic_grid.get("external_physical_validation_pass") is not False):
        raise ValueError("unqualified experimental validation claim")
    return {
        "scientific_status":"PHYSICAL_VALIDATION_BLOCKED_INSTRUMENT_METADATA",
        "doi":SOURCE_DOI,
        "raw_case_B_sha256":CASE_B_SHA,
        "historical_mesh_provisional_pass":historic_grid["provisional_numerical_increment_pass_at_512"],
        "target_independent_mesh_provisional_pass":independent_grid["provisional_spatial_screen_pass"],
        "target_independent_exhaust_flow_exists":True,
        "target_independent_mass_flow_measured_and_calibrated":False,
        "differential_pressure_units_zero_and_tap_correction_qualified":False,
        "thermocouple_geometry_uncertainty_and_lag_qualified":False,
        "slag_cp_T_k_T_and_horizontal_radial_transport_validated":False,
        "true_experimental_predictive_validation_pass":False,
        "whole_run_holdout_C_D_used_for_model_selection":False,
        "case_A_previously_inspected":True,
        "missing_evidence":{
            "gas_flow":[
                "measured internal diameter/cross-section at exhaust velocity probe",
                "calibrated hot-wire velocity traverse or matched independent flow meter",
                "gas density/pressure at actual probe and exhaust mixing/transit delay",
                "mass-flow uncertainty and possible bypass/leakage assessment"
            ],
            "pressure":[
                "raw differential-pressure units to Pa and calibration source",
                "transducer zero and uncertainty across observed range",
                "inlet/outlet pressure tap positions and independent duct/minor losses"
            ],
            "thermal":[
                "axial/radial TC positions, measured phase, time constants, uncertainty",
                "temperature-dependent measured slag/air properties and packed inventory",
                "horizontal buoyancy, radial gradient and wall/pipe thermal inertia"
            ],
        },
        "next_qualified_validation_gate":
            "source-qualified experimental boundary plus locked, no-target-leak "
            "model and independent held-out full-run thermal/pressure comparison",
        "stop_reason":
            "A 512-cell mesh pass demonstrates conditional numerical refinement "
            "only; experiment-vs-model errors remain large and physical "
            "instrument / structural evidence is missing.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--historic",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_fine_mesh_512.json"))
    p.add_argument("--target-independent",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_no_target_leak_512_mesh.json"))
    p.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/physical_validation_readiness.json"))
    args=p.parse_args()
    result=assess(json.loads(args.historic.read_text()),
                  json.loads(args.target_independent.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("HISTORICAL_NUMERICAL_SCREEN",result["historical_mesh_provisional_pass"])
    print("NO_TARGET_LEAK_NUMERICAL_SCREEN",result["target_independent_mesh_provisional_pass"])
    print("EXPERIMENTAL_VALIDATION_GATE",result["scientific_status"])
    print("EXPERIMENTAL_VALIDATION_PASS",result["true_experimental_predictive_validation_pass"])


if __name__=="__main__":
    main()
