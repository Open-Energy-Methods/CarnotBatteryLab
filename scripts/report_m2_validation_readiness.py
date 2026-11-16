"""Evaluate independent experimental validation readiness without inventing metadata.

This is a STOP GATE, not a scientific score. An accessible CC-BY time series
does not supply calibrated mass flow, transducer pressure units, tap-only
bed losses or sensor locations. Status is machine-readable in CI and
does not silently promote a numerical-resolution pass to physical validity.

Case B: model development source (not validation holdout).
Case A: previously inspected, not pristine blind.
C/D: raw source downloaded and descriptive statistics known; not used for
model parameter tuning or numerical convergence.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from carnot_battery_lab.validation.flow_pressure_audit import PressureCalibration

EXPECTED_DOI="10.17632/j37x6ptpk2.1"
SOURCE_B_SHA="5f7e6143cfb3f6e2efa2bb6a6b4061e10fe44591588f7e3b7216fa34ff6d47ab"


def assess(observations:dict,convergence:dict)->dict:
    if observations.get("dataset_doi")!=EXPECTED_DOI:
        raise ValueError("unexpected experimental dataset DOI")
    by_case=observations.get("comparisons",{})
    if "B" not in by_case or by_case["B"]["source_sha256"]!=SOURCE_B_SHA:
        raise ValueError("source-locked experimental Case B must be present")
    if convergence.get("case")!="B ONLY" or not isinstance(
            convergence.get("numerical_resolution_pass"),bool):
        raise ValueError("qualified numerical convergence assessment is required")
    missing={
        "mass_flow":[
            "traceable exhaust pipe measured internal bore/area at velocity probe",
            "hot-wire spatial calibration or cross-section velocity correction",
            "measured exhaust pressure and transport delay",
            "outlet pipe leakage/bypass assessment and flow uncertainty"
        ],
        "pressure":[
            "2024 differential pressure native-units-to-Pa source calibration",
            "transducer zero and precision over measured range",
            "independently measured duct/minor losses between pressure taps",
            "pressure tap positions and fluid-property variation"
        ],
        "thermal":[
            "unambiguous thermocouple axial/radial coordinates and measured phase",
            "sensor accuracy and time constants",
            "measured slag cp(T)/k(T)/particle distribution",
            "2D horizontal-buoyancy/radial-mixing discrepancy analysis"
        ],
    }
    cal=PressureCalibration(channel_name="2024 original CSV differential pressure")
    return {
        "status":"EXPERIMENTAL_MODEL_VALIDATION_BLOCKED",
        "source_doi":EXPECTED_DOI,
        "case_B_sha256":SOURCE_B_SHA,
        "measurement_data_acquired":True,
        "numerical_resolution_pass":convergence["numerical_resolution_pass"],
        "mass_flow_calibration_pass":False,
        "pressure_calibration_pass":not bool(cal.missing()),
        "pressure_calibration_missing_machine_fields":cal.missing(),
        "thermal_sensor_and_material_metadata_pass":False,
        "full_experimental_validation_pass":False,
        "missing_independent_source_information":missing,
        "calibration_and_holdout_integrity":{
            "development_case":"B",
            "case_A_previously_inspected":True,
            "cases_C_D_not_used_to_select_physics":True,
            "case_C_D_descriptive_statistics_seen":True,
            "qualified_blind_holdout_available":False,
        },
        "decision":"STOP: do not certify thermal breakthrough, Ergun pressure, industry HP/TES performance or v1.0",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--observations",type=Path,default=Path(
        "results/external_horizontal_bed/measured_observations.json"))
    p.add_argument("--convergence",type=Path,default=Path(
        "results/external_horizontal_bed/case_B_spatial_convergence_assessment.json"))
    p.add_argument("--output",type=Path,default=Path(
        "results/external_horizontal_bed/experimental_validation_readiness.json"))
    args=p.parse_args()
    result=assess(json.loads(args.observations.read_text()),
                  json.loads(args.convergence.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("PHYSICAL_VALIDATION_GATE",result["status"])
    print("NUMERICAL_RESOLUTION_PASS",result["numerical_resolution_pass"])
    print("MASS_FLOW_QUALIFIED",result["mass_flow_calibration_pass"])
    print("PRESSURE_QUALIFIED",result["pressure_calibration_pass"])
    print("FULL_EXPERIMENTAL_VALIDATION_PASS",result["full_experimental_validation_pass"])


if __name__=="__main__":
    main()
