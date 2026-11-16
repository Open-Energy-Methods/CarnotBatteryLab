"""M1.4: machine-readable, input-hashed compressor MAP-REQUIREMENT dossier.

Runs actual R718 and R600 CoolProp-based cycle hypotheses at the H-REF
boundary. Exports required suction volume, stage ratio, flow, P/T and shaft
work. This is a REQUEST to obtain independently measured compressor maps,
not evidence that any actual compressor can operate at these points.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

from carnot_battery_lab.physics.r718 import R718Inputs, solve_r718
from carnot_battery_lab.physics.r600_transcritical_screen import (
    R600ScreenInputs, solve_r600_screen, scan_transcritical_high_side,
)
from carnot_battery_lab.physics.gas_rock_regenerator import (
    GasRockBed, BedState,
)
from carnot_battery_lab.physics.coupled_charge import (
    ChargeControl, simulate_charge,
)
from carnot_battery_lab.physics.compressor_envelope_requirements import (
    r718_requirements_report, r600_requirements_report,
    r718_charge_trajectory_demands,
)
from carnot_battery_lab.physics.compressor_literature_gate import evidence_crosswalk


# Distinct R718 machines and different publications. These are not an
# interchangeable manufacturer's operating envelope or simultaneous points.
COMPARATORS=(
    {
        "id":"zuehlsdorf_2018_nominal_R718_two_impellers",
        "reference":"doi:10.18462/iir.gl.2018.1367",
        "class":"NOMINAL_DESIGN_RATIOS_NOT_MAP",
        "stage_ratios":(3.2,2.0),
    },
    {
        "id":"verpe_2020_R718_test_rig_stage_maxima",
        "reference":"doi:10.18462/iir.gl.2020.1019",
        "class":"EXPERIMENTAL_STAGE_MAXIMA_NOT_SIMULTANEOUS_MAP",
        "stage_ratios":(2.4,2.0),
    },
)


def compare_against_different_rig(result)->list[dict]:
    ratios=result.stage_pressure_ratios
    outcomes=[]
    for source in COMPARATORS:
        outcomes.append({
            **{k:v for k,v in source.items() if k!="stage_ratios"},
            "comparator_stage_pressure_ratios":list(source["stage_ratios"]),
            "model_stage_pressure_ratios":list(ratios),
            "model_exceeds_one_or_more_reference_stage_ratios":any(
                a>b*(1+1e-10) for a,b in zip(ratios,source["stage_ratios"])),
            "manufacturer_envelope_validation":False,
            "interpretation":"Different equipment and test topology; neither nominal "
                "stage ratios nor independent maxima establish a manufacturer map",
        })
    return outcomes


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path(
        "results/m1_compressor_map_requirements_80_70_to_110_150.json"))
    args=parser.parse_args()

    hp=R718Inputs()
    r718=solve_r718(hp)
    hp_report=r718_requirements_report(r718)
    hp_report["different_machine_pressure_ratio_comparators"]=compare_against_different_rig(r718)
    bed=GasRockBed(cells=8)
    start=BedState.uniform(bed,95.)
    trajectory={}
    for count in (2,16,32):
        control=ChargeControl(dt_s=120.,number_of_steps=count)
        charge=simulate_charge(bed,start,hp,control)
        result=r718_charge_trajectory_demands(charge,hp,bed,control)
        result["number_of_charge_steps_requested"]=count
        result["number_of_charge_steps_completed"]=len(charge.steps)
        trajectory[f"{count}_charge_steps"]=result

    base=R600ScreenInputs()
    scan=scan_transcritical_high_side(base)
    r600_demands={}
    for point in scan["points"]:
        if point["status"]!="FINITE_HX_THERMODYNAMIC_SCREEN_PASS":
            continue
        case=replace(base,high_pressure_Pa=point["pressure_Pa"])
        result=solve_r600_screen(case)
        r600_demands[str(int(point["pressure_Pa"]))]=r600_requirements_report(result)

    input_contract={
        "r718":asdict(hp),
        "r600":asdict(base),
        "bed":asdict(bed),
        "initial_state":asdict(start),
        "charge_steps":[2,16,32],
        "charge_dt_s":120.,
        "R600_pressures_Pa":[v["pressure_Pa"] for v in scan["points"]],
        "stage_pressure_ratio_comparator_provenance":list(COMPARATORS),
    }
    report={
        "evidence_status":"M1_4_SCIENTIFIC_REQUIREMENTS_AND_LITERATURE_CROSSWALK_ONLY",
        "inputs_sha256":sha256(json.dumps(input_contract,sort_keys=True).encode()).hexdigest(),
        "input_contract":input_contract,
        "r718_80C_source_110_150C_direct_liquid_screen":hp_report,
        "r718_TES_responsive_charging_envelope_demands":trajectory,
        "r600_80C_source_110_150C_transcritical_screen":{
            "thermodynamic_scan":scan,
            "map_requirements_for_numerically_feasible_points":r600_demands,
            "manufacturer_map_qualified":False,
        },
        "independent_literature_crosswalk":evidence_crosswalk(),
        "missing_map_request":[
            "Original manufacturer compressor speed lines including mass and inlet volumetric flow",
            "Suction and outlet absolute pressure/temperature and full pressure-ratio range",
            "Isentropic efficiency, electrical/shaft power, measured uncertainty at every speed point",
            "Surge, choke, safe oil discharge-temperature and casing pressure limits",
            "Physical source 80 to 70C and process 110 to 150C at actual source/sink flow caps",
            "Installed heat exchangers, refrigerant pressure losses, IHX/intercooler topology and auxiliaries",
            "Measured multi-point capacity and qualified unit/trains at total 1MW, with part-load map",
            "Independent measurement traces and uncertainty permitting reserved-point comparison",
        ],
        "equipment_qualified":False,
        "industrial_process_heat_validation":False,
        "R718_original_5to1_guard_is_manufacturer_limit":False,
        "R600_best_scan_pressure_is_rated_operation":False,
        "all_scenarios_round_trip_efficiency":None,
        "matched_Carnot_battery_architecture_rank":None,
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf8")

    print("M1_4_HARDWARE_QUALIFIED=False")
    for stage in hp_report["compressor_stage_demands"]:
        print("R718_DIRECT_STAGE",stage["stage"],
              "suction_Pa",round(stage["suction_pressure_Pa"]),
              "suction_C",round(stage["suction_temperature_C"],2),
              "pressure_ratio",round(stage["stage_pressure_ratio"],4),
              "Vdot_suction_m3_s",round(stage["suction_volumetric_flow_m3_s"],4),
              "T_discharge_C",round(stage["discharge_temperature_C"],2))
    for key,value in trajectory.items():
        print("R718_TES_TRAJECTORY",key,"completed",value["charge_completed"],
              "points",len(value["points"]),
              "termination",value["charge_termination_reason"])
    print("R600_SCREEN_FEASIBLE_NOMINAL_POINTS",len(r600_demands),
          "OF",len(scan["points"]))
    for pressure,entry in r600_demands.items():
        stage=entry["compressor_stage_demands"][0]
        print("R600_NOMINAL",pressure,
              "ratio",round(stage["stage_pressure_ratio"],4),
              "Vdot_suction_m3_s",round(stage["suction_volumetric_flow_m3_s"],4),
              "T_discharge_C",round(stage["discharge_temperature_C"],2))
    print("PUBLISHED_INDEPENDENT_MAP_AT_EXACT_TARGET=False; EVERY DEMAND UNQUALIFIED")


if __name__=="__main__":
    main()
