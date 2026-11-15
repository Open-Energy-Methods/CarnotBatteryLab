"""Evidence-graded R600/R718/R1233zd(E) cycle alternatives for 80C source.

Returns published operating points as unmodified literature-anchored facts
separate from a newly calculated UNQUALIFIED transcritical R600 thermodynamic
screen. Does NOT pretend R600 hardware measured at exactly source 80->70 C.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from carnot_battery_lab.physics.r600_transcritical_screen import (
    R600ScreenInputs,scan_transcritical_high_side)


EVIDENCE=[
  {
    "id":"verdnik_rieberer_2022_r600_transcritical",
    "doi":"10.1016/j.ijrefrig.2022.05.010",
    "working_fluid":"R600 n-butane",
    "natural_refrigerant":True,
    "study_type":"experiment_and_model",
    "source_inlet_C":60.0,
    "source_outlet_C":None,
    "evaporating_C":None,
    "process_return_C":None,
    "process_supply_C":160.0,
    "heating_COP":3.1,
    "heat_output_kW":24.2,
    "compressor_description":"single-stage suction-gas-cooled reciprocating with IHX",
    "coverage":"reported experimental point; NO 80C source experiment asserted",
  },
  {
    "id":"ramirez_2024_r1233zde_source80",
    "doi":"10.1016/j.applthermaleng.2024.122961",
    "working_fluid":"R1233zd(E) HFO",
    "natural_refrigerant":False,
    "study_type":"experiment",
    "source_inlet_C":80.0,
    "source_outlet_C":None,
    "evaporating_C":None,
    "process_return_C":None,
    "process_supply_C":148.5,
    "heating_COP":3.6,
    "heat_output_kW":38.6,
    "electric_input_kW":10.7,
    "compressor_description":"variable-speed piston with external subcooler",
    "coverage":"near target hardware lift only, non-natural refrigerant",
  },
  {
    "id":"wu_2019_r718_water_injected",
    "doi":"10.1016/j.energy.2019.116427",
    "working_fluid":"R718 water",
    "natural_refrigerant":True,
    "study_type":"experiment",
    "source_inlet_C":None,
    "source_outlet_C":None,
    "evaporating_C":85.0,
    "process_return_C":None,
    "process_supply_C":None,
    "condensing_C":150.0,
    "heating_COP":1.96,
    "heat_output_kW":None,
    "compressor_description":"water-injected twin-screw",
    "coverage":"85 C evaporation thermally incompatible with 80 C source",
  },
  {
    "id":"verdnik_2019_r600_source80_theoretical",
    "url":"https://waermepumpe-izw.de/wp-content/uploads/2020/05/190800-ICR-1-3-E2_1186-Verdink-et-al.pdf",
    "working_fluid":"R600 n-butane",
    "natural_refrigerant":True,
    "study_type":"simulation_only_for_this_point",
    "source_inlet_C":80.0,
    "source_outlet_C":75.0,
    "evaporating_C":None,
    "process_return_C":80.0,
    "process_supply_C":160.0,
    "heating_COP":3.24,
    "heat_output_kW":None,
    "compressor_description":"R600 high-pressure-control simulated prototype, no IHX",
    "coverage":"published simulated 80/75 to 80/160, NOT experimental 80/70 -> 110/150",
  },
]


def assess_evidence(point:dict)->dict:
    """No imputation of unreported temperatures; no extrapolation counted as proof."""
    missing=[k for k in ("source_inlet_C","source_outlet_C",
                         "process_return_C","process_supply_C")
             if point.get(k) is None]
    exact=not missing and all([
      point["source_inlet_C"]==80,
      point["source_outlet_C"]==70,
      point["process_return_C"]==110,
      point["process_supply_C"]==150,
    ])
    status=("HARDWARE_MATCHED_TARGET"
            if exact and point["study_type"]=="experiment"
            and point["natural_refrigerant"]
            else "NOT_QUALIFIED_AT_EXACT_TARGET")
    return {**point,"status":status,"missing_target_boundary_fields":missing,
            "cannot_claim_compressor_map":True}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=Path("results/natural_refrigerant_80C_screen.json"))
    args=p.parse_args()
    inputs=R600ScreenInputs()
    scan=scan_transcritical_high_side(inputs)
    payload={
        "status":"SCIENCE_SCREEN_NONQUALIFIED",
        "service_target":{
            "source_in_C":80,"source_out_C":70,"process_return_C":110,
            "process_supply_C":150,"target_process_heat_W":1_000_000,
        },
        "literature_operating_points":[assess_evidence(x) for x in EVIDENCE],
        "r600_screen_inputs":asdict(inputs),
        "r600_screen_result":scan,
        "claim":"Natural-fluid candidate identified, but no manufacturer-validated exact-target machine yet",
        "limitations":[
          "Published 60C R600 experimental source is not exact-target 80C machine",
          "Published 80/75 R600 point is SIMULATED not experimental",
          "R1233zd(E) source-80 and 148.5C sink is experimentally supported but HFO, not natural",
          "Existing water vapor 85C evaporation cannot extract heat from 80C source",
          "Single-stage R600 screen has no compressor IHX, speed/pressure map, geometry, control or safety",
          "No 1MW compressor scaling or process/TES dynamic claim is permitted",
        ],
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("NATURAL_FLUID_HARDWARE_QUALIFIED",any(
        p["status"]=="HARDWARE_MATCHED_TARGET" for p in payload["literature_operating_points"]))
    for v in scan["points"]:
        print("R600_SCREEN",v)
    print("NOTE no exact 80/70 -> 110/150 natural-fluid hardware map is established")


if __name__=="__main__":
    main()
