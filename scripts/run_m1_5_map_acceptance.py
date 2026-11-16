"""M1.5: apply independently supplied stage-map JSON to M1.4 demand dossier.

Default with NO map is a meaningful negative audit, not a fabricated map.
The M1.4 JSON must be created by scripts/run_m1_compressor_map_requirements.py
first. A map supplied later through --map-package is provenance-reported
and screened, but data authenticity and machine qualification stay external.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from carnot_battery_lab.physics.compressor_envelope_requirements import (
    CompressorStageDemand,
)
from carnot_battery_lab.physics.measured_compressor_map_gate import (
    MapThresholds,read_map_package,screen_compressor_train,
    screen_r718_charging_trajectory,
)


def sha_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--requirements",type=Path,default=Path(
        "results/m1_compressor_map_requirements_80_70_to_110_150.json"))
    p.add_argument("--map-package",type=Path,default=None,
        help="Optional externally provided, measured stage-map JSON schema")
    p.add_argument("--output",type=Path,default=Path(
        "results/m1_5_independent_compressor_map_acceptance.json"))
    args=p.parse_args()
    requirements=json.loads(args.requirements.read_text(encoding="utf-8"))
    if requirements.get("evidence_status")!=(
            "M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY"):
        raise ValueError("input is not the M1.4 independently reproducible dossier")
    maps=read_map_package(args.map_package) if args.map_package else ()
    thresholds=MapThresholds()
    r718=requirements["r718_80C_source_110_150C_direct_liquid_screen"]
    direct=screen_compressor_train(
        tuple(CompressorStageDemand(**d)
              for d in r718["compressor_stage_demands"]),
        maps,train_id="H_REF_R718_TWO_STAGE_INTERCOOLED",
        topology_id="R718_TWO_STAGE_WITH_EXTERNAL_INTERCOOLER",
        thresholds=thresholds,
    )
    trajectories={
        key:screen_r718_charging_trajectory(
            traj,maps,thresholds=thresholds)
        for key,traj in
        requirements["r718_TES_responsive_charging_envelope_demands"].items()
    }
    r600_cases={}
    for key,case in requirements["r600_80C_source_110_150C_transcritical_screen"][
            "map_requirements_for_numerically_feasible_points"].items():
        r600_cases[key]=screen_compressor_train(
            tuple(CompressorStageDemand(**d)
                  for d in case["compressor_stage_demands"]),
            maps,train_id="H_REF_R600_TRANSCRITICAL_NO_IHX",
            topology_id="R600_SINGLE_STAGE_TRANSCRITICAL_NO_IHX",
            thresholds=thresholds)
    outcomes={
        "r718_direct_liquid_process_cycle":direct,
        "r718_TES_state_responsive_charge_schedules":trajectories,
        "r600_transcritical_pressure_scenarios":r600_cases,
    }
    if not maps:
        status="NO_MEASURED_COMPRESSOR_MAPS_SUPPLIED"
    else:
        all_direct=direct["model_stage_coordinates_supported"]
        all_charges=all(x["entire_requested_trajectory_locally_supported"]
                        for x in trajectories.values())
        status=("LOCALLY_SUPPORTED_MAP_POINTS_ONLY_SYSTEM_NOT_QUALIFIED"
                if all_direct and all_charges
                else "PARTIAL_OR_NO_MAP_SUPPORT_SYSTEM_NOT_QUALIFIED")
    report={
        "status":status,
        "method":"M1_5_FIXED_SPEED_CONVEX_HULL_INDEPENDENT_HOLDOUT_SCREEN",
        "input_M1_4_requirements_sha256":sha_file(args.requirements),
        "external_map_package_sha256":sha_file(args.map_package)
            if args.map_package is not None else None,
        "maps_count":len(maps),
        "maps_provenance":[asdict(m.evidence) for m in maps],
        "source_documents_digest_checked_against_original":False,
        "quantitative_screening_thresholds":asdict(thresholds),
        "source_service_80_to_70_C":True,
        "industrial_liquid_process_return_110_supply_150_C":True,
        "nominal_process_heat_duty_W":1_000_000.,
        "results":outcomes,
        "manufacturer_certified_compressor_envelopes":False,
        "whole_H_REF_operating_trajectory_equipment_qualified":False,
        "independent_hardware_performance_validation_complete":False,
        "startup_transients_speed_ramps_and_concurrent_stage_control_qualified":False,
        "TES_experimentally_validated":False,
        "process_liquid_HX_physically_verified":False,
        "industrial_heat_delivery_qualified":False,
        "whole_system_efficiency":None,
        "architecture_ranking":None,
        "open_gates":[
            "Authentic independently reviewed measured maps per specified machine and stage",
            "Measured inlet pressure/temperature, speed-line mass and volumetric flow, shaft duty, discharge temperature and uncertainty",
            "Independent held-out predictions without fitting target operating data",
            "Rated surge/choke/oil/thermal/pressure/power limits and machine train control",
            "Verify any interpolated map predictions against independently observed operation",
            "Match 80->70C source availability, 110->150C liquid HX and plant auxiliary power",
            "Close TES thermocline/pressure experimental validation and full cycle terminal state",
        ],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("M1_5_MAP_ACCEPTANCE",status,"MAPS_SUPPLIED",len(maps))
    print("R718_DIRECT_LOCAL_SUPPORT",direct["model_stage_coordinates_supported"])
    for name,case in trajectories.items():
        print("R718_CHARGE",name,"completed",case["requested_trajectory_complete"],
              "evaluated_steps",case["evaluated_steps"],
              "locally_supported",case["entire_requested_trajectory_locally_supported"],
              "termination",case["charge_termination_reason"])
    print("R600_SCREENED_PRESSURES",len(r600_cases))
    print("PHYSICAL_HARDWARE_QUALIFIED=False; MATCHED_SERVICE=False; RTE=None")


if __name__=="__main__":
    main()
