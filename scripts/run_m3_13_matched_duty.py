"""Predeclared fixed-service screen; a low duty is not equivalent to a high duty."""
import json
from dataclasses import replace
from pathlib import Path
from carnot_battery_lab.physics.closed_real_air_cycle import ClosedCycle,run_closed_cycle
from carnot_battery_lab.physics.periodic_recovery import periodic_audit

def study():
    c=replace(ClosedCycle(),discharge_s=600.)
    cases={
        "reverse_500W":(c,True,500.,True),
        "reverse_1000W":(c,True,1000.,True),
        "reverse_2000W":(c,True,2000.,True),
        "reverse_3400W":(c,True,3400.,True),
        "forward_1000W":(c,False,1000.,True),
        "reverse_1000W_no_bypass":(c,True,1000.,False),
        "reverse_1000W_bed_refined":(replace(c,train=replace(c.train,bed_cells=5)),True,1000.,True),
        "reverse_1000W_hx_refined":(replace(c,train=replace(c.train,hx_cells=5)),True,1000.,True),
        "reverse_1000W_half_step":(replace(c,max_step_s=2.5),True,1000.,True),
    }
    out={}
    for name,(cfg,rev,duty,bypass) in cases.items():
        v=run_closed_cycle(cfg,reverse_discharge=rev,valve_loss_K=2.,cycles=10,
                           process_duty_W=duty,process_bypass=bypass)
        audit=periodic_audit(v["cycle_records"])
        summaries=[]
        for row in v["cycle_records"]:
            ch,d=row["charge"],row["discharge"]
            demand=duty*d["duration_s"]
            summaries.append(dict(cycle=row["cycle"],demand_W=duty,requested_J=demand,
                delivered_J=d["water_boundary_heat_J"],deficit_J=d["process_duty_deficit_J"],
                excess_J=d["process_duty_excess_J"],matched_seconds=d["simultaneous_target_duration_s"],
                matched_heat_J=d["simultaneous_target_heat_J"],grade_heat_J=d["qualified_water_heat_J"],
                delivered_water_kg=d["water_throughput_kg"],bypass_water_kg=d["bypass_water_throughput_kg"],
                final_water_C=d["final_water_outlet_C"],
                modeled_electric_J=ch["heater_electric_J"]+ch["blower_electric_J"]+d["blower_electric_J"]))
        last=summaries[-1]
        # A strict full-service gate includes every accepted node, not just integral averages.
        d=v["cycle_records"][-1]["discharge"]
        full=bool(audit["approximate_periodic_model_gate_pass"] and
                  d["min_water_outlet_C"]>=149.5 and d["max_water_outlet_C"]<=150.5 and
                  d["min_delivered_duty_W"]>=.9985*duty and d["max_delivered_duty_W"]<=1.0015*duty and
                  last["matched_seconds"]>=cfg.discharge_s-1e-6)
        out[name]=dict(summary=summaries,periodic_audit=audit,full_modeled_service_gate=full,result=v)
        print(name,json.dumps(dict(last=last,periodic=audit["approximate_periodic_model_gate_pass"],full=full)),flush=True)
    return dict(research_stage="M3_13_FIXED_PROCESS_DEMAND_MODEL_ONLY",cases=out,
                industrial_matched_service=False,hardware_qualified=False,experimental_validation=False,Carnot_battery_RTE=None)

if __name__=="__main__":
    p=Path("results/m3_13_matched_duty.json")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(study(),indent=2,allow_nan=False)+"\n")
