"""Literature-screened, EOS-based candidates; no TES heat-pump charging claim."""
import argparse,json
from pathlib import Path
from carnot_battery_lab.physics.transcritical_hp_screen import (
    ServiceEnvelope,screen_envelope,PAPER_EVIDENCE,thermal_interface_gate)

# Measured OST Purdue source differs from original design.
# All pressure grids are explicit exploratory hypotheses (not fitted to paper).
CASES={
    "OST_R600a":(100.,70.,100.,150.,"R600a"),
    "OST_mix5050":(100.,70.,100.,150.,"R290_R601a_50_50"),
    "OST_mix6040":(100.,70.,100.,150.,"R290_R601a_60_40"),
    "source80_R600a_process150":(80.,60.,110.,150.,"R600a"),
    "source80_R600_process150":(80.,60.,110.,150.,"R600"),
    "source80_mix5050_process150":(80.,60.,110.,150.,"R290_R601a_50_50"),
    "source80_R600a_charge195":(80.,60.,110.,195.,"R600a"),
    "source80_R600_charge195":(80.,60.,110.,195.,"R600"),
    "source80_mix5050_charge195":(80.,60.,110.,195.,"R290_R601a_50_50"),
}

def run(case):
    source_in,source_out,sink_in,sink_out,fluid=CASES[case]
    envelope=ServiceEnvelope(source_in,source_out,sink_in,sink_out)
    hp=screen_envelope(envelope,fluid)
    gate=thermal_interface_gate(sink_out)
    if sink_out==150. and gate["thermally_compatible_without_booster"]:
        raise RuntimeError("forbidden TES temperature acceptance")
    if hp["best"] is not None:
        z=hp["best"]
        assert z["energy_residual_W"]==0. or abs(z["energy_residual_W"])<.2
        assert z["compressor_rating_margin_C"]>=-1e-7
        assert z["gas_cooler_min_approach_K"]>=envelope.approach_min_K-1e-4
        assert z["evaporator_min_approach_K"]>=envelope.approach_min_K-1e-4
        assert z["power_compressor_electric_W"]>0
        assert abs(z["source_heat_W"]+z["compressor_shaft_W"]-z["heating_W"])<.2
    result=dict(case=case,fluid=fluid,heat_pump=hp,charging_thermal_interface_gate=gate,
        published_reference=PAPER_EVIDENCE["PURDUE_2026"] if case.startswith("OST_") else None,
        TES_charging_verified=False,matched_80C_TES_heat_pump_architecture_qualified=False,
        compressor_performance_calibrated=False,
        hardware_qualified=False,high_pressure_safety_qualified=False,
        experimental_operating_points_reproduced=False)
    print(json.dumps({k:v for k,v in result.items() if k!="published_reference"}),flush=True)
    return result

def aggregate(folder):
    records={}
    for p in folder.rglob("case_*.json"):
        c=json.loads(p.read_text());name=c["case"]
        if name not in CASES or name in records:raise ValueError("unknown/duplicate case")
        a=CASES[name]
        if c["fluid"]!=a[4] or tuple(c["heat_pump"]["assumptions"][k] for k in
            ("source_in_C","source_out_C","sink_in_C","sink_out_C"))!=a[:4]:
            raise ValueError("incorrect source-service provenance")
        records[name]=c
    if set(records)!=set(CASES):raise ValueError("incomplete EOS study")
    # Do not confuse a 150C process sink with a 190C gas charging target.
    for k,v in records.items():
        if CASES[k][3]==150. and v["charging_thermal_interface_gate"]["thermally_compatible_without_booster"]:
            raise ValueError("physically impossible 150C TES charging gate")
        if v["TES_charging_verified"] or v["experimental_operating_points_reproduced"]:
            raise ValueError("unsupported qualification claim")
    out=dict(cases={k:dict(status=v["heat_pump"]["status"],best=v["heat_pump"]["best"],
          rejections=v["heat_pump"].get("rejections"),charging_gate=v["charging_thermal_interface_gate"])
          for k,v in records.items()},
        source_condition_provenance={"OST_experiment_C":(100,70),"CarnotBatteryLab_original_C":(80,60)},
        last_80C_TES_charge_target_C=190.,
        compressor_data_requested_from_OST=True,measurement_dataset_not_yet_available=True,
        equipment_selection_validated=False,thermal_integration_validated=False,
        Carnot_battery_RTE=None,
        no_positive_charge_architecture_forced=True)
    print(json.dumps(out),flush=True)
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--case",choices=CASES);p.add_argument("--aggregate",type=Path)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if bool(a.case)==bool(a.aggregate):p.error("choose exactly one mode")
    result=run(a.case) if a.case else aggregate(a.aggregate)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
