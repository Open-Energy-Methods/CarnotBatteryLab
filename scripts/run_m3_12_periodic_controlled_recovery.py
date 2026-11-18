"""Bounded feedback and periodic operation, no matched-duty claim."""
import json
from pathlib import Path
from dataclasses import replace
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
from carnot_battery_lab.physics.periodic_recovery import periodic_audit

def study():
    c=replace(ClosedCycle(),discharge_s=600.)
    cases={
        "forward_fixed":(c,False,0.),
        "reverse_fixed":(c,True,0.),
        "reverse_gain_low":(c,True,.001),
        "reverse_gain_mid":(c,True,.004),
        "reverse_gain_high":(c,True,.012),
        "reverse_gain_mid_half_step":(replace(c,max_step_s=2.5),True,.004),
        "reverse_gain_mid_refined":(replace(c,train=replace(c.train,bed_cells=5,hx_cells=5)),True,.004),
    }
    out={}
    for name,(cfg,rev,gain) in cases.items():
        result=run_closed_cycle(cfg,reverse_discharge=rev,valve_loss_K=2.,cycles=10,water_control_gain_kg_s_K=gain)
        audit=periodic_audit(result["cycle_records"])
        summary=[]
        for row in result["cycle_records"]:
            ch,d=row["charge"],row["discharge"]
            electricity=ch["heater_electric_J"]+ch["blower_electric_J"]+d["blower_electric_J"]
            summary.append(dict(cycle=row["cycle"],modeled_input_electric_J=electricity,
                qualified_heat_J=d["qualified_water_heat_J"],qualified_seconds=d["qualified_water_duration_s"],
                band_heat_J=d["water_target_band_heat_J"],band_seconds=d["water_target_band_duration_s"],
                gross_heat_J=d["water_boundary_heat_J"],water_kg=d["water_throughput_kg"],
                final_water_C=d["final_water_outlet_C"],
                qualified_heat_per_modeled_electric=d["qualified_water_heat_J"]/electricity))
        out[name]=dict(summary=summary,audit=audit,result=result)
        print(name,json.dumps({"last":summary[-1],"periodic":audit["approximate_periodic_model_gate_pass"],
            "last_gate":audit["rows"][-1]}),flush=True)
    eligible={k:v["summary"][-1] for k,v in out.items()
        if k in ("reverse_gain_low","reverse_gain_mid","reverse_gain_high")
        and v["audit"]["approximate_periodic_model_gate_pass"]}
    best=max(eligible,key=lambda k:eligible[k]["band_heat_J"]) if eligible else None
    return dict(research_stage="M3_12_PERIODIC_CONTROLLED_RECOVERY_MODEL_ONLY",cases=out,
        best_screened_periodic_gain_by_band_heat=best,hardware_qualified=False,
        industrial_matched_service=False,experimental_validation=False,Carnot_battery_RTE=None)

if __name__=="__main__":
    x=study()
    p=Path("results/m3_12_periodic_controlled_recovery.json")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
